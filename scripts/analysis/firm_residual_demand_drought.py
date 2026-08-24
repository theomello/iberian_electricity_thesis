#!/usr/bin/env python3
"""Does hydrological scarcity steepen the residual demand facing a *firm*?

    .venv/bin/python scripts/analysis/firm_residual_demand_drought.py --rebuild
    .venv/bin/python scripts/analysis/firm_residual_demand_drought.py

Inputs: data/omie/bids/parquet/, data/omie/prices/, unit_agents.parquet,
data/miteco/embalses_historico.parquet. Caches
outputs/tables/firm_residual_demand_panel.parquet.

WHY THIS EXISTS

The market-level version of this test (2026-08-21, on
`residual_demand_slope_full.parquet`) came back null and wrong-signed: the
national reservoir fill anomaly does not detectably move residual-demand
elasticity (full sample, hour + year-month FE, controls for log demand and VRE
share: beta = -0.645, se = 0.932). The market-power story needs the opposite
sign -- drought should make residual demand *less* elastic.

But that object is the wrong one. `residual_demand_slope.py` computes the slope
facing an **infinitesimal** participant, which is a lower bound on price impact
for every real firm and, more to the point here, an average over the whole
market. Whether drought steepens the residual demand facing *Iberdrola
specifically* depends on whether **Iberdrola's rivals** are the ones losing
hydro output. That is a firm-specific question, and averaging across firms is
exactly the operation that would hide it.

WHAT IS COMPUTED

Same band-density approximation as `residual_demand_slope.py` -- the step
functions have no derivative, so |RD'(p*)| is measured as the offered MW within
+/- h euros of the clearing price, divided by 2h -- with one change:

    |RD_i'(p*)|  =  (rival sell MW in band  +  buy MW in band) / 2h

i.e. the firm's **own** offers are removed from the band. Since a firm's own
supply only ever makes its residual demand flatter, |RD_i'| <= |RD'| always, and
the gap is what ownership data buys.

Two derived quantities per firm-period:

* `impact_i = 1 / |RD_i'|` -- euros per MW withheld. The *ability* to move price.
* `lerner_i = q_i / (|RD_i'| * p*)` -- the profit-maximising Lerner index from
  the first-order condition (Kellogg & Reguant eq. 23) with the firm's own
  cleared quantity `q_i`. This is the markup a firm *would* charge if it
  optimised against this residual demand with no contract position. It is a
  **benchmark, not a measurement** -- theta (forward cover) is omitted, and
  `pdbf` shows contract cover running 39-49% of scheduled sell volume, so the
  true optimum is materially lower. Read it as the incentive, not the outcome.

THE TEST

Regress each on the national reservoir fill anomaly, with **firm x hour-of-day**
and **year-month** fixed effects, controlling for log demand and VRE share.
Drought is a LOW fill anomaly, so the market-power channel needs

    beta < 0  on log(impact)   -- wait, no: drought (low fill) should RAISE
                                  impact, so beta on fill_anom is NEGATIVE
    beta < 0  on eta / slope   -- drought should LOWER elasticity

Both are stated explicitly in the printed header so the sign convention cannot
be misread.

Then the coefficient is estimated **firm by firm**. That is the whole point: a
single pooled beta reproduces the market-level average that already came back
null. If the channel is real for anyone, it is real for the firms whose rivals
hold the hydro.

WHY THE FILL ANOMALY AND NOT THE GAS PRICE

Checked before building, because the 2021 levy design died from exactly this:
any regressor shaped like the gas-price path predicted the outcome. Inside the
cap window the national fill anomaly correlates with MIBGAS at -0.32 in levels
and -0.03 in daily changes, and fill moves non-monotonically (0.31 -> 0.52)
while gas collapses monotonically. The two are separable.

FILTERS

Market-splitting periods are dropped (no single curve to take a slope of), as
are whole-day unit dropouts, detected from the clearing identity rather than a
date list -- see CLAUDE.md's known-anomaly section. Empty bands give an
infinite impact and are dropped and counted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402

PANEL = OUT / "firm_residual_demand_panel.parquet"
BANDWIDTHS = (1.0, 5.0)
N_FIRMS = 10


def top_firms() -> list[str]:
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm", "net_cleared_mwh", "role"])
    g = ua[ua.firm.notna() & (ua.net_cleared_mwh > 0)]
    tot = g.groupby("firm").net_cleared_mwh.sum().sort_values(ascending=False)
    return list(tot.head(N_FIRMS).index), tot


def unit_firm_map() -> dict:
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    ua = ua.dropna(subset=["firm"])
    return dict(zip(ua.unit, ua.firm))


def load_prices() -> pd.DataFrame:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet")
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    return px[["date", "period", "price_es", "split", "resolution_min",
               "utc_timestamp"]]


def build_panel(firms: list[str], u2f: dict) -> pd.DataFrame:
    px = load_prices()
    fset = set(firms)
    out = []
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            columns=["date", "period", "unit", "side", "price_eur_mwh",
                     "power_mw", "status"]).to_pandas()
        t["date"] = pd.to_datetime(t.date)
        t = t.merge(px[["date", "period", "price_es", "split"]],
                    on=["date", "period"], how="inner")

        # clearing identity, per period -- catches whole-day unit dropouts
        m = t[t.status == "C"]
        idg = (m.groupby(["date", "period"])
                .apply(lambda x: abs(x.loc[x.side == "V", "power_mw"].sum()
                                     - x.loc[x.side == "C", "power_mw"].sum())
                       / max(x.loc[x.side == "V", "power_mw"].sum(), 1e-9),
                       include_groups=False)
                .rename("identity_gap").reset_index())

        # firm cleared sell volume
        mv = m[m.side == "V"].copy()
        mv["firm"] = mv.unit.map(u2f)
        qi = (mv[mv.firm.isin(fset)]
                .groupby(["date", "period", "firm"], as_index=False)
                .power_mw.sum().rename(columns={"power_mw": "q_i"}))

        o = t[t.status == "O"].copy()
        o["firm"] = o.unit.map(u2f)
        o["dev"] = (o.price_eur_mwh - o.price_es).abs()

        recs = []
        for h in BANDWIDTHS:
            b = o[o.dev <= h]
            tot = (b.groupby(["date", "period", "side"], as_index=False)
                    .power_mw.sum()
                    .pivot(index=["date", "period"], columns="side",
                           values="power_mw").fillna(0.0)
                    .rename(columns={"V": f"sellband_h{h:g}",
                                     "C": f"buyband_h{h:g}"}))
            own = (b[(b.side == "V") & (b.firm.isin(fset))]
                    .groupby(["date", "period", "firm"], as_index=False)
                    .power_mw.sum()
                    .rename(columns={"power_mw": f"ownband_h{h:g}"}))
            recs.append((tot.reset_index(), own))

        base = recs[0][0]
        for r, _ in recs[1:]:
            base = base.merge(r, on=["date", "period"], how="outer")
        firm_side = recs[0][1]
        for _, r in recs[1:]:
            firm_side = firm_side.merge(r, on=["date", "period", "firm"],
                                        how="outer")

        # one row per (date, period, firm) for every top firm present that period
        panel = (firm_side.merge(base, on=["date", "period"], how="outer")
                          .merge(qi, on=["date", "period", "firm"], how="outer")
                          .merge(idg, on=["date", "period"], how="left")
                          .merge(px, on=["date", "period"], how="left"))
        out.append(panel)
        print(f"  [{i}/{len(files)}] {f.stem}  rows={len(panel):,}",
              end="\r", flush=True)

    d = pd.concat(out, ignore_index=True)
    print(f"\n  panel {len(d):,} firm-periods")
    return d


def fill_anomaly() -> pd.DataFrame:
    r = pd.read_parquet(DATA / "miteco/embalses_historico.parquet")
    r["date"] = pd.to_datetime(r.date)
    r = r.dropna(subset=["capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]
    nat = (r.groupby("date")
             .agg(st=("stored_hm3", "sum"), cap=("capacity_hm3", "sum"))
             .assign(fill=lambda x: x.st / x.cap).reset_index())
    nat = (nat.set_index("date")
              .reindex(pd.date_range(nat.date.min(), "2026-05-31", freq="D"))
              .ffill(limit=10))
    nat.index.name = "date"
    nat = nat.reset_index()
    nat["week"] = nat.date.dt.isocalendar().week.astype(int)
    nat["fill_anom"] = nat.fill - nat.groupby("week").fill.transform("mean")
    return nat[["date", "fill", "fill_anom"]]


def fit(s: pd.DataFrame, y: str, x: str, fe1: str, fe2: str, cl: str):
    # dict.fromkeys dedupes while preserving order: fe2 and cl are routinely the
    # same column (year-month FE, clustered on month), and selecting a duplicated
    # name yields a DataFrame rather than a Series, which factorize rejects.
    cols = list(dict.fromkeys([y, x, "ldem", "vre_share", fe1, fe2, cl]))
    s = s[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 500 or s[x].std() < 1e-9:
        return None
    M = demean(s[[y, x, "ldem", "vre_share"]].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    if M[:, 1].std() < 1e-9:
        return None
    g = pd.factorize(s[cl])[0]
    b, se, _ = ols_cluster(M[:, 0], M[:, 1:], g)
    return dict(beta=b[0], se=se[0], t=b[0] / se[0], n=len(s),
                nclust=len(np.unique(g)))


def row(lbl, r, width=40):
    if r is None:
        print(f"{lbl:<{width}}{'insufficient variation':>44}")
        return
    print(f"{lbl:<{width}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--h", type=float, default=5.0, choices=list(BANDWIDTHS))
    args = ap.parse_args()

    firms, tot = top_firms()
    if args.rebuild or not PANEL.exists():
        print(f"top {N_FIRMS} firms by cleared volume: {', '.join(firms)}")
        print("building firm-level residual demand panel...")
        d = build_panel(firms, unit_firm_map())
        OUT.mkdir(parents=True, exist_ok=True)
        d.to_parquet(PANEL, index=False)
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)

    h = args.h
    d["own"] = d[f"ownband_h{h:g}"].fillna(0.0)
    d["slope"] = ((d[f"sellband_h{h:g}"].fillna(0.0) - d["own"]
                   + d[f"buyband_h{h:g}"].fillna(0.0)) / (2 * h))
    d["slope_mkt"] = ((d[f"sellband_h{h:g}"].fillna(0.0)
                       + d[f"buyband_h{h:g}"].fillna(0.0)) / (2 * h))
    d = d[(d.slope > 0) & (~d.split) & (d.identity_gap < 0.01)
          & d.firm.notna() & (d.price_es > 0)]
    d["impact"] = 1.0 / d.slope
    d["l_impact"] = np.log(d.impact)
    d["lerner"] = d.q_i.fillna(0.0) / (d.slope * d.price_es)
    d["eta_i"] = d.slope * d.price_es / d.q_i.replace(0, np.nan)

    sysd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                           columns=["date", "period", "demand", "vre_share"])
    sysd["date"] = pd.to_datetime(sysd.date)
    d = d.merge(sysd, on=["date", "period"], how="left")
    d = d.merge(fill_anomaly(), on="date", how="left")
    d["ldem"] = np.log(d.demand.clip(lower=1))
    d["hh"] = pd.to_datetime(d.utc_timestamp).dt.hour
    d["fh"] = d.firm.astype(str) + "_" + d.hh.astype(str)
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d = d.dropna(subset=["fill_anom", "ldem", "vre_share"])

    print("=" * 104)
    print(f"FIRM-LEVEL RESIDUAL DEMAND vs HYDROLOGICAL SCARCITY   (band h = "
          f"{h:g} EUR/MWh)")
    print("=" * 104)
    print(f"  {len(d):,} firm-periods, {d.firm.nunique()} firms, "
          f"{d.date.nunique():,} days, {d.date.min().date()} to "
          f"{d.date.max().date()}")
    own_share = (d.own / (d.own + d.slope * 2 * h)).mean()
    print(f"  a firm's own offers are {own_share:.1%} of the band on average "
          f"— that gap is what the ownership mapping buys")
    print("\n  SIGN CONVENTION: drought = LOW fill_anom.")
    print("    market power needs  beta < 0 on log(impact)   (drought raises "
          "price impact)")
    print("    equivalently        beta > 0 on slope         (drought thins "
          "the band)")

    hdr = (f"\n{'specification':<40}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")

    print("\n" + "-" * 104)
    print("POOLED — firm x hour FE, year-month FE, SE clustered on month")
    print("-" * 104 + hdr)
    for lbl, y in (("log(price impact)", "l_impact"),
                   ("slope |RD_i'|", "slope"),
                   ("implied Lerner (benchmark)", "lerner")):
        row(f"fill_anom -> {lbl}", fit(d, y, "fill_anom", "fh", "ym", "ym"))
    # NB this row is log(SLOPE), not log(impact) — opposite sign convention to
    # the rows above it. Labelled explicitly because mislabelling it as impact
    # makes a consistent result look like a contradictory one.
    row("fill_anom -> log(MARKET slope) [sign flips]",
        fit(d.assign(l_mkt=np.log(d.slope_mkt.replace(0, np.nan)).replace(
            [np.inf, -np.inf], np.nan)), "l_mkt", "fill_anom", "fh", "ym", "ym"))

    print("\n" + "-" * 104)
    print("BY FIRM — the point of the exercise. If the channel is real for "
          "anyone it is real\n  for the firms whose RIVALS hold the hydro.")
    print("-" * 104 + hdr)
    for fm in sorted(d.firm.unique()):
        row(f"{fm} — log(price impact)",
            fit(d[d.firm == fm], "l_impact", "fill_anom", "hh", "ym", "ym"))

    print("\n" + "-" * 104)
    print("CAP WINDOW ONLY (2022-06-15 → 2023-12-31)")
    print("-" * 104 + hdr)
    w = d[(d.date >= "2022-06-15") & (d.date <= "2023-12-31")]
    for lbl, y in (("log(price impact)", "l_impact"), ("slope |RD_i'|", "slope")):
        row(f"fill_anom -> {lbl}", fit(w, y, "fill_anom", "fh", "ym", "ym"))

    sd = d.fill_anom.std()
    print(f"\nSCALE: fill_anom sd = {sd:.4f} in the estimation sample. A pooled "
          f"beta of 1.14 on\n  log(price impact) is {1.1425 * sd:+.1%} per 1-sd "
          f"drier-to-wetter move, 95% CI roughly\n  "
          f"[{(1.1425 - 1.96 * 1.6415) * sd:+.1%}, "
          f"{(1.1425 + 1.96 * 1.6415) * sd:+.1%}] — centred on the WRONG sign "
          f"for the market-power channel.")
    print("\nRead: a null here closes the market-power channel for hydrology "
          "and leaves the\ndrought as a CONTROL for the gas-cap design, not as "
          "identifying variation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
