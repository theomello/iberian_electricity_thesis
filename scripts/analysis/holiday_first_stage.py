#!/usr/bin/env python3
"""The regional-holiday dose, its first stage on each firm's stake, and the design's power.

    .venv/bin/python scripts/analysis/holiday_first_stage.py --dose
    .venv/bin/python scripts/analysis/holiday_first_stage.py --first-stage
    .venv/bin/python scripts/analysis/holiday_first_stage.py --power

Step 2 of `docs/specs/2026-10-20-regional-holidays-design.md`; plan
`docs/plans/2026-10-20-regional-holidays-step2.md`.

DOSE (`--dose` → outputs/tables/holiday_dose.parquet, holiday_profile.csv). For group f on
day d, hour h:

    dose = (Σ_local areas e_fa·H_ad + e_f,ES·ES_d + e_f,PT·H_PT,d) × p_h

with step 1's exposures from the run that left d's year out (`holiday_exposure_loyo.csv`),
the indicators of `build_holiday_exposure.design` (local areas on days with at most three
mainland regions off; ES = share of mainland demand off on the others; PT), a merged area
("AS+EX") on whenever either member is, and placebo areas (islands, Ceuta, Melilla) left
out: their load is not bought in MIBEL. Weekday holidays only (spec §3.1): weekend doses are
0. p_h: the hourly profile of the mainland demand drop on the Spain-only national days
against their reference days (`ree_realtime_5min`), mean 1, so a day's mean dose is its
exposure. dose > 0: the firm buys that many MW less, so its net position rises.

FIRST STAGE (`--first-stage` → outputs/tables/holiday_first_stage.csv). The stake on the
dose, pooled and for Endesa alone (its dose and stake interacted with an Endesa indicator,
the other firms' terms in the same regression):
  firm, hydro, at cost   one row per hydro owner and hour (`hcompcost`): n at the cost point
                         (GW) on the dose (GW); Zb = n / |RD′| on P = dose / |RD′|; group ×
                         month and hour effects; 2019-01 → 2025-09
  firm, five, actual     `firm_x` clean rows: exposed n (GW) on the dose; X on dose / slope;
                         firm × month and period effects; 2018-01 → 2026-05
  unit, hydro            the fixed-step main sample: Zb on P; unit × month and class × hour
  unit, thermal          `outage_offer_panel` gas and coal rows with a cost: X on the dose
                         (GW); unit × week and class × date × hour
Clusters by date (the event, spec §8) and by week. F = t².

POWER (`--power` → outputs/tables/holiday_power.csv). The outcome's response to the dose is
NOT estimated here. The outcome is residualised on the fixed effects alone; under β = 0 that
residual is the reduced form's, so its clustered standard error is the reduced form's se
under the null. se(β) = (Z′X)⁻¹ × se — exactly the just-identified IV variance at β = 0 —
and the minimum detectable β at 80% power, 5% two-sided, is 2.80 × se(β). Outcomes: the
fixed-step read at cf_s minus λ*30s (hydro, Zb instrumented by P) and the offer at 25% of
volume minus the cost known at bidding (thermal, X instrumented by the dose).

Stop rule (spec §4 step 2): STOP if the firm-level F on the dose is below 20, or if the
minimum detectable β⁻ (Endesa) exceeds 1 on every outcome. The larger of the date- and
week-clustered standard errors decides.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis", "build"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from build_holiday_exposure import design, mainland_shares, references  # noqa: E402
from holidays import ES_MAINLAND, PLACEBO, unshared  # noqa: E402
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_engine import NEAR  # noqa: E402
from step_estimator import wdemean  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402

T = ROOT / "outputs" / "tables"
CACHE = ROOT / "outputs" / "cache" / "step"
LOYO = T / "holiday_exposure_loyo.csv"
DOSE = T / "holiday_dose.parquet"
PROFILE = T / "holiday_profile.csv"
REALTIME = ROOT / "data" / "ree" / "ree_realtime_5min.parquet"
START, END = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-05-31")
REALTIME_END = pd.Timestamp("2025-12-12")
Z80 = 1.96 + 0.84


# ------------------------------------------------------------------ dose
def profile() -> pd.Series:
    rt = pd.read_parquet(REALTIME, columns=["ts", "local_date", "demand"])
    rt["date"] = pd.to_datetime(rt.local_date)
    rt = rt[rt.date < REALTIME_END]
    rt["hour"] = rt.ts.str[11:13].replace({"2A": "02", "2B": "02"}).astype(int)
    h = rt.groupby(["date", "hour"]).demand.mean().unstack()
    days = pd.DatetimeIndex(h.index)
    un = unshared(days)
    es_only = ((un[list(ES_MAINLAND)].sum(axis=1) == len(ES_MAINLAND)) & (un["PT"] == 0)).to_numpy() \
        & (days.dayofweek < 5)
    ref = references(days)
    sel = es_only & ref.left.notna().to_numpy() & ref.right.notna().to_numpy()
    base = (h.reindex(ref.left[sel]).to_numpy() + h.reindex(ref.right[sel]).to_numpy()) / 2
    drop = np.nanmean(base - h.loc[sel].to_numpy(), axis=0)
    print(f"profile from {int(sel.sum())} Spain-only national days; drop {drop.min():.0f}–{drop.max():.0f} MW by hour")
    return pd.Series(drop / drop.mean(), index=pd.RangeIndex(24, name="hour"), name="p_h")


def daily_dose() -> pd.DataFrame:
    loyo = pd.read_csv(LOYO)
    loyo = loyo[~loyo.group.isin(["ALL", "PASS"])]
    days = pd.date_range(START, END)
    hol, _ = design(days, mainland_shares())
    weekday = days.dayofweek < 5
    out = []
    for (g, y), r in loyo.groupby(["group", "year_out"]):
        sel = days.year == y
        tot = np.zeros(sel.sum())
        for area, e in zip(r.area, r.e_mw):
            members = area.split("+")
            if any(m in PLACEBO for m in members):
                continue
            tot += e * hol.loc[sel, members].max(axis=1).to_numpy()
        tot *= weekday[sel]
        out.append(pd.DataFrame({"group": g, "date": days[sel], "dose_day": tot}))
    return pd.concat(out, ignore_index=True)


def build_dose() -> int:
    p = profile()
    p.reset_index().to_csv(PROFILE, index=False)
    d = daily_dose()
    d = d.merge(p.reset_index(), how="cross")
    d["dose_mw"] = d.dose_day * d.p_h
    d[["group", "date", "hour", "dose_mw"]].to_parquet(DOSE, index=False)
    on = d.groupby(["group", "date"]).dose_day.first()
    print(f"wrote {DOSE.relative_to(ROOT)}: {len(d):,} rows; days with a dose, by group:")
    print((on > 0).groupby(level=0).sum().sort_values(ascending=False).head(10).to_string())
    return 0


def attach_dose(df: pd.DataFrame, group: str = "group") -> pd.DataFrame:
    z = pd.read_parquet(DOSE)
    z["date"] = z.date.astype("datetime64[ns]")
    df = df.copy()
    df["date"] = df.date.astype("datetime64[ns]")
    df = df.merge(z.rename(columns={"group": group}), on=[group, "date", "hour"], how="left")
    df["dose_mw"] = df.dose_mw.fillna(0.0)
    return df


# ------------------------------------------------------------------ inference
def iv_null(df: pd.DataFrame, xs: list[str], zs: list[str], codes: list[np.ndarray],
            clusters: dict[str, np.ndarray], y: str | None = None) -> list[dict]:
    """Just-identified IV pieces on fixed-effect-demeaned data: the first stage of each x on
    its own z (the other zs in), F = t²; and, given y, se(β) under β = 0 from the residual y
    itself: V = (Z′X)⁻¹ meat(Z, ỹ) (X′Z)⁻¹. The coefficient of y on z is never formed."""
    cols = xs + zs + ([y] if y else [])
    M = wdemean(df[cols].to_numpy(float), codes, np.ones(len(df)))
    X, Z = M[:, :len(xs)], M[:, len(xs):len(xs) + len(zs)]
    out = []
    zz_inv = np.linalg.inv(Z.T @ Z)
    for j, x in enumerate(xs):
        b = zz_inv @ Z.T @ X[:, j]
        e = X[:, j] - Z @ b
        row = {"x": x, "z": zs[j], "n": len(df), "pi": b[j], "sd_z": df[zs[j]].std(),
               "share_z_nonzero": float((df[zs[j]] != 0).mean())}
        for c, cl in clusters.items():
            V = zz_inv @ cluster_meat(Z, e, cl) @ zz_inv
            row[f"se_pi_{c}"] = float(np.sqrt(V[j, j]))
            row[f"F_{c}"] = float((b[j] / np.sqrt(V[j, j])) ** 2)
            row[f"clusters_{c}"] = int(pd.Series(cl).nunique())
        if y:
            A_inv = np.linalg.inv(Z.T @ X)
            for c, cl in clusters.items():
                V = A_inv @ cluster_meat(Z, M[:, -1], cl) @ A_inv.T
                se = float(np.sqrt(V[j, j]))
                row[f"se_beta_{c}"] = se
                row[f"mde_{c}"] = Z80 * se
            row["y"] = y
            row["sd_y_resid"] = float(M[:, -1].std())
        out.append(row)
    return out


def endesa_split(df: pd.DataFrame, x: str, z: str, firm: str = "group") -> tuple[list[str], list[str]]:
    e = (df[firm] == "ENDESA").to_numpy()
    df[f"{x}|ENDESA"], df[f"{x}|others"] = np.where(e, df[x], 0.0), np.where(e, 0.0, df[x])
    df[f"{z}|ENDESA"], df[f"{z}|others"] = np.where(e, df[z], 0.0), np.where(e, 0.0, df[z])
    return [f"{x}|ENDESA", f"{x}|others"], [f"{z}|ENDESA", f"{z}|others"]


def codes_of(*keys: pd.Series) -> list[np.ndarray]:
    return [pd.factorize(k)[0] for k in keys]


# ------------------------------------------------------------------ samples
def firm_hydro() -> pd.DataFrame:
    parts = []
    for f in sorted(CACHE.glob("hcompcost_2*.parquet")):
        ym = f.stem.split("_")[1]
        c = pd.read_parquet(f, columns=["hid", "group", "kb_sn", "kb_s"]).drop_duplicates(["hid", "group"])
        h = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period", "valid"])
        parts.append(c.merge(h, on="hid"))
    d = pd.concat(parts, ignore_index=True)
    d = d[d.valid]
    d["n_gw"] = d.kb_sn / NEAR / 1000
    d["slope"] = d.kb_s / NEAR
    d = d[d.slope >= sh.FLOOR].copy()
    d["Zb"] = d.n_gw * 1000 / d.slope
    d["hour"] = (d.period - 1).clip(0, 23)
    d = attach_dose(d)
    d["dose_gw"] = d.dose_mw / 1000
    d["P"] = d.dose_mw / d.slope
    d["ym"] = d.date.dt.strftime("%Y%m")
    d["week"] = d.date.dt.strftime("%G%V")
    return d


def firm_five() -> pd.DataFrame:
    d = pd.read_parquet(T / "firm_x.parquet", columns=["date", "period", "resolution_min", "firm", "net_mw",
                                                        "slope_net", "X", "clean"])
    d = d[d.clean & d.slope_net.gt(0) & d.X.notna()].rename(columns={"firm": "group"})
    d["hour"] = np.where(d.resolution_min == 60, d.period - 1, (d.period - 1) // 4).clip(0, 23)
    d = attach_dose(d)
    d["n_gw"], d["dose_gw"] = d.net_mw / 1000, d.dose_mw / 1000
    d["P"] = d.dose_mw / d.slope_net
    d["ym"] = d.date.dt.strftime("%Y%m")
    d["week"] = d.date.dt.strftime("%G%V")
    d["tkey"] = d.date.dt.strftime("%Y%m%d") + "|" + d.period.astype(str) + "|" + d.resolution_min.astype(str)
    return d


def unit_hydro() -> pd.DataFrame:
    from fixed_step_test import IN_PLAY, load_rows, stake_parts
    d = load_rows()
    d = d[d.Zb.notna() & (d.rel >= IN_PLAY) & (d.cls != "pumped")]
    d = stake_parts(d).drop(columns=["dose_mw", "D", "P"])  # the reactor dose; not used here
    d["hour"] = (d.period - 1).clip(0, 23)
    d = attach_dose(d)
    d["P"] = d.dose_mw / d.slope.where(d.slope >= sh.FLOOR)
    return d[d.P.notna()].copy()


def unit_thermal() -> pd.DataFrame:
    d = pd.read_parquet(T / "outage_offer_panel.parquet",
                        columns=["unit", "group", "cls", "date", "hour", "o25", "c_bid", "X", "wk"])
    d = d[d.cls.isin(["ccgt", "coal"]) & d.c_bid.notna() & d.X.notna() & d.o25.notna()]
    d["hour"] = d.hour.clip(0, 23)
    d = attach_dose(d)
    d["dose_gw"] = d.dose_mw / 1000
    d["y25"] = d.o25 - d.c_bid
    d["week"] = d.date.dt.strftime("%G%V")
    return d


# ------------------------------------------------------------------ runs
def run(which: str) -> list[dict]:
    rows = []

    def add(sample: str, cell: str, res: list[dict]) -> None:
        for r in res:
            rows.append({"sample": sample, "cell": cell} | r)
            f = " ".join(f"F_{c} {r[f'F_{c}']:.1f}" for c in ("date", "week"))
            m = (" | mde " + " ".join(f"{c} {r[f'mde_{c}']:.2f}" for c in ("date", "week"))) if "mde_date" in r else ""
            print(f"  {sample:22s} {cell:10s} {r['x']:16s} on {r['z']:14s} pi {r['pi']:+.3f}  {f}{m}", flush=True)

    power = which == "power"
    if not power:
        d = firm_hydro()
        cl = {"date": d.date.dt.strftime("%Y%m%d").to_numpy(), "week": d.week.to_numpy()}
        fe = codes_of(d.group + d.ym, d.hid.astype(str))
        add("firm hydro at cost", "pooled", iv_null(d, ["n_gw"], ["dose_gw"], fe, cl))
        add("firm hydro at cost", "pooled", iv_null(d, ["Zb"], ["P"], fe, cl))
        xs, zs = endesa_split(d, "Zb", "P")
        add("firm hydro at cost", "Endesa", iv_null(d, xs, zs, fe, cl))
        xs, zs = endesa_split(d, "n_gw", "dose_gw")
        add("firm hydro at cost", "Endesa", iv_null(d, xs, zs, fe, cl))

        d = firm_five()
        cl = {"date": d.date.dt.strftime("%Y%m%d").to_numpy(), "week": d.week.to_numpy()}
        fe = codes_of(d.group + d.ym, d.tkey)
        add("firm five actual", "pooled", iv_null(d, ["n_gw"], ["dose_gw"], fe, cl))
        add("firm five actual", "pooled", iv_null(d, ["X"], ["P"], fe, cl))
        xs, zs = endesa_split(d, "n_gw", "dose_gw")
        add("firm five actual", "Endesa", iv_null(d, xs, zs, fe, cl))
        xs, zs = endesa_split(d, "X", "P")
        add("firm five actual", "Endesa", iv_null(d, xs, zs, fe, cl))

    d = unit_hydro()
    cl = {"date": d.date.dt.strftime("%Y%m%d").to_numpy(), "week": d.week.to_numpy()}
    fe = codes_of(d.unit + d.ym, d.cls + d.hid.astype(str))
    y = "g_p_cf" if power else None
    add("unit hydro fixed step", "pooled", iv_null(d, ["Zb"], ["P"], fe, cl, y))
    xs, zs = endesa_split(d, "Zb", "P")
    add("unit hydro fixed step", "Endesa", iv_null(d, xs, zs, fe, cl, y))

    d = unit_thermal()
    cl = {"date": d.date.dt.strftime("%Y%m%d").to_numpy(), "week": d.week.to_numpy()}
    fe = codes_of(d.unit + d.wk.astype(str), d.cls + d.date.dt.strftime("%Y%m%d") + d.hour.astype(str))
    y = "y25" if power else None
    add("unit thermal", "pooled", iv_null(d, ["X"], ["dose_gw"], fe, cl, y))
    xs, zs = endesa_split(d, "X", "dose_gw")
    add("unit thermal", "Endesa", iv_null(d, xs, zs, fe, cl, y))
    return rows


def main() -> int:
    ap = ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dose", action="store_true")
    g.add_argument("--first-stage", action="store_true")
    g.add_argument("--power", action="store_true")
    a = ap.parse_args()
    if a.dose:
        return build_dose()
    which = "power" if a.power else "first"
    out = pd.DataFrame(run(which))
    path = T / ("holiday_power.csv" if a.power else "holiday_first_stage.csv")
    out.to_csv(path, index=False)
    print(f"wrote {path.relative_to(ROOT)}")
    if a.power:
        e = out[out.x.str.endswith("|ENDESA")]
        mde = e[["mde_date", "mde_week"]].max(axis=1)
        print("\nEndesa's minimum detectable β⁻ (larger of date/week se):",
              ", ".join(f"{s} {m:.2f}" for s, m in zip(e["sample"], mde)))
        print("stop rule (MDE):", "STOP" if (mde > 1).all() else "CONTINUE")
    else:
        f = out[(out["sample"].str.startswith("firm")) & (out.z == "dose_gw") & (out.cell == "pooled")]
        fmin = f[["F_date", "F_week"]].min(axis=1)
        print("\nfirm-level F on the dose (smaller of date/week):",
              ", ".join(f"{s} {v:.1f}" for s, v in zip(f["sample"], fmin)))
        print("stop rule (F):", "STOP" if (fmin < 20).all() else "CONTINUE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
