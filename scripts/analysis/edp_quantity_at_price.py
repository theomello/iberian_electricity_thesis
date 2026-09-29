#!/usr/bin/env python3
"""Within-day test on EDP's cascades, read horizontally: quantity offered at fixed prices.

    .venv/bin/python scripts/analysis/edp_quantity_at_price.py

Step 6c of `notes/rq-midday-hydro.md`; §3.13 there. The price at a fixed point
of the offer curve is a valid within-day outcome only if that point is the same
tranche all day (assumption A2 of `docs/specs/2026-09-29-water-value-design.md`),
and A2 fails for Douro, Mondego and Tejo-Mondego, which reshape their tranche
quantities through the day. This reads the curve the other way.

THE OUTCOME

For each unit-period, the MW offered at or below a price p_k, over capacity:

    s_k = S_ih(p_k) / capacity,     p_k = the k-th quantile (k = 25, 50, 75) of the
                                    unit-DAY's offered prices, volume-weighted over
                                    all its periods

p_k is fixed within the unit-day, so the unit-day fixed effect still absorbs the
water value. Under a constant water value and price-taking, the curve is the
same in every hour, so s_k is constant within the day. Under market power, a
higher markup term X lifts the curve and LESS is offered below p_k: the
coefficient on X is negative. No assumption about which tranche is which is
needed.

SCALE

A vertical shift of beta * X moves S(p_k) by about -beta * X * S'(p_k), with
S'(p_k) the curve's local density of offers (MW per EUR/MWh, over +/-5 EUR/MWh
around p_k). So `implied beta = -coefficient / mean S'`, both in capacity
shares. Rough -- the curves are step functions -- and reported as a scale, not
an estimate.

Same specification as `midday_hydro_iv.py`: X instrumented by offered solar,
unit-day + hour x year-month fixed effects, demand-forecast control, errors
clustered on date, closed-form Anderson-Rubin sets.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_within_day_probe import BIDS  # noqa: E402
from midday_hydro_iv import ar_closed, ols, tsls  # noqa: E402
from solar_first_stage import demean, load_edp_sample  # noqa: E402

OUT = ROOT / "outputs/tables/edp_quantity_at_price.parquet"
RESHAPING = ["ADOURO", "MONDEGO", "TEMON"]      # A2 fails (§3.13)
STABLE = ["ACAVADO", "ALIMA", "GUADIA", "HCHI"]  # usually an identical curve all day
QS = (0.25, 0.50, 0.75)
H = 5.0


def weighted_quantile(price: np.ndarray, w: np.ndarray, q: float) -> float:
    o = np.argsort(price)
    cw = np.cumsum(w[o])
    return float(price[o][np.searchsorted(cw, q * cw[-1])])


def month_outcomes(f: Path, units: list[str], cap: pd.Series) -> pd.DataFrame:
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw",
                                  "price_eur_mwh"],
                      filters=[("unit", "in", units), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    if b.empty:
        return pd.DataFrame()
    b["date"] = pd.to_datetime(b.date)
    # The unit-day's reference prices: volume-weighted quantiles over ALL its periods.
    ref = (b.groupby(["unit", "date"])
           .apply(lambda g: pd.Series({f"pk{int(q*100)}": weighted_quantile(
               g.price_eur_mwh.to_numpy(), g.power_mw.to_numpy(), q) for q in QS}),
               include_groups=False)
           .reset_index())
    b = b.merge(ref, on=["unit", "date"])
    keys = ["unit", "date", "period"]
    out = b[keys].drop_duplicates().copy()
    for q in QS:
        k = f"pk{int(q*100)}"
        at = (b.price_eur_mwh <= b[k])
        s = b.power_mw.where(at, 0.0).groupby([b.unit, b.date, b.period]).sum()
        near = ((b.price_eur_mwh - b[k]).abs() <= H)
        dens = b.power_mw.where(near, 0.0).groupby([b.unit, b.date, b.period]).sum() / (2 * H)
        out = out.merge(s.rename(f"s{int(q*100)}").reset_index(), on=keys)
        out = out.merge(dens.rename(f"d{int(q*100)}").reset_index(), on=keys)
    capv = out.unit.map(cap)
    for q in QS:
        out[f"s{int(q*100)}"] /= capv
        out[f"d{int(q*100)}"] /= capv
    return out


def iv_row(d: pd.DataFrame, y: str, dens: str, label: str) -> None:
    cols = [y, "X", "z_offered", "fcst"]
    d = d.dropna(subset=cols)
    # Percentage points of capacity, so coefficients and AR bounds read directly.
    d = d.assign(**{y: d[y] * 100, dens: d[dens] * 100})
    if len(d) < 500:
        print(f"    {label:30s} too few ({len(d)})")
        return
    w = demean(d, cols, ["ud", "hym"])
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    Y, X, Z, W = (w[c].to_numpy() for c in cols)
    b_fs, se_fs = ols(X, np.column_stack([Z, W]), cl)
    b, se = tsls(Y, X, Z, W, cl)
    ar = ar_closed(Y, X, Z, W, cl)
    sd = d.groupby("ud")[y].transform("std").mean()
    implied = -b / d[dens].mean() if d[dens].mean() > 0 else np.nan
    print(f"    {label:30s} n={len(d):>7,}  F {(b_fs[0]/se_fs[0])**2:6.1f}  "
          f"coef {b:+.3f} pp per EUR/MWh of X ({se:.3f})  AR95 {ar}  "
          f"| within-day sd {sd:.2f} pp  | implied beta {implied:+.2f}")


def main() -> int:
    p = load_edp_sample(panel_cols=("cap",))
    cap = p.groupby("unit").cap.first()
    units = sorted(p.unit.unique())
    parts = [month_outcomes(f, units, cap) for f in sorted(BIDS.glob("bids_*.parquet"))]
    q = pd.concat([x for x in parts if not x.empty], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    q.to_parquet(OUT, index=False)
    d = p.merge(q, on=["unit", "date", "period"], how="inner")

    print("QUANTITY OFFERED AT OR BELOW THE UNIT-DAY'S OWN PRICE QUANTILES, share of capacity.")
    print("Market power predicts a NEGATIVE coefficient on X (the curve lifts, less is "
          "offered below a fixed price); price-taking predicts 0.\n")
    for name, us in (("RESHAPING CASCADES (A2 fails): Douro, Mondego, Tejo-Mondego", RESHAPING),
                     ("STABLE CASCADES (check -- should be 0): Cavado, Lima, Guadiana, "
                      "Hidrocantabrico", STABLE)):
        print(name)
        g = d[d.unit.isin(us)]
        for qk in (25, 50, 75):
            iv_row(g, f"s{qk}", f"d{qk}", f"s{qk}, pooled")
        for era, e in g.groupby("era", observed=True):
            iv_row(e, "s50", "d50", f"s50, {era}")
        print()
    print("BY CASCADE, s50, 2024-2026")
    late = d[d.date.dt.year >= 2024]
    for u, g in late.groupby("unit"):
        iv_row(g, "s50", "d50", u)
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(q):,} unit-periods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
