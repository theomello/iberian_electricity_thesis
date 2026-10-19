#!/usr/bin/env python3
"""T3 of the nuclear-cuts design: does a reactor's departure from price-taking follow
its owners' stake in the price?

    .venv/bin/python scripts/analysis/nuclear_cuts_conduct.py
    .venv/bin/python scripts/analysis/nuclear_cuts_conduct.py --operator-split
    .venv/bin/python scripts/analysis/nuclear_cuts_conduct.py --slope-test     # on the stored panel

Design: docs/specs/2026-10-19-nuclear-cuts-design.md §4 T3; T2 in
notes/rq-nuclear-cuts.md §5. Reads T2's reactor-days (nuclear_cuts_benchmark.py).

OUTCOME. dev_rd = actual cut minus the price-taker's cut at c_acct (fuel at book value),
MW, daily mean. Positive: the reactor cut where a price-taker would run (excess);
negative: it ran where a price-taker would cut (missing).

REGRESSOR. X_rd = the reactor's owners' n_full / |RD′|, €/MWh, daily mean, each owner
weighted by its share of the reactor (design §2, rule 3). n_full is the owner's exposed
net position (firm_x.py) with its share of its reactors' chosen cuts added back: the
position it would hold if its reactors ran in full, since a cut lowers n by itself.
|RD′| is firm_x's rivals' slope (`slope_net`, MW per €/MWh). Market power predicts
dev rising with X: a large net seller cuts more than a price-taker, a net buyer less.

INSTRUMENTS, owner-share-weighted like X:
  Z_unpl, Z_plan  the owners' shares of OTHER reactors' declared unplanned and planned
                  lost output, GW, leaving out the same site (Almaraz 1-2, Ascó 1-2)
  Z_wind          the owners' regional wind deviation, REE's D-1 forecast split by
                  realised regional shares (regional_wind_offer_test.py), GW
  Z_rain          the owners' own-catchment rain over the 30 days before (H30)
EFFECTS reactor x month and day of week; week clusters; Anderson-Rubin sets on a grid.
Sample 2019-01-01 (REE's forecasts start) to 2026-05-31; reactor-days T1 kept
(no other declared loss, no whole-day stop).

SIGN TEST. X split by the sign of the owners' n_full over the previous 7 days, each
instrument interacted with the same sign: market power predicts the same positive slope
on both sides (cut above cost when selling, run below cost when buying).

IMPLIED β. dev = γ X; the price-taker's own response to price is s = d cut / d p_exp.
With cut = g(p − c − β X), β = −γ / s. s from cut on p_exp and X (instrumented),
reactor x month effects.

NULL BAND. Price-takers whose true cost differs from c_acct by a common δ (−5, 0, +5)
plus a daily error ε ~ N(0, SIGMA): their cut minus the c_acct price-taker's is run
through the same IV. The band is the range of γ over δ and seeds.

OPERATOR SPLIT (--operator-split). The planned-outage instrument split by who runs the
other reactor (CNAT: Almaraz and Trillo; ANAV: Ascó and Vandellós; Iberdrola: Cofrentes):
the same operator at another site, another operator, and, as a check outside the
instruments, the reactor's own site. If refuelling moves the cut only when the same
operator runs the other reactor, it is fleet management, not the price stake.

OUTPUTS: outputs/tables/nuclear_cuts_conduct_panel.parquet, nuclear_cuts_conduct.csv,
nuclear_cuts_operator_split.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from iv_two_endog import _ar_parts, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from outage_offer_test import demean  # noqa: E402
from omie_common import day_periods_utc  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402
from nuclear_cuts_benchmark import simulate  # noqa: E402
from regional_wind_offer_test import forecasts, own_capacity, regional_cf  # noqa: E402
from outage_rain_offer_test import daily_rain  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_PANEL = TABLES / "nuclear_cuts_conduct_panel.parquet"
OUT = TABLES / "nuclear_cuts_conduct.csv"
START, END = "2019-01-01", "2026-05-31"
SITE = {"ALZ1": "ALZ", "ALZ2": "ALZ", "ASC1": "ASC", "ASC2": "ASC", "COF1": "COF", "TRL1": "TRL", "VAN2": "VAN"}
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
FREE = {"economic"}
GRID = np.round(np.arange(-400, 400.0001, 0.25), 2)
SIGMA, DELTAS, SEEDS = 5.0, (-5.0, 0.0, 5.0), range(5)
INST = ["Z_unpl", "Z_plan", "Z_wind", "Z_rain"]
OP_SITE = {"ALZ": "CNAT", "TRL": "CNAT", "ASC": "ANAV", "VAN": "ANAV", "COF": "Iberdrola"}
OUT_SPLIT = TABLES / "nuclear_cuts_operator_split.csv"
OUT_SLOPE = TABLES / "nuclear_cuts_slope_test.csv"


def local_date(utc: pd.Series) -> pd.Series:
    return utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()


def reactor_hours() -> pd.DataFrame:
    """unit, utc, date, cut_mw (chosen), unpl_mw, plan_mw (declared)."""
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet",
                        columns=["unit", "utc", "cls", "lost_decl_mw", "lost_undecl_mw"])
    h["date"] = local_date(h.utc)
    h["cut_mw"] = h.lost_undecl_mw.fillna(0) + np.where(h.cls.isin(FREE), h.lost_decl_mw, 0.0)
    h["unpl_mw"] = np.where(h.cls == "unplanned", h.lost_decl_mw, 0.0)
    h["plan_mw"] = np.where(h.cls == "planned", h.lost_decl_mw, 0.0)
    return h[["unit", "utc", "date", "cut_mw", "unpl_mw", "plan_mw"]]


def shares(h: pd.DataFrame) -> pd.DataFrame:
    """unit, date, firm, share: each reactor's owners by date (the five firms only)."""
    k = h[["unit", "date"]].drop_duplicates()
    a = attach_owners(k, spells(), value_cols=())
    a = a.rename(columns={"group": "firm"})
    return a[a.firm.isin(FIRMS)][["unit", "date", "firm", "share"]]


def firm_hours() -> pd.DataFrame:
    """firm, utc, n (MW), slope (MW per €/MWh): firm_x averaged over the UTC hour."""
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "firm", "net_mw", "slope_net"])
    x["date"] = pd.to_datetime(x.date)
    n = x[["date", "period"]].drop_duplicates().groupby("date").period.max()
    utc = pd.concat([pd.DataFrame({"date": d, "period": range(1, k + 1), "utc": day_periods_utc(d.date(), int(k))})
                     for d, k in n.items()])
    utc["utc"] = pd.to_datetime(utc.utc, utc=True).dt.floor("h")
    x = x.merge(utc, on=["date", "period"])
    return x.groupby(["firm", "utc"], as_index=False).agg(n=("net_mw", "mean"), slope=("slope_net", "mean"))


def owner_days(h: pd.DataFrame, sh: pd.DataFrame) -> pd.DataFrame:
    """firm, date: n_full (MW), X_full (€/MWh) daily means; and per reactor the owner's
    dose of other reactors' declared outages, by site (for the exclusion)."""
    hs = h.merge(sh, on=["unit", "date"])
    hs["site"] = hs.unit.map(SITE)
    add = hs.assign(a=hs.cut_mw * hs.share).groupby(["firm", "utc"]).a.sum().rename("add").reset_index()
    f = firm_hours().merge(add, on=["firm", "utc"], how="left").fillna({"add": 0.0})
    f["n_full"] = f.n + f["add"]
    f["X_full"] = (f.n_full / f.slope).where(f.slope > 0)
    f["date"] = local_date(f.utc)
    od = f.groupby(["firm", "date"]).agg(n_full=("n_full", "mean"), X_full=("X_full", "mean")).reset_index()
    # each owner's declared outage dose by site, daily mean GW
    dz = hs.assign(u=hs.unpl_mw * hs.share / 1000, p=hs.plan_mw * hs.share / 1000)
    dz = dz.groupby(["firm", "site", "date"])[["u", "p"]].sum() / 24
    return od, dz.reset_index()


def wind_days(groups) -> pd.DataFrame:
    fc = forecasts()
    cf = regional_cf(fc)
    k = own_capacity(groups)
    w = k.merge(cf, on="nuts_id")
    w["Wdev_fc"] = w.K_gw * w.dev_fc
    w = w.groupby(["group", "utc"]).Wdev_fc.sum(min_count=1).reset_index()
    w["date"] = local_date(w.utc)
    return w.groupby(["group", "date"]).Wdev_fc.mean().rename("wind").reset_index().rename(columns={"group": "firm"})


def build_panel() -> pd.DataFrame:
    d = pd.read_parquet(TABLES / "nuclear_cuts_benchmark_daily.parquet")
    d = d[(d.date >= START) & (d.date <= END)].reset_index(drop=True)
    h = reactor_hours()
    sh = shares(h)
    od, dz = owner_days(h, sh)
    wd = wind_days(FIRMS)
    rn = daily_rain(pd.DatetimeIndex(sorted(d.date.unique())))
    rn = rn.rename(columns={"group": "firm"})[["firm", "date", "H30"]]
    rows = d[["unit", "date"]].merge(sh, on=["unit", "date"])
    rows["site"] = rows.unit.map(SITE)
    rows = rows.merge(od, on=["firm", "date"], how="left").merge(wd, on=["firm", "date"], how="left")
    rows = rows.merge(rn, on=["firm", "date"], how="left")
    rows[["wind", "H30"]] = rows[["wind", "H30"]].fillna(0.0)
    # other reactors' outages: the owner's dose at every site but the reactor's own
    tot = dz.groupby(["firm", "date"])[["u", "p"]].sum().rename(columns={"u": "u_all", "p": "p_all"})
    own = dz.rename(columns={"u": "u_site", "p": "p_site"})
    rows = rows.merge(tot.reset_index(), on=["firm", "date"], how="left")
    rows = rows.merge(own, on=["firm", "site", "date"], how="left")
    rows = rows.fillna({"u_all": 0.0, "p_all": 0.0, "u_site": 0.0, "p_site": 0.0})
    rows["Z_unpl"] = rows.u_all - rows.u_site
    rows["Z_plan"] = rows.p_all - rows.p_site
    # the same outages by who runs the other reactor: the same operator at another site,
    # another operator, and the reactor's own site (left out of Z_unpl and Z_plan)
    ps = dz.pivot_table(index=["firm", "date"], columns="site", values=["u", "p"], aggfunc="sum", fill_value=0.0)
    ps.columns = [f"{v}_{st}" for v, st in ps.columns]
    rows = rows.merge(ps.reset_index(), on=["firm", "date"], how="left")
    rows["op"] = rows.site.map(OP_SITE)
    split = []
    for v, name in (("u", "unpl"), ("p", "plan")):
        same = np.zeros(len(rows))
        other = np.zeros(len(rows))
        for st, op in OP_SITE.items():
            x = rows.get(f"{v}_{st}", pd.Series(0.0, index=rows.index)).fillna(0.0).to_numpy()
            same += x * ((rows.site != st) & (rows.op == op)).to_numpy()
            other += x * (rows.op != op).to_numpy()
        rows[f"Z_{name}_sameop"], rows[f"Z_{name}_otherop"] = same, other
        rows[f"Z_{name}_samesite"] = rows[f"{v}_site"]
        assert np.allclose(same + other, rows[f"Z_{name}"]), f"operator split of Z_{name} does not add up"
        split += [f"Z_{name}_sameop", f"Z_{name}_otherop", f"Z_{name}_samesite"]
    agg = {}
    for c, z in (("X_full", "X"), ("n_full", "n_full"), ("Z_unpl", "Z_unpl"), ("Z_plan", "Z_plan"),
                 ("wind", "Z_wind"), ("H30", "Z_rain"), *((c, c) for c in split)):
        rows[f"w_{z}"] = rows[c] * rows.share
        agg[z] = (f"w_{z}", "sum")
    r = rows.groupby(["unit", "date"]).agg(**agg, share_cov=("share", "sum")).reset_index()
    d = d.merge(r, on=["unit", "date"], how="inner")
    d["n_full"] = d.n_full / 1000.0                          # GW
    d["dev"] = d.cut_mw - d.sim_c_acct
    d = d.sort_values(["unit", "date"]).reset_index(drop=True)
    # owners' sign over the previous 7 days
    prev = d.groupby("unit").n_full.transform(lambda s: s.shift(1).rolling(7, min_periods=4).mean())
    d["sell_prev"] = prev > 0
    d["um"] = d.unit + "_" + d.date.dt.strftime("%Y%m")
    d["dow"] = d.date.dt.dayofweek.astype(str)
    d["wk"] = d.date.dt.strftime("%G%V")
    return d


def ar_grid(y, x, Z, W, cl, level=0.95):
    C, V = _ar_parts(y, x[:, None], Z, W, cl)
    L = Z.shape[1]
    crit = chi2.ppf(level, L)

    def stat(g):
        wv = np.array([1.0, -g])
        b = C @ wv
        S = sum(wv[a] * wv[c] * V[a][c] for a in range(2) for c in range(2))
        return float(b @ np.linalg.solve(S, b))

    keep = np.array([stat(g) <= crit for g in GRID])
    iv, start, prev = [], None, None
    for g, k in zip(GRID, keep):
        if k and start is None:
            start = g
        if not k and start is not None:
            iv.append((start, prev))
            start = None
        prev = g
    if start is not None:
        iv.append((start, GRID[-1]))
    txt = " U ".join(f"[{'-inf' if lo == GRID[0] else f'{lo:.1f}'}, {'+inf' if hi == GRID[-1] else f'{hi:.1f}'}]"
                     for lo, hi in iv) or "empty"
    return txt, float(chi2.sf(stat(0.0), L))


def matrices(d: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return demean(d[cols].to_numpy(float), [pd.factorize(d.um)[0], pd.factorize(d.dow)[0]])


def iv(d: pd.DataFrame, y: str, zs: list[str], label: str, ws: tuple = (), quiet: bool = False) -> dict:
    s = d.dropna(subset=[y, "X", *zs, *ws]).reset_index(drop=True)
    M = matrices(s, [y, "X", *zs, *ws])
    Y, X, Z = M[:, 0], M[:, [1]], M[:, 2:2 + len(zs)]
    W = M[:, 2 + len(zs):]
    cl = s.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    F = sw_f(X, Z, W, cl, 0)
    row = {"spec": label, "y": y, "instruments": "+".join(zs), "controls": "+".join(ws), "n": len(s),
           "b": b[0], "se": float(np.sqrt(V[0, 0])), "F": F, "sd_X": float(s.X.std())}
    if quiet:
        return row
    ar, p0 = ar_grid(Y, X[:, 0], Z, W, cl)
    fs = ols(X[:, 0], np.column_stack([Z, W]), cl)
    XW = np.column_stack([X, W])
    bl = ols(Y, XW, cl)
    row |= {"ar_set": ar, "ar_p0": p0, "b_ls": bl[0][0], "se_ls": bl[1][0]}
    if ws:
        bw, Vw = tsls_k(Y, np.column_stack([X, W]), np.column_stack([Z, W]), np.zeros((len(Y), 0)), cl)
        row |= {f"b_{w}": bw[1 + k] for k, w in enumerate(ws)}
    fs_txt = " ".join(f"{z} {fs[0][k]:+.2f}({fs[1][k]:.2f})" for k, z in enumerate(zs))
    print(f"  {label:44s} n={len(s):5d}  FS [{fs_txt}]  F {F:5.1f}  IV {b[0]:+7.2f} ({np.sqrt(V[0, 0]):6.2f})"
          f"  AR p(0) {p0:.3f} set {ar}  LS {bl[0][0]:+.2f} ({bl[1][0]:.2f})", flush=True)
    return row


def sign_test(d: pd.DataFrame, zs: list[str]) -> dict:
    s = d.dropna(subset=["dev", "X", *zs, "sell_prev"]).reset_index(drop=True)
    on = s.sell_prev.to_numpy(float)
    for c in ["X", *zs]:
        s[f"{c}_s"] = s[c] * on
        s[f"{c}_b"] = s[c] * (1 - on)
    xs = ["X_s", "X_b"]
    zz = [f"{z}_{k}" for z in zs for k in ("s", "b")]
    M = matrices(s, ["dev", *xs, *zz])
    Y, X, Z = M[:, 0], M[:, 1:3], M[:, 3:]
    W = np.zeros((len(Y), 0))
    cl = s.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    F = [sw_f(X, Z, W, cl, j) for j in range(2)]
    print(f"  sign test ({len(s)} days, {int(on.sum())} after a selling week): "
          f"sellers {b[0]:+.2f} ({np.sqrt(V[0, 0]):.2f}, F {F[0]:.1f})  buyers {b[1]:+.2f} ({np.sqrt(V[1, 1]):.2f}, F {F[1]:.1f})")
    return {"spec": "sign test", "b_sell": b[0], "se_sell": np.sqrt(V[0, 0]), "F_sell": F[0],
            "b_buy": b[1], "se_buy": np.sqrt(V[1, 1]), "F_buy": F[1], "n": len(s), "n_sell": int(on.sum())}


def main() -> int:
    d = build_panel()
    d.to_parquet(OUT_PANEL, index=False)
    rows = []
    print(f"\n{len(d):,} reactor-days, {d.unit.nunique()} reactors, {d.date.min().date()} -> {d.date.max().date()}; "
          f"owner share covered: {d.share_cov.min():.2f}-{d.share_cov.max():.2f}")
    print("\nby reactor: mean dev (MW), mean X (€/MWh), share of days after a selling week, sd of each instrument")
    print(d.groupby("unit").agg(dev=("dev", "mean"), X=("X", "mean"), sell=("sell_prev", "mean"),
                                **{z: (z, "std") for z in INST}).round(3).to_string())
    print(f"\ndescriptive: dev on 1[owners sold the previous week], reactor x month + dow effects:")
    s = d.dropna(subset=["dev", "sell_prev"]).reset_index(drop=True)
    M = matrices(s.assign(sp=s.sell_prev.astype(float)), ["dev", "sp"])
    bb = ols(M[:, 0], M[:, [1]], s.wk.to_numpy())
    print(f"  selling-week days minus buying-week days: {bb[0][0]:+.1f} MW (se {bb[1][0]:.1f})")
    rows.append({"spec": "dev on selling week", "b": bb[0][0], "se": bb[1][0], "n": len(s)})

    print("\nMAIN: dev (MW) on X (€/MWh), reactor x month + day-of-week effects, week clusters")
    specs = [("all four instruments", INST), ("reactor outages", ["Z_unpl", "Z_plan"]),
             ("regional wind", ["Z_wind"]), ("rain", ["Z_rain"]), ("outages + wind", ["Z_unpl", "Z_plan", "Z_wind"])]
    for lab, zs in specs:
        rows.append(iv(d, "dev", zs, lab))
    main_b = rows[1]["b"]
    e = d[d.date >= "2024-01-01"]
    print("\n2024-2026 only")
    for lab, zs in specs[:3]:
        rows.append(iv(e, "dev", zs, f"2024-26 {lab}"))
    print("\nwith the expected price as a control")
    rows.append(iv(d, "dev", INST, "all four + p_exp", ws=("p_exp",)))

    print("\nSIGN TEST")
    rows.append(sign_test(d, INST))

    print("\nIMPLIED β: cut (not dev) on X (instrumented) and p_exp (exogenous)")
    r = iv(d, "cut_mw", INST, "cut on X and p_exp", ws=("p_exp",))
    s_p = r.get("b_p_exp", np.nan)
    print(f"  s = d cut / d p_exp = {s_p:+.2f} MW per €/MWh;  implied β = −γ/s = {-r['b'] / s_p:+.3f} "
          f"(γ {r['b']:+.2f}, se {r['se']:.2f} -> β se ≈ {r['se'] / abs(s_p):.3f})")
    rows.append(r | {"s_p": s_p, "beta_implied": -r["b"] / s_p, "beta_se_approx": r["se"] / abs(s_p)})

    print("\nNULL BAND: price-takers with cost c_acct + δ + ε (ε ~ N(0, 5)), their cut minus the c_acct price-taker's")
    nulls = []
    base = simulate(d, LIMITS, "c_acct")          # the c_acct price-taker on the same days
    for delta in DELTAS:
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            t = d.copy()
            t["c_null"] = t.c_acct + delta + rng.normal(0, SIGMA, len(t))
            t["sim_null"] = simulate(t, LIMITS, "c_null")
            t["dev_null"] = t.sim_null - base
            nr = iv(t, "dev_null", INST, f"null δ {delta:+.0f} seed {seed}", quiet=True)
            nulls.append(nr | {"delta": delta, "seed": seed})
    nb = pd.DataFrame(nulls)
    print(nb.groupby("delta").b.agg(["min", "mean", "max"]).round(2).to_string())
    print(f"  band over all: [{nb.b.min():+.2f}, {nb.b.max():+.2f}];  actual main {main_b:+.2f}")
    rows.extend(nb.to_dict("records"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT_PANEL.relative_to(ROOT)}, {OUT.relative_to(ROOT)}")
    return 0


def _limits() -> pd.DataFrame:
    import nuclear_cuts_benchmark as nb
    d = pd.read_parquet(TABLES / "nuclear_cuts_daily.parquet")
    d = d[d.form.isin(["partial", "none"])].sort_values(["unit", "date"]).reset_index(drop=True)
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet", columns=["unit", "utc", "cap_mw", "sched_mw"])
    h["date"] = local_date(h.utc)
    return nb.limits(d, h, 0.02)


def operator_split() -> int:
    """Refuelling elsewhere, by who runs the other reactor. Price stake: a refuelling
    moves dev by what it moves X, whoever runs it. Fleet management: only the same
    operator's refuelling matters, whatever it does to X."""
    d = build_panel()
    d.to_parquet(OUT_PANEL, index=False)
    rows = []
    comp = ["Z_plan_samesite", "Z_plan_sameop", "Z_plan_otherop"]
    rest = ["Z_unpl", "Z_wind", "Z_rain"]
    print("\nplanned-outage dose by component: share of reactor-days above 0, mean GW when above 0")
    print(pd.DataFrame({c: [(d[c] > 0).mean(), d.loc[d[c] > 0, c].mean()] for c in comp},
                       index=["share > 0", "mean GW"]).round(3).to_string())
    print(d.assign(op=d.unit.map(SITE).map(OP_SITE)).groupby("op")[comp].apply(lambda g: (g > 0).mean()).round(3).to_string())
    for lab, s0 in (("2019-2026", d), ("2024-2026", d[d.date >= "2024-01-01"]),
                    ("2019-2026, CNAT reactors", d[d.unit.isin(["ALZ1", "ALZ2", "TRL1"])]),
                    ("2019-2026, ANAV reactors", d[d.unit.isin(["ASC1", "ASC2", "VAN2"])])):
        s = s0.dropna(subset=["dev", "X", *comp, *rest]).reset_index(drop=True)
        M = matrices(s, ["dev", "X", *comp, *rest])
        cl = s.wk.to_numpy()
        R = M[:, 2:]
        rf, fs = ols(M[:, 0], R, cl), ols(M[:, 1], R, cl)
        print(f"\n{lab}: {len(s):,} reactor-days. Jointly on all instruments, the planned-outage parts, per GW:")
        for k, c in enumerate(comp):
            ratio = rf[0][k] / fs[0][k] if abs(fs[0][k]) > 0 else np.nan
            print(f"  {c:16s} dev {rf[0][k]:+8.1f} ({rf[1][k]:6.1f})   X {fs[0][k]:+6.2f} ({fs[1][k]:5.2f})   ratio {ratio:+8.1f}")
            rows.append({"sample": lab, "term": c, "rf": rf[0][k], "rf_se": rf[1][k], "fs": fs[0][k],
                         "fs_se": fs[1][k], "n": len(s)})
        if "reactors" in lab:
            continue
        for zl, zs in (("same operator alone", ["Z_plan_sameop"]), ("other operator alone", ["Z_plan_otherop"]),
                       ("both", ["Z_plan_sameop", "Z_plan_otherop"]),
                       ("main, plan split", ["Z_unpl", "Z_plan_sameop", "Z_plan_otherop", "Z_wind", "Z_rain"])):
            rows.append(iv(s, "dev", zs, f"{lab}: {zl}") | {"sample": lab})
    pd.DataFrame(rows).to_csv(OUT_SPLIT, index=False)
    print(f"\nwrote {OUT_PANEL.relative_to(ROOT)}, {OUT_SPLIT.relative_to(ROOT)}")
    return 0


def slope_test() -> int:
    """Price motive or supply motive? A dose of D GW lost elsewhere moves the owners' n by
    about −0.86 D, and their X by that over |RD′|. A price motive acts through X, so its
    effect on dev should scale with 1/|RD′|: on steep days (small |RD′|) the same dose
    moves the price stake more. A supply motive (keeping the remaining reactors running
    to cover the owners' own retail) should not depend on |RD′|. So, on the T3 panel:

        dev = θ_Z · Z + θ_P · P + c · (1/|RD′|) + controls + effects,   P = 1000 Z / |RD′|

    P is the dose's move along the owners' residual demand, €/MWh. The owners' X on the
    same terms is the benchmark: a price motive makes dev = γ X, so dev loads on Z and P
    as γ times X does (same signs; Nash γ is the price-taker's cost slope). A supply motive
    makes dev follow the lost output: a loading on Z, none on P. The dose can only
    reduce a cut on a day the price-taker would cut, so the cut opportunity (Z × 1[the
    price-taker cuts], Z × expected margin) is controlled in a second version, and the
    third keeps only days the price-taker cuts."""
    d = pd.read_parquet(OUT_PANEL)
    sh = shares(d[["unit", "date"]].drop_duplicates())
    f = firm_hours()
    f["inv"] = (1.0 / f.slope).where(f.slope > 0)
    f["date"] = local_date(f.utc)
    fd = f.groupby(["firm", "date"]).inv.mean().rename("inv").reset_index()
    r = sh.merge(fd, on=["firm", "date"], how="left").dropna(subset=["inv"])
    r["w"] = r.inv * r.share
    g = r.groupby(["unit", "date"]).agg(w=("w", "sum"), cov=("share", "sum"))
    d = d.merge((g.w / g["cov"]).rename("inv").reset_index(), on=["unit", "date"], how="left")
    d["inv"] = d.inv * 1000.0                         # €/MWh per GW
    for z in ("Z_plan", "Z_plan_sameop", "Z_plan_otherop", "Z_wind"):
        d[z.replace("Z_", "P_")] = d[z] * d.inv
    d["simcut"] = (d.sim_c_acct > 0).astype(float)
    d["margin"] = d.p_exp - d.c_acct
    d["Zp_simcut"], d["Zp_margin"] = d.Z_plan * d.simcut, d.Z_plan * d.margin
    d["Zw_simcut"], d["Zw_margin"] = d.Z_wind * d.simcut, d.Z_wind * d.margin
    rows = []
    on = d[d.Z_plan > 0]
    print(f"days with an other-reactor planned dose: {len(on):,}; dose mean {on.Z_plan.mean():.3f} GW; "
          f"P mean {on.P_plan.mean():.2f} €/MWh, quartiles {on.P_plan.quantile([.25, .5, .75]).round(2).tolist()}")
    base = ["inv", "Z_unpl", "Z_rain"]
    specs = [
        ("refuelling", "dev", ["Z_plan", "P_plan", "Z_wind"] + base),
        ("refuelling, cut opportunity controlled", "dev",
         ["Z_plan", "P_plan", "Z_wind", "simcut", "margin", "Zp_simcut", "Zp_margin"] + base),
        ("refuelling, by operator", "dev",
         ["Z_plan_sameop", "P_plan_sameop", "Z_plan_otherop", "P_plan_otherop", "Z_wind"] + base),
        ("regional wind", "dev", ["Z_wind", "P_wind", "Z_plan", "simcut", "margin", "Zw_simcut", "Zw_margin"] + base),
        ("same terms, owners' n_full (GW)", "n_full", ["Z_plan", "P_plan", "Z_wind"] + base),
        ("same terms, owners' X (first stage)", "X", ["Z_plan", "P_plan", "Z_wind"] + base),
        ("wind terms, owners' X (first stage)", "X",
         ["Z_wind", "P_wind", "Z_plan", "simcut", "margin", "Zw_simcut", "Zw_margin"] + base),
    ]
    show = {"Z_plan", "P_plan", "Z_plan_sameop", "P_plan_sameop", "Z_plan_otherop", "P_plan_otherop",
            "Z_wind", "P_wind", "Zp_simcut", "Zp_margin"}
    for lab, s0 in (("2019-2026", d), ("2024-2026", d[d.date >= "2024-01-01"]),
                    ("2019-2026, days the price-taker cuts", d[d.simcut > 0])):
        print(f"\n{lab}")
        for name, y, xs in specs:
            if "price-taker cuts" in lab and ("opportunity" in name or "wind" in name):
                continue
            s = s0.dropna(subset=[y, *xs]).reset_index(drop=True)
            M = matrices(s, [y, *xs])
            b, se = ols(M[:, 0], M[:, 1:], s.wk.to_numpy())
            txt = "  ".join(f"{x} {b[k]:+.2f} ({se[k]:.2f})" for k, x in enumerate(xs) if x in show)
            print(f"  {name:40s} n={len(s):5d}  {txt}")
            for k, x in enumerate(xs):
                rows.append({"sample": lab, "spec": name, "y": y, "term": x, "b": b[k], "se": se[k], "n": len(s)})
    print("\nThe owners' X on the same terms is the benchmark: a price motive makes dev = γ X, so dev's")
    print("loadings on (Z, P) are γ times X's, same signs. A supply motive makes dev follow the lost")
    print("output itself: a loading on Z, none on P. Nash γ is the price-taker's cost slope: 1.5 MW per")
    print("€/MWh over 2019–2026, 3.3 in 2024–2026 (§6).")
    pd.DataFrame(rows).to_csv(OUT_SLOPE, index=False)
    print(f"\nwrote {OUT_SLOPE.relative_to(ROOT)}")
    return 0


LIMITS = None
if __name__ == "__main__":
    if "--slope-test" in sys.argv:
        raise SystemExit(slope_test())
    if "--operator-split" in sys.argv:
        raise SystemExit(operator_split())
    LIMITS = _limits()
    raise SystemExit(main())
