#!/usr/bin/env python3
"""Full-archive offer panel for the storage hydro that sells through the auction.

    .venv/bin/python scripts/analysis/edp_hydro_panel.py          # build + report
    .venv/bin/python scripts/analysis/edp_hydro_panel.py --report # report only

WHY THESE UNITS

`notes/rq-midday-hydro.md` §3.7: Iberdrola, Endesa (to 2023) and Naturgy (from
2022) sell most storage hydro through bilateral self-supply, so their auction
offers are residuals and cannot carry the water-allocation test. EDP, Movhera
and Repsol sell almost everything through the auction, so for them the offer
curve IS the allocation decision. EDP is the case the design now rests on:
seven units, 8.3 GW. Movhera (Douro Internacional) and Repsol (Viesgo) are
carried alongside as the only other auction-route owners.

ONE ROW PER UNIT-PERIOD

Periods, not hours, because the day-ahead market moves to 15 minutes on
2025-10-01 and an offer is submitted per period. `hour` is carried for joining
the hourly route split in `hydro_schedule_routes.parquet`.

* offer shape -- price at 25/50/75% of CAPACITY (`p25_cap`..., censored when
  the unit offers less), price at 25/50/75% of what was OFFERED (`o25`...,
  always defined), number of steps, lowest and highest step price, and the
  share of offered MW that is PRICED OUT (>= PRICE_OUT EUR/MWh and more than
  100 above the zone price). Steps under MIN_STEP_MW are dropped from the step
  counts and price sets -- Iberdrola adds 0.1 MW token steps (hydro_flat_break.py).
* outcome -- day-ahead cleared MW, and the pumping twin's cleared purchase.
* price -- the price of the unit's OWN zone. Six of EDP's seven units are
  Portuguese, and a Portuguese unit is paid `price_pt` when the market splits.
* incentive -- the owner's NET AUCTION POSITION and X come from `firm_x.py`,
  on the exposed position (framework spec §2.4): regulated pass-through
  suppliers such as SU Eletricidade are left out. `X_built` keeps the as-built
  value. Both are defined on the firm panel's periods only (clean, p* above
  1 EUR/MWh). The design's term is `X = net_mw / slope_net`, the Hortacsu-Puller
  markup with the firm's exposure to the auction price in the numerator.

  NOT the panel's `incentive_h*`, which multiplies by `(q - theta)/q` with q the
  auction-cleared sell volume and theta the BILATERAL schedule. Bilateral energy
  never enters q, so that subtracts contracts twice -- the error
  `hortacsu_puller_test.py` caught in its first pass. See
  `notes/rq-descriptive-price-formation.md` §4.5.

  The slope in X is `slope_net`: the firm's own DEMAND bids near p* are removed
  too, not only its sell offers. For EDP that is mostly its pumping legs, and it
  matters in a tail of periods, not the median.

  EDP COMERCIAL (EDP's Portuguese retailer) is merged into EDP in
  `owner_groups.parquet` (GROUP_MERGES, 2026-09-30). It offers essentially no
  supply but buys 1.6-4.7 TWh a year in 2022-2024.
* flatness -- per unit-day: `flat_p50` (the capacity-p50 is identical in every
  period, scored when defined in at least half of them) and `same_prices` (the
  same set of step prices, >= MIN_STEP_MW, in every period).

PUMPING TWINS

A cascade with a pumping leg can refill within the day, so its water value is
tied to the pumping price rather than fixed by a daily budget (threat 3 in the
note). Each unit carries its twin, if any: the five `...B` legs by name, and
TANB (C.H.B. Tanes bombeo, Hidrocantabrico) for HCHI, matched on the owner and
the plant rather than the code -- a hand match, stated as one.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_within_day_probe import BIDS, storage_hydro  # noqa: E402

DATA = ROOT / "data"
PRICES = DATA / "omie/prices/omie_day_ahead_prices.parquet"
FIRM_SLOPE = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"   # firm_x.py
OUT = ROOT / "outputs/tables/edp_hydro_panel.parquet"

GROUPS = ("EDP", "MOVHERA", "REPSOL")
PRICE_OUT = 300.0     # EUR/MWh, as in hydro_schedule_routes.py
# X is undefined below this slope. A band that the firm's own demand nearly
# fills leaves a slope just above zero and an X up to 2.8e8 EUR/MWh -- a division
# artefact, not a markup. 5 MW per EUR/MWh (50 MW in the +/-5 band) drops 0.08%
# of EDP's periods.
MIN_SLOPE = 5.0
MIN_STEP_MW = 1.0     # as in hydro_flat_break.py
QS = (0.25, 0.50, 0.75)
TWINS = {"ACAVADO": "ACAVADB", "ADOURO": "ADOUROB", "ALIMA": "ALIMAB",
         "GUADIA": "GUADIAB", "MONDEGO": "MONDEGB", "HCHI": "TANB",
         "DOUSUP": "DOUSUPB"}
ERAS = {"2018-2020": (2018, 2020), "2021-2023": (2021, 2023), "2024-2026": (2024, 2026)}


def first_crossing(t: pd.DataFrame, target: np.ndarray, codes: np.ndarray,
                   size: np.ndarray, start: np.ndarray, cum: np.ndarray) -> np.ndarray:
    """Price at the first step whose cumulative MW reaches `target` (per group).

    Rows are sorted by price within each group, so `cum < target` is True for a
    run of rows and False after -- the crossing is start + count(True).
    """
    below = np.bincount(codes, weights=(cum < target[codes]).astype(float),
                        minlength=len(size)).astype(np.int64)
    reached = below < size
    idx = np.where(reached, start + np.minimum(below, size - 1), 0)
    return np.where(reached, t.price_eur_mwh.to_numpy()[idx], np.nan)


def offer_shape(off: pd.DataFrame, cap: pd.Series) -> pd.DataFrame:
    t = off.sort_values(["date", "period", "unit", "price_eur_mwh"], kind="stable",
                        ignore_index=True)
    codes, keys = pd.factorize(pd.MultiIndex.from_frame(t[["date", "period", "unit"]]),
                               sort=False)
    size = np.bincount(codes)
    start = np.concatenate([[0], np.cumsum(size)[:-1]])
    cum = t.groupby(codes, sort=False).power_mw.cumsum().to_numpy()
    offered = cum[start + size - 1]
    capv = t.unit.map(cap).to_numpy()[start]
    out = pd.DataFrame({"date": keys.get_level_values(0), "period": keys.get_level_values(1),
                        "unit": keys.get_level_values(2), "cap": capv, "offered_mw": offered})
    for q in QS:
        out[f"p{int(q*100)}_cap"] = first_crossing(t, q * capv, codes, size, start, cum)
        out[f"o{int(q*100)}"] = first_crossing(t, q * offered, codes, size, start, cum)

    big = t[t.power_mw >= MIN_STEP_MW]
    g = big.groupby(["date", "period", "unit"])
    steps = g.agg(n_steps=("price_eur_mwh", "size"), min_price=("price_eur_mwh", "min"),
                  max_price=("price_eur_mwh", "max"))
    steps["price_set"] = g.price_eur_mwh.agg(lambda x: "|".join(f"{v:.2f}" for v in sorted(set(x))))
    return out.merge(steps.reset_index(), on=["date", "period", "unit"], how="left")


def month_panel(ym: str, cap: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    units = list(cap.unit)
    twins = [TWINS[u] for u in units if u in TWINS]
    t = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "hour", "resolution_min", "unit", "side",
                               "status", "power_mw", "price_eur_mwh"],
                      filters=[("unit", "in", units + twins)]).to_pandas()
    t["date"] = pd.to_datetime(t.date)
    sell = t[t.unit.isin(units) & (t.side == "V")]
    off = sell[sell.status == "O"]
    if off.empty:
        return pd.DataFrame()
    d = offer_shape(off, cap.set_index("unit").cap)

    cleared = (sell[sell.status == "C"].groupby(["date", "period", "unit"]).power_mw.sum()
               .rename("cleared_mw"))
    d = d.merge(cleared.reset_index(), on=["date", "period", "unit"], how="left")
    pump = t[t.unit.isin(twins) & (t.side == "C") & (t.status == "C")]
    pump = (pump.groupby(["date", "period", "unit"]).power_mw.sum().rename("pump_mw")
            .reset_index().rename(columns={"unit": "twin"}))
    d["twin"] = d.unit.map(TWINS)
    d = d.merge(pump, on=["date", "period", "twin"], how="left")
    d[["cleared_mw", "pump_mw"]] = d[["cleared_mw", "pump_mw"]].fillna(0.0)
    d.loc[d.twin.isna(), "pump_mw"] = np.nan

    per = t.drop_duplicates(["date", "period"])[["date", "period", "hour", "resolution_min"]]
    d = d.merge(per, on=["date", "period"], how="left")
    d = d.merge(cap[["unit", "group", "country"]], on="unit").merge(prices, on=["date", "period"],
                                                                  how="left")
    d["p_zone"] = np.where(d.country.eq("PT"), d.price_pt, d.price_es)
    d["split"] = (d.price_pt - d.price_es).abs() > 0.005

    # Priced-out share, in the unit's own zone.
    po = sell[sell.status == "O"].merge(d[["date", "period", "unit", "p_zone"]],
                                        on=["date", "period", "unit"])
    po = po[(po.price_eur_mwh >= PRICE_OUT) & (po.price_eur_mwh > po.p_zone + 100)]
    po = po.groupby(["date", "period", "unit"]).power_mw.sum().rename("priced_out_mw")
    d = d.merge(po.reset_index(), on=["date", "period", "unit"], how="left")
    d["priced_out_mw"] = d.priced_out_mw.fillna(0.0)
    d["priced_out_share"] = d.priced_out_mw / d.offered_mw

    # Price-setting: the unit's highest cleared sell step IS its zone's price.
    top = (sell[sell.status == "C"].groupby(["date", "period", "unit"]).price_eur_mwh.max()
           .rename("top_cleared_price"))
    d = d.merge(top.reset_index(), on=["date", "period", "unit"], how="left")
    d["marginal"] = (d.cleared_mw > 0) & ((d.top_cleared_price - d.p_zone).abs() < 0.01)
    return d


def attach_x(d: pd.DataFrame) -> pd.DataFrame:
    """Net position and X per owner-period from firm_x.py, on the firm panel's
    periods (clean, p* above ZERO_PRICE) so the sample is unchanged. `X` and
    `net_mw` are the EXPOSED position (framework spec §2.4); `X_built` and
    `net_built_mw` as built. MOVHERA is not in firm_x and gets NaN, as before."""
    drop = [c for c in ("net_mw", "net_built_mw", "slope_net", "X", "X_built", "X_gross")
            if c in d.columns]
    x = pd.read_parquet(FIRM_X, columns=["date", "period", "firm", "clean", "zero_price", "net_mw",
                                         "net_built_mw", "slope_net", "X", "X_built"])
    x = x[x.firm.isin(GROUPS) & x.clean & ~x.zero_price].drop(columns=["clean", "zero_price"])
    x = x.rename(columns={"firm": "group"})
    x["date"] = pd.to_datetime(x.date)
    return d.drop(columns=drop).merge(x, on=["date", "period", "group"], how="left")


def add_flatness(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["unit", "date"])
    n = g.period.transform("size")
    n50 = g.p50_cap.transform("count")
    rng = g.p50_cap.transform("max") - g.p50_cap.transform("min")
    d["flat_p50"] = np.where(n50 >= n / 2, (rng < 0.01).astype(float), np.nan)
    d["same_prices"] = (g.price_set.transform("nunique") == 1).astype(float)
    return d


def add_firm(d: pd.DataFrame) -> pd.DataFrame:
    f = pq.read_table(FIRM_SLOPE, columns=["date", "period", "firm", "slope_i_h5", "q_firm_mw",
                                           "theta_mw"],
                      filters=[("firm", "in", list(GROUPS))]).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    return d.merge(f.rename(columns={"firm": "group"}), on=["date", "period", "group"], how="left")


def build() -> pd.DataFrame:
    cap = storage_hydro()
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "country"])
    cap = cap[cap.group.isin(GROUPS)].merge(u, on="unit")
    prices = pd.read_parquet(PRICES, columns=["date", "period", "price_es", "price_pt"])
    prices["date"] = pd.to_datetime(prices.date)
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    parts = []
    for m in months:
        parts.append(month_panel(m, cap, prices))
        print(f"  {m}", flush=True, file=sys.stderr)
    d = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    d = attach_x(add_firm(add_flatness(d)))
    d["year"] = d.date.dt.year
    d["era"] = pd.cut(d.year, [2017, 2020, 2023, 2026], labels=list(ERAS))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-periods)")
    return d


def report(d: pd.DataFrame) -> None:
    ud = d.drop_duplicates(["unit", "date"])
    print("\nUNITS")
    info = d.groupby("unit").agg(group=("group", "first"), country=("country", "first"),
                                 cap=("cap", "first"), twin=("twin", "first"),
                                 first=("date", "min"), last=("date", "max"),
                                 days=("date", "nunique"))
    print(info.to_string())

    print("\nCOVERAGE")
    print(f"  p_zone defined: {d.p_zone.notna().mean():.3f}; split periods: {d.split.mean():.3f}")
    print(f"  firm slope joined: {d.slope_i_h5.notna().mean():.3f} of unit-periods")
    print(f"  p50_cap censored: {d.p50_cap.isna().mean():.3f}; o50 defined: {d.o50.notna().mean():.3f}")

    print("\nFLAT SHARE by unit and year -- flat_p50 / same_prices")
    for col in ("flat_p50", "same_prices"):
        t = ud.groupby(["unit", "year"])[col].mean().unstack().round(2)
        print(f"  {col}"); print(t.to_string())

    # What kind of within-day variation: a smooth tilt or discrete price-outs?
    edp = d[d.group == "EDP"]
    day = edp.groupby(["unit", "date"]).agg(rng=("o50", lambda x: x.max() - x.min()),
                                            po=("priced_out_share", "max"),
                                            flat=("same_prices", "first"),
                                            year=("year", "first"))
    nf = day[day.flat == 0]
    print("\nEDP NON-FLAT unit-days: within-day range of o50 (price at half the offered MW)")
    bins = pd.cut(nf.rng, [-0.01, 5, 20, 100, 300, 10_000],
                  labels=["<5", "5-20", "20-100", "100-300", ">300"])
    print(pd.crosstab(nf.year, bins, normalize="index").round(2).to_string())
    print("  share of non-flat unit-days with any priced-out tranche:",
          round((nf.po > 0).mean(), 3))

    print("\nEDP HOUR PROFILE by era: mean deviation from the unit-day mean")
    edp = edp.assign(o50_dev=edp.o50 - edp.groupby(["unit", "date"]).o50.transform("mean"),
                     clr_dev=edp.cleared_mw - edp.groupby(["unit", "date"]).cleared_mw.transform("mean"),
                     po_dev=edp.priced_out_share
                     - edp.groupby(["unit", "date"]).priced_out_share.transform("mean"))
    hours = [3, 6, 9, 12, 14, 16, 19, 21, 23]
    for era, g in edp.groupby("era", observed=True):
        prof = pd.DataFrame({"o50_dev EUR": g.groupby("hour").o50_dev.mean(),
                             "priced_out_dev": g.groupby("hour").po_dev.mean(),
                             "cleared_dev MW": g.groupby("hour").clr_dev.mean(),
                             "p_zone": g.groupby("hour").p_zone.median()})
        print(f"  {era}"); print(prof.reindex(hours).round(2).T.to_string())

    print("\nEDP NET AUCTION POSITION (MW, all EDP + EDP COMERCIAL units) and X = net / slope "
          "(EUR/MWh), median by era and hour")
    ep = edp.drop_duplicates(["date", "period"])
    for col in ("net_mw", "X"):
        t = ep.groupby(["era", "hour"], observed=True)[col].median().unstack().reindex(columns=hours)
        print(f"  {col}"); print(t.round(1).to_string())

    # The descriptive check the design needs before any regression: within a
    # unit-day, does the offer sit higher in the periods where X is higher?
    # Binned, not regressed, and on the periods where the slope is defined.
    x = edp.dropna(subset=["X", "o50"]).copy()
    for c in ("X", "o50"):
        x[c + "_w"] = x[c] - x.groupby(["unit", "date"])[c].transform("mean")
    x = x[x.groupby(["unit", "date"]).X_w.transform("std") > 0]
    x["bin"] = x.groupby("era", observed=True).X_w.transform(
        lambda v: pd.qcut(v, 10, labels=False, duplicates="drop"))
    print("\nEDP WITHIN UNIT-DAY: mean o50 deviation (EUR/MWh) by decile of the X deviation")
    t = x.groupby(["era", "bin"], observed=True).agg(X_w=("X_w", "mean"), o50_w=("o50_w", "mean"))
    print(t.unstack("era").round(1).to_string())
    print(f"  ({len(x):,} unit-periods, {x.groupby(['unit', 'date']).ngroups:,} unit-days)")

    # The sharper version: in periods where an EDP unit SETS the price, its offer
    # there equals p*, so the FOC reads p* = lambda_day + X and, within a
    # unit-day, p* should move one-for-one with X.
    mg = edp[edp.marginal & edp.X.notna()].copy()
    print(f"\nEDP PRICE-SETTING periods: {edp.marginal.mean():.3f} of EDP unit-periods; "
          f"{len(mg):,} with X defined")
    print(mg.groupby("era", observed=True).size().rename("unit-periods").to_string())
    k = mg.groupby(["unit", "date"]).period.transform("size")
    mg = mg[k >= 2]
    for c in ("X", "p_zone"):
        mg[c + "_w"] = mg[c] - mg.groupby(["unit", "date"])[c].transform("mean")
    mg = mg[mg.groupby(["unit", "date"]).X_w.transform("std") > 0]
    print(f"  unit-days with 2+ price-setting periods and varying X: "
          f"{mg.groupby(['unit', 'date']).ngroups:,} ({len(mg):,} unit-periods)")
    for era, g in mg.groupby("era", observed=True):
        if len(g) < 200:
            print(f"  {era}: too few ({len(g)})")
            continue
        g = g.assign(bin=pd.qcut(g.X_w, 5, labels=False, duplicates="drop"))
        t = g.groupby("bin").agg(X_w=("X_w", "mean"), p_w=("p_zone_w", "mean"), n=("X_w", "size"))
        b = np.polyfit(g.X_w, g.p_zone_w, 1)[0]
        gg = g.dropna(subset=["X_built"])
        xg = gg.X_built - gg.groupby(["unit", "date"]).X_built.transform("mean")
        bg = np.polyfit(xg, gg.p_zone_w, 1)[0]
        print(f"  {era}: within unit-day slope of p* on X = {b:.3f} (on X as built {bg:.3f}; "
              "supply-function Nash predicts 1, price-taking 0)")
        print(t.round(2).T.to_string())

    print("\nEDP PUMPING: twin's cleared purchase by hour, MW per unit-period (units with a twin)")
    tw = edp[edp.twin.notna()]
    print(tw.groupby(["era", "hour"], observed=True).pump_mw.mean().unstack().reindex(columns=hours)
          .round(0).to_string())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="report on the saved panel only")
    ap.add_argument("--attach-x", action="store_true",
                    help="re-attach X from firm_x.parquet to the saved panel, without re-reading bids")
    args = ap.parse_args()
    if args.attach_x:
        old = pd.read_parquet(OUT)
        d = attach_x(old)
        m = old[["date", "period", "unit", "X"]].merge(d[["date", "period", "unit", "X_built"]],
                                                       on=["date", "period", "unit"]).dropna()
        diff = (m.X - m.X_built).abs()
        print(f"old X vs new X_built: corr {m.X.corr(m.X_built):.6f}, median |diff| {diff.median():.4f}, "
              f"exact (<1e-3) {(diff < 1e-3).mean():.3f} over {len(m):,} unit-periods")
        if not (m.X.corr(m.X_built) > 0.9999):
            print("FAIL: as-built X does not reproduce the saved panel's X; not overwriting")
            return 1
        d.to_parquet(OUT, index=False)
        print(f"wrote {OUT.relative_to(ROOT)}")
    else:
        d = pd.read_parquet(OUT) if args.report else build()
    report(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
