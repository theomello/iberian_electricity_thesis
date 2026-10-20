#!/usr/bin/env python3
"""The France link, step 2: the slope French supply adds, the corrected stake, the first stage
and the power.

    .venv/bin/python scripts/analysis/france_link_first_stage.py --calibrate
    .venv/bin/python scripts/analysis/france_link_first_stage.py --first-stage

Spec `docs/specs/2026-10-20-france-link-design.md` §3.3–3.4, §4 step 2; plan
`docs/plans/2026-10-20-france-link-step2.md`; step 1 in `notes/rq-france-link.md`.

CALIBRATE (`--calibrate` → outputs/tables/france_link_slope.csv). While the line to France
has room, French supply flattens the Iberian residual demand by S MW per €/MWh. A GW of
Iberian residual demand (REE's D-1 forecast of demand net of wind and solar, ESIOS 1775 −
1777 − 1779) moves the price by a when the line is full and by b when it is open, so
(|RD′| + S)/|RD′| = a/b and S = |RD′| · (a/b − 1), with |RD′| the median slope of the hour's
effective curve within ±€5 of the price (step cache `market`). The line's state enters as
its prediction (p_open_full, `build/build_france_link.py`), never as the outcome: a and b are
the slopes at p = 0 and p = 1 of a regression of the Spanish price on RDf, RDf × p and p, with
date and month × hour effects, errors clustered by date.

FIRST STAGE AND POWER (`--first-stage` → outputs/tables/france_link_first_stage.csv). The
corrected at-cost stake Zb_c = n · 1000 / (slope + S · 1[open]), with n (GW) and slope (MW per
€/MWh) the firm's net position and residual-demand slope at its cost point (`hcompcost`,
`compcost`, slope ≥ FLOOR) and open the line's actual state, on the instrument Z = Zb ×
z_open, controls Zb, Zb × p_open_ib, Zb × RDf, Zb × gas (MIBGAS at D−2), partialled out after
the fixed effects (`iv_ctrl`). For S, S/2 and 2S. Samples, effects and outcomes as in the
holiday step 2 (`holiday_first_stage.py`): firm hydro at cost (group × month, hour), unit
hydro on the fixed-step main sample (unit × month, class × hour; outcome g_p_cf), unit thermal
on gas and coal (unit × week, class × date × hour; outcome o25 − c_bid; `compcost` ends
2023-12). Power: se(β) under β = 0 from the outcome's residual on the effects and controls,
MDE = 2.80 × se(β); the outcome is never fitted on Z.

STOP RULE (plan): STOP if the pooled first-stage F (smaller of date and week clusters) is
below 20 on both unit-level samples, or if the pooled MDE (larger of the two) exceeds 1 on both
outcomes.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_engine import NEAR  # noqa: E402
from step_estimator import wdemean  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402

T = ROOT / "outputs" / "tables"
CACHE = ROOT / "outputs" / "cache" / "step"
HOURS = T / "france_link_hours.parquet"
SLOPE = T / "france_link_slope.csv"
HALF = 5.0                      # €/MWh either side of the price for the market slope
Z80 = 1.96 + 0.84
FS = T / "france_link_first_stage.csv"
CONTROLS = ["Zb", "Zb_pib", "Zb_rdf", "Zb_gas"]


def calibrate(d: pd.DataFrame, rdf: str = "RDf", p: str = "p_open_full") -> dict:
    """a, b: the price's response to a GW of residual demand at p = 0 and p = 1; ratio a/b with
    its delta-method se. Date and month × hour effects; errors clustered by date."""
    d = d.dropna(subset=["price_es", rdf, p])
    cols = ["price_es", rdf, "inter", p]
    d = d.assign(inter=d[rdf] * d[p])
    codes = [pd.factorize(d.date)[0], pd.factorize(d.month.astype(str) + "|" + d.hour.astype(str))[0]]
    M = wdemean(d[cols].to_numpy(float), codes, np.ones(len(d)))
    y, X = M[:, 0], M[:, 1:]
    A = np.linalg.inv(X.T @ X)
    beta = A @ X.T @ y
    e = y - X @ beta
    V = A @ cluster_meat(X, e, pd.factorize(d.date)[0]) @ A
    a, b = beta[0], beta[0] + beta[1]
    va, vb, cab = V[0, 0], V[0, 0] + V[1, 1] + 2 * V[0, 1], V[0, 0] + V[0, 1]
    g = np.array([1 / b, -a / b ** 2])
    se_ratio = float(np.sqrt(g @ np.array([[va, cab], [cab, vb]]) @ g))
    return {"a": float(a), "b": float(b), "se_a": float(np.sqrt(va)), "se_b": float(np.sqrt(vb)),
            "ratio": float(a / b), "se_ratio": se_ratio, "n": len(d), "days": int(d.date.nunique())}


def market_slope() -> float:
    """Median over valid hours of the effective curve's MW per €/MWh within ±HALF of the price."""
    out = []
    for f in sorted(CACHE.glob("market_2*.parquet")):
        ym = f.stem.split("_")[1]
        h = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "p_star", "valid"])
        h = h[h.valid]
        m = pd.read_parquet(f).merge(h, on="hid").sort_values(["hid", "price"])
        lo = m[m.price <= m.p_star - HALF].groupby("hid").a.last()
        hi = m[m.price <= m.p_star + HALF].groupby("hid").a.last()
        s = ((hi - lo.reindex(hi.index).fillna(0.0)) / (2 * HALF)).dropna()
        out.append(s)
    return float(pd.concat(out).median())


def iv_ctrl(df: pd.DataFrame, xs: list[str], zs: list[str], controls: list[str], codes: list[np.ndarray],
            clusters: dict[str, np.ndarray], y: str | None = None) -> list[dict]:
    """`holiday_first_stage.iv_null` with `controls` partialled out of x, z and y after the fixed
    effects: the first stage of each x on its own z (other zs in), F = t²; given y, se(β) under
    β = 0 from y's residual itself, V = (Z′X)⁻¹ meat(Z, ỹ) (X′Z)⁻¹. y is never fitted on z."""
    main = xs + zs + ([y] if y else [])
    M = wdemean(df[main + controls].to_numpy(float), codes, np.ones(len(df)))
    if controls:
        W = M[:, len(main):]
        M = M[:, :len(main)] - W @ np.linalg.lstsq(W, M[:, :len(main)], rcond=None)[0]
    X, Z = M[:, :len(xs)], M[:, len(xs):len(xs) + len(zs)]
    zz_inv = np.linalg.inv(Z.T @ Z)
    out = []
    for j, x in enumerate(xs):
        b = zz_inv @ Z.T @ X[:, j]
        e = X[:, j] - Z @ b
        row = {"x": x, "z": zs[j], "n": len(df), "pi": float(b[j])}
        for c, cl in clusters.items():
            V = zz_inv @ cluster_meat(Z, e, cl) @ zz_inv
            row[f"se_pi_{c}"] = float(np.sqrt(V[j, j]))
            row[f"F_{c}"] = float((b[j] / np.sqrt(V[j, j])) ** 2)
        if y:
            A_inv = np.linalg.inv(Z.T @ X)
            for c, cl in clusters.items():
                V = A_inv @ cluster_meat(Z, M[:, -1], cl) @ A_inv.T
                row[f"se_beta_{c}"] = float(np.sqrt(V[j, j]))
                row[f"mde_{c}"] = Z80 * row[f"se_beta_{c}"]
            row["y"] = y
        out.append(row)
    return out


def link() -> pd.DataFrame:
    """date, period: open, z_open, p_open_ib, RDf (GW) and the gas price known at the bid."""
    h = pd.read_parquet(HOURS, columns=["date", "period", "state", "z_open", "p_open_ib", "ib_demand_fc",
                                        "ib_wind_fc", "ib_solar_fc"])
    h["date"] = pd.to_datetime(h.date)
    h["open"] = (h.state == "open").astype(float)
    h["RDf"] = (h.ib_demand_fc - h.ib_wind_fc - h.ib_solar_fc) / 1000.0
    g = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet", columns=["date", "mibgas_es_eur_mwh"])
    g["date"] = pd.to_datetime(g.date) + pd.Timedelta(days=2)
    h = h.merge(g.rename(columns={"mibgas_es_eur_mwh": "gas"}), on="date", how="left")
    return h[["date", "period", "open", "z_open", "p_open_ib", "RDf", "gas"]].dropna()


def stake_terms(d: pd.DataFrame, S_values: dict[str, float]) -> pd.DataFrame:
    d = d[d.slope >= sh.FLOOR].copy()
    d["Zb"] = d.n_gw * 1000 / d.slope
    for k, S in S_values.items():
        d[f"Zc_{k}"] = d.n_gw * 1000 / (d.slope + S * d.open)
    d["Z"] = d.Zb * d.z_open
    d["Zb_pib"], d["Zb_rdf"], d["Zb_gas"] = d.Zb * d.p_open_ib, d.Zb * d.RDf, d.Zb * d.gas
    d["week"] = d.date.dt.strftime("%G%V")
    d["ym"] = d.date.dt.strftime("%Y%m")
    return d


def at_cost(prefix: str) -> pd.DataFrame:
    parts = []
    for f in sorted(CACHE.glob(f"{prefix}_2*.parquet")):
        ym = f.stem.split("_")[1]
        c = pd.read_parquet(f, columns=["hid", "group", "unit", "kb_sn", "kb_s"]).drop_duplicates(["hid", "group", "unit"])
        h = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period", "valid"])
        parts.append(c.merge(h, on="hid"))
    c = pd.concat(parts, ignore_index=True)
    c["date"] = pd.to_datetime(c.date)
    c["n_gw"], c["slope"] = c.kb_sn / NEAR / 1000, c.kb_s / NEAR
    return c


def firm_hydro(lk: pd.DataFrame, S: dict) -> pd.DataFrame:
    c = at_cost("hcompcost")
    c = c[c.valid].drop_duplicates(["hid", "group"])
    return stake_terms(c.merge(lk, on=["date", "period"]), S)


def unit_hydro(lk: pd.DataFrame, S: dict) -> pd.DataFrame:
    from fixed_step_test import IN_PLAY, load_rows, stake_parts
    d = load_rows()
    d = d[d.Zb.notna() & (d.rel >= IN_PLAY) & (d.cls != "pumped")]
    d = stake_parts(d).drop(columns=["dose_mw", "D", "P", "Zb"])
    d["date"] = pd.to_datetime(d.date)
    return stake_terms(d.merge(lk, on=["date", "period"]), S)


def unit_thermal(lk: pd.DataFrame, S: dict) -> pd.DataFrame:
    d = pd.read_parquet(T / "outage_offer_panel.parquet", columns=["unit", "group", "cls", "date", "hour", "o25",
                                                                   "c_bid", "wk"])
    d = d[d.cls.isin(["ccgt", "coal"]) & d.c_bid.notna() & d.o25.notna()].copy()
    d["date"] = pd.to_datetime(d.date)
    d["period"] = d.hour + 1
    c = at_cost("compcost")
    d = d.merge(c[["date", "period", "hid", "group", "unit", "n_gw", "slope"]], on=["date", "period", "group", "unit"])
    d["y25"] = d.o25 - d.c_bid
    return stake_terms(d.merge(lk, on=["date", "period"]), S)


def run_first_stage() -> int:
    sl = pd.read_csv(SLOPE).iloc[0]
    S = {"S": sl.S, "S_half": sl.S_half, "S_double": sl.S_double}
    print(f"  S = {sl.S:.0f} MW per €/MWh (checks {sl.S_half:.0f}, {sl.S_double:.0f})")
    lk = link()
    rows = []
    samples = [("firm hydro at cost", firm_hydro, lambda d: [pd.factorize(d.group + d.ym)[0], pd.factorize(d.hid)[0]], None),
               ("unit hydro fixed step", unit_hydro,
                lambda d: [pd.factorize(d.unit + d.ym)[0], pd.factorize(d.cls + d.hid.astype(str))[0]], "g_p_cf"),
               ("unit thermal", unit_thermal,
                lambda d: [pd.factorize(d.unit + d.wk.astype(str))[0],
                           pd.factorize(d.cls + d.date.dt.strftime("%Y%m%d") + d.hour.astype(str))[0]], "y25")]
    for name, build, fe, y in samples:
        d = build(lk, S)
        d = d.dropna(subset=["Z"] + CONTROLS + ([y] if y else []))
        cl = {"date": d.date.dt.strftime("%Y%m%d").to_numpy(), "week": d.week.to_numpy()}
        print(f"  {name}: {len(d):,} rows, {d.date.nunique():,} days; open {d.open.mean():.2f}", flush=True)
        for k in S:
            for r in iv_ctrl(d, [f"Zc_{k}"], ["Z"], CONTROLS, fe(d), cl, y):
                rows.append({"sample": name, "S": k} | r)
                m = f" | mde date {r['mde_date']:.2f} week {r['mde_week']:.2f}" if y else ""
                print(f"    {k:8s} pi {r['pi']:+.4f}  F_date {r['F_date']:.1f}  F_week {r['F_week']:.1f}{m}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(FS, index=False)
    main_ = out[(out.S == "S") & out["sample"].str.startswith("unit")]
    F = main_[["F_date", "F_week"]].min(axis=1)
    mde = main_[["mde_date", "mde_week"]].max(axis=1)
    weak, imprecise = bool((F < 20).all()), bool((mde > 1).all())
    for (_, r), f, m in zip(main_.iterrows(), F, mde):
        print(f"  {r['sample']}: F {f:.1f}, MDE {m:.2f}")
    print(f"  {'STOP' if weak else 'ok  '} F below 20 on both unit-level samples")
    print(f"  {'STOP' if imprecise else 'ok  '} MDE above 1 on both outcomes")
    print(f"stop rule (step 2): {'STOP' if weak or imprecise else 'CONTINUE'}")
    print(f"wrote {FS.relative_to(ROOT)}")
    return 0


def run_calibrate() -> int:
    h = pd.read_parquet(HOURS)
    h["date"] = pd.to_datetime(h.date)
    h["RDf"] = (h.ib_demand_fc - h.ib_wind_fc - h.ib_solar_fc) / 1000.0
    c = calibrate(h)
    print(f"  price per GW of residual demand: full {c['a']:.3f} (se {c['se_a']:.3f}), open {c['b']:.3f} "
          f"(se {c['se_b']:.3f}); ratio {c['ratio']:.2f} (se {c['se_ratio']:.2f}); {c['n']:,} hours, {c['days']:,} days")
    if not (c["b"] > 0 and c["ratio"] > 1):
        print("  STOP: the price does not respond less when the line is predicted open; S is undefined")
        return 1
    s = market_slope()
    S = s * (c["ratio"] - 1)
    out = pd.DataFrame([c | {"market_slope": s, "S": S, "S_half": S / 2, "S_double": 2 * S}])
    out.to_csv(SLOPE, index=False)
    print(f"  median market slope {s:.0f} MW per €/MWh → S = {S:.0f} (checks {S / 2:.0f}, {2 * S:.0f})")
    print(f"wrote {SLOPE.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--calibrate", action="store_true")
    g.add_argument("--first-stage", action="store_true")
    args = ap.parse_args()
    if args.calibrate:
        return run_calibrate()
    return run_first_stage()


if __name__ == "__main__":
    sys.exit(main())
