#!/usr/bin/env python3
"""Does a known tax reach the combined cycles' declared cost? Spain's 2024 IVPEE steps.

    .venv/bin/python scripts/analysis/ivpee_tax_test.py

Framework spec §9.6: a tax moves cost, not n, so it tests the cost term c. The
Impuesto sobre el Valor de la Producción de Energía Eléctrica (IVPEE, Ley 15/2012)
takes 7% of the revenue of every Spanish generator and none from a Portuguese one in
the same auction. Suspended 2021-07-01 → 2023-12-31, it came back in three steps
(RDL 8/2023): 3.5% in 2024 Q1, 5.25% in Q2, 7% from 2024-07-01.

OUTCOME: the minimum-income condition's variable term (`cab`, €/MWh), the cost a
unit declares with its offer. Combined cycles in both countries declare it on
89–100% of days and revise it almost daily; Portuguese ones offered most of their
volume at 0 €/MWh in 2024, so their offer prices carry no cost. The term ends on
2025-03-18 (the SCO replaced it), which ends the sample.

PREDICTION. The tax is on revenue, so to keep revenue net of tax ≥ fixed + v × q a
Spanish unit must declare v/(1 − τ). In logs:

    log v_ud = α_u + δ_d + θ · ES_u · log(1 / (1 − τ_d)) + ε_ud,        θ = 1

Full pass-through gives θ = 1; a declared term that ignores the tax gives θ = 0.
Unit effects absorb efficiency and date effects the fuel and carbon prices: cost is
(gas + 0.2020 × CO2) / efficiency, a date term over a unit term.

PORTUGAL IS UNTREATED IN 2024. Portugal's clawback (Decreto-Lei 74/2013, Portaria
282/2019) charges producers per MWh for the IVPEE's price effect, suspended with it
from 2021 H2 to 2023. Combined cycles pay it only beyond 2,000 equivalent hours a
year, and in 2024 every Portuguese combined cycle ran under 1,200 (printed below,
from PDBF). The January step falls on New Year's Day, when yearly contracts and
charges also change; the April and July steps fall mid-year.

THE DECLARED TERM IS NOT PROPORTIONAL TO FUEL COST. Within a unit, before the tax
came back, it moves 0.95% per 1% of implied cost in Spain and 0.70% in Portugal: part
of it does not scale with fuel. So the main model gives each unit its own slope on
the log of its implied cost (`marginal_cost_capped_bid_eur_mwh`, prices final at
bidding; the same as the uncapped cost from March 2023);
the model without them is reported alongside.

Units: combined cycles with a plant-specific efficiency (`jrc_cab_match`), 44
Spanish and 10 Portuguese, less Turbogás (RTG01–03): it left the market on
2024-03-30 and declared a quarter of its cost in its last two months. Sample
2023-04-01 (the gas cap stopped binding in March 2023) → 2025-03-18. Dropped:
declared terms of 999 (OMIE's "never"), and terms below half or above three times
the implied cost, which are not cost declarations. Inference: unit clusters,
two-way unit and week clusters, and a wild cluster bootstrap by unit (Webb weights,
restricted under the null) since only 7 clusters are Portuguese.

THE STEP DAYS. Declared terms are revised daily and each tax rate starts on a known
day, so the sharpest comparison is a narrow window around it: the Spanish −
Portuguese gap in the 7 or 14 days after against the days before (unit, date
effects and cost slopes). Its benchmark is the same jump on every first of the month
from 2021-08 with no tax change: with 7 Portuguese units, that is the noise a step
must beat.

Writes outputs/tables/ivpee_tax_test.csv, ivpee_tax_event_study.csv,
ivpee_tax_step_windows.csv and outputs/figures/ivpee_tax_event_study.png.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from outage_offer_test import demean  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
FIG = ROOT / "outputs/figures/ivpee_tax_event_study.png"
START, END = "2023-04-01", "2025-03-18"
LONG_START = "2021-07-01"  # both countries untreated from here to 2023: IVPEE and clawback suspended
COST = "marginal_cost_capped_bid_eur_mwh"   # the gas cap's reference price while it bound (2022-06 → 2023-02)
STEPS = [("2024-01-01", 0.035), ("2024-04-01", 0.0525), ("2024-07-01", 0.07)]
NEVER = 999.0            # OMIE's placeholder for a condition that is never met
RATIO = (0.5, 3.0)       # declared term over implied cost: outside it, not a cost
CLOSING = ["RTG01", "RTG02", "RTG03"]   # Turbogás, out of the market from 2024-03-30
B = 9999
SEED = 20261006


def tau(dates: pd.Series) -> np.ndarray:
    t = np.zeros(len(dates))
    for day, rate in STEPS:
        t[(dates >= day).to_numpy()] = rate
    return t


def units() -> pd.DataFrame:
    m = pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet")
    u = m[(m.cab_tech == "combined_cycle") & ~m.eff_is_generic][["unit", "country", "eff"]]
    if u.unit.duplicated().any():
        raise SystemExit("a unit appears twice in jrc_cab_match")
    return u


def declared(u: pd.DataFrame, start: str = START) -> pd.DataFrame:
    files = [f for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet")))
             if start[:7].replace("-", "") <= Path(f).stem[-6:] <= END[:7].replace("-", "")]
    d = pd.concat([pd.read_parquet(f, columns=["date", "unit", "side", "min_income_var_eur_mwh",
                                               "min_income_fixed_eur"],
                                   filters=[("unit", "in", u.unit.tolist())]) for f in files])
    d["date"] = pd.to_datetime(d.date)
    d = d[(d.date >= start) & (d.date <= END) & (d.side == "V")]
    if d.duplicated(["unit", "date"]).any():
        raise SystemExit("more than one sell header per unit and day")
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", COST], filters=[("unit", "in", u.unit.tolist())])
    c["date"] = pd.to_datetime(c.date)
    d = d.merge(u, on="unit").merge(c, on=["unit", "date"], how="left")
    if d[COST].isna().any():
        raise SystemExit("unit-days without an implied cost")
    return d


def equivalent_hours(u: pd.DataFrame, year: int) -> pd.Series:
    """Scheduled MWh over cab max power, per Portuguese combined cycle, from PDBF."""
    pt = u[u.country == "PT"].unit.tolist()
    d = pd.concat([pd.read_parquet(f, columns=["unit", "schedule_mw", "resolution_min"],
                                   filters=[("unit", "in", pt)])
                   for f in sorted(glob.glob(str(DATA / f"omie/pdbf/parquet/pdbf_{year}*.parquet")))])
    mwh = (d.schedule_mw.clip(lower=0) * d.resolution_min / 60).groupby(d.unit).sum()
    cab = pd.concat([pd.read_parquet(f, columns=["unit", "max_power_mw"], filters=[("unit", "in", pt)])
                     for f in sorted(glob.glob(str(DATA / f"omie/cab/parquet/cab_{year}*.parquet")))])
    return (mwh / cab.groupby("unit").max_power_mw.max()).reindex(pt).fillna(0).round(0)


def vcov(X: np.ndarray, e: np.ndarray, cls: list[np.ndarray]) -> np.ndarray:
    """Cluster-robust covariance; several cluster variables give the two-way form
    (Cameron, Gelbach & Miller 2011): V_a + V_b − V_ab."""
    inv = np.linalg.inv(X.T @ X)

    def meat(cl):
        g = pd.factorize(cl)[0]
        S = np.zeros((g.max() + 1, X.shape[1]))
        np.add.at(S, g, X * e[:, None])
        G = g.max() + 1
        return G / (G - 1) * S.T @ S

    if len(cls) == 1:
        M = meat(cls[0])
    else:
        a, b = cls
        M = meat(a) + meat(b) - meat(pd.Series(a).astype(str).to_numpy() + "|" + pd.Series(b).astype(str).to_numpy())
    return inv @ M @ inv


def wild_p(y: np.ndarray, x: np.ndarray, cl: np.ndarray, theta0: float, rng) -> float:
    """Wild cluster bootstrap p-value of θ = θ0, restricted residuals, Webb weights.
    y and x are already net of the fixed effects (Frisch–Waugh)."""
    g = pd.factorize(cl)[0]
    G = g.max() + 1
    xx = x @ x

    def tstat(yy):
        th = (x @ yy) / xx
        s = np.bincount(g, weights=x * (yy - th * x), minlength=G)
        return (th - theta0) / np.sqrt(G / (G - 1) * (s @ s) / xx ** 2)

    t = tstat(y)
    er = y - theta0 * x
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    xe = np.bincount(g, weights=x * er, minlength=G)         # cluster scores of the restricted model
    W = webb[rng.integers(0, 6, size=(B, G))]
    th = theta0 + (W @ xe) / xx
    # residual score per cluster: sum x (y* − θ* x) = w_g xe_g − (θ* − θ0) sum_g x²
    xg2 = np.bincount(g, weights=x * x, minlength=G)
    s = W * xe - (th - theta0)[:, None] * xg2
    tb = (th - theta0) / np.sqrt(G / (G - 1) * (s ** 2).sum(axis=1) / xx ** 2)
    return float((np.abs(tb) >= abs(t)).mean())


def fit(d: pd.DataFrame, y: str, xs: list[str], slopes: bool, extra: list[str] = ()):
    """Unit and date effects; with `slopes`, each unit's own slope on its log cost is
    partialled out too (Frisch–Waugh). Returns y and the xs net of all of it."""
    codes = [pd.factorize(d.unit)[0], pd.factorize(d.date)[0]]
    cols = [y] + xs
    S = d[list(extra)].to_numpy(float) if extra else None
    if slopes:
        g = pd.factorize(d.unit)[0]
        lc = d.lc.to_numpy()
        U = np.zeros((len(d), g.max() + 1))
        U[np.arange(len(d)), g] = lc
        S = U if S is None else np.column_stack([S, U])
    M = demean(np.column_stack([d[cols].to_numpy()] + ([S] if S is not None else [])), codes)
    yt, Xt = M[:, 0], M[:, 1:len(cols)]
    if S is not None:
        C = M[:, len(cols):]
        nrm = np.linalg.norm(C, axis=0)
        C = C[:, nrm > 1e-9 * nrm.max()]
        Q, _ = np.linalg.qr(C)
        yt = yt - Q @ (Q.T @ yt)
        Xt = Xt - Q @ (Q.T @ Xt)
    b = np.linalg.lstsq(Xt, yt, rcond=None)[0]
    e = yt - Xt @ b
    return yt, Xt, b, e


def sample(u: pd.DataFrame, start: str = START) -> pd.DataFrame:
    d = declared(u, start)
    v = d.min_income_var_eur_mwh
    r = v / d[COST]
    drop = {"no term (0)": v <= 0, "999": v >= NEVER,
            f"ratio to cost outside {RATIO}": (v > 0) & (v < NEVER) & ~r.between(*RATIO),
            "Turbogás": d.unit.isin(CLOSING)}
    keep = ~np.logical_or.reduce(list(drop.values()))
    print(f"\n{len(d):,} unit-days; dropped: " + ", ".join(f"{k} {int(m.sum()):,}" for k, m in drop.items())
          + f"; kept {int(keep.sum()):,}")
    d = d[keep].copy()
    d["es"] = (d.country == "ES").astype(float)
    d["tau"] = tau(d.date)
    d["lv"] = np.log(d.min_income_var_eur_mwh)
    d["lc"] = np.log(d[COST])
    d["T"] = d.es * np.log(1 / (1 - d.tau))
    for i, (day, _) in enumerate(STEPS):
        nxt = STEPS[i + 1][0] if i + 1 < len(STEPS) else "2100-01-01"
        d[f"S{i + 1}"] = d.es * ((d.date >= day) & (d.date < nxt))
    d["week"] = d.date.dt.to_period("W").astype(str)
    return d


def main() -> int:
    u = units()
    print(f"units: {u.country.value_counts().to_dict()}")
    h = equivalent_hours(u, 2024)
    print(f"Portuguese combined cycles, equivalent hours in 2024 (clawback from 2,000): "
          f"max {h.max():.0f}\n{h.to_string()}")
    if h.max() >= 2000:
        raise SystemExit("a Portuguese combined cycle passed 2,000 hours in 2024: it paid the clawback")

    d = sample(u)
    print(f"{d.unit.nunique()} units ({(d.groupby('unit').es.first() == 0).sum()} Portuguese)")
    d["ratio"] = d.min_income_var_eur_mwh / d[COST]
    q = d.groupby([d.date.dt.to_period("Q"), "country"]).agg(v=("min_income_var_eur_mwh", "median"),
                                                             ratio=("ratio", "median")).unstack()
    print("\nmedian declared term (€/MWh) and its ratio to implied cost, by quarter:\n" + q.round(2).to_string())

    rng = np.random.default_rng(SEED)
    pred = [np.log(1 / (1 - r)) for _, r in STEPS]
    S = [f"S{i + 1}" for i in range(len(STEPS))]
    unit_cl = d.unit.to_numpy()
    rows = []
    for slopes in (True, False):
        spec = "unit + date effects, unit cost slopes" if slopes else "unit + date effects"
        print(f"\n== {spec}")
        yt, Xt, b, e = fit(d, "lv", ["T"], slopes)
        se_u = np.sqrt(vcov(Xt, e, [unit_cl])[0, 0])
        se_uw = np.sqrt(vcov(Xt, e, [unit_cl, d.week.to_numpy()])[0, 0])
        p0 = wild_p(yt, Xt[:, 0], unit_cl, 0.0, rng)
        p1 = wild_p(yt, Xt[:, 0], unit_cl, 1.0, rng)
        rows.append({"spec": spec, "model": "pooled", "term": "ES x log(1/(1-tau))", "b": b[0], "se": se_u,
                     "se_unit_week": se_uw, "predicted": 1.0, "wild_p_theta0": p0, "wild_p_theta1": p1})
        vmed = d[d.es == 1].min_income_var_eur_mwh.median()
        print(f"pooled θ = {b[0]:.3f} (unit {se_u:.3f}; unit + week {se_uw:.3f}); wild bootstrap "
              f"p(θ=0) {p0:.3f}, p(θ=1) {p1:.3f}; predicted 1. At 7% and the Spanish median term "
              f"({vmed:.0f} €/MWh): {b[0] * pred[-1] * vmed:+.2f} €/MWh (full pass-through {pred[-1] * vmed:+.2f})")

        yt, Xt, b, e = fit(d, "lv", S, slopes)
        V = vcov(Xt, e, [unit_cl])
        print("step by step (log points; predicted in brackets):")
        for i, (day, rate) in enumerate(STEPS):
            rows.append({"spec": spec, "model": "steps", "term": f"ES x 1[tau = {rate}] (from {day})",
                         "b": b[i], "se": np.sqrt(V[i, i]), "predicted": pred[i]})
            print(f"  {day}  τ {rate:.4f}: {b[i]:+.4f} ({np.sqrt(V[i, i]):.4f})  [{pred[i]:+.4f}]")
        for i in range(1, len(STEPS)):
            c = np.zeros(len(STEPS))
            c[i], c[i - 1] = 1, -1
            rows.append({"spec": spec, "model": "steps", "term": f"step at {STEPS[i][0]}", "b": c @ b,
                         "se": np.sqrt(c @ V @ c), "predicted": pred[i] - pred[i - 1]})
            print(f"  step at {STEPS[i][0]}: {c @ b:+.4f} ({np.sqrt(c @ V @ c):.4f})  [{pred[i] - pred[i - 1]:+.4f}]")

        pre = d[d.date < STEPS[0][0]].copy()
        fake = ["2023-07-01", "2023-10-01"]
        for j, day in enumerate(fake):
            pre[f"F{j}"] = pre.es * (pre.date >= day)
        _, Xp, bp, ep = fit(pre, "lv", [f"F{j}" for j in range(len(fake))], slopes)
        Vp = vcov(Xp, ep, [pre.unit.to_numpy()])
        print("placebo steps in 2023 (τ = 0):  " + ";  ".join(
            f"{day}: {bp[j]:+.4f} ({np.sqrt(Vp[j, j]):.4f})" for j, day in enumerate(fake)))
        for j, day in enumerate(fake):
            rows.append({"spec": spec, "model": "placebo", "term": f"ES x 1[date >= {day}], 2023 only",
                         "b": bp[j], "se": np.sqrt(Vp[j, j]), "predicted": 0.0})

    for r in rows:
        r.update(n=len(d), units=d.unit.nunique(), units_pt=int((d.groupby("unit").es.first() == 0).sum()))
    rows += long_window(u, rng, pred, S)
    step_windows(u)
    out = pd.DataFrame(rows)
    out["t_vs_predicted"] = (out.b - out.predicted) / out.se
    path = TABLES / "ivpee_tax_test.csv"
    out.to_csv(path, index=False)
    print(f"-> {path.relative_to(ROOT)}")
    event_study(d)
    return 0


def long_window(u: pd.DataFrame, rng, pred: list[float], S: list[str]) -> list[dict]:
    """From 2021-07, when the IVPEE and the clawback were both suspended: 2.5 years
    untreated give Spain its own effect for each calendar month, so the April and
    July steps are not read off a seasonal pattern seen only once."""
    print(f"\n== long window from {LONG_START}: unit cost slopes, with and without ES x calendar month")
    d = sample(u, LONG_START)
    moy = d.date.dt.month
    season = []
    for m in range(1, 12):
        d[f"es_m{m}"] = d.es * (moy == m)
        season.append(f"es_m{m}")
    rows = []
    for extra, spec in [((), "long window, unit cost slopes"),
                        (season, "long window, unit cost slopes, ES x calendar month")]:
        yt, Xt, b, e = fit(d, "lv", ["T"], True, extra)
        se = np.sqrt(vcov(Xt, e, [d.unit.to_numpy()])[0, 0])
        p0 = wild_p(yt, Xt[:, 0], d.unit.to_numpy(), 0.0, rng)
        p1 = wild_p(yt, Xt[:, 0], d.unit.to_numpy(), 1.0, rng)
        print(f"{spec}: pooled θ = {b[0]:.3f} ({se:.3f}); wild p(θ=0) {p0:.3f}, p(θ=1) {p1:.3f}")
        rows.append({"spec": spec, "model": "pooled", "term": "ES x log(1/(1-tau))", "b": b[0], "se": se,
                     "predicted": 1.0, "wild_p_theta0": p0, "wild_p_theta1": p1})
        yt, Xt, b, e = fit(d, "lv", S, True, extra)
        V = vcov(Xt, e, [d.unit.to_numpy()])
        for i, (day, rate) in enumerate(STEPS):
            rows.append({"spec": spec, "model": "steps", "term": f"ES x 1[tau = {rate}] (from {day})",
                         "b": b[i], "se": np.sqrt(V[i, i]), "predicted": pred[i]})
        for i in range(1, len(STEPS)):
            c = np.zeros(len(STEPS))
            c[i], c[i - 1] = 1, -1
            rows.append({"spec": spec, "model": "steps", "term": f"step at {STEPS[i][0]}", "b": c @ b,
                         "se": np.sqrt(c @ V @ c), "predicted": pred[i] - pred[i - 1]})
        print("  steps: " + ";  ".join(f"{r['term'].split('(')[-1].rstrip(')') if 'from' in r['term'] else r['term']}: "
                                       f"{r['b']:+.4f} ({r['se']:.4f}) [{r['predicted']:+.4f}]" for r in rows[-5:]))
    for r in rows:
        r.update(n=len(d), units=d.unit.nunique(), units_pt=int((d.groupby("unit").es.first() == 0).sum()))
    return rows


def step_windows(u: pd.DataFrame, widths=(7, 14)) -> None:
    """Jump in the Spanish − Portuguese gap on each step day, against the same jump on
    every first of the month from 2021-08 without a tax change."""
    d = sample(u, LONG_START)
    steps = {pd.Timestamp(day): rate for day, rate in STEPS}
    rows = []
    for D in pd.date_range("2021-08-01", END, freq="MS"):
        for w in widths:
            x = d[(d.date >= D - pd.Timedelta(days=w)) & (d.date < D + pd.Timedelta(days=w))].copy()
            x["post"] = x.es * (x.date >= D)
            _, Xt, b, e = fit(x, "lv", ["post"], True)
            prev = max([0.0] + [r for day, r in steps.items() if day < D])
            rows.append({"date": D.date(), "days": w, "jump": b[0],
                         "se": np.sqrt(vcov(Xt, e, [x.unit.to_numpy()])[0, 0]), "tax_step": D in steps,
                         "predicted": np.log((1 - prev) / (1 - steps[D])) if D in steps else 0.0})
    r = pd.DataFrame(rows)
    print("\n== jumps on the step days against ordinary month starts")
    for w in widths:
        p = r[(r.days == w) & ~r.tax_step].jump
        print(f"±{w} days: {len(p)} ordinary month starts, sd {p.std():.4f}, 5–95% "
              f"[{p.quantile(.05):+.4f}, {p.quantile(.95):+.4f}]")
        for i in r[(r.days == w) & r.tax_step].index:
            s = r.loc[i]
            r.loc[i, "share_placebo_ge"] = (p >= s.jump).mean()
            print(f"  {s.date}: {s.jump:+.4f} ({s.se:.4f}), predicted {s.predicted:+.4f}; "
                  f"ordinary month starts at least as large: {(p >= s.jump).mean():.3f}")
    path = TABLES / "ivpee_tax_step_windows.csv"
    r.to_csv(path, index=False)
    print(f"-> {path.relative_to(ROOT)}")


def event_study(d: pd.DataFrame) -> None:
    """ES × month, December 2023 the reference: the Spanish − Portuguese gap in log
    declared terms, month by month, with and without the unit cost slopes."""
    month = d.date.dt.to_period("M")
    ref = pd.Period("2023-12", "M")
    ms = [m for m in sorted(month.unique()) if m != ref]
    cols = []
    for m in ms:
        d[f"m{m}"] = d.es * (month == m)
        cols.append(f"m{m}")
    r = pd.DataFrame({"month": [str(m) for m in ms]})
    for slopes, tag in [(True, "slopes"), (False, "plain")]:
        _, Xt, b, e = fit(d, "lv", cols, slopes)
        r[f"b_{tag}"] = b
        r[f"se_{tag}"] = np.sqrt(np.diag(vcov(Xt, e, [d.unit.to_numpy()])))
    r = pd.concat([r, pd.DataFrame({"month": [str(ref)], "b_slopes": [0.0], "se_slopes": [0.0],
                                    "b_plain": [0.0], "se_plain": [0.0]})]).sort_values("month")
    r["predicted"] = np.log(1 / (1 - tau(pd.to_datetime(r.month))))
    path = TABLES / "ivpee_tax_event_study.csv"
    r.to_csv(path, index=False)
    print(f"-> {path.relative_to(ROOT)}")
    print(r.round(4).to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(r))
    ax.axhline(0, color="0.6", lw=0.8)
    ax.step(x, r.predicted, where="mid", color="C3", lw=1.5, label="full pass-through of the tax")
    ax.errorbar(x - 0.15, r.b_plain, yerr=1.96 * r.se_plain, fmt="s", color="0.6", ms=3, capsize=0, lw=0.8,
                label="unit and date effects")
    ax.errorbar(x + 0.15, r.b_slopes, yerr=1.96 * r.se_slopes, fmt="o", color="C0", ms=4, capsize=2,
                label="plus each unit's slope on its own cost (main)")
    ax.set_xticks(x[::3])
    ax.set_xticklabels(r.month.iloc[::3], rotation=45, ha="right")
    ax.set_ylabel("Spain − Portugal, log declared term,\nrelative to Dec 2023")
    ax.set_title("IVPEE back in 2024: 3.5% (Jan), 5.25% (Apr), 7% (Jul); combined cycles' declared variable cost")
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    print(f"-> {FIG.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
