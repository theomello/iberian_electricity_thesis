#!/usr/bin/env python3
"""Does the hydro capacity a firm leaves unoffered follow the firm's price incentive?

    .venv/bin/python scripts/analysis/hydro_unoffered_incentive.py --build   # the unit-hour panel
    .venv/bin/python scripts/analysis/hydro_unoffered_incentive.py           # the regressions

`rq-water-value-forward.md` §5.5 – §5.9 found that Endesa and Naturgy offer only part of
their hydro capacity, and that about 80% of what they leave unoffered is not declared out
of service, not offered intraday and not held as reserve. §5.10 asks the test that was
left: does the unoffered share move with the firm's incentive to raise the price?

THE TEST, WITH AN EXAMPLE. On a Tuesday at 20:00 Endesa sells 6 GW more than it buys in the
auction and rivals offer only 300 MW per €/MWh around the price: its incentive X is
6,000 / 300 = €20/MWh, and withholding 100 MW of hydro there raises the price on all
its other output. At 04:00 the same day it is a net buyer, X is negative, and
withholding would raise the price it pays. If Endesa uses its hydro on the quantity margin, the share of hydro capacity it
leaves unoffered is higher at 20:00 than at 04:00, and on days of high incentive than on
days of low, after taking out what water and contracts would explain. If instead the
capacity is unoffered because there is no water for it, or because it is committed to
bilateral contracts, the share follows the reservoir's fill and the contract position, and
the incentive adds nothing.

DATA, per Spanish storage-hydro unit of the four large groups (EDP, Iberdrola, Endesa,
Naturgy) and hour, 2019-01 → 2025-09, built as in `hydro_unoffered_capacity.py`:
  C  `cab` max power;  O  MW offered in the auction;  B  MW delivered under bilateral
  contracts;  G = max(C − O − B, 0), the unoffered capacity
  U  MW declared unavailable in `indisp`;  E = min(U, G), the part outages explain;
  R = G − E, the part they do not.  So G/C = E/C + R/C and the two coefficients add.

THE INCENTIVE is the firm's X from `firm_x.py` (Hortaçsu & Puller's markup term): net
position n in the auction over the slope of its residual demand, hour by hour, exposed
basis (regulated pass-through suppliers out). Used as X̃ = (n − own storage hydro cleared
in the auction) / slope. The firm's own hydro sale is part of n, and a firm that leaves
more unoffered sells less of it, so n falls with the dependent variable by construction;
taking the unit-hour's own hydro out of n removes that. The firm's other plant and its
retail purchases are what is left. X as built is run as a check (it must be biased down).

WATER STATE: the MITECO basin fill anomaly of the unit's own demarcation, known two days
before (`hydro_cost_daily.fill_anom`), and the expected running share cf_s (fill and
season). Units without a MITECO series (Iberdrola's JUCA, Endesa's TEES and EBRERZ)
are left out of the main sample. CONTRACTS: the bilateral share B / C.

SPECIFICATIONS (weights C, effects absorbed by alternating projections, week-clustered errors;
details and the pass / fail / stop rules in `rq-water-value-forward.md` §5.10):
  P1 unit x month, hour, weekday; fill, cf_s, log C     P2 P1 + bilateral share B/C and its lag
  P3 unit x month + hour of sample (firms in one hour)  P4 P2 on days `indisp` covers
  P5 P2 on all 16 units, without the fill               P6 unit + month (additive), hour, weekday
  P7 as P2 without hour-of-day effects                  P2f, P3f firm-specific nuisance (post hoc)
Checks: X lagged / led a day, X as built, not winsorised, leave one firm out, unit x calendar
month + unit x year. P6, P7, P2f, P3f were added after the first run, each with its rule written
in the note before it ran.

`--build` writes outputs/cache/hydro_unoffered_incentive_panel.parquet (not committed). The
regression step reads it and writes outputs/tables/hydro_unoffered_incentive.csv (the
estimates), hydro_unoffered_incentive_checks.csv and hydro_unoffered_incentive_controls.csv.
The rules for reading them are written in `rq-water-value-forward.md` §5.10 before the
first run.
"""
from __future__ import annotations

import faulthandler
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

faulthandler.dump_traceback_later(900, exit=True)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from counterfactual_hydro import EPOCH, bilateral  # noqa: E402
from hydro_unoffered_capacity import CACHE, DATA, TABLES, declarations, groups, unavailable  # noqa: E402

PANEL = ROOT / "outputs/cache/hydro_unoffered_incentive_panel.parquet"
FOUR = ["EDP", "IBERDROLA", "ENDESA", "NATURGY"]
FIRST, LAST = "201901", "202509"
MIN_SLOPE = 5.0
WINSOR = (0.01, 0.99)


# --------------------------------------------------------------------------- the panel
def unit_hours(ym: str, g: pd.DataFrame, dec: pd.DataFrame) -> pd.DataFrame:
    """One month of unit-hours: C, O, A (cleared in the auction), B, U by cause."""
    units = g.unit.unique().tolist()
    h = pd.read_parquet(CACHE / f"hydro_{ym}.parquet", columns=["hid", "date", "unit", "mw", "cleared_mw", "withdrawn"])
    hids = np.arange(h.hid.min(), h.hid.max() + 1)
    h = h[h.unit.isin(units)]
    o = h[(~h.withdrawn) & (h.mw > 0)].groupby(["hid", "unit"]).mw.sum().rename("O")
    a = h.groupby(["hid", "unit"]).cleared_mw.first().rename("A")
    c = pd.read_parquet(DATA / f"omie/cab/parquet/cab_{ym}.parquet", columns=["date", "unit", "max_power_mw"],
                        filters=[("unit", "in", units)])
    c = c.groupby(["unit", pd.to_datetime(c.date).rename("date")]).max_power_mw.max().rename("C").reset_index()
    grid = pd.MultiIndex.from_product([hids, units], names=["hid", "unit"]).to_frame(index=False)
    grid["date"] = EPOCH + pd.to_timedelta(grid.hid // 24, "D")
    d = grid.merge(c, on=["unit", "date"]).set_index(["hid", "unit"])
    d = d.join(o).join(a).join(bilateral(ym, units).rename("B")).join(unavailable(dec, g, hids)).fillna(0.0)
    return d[d.C > 0].reset_index()


def firm_incentive(first: str, last: str) -> pd.DataFrame:
    """(hid, firm) -> n, slope, X and the flags of firm_x.parquet; 24-period days only."""
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "resolution_min", "firm", "net_mw",
                                                           "slope_net", "X", "clean", "zero_price"])
    x["date"] = pd.to_datetime(x.date)
    x = x[x.firm.isin(FOUR) & (x.date >= pd.Timestamp(first + "01")) & (x.date < pd.Timestamp(last + "01") + pd.offsets.MonthBegin(1))]
    npd = x.groupby("date").period.transform("max")
    x = x[(x.resolution_min == 60) & (npd == 24)]                      # drops the 23- and 25-hour days
    x["hid"] = (x.date - EPOCH).dt.days * 24 + x.period - 1
    return x.drop(columns=["period", "resolution_min"])


def build() -> pd.DataFrame:
    g = groups()
    g = g[g.group.isin(FOUR)]
    dec, covered = declarations(g)
    months = [p.stem.split("_")[1] for p in sorted(CACHE.glob("hydro_2*.parquet"))]
    months = [m for m in months if FIRST <= m <= LAST]
    d = pd.concat([unit_hours(m, g, dec) for m in months], ignore_index=True)
    d["group"] = d.unit.map(g.drop_duplicates("unit").set_index("unit").group)
    d["U"] = (d.U_technical + d.U_water).clip(upper=d.C)
    d["G"] = (d.C - d.O - d.B).clip(lower=0)
    d["E"] = np.minimum(d.U, d.G)
    d["R"] = d.G - d.E
    d["covered"] = d.date.isin(covered)
    print(f"{len(d):,} unit-hours, {d.unit.nunique()} units", file=sys.stderr)

    # the incentive: firm-hour, own storage hydro's auction sale taken out of n
    own = d.groupby(["hid", "group"]).A.sum().rename("A_own").reset_index().rename(columns={"group": "firm"})
    x = firm_incentive(FIRST, LAST).merge(own, on=["hid", "firm"], how="left")
    x["A_own"] = x.A_own.fillna(0.0)
    x["Xex"] = np.where(x.slope_net >= MIN_SLOPE, (x.net_mw - x.A_own) / x.slope_net, np.nan)
    x["ok"] = x.clean & ~x.zero_price & x.X.notna()
    x = x.rename(columns={"firm": "group", "X": "Xbuilt"})[["hid", "group", "Xbuilt", "Xex", "ok", "net_mw", "A_own", "slope_net"]]
    lag = x[["hid", "group", "Xex"]].assign(hid=lambda v: v.hid + 24).rename(columns={"Xex": "Xex_lag"})
    lead = x[["hid", "group", "Xex"]].assign(hid=lambda v: v.hid - 24).rename(columns={"Xex": "Xex_lead"})
    d = d.merge(x, on=["hid", "group"], how="inner").merge(lag, on=["hid", "group"], how="left") \
         .merge(lead, on=["hid", "group"], how="left")
    bl = d[["hid", "unit", "B", "C"]].assign(hid=lambda v: v.hid + 24)
    bl["B_lag_share"] = bl.B / bl.C
    d = d.merge(bl[["hid", "unit", "B_lag_share"]], on=["hid", "unit"], how="left")

    w = pd.read_parquet(TABLES / "hydro_cost_daily.parquet", columns=["unit", "date", "fill_anom", "cf_s", "storage"])
    d = d.merge(w, on=["unit", "date"], how="left")
    d["hour"] = d.hid % 24
    d["month"] = d.date.dt.strftime("%Y%m")
    d["week"] = d.date.dt.strftime("%G%V")
    d["dow"] = d.date.dt.dayofweek
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(PANEL, index=False)
    print(f"wrote {PANEL.relative_to(ROOT)}: {len(d):,} unit-hours with an incentive observation "
          f"({d.ok.mean():.3f} clean, positive-price, slope >= {MIN_SLOPE:g})", file=sys.stderr)
    return d


def describe_panel(d: pd.DataFrame) -> None:
    """Sample sizes only: no relation between the incentive and the unoffered share."""
    pd.set_option("display.width", 200)
    print(d.groupby("group").agg(units=("unit", "nunique"), unit_hours=("hid", "size"), ok=("ok", "mean"),
                                 fill=("fill_anom", lambda s: s.notna().mean()),
                                 C_mw=("C", "mean")).round(3).to_string())


# --------------------------------------------------------------------------- the regressions
def absorb(M: np.ndarray, w: np.ndarray, factors: list[np.ndarray], tol: float = 1e-9, maxit: int = 300) -> np.ndarray:
    """Weighted alternating projections: the columns of M less the weighted mean within each factor."""
    M = M.astype(float).copy()
    sw = [np.bincount(f, weights=w) for f in factors]
    for _ in range(maxit):
        move = 0.0
        for f, s in zip(factors, sw):
            for j in range(M.shape[1]):
                m = np.bincount(f, weights=w * M[:, j]) / s
                M[:, j] -= m[f]
                move = max(move, np.abs(m).max())
        if len(factors) == 1 or move < tol * (1 + np.abs(M).max()):
            break
    return M


def wls_cluster(Y: np.ndarray, X: np.ndarray, w: np.ndarray, cl: np.ndarray):
    """B (k, m), se (k, m): weighted least squares of each column of Y on X, clustered on cl."""
    xtx = X.T @ (X * w[:, None])
    inv = np.linalg.inv(xtx)
    B = inv @ (X.T @ (Y * w[:, None]))
    E = Y - X @ B
    order = np.argsort(cl, kind="stable")
    cs = cl[order]
    starts = np.flatnonzero(np.r_[True, cs[1:] != cs[:-1]])
    G = len(starts)
    se = np.zeros_like(B)
    for j in range(Y.shape[1]):
        S = np.add.reduceat((X * (w * E[:, j])[:, None])[order], starts, axis=0)
        V = inv @ (S.T @ S) @ inv * G / (G - 1)
        se[:, j] = np.sqrt(np.diag(V))
    return B, se, G


DEPS = {"G": "G", "E": "E", "R": "R"}
FES = {
    "month": lambda d: [f(d.unit + d.month), f(d.hour), f(d.dow)],
    "hour": lambda d: [f(d.unit + d.month), f(d.hid)],
    "nohour": lambda d: [f(d.unit + d.month), f(d.dow)],
    "add": lambda d: [f(d.unit), f(d.month), f(d.hour), f(d.dow)],
    "season": lambda d: [f(d.unit + d.date.dt.month.astype(str)), f(d.unit + d.date.dt.year.astype(str)), f(d.hour), f(d.dow)],
}
CONTROLS = {
    "water": ["fill_anom", "cf_s", "logC"],
    "water+contract": ["fill_anom", "cf_s", "logC", "Bshare", "B_lag_share"],
    "nofill+contract": ["cf_s", "logC", "Bshare", "B_lag_share"],
}


def f(s: pd.Series) -> np.ndarray:
    return pd.factorize(s)[0]


def winsorise(d: pd.DataFrame, col: str) -> pd.Series:
    """col clipped at the 1st and 99th percentile of the firm-hours in the panel."""
    fh = d.drop_duplicates(["hid", "group"])
    lo, hi = fh[col].quantile(list(WINSOR))
    return d[col].clip(lo, hi)


def fit(d: pd.DataFrame, xcol: str, controls: list[str], fe: str, deps=("G", "E", "R"),
        by_firm: bool = False) -> tuple[list[dict], list[dict]]:
    """Weighted regression of each dep / C (in pp) on xcol + controls, with fixed effects `fe`.
    by_firm: hour-of-day and day-of-week effects and the controls' coefficients differ by firm.
    A control with no variation left after the fixed effects (log C within a unit-month, for a
    firm whose capacity never changes) is dropped. Returns (rows for xcol, rows for the controls)."""
    d = d.dropna(subset=[xcol] + controls)
    w = d.C.to_numpy()
    cols = {xcol: d[xcol].to_numpy()}
    for c in controls:
        if by_firm:
            for firm in sorted(d.group.unique()):
                cols[f"{c}|{firm}"] = np.where(d.group == firm, d[c], 0.0)
        else:
            cols[c] = d[c].to_numpy()
    regs = list(cols)
    Y = np.column_stack([100 * d[k] / d.C for k in deps])
    Z = np.column_stack(list(cols.values()))
    raw_var = np.average((Z[:, 0] - np.average(Z[:, 0], weights=w)) ** 2, weights=w)
    factors = FES[fe](d)
    if by_firm and fe == "month":
        factors = [factors[0], f(d.group + d.hour.astype(str)), f(d.group + d.dow.astype(str))]
    M = absorb(np.column_stack([Y, Z]), w, factors)
    Yd, Zd = M[:, :len(deps)], M[:, len(deps):]
    sd = np.sqrt(np.average(Zd ** 2, axis=0, weights=w))
    keep = [j for j in range(Zd.shape[1]) if sd[j] > 1e-6 * max(np.sqrt(np.average(Z[:, j] ** 2, weights=w)), 1e-12)]
    B = np.full((Zd.shape[1], len(deps)), np.nan)
    se = np.full_like(B, np.nan)
    Bk, sek, G = wls_cluster(Yd, Zd[:, keep], w, f(d.week))
    B[keep], se[keep] = Bk, sek
    base = {"n": len(d), "clusters": G, "units": d.unit.nunique(),
            "within_sd_X": sd[0], "x_var_left": sd[0] ** 2 / raw_var,
            "mean_G_over_C_pp": 100 * d.G.sum() / d.C.sum()}
    rows, crows = [], []
    for j, k in enumerate(deps):
        b, s_ = B[0, j], se[0, j]
        rows.append({**base, "dep": k, "beta_pp_per_eur": b, "se": s_, "lo": b - 1.96 * s_, "hi": b + 1.96 * s_,
                     "per_sd_pp": b * sd[0], "per_sd_lo": (b - 1.96 * s_) * sd[0], "per_sd_hi": (b + 1.96 * s_) * sd[0]})
        for i, c in enumerate(regs[1:], start=1):
            crows.append({"dep": k, "variable": c, "coef": B[i, j], "se": se[i, j], "within_sd": sd[i],
                          "per_sd_pp": B[i, j] * sd[i], "n": len(d)})
    return rows, crows


def prepare() -> pd.DataFrame:
    d = pd.read_parquet(PANEL)
    d = d[d.ok & d.Xex.notna()].copy()
    d["date"] = pd.to_datetime(d.date)
    d["logC"] = np.log(d.C)
    d["Bshare"] = d.B / d.C
    full = pd.read_parquet(PANEL, columns=["hid", "group", "Xex", "Xbuilt", "Xex_lag", "Xex_lead", "ok"])
    full = full[full.ok]
    for col, new in [("Xex", "X"), ("Xbuilt", "X_built"), ("Xex_lag", "X_lag"), ("Xex_lead", "X_lead")]:
        fh = full.drop_duplicates(["hid", "group"])[col]
        lo, hi = fh.quantile(list(WINSOR))
        d[new] = d[col].clip(lo, hi)
    d["X_raw"] = d.Xex
    return d


def specs(d: pd.DataFrame):
    """Yield (spec, scope, xcol, fe, controls, sample) for the main table."""
    main = d[d.fill_anom.notna()]
    for name, ctrl, fe, samp in [("P1", "water", "month", main), ("P2", "water+contract", "month", main),
                                 ("P3", "water+contract", "hour", main),
                                 ("P4", "water+contract", "month", main[main.covered]),
                                 ("P6", "water+contract", "add", main), ("P7", "water+contract", "nohour", main),
                                 ("P5", "nofill+contract", "month", d)]:
        yield name, "pooled", "X", fe, ctrl, samp
        if name in ("P2", "P3"):                               # added 2026-11-05 after the first run: see §5.10
            yield name + "f", "pooled", "X", fe, ctrl, samp
        if name != "P3":
            for firm in FOUR:
                yield name, firm, "X", fe, ctrl, samp[samp.group == firm]


def run() -> int:
    pd.set_option("display.width", 220)
    d = prepare()
    main = d[d.fill_anom.notna()]
    print(f"{len(d):,} unit-hours (all units), {len(main):,} in the main sample "
          f"({main.C.sum() / d.C.sum():.3f} of capacity-hours)")
    w_ = main.C.to_numpy(); y_ = (main.G / main.C).to_numpy()
    um = pd.factorize(main.unit + main.month)[0]
    ybar = np.bincount(um, weights=w_ * y_) / np.bincount(um, weights=w_)
    tot = np.average((y_ - np.average(y_, weights=w_)) ** 2, weights=w_)
    within = np.average((y_ - ybar[um]) ** 2, weights=w_)
    print(f"share of the weighted variance of G/C within unit-months: {within / tot:.3f}")
    est, ctl = [], []
    for spec, scope, x, fe, cname, samp in specs(d):
        r, c = fit(samp, x, CONTROLS[cname], fe, by_firm=spec.endswith("f"))
        est += [{"spec": spec, "scope": scope, "fe": fe, "controls": cname, **v} for v in r]
        if (scope == "pooled" or spec in ("P1", "P2")) and not spec.endswith("f"):
            ctl += [{"spec": spec, "scope": scope, **v} for v in c]
        print(f"  {spec} {scope}", file=sys.stderr, flush=True)
    est = pd.DataFrame(est)
    show = ["spec", "scope", "dep", "n", "clusters", "within_sd_X", "beta_pp_per_eur", "se", "lo", "hi", "per_sd_pp", "per_sd_lo", "per_sd_hi"]
    print("\nG/C, E/C and R/C (pp of capacity) on X-tilde (per €1/MWh; per within-sd):")
    print(est[show].round(3).to_string(index=False))

    # checks on P2
    chk = []
    p2 = main
    def add(label, scope, x, samp, fe="month", cname="water+contract"):
        r, _ = fit(samp, x, CONTROLS[cname], fe, deps=("G", "E", "R"))
        chk.extend({"check": label, "scope": scope, "fe": fe, **v} for v in r)
    def add6(label, x):
        add(label + ", P6", "pooled", x, p2, fe="add")
        for firm in FOUR:
            add(label + ", P6", firm, x, p2[p2.group == firm], fe="add")
    for label, x in [("X lagged one day", "X_lag"), ("X led one day (placebo)", "X_lead"), ("X as built (own hydro in)", "X_built")]:
        add6(label, x)
    for label, x in [("X lagged one day", "X_lag"), ("X led one day (placebo)", "X_lead"), ("X as built (own hydro in)", "X_built"),
                     ("X-tilde, not winsorised", "X_raw")]:
        add(label, "pooled", x, p2)
        for firm in FOUR:
            add(label, firm, x, p2[p2.group == firm])
        print(f"  check {label}", file=sys.stderr, flush=True)
    add("unit x calendar month + unit x year", "pooled", "X", p2, fe="season")
    for firm in FOUR:
        add("leave one firm out", f"without {firm}", "X", p2[p2.group != firm])
    chk = pd.DataFrame(chk)
    print("\nchecks on P2 (water + contract controls):")
    print(chk[["check", "scope", "dep", "n", "beta_pp_per_eur", "se", "lo", "hi", "per_sd_pp"]].round(3).to_string(index=False))

    ctl = pd.DataFrame(ctl)
    print("\ncontrols (P1, P2; per within-sd of each variable, pp of capacity), G/C:")
    print(ctl[(ctl.dep == "G")][["spec", "scope", "variable", "coef", "se", "per_sd_pp"]].round(3).to_string(index=False))

    est.to_csv(TABLES / "hydro_unoffered_incentive.csv", index=False)
    chk.to_csv(TABLES / "hydro_unoffered_incentive_checks.csv", index=False)
    ctl.to_csv(TABLES / "hydro_unoffered_incentive_controls.csv", index=False)
    verdict(est, chk)
    print(f"\nwrote hydro_unoffered_incentive{{,_checks,_controls}}.csv in {TABLES.relative_to(ROOT)}")
    return 0


def verdict(est: pd.DataFrame, chk: pd.DataFrame) -> None:
    """The rules of §5.10, evaluated as written."""
    g = est[est.dep == "G"].set_index(["spec", "scope"])
    P = lambda s: g.loc[(s, "pooled")]
    a = all(P(s).lo > 0 for s in ("P1", "P2", "P3"))
    firms = g.loc["P2"].drop("pooled")
    b = (firms.beta_pp_per_eur > 0).sum() >= 3 and not (firms.hi < 0).any()
    c_ = chk[(chk.dep == "G") & (chk.scope == "pooled")].set_index("check")
    lag, lead, built = c_.loc["X lagged one day"], c_.loc["X led one day (placebo)"], c_.loc["X as built (own hydro in)"]
    c = lag.lo > 0 and lead.beta_pp_per_eur < P("P2").beta_pp_per_eur
    d_ = built.beta_pp_per_eur < P("P2").beta_pp_per_eur
    e = P("P2").per_sd_pp >= 1.0
    e_ = est[(est.spec == "P2") & (est.scope == "pooled")].set_index("dep")
    share_R = e_.loc["R"].beta_pp_per_eur / e_.loc["G"].beta_pp_per_eur if e_.loc["G"].beta_pp_per_eur != 0 else np.nan
    share_E = e_.loc["E"].beta_pp_per_eur / e_.loc["G"].beta_pp_per_eur if e_.loc["G"].beta_pp_per_eur != 0 else np.nan
    f_ = share_R >= 0.8
    print("\nRULES OF §5.10")
    print(f"  (a) P1, P2, P3 pooled CI above zero: {a}   "
          f"[P1 {P('P1').beta_pp_per_eur:.3f} ({P('P1').lo:.3f}, {P('P1').hi:.3f}); P2 {P('P2').beta_pp_per_eur:.3f} "
          f"({P('P2').lo:.3f}, {P('P2').hi:.3f}); P3 {P('P3').beta_pp_per_eur:.3f} ({P('P3').lo:.3f}, {P('P3').hi:.3f})]")
    print(f"  (b) P2 per firm >=3 positive and none significantly negative: {b}   "
          f"{firms.beta_pp_per_eur.round(3).to_dict()}")
    print(f"  (c) lag CI above zero and lead below contemporaneous: {c}   lag {lag.beta_pp_per_eur:.3f} "
          f"({lag.lo:.3f}, {lag.hi:.3f}); lead {lead.beta_pp_per_eur:.3f} ({lead.lo:.3f}, {lead.hi:.3f})")
    print(f"  (d) X as built below X-tilde: {d_}   built {built.beta_pp_per_eur:.3f}")
    print(f"  (e) P2 per-sd effect >= 1 pp: {e}   {P('P2').per_sd_pp:.3f} ({P('P2').per_sd_lo:.3f}, {P('P2').per_sd_hi:.3f})")
    print(f"  (f) R carries >= 0.8 of the G coefficient: {f_}   R share {share_R:.2f}, E share {share_E:.2f}")
    print(f"  PASS: {a and b and c and d_ and e and f_ and share_E < 0.5}")
    fail_null = P("P1").per_sd_hi < 1.0 and P("P2").per_sd_hi < 1.0
    fail_neg = P("P2").hi < 0
    print(f"  FAIL (informative zero, per-sd upper end < 1 pp in P1 and P2): {fail_null}; "
          f"FAIL (significantly negative P2): {fail_neg}")
    s1 = lead.beta_pp_per_eur >= P("P2").beta_pp_per_eur
    s2 = (P("P2").per_sd_hi - P("P2").per_sd_lo) > 4.0
    s3 = np.sign(P("P1").beta_pp_per_eur) != np.sign(P("P3").beta_pp_per_eur) or \
        abs(P("P1").beta_pp_per_eur - P("P3").beta_pp_per_eur) > np.hypot(P("P1").se, P("P3").se)
    s4 = P("P2").x_var_left < 0.001
    for sp, lab in (("P6", "unit and month effects, additive"), ("P7", "no hour-of-day effects")):
        p6 = g.loc[sp]
        print(f"  {sp} ({lab}):", {k: (round(v.beta_pp_per_eur, 3), round(v.lo, 3), round(v.hi, 3),
                                       round(v.per_sd_pp, 3)) for k, v in p6.iterrows()})
    for sp in ("P2f", "P3f"):
        if (sp, "pooled") in g.index:
            r = g.loc[(sp, "pooled")]
            print(f"  post hoc {sp} (firm-specific hour, weekday and control effects): {r.beta_pp_per_eur:.3f} "
                  f"({r.lo:.3f}, {r.hi:.3f}), per sd {r.per_sd_pp:.3f}")
    print(f"  STOP: lead >= contemporaneous {s1}; per-sd CI wider than 4 pp {s2}; P1/P3 disagree {s3}; "
          f"X variance left < 0.1% {s4}  ->  {s1 or s2 or s3 or s4}")


if __name__ == "__main__":
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    raise SystemExit(describe_panel(build()) or 0 if args.build else run())
