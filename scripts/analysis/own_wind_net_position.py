#!/usr/bin/env python3
"""Own wind and the firm's NET position: does the retailer buy back what the generators cut?

    .venv/bin/python scripts/analysis/own_wind_net_position.py --legs      # rebuild the legs on current ownership
    .venv/bin/python scripts/analysis/own_wind_net_position.py --verify    # gate G2
    .venv/bin/python scripts/analysis/own_wind_net_position.py --run       # gates G1, G3, then everything

Note `notes/rq-own-wind-quantity.md`, section "Net position and the retail legs (2026-11-05)": the
rules (what is computed, the references, the gates and the reading order) are written there before
this script produced any result, with two dated amendments (also before results). Extends
`own_wind_quantity_test.py --alone` with the SAME panel (`own_wind_quantity_panel.parquet`),
instrument (Wdev), effects (date × hour, firm × month), clusters (date) and controls.

PANELS. "refreshed" (main): the stored panel's rows, with every PDBF leg and the wind / generic /
other-generation split rebuilt (`--legs`, cache outputs/cache/own_wind_net_position_legs.parquet) on the
ownership module as it stands. The stored panel predates the ownership fixes of 2026-10-21 (Movhera's Douro
dams, EDP Energia's sale, Castejon's represented units) and differs from the rebuild for EDP only
(`--verify` quantifies it). "stored": the panel as it is, to compare with the "alone" run.

QUANTITIES (MW, hourly, sold +; every leg PDBF, "auction" = role code other than 4, "bilateral" = 4).
  R_a, R_b, R   purchases of units with registry role purchase_retail, auction / bilateral / both
                (positive = bought; the panel stores them negative). Only some firms' retail arms
                carry that role: Naturgy's and Repsol's sit in other purchases.
  X             other purchases (non-retail-role units that buy, pumping excluded)
  B_a, B_b, B   R + X by leg: every buying unit but pumping. The retail-side outcome of the reading.
  Bnet          B − generic units' resale (bought energy resold), both legs together
  PM            pumping purchases
  N_auc, N_bil, N_tot   net position: all sales minus all purchases (pumping included)
  NX_x = N_x − W_s_x    net position excluding own wind: what the firm does with everything else
  A, A_auc, A_bil       other generation (`G_other*`), as in the "alone" run
Firms are the panel's five, unit to its largest owner that day, regulated pass-through suppliers out.

ESTIMATOR. Each outcome on own scheduled wind W_s instrumented by Wdev. Controls C0: 1/slope and a slope
per firm on each D-1 forecast. C1 = C0 + own retail purchases (the original controls; a bad control for
any outcome that contains a retail leg). Other generation is run under both.

--run      gates G1 and G3, then, for each panel variant (tag in column `panel`):
  own_wind_net_position.csv            pooled, C0 (and A under C1), with the references
  own_wind_net_position_by_firm.csv    W_s × firm instrumented by Wdev × firm, one regression per outcome
  own_wind_net_position_checks.csv     firm × date effects, price above €5, 2022 on, Wdev_fc, week
                                       clusters, C1
  own_wind_net_position_decision.csv   gates and the reading, pooled and by firm
  own_wind_net_position_levels.csv     mean legs by firm (MW), for scale
"""

from __future__ import annotations

import faulthandler
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from own_wind_quantity_test import (FIRMS, KEY, PANEL, T, Z80, _clusters, by_firm,  # noqa: E402
                                    controls_for, prep)

OUT = T / "own_wind_net_position.csv"
OUT_FIRM = T / "own_wind_net_position_by_firm.csv"
OUT_CHECK = T / "own_wind_net_position_checks.csv"
OUT_DEC = T / "own_wind_net_position_decision.csv"
OUT_LEVEL = T / "own_wind_net_position_levels.csv"

LEGS = ROOT / "outputs" / "cache" / "own_wind_net_position_legs.parquet"
LEGCOLS = ["gen_auction", "gen_bilateral", "retail_auction", "retail_bilateral", "other_buy_auction",
           "other_buy_bilateral", "pumping_auction", "pumping_bilateral", "W_s_auction", "W_s_bilateral",
           "generic_auction", "generic_bilateral", "G_other_auction", "G_other_bilateral"]
GEN = ["G_other", "G_other_auction", "G_other_bilateral"]
MAIN_Y = ["B_a", "B_b", "B", "R_a", "R_b", "R", "X", "Bnet", "PM", "NX_auc", "NX_bil", "NX_tot",
          "N_auc", "N_bil", "N_tot"]
CHECK_Y = ["G_other", "G_other_auction", "B_a", "B_b", "B", "R_a", "R_b", "NX_auc", "NX_bil", "NX_tot"]
MATERIAL = 0.10      # rules: "material" share of the cut, about half of x and half of Nash
START, END = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-09-30")


def positions(d: pd.DataFrame) -> pd.DataFrame:
    """Adds the purchase and net-position columns (positive = bought for R, X, B, PM; sold − bought for N)."""
    d["R_a"], d["R_b"] = -d.retail_auction, -d.retail_bilateral
    d["R"] = d.R_a + d.R_b
    d["X_a"], d["X_b"] = -d.other_buy_auction, -d.other_buy_bilateral
    d["X"] = d.X_a + d.X_b
    d["B_a"], d["B_b"] = d.R_a + d.X_a, d.R_b + d.X_b
    d["B"] = d.B_a + d.B_b
    d["Bnet"] = d.B - d.generic_auction - d.generic_bilateral
    d["PM_a"], d["PM_b"] = -d.pumping_auction, -d.pumping_bilateral
    d["PM"] = d.PM_a + d.PM_b
    d["N_auc"] = d.gen_auction - d.B_a - d.PM_a
    d["N_bil"] = d.gen_bilateral - d.B_b - d.PM_b
    d["N_tot"] = d.N_auc + d.N_bil
    d["NX_auc"] = d.N_auc - d.W_s_auction
    d["NX_bil"] = d.N_bil - d.W_s_bilateral
    d["NX_tot"] = d.NX_auc + d.NX_bil
    d["G_other"] = d.G_other_auction + d.G_other_bilateral
    d["W_s"] = d.W_s_auction + d.W_s_bilateral
    d["generic"] = d.generic_auction + d.generic_bilateral
    d["gen"] = d.gen_auction + d.gen_bilateral
    d["retail"] = d.retail_auction + d.retail_bilateral
    return d


def load(variant: str = "refreshed") -> pd.DataFrame:
    """The panel; 'refreshed' swaps in the legs rebuilt on current ownership (`--legs`)."""
    d = pd.read_parquet(PANEL)
    if variant == "refreshed":
        if not LEGS.exists():
            raise SystemExit("run --legs first")
        n = pd.read_parquet(LEGS)[KEY + LEGCOLS]
        stale = LEGCOLS + ["G_other", "W_s", "generic", "gen", "retail"] + [c for c in d.columns if c.startswith("g_")]
        d = d.drop(columns=[c for c in stale if c in d.columns]).merge(n, on=KEY, how="left", validate="1:1")
        d[LEGCOLS] = d[LEGCOLS].fillna(0.0)
    return positions(d)


# --------------------------------------------------------------------------------------- legs
def month_all(f: Path, role: pd.Series, cls: pd.Series, sp: pd.DataFrame) -> pd.DataFrame:
    """One PDBF month, as `holiday_quantity_test.month_legs` (same filters, same leg rule), with the
    generation leg also split into own wind, generic units and the rest (`self_supply_cost` rule)."""
    from unit_ownership import majority_group
    p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"])
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END) & (p.date.dt.dayofweek < 5)]
    if p.empty:
        return p
    per = p.groupby("date").agg(n=("period", "max"), res=("resolution_min", "first"))
    full = per.index[((per.res == 60) & (per.n == 24)) | ((per.res == 15) & (per.n == 96))]
    p = p[p.date.isin(full)].copy()
    p["hour"] = np.where(p.resolution_min == 60, p.period - 1, (p.period - 1) // 4)
    p["mw"] = p.schedule_mw * p.resolution_min / 60
    p["bil"] = p.role_code == "4"
    u = p.groupby(["unit", "date", "hour", "bil"], as_index=False).mw.sum()
    keys = u[["unit", "date"]].drop_duplicates()
    keys["group"] = majority_group(keys, sp, exposed=True).to_numpy()
    u = u.merge(keys, on=["unit", "date"])
    u = u[u.group.isin(FIRMS)]
    r = u.unit.map(role)
    u["leg"] = np.select([r.eq("purchase_retail"), r.eq("pumping"), u.mw > 0], ["retail", "pumping", "gen"], "other_buy")
    u["side"] = np.where(u.bil, "_bilateral", "_auction")
    out = u.groupby(KEY + ["leg", "side"]).mw.sum().unstack(["leg", "side"], fill_value=0.0)
    out.columns = [a + b for a, b in out.columns]
    g = u[u.leg == "gen"].copy()
    c = g.unit.map(cls).fillna("nocost")
    g["k"] = np.where(c == "wind", "W_s", np.where(c == "generic", "generic", "G_other"))
    gk = g.groupby(KEY + ["k", "side"]).mw.sum().unstack(["k", "side"], fill_value=0.0)
    gk.columns = [a + b for a, b in gk.columns]
    out = out.join(gk, how="left").fillna(0.0)
    for c_ in LEGCOLS:
        if c_ not in out:
            out[c_] = 0.0
    return out[LEGCOLS].reset_index()


def build_legs() -> int:
    from holiday_quantity_test import DATA
    from self_supply_cost import unit_classes
    from unit_ownership import spells
    faulthandler.dump_traceback_later(1500, exit=True)
    role = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "role"]).set_index("unit").role
    cls = unit_classes().set_index("unit").cls
    sp = spells()
    parts = []
    for f in sorted((DATA / "omie/pdbf/parquet").glob("pdbf_*.parquet")):
        ym = f.stem.split("_")[1]
        if "201901" <= ym <= "202509":
            parts.append(month_all(f, role, cls, sp))
            print(f"  {ym}", flush=True)
    d = pd.concat(parts, ignore_index=True)
    LEGS.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(LEGS, index=False)
    print(f"wrote {LEGS.relative_to(ROOT)}: {len(d):,} firm-hours")
    faulthandler.cancel_dump_traceback_later()
    return 0


# --------------------------------------------------------------------------------------- gates (G2)
def verify() -> int:
    """G2. (a) identity NX = A + generic − B − PM by leg, on both panels; (b) the refreshed legs for May 2023
    equal `holiday_quantity_test.month_legs` (an independent copy of the leg rule) to 0.01 MW; (c) the
    refreshed wind / generic / other split equals the stored one for the four firms whose ownership did not
    change; (d) excluding pass-through suppliers changes the purchase legs; and, reported, not gated:
    how the stored panel differs from the refreshed one."""
    from holiday_quantity_test import DATA, month_legs
    from unit_ownership import spells
    ok = True
    st, rf = load("stored"), load("refreshed")
    for tag, d in (("stored", st), ("refreshed", rf)):
        for leg, short, g in (("auction", "auc", "B_a"), ("bilateral", "bil", "B_b")):
            pm = "PM_a" if leg == "auction" else "PM_b"
            a = d[f"G_other_{leg}"] + d[f"generic_{leg}"] - d[g] - d[pm]
            gap = float((a - d[f"NX_{short}"]).abs().max())
            print(f"[{tag}] identity NX_{short} = A + generic - B - PM: max gap {gap:.5f} MW")
            ok &= gap < 0.01
        w = float((d.gen - d.W_s - d.generic - d.G_other).abs().max())
        print(f"[{tag}] gen = W_s + generic + G_other: max gap {w:.5f} MW")
        ok &= w < 0.01
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "role"]).set_index("unit").role
    sp = spells()
    f = DATA / "omie/pdbf/parquet/pdbf_202305.parquet"
    m = month_legs(f, reg, sp)
    cols = LEGCOLS[:8]
    for c in cols:
        if c not in m:
            m[c] = 0.0
    mm = rf[(rf.date >= "2023-05-01") & (rf.date <= "2023-05-31")][KEY + cols]
    x = mm.merge(m[KEY + cols], on=KEY, suffixes=("", "_re"))
    ok &= len(x) == len(mm) and len(x) > 0
    print(f"(b) May 2023: {len(x):,} of {len(mm):,} refreshed firm-hours matched to month_legs")
    gaps = {c: float((x[c] - x[c + "_re"]).abs().max()) for c in cols}
    print("    max gap by leg:", {c: round(v, 5) for c, v in gaps.items()})
    ok &= max(gaps.values()) < 0.01
    cl = ["W_s_auction", "W_s_bilateral", "generic_auction", "generic_bilateral", "G_other_auction", "G_other_bilateral"]
    st4 = st[st.group != "EDP"]
    j = st4[KEY + cl].merge(rf[KEY + cl], on=KEY, suffixes=("", "_n"))
    cg = {c: float((j[c] - j[c + "_n"]).abs().max()) for c in cl}
    print("(c) stored vs refreshed class split, four unchanged firms, max gap:", {c: round(v, 4) for c, v in cg.items()})
    ok &= max(cg.values()) < 0.01 and len(j) == len(st4)
    import holiday_quantity_test as hq
    orig = hq.majority_group
    hq.majority_group = lambda df, sp_=None, **kw: orig(df, sp_, exposed=False)
    try:
        m2 = month_legs(f, reg, sp)
    finally:
        hq.majority_group = orig
    pur = ["retail_auction", "retail_bilateral", "other_buy_auction", "other_buy_bilateral"]
    for c in pur:
        if c not in m2:
            m2[c] = 0.0
    y = m[KEY + pur].merge(m2[KEY + pur], on=KEY, suffixes=("", "_all"))
    diff = sum(y[c] - y[c + "_all"] for c in pur)
    live = float(diff.abs().max()) > 0.01
    print(f"(d) purchases with minus without the pass-through exclusion, mean MW by firm: "
          f"{diff.groupby(y.group).mean().round(1).to_dict()}; exclusion live: {live}")
    ok &= live
    j = st[KEY + LEGCOLS[:8]].merge(rf[KEY + LEGCOLS[:8]], on=KEY, suffixes=("", "_n"))
    print("stored minus refreshed (reported, not gated):")
    for c in LEGCOLS[:8]:
        g = j[c] - j[c + "_n"]
        sh = (g.abs() > 0.01).groupby(j.group).mean().round(3).to_dict()
        if any(v > 0 for v in sh.values()):
            print(f"  {c}: share of firm-hours differing {sh}; mean gap MW {g.groupby(j.group).mean().round(1).to_dict()}")
    print(f"G2: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------------------- estimation
def fit_many(d: pd.DataFrame, ys: list[str], endog: list[str], inst: list[str], controls: list[str],
             cluster: str = "date", firm_fe: str = "month") -> dict:
    """2SLS of each y on endog (instruments inst, controls, date × hour and firm × (month|date) effects);
    {y: {endog: (b, se)}}. The effects are swept out once for all outcomes."""
    from iv_two_endog import tsls_k
    k, L = len(endog), len(inst)
    M = prep(d, ys + endog + inst + controls, firm_fe)
    n = len(ys)
    X, Z, W = M[:, n:n + k], M[:, n + k:n + k + L], M[:, n + k + L:]
    cl = _clusters(d, cluster)
    out = {}
    for i, y in enumerate(ys):
        b, V = tsls_k(M[:, i], X, Z, W, cl)
        out[y] = {e: (float(b[j]), float(np.sqrt(V[j, j]))) for j, e in enumerate(endog)}
    return out


def first_stage_f(d: pd.DataFrame, inst: str, controls: list[str], cluster: str = "date") -> tuple[float, float, float]:
    from holiday_quantity_test import ols
    M = prep(d, ["W_s", inst] + controls)
    b, se = ols(M[:, 0], M[:, 1:], _clusters(d, cluster))
    return float(b[0]), float(se[0]), float((b[0] / se[0]) ** 2)


def nash_r(x: pd.DataFrame) -> float:
    return float(np.average(x.s.to_numpy(float) * x.inv_slope.to_numpy(), weights=x.Wdev.abs().to_numpy()))


def references(sb: float, r: float, xcut: float) -> dict[str, dict[str, float]]:
    """Per MW of own wind, the rules table; NaN where the theory does not fix the number. The retail-side
    entries apply to R (registry retail role) and B (every buying unit but pumping) alike."""
    nan = np.nan
    out = {}
    for k, (ra, rb, rt, nxa, nxb, nxt, g) in {
        "price_taking": (0, 0, 0, nan, nan, 0, 0),
        "book_balancing": (0, 0, 0, 0, -sb, -sb, -sb),
        "market_power": (0, 0, 0, -r, 0, -r, -r),
        "label_net_unchanged": (0, -xcut, -xcut, 0, 0, 0, -xcut),
        "buy_back": (xcut, -xcut, 0, -xcut, 0, -xcut, -xcut),
    }.items():
        out[k] = {"B_a": ra, "R_a": ra, "B_b": rb, "R_b": rb, "B": rt, "R": rt, "NX_auc": nxa, "NX_bil": nxb,
                  "NX_tot": nxt, "G_other": g}
    return out


def interval(b: float, se: float) -> tuple[float, float]:
    return b - 1.96 * se, b + 1.96 * se


def reading(res: dict, r: float, power_ok: bool) -> str:
    """The rules' reading order (note, amendment 1: the retail-side outcome is B_a). res: {outcome: (b, se)}
    for NX_auc, B_a, NX_bil, NX_tot, G_other, G_other_auction."""
    if not power_ok:
        return "STOP: cannot tell 0 from the Nash cut on the net auction position (G3)"
    lo, hi = interval(*res["NX_auc"])
    ba_lo, ba_hi = interval(*res["B_a"])
    if hi < 0:
        tail = f" (interval {'holds' if lo <= -r <= hi else 'excludes'} -r = {-r:.2f})"
        if res["B_a"][0] >= MATERIAL and ba_lo > 0:
            return "(iii-b) retailer buys back in the auction; market power in net terms" + tail
        if interval(*res["G_other_auction"])[1] < 0:
            return "(ii) generation withheld in the auction" + tail
        return "net auction position falls, route not identified" + tail
    if lo <= 0 <= hi and -r < lo:
        nb_hi = interval(*res["NX_bil"])[1]
        nt_lo, nt_hi = interval(*res["NX_tot"])
        if ba_lo <= 0 <= ba_hi and abs(res["B_a"][0]) < MATERIAL and nb_hi < 0:
            return "(i) physical book balancing"
        if nt_lo <= 0 <= nt_hi and interval(*res["G_other"])[1] < 0:
            return "(iii-a) label only, net unchanged"
        return "no net auction change, legs unclear"
    if lo > 0:
        return "net auction position rises with own wind (not in the rules' tree)"
    return "inconclusive: interval holds both 0 and -r"


def cell(t: tuple[float, float]) -> str:
    return f"{t[0]:+.3f} ({t[1]:.3f})"


# --------------------------------------------------------------------------------------- run
def analyse(variant: str) -> dict | None:
    """Everything for one panel variant; frames carry a `panel` column."""
    from iv_two_endog import sw_f
    from self_supply_cost import prices
    d = load(variant)
    faulthandler.dump_traceback_later(900, exit=True)
    c1 = controls_for(d)
    c0 = [c for c in c1 if c != "retail"]
    n = len(d)
    print(f"\n===== panel: {variant}: {n:,} firm-hours, {d.date.nunique():,} days, firms {sorted(d.group.unique())}")

    # ---- G1
    b1, se1, F1 = first_stage_f(d, "Wdev", c0)
    print(f"G1 first stage (C0): own wind on Wdev {b1:.3f} ({se1:.3f}), F {F1:,.0f}")
    if F1 < 10:
        print("G1: STOP")
        return {"decision": [{"panel": variant, "item": "G1", "F": F1, "verdict": "STOP: first-stage F < 10"}]}

    # ---- shares and references (C1 for the generation numbers, as in the "alone" run)
    r = nash_r(d)
    ga = fit_many(d, GEN + ["W_s_bilateral"], ["W_s"], ["Wdev"], c1)
    sb = ga["W_s_bilateral"]["W_s"][0]
    xcut = -ga["G_other_bilateral"]["W_s"][0]
    refs = references(sb, r, xcut)
    print(f"s_b (bilateral share of the extra wind) {sb:.3f}; Nash r {r:.3f}; observed bilateral cut x {xcut:.3f}")

    # ---- pooled, C0
    ys = MAIN_Y + GEN
    main = fit_many(d, ys, ["W_s"], ["Wdev"], c0)
    rows = []
    for spec, res_ in (("pooled C0", main), ("pooled C1 (original controls)", ga)):
        for y in (ys if spec == "pooled C0" else GEN):
            b, se = res_[y]["W_s"]
            rows.append({"panel": variant, "spec": spec, "y": y, "b": b, "se": se, "n": n,
                         **{f"ref_{k}": v.get(y, np.nan) for k, v in refs.items()}})
    pooled = pd.DataFrame(rows)
    pooled["t"] = pooled.b / pooled.se
    pooled["lo95"], pooled["hi95"] = pooled.b - 1.96 * pooled.se, pooled.b + 1.96 * pooled.se
    pooled["F_first_stage"] = F1
    pooled["s_b"], pooled["r_nash"], pooled["x_cut"] = sb, r, xcut

    # ---- G3
    se_nx = main["NX_auc"]["W_s"][1]
    power_ok = Z80 * se_nx <= r
    print(f"G3 power: 2.8 × se(NX_auc) = {Z80 * se_nx:.3f} against r = {r:.3f}: {'ok' if power_ok else 'STOP'}")
    a_c0, a_c1 = main["G_other"]["W_s"], ga["G_other"]["W_s"]
    a_shift = (a_c0[0] - a_c1[0]) / a_c1[1]
    print(f"A under C0 {cell(a_c0)}, under C1 {cell(a_c1)}; difference {a_shift:+.2f} se")

    # ---- by firm (one regression per outcome, W_s × firm on Wdev × firm)
    ws, wd = by_firm(d, "W_s"), by_firm(d, "Wdev")
    Mf = prep(d, ws + wd + c0)
    k = len(ws)
    cl = _clusters(d)
    firms = sorted(d.group.unique())
    Ff = {g: sw_f(Mf[:, :k], Mf[:, k:2 * k], Mf[:, 2 * k:], cl, j) for j, g in enumerate(firms)}
    rf = fit_many(d, ys + ["W_s_bilateral"], ws, wd, c0)
    rfa = fit_many(d, GEN, ws, wd, c1)
    frows, fdec = [], []
    for g in firms:
        sbg = rf["W_s_bilateral"][f"W_s_{g}"][0]
        rg = nash_r(d[d.group == g])
        xg = -rfa["G_other_bilateral"][f"W_s_{g}"][0]
        rg_refs = references(sbg, rg, xg)
        res = {}
        for y in ys:
            b, se = rf[y][f"W_s_{g}"]
            res[y] = (b, se)
            frows.append({"panel": variant, "firm": g, "y": y, "b": b, "se": se, "t": b / se, "lo95": b - 1.96 * se,
                          "hi95": b + 1.96 * se, "F": Ff[g], "s_b": sbg, "r_nash": rg, "x_cut": xg,
                          **{f"ref_{kk}": v.get(y, np.nan) for kk, v in rg_refs.items()}})
        pok = Z80 * res["NX_auc"][1] <= rg
        label = reading(res, rg, pok) if Ff[g] >= 10 else "not read: first-stage F < 10"
        fdec.append({"panel": variant, "item": f"firm {g}", "F": Ff[g], "se_NX_auc": res["NX_auc"][1], "r_nash": rg,
                     "power_ok": pok, "verdict": label, "NX_auc": cell(res["NX_auc"]), "B_a": cell(res["B_a"]),
                     "B_b": cell(res["B_b"]), "NX_tot": cell(res["NX_tot"])})
    byfirm = pd.DataFrame(frows)

    # ---- checks on the reading
    p = prices()[["date", "hour", "price_es"]]
    dp = d.merge(p, on=["date", "hour"], how="left")
    checks = [("main (C0)", d, "Wdev", c0, {}),
              ("firm × date effects", d, "Wdev", c0, {"firm_fe": "date"}),
              ("Spanish price above €5", dp[dp.price_es > 5].reset_index(drop=True), "Wdev", c0, {}),
              ("2022 on", d[d.date >= "2022-01-01"].reset_index(drop=True), "Wdev", c0, {}),
              ("Wdev_fc as instrument", d, "Wdev_fc", c0, {}),
              ("week clusters", d, "Wdev", c0, {"cluster": "week"}),
              ("C1 controls (retail as control; bad control for retail outcomes)", d, "Wdev", c1, {})]
    crow, creads = [], {}
    for lab, x, z, ctrl, kw in checks:
        rr = fit_many(x, CHECK_Y, ["W_s"], [z], ctrl, **kw)
        rx = r if x is d else nash_r(x)
        for y in CHECK_Y:
            b, se = rr[y]["W_s"]
            crow.append({"panel": variant, "check": lab, "y": y, "b": b, "se": se, "t": b / se, "lo95": b - 1.96 * se,
                         "hi95": b + 1.96 * se, "n": len(x)})
        creads[lab] = reading({y: rr[y]["W_s"] for y in CHECK_Y}, rx, Z80 * rr["NX_auc"]["W_s"][1] <= rx)
    checks_df = pd.DataFrame(crow)

    # ---- levels
    lc = ["gen_auction", "gen_bilateral", "W_s", "generic", "R_a", "R_b", "X_a", "X_b", "PM", "N_auc", "N_bil", "N_tot",
          "NX_auc", "NX_bil", "NX_tot"]
    lv = d.groupby("group")[lc].mean().round(1)
    lv["hours"] = d.groupby("group").size()
    lv = lv.reset_index().assign(panel=variant)

    # ---- decision
    verdict = reading({y: tuple(main[y]["W_s"]) for y in ys}, r, power_ok)
    stable = sum(creads[k_] == creads["main (C0)"] for k_ in creads if k_ != "main (C0)")
    flags = []
    for y in ("R", "B"):
        if abs(main[y]["W_s"][0] - (-0.06)) > 0.10:
            flags.append(f"{y} total {main[y]['W_s'][0]:+.3f} is more than 0.10 from the -0.06 baseline (load confound?)")
    if abs(main["X"]["W_s"][0]) >= 0.10:
        flags.append(f"other purchases X {main['X']['W_s'][0]:+.3f}, at least 0.10 (traders absorb?)")
    if abs(a_shift) > 1:
        flags.append(f"A differs between C0 and C1 by {a_shift:+.2f} se (retail control carrying the result?)")
    dec = [{"panel": variant, "item": "G1 first-stage F", "F": F1, "verdict": "pass"},
           {"panel": variant, "item": "G3 power", "se_NX_auc": se_nx, "r_nash": r, "power_ok": power_ok,
            "verdict": "pass" if power_ok else "STOP"},
           {"panel": variant, "item": "pooled reading (C0)", "verdict": verdict, "NX_auc": cell(main["NX_auc"]["W_s"]),
            "B_a": cell(main["B_a"]["W_s"]), "B_b": cell(main["B_b"]["W_s"]), "NX_tot": cell(main["NX_tot"]["W_s"])}]
    dec += [{"panel": variant, "item": f"check: {k_}", "verdict": v} for k_, v in creads.items()]
    dec.append({"panel": variant, "item": "stability",
                "verdict": f"{stable} of {len(creads) - 1} checks give the pooled reading"})
    dec += [{"panel": variant, "item": "flag", "verdict": f_} for f_ in flags]
    dec += fdec
    faulthandler.cancel_dump_traceback_later()

    with pd.option_context("display.width", 220, "display.float_format", "{:.3f}".format, "display.max_columns", 30):
        print("\nPOOLED")
        print(pooled[["spec", "y", "b", "se", "t", "lo95", "hi95"]].to_string(index=False))
        print("\nREFERENCES (per MW of own wind)")
        print(pd.DataFrame(refs).to_string())
        print("\nBY FIRM: b, then se")
        print(byfirm.pivot(index="y", columns="firm", values="b").loc[ys].to_string())
        print(byfirm.pivot(index="y", columns="firm", values="se").loc[ys].to_string())
        print("F:", {g: round(v) for g, v in Ff.items()})
        print("\nCHECKS: b, then se")
        print(checks_df.pivot(index="y", columns="check", values="b").loc[CHECK_Y].to_string())
        print(checks_df.pivot(index="y", columns="check", values="se").loc[CHECK_Y].to_string())
        print("\nLEVELS (mean MW)")
        print(lv.to_string(index=False))
    print("\nDECISION")
    for r_ in dec:
        print("  ", {k_: v for k_, v in r_.items() if isinstance(v, str) and k_ != "panel" or k_ == "F"})
    return {"pooled": pooled, "byfirm": byfirm, "checks": checks_df, "decision": dec, "levels": lv}


def run() -> int:
    parts = [analyse(v) for v in ("refreshed", "stored")]
    keys = {"pooled": OUT, "byfirm": OUT_FIRM, "checks": OUT_CHECK, "levels": OUT_LEVEL}
    for k, path in keys.items():
        frames = [p[k] for p in parts if p and k in p]
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(path, index=False)
    pd.DataFrame([r_ for p in parts if p for r_ in p["decision"]]).to_csv(OUT_DEC, index=False)
    print("\nwrote", ", ".join(str(x.relative_to(ROOT)) for x in (OUT, OUT_FIRM, OUT_CHECK, OUT_DEC, OUT_LEVEL)))
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--legs", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.legs:
        return build_legs()
    if a.verify:
        return verify()
    if a.run:
        return run()
    raise SystemExit("--legs, --verify or --run")


if __name__ == "__main__":
    sys.exit(main())
