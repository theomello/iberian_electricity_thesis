#!/usr/bin/env python3
"""Did the 2021 levy push hydro to reallocate output across hours?

    .venv/bin/python scripts/analysis/levy_within_month_timing.py

THE MARGIN THIS TESTS, AND WHY IT IS THE RIGHT ONE

RDL 17/2021 charges a fixed number of euros per MWh produced, and that number is
set by the **monthly gas price** -- not by the price the plant actually received:

    Y_it = Q_it * FMIG_t * (PGN_t - 20) * 0.9

So within a month the levy is a constant per-MWh charge while the electricity
price swings hour to hour. In a windy hour clearing at 20 EUR/MWh the levy eats a
large share of revenue; in a still hour clearing at 180 it eats a small one.

A storage plant should respond by **concentrating output in high-price hours and
withdrawing from low-price ones**. That is a within-month reallocation, and it is
the sharpest prediction the levy makes.

`clawback_intensity_did.py` tests the monthly *level* of offer prices and finds a
clean null. But a pure reallocation across hours leaves monthly averages
unchanged -- so that null is a null about a different margin, and cannot rule
this one out.

THE OUTCOME

The **capture rate**: revenue per MWh divided by the month's simple average
price.

    capture_it = sum_h(q_ih * p_h) / ( sum_h(q_ih) * mean_h(p_h) )

Above 1 means the unit generates disproportionately when power is expensive.
It is scale-free and unit-free, so a plant that simply generates more is not
mistaken for one that generates smarter.

DESIGN

Same as the level test: Spanish hydro storage treated, Portuguese hydro control
-- the levy binds only on peninsular Spanish installations, while both countries
clear in the same auction against the same prices. Two-way fixed effects on unit
and month, standard errors clustered on unit, with treatment
`SPAIN_i x intensity_t` where intensity is `(PGN_t - 20) * 0.9` inside the
statutory window and zero outside it.

`beta > 0` means Spanish hydro concentrated its output into expensive hours by
more, in months when the levy bit harder.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawback_intensity_did import gas_intensity, twfe  # noqa: E402


def groups() -> dict[str, str]:
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet").to_pandas()
    g = {}
    for _, r in ua.iterrows():
        if r.country == "ES" and r.tech == "hydro_ugh":
            g[r.unit] = "ES"
        elif r.country == "PT" and str(r.tech).startswith("hydro"):
            g[r.unit] = "PT"
    return g


def prices(drop_split: bool) -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es", "price_pt"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)
    if drop_split:
        # When the market splits the two countries face different prices and the
        # capture rate is not comparable across them.
        px = px[(px.price_es - px.price_pt).abs() < 1e-6]
    return px[["date", "period", "price_es"]].rename(columns={"price_es": "p"})


def build(drop_split: bool) -> pd.DataFrame:
    grp = groups()
    px = prices(drop_split)
    px["month"] = px.date.dt.to_period("M")
    # The month's simple average price: the benchmark a unit is measured against.
    pbar = px.groupby("month").p.mean().rename("pbar")

    out = []
    for f in sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet")):
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "power_mw", "resolution_min"]
        ).to_pandas()
        t = t[t.unit.isin(grp)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        t = t.merge(px, on=["date", "period"], how="inner")
        if t.empty:
            continue
        t["q"] = t.power_mw * t.resolution_min / 60.0
        t["qp"] = t.q * t.p
        g = t.groupby([t.date.dt.to_period("M"), "unit"], as_index=False)[["q", "qp"]].sum()
        g.columns = ["month", "unit", "q", "qp"]
        out.append(g)

    d = pd.concat(out, ignore_index=True)
    d = d.groupby(["month", "unit"], as_index=False)[["q", "qp"]].sum()
    d = d.merge(pbar, left_on="month", right_index=True)
    d = d[(d.q > 0) & (d.pbar > 0)]
    d["capture"] = d.qp / (d.q * d.pbar)
    d["grp"] = d.unit.map(grp)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep-split", action="store_true")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    d = build(drop_split=not args.keep_split)
    inten = gas_intensity()
    d["intensity"] = d.month.map(inten)
    d = d.dropna(subset=["intensity"])
    d["ES"] = (d.grp == "ES").astype(float)
    d["treat"] = d.ES * d.intensity
    # Capture rates are ratios; log makes the effect proportional and symmetric.
    d["y"] = np.log(d.capture.clip(lower=1e-6))

    print("CAPTURE RATE = revenue per MWh / month's average price\n")
    for g, x in d.groupby("grp"):
        print(f"  {g}: {x.unit.nunique():3d} units, {len(x):5,} unit-months, "
              f"mean capture {x.capture.mean():.3f}")

    pre = d[d.month < pd.Period("2021-09")]
    win = d[(d.month >= pd.Period("2021-09")) & (d.month <= pd.Period("2023-12"))]
    print("\nraw means, capture rate")
    print(f"{'':<14}{'ES':>9}{'PT':>9}{'gap':>9}")
    for lbl, x in (("pre-levy", pre), ("levy window", win)):
        a = x[x.grp == "ES"].capture.mean(); b = x[x.grp == "PT"].capture.mean()
        print(f"  {lbl:<12}{a:>9.3f}{b:>9.3f}{a - b:>+9.3f}")

    print("\ny = log(capture);  unit + month FE;  SE clustered on unit\n")
    print(f"{'specification':<36}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    b, se, t, n, k = twfe(d, "y", "treat", "unit", "month")
    print(f"{'ES x intensity':<36}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")

    # Placebo: the real intensity path run 36 months earlier, pre-levy sample.
    ph = pre.copy()
    fake = inten[(inten.index >= pd.Period("2021-09")) &
                 (inten.index <= pd.Period("2023-12"))].copy()
    fake.index = fake.index - 36
    ph["treat"] = ph.ES * ph.month.map(fake).fillna(0.0)
    if ph.treat.abs().sum() > 0:
        b2, se2, t2, n2, k2 = twfe(ph, "y", "treat", "unit", "month")
        print(f"{'placebo: path -36m, pre-levy':<36}{b2:>10.5f}{se2:>9.5f}"
              f"{t2:>7.2f}{n2:>8,}{k2:>7}")

    if args.save:
        p = ROOT / "outputs" / "tables" / "levy_capture_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
