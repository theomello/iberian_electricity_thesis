#!/usr/bin/env python3
"""Step 1 of the minimum-income near-miss design: is the threshold clean, and what do
withdrawn plants do?

    .venv/bin/python scripts/analysis/mic_near_miss_describe.py [--restrict] [--single]

Spec `docs/specs/2026-10-20-mic-near-miss-design.md` §3.2 and §4 step 1. Reads
`outputs/tables/mic_running.parquet` (`build/build_mic_running.py`); rows flagged there
(more than four hours not re-clearable) are left out.

CHECKS at r_A = 0 (`lib/rd.rd_jump`: local linear each side, triangular kernel, bandwidth
€2/MWh, errors clustered by date):
  accepted          cleared in ≥ 4 hours
  covariates        v, F; REE's D-1 forecasts of D's demand, wind and solar (ESIOS 1775,
                    1777, 1779, daily mean MWh); MIBGAS's Spanish index at D−2 (known when
                    offers close); ran_prev (the unit scheduled in PDBF in ≥ 4 periods on
                    D−1); weekend
  density           McCrary on r_A (`lib/rd.mccrary`)
  the unit's fate   pdvd_mw, id_mw, run_mw (below): the unit's own schedule, not its
                    owner's stake, which is step 2

FATE of each unit-day within €2: pdvd_mw, the mean over D's periods of its schedule after
REE's technical constraints (OMIE `pdvd`, all roles); id_mw, its net cleared intraday sales
(all sessions, sell − buy) averaged the same way; run_mw = pdvd_mw + id_mw. A withdrawn unit
is REE-scheduled if pdvd_mw > 1 MW, sold intraday if id_mw > 1 MW, idle if neither.

STOP RULE (spec §4 step 1): the jump in the accepted share is below 0.5; the density test
rejects at 1%; two or more covariates jump at 1%; fewer than 1,000 single-unit firm-days
(one unit within €2 for the group that day) in 2019-01-01 → 2024-06-13.

Writes outputs/tables/mic_near_miss_rd.csv and mic_near_miss_fate.csv.

--restrict (plan Task 6, after step 1 stopped): only unit-days on which the condition can bind
(`can_bind`: a fixed term, or some MW offered below v), written with suffix `_bind`. Either
way, if the columns are there, it prints the re-clearing's price shift for withdrawn units
near the threshold against the plant's added MW over the local slope of the effective curve.

--single (after the restricted check, note §1.6): only days on which exactly one unit in the
whole market is within €2 of its threshold, so the algorithm has no choice to make between
near-miss plants; suffix `_single`. The selection looks at other units' margins, which the
focal unit's status moves through the price, so it is not wholly independent of the side.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from rd import mccrary, rd_jump  # noqa: E402

DATA = ROOT / "data"
T = ROOT / "outputs/tables"
H = 2.0
FIRMS = ["NATURGY", "EDP", "ENDESA", "IBERDROLA"]
PANEL_END = pd.Timestamp("2024-06-13")
COVARIATES = ["v", "F", "fc_demand", "fc_wind", "fc_solar", "gas_d2", "ran_prev", "weekend"]


def forecasts() -> pd.DataFrame:
    out = None
    for name, i in {"fc_demand": 1775, "fc_wind": 1777, "fc_solar": 1779}.items():
        f = pd.read_parquet(DATA / f"esios/esios_{i}.parquet", columns=["datetime", "value"])
        f = f.assign(date=pd.to_datetime(f.datetime.str[:10])).groupby("date").value.mean().rename(name)
        out = f.to_frame() if out is None else out.join(f, how="outer")
    return out.reset_index()


def gas() -> pd.DataFrame:
    g = pd.read_parquet(DATA / "mibgas/mibgas_price_index_daily.parquet", columns=["date", "mibgas_es_eur_mwh"])
    g["date"] = pd.to_datetime(g.date) + pd.Timedelta(days=2)
    return g.rename(columns={"mibgas_es_eur_mwh": "gas_d2"})


def per_unit_day(root: Path, prefix: str, units: set, months: list[str], cols: list[str], filters=None) -> pd.DataFrame:
    parts = []
    for ym in months:
        f = root / f"{prefix}_{ym}.parquet"
        if not f.exists():
            continue
        t = pq.read_table(f, columns=cols, filters=filters).to_pandas()
        t["unit"] = t.unit.astype(str)
        parts.append(t[t.unit.isin(units)])
    t = pd.concat(parts, ignore_index=True)
    t["date"] = pd.to_datetime(t.date)
    return t


def months_of(d: pd.DataFrame, pad: int = 0) -> list[str]:
    lo, hi = d.date.min() - pd.Timedelta(days=pad), d.date.max() + pd.Timedelta(days=pad)
    return [p.strftime("%Y%m") for p in pd.period_range(lo, hi, freq="M")]


def shift_check(d: pd.DataFrame) -> None:
    w = d[~d.accepted & d.add_mw.notna() & (d.r.abs() < H)]
    pred = -w.add_mw / w.slope_local
    ratio = (w.dp_mean / pred).replace([np.inf, -np.inf], np.nan)
    print(f"\nprice shift, withdrawn units with |r| < {H:g} re-cleared ({len(w):,}): median {w.dp_mean.median():.3f} €/MWh; "
          f"added MW / local slope predicts {pred.median():.3f}; corr {w.dp_mean.corr(pred):.2f}; "
          f"shift/prediction p10 {ratio.quantile(.1):.2f}, median {ratio.median():.2f}, p90 {ratio.quantile(.9):.2f}; "
          f"median added {w.add_mw.median():.0f} MW, slope {w.slope_local.median():.0f} MW per €/MWh")


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--restrict", action="store_true", help="only unit-days on which the condition can bind")
    ap.add_argument("--single", action="store_true", help="only days with exactly one unit within the bandwidth")
    args = ap.parse_args()
    suffix = ("_bind" if args.restrict else "") + ("_single" if args.single else "")
    d = pd.read_parquet(T / "mic_running.parquet")
    d["date"] = pd.to_datetime(d.date)
    n0 = len(d)
    d = d[~d.flag & d.r_A.notna()].copy()
    print(f"mic_running: {n0:,} unit-days, {len(d):,} kept (not flagged, r_A defined)")
    if "add_mw" in d.columns:
        shift_check(d)
    if args.restrict:
        near = d.r_A.abs() < H
        print(f"--restrict: can bind on {d.can_bind.mean():.1%} of kept unit-days, {d[near].can_bind.mean():.1%} within €{H:g}")
        d = d[d.can_bind].copy()
    if args.single:
        per_day = d[d.r_A.abs() < H].groupby("date").size()
        one = per_day.index[per_day == 1]
        print(f"--single: {len(one):,} of {len(per_day):,} days with a unit within €{H:g} have exactly one")
        d = d[d.date.isin(one)].copy()
    units = set(d.unit)

    # covariates
    d = d.merge(forecasts(), on="date", how="left").merge(gas(), on="date", how="left")
    pdbf = per_unit_day(DATA / "omie/pdbf/parquet", "pdbf", units, months_of(d, pad=31),
                        ["date", "period", "unit", "schedule_mw"])
    run = (pdbf.groupby(["date", "unit", "period"]).schedule_mw.sum().gt(0)
           .groupby(level=["date", "unit"]).sum().ge(4).rename("ran_prev").reset_index())
    run["date"] = run.date + pd.Timedelta(days=1)
    d = d.merge(run, on=["date", "unit"], how="left")
    d["ran_prev"] = d.ran_prev.fillna(False).astype(float)
    d["weekend"] = (d.date.dt.dayofweek >= 5).astype(float)
    d["accepted_f"] = d.accepted.astype(float)

    # fate of near-miss units
    near = d[d.r_A.abs() < H]
    nu = set(near.unit)
    pv = per_unit_day(DATA / "omie/pdvd/parquet", "pdvd", nu, months_of(near), ["date", "period", "unit", "schedule_mw"])
    pv = (pv.groupby(["date", "unit", "period"]).schedule_mw.sum().groupby(level=["date", "unit"]).sum() / 24).rename("pdvd_mw")
    idt = per_unit_day(DATA / "omie/intraday/parquet", "intraday", nu, months_of(near, pad=1),
                       ["date", "period", "unit", "side", "power_mw", "status"], filters=[("status", "==", "C")])
    idt["net"] = np.where(idt.side.astype(str) == "V", idt.power_mw, -idt.power_mw)
    idm = (idt.groupby(["date", "unit"]).net.sum() / 24).rename("id_mw")
    d = d.merge(pv.reset_index(), on=["date", "unit"], how="left").merge(idm.reset_index(), on=["date", "unit"], how="left")
    near_idx = d.r_A.abs() < H
    d.loc[near_idx, ["pdvd_mw", "id_mw"]] = d.loc[near_idx, ["pdvd_mw", "id_mw"]].fillna(0.0)
    d["run_mw"] = d.pdvd_mw + d.id_mw

    # RD checks
    rows = []
    for name, col in [("accepted", "accepted_f")] + [(c, c) for c in COVARIATES] + \
                     [("pdvd_mw", "pdvd_mw"), ("id_mw", "id_mw"), ("run_mw", "run_mw")]:
        j = rd_jump(d[col], d.r_A, d.date.dt.strftime("%Y%m%d"), h=H)
        rows.append({"check": name, **{k: j[k] for k in ("tau", "se", "p", "n_left", "n_right")}})
    mc = mccrary(d.r_A, h=H, b=0.05)
    rows.append({"check": "density (McCrary, theta)", "tau": mc["theta"], "se": mc["se"], "p": mc["p"],
                 "n_left": int((d.r_A.between(-H, 0, inclusive="left")).sum()),
                 "n_right": int((d.r_A.between(0, H, inclusive="left")).sum())})
    rd = pd.DataFrame(rows)
    rd.to_csv(T / f"mic_near_miss_rd{suffix}.csv", index=False)
    with pd.option_context("display.width", 140, "display.float_format", "{:.4g}".format):
        print(rd.to_string(index=False))

    # fate table
    near = d[d.r_A.abs() < H].copy()
    near["side"] = np.where(near.r_A < 0, "withdrawn", "accepted")
    near["year"] = near.date.dt.year.astype(str)
    near["grp"] = near.group.where(near.group.isin(FIRMS), "other")
    near["pdvd_on"] = near.pdvd_mw > 1
    near["id_on"] = near.id_mw > 1
    near["idle"] = ~near.pdvd_on & ~near.id_on

    def fate(g: pd.DataFrame) -> pd.Series:
        return pd.Series({"n": len(g), "pdvd_share": g.pdvd_on.mean(), "pdvd_mw": g.pdvd_mw.mean(),
                          "id_share": g.id_on.mean(), "id_mw": g.id_mw.mean(), "run_mw": g.run_mw.mean(),
                          "idle_share": g.idle.mean()})

    parts = [near.groupby("side").apply(fate, include_groups=False).reset_index().assign(year="all", grp="all"),
             near.groupby(["side", "year"]).apply(fate, include_groups=False).reset_index().assign(grp="all"),
             near.groupby(["side", "grp"]).apply(fate, include_groups=False).reset_index().assign(year="all")]
    ft = pd.concat(parts, ignore_index=True).rename(columns={"grp": "group"})
    ft = ft[["side", "year", "group", "n", "pdvd_share", "pdvd_mw", "id_share", "id_mw", "run_mw", "idle_share"]]
    ft.to_csv(T / f"mic_near_miss_fate{suffix}.csv", index=False)
    with pd.option_context("display.width", 140, "display.float_format", "{:.3f}".format):
        print(ft.to_string(index=False))

    # single-unit firm-days in the intraday panel's window
    w = d[(d.r_A.abs() < H) & d.group.notna() & (d.date <= PANEL_END)]
    fd = w.groupby(["group", "date"]).size()
    single = int((fd == 1).sum())
    print(f"\nfirm-days within €{H:g} to {PANEL_END.date()}: {len(fd):,}; single-unit {single:,}")

    jump = rd.set_index("check").loc["accepted", "tau"]
    cov = rd[rd.check.isin(COVARIATES)]
    n_cov = int((cov.p < 0.01).sum())
    stops = {
        f"accepted-share jump {jump:.3f} < 0.5": jump < 0.5,
        f"density test p {mc['p']:.3g} < 0.01": mc["p"] < 0.01,
        f"{n_cov} covariates jump at 1% (≥ 2 stops)": n_cov >= 2,
        f"single-unit firm-days {single:,} < 1,000": single < 1000,
    }
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print(f"stop rule (step 1): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
