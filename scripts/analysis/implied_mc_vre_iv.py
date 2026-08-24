#!/usr/bin/env python3
"""Do firms mark up more than their own residual demand justifies when
renewables are abundant?

    .venv/bin/python scripts/analysis/implied_mc_vre_iv.py --save
    .venv/bin/python scripts/analysis/implied_mc_vre_iv.py --bands 2,5,10,20

THE IDEA

A firm's own offer reveals its cost. Under the supply-function first-order
condition with forward contracts (Hortacsu & Puller 2008),

    MC_it  =  p_t  -  (q_it - theta_it) / |RD'_it|

and every term on the right is published in MIBEL: `theta` is PDBF role 4,
`q` is the firm's total PDBF schedule, `|RD'|` is built from rivals' actual
submitted offers. `hortacsu_puller_test.py` validates the construction -- implied
MC orders wind < cogeneration < hydro < gas CCGT with nothing imposing it.

THE TEST

A plant's true marginal cost depends on fuel and technology. It does **not**
depend on the wind. The FOC already nets out the mechanical fact that a steeper
residual demand justifies a bigger markup -- that is environment, not conduct.

So under the SFE benchmark, implied MC should be orthogonal to renewable output.
A positive gradient means firms mark up beyond what their own residual demand
justifies, which is a conduct result. The null is zero, and it comes from theory
rather than from a guess.

    MC_it = b * vre_share_t + controls + firm + hour + month + year FE

instrumented with wind speed, wind speed cubed and irradiance, as in
`eta_vre_iv.py`.

WHY THIS OUTCOME AND NOT BID STEEPNESS

`bid_steepness_iv.py` asked a version of this question and was withdrawn on
2026-08-17: trimming 10% from each end of a unit's own offer curve flipped the
estimate from +0.428 to -0.202. That measure is a **shape statistic over the
whole submitted curve**, so it is dominated by the tails, where withholding bids
and cost-revealing bids are indistinguishable.

Implied MC is a different object -- it is evaluated at the realised clearing
point, and the only estimated ingredient is `|RD'|`, taken from the aggregate
curve where thousands of offers smooth it. Checked directly: varying the slope
band over 2/5/10/20 EUR/MWh moves implied MC by at most 3.5 EUR/MWh and leaves
the technology ordering identical. `--bands` re-runs that check on the estimate
itself, which is the part that actually matters and was never tested.

THE KNOWN WEAKNESSES

* `theta` is PHYSICAL contracts only; financial hedges are invisible, so it is a
  lower bound and implied MC is biased down. Direction is known, not the size.
* No date-x-period fixed effects are possible: `vre_share` is a single number
  per period, so it is collinear with them. Identification rests on the
  exclusion restriction, exactly as in `eta_vre_iv.py`.
* Entity definition matters -- `RD'` nets out the firm's OWN offers, so treating
  Iberdrola's three agents as three firms understates each one's market power.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
ETA = OUT / "residual_demand_slope_full.parquet"
WX = DATA / "weather" / "weather_spain_aggregate.parquet"

TOP_FIRMS = 6


def owner_map() -> dict[str, str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    o = ul.dropna(subset=["agent_owner"]).drop_duplicates("unit", keep="last")
    return dict(zip(o.unit, o.agent_owner))


def tech_map() -> dict[str, str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    t = ul.dropna(subset=["technology"]).drop_duplicates("unit", keep="last")
    return dict(zip(t.unit, t.technology))


def tech_band(t) -> str | None:
    """Collapse OMIE's technology labels onto the bands used elsewhere here."""
    import re
    t = str(t)
    if "Nuclear" in t:                                    return "nuclear"
    if re.search(r"Hidr[aá]ulica|Bombeo", t):             return "hydro"
    if re.search(r"E[oó]lica", t):                        return "wind"
    if "Solar" in t:                                      return "solar"
    if "Ciclo Combinado" in t:                            return "gas CCGT"
    if re.search(r"Hulla|Antracita|Carb[oó]n|Lignito", t): return "coal"
    if re.search(r"T[eé]rmica no", t):                    return "cogeneration"
    return None


def firm_position(ym: str, owner: dict) -> pd.DataFrame:
    """Scheduled output `q` and contracted position `theta` per firm-period, in MW.

    `q` is TOTAL production from PDBF, not day-ahead cleared volume: bilaterally
    contracted energy never enters the auction, so cleared volume is already
    roughly `q - theta` and using it as `q` double-counts contracts.

    UNITS. `q` and `theta` are **average MW**, deliberately NOT energy. The
    first-order condition needs `q` and `RD'` in the same quantity units, and the
    slope is built by summing `power_mw` from the bid curves, which is MW and does
    not change with market resolution. Converting to MWh per period here would
    quarter `q` from the 15-minute switch (day-ahead 2025-10-01, PDBF 2025-03-19)
    while leaving the slope untouched, mechanically dividing every markup by four.
    That is not hypothetical: it made the 2025-26 markup collapse to a third of its
    2024 level and read as a real decline. PDBF `schedule_mw` is already average
    MW, so summing it directly is the consistent choice.
    """
    f = DATA / "omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
    if not f.exists():
        return pd.DataFrame()
    t = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw",
                                  "role_code"]).to_pandas()
    t = t[t.schedule_mw > 0].copy()
    t["firm"] = t.unit.map(owner)
    t["date"] = pd.to_datetime(t.date)
    t["theta_mw"] = np.where(t.role_code.astype(str) == "4", t.schedule_mw, 0.0)
    return (t.groupby(["date", "period", "firm"], as_index=False)
             .agg(q=("schedule_mw", "sum"), theta=("theta_mw", "sum")))


def month_panel(ym: str, owner: dict, tech: dict, px: pd.DataFrame, band: float,
                top: list[str]) -> pd.DataFrame:
    """Implied MC per firm-period for one month.

    Vectorised: the per-firm residual-demand slope is
    (total near-price sell - the firm's own near-price sell + near-price buy),
    so it comes from two groupbys rather than a Python loop over firm x period.
    Unmapped units carry firm NaN and count toward rivals' supply, matching
    `hortacsu_puller_test.py`, where `sell.firm != fm` is True for NaN.
    """
    f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
    if not f.exists():
        return pd.DataFrame()
    raw = pq.read_table(f, columns=["date", "period", "unit", "side", "status",
                                    "price_eur_mwh", "power_mw"]).to_pandas()
    raw["date"] = pd.to_datetime(raw.date)
    raw = raw.merge(px, on=["date", "period"], how="inner")
    raw = raw[raw.price_es > 1]                # eta degenerates at zero prices
    raw["firm"] = raw.unit.map(owner)
    key = ["date", "period"]

    # The technology at the firm's own margin: its highest-priced accepted sell
    # offer that period. Needed because when renewables are abundant a firm
    # simply stops running its expensive plant, so implied MC falls for a
    # compositional reason that has nothing to do with conduct.
    marg = (raw[(raw.status == "C") & (raw.side == "V") & (raw.price_eur_mwh > 0)
                & raw.firm.isin(top)]
            .sort_values("price_eur_mwh")
            .groupby(key + ["firm"]).tail(1)[key + ["firm", "unit"]])
    marg["margtech"] = marg.unit.map(tech).map(tech_band)
    marg = marg.drop(columns=["unit"])

    b = raw[(raw.status == "O")
            & ((raw.price_eur_mwh - raw.price_es).abs() <= band)]
    if b.empty:
        return pd.DataFrame()
    sell, buy = b[b.side == "V"], b[b.side == "C"]
    tot = (sell.groupby(key).power_mw.sum().rename("sell_all")
              .to_frame()
              .join(buy.groupby(key).power_mw.sum().rename("buy_all"), how="outer")
              .fillna(0.0).reset_index())

    own = (sell[sell.firm.isin(top)].groupby(key + ["firm"])
               .power_mw.sum().rename("own").reset_index())
    grid = tot.merge(pd.DataFrame({"firm": top}), how="cross")
    grid = grid.merge(own, on=key + ["firm"], how="left").fillna({"own": 0.0})
    grid["slope"] = (grid.sell_all - grid.own + grid.buy_all) / (2 * band)
    grid = grid[grid.slope > 0]

    pos = firm_position(ym, owner)
    if pos.empty:
        return pd.DataFrame()
    m = grid.merge(px, on=key, how="left").merge(pos, on=key + ["firm"], how="inner")
    m = m.merge(marg, on=key + ["firm"], how="left")
    m["mc"] = m.price_es - (m.q - m.theta) / m.slope
    return m[key + ["firm", "price_es", "slope", "q", "theta", "mc", "margtech"]]


def build(months: list[str], band: float) -> pd.DataFrame:
    owner, tech = owner_map(), tech_map()
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)

    top: list[str] = []
    for ym in months[:12]:                     # rank firms on the first year
        p = firm_position(ym, owner)
        if not p.empty:
            top.append(p.groupby("firm").q.sum())
    top = list(pd.concat(top).groupby(level=0).sum().nlargest(TOP_FIRMS).index)
    print(f"  top {TOP_FIRMS} firms: {', '.join(str(t)[:24] for t in top)}")

    out = []
    for i, ym in enumerate(months, 1):
        m = month_panel(ym, owner, tech, px, band, top)
        if not m.empty:
            out.append(m)
        if i % 12 == 0 or i == len(months):
            print(f"    {i}/{len(months)} months, {sum(len(x) for x in out):,} rows",
                  flush=True)
    return pd.concat(out, ignore_index=True)


def attach(m: pd.DataFrame) -> pd.DataFrame:
    e = pd.read_parquet(ETA, columns=["date", "period", "vre_share", "demand",
                                      "utc_timestamp", "resolution_min", "split"])
    e["date"] = pd.to_datetime(e.date)
    w = pd.read_parquet(WX)
    e["utc_timestamp"] = pd.to_datetime(e.utc_timestamp, utc=True)
    w["utc_timestamp"] = pd.to_datetime(w.utc_timestamp, utc=True)
    w = w.set_index("utc_timestamp").sort_index()
    e = e.sort_values("utc_timestamp")
    e = pd.merge_asof(e, w, on="utc_timestamp", direction="nearest",
                      tolerance=pd.Timedelta("1h"))

    d = m.merge(e, on=["date", "period"], how="inner")
    d = d[~d.split.astype(bool)]                      # ES/PT splitting hours out
    d["wind"] = d.wind_speed_100m_wind_sites
    d["wind3"] = d.wind ** 3 / 1000.0
    d["rad"] = d.radiation_solar_sites / 100.0
    d["temp"] = d.temperature_2m_mean
    d["temp2"] = d.temp ** 2
    d["hour"] = ((d.period - 1) * d.resolution_min // 60).astype(int)
    d["month"] = d.date.dt.month
    d["year"] = d.date.dt.year
    d["ldem"] = np.log(d.demand)
    return d.dropna(subset=["mc", "vre_share", "wind", "rad", "temp", "demand"])


def demean(v: np.ndarray, *codes) -> np.ndarray:
    """Sweep out several one-way fixed effects by alternating projection."""
    v = v.astype(float).copy()
    for _ in range(60):
        before = v.copy()
        for c in codes:
            k = c.max() + 1
            cnt = np.bincount(c, minlength=k).astype(float)
            s = np.bincount(c, weights=v, minlength=k)
            v -= (s / np.where(cnt == 0, 1, cnt))[c]
        if np.max(np.abs(v - before)) < 1e-9:
            break
    return v


def estimate(d: pd.DataFrame, label: str) -> dict:
    fi = pd.factorize(d.firm)[0]
    hi = pd.factorize(d.hour)[0]
    mi = pd.factorize(d.month)[0]
    yi = pd.factorize(d.year)[0]
    dm = lambda s: demean(d[s].to_numpy(), fi, hi, mi, yi)

    y = dm("mc")
    ctrl = np.column_stack([dm(c) for c in ("ldem", "temp", "temp2")])
    x = dm("vre_share")
    Z = np.column_stack([dm(c) for c in ("wind", "wind3", "rad")])

    Xo = np.column_stack([x, ctrl])
    ols = sm.OLS(y, Xo).fit(cov_type="cluster",
                            cov_kwds={"groups": pd.factorize(d.date)[0]})

    first = sm.OLS(x, np.column_stack([Z, ctrl])).fit()
    xhat = first.fittedvalues
    iv = sm.OLS(y, np.column_stack([xhat, ctrl])).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.date)[0]})

    r = sm.OLS(x, ctrl).fit()
    fstat = ((r.ssr - first.ssr) / 3) / (first.ssr / (len(d) - Z.shape[1] - 4))
    return {"label": label, "n": len(d), "ols": ols.params[0], "ols_se": ols.bse[0],
            "iv": iv.params[0], "iv_se": iv.bse[0], "F": fstat,
            "mc_mean": d.mc.mean(), "sd_vre": d.vre_share.std()}


def report(rows: list[dict]) -> None:
    print(f"\n{'-'*78}\n  IMPLIED MARGINAL COST ON RENEWABLE SHARE"
          f"\n  null: zero. a plant's cost does not depend on the wind.\n{'-'*78}")
    print(f"{'spec':<14}{'n':>9}{'OLS':>11}{'(se)':>9}{'2SLS':>11}{'(se)':>9}"
          f"{'first-stage F':>15}")
    for r in rows:
        print(f"{r['label']:<14}{r['n']:>9,}{r['ols']:>11.4f}{r['ols_se']:>9.4f}"
              f"{r['iv']:>11.4f}{r['iv_se']:>9.4f}{r['F']:>15,.0f}")
    b = rows[0]
    eff = b["iv"] * b["sd_vre"]
    print(f"\n  a 1 s.d. rise in the renewable share ({b['sd_vre']:.1f} pp) moves "
          f"implied MC by {eff:+.2f} EUR/MWh")
    print(f"  against a mean implied MC of {b['mc_mean']:.1f} EUR/MWh "
          f"({eff / b['mc_mean']:+.1%})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bands", default="5", help="slope windows, EUR/MWh")
    ap.add_argument("--start", default="201801")
    ap.add_argument("--end", default="202605")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    months = [f"{d:%Y%m}" for d in
              pd.period_range(a.start, a.end, freq="M").to_timestamp()]
    rows, keep = [], None
    for band in [float(x) for x in a.bands.split(",")]:
        print(f"\nBAND {band} EUR/MWh")
        d = attach(build(months, band))
        rows.append(estimate(d, f"band {band:g}"))
        if keep is None:
            keep = d
    report(rows)

    if a.save and keep is not None:
        p = OUT / "implied_mc_vre_panel.parquet"
        keep.to_parquet(p, index=False)
        print(f"\n  wrote {p} ({len(keep):,} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
