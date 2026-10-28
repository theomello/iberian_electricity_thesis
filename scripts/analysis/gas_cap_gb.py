#!/usr/bin/env python3
"""Step 2d of the gas-cap design: British gas plants as a second comparison for Iberia.

    .venv/bin/python scripts/analysis/gas_cap_gb.py [--outcome price|run]

Builds a British unit-day panel from Elexon's balancing offers (BOD) and physical notifications
(PN), on whatever units are on disk, and runs step 1's pre-trend test (design §6) of Iberia
against it. Writes outputs/tables/gas_cap_gb_panel.parquet.

Outcomes, fixed in the design before looking:
- **price**: Britain, the offer on the first band above the notified level (`pairId` 1), minus
  the bid-time gross cost, in EUR; Iberia, p_mid minus its cost after the subsidy (as in steps
  1c-2). Daily means over periods.
- **run**: Britain, the notified level (FPN) over K, K the unit's pre-cap 99th percentile of
  notified MW; Iberia, run20 (MW offered at or below cost + 20, over K). Daily means.

The notified level is the duration-weighted mean of the PN segments in each half-hour. Firms:
Elexon's lead party. Pre-period 2021-06-15 -> 2022-06-14; placebos and thresholds as in step 1
(Y_bar/5 for price, 0.05 for run).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gas_cap_pretrend import did  # noqa: E402

DATA = ROOT / "data"
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
OUT = ROOT / "outputs" / "tables" / "gas_cap_gb_panel.parquet"
START, END = pd.Timestamp("2021-06-15"), pd.Timestamp("2023-06-30")
PRE_END = pd.Timestamp("2022-06-14")
PLACEBOS = ["2021-10-01", "2022-01-01", "2022-03-01"]


def gb_panel() -> pd.DataFrame:
    cost = pd.read_parquet(DATA / "jrc_ppdb" / "gb_implied_marginal_cost_daily.parquet")
    cost = cost[~cost.eff_is_generic & cost.elexon_unit.notna()]
    rows = []
    for u, firm in cost.drop_duplicates("unit")[["elexon_unit", "lead_party"]].itertuples(index=False):
        pb, pp = DATA / "elexon" / "bod" / "parquet" / f"{u}.parquet", DATA / "elexon" / "pn" / "parquet" / f"{u}.parquet"
        if not (pb.exists() and pp.exists()):
            continue
        pn = pd.read_parquet(pp)
        dur = (pn.timeTo - pn.timeFrom).dt.total_seconds()
        pn = pn.assign(w=dur, lv=(pn.levelFrom + pn.levelTo) / 2 * dur)
        per = pn.groupby(["settlementDate", "settlementPeriod"]).agg(lv=("lv", "sum"), w=("w", "sum"))
        per["fpn"] = per.lv / per.w
        b = pd.read_parquet(pb)
        o1 = b[b.pairId == 1].groupby(["settlementDate", "settlementPeriod"]).offer.first().rename("offer1")
        per = per[["fpn"]].join(o1, how="left").reset_index()
        per["date"] = pd.to_datetime(per.settlementDate)
        per = per[per.date.between(START, END)]
        K = per[per.date <= PRE_END].fpn.quantile(0.99)
        if not K > 10:
            continue
        d = per.groupby("date").agg(fpn=("fpn", "mean"), offer1=("offer1", "mean")).reset_index()
        d["K"], d["elexon_unit"], d["firm"] = K, u, firm if isinstance(firm, str) else u
        rows.append(d)
    g = pd.concat(rows, ignore_index=True)
    c = cost[["elexon_unit", "date", "marginal_cost_bid_gbp_mwh", "gbp_per_eur_bid"]]
    g = g.merge(c, on=["elexon_unit", "date"], how="left")
    g["offer1_eur"] = g.offer1 / g.gbp_per_eur_bid
    g["cost_eur"] = g.marginal_cost_bid_gbp_mwh / g.gbp_per_eur_bid
    g["m_price"] = g.offer1_eur - g.cost_eur
    g["m_run"] = g.fpn / g.K
    g.to_parquet(OUT, index=False)
    return g.rename(columns={"elexon_unit": "unit"})


def iberia(outcome: str) -> tuple[pd.DataFrame, float]:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p_mid", "run20", "cost", "subsidy"])
    ybar = h[h.subsidy > 0].drop_duplicates("date").subsidy.mean()
    h = h[h.iberia]
    h["m"] = h.p_mid - h.cost if outcome == "price" else h.run20
    d = h.dropna(subset=["m"]).groupby(["unit", "date"], as_index=False).agg(m=("m", "mean"), firm=("firm", "first"))
    d["firm"] = d.firm.fillna(d.unit)
    return d, ybar


def step1(d: pd.DataFrame, thr: float, dec: int) -> None:
    pre = d[(d.date >= START) & (d.date <= PRE_END)].copy()
    pre["m_u"] = pre.m - pre.groupby("unit").m.transform("mean")
    mon = pre.assign(ym=pre.date.dt.to_period("M")).groupby(["ym", "iberia"]).m_u.mean().unstack()
    mon.columns = ["Britain", "Iberia"]
    mon["gap"] = mon.Iberia - mon.Britain
    print("pre-period, unit-demeaned outcome\n" + mon.round(dec).to_string())
    wk = pre.assign(w=pre.date.dt.to_period("W")).groupby(["w", "iberia"]).m_u.mean().unstack()
    gap = (wk[True] - wk[False]).dropna()
    t = np.arange(len(gap), dtype=float)
    X = np.column_stack([np.ones_like(t), t])
    b = np.linalg.lstsq(X, gap.to_numpy(), rcond=None)[0]
    e, L, n = gap.to_numpy() - X @ b, 4, len(gap)
    S = sum((1 - l / (L + 1)) * (2 if l else 1) * (X[l:] * e[l:, None]).T @ (X[:n - l] * e[:n - l, None])
            for l in range(L + 1))
    S = (S + S.T) / 2
    XtXi = np.linalg.inv(X.T @ X)
    se = np.sqrt((XtXi @ S @ XtXi)[1, 1])
    fail = abs(b[1] / se) > 1.96 and abs(b[1] * 52) >= thr
    print(f"\nweekly gap trend {b[1]:.4g}/week (se {se:.3g}), {b[1] * 52:.3g} a year, {n} weeks"
          f"{'  <-- FAILS' if fail else ''}")
    print(f"placebo caps (unit + date FE, firm clusters, {pre.firm.nunique()} firms), threshold {thr:.3g}:")
    for p in PLACEBOS:
        bt, s = did(pre, (pre.iberia & (pre.date >= p)).to_numpy())
        print(f"  {p}: {bt:+.3g} (se {s:.3g}){'  <-- exceeds threshold' if abs(bt) >= thr else ''}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outcome", choices=["price", "run"], default="price")
    a = ap.parse_args()
    g = gb_panel()
    ib, ybar = iberia(a.outcome)
    col = "m_price" if a.outcome == "price" else "m_run"
    gb = g.dropna(subset=[col])[["unit", "date", "firm", col]].rename(columns={col: "m"})
    d = pd.concat([ib.assign(iberia=True), gb.assign(iberia=False)], ignore_index=True)
    print(f"Britain: {gb.unit.nunique()} units, {gb.firm.nunique()} firms on disk; "
          f"Iberia: {ib.unit.nunique()} units. Outcome {a.outcome}.\n")
    step1(d, ybar / 5 if a.outcome == "price" else 0.05, 1 if a.outcome == "price" else 3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
