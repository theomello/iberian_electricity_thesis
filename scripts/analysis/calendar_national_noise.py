"""Step zero (S0, S1b) of docs/specs/2026-11-17-calendar-national-design.md. Placebo events only; the real boundary windows are sealed.

    .venv/bin/python scripts/analysis/calendar_national_noise.py

Series: E1+E2 = ESIOS 1202+1203; 6.2, 6.3, 6.4 = 1216, 1217, 1218 (hourly, local Madrid); Portugal = REN `Consumption` (15-minute, Lisbon time, Portuguese holidays). lr = ln(sum hours 8-23) - ln(sum hours 0-7) per complete day.
S(t0, Y) = (working-day mean - weekend/national-holiday mean of lr) after t0 (t0..t0+13) minus before (t0-14..t0-1); D = S(Y) - mean(S(2018), S(2019)); DD = D(series) - D(Portugal). Placebo events: the 15th of
Jan, Feb, Mar, Apr, May, Jul, Aug, Sep, Oct, Nov, Dec, 2021 (from 15 Jul) to 2025 (June excluded: the old 16 June step). S1b: detectable = 2.8 sd(DD) sqrt(DEFF) / sqrt(sum dose^2) over the real boundary-years
(6.1TD, or the series' own tariff, log top-period price change at each year's mean OMIE price; prices only), DEFF = 1 + (m-1) rho from a one-way ANOVA of DD across years on the same placebo events. Bar 0.15.
Writes outputs/tables/calendar_national_noise*.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendar_boundary_noise as CB  # noqa: E402
import calendar_boundary_s1b as S1  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

ROOT = T.ROOT
SERIES = {"e12": [1202, 1203], "t62": [1216], "t63": [1217], "t64": [1218]}
TARIFF = {"e12": "6.1TD", "t62": "6.2TD", "t63": "6.3TD", "t64": "6.4TD"}
REAL = CB.REAL
MONTHS = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]


def lr_from_hourly(h):
    """h: Series indexed (date, hour) -> daily ln(day 8-23) - ln(night 0-7) for complete days."""
    cnt = h.groupby(level=0).size()
    h = h[h.index.get_level_values(0).isin(cnt[cnt == 24].index)]
    hr = h.index.get_level_values(1)
    day = h[hr >= 8].groupby(level=0).sum()
    night = h[hr < 8].groupby(level=0).sum()
    return np.log(day.where(day > 0)) - np.log(night.where(night > 0))


def series_lr():
    out = {}
    for k, ids in SERIES.items():
        out[k] = lr_from_hourly(sum(N.hourly(i) for i in ids))
    d = pd.read_parquet(ROOT / "data/ren/ren_production_15min.parquet")
    d = d[d.series == "Consumption"].drop_duplicates("utc_timestamp")
    loc = pd.DatetimeIndex(d.utc_timestamp).tz_convert("Europe/Lisbon")
    x = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": d.value_mw.to_numpy()})
    h = x.groupby(["date", "hour"]).v.sum()
    out["pt"] = lr_from_hourly(h)
    frames = [pd.Series(v.to_numpy(), index=pd.MultiIndex.from_arrays([v.index, [k] * len(v)], names=["date", "sector"])) for k, v in out.items()]
    return pd.concat(frames)


def main():
    lr = series_lr()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    events = [(Y, m) for Y in (2021, 2022, 2023, 2024, 2025) for m in MONTHS if pd.Timestamp(Y, m, 15) >= pd.Timestamp("2021-07-15")]
    for Y, m in events:
        assert (m, 15) not in REAL and m != 6
    # S0
    days = {k: set(lr.xs(k, level="sector").dropna().index) for k in list(SERIES) + ["pt"]}
    need = set()
    for Y, m in events:
        for yy in (Y, 2018, 2019):
            t0 = pd.Timestamp(yy, m, 15)
            need |= set(pd.date_range(t0 - pd.Timedelta(days=14), t0 + pd.Timedelta(days=13)))
    cov = {k: len(need & v) / len(need) for k, v in days.items()}
    s0 = bool(all(c >= 0.95 for c in cov.values()))
    print("S0 coverage of window days by series:", {k: round(c, 3) for k, c in cov.items()}, "->", "PASS" if s0 else "FAIL, stop", flush=True)
    if not s0:
        return
    rows = []
    for Y, m in events:
        t0 = pd.Timestamp(Y, m, 15)
        row = dict(year=Y, month=m, kind="mid-month")
        Spt = CB.s_stat(lr, "pt", t0, hpt)
        bpt = np.nanmean([CB.s_stat(lr, "pt", pd.Timestamp(yy, m, 15), hpt) for yy in (2018, 2019)])
        Dpt = Spt - bpt
        for k in SERIES:
            a = CB.s_stat(lr, k, t0, hes)
            b = np.nanmean([CB.s_stat(lr, k, pd.Timestamp(yy, m, 15), hes) for yy in (2018, 2019)])
            row[f"D_{k}"] = a - b
            row[f"DD_{k}"] = (a - b) - Dpt
        row["D_pt"] = Dpt
        rows.append(row)
    R = pd.DataFrame(rows)
    # doses (prices only)
    pr = pd.read_csv(ROOT / "outputs/tables/tou_tariff_prices_2021.csv")
    dm = CT.omie_hourly().groupby(level=0).mean()
    out = []
    for k, tar in TARIFF.items():
        p = pr[pr.tariff == tar].set_index("period").total_eur_mwh
        doses = []
        for Y in (2021, 2022, 2023, 2024, 2025):
            for (m, d) in REAL:
                t0 = pd.Timestamp(Y, m, d)
                if t0 < pd.Timestamp("2021-07-01") or t0 + pd.Timedelta(days=13) > pd.Timestamp("2025-09-30"):
                    continue
                E = float(dm.loc[t0 - pd.Timedelta(days=14): t0 + pd.Timedelta(days=13)].mean())
                before, after = CB.SEASON_PERIOD[(m - 2) % 12 + 1], CB.SEASON_PERIOD[m]
                doses.append(dict(year=Y, month=m, log_dose=float(np.log((E + p[after]) / (E + p[before])))))
        Dz = pd.DataFrame(doses)
        ss = float((Dz.log_dose ** 2).sum())
        sd = float(R[f"DD_{k}"].std(ddof=1))
        rho, msb, msw = S1.icc(R[f"DD_{k}"].to_numpy(), R.year.to_numpy())
        m_per_year = len(Dz) / Dz.year.nunique()
        deff = 1 + (m_per_year - 1) * rho
        se = sd / np.sqrt(ss)
        out.append(dict(series=k, tariff=tar, real_events=len(Dz), mean_abs_log_dose=float(Dz.log_dose.abs().mean()), sum_dose2=ss, placebo_events=int(R[f"DD_{k}"].notna().sum()), sd_placebo=sd, rho=rho, DEFF=deff,
                        SE_pooled=se * np.sqrt(deff), detectable_S1b=2.8 * se * np.sqrt(deff), detectable_rho05=2.8 * se * np.sqrt(1 + (m_per_year - 1) * 0.5)))
    O = pd.DataFrame(out)
    pd.set_option("display.width", 220)
    print(O.round(4).to_string(index=False))
    e12 = float(O[O.series == "e12"].detectable_S1b.iloc[0])
    ok = bool(np.isfinite(e12) and e12 <= 0.15)
    print(f"S1b (E1+E2): detectable elasticity {e12:.3f} (bar 0.15) -> {'PASS' if ok else 'FAIL, close the calendar design'}", flush=True)
    R.round(5).to_csv(T.OUT / "calendar_national_noise.csv", index=False)
    O.round(5).to_csv(T.OUT / "calendar_national_noise_summary.csv", index=False)


if __name__ == "__main__":
    main()
