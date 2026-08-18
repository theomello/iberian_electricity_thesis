#!/usr/bin/env python3
"""Offer price at a fixed quantile of a unit's OWN capacity.

    .venv/bin/python scripts/analysis/capacity_quantile_offer.py
    .venv/bin/python scripts/analysis/capacity_quantile_offer.py --winsor 0.05

WHY THIS MEASURE EXISTS

Every constructed measure of bidding behaviour tried in this repo has collapsed:
levy passthrough, gas-cap passthrough, and bid steepness all flipped sign under
a reasonable change of rule. The recorded diagnoses are specific, and between
them they name what a valid measure has to avoid:

  * `ab99b50` -- banding on distance from the clearing price conditions on an
    endogenous variable, because renewable output determines that price. OLS and
    2SLS diverged fourfold once banded. The remedy proposed there, never built,
    was "a band defined on something exogenous -- an absolute price range, or
    quantiles of the unit's own capacity."
  * `72d4d75` -- steepness measured over a unit's own offered volume reversed,
    +0.428 to -0.202, when 10% was trimmed from each end. Offer distributions
    have enormous tails and a whole-curve statistic is governed by them.

This builds the remedy. For unit i in period t, take its submitted sell steps,
sort by price, accumulate, and read off the price at which it has offered

    q * max_power_mw

megawatts, for q in {0.25, 0.50, 0.75}. `max_power_mw` comes from the `cab`
offer header and is a plant characteristic, not a period outcome.

WHAT MAKES IT DIFFERENT FROM STEEPNESS

The denominator. Steepness normalises by the volume the unit offered *in that
period*, which is itself a choice -- a unit that withholds offers less, so the
same physical megawatt sits at a different point on the normalised curve, and
the measure moves without any change in the price demanded for it. Nameplate
capacity is fixed across periods, so a change in this measure is a change in the
price attached to a fixed physical quantity.

It is also a level in EUR/MWh. The levy work (`1a15111`) established that levels
are the right functional form for an additive per-MWh shock and that logs and
levels disagreed; a spread-per-unit-share has no such interpretation.

CENSORING, WHICH IS THE HONEST WEAKNESS

If a unit offers less than q * capacity in a period the quantile is undefined.
That is not random -- a withholding unit offers less -- so coverage is reported
per quantile and per year rather than silently dropped. The higher q, the more
censored and the more selected the surviving sample.

THE TEST

The outcome is swapped into the regression of `bid_steepness_iv.py` unchanged --
same months, same weather instruments, same unit/month/hour fixed effects -- so
the only thing that differs is the measure. Steepness failed by reversing across
trimming rules. This reports every quantile against every winsorising rule; if
the sign moves, the measure is no better and should be withdrawn too.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
WX = DATA / "weather" / "weather_spain_aggregate.parquet"
ETA = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"
AGENTS = DATA / "omie/registry/unit_agents.parquet"

MONTHS = [f"{y}{m}" for y in range(2018, 2027) for m in ("04", "10")]
QUANTILES = (0.25, 0.50, 0.75)

# Every role that offers energy. `generation` alone is WRONG and was the first
# version's bug: Asco 1 is `generation_large`, so filtering on `generation`
# silently dropped all 62 combined-cycle units, all 7 nuclear, the 44 hydro
# cascade units and every pumped-storage unit -- exactly the plant with a
# bidding margin. What survived was wind and solar, which is why 76% of the
# outcome sat at zero and no merit order appeared.
SUPPLY_ROLES = ("generation", "generation_large", "storage_mixed", "pumping")

# Technologies whose operator chooses whether to run, so an offer price is a
# decision rather than a formality. Wind and solar offer at zero to guarantee
# dispatch; market power is not defined for them and they are the mass point.
# Defined on technology, which is predetermined and unrelated to the treatment,
# so it does not reintroduce the selection that invalidated the p* band.
DISPATCHABLE = ("combined_cycle", "hydro", "hydro_ugh", "pumped_storage",
                "storage", "thermal", "cogeneration", "nuclear")


def load_capacity() -> pd.DataFrame:
    a = pq.read_table(AGENTS, columns=["unit", "country", "role", "max_power_mw",
                                       "tech", "firm"]).to_pandas()
    a = a[a.role.isin(SUPPLY_ROLES) & (a.max_power_mw > 0)]
    return a.rename(columns={"max_power_mw": "cap"})


def quantile_prices(t: pd.DataFrame, cap: pd.DataFrame) -> pd.DataFrame:
    """Price at which each unit-period has offered q * capacity.

    Within a unit-period, cumulative offered volume is monotone once sorted by
    price, so `cum >= target` is a monotone boolean: False for a run of rows and
    True thereafter. The first crossing is therefore the group's start index plus
    the number of False rows in it, which `np.bincount` gives in one pass. A
    groupby.idxmax per quantile does the same thing and does not finish on this
    archive.
    """
    t = t.merge(cap[["unit", "cap"]], on="unit", how="inner")
    if t.empty:
        return pd.DataFrame()
    t = t.sort_values(["date", "period", "unit", "price_eur_mwh"],
                      kind="stable", ignore_index=True)

    codes, keys = pd.factorize(
        pd.MultiIndex.from_frame(t[["date", "period", "unit"]]), sort=False)
    n_g = len(keys)
    size = np.bincount(codes, minlength=n_g)
    start = np.concatenate([[0], np.cumsum(size)[:-1]])

    cum = t.groupby(codes, sort=False)["power_mw"].cumsum().to_numpy()
    capv = t["cap"].to_numpy()
    price = t["price_eur_mwh"].to_numpy()

    out = pd.DataFrame(
        {"date": keys.get_level_values(0), "period": keys.get_level_values(1),
         "unit": keys.get_level_values(2),
         "cap": capv[start], "offered": cum[start + size - 1], "steps": size})
    for q in QUANTILES:
        below = np.bincount(codes, weights=(cum < q * capv).astype(float),
                            minlength=n_g).astype(np.int64)
        reached = below < size
        idx = np.where(reached, start + np.minimum(below, size - 1), 0)
        out[f"p{int(q*100)}"] = np.where(reached, price[idx], np.nan)
    return out


def build() -> pd.DataFrame:
    cap = load_capacity()
    eta = pq.read_table(ETA, columns=["date", "period", "utc_timestamp",
                                      "vre_share", "demand", "p_star"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)

    rows = []
    for i, ym in enumerate(MONTHS, 1):
        f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
        if not f.exists():
            continue
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh", "power_mw"]
        ).to_pandas()
        t = t[(t.price_eur_mwh >= 0) & (t.price_eur_mwh < 3000) & (t.power_mw > 0)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        rows.append(quantile_prices(t, cap))
        print(f"  [{i:2d}/{len(MONTHS)}] {ym}", end="\r", flush=True)
    print(" " * 40, end="\r")

    d = pd.concat(rows, ignore_index=True).merge(eta, on=["date", "period"], how="inner")
    w = pd.read_parquet(WX)
    w["hour_utc"] = pd.to_datetime(w.utc_timestamp, utc=True)
    d["hour_utc"] = pd.to_datetime(d.utc_timestamp, utc=True).dt.floor("h")
    d = d.merge(w.drop(columns=["utc_timestamp"]), on="hour_utc", how="inner")

    d["month"] = d.hour_utc.dt.to_period("M")
    d["hour"] = d.hour_utc.dt.hour
    d["year"] = d.hour_utc.dt.year
    d["wind"] = d.wind_speed_100m_wind_sites
    d["wind3"] = d.wind ** 3 / 1000.0
    d["rad"] = d.radiation_solar_sites / 100.0
    d["temp"] = d.temperature_2m_mean
    d["log_demand"] = np.log(d.demand.clip(lower=1))
    return d.merge(cap[["unit", "tech", "firm"]], on="unit", how="left")


def demean(v: np.ndarray, *codes) -> np.ndarray:
    v = v.astype(float).copy()
    for _ in range(300):
        prev = v.copy()
        for c in codes:
            v -= np.bincount(c, v)[c] / np.bincount(c)[c]
        if np.max(np.abs(v - prev)) < 1e-10:
            break
    return v


def cluster_meat(X: np.ndarray, e: np.ndarray, codes: np.ndarray) -> np.ndarray:
    """sum_g (X_g' e_g)(X_g' e_g)', computed by summing X*e within each cluster."""
    h = X * e[:, None]
    G = codes.max() + 1
    H = np.zeros((G, X.shape[1]))
    np.add.at(H, codes, h)
    return H.T @ H


def sandwich(X: np.ndarray, e: np.ndarray, clusters: dict) -> dict:
    """Cluster-robust SEs for every clustering in `clusters`, plus two-way.

    WHY THE CLUSTER CHOICE IS THE WHOLE TEST HERE

    `vre_share` is market-wide: identical for every unit in a period. Clustering
    on unit therefore does NOT address the dependence that matters -- residuals
    are correlated ACROSS units within a period, and the regressor is constant
    within one. `a2afd5e` diagnosed exactly this for the earlier designs: the
    effective sample is periods, not unit-periods. Clustering on date is the
    honest standard error; clustering on unit is reported only to show the gap.
    """
    XtX_inv = np.linalg.pinv(X.T @ X)
    n, k = X.shape
    out = {}
    for name, codes in clusters.items():
        G = codes.max() + 1
        c = (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
        V = c * XtX_inv @ cluster_meat(X, e, codes) @ XtX_inv
        out[name] = (np.sqrt(np.abs(np.diag(V))), G)
    if "unit" in clusters and "date" in clusters:
        both = pd.factorize(pd.Series(clusters["unit"]).astype(str) + "_"
                            + pd.Series(clusters["date"]).astype(str))[0]
        Gs = {n_: c_.max() + 1 for n_, c_ in clusters.items()}
        Gb = both.max() + 1
        V = (((Gs["unit"] / max(Gs["unit"] - 1, 1)) * XtX_inv @ cluster_meat(X, e, clusters["unit"]) @ XtX_inv)
             + ((Gs["date"] / max(Gs["date"] - 1, 1)) * XtX_inv @ cluster_meat(X, e, clusters["date"]) @ XtX_inv)
             - ((Gb / max(Gb - 1, 1)) * XtX_inv @ cluster_meat(X, e, both) @ XtX_inv))
        d = np.diag(V)
        out["two-way"] = (np.sqrt(np.abs(d)), min(Gs["unit"], Gs["date"]))
    return out


def ols(Y, X):
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ b
    n, k = X.shape
    s2 = e @ e / max(n - k, 1)
    V = s2 * np.linalg.pinv(X.T @ X)
    return b, np.sqrt(np.diag(V))


def ladder(disp: pd.DataFrame, col: str, winsor: float) -> None:
    """Specification ladder: does the estimate survive daily market-wide costs?

    Month fixed effects absorb slow-moving cost drivers but NOT the daily gas
    price, and a third of this sample is combined cycle, whose offer tracks gas
    almost mechanically. If weather correlates with gas at daily frequency --
    cold snaps alone would do it -- the baseline is contaminated.

    Two tests, increasing in severity:
      (2) control for the MIBGAS day-ahead price for that delivery day
      (3) replace month with DATE fixed effects, which absorb gas, carbon,
          hydrology, French prices and every other market-wide daily driver
          without naming them. Identification is then only within-day,
          hour-to-hour: a unit's offer against the renewable share in that hour
          relative to its own day and its own hour-of-day average.
    """
    s_ = disp.dropna(subset=[col, "vre_share", "wind", "rad", "temp"]).copy()
    if winsor > 0:
        lo, hi = s_[col].quantile([winsor, 1 - winsor])
        s_ = s_[(s_[col] >= lo) & (s_[col] <= hi)]

    gas = pd.read_parquet(ROOT / "data/mibgas/mibgas_prices.parquet")
    gas = gas[gas["product"] == "GDAES_D+1"][["first_delivery", "price_eur_mwh"]]
    gas = gas.rename(columns={"first_delivery": "date", "price_eur_mwh": "gas"})
    gas["date"] = pd.to_datetime(gas["date"])
    s_["date"] = pd.to_datetime(s_["date"])
    merged = s_.merge(gas.drop_duplicates("date"), on="date", how="left")
    have_gas = merged.gas.notna()
    print(f"  MIBGAS coverage on this sample: {100*have_gas.mean():.1f}% "
          f"({merged.loc[have_gas,'date'].min().date()} to "
          f"{merged.loc[have_gas,'date'].max().date()})")

    specs = [("unit+month+hour (baseline)", merged, ("unit", "month", "hour"), False),
             ("  + daily gas price", merged[have_gas], ("unit", "month", "hour"), True),
             ("unit+DATE+hour (all daily absorbed)", merged, ("unit", "date", "hour"), False),
             ("  same, gas-covered sample only", merged[have_gas], ("unit", "date", "hour"), False)]
    print(f"\n{'specification':<38}{'beta':>9}{'two-way se':>12}{'t':>8}{'n':>12}{'units':>7}")
    for name, sub, fes, with_gas in specs:
        if len(sub) < 1000:
            continue
        codes = [pd.factorize(sub[f])[0] for f in fes]
        y = demean(sub[col].to_numpy(float), *codes)
        x = demean(sub.vre_share.to_numpy(float), *codes)
        cnames = ["log_demand", "temp"] + (["gas"] if with_gas else [])
        ctrl = np.column_stack([demean(sub[c].to_numpy(float), *codes) for c in cnames])
        inst = np.column_stack([demean(sub[c].to_numpy(float), *codes)
                                for c in ("wind", "wind3", "rad")])
        Z = np.column_stack([inst, ctrl])
        bz, _ = ols(x, Z)
        xhat = Z @ bz
        X2 = np.column_stack([xhat, ctrl])
        b2, _ = ols(y, X2)
        e = y - np.column_stack([x, ctrl]) @ b2
        cl = {"unit": pd.factorize(sub.unit)[0], "date": pd.factorize(sub.date)[0]}
        se = sandwich(X2, e, cl)["two-way"][0][0]
        print(f"  {name:<38}{b2[0]:>9.4f}{se:>12.4f}{b2[0]/se:>8.2f}"
              f"{len(sub):>12,}{sub.unit.nunique():>7}")


def run_clustered(d: pd.DataFrame, col: str, winsor: float) -> dict | None:
    """2SLS point estimate with unclustered, unit-, date- and two-way-clustered SEs."""
    s = d.dropna(subset=[col, "vre_share", "wind", "rad", "temp"]).copy()
    if winsor > 0:
        lo, hi = s[col].quantile([winsor, 1 - winsor])
        s = s[(s[col] >= lo) & (s[col] <= hi)]
    if len(s) < 1000:
        return None
    ui, mi, hi_ = (pd.factorize(s.unit)[0], pd.factorize(s.month)[0],
                   pd.factorize(s.hour)[0])
    y = demean(s[col].to_numpy(float), ui, mi, hi_)
    x = demean(s.vre_share.to_numpy(float), ui, mi, hi_)
    ctrl = np.column_stack([demean(s[c].to_numpy(float), ui, mi, hi_)
                            for c in ("log_demand", "temp")])
    inst = np.column_stack([demean(s[c].to_numpy(float), ui, mi, hi_)
                            for c in ("wind", "wind3", "rad")])
    Z = np.column_stack([inst, ctrl])
    bz, _ = ols(x, Z)
    xhat = Z @ bz
    X2 = np.column_stack([xhat, ctrl])
    b2, se_naive = ols(y, X2)
    # 2SLS residuals use the ACTUAL regressor, not the fitted one.
    e = y - np.column_stack([x, ctrl]) @ b2
    cl = {"unit": ui, "date": pd.factorize(s.date)[0]}
    ses = sandwich(X2, e, cl)
    return {"beta": b2[0], "naive": se_naive[0], "n": len(s),
            **{k: (v[0][0], v[1]) for k, v in ses.items()}}


def run(d: pd.DataFrame, col: str, winsor: float) -> tuple:
    s = d.dropna(subset=[col, "vre_share", "wind", "rad", "temp"]).copy()
    if winsor > 0:
        lo, hi = s[col].quantile([winsor, 1 - winsor])
        s = s[(s[col] >= lo) & (s[col] <= hi)]
    if len(s) < 1000:
        return (np.nan,) * 5
    ui, mi, hi_ = (pd.factorize(s.unit)[0], pd.factorize(s.month)[0],
                   pd.factorize(s.hour)[0])
    y = demean(s[col].to_numpy(float), ui, mi, hi_)
    x = demean(s.vre_share.to_numpy(float), ui, mi, hi_)
    ctrl = np.column_stack([demean(s[c].to_numpy(float), ui, mi, hi_)
                            for c in ("log_demand", "temp")])
    inst = np.column_stack([demean(s[c].to_numpy(float), ui, mi, hi_)
                            for c in ("wind", "wind3", "rad")])
    b, se = ols(y, np.column_stack([x, ctrl]))
    Z = np.column_stack([inst, ctrl])
    bz, _ = ols(x, Z)
    xhat = Z @ bz
    b2, se2 = ols(y, np.column_stack([xhat, ctrl]))
    return b[0], b2[0], se2[0], len(s), s.unit.nunique()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--from-cache", action="store_true",
                    help="reuse outputs/tables/capacity_quantile_offer.parquet "
                         "instead of re-reading the bid archive")
    ap.add_argument("--inference", action="store_true",
                    help="report cluster-robust SEs for the dispatchable sample")
    args = ap.parse_args()

    cache = ROOT / "outputs/tables/capacity_quantile_offer.parquet"
    d = pd.read_parquet(cache) if (args.from_cache and cache.exists()) else build()

    if args.inference:
        disp = d[d.tech.isin(DISPATCHABLE)]
        print("=" * 86)
        print(f"INFERENCE, DISPATCHABLE SAMPLE -- {len(disp):,} unit-periods, "
              f"{disp.unit.nunique()} units, {disp.date.nunique()} days")
        print("=" * 86)
        print(f"{'quantile':<9}{'winsor':>7}{'beta':>9}{'naive se':>10}"
              f"{'cl(unit)':>10}{'cl(date)':>10}{'two-way':>10}{'t two-way':>11}{'n':>12}")
        for q in QUANTILES:
            col = f"p{int(q*100)}"
            for wz in (0.0, 0.01, 0.05):
                r = run_clustered(disp, col, wz)
                if r is None:
                    continue
                tw = r["two-way"][0]
                print(f"{col:<9}{wz:>7.2f}{r['beta']:>9.4f}{r['naive']:>10.4f}"
                      f"{r['unit'][0]:>10.4f}{r['date'][0]:>10.4f}{tw:>10.4f}"
                      f"{r['beta']/tw:>11.2f}{r['n']:>12,}")
        print(f"\n  clusters: {run_clustered(disp, 'p50', 0.0)['unit'][1]} units, "
              f"{run_clustered(disp, 'p50', 0.0)['date'][1]} dates")
        for wz in (0.0, 0.05):
            print(f"\n{'='*86}\nSPECIFICATION LADDER -- p50, winsor {wz:.2f}\n{'='*86}")
            ladder(disp, "p50", wz)
        return 0
    print("=" * 78)
    print(f"CAPACITY-QUANTILE OFFER PRICE   {len(d):,} unit-periods, "
          f"{d.unit.nunique():,} units, {d.month.nunique()} months")
    print("=" * 78)

    print("\nCOVERAGE -- share of unit-periods where the quantile is reached")
    cov = d.groupby("year")[[f"p{int(q*100)}" for q in QUANTILES]].apply(
        lambda g: g.notna().mean())
    cov["n"] = d.groupby("year").size()
    print(cov.round(3).to_string())

    print("\nVALIDATION -- median p50 by technology (should order by merit)")
    tech = (d.dropna(subset=["p50", "tech"]).groupby("tech")
              .agg(median_p50=("p50", "median"), zero_share=("p50", lambda x: (x == 0).mean()),
                   n=("p50", "size")))
    print(tech[tech.n >= 500].sort_values("median_p50").round(2).to_string())

    disp = d[d.tech.isin(DISPATCHABLE)]
    for label, sub in (("ALL SUPPLY-SIDE UNITS", d), ("DISPATCHABLE ONLY", disp)):
        print(f"\n{'='*78}\n{label}: {len(sub):,} unit-periods, "
              f"{sub.unit.nunique():,} units\n{'='*78}")
        for q in QUANTILES:
            col = f"p{int(q*100)}"
            nz = sub[col].dropna()
            print(f"  {col}: coverage {sub[col].notna().mean():.3f}, "
                  f"share exactly zero {(nz == 0).mean():.3f}, median {nz.median():.2f}")
        print(f"\n  {'quantile':<10}{'winsor':>9}{'2SLS beta':>12}{'se':>9}{'t':>8}"
              f"{'[OLS]':>10}{'n':>12}{'units':>8}")
        for q in QUANTILES:
            col = f"p{int(q*100)}"
            for wz in (0.0, 0.01, 0.05):
                b, b2, se2, n, nu = run(sub, col, wz)
                if np.isnan(b2):
                    continue
                print(f"  {col:<10}{wz:>9.2f}{b2:>12.4f}{se2:>9.4f}{b2/se2:>8.2f}"
                      f"{b:>10.4f}{n:>12,}{nu:>8,}")

    if args.save:
        out = ROOT / "outputs/tables/capacity_quantile_offer.parquet"
        d.to_parquet(out, index=False)
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
