"""R0 and estimation rules E1-E8 (with E6b) of docs/specs/2026-11-17-calendar-national-design.md: the real boundary windows are opened here.

    .venv/bin/python scripts/analysis/calendar_national_estimate.py

R0: old (ITC/2794/2007) day type on each side of the eight boundaries, from tou_tariff_schedule.old_period_6/old_day_type, checked against the old calendar read from the BOE text (expected types below);
stop (no estimation) if fewer than six of eight match. Dose difference doseDiff = log((E+p_new_after)/(E+p_new_before)) - log((E+p_old_after)/(E+p_old_before)), top-period prices of the series' tariff
(6.1TD / old 6.1A for E1+E2; 6.2, 6.3, 6.4 likewise), E = mean OMIE price of the window in the event year. Statistic: calendar_boundary_noise.s_stat on lr = ln(day hours) - ln(hours 0-7);
D = S(Y) - mean(S(2018), S(2019)); DD = D(series) - D(Portugal). Real events: 34 boundary-years from 2021-07-01 to 2025-09-30 (window end). Placebo events: 15th of 11 months, 2021-07-15 to 2025 (dose 0).
eta = sum(doseDiff DD)/sum(doseDiff^2); randomization: doses permuted within year over real + placebo events, 10,000 draws, one-sided p = (1+#{eta_perm <= eta})/(1+N), interval eta - [q97.5, q2.5].
E6b: separate intercept per year (within-year demeaning). Writes outputs/tables/calendar_national_{old_dose,estimate,estimate_summary}.csv. Seed 20261117.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendar_boundary_noise as CB  # noqa: E402
import calendar_national_noise as CNN  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

ROOT, SEED, NPERM = T.ROOT, 20261117, 10000
REAL = CB.REAL
OLD_TARIFF = {"e12": "6.1", "t62": "6.2", "t63": "6.3", "t64": "6.4"}
# old calendar from Orden ITC/2794/2007 annex II as read in docs/tou-policy-sources.md: (type before, type after) on each boundary date
EXPECTED = {(3, 1): ("A", "B1"), (4, 1): ("B1", "C"), (6, 1): ("C", "B"), (7, 1): ("A1", "A1"), (8, 1): ("A1", "D"), (10, 1): ("B", "C"), (11, 1): ("C", "B1"), (12, 1): ("B1", "A")}
MONTHS = CNN.MONTHS
DAY_MAIN, DAY_ALT = list(range(8, 24)), list(range(9, 14)) + list(range(18, 22))


def weekday_near(t):
    while t.dayofweek >= 5:
        t += pd.Timedelta(days=1)
    return t


def old_types(m, d):
    t0 = pd.Timestamp(2019, m, d)
    b, a = weekday_near(t0 - pd.Timedelta(days=7)), weekday_near(t0 + pd.Timedelta(days=7))
    return TS.old_day_type(b, False), TS.old_day_type(a, False)


def top_old(dt):
    return min(TS.old_period_6(dt, h) for h in range(8, 24))


def r0():
    rows = []
    for (m, d), exp in EXPECTED.items():
        got = old_types(m, d)
        rows.append(dict(month=m, expected_before=exp[0], expected_after=exp[1], module_before=got[0], module_after=got[1], match=bool(got == exp),
                         old_top_before=top_old(got[0]), old_top_after=top_old(got[1])))
    R = pd.DataFrame(rows)
    ok = int(R.match.sum())
    print(f"R0 old calendar reproduced for {ok} of 8 boundaries ->", "PASS" if ok >= 6 else "FAIL, stop", flush=True)
    print(R.to_string(index=False), flush=True)
    R.to_csv(T.OUT / "calendar_national_old_dose.csv", index=False)
    return R, ok >= 6


def hourly_all():
    h = {k: sum(N.hourly(i) for i in ids) for k, ids in CNN.SERIES.items()}
    d = pd.read_parquet(ROOT / "data/ren/ren_production_15min.parquet")
    d = d[d.series == "Consumption"].drop_duplicates("utc_timestamp")
    loc = pd.DatetimeIndex(d.utc_timestamp).tz_convert("Europe/Lisbon")
    x = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": d.value_mw.to_numpy()})
    h["pt"] = x.groupby(["date", "hour"]).v.sum()
    return h


def lr_variant(h, dayhours):
    out = {}
    for k, s in h.items():
        cnt = s.groupby(level=0).size()
        s = s[s.index.get_level_values(0).isin(cnt[cnt == 24].index)]
        hr = s.index.get_level_values(1)
        day = s[np.isin(hr, dayhours)].groupby(level=0).sum()
        night = s[hr < 8].groupby(level=0).sum()
        v = np.log(day.where(day > 0)) - np.log(night.where(night > 0))
        out[k] = pd.Series(v.to_numpy(), index=pd.MultiIndex.from_arrays([v.index, [k] * len(v)], names=["date", "sector"]))
    return pd.concat(out.values())


def stats(lr, k, t0, hes, hpt, months_base):
    def one(sec, hol, t):
        return CB.s_stat(lr, sec, t, hol)
    a = one(k, hes, t0)
    b = np.nanmean([one(k, hes, pd.Timestamp(yy, t0.month, t0.day)) for yy in (2018, 2019)])
    ap = one("pt", hpt, t0)
    bp = np.nanmean([one("pt", hpt, pd.Timestamp(yy, t0.month, t0.day)) for yy in (2018, 2019)])
    return a - b, ap - bp


def eta_plain(dose, y):
    return float((dose * y).sum() / (dose ** 2).sum())


def eta_fe(df, ycol):
    d = df.dose - df.groupby("year").dose.transform("mean")
    y = df[ycol] - df.groupby("year")[ycol].transform("mean")
    return float((d * y).sum() / (d ** 2).sum())


def perm(pool, ycol, rng, fe=False):
    groups = [(g.dose.to_numpy(), g[ycol].to_numpy()) for _, g in pool.groupby("year")]
    if fe:
        ss_parts = None
        out = np.empty(NPERM)
        for r in range(NPERM):
            num = den = 0.0
            for d, v in groups:
                dp = rng.permutation(d)
                dd = dp - dp.mean()
                num += (dd * (v - v.mean())).sum()
                den += (dd ** 2).sum()
            out[r] = num / den
        return out
    ss = float((pool.dose ** 2).sum())
    out = np.empty(NPERM)
    for r in range(NPERM):
        out[r] = sum((rng.permutation(d) * v).sum() for d, v in groups) / ss
    return out


def summarize(e, dist, two=False):
    p = (1 + np.sum(np.abs(dist) >= abs(e))) / (1 + len(dist)) if two else (1 + np.sum(dist <= e)) / (1 + len(dist))
    return dict(eta=e, p=p, lo=e - np.quantile(dist, 0.975), hi=e - np.quantile(dist, 0.025))


def main():
    R0, ok0 = r0()
    if not ok0:
        return
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    h = hourly_all()
    lrs = {"main": lr_variant(h, DAY_MAIN), "alt": lr_variant(h, DAY_ALT)}
    pr = pd.read_csv(ROOT / "outputs/tables/tou_tariff_prices_2021.csv")
    dm = CT.omie_hourly().groupby(level=0).mean()
    tariff = CNN.TARIFF
    real_ev = [(Y, m, d) for Y in (2021, 2022, 2023, 2024, 2025) for (m, d) in REAL
               if pd.Timestamp(Y, m, d) >= pd.Timestamp("2021-07-01") and pd.Timestamp(Y, m, d) + pd.Timedelta(days=13) <= pd.Timestamp("2025-09-30")]
    plc_ev = [(Y, m, 15) for Y in (2021, 2022, 2023, 2024, 2025) for m in MONTHS if pd.Timestamp(Y, m, 15) >= pd.Timestamp("2021-07-15")]
    for Y, m, d in plc_ev:
        assert (m, d) not in REAL and m != 6
    print(f"real events {len(real_ev)}, placebo events {len(plc_ev)}", flush=True)
    om = {r.month: r for r in R0.itertuples()}
    rows = []
    for kind, evs in (("real", real_ev), ("placebo", plc_ev)):
        for Y, m, d in evs:
            t0 = pd.Timestamp(Y, m, d)
            row = dict(kind=kind, year=Y, month=m)
            E = float(dm.loc[t0 - pd.Timedelta(days=14): t0 + pd.Timedelta(days=13)].mean())
            for k in CNN.SERIES:
                tar = tariff[k]
                p = pr[pr.tariff == tar].set_index("period").total_eur_mwh
                if kind == "real":
                    bn, an = CB.SEASON_PERIOD[(m - 2) % 12 + 1], CB.SEASON_PERIOD[m]
                    dn = float(np.log((E + p[an]) / (E + p[bn])))
                    po = TS.OLD[OLD_TARIFF[k]]
                    do = float(np.log((E + po[om[m].old_top_after - 1]) / (E + po[om[m].old_top_before - 1])))
                    row[f"dose_new_{k}"], row[f"dose_old_{k}"], row[f"dose_{k}"] = dn, do, dn - do
                else:
                    row[f"dose_{k}"] = 0.0
            for var, lr in lrs.items():
                for k in CNN.SERIES:
                    Dk, Dpt = stats(lr, k, t0, hes, hpt, None)
                    row[f"D_{k}_{var}"], row[f"DD_{k}_{var}"] = Dk, Dk - Dpt
                    row[f"D_pt_{var}"] = Dpt
            rows.append(row)
        print(f"{kind} events computed", flush=True)
    A = pd.DataFrame(rows)
    A.round(5).to_csv(T.OUT / "calendar_national_estimate.csv", index=False)
    Rl, Pl = A[A.kind == "real"].copy(), A[A.kind == "placebo"].copy()
    print("real doseDiff e12 by month (mean over years):", Rl.groupby("month").dose_e12.mean().round(3).to_dict(), flush=True)
    print(f"NaN in real DD_e12_main: {int(Rl.DD_e12_main.isna().sum())}; placebo: {int(Pl.DD_e12_main.isna().sum())}", flush=True)
    Rl = Rl.dropna(subset=["DD_e12_main", "D_e12_main", "D_pt_main"])
    Pl = Pl.dropna(subset=["DD_e12_main", "D_e12_main", "D_pt_main"])

    def pool_for(k, ycol):
        a = Rl[["year", f"dose_{k}", ycol]].rename(columns={f"dose_{k}": "dose"})
        b = Pl[["year", f"dose_{k}", ycol]].rename(columns={f"dose_{k}": "dose"})
        return a, pd.concat([a, b], ignore_index=True)

    def est(k, ycol, seed, two=False, fe=False):
        a, pool = pool_for(k, ycol)
        pool = pool.dropna()
        dist = perm(pool, ycol, np.random.default_rng(seed), fe=fe)
        e = eta_fe(pool, ycol) if fe else eta_plain(a.dropna().dose, a.dropna()[ycol])
        return summarize(e, dist, two), a.dropna()

    e1, a1 = est("e12", "DD_e12_main", SEED)
    ok1 = bool(-1 <= e1["eta"] <= 0 and e1["p"] <= 0.05 and e1["hi"] < 0)
    print(f"E1 eta {e1['eta']:+.4f} one-sided p {e1['p']:.4f} interval [{e1['lo']:+.4f}, {e1['hi']:+.4f}] ({len(a1)} events) -> {ok1}", flush=True)
    up, dn = a1[a1.dose > 0], a1[a1.dose < 0]
    eu, ed = eta_plain(up.dose, up.DD_e12_main), eta_plain(dn.dose, dn.DD_e12_main)
    ok2 = bool(eu < 0 and ed < 0)
    print(f"E2 eta_up {eu:+.4f} ({len(up)} events), eta_down {ed:+.4f} ({len(dn)} events) -> {ok2}", flush=True)
    e3, _ = est("e12", "D_pt_main", SEED + 1, two=True)
    ok3 = bool(e3["p"] > 0.05 and abs(e3["eta"]) < abs(e1["eta"]) / 3)
    print(f"E3 Portugal alone eta {e3['eta']:+.4f}, two-sided p {e3['p']:.4f}, interval [{e3['lo']:+.4f}, {e3['hi']:+.4f}] -> {ok3}", flush=True)
    full = Rl.assign(dose=Rl.dose_e12)
    loo = {}
    for y in sorted(full.year.unique()):
        s = full[full.year != y]
        loo[f"year {y}"] = eta_plain(s.dose, s.DD_e12_main)
    for m in sorted(full.month.unique()):
        s = full[full.month != m]
        loo[f"month {m}"] = eta_plain(s.dose, s.DD_e12_main)
    ok4 = bool(all(v < 0 and e1["lo"] <= v <= e1["hi"] for v in loo.values()))
    print("E4 leave-out:", {k: round(v, 4) for k, v in loo.items()}, "->", ok4, flush=True)
    e5, _ = est("e12", "DD_e12_alt", SEED + 2)
    ok5 = bool(e5["eta"] < 0 and e1["lo"] <= e5["eta"] <= e1["hi"])
    print(f"E5 hours 9-14 and 18-22 as day: eta {e5['eta']:+.4f} [{e5['lo']:+.4f}, {e5['hi']:+.4f}] -> {ok5}", flush=True)
    e6, _ = est("e12", "D_e12_main", SEED + 3)
    ok6 = bool(e6["eta"] < 0 and e6["lo"] <= e1["eta"] <= e6["hi"] and e1["lo"] <= e6["eta"] <= e1["hi"])
    print(f"E6 no control: eta {e6['eta']:+.4f} [{e6['lo']:+.4f}, {e6['hi']:+.4f}] vs Portugal control {e1['eta']:+.4f} -> {ok6}", flush=True)
    e6b, _ = est("e12", "DD_e12_main", SEED + 4, fe=True)
    ok6b = bool(e6b["eta"] < 0 and e1["lo"] <= e6b["eta"] <= e1["hi"] and e6b["p"] <= 0.10)
    print(f"E6b year intercepts: eta {e6b['eta']:+.4f} one-sided p {e6b['p']:.4f} [{e6b['lo']:+.4f}, {e6b['hi']:+.4f}] -> {ok6b}", flush=True)
    e7 = {}
    for i, k in enumerate(("t62", "t63", "t64")):
        ek, ak = est(k, f"DD_{k}_main", SEED + 10 + i)
        e7[k] = ek
        print(f"E7 {tariff[k]}: eta {ek['eta']:+.4f} p {ek['p']:.4f} [{ek['lo']:+.4f}, {ek['hi']:+.4f}] mean|doseDiff| {ak.dose.abs().mean():.3f}", flush=True)
    by_year = {int(y): eta_plain(g.dose_e12, g.DD_e12_main) for y, g in full.groupby("year")}
    print("E8 by year:", {k: round(v, 3) for k, v in by_year.items()}, "| up", round(eu, 3), "down", round(ed, 3), flush=True)
    keep = ~full.month.isin([4, 10])
    s = full[keep]
    print(f"E8 (description) Portugal-control without 1 Apr and 1 Oct: eta {eta_plain(s.dose, s.DD_e12_main):+.4f} ({len(s)} events)", flush=True)
    summ = pd.DataFrame([
        dict(rule="E1", passed=ok1, **e1), dict(rule="E2", passed=ok2, eta=eu, p=np.nan, lo=ed, hi=np.nan), dict(rule="E3", passed=ok3, **e3),
        dict(rule="E4", passed=ok4, eta=min(loo.values()), p=np.nan, lo=max(loo.values()), hi=np.nan), dict(rule="E5", passed=ok5, **e5),
        dict(rule="E6", passed=ok6, **e6), dict(rule="E6b", passed=ok6b, **e6b)] + [dict(rule=f"E7 {k}", passed=np.nan, **v) for k, v in e7.items()])
    summ.round(5).to_csv(T.OUT / "calendar_national_estimate_summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(summ.round(4).to_string(index=False))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
