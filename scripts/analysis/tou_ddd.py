"""Triple difference for the June 2021 time-of-use reform (docs/specs/2026-11-11-tou-hardening-design.md, step 2).

Outcome: ln load of Spain minus ln Portuguese load at the same local hour (E0 = measured low-voltage demand, ESIOS 1201, with --e0;
else ESIOS 352). Clock classes by hour (off 0-7, peak 10-13 and 18-21, mid the rest) on two kinds of days: working days (the policy's
peak and mid-peak apply) and weekends and national holidays (all off-peak under the policy; the same clock hours are 'fake'). Break
2021-06-01, window 2018-01-01 -> 2021-09-30. DiD: post x class x day kind with hour, weekday and month effects, clustered by week.
DDD = (peak - off, working days) - (peak - off, weekends); the same for mid. LASSO prediction errors (tou_did.lasso_errors) by class x
day kind give the same contrasts. Placebo breaks (V1 only): the 1st of each month 2019-01 -> 2020-12 whose 4-month window misses
March-June 2020. Writes outputs/tables/tou_ddd{,_e0}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_did as T  # noqa: E402

PEAK = [10, 11, 12, 13, 18, 19, 20, 21]


def prep(x):
    x = x.copy()
    x["cls"] = np.where(x.hour < 8, "off", np.where(x.hour.isin(PEAK), "peak", "mid"))
    x["kind"] = np.where(x.weekend, "wknd", "work")
    x["cell"] = x.cls + "_" + x.kind
    return x


def contrasts(b, V, names):
    def c(pairs):
        w = np.zeros(len(names))
        for n, s in pairs:
            w[names.index(n)] += s
        return w @ b, np.sqrt(w @ V @ w)
    return {"peak-off work": c([("post_peak_work", 1), ("post_off_work", -1)]), "peak-off wknd": c([("post_peak_wknd", 1), ("post_off_wknd", -1)]),
            "mid-off work": c([("post_mid_work", 1), ("post_off_work", -1)]), "mid-off wknd": c([("post_mid_wknd", 1), ("post_off_wknd", -1)]),
            "DDD peak": c([("post_peak_work", 1), ("post_off_work", -1), ("post_peak_wknd", -1), ("post_off_wknd", 1)]),
            "DDD mid": c([("post_mid_work", 1), ("post_off_work", -1), ("post_mid_wknd", -1), ("post_off_wknd", 1)])}


def did_ddd(x, brk, end):
    s = x[x.date <= end]
    post = (s.date >= brk).astype(float).to_numpy()
    cols = {f"post_{c}": post * (s.cell.to_numpy() == c) for c in ("peak_work", "mid_work", "off_work", "peak_wknd", "mid_wknd", "off_wknd")}
    cols = {k.replace("post_peak_work", "post_peak_work"): v for k, v in cols.items()}
    cols = {k: cols[k] for k in cols}
    ren = {"post_peak_work": "post_peak_work", "post_mid_work": "post_mid_work", "post_off_work": "post_off_work",
           "post_peak_wknd": "post_peak_wknd", "post_mid_wknd": "post_mid_wknd", "post_off_wknd": "post_off_wknd"}
    base = [T.dummies(s, ["hour", "dow", "month"]), pd.get_dummies(s.cell, drop_first=True, dtype=float)]
    X = pd.concat(base + [pd.DataFrame({k: v for k, v in cols.items()}, index=s.index)], axis=1)
    X = X.loc[:, X.std() > 0]
    X.insert(0, "const", 1.0)
    Xv, yv = X.to_numpy(), s.d.to_numpy()
    b = np.linalg.pinv(Xv) @ yv
    e = yv - Xv @ b
    V = T.hac_cluster(Xv, e, s.date.dt.to_period("W").astype(str).factorize()[0])
    return contrasts(b, V, list(X.columns))


def lasso_ddd(x, brk, end):
    p = T.lasso_errors(x, brk, end)
    p["cell"] = x.loc[p.index, "cell"]
    g = p.date.dt.to_period("W").astype(str).factorize()[0]
    D = pd.get_dummies(p.cell, dtype=float)
    Xv = D.to_numpy()
    b = np.linalg.pinv(Xv) @ p.err_d.to_numpy()
    e = p.err_d.to_numpy() - Xv @ b
    V = T.hac_cluster(Xv, e, g)
    names = [f"post_{c}" for c in D.columns]
    return contrasts(b, V, names)


def main():
    e0 = "--e0" in sys.argv
    x = prep(T.build("e0" if e0 else "352"))
    rows = []
    r = did_ddd(x, T.BREAK, T.END)
    for k, (b, se) in r.items():
        rows.append(dict(est="DiD V1 (hour, weekday, month effects)", contrast=k, effect_pct=100 * b, se_pct=100 * se, t=b / se))
    l = lasso_ddd(x, T.BREAK, T.END)
    for k, (b, se) in l.items():
        rows.append(dict(est="LASSO errors", contrast=k, effect_pct=100 * b, se_pct=100 * se, t=b / se))
    pl = []
    for b0 in pd.date_range("2019-01-01", "2020-12-01", freq="MS"):
        end = b0 + pd.DateOffset(months=4) - pd.Timedelta(days=1)
        if end >= pd.Timestamp("2020-03-01") and b0 <= pd.Timestamp("2020-06-30"):
            continue
        rr = did_ddd(x, b0, end)
        pl.append(dict(break_date=b0.date(), ddd_peak=100 * rr["DDD peak"][0], ddd_mid=100 * rr["DDD mid"][0], peak_off_work=100 * rr["peak-off work"][0]))
    pl = pd.DataFrame(pl)
    tag = "_e0" if e0 else ""
    out = pd.DataFrame(rows)
    out.round(3).to_csv(T.OUT / f"tou_ddd{tag}.csv", index=False)
    pl.round(3).to_csv(T.OUT / f"tou_ddd{tag}_placebo.csv", index=False)
    pd.set_option("display.width", 200)
    print(("E0" if e0 else "ESIOS 352"), "\n", out.round(2).to_string(index=False))
    for col, real in (("ddd_peak", r["DDD peak"][0] * 100), ("peak_off_work", r["peak-off work"][0] * 100)):
        s = pl[col]
        print(f"{col}: real {real:+.2f}; {len(s)} placebos sd {s.std():.2f}, 5-95% [{s.quantile(.05):+.2f}, {s.quantile(.95):+.2f}], rank by |.| {int((s.abs() >= abs(real)).sum()) + 1} of {len(s) + 1}")


if __name__ == "__main__":
    main()
