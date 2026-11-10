#!/usr/bin/env python3
"""Descriptives of the direct-consumer bid panel (build_direct_consumer_panel.py): who they are, how much they buy,
and how price-sensitive their stated buy curves are, by year, kind and sector.

    .venv/bin/python scripts/analysis/direct_consumer_describe.py

Stated sensitivity, per unit-hour with demand at the price q_p > 0:
    drop10 = (q_p - q_p10) / q_p      share of demand at p* given up if the price were EUR 10 higher
    drop50 = (q_p - q_p50) / q_p      the same for EUR 50
    arc    = (q_m10 - q_p10) / q_p * p / 20   arc elasticity of the stated curve at p* (hours with p >= 20)
Before 2021-07-07 bids are capped at EUR 180.30, so an hour enters drop10/arc only if p + 10 < 180.30 and drop50
only if p + 50 < 180.30: otherwise a bid at the cap would count as dropping out by rule. Means are weighted by q_p.

Writes outputs/tables/direct_consumer_describe_{year,sector}.csv.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs" / "tables"
LIMIT_CHANGE = pd.Timestamp("2021-07-07")
CAP_OLD = 180.30


def load() -> pd.DataFrame:
    cols = ["date", "hour", "unit", "p", "q_cleared", "q_m10", "q_m50", "q_p", "q_p10", "q_p50"]
    h = pd.concat(pd.read_parquet(f, columns=cols) for f in sorted(glob.glob(str(T / "direct_consumer_panel/*.parquet"))))
    h["date"] = pd.to_datetime(h.date)
    h["year"] = h.date.dt.year
    reg = pd.read_parquet(ROOT / "data/omie/registry/direct_consumers.parquet",
                          columns=["unit", "kind", "sector", "consumer"])
    h = h.merge(reg, on="unit", how="left")
    h["group_kind"] = h.kind.replace({"own": "consumer", "represented": "consumer"})
    old = h.date < LIMIT_CHANGE
    ok10 = ~old | (h.p + 10 < CAP_OLD)
    ok50 = ~old | (h.p + 50 < CAP_OLD)
    pos = h.q_p > 0
    h["w10"] = np.where(pos & ok10, h.q_p, 0.0)
    h["w50"] = np.where(pos & ok50, h.q_p, 0.0)
    h["wa"] = np.where(pos & ok10 & (h.p >= 20), h.q_p, 0.0)
    qp = h.q_p.where(pos)
    h["drop10"] = ((h.q_p - h.q_p10) / qp).fillna(0.0)
    h["drop50"] = ((h.q_p - h.q_p50) / qp).fillna(0.0)
    h["arc"] = ((h.q_m10 - h.q_p10) / qp * h.p / 20).fillna(0.0)
    return h


def summarise(h: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = h.groupby(by, observed=True)
    out = pd.DataFrame({
        "units": g.unit.nunique(),
        "twh_cleared": g.q_cleared.sum() / 1e6,
        "drop10": g.apply(lambda x: np.average(x.drop10, weights=x.w10) if x.w10.sum() else np.nan),
        "drop50": g.apply(lambda x: np.average(x.drop50, weights=x.w50) if x.w50.sum() else np.nan),
        "arc_elasticity": g.apply(lambda x: np.average(x.arc, weights=x.wa) if x.wa.sum() else np.nan),
    })
    # a unit-year is price-sensitive if, on average, it would give up >= 5% of its demand for EUR 50 more
    uy = h[h.w50 > 0].groupby(by + ["unit"], observed=True).apply(
        lambda x: np.average(x.drop50, weights=x.w50))
    out["share_units_sensitive"] = (uy >= 0.05).groupby(level=list(range(len(by)))).mean()
    return out


def main() -> int:
    h = load()
    print(f"panel: {len(h):,} unit-hours, {h.unit.nunique()} units, {h.date.min().date()} -> {h.date.max().date()}")
    y = summarise(h, ["group_kind", "year"])
    y.to_csv(T / "direct_consumer_describe_year.csv")
    pd.set_option("display.width", 200)
    print("\nby kind and year (consumer = own + represented):")
    print(y.round(3).to_string())
    c = h[h.group_kind == "consumer"].copy()
    c["sector"] = c.sector.fillna("").replace("", "(none)")
    c["era"] = np.where(c.date < LIMIT_CHANGE, "2018-2021H1", np.where(c.year <= 2023, "2021H2-2023", "2024-2026"))
    s = summarise(c, ["sector", "era"])
    s.to_csv(T / "direct_consumer_describe_sector.csv")
    print("\nconsumers by sector and era:")
    print(s.round(3).to_string())
    top = c[c.year >= 2022].groupby(["unit", "consumer", "sector"], observed=True).apply(
        lambda x: pd.Series({"gwh": x.q_cleared.sum() / 1e3,
                             "drop50": np.average(x.drop50, weights=x.w50) if x.w50.sum() else np.nan}))
    print("\nlargest consumers 2022-2026:")
    print(top.sort_values("gwh", ascending=False).head(15).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
