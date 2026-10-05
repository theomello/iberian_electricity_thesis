#!/usr/bin/env python3
"""First stage of each firm's own-catchment rainfall on its net position, on complete data.

    .venv/bin/python scripts/build/build_catchment_rain.py       # input: rain per plant catchment
    .venv/bin/python scripts/build/build_hydro_plant_units.py    # input: plant -> OMIE unit, by date
    .venv/bin/python scripts/analysis/hydro_rain_catchment_first_stage.py

The design is `hydro_rain_first_stage.py`'s (notes/rq-hydro-rain-first-stage.md):
rain in a firm's own catchments makes its hydro sell more and moves its net
position n for reasons it does not choose. That probe used one ERA5 point per basin
and each unit's latest owner. This one uses the rain over each plant's whole
upstream catchment (E-OBS, 0.25 degrees) and the owners in force each day, by share.

WATER INDEX. For plant j, R_jt is rain over its catchment summed over the K days
before day t (K = 90, 30), as a z-score against plant j's distribution of K-day
sums in the same calendar month over 1991-2020 (the climate normal). For firm f,

    H_ft = sum over plants j of  GW_j x share_fjt x z_jt

GW_j is JRC's capacity; share_fjt is f's ownership share of the OMIE unit offering
plant j on day t (`build_hydro_plant_units.owners_of_plants`). Plants with no OMIE
unit (no link) carry no owner and drop out. The share-weighted index S divides by
the firm's linked GW that day: no size, only the mix of catchments.

COVERAGE. The Spanish link reaches 49-98% of a cascade's REE capacity (DUER 96%,
TAJO 98%, EBRFEN 52%, JUCA 49%, GDLQ 51%). `RESCALED` scales each Spanish unit's
linked plants up to the unit's REE capacity: it assumes the unlinked plants share
the linked plants' rain, which is what catchments in one cascade mostly do.

PUMPED STORAGE. JRC's HPHS includes mixed plants with large natural inflow (Alqueva,
Villarino, Aldeadavila II, Alto Lindoso's neighbours), so the main index keeps them;
a robustness row leaves them out, as the single-point probe did.

PANEL and REGRESSION as in the probe: firm x week, n = mean exposed net position
(`firm_incentive_net.parquet`, on owners by date since 2026-10-03), H taken on the
Monday the week starts, so rain inside the week does not enter.

    n_fw = a_(f x calendar month) + d_w + pi * H_fw + e

Standard errors clustered by month of sample; F = t^2. With six firms, a wild
cluster bootstrap over FIRMS (Webb's six-point weights, null imposed) is the check
that firm-level dependence is not what makes the coefficient significant.

Writes outputs/tables/hydro_rain_catchment_first_stage.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from build_hydro_plant_units import owners_of_plants  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT = TABLES / "hydro_rain_catchment_first_stage.csv"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA")
WINDOWS = (90, 30)
NORMAL = ("1991-01-01", "2020-12-31")
START = "2018-04-02"          # the first Monday with a 90-day window inside 2018
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def plant_z(k: int) -> pd.DataFrame:
    """date x plant: catchment rain over the k days before the date, z-scored against
    the plant's 1991-2020 k-day sums in the same calendar month."""
    r = pd.read_parquet(DATA / "eobs/catchment_rain_daily.parquet")
    w = r.pivot(index="date", columns="plant_id", values="rr").sort_index()
    s = w.rolling(k, min_periods=k).sum().shift(1)                # the k days BEFORE the date
    base = s.loc[NORMAL[0]:NORMAL[1]]
    mu = base.groupby(base.index.month).mean()
    sd = base.groupby(base.index.month).std()
    m = s.index.month
    z = (s - mu.reindex(m).to_numpy()) / sd.reindex(m).to_numpy()
    return z.loc[START:]


def weights(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """plant_id, date, firm, gw (JRC capacity x share), type, unit: owners in force each Monday."""
    pc = pd.read_parquet(DATA / "eobs/plant_catchments.parquet", columns=["plant_id", "type", "capacity_mw"])
    df = pc.merge(pd.DataFrame({"date": dates}), how="cross")
    o = owners_of_plants(df)
    o = o[o.group.isin(FIRMS)].rename(columns={"group": "firm"})
    o["gw"] = o.capacity_mw / 1000 * o.share
    # RESCALED: each Spanish unit's linked plants scaled to the unit's REE capacity.
    cov = pd.read_parquet(DATA / "omie/registry/hydro_unit_coverage.parquet", columns=["unit", "matched_share"])
    f = o.unit.map(cov.set_index("unit").matched_share)
    o["gw_rescaled"] = o.gw / f.where(f > 0).fillna(1.0)
    return o[["plant_id", "date", "firm", "unit", "type", "gw", "gw_rescaled"]]


def firm_index(z: pd.DataFrame, w: pd.DataFrame, col: str = "gw", shares: bool = False,
               types: tuple = ("HDAM", "HROR", "HPHS")) -> pd.DataFrame:
    """firm, week, H: sum over the firm's plants of weight x the plant's z that Monday."""
    zz = z.rename_axis(index="date", columns="plant_id").stack().rename("z").reset_index()
    m = w[w.type.isin(types)].merge(zz, on=["plant_id", "date"], how="inner").dropna(subset=["z"])
    if shares:
        m[col] = m[col] / m.groupby(["firm", "date"])[col].transform("sum")
    m["v"] = m[col] * m.z
    return m.groupby(["firm", "date"]).v.sum().rename("H").reset_index().rename(columns={"date": "week"})


def weekly_positions() -> pd.DataFrame:
    x = pd.read_parquet(TABLES / "firm_incentive_net.parquet", columns=["date", "firm", "net_exp_mw", "q_exp_mw"],
                        filters=[("firm", "in", list(FIRMS))])
    x["week"] = x.date - pd.to_timedelta(x.date.dt.dayofweek, unit="D")
    return x.groupby(["firm", "week"]).agg(n=("net_exp_mw", "mean"), q=("q_exp_mw", "mean")).reset_index()


def wild_firm_p(y: np.ndarray, x: np.ndarray, firm: np.ndarray, cl: np.ndarray, b: float, se: float,
                reps: int = 9999) -> float:
    """Wild cluster bootstrap over firms, null imposed, Webb weights. y and x are already
    demeaned of the fixed effects, so under the null the restricted residual is y."""
    t_hat = abs(b / se)
    g, gi = np.unique(firm, return_inverse=True)
    rng = np.random.default_rng(0)
    draws = WEBB[rng.integers(0, 6, size=(reps, len(g)))]
    ts = np.empty(reps)
    for r in range(reps):
        yb = y * draws[r, gi]
        bb, sb = ols(yb, x[:, None], cl)
        ts[r] = abs(bb[0] / sb[0])
    return float((ts >= t_hat).mean())


def regress(d: pd.DataFrame, y: str, h: str, fes: list[str], label: str, cl: str = "msample",
            boot: bool = False) -> dict:
    d = d.dropna(subset=[y, h])
    w = demean(d, [y, h], fes)
    b, se = ols(w[y].to_numpy(), w[[h]].to_numpy(), d[cl].to_numpy())
    row = {"sample": label, "y": y, "index": h, "effects": " + ".join(fes), "cluster": cl, "n_obs": len(d),
           "firms": d.firm.nunique(), "clusters": d[cl].nunique(), "b": b[0], "se": se[0], "F": (b[0] / se[0]) ** 2,
           "sd_index_within": float(w[h].std()), "sd_y_within": float(w[y].std())}
    row["std_effect"] = row["b"] * row["sd_index_within"] / row["sd_y_within"]
    if boot:
        row["wild_firm_p"] = wild_firm_p(w[y].to_numpy(), w[h].to_numpy(), d.firm.to_numpy(), d[cl].to_numpy(),
                                         b[0], se[0])
    extra = f"  wild-by-firm p {row['wild_firm_p']:.4f}" if boot else ""
    print(f"  {label:44s} {y} on {h:9s} b {b[0]:+8.1f} ({se[0]:6.1f})  F {row['F']:7.1f}  "
          f"1 sd moves y {row['std_effect']:+.2f} sd  n={len(d):,}{extra}")
    return row


def main() -> int:
    pos = weekly_positions()
    pos = pos[pos.week >= START].copy()
    mondays = pd.DatetimeIndex(sorted(pos.week.unique()))
    w = weights(mondays)
    lw = w.groupby(["firm", "type"]).gw.sum().unstack().div(len(mondays)).round(2)
    print("mean linked hydro, GW (JRC capacity x share), by firm and JRC type:\n" + lw.fillna(0).to_string() + "\n")
    for k in WINDOWS:
        z = plant_z(k).reindex(mondays)
        for name, kw in ((f"H{k}", {}), (f"S{k}", {"shares": True}), (f"R{k}", {"col": "gw_rescaled"}),
                         (f"N{k}", {"types": ("HDAM", "HROR")})):
            pos = pos.merge(firm_index(z, w, **kw).rename(columns={"H": name}), on=["firm", "week"], how="left")
    pos["fmoy"] = pos.firm + "_" + pos.week.dt.month.astype(str)
    pos["msample"] = pos.week.dt.strftime("%Y%m")
    pos["qsample"] = pos.week.dt.year.astype(str) + "Q" + pos.week.dt.quarter.astype(str)
    pos["yr"] = pos.firm + "_" + pos.week.dt.year.astype(str)
    print(f"{len(pos):,} firm-weeks, {pos.week.min().date()} -> {pos.week.max().date()}")
    print("correlation of the firms' share-weighted 90-day indices (weekly):")
    print(pos.pivot(index="week", columns="firm", values="S90").corr().round(2).to_string() + "\n")

    rows = []
    print("POOLED, week effects: own rain beyond what every firm gets that week")
    for k in WINDOWS:
        rows.append(regress(pos, "n", f"H{k}", ["fmoy", "week"], f"pooled, {k} days", boot=True))
        rows.append(regress(pos, "q", f"H{k}", ["fmoy", "week"], f"pooled, {k} days"))
    rows.append(regress(pos, "n", "H90", ["fmoy", "week"], "pooled, 90 days, quarter clusters", cl="qsample"))
    rows.append(regress(pos[pos.firm != "MOVHERA"], "n", "H90", ["fmoy", "week"], "pooled, 90 days, without Movhera"))
    for k in WINDOWS:
        rows.append(regress(pos, "n", f"S{k}", ["fmoy", "week"], f"pooled, {k} days, catchment mix only"))
        rows.append(regress(pos, "n", f"R{k}", ["fmoy", "week"], f"pooled, {k} days, rescaled to REE capacity"))
        rows.append(regress(pos, "n", f"N{k}", ["fmoy", "week"], f"pooled, {k} days, without pumped storage"))
    print("\nBY FIRM, no week effects (size only, not identification)")
    for f in FIRMS:
        rows.append(regress(pos[pos.firm == f], "n", "H90", ["fmoy", "yr"], f"{f}, 90 days"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
