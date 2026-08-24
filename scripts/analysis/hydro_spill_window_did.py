#!/usr/bin/env python3
"""The spill-window design: does an extreme inflow shock cut a hydro unit's
offer *more* when its basin was already wet?

    .venv/bin/python scripts/analysis/hydro_spill_window_did.py
    .venv/bin/python scripts/analysis/hydro_spill_window_did.py --rebuild

Inputs: data/omie/bids/parquet/, data/weather/precipitation_basins_daily.parquet,
data/miteco/embalses_historico.parquet, data/omie/registry/unit_agents.parquet.
Caches outputs/tables/hydro_spill_panel.parquet. Prints; --save writes results.

WHY A FOURTH HYDRO PROBE

Two earlier probes tested whether basin hydrology moves a storage unit's offers
and both failed, in different ways (see notes/hydro-water-value-design.md):

* 2026-08-17, rainfall. A 90-day trailing rain anomaly against *monthly* offers:
  nothing significant, and the one hint of own-basin beating placebo had the
  wrong sign. The note's own diagnosis is the reason to expect that -- a large
  reservoir buffers a slow anomaly, so the state variable barely moves.
* 2026-08-18, reservoir fill. The state variable directly: own-basin fill beat
  the placebo (t = 2.00) but with a **positive** sign, consistent with reverse
  causality -- a plant conserving water bids high and stays fuller for the same
  reason.

This probe is not a third pass at the same regression. It changes three things,
each aimed at one of those two failures.

**Sharp, not smooth.** Three-day cumulative precipitation against *daily*
offers, not a 90-day anomaly against monthly ones. The mechanism here is not
"the reservoir is slowly filling"; it is the spill constraint. Water arriving at
a reservoir that is already near capacity either turns into electricity or is
lost over the weir, so its opportunity cost collapses toward zero for a few
days. That is a sharp, short-horizon event, and averaging it into a month is
exactly what would hide it.

**State-dependent, not a constant effect.** The same rain does nothing at 40%
fill and everything at 90%. The earlier probes imposed one coefficient on rain
and would average those two regimes toward zero. Here the object is the
**interaction**, and the prediction has a sign: `beta < 0` on
`shock x antecedent wetness` -- an inflow shock cuts the offer *by more* where
there was no headroom to absorb it.

**Exogenous on both arms of the interaction.** Interacting an exogenous shock
with *realised* fill would smuggle the 2026-08-18 endogeneity straight back in,
since fill is partly the result of the plant's own past bidding. So antecedent
wetness is measured as cumulative own-basin precipitation over t-90 to t-4 --
weather, not a plant decision -- standardised within basin and ISO week so it
carries deviation-from-normal rather than season. The realised-fill version is
reported alongside it, as a comparison, not as the headline.

WHAT IDENTIFIES IT

Unit and **date** fixed effects. Date FE absorb every national confound at
once: the gas price, carbon, the 2021 levy and the gas cap, national demand,
the market-wide renewable share. Precipitation varies across the nine basins
within a single day, so the rain terms survive that. Identification is the
comparison of a unit in a wet-shocked basin against a unit in an unshocked
basin **in the same auction**, which is the one thing the earlier monthly
designs could not do.

FOUR OUTCOMES, AND WHY THE BOTTOM OF THE OFFER CURVE IS THE SHARPEST

* `marg_acc` -- the highest-priced step the unit actually cleared, averaged over
  the day's periods. The price at which the plant revealed itself willing to
  run; for a reservoir, its water value. Censored above by the clearing price.
* `offer_med` -- volume-weighted median submitted offer. Includes deliberately
  unclearable bids, which express an intention *not* to run.
* `offer_p10` -- volume-weighted 10th percentile of submitted offers. **The
  spill story predicts the largest movement here.** Must-run water shows up at
  the bottom of the offer curve, not at its middle: a plant dumping water it
  cannot store prices that tranche to clear at any price, and leaves the rest of
  its curve where it was.
* `log1p(q)` -- cleared MWh, the extensive margin.

INFERENCE: NINE CLUSTERS

Treatment varies at basin x day and there are only nine basins with
precipitation coverage, so basin-clustered standard errors rest on nine
clusters. That is far below where the asymptotics work. The p-value reported is
therefore a **wild cluster bootstrap** with the null imposed and Rademacher
weights, enumerated exhaustively over all 2^9 = 512 sign vectors rather than
sampled. Analytic clustered SEs are printed next to it, and where the two
disagree the bootstrap is the one to believe.

The placebo is the fixed wrong-basin rotation the two earlier probes already
use: refit with each unit's own-basin regressors replaced by another basin's.
If wrong-basin rain predicts the same unit's offers as well as its own basin's,
the effect is not basin-specific water value and this design fails the same way
the 2026-08-17 one did.

VERDICT, 2026-08-21: THE DESIGN FAILS, AND IT FAILS IN AN INSTRUCTIVE WAY

Run on 58,815 unit-days. Read only the single interaction coefficients and this
looks like the first hydro design in this repo that works: every offer outcome
carries the predicted negative sign, the wrong-basin placebo is null on all
four, and the threshold form -- `shock x 1(fill in the basin's top quartile)`
-- gives -0.30 on the marginal accepted offer, clearing the wild cluster
bootstrap at p = 0.039. Three earlier probes never got that far.

The event study says it is not real. Split by fill regime, the k = 0
coefficient in the **high-fill** arm -- the arm where the spill mechanism does
all its work -- is +0.008 (t = 0.16). Nothing. The entire interaction is coming
from the **low-fill** arm, which jumps +0.159 (t = 3.48) on the shock day.
A negative interaction built out of a positive low-fill response and a zero
high-fill response is arithmetic, not a spill constraint. On the 10th-percentile
outcome the high-fill arm has large negative coefficients at k = -5, -4, -3 and
-2 (t down to -2.10) and a k = 0 that sits right on that pre-trend: a drift
already under way, not an event.

Two further checks close it off:

* **Not a censoring artefact.** The +0.13 shock effect on the marginal accepted
  offer is not the unit climbing its own offer curve because the shock moved its
  volume -- adding log cleared MWh as a control moves the coefficient from
  +0.131 to +0.137. Rain genuinely raises the price at which these plants agree
  to run. That is the wrong sign for a cost shifter and it is the **third**
  wrong-signed hydro result in this repo (2026-08-17 rainfall, 2026-08-18
  reservoir fill, and now this), which makes it a pattern rather than a fluke.
* **The one robust finding is physical, not economic.** In basins already in
  their top fill quartile, an extreme 3-day rain event cuts *offered* volume by
  13% (p_wcb = 0.008, the only result here that survives the bootstrap
  comfortably). Plants withdraw capacity during floods. That is plausibly
  spill-bypass, ramping limits and flood-control operation -- a supply
  restriction, not a water value -- and it is one of roughly thirty tests run
  in this file, so treat it as a lead and not a finding.

The lesson worth carrying: with nine clusters, a correctly-signed interaction
that clears a bootstrap is not enough. The event study is what separated a
mechanism from an arithmetic artefact here, and it should be run before any
single coefficient from this family of designs is believed.

WHAT WOULD MAKE THIS WRONG

Basin-aggregate fill is the wrong resolution for a spill mechanism. One
reservoir can be at 100% and spilling while its demarcation aggregates to 65%,
so the aggregate averages away the variable the story runs on. Matching units to
their own reservoirs (MITECO publishes all 401 individually) would be the fix
and is not built. Read a null here as "not detectable at basin resolution",
which is weaker than "not there".
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from hydro_water_value_precip import (  # noqa: E402
    PLACEBO_ROTATION, hydro_units_with_basin)
from hydro_water_value_reservoir import AMBITO_TO_BASIN  # noqa: E402

PANEL = OUT / "hydro_spill_panel.parquet"


# --------------------------------------------------------------- panel build

def wq(v: np.ndarray, w: np.ndarray, q: float) -> float:
    """Weighted quantile of v with weights w."""
    if len(v) == 0 or w.sum() <= 0:
        return np.nan
    o = np.argsort(v)
    v, w = v[o], w[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, q * c[-1])])


def build_panel(units: set[str]) -> pd.DataFrame:
    out = []
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            filter=(pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh", "power_mw",
                     "resolution_min", "status"]).to_pandas()
        t = t[t.unit.isin(units)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        t["q"] = t.power_mw * t.resolution_min / 60.0

        off = t[(t.status == "O") & (t.price_eur_mwh > 0)
                & (t.price_eur_mwh < 3000)]
        a = (off.groupby(["date", "unit"])
                .apply(lambda x: pd.Series({
                    "offer_med": wq(x.price_eur_mwh.to_numpy(float),
                                    x.q.to_numpy(float), 0.5),
                    "offer_p10": wq(x.price_eur_mwh.to_numpy(float),
                                    x.q.to_numpy(float), 0.10),
                    "q_off": float(x.q.sum())}), include_groups=False)
                .reset_index())

        acc = t[(t.status == "C") & (t.price_eur_mwh > 0)]
        mrg = (acc.groupby(["date", "unit", "period"]).price_eur_mwh.max()
                  .groupby(level=["date", "unit"]).mean()
                  .rename("marg_acc").reset_index())

        cl = (t[t.status == "C"].groupby(["date", "unit"], as_index=False)
                .q.sum().rename(columns={"q": "q_cl"}))

        m = a.merge(mrg, on=["date", "unit"], how="outer")
        out.append(m.merge(cl, on=["date", "unit"], how="outer"))
        print(f"  [{i}/{len(files)}] {f.stem}", end="\r", flush=True)

    d = pd.concat(out, ignore_index=True)
    print(f"\n  panel {d.shape[0]:,} unit-days, {d.unit.nunique()} units")
    return d


# ------------------------------------------------------------- basin weather

def basin_weather() -> pd.DataFrame:
    """Basin-day: the 3-day inflow shock, antecedent wetness, and realised fill.

    `wet90` deliberately ENDS at t-4, three days clear of the 3-day shock
    window, so the shock is not mechanically inside its own antecedent measure.
    """
    p = pd.read_parquet(DATA / "weather/precipitation_basins_daily.parquet")
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["basin", "date"]).reset_index(drop=True)

    g = p.groupby("basin")
    p["precip3"] = g.precipitation_sum.rolling(3, min_periods=3).sum() \
                    .reset_index(level=0, drop=True)
    p["snow3"] = g.snowfall_sum.rolling(3, min_periods=3).sum() \
                  .reset_index(level=0, drop=True)
    # cumulative rain over the 87 days ending 4 days before today
    cum = g.precipitation_sum.rolling(90, min_periods=60).sum() \
            .reset_index(level=0, drop=True)
    p["wet90"] = p.groupby("basin")[["date"]].cumcount().map(lambda _: np.nan)
    p["wet90"] = cum.groupby(p.basin).shift(4)

    p["week"] = p.date.dt.isocalendar().week.astype(int)
    # standardise WITHIN basin x ISO week: deviation from that basin's normal
    # for that time of year, so season is not doing the work
    for col in ("wet90", "snow3"):
        grp = p.groupby(["basin", "week"])[col]
        p[col + "_z"] = (p[col] - grp.transform("mean")) / grp.transform("std")
    p["rain3_pct"] = p.groupby("basin").precip3.rank(pct=True)
    p["shock"] = (p.rain3_pct >= 0.90).astype(float)
    p.loc[p.precip3.isna(), "shock"] = np.nan

    # The PRIMARY shock definition is conditioned on basin AND calendar month.
    # An unconditional within-basin decile is mostly "it is winter in the north"
    # -- the same 3-day total is an ordinary week in Galicia in December and a
    # once-a-decade event in Segura in July, and only the second is a shock to
    # anyone's water value. The unconditional version is kept as a robustness
    # row because it is what the first cut used.
    p["mon"] = p.date.dt.month
    p["rain3_pct_m"] = p.groupby(["basin", "mon"]).precip3.rank(pct=True)
    p["shock_m"] = (p.rain3_pct_m >= 0.90).astype(float)
    p.loc[p.precip3.isna(), "shock_m"] = np.nan
    gm = p.groupby(["basin", "mon"]).wet90
    p["wet90_zm"] = (p.wet90 - gm.transform("mean")) / gm.transform("std")

    # realised basin fill, weekly -> daily, for the comparison spec only
    r = pd.read_parquet(DATA / "miteco/embalses_historico.parquet")
    r["date"] = pd.to_datetime(r["date"])
    r["basin"] = r.ambito.map(AMBITO_TO_BASIN)
    r = r.dropna(subset=["basin", "capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]
    wk = (r.groupby(["basin", "date"])
            .agg(stored=("stored_hm3", "sum"), cap=("capacity_hm3", "sum"))
            .reset_index())
    wk["fill"] = wk.stored / wk.cap
    daily = []
    for b, gg in wk.groupby("basin"):
        gg = gg.set_index("date").sort_index()
        idx = pd.date_range(gg.index.min(), p.date.max(), freq="D")
        z = gg.reindex(idx).ffill(limit=10)
        z["basin"] = b
        daily.append(z.reset_index().rename(columns={"index": "date"}))
    fill = pd.concat(daily)[["basin", "date", "fill"]]

    p = p.merge(fill, on=["basin", "date"], how="left")
    p["fweek"] = p.date.dt.isocalendar().week.astype(int)
    fg = p.groupby(["basin", "fweek"]).fill
    p["fill_z"] = (p.fill - fg.transform("mean")) / fg.transform("std")

    keep = ["basin", "date", "shock", "shock_m", "rain3_pct", "wet90_z",
            "wet90_zm", "snow3_z", "fill", "fill_z"]
    return p[keep]


def event_lags(bw: pd.DataFrame, K) -> pd.DataFrame:
    """Leads and lags of the shock indicator, per basin.

    `shift(k)` is the lag for k > 0 and the lead for k < 0 -- writing the two
    branches separately is how the first pass produced sixteen columns that
    were pairwise identical (K-5 == K+5, and so on down to K0), a palindromic
    coefficient path that looks like a result and is a duplicated regressor.
    """
    ev = bw[["basin", "date", "shock_m"]].sort_values(["basin", "date"]).copy()
    for k in K:
        ev[f"K{k}"] = ev.groupby("basin").shock_m.shift(k)
    cols = [f"K{k}" for k in K]
    c = ev[cols].corr().to_numpy()
    iu = np.triu_indices(len(K), 1)
    assert not np.isclose(c[iu], 1.0).any(), "duplicated event-time columns"
    return ev[["basin", "date"] + cols]


# ---------------------------------------------------------------- estimation

def demean(M: np.ndarray, ui: np.ndarray, ti: np.ndarray) -> np.ndarray:
    """Absorb two-way FE by alternating projection."""
    M = np.asarray(M, float).copy()
    nu, nt = np.bincount(ui), np.bincount(ti)
    for _ in range(500):
        prev = M.copy()
        for j in range(M.shape[1]):
            M[:, j] -= np.bincount(ui, M[:, j])[ui] / nu[ui]
            M[:, j] -= np.bincount(ti, M[:, j])[ti] / nt[ti]
        if np.max(np.abs(M - prev)) < 1e-10:
            break
    return M


def ols_cluster(Y, X, cl):
    """OLS with cluster-robust VCOV. Returns beta, se vector, residuals."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ Y)
    e = Y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in np.unique(cl):
        m = cl == c
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    G = len(np.unique(cl))
    n, k = X.shape
    dof = G / (G - 1) * (n - 1) / (n - k)
    V = dof * XtX_inv @ meat @ XtX_inv
    return beta, np.sqrt(np.diag(V)), e


def wild_bootstrap_p(Y, X, cl, j: int) -> float:
    """Wild cluster bootstrap p-value for coefficient j, null imposed,
    Rademacher weights, ALL 2^G sign vectors enumerated (G small)."""
    beta, se, _ = ols_cluster(Y, X, cl)
    t_hat = beta[j] / se[j]

    keep = [c for c in range(X.shape[1]) if c != j]
    Xr = X[:, keep]
    br = np.linalg.pinv(Xr.T @ Xr) @ (Xr.T @ Y)
    er = Y - Xr @ br                      # restricted residuals, beta_j = 0
    fit = Xr @ br

    groups = np.unique(cl)
    G = len(groups)
    if G > 14:                            # 2^15 gets slow; sample instead
        rng = np.random.default_rng(0)
        signs = rng.choice([-1.0, 1.0], size=(4999, G))
    else:
        signs = np.array(list(itertools.product([-1.0, 1.0], repeat=G)))
    idx = {g: (cl == g) for g in groups}

    ts = []
    for s in signs:
        w = np.empty_like(Y)
        for gi, g in enumerate(groups):
            w[idx[g]] = s[gi]
        Yb = fit + w * er
        bb, sb, _ = ols_cluster(Yb, X, cl)
        ts.append(abs(bb[j] / sb[j]))
    ts = np.array(ts)
    return float((ts >= abs(t_hat) - 1e-12).mean())


def fit(d: pd.DataFrame, y: str, xcols: list[str], jname: str, boot=True):
    cols = [y] + xcols + ["unit", "date", "basin"]
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 100:
        return None
    ui = pd.factorize(s.unit)[0]
    ti = pd.factorize(s.date)[0]
    M = demean(s[[y] + xcols].to_numpy(float), ui, ti)
    Y, X = M[:, 0], M[:, 1:]
    cl = pd.factorize(s.basin)[0]
    beta, se, _ = ols_cluster(Y, X, cl)
    j = xcols.index(jname)
    p = wild_bootstrap_p(Y, X, cl, j) if boot else np.nan
    return dict(beta=beta[j], se=se[j], t=beta[j] / se[j], p_wcb=p,
                n=len(s), units=s.unit.nunique(), basins=len(np.unique(cl)))


def row(lbl, r):
    if r is None:
        print(f"{lbl:<46}{'insufficient obs':>44}")
        return
    star = "*" if r["p_wcb"] < 0.10 else " "
    print(f"{lbl:<46}{r['beta']:>11.4f}{r['se']:>9.4f}{r['t']:>7.2f}"
          f"{r['p_wcb']:>9.3f}{star}{r['n']:>9,}{r['units']:>7}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    hy = hydro_units_with_basin().dropna(subset=["basin"]).copy()
    units = set(hy.unit)

    if args.rebuild or not PANEL.exists():
        print("building daily hydro offer panel from the bid archive...")
        d = build_panel(units)
        OUT.mkdir(parents=True, exist_ok=True)
        d.to_parquet(PANEL, index=False)
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)

    d["basin"] = d.unit.map(dict(zip(hy.unit, hy.basin)))
    d["placebo_basin"] = d.basin.map(PLACEBO_ROTATION)

    bw = basin_weather()
    d = d.merge(bw, on=["basin", "date"], how="left")
    pb = bw.rename(columns={c: "pl_" + c for c in bw.columns
                            if c not in ("basin", "date")})
    d = d.merge(pb.rename(columns={"basin": "placebo_basin"}),
                on=["placebo_basin", "date"], how="left")

    d = d[(d.date >= "2018-01-01") & (d.date <= "2026-05-08")]
    d["shock_x_wet"] = d.shock_m * d.wet90_zm           # primary
    d["shock_x_wet_u"] = d.shock * d.wet90_z             # unconditional, robustness
    d["shock_x_fill"] = d.shock_m * d.fill_z
    d["fill_pct"] = d.groupby("basin").fill.rank(pct=True)
    d["hi_fill"] = (d.fill_pct > 0.75).astype(float)
    d.loc[d.fill.isna(), "hi_fill"] = np.nan
    d["shock_x_hifill"] = d.shock_m * d.hi_fill
    d["pl_shock_x_wet"] = d.pl_shock_m * d.pl_wet90_zm
    d["y_marg"] = np.log(d.marg_acc.clip(lower=0.01))
    d["y_med"] = np.log(d.offer_med.clip(lower=0.01))
    d["y_p10"] = np.log(d.offer_p10.clip(lower=0.01))
    d["y_q"] = np.log1p(d.q_cl.clip(lower=0))

    print("=" * 100)
    print("THE SPILL-WINDOW DESIGN — daily, unit + date FE, basin-clustered")
    print("=" * 100)
    # count basins that actually carry weather: `cataluna_interna` has a mapped
    # unit (TERE, the Ter) but no precipitation point, so it drops in every
    # regression. Reporting d.basin.nunique() here overstates it by one.
    nb = d.loc[d.shock_m.notna(), "basin"].nunique()
    print(f"  {len(d):,} unit-days, {d.unit.nunique()} units, "
          f"{nb} basins with precipitation coverage "
          f"({d.basin.nunique()} mapped), {d.date.min().date()} to "
          f"{d.date.max().date()}")
    ev = d[d.shock == 1]
    print(f"  shock unit-days (own-basin 3-day rain in top decile): "
          f"{len(ev):,}  in {ev.date.nunique():,} distinct dates")
    print(f"  wet90_z on shock days: mean {ev.wet90_z.mean():+.2f}, "
          f"sd {ev.wet90_z.std():.2f}   (full sample sd {d.wet90_z.std():.2f})")

    hdr = (f"\n{'specification':<46}{'beta':>11}{'se':>9}{'t':>7}"
           f"{'p_wcb':>10}{'obs':>9}{'units':>7}")
    base = ["shock_m", "wet90_zm", "shock_x_wet"]

    print("\n" + "-" * 100)
    print("MAIN: y = log(offer);  x = shock x antecedent wetness "
          "(both weather-driven)")
    print("  prediction: beta < 0 — an inflow shock cuts the offer BY MORE "
          "where there was no headroom")
    print("-" * 100 + hdr)
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("median submitted offer", "y_med"),
                   ("10th-pct submitted offer  <-- sharpest", "y_p10"),
                   ("log(1 + cleared MWh)", "y_q")):
        row(f"shock x wet90 — {lbl}", fit(d, y, base, "shock_x_wet"))

    print("\n" + "-" * 100)
    print("PLACEBO: same, with a wrong basin's weather (fixed rotation)")
    print("-" * 100 + hdr)
    plb = ["pl_shock_m", "pl_wet90_zm", "pl_shock_x_wet"]
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("median submitted offer", "y_med"),
                   ("10th-pct submitted offer", "y_p10"),
                   ("log(1 + cleared MWh)", "y_q")):
        row(f"PLACEBO shock x wet90 — {lbl}", fit(d, y, plb, "pl_shock_x_wet"))

    print("\n" + "-" * 100)
    print("COMPARISON: realised basin fill in place of antecedent wetness")
    print("  (fill is partly the result of the plant's own past bidding — this "
          "is the\n   2026-08-18 endogeneity, shown for contrast, not as the "
          "headline)")
    print("-" * 100 + hdr)
    alt = ["shock_m", "fill_z", "shock_x_fill"]
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("median submitted offer", "y_med"),
                   ("10th-pct submitted offer", "y_p10")):
        row(f"shock x fill — {lbl}", fit(d, y, alt, "shock_x_fill"))

    print("\n" + "-" * 100)
    print("MAIN EFFECT of the shock alone (no interaction) — what the 2026-08-17"
          "\n  probe tested, now daily and sharp rather than monthly and smooth")
    print("-" * 100 + hdr)
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("median submitted offer", "y_med"),
                   ("10th-pct submitted offer", "y_p10"),
                   ("log(1 + cleared MWh)", "y_q")):
        row(f"shock — {lbl}", fit(d, y, ["shock_m", "wet90_zm"], "shock_m"))

    print("\n" + "-" * 100)
    print("SNOW: 3-day snowfall anomaly — inflow with a LAG, arriving at melt")
    print("-" * 100 + hdr)
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("10th-pct submitted offer", "y_p10")):
        row(f"snow3_z — {lbl}", fit(d, y, ["snow3_z", "shock_m", "wet90_zm"],
                                    "snow3_z"))

    print("\n" + "-" * 100)
    print("THRESHOLD form: spill is a kink, not a slope. shock x 1(fill in the "
          "basin's top quartile)")
    print("-" * 100 + hdr)
    thr = ["shock_m", "hi_fill", "shock_x_hifill"]
    for lbl, y in (("marginal accepted offer", "y_marg"),
                   ("median submitted offer", "y_med"),
                   ("10th-pct submitted offer", "y_p10")):
        row(f"shock x hi-fill — {lbl}", fit(d, y, thr, "shock_x_hifill"))

    print("\n" + "-" * 100)
    print("MECHANISM: is a marginal-accepted move a water value, or the unit "
          "climbing its\n  own offer curve because the shock moved its volume?")
    print("-" * 100 + hdr)
    d["y_qoff"] = np.log1p(d.q_off.clip(lower=0))
    for lbl, sub in (("all", d), ("low/mid fill", d[d.hi_fill == 0]),
                     ("high fill", d[d.hi_fill == 1])):
        row(f"[{lbl}] shock -> log(1+offered MWh)",
            fit(sub, "y_qoff", ["shock_m", "wet90_zm"], "shock_m"))
    row("marg_acc on shock, NO volume control",
        fit(d, "y_marg", ["shock_m", "wet90_zm"], "shock_m"))
    row("marg_acc on shock, + log(1+cleared MWh)",
        fit(d, "y_marg", ["shock_m", "wet90_zm", "y_q"], "shock_m"))

    print("\n" + "=" * 100)
    print("EVENT STUDY — the diagnostic the single coefficients cannot give")
    print("  spill predicts: flat before k=0, a DROP at k=0..3, recovery after."
          "\n  k=-1 is the omitted reference. Analytic t only (16 coefficients, "
          "no bootstrap).")
    print("=" * 100)
    K = list(range(-5, 11))
    d = d.merge(event_lags(bw, K), on=["basin", "date"], how="left")
    use = [f"K{k}" for k in K if k != -1]
    for y, yl in (("y_marg", "marginal accepted offer"),
                  ("y_p10", "10th-pct submitted offer")):
        print(f"\n--- {yl} ---")
        for lab, sub in (("HIGH fill (basin top quartile)", d[d.hi_fill == 1]),
                         ("LOW/MID fill", d[d.hi_fill == 0]),
                         ("all fill levels", d)):
            s2 = sub[[y] + use + ["wet90_zm", "unit", "date", "basin"]] \
                    .replace([np.inf, -np.inf], np.nan).dropna()
            if len(s2) < 300:
                print(f"  {lab}: too few obs ({len(s2)})")
                continue
            M = demean(s2[[y] + use + ["wet90_zm"]].to_numpy(float),
                       pd.factorize(s2.unit)[0], pd.factorize(s2.date)[0])
            b, se, _ = ols_cluster(M[:, 0], M[:, 1:],
                                   pd.factorize(s2.basin)[0])
            print(f"  {lab}   n={len(s2):,}  units={s2.unit.nunique()}")
            print("    k:  " + "".join(f"{k:>7}" for k in K))
            print("    b:  " + "".join("      ." if k == -1 else
                  f"{b[use.index(f'K{k}')]:>7.3f}" for k in K))
            print("    t:  " + "".join("      ." if k == -1 else
                  f"{b[use.index(f'K{k}')] / se[use.index(f'K{k}')]:>7.2f}"
                  for k in K))

    if args.save:
        d.to_parquet(OUT / "hydro_spill_regression_panel.parquet", index=False)
        print(f"\nwrote {OUT / 'hydro_spill_regression_panel.parquet'}")

    print("\nRead: the design lives or dies on the MAIN block's sign and the "
          "PLACEBO\nblock being null. p_wcb is a wild cluster bootstrap on nine "
          "basins;\nprefer it to t wherever the two disagree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
