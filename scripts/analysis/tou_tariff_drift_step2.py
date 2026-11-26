"""Step 2 of docs/specs/2026-11-26-tariff-drift-design.md: one pre-named observable for the 6.3 drift.

Candidate (a): the summer's mean OMIE price spread, evening hours 18-21 minus night hours 0-7, over the aligned window.
K1: R^2 of the six placebo betas on the covariate at least 0.70.  K2: rolling-origin RMSE (targets 2017, 2018, 2019, fit on
earlier summers) below the year trend's RMSE.  Both must hold. Tariff 6.3 (the only tariff with an established trend).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
# OMIE price files on disk start in 2018; REN's ES market price (the same day-ahead price) covers 2014 onwards
import tou_industry_regulated_price as RP  # noqa: E402
ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
ren = ren[ren.series == "ES"]
loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
eh = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
d = eh.index.get_level_values(0)
h = eh.index.get_level_values(1)
spread = {}
for y in S6.SUMMERS + [2021]:
    a, b = (S6.R0, S6.R1) if y == 2021 else S6.aligned(y)
    w = (d >= a) & (d <= b)
    spread[y] = float(eh[w & np.isin(h, [18, 19, 20, 21])].mean() - eh[w & (h <= 7)].mean())
t3 = pd.read_csv(OUT / "tou_tariff_drift_step3.csv").set_index("series")
beta = {int(k): float(v) for k, v in (p.split(":") for p in t3.loc["6.3", "placebos"].split())}
yrs = np.array(S6.SUMMERS, float)
b = np.array([beta[y] for y in S6.SUMMERS])
s = np.array([spread[y] for y in S6.SUMMERS])
print("summer: beta_6.3  spread(18-21 minus 0-7, EUR/MWh)")
for y in S6.SUMMERS:
    print(f"  {y}: {beta[y]:+.3f}  {spread[y]:+.2f}")
print(f"  2021: (reform summer) spread {spread[2021]:+.2f}")
r = np.corrcoef(s, b)[0, 1]
print(f"K1: corr {r:+.3f}, R^2 {r * r:.3f} >= 0.70: {bool(r * r >= 0.70)}")


def pred(x_tr, y_tr, x0):
    c = np.polyfit(x_tr, y_tr, 1)
    return c[0] * x0 + c[1]


err_cov, err_tr = [], []
for tgt in (2017, 2018, 2019):
    tr = [y for y in S6.SUMMERS if y < tgt]
    err_cov.append(beta[tgt] - pred([spread[y] for y in tr], [beta[y] for y in tr], spread[tgt]))
    err_tr.append(beta[tgt] - pred(tr, [beta[y] for y in tr], tgt))
rm = lambda e: float(np.sqrt(np.mean(np.square(e))))
print(f"K2: RMSE covariate {rm(err_cov):.3f} (errors {np.round(err_cov, 3)}) vs trend {rm(err_tr):.3f} (errors {np.round(err_tr, 3)}) -> covariate below trend: {bool(rm(err_cov) < rm(err_tr))}")
pd.DataFrame([dict(summer=y, beta_63=beta[y], spread=spread[y]) for y in S6.SUMMERS] + [dict(summer=2021, beta_63=np.nan, spread=spread[2021])]).to_csv(OUT / "tou_tariff_drift_step2.csv", index=False)
