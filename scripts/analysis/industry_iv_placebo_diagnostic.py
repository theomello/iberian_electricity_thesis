"""Descriptive diagnostic of docs/specs/2026-11-17-industry-iv-placebo-diagnostic-design.md. No elasticity.

    .venv/bin/python scripts/analysis/industry_iv_placebo_diagnostic.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_instrument_settlement as S  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import industry_iv_second_settlement as S2  # noqa: E402
import tou_did as T  # noqa: E402


def rf(y, z, mask, dates):
    idx = np.flatnonzero(mask)
    if len(idx) < 200:
        return np.nan, np.nan, len(idx)
    st = E.starts_of(dates[idx])
    b, t = S.t_slope(y[idx], z[idx], st)
    return b, t, len(idx)


def main():
    d = S.build_frame()
    X = np.column_stack([S2.predictors(d, False), d.slope7])
    order = d.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    slz = d.slope7z
    inst = {"C1 d_pc": d.d_pc, "X1 int": d.d_pc * slz, "B0 d_dpw": d.d_dpw, "B0 d_dps": d.d_dps, "B1 w": d.c2w, "B1 s": d.c2s, "B2 iw": d.d_dpw * slz, "B2 is": d.d_dps * slz}
    Y = np.column_stack([np.asarray(v, float) for v in inst.values()])
    Rz = dict(zip(inst, N.gb_resid(Y, X, blocks, d.date.to_numpy()).T))
    keep = [i for i in range(X.shape[1]) if i != 6]
    yp = N.gb_resid(np.asarray(d.d_lnL_7, float)[:, None], X[:, keep], blocks, d.date.to_numpy())[:, 0]
    dates = d.date.to_numpy()
    reg = np.where(d.date < "2021-07-01", "2019-21H1", "2021H2-23")
    yr, mo, hr = d.date.dt.year.to_numpy(), d.date.dt.month.to_numpy(), d.hour.to_numpy()
    season = np.select([np.isin(mo, [12, 1, 2]), np.isin(mo, [3, 4, 5]), np.isin(mo, [6, 7, 8])], ["DJF", "MAM", "JJA"], "SON")
    cells = {"regime 2019-21H1": reg == "2019-21H1", "regime 2021H2-23": reg == "2021H2-23"}
    h1 = reg == "2019-21H1"
    cells |= {f"H1 year {y}": h1 & (yr == y) for y in (2019, 2020, 2021)}
    cells |= {f"H1 season {s}": h1 & (season == s) for s in ("DJF", "MAM", "JJA", "SON")}
    cells |= {f"H1 hours {n}": h1 & m for n, m in (("night 0-7", hr <= 7), ("day 8-17", (hr >= 8) & (hr <= 17)), ("evening 18-23", hr >= 18))}
    rows = []
    for name, z in Rz.items():
        for cn, m in cells.items():
            b, t, n = rf(yp, z, m, dates)
            rows.append(dict(instrument=name, cell=cn, n=n, coef=b, t=t))
    P = pd.DataFrame(rows)
    P.round(4).to_csv(T.OUT / "industry_iv_placebo_diagnostic.csv", index=False)
    drivers = {"d_dem": d.d_dem, "d_temp": d.d_temp, "d_out_planned": d.d_out_planned, "d_out_fault": d.d_out_fault, "slope7z": slz}
    cr = []
    for name, v in inst.items():
        for rg in ("2019-21H1", "2021H2-23"):
            m = reg == rg
            row = dict(instrument=name, regime=rg, sd=float(np.nanstd(np.asarray(v)[m])))
            for dn, dv in drivers.items():
                row[f"corr_{dn}"] = float(np.corrcoef(np.asarray(v, float)[m], np.asarray(dv, float)[m])[0, 1])
            cr.append(row)
    Cc = pd.DataFrame(cr)
    Cc.round(4).to_csv(T.OUT / "industry_iv_placebo_diagnostic_corr.csv", index=False)
    # leave-driver-out: residualise each instrument on the driver most correlated with it in 2019-21H1
    lo = []
    for name, z in Rz.items():
        c = Cc[(Cc.instrument == name) & (Cc.regime == "2019-21H1")].iloc[0]
        dn = max(drivers, key=lambda k: abs(c[f"corr_{k}"]))
        dv = np.asarray(drivers[dn], float)
        dv = dv - dv.mean()
        zr = z - dv * (dv @ z) / (dv @ dv)
        b0, t0, _ = rf(yp, z, h1, dates)
        b1, t1, _ = rf(yp, zr, h1, dates)
        lo.append(dict(instrument=name, driver=dn, corr=float(c[f"corr_{dn}"]), t_unadjusted=t0, t_adjusted=t1))
    L = pd.DataFrame(lo)
    L.round(4).to_csv(T.OUT / "industry_iv_placebo_diagnostic_leave_driver_out.csv", index=False)
    pd.set_option("display.width", 250, "display.max_rows", 200)
    print(P.pivot(index="cell", columns="instrument", values="t").round(2).to_string())
    print(Cc.round(3).to_string(index=False))
    print(L.round(3).to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
