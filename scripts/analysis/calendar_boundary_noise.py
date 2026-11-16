"""Step zero (S0, S1, S2) of docs/specs/2026-11-17-calendar-boundary-design.md. The real boundary windows are sealed: only placebo dates and mid-month dates are computed.

    .venv/bin/python scripts/analysis/calendar_boundary_noise.py

Barcelona electricity (kWh), city level, sectors Serveis / Residencial / Industria, band 'No consta' dropped. Daily lr = log(sum of the 06-12, 12-18, 18-24 bands) - log(00-06 band); per side of a date (14 days
before, 14 days from the date on): mean(lr) of working days - mean(lr) of weekends and national holidays; S = after - before; D = S(Y) - S(2019, same calendar date); DD = D(Serveis) - D(Residencial).
Placebo dates: 1 Feb, 1 May, 1 Sep (1 Jan cannot be computed in 2019: the 2018 days of its window do not exist; forced by the data, recorded in the spec), years 2021 (Sep only: after the 1 June 2021 reform),
2022-2025. Mid-month dates: the 15th of each month from 2021-07 on. Dose: mean absolute log change of the 3.0TD top-period price at the eight real boundaries (2021 tolls and charges, each year's mean
OMIE price in the window as the energy price); outcomes at the real dates are never computed. Detectable elasticity = 2.8 sd(DD) / mean|dose|. Writes outputs/tables/calendar_boundary_noise.csv.
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

ROOT = T.ROOT
BANDS = {"De 00:00:00 a 05:59:59 h": "night", "De 06:00:00 a 11:59:59 h": "b1", "De 12:00:00 a 17:59:59 h": "b2", "De 18:00:00 a 23:59:59 h": "b3"}
SECT = {"Serveis": "serv", "Residencial": "res", "Indústria": "ind"}
REAL = [(3, 1), (4, 1), (6, 1), (7, 1), (8, 1), (10, 1), (11, 1), (12, 1)]
PLACEBO = [(2, 1), (5, 1), (9, 1)]
SEASON_PERIOD = {1: "P1", 2: "P1", 7: "P1", 12: "P1", 3: "P2", 11: "P2", 6: "P3", 8: "P3", 9: "P3", 4: "P4", 5: "P4", 10: "P4"}


def load():
    D = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in sorted(glob.glob(str(ROOT / "data/barcelona_electricity/raw/*.csv")))], ignore_index=True)
    D.columns = ["year", "date", "zip", "sector", "band", "value"]
    D["date"] = pd.to_datetime(D.date)
    D = D[D.band.isin(BANDS) & D.sector.isin(SECT)].copy()
    D["band"], D["sector"] = D.band.map(BANDS), D.sector.map(SECT)
    return D


def daily(D):
    p = D.groupby(["date", "sector", "band"]).value.sum().unstack("band")
    p["day"] = p.b1 + p.b2 + p.b3
    return np.log(p["day"].where(p["day"] > 0)) - np.log(p["night"].where(p["night"] > 0))


def s_stat(lr, sector, t0, wk):
    """Working-day minus weekend/holiday mean of lr, after (t0..t0+13) minus before (t0-14..t0-1)."""
    s = lr.xs(sector, level="sector")
    out = []
    for a, b in ((t0 - pd.Timedelta(days=14), t0 - pd.Timedelta(days=1)), (t0, t0 + pd.Timedelta(days=13))):
        w = s.loc[a:b]
        if len(w) < 12:
            return np.nan
        isw = w.index.map(lambda d: d in wk)
        out.append(w[~isw].mean() - w[isw].mean())
    return out[1] - out[0]


def main():
    D = load()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    lr = daily(D)
    days = set(D.date.unique())
    # S0
    events = [(Y, m, d) for Y in (2021, 2022, 2023, 2024, 2025) for (m, d) in PLACEBO if not (Y == 2021 and m < 7)]
    mid = [(Y, m, 15) for Y in (2021, 2022, 2023, 2024, 2025) for m in range(1, 13) if pd.Timestamp(Y, m, 15) >= pd.Timestamp("2021-07-15") and pd.Timestamp(Y, m, 15) + pd.Timedelta(days=13) <= pd.Timestamp("2025-11-30")]
    need = set()
    for Y, m, d in events + mid + [(2019, m, d) for (_, m, d) in events + mid]:
        t0 = pd.Timestamp(Y, m, d)
        need |= set(pd.date_range(t0 - pd.Timedelta(days=14), t0 + pd.Timedelta(days=13)))
    have = sum(1 for x in need if x in days)
    cov = have / len(need)
    serv = D[(D.sector == "serv") & (D.band != "night") & (D.value > 0)].groupby("date").zip.nunique()
    zip_share = float((serv.reindex(sorted(need)).fillna(0) >= 30).mean())
    s0 = bool(cov >= 0.95 and zip_share >= 0.95)
    print(f"S0 coverage of window days {cov:.3f} ({have}/{len(need)}); days with >= 30 Serveis postal codes with non-zero day bands {zip_share:.3f} -> {'PASS' if s0 else 'FAIL, stop'}", flush=True)
    if not s0:
        return
    # S2 seal check
    for Y, m, d in events + mid:
        assert (m, d) not in REAL, "real boundary date in the event list"
    rows = []
    for kind, ev in (("placebo", events), ("mid-month", mid)):
        for Y, m, d in ev:
            r = dict(kind=kind, year=Y, month=m, day=d)
            for sec in ("serv", "res", "ind"):
                a = s_stat(lr, sec, pd.Timestamp(Y, m, d), hes)
                b = s_stat(lr, sec, pd.Timestamp(2019, m, d), hes)
                r[f"D_{sec}"] = a - b
            r["DD_serv"], r["DD_ind"] = r["D_serv"] - r["D_res"], r["D_ind"] - r["D_res"]
            rows.append(r)
    R = pd.DataFrame(rows)
    # dose: 3.0TD top-period price changes at the eight real boundaries (prices only, no outcomes)
    pr = pd.read_csv(ROOT / "outputs/tables/tou_tariff_prices_2021.csv")
    pr = pr[pr.tariff == "3.0TD"].set_index("period").total_eur_mwh
    eh = CT.omie_hourly()
    dm = eh.groupby(level=0).mean()
    doses = []
    for Y in (2021, 2022, 2023, 2024, 2025):
        for (m, d) in REAL:
            t0 = pd.Timestamp(Y, m, d)
            if t0 < pd.Timestamp("2021-07-01") or t0 + pd.Timedelta(days=13) > pd.Timestamp("2025-09-30"):
                continue
            E = float(dm.loc[t0 - pd.Timedelta(days=14): t0 + pd.Timedelta(days=13)].mean())
            before, after = SEASON_PERIOD[(m - 2) % 12 + 1], SEASON_PERIOD[m]
            doses.append(dict(year=Y, month=m, step_eur=float(pr[after] - pr[before]), E=E, log_dose=float(np.log((E + pr[after]) / (E + pr[before])))))
    Dz = pd.DataFrame(doses)
    mean_abs = float(Dz.log_dose.abs().mean())
    print(f"dose: {len(Dz)} real boundary-years, mean |log dose| {mean_abs:.3f}; steps in EUR/MWh {sorted(set(Dz.step_eur.round(1)))}", flush=True)
    pd.set_option("display.width", 200)
    P = R[R.kind == "placebo"]
    print(P[["year", "month", "D_serv", "D_res", "D_ind", "DD_serv", "DD_ind"]].round(4).to_string(index=False))
    out = []
    for kind in ("placebo", "mid-month"):
        sub = R[R.kind == kind]
        for col in ("DD_serv", "DD_ind"):
            sd = float(sub[col].std(ddof=1))
            out.append(dict(kind=kind, measure=col, n_events=int(sub[col].notna().sum()), mean=float(sub[col].mean()), sd=sd, detectable=2.8 * sd / mean_abs))
    O = pd.DataFrame(out)
    print(O.round(4).to_string(index=False))
    s1 = float(O[(O.kind == "placebo") & (O.measure == "DD_serv")].detectable.iloc[0])
    print(f"S1: placebo-date sd of DD (Serveis minus Residencial) -> detectable elasticity {s1:.3f} (bar 0.15) -> {'PASS' if s1 <= 0.15 else 'FAIL, close the design'}", flush=True)
    R.round(5).to_csv(T.OUT / "calendar_boundary_noise.csv", index=False)
    O.round(5).to_csv(T.OUT / "calendar_boundary_noise_summary.csv", index=False)
    Dz.round(4).to_csv(T.OUT / "calendar_boundary_dose.csv", index=False)


if __name__ == "__main__":
    main()
