"""Estimation of the medium-firm period-calendar design (docs/specs/2026-11-23-medium-firms-period-calendar-design.md).

    .venv/bin/python scripts/analysis/mf_period_calendar_estimate.py

Runs after step zero passed (33bea3a: M1 stand-in failed, so placebo summers = 2014, 2017, 2018, 2019; S = 4).
Treated summer 2021 (working days 1 Jun - 30 Sep), E1+E2 = ESIOS 1202+1203. Per-year raw OLS on 120 cells
s_Y(c) = alpha_Y(h) + b_Y d(c); effect = b_2021 - m. Rules E1-E8 as registered; E5 coincides with E1 (no stand-in).
E8 price share: REN Spanish day-ahead price (data/ren/ren_market_prices.parquet, series ES) through UTC to local
hours; share = hourly price / daily mean, computed on days whose mean price is above 1 EUR/MWh (others left out of
the share only), averaged over the cell. Writes outputs/tables/mf_period_calendar_estimate{,_summary}.csv. Deterministic.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mf_period_calendar_step0 as M0  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = TS.ROOT / "outputs" / "tables"
PLACEBO = [2014, 2017, 2018, 2019]
R = 2021
SBAR, DBAR, DBAR_NOFE = 107.2309, 0.1049, 0.1112   # step zero (33bea3a)


def price_share():
    p = pd.read_parquet(TS.ROOT / "data/ren/ren_market_prices.parquet")
    p = p[p.series == "ES"].drop_duplicates("utc_timestamp").sort_values("utc_timestamp")
    # Before 2018 REN sends each day's 24 hourly prices twice on a 30-minute grid (46/48/50 rows a day); the
    # utc_timestamp of those rows is not the hour. Rebuild the hourly series from each local day's sequence.
    rows = []
    for day, v in p.groupby("local_date").value:
        v = v.to_numpy()
        n = len(v)
        if n in (46, 48, 50):
            assert (v[: n // 2] == v[n // 2:]).all(), day
            v = v[: n // 2]
        t0 = pd.Timestamp(str(day)).tz_localize("Europe/Madrid").tz_convert("UTC")
        rows += [(t0 + pd.Timedelta(hours=i), x) for i, x in enumerate(v)]
    u = pd.DataFrame(rows, columns=["utc", "p"])
    loc = u.utc.dt.tz_convert("Europe/Madrid")
    d = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "p": u.p.to_numpy()})
    d = d.drop_duplicates(["date", "hour"])
    mean = d.groupby("date").p.transform("mean")
    d = d[mean > 1.0].copy()
    d["ps"] = d.p / d.groupby("date").p.transform("mean")
    return d[["date", "hour", "ps"]]


def year_cells(x, y, hol, dc, ps, split_sep=False):
    f, cov = M0.summer(x, y, hol)
    if split_sep:
        f["part"] = np.where((f.date.dt.month == 9) & (f.date.dt.day >= 16), "09b", f.part)
    f = f.merge(ps, on=["date", "hour"], how="left")
    c = f.groupby(["part", "hour"]).agg(s=("s", "mean"), ps=("ps", "mean")).reset_index()
    dd = dc.reset_index()
    if split_sep:
        dd = pd.concat([dd, dd[dd.part == "09"].assign(part="09b")])
    c = c.merge(dd, on=["part", "hour"], how="left")
    assert c.d.notna().all()
    return c, cov


def fit(c, fe=True, extra=None):
    cols = [(c.hour.to_numpy() == h).astype(float) for h in sorted(c.hour.unique())] if fe else [np.ones(len(c))]
    cols.append(c.d.to_numpy())
    if extra:
        cols.append(c[extra].to_numpy())
    X = np.column_stack(cols)
    coef = np.linalg.lstsq(X, c.s.to_numpy(), rcond=None)[0]
    return float(coef[len(cols) - 1 - (1 if extra else 0)])


def test(bR, pl, years):
    pl, years = np.asarray(pl, float), np.asarray(years, float)
    S = len(pl)
    m, s = pl.mean(), pl.std(ddof=1)
    se = s * np.sqrt(1 + 1 / S)
    t = (bR - m) / se
    p = stats.t.cdf(t, S - 1)
    q = stats.t.ppf(0.975, S - 1)
    out = dict(S=S, b_R=bR, m=m, s=s, effect=bR - m, t=t, p_mean=p, lo=bR - m - q * se, hi=bR - m + q * se,
               p_rank=(1 + int((pl <= bR).sum())) / (S + 1))
    if S >= 3:
        slope, icpt = np.polyfit(years, pl, 1)
        resid = pl - (icpt + slope * years)
        s_e = np.sqrt((resid ** 2).sum() / (S - 2))
        se_p = s_e * np.sqrt(1 + 1 / S + (R - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum())
        yhat = icpt + slope * R
        out.update(yhat=yhat, effect_trend=bR - yhat, p_trend=stats.t.cdf((bR - yhat) / se_p, S - 2),
                   lo_trend=bR - yhat - stats.t.ppf(0.975, S - 2) * se_p, hi_trend=bR - yhat + stats.t.ppf(0.975, S - 2) * se_p)
    return out


def main():
    pd.set_option("display.width", 240)
    hol = TS.holidays()
    dc = M0.d_cells(hol)
    x = CT.esios_load([1202, 1203])
    ps = price_share()
    C = {}
    for y in PLACEBO + [R]:
        C[y], cov = year_cells(x, y, hol, dc, ps)
        assert len(C[y]) == 120 and cov >= 0.99, (y, cov)
        assert C[y].ps.notna().all(), y
    nps = {y: int(C[y].ps.isna().sum()) for y in C}

    def stat(fun):
        return {y: fun(C[y]) for y in PLACEBO + [R]}

    rows = {}
    main_b = stat(lambda c: fit(c))
    rows["main (hour FE)"] = test(main_b[R], [main_b[y] for y in PLACEBO], PLACEBO)
    for y in PLACEBO:  # E4
        keep = [z for z in PLACEBO if z != y]
        rows[f"E4 without {y}"] = test(main_b[R], [main_b[z] for z in keep], keep)
    for name, drop in (("E6 without August", ["08"]), ("E6b without late June", ["06b"]), ("E6c without July", ["07"])):
        b = stat(lambda c, drop=drop: fit(c[~c.part.isin(drop)]))
        rows[name] = test(b[R], [b[y] for y in PLACEBO], PLACEBO)
    # E7 wrong hours: hours 1-4, fake d = mean d over hours 8-23 of the part
    fake = dc.reset_index().query("hour >= 8").groupby("part").d.mean()
    b7 = stat(lambda c: fit(c[c.hour.between(1, 4)].assign(d=lambda z: z.part.map(fake))))
    rows["E7 wrong hours 1-4"] = test(b7[R], [b7[y] for y in PLACEBO], PLACEBO)
    b8 = stat(lambda c: fit(c, extra="ps"))
    rows["E8 price-share control"] = test(b8[R], [b8[y] for y in PLACEBO], PLACEBO)
    bi = stat(lambda c: fit(c, fe=False))
    rows["industry form (no FE)"] = test(bi[R], [bi[y] for y in PLACEBO], PLACEBO)
    Csep = {y: year_cells(x, y, hol, dc, ps, split_sep=True)[0] for y in PLACEBO + [R]}
    bs = {y: fit(Csep[y]) for y in Csep}
    rows["September split at 16th"] = test(bs[R], [bs[y] for y in PLACEBO], PLACEBO)

    T = pd.DataFrame(rows).T
    mn = rows["main (hour FE)"]
    rules = {
        "E1 detection (p<=0.05, effect<0)": mn["effect"] < 0 and mn["p_mean"] <= 0.05,
        "E2 rank (below all placebo)": mn["p_rank"] == 1 / (len(PLACEBO) + 1),
        "E3 trend null (p<=0.10, effect<0)": mn["effect_trend"] < 0 and mn["p_trend"] <= 0.10,
        "E4 leave-one-out (all p<=0.10)": all(rows[f"E4 without {y}"]["p_mean"] <= 0.10 for y in PLACEBO),
        "E5 without stand-in (= E1 sample; p<=0.10)": mn["effect"] < 0 and mn["p_mean"] <= 0.10,
        "E6 without August keeps sign": np.sign(rows["E6 without August"]["effect"]) == np.sign(mn["effect"]),
        "E6b without late June keeps sign": np.sign(rows["E6b without late June"]["effect"]) == np.sign(mn["effect"]),
        "E6c without July keeps sign": np.sign(rows["E6c without July"]["effect"]) == np.sign(mn["effect"]),
        # b_R below the placebo prediction interval's lower bound m - q*se  <=>  effect + q*se < 0  <=>  hi < 0
        "E7 wrong hours not below lower 95% bound": not (rows["E7 wrong hours 1-4"]["hi"] < 0),
        "E8 price control: same sign, inside main interval": (np.sign(rows["E8 price-share control"]["effect"]) == np.sign(mn["effect"]))
        and (mn["lo"] <= rows["E8 price-share control"]["effect"] <= mn["hi"]),
    }
    sig_wrong = mn["effect"] > 0 and (1 - mn["p_mean"]) <= 0.05
    T.to_csv(OUT / "mf_period_calendar_estimate.csv")
    pd.DataFrame([dict(rule=k, passed=bool(v)) for k, v in rules.items()]).to_csv(OUT / "mf_period_calendar_estimate_summary.csv", index=False)
    print("price-share cells missing by year:", nps)
    print("b by year (main):", {y: round(v, 4) for y, v in main_b.items()})
    print(T[["S", "b_R", "m", "s", "effect", "p_mean", "lo", "hi", "p_rank", "effect_trend", "p_trend", "lo_trend", "hi_trend"]].astype(float).round(4).to_string())
    print()
    for k, v in rules.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    print("significant wrong sign:", sig_wrong)
    eff = mn["effect"]
    print(f"\nElasticity equivalent: effect {eff:+.4f} pts/step -> {(eff / SBAR) / DBAR:+.3f} (interval {(mn['lo'] / SBAR) / DBAR:+.3f}, {(mn['hi'] / SBAR) / DBAR:+.3f});"
          f" trend null {(mn['effect_trend'] / SBAR) / DBAR:+.3f}; industry form {(rows['industry form (no FE)']['effect'] / SBAR) / DBAR_NOFE:+.3f}"
          f" (pts/step {rows['industry form (no FE)']['effect']:+.4f} vs large industry -1.0)")


if __name__ == "__main__":
    main()
