#!/usr/bin/env python3
"""Implied Lerner index by firm, combining measured elasticity with CNMC shares.

    .venv/bin/python scripts/analysis/markup_from_shares.py

Reads outputs/tables/residual_demand_slope_full.parquet (produced by
scripts/analysis/residual_demand_slope.py --full --save) and
data/cnmc/cnmc_generation_shares.parquet. Prints; writes nothing.

THE IDENTITY BEING USED

A profit-maximising firm sets p = C' - RD_i/RD'_i, so its markup over marginal
cost is q_i / |RD'_i| and its Lerner index is

    L_i = (p - C') / p = q_i / (|RD'_i| p) = s_i / eta,     eta = |RD'| p / Q

where s_i is firm i's share of cleared volume Q and eta is the residual demand
elasticity evaluated at market scale. Both inputs are now measured rather than
assumed: eta from the submitted bid curves, s_i from CNMC's published
generation shares by business group.

WHY THIS IS A LOWER BOUND

eta here is built from the *market-wide* curve, i.e. the residual demand facing
an infinitesimal participant. A real firm's own supply is excluded from its
residual demand, which can only make that curve steeper: |RD'_i| <= |RD'|, so

    L_i = s_i / eta_i  >=  s_i / eta.

Every number below is therefore the **least** markup consistent with static
profit maximisation, not an estimate of the markup actually taken. It is also
not evidence that firms exercised it -- it is what the market structure and the
submitted curves made available.

CAVEATS THAT MATTER FOR READING THE TABLES

* CNMC shares are **annual and MIBEL-wide**; eta is per market period. Pairing
  them assumes a firm's share is stable within the year, which it is not --
  shares move with hydrology and outages. Treat the within-year splits as
  indicative.
* CNMC covers 2008-2023, the bid archive 2018-2026, so the overlap is 2018-2023.
* Zero-price periods are already excluded upstream: L = s/eta is undefined when
  p = 0. Their share grows to 21% of periods by 2026, so the recent years
  describe a shrinking subset of hours.
* Market-splitting hours are excluded upstream too, and those are the *most*
  concentrated hours, so this understates further.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
ETA = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"
CNMC = ROOT / "data" / "cnmc" / "cnmc_generation_shares.parquet"
FIRMS = ["IBERDROLA", "ENDESA", "EDP", "NATURGY", "AXPO", "ACCIONA", "REPSOL"]


def main() -> int:
    if not ETA.exists():
        print(f"missing {ETA.relative_to(ROOT)} -- run\n"
              f"  .venv/bin/python scripts/analysis/residual_demand_slope.py --full --save",
              file=sys.stderr)
        return 1
    d = pq.read_table(ETA).to_pandas()
    shares = pq.read_table(CNMC).to_pandas().set_index("year")

    d["vre_tercile"] = d.groupby("year").vre_share.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))

    years = sorted(set(d.year) & set(shares.index))
    eta_all = d.groupby("year").eta_h5.median()
    eta_hi = d[d.vre_tercile == "high"].groupby("year").eta_h5.median()
    px = d.groupby("year").p_star.median()

    print("=" * 74)
    print("IMPLIED LERNER INDEX  L = s / eta   (lower bound; see docstring)")
    print("=" * 74)
    print(f"\n  eta and price by year ({len(d):,} periods)\n")
    t = pd.DataFrame({"eta (all hours)": eta_all, "eta (high-VRE third)": eta_hi,
                      "median price EUR/MWh": px}).loc[years]
    print(t.round(2).to_string())

    for label, eta in (("ALL HOURS", eta_all), ("HIGH-VRE THIRD OF HOURS", eta_hi)):
        print(f"\n{'-' * 74}\n  {label}: implied Lerner, by firm and year\n{'-' * 74}")
        tab = pd.DataFrame({f: shares.loc[years, f] / 100 / eta.loc[years] for f in FIRMS})
        print((tab * 100).round(1).to_string())

    print(f"\n{'-' * 74}\n  Implied markup in EUR/MWh (Lerner x median price), all hours\n{'-' * 74}")
    mk = pd.DataFrame({f: shares.loc[years, f] / 100 / eta_all.loc[years] * px.loc[years]
                       for f in FIRMS})
    print(mk.round(1).to_string())

    a, b = years[0], years[-1]
    big = shares.loc[[a, b], ["IBERDROLA", "ENDESA"]].mean(axis=1) / 100
    print(f"\n{'=' * 74}")
    print(f"  For the average of Iberdrola and Endesa, the implied floor on the")
    print(f"  Lerner index moves from {big[a]/eta_all[a]*100:.0f}% in {a} to "
          f"{big[b]/eta_all[b]*100:.0f}% in {b} across all hours,")
    print(f"  and to {big[b]/eta_hi[b]*100:.0f}% in the highest-VRE third of {b}.")
    print(f"  CNMC's HHI over the same window: {shares.loc[a,'HHI']:.0f} -> "
          f"{shares.loc[b,'HHI']:.0f} (i.e. measured concentration FELL).")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
