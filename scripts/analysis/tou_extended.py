"""Pre-registered extended two-channel regression (docs/specs/2026-11-11-tou-hardening-design.md, "Pre-registration: the extended two-channel regression").

Monthly evening-peak (18-21h vs night) DDD, working days vs weekends and holidays, E0 against Portugal (also France, LASSO errors, and industry E1-E6 as a placebo
outcome), V2 pre-window (2018-2020 without March-June 2020), one estimate per month 2021-06 -> 2023-12, each against the pre-window alone. Regressors per month from ESIOS 1001 and
1876 (working days, evening vs night, change in ln relative price against the old flat 44): x_charge (actual charges, energy held at its window mean) and x_energy (actual energy
term, charges held at their October-December 2021 mean). DDD_m = a + eps_c x_charge + eps_e x_energy, Newey-West (3 lags), also weighted by 1/se^2, and with a linear trend.
Writes outputs/tables/tou_extended_{months,coef}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_ddd_robust as R  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as E  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

PRE_END = pd.Timestamp("2020-12-31")
HOURS = [18, 19, 20, 21]
FIRST, LAST = pd.Timestamp("2021-06-01"), pd.Timestamp("2023-12-31")
SUMMER_A = 5.46  # charge-cut test window A, Portugal, percent


def regressors():
    def hourly(i):
        d = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")
        d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
        loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
        return pd.DataFrame({"date": loc.dt.tz_localize(None).dt.normalize().to_numpy(), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})
    p = hourly(1001).merge(hourly(1876), on=["date", "hour"])
    p = p[(p.date >= FIRST) & (p.date <= LAST) & (p.date.dt.dayofweek < 5)].copy()
    p["E"] = p.v1001 - p.v1876
    p["blk"] = np.where(p.hour.isin(HOURS), "b", np.where(p.hour < 8, "n", "x"))
    day = p[p.blk != "x"].groupby(["date", "blk"])[["E", "v1876"]].mean().unstack()
    Eb, En, Cb, Cn = day[("E", "b")], day[("E", "n")], day[("v1876", "b")], day[("v1876", "n")]
    ref = (day.index >= "2021-10-01") & (day.index <= "2021-12-31")
    Ebar_b, Ebar_n, Cs_b, Cs_n = Eb.mean(), En.mean(), Cb[ref].mean(), Cn[ref].mean()
    old = lambda a, b: np.log((a + E.OLD) / (b + E.OLD))
    xc = np.log((Ebar_b + Cb) / (Ebar_n + Cn)) - old(Ebar_b, Ebar_n)
    xe = np.log((Eb + Cs_b) / (En + Cs_n)) - old(Eb, En)
    out = pd.DataFrame({"x_charge": xc, "x_energy": xe}).dropna()
    out["ym"] = out.index.strftime("%Y-%m")
    print("reference charges Oct-Dec 2021: evening %.1f night %.1f; window mean energy: evening %.1f night %.1f" % (Cs_b, Cs_n, Ebar_b, Ebar_n), flush=True)
    return out.groupby("ym").mean()


def estimate(x, s, e):
    keep = ((x.date <= PRE_END) | ((x.date >= s) & (x.date <= e))) & ~x.date.between(*E.COVID)
    return E.contrasts_of(E.classed(x[keep], HOURS), s, e), keep


def monthly(x, lasso=False):
    rows = []
    for s in pd.date_range(FIRST, LAST, freq="MS"):
        e = s + pd.offsets.MonthEnd(0)
        (r, keep) = estimate(x, s, e)
        (b, se), _, _ = r
        row = dict(ym=s.strftime("%Y-%m"), ddd=b, se=se)
        if lasso:
            lb, lse = E.lasso_cells(E.classed(x[keep], HOURS), s, e)
            row.update(lasso=lb, lasso_se=lse)
        rows.append(row)
        print(row, flush=True)
    return pd.DataFrame(rows).set_index("ym")


def nw(X, y, lags=3, w=None):
    if w is not None:
        X, y = X * np.sqrt(w)[:, None], y * np.sqrt(w)
    n = len(y)
    A = np.linalg.inv(X.T @ X)
    b = A @ X.T @ y
    u = X * (y - X @ b)[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        G = u[L:].T @ u[:-L]
        S += (1 - L / (lags + 1)) * (G + G.T)
    V = A @ S @ A * n / (n - X.shape[1])
    return b, np.sqrt(np.diag(V))


def reg(df, ycol, trend=False, weight=None):
    df = df.dropna(subset=[ycol] + ([weight] if weight else []))  # months with no estimate (industry 2021-06) drop out
    cols = [np.ones(len(df)), df.x_charge.to_numpy(), df.x_energy.to_numpy()]
    names = ["const", "eps_charge", "eps_energy"]
    if trend:
        cols.append(np.arange(len(df)) / 12.0)  # position in the kept months
        names.append("trend_per_year")
    w = None if weight is None else (1.0 / df[weight] ** 2).to_numpy()
    b, se = nw(np.column_stack(cols), df[ycol].to_numpy(), w=w)
    return {n: (bb, ss, bb / ss) for n, bb, ss in zip(names, b, se)}


def main():
    base = D.prep(T.build("e0", end="2023-12-31"))
    xf = R.with_france(base)
    ind = D.prep(T.build("ind", end="2023-12-31"))
    reg_x = regressors()
    pt = monthly(xf.assign(d=xf.d_pt), lasso=True)
    fr = monthly(xf.assign(d=xf.d_fr))
    ib = monthly(ind)
    # paper-style LASSO (per area and hour, calendar and temperature interactions, 10-fold one-SE, no trend)
    es_e, pt_e = L.errors(base)
    ind_e, _ = L.errors(ind)
    pl = {"E0": es_e - pt_e, "industry": ind_e - pt_e}
    pap = {}
    for lab, err, xx in (("pl", pl["E0"], base), ("ipl", pl["industry"], ind)):
        rows = []
        for s0 in pd.date_range(FIRST, LAST, freq="MS"):
            b, se = L.cell_ddd(xx, err, s0, s0 + pd.offsets.MonthEnd(0))
            rows.append(dict(ym=s0.strftime("%Y-%m"), ddd=b, se=se))
        pap[lab] = pd.DataFrame(rows).set_index("ym")
    for lab, (s0, e0) in {"pre in-sample 2018-2020": ("2018-01-01", "2020-12-31"), "evening window Jun-Sep 2021": ("2021-06-01", "2021-09-30"),
                          "A 2021-06-01..09-15": ("2021-06-01", "2021-09-15"), "B 2021-09-16..12-31": ("2021-09-16", "2021-12-31")}.items():
        b, se = L.cell_ddd(base, pl["E0"], pd.Timestamp(s0), pd.Timestamp(e0))
        print(f"paper LASSO {lab}: E0 DDD {100 * b:.2f}% (se {100 * se:.2f})", flush=True)
    m = reg_x.join(pt.add_prefix("pt_")).join(fr.add_prefix("fr_")).join(ib.add_prefix("ind_")).join(pap["pl"].add_prefix("pl_")).join(pap["ipl"].add_prefix("ipl_"))
    m.round(5).to_csv(T.OUT / "tou_extended_months.csv")
    pd.set_option("display.width", 220)
    print((m * 1).round(4).to_string())
    rules = {}
    # 1 identification
    corr = float(np.corrcoef(m.x_charge, m.x_energy)[0, 1])
    print(f"corr(x_charge, x_energy) = {corr:.3f}; sd x_charge {m.x_charge.std():.3f}, sd x_energy {m.x_energy.std():.3f}")
    rows = []
    for lab, ycol, kw in (("Portugal OLS", "pt_ddd", {}), ("Portugal weighted", "pt_ddd", {"weight": "pt_se"}), ("Portugal trend", "pt_ddd", {"trend": True}),
                          ("France OLS", "fr_ddd", {}), ("LASSO OLS", "pt_lasso", {}), ("industry OLS", "ind_ddd", {}),
                          ("paper LASSO OLS", "pl_ddd", {}), ("paper LASSO weighted", "pl_ddd", {"weight": "pl_se"}), ("paper LASSO trend", "pl_ddd", {"trend": True}), ("paper LASSO industry", "ipl_ddd", {})):
        r = reg(m, ycol, **kw)
        for k, (b, se, t) in r.items():
            rows.append(dict(spec=lab, term=k, coef=b, se=se, t=t))
        print(lab, {k: (round(v[0], 3), round(v[2], 2)) for k, v in r.items()}, flush=True)
    coef = pd.DataFrame(rows)
    coef.round(4).to_csv(T.OUT / "tou_extended_coef.csv", index=False)
    g = lambda spec, term: coef[(coef.spec == spec) & (coef.term == term)].iloc[0]
    c, e = g("Portugal OLS", "eps_charge"), g("Portugal OLS", "eps_energy")
    top = m[(m.x_energy >= m.x_energy.quantile(0.75)) & (m.index >= "2021-10")]
    print("RULE 1 identification:", abs(corr) < 0.7 and m.x_charge.std() >= 0.05 and m.x_energy.std() >= 0.05)
    print("RULE 2 charge channel:", c.coef < 0 and c.t <= -2 and -0.18 <= c.coef <= -0.045, f"(eps_c {c.coef:.3f}, t {c.t:.2f})")
    print("RULE 3 energy does not carry it:", not (e.coef < 0 and e.t <= -2 and abs(e.coef) >= abs(c.coef)), f"(eps_e {e.coef:.3f}, t {e.t:.2f})")
    print("RULE 4 controls:", g("France OLS", "eps_charge").coef <= 0, g("LASSO OLS", "eps_charge").coef <= 0, g("Portugal weighted", "eps_charge").coef < 0)
    for sp in ("paper LASSO OLS", "paper LASSO weighted", "paper LASSO trend", "paper LASSO industry"):
        print(sp, "eps_c %.3f (t %.2f)  eps_e %.3f (t %.2f)" % (g(sp, "eps_charge").coef, g(sp, "eps_charge").t, g(sp, "eps_energy").coef, g(sp, "eps_energy").t))
    print("RULE 5 placebo:", abs(g("industry OLS", "eps_charge").t) < 2, f"(industry eps_c {g('industry OLS', 'eps_charge').coef:.3f}, t {g('industry OLS', 'eps_charge').t:.2f})")
    tr = g("Portugal trend", "eps_charge")
    print("RULE 6 drift:", tr.coef < -0.02, f"(eps_c with trend {tr.coef:.3f}, t {tr.t:.2f})")
    print("RULE 7 high-energy months past the cut:", bool((100 * top.pt_ddd.abs() <= SUMMER_A).all()), top[["x_energy", "pt_ddd"]].round(4).to_dict("index"))


if __name__ == "__main__":
    main()
