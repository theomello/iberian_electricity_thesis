"""Step 1 of docs/specs/2026-11-26-tariff-drift-design.md: a trend term in the regression, per tariff.

    tou_tariff_drift_step1.py 6.3 [6.4 ...]     # tariffs with an established trend (T2) from Step 3

Cached errors only. Stack: for each placebo year Y the rows of year Y from the model that left Y out (errs[(k, "(Y,)")]),
for 2021 the window rows from errs[(k, "()")]; Spain and Portugal blocks, fixed effects as the baseline (fe3, year-month
unique). Regressors, each laid on its own year's aligned window: dose, dose x (year - 2021), dose x 1{2021}.
alpha = no-reform drift value at 2021, gamma = trend per year, theta = reform effect against the trend null.
Week-clustered standard errors. J1 (gamma = 0 reduces to the mean null), J2 (agrees with Step 3's trend null), J3 (leave one
placebo summer out).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT


def build_stack(x, errs, pre, k, dpk, drop=None):
    parts = []
    for yr in [2021] + S6.SUMMERS:
        if yr == drop:
            continue
        if yr == 2021:
            a, b = S6.R0, S6.R1
            mask = (x.date >= a) & (x.date <= b)
            key = "()"
        else:
            a, b = S6.aligned(yr)
            mask = pre & (x.date.dt.year == yr)
            key = f"({yr},)"
        st = CT.make_stack(x, errs[(k, key)], errs[("PT", key)], "PT", mask)
        inwin = ((st.date >= a) & (st.date <= b)).to_numpy()
        spain = st.area.to_numpy() == 0
        d = np.where(spain & inwin, dpk[st.src.to_numpy()], 0.0)
        st["year"] = yr
        st["d0"], st["d1"], st["d2"] = d, d * (yr - 2021), d * float(yr == 2021)
        parts.append(st)
    s = pd.concat(parts, ignore_index=True)
    return s


def fit(s, cols):
    F = CT.fe3(s)
    y = CT.EL.resid(F, s.e)
    X = np.column_stack([CT.EL.resid(F, s[c].to_numpy()) for c in cols])
    g = pd.factorize(s.date.dt.to_period("W").astype(str))[0]
    b, V, G = CT.ols_cl(y, X, g)
    return b, np.sqrt(np.diag(V)), G


def main():
    tariffs = [a for a in sys.argv[1:] if not a.startswith("-")]
    assert tariffs, "name the tariffs with an established trend"
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    tab = RP.tables(dates, RP.power_table(), "full", wp=wp)
    errs = S6.errors(x, clean)
    step3 = pd.read_csv(OUT / "tou_tariff_drift_step3.csv").set_index("series")
    rows = []
    for k in tariffs:
        dpk = np.nan_to_num(CT.series_dose(k, tab, ebar).reindex(idx).to_numpy())
        s = build_stack(x, errs, pre, k, dpk)
        b, se, G = fit(s, ["d0", "d1", "d2"])
        b0, se0, _ = fit(s, ["d0", "d2"])  # gamma fixed at 0
        theta, th_se = b[2], se[2]
        p = float(stats.norm.cdf(theta / th_se))
        j1 = abs(b0[1] - step3.loc[k, "mean_effect"])
        j2 = abs(theta - step3.loc[k, "trend_effect"])
        loo = []
        for y in S6.SUMMERS:
            bb, _, _ = fit(build_stack(x, errs, pre, k, dpk, drop=y), ["d0", "d1", "d2"])
            loo.append(float(bb[2]))
        j3 = all(np.sign(v) == np.sign(theta) and abs(v - theta) <= 0.10 for v in loo)
        r = dict(tariff=k, alpha=b[0], alpha_se=se[0], gamma=b[1], gamma_se=se[1], theta=theta, theta_se=th_se, theta_p=p,
                 theta_lo=theta - 1.96 * th_se, theta_hi=theta + 1.96 * th_se, theta_gamma0=b0[1], clusters=G,
                 step3_mean_effect=step3.loc[k, "mean_effect"], step3_trend_effect=step3.loc[k, "trend_effect"],
                 J1_gap=j1, J2_gap=j2, J3_pass=j3, loo=" ".join(f"{y}:{v:+.3f}" for y, v in zip(S6.SUMMERS, loo)))
        rows.append(r)
        print(k, {a: (round(v, 4) if isinstance(v, float) else v) for a, v in r.items()}, flush=True)
        print(f"  J1 theta(gamma=0) {b0[1]:+.4f} vs Step 3 mean-null {step3.loc[k, 'mean_effect']:+.4f}: gap {j1:.4f} <= 0.01: {bool(j1 <= 0.01)}")
        print(f"  J2 theta {theta:+.4f} vs Step 3 trend-null {step3.loc[k, 'trend_effect']:+.4f}: gap {j2:.4f} <= 0.03: {bool(j2 <= 0.03)}")
        print(f"  J3 leave-one-summer-out theta {[round(v, 3) for v in loo]} -> {bool(j3)}")
        pd.DataFrame(rows).to_csv(OUT / "tou_tariff_drift_step1.csv", index=False)


if __name__ == "__main__":
    main()
