#!/usr/bin/env python3
"""Which EDP cascades carry the 2024 upper-tranche response, and do they have storage?

    .venv/bin/python scripts/analysis/edp_cascade_split.py

Step 6(a) of `notes/rq-midday-hydro.md`. §3.11 there found that from 2024 the
top quarter of EDP's offered volume (`o75`) moves roughly one-for-one with its
markup term X, while the rest of the curve is flat. Two readings:

* MARKET POWER -- EDP, a net buyer at midday, offers its upper tranches cheaper
  when X is low. Nothing in it depends on which cascade the tranche sits in.
* SMALL-STORAGE PHYSICS -- EDP's "units" are whole river cascades, and the upper
  tranches may be plants with little storage, whose water cannot wait for the
  evening. Then the response should sit in the cascades with the LEAST storage
  per MW, and be absent where storage is ample.

So the test: estimate the upper-tranche response cascade by cascade, and set it
against how much storage each cascade has.

STORAGE, AND WHY IT IS A PROXY

Six of the seven cascades are Portuguese, and Portugal's reservoir data (APA /
SNIRH) is geo-blocked outside Portugal (`notes/email-apa-reservoir-data.md`).
No per-cascade energy storage is available. The proxy is behavioural and
PREDETERMINED -- measured on 2018-2023, before the effect:

    peak_share = share of a unit's daily cleared energy that falls in that day's
                 8 highest-priced hours, averaged over days with output

A plant that cannot move water between hours produces in proportion to its
inflow and scores near 8/24 = 0.33; a plant with storage concentrates its
output in the dear hours and scores near 1. It measures the ability to shift
energy within a day as revealed by past dispatch -- not reservoir volume, and it
is stated as such. `cf` (mean cleared MW / capacity) is carried beside it.

THE REGRESSION, per unit

    o75 (and o50) on X instrumented by z_offered; unit-day + hour x year-month
    fixed effects; demand-forecast control; errors clustered on date; closed-form
    Anderson-Rubin sets. The same specification as midday_hydro_iv.py, one
    cascade at a time.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from midday_hydro_iv import ar_closed, ols, tsls  # noqa: E402
from solar_first_stage import demean, load_edp_sample  # noqa: E402

PEAK_HOURS = 8


def flexibility(p: pd.DataFrame) -> pd.DataFrame:
    """peak_share and capacity factor per unit, 2018-2023, hourly."""
    d = p[p.date.dt.year <= 2023]
    h = (d.groupby(["unit", "date", "hour"])
         .agg(mwh=("cleared_mw", "mean"), price=("p_zone", "mean"), cap=("cap", "first"))
         .reset_index())
    h["rank"] = h.groupby(["unit", "date"]).price.rank(ascending=False, method="first")
    day = h.groupby(["unit", "date"]).agg(total=("mwh", "sum"))
    peak = h[h["rank"] <= PEAK_HOURS].groupby(["unit", "date"]).mwh.sum().rename("peak")
    day = day.join(peak)
    day = day[day.total > 0]
    out = (day.peak / day.total).groupby("unit").mean().rename("peak_share").to_frame()
    out["cf"] = h.groupby("unit").apply(lambda g: g.mwh.mean() / g.cap.iloc[0],
                                        include_groups=False)
    return out


def iv(d: pd.DataFrame, y: str) -> dict:
    cols = [y, "X", "z_offered", "fcst"]
    d = d.dropna(subset=cols)
    if len(d) < 500:
        return {"n": len(d)}
    w = demean(d, cols, ["ud", "hym"])
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    Y, X, Z, W = (w[c].to_numpy() for c in cols)
    b_fs, se_fs = ols(X, np.column_stack([Z, W]), cl)
    b, se = tsls(Y, X, Z, W, cl)
    return {"n": len(d), "F": (b_fs[0] / se_fs[0]) ** 2, "beta": b, "se": se,
            "ar": ar_closed(Y, X, Z, W, cl)}


def main() -> int:
    p = load_edp_sample(panel_cols=("p_zone", "o50", "o75", "cleared_mw", "cap"))
    flex = flexibility(p)
    rows = []
    for unit, g in p.groupby("unit"):
        for label, s in (("2024-2026", g[g.date.dt.year >= 2024]), ("pooled", g)):
            for y in ("o75", "o50"):
                rows.append({"unit": unit, "sample": label, "outcome": y, **iv(s, y)})
    r = pd.DataFrame(rows)

    print("FLEXIBILITY PROXY, 2018-2023 (predetermined): share of daily cleared energy in "
          f"the day's {PEAK_HOURS} dearest hours; 0.33 = cannot shift, 1 = fully shifted")
    print(flex.round(3).sort_values("peak_share").to_string(), "\n")

    print("RESPONSE BY CASCADE -- 2SLS beta (se), first-stage F, AR 95% set")
    for (label, y), t in r.groupby(["sample", "outcome"], sort=False):
        print(f"  {y}, {label}")
        t = t.set_index("unit").join(flex).sort_values("peak_share")
        for unit, row in t.iterrows():
            if pd.isna(row.get("beta")):
                print(f"    {unit:8s} too few ({int(row.n)})")
                continue
            print(f"    {unit:8s} peak_share {row.peak_share:.3f}  n={int(row.n):>7,}  "
                  f"beta {row.beta:+.3f} ({row.se:.3f})  F {row.F:6.1f}  AR95 {row.ar}")
    t = r[(r["sample"] == "2024-2026") & (r.outcome == "o75")].set_index("unit").join(flex)
    t = t.dropna(subset=["beta"])
    if len(t) >= 3:
        rho = np.corrcoef(t.peak_share, t.beta)[0, 1]
        print(f"\n  across cascades, 2024-2026: corr(peak_share, o75 beta) = {rho:+.2f} "
              f"over {len(t)} cascades -- a description, not a test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
