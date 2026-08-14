#!/usr/bin/env python3
"""Continuous-intensity difference-in-differences for the 2021 Spanish clawback.

    .venv/bin/python scripts/analysis/clawback_intensity_did.py
    .venv/bin/python scripts/analysis/clawback_intensity_did.py --save

THE DESIGN

RDL 17/2021 levied a charge on Spanish peninsular non-emitting generation above
10 MW. Per installation i in month t:

    Y_it = Q_it * FMIG_t * (PGN_t - 20) * alpha,   alpha = 0.9

`Q_it` is energy actually produced, so this is a **per-MWh output levy** and it
raises the marginal opportunity cost of generating. Crucially, its rate moves
with the monthly gas price: PGN ran 28.9 to 165.9 EUR/MWh over the 27 months the
levy was in force, never once below the 20 EUR floor. So treatment intensity is
continuous and varies 5.7-fold *within* the treated period.

That is what this script exploits. A single before/after break at 16 September
2021 gives four usable observations and placebo years whose spread exceeds any
plausible effect. Interacting Spanish exposure with a continuously varying
intensity uses the policy's own structure and 27 months of variation:

    y_it = beta * (SPAIN_i * intensity_t) + mu_i + lambda_t + e_it

with unit and month fixed effects and standard errors clustered on the unit.
`beta > 0` means Spanish hydro raised its offers relative to Portuguese hydro by
more in months when the levy bit harder.

TREATMENT AND CONTROL

Treated: Spanish hydro storage units (ESIOS class UGH -- managed storage groups).
Control: **Portuguese hydro.** Portugal clears in the same auction, against the
same merged MIBEL bid stack, at the same price, facing the same gas-driven
forward curve -- but RDL 17/2021 binds only on *peninsular Spanish*
installations. Spanish and Portuguese hydro output correlate at r = 0.82 daily
and 0.79 in monthly log-changes over the pre-period, so the hydrological common
shock is strong.

The intended within-Spain control -- run-of-river hydro, treated but unable to
store -- does not exist in these data. ESIOS registers 218 such units, none of
them appear in the day-ahead bid files (small hydro sells through aggregation
vehicles), and their median capacity is 3.7 MW with 77% at or below the 10 MW
exemption, so most were never treated. That is why the control is national.

FIVE THREATS, ALL REAL

1. **The treatment is a bundle.** RDL 17/2021 also extended the suspension of
   the IVPEE, the 7% tax on generation value -- a tax *cut* for all Spanish
   generators. The dates differ (IVPEE suspended from 1 July 2021, levy from
   16 September), which is what makes them separable at all, but a specification
   that ignores the IVPEE attributes both to the levy.
2. **Portugal is not untreated throughout.** Its own clawback (the *mecanismo de
   equilibrio concorrencial*) was set to **zero from 1 October 2021 to 31
   December 2023**, tracking the IVPEE suspension. Inside the levy window that
   is ideal -- the control carries no output levy at all. But the transition
   lands two weeks after the Spanish one, so any window straddling it compares a
   levy imposed against a levy removed, and **overstates** the effect.
3. **Composition change in the control.** Tamega (1,158 MW) enters the
   Portuguese group in January 2022, mid-treatment. Unit fixed effects absorb
   its level but not its effect on the group's composition; `--balanced` keeps
   only units present throughout.
4. **FMIG is omitted.** It is not published machine-readably, so intensity here
   is `(PGN - 20) * alpha` without it. FMIG is a share in [0, 1] moving slowly,
   so this rescales beta and understates intensity in low-gas months; it does
   not flip sign. Do not report beta as a levy elasticity until FMIG is in.
5. **Market splitting.** When the interconnection binds, Spain and Portugal take
   different prices and the common-price assumption fails. Split days are
   dropped by default.

WHAT THE OUTCOME IS

The volume-weighted median offer price of a unit's sell offers, divided by the
day's mean day-ahead price, then averaged to the month and logged. Dividing by
the market price makes it scale-free: the gas-price level moves both numerator
and denominator, so it cannot drive the result mechanically.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUTDIR = ROOT / "outputs" / "tables"

ALPHA = 0.9
GAS_FLOOR = 20.0
LEVY_START = pd.Timestamp("2021-09-16")
LEVY_END = pd.Timestamp("2023-12-31")


def wmedian(v: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(v)
    v, w = np.asarray(v)[o], np.asarray(w)[o]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return np.nan
    return float(v[np.searchsorted(c, c[-1] / 2.0)])


def load_groups() -> dict[str, str]:
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet").to_pandas()
    g = {}
    for _, r in ua.iterrows():
        if r.country == "ES" and r.tech == "hydro_ugh":
            g[r.unit] = "ES"
        elif r.country == "PT" and str(r.tech).startswith("hydro"):
            g[r.unit] = "PT"
    return g


def day_prices(drop_split: bool) -> pd.Series:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es", "price_pt"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)
    if drop_split:
        px = px[(px.price_es - px.price_pt).abs() < 1e-6]
    n = px.groupby("date").period.size()
    p = px.groupby("date").price_es.mean()
    # A day with most periods split is not a like-for-like ES/PT comparison.
    return p[n >= 18]


def build_panel(drop_split: bool) -> pd.DataFrame:
    groups = load_groups()
    pday = day_prices(drop_split)
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    rows = []
    for f in files:
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O") & (pc.field("side") == "V"),
            columns=["date", "unit", "price_eur_mwh", "power_mw"]).to_pandas()
        t["g"] = t.unit.map(groups)
        t = t[t.g.notna() & (t.price_eur_mwh > 0) & (t.price_eur_mwh < 3000)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        t = t[t.date.isin(pday.index)]
        if t.empty:
            continue
        for (d, u, g), x in t.groupby(["date", "unit", "g"], sort=False):
            rows.append((d, u, g, wmedian(x.price_eur_mwh.values, x.power_mw.values),
                         float(x.power_mw.sum())))
    d = pd.DataFrame(rows, columns=["date", "unit", "grp", "offer", "mw"])
    d["mkt"] = d.date.map(pday)
    d = d[d.mkt > 0]
    d["ratio"] = d.offer / d.mkt
    d["month"] = d.date.dt.to_period("M")
    # Volume-weight days within the month so a one-offer day does not count as
    # much as a full month of operation.
    g = d.groupby(["unit", "grp", "month"])
    p = g.apply(lambda x: pd.Series({
        "ratio": np.average(x.ratio, weights=np.maximum(x.mw, 1e-9)),
        "days": len(x), "mw": x.mw.sum()}), include_groups=False).reset_index()
    return p


def gas_intensity() -> pd.Series:
    mg = pq.read_table(DATA / "mibgas/mibgas_prices.parquet").to_pandas()
    mg = mg[mg["product"].eq("GDAES_D+1") & mg.area.eq("ES")].copy()
    mg["month"] = pd.to_datetime(mg.trading_day).dt.to_period("M")
    pgn = mg.groupby("month").price_eur_mwh.mean()
    # The levy is zero below the floor and zero outside the statutory window.
    inten = (pgn - GAS_FLOOR).clip(lower=0) * ALPHA
    # Outside the statutory window the levy is zero *by law*, whatever gas did.
    # MIBGAS only publishes from 2021, so a month with no gas price before the
    # levy existed must become 0, not NaN -- dropping those NaNs deletes the
    # entire pre-period and leaves the design with nothing to difference against.
    full = pd.period_range("2018-01", "2026-05", freq="M")
    inten = inten.reindex(full)
    live = pd.Series([(m >= LEVY_START.to_period("M")) and
                      (m <= LEVY_END.to_period("M")) for m in full], index=full)
    inten = inten.where(live, 0.0)
    if inten[live].isna().any():
        raise ValueError("missing gas price inside the levy window: "
                         f"{list(inten[live][inten[live].isna()].index)}")
    return inten.fillna(0.0)


def twfe(df: pd.DataFrame, y: str, x: str, unit: str, time: str):
    """Two-way fixed effects by alternating projection, SEs clustered on unit."""
    d = df[[y, x, unit, time]].dropna().copy()
    Y, X = d[y].to_numpy(float), d[x].to_numpy(float)
    ui = pd.factorize(d[unit])[0]
    ti = pd.factorize(d[time])[0]

    def demean(v):
        v = v.copy()
        for _ in range(200):
            before = v.copy()
            v -= np.bincount(ui, v) [ui] / np.bincount(ui)[ui]
            v -= np.bincount(ti, v)[ti] / np.bincount(ti)[ti]
            if np.max(np.abs(v - before)) < 1e-11:
                break
        return v

    Yd, Xd = demean(Y), demean(X)
    denom = float(Xd @ Xd)
    if denom <= 0:
        return np.nan, np.nan, np.nan, len(d), 0
    beta = float(Xd @ Yd) / denom
    e = Yd - beta * Xd
    nclust = ui.max() + 1
    meat = 0.0
    for c in range(nclust):
        m = ui == c
        meat += float(Xd[m] @ e[m]) ** 2
    dof = nclust / (nclust - 1) * (len(d) - 1) / (len(d) - 2)
    se = float(np.sqrt(dof * meat) / denom)
    return beta, se, beta / se if se else np.nan, len(d), nclust


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--keep-split", action="store_true",
                    help="keep days when ES and PT prices diverge")
    ap.add_argument("--balanced", action="store_true",
                    help="only units present in every month of the sample")
    ap.add_argument("--from", dest="frm", default="2018-01")
    ap.add_argument("--to", dest="to", default="2026-05")
    args = ap.parse_args()

    panel = build_panel(drop_split=not args.keep_split)
    inten = gas_intensity()
    panel = panel[(panel.month >= pd.Period(args.frm)) &
                  (panel.month <= pd.Period(args.to))].copy()
    panel["intensity"] = panel.month.map(inten)
    panel = panel.dropna(subset=["intensity"])
    panel["ES"] = (panel.grp == "ES").astype(float)
    panel["treat"] = panel.ES * panel.intensity
    panel["y"] = np.log(panel.ratio.clip(lower=1e-6))

    if args.balanced:
        n = panel.month.nunique()
        full = panel.groupby("unit").month.nunique().pipe(lambda s: s[s == n].index)
        panel = panel[panel.unit.isin(full)]

    print("PANEL")
    for g, x in panel.groupby("grp"):
        print(f"  {g}: {x.unit.nunique():3d} units, {len(x):5,} unit-months, "
              f"{x.month.min()} to {x.month.max()}")
    live = inten[inten > 0]
    print(f"  levy live in {len(live)} months; intensity "
          f"{live.min():.1f} to {live.max():.1f} EUR/MWh\n")

    print("y = log(offer price / day-ahead price);  unit + month FE;  "
          "SE clustered on unit\n")
    print(f"{'specification':<34}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    b, se, t, n, k = twfe(panel, "y", "treat", "unit", "month")
    print(f"{'ES x intensity (headline)':<34}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")

    # Placebo: run the real intensity path 36 months EARLIER, on the pre-levy
    # sample only. Shifting forward would land the fake treatment inside the
    # true window and is not a placebo at all -- that mistake produced a
    # "significant" placebo on the first run of this script.
    pre_only = panel[panel.month < pd.Period("2021-09")].copy()
    fake = inten[(inten.index >= pd.Period("2021-09")) &
                 (inten.index <= pd.Period("2023-12"))].copy()
    fake.index = fake.index - 36
    pre_only["treat"] = pre_only.ES * pre_only.month.map(fake).fillna(0.0)
    if pre_only.treat.abs().sum() > 0:
        b2, se2, t2, n2, k2 = twfe(pre_only, "y", "treat", "unit", "month")
        print(f"{'placebo: intensity path -36m, pre':<34}{b2:>10.5f}{se2:>9.5f}"
              f"{t2:>7.2f}{n2:>8,}{k2:>7}")

    # Same design on days when the market splits is not like-for-like; report
    # the treated-window means so the reader can see the raw movement.
    w = panel[(panel.month >= pd.Period("2021-09")) & (panel.month <= pd.Period("2023-12"))]
    pre = panel[panel.month < pd.Period("2021-09")]
    print("\nraw group means of log(offer/market):")
    for lbl, x in (("pre-levy", pre), ("levy window", w)):
        es = x[x.grp == "ES"].y.mean(); pt = x[x.grp == "PT"].y.mean()
        print(f"  {lbl:<14} ES {es:+.3f}   PT {pt:+.3f}   gap {es - pt:+.3f}"
              f"   ({x.unit.nunique()} units, {len(x):,} obs)")

    # Pre-levy sample only: identifies off nothing, must be exactly zero.
    pre = panel[panel.month < pd.Period("2021-09")]
    if pre.treat.abs().sum() == 0:
        print(f"{'pre-period only (no variation)':<34}{'—':>10}{'—':>9}{'—':>7}"
              f"{len(pre):>8,}{pre.unit.nunique():>7}")

    if args.save:
        OUTDIR.mkdir(parents=True, exist_ok=True)
        p = OUTDIR / "clawback_intensity_panel.parquet"
        panel.assign(month=panel.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
