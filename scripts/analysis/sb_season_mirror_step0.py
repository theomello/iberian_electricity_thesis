"""Step zero of the small-business season-mirror design (docs/specs/2026-11-23-small-business-season-mirror-design.md).

    .venv/bin/python scripts/analysis/sb_season_mirror_step0.py

Placebo years only (E0 = ESIOS 1201 is cut at 2020-02-29 right after loading, asserted). S0 data, S1 seal, Z1 price
tables (old 3.0A and new 3.0TD power terms, read from the BOE XML and PDF, both readings compared), S2 noise gate.
Per placebo year Y (1 June Y -> end of February Y+1; months Jun-Sep and Jan-Feb; 1 January dropped), cell = (month,
day type, hour), s = 100 x load / daily mean; per-year raw WLS s_Y(c) = alpha_Y(h) + b_Y D(c), weights = days in cell.
D = old 3.0A within-day rank - new 3.0TD within-day rank (spec step 3). Gate: eta_MDE of the non-working-day leg <= 0.15.
Writes outputs/tables/sb_season_mirror_step0{,_years}.csv and outputs/tables/tou_power_term_30.csv.
Deterministic.
"""
import html
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pypdf
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

ROOT = TS.ROOT
OUT = ROOT / "outputs" / "tables"
RAW_TARIFF = ROOT / "data" / "tariffs" / "raw"
SEAL = pd.Timestamp("2020-02-29")
PLACEBO = [2014, 2015, 2016, 2017, 2018, 2019]
SUMMER_M, WINTER_M = [6, 7, 8, 9], [1, 2]
E_PRICE = 100.81
GATE = 0.15
TOP = set(range(9, 14)) | set(range(18, 22))   # new 3.0TD top-of-season hours, working days
MID = {8, 14, 15, 16, 17, 22, 23}
LEGS = {"nw": dict(nonworking=True, drop_hours=set()),
        "wm": dict(nonworking=False, drop_hours=set(range(18, 22))),
        "we": dict(nonworking=False, drop_hours=set())}

# Z1 values (EUR/kW-year) and where they are printed; each is searched for in the XML and in the PDF text.
Z1 = {
    "old_3.0A": ("BOE-A-2014-1052", "Peaje 3.0A", [40.728885, 24.437330, 16.291555]),
    "new_3.0TD_TD": ("BOE-A-2021-4565", "3.0 TD", [10.646876, 9.302956, 3.751315, 2.852114, 1.145308, 1.145308]),
    "new_3.0TD_charge": ("BOE-A-2021-6390", "2", [8.950109, 4.478963, 3.254069, 3.254069, 3.254069, 1.491685]),
}


def fmt(v):
    return f"{v:.6f}".replace(".", ",")


def z1():
    """Both readings must contain each row's six (or three) values as one consecutive run, in order."""
    out = {}
    for key, (boe, _label, vals) in Z1.items():
        run = " ".join(fmt(v) for v in vals)
        x = open(RAW_TARIFF / f"{boe}.xml", encoding="utf-8", errors="ignore").read()
        x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x)))
        p = " ".join(pg.extract_text() or "" for pg in pypdf.PdfReader(RAW_TARIFF / f"{boe}.pdf").pages)
        p = re.sub(r"\s+", " ", p)
        out[key] = (run in x, run in p)
    # independent arithmetic check: transport + distribution = the T&D row (BOE-A-2021-4565 annex I 1.a)
    tr = [1.730663, 1.466482, 0.649068, 0.511293, 0.092472, 0.092472]
    di = [8.916213, 7.836474, 3.102247, 2.340821, 1.052836, 1.052836]
    td_ok = all(abs(a + b - c) < 1e-6 for a, b, c in zip(tr, di, Z1["new_3.0TD_TD"][2]))
    return out, td_ok


def power_table_30():
    s = TS.schedule(pd.date_range("2019-01-01", "2019-12-31"))
    g = s[s.tariff == "3.0"]
    new = [a + b for a, b in zip(Z1["new_3.0TD_TD"][2], Z1["new_3.0TD_charge"][2])]
    rows = []
    for regime, col, vals in (("old", "old_period", Z1["old_3.0A"][2]), ("new", "new_period", new)):
        for p, h in g.groupby(col).size().items():
            rows.append(dict(tariff="3.0", regime=regime, period=int(p), hours=int(h), eur_kw_year=vals[p - 1],
                             w_eur_mwh=1000 * vals[p - 1] / h))
    return pd.DataFrame(rows)


def holidays():
    return TS.holidays()


def nonworking(dates, hol):
    d = pd.DatetimeIndex(dates)
    return (d.dayofweek >= 5) | d.isin(list(hol)) | ((d.month == 1) & (d.day == 6))


def new_rank(date, hour, nw):
    if nw or hour < 8:
        return 3
    return 1 if hour in TOP else 2


def d_table():
    """D by (season, day type, hour), from old_period_3 and the rank mapping; checked against new_period_6."""
    rows = []
    for date, season in ((pd.Timestamp("2019-07-10"), "S"), (pd.Timestamp("2020-01-15"), "W")):  # Wednesdays
        for nw in (False, True):
            for h in range(24):
                old = TS.old_period_3(date, h)
                pn = TS.new_period_6(date, h, nw)
                # consistency: rank 3 <=> P6; rank 1 <=> base period of the season
                r = new_rank(date, h, nw)
                assert (r == 3) == (pn == 6), (date, h, nw, pn)
                rows.append(dict(season=season, nw=nw, hour=h, D=old - r))
    t = pd.DataFrame(rows).pivot_table(index=["nw", "hour"], columns="season", values="D")
    # the spec's table (hour-beginning)
    exp = {}
    for h in range(24):
        wd = (1, 1) if h in (9, 10) else (0, 1) if h in (11, 12, 13) else (-1, 0) if h == 14 else (1, 0) if h in range(18, 22) else (0, 0)
        nwv = (0, 0) if h < 8 else (-2, -1) if h in range(11, 15) else (-1, -2) if h in range(18, 22) else (-1, -1)
        exp[(False, h)], exp[(True, h)] = wd, nwv
    for (nw, h), (s_, w_) in exp.items():
        assert (t.loc[(nw, h), "S"], t.loc[(nw, h), "W"]) == (s_, w_), (nw, h, t.loc[(nw, h)].to_dict(), (s_, w_))
    return t


def load_e0():
    x = CT.esios_load([1201])
    x = x[x.date <= SEAL].copy()          # seal: applied at once
    assert x.date.max() <= SEAL
    return x


def year_frame(x, y, hol):
    d0, d1 = pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y + 1}-02-28") + pd.offsets.MonthEnd(0)
    f = x[(x.date >= d0) & (x.date <= d1) & x.date.dt.month.isin(SUMMER_M + WINTER_M)].copy()
    f = f[~((f.date.dt.month == 1) & (f.date.dt.day == 1))]
    expected = pd.date_range(d0, d1)
    expected = expected[expected.month.isin(SUMMER_M + WINTER_M) & ~((expected.month == 1) & (expected.day == 1))]
    n_full = f.groupby("date").v.count()
    full_days = n_full[n_full == 24].index
    coverage = len(f) / (24 * len(expected))
    f = f[f.date.isin(full_days)]
    f["s"] = 100 * f.v / f.groupby("date").v.transform("mean")
    f["nw"] = nonworking(f.date, hol)
    f["m"] = f.date.dt.month
    return f, coverage


def cells(f):
    c = f.groupby(["m", "nw", "hour"]).agg(s=("s", "mean"), days=("date", "nunique")).reset_index()
    c["season"] = np.where(c.m.isin(SUMMER_M), "S", "W")
    return c


def attach_D(c, dt):
    c = c.copy()
    c["D"] = [dt.loc[(bool(nw), h), s] for nw, h, s in zip(c.nw, c.hour, c.season)]
    return c


def wls_b(c, hour_col="hour", extra=None):
    hours = sorted(c[hour_col].unique())
    X = np.column_stack([(c[hour_col].to_numpy() == h).astype(float) for h in hours] + [c.D.to_numpy()]
                        + ([c[e].to_numpy() for e in extra] if extra else []))
    w = np.sqrt(c.days.to_numpy())
    coef = np.linalg.lstsq(X * w[:, None], c.s.to_numpy() * w, rcond=None)[0]
    return float(coef[len(hours)])


def leg_cells(c, leg):
    spec = LEGS[leg]
    return c[(c.nw == spec["nonworking"]) & ~c.hour.isin(spec["drop_hours"])]


def ident_hours(leg):
    return [11, 12, 13, 14, 18, 19, 20, 21] if leg == "nw" else [11, 12, 13, 14] if leg == "wm" else [11, 12, 13, 14, 18, 19, 20, 21]


def mix_weights():
    def ld(i):
        d = CT.esios_load([i])
        return d[(d.date >= "2024-06-01") & (d.date <= "2026-04-30")]
    a, b = ld(1209), ld(2532)
    cov = (len(a) / (24 * 699), len(b) / (24 * 699))  # 2024-06-01 .. 2026-04-30 = 699 days
    j = a.merge(b, on=["date", "hour"], suffixes=("_2", "_3"))
    hol = holidays()
    j["nw"] = nonworking(j.date, hol)
    j["m"] = j.date.dt.month
    day = j.groupby(["date", "nw", "m"])[["v_2", "v_3"]].sum().reset_index()
    day["w"] = day.v_3 / (day.v_2 + day.v_3)
    w = day.groupby(["m", "nw"]).w.mean()
    j["s3"] = 100 * j.v_3 / j.groupby("date").v_3.transform("mean")
    s3 = j.groupby(["m", "nw", "hour"]).s3.mean()
    return w, s3, cov


def dose_per_step(pt, full=True):
    """d-bar per leg: mean over identifying hours of |dlnp(S,h) - dlnp(W,h)| / |D(S,h) - D(W,h)|, day-weighted by month."""
    hol = holidays()
    dates = pd.date_range("2021-06-01", "2022-02-28")
    dates = dates[dates.month.isin(SUMMER_M + WINTER_M) & ~((dates.month == 1) & (dates.day == 1))]
    s = TS.schedule(dates)
    s = s[s.tariff == "3.0"].copy()
    # old periods depend on the clock season, not on the year: use the same date's old period (already in schedule)
    w = pt.set_index(["regime", "period"]).w_eur_mwh
    wo = s.old_period.map(lambda p: w[("old", p)]) if full else 0.0
    wn = s.new_period.map(lambda p: w[("new", p)]) if full else 0.0
    s["dlnp"] = np.log((E_PRICE + s.new_price + wn) / (E_PRICE + s.old_price + wo))
    s["nw"] = nonworking(s.date, hol)
    s["season"] = np.where(s.date.dt.month.isin(SUMMER_M), "S", "W")
    g = s.groupby(["nw", "season", "hour"]).dlnp.mean()
    dt = d_table()
    out = {}
    for leg in LEGS:
        nw = LEGS[leg]["nonworking"]
        vals = []
        for h in ident_hours(leg):
            dD = dt.loc[(nw, h), "S"] - dt.loc[(nw, h), "W"]
            if dD == 0:
                continue
            vals.append(abs(g[(nw, "S", h)] - g[(nw, "W", h)]) / abs(dD))
        out[leg] = float(np.mean(vals))
    return out


def inference(bs, years):
    bs, years = np.asarray(bs, float), np.asarray(years, float)
    S = len(bs)
    m, s = bs.mean(), bs.std(ddof=1)
    q_mean = stats.t.ppf(0.95, S - 1) + stats.t.ppf(0.80, S - 1)
    mde = q_mean * s * np.sqrt(1 + 1 / S)
    mde_norm = (stats.norm.ppf(0.95) + stats.norm.ppf(0.80)) * s * np.sqrt(1 + 1 / S)
    slope, icpt = np.polyfit(years, bs, 1)
    resid = bs - (icpt + slope * years)
    s_e = np.sqrt((resid ** 2).sum() / (S - 2))
    se_pred = s_e * np.sqrt(1 + 1 / S + (2021 - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum())
    q_tr = stats.t.ppf(0.95, S - 2) + stats.t.ppf(0.80, S - 2)
    return dict(S=S, m=m, s=s, q=q_mean, mde=mde, mde_normal=mde_norm, trend_slope=slope, trend_se_pred=se_pred,
                mde_trend=q_tr * se_pred)


def main():
    pd.set_option("display.width", 220)
    hol = holidays()
    dt = d_table()
    print("D table verified against the spec (season S/W by day type and hour).")

    z, td_ok = z1()
    z1_pass = all(a and b for a, b in z.values()) and td_ok
    print("Z1:", {k: f"xml {a}, pdf {b}" for k, (a, b) in z.items()}, "| T+D sum check", td_ok, "->", "pass" if z1_pass else "FAIL")
    pt = power_table_30()
    pt.to_csv(OUT / "tou_power_term_30.csv", index=False)

    x = load_e0()
    print(f"S1 seal: E0 rows end {x.date.max().date()} (<= {SEAL.date()})")
    rows, cov = [], {}
    for y in PLACEBO:
        f, cov[y] = year_frame(x, y, hol)
        c = attach_D(cells(f), dt)
        for leg in LEGS:
            rows.append(dict(year=y, leg=leg, b=wls_b(leg_cells(c, leg)), cells=len(leg_cells(c, leg)),
                             days=int(f[f.nw == LEGS[leg]["nonworking"]].date.nunique())))
        if y == PLACEBO[0]:
            cell_days = c.set_index(["m", "nw", "hour"]).days
    yrs = pd.DataFrame(rows)
    s0_e0 = all(v >= 0.99 for v in cov.values())

    w, s3, mixcov = mix_weights()
    s0_mix = all(v >= 0.95 for v in mixcov)
    print("S0: E0 coverage by year", {k: round(v, 4) for k, v in cov.items()}, "| 1209/2532 coverage", tuple(round(v, 3) for v in mixcov),
          "->", "pass" if (s0_e0 and s0_mix) else "FAIL")

    dbar_full, dbar_energy = dose_per_step(pt, True), dose_per_step(pt, False)
    dbar = dbar_full if z1_pass else dbar_energy

    summ = []
    for leg in LEGS:
        b = yrs[yrs.leg == leg].sort_values("year")
        inf = inference(b.b, b.year)
        nw = LEGS[leg]["nonworking"]
        idc = [(m, nw, h) for m in SUMMER_M + WINTER_M for h in ident_hours(leg)]
        wts = np.array([cell_days.get(k, 0) for k in idc], float)
        wbar = float(np.average([w[(m, nw)] for m, nw, _ in idc], weights=wts))
        sbar = float(np.average([s3[k] for k in idc], weights=wts))
        mde3 = inf["mde"] / wbar
        eta = (mde3 / sbar) / dbar[leg]
        eta_tr = (inf["mde_trend"] / wbar / sbar) / dbar[leg]
        eta_en = (mde3 / sbar) / dbar_energy[leg]
        summ.append(dict(leg=leg, **inf, wbar=wbar, sbar_B=sbar, dbar=dbar[leg], dbar_full=dbar_full[leg],
                         dbar_energy=dbar_energy[leg], mde3=mde3, eta_mde=eta, eta_mde_trend=eta_tr,
                         eta_mde_energy_dose=eta_en, gate=(eta <= GATE) if leg == "nw" else np.nan))
    S = pd.DataFrame(summ)
    yrs.to_csv(OUT / "sb_season_mirror_step0_years.csv", index=False)
    S.assign(z1_pass=z1_pass, s0_pass=s0_e0 and s0_mix).to_csv(OUT / "sb_season_mirror_step0.csv", index=False)
    print("\nPlacebo b_Y (E0 points per rank step):")
    print(yrs.pivot(index="year", columns="leg", values="b").round(4).to_string())
    print()
    print(S.round(4).to_string(index=False))
    nwrow = S[S.leg == "nw"].iloc[0]
    print(f"\nS2 gate (non-working leg): eta_MDE = {nwrow.eta_mde:.3f} vs {GATE} -> {'PASS' if nwrow.eta_mde <= GATE else 'FAIL'}"
          f" (trend-null eta_MDE {nwrow.eta_mde_trend:.3f}, energy-only dose {nwrow.eta_mde_energy_dose:.3f})")


if __name__ == "__main__":
    main()
