#!/usr/bin/env python3
"""First stage of each firm's own-basin rainfall on its net position: does nature move n?

    .venv/bin/python scripts/fetch/fetch_hydro_precipitation.py   # input (18 points)
    .venv/bin/python scripts/analysis/hydro_rain_first_stage.py

The design (notes/rq-hydro-rain-first-stage.md): a firm's hydro sits in its own
river basins, and rain in those basins makes it sell more, moving its net position
n for reasons the firm does not choose. If the shift is firm-specific, it can
instrument X = n / |RD'| in an equation for the firm's THERMAL offers, whose cost
rain does not change. This script only asks the first question: does a firm's own
rainfall move its n, beyond what moves every firm that week?

WATER INDEX. For basin b, R_bt is precipitation (ERA5, one point near the
reservoirs) summed over the K days before day t (K = 90 and 30), as a z-score
against basin b's mean and sd in the same calendar month over 2018-2026. For firm
f, H_ft = sum over its hydro units u (pumped storage excluded) of capacity_u,month
(GW, `cab` max power, median of the month) x z_basin(u),t: GW-weighted, so a firm
with more hydro moves more. The share-weighted index S (capacity shares summing to
1) has no size: with week effects only the firms' different basins identify it.

PANEL. Six firms with hydro (EDP, Iberdrola, Endesa, Naturgy, Repsol, Movhera);
weekly; n = mean exposed net position (`firm_incentive_net.parquet`, net_exp_mw)
over the week, q = mean exposed sell volume; H taken the day before the week starts,
so rain inside the week does not enter.

    n_fw = a_(f x calendar month) + d_w + pi * H_fw + e

d_w, the week effect, absorbs everything common: the price, demand, rain that falls
on every basin. Standard errors clustered by month of sample (the 90-day index is
autocorrelated); F = t^2. Per-firm rows drop the week effect (one firm's own series,
year and calendar-month effects): they show size, not identification.

Unit -> basin is a hand map (UNIT_BASIN), checked against `descr`. Ownership is the
static owner group (`firm_incentive_net`'s convention); Repsol owns Viesgo's hydro
only from 2018-11-02, Movhera the Douro dams from 2020-12.

Writes outputs/tables/hydro_rain_first_stage.csv.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT = TABLES / "hydro_rain_first_stage.csv"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA")

# Hydro (not pumped) units of the six firms -> the precipitation point of their basin.
UNIT_BASIN = {
    # EDP: Portugal's cascades and Asturias
    "ALIMA": "pt_lima_cavado", "ACAVADO": "pt_lima_cavado", "ADOURO": "pt_douro",
    "TEMON": "pt_tejo_zezere", "MONDEGO": "pt_mondego", "GUADIA": "pt_guadiana", "HCHI": "cantabrico",
    # Iberdrola: the plateau, Galicia, Tamega
    "DUER": "duero", "TAJO": "tajo", "SIL": "galicia_sil_mino", "TAMEGA": "pt_tamega",
    "JUCA": "jucar", "EBRA": "ebro",
    # Endesa: Pyrenees and Catalonia, Galicia, the south
    "EBRFEN": "pirineo", "TERE": "catalunya_ter", "SBEU": "galicia_sil_mino", "GDLQ": "guadalquivir",
    "GDNA": "guadiana", "TEES": "duero", "EBRERZ": "ebro",
    # Naturgy: Galicia
    "UFMI": "galicia_sil_mino", "UFGC": "galicia_costa", "UFTA": "tajo",
    # Repsol: Cantabria
    "VIES": "cantabrico",
    # Movhera: the Douro dams bought from EDP
    "DOUSUP": "pt_douro",
}
UNIT_FIRM = {u: f for f, us in {
    "EDP": ["ALIMA", "ACAVADO", "ADOURO", "TEMON", "MONDEGO", "GUADIA", "HCHI"],
    "IBERDROLA": ["DUER", "TAJO", "SIL", "TAMEGA", "JUCA", "EBRA"],
    "ENDESA": ["EBRFEN", "TERE", "SBEU", "GDLQ", "GDNA", "TEES", "EBRERZ"],
    "NATURGY": ["UFMI", "UFGC", "UFTA"], "REPSOL": ["VIES"], "MOVHERA": ["DOUSUP"]}.items() for u in us}
WINDOWS = (90, 30)


def basin_z(k: int) -> pd.DataFrame:
    """date x basin: precipitation over the k days before the date, z-scored by basin x calendar month."""
    p = pd.read_parquet(DATA / "weather/precipitation_basins_daily.parquet", columns=["basin", "date", "precipitation_sum"])
    w = p.pivot(index="date", columns="basin", values="precipitation_sum").sort_index()
    r = w.rolling(k, min_periods=k).sum().shift(1)          # the k days BEFORE the date
    m = r.index.month
    return (r - r.groupby(m).transform("mean")) / r.groupby(m).transform("std")


def capacity() -> pd.DataFrame:
    """unit x month: median `cab` max power (GW) for the mapped hydro units."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet"))):
        c = pd.read_parquet(f, columns=["date", "unit", "max_power_mw"], filters=[("unit", "in", list(UNIT_BASIN))])
        frames.append(c)
    c = pd.concat(frames)
    c["month"] = pd.to_datetime(c.date).dt.to_period("M")
    return c.groupby(["unit", "month"]).max_power_mw.median().div(1000).rename("gw").reset_index()


def firm_index(z: pd.DataFrame, cap: pd.DataFrame, shares: bool = False) -> pd.DataFrame:
    """date x firm water index: sum over units of GW (or capacity share) x the unit's basin z."""
    days = pd.DataFrame({"date": z.index})
    days["month"] = days.date.dt.to_period("M")
    out = {}
    for f in FIRMS:
        cf = cap[cap.unit.map(UNIT_FIRM) == f]
        wide = cf.pivot(index="month", columns="unit", values="gw").fillna(0.0)
        if shares:
            wide = wide.div(wide.sum(axis=1), axis=0)
        wd = wide.reindex(days.month).to_numpy()
        zb = z[[UNIT_BASIN[u] for u in wide.columns]].to_numpy()
        out[f] = np.nansum(wd * zb, axis=1) * np.where(np.isnan(zb).all(axis=1), np.nan, 1.0)
    return pd.DataFrame(out, index=z.index)


def weekly_positions() -> pd.DataFrame:
    x = pd.read_parquet(TABLES / "firm_incentive_net.parquet", columns=["date", "firm", "net_exp_mw", "q_exp_mw"],
                        filters=[("firm", "in", list(FIRMS))])
    x["week"] = x.date - pd.to_timedelta(x.date.dt.dayofweek, unit="D")
    return x.groupby(["firm", "week"]).agg(n=("net_exp_mw", "mean"), q=("q_exp_mw", "mean")).reset_index()


def regress(d: pd.DataFrame, y: str, h: str, fes: list[str], label: str, cl: str = "msample") -> dict:
    d = d.dropna(subset=[y, h])
    w = demean(d, [y, h], fes)
    b, se = ols(w[y].to_numpy(), w[[h]].to_numpy(), d[cl].to_numpy())
    row = {"sample": label, "y": y, "index": h, "effects": " + ".join(fes), "cluster": cl, "n_obs": len(d),
           "clusters": d[cl].nunique(), "b": b[0], "se": se[0], "F": (b[0] / se[0]) ** 2,
           "sd_index_within": float(w[h].std()), "sd_y_within": float(w[y].std())}
    row["std_effect"] = row["b"] * row["sd_index_within"] / row["sd_y_within"]
    print(f"  {label:34s} {y:2s} on {h:6s}  b {b[0]:+8.1f} ({se[0]:6.1f})  F {row['F']:7.1f}  "
          f"1 sd of index moves y by {row['std_effect']:+.2f} sd   n={len(d):,}  clusters={d[cl].nunique()}")
    return row


def main() -> int:
    cap = capacity()
    pos = weekly_positions()
    rows = []
    for k in WINDOWS:
        z = basin_z(k)
        H, S = firm_index(z, cap), firm_index(z, cap, shares=True)
        if k == 90:
            print("correlation of the firms' share-weighted 90-day indices (weekly):")
            print(S.resample("W-MON").first().corr().round(2).to_string())
        for name, idx in ((f"H{k}", H), (f"S{k}", S)):
            h = idx.stack().rename(name).reset_index().rename(columns={"level_1": "firm"})
            h = h[h.date.dt.dayofweek == 0].rename(columns={"date": "week"})  # the day the week starts
            pos = pos.merge(h, on=["firm", "week"], how="left")
    pos = pos[pos.week >= "2018-04-02"].copy()
    pos["fmoy"] = pos.firm + "_" + pos.week.dt.month.astype(str)
    pos["msample"] = pos.week.dt.strftime("%Y%m")
    pos["qsample"] = pos.week.dt.year.astype(str) + "Q" + pos.week.dt.quarter.astype(str)
    pos["yr"] = pos.firm + "_" + pos.week.dt.year.astype(str)
    print(f"\n{len(pos):,} firm-weeks, {pos.week.min().date()} -> {pos.week.max().date()}\n")
    print("POOLED, week effects: own rain beyond what every firm gets that week")
    for k in WINDOWS:
        for y in ("n", "q"):
            rows.append(regress(pos, y, f"H{k}", ["fmoy", "week"], f"pooled, {k} days"))
    rows.append(regress(pos, "n", "H90", ["fmoy", "week"], "pooled, 90 days, quarter clusters", cl="qsample"))
    rows.append(regress(pos[pos.firm != "MOVHERA"], "n", "H90", ["fmoy", "week"], "pooled, 90 days, without Movhera"))
    # The GW index varies across firms on a given week partly as common rain x hydro size.
    # The share-weighted index has no size: only the firms' different basins identify it.
    for k in WINDOWS:
        rows.append(regress(pos, "n", f"S{k}", ["fmoy", "week"], f"pooled, {k} days, basin mix only"))
    print("\nBY FIRM, no week effects (size only, not identification)")
    for f in FIRMS:
        rows.append(regress(pos[pos.firm == f], "n", "H90", ["fmoy", "yr"], f"{f}, 90 days"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
