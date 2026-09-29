#!/usr/bin/env python3
"""Test assumptions A2 and A1 of the water-value spec on EDP's cascades.

    .venv/bin/python scripts/analysis/water_value_assumptions.py

`docs/specs/2026-09-29-water-value-design.md` §5 and §9. The within-day test
(`midday_hydro_iv.py`, `notes/rq-midday-hydro.md` §3.11) differences the water
value out of the price at FIXED POINTS of each cascade's offer curve. Two
assumptions carry that:

A2 -- A FIXED POINT IS THE SAME TRANCHE ALL DAY. A cascade stacks several plants.
      If its tranche structure changes within a day, "the price at 50% of
      offered volume" can be one plant at noon and another at night. Test: the
      unit-period's QUANTITY SIGNATURE -- the MW of each step (>= 1 MW), in price
      order, prices ignored. A unit-day is A2-stable when the signature is the
      same in every period, so only the prices move.

A1 -- THE WATER VALUE IS CONSTANT WITHIN THE DAY. It fails when a storage bound
      binds inside the day. Reservoirs are not observed per cascade, so the
      unit-days where one most plausibly binds are flagged from dispatch:
      * forced release -- mean output >= 80% of capacity in the day's 8 cheapest
        hours: water that cannot be stored must run (upper bound, spill);
      * near-empty -- offering < 10% of capacity in at least half the periods
        (lower bound);
      * peak at capacity -- output >= 95% of capacity in any of the 8 dearest
        hours. Reported, not excluded by default: a binding turbine limit
        constrains the allocation but does not by itself move the water value.
      Plus a cascade-level cut: the four cascades with a storage proxy >= 0.7
      (`edp_cascade_split.py`, 2018-2023, predetermined).

Each test reruns the §3.11 specification -- o50 and o75 on X instrumented by
offered solar, unit-day and hour x year-month fixed effects, demand-forecast
control, date clustering, Anderson-Rubin sets -- on the subsample that
satisfies the assumption, beside the full sample.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from edp_cascade_split import flexibility  # noqa: E402
from edp_hydro_panel import MIN_STEP_MW  # noqa: E402
from hydro_within_day_probe import BIDS  # noqa: E402
from midday_hydro_iv import run  # noqa: E402
from solar_first_stage import load_edp_sample  # noqa: E402

HYM = ["ud", "hym"]
FLEX_MIN = 0.7
LOW_HOURS = HIGH_HOURS = 8


def quantity_signatures(units: list[str]) -> pd.DataFrame:
    """Per unit-period: the step quantities in price order, prices ignored."""
    out = []
    for f in sorted(BIDS.glob("bids_*.parquet")):
        b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw",
                                      "price_eur_mwh"],
                          filters=[("unit", "in", units), ("side", "==", "V"),
                                   ("status", "==", "O")]).to_pandas()
        b = b[b.power_mw >= MIN_STEP_MW]
        if b.empty:
            continue
        b = b.sort_values(["unit", "date", "period", "price_eur_mwh", "power_mw"])
        b["q"] = b.power_mw.round(0).astype(int).astype(str)
        sig = b.groupby(["unit", "date", "period"]).q.agg("|".join).rename("qsig")
        out.append(sig.reset_index())
    d = pd.concat(out, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d


def a1_flags(p: pd.DataFrame) -> pd.DataFrame:
    h = (p.groupby(["unit", "date", "hour"])
         .agg(clr=("cleared_mw", "mean"), off=("offered_mw", "mean"), price=("p_zone", "mean"),
              cap=("cap", "first")).reset_index())
    h["rank_hi"] = h.groupby(["unit", "date"]).price.rank(ascending=False, method="first")
    h["rank_lo"] = h.groupby(["unit", "date"]).price.rank(ascending=True, method="first")
    g = h.groupby(["unit", "date"])
    f = pd.DataFrame({
        "forced_release": h[h.rank_lo <= LOW_HOURS].groupby(["unit", "date"]).apply(
            lambda x: x.clr.mean() >= 0.8 * x.cap.iloc[0], include_groups=False),
        "near_empty": g.apply(lambda x: (x.off < 0.1 * x.cap).mean() >= 0.5, include_groups=False),
        "peak_at_cap": h[h.rank_hi <= HIGH_HOURS].groupby(["unit", "date"]).apply(
            lambda x: (x.clr >= 0.95 * x.cap.iloc[0]).any(), include_groups=False),
    }).fillna(False)
    return f.reset_index()


def compare(p: pd.DataFrame, keep: pd.Series, label: str) -> None:
    print(f"\n  {label}: keeps {keep.mean():.3f} of unit-periods")
    for y in ("o50", "o75"):
        run(p, y, "z_offered", HYM, f"{y}, all")
        run(p[keep], y, "z_offered", HYM, f"{y}, assumption holds")
        late = p.date.dt.year >= 2024
        run(p[keep & late], y, "z_offered", HYM, f"{y}, holds, 2024-2026")


def main() -> int:
    p = load_edp_sample(panel_cols=("p_zone", "o50", "o75", "cleared_mw", "offered_mw", "cap",
                                    "n_steps", "same_prices"))

    # ---------- A2
    sig = quantity_signatures(sorted(p.unit.unique()))
    p = p.merge(sig, on=["unit", "date", "period"], how="left")
    ud = p.groupby(["unit", "date"]).agg(nsig=("qsig", "nunique"), nsteps=("n_steps", "nunique"),
                                         year=("date", lambda x: x.iloc[0].year))
    ud["a2"] = ud.nsig == 1
    print("A2 -- share of unit-days whose tranche QUANTITIES are identical in every period")
    print(ud.groupby(["unit", "year"]).a2.mean().unstack().round(2).to_string())
    print("\n   median number of distinct quantity signatures per unit-day")
    print(ud.groupby(["unit", "year"]).nsig.median().unstack().to_string())
    p = p.merge(ud[["a2"]].reset_index(), on=["unit", "date"], how="left")

    print("\nA2 RERUN -- beta, first-stage F and AR set on A2-stable unit-days")
    compare(p, p.a2.fillna(False), "A2-stable unit-days")

    # A zero on A2-stable days can be mechanical: a day whose tranche quantities
    # never change may also be a day whose prices never change, leaving nothing
    # to move. The informative subsample is A2-stable days whose PRICES do vary:
    # the tranches hold still and only their prices move -- exactly the curve
    # shift the design is about.
    a2d = p[p.a2.fillna(False)].drop_duplicates(["unit", "date"])
    print(f"\n  of A2-stable unit-days, {(a2d.same_prices == 1).mean():.3f} also keep the same "
          f"prices all day (nothing to move)")
    varying = p.a2.fillna(False) & (p.same_prices == 0)
    compare(p, varying, "A2-stable unit-days whose prices vary (the clean curve-shift test)")
    print("   by unit, share of unit-days that are A2-stable with varying prices:")
    ud_v = p.assign(v=varying).drop_duplicates(["unit", "date"]).groupby("unit").v.mean()
    print(ud_v.round(3).to_string())

    # ---------- A1
    fl = a1_flags(p)
    p = p.merge(fl, on=["unit", "date"], how="left")
    for c in ("forced_release", "near_empty", "peak_at_cap"):
        p[c] = p[c].fillna(False).astype(bool)
    ud1 = p.drop_duplicates(["unit", "date"]).assign(year=lambda x: x.date.dt.year)
    print("\nA1 -- share of unit-days flagged, by unit (all years)")
    print(ud1.groupby("unit")[["forced_release", "near_empty", "peak_at_cap"]].mean()
          .round(3).to_string())
    flex = flexibility(p)
    high = flex[flex.peak_share >= FLEX_MIN].index
    print(f"\n   high-storage cascades (proxy >= {FLEX_MIN}): {', '.join(high)}")

    print("\nA1 RERUN")
    compare(p, ~(p.forced_release | p.near_empty), "no forced release, not near-empty")
    compare(p, p.unit.isin(high), "high-storage cascades only")
    compare(p, ~(p.forced_release | p.near_empty) & p.unit.isin(high) & p.a2.fillna(False),
            "A1 and A2 together: unflagged, high-storage, A2-stable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
