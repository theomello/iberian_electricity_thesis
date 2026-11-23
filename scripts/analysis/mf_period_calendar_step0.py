"""Step zero of the medium-firm period-calendar design (docs/specs/2026-11-23-medium-firms-period-calendar-design.md).

    .venv/bin/python scripts/analysis/mf_period_calendar_step0.py

Placebo summers only: E1+E2 (ESIOS 1202+1203) and the 6.1A stand-in (ESIOS 1369) are cut at 2019-09-30 right after
loading (asserted). M0 data and the 2014 gate, M1 stand-in gate, M2 seal, M3 noise gate.
Working days 1 Jun - 30 Sep; cells = (part of summer: Jun 1-15, Jun 16-30, Jul, Aug, Sep) x hour; s = 100 x load /
daily mean; per-year raw OLS s_Y(c) = alpha_Y(h) + b_Y d(c), unweighted; d = old 6.1A period number - new 6.1TD
period number (tou_tariff_schedule.schedule, tariff 6.1, 2021 calendar), mean over the cell's working days.
Gate: eta_MDE = (MDE / s-bar) / d-bar <= 0.15. Writes outputs/tables/mf_period_calendar_step0{,_years}.csv.
Deterministic.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_industry_regulated_price as IR  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = TS.ROOT / "outputs" / "tables"
SEAL = pd.Timestamp("2019-09-30")
E1E2_YEARS = [2014, 2017, 2018, 2019]
STANDIN_YEARS = [2015, 2016]
OVERLAP = [2017, 2018, 2019]
E_PRICE = 100.81
GATE = 0.15


def part(dates):
    d = pd.DatetimeIndex(dates)
    mm = pd.Series(d.month).astype(str).str.zfill(2).to_numpy()
    return np.where(d.month == 6, np.where(d.day <= 15, "06a", "06b"), mm)


def working(dates, hol):
    d = pd.DatetimeIndex(dates)
    return (d.dayofweek < 5) & ~d.isin(list(hol)) & ~((d.month == 1) & (d.day == 6))


def load(ids):
    x = CT.esios_load(ids)
    x = x[x.date <= SEAL].copy()   # seal: applied at once
    assert x.date.max() <= SEAL
    return x


def summer(x, y, hol):
    d0, d1 = pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-30")
    f = x[(x.date >= d0) & (x.date <= d1)].copy()
    exp_days = pd.date_range(d0, d1)
    cov = len(f) / (24 * len(exp_days))
    n = f.groupby("date").v.count()
    f = f[f.date.isin(n[n == 24].index)]
    f = f[working(f.date, hol)]
    f["s"] = 100 * f.v / f.groupby("date").v.transform("mean")
    f["part"] = part(f.date)
    return f, cov


def d_cells(hol):
    dates = pd.date_range("2021-06-01", "2021-09-30")
    s = TS.schedule(dates)
    s = s[(s.tariff == "6.1")].copy()
    s = s[working(s.date, hol)]
    s["d"] = s.old_period - s.new_period
    s["part"] = part(s.date)
    pt = IR.power_table()
    w = pt[pt.tariff == "6.1"].set_index(["regime", "period"]).w_eur_mwh
    s["dlnp"] = np.log((E_PRICE + s.new_price + s.new_period.map(lambda p: w[("new", p)]))
                       / (E_PRICE + s.old_price + s.old_period.map(lambda p: w[("old", p)])))
    return s.groupby(["part", "hour"])[["d", "dlnp"]].mean()


def cells(f, dc):
    c = f.groupby(["part", "hour"]).s.mean().to_frame().join(dc).reset_index()
    assert len(c) == 120 and c.d.notna().all()
    return c


def ols_b(c, fe=True):
    if fe:
        X = np.column_stack([(c.hour.to_numpy() == h).astype(float) for h in range(24)] + [c.d.to_numpy()])
    else:
        X = np.column_stack([np.ones(len(c)), c.d.to_numpy()])
    return float(np.linalg.lstsq(X, c.s.to_numpy(), rcond=None)[0][-1])


def inference(bs, years):
    bs, years = np.asarray(bs, float), np.asarray(years, float)
    S = len(bs)
    m, s = bs.mean(), bs.std(ddof=1)
    mde = (stats.t.ppf(0.95, S - 1) + stats.t.ppf(0.80, S - 1)) * s * np.sqrt(1 + 1 / S)
    mde_n = (stats.norm.ppf(0.95) + stats.norm.ppf(0.80)) * s * np.sqrt(1 + 1 / S)
    out = dict(S=S, m=m, s=s, mde=mde, mde_normal=mde_n)
    if S >= 3:
        slope, icpt = np.polyfit(years, bs, 1)
        resid = bs - (icpt + slope * years)
        s_e = np.sqrt((resid ** 2).sum() / (S - 2)) if S > 2 else np.nan
        se_pred = s_e * np.sqrt(1 + 1 / S + (2021 - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum())
        out.update(trend_slope=slope, mde_trend=(stats.t.ppf(0.95, S - 2) + stats.t.ppf(0.80, S - 2)) * se_pred if S > 3 else np.nan)
    return out


def dbar(dc, fe=True):
    c = dc.reset_index()
    if fe:
        dd = c.d - c.groupby("hour").d.transform("mean")
        dp = c.dlnp - c.groupby("hour").dlnp.transform("mean")
    else:
        dd, dp = c.d - c.d.mean(), c.dlnp - c.dlnp.mean()
    return float((dd * dp).sum() / (dd * dd).sum())


def main():
    pd.set_option("display.width", 220)
    hol = TS.holidays()
    dc = d_cells(hol)
    # identification split (within-hour sum of squares of d by part)
    c0 = dc.reset_index()
    dd = c0.d - c0.groupby("hour").d.transform("mean")
    share = (dd ** 2).groupby(c0.part).sum() / (dd ** 2).sum()
    print("within-hour variation of d by part:", share.round(3).to_dict())

    e12, i1369 = load([1202, 1203]), load([1369])
    print(f"M2 seal: E1+E2 ends {e12.date.max().date()}, 1369 ends {i1369.date.max().date()} (<= {SEAL.date()})")
    assert i1369.date.dt.year.isin([2015, 2016, 2017]).any() and i1369.date.dt.year.isin([2018, 2019]).any()

    rows, cov, cl = [], {}, {}
    for ser, x, years in (("E1+E2", e12, E1E2_YEARS), ("1369", i1369, STANDIN_YEARS + OVERLAP)):
        for y in years:
            f, cv = summer(x, y, hol)
            cov[(ser, y)] = cv
            if f.empty:
                continue
            c = cells(f, dc)
            cl[(ser, y)] = c
            rows.append(dict(series=ser, year=y, b=ols_b(c), b_nofe=ols_b(c, fe=False), coverage=cv,
                             energy_twh=float(f.v.sum() / 1e6)))
    yrs = pd.DataFrame(rows)

    # M0
    m0_e12 = {y: cov[("E1+E2", y)] >= 0.99 for y in E1E2_YEARS}
    m0_1369 = {y: cov[("1369", y)] >= 0.99 for y in STANDIN_YEARS + [2017]}
    mon = e12[e12.date.dt.month.between(6, 9)].assign(y=lambda d: d.date.dt.year, m=lambda d: d.date.dt.month)
    mon = mon.groupby(["y", "m"]).v.sum().unstack("y")
    ratio14 = mon[2014] / mon[[2017, 2018, 2019]].mean(axis=1)
    gate14 = bool(((ratio14 - 1).abs() <= 0.15).all())
    print("M0 coverage E1+E2:", {y: round(cov[('E1+E2', y)], 4) for y in E1E2_YEARS}, "| 1369:", {y: round(cov[('1369', y)], 4) for y in STANDIN_YEARS + OVERLAP})
    print("M0 2014 gate (Jun-Sep energy / 2017-19 mean):", ratio14.round(3).to_dict(), "->", "pass" if gate14 else "FAIL")
    e12_years = [y for y in E1E2_YEARS if m0_e12[y] and (y != 2014 or gate14)]

    # M1 stand-in gate
    b_e = yrs[yrs.series == "E1+E2"].set_index("year").b
    b_s = yrs[yrs.series == "1369"].set_index("year").b
    diff = (b_s.reindex(OVERLAP) - b_e.reindex(OVERLAP))
    sd_e = float(b_e.reindex(e12_years).std(ddof=1))
    corr = {y: float(np.corrcoef(cl[("1369", y)].s, cl[("E1+E2", y)].s)[0, 1]) for y in OVERLAP}
    m1 = bool(diff.abs().max() <= 0.5 * sd_e and abs(diff.mean()) <= 0.5 * sd_e)
    print(f"M1 stand-in: b(1369) - b(E1+E2) by overlap year {diff.round(4).to_dict()}; max |diff| {diff.abs().max():.4f}, "
          f"|mean diff| {abs(diff.mean()):.4f}, bar 0.5 x sd(E1+E2) = {0.5 * sd_e:.4f}; share corr {np.round(list(corr.values()), 4)} -> {'pass' if m1 else 'FAIL'}")

    # placebo set
    pl = [(y, float(b_e[y]), float(yrs[(yrs.series == "E1+E2") & (yrs.year == y)].b_nofe.iloc[0])) for y in e12_years]
    if m1:
        pl += [(y, float(b_s[y]), float(yrs[(yrs.series == "1369") & (yrs.year == y)].b_nofe.iloc[0])) for y in STANDIN_YEARS if m0_1369[y]]
    pl.sort()
    years = [p[0] for p in pl]
    inf = inference([p[1] for p in pl], years)
    inf_nofe = inference([p[2] for p in pl], years)

    # scale: s-bar over hours 8-23 in E1+E2 placebo years; d-bar slopes
    sbar = float(np.mean([cl[("E1+E2", y)].query("hour >= 8").s.mean() for y in e12_years]))
    db, db_nofe = dbar(dc, True), dbar(dc, False)
    eta = (inf["mde"] / sbar) / db
    eta_tr = (inf.get("mde_trend", np.nan) / sbar) / db
    eta_nofe = (inf_nofe["mde"] / sbar) / db_nofe
    summ = pd.DataFrame([dict(form="hour FE (rule)", years=" ".join(map(str, years)), **inf, sbar=sbar, dbar=db, eta_mde=eta, eta_mde_trend=eta_tr,
                              gate_pass=eta <= GATE, m0_2014=gate14, m1_pass=m1),
                         dict(form="industry form (no FE)", years=" ".join(map(str, years)), **inf_nofe, sbar=sbar, dbar=db_nofe,
                              eta_mde=eta_nofe, eta_mde_trend=(inf_nofe.get("mde_trend", np.nan) / sbar) / db_nofe)])
    yrs.to_csv(OUT / "mf_period_calendar_step0_years.csv", index=False)
    summ.to_csv(OUT / "mf_period_calendar_step0.csv", index=False)
    print("\nPer-year b (points of the daily mean per period step):")
    print(yrs.round(4).to_string(index=False))
    print()
    print(summ.round(4).to_string(index=False))
    print(f"\nM3 gate: eta_MDE = {eta:.3f} vs {GATE} -> {'PASS' if eta <= GATE else 'FAIL'} (trend-null {eta_tr:.3f}); placebo years {years}")


if __name__ == "__main__":
    main()
