"""Step zero of the firm calendar persistence design (docs/specs/2026-11-23-firm-calendar-persistence-design.md).

    .venv/bin/python scripts/analysis/firm_persistence_step0.py

Sealed: E1+E2 (1202+1203) and 6.2/6.3/6.4 (1216-1218) are cut at 2019-12-31 right after loading (asserted on the
filtered frame); post-year coverage (2022-2025) is counted from the timestamp column only, no load value is read.
Z0 data and E1+E2 volume, Z1 reproduction (medium-firm summer b; large-industry E6 placebo slopes), Z2 Part B
decision (s_B <= 0.8 s_A per group). Prints placebo b, m, s, trend and MDEs for every statistic the rules use, and the
large-industry dose per step. Writes outputs/tables/firm_persistence_step0{,_years}.csv. Deterministic.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mf_period_calendar_step0 as MF  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_industry_regulated_price as IR  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

ROOT = TS.ROOT
OUT = ROOT / "outputs" / "tables"
SEAL = pd.Timestamp("2019-12-31")
E_PRICE = 100.81
K = 4
POST = [2022, 2023, 2024, 2025]
GROUPS = {
    "medium": dict(series={"E1+E2": [1202, 1203]}, tariff="6.1", years=[2014, 2017, 2018, 2019], fe=True),
    "large": dict(series={"6.2": [1216], "6.3": [1217], "6.4": [1218]}, tariff=None, years=[2014, 2015, 2016, 2017, 2018, 2019], fe=False),
}
MF_REGISTERED = {2014: 0.2277, 2017: 0.2929, 2018: 0.1773, 2019: 0.2334}
SOLAR = set(range(10, 18))


def holy_days(years):
    out = set()
    for y in years:
        e = pd.Timestamp(easter(y))
        out |= {e - pd.Timedelta(days=3), e - pd.Timedelta(days=2), e + pd.Timedelta(days=1)}
    return out


def working(dates, hol):
    d = pd.DatetimeIndex(dates)
    return (d.dayofweek < 5) & ~d.isin(list(hol)) & ~((d.month == 1) & (d.day == 6))


def part_of(dates, june_split):
    d = pd.DatetimeIndex(dates)
    mm = pd.Series(d.month).astype(str).str.zfill(2).to_numpy()
    if not june_split:
        return mm
    return np.where(d.month == 6, np.where(d.day <= 15, "06a", "06b"), mm)


def load(ids):
    x = CT.esios_load(ids)
    x = x[x.date <= SEAL].copy()
    assert x.date.max() <= SEAL
    return x


def post_rowcount(ids):
    """Hours present in each post year's June-September and calendar year, from timestamps only (no values)."""
    out = {}
    for i in ids:
        t = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet", columns=["utc_timestamp"]).drop_duplicates("utc_timestamp")
        loc = pd.to_datetime(t.utc_timestamp, utc=True).dt.tz_convert("Europe/Madrid")
        for y in POST:
            yr = loc[loc.dt.year == y]
            out[(i, y)] = (int(yr.dt.month.between(6, 9).sum()), int(len(yr)))
    return out


def d_table(tariff, dates, hol, june_split):
    s = TS.schedule(dates)
    s = s[(s.tariff == tariff)].copy()
    s = s[working(s.date, hol)]
    s["d"] = s.old_period - s.new_period
    s["part"] = part_of(s.date, june_split)
    return s.groupby(["part", "hour"]).d.mean()


def frame(x, d0, d1, hol, months):
    f = x[(x.date >= d0) & (x.date <= d1) & x.date.dt.month.isin(months)].copy()
    n = f.groupby("date").v.count()
    f = f[f.date.isin(n[n == 24].index)]
    f = f[working(f.date, hol)]
    f["s"] = 100 * f.v / f.groupby("date").v.transform("mean")
    return f


def cells(f, dt, june_split, series):
    f = f.assign(part=part_of(f.date, june_split))
    c = f.groupby(["part", "hour"]).s.mean().rename("s").reset_index()
    c["d"] = [dt.get((p, h), np.nan) for p, h in zip(c.part, c.hour)]
    assert c.d.notna().all()
    c["series"] = series
    return c


def fit(c, form):
    """form: 'fe' hour effects (series x hour for pooled), 'int' one intercept."""
    if form == "fe":
        key = c.series.astype(str) + "|" + c.hour.astype(str)
        X = np.column_stack([(key == k).astype(float).to_numpy() for k in sorted(key.unique())] + [c.d.to_numpy()])
    else:
        X = np.column_stack([np.ones(len(c)), c.d.to_numpy()])
    return float(np.linalg.lstsq(X, c.s.to_numpy(), rcond=None)[0][-1])


def variants(c, main_form):
    """Every statistic the rules use, as (name, cells, form)."""
    fake = c[c.hour.between(8, 23)].groupby(["series", "part"]).d.mean()
    w = c[c.hour.between(1, 4)].copy()
    w["d"] = [fake[(s, p)] for s, p in zip(w.series, w.part)]
    other = "int" if main_form == "fe" else "fe"
    return {
        "main": (c, main_form),
        "solar_robust": (c[~c.hour.isin(SOLAR)], main_form),
        "no_august": (c[c.part != "08"], main_form),
        "wrong_hours_1_4": (w, "fe"),
        f"other_form_{other}": (c, other),
    }


def summarize(bs, years):
    bs, years = np.asarray(bs, float), np.asarray(years, float)
    S = len(bs)
    m, s = bs.mean(), bs.std(ddof=1)
    slope, icpt = np.polyfit(years, bs, 1)
    s_e = np.sqrt(((bs - (icpt + slope * years)) ** 2).sum() / (S - 2))
    ypost = np.mean(POST)
    se_tr = s_e * np.sqrt(1 / K + 1 / S + (ypost - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum())
    q = lambda df, a: stats.t.ppf(a, df)
    return dict(S=S, m=m, s=s, trend_slope=slope, s_e=s_e,
                mde_mean=(q(S - 1, .95) + q(S - 1, .80)) * s * np.sqrt(1 / K + 1 / S),
                mde_conservative=(q(S - 1, .95) + q(S - 1, .80)) * s * np.sqrt(1 + 1 / S),
                mde_trend=(q(S - 2, .90) + q(S - 2, .80)) * se_tr)


def e6_reference(placebo, hol):
    """tou_industry_regulated_price E6 logic, placebo years only: fraction shares, LOO-centred slopes."""
    sched = TS.schedule(pd.date_range("2021-06-01", "2021-09-30"))
    rk = sched[(sched.date.dt.dayofweek < 5) & ~sched.date.isin(hol)].assign(m=lambda d: d.date.dt.month, d_rank=lambda d: d.old_period - d.new_period)
    rk = rk.groupby(["tariff", "m", "hour"]).d_rank.mean()
    cl = []
    for n, ids in (("6.2", [1216]), ("6.3", [1217]), ("6.4", [1218])):
        d = load(ids)
        d = d[(d.date.dt.dayofweek < 5) & ~d.date.isin(hol) & d.date.dt.month.between(6, 9)]
        d = d.assign(s=d.v / d.groupby("date").v.transform("mean"), y=d.date.dt.year, m=d.date.dt.month)
        c = d.groupby(["y", "m", "hour"]).s.mean().unstack("y")
        c["d_rank"] = [rk.get((n, m, h), np.nan) for m, h in c.index]
        cl.append(c)
    C = pd.concat(cl)
    X = np.c_[np.ones(len(C)), C.d_rank]
    return {y: float(np.linalg.lstsq(X, (C[y] - C[[o for o in placebo if o != y]].mean(axis=1)).to_numpy(), rcond=None)[0][1]) for y in placebo}


def large_dose(hol):
    dates = pd.date_range("2021-06-01", "2021-09-30")
    tabs = IR.tables(dates, IR.power_table(), "full")
    rows = []
    for tar in ("6.2", "6.3", "6.4"):
        t = tabs[tar].reset_index()
        t = t[working(t.date, hol)]
        sch = TS.schedule(dates)
        sch = sch[(sch.tariff == tar)][["date", "hour", "old_period", "new_period"]]
        t = t.merge(sch, on=["date", "hour"])
        t["dlnp"] = np.log((E_PRICE + t.new_price) / (E_PRICE + t.old_price))
        t["d"] = t.old_period - t.new_period
        t["m"] = t.date.dt.month
        rows.append(t.groupby(["m", "hour"])[["dlnp", "d"]].mean().reset_index())
    c = pd.concat(rows)
    X = np.c_[np.ones(len(c)), c.d]
    return float(np.linalg.lstsq(X, c.dlnp.to_numpy(), rcond=None)[0][1])


def main():
    pd.set_option("display.width", 250)
    hol = TS.holidays()
    allyears = list(range(2014, 2027))
    holy = holy_days(allyears)
    drop = hol | holy | {pd.Timestamp(f"{y}-01-01") for y in allyears}
    years_rows, summ, gates = [], [], {}

    # d tables: Part A 2021 summer calendar; Part B 2022 calendar year (holy days and 1 Jan excluded)
    dA = pd.date_range("2021-06-01", "2021-09-30")
    dB = pd.DatetimeIndex([d for d in pd.date_range("2022-01-01", "2022-12-31") if d not in holy and not (d.month == 1 and d.day == 1)])

    for g, spec in GROUPS.items():
        tar_of = (lambda n: spec["tariff"]) if spec["tariff"] else (lambda n: n)
        june_split = g == "medium"
        main_form = "fe" if spec["fe"] else "int"
        loads = {n: load(ids) for n, ids in spec["series"].items()}
        # Z0 coverage and E1+E2 volume
        cov_ok = True
        for n, x in loads.items():
            for y in spec["years"]:
                for mth in range(1, 13):
                    exp = pd.Period(f"{y}-{mth:02d}").days_in_month * 24
                    got = int(((x.date.dt.year == y) & (x.date.dt.month == mth)).sum())
                    if got < 0.99 * exp - 2:  # clock-change months have +-1 hour
                        cov_ok = False
                        print(f"Z0 coverage short: {g} {n} {y}-{mth:02d} {got}/{exp}")
        if g == "medium":
            x = loads["E1+E2"]
            mon = x.assign(y=x.date.dt.year, mm=x.date.dt.month).groupby(["y", "mm"]).v.sum().unstack("y")
            ratio = mon[spec["years"]].div(mon[[2017, 2018, 2019]].mean(axis=1), axis=0)
            vol_ok = bool(((ratio - 1).abs() <= 0.15).all().all())
            print("Z0 E1+E2 volume (month / 2017-19 mean), min/max by year:", {y: (round(ratio[y].min(), 3), round(ratio[y].max(), 3)) for y in spec["years"]}, "->", "pass" if vol_ok else "FAIL")
            gates["Z0_volume_medium"] = vol_ok
        gates[f"Z0_coverage_{g}"] = cov_ok
        prc = post_rowcount([i for ids in spec["series"].values() for i in ids])
        print(f"Z0 post-year rows ({g}; Jun-Sep, calendar year):", prc)

        for part, (dts, months, cal) in {"A": (dA, [6, 7, 8, 9], "summer"), "B": (dB, list(range(1, 13)), "calendar")}.items():
            dts_ = {n: d_table(tar_of(n), dts, hol | holy, june_split) for n in loads}
            per = {}
            for y in spec["years"]:
                d0, d1 = (pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-30")) if part == "A" else (pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31"))
                cl = [cells(frame(x, d0, d1, drop, months), dts_[n], june_split, n) for n, x in loads.items()]
                per[y] = pd.concat(cl, ignore_index=True)
            for vname in variants(per[spec["years"][0]], main_form):
                bs = []
                for y in spec["years"]:
                    cc, form = variants(per[y], main_form)[vname]
                    b = fit(cc, form)
                    bs.append(b)
                    years_rows.append(dict(group=g, part=part, statistic=vname, year=y, b=b))
                summ.append(dict(group=g, part=part, statistic=vname, **summarize(bs, spec["years"])))

        # Z1 reproduction
        if g == "medium":
            got = {r["year"]: r["b"] for r in years_rows if r["group"] == "medium" and r["part"] == "A" and r["statistic"] == "main"}
            z1 = all(abs(got[y] - v) <= 1e-4 for y, v in MF_REGISTERED.items())
            print("Z1 medium summer b:", {y: round(v, 4) for y, v in got.items()}, "registered", MF_REGISTERED, "->", "pass" if z1 else "FAIL")
        else:
            raw = {r["year"]: r["b"] for r in years_rows if r["group"] == "large" and r["part"] == "A" and r["statistic"] == "main"}
            loo = {y: (raw[y] - np.mean([raw[o] for o in raw if o != y])) / 100 for y in raw}
            ref = e6_reference(spec["years"], hol)
            z1 = all(abs(loo[y] - ref[y]) <= 1e-6 for y in ref)
            print("Z1 large LOO slopes vs E6 logic:", {y: (round(loo[y], 6), round(ref[y], 6)) for y in ref}, "->", "pass" if z1 else "FAIL")
        gates[f"Z1_{g}"] = z1

    S = pd.DataFrame(summ)
    for g in GROUPS:
        sA = float(S[(S.group == g) & (S.part == "A") & (S.statistic == "main")].s.iloc[0])
        sB = float(S[(S.group == g) & (S.part == "B") & (S.statistic == "main")].s.iloc[0])
        gates[f"Z2_partB_{g}"] = sB <= 0.8 * sA
        print(f"Z2 {g}: s_A {sA:.4f}, s_B {sB:.4f}, ratio {sB / sA:.3f} (bar 0.8) -> Part B {'GOES AHEAD' if sB <= 0.8 * sA else 'does not go ahead'}")
    dbar = large_dose(hol)
    print(f"large-industry dose per step (summer cells, intercept, full dose 2021, E={E_PRICE}): {dbar:.4f}")

    Y = pd.DataFrame(years_rows)
    Y.to_csv(OUT / "firm_persistence_step0_years.csv", index=False)
    S.assign(dbar_large=dbar).to_csv(OUT / "firm_persistence_step0.csv", index=False)
    pd.DataFrame([gates]).to_csv(OUT / "firm_persistence_step0_gates.csv", index=False)
    print()
    print(Y.pivot_table(index=["group", "part", "statistic"], columns="year", values="b").round(4).to_string())
    print()
    print(S.round(4).to_string(index=False))
    print("\nGates:", gates)


if __name__ == "__main__":
    main()
