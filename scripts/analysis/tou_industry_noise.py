"""Noise check for the industry CES (docs/specs/2026-11-13-industry-noise-check.md): pre-reform data only.

    .venv/bin/python scripts/analysis/tou_industry_noise.py

For each series, the standard deviation of 74-weekday window means of the leave-year-out LASSO residual of ln(evening/night load), Spain minus Portugal, and the detectable
elasticity given the series' dose. Writes outputs/tables/tou_industry_noise.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

SERIES = {"E0": [1201], "E1+E2": [1202, 1203], "6.2": [1216], "6.3": [1217], "6.4": [1218]}
EVE, NIGHT = [18, 19, 20, 21], list(range(8))
WIN, STEP = 74, 5


def eve_night(load):
    """Daily ln(evening/night) from an hourly (date, hour, v) frame, complete days only."""
    g = load.groupby("date")
    ok = g.hour.count() == 24
    e = load[load.hour.isin(EVE)].groupby("date").v.sum()
    n = load[load.hour.isin(NIGHT)].groupby("date").v.sum()
    return np.log(e / n)[ok[ok].index]


def main():
    d, _ = C.daily_frame()
    x = C.D.prep(T.build("e0", end="2021-09-14"))
    pt = x[["date", "hour", "load_pt"]].rename(columns={"load_pt": "v"})
    d = d.set_index("date")
    d["y_pt"] = eve_night(pt)
    dose = pd.read_csv(T.OUT / "tou_cross_tariff_dose.csv").set_index("series").dose_ddd
    rows = []
    for name, ids in SERIES.items():
        dd = d.copy()
        dd["y_es"] = eve_night(CT.esios_load(ids))
        dd = dd.reset_index()
        yes, ypt = dd.set_index(dd.index).y_es.reset_index(drop=True), dd.y_pt.reset_index(drop=True)
        res_es = pd.Series(np.nan, index=dd.index)
        res_pt = pd.Series(np.nan, index=dd.index)
        for yr in (2018, 2019, 2020):
            sel = dd.year == yr
            res_es[sel] = (dd.y_es - C.taste_pred(dd, dd.y_es, "es", (yr,)))[sel]
            res_pt[sel] = (dd.y_pt - C.taste_pred(dd, dd.y_pt, "pt", (yr,)))[sel]
        elig = dd.pre & dd.both & res_es.notna() & res_pt.notna()
        r = (res_es - res_pt)[elig].to_numpy()
        means = np.array([r[i:i + WIN].mean() for i in range(0, len(r) - WIN + 1, STEP)])
        noise = float(means.std(ddof=1))
        mde_eff = 2.8 * noise
        mde_sig = mde_eff / float(dose[name])
        verdict = "feasible" if mde_sig <= 0.15 else "marginal" if mde_sig <= 0.30 else "infeasible"
        rows.append(dict(series=name, dose=float(dose[name]), days=len(r), daily_sd=float(r.std(ddof=1)), window_mean_sd=noise, max_abs_window_mean=float(np.abs(means).max()),
                         mde_effect=mde_eff, mde_sigma=mde_sig, signal_if_sigma_074=float(dose[name]) * 0.074 / noise, signal_if_sigma_167=float(dose[name]) * 0.167 / noise, verdict=verdict))
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "tou_industry_noise.csv", index=False)
    print(R.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
