#!/usr/bin/env python3
"""Intraday offers on the intraday X, with each firm's share of the forecast error as instrument.

    .venv/bin/python scripts/analysis/intraday_firm_panel.py     # input: intraday n, X and offers
    .venv/bin/python scripts/analysis/outage_offer_panel.py      # input: day-ahead offers (placebo)
    .venv/bin/python scripts/analysis/intraday_surprise_test.py                # everything, in turn
    .venv/bin/python scripts/analysis/intraday_surprise_test.py --part thermal # one part (run parts in parallel)
    .venv/bin/python scripts/analysis/intraday_surprise_test.py --collect      # parts -> the results table

Framework spec §9.5 and §9.7 step 5. Day-ahead positions are fixed at noon on D-1
against REE's D-1 forecasts. When the wind then blows harder than forecast, every
farm has more to sell, so a firm holding 20% of Spain's wind finds itself with 20% of
the surplus in the intraday auctions. That moves its intraday position n, and with it
X = n / |RD′| in the intraday auction, for a reason no offer chose.

INSTRUMENT, a shift-share across firms within the hour:

    Z_wind_ft = s_f^wind × (realised − D-1 forecast wind)_t      (GW)
    Z_pv_ft   = s_f^pv   × (realised − D-1 forecast solar)_t

s_f is the firm's share of REE's registered wind or PV capacity (ESIOS archive 81, a
2026-08-12 snapshot; a farm's firm is its agent's, `build_renewable_locations.py`).
Realised output: ESIOS 1159 / 1161 by province, peninsular; forecasts 1777 / 1779
(`da_id_premium.surprises`). Session × date × period effects absorb the national
surprise itself; only its split across firms identifies.

FIRST STAGE (group level): n (GW) and X on the instruments, with group × session ×
hour and session × date × period effects, week clusters; pooled and by session.

THE SHIFT-SHARE FAILS ITS FIRST STAGE (run 2026-10-06): F 3.3, and the wrong sign.
Firms rich in wind also own hydro and gas, and when the wind beats its forecast they
buy back their own output in the intraday auctions more than they sell surplus wind.
Summed over sessions, per GW of national wind surprise: Iberdrola −52 MW (se 9), EDP
−41, Naturgy −11, Endesa +15, Acciona +33. The surprise reaches each firm through its
whole fleet, as the D-1 forecasts did (`notes/rq-forecast-first-stage.md`). So the
second design lets each firm respond in its own way: FIRM-SPECIFIC instruments, the
group's dummy × the wind and the solar surprise for the ten firms with 1 GW or more
(20 instruments; 0 for other groups). Its exclusion: within a class, session and
hour, the surprise reaches a unit's offer only through its owner's X. A unit's own
efficiency × the surprise is controlled in one specification, since a less efficient
plant may react to the surprise whoever owns it.

OFFERS: the offer price at 50% (and 25%) of a leg-D unit's offered sell volume in
session s, on its group's X in s instrumented by Z; unit × week and class × session ×
date × period effects; week clusters; Anderson–Rubin sets. Thermal units (combined
cycle, coal) are the main sample: a forecast error does not change their fuel cost.
All classes, and sessions 1–2 (held on D-1) against 3–6 (on D), as checks.

PLACEBO: day-ahead offers and the day-ahead X (`outage_offer_panel`) on the same Z,
with §9.2's effects. The error arrives after day-ahead offers close, so both must be
zero; a response would mean firms forecast their own farms better than REE.

Clean session-periods only: Spanish and Portuguese session prices equal, clearing
identity within 0.1%, price above 1 €/MWh. 2019-01-01 → 2024-06-13 (MIBEL's sessions).

Each sample keeps the firm-specific instruments of the firms with MIN_ROWS rows or
more in it: a firm without units there has an instrument of zeros.

Writes outputs/tables/intraday_surprise_results.csv (parts in .superpowers/sdd/
2026-10-06-intraday/ while running; the two-way demeaning on millions of rows takes
10–40 minutes a part).
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from da_id_premium import surprises  # noqa: E402
from ivpee_tax_test import vcov  # noqa: E402
from outage_offer_test import demean  # noqa: E402
from outage_rain_offer_test import iv  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT = TABLES / "intraday_surprise_results.csv"
PARTS = ROOT / ".superpowers/sdd/2026-10-06-intraday"
MIN_ROWS = 20_000
START, END = "2019-01-01", "2024-06-13"
ZS = ["Z_wind", "Z_pv"]
# firms with a registered fleet of 1 GW or more of wind or PV (the shift-share's own list)
FIRMS_Z = ["IBERDROLA", "ENDESA", "NATURGY", "EDP", "REPSOL", "ACCIONA", "IGNIS", "NEXUS", "ENGIE", "GALP"]
ZF = [f"{k}_{g}" for g in FIRMS_Z for k in ("Zw", "Zs")]
WIND = ("Eólica terrestre", "Eólica marina")
PV = ("Solar fotovoltaica",)


def shares() -> pd.DataFrame:
    """group, s_wind, s_pv: each firm's share of REE's registered capacity."""
    reg = pd.read_parquet(DATA / "esios/esios_physical_units.parquet", columns=["tech", "agent", "max_power_mw"])
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    reg["firm"] = reg.agent.map(ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0]))
    out = {}
    for name, techs in (("s_wind", WIND), ("s_pv", PV)):
        r = reg[reg.tech.isin(techs)]
        out[name] = r.groupby("firm").max_power_mw.sum() / r.max_power_mw.sum()
        print(f"{name}: {r.max_power_mw.sum() / 1000:.1f} GW registered, "
              f"{r[r.firm.notna()].max_power_mw.sum() / r.max_power_mw.sum():.1%} with a firm")
    return pd.DataFrame(out).fillna(0.0).rename_axis("group").reset_index()


def utc_map() -> pd.DataFrame:
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                        columns=["date", "period", "utc_timestamp", "resolution_min"])
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END) & (p.resolution_min == 60)]
    return p.assign(utc=p.utc_timestamp.dt.floor("h"))[["date", "period", "utc"]]


def add_z(d: pd.DataFrame, sh: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    """Both instrument sets on rows with group and utc: the shift-share (Z_wind, Z_pv)
    and the firm-specific one (group dummy × surprise for FIRMS_Z; 0 for other groups)."""
    d = d[d.utc.isin(s.utc)].merge(s, on="utc").merge(sh, on="group", how="left")
    d[["s_wind", "s_pv"]] = d[["s_wind", "s_pv"]].fillna(0.0)     # no registered farm, no share
    d["Z_wind"] = d.s_wind * d.err_wind
    d["Z_pv"] = d.s_pv * d.err_solar
    for g in FIRMS_Z:
        on = (d.group == g).to_numpy(float)
        d[f"Zw_{g}"] = on * d.err_wind
        d[f"Zs_{g}"] = on * d.err_solar
    return d


def wald_f(b: np.ndarray, V: np.ndarray) -> float:
    return float(b @ np.linalg.solve(V, b) / len(b))


def first_stage(f: pd.DataFrame, zs: list[str], tag: str) -> list[dict]:
    rows = []
    for y in ("n_gw", "X"):
        for label, x in [("all sessions", f)] + [(f"session {s}", f[f.session == s]) for s in range(1, 7)]:
            x = x.dropna(subset=[y])
            codes = [pd.factorize(x.gsh)[0], pd.factorize(x.sdp)[0]]
            M = demean(x[[y] + zs].to_numpy(float), codes)
            b = np.linalg.lstsq(M[:, 1:], M[:, 0], rcond=None)[0]
            V = vcov(M[:, 1:], M[:, 0] - M[:, 1:] @ b, [x.wk.to_numpy()])
            F = wald_f(b, V)
            se = np.sqrt(np.diag(V))
            txt = ", ".join(f"{z} {b[k]:+.3f} ({se[k]:.3f})" for k, z in enumerate(zs)) if len(zs) <= 2 else ""
            print(f"  {tag} {y:4s} {label:13s}: {txt}{'; ' if txt else ''}F {F:.1f}; {len(x):,} rows")
            rows.append({"design": tag, "model": f"first stage {y}", "sample": label, "F": F, "n": len(x),
                         **{f"b_{z}": b[k] for k, z in enumerate(zs)}, **{f"se_{z}": se[k] for k, z in enumerate(zs)}})
    return rows


def firm_responses(f: pd.DataFrame) -> list[dict]:
    """Each firm's intraday position summed over sessions, on the national wind and solar
    surprise, with year-month × hour effects: how the surprise reaches each firm."""
    g = f.groupby(["date", "period", "group", "utc"], as_index=False).agg(
        n_mw=("n_mw", "sum"), err_wind=("err_wind", "first"), err_solar=("err_solar", "first"))
    loc = g.utc.dt.tz_convert("Europe/Madrid")
    g["mh"] = loc.dt.strftime("%Y%m") + "_" + loc.dt.hour.astype(str)
    g["wk"] = loc.dt.strftime("%G%V")
    rows = []
    print("\n== each firm's intraday position (MW, summed over sessions) per GW of national surprise")
    for grp in FIRMS_Z:
        x = g[g.group == grp].reset_index(drop=True)
        M = demean(x[["n_mw", "err_wind", "err_solar"]].to_numpy(float), [pd.factorize(x.mh)[0]])
        b = np.linalg.lstsq(M[:, 1:], M[:, 0], rcond=None)[0]
        se = np.sqrt(np.diag(vcov(M[:, 1:], M[:, 0] - M[:, 1:] @ b, [x.wk.to_numpy()])))
        print(f"  {grp:10s} wind {b[0]:+7.1f} ({se[0]:5.1f})  solar {b[1]:+7.1f} ({se[1]:5.1f})")
        rows.append({"design": "firm response", "model": "position on national surprise", "sample": grp,
                     "b_err_wind": b[0], "se_err_wind": se[0], "b_err_solar": b[1], "se_err_solar": se[1],
                     "n": len(x)})
    return rows


def offers(f: pd.DataFrame, sh: pd.DataFrame, s: pd.DataFrame, um: pd.DataFrame, thermal: bool) -> pd.DataFrame:
    u = pd.read_parquet(TABLES / "intraday_offer_panel.parquet",
                        filters=[("cls", "in", ["ccgt", "coal"])] if thermal else None)
    u["date"] = pd.to_datetime(u.date)
    u = u.merge(f[["session", "date", "period", "group", "X", "wk"]], on=["session", "date", "period", "group"])
    u = add_z(u.merge(um, on=["date", "period"]), sh, s)
    eff = pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet", columns=["unit", "eff", "eff_is_generic"])
    u = u.merge(eff[~eff.eff_is_generic][["unit", "eff"]], on="unit", how="left")
    u["eff_wind"] = u.eff * u.err_wind
    u["eff_pv"] = u.eff * u.err_solar
    u["uw"] = u.unit + "_" + u.wk.astype(str)
    u["csd"] = u.cls + "_" + u.session.astype(str) + "_" + u.date.dt.strftime("%Y%m%d") + "_" + u.period.astype(str)
    return u.dropna(subset=["o25", "o50", "X"]).reset_index(drop=True)


def partial_out(T: np.ndarray, C: np.ndarray) -> np.ndarray:
    Q, _ = np.linalg.qr(C)
    return T - Q @ (Q.T @ T)


def present(u: pd.DataFrame, zs: list[str]) -> list[str]:
    """The firm-specific instruments of firms with MIN_ROWS rows or more in u."""
    n = u.group.value_counts()
    return [z for z in zs if n.get(z.split("_", 1)[1], 0) >= MIN_ROWS]


def run_iv(u: pd.DataFrame, label: str, rows: list[dict], zs: list[str], tag: str, ctrl=()) -> None:
    if tag == "firm-specific":
        zs = present(u, zs)
        print(f"  {label}: instruments for {sorted({z.split('_', 1)[1] for z in zs})}")
    codes = [pd.factorize(u.uw)[0], pd.factorize(u.csd)[0]]
    cols = ["o25", "o50", "X"] + zs
    M = demean(u[cols + list(ctrl)].to_numpy(float), codes)
    if ctrl:
        M = partial_out(M[:, :len(cols)], M[:, len(cols):])
    D = pd.DataFrame(M[:, :len(cols)], columns=cols, index=u.index)
    for y in ("o50", "o25"):
        r = iv(u, D, y, zs, f"{tag}: {label}", "unit x week, class x session x date x period", "wk")
        rows.append(r | {"design": tag, "model": "offers", "controls": "+".join(ctrl)})


def placebo(sh: pd.DataFrame, s: pd.DataFrame, um: pd.DataFrame, rows: list[dict]) -> None:
    d = pd.read_parquet(TABLES / "outage_offer_panel.parquet",
                        columns=["unit", "group", "cls", "date", "hour", "o50", "X", "wk"])
    d = d[(d.date >= START) & (d.date <= END)]
    d = add_z(d.assign(period=d.hour + 1).merge(um, on=["date", "period"]), sh, s)
    d = d.dropna(subset=["o50", "X"]).reset_index(drop=True)
    d["uw"] = d.unit + "_" + d.wk.astype(str)
    d["cdh"] = d.cls + "_" + d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    for label, x in [("day-ahead, thermal", d[d.cls.isin(["ccgt", "coal"])].reset_index(drop=True)),
                     ("day-ahead, all classes", d)]:
        codes = [pd.factorize(x.uw)[0], pd.factorize(x.cdh)[0]]
        for tag, zs in (("shift-share", ZS), ("firm-specific", present(x, ZF))):
            M = demean(x[["o50", "X"] + zs].to_numpy(float), codes)
            for j, y in enumerate(("o50", "X")):
                b = np.linalg.lstsq(M[:, 2:], M[:, j], rcond=None)[0]
                V = vcov(M[:, 2:], M[:, j] - M[:, 2:] @ b, [x.wk.to_numpy()])
                F = wald_f(b, V)
                print(f"  placebo {tag}, {label}, {y} on the instruments: joint F {F:.2f}"
                      + (f" (Z_wind {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f}))" if tag == "shift-share" else "")
                      + f"; {len(x):,} unit-hours")
                rows.append({"design": tag, "model": f"placebo {y}", "sample": label, "F": F, "n": len(x)})
    firm_placebo(sh, s, um, rows)


def firm_placebo(sh: pd.DataFrame, s: pd.DataFrame, um: pd.DataFrame, rows: list[dict]) -> None:
    """The five firms' day-ahead X (firm_x) on the instruments, by day-ahead price band:
    curtailment at low prices makes measured output a market outcome, so if it were the
    reason the placebo fails, the failure would vanish at high prices."""
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "firm", "X", "p_star", "clean"])
    x["date"] = pd.to_datetime(x.date)
    x = x[(x.date >= START) & (x.date <= END) & x.clean].rename(columns={"firm": "group"})
    x = add_z(x.merge(um, on=["date", "period"]), sh, s).dropna(subset=["X"])
    loc = x.utc.dt.tz_convert("Europe/Madrid")
    x["dh"] = x.date.dt.strftime("%Y%m%d") + "_" + x.period.astype(str)
    x["gh"] = x.group + "_" + loc.dt.hour.astype(str)
    x["wk"] = loc.dt.strftime("%G%V")
    for label, m in [("all hours", x.p_star > -1e9), ("day-ahead price > 20", x.p_star > 20),
                     ("day-ahead price > 40", x.p_star > 40)]:
        y = x[m].reset_index(drop=True)
        for tag, zs in (("shift-share", ZS), ("firm-specific", present(y, ZF))):
            M = demean(y[["X"] + zs].to_numpy(float), [pd.factorize(y.dh)[0], pd.factorize(y.gh)[0]])
            b = np.linalg.lstsq(M[:, 1:], M[:, 0], rcond=None)[0]
            F = wald_f(b, vcov(M[:, 1:], M[:, 0] - M[:, 1:] @ b, [y.wk.to_numpy()]))
            print(f"  placebo {tag}, five firms' day-ahead X, {label}: F {F:.2f}; {len(y):,} firm-hours")
            rows.append({"design": tag, "model": "placebo X, five firms", "sample": label, "F": F, "n": len(y)})


def load() -> tuple:
    sh = shares()
    print(sh[(sh.s_wind > 0.01) | (sh.s_pv > 0.01)].sort_values("s_wind", ascending=False).round(3).to_string(index=False))
    um = utc_map()
    s = surprises()[["utc", "err_wind", "err_solar"]].dropna()
    f = pd.read_parquet(TABLES / "intraday_firm_panel.parquet")
    f["date"] = pd.to_datetime(f.date)
    n0 = len(f)
    f = f[~f.split & (f.identity_gap <= 0.001) & (f.p_s > 1.0)]
    f = add_z(f.merge(um, on=["date", "period"]), sh, s)
    f["n_gw"] = f.n_mw / 1000
    loc = f.utc.dt.tz_convert("Europe/Madrid")
    f["wk"] = loc.dt.strftime("%G%V").astype(int)
    f["gsh"] = f.group + "_" + f.session.astype(str) + "_" + loc.dt.hour.astype(str)
    f["sdp"] = f.session.astype(str) + "_" + f.date.dt.strftime("%Y%m%d") + "_" + f.period.astype(str)
    print(f"\nfirm panel: {len(f):,} of {n0:,} group-session-periods clean and with a surprise")
    return sh, um, s, f


def part(name: str) -> list[dict]:
    sh, um, s, f = load()
    rows: list[dict] = []
    if name == "first":
        print("\n== first stage, group level")
        rows += first_stage(f, ZS, "shift-share")
        rows += first_stage(f, ZF, "firm-specific")
        rows += firm_responses(f)
        return rows
    if name == "placebo":
        print("\n== placebo: day-ahead offers and X on the same instruments")
        placebo(sh, s, um, rows)
        return rows
    u = offers(f, sh, s, um, thermal=name != "all")
    del f
    th = u[u.cls.isin(["ccgt", "coal"])].reset_index(drop=True)
    print(f"{len(u):,} unit-session-periods, {u.unit.nunique()} units; thermal {len(th):,}, {th.unit.nunique()} units")
    print("\n== intraday offers on the intraday X")
    if name == "thermal":
        for tag, zs in (("shift-share", ZS), ("firm-specific", ZF)):
            run_iv(th, "thermal, all sessions", rows, zs, tag)
    elif name == "thermal_eff":
        thc = th.dropna(subset=["eff"]).reset_index(drop=True)
        run_iv(thc, "thermal with efficiency, efficiency x surprise controlled", rows, ZF, "firm-specific",
               ("eff_wind", "eff_pv"))
    elif name == "sessions":
        run_iv(th[th.session <= 2].reset_index(drop=True), "thermal, sessions 1-2 (D-1)", rows, ZF, "firm-specific")
        run_iv(th[th.session >= 3].reset_index(drop=True), "thermal, sessions 3-6 (D)", rows, ZF, "firm-specific")
    elif name == "all":
        del th
        run_iv(u, "all classes, all sessions", rows, ZF, "firm-specific")
    return rows


NAMES = ["first", "thermal", "thermal_eff", "sessions", "placebo"]   # "all" (every class) on request: an hour


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--part", choices=NAMES + ["all"])
    ap.add_argument("--collect", action="store_true")
    args = ap.parse_args()
    if args.collect:
        missing = [n for n in NAMES if not (PARTS / f"part_{n}.csv").exists()]
        if missing:
            raise SystemExit(f"parts not yet run: {missing}")
        pd.concat([pd.read_csv(PARTS / f"part_{n}.csv").assign(part=n) for n in NAMES]).to_csv(OUT, index=False)
        print(f"-> {OUT.relative_to(ROOT)}")
        return 0
    PARTS.mkdir(parents=True, exist_ok=True)
    for n in [args.part] if args.part else NAMES:
        pd.DataFrame(part(n)).to_csv(PARTS / f"part_{n}.csv", index=False)
        print(f"-> part {n}")
    if not args.part:
        return main_collect()
    return 0


def main_collect() -> int:
    pd.concat([pd.read_csv(PARTS / f"part_{n}.csv").assign(part=n) for n in NAMES]).to_csv(OUT, index=False)
    print(f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
