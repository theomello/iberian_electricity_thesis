#!/usr/bin/env python3
"""Step 1b of the gas-cap design: does an alternative gas-cost definition remove the pre-cap
drift between Iberian and Italian gas plants? (docs/specs/2026-10-28-gas-cap-conduct-design.md)

    .venv/bin/python scripts/analysis/gas_cap_cost_test.py

Step 1 failed on every outcome, and the drift is on the Iberian side. Two hypotheses about the
gas price Iberian plants bid on, each a cost definition, each run through step 1 unchanged
(outcomes m25 and run20, same thresholds, same placebos):

* `lag30`: the mean hub price over days D-31 .. D-2 (gas bought ahead, so the cost lags spot),
  in BOTH countries (MIBGAS in Iberia, PSV in Italy): if it is how plants bid, it is how
  Italian plants bid too.
* `maxpsv`: in Iberia, the higher of MIBGAS and PSV, both as known at D-2 (gas valued at what it
  would fetch in Europe); Italy unchanged.
* `base`, the definition step 1 used, for reference.

Cost = (gas + 0.2020 * EUA) / eff, minus the decree's bid-time subsidy in Iberia.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gas_cap_offer_panel import iberia_steps, italy_steps, unit_hour, START, END, PRE_END  # noqa: E402
from gas_cap_pretrend import did, PLACEBOS  # noqa: E402

EF = 0.2020


def hub(series: pd.Series) -> pd.DataFrame:
    """D-2 value and the D-31..D-2 mean of a daily hub price, by delivery day D."""
    s = series.sort_index().asfreq("D")
    out = pd.DataFrame({"bid": s.ffill(limit=5).shift(2), "lag30": s.rolling(30, min_periods=20).mean().shift(2)})
    out.index.name = "date"
    return out.reset_index()


def costs() -> tuple[dict, dict]:
    mib = pd.read_parquet(DATA / "mibgas" / "mibgas_price_index_daily.parquet")
    mib = mib.assign(date=pd.to_datetime(mib.date)).set_index("date").mibgas_es_eur_mwh
    g = pd.read_parquet(DATA / "gme" / "gas" / "gme_mgp_gas_daily.parquet").sort_values(["gas_day", "session"])
    g["px"] = g.price_mean.fillna(g.price_ref)
    psv = g.dropna(subset=["px"]).groupby("gas_day").px.last()
    M, P = hub(mib).add_prefix("mib_").rename(columns={"mib_date": "date"}), hub(psv).add_prefix("psv_").rename(columns={"psv_date": "date"})
    ib = pd.read_parquet(DATA / "jrc_ppdb" / "implied_marginal_cost_daily.parquet",
                         columns=["unit", "date", "fuel", "eff", "eff_is_generic", "co2_eur_tco2_bid",
                                  "subsidy_bid_eur_mwh", "marginal_cost_subsidised_bid_eur_mwh"])
    ib = ib[(ib.fuel == "gas") & ~ib.eff_is_generic & ib.date.between(START, END)]
    ib = ib.merge(M, on="date", how="left").merge(P, on="date", how="left")
    it = pd.read_parquet(DATA / "jrc_ppdb" / "italy_implied_marginal_cost_daily.parquet",
                         columns=["unit", "date", "eff", "eff_is_generic", "capacity_g", "co2_eur_tco2_bid",
                                  "marginal_cost_bid_eur_mwh"])
    it = it[~it.eff_is_generic & (it.capacity_g >= 100) & it.date.between(START, END)].merge(P, on="date", how="left")
    c_ib = {"base": ib.marginal_cost_subsidised_bid_eur_mwh,
            "lag30": (ib.mib_lag30 + EF * ib.co2_eur_tco2_bid) / ib.eff - ib.subsidy_bid_eur_mwh,
            "maxpsv": (np.fmax(ib.mib_bid, ib.psv_bid) + EF * ib.co2_eur_tco2_bid) / ib.eff - ib.subsidy_bid_eur_mwh}
    c_it = {"base": it.marginal_cost_bid_eur_mwh,
            "lag30": (it.psv_lag30 + EF * it.co2_eur_tco2_bid) / it.eff,
            "maxpsv": it.marginal_cost_bid_eur_mwh}
    mk = lambda f, c: pd.DataFrame({"unit": f.unit.to_numpy(), "date": f.date.to_numpy(), "cost": c.to_numpy()})
    return {k: mk(ib, v) for k, v in c_ib.items()}, {k: mk(it, v) for k, v in c_it.items()}


def step1(d: pd.DataFrame, col: str, thr: float) -> str:
    pre = d[d.date <= PRE_END].dropna(subset=[col]).copy()
    pre["m"] = pre[col]
    pre["m_u"] = pre.m - pre.groupby("unit").m.transform("mean")
    wk = pre.assign(w=pre.date.dt.to_period("W")).groupby(["w", "iberia"]).m_u.mean().unstack()
    gap = (wk[True] - wk[False]).dropna().to_numpy()
    t = np.arange(len(gap), dtype=float)
    X = np.column_stack([np.ones_like(t), t])
    b = np.linalg.lstsq(X, gap, rcond=None)[0]
    e = gap - X @ b
    S = sum((1 - l / 5) * (X[l:] * e[l:, None]).T @ (X[:len(e) - l] * e[:len(e) - l, None]) * (1 if l == 0 else 1)
            + ((X[:len(e) - l] * e[:len(e) - l, None]).T @ (X[l:] * e[l:, None]) if l else 0)
            for l in range(5))
    iXX = np.linalg.inv(X.T @ X)
    se = np.sqrt((iXX @ S @ iXX)[1, 1])
    fail_t = abs(b[1] / se) > 1.96 and abs(b[1] * 52) >= thr
    pl = []
    for p in PLACEBOS:
        bt, s = did(pre, (pre.iberia & (pre.date >= p)).to_numpy())
        pl.append((bt, s))
    fail_p = any(abs(bt) >= thr for bt, _ in pl)
    mon = pre.assign(ym=pre.date.dt.to_period("M")).groupby(["ym", "iberia"]).m_u.mean().unstack()
    rng = lambda c: f"{mon[c].min():+.3g} .. {mon[c].max():+.3g}"
    return (f"trend/yr {b[1] * 52:+.3g} (t {b[1] / se:.1f}){' FAIL' if fail_t else ''}; placebos "
            + ", ".join(f"{bt:+.3g} ({s:.2g})" for bt, s in pl) + (" FAIL" if fail_p else "")
            + f"; monthly Italy {rng(False)}, Iberia {rng(True)}"
            + ("  => PASSES" if not (fail_t or fail_p) else ""))


def main() -> int:
    ibs, _ = iberia_steps()
    its, _ = italy_steps()
    its = its.drop(columns="operator")
    cib, cit = costs()
    sub = pd.read_parquet(DATA / "jrc_ppdb" / "implied_marginal_cost_daily.parquet",
                          columns=["fuel", "date", "subsidy_bid_eur_mwh"]).query("fuel == 'gas'")
    ybar = sub[sub.subsidy_bid_eur_mwh > 0].drop_duplicates("date").subsidy_bid_eur_mwh.mean()
    firm = pd.read_parquet(ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet",
                           columns=["unit", "date", "firm"]).drop_duplicates(["unit", "date"])
    for k in ("base", "lag30", "maxpsv"):
        parts = []
        for steps, c, ib in ((ibs, cib[k], True), (its, cit[k], False)):
            h = unit_hour(steps, c).merge(c, on=["unit", "date"], how="left")
            h["m25"] = h.p25 - h.cost
            h["iberia"] = ib
            parts.append(h[["unit", "date", "iberia", "m25", "run20"]])
        h = pd.concat(parts, ignore_index=True)
        d = h.groupby(["unit", "date", "iberia"], as_index=False)[["m25", "run20"]].mean()
        d = d.merge(firm, on=["unit", "date"], how="left")
        d["firm"] = d.firm.fillna(d.unit)
        print(f"\n=== cost {k}")
        print(f"  m25   (threshold {ybar / 5:.1f}): {step1(d, 'm25', ybar / 5)}")
        print(f"  run20 (threshold 0.05): {step1(d, 'run20', 0.05)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
