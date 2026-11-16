"""Estimation rules E1-E8 of docs/specs/2026-11-17-calendar-boundary-design.md: the real boundary windows are opened here.

    .venv/bin/python scripts/analysis/calendar_boundary_estimate.py

Real events: the 34 boundary-years of calendar_boundary_dose.csv (3.0TD top-period log price change; 2021 tolls and charges approximation). DD = D(Serveis) - D(Residencial); D = S(Y) - S(2019, same date); S from
calendar_boundary_noise.py. eta = sum(dose DD) / sum(dose^2). Randomization: doses permuted within year across the real, placebo (1 Feb, 1 May, 1 Sep) and mid-month events of the same year (10,000 draws),
one-sided p = (1 + #{eta_perm <= eta}) / (1 + N); interval eta - [q97.5, q2.5]. E8 uses REN national consumption (local Lisbon time, Portuguese holidays) in place of Residencial, dropping months 4 and 10 and the
boundary-years 2023-07 and 2024-06. Writes outputs/tables/calendar_boundary_estimate*.csv. Seed 20261117.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendar_boundary_noise as CB  # noqa: E402
import tou_did as T  # noqa: E402

ROOT, SEED, NPERM = T.ROOT, 20261117, 10000


def lr_alt(D):
    p = D.groupby(["date", "sector", "band"]).value.sum().unstack("band")
    return np.log((p.b2 + p.b3).where(p.b2 + p.b3 > 0)) - np.log(p.night.where(p.night > 0))


def lr_pt():
    d = pd.read_parquet(ROOT / "data/ren/ren_production_15min.parquet")
    d = d[d.series == "Consumption"].drop_duplicates("utc_timestamp")
    loc = pd.DatetimeIndex(d.utc_timestamp).tz_convert("Europe/Lisbon")
    x = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": d.value_mw.to_numpy()})
    night = x[x.hour < 6].groupby("date").v.sum()
    day = x[x.hour >= 6].groupby("date").v.sum()
    s = np.log(day) - np.log(night)
    s.index = pd.MultiIndex.from_product([s.index, ["pt"]], names=["date", "sector"]) if False else pd.MultiIndex.from_arrays([s.index, ["pt"] * len(s)], names=["date", "sector"])
    return s


def eta(dose, dd):
    return float((dose * dd).sum() / (dose ** 2).sum())


def perm_dist(pool, col, rng):
    """pool: DataFrame with year, dose (0 for placebo/mid), col. Permute doses within year; return eta_perm array."""
    ss = float((pool.dose ** 2).sum())
    groups = [(g.dose.to_numpy(), g[col].to_numpy()) for _, g in pool.groupby("year")]
    out = np.empty(NPERM)
    for r in range(NPERM):
        out[r] = sum((rng.permutation(d) * v).sum() for d, v in groups) / ss
    return out


def rand_stats(e, dist, two_sided=False):
    p = (1 + np.sum(np.abs(dist) >= abs(e))) / (1 + len(dist)) if two_sided else (1 + np.sum(dist <= e)) / (1 + len(dist))
    return dict(eta=e, p=p, lo=e - np.quantile(dist, 0.975), hi=e - np.quantile(dist, 0.025))


def main():
    D = CB.load()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    lr, la = CB.daily(D), lr_alt(D)
    lp = lr_pt()
    dz = pd.read_csv(ROOT / "outputs/tables/calendar_boundary_dose.csv")
    ev = pd.read_csv(ROOT / "outputs/tables/calendar_boundary_noise.csv")
    rows = []
    for _, r in dz.iterrows():
        Y, m = int(r.year), int(r.month)
        t, b = pd.Timestamp(Y, m, 1), pd.Timestamp(2019, m, 1)
        row = dict(kind="real", year=Y, month=m, dose=float(r.log_dose), step_eur=float(r.step_eur))
        for sec in ("serv", "res", "ind"):
            row[f"D_{sec}"] = CB.s_stat(lr, sec, t, hes) - CB.s_stat(lr, sec, b, hes)
            row[f"Da_{sec}"] = CB.s_stat(la, sec, t, hes) - CB.s_stat(la, sec, b, hes)
        row["D_pt"] = CB.s_stat(lp, "pt", t, hpt) - CB.s_stat(lp, "pt", b, hpt)
        rows.append(row)
    R = pd.DataFrame(rows)
    R["DD_serv"], R["DD_ind"], R["DD_alt"] = R.D_serv - R.D_res, R.D_ind - R.D_res, R.Da_serv - R.Da_res
    R["DD_pt"] = R.D_serv - R.D_pt
    pl = ev[ev.kind.isin(["placebo", "mid-month"])].copy()
    pl["dose"] = 0.0
    pool = pd.concat([R[["year", "dose", "DD_serv", "D_res"]], pl[["year", "dose", "DD_serv", "D_res"]]], ignore_index=True)
    rng = np.random.default_rng(SEED)
    dist = perm_dist(pool, "DD_serv", rng)
    e1 = rand_stats(eta(R.dose, R.DD_serv), dist)
    print(f"E1 eta {e1['eta']:+.4f} one-sided p {e1['p']:.4f} interval [{e1['lo']:+.4f}, {e1['hi']:+.4f}] ({len(R)} events)", flush=True)
    ok1 = bool(-1 <= e1["eta"] <= 0 and e1["p"] <= 0.05 and e1["hi"] < 0)
    up, dn = R[R.dose > 0], R[R.dose < 0]
    eu, ed = eta(up.dose, up.DD_serv), eta(dn.dose, dn.DD_serv)
    ok2 = bool(eu < 0 and ed < 0)
    print(f"E2 eta_up {eu:+.4f} ({len(up)} events), eta_down {ed:+.4f} ({len(dn)} events) -> {ok2}", flush=True)
    dres = perm_dist(pool.assign(DD_serv=pool.D_res), "DD_serv", np.random.default_rng(SEED + 1))
    e3 = rand_stats(eta(R.dose, R.D_res), dres, two_sided=True)
    ok3 = bool(e3["p"] > 0.05 and abs(e3["eta"]) < abs(e1["eta"]) / 3)
    print(f"E3 Residencial alone eta {e3['eta']:+.4f}, two-sided p {e3['p']:.4f} -> {ok3}", flush=True)
    lo_, hi_ = e1["lo"], e1["hi"]
    loo = {}
    for y in sorted(R.year.unique()):
        s = R[R.year != y]
        loo[f"year {y}"] = eta(s.dose, s.DD_serv)
    for m in sorted(R.month.unique()):
        s = R[R.month != m]
        loo[f"month {m}"] = eta(s.dose, s.DD_serv)
    ok4 = bool(all(v < 0 and lo_ <= v <= hi_ for v in loo.values()))
    print("E4 leave-out:", {k: round(v, 4) for k, v in loo.items()}, "->", ok4, flush=True)
    ea = eta(R.dose, R.DD_alt)
    ok5 = bool(ea < 0 and lo_ <= ea <= hi_)
    print(f"E5 bands 12-24 as day: eta {ea:+.4f} -> {ok5}", flush=True)
    print(f"E6 half pass-through range: eta {e1['eta']:+.4f} to {2 * e1['eta']:+.4f} (dose approximation; actual 2022-25 tolls not read)", flush=True)
    by_year = {int(y): eta(g.dose, g.DD_serv) for y, g in R.groupby("year")}
    ei = eta(R.dose, R.DD_ind)
    print(f"E7 by year {({k: round(v, 3) for k, v in by_year.items()})}; Indústria eta {ei:+.4f}", flush=True)
    keep = ~(R.month.isin([4, 10]) | ((R.year == 2023) & (R.month == 7)) | ((R.year == 2024) & (R.month == 6)))
    s = R[keep]
    ep = eta(s.dose, s.DD_pt)
    ok8 = bool(ep < 0 and lo_ <= ep <= hi_)
    print(f"E8 Portuguese control: eta {ep:+.4f} ({len(s)} events) -> {ok8}", flush=True)
    summ = pd.DataFrame([
        dict(rule="E1", passed=ok1, **e1), dict(rule="E2", passed=ok2, eta=eu, p=np.nan, lo=ed, hi=np.nan), dict(rule="E3", passed=ok3, **e3), dict(rule="E4", passed=ok4, eta=min(loo.values()), p=np.nan, lo=max(loo.values()), hi=np.nan),
        dict(rule="E5", passed=ok5, eta=ea, p=np.nan, lo=np.nan, hi=np.nan), dict(rule="E8", passed=ok8, eta=ep, p=np.nan, lo=np.nan, hi=np.nan)])
    summ.round(5).to_csv(T.OUT / "calendar_boundary_estimate_summary.csv", index=False)
    R.round(5).to_csv(T.OUT / "calendar_boundary_estimate.csv", index=False)
    print(summ.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
