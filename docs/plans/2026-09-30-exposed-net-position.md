# Exposed Net Position Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure each firm's net auction position on the volume whose revenue actually moves with the day-ahead price, then rerun legs A and B and the chapter's net-buyer shares on it.

**Architecture:** One rule in `scripts/lib/omie_owner.py` marks regulated last-resort suppliers as pass-through. One builder, `scripts/analysis/firm_x.py` (generalised from `edp_x_all_periods.py`), computes net position, residual-demand slope and X for the five large firms in every period, both as built and exposed. The consumers of X read that one table instead of each computing n. `firm_incentive_rebuild.py` gets the same correction for the chapter's all-firm panel, and the two independent computations must agree.

**Tech Stack:** Python 3.14 in `.venv`, pandas 3.0, pyarrow 25. No pytest in this repo: checks are `scripts/qa/` scripts and builder reports that exit non-zero on failure.

**Spec:** `docs/specs/2026-09-29-thesis-framework-design.md` §2.4 and §8 steps 2–3.

## Global Constraints

- Always run Python as `.venv/bin/python`, never bare `python3` (CLAUDE.md).
- Scripts resolve the repo root from their own location; never hardcode paths.
- `$SCRATCH` below is the session scratchpad; logs go there, not into the repo.
- Commit messages: imperative, present tense, ≤72-character subject, ending with the `Co-Authored-By` line the session specifies.
- Never commit anything under `data/` or `outputs/tables/*.parquet`.
- X is undefined where the slope is below `MIN_SLOPE = 5.0` MW per €/MWh.
- The band half-width is `H = 5.0` €/MWh, as everywhere in legs A and B.
- The five firms: `EDP`, `IBERDROLA`, `ENDESA`, `NATURGY`, `REPSOL`.
- Pass-through entities are excluded from n **and** their offers count as a rival's in the slope (they are not the firm's to control).
- Old results are not deleted from the notes. They are marked superseded, with a pointer to the rerun.

## Review Focus

1. **A renamed regulated supplier.** EDP's supplier was `EDP SERVIÇO UNIVERSAL` before 2021 and `SU ELETRICIDADE, S.A.` after; both must match. Test in Task 1.
2. **A name that merely looks regulated.** `NEXT ENERGIA XXI SL`, `SERVIGAS S.XXI S.A.`, `TRADE UNIVERSAL ENERGY, S.A.` must not match. Test in Task 1.
3. **Periods where a firm cleared nothing.** They must carry net 0, not be missing, or day means are taken over the wrong periods. Row count = periods × firms, tested in Task 4.
4. **The exposed slope can only be flatter than the as-built one** (it gives back pass-through offers to the rivals and removes fewer own buys). Any period with `slope_net < slope_built` is a bug. Tested in Tasks 3 and 4.
5. **EDP Comercial counted twice or not at all** after the group merge. After Task 2 it must map to EDP everywhere, and `firm_x`'s as-built EDP X must reproduce the old panel X, which already included it. Tested in Tasks 2 and 5.

---

### Task 1: The pass-through rule

**Files:**
- Modify: `scripts/lib/omie_owner.py` (append after `owner_group`)
- Create: `scripts/qa/check_exposed_position.py`

**Interfaces:**
- Produces: `is_pass_through(name: str | None) -> bool`; `exposed_group(name: str | None) -> str | None`; `PASS_THROUGH_MARKERS: tuple[str, ...]`.

- [ ] **Step 1: Write the failing check**

Create `scripts/qa/check_exposed_position.py`:

```python
#!/usr/bin/env python3
"""The pass-through rule matches exactly the regulated suppliers.

    .venv/bin/python scripts/qa/check_exposed_position.py

Framework spec §2.4. Pins the set of OMIE owner strings the rule matches, so a
registry snapshot that adds or renames a regulated supplier fails here instead
of silently changing a firm's net position. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import exposed_group, is_pass_through, owner_group  # noqa: E402

GROUPS = ROOT / "data/omie/registry/owner_groups.parquet"

# Every owner string in owner_groups.parquet the rule must match (2026-09-30).
EXPECTED = {
    "BASER COMERCIALIZADORA DE REFERENCIA SA",
    "CHC COMERCIALIZADOR DE REFERENCIA, A.L.U.",
    "COMERCIALIZADOR DE REFERENCIA ENERGÉTICO, S.L.U",
    "COMERCIALIZADORA REGULADA GAS POWER, S.A",
    "CURENERGÍA COMERCIALIZADOR DE ÚLTIMO RECURSO, SAU",
    "E.ON COMERC. DE ULTIMO RECURSO, S.L. (REP. RE)",
    "E.ON COMERCIALIZADORA DE ULTIMO RECURSO, S.L.",
    "EDP COMERCIALIZADORA DE ULTIMO RECURSO SA",
    "EDP SERVIÇO UNIVERSAL",
    "ENDESA ENERGIA XXI, S.L.",
    "ENDESA ENERGIA XXI, S.L. (REP. RE)",
    "ENERGÍA XXI COMERCIALIZADORA DE REFERENCIA, S.L.",
    "IBERDROLA COMERC. DE ÚLTIMO RECURSO, SA (REP.RE)",
    "IBERDROLA COMERCIALIZACIÓN DE ÚLTIMO RECURSO, SA",
    "REGSITI COMERCIALIZADORA REGULADA, S.L.U.",
    "SU ELETRICIDADE, S.A.",
    "VIESGO COMERCIALIZADORA DE REFERENCIA, S.L.",
}

# Exposed entities of the five firms, and names that only look regulated.
MUST_NOT = [
    "EDP COMERCIAL COMERCIALIZACAO DE ENERGIA SA", "EDP GEM PORTUGAL S.A.",
    "EDP ESPAÑA, S.A.U. (COMERCIAL)", "IBERDROLA CLIENTES ESPAÑA S.A.U",
    "IBERDROLA ENERGÍA ESPAÑA S..A.", "ENDESA ENERGÍA", "GAS NATURAL COMERCIALIZADORA",
    "REPSOL COMERCIALIZADORA DE ELECTRICIDAD Y GAS SLU", "NEXT ENERGIA XXI SL",
    "MYEN XXI SL", "SERVIGAS S.XXI S.A.", "TRADE UNIVERSAL ENERGY, S.A.",
    "GRUPO ENERGÉTICO ASECOR S.L",
]


def main() -> int:
    fails: list[str] = []
    for s in sorted(EXPECTED):
        if not is_pass_through(s):
            fails.append(f"should match: {s!r}")
        if exposed_group(s) is not None:
            fails.append(f"exposed_group should be None: {s!r}")
    for s in MUST_NOT:
        if is_pass_through(s):
            fails.append(f"should NOT match: {s!r}")
        if exposed_group(s) != owner_group(s):
            fails.append(f"exposed_group should equal owner_group: {s!r}")
    if is_pass_through(None) or is_pass_through("  ") or exposed_group(None) is not None:
        fails.append("null or blank names must give False / None")

    g = pd.read_parquet(GROUPS, columns=["agent_owner"])
    got = set(g.agent_owner[g.agent_owner.map(is_pass_through)])
    for s in sorted(got - EXPECTED):
        fails.append(f"unexpected match in owner_groups: {s!r}")
    for s in sorted(EXPECTED - got):
        fails.append(f"expected string absent from owner_groups: {s!r}")

    print(f"pass-through strings matched in owner_groups: {len(got)} (expected {len(EXPECTED)})")
    for f in fails:
        print(f"  FAIL {f}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python scripts/qa/check_exposed_position.py`
Expected: `ImportError: cannot import name 'exposed_group' from 'omie_owner'`.

- [ ] **Step 3: Implement the rule**

Append to `scripts/lib/omie_owner.py`:

```python
# Regulated last-resort suppliers. Their auction purchases and sales are passed
# through to regulated tariffs, so the day-ahead price does not reach their
# group's profit on that volume (framework spec §2.4). SU Eletricidade resells
# Portugal's feed-in renewables and buys for regulated customers; Curenergia
# buys for Spain's regulated household tariff and sells renewables it represents
# as representative of last resort. Matched on the normalised owner name, so a
# renamed entity (EDP SERVICO UNIVERSAL -> SU ELETRICIDADE, 2021) is caught
# under either name. scripts/qa/check_exposed_position.py pins what it matches.
PASS_THROUGH_MARKERS = (
    "ULTIMO RECURSO", "COMERCIALIZADORA DE REFERENCIA", "COMERCIALIZADOR DE REFERENCIA",
    "COMERCIALIZADORA REGULADA", "SERVICO UNIVERSAL", "SU ELETRICIDADE", "CURENERGIA",
    "ENDESA ENERGIA XXI", "ENERGIA XXI COMERCIALIZADORA", "REGSITI",
)


def _norm(name: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s.upper()).split())


def is_pass_through(name: str | None) -> bool:
    """True for a regulated supplier whose auction volume is passed through to tariffs."""
    if not isinstance(name, str) or not name.strip():
        return False
    n = _norm(name)
    return any(k in n for k in PASS_THROUGH_MARKERS)


def exposed_group(name: str | None) -> str | None:
    """The group whose PROFIT an owner's auction volume reaches, or None.

    As owner_group, except that a regulated pass-through supplier belongs to no
    group: its volume is left out of the net position, and its offers count as
    a rival's in the residual-demand slope.
    """
    return None if is_pass_through(name) else owner_group(name)
```

- [ ] **Step 4: Run the check and confirm it passes**

Run: `.venv/bin/python scripts/qa/check_exposed_position.py`
Expected: `pass-through strings matched in owner_groups: 17 (expected 17)` then `OK`, exit 0.
If a string in `EXPECTED` is reported absent although it looks identical, print `repr()` of the registry value (trailing spaces or decomposed accents) and copy that exact value into `EXPECTED`.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/omie_owner.py scripts/qa/check_exposed_position.py
git commit -m "Add the pass-through rule for regulated suppliers"
```

---

### Task 2: Merge EDP Comercial into EDP

EDP Comercial is EDP's Portuguese liberalised retailer, standing as its own group only for want of merge evidence. Legs A and B already counted it in EDP's n; the chapter's firm panel did not. One definition everywhere.

**Files:**
- Modify: `scripts/build/build_owner_groups.py:135-145` (`GROUP_MERGES`)
- Modify: `scripts/qa/check_exposed_position.py` (add the group check)
- Modify: `CLAUDE.md` (the "One group-level merge" paragraph)
- Modify: `scripts/analysis/edp_hydro_panel.py` (docstring paragraph "EDP COMERCIAL (EDP's Portuguese retailer) stands as its own group…")

**Interfaces:**
- Produces: `owner_group("EDP COMERCIAL COMERCIALIZACAO DE ENERGIA SA") == "EDP"`, and the same for `"EDP COMERCIAL-COMERCIALIZAÇÃO DE ENERGIA"`.

- [ ] **Step 1: Confirm the ownership and record the source**

Search EDP's most recent annual report (consolidation perimeter) for "EDP Comercial – Comercialização de Energia, S.A." and note the ownership percentage and document. Proceed only if it is a full subsidiary of EDP – Energias de Portugal, S.A. for 2018–2026. If it is not, stop and report.

- [ ] **Step 2: Add the failing group check**

In `scripts/qa/check_exposed_position.py`, inside `main()` before the `print(f"pass-through strings matched…` line, add:

```python
    for s in ("EDP COMERCIAL COMERCIALIZACAO DE ENERGIA SA",
              "EDP COMERCIAL-COMERCIALIZAÇÃO DE ENERGIA"):
        if owner_group(s) != "EDP":
            fails.append(f"EDP Comercial should group as EDP: {s!r} -> {owner_group(s)!r}")
```

Run: `.venv/bin/python scripts/qa/check_exposed_position.py`
Expected: FAIL on both strings (`-> 'EDP COMERCIAL'`), exit 1.

- [ ] **Step 3: Add the merge**

In `GROUP_MERGES` in `scripts/build/build_owner_groups.py`, after the `"ENEL"` entry:

```python
    "EDP COMERCIAL": ("EDP",
        "EDP Comercial - Comercializacao de Energia, S.A. is EDP's Portuguese "
        "liberalised retailer, a full subsidiary of EDP - Energias de Portugal "
        "(<document and year from Step 1>). It stood alone for want of merge "
        "evidence in the ESIOS chain. The midday-hydro panels already counted it "
        "in EDP's net position; the firm panel did not, so EDP's retail load was "
        "missing from the chapter's net-buyer shares (merged 2026-09-30)"),
```

Replace `<document and year from Step 1>` with the source found in Step 1.

- [ ] **Step 4: Rebuild the groups and rerun the check**

Run: `.venv/bin/python scripts/build/build_owner_groups.py --save`
Expected: a line `group merge EDP COMERCIAL -> EDP: 2 entities, … units`.
Run: `.venv/bin/python scripts/qa/check_exposed_position.py`
Expected: `OK`, exit 0.

- [ ] **Step 5: Update the two prose descriptions**

In `CLAUDE.md`, change the heading sentence **"One group-level merge, 2026-09-29: `ENEL` → `ENDESA`"** to **"Two group-level merges: `ENEL` → `ENDESA` (2026-09-29) and `EDP COMERCIAL` → `EDP` (2026-09-30)"**, and add after the ENEL explanation: "EDP Comercial, EDP's Portuguese liberalised retailer, is merged on the same mechanism; the midday-hydro panels already counted it in EDP's net position and the firm panel did not."

In `scripts/analysis/edp_hydro_panel.py`, replace the docstring paragraph beginning "EDP COMERCIAL (EDP's Portuguese retailer) stands as its own group" with:

```
  EDP COMERCIAL (EDP's Portuguese retailer) is merged into EDP in
  `owner_groups.parquet` (GROUP_MERGES, 2026-09-30). It offers essentially no
  supply but buys 1.6-4.7 TWh a year in 2022-2024.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/build/build_owner_groups.py scripts/qa/check_exposed_position.py CLAUDE.md scripts/analysis/edp_hydro_panel.py
git commit -m "Merge EDP Comercial into EDP's owner group"
```

---

### Task 3: Exposed columns in the chapter's firm panel

**Files:**
- Modify: `scripts/analysis/firm_incentive_rebuild.py` (imports, `unit_firm`, `month_extras`, `build`, `report`, docstring)
- Modify: `scripts/analysis/descriptive_figures.py:227` (`net_mw` → `net_exp_mw`)

**Interfaces:**
- Consumes: `is_pass_through`, `owner_group` (Task 1).
- Produces: in `outputs/tables/firm_incentive_net.parquet`, new columns `pt_net_mw`, `pt_q_mw`, `net_exp_mw`, `q_exp_mw`, and per h in `BANDWIDTHS`: `pt_buy_h{h}`, `pt_sell_h{h}`, `slope_exp_h{h}`, `ability_exp_h{h}`, `incentive_exp_h{h}`. Existing columns unchanged.

The algebra. The panel's `slope_i_h` removed the firm's own **sell** offers, pass-through ones included (their units are role `generation`). The exposed slope gives those back to the rivals and removes only the exposed own **buy** offers:

```
slope_exp_h = slope_i_h + (pt_sell_h - (own_buy_h - pt_buy_h)) / 2h
            = slope_net_h + (pt_sell_h + pt_buy_h) / 2h   >=   slope_net_h
```

- [ ] **Step 1: Replace `unit_firm` and `month_extras`**

Change the import line to `from omie_owner import is_pass_through, owner_group  # noqa: E402` and replace both functions:

```python
def unit_firm() -> pd.DataFrame:
    """unit -> (firm, pt): the owner group, and whether the owner is pass-through."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    u["firm"] = u.agent_owner.map(owner_group)
    u["pt"] = u.agent_owner.map(is_pass_through).astype(bool)
    return u.dropna(subset=["firm"]).set_index("unit")[["firm", "pt"]]


def month_extras(ym: str, umap: pd.DataFrame, pstar: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b = b.join(umap, on="unit", how="inner")
    b["side"] = b.side.astype(str)
    b["status"] = b.status.astype(str)
    b["sgn"] = b.side.map({"V": 1.0, "C": -1.0})
    c = b[b.status == "C"]
    net = (c.power_mw * c.sgn).groupby([c.date, c.period, c.firm]).sum().rename("net_mw")
    cp = c[c.pt]
    k = [cp.date, cp.period, cp.firm]
    pt_net = (cp.power_mw * cp.sgn).groupby(k).sum().rename("pt_net_mw")
    pt_q = cp.power_mw.where(cp.side == "V", 0.0).groupby(k).sum().rename("pt_q_mw")
    o = b[b.status == "O"].merge(pstar, on=KEY, how="inner")
    o["dev"] = (o.price_eur_mwh - o.p_star).abs()
    o = o[o.dev <= max(BANDWIDTHS)]
    g = [o.date, o.period, o.firm]
    parts = [net, pt_net, pt_q]
    for h in BANDWIDTHS:
        inb = o.dev <= h
        buy, sell = inb & (o.side == "C"), inb & (o.side == "V")
        parts.append(o.power_mw.where(buy, 0.0).groupby(g).sum().rename(f"own_buy_h{h:g}"))
        parts.append(o.power_mw.where(buy & o.pt, 0.0).groupby(g).sum().rename(f"pt_buy_h{h:g}"))
        parts.append(o.power_mw.where(sell & o.pt, 0.0).groupby(g).sum().rename(f"pt_sell_h{h:g}"))
    return pd.concat(parts, axis=1).fillna(0.0).reset_index()
```

- [ ] **Step 2: Add the exposed columns in `build`**

In `build()`, rename `fmap = unit_firm()` to `umap = unit_firm()` and pass `umap` to `month_extras`. Replace the fill and the per-h loop with:

```python
    ext = ["net_mw", "pt_net_mw", "pt_q_mw"] + [
        f"{s}_h{h:g}" for h in BANDWIDTHS for s in ("own_buy", "pt_buy", "pt_sell")]
    f[ext] = f[ext].fillna(0.0)
    f["net_exp_mw"] = f.net_mw - f.pt_net_mw
    f["q_exp_mw"] = f.q_firm_mw - f.pt_q_mw
    for h in BANDWIDTHS:
        sn = f[f"slope_i_h{h:g}"] - f[f"own_buy_h{h:g}"] / (2 * h)
        ok = sn >= MIN_SLOPE
        f[f"slope_net_h{h:g}"] = sn
        f[f"ability_net_h{h:g}"] = np.where(ok & (f.q_firm_mw > 0), f.q_firm_mw / (100 * sn), np.nan)
        f[f"incentive_net_h{h:g}"] = np.where(ok, f.net_mw / (100 * sn), np.nan)
        # Exposed (framework spec §2.4): pass-through offers go back to the rivals.
        se = sn + (f[f"pt_sell_h{h:g}"] + f[f"pt_buy_h{h:g}"]) / (2 * h)
        oke = se >= MIN_SLOPE
        f[f"slope_exp_h{h:g}"] = se
        f[f"ability_exp_h{h:g}"] = np.where(oke & (f.q_exp_mw > 0), f.q_exp_mw / (100 * se), np.nan)
        f[f"incentive_exp_h{h:g}"] = np.where(oke, f.net_exp_mw / (100 * se), np.nan)
```

- [ ] **Step 3: Report both definitions, with the checks as failures**

In `report()`, add `("incentive_exp_h5", "incentive, EXPOSED net position (pass-through excluded)")` to the list of indices printed. Replace the net-buyer block and extend CHECKS, and make `report` return a bool:

```python
    for col, lab in (("net_mw", "as built"), ("net_exp_mw", "EXPOSED (pass-through excluded)")):
        print(f"\nSHARE OF FIRM-PERIODS AS A NET BUYER, {lab}")
        nb = t.assign(buyer=t[col] < 0).groupby(["firm", "year"]).buyer.mean().unstack()
        print(nb.reindex(TABLE_FIRMS).round(2).to_string())
    print("\nPASS-THROUGH VOLUME by firm (mean MW over firm-periods; nonzero only for EDP, IBERDROLA)")
    print(t.groupby("firm")[["pt_net_mw", "pt_q_mw", "pt_sell_h5", "pt_buy_h5"]].mean()
          .reindex(TABLE_FIRMS).round(1).to_string())
    bad = []
    for h in BANDWIDTHS:
        v = (f[f"slope_exp_h{h:g}"] < f[f"slope_net_h{h:g}"] - 1e-6).mean()
        print(f"  h={h:g}: slope_exp below slope_net on {v:.6f} of firm-periods (must be 0)")
        if v > 0:
            bad.append(f"slope_exp < slope_net at h={h:g}")
    other = t[~t.firm.isin(["EDP", "IBERDROLA"])]
    if (other.pt_net_mw.abs() > 0).any():
        bad.append("pass-through volume attributed outside EDP and IBERDROLA")
    for b_ in bad:
        print(f"  FAIL {b_}")
    return not bad
```

Keep the existing ENEL check and the `wrote …` line above the `bad` block. In `main()`, replace `report(build())` with `return 0 if report(build()) else 1`.

- [ ] **Step 4: Update the docstring**

Add a third numbered item to the module docstring:

```
3. PASS-THROUGH. Regulated last-resort suppliers (SU Eletricidade in EDP,
   Curenergia in Iberdrola) buy and sell volume whose cost is passed through to
   regulated tariffs (framework spec §2.4). The `*_exp_*` columns leave that
   volume out of n and q and give those units' offers back to the rivals:
       slope_exp_h = slope_net_h + (pt_sell_h + pt_buy_h) / 2h
```

- [ ] **Step 5: Run it**

Run (background; it reads every bid month):
`.venv/bin/python scripts/analysis/firm_incentive_rebuild.py > $SCRATCH/firm_incentive.log 2>&1`
Expected in the log: exit 0; `slope_exp below slope_net on 0.000000` for every h; EDP's exposed net-buyer share 0.80 or above in most years (against 0.01–0.35 as built); Iberdrola's exposed share below its as-built share; pass-through means zero outside EDP and IBERDROLA.

- [ ] **Step 6: Point the chapter figure at the exposed position**

In `scripts/analysis/descriptive_figures.py:227`, change `x.net_mw < 0` to `x.net_exp_mw < 0`, and in that figure's title or caption text add "(exposed net position)". Regenerate: `.venv/bin/python scripts/analysis/descriptive_figures.py` and confirm the buyer-share figure file's timestamp changed.

- [ ] **Step 7: Commit**

```bash
git add scripts/analysis/firm_incentive_rebuild.py scripts/analysis/descriptive_figures.py
git commit -m "Add the exposed net position to the firm incentive panel"
```

---

### Task 4: One builder for X, both definitions, every period

**Files:**
- Rename: `scripts/analysis/edp_x_all_periods.py` → `scripts/analysis/firm_x.py` (`git mv`, then rewrite)
- Modify: `scripts/analysis/water_value_across_days.py` (`X_ALL` path, `daily_x_all`, docstring)

**Interfaces:**
- Consumes: `is_pass_through`, `owner_group` (Task 1); `firm_incentive_net.parquet` exposed columns (Task 3) for validation.
- Produces: `outputs/tables/firm_x.parquet`, one row per (date, period, firm) for every price period × the five firms, columns: `date, period, resolution_min, firm, p_star, split, identity_gap, zero_price, clean, net_built_mw, net_mw, q_mw, pt_net_mw, band_mw, own_band_built_mw, own_band_mw, slope_built, slope_net, X_built, X`. `net_mw`, `slope_net` and `X` are **exposed**; `*_built` are as built. Constants `FIRMS`, `H`, `MIN_SLOPE`, `OUT`.

- [ ] **Step 1: Rename**

```bash
git mv scripts/analysis/edp_x_all_periods.py scripts/analysis/firm_x.py
```

- [ ] **Step 2: Write the builder**

Replace the whole of `scripts/analysis/firm_x.py` with:

```python
#!/usr/bin/env python3
"""The five large firms' markup term X for every period, as built and exposed.

    .venv/bin/python scripts/analysis/firm_x.py            # build + validate
    .venv/bin/python scripts/analysis/firm_x.py --report   # validate only

X = n / slope, the Hortacsu-Puller markup term, from the bids, for EDP,
Iberdrola, Endesa, Naturgy and Repsol, in every period:

    n       = cleared sell - cleared buy over the firm's units
    slope   = (all offered MW within +/-H of p* - the firm's own offered MW in
               that band, both sides) / 2H
    X       = n / slope, undefined below MIN_SLOPE

with p* the Spanish price. Two definitions of "the firm's units":

    *_built   every unit whose owner rolls up to the firm (owner_group)
    exposed   the same, less regulated pass-through suppliers (is_pass_through;
              framework spec §2.4). Their volume leaves n and their offers
              count as a rival's.

Split periods and clearing-identity failures are flagged (`clean`), zero prices
too (`zero_price`: p* <= 1), not dropped. Legs A and B use clean periods; the
firm panel's periods are `clean & ~zero_price`.

Supersedes edp_x_all_periods.py (EDP only, as built), which it reproduces.

VALIDATION (exits non-zero on failure). Against firm_incentive_net.parquet on
the periods it keeps: the as-built net and slope must reproduce net_mw and
slope_net_h5, and the exposed ones net_exp_mw and slope_exp_h5 -- a second,
independent computation of the same correction. Every period x firm is present,
and the exposed slope is never below the as-built one.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import is_pass_through, owner_group  # noqa: E402
from residual_demand import IDENTITY_TOL, KEY, ZERO_PRICE, cleared_by_period  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/firm_incentive_net.parquet"   # firm_incentive_rebuild.py
OUT = ROOT / "outputs/tables/firm_x.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
H = 5.0
MIN_SLOPE = 5.0   # MW per EUR/MWh
MW = ["net_built_mw", "net_mw", "q_mw", "pt_net_mw", "own_band_built_mw", "own_band_mw"]


def unit_map() -> pd.DataFrame:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    u["firm"] = u.agent_owner.map(owner_group)
    u["pt"] = u.agent_owner.map(is_pass_through).astype(bool)
    return u[u.firm.isin(FIRMS)].set_index("unit")[["firm", "pt"]]


def prices() -> pd.DataFrame:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "resolution_min", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    return px.rename(columns={"price_es": "p_star"})[KEY + ["resolution_min", "p_star", "split"]]


def month(ym: str, umap: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b["side"] = b.side.astype(str)
    b["status"] = b.status.astype(str)
    idg = cleared_by_period(b)[KEY + ["identity_gap"]]

    m = b.join(umap, on="unit", how="inner")
    m["sgn"] = m.side.map({"V": 1.0, "C": -1.0})
    c = m[m.status == "C"]
    fk = KEY + ["firm"]
    net_b = (c.power_mw * c.sgn).groupby([c.date, c.period, c.firm]).sum().rename("net_built_mw")
    ce, cp = c[~c.pt], c[c.pt]
    net_e = (ce.power_mw * ce.sgn).groupby([ce.date, ce.period, ce.firm]).sum().rename("net_mw")
    q_e = ce.power_mw.where(ce.side == "V", 0.0).groupby([ce.date, ce.period, ce.firm]).sum().rename("q_mw")
    pt = (cp.power_mw * cp.sgn).groupby([cp.date, cp.period, cp.firm]).sum().rename("pt_net_mw")

    o = b[b.status == "O"].merge(px[KEY + ["p_star"]], on=KEY, how="inner")
    o = o[(o.price_eur_mwh - o.p_star).abs() <= H]
    band = o.groupby(KEY).power_mw.sum().rename("band_mw")
    om = o.join(umap, on="unit", how="inner")
    own_b = om.groupby([om.date, om.period, om.firm]).power_mw.sum().rename("own_band_built_mw")
    ome = om[~om.pt]
    own_e = ome.groupby([ome.date, ome.period, ome.firm]).power_mw.sum().rename("own_band_mw")

    per = px[px.date.dt.strftime("%Y%m") == ym]
    out = per.merge(pd.DataFrame({"firm": FIRMS}), how="cross")
    out = out.merge(idg, on=KEY, how="left").merge(band.reset_index(), on=KEY, how="left")
    firm_cols = pd.concat([net_b, net_e, q_e, pt, own_b, own_e], axis=1).reset_index()
    out = out.merge(firm_cols, on=fk, how="left")
    out[MW + ["band_mw"]] = out[MW + ["band_mw"]].fillna(0.0)
    out["slope_built"] = (out.band_mw - out.own_band_built_mw) / (2 * H)
    out["slope_net"] = (out.band_mw - out.own_band_mw) / (2 * H)
    out["X_built"] = np.where(out.slope_built >= MIN_SLOPE, out.net_built_mw / out.slope_built, np.nan)
    out["X"] = np.where(out.slope_net >= MIN_SLOPE, out.net_mw / out.slope_net, np.nan)
    out["zero_price"] = out.p_star <= ZERO_PRICE
    out["clean"] = (~out.split) & (out.identity_gap <= IDENTITY_TOL)
    return out


def build() -> pd.DataFrame:
    umap, px = unit_map(), prices()
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    parts = []
    for ym in months:
        parts.append(month(ym, umap, px))
        print(f"  {ym}", flush=True, file=sys.stderr)
    d = pd.concat(parts, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} firm-periods)")
    return d


def compare(m: pd.DataFrame, a: str, b: str) -> tuple[float, float]:
    diff = (m[a] - m[b]).abs()
    print(f"    {a:14s} vs {b:14s} corr {m[a].corr(m[b]):.6f}   median |diff| {diff.median():.4f}   "
          f"p99 |diff| {diff.quantile(.99):.4f}   exact (<1e-3) {(diff < 1e-3).mean():.3f}")
    return m[a].corr(m[b]), diff.median()


def report(d: pd.DataFrame) -> bool:
    bad = []
    n_periods = d.drop_duplicates(KEY).shape[0]
    if len(d) != n_periods * len(FIRMS):
        bad.append(f"rows {len(d):,} != periods {n_periods:,} x {len(FIRMS)} firms")
    v = (d.slope_net < d.slope_built - 1e-6).mean()
    print(f"exposed slope below as-built slope on {v:.6f} of firm-periods (must be 0)")
    if v > 0:
        bad.append("slope_net < slope_built")

    p = pd.read_parquet(PANEL, columns=KEY + ["firm", "net_mw", "slope_net_h5", "net_exp_mw",
                                               "slope_exp_h5"])
    p = p[p.firm.isin(FIRMS)]
    p["date"] = pd.to_datetime(p.date)
    m = d.merge(p, on=KEY + ["firm"], how="inner", suffixes=("", "_panel"))
    print(f"\nVALIDATION against {PANEL.name}, {len(m):,} firm-periods")
    for f, g in m.groupby("firm"):
        print(f"  {f}")
        for a, b in (("net_built_mw", "net_mw_panel"), ("slope_built", "slope_net_h5"),
                     ("net_mw", "net_exp_mw"), ("slope_net", "slope_exp_h5")):
            r, med = compare(g, a, b)
            if not (r > 0.9999 and med < 1e-3):
                bad.append(f"{f}: {a} does not reproduce {b} (corr {r:.6f}, median {med:.4f})")

    c = d[d.clean].assign(year=d.date.dt.year)
    for col, lab in (("net_built_mw", "as built"), ("net_mw", "EXPOSED")):
        print(f"\nNET-BUYER SHARE of clean periods, {lab}")
        print(c.assign(b=c[col] < 0).groupby(["firm", "year"]).b.mean().unstack(0).round(2).to_string())
    day = c.assign(buyer=c.net_mw < 0).groupby(["firm", "year", "date"]).buyer.mean()
    both = ((day > 0) & (day < 1)).groupby(["firm", "year"]).sum().unstack(0)
    print("\nFIRM-DAYS WITH BOTH SIGNS of the exposed position (leg D's sample)")
    print(both.to_string())
    print(f"  total: {both.sum().to_dict()}")

    for b_ in bad:
        print(f"  FAIL {b_}")
    return not bad


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    d = pd.read_parquet(OUT) if args.report else build()
    return 0 if report(d) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Build and validate**

Run (background, ~10–20 min):
`.venv/bin/python scripts/analysis/firm_x.py > $SCRATCH/firm_x.log 2>&1`
Expected: exit 0; row count check silent; `exposed slope below as-built slope on 0.000000`; for every firm all four comparisons with corr > 0.9999 and median |diff| < 1e-3.
If EDP's `slope_built` alone fails, the cause is EDP Comercial's sell offers, which the old firm panel counted as a rival's (the panel predates the Task 2 merge). Confirm by printing EDP Comercial's in-band sell MW; if that is the whole gap, record it in the log and accept.

- [ ] **Step 4: Point leg B at the new table**

In `scripts/analysis/water_value_across_days.py`:
- change `X_ALL = ROOT / "outputs/tables/edp_x_all_periods.parquet"   # edp_x_all_periods.py` to `X_ALL = ROOT / "outputs/tables/firm_x.parquet"   # firm_x.py`;
- in `daily_x_all`, read `["date", "period", "firm", "X", "clean"]` and add `x = x[x.firm == "EDP"]` before computing `Xc`;
- in the docstring, replace "`edp_x_all_periods.py`" with "`firm_x.py`" and add the sentence: "Both use EDP's exposed net position (framework spec §2.4)."

Run: `.venv/bin/python -c "import ast,sys; ast.parse(open('scripts/analysis/water_value_across_days.py').read())"`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/firm_x.py scripts/analysis/water_value_across_days.py
git commit -m "Build X for the five firms on the exposed net position"
```

---

### Task 5: Consumers of X read `firm_x`

**Files:**
- Modify: `scripts/analysis/edp_hydro_panel.py` (constants, remove `owner_units`/`month_net`/`OWN_DEMAND` use and `X_gross`, add `attach_x`, `--attach-x` flag, docstring "incentive" paragraph)
- Modify: `scripts/analysis/iberdrola_quantity_test.py:132-153` (`firm_x`) and `:207-208` (call sites)

**Interfaces:**
- Consumes: `outputs/tables/firm_x.parquet` (Task 4).
- Produces: `edp_hydro_panel.parquet` with `net_mw`, `net_built_mw`, `slope_net`, `X` (exposed) and `X_built`, defined on the firm panel's periods only (`clean & ~zero_price`), so legs A and B change by the exposure and nothing else. `iberdrola_quantity_test.firm_x(firm: str) -> DataFrame[date, hour, X, net_mw]`.

- [ ] **Step 1: Add `attach_x` to `edp_hydro_panel.py`**

Add the constant `FIRM_X = ROOT / "outputs/tables/firm_x.parquet"   # firm_x.py` beside `OWN_DEMAND`, and the function:

```python
def attach_x(d: pd.DataFrame) -> pd.DataFrame:
    """Net position and X per owner-period from firm_x.py, on the firm panel's
    periods (clean, p* above ZERO_PRICE) so the sample is unchanged. `X` and
    `net_mw` are the EXPOSED position (framework spec §2.4); `X_built` and
    `net_built_mw` as built. MOVHERA is not in firm_x and gets NaN, as before."""
    drop = [c for c in ("net_mw", "net_built_mw", "slope_net", "X", "X_built", "X_gross")
            if c in d.columns]
    x = pd.read_parquet(FIRM_X, columns=["date", "period", "firm", "clean", "zero_price", "net_mw",
                                         "net_built_mw", "slope_net", "X", "X_built"])
    x = x[x.firm.isin(GROUPS) & x.clean & ~x.zero_price].drop(columns=["clean", "zero_price"])
    x = x.rename(columns={"firm": "group"})
    x["date"] = pd.to_datetime(x.date)
    return d.drop(columns=drop).merge(x, on=["date", "period", "group"], how="left")
```

- [ ] **Step 2: Use it in `build()` and delete the old path**

In `build()`, delete `owners = owner_units()`, the `nets` list and `nets.append(month_net(m, owners))`, the `d.merge(pd.concat(nets…))` line, the `own = pd.read_parquet(OWN_DEMAND…)` merge, and the `X_gross` and `X` lines. After `d = add_firm(add_flatness(d))` add `d = attach_x(d)`. Delete the functions `owner_units` and `month_net`, the constants `NET_OWNERS` and `OWN_DEMAND`. In the docstring's "incentive" paragraph, replace the sentences describing how net and slope are computed here with: "The owner's NET AUCTION POSITION and X come from `firm_x.py`, on the exposed position (framework spec §2.4): regulated pass-through suppliers such as SU Eletricidade are left out. `X_built` keeps the as-built value." Delete the sentence mentioning `X_gross`.

Run: `grep -n "owner_units\|month_net\|NET_OWNERS\|OWN_DEMAND\|X_gross" scripts/analysis/edp_hydro_panel.py`
Expected: no output.

- [ ] **Step 3: Add the `--attach-x` path, with the regression check**

Replace `main()` with:

```python
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="report on the saved panel only")
    ap.add_argument("--attach-x", action="store_true",
                    help="re-attach X from firm_x.parquet to the saved panel, without re-reading bids")
    args = ap.parse_args()
    if args.attach_x:
        old = pd.read_parquet(OUT)
        d = attach_x(old)
        m = old[["date", "period", "unit", "X"]].merge(d[["date", "period", "unit", "X_built"]],
                                                       on=["date", "period", "unit"]).dropna()
        diff = (m.X - m.X_built).abs()
        print(f"old X vs new X_built: corr {m.X.corr(m.X_built):.6f}, median |diff| {diff.median():.4f}, "
              f"exact (<1e-3) {(diff < 1e-3).mean():.3f} over {len(m):,} unit-periods")
        if not (m.X.corr(m.X_built) > 0.9999):
            print("FAIL: as-built X does not reproduce the saved panel's X; not overwriting")
            return 1
        d.to_parquet(OUT, index=False)
        print(f"wrote {OUT.relative_to(ROOT)}")
    else:
        d = pd.read_parquet(OUT) if args.report else build()
    report(d)
    return 0
```

- [ ] **Step 4: Run it**

Run: `.venv/bin/python scripts/analysis/edp_hydro_panel.py --attach-x > $SCRATCH/edp_panel_attach.log 2>&1`
Expected: `old X vs new X_built: corr` above 0.9999, `wrote outputs/tables/edp_hydro_panel.parquet`, then the usual report, whose "EDP NET AUCTION POSITION" table now shows negative medians in most era-hours.

- [ ] **Step 5: Replace Iberdrola's `firm_x`**

In `scripts/analysis/iberdrola_quantity_test.py`, add `FIRM_X = ROOT / "outputs/tables/firm_x.parquet"   # firm_x.py` beside `OWN`, and replace the function at lines 132-153 with:

```python
def firm_x(firm: str) -> pd.DataFrame:
    """Hourly X = exposed net position / |RD'| for one firm (firm_x.py; framework
    spec §2.4), on the firm panel's periods: clean and priced above ZERO_PRICE."""
    d = pd.read_parquet(FIRM_X, columns=["date", "period", "resolution_min", "firm", "net_mw", "X",
                                         "clean", "zero_price"])
    d = d[(d.firm == firm) & d.clean & ~d.zero_price].copy()
    d["date"] = pd.to_datetime(d.date)
    d["hour"] = to_hour(d.period, d.resolution_min)
    return d.groupby(["date", "hour"])[["X", "net_mw"]].mean().reset_index()
```

and the call sites at lines 207-208 with:

```python
    xs = pd.concat([firm_x("IBERDROLA").assign(group="IBERDROLA"),
                    firm_x("EDP").assign(group="EDP")])
```

If `OWN` and the `owner_group` import are now unused, delete them.
Run: `.venv/bin/python -c "import ast; ast.parse(open('scripts/analysis/iberdrola_quantity_test.py').read())"`
Expected: no output.

- [ ] **Step 6: Mark the two as-built diagnostics**

`own_demand_in_band.py` and `firm_net_position.py` measured the as-built position and are no longer read for X. Add this line at the end of each module docstring:

```
Describes the AS-BUILT net position. The exposed position (regulated
pass-through suppliers excluded, framework spec §2.4) is computed in firm_x.py.
```

Run: `grep -rn "own_demand_in_band.parquet" scripts/analysis/*.py`
Expected: only `own_demand_in_band.py` itself.

- [ ] **Step 7: Commit**

```bash
git add scripts/analysis/edp_hydro_panel.py scripts/analysis/iberdrola_quantity_test.py scripts/analysis/own_demand_in_band.py scripts/analysis/firm_net_position.py
git commit -m "Read X from firm_x in the hydro panels"
```

---

### Task 6: Rerun legs A and B and record what changes

**Files:**
- Modify: `notes/rq-midday-hydro.md` (new §3.20; one-line pointers in §3.10, §3.11, §3.14, §3.15, §3.16, §3.18, §3.19; §7 build order)

**Interfaces:**
- Consumes: the rewired panels (Task 5), `firm_x.parquet` (Task 4).

- [ ] **Step 1: Rerun every consumer, logging each**

```bash
for s in solar_first_stage midday_hydro_iv edp_quantity_at_price iberdrola_quantity_test water_value_revealed water_value_across_days; do
  .venv/bin/python scripts/analysis/$s.py > $SCRATCH/rerun_$s.log 2>&1; echo "$s exit $?"
done
```

Expected: every script exits 0. If `water_value_revealed.py` rebuilds from bids and is slow, run it in the background and continue with the others.

- [ ] **Step 2: Build the before/after table**

For each headline number below, take "before" from the note section cited and "after" from the matching log line:

| result | section | before |
|---|---|---|
| solar first stage on EDP's X (F) | §3.10 | from the note |
| within-day IV, EDP (β, AR set) | §3.11 | from the note |
| reshaping cascades 2024–26, quantity at median price | §3.14 | −0.111, AR [−0.18, −0.05], implied β 0.06 |
| Iberdrola best β by era; overlap at β = 1 | §3.15 | −0.75 / −0.25 / −0.5; 0.799 / 0.713 / 0.685 |
| leg B large storage pooled, all periods | §3.19 | β +0.13, AR [−0.43, 0.77], F 34.5 |
| leg B large storage 2024–26, all periods | §3.19 | β +0.09, AR [−0.72, 1.13], F 15.6 |
| EDP median X by era (midday hours) | §3.9 / panel report | from the note |

- [ ] **Step 3: Write §3.20**

Add `### 3.20 The exposed net position: what changes in legs A and B` after §3.19 with: what was wrong (one paragraph: SU Eletricidade's feed-in sales inside EDP's n; Curenergía inside Iberdrola's; EDP Comercial merged); the before/after table from Step 2; one "What it shows" list stating plainly which conclusions survive, which change, and any sign reversal; the sign of EDP's X by hour after the fix. Mark it **[preliminary]** as the other sections are.

- [ ] **Step 4: Mark the superseded sections**

At the top of each of §3.10, §3.11, §3.14, §3.15, §3.16, §3.18 and §3.19, add one line: `> **Rerun on the exposed net position in §3.20** — the figures below use n with the regulated supplier inside.` Do not delete the old figures. Update build-order items 9 and 10 in §7 with one line each pointing to §3.20.

- [ ] **Step 5: Commit**

```bash
git add notes/rq-midday-hydro.md
git commit -m "Rerun legs A and B on the exposed net position"
```

---

### Task 7: Chapter, spec, project notes and supervisor pages

**Files:**
- Modify: `notes/rq-descriptive-price-formation.md` §4.5
- Modify: `docs/specs/2026-09-29-thesis-framework-design.md` (§2.4 table, Leg A and B headings and results, §5 table, §8 steps 2–3)
- Modify: `CLAUDE.md` (owner-groups section: the pass-through rule)
- Update: supervisor artifacts `https://claude.ai/artifact/684DxKaftaqwut4Ct5akiX` and `https://claude.ai/artifact/TLZCPufGsAJ8Gi1CC4EaMo`

- [ ] **Step 1: Chapter §4.5**

Add a dated paragraph (2026-09-30) giving the exposed net-buyer shares by firm and year from `$SCRATCH/firm_incentive.log`, beside the as-built ones already there, and the exposed `incentive_exp_h5` medians for EDP and Iberdrola. State that EDP's retail load (EDP Comercial) was missing from the as-built figures and SU Eletricidade's pass-through sales were inside them. Keep the old figures, marked as built.

- [ ] **Step 2: Framework spec**

- §2.4: replace the five-sample-month table with full-panel figures from `firm_x.log` (net-buyer share of clean periods, exposed vs as built, by firm, first and last year).
- Leg A and Leg B: replace "to rerun on the exposed position" with the rerun results from §3.20, and the verdict lines accordingly.
- §5: update the EDP rows.
- §8: strike through steps 2 and 3 as done, with the date and the commits. In step 2, record that n is computed in one place, `firm_x.py` (five firms) plus `firm_incentive_rebuild.py` (all firms, chapter), that the two agree, and that `own_demand_in_band.py` and `firm_net_position.py` remain as diagnostics of the as-built measure.

- [ ] **Step 3: CLAUDE.md**

In the owner-groups section, after the group-merges paragraph, add a short paragraph: "**Regulated pass-through suppliers are excluded from every firm's net position** (`is_pass_through` / `exposed_group` in `lib/omie_owner.py`, pinned by `qa/check_exposed_position.py`). SU Eletricidade (in EDP) and Curenergía (in Iberdrola) buy and sell volume whose cost is passed through to regulated tariffs; left in, they made EDP look like a net seller when it is a net buyer in most periods. `analysis/firm_x.py` is the one place X is computed for the five large firms."

- [ ] **Step 4: Supervisor pages**

Read each artifact first (`Artifact` action `read`), then republish by `url` with: the framework page's Leg A and Leg B cards and the "Net position" bullet updated to the exposed figures; the midday-hydro page's results updated from §3.20. State on each page, in one sentence, that the regulated suppliers were removed from n on 2026-09-30 and why.

- [ ] **Step 5: Commit**

```bash
git add notes/rq-descriptive-price-formation.md docs/specs/2026-09-29-thesis-framework-design.md CLAUDE.md
git commit -m "Record the exposed net position in the chapter and the spec"
```

- [ ] **Step 6: Final checks**

Run: `.venv/bin/python scripts/qa/check_exposed_position.py` → `OK`.
Run: `.venv/bin/python scripts/analysis/firm_x.py --report > $SCRATCH/firm_x_final.log 2>&1; echo $?` → `0`.
Run: `git status --short` → clean.
