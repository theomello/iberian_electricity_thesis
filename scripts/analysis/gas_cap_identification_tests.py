#!/usr/bin/env python3
"""Step 1d of the gas-cap design: four ways of building the Italian comparison, each tested on
the pre-cap period with the same placebo dates and thresholds as step 1.
(docs/specs/2026-10-28-gas-cap-conduct-design.md)

    .venv/bin/python scripts/analysis/gas_cap_identification_tests.py

Outcome: `mmid` = p_mid - cost (the price at the midpoint between minimum load and K, minus the
cost after the subsidy). Pre-period 2021-06-15 -> 2022-06-14, placebo caps 2021-10-01,
2022-01-01, 2022-03-01, threshold EUR 20.5 (a fifth of the mean subsidy).

1. Conditional difference in differences: unit and date fixed effects, Iberia x Z for every
   control Z (with date effects, Italy x Z is the same regression), firm-clustered errors.
   Z: the eight of `gas_cap_conditional_pretrend.py` plus the Iberian thermal gap (D-1 demand
   forecast - wind - solar forecasts - nuclear output over D-8..D-2), Iberian and Italian
   population-weighted temperature (mean, cooling and heating degree hours), holidays (share of
   Spanish areas on holiday, Portugal, Italy), and Italian demand (GME accepted purchases; Italy
   was not treated, so the cap cannot move it).
2. Interactive fixed effects (Bai 2009), weekly unit means: y = a_u + d_w + l_u'F_w + theta*D + e,
   r = 1, 2, 3 factors, estimated by alternating least squares with missing cells imputed (EM).
   Firm block bootstrap, 49 draws.
3. Synthetic control, weekly: each Iberian unit's pre-placebo path matched by non-negative
   weights over Italian units summing to one; effect = mean gap after the placebo minus before.
   Inference by placing each Italian unit in turn as the treated one (placebo in space).
4. Design B's validity: before the cap, does the change in a unit's offer follow the change in
   its cost? Slope of d(p_mid) on d(cost before subsidy), by country, over consecutive days, and
   (`--design-b`) over consecutive weeks and months of unit means.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
START, PRE_END = pd.Timestamp("2021-06-15"), pd.Timestamp("2022-06-14")
PLACEBOS = ["2021-10-01", "2022-01-01", "2022-03-01"]
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gas_cap_conditional_pretrend import controls, ols_fe, ZS  # noqa: E402

IT_HOLIDAYS_FIXED = ["01-01", "01-06", "04-25", "05-01", "06-02", "08-15", "11-01", "12-08", "12-25", "12-26"]
EASTER_MONDAY = ["2021-04-05", "2022-04-18", "2023-04-10"]


def extra_controls() -> pd.DataFrame:
    days = pd.DataFrame({"date": pd.date_range(START, "2023-06-30")})
    f = pd.read_parquet(ROOT / "outputs" / "tables" / "france_link_hours.parquet",
                        columns=["date", "ib_demand_fc", "ib_wind_fc", "ib_solar_fc"]).groupby("date").mean()
    r = pd.read_parquet(DATA / "ree" / "ree_realtime_5min.parquet", columns=["local_date", "nuclear"])
    nuc = r.groupby(pd.to_datetime(r.local_date)).nuclear.mean().asfreq("D").rolling(7, min_periods=5).mean().shift(2)
    f.index = pd.to_datetime(f.index)
    tg = (f.ib_demand_fc - f.ib_wind_fc - f.ib_solar_fc - nuc.reindex(f.index)).rename("thermal_gap")
    t_ib = pd.read_parquet(DATA / "weather" / "temperature_population_index.parquet")
    t_ib["date"] = t_ib.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    t_ib = t_ib.assign(cdh=(t_ib.temp_pop_iberia - 18).clip(lower=0), hdh=(18 - t_ib.temp_pop_iberia).clip(lower=0))
    t_ib = t_ib.groupby("date").agg(temp_ib=("temp_pop_iberia", "mean"), cdh_ib=("cdh", "sum"), hdh_ib=("hdh", "sum"))
    t_it = pd.read_parquet(DATA / "weather" / "temperature_population_italy.parquet")
    t_it["date"] = t_it.utc_timestamp.dt.tz_convert("Europe/Rome").dt.tz_localize(None).dt.normalize()
    t_it = t_it.groupby("date").agg(temp_it=("temp_pop_it", "mean"), cdh_it=("cdh_it", "sum"), hdh_it=("hdh_it", "sum"))
    hol = pd.read_parquet(DATA / "holidays" / "holidays_es_pt.parquet")
    hol["date"] = pd.to_datetime(hol.date)
    es_areas = hol[hol.area != "PT"].area.nunique()
    h_es = (hol[hol.area != "PT"].groupby("date").area.nunique() / es_areas).rename("hol_es")
    h_pt = hol[hol.area == "PT"].groupby("date").size().clip(upper=1).rename("hol_pt")
    it_h = set(pd.to_datetime([f"{y}-{md}" for y in (2021, 2022, 2023) for md in IT_HOLIDAYS_FIXED] + EASTER_MONDAY))
    import pyarrow.dataset as ds, pyarrow.compute as pc
    g = ds.dataset(DATA / "gme" / "offers" / "parquet").to_table(
        filter=(pc.field("side") == "BID") & (pc.field("status") == "ACC"), columns=["date", "awarded_mwh"]).to_pandas()
    dem_it = g.groupby("date").awarded_mwh.sum().rename("demand_it")
    out = days.set_index("date").join([tg, t_ib, t_it, h_es, h_pt, dem_it])
    out[["hol_es", "hol_pt"]] = out[["hol_es", "hol_pt"]].fillna(0.0)
    out["hol_it"] = out.index.isin(it_h).astype(float)
    return out.reset_index()


EXTRA = ["thermal_gap", "temp_ib", "cdh_ib", "hdh_ib", "temp_it", "cdh_it", "hdh_it", "hol_es", "hol_pt",
         "hol_it", "demand_it"]


def load() -> tuple[pd.DataFrame, float]:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p_mid", "cost", "cost_gross", "subsidy"])
    ybar = h[h.subsidy > 0].drop_duplicates("date").subsidy.mean()
    h = h[(h.date >= START) & (h.date <= PRE_END)].dropna(subset=["cost", "p_mid"])
    h["mmid"] = h.p_mid - h.cost
    d = h.groupby(["unit", "date"], as_index=False).agg(mmid=("mmid", "mean"), p_mid=("p_mid", "mean"),
                                                        cost_gross=("cost_gross", "first"),
                                                        iberia=("iberia", "first"), firm=("firm", "first"))
    d["firm"] = d.firm.fillna(d.unit)
    d["date"] = d.date.astype("datetime64[ns]")
    return d, ybar


def test_conditional(d: pd.DataFrame, thr: float) -> None:
    z = controls().merge(extra_controls().assign(date=lambda x: x.date.astype("datetime64[ns]")), on="date", how="left")
    zz = ZS + EXTRA
    x = d.merge(z, on="date", how="left").dropna(subset=zz).copy()
    for c in zz:
        x[f"ibx_{c}"] = x.iberia * (x[c] - x[c].mean()) / x[c].std()
    zc = [f"ibx_{c}" for c in zz]
    x["ibx_t"] = x.iberia * (x.date - x.date.min()).dt.days / 7.0
    b, se = ols_fe(x, "mmid", ["ibx_t"] + zc)
    fail = abs(b[0] / se[0]) > 1.96 and abs(b[0] * 52) >= thr
    print(f"1. conditional DiD, {len(zz)} controls, {len(x):,} unit-days: trend/yr {b[0] * 52:+.3g} "
          f"(t {b[0] / se[0]:.1f}){' FAIL' if fail else ''}")
    for p in PLACEBOS:
        x["ibx_pl"] = (x.iberia & (x.date >= p)).astype(float)
        bp, sp = ols_fe(x, "mmid", ["ibx_pl"] + zc)
        print(f"   placebo {p}: {bp[0]:+.3g} (se {sp[0]:.2g}){'  FAIL' if abs(bp[0]) >= thr else ''}")


def weekly(d: pd.DataFrame, maxmiss: float = 0.2) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    w = d.assign(w=d.date.dt.to_period("W").dt.start_time).groupby(["unit", "w"]).mmid.mean().unstack()
    w = w[w.isna().mean(axis=1) <= maxmiss]
    meta = d.drop_duplicates("unit").set_index("unit")
    return w, meta.iberia.reindex(w.index), meta.firm.reindex(w.index)


def ife(Y: np.ndarray, D: np.ndarray, r: int, it: int = 200) -> float:
    """Bai (2009) with two-way effects and EM imputation of missing cells; returns theta."""
    obs = ~np.isnan(Y)
    theta = 0.0
    fit = np.zeros_like(Y)
    for _ in range(it):
        R = np.where(obs, Y - theta * D, fit)
        a = R.mean(axis=1, keepdims=True)
        b = (R - a).mean(axis=0, keepdims=True)
        E = R - a - b
        if r:
            U, s, Vt = np.linalg.svd(E, full_matrices=False)
            LF = (U[:, :r] * s[:r]) @ Vt[:r]
        else:
            LF = 0.0
        fit = a + b + LF + theta * D
        resid = Y - (a + b + LF)
        m = obs & (D != 0)
        dd = D[obs]
        new = (resid[obs] @ dd) / (dd @ dd) if (dd @ dd) > 0 else 0.0
        if abs(new - theta) < 1e-6:
            theta = new
            break
        theta = new
        fit = a + b + LF + theta * D
    return theta


def test_ife(w: pd.DataFrame, ib: pd.Series, firm: pd.Series, thr: float, reps: int = 49) -> None:
    Y = w.to_numpy()
    cols = w.columns
    firms = firm.unique()
    rng = np.random.default_rng(20261028)
    print(f"2. interactive fixed effects, weekly, {Y.shape[0]} units x {Y.shape[1]} weeks")
    for r in (1, 2, 3):
        row = []
        for p in PLACEBOS:
            D = np.outer(ib.to_numpy().astype(float), (cols >= pd.Timestamp(p)).astype(float))
            th = ife(Y, D, r)
            bs = []
            for _ in range(reps):
                pick = rng.choice(firms, size=len(firms), replace=True)
                idx = np.concatenate([np.flatnonzero(firm.to_numpy() == f) for f in pick])
                if ib.to_numpy()[idx].all() or not ib.to_numpy()[idx].any():
                    continue
                bs.append(ife(Y[idx], D[idx], r, it=100))
            se = np.std(bs, ddof=1)
            row.append(f"{p}: {th:+.3g} (se {se:.2g}){' FAIL' if abs(th) >= thr else ''}")
        print(f"   r={r}: " + "; ".join(row))


def synth(Y: np.ndarray, t: int, donors: np.ndarray, target: int) -> float:
    """Placebo effect for one treated row: mean(actual - synthetic) after t minus before t."""
    pre = slice(0, t)
    A = Y[donors][:, pre].T
    yv = Y[target, pre]
    # sum-to-one by a heavily weighted row of ones (standard trick with nnls)
    k = 1e3
    w, _ = nnls(np.vstack([A, k * np.ones(A.shape[1])]), np.concatenate([yv, [k]]))
    gap = Y[target] - w @ Y[donors]
    return gap[t:].mean() - gap[:t].mean()


def test_synth(w: pd.DataFrame, ib: pd.Series, thr: float) -> None:
    Yf = w.T.interpolate(limit_direction="both").T.to_numpy()
    cols = w.columns
    it_idx = np.flatnonzero(~ib.to_numpy())
    ib_idx = np.flatnonzero(ib.to_numpy())
    print(f"3. synthetic control, weekly, {len(ib_idx)} Iberian units, {len(it_idx)} Italian donors")
    for p in PLACEBOS:
        t = int((cols < pd.Timestamp(p)).sum())
        eff = np.array([synth(Yf, t, it_idx, i) for i in ib_idx])
        null = np.array([synth(Yf, t, np.setdiff1d(it_idx, [j]), j) for j in it_idx])
        avg = eff.mean()
        # placebo-in-space: the spread of Italian 'effects' averaged over groups of the same size
        rng = np.random.default_rng(7)
        sims = [rng.choice(null, size=len(ib_idx), replace=True).mean() for _ in range(999)]
        lo, hi = np.percentile(sims, [2.5, 97.5])
        print(f"   placebo {p}: mean effect {avg:+.3g} (median {np.median(eff):+.3g}); "
              f"Italian placebo-in-space 95% band [{lo:+.3g}, {hi:+.3g}]{'  FAIL' if abs(avg) >= thr else ''}")


def test_design_b(d: pd.DataFrame) -> None:
    x = d.sort_values(["unit", "date"]).copy()
    g = x.groupby("unit")
    x["dp"], x["dc"] = g.p_mid.diff(), g.cost_gross.diff()
    x["gap_days"] = g.date.diff().dt.days
    x = x[(x.gap_days == 1)].dropna(subset=["dp", "dc"])
    x["dow"] = x.date.dt.dayofweek
    print("4. Design B validity, pre-cap: slope of daily change in p_mid on daily change in cost")
    for ibv, name in ((True, "Iberia"), (False, "Italy")):
        s = x[x.iberia == ibv]
        X = np.column_stack([s.dc.to_numpy(), pd.get_dummies(s.dow, drop_first=False).to_numpy(float)])
        b = np.linalg.lstsq(X, s.dp.to_numpy(), rcond=None)[0]
        e = s.dp.to_numpy() - X @ b
        G = pd.factorize(s.firm)[0]
        iXX = np.linalg.pinv(X.T @ X)
        S = pd.DataFrame(X * e[:, None]).groupby(G).sum().to_numpy()
        V = iXX @ S.T @ S @ iXX
        print(f"   {name}: slope {b[0]:.2f} (se {np.sqrt(V[0, 0]):.2f}), {len(s):,} unit-days; "
              f"bidding at cost predicts 1")


def test_design_b_horizons(d: pd.DataFrame) -> None:
    print("4b. Design B validity by horizon, pre-cap: slope of the change in p_mid on the change in cost")
    for freq, name in (("W", "weekly"), ("M", "monthly")):
        x = d.assign(t=d.date.dt.to_period(freq)).groupby(["unit", "t"], as_index=False).agg(
            p=("p_mid", "mean"), c=("cost_gross", "mean"), iberia=("iberia", "first"), firm=("firm", "first"))
        x = x.sort_values(["unit", "t"])
        g = x.groupby("unit")
        x["dp"], x["dc"] = g.p.diff(), g.c.diff()
        x["step"] = g.t.diff().apply(lambda v: v.n if pd.notna(v) else np.nan)
        x = x[x.step == 1].dropna(subset=["dp", "dc"])
        for ibv, cn in ((True, "Iberia"), (False, "Italy")):
            s_ = x[x.iberia == ibv]
            X = np.column_stack([s_.dc.to_numpy(), np.ones(len(s_))])
            b = np.linalg.lstsq(X, s_.dp.to_numpy(), rcond=None)[0]
            e = s_.dp.to_numpy() - X @ b
            G = pd.factorize(s_.firm)[0]
            iXX = np.linalg.inv(X.T @ X)
            S = pd.DataFrame(X * e[:, None]).groupby(G).sum().to_numpy()
            V = iXX @ S.T @ S @ iXX
            print(f"   {name:<8}{cn:<7} slope {b[0]:.2f} (se {np.sqrt(V[0, 0]):.2f}), {len(s_):,} unit-{name[:-2]}s")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design-b", action="store_true", help="run only the Design B horizon check")
    a = ap.parse_args()
    if a.design_b:
        d, _ = load()
        test_design_b_horizons(d)
        return 0
    d, ybar = load()
    thr = ybar / 5
    print(f"threshold {thr:.1f} EUR/MWh; {d.unit.nunique()} units, {len(d):,} unit-days\n")
    test_conditional(d, thr)
    w, ib, firm = weekly(d)
    test_ife(w, ib, firm, thr)
    test_synth(w, ib, thr)
    test_design_b(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
