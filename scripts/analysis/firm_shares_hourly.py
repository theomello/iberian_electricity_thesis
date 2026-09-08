#!/usr/bin/env python3
"""Firm shares and implied Lerner index at market-period resolution.

    .venv/bin/python scripts/analysis/firm_shares_hourly.py            # all tiers
    .venv/bin/python scripts/analysis/firm_shares_hourly.py --tier confirmed
    .venv/bin/python scripts/analysis/firm_shares_hourly.py --save

Replaces CNMC's annual, MIBEL-wide shares with shares computed per market
period from the cleared bid data, so that

    L_it = s_it / eta_t

varies hour by hour on both sides instead of pairing a per-period elasticity
with a share held fixed for a year.

WHAT IS AND IS NOT MEASURED

`s_it` is firm i's share of **total** cleared sell volume in period t, with the
unmapped units left in the denominator. Shares are therefore understated by
construction, and so is every Lerner index below -- the same direction as the
market-wide `eta` bound. Normalising to mapped volume only would flatter the
result and is not done.

THE TIER SPLIT MATTERS, so run it both ways

`--tier confirmed` uses only units whose agent is established by the data:
ESIOS exact match, or an ESIOS agent code appearing inside the cab plant name.
The default `all` additionally uses the inferred prefix assignments
(EDP, IBE, IGN, GGN, NXV, the Portuguese hydro cascades, GED), each of which
rests on a mnemonic corroborated by the CNMC share gap rather than on direct
evidence. Coverage of generation volume is 45% versus 74%.

If a conclusion holds under both tiers, the inference does not matter. If it
does not, the conclusion depends on an assumption that no public Spanish source
can currently verify, and it must be reported that way.

COVERAGE, AND WHICH TIER TO USE FOR TRENDS

This docstring used to say coverage "rises from 49.0% in 2018 to 70.1% in 2026"
and that across-year trends were therefore unusable. Re-measured 2026-09-04,
that is no longer true of either tier:

    cleared sell volume covered   2018    2020    2022    2024    2025    2026
      inferred firm              75.6%   75.3%   80.3%   71.7%   70.4%   73.9%
      agent_owner (--tier owner) 92.9%   93.7%   95.7%   94.8%   90.1%   85.0%

The 49% figure described a build predating the 2026-08 prefix expansion. The
inference chain is now flat-to-falling, not rising, so the mechanism the old
warning described does not operate.

* **`--tier owner`** uses OMIE's published `agent_owner`. Coverage is 92.7-95.7%
  over 2018-2024, a 3-point range, and **this is the tier for across-year work**.
  It falls to 90.1%/85.0% in 2025-26 purely because the unit listings stop at
  the 2025-01-31 snapshot, so end trends there until a newer listing is loaded.
* **`all` and `confirmed`** still carry a 10-point coverage range. Use them for
  within-year contrasts, which hold coverage fixed, and for the tier robustness
  check described above.

Note the residual bias now runs *against* the headline rather than with it:
coverage falls over 2024-26 while the measured Lerner rises, so that rise cannot
be produced by coverage.

GROUPING IS THE REMAINING WEAK POINT ON `--tier owner`

`agent_owner` names legal entities, not corporate groups, and unlike `firm` it
does no roll-up. On 2023 cleared sell volume `SU ELETRICIDADE` is 7.96% and is
EDP's Portuguese regulated supplier. `OWNER_ALIASES` below fixes four such
cases and is **not exhaustive**, so owner-tier share *levels* are diagnostic
until a proper group mapping is built. The coverage claim above does not depend
on the grouping.

VALIDATION

Annual means of the hourly shares are printed against CNMC's published figures.
That comparison is the check on whether the mapping is good enough to use --
not a target to fit. The prefix assignments were fixed before this ran.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BIDS = DATA / "omie" / "bids" / "parquet"
ETA = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"
FIRMS = ["IBERDROLA", "ENDESA", "EDP", "NATURGY", "AXPO", "ACCIONA", "REPSOL"]


# Legal-entity suffixes and divisional words to strip when rolling OMIE's
# published owner up to something firm-like. "REPSOL SERVICIOS RENOVABLES,
# S.A.", "REPSOL GENERACION ELECTRICA, S.L.U." and "REPSOL GENERACION
# ELECTRICA, S.A" are three registrations of one firm; without this they are
# three competitors. Deliberately crude -- it collapses 84 owners of plant
# >=50 MW to 67 groups -- and it is presentation-level, not evidence.
_OWNER_NOISE = re.compile(
    r"\b(S\.?A\.?U?|S\.?L\.?U?|SLU|SAU|SA|SL|ESPANA|ESPAÑA|IBERIA|"
    r"GENERACION|GENERACIÓN|RENOVABLES|SERVICIOS|ELECTRICA|ELÉCTRICA|"
    r"ENERGIA|ENERGÍA|POWER|GROUP|COMERCIALIZADORA|PRODUCCION|PRODUCCIÓN)\b",
    re.I)


# Entities whose first token does not name their group. Each is corroborated
# TWICE and independently -- by the unit codes themselves and by the ESIOS-based
# inference chain in unit_agents.parquet -- not by outside knowledge:
#
#   SU ELETRICIDADE  4 units, all PT, coded EDPSVD1-3; chain says EDP  4/4
#   GAS NATURAL     49 units, coded ACE4/BES4/ALZ1;    chain says NATURGY 44/49
#   ENERGIA XXI     14 units, coded E21VD*;            chain says ENDESA/EEXXI
#   CURENERGIA      11 units, coded IBCUC01/ICUVD*;    chain says IBERDROLA 11/11
#
# They matter: on 2023 cleared sell volume SU is 7.96%, GAS 2.83%. Left
# unaliased they appear as separate firms and understate EDP and Naturgy.
# This list is NOT exhaustive -- see the docstring on grouping.
OWNER_ALIASES = {
    "SU": "EDP",
    "GAS": "NATURGY",
    "XXI": "ENDESA",
    "CURENERG": "IBERDROLA",
}


def owner_group(name: str | None) -> str | None:
    """First surviving token of OMIE's published owner name.

    Not a corporate-structure mapping: it will merge unrelated firms sharing a
    first word and will split a group whose entities are named differently.
    Use it for coverage and trend diagnostics, not for a published share table.
    """
    if not isinstance(name, str) or not name.strip():
        return None
    t = _OWNER_NOISE.sub(" ", name.upper())
    t = re.sub(r"[^A-Z ]", " ", t)
    t = " ".join(t.split())
    if not t:
        return None
    g = t.split(" ")[0][:12]
    return OWNER_ALIASES.get(g, g)


def firm_period_volume(unit_firm: dict[str, str]) -> pd.DataFrame:
    """Cleared sell volume by (date, period, firm), whole archive."""
    frames = []
    files = sorted(BIDS.glob("bids_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "power_mw"]).to_pandas()
        t["firm"] = t.unit.map(unit_firm)
        tot = t.groupby(["date", "period"]).power_mw.sum().rename("total_mw")
        g = (t[t.firm.notna()].groupby(["date", "period", "firm"]).power_mw.sum()
             .rename("firm_mw").reset_index().merge(tot, on=["date", "period"]))
        frames.append(g)
        print(f"  [{i:3d}/{len(files)}] {f.stem}", end="\r", flush=True)
    print(" " * 40, end="\r")
    out = pd.concat(frames, ignore_index=True)
    out["share"] = out.firm_mw / out.total_mw
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["all", "confirmed", "owner"], default="all")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    reg = (DATA / "omie" / "registry" /
           ("unit_agents_confirmed.parquet" if args.tier == "confirmed"
            else "unit_agents.parquet"))
    if not reg.exists():
        print(f"missing {reg.name} -- run build_unit_agents.py --tier {args.tier}",
              file=sys.stderr)
        return 1
    ua = pq.read_table(reg).to_pandas()
    if args.tier == "owner":
        # OMIE's published owner instead of the inference chain -- see the
        # docstring's coverage section for why this is the tier to use for
        # anything across years.
        ua["firm"] = ua.agent_owner.map(owner_group)
    unit_firm = dict(zip(ua.loc[ua.firm.notna(), "unit"], ua.loc[ua.firm.notna(), "firm"]))
    print(f"tier={args.tier}: {len(unit_firm):,} units carry a firm\n")

    fv = firm_period_volume(unit_firm)
    eta = pq.read_table(ETA, columns=["date", "period", "eta_h5", "p_star",
                                      "vre_share", "year"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)
    fv["date"] = pd.to_datetime(fv.date)
    m = fv.merge(eta, on=["date", "period"], how="inner")
    m["lerner"] = m.share / m.eta_h5

    print(f"{len(m):,} firm-period observations over "
          f"{m[['date','period']].drop_duplicates().shape[0]:,} periods\n")

    print("=" * 72)
    print("VALIDATION: annual mean of hourly shares vs CNMC published (%)")
    print("=" * 72)
    cnmc = pq.read_table(DATA / "cnmc" / "cnmc_generation_shares.parquet").to_pandas().set_index("year")
    ann = m.pivot_table(index="year", columns="firm", values="share", aggfunc="mean") * 100
    yrs = [y for y in ann.index if y in cnmc.index]
    comp = pd.concat({"ours": ann.loc[yrs, [f for f in FIRMS if f in ann.columns]],
                      "CNMC": cnmc.loc[yrs, [f for f in FIRMS if f in cnmc.columns]]}, axis=1)
    print(comp.round(1).to_string())

    print("\n" + "=" * 72)
    print("IMPLIED LERNER from hourly shares, median by year (%)")
    print("=" * 72)
    lt = m.pivot_table(index="year", columns="firm", values="lerner", aggfunc="median") * 100
    print(lt[[f for f in FIRMS if f in lt.columns]].round(1).to_string())

    print("\n" + "=" * 72)
    print("BY VRE TERCILE, median Lerner (%) -- the within-year gradient")
    print("=" * 72)
    m["vre_t"] = m.groupby("year").vre_share.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    for f in ["IBERDROLA", "ENDESA", "EDP"]:
        if f not in set(m.firm):
            continue
        p = m[m.firm == f].pivot_table(index="year", columns="vre_t",
                                       values="lerner", aggfunc="median", observed=True) * 100
        p["high/low"] = p["high"] / p["low"]
        print(f"\n  {f}")
        print(p.round(2).to_string())

    print("\n  Mapped share of cleared sell volume by year (coverage drift --")
    print("  rising coverage inflates later-year shares; see the docstring):")
    cov = (m.groupby(["year", "date", "period"])
             .agg(mapped=("firm_mw", "sum"), tot=("total_mw", "first")).reset_index()
             .groupby("year").apply(lambda g: g.mapped.sum() / g.tot.sum(),
                                    include_groups=False))
    print("   " + "  ".join(f"{y}:{v:.0%}" for y, v in cov.items()))

    print("\n  Hourly share dispersion (a firm's share is NOT constant within a year):")
    d = m.groupby(["year", "firm"]).share.agg(["mean", "std"]).reset_index()
    d["cv"] = d["std"] / d["mean"]
    print(d[d.firm.isin(FIRMS)].pivot_table(index="year", columns="firm",
                                            values="cv").round(2).to_string())

    if args.save:
        out = ROOT / "outputs" / "tables" / f"firm_shares_hourly_{args.tier}.parquet"
        m.to_parquet(out, index=False)
        print(f"\nwrote {out.relative_to(ROOT)}  ({len(m):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
