"""Corrected placebo errors for G5, G6 and Part B (replaces g_placebo_errors.parquet from goiener_save_errors.py, which trained its leave-year-out LASSO on the 2021 window days as well).

    .venv/bin/python scripts/analysis/goiener_save_placebo.py

Same 3,000-household 2.0TD subsample and LASSO as goiener_noise.py; the placebo model sees only pre-lockdown (< 2020-03-01) weekday days, exactly as in the registered step zero. Households are processed in chunks of 250
and each chunk is saved (data/goiener/daily/placebo_chunks/chunk_*.parquet), so an interrupted run resumes. Final file data/goiener/daily/g_placebo_errors_pre.parquet : user, date, peak, mid, off.
Window mid errors (g2_window_mid.parquet) were trained on pre-lockdown days only and are unchanged.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_household as GH  # noqa: E402
import goiener_noise as G  # noqa: E402
import tou_did as T  # noqa: E402

ROOT = T.ROOT
PERS = ("kwh_peak", "kwh_mid", "kwh_off")


def one(u, g, temp):
    g = g[g.date < "2020-03-01"].set_index("date").sort_index()
    pl = {per: G.errors_leave_year(np.log(g[per].where(g[per] > 0)).dropna(), temp) for per in PERS}
    if any(len(v) == 0 for v in pl.values()):
        return pd.DataFrame(columns=["user", "date", "peak", "mid", "off"])
    e = pd.concat(pl, axis=1).dropna()
    e.columns = ["peak", "mid", "off"]
    e["user"] = u
    e.index.name = "date"
    return e.reset_index()[["user", "date", "peak", "mid", "off"]]


def main():
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    daily["date"] = pd.to_datetime(daily.date)
    wd = daily[(daily.date.dt.dayofweek < 5) & ~daily.date.isin(hes)].copy()
    pre = wd[wd.date < "2020-03-01"]
    win = wd[(wd.date >= GH.W0) & (wd.date <= GH.W1)]
    npre, nwin = pre.groupby("user").size(), win.groupby("user").size()
    imp = wd[wd.user.isin(win.user)].groupby("user").n_imputed.sum() / (24 * wd.groupby("user").size())
    g0 = (npre.reindex(meta.index).fillna(0) >= 250) & (nwin.reindex(meta.index).fillna(0) >= 60) & (imp.reindex(meta.index).fillna(1) <= 0.10)
    elig = meta.index[g0]
    temps = G.daily_temps()
    rng = np.random.default_rng(G.SEED)
    e20 = [u for u in elig if meta.loc[u, "contracted_tariff"] == "2.0TD"]
    sub = list(rng.choice(e20, size=min(G.NSUB, len(e20)), replace=False))
    grp = {u: g for u, g in wd[wd.user.isin(sub)].groupby("user")}
    users = [u for u in sub if u in grp]
    d = ROOT / "data/goiener/daily/placebo_chunks"
    d.mkdir(exist_ok=True)
    for i in range(0, len(users), 250):
        f = d / f"chunk_{i // 250:02d}.parquet"
        if f.exists():
            continue
        res = Parallel(n_jobs=4, verbose=0)(delayed(one)(u, grp[u], temps[G.CITY[meta.loc[u, "province"]]]) for u in users[i:i + 250])
        pd.concat(res, ignore_index=True).to_parquet(f)
        print(f"chunk {i // 250 + 1} of {-(-len(users) // 250)} saved", flush=True)
    P = pd.concat([pd.read_parquet(f) for f in sorted(d.glob("chunk_*.parquet"))], ignore_index=True)
    P.to_parquet(ROOT / "data/goiener/daily/g_placebo_errors_pre.parquet")
    print(f"placebo errors (pre-only training): {len(P)} household-days from {P.user.nunique()} households", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
