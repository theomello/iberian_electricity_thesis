"""Step 3 of docs/specs/2026-11-26-tariff-drift-design.md: the placebo drift by tariff, mean null and trend null.

Cached errors only. For each of 6.2, 6.3, 6.4 (full regulated-price dose, series-specific fixed effects) and, as a check on
the trend-null formula, the pool: eta_2021, six placebo summers, slope, effect against the mean null and against the trend null
(Amendment A of the regulated-price design: straight line in year, S - 2 d.f.). Steps 1 and 2 are not implemented here.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_drift_location as DL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
COMMITTED = {"6.2": (-0.06369, 0.01955, 0.01684), "6.3": (-0.23291, 0.19751, 0.1808), "6.4": (-0.33676, 0.32562, 0.083)}


def nulls(real, pl):
    yrs = np.array(list(pl.keys()), float)
    v = np.array(list(pl.values()), float)
    S = len(v)
    m, sd = v.mean(), v.std(ddof=1)
    se_m = sd * np.sqrt(1 + 1 / S)
    qm = stats.t.ppf(0.975, S - 1)
    mean = dict(eff=real - m, p=float(stats.t.cdf((real - m) / se_m, S - 1)), lo=real - m - qm * se_m, hi=real - m + qm * se_m)
    xc = yrs - yrs.mean()
    b = (xc * v).sum() / (xc ** 2).sum()
    a = v.mean()
    res = v - (a + b * xc)
    se_e = np.sqrt((res ** 2).sum() / (S - 2))
    slope_se = se_e / np.sqrt((xc ** 2).sum())
    x0 = 2021 - yrs.mean()
    yhat = a + b * x0
    se_p = se_e * np.sqrt(1 + 1 / S + x0 ** 2 / (xc ** 2).sum())
    qt = stats.t.ppf(0.975, S - 2)
    trend = dict(yhat=yhat, eff=real - yhat, p=float(stats.t.cdf((real - yhat) / se_p, S - 2)),
                 lo=real - yhat - qt * se_p, hi=real - yhat + qt * se_p)
    return mean, trend, float(b), float(slope_se), float(m), float(sd)


def main():
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    tab = RP.tables(dates, RP.power_table(), "full", wp=wp)
    dp = {n: to_x(CT.series_dose(n, tab, ebar)) for n in RP.POOL}
    errs = S6.errors(x, clean)
    win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()

    def betas(names):
        res = {}
        for yr in [2021] + S6.SUMMERS:
            if yr == 2021:
                w, key, mask, rng = win21, "()", pre | pd.Series(win21, index=x.index), (S6.R0, S6.R1)
            else:
                a, b = S6.aligned(yr)
                w = ((x.date >= a) & (x.date <= b)).to_numpy()
                key, mask, rng = f"({yr},)", pre, (a, b)
            res[yr] = DL.eta_variant(x, errs, key, {n: np.where(w, dp[n], 0.0) for n in names}, mask, names, rng, "baseline")[0]
        return res

    rows, store = [], {}
    for tag, names in [("6.2", ["6.2"]), ("6.3", ["6.3"]), ("6.4", ["6.4"]), ("pool", RP.POOL)]:
        r = betas(names)
        pl = {k: v for k, v in r.items() if k != 2021}
        mean, trend, slope, slope_se, m, sd = nulls(r[2021], pl)
        store[tag] = dict(real=r[2021], m=m, sd=sd, slope=slope, slope_se=slope_se, mean=mean, trend=trend)
        rows.append(dict(series=tag, eta_2021=r[2021], placebo_mean=m, placebo_sd=sd, slope=slope, slope_se=slope_se,
                         mean_effect=mean["eff"], mean_p=mean["p"], mean_lo=mean["lo"], mean_hi=mean["hi"],
                         yhat_2021=trend["yhat"], trend_effect=trend["eff"], trend_p=trend["p"], trend_lo=trend["lo"], trend_hi=trend["hi"],
                         placebos=" ".join(f"{k}:{v:+.3f}" for k, v in pl.items())))
        print(tag, {k: round(v, 4) if isinstance(v, float) else v for k, v in rows[-1].items() if k != "placebos"}, rows[-1]["placebos"], flush=True)
        pd.DataFrame(rows).to_csv(OUT / "tou_tariff_drift_step3.csv", index=False)

    print("\nRULES")
    ok = True
    for k, (e, m, s) in COMMITTED.items():
        c = store[k]
        good = abs(c["real"] - e) < 0.0015 and abs(c["m"] - m) < 0.0015 and abs(c["sd"] - s) < 0.0015
        ok &= good
        print(f"T1 {k}: eta {c['real']:+.5f} (committed {e:+.5f}), mean {c['m']:+.5f} ({m:+.5f}), sd {c['sd']:.5f} ({s:.5f}) -> {'pass' if good else 'FAIL'}")
    p = store["pool"]
    print(f"   sanity, pool trend null (A2 committed: yhat -0.026, effect -0.151, p 0.044, [-0.337, +0.036]): "
          f"yhat {p['trend']['yhat']:+.3f} effect {p['trend']['eff']:+.3f} p {p['trend']['p']:.3f} [{p['trend']['lo']:+.3f}, {p['trend']['hi']:+.3f}]")
    if not ok:
        sys.exit("T1 failed: stop")
    for k in ("6.2", "6.3", "6.4"):
        c = store[k]
        est = c["slope"] < 0 and abs(c["slope"]) >= 1.5 * c["slope_se"]
        gap = abs(c["mean"]["eff"] - c["trend"]["eff"])
        settled = (not est) or gap <= 0.10
        print(f"{k}: T2 slope {c['slope']:+.4f} (se {c['slope_se']:.4f}) established {bool(est)} | "
              f"T3 mean effect {c['mean']['eff']:+.3f}, trend effect {c['trend']['eff']:+.3f}, gap {gap:.3f} -> "
              f"{'settled' if settled else 'NOT settled'} | T4 detected mean p {c['mean']['p']:.3f}, trend p {c['trend']['p']:.3f}")


if __name__ == "__main__":
    main()
