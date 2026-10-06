#!/usr/bin/env python3
"""Intraday offers on the intraday X, with each firm's OWN wind surprise as instrument.

    .venv/bin/python scripts/analysis/own_wind_surprise.py               # input: S
    .venv/bin/python scripts/analysis/intraday_own_surprise_test.py      # all parts in turn
    .venv/bin/python scripts/analysis/intraday_own_surprise_test.py --part thermal

The rescue of `intraday_surprise_test.py` (`notes/rq-intraday-surprise.md` §5).
S_gt = the firm's realised wind (its located farms' capacity factor, scaled to its
scheduled fleet) minus its own day-ahead wind schedule (`own_wind_surprise.py`), GW.

CONTROLS. The firm's own response to the national surprise: group × REE's wind error
and group × REE's solar error (the firm-specific instruments of the failed design, ZF),
partialled out after the fixed effects. So S identifies only through the part of the
firm's surprise that is not the national one times a firm-specific response.

THREE CHECKS, as for the failed design:
  first    the firm's intraday position n and X on S (group × session × hour and
           session × date × period effects), by session
  placebo  day-ahead X (five firms, `firm_x`) and day-ahead thermal offers
           (`outage_offer_panel`) on S, same controls: S arrives after the day-ahead
           offers close, so both must be zero
  thermal  intraday offer at 50% (25%) of thermal units on their group's intraday X,
           instrumented by S (pooled: one instrument; and S × group for the firms with
           thermal units), unit × week and class × session × date × period effects,
           Anderson–Rubin sets; sessions 1–2 against 3–6

WITH --schedule: group × the firm's own day-ahead wind schedule is controlled as well.
S = W_hat − sched, so S then varies only through the firm's realised wind given what
it scheduled. Without it, S carries −sched, which is part of the day-ahead position
itself, and the day-ahead placebo fails by construction (run 2026-10-06: day-ahead X
−3.6 per GW of S, F 22; day-ahead thermal offers −€24 per GW, F 45).

WITH --forecasts: group × REE's D-1 forecasts of wind, solar and demand (levels) as well.
A firm's located farms are windy when the forecast is windy, and the forecast, known at
noon on D-1, moves day-ahead offers and positions firm by firm (`rq-forecast-first-stage.md`).

Groups with located wind among `FIRMS_Z`; S is 0 for every other group (no own wind
measured). 2019-01-01 → 2024-06-13. Parts are written to .superpowers/sdd/2026-10-06-step/
own{_schedule}{_forecasts}/; `--collect` gathers every variant's parts into
outputs/tables/intraday_own_surprise_results.csv.

RUN 2026-10-06 (`notes/rq-intraday-surprise.md` §6). First stage strong (n: F 120; X: F 27;
unit level F 24). Thermal offers: β −3.1 (se 7.7), AR set [−19.2, 13.6]: S moves X by only
0.40 €/MWh per GW. The day-ahead placebo fails in all three variants: plain S, with the
schedule held, and with the schedule and the forecast levels held (five firms'
day-ahead X: F 22, 4 and 12; at prices above 40 €/MWh F 26, 16 and 18). Stopped there.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from intraday_surprise_test import (FIRMS_Z, MIN_ROWS, ZF, add_z, load, partial_out,  # noqa: E402
                                    wald_f)
from ivpee_tax_test import vcov  # noqa: E402
from outage_offer_test import demean  # noqa: E402
from outage_rain_offer_test import iv  # noqa: E402

TABLES = ROOT / "outputs/tables"
_TAG = ("_schedule" if "--schedule" in sys.argv else "") + ("_forecasts" if "--forecasts" in sys.argv else "")
OUT = TABLES / f"intraday_own_surprise_results{_TAG}.csv"
PARTS = ROOT / ".superpowers/sdd/2026-10-06-step" / f"own{_TAG}"
START, END = "2019-01-01", "2024-06-13"
NAMES = ["first", "placebo", "thermal", "sessions"]


SCHED = "--schedule" in sys.argv     # hold each firm's own day-ahead wind schedule fixed
FCST = "--forecasts" in sys.argv     # and each firm's response to REE's D-1 forecast levels


def surprise() -> pd.DataFrame:
    s = pd.read_parquet(TABLES / "own_wind_surprise.parquet", columns=["group", "utc", "S_mw", "sched_mw"])
    s["utc"] = pd.to_datetime(s.utc, utc=True)
    s["S"] = s.S_mw / 1000
    s["sched"] = s.sched_mw / 1000
    return s[["group", "utc", "S", "sched"]]


_FC = None


def fcst() -> pd.DataFrame:
    global _FC
    if _FC is None:
        from regional_wind_offer_test import forecasts
        _FC = forecasts()
        _FC["utc"] = pd.to_datetime(_FC.utc, utc=True)
    return _FC


def add_s(d: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["utc"] = pd.to_datetime(d.utc, utc=True)
    d = d.merge(s, on=["group", "utc"], how="left")
    if FCST:
        d = d.merge(fcst(), on="utc", how="left")
    have = set(s.group)
    d.loc[~d.group.isin(have), ["S", "sched"]] = 0.0
    d = d[d.S.notna()].reset_index(drop=True)
    for g in sorted(have):
        on = (d.group == g).to_numpy(float)
        d[f"S_{g}"] = on * d.S.to_numpy()
        d[f"sched_{g}"] = on * d.sched.to_numpy()
        if FCST:
            for k in ("F_wind", "F_solar", "F_demand"):
                d[f"{k}_{g}"] = (on * d[k].to_numpy()).astype("float32")
    if FCST:
        d = d.dropna(subset=["F_wind", "F_solar", "F_demand"]).reset_index(drop=True)
    return d


def ctrl_cols(d: pd.DataFrame) -> list[str]:
    """Group × REE's wind and solar errors; with --schedule also group × the firm's own
    day-ahead wind schedule, so that S varies only through the firm's realised wind."""
    n = d.group.value_counts()
    zs = ZF + ([c for c in d.columns if c.startswith("sched_")] if SCHED else [])
    zs += [c for c in d.columns if c.startswith(("F_wind_", "F_solar_", "F_demand_"))] if FCST else []
    return [z for z in zs if n.get(z.rsplit("_", 1)[1] if z.startswith("F_") else z.split("_", 1)[1], 0) >= MIN_ROWS
            and d[z].abs().sum() > 0]


def firm_s(d: pd.DataFrame) -> list[str]:
    n = d.group.value_counts()
    return [c for c in d.columns if c.startswith("S_") and n.get(c[2:], 0) >= MIN_ROWS and d[c].abs().sum() > 0]


def regress(M: np.ndarray, k: int, cl: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = np.linalg.lstsq(M[:, 1:1 + k], M[:, 0], rcond=None)[0]
    V = vcov(M[:, 1:1 + k], M[:, 0] - M[:, 1:1 + k] @ b, [cl])
    return b, V


def first(f: pd.DataFrame, rows: list[dict]) -> None:
    print("\n== first stage: intraday n (GW) and X on S, controls group × national errors")
    for y in ("n_gw", "X"):
        for label, x in [("all sessions", f)] + [(f"session {s}", f[f.session == s]) for s in range(1, 7)]:
            x = x.dropna(subset=[y]).reset_index(drop=True)
            ctrl = ctrl_cols(x)
            M = demean(x[[y, "S"] + ctrl].to_numpy(float), [pd.factorize(x.gsh)[0], pd.factorize(x.sdp)[0]])
            M = np.column_stack([partial_out(M[:, :2], M[:, 2:]), np.zeros((len(M), 0))]) if ctrl else M
            b, V = regress(M, 1, x.wk.to_numpy())
            F = b[0] ** 2 / V[0, 0]
            print(f"  {y:4s} {label:13s}: S {b[0]:+.4f} ({np.sqrt(V[0, 0]):.4f}), F {F:.1f}; {len(x):,} rows")
            rows.append({"model": f"first stage {y}", "sample": label, "b_S": b[0], "se_S": np.sqrt(V[0, 0]),
                         "F": F, "n": len(x)})
    print("\n  by firm: intraday n summed over sessions (MW) per MW of own surprise, year-month × hour effects")
    g = f.groupby(["date", "period", "group", "utc"], as_index=False).agg(n_mw=("n_mw", "sum"), S=("S", "first"),
                                                                           err_wind=("err_wind", "first"),
                                                                           err_solar=("err_solar", "first"),
                                                                           sched=("sched", "first"))
    xs = ["S", "err_wind", "err_solar"] + (["sched"] if SCHED else [])
    loc = g.utc.dt.tz_convert("Europe/Madrid")
    g["mh"] = loc.dt.strftime("%Y%m") + "_" + loc.dt.hour.astype(str)
    g["wk"] = loc.dt.strftime("%G%V")
    for grp in sorted(set(f.loc[f.S != 0, "group"])):
        x = g[g.group == grp].reset_index(drop=True)
        M = demean(x[["n_mw"] + xs].to_numpy(float), [pd.factorize(x.mh)[0]])
        b, V = regress(M, len(xs), x.wk.to_numpy())
        se = np.sqrt(np.diag(V))
        print(f"    {grp:10s} {b[0] / 1000:+.3f} ({se[0] / 1000:.3f}) MW per MW; national wind error "
              f"{b[1]:+.1f} ({se[1]:.1f}) MW per GW; {len(x):,} hours")
        rows.append({"model": "firm response to own surprise", "sample": grp, "b_S": b[0] / 1000,
                     "se_S": se[0] / 1000, "b_err_wind": b[1], "se_err_wind": se[1], "n": len(x)})


def placebo(s: pd.DataFrame, um: pd.DataFrame, rows: list[dict]) -> None:
    from da_id_premium import surprises
    from intraday_surprise_test import shares
    sh, e = shares(), surprises()[["utc", "err_wind", "err_solar"]].dropna()
    print("\n== placebo: day-ahead X and offers on S (controls group × national errors)")
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "firm", "X", "p_star", "clean"])
    x["date"] = pd.to_datetime(x.date)
    x = x[(x.date >= START) & (x.date <= END) & x.clean].rename(columns={"firm": "group"})
    x = add_s(add_z(x.merge(um, on=["date", "period"]), sh, e).dropna(subset=["X"]), s)
    loc = x.utc.dt.tz_convert("Europe/Madrid")
    x["dh"] = x.date.dt.strftime("%Y%m%d") + "_" + x.period.astype(str)
    x["gh"] = x.group + "_" + loc.dt.hour.astype(str)
    x["wk"] = loc.dt.strftime("%G%V")
    for label, m in [("all hours", x.p_star > -1e9), ("day-ahead price > 40", x.p_star > 40)]:
        y = x[m].reset_index(drop=True)
        ctrl = ctrl_cols(y)
        for tag, zs in (("pooled S", ["S"]), ("S by firm", firm_s(y))):
            M = demean(y[["X"] + zs + ctrl].to_numpy(float), [pd.factorize(y.dh)[0], pd.factorize(y.gh)[0]])
            M = partial_out(M[:, :1 + len(zs)], M[:, 1 + len(zs):]) if ctrl else M
            b, V = regress(M, len(zs), y.wk.to_numpy())
            F = wald_f(b, V)
            print(f"  five firms' day-ahead X, {label}, {tag}: F {F:.2f}"
                  + (f" (S {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f}))" if tag == "pooled S" else "") + f"; {len(y):,}")
            rows.append({"model": "placebo X, five firms", "sample": f"{label}, {tag}", "F": F, "n": len(y),
                         "b_S": b[0] if tag == "pooled S" else np.nan})
    d = pd.read_parquet(TABLES / "outage_offer_panel.parquet", columns=["unit", "group", "cls", "date", "hour", "o50", "X", "wk"])
    d = d[(d.date >= START) & (d.date <= END) & d.cls.isin(["ccgt", "coal"])]
    d = add_s(add_z(d.assign(period=d.hour + 1).merge(um, on=["date", "period"]), sh, e), s)
    d = d.dropna(subset=["o50", "X"]).reset_index(drop=True)
    d["uw"] = d.unit + "_" + d.wk.astype(str)
    d["cdh"] = d.cls + "_" + d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    ctrl = ctrl_cols(d)
    for tag, zs in (("pooled S", ["S"]), ("S by firm", firm_s(d))):
        M = demean(d[["o50", "X"] + zs + ctrl].to_numpy(float), [pd.factorize(d.uw)[0], pd.factorize(d.cdh)[0]])
        M = partial_out(M[:, :2 + len(zs)], M[:, 2 + len(zs):]) if ctrl else M
        for j, yv in enumerate(("o50", "X")):
            Mj = np.column_stack([M[:, j], M[:, 2:]])
            b, V = regress(Mj, len(zs), d.wk.to_numpy())
            F = wald_f(b, V)
            print(f"  day-ahead thermal {yv}, {tag}: F {F:.2f}"
                  + (f" (S {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f}))" if tag == "pooled S" else "") + f"; {len(d):,}")
            rows.append({"model": f"placebo {yv}, day-ahead thermal", "sample": tag, "F": F, "n": len(d),
                         "b_S": b[0] if tag == "pooled S" else np.nan})


def offers(f: pd.DataFrame, um: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    u = pd.read_parquet(TABLES / "intraday_offer_panel.parquet", filters=[("cls", "in", ["ccgt", "coal"])])
    u["date"] = pd.to_datetime(u.date)
    keep = ["session", "date", "period", "group", "X", "wk", "utc", "err_wind", "err_solar"] + ZF
    u = u.merge(f[keep], on=["session", "date", "period", "group"])
    u = add_s(u, s)
    u["uw"] = u.unit + "_" + u.wk.astype(str)
    u["csd"] = u.cls + "_" + u.session.astype(str) + "_" + u.date.dt.strftime("%Y%m%d") + "_" + u.period.astype(str)
    return u.dropna(subset=["o25", "o50", "X"]).reset_index(drop=True)


def run_iv(u: pd.DataFrame, label: str, rows: list[dict]) -> None:
    ctrl = ctrl_cols(u)
    for tag, zs in (("pooled S", ["S"]), ("S by firm", firm_s(u))):
        cols = ["o25", "o50", "X"] + zs
        M = demean(u[cols + ctrl].to_numpy(float), [pd.factorize(u.uw)[0], pd.factorize(u.csd)[0]])
        M = partial_out(M[:, :len(cols)], M[:, len(cols):]) if ctrl else M
        D = pd.DataFrame(M[:, :len(cols)], columns=cols, index=u.index)
        print(f"  {tag}: instruments {zs}")
        for y in ("o50", "o25"):
            r = iv(u, D, y, zs, f"{tag}: {label}", "unit x week, class x session x date x period", "wk")
            rows.append(r | {"model": "offers", "design": tag})


def part(name: str) -> list[dict]:
    sh, um, e, f = load()
    s = surprise()
    rows: list[dict] = []
    if name == "placebo":
        del f
        placebo(s, um, rows)
        return rows
    f = add_s(f, s)
    print(f"own surprise: sd by group (GW): {f[f.S != 0].groupby('group').S.std().round(3).to_dict()}")
    if name == "first":
        first(f, rows)
        return rows
    u = offers(f, um, s)
    del f
    print(f"{len(u):,} thermal unit-session-periods, {u.unit.nunique()} units")
    if name == "thermal":
        run_iv(u, "thermal, all sessions", rows)
    elif name == "sessions":
        run_iv(u[u.session <= 2].reset_index(drop=True), "thermal, sessions 1-2 (D-1)", rows)
        run_iv(u[u.session >= 3].reset_index(drop=True), "thermal, sessions 3-6 (D)", rows)
    return rows


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--part", choices=NAMES)
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--schedule", action="store_true", help="control group × own day-ahead wind schedule")
    ap.add_argument("--forecasts", action="store_true", help="control group × REE's D-1 forecasts (levels)")
    args = ap.parse_args()
    PARTS.mkdir(parents=True, exist_ok=True)
    if not args.collect:
        for n in [args.part] if args.part else NAMES:
            pd.DataFrame(part(n)).to_csv(PARTS / f"part_{n}.csv", index=False)
            print(f"-> part {n}")
        if args.part:
            return 0
    base = ROOT / ".superpowers/sdd/2026-10-06-step"
    labels = {"own": "S", "own_schedule": "S | own schedule",
              "own_schedule_forecasts": "S | own schedule, forecast levels"}
    parts = [pd.read_csv(f).assign(variant=lab, part=f.stem[5:])
             for v, lab in labels.items() for f in sorted((base / v).glob("part_*.csv"))]
    out = TABLES / "intraday_own_surprise_results.csv"
    pd.concat(parts, ignore_index=True).to_csv(out, index=False)
    print(f"-> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
