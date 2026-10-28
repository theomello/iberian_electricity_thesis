#!/usr/bin/env python3
"""Gas cap: the pre-trend test against Italy on the Iberian plants that bid like Italian ones.

    .venv/bin/python scripts/analysis/gas_cap_italy_like.py

Every comparison with Italy failed on the Iberian three-part offer (a cheap minimum-load block,
a near-cost band, high-priced withholding blocks). Rule fixed before running: an Iberian unit is
"Italian-looking" if its median |p_mid - cost| over unit-hours of the selection window
(2021-06-15 -> 2021-09-30) is at or below the median of the same over Italian units. The test
window starts after it (2021-10-01 -> 2022-06-14), so selection and test do not share months; the
two later placebos (2022-01-01, 2022-03-01) apply, thresholds as in step 1. Outcomes: p_mid minus
cost (mmid) and run20.

What it buys: a comparison valid for those plants only, not for Iberian bidding as a whole.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gas_cap_gb import PANEL, step1  # noqa: E402

SEL0, SEL1, TEST0 = pd.Timestamp("2021-06-15"), pd.Timestamp("2021-09-30"), pd.Timestamp("2021-10-01")


def main() -> int:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p_mid", "run20", "cost", "subsidy"])
    ybar = h[h.subsidy > 0].drop_duplicates("date").subsidy.mean()
    s = h[h.date.between(SEL0, SEL1)].dropna(subset=["p_mid", "cost"])
    dev = (s.p_mid - s.cost).abs().groupby([s.unit, s.iberia]).median().reset_index(name="dev")
    cut = dev[~dev.iberia].dev.median()
    keep = set(dev[dev.iberia & (dev.dev <= cut)].unit)
    fm = h.drop_duplicates("unit").set_index("unit").firm
    print(f"Italian median |p_mid - cost| in summer 2021: {cut:.1f}; Iberian units at or below it: "
          f"{len(keep)} of {dev.iberia.sum()}")
    print("  by firm: " + fm.reindex(sorted(keep)).value_counts().to_string().replace("\n", "; "))
    print("  Iberian units' median deviation, quartiles: "
          + ", ".join(f"{q:.1f}" for q in dev[dev.iberia].dev.quantile([.25, .5, .75])))
    h = h[~h.iberia | h.unit.isin(keep)]
    for out, col, thr, dec in (("mmid", None, ybar / 5, 1), ("run20", "run20", 0.05, 3)):
        x = h.assign(m=(h.p_mid - h.cost) if col is None else h[col]).dropna(subset=["m"])
        d = x.groupby(["unit", "date"], as_index=False).agg(m=("m", "mean"), firm=("firm", "first"),
                                                            iberia=("iberia", "first"))
        d["firm"] = d.firm.fillna(d.unit)
        print(f"\n=== {out} (test window from {TEST0.date()}) ===")
        step1(d, thr, dec, label="Italy", start=TEST0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
