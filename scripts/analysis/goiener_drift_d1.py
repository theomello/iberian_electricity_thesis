"""D1 and F1-F3 of docs/specs/2026-11-17-goiener-placebo-drift-design.md (amendment 2026-11-16). No LASSO.

    .venv/bin/python scripts/analysis/goiener_drift_d1.py

Daily log(peak kWh) - log(off-peak kWh) of weekday non-holiday days in June 1 -> September 15 of 2018, 2019 and 2021, household means (>= 40 days in each window), changes 2018->2019 (drift19) and
2019->2021 (change21), each net of Portugal's (REN) change; E0 through the same transformation. Household-cluster bootstrap (2,000 draws, Portugal and E0 fixed). Dose 0.784 (households, Portugal) and
0.609 (E0 mix). eta_FD = change21 / dose; eta_FD_adj = (change21 - 2 drift19) / dose; D0 gate: |drift19 / 0.784| > 0.02 or interval excludes zero. Writes outputs/tables/goiener_drift_d1.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_noise as G  # noqa: E402
import tou_did as T  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT
PEAK = [10, 11, 12, 13, 18, 19, 20, 21]
WIN = {2018: ("2018-06-01", "2018-09-15"), 2019: ("2019-06-01", "2019-09-15"), 2021: ("2021-06-01", "2021-09-15")}
DOSE_H, DOSE_E0, NB = 0.784, 0.609, 2000


def window_mask(dates, y):
    a, b = WIN[y]
    return (dates >= a) & (dates <= b)


def household_means(wd, users):
    d = wd[wd.user.isin(users)].copy()
    d = d[(d.kwh_peak > 0) & (d.kwh_off > 0)]
    d["lr"] = np.log(d.kwh_peak) - np.log(d.kwh_off)
    M = {}
    for y in WIN:
        s = d[window_mask(d.date, y)].groupby("user").lr.agg(["mean", "count"])
        M[y] = s
    ok = [u for u in users if all(u in M[y].index and M[y].loc[u, "count"] >= 40 for y in WIN)]
    return pd.DataFrame({y: M[y].loc[ok, "mean"] for y in WIN}), ok


def agg_lr(x, load, holi):
    d = x[~x.date.isin(holi) & (x.date.dt.dayofweek < 5)].copy()
    d["per"] = np.where(d.hour.isin(PEAK), "peak", np.where(d.hour < 8, "off", "mid"))
    cnt = d.groupby("date").size()
    pv = d.pivot_table(index="date", columns="per", values=load, aggfunc="sum")
    pv = pv[cnt.reindex(pv.index) == 24]
    lr = np.log(pv.peak) - np.log(pv.off)
    return {y: float(lr[window_mask(lr.index, y)].mean()) for y in WIN}


def stats_for(M, ctrl, dose, rng, label):
    base = M.to_numpy()
    c19 = (ctrl[2019] - ctrl[2018])
    c21 = (ctrl[2021] - ctrl[2019])

    def est(b):
        m = b.mean(0)
        d19, d21 = (m[1] - m[0]) - c19, (m[2] - m[1]) - c21
        return d19, d21, d21 - 2 * d19, d21 - d19
    pt = est(base)
    boot = np.array([est(base[rng.integers(0, len(base), len(base))]) for _ in range(NB)])
    ci = np.percentile(boot, [2.5, 97.5], axis=0)
    names = ["drift19", "change21", "change21_minus_2drift", "change21_minus_1drift"]
    rows = []
    for k, nme in enumerate(names):
        rows.append(dict(sample=label, quantity=nme, value=pt[k], lo=ci[0, k], hi=ci[1, k], eta=pt[k] / dose, eta_lo=ci[0, k] / dose, eta_hi=ci[1, k] / dose, n_households=len(base)))
    raw = pd.DataFrame(base.mean(0).reshape(1, -1), columns=["mean_2018", "mean_2019", "mean_2021"])
    return rows, raw, pt


def main():
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    daily["date"] = pd.to_datetime(daily.date)
    wd = daily[(daily.date.dt.dayofweek < 5) & ~daily.date.isin(hes)]
    # the G2 subsample, as in goiener_household.py
    pre = wd[wd.date < "2020-03-01"]
    win = wd[(wd.date >= "2021-06-01") & (wd.date <= "2021-09-15")]
    npre, nwin = pre.groupby("user").size(), win.groupby("user").size()
    imp = wd[wd.user.isin(win.user)].groupby("user").n_imputed.sum() / (24 * wd.groupby("user").size())
    g0 = (npre.reindex(meta.index).fillna(0) >= 250) & (nwin.reindex(meta.index).fillna(0) >= 60) & (imp.reindex(meta.index).fillna(1) <= 0.10)
    elig = meta.index[g0]
    rng = np.random.default_rng(G.SEED)
    e20 = [u for u in elig if meta.loc[u, "contracted_tariff"] == "2.0TD"]
    sub = list(rng.choice(e20, size=min(G.NSUB, len(e20)), replace=False))
    x = RI.D.prep(T.build("e0", end="2021-09-15"))
    pt, es = agg_lr(x, "load_pt", hpt), agg_lr(x, "load_es", hes)
    print("Portugal window mean log(peak/off):", {k: round(v, 4) for k, v in pt.items()}, "| E0:", {k: round(v, 4) for k, v in es.items()}, flush=True)
    rows, raws = [], []
    rb = np.random.default_rng(G.SEED + 1)
    for label, users in (("G2 subsample", sub), ("all eligible 2.0TD", e20)):
        M, ok = household_means(wd, users)
        r, raw, p = stats_for(M, pt, DOSE_H, rb, label)
        rows += r
        raw["sample"], raw["n"] = label, len(ok)
        raws.append(raw)
        print(f"{label}: {len(ok)} households with >= 40 days in all three windows", flush=True)
    # E0 through the same transformation (no household sampling: single series)
    c19, c21 = (es[2019] - es[2018]) - (pt[2019] - pt[2018]), (es[2021] - es[2019]) - (pt[2021] - pt[2019])
    rows.append(dict(sample="E0 aggregate", quantity="drift19", value=c19, eta=c19 / DOSE_E0))
    rows.append(dict(sample="E0 aggregate", quantity="change21", value=c21, eta=c21 / DOSE_E0))
    rows.append(dict(sample="E0 aggregate", quantity="change21_minus_2drift", value=c21 - 2 * c19, eta=(c21 - 2 * c19) / DOSE_E0))
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "goiener_drift_d1.csv", index=False)
    pd.set_option("display.width", 220)
    print(pd.concat(raws).round(4).to_string(index=False))
    print(R[["sample", "quantity", "value", "lo", "hi", "eta", "eta_lo", "eta_hi", "n_households"]].round(4).to_string(index=False))
    h = R[(R["sample"] == "G2 subsample") & (R.quantity == "drift19")].iloc[0]
    live = bool(abs(h.eta) > 0.02 or h.eta_lo > 0 or h.eta_hi < 0)
    print(f"D0 gate: household drift19 {h.eta:+.4f} [{h.eta_lo:+.4f}, {h.eta_hi:+.4f}] in elasticity units -> drift is {'a LIVE explanation, run D2/D3' if live else 'NOT live, D2/D3 not run'}", flush=True)


if __name__ == "__main__":
    main()
