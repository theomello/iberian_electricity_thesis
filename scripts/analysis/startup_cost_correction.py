#!/usr/bin/env python3
"""How much of the static gap `price - cost` of Iberian thermal plant is its own declared start-up cost?

    .venv/bin/python scripts/analysis/startup_cost_correction.py              # build the panel, then tables
    .venv/bin/python scripts/analysis/startup_cost_correction.py --from-panel # tables only, from the saved panel
    .venv/bin/python scripts/analysis/startup_cost_correction.py --sco        # after 2025-03-19 (note §5)

Rules are written in notes/rq-startup-cost-correction.md §1 before the first run.

Jha & Leslie (SSRN 3603627): a positive static gap P - MC can be start-up cost recovery under
perfect competition. `cab` publishes the plant's own statement of what it needs, the
minimum-income condition: a fixed term F (EUR/day) and a variable term V (EUR/MWh), 2018-01-01 →
2025-03-18 (the wide layout; the later SCO lump sum is not comparable and is left out).

Per unit-day with cleared sell volume Q > 0 (84 units with a plant-specific efficiency):
    M = sum_h (p_h - c) q_h      static gap, c the bid-time cost (known at noon on D-1)
    F share of the gap           sum F / sum M over declaring days with M > 0   (a LOWER bound on start-up)
    M = W + F + E on clean-V days with W = (V - c) Q declared variable cost beyond fuel and
    E = sum_h (p_h - V) q_h - F  margin above everything declared. (F + W) / M is an UPPER bound.
The minimum-income rule makes E >= 0 on every accepted declaring day: that is the join gate.

F and V are strategic choices (Reguant 2014), so every number is a bound, and the declaring
plants are selected. Writes outputs/tables/startup_cost_correction*.csv and the unit-day panel.
"""
from __future__ import annotations

import faulthandler
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

faulthandler.dump_traceback_later(2400, exit=True)

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs/tables"
PANEL = OUT / "startup_cost_correction_unitdays.parquet"
START, END = pd.Timestamp("2018-01-01"), pd.Timestamp("2025-03-18")
DROP_DAYS = [pd.Timestamp("2018-06-14"), pd.Timestamp("2022-10-12")]   # whole-day clearing-identity dropouts
CAP = (pd.Timestamp("2022-06-15"), pd.Timestamp("2023-02-25"))        # days with a positive gas-cap subsidy
NEVER = 999.0
RATIO = (0.5, 3.0)
TOL = 100.0          # EUR/day tolerance on the minimum-income identity
SHORT = 3          # post-hoc (note §3.1): a unit-day with at most this many cleared periods is a ramp tail or head
MIN_DAYS = 500       # declaring unit-days needed to read a year x group cell
MONTHS = pd.period_range("2018-01", "2025-03", freq="M")


def units() -> pd.DataFrame:
    m = pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet")
    u = m[~m.eff_is_generic & m.cab_tech.isin(["combined_cycle", "thermal"])][["unit", "country", "cab_tech"]]
    f = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet", columns=["unit", "fuel"]).drop_duplicates()
    u = u.merge(f, on="unit")
    if u.unit.duplicated().any():
        raise SystemExit("a unit appears twice")
    u["group"] = np.where(u.fuel == "coal", "coal", np.where(u.country == "ES", "ES gas", "PT gas"))
    return u[["unit", "country", "fuel", "group"]]


def cleared(u: pd.DataFrame) -> pd.DataFrame:
    """Unit-day cleared energy Q (MWh) and revenue R (EUR) at the unit's own country's price."""
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                        columns=["date", "period", "price_es", "price_pt"])
    p["date"] = pd.to_datetime(p.date)
    country = u.set_index("unit").country
    out = []
    for per in MONTHS:
        f = DATA / f"omie/bids/parquet/bids_{per.strftime('%Y%m')}.parquet"
        b = pd.read_parquet(f, columns=["date", "period", "unit", "power_mw", "resolution_min"],
                            filters=[("unit", "in", u.unit.tolist()), ("status", "=", "C"), ("side", "=", "V")])
        if b.empty:
            continue
        b["date"] = pd.to_datetime(b.date)
        b = b.groupby(["date", "period", "unit", "resolution_min"], as_index=False).power_mw.sum()
        b = b.merge(p, on=["date", "period"], how="left")
        if b.price_es.isna().any():
            raise SystemExit(f"{per}: periods without a price")
        b["price"] = np.where(b.unit.map(country) == "ES", b.price_es, b.price_pt)
        b["mwh"] = b.power_mw * b.resolution_min / 60
        b["rev"] = b.mwh * b.price
        b = b[b.mwh > 1e-6]
        out.append(b.groupby(["unit", "date"], as_index=False).agg(
            mwh=("mwh", "sum"), rev=("rev", "sum"), n_periods=("period", "nunique"),
            first_period=("period", "min"), last_period=("period", "max")))
        print(per, len(out[-1]), flush=True)
    d = pd.concat(out, ignore_index=True).rename(columns={"mwh": "Q", "rev": "R"})
    return d[d.Q > 1e-6]


def declared(units_list: list[str] | None) -> pd.DataFrame:
    keep = ["date", "unit", "side", "ofer_plazo", "min_income_fixed_eur", "min_income_var_eur_mwh"]
    parts = []
    for per in MONTHS:
        f = DATA / f"omie/cab/parquet/cab_{per.strftime('%Y%m')}.parquet"
        kw = {"filters": [("unit", "in", units_list)]} if units_list else {}
        parts.append(pd.read_parquet(f, columns=keep, **kw))
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    d = d[(d.side == "V") & (d.date >= START) & (d.date <= END)].drop(columns="side")
    # A long-term ("P") header sits beside the daily ("O") one for a few portfolio units (EDPSVD1, 91
    # unit-days in four sampled months); none of the 84 plants has one. Keep the daily header.
    d = d.sort_values("ofer_plazo", key=lambda x: x.ne("O")).drop_duplicates(["unit", "date"]).drop(columns="ofer_plazo")
    return d.rename(columns={"min_income_fixed_eur": "F", "min_income_var_eur_mwh": "V"})


def build_panel() -> pd.DataFrame:
    u = units()
    q = cleared(u)
    h = declared(u.unit.tolist())
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "marginal_cost_bid_eur_mwh", "marginal_cost_subsidised_bid_eur_mwh"],
                        filters=[("unit", "in", u.unit.tolist())])
    c["date"] = pd.to_datetime(c.date)
    c = c.rename(columns={"marginal_cost_bid_eur_mwh": "c_bid", "marginal_cost_subsidised_bid_eur_mwh": "c_sub"})
    d = q.merge(u, on="unit").merge(h, on=["unit", "date"], how="left").merge(c, on=["unit", "date"], how="left")
    d["c_sub"] = d.c_sub.fillna(d.c_bid)
    d.to_parquet(PANEL)
    return d


def prepare(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n = {"unit_days_cleared": len(d)}
    d = d[~d.date.isin(DROP_DAYS)]
    n["after_dropout_days"] = len(d)
    miss = d.c_bid.isna()
    n["no_bid_cost"] = int(miss.sum())
    d = d[~miss].copy()
    n["no_cab_header"] = int(d.F.isna().sum())
    d["year"] = d.date.dt.year
    d["short"] = d.n_periods <= SHORT
    d["in_cap"] = (d.date >= CAP[0]) & (d.date <= CAP[1])
    d["v_valid"] = (d.V > 0) & (d.V < NEVER)
    d["declares"] = np.where(d.F.isna(), np.nan, ((d.F > 0) | d.v_valid).astype(float))
    d["v_never"] = d.V >= NEVER
    d["clean_v"] = d.v_valid & (d.V / d.c_bid).between(*RATIO)
    for tag, col in [("", "c_bid"), ("_sub", "c_sub")]:
        d["M" + tag] = d.R - d[col] * d.Q
    d["W"] = np.where(d.clean_v, (d.V - d.c_bid) * d.Q, np.nan)
    d["E"] = np.where(d.F.notna() & ((d.F > 0) | d.v_valid), d.R - np.where(d.v_valid, d.V, 0.0) * d.Q - d.F, np.nan)
    return d, n


def ratio_rows(d: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = d.groupby(by)
    r = g.agg(n_days=("Q", "size"), Q_gwh=("Q", lambda s: s.sum() / 1e3), sumQ=("Q", "sum"),
              sumR=("R", "sum"), sumM=("M", "sum"), sumF=("F", "sum"))
    r["gap_eur_mwh"] = r.sumM / r.sumQ
    r["lerner_share"] = r.sumM / r.sumR
    r["F_eur_mwh"] = r.sumF / r.sumQ
    r["gap_net_of_F_eur_mwh"] = (r.sumM - r.sumF) / r.sumQ
    return r.drop(columns=["sumQ", "sumR", "sumM", "sumF"]).reset_index()


def with_all(d: pd.DataFrame) -> pd.DataFrame:
    """Each group plus pooled rows: 'gas' (ES + PT combined cycles) and 'all' (gas and coal)."""
    a = d.copy()
    a["group"] = "all"
    g = d[d.group.isin(["ES gas", "PT gas"])].copy()
    g["group"] = "gas"
    return pd.concat([d, g, a], ignore_index=True)


def headline(d: pd.DataFrame, cost: str = "M") -> pd.DataFrame:
    """Declaring days: F share of the static gap. Ratio of sums."""
    s = with_all(d[d.declares == 1].copy())
    s["Mx"] = s[cost]
    rows = []
    for (y, g), x in s.groupby(["year", "group"]):
        pos = x[x.Mx > 0]
        rows.append(dict(year=y, group=g, n_declaring_days=len(x), n_pos_gap_days=len(pos),
                         share_F_positive=(x.F > 0).mean(),
                         gap_eur_mwh_all=x.Mx.sum() / x.Q.sum(), F_eur_mwh_all=x.F.sum() / x.Q.sum(),
                         sumF_over_sumM_all=x.F.sum() / x.Mx.sum() if x.Mx.sum() > 0 else np.nan,
                         sumF_over_sumM_posgap=pos.F.sum() / pos.Mx.sum() if len(pos) else np.nan,
                         gap_posgap=pos.Mx.sum() / pos.Q.sum() if len(pos) else np.nan,
                         gap_net_of_F_posgap=(pos.Mx.sum() - pos.F.sum()) / pos.Q.sum() if len(pos) else np.nan,
                         median_F_over_M_posgap=(pos.F / pos.Mx).median() if len(pos) else np.nan,
                         share_gap_le0=(x.Mx <= 0).mean(), share_F_gt_gap=(x.F > x.Mx).mean(),
                         readable=len(x) >= MIN_DAYS))
    h = pd.DataFrame(rows)
    band = pd.cut(h.sumF_over_sumM_posgap, [-np.inf, 0.05, 0.25, np.inf], labels=["<5%", "5-25%", ">25%"])
    h["band"] = band.astype(object).where(h.readable, "not read")
    return h


def decomposition(d: pd.DataFrame) -> pd.DataFrame:
    s = with_all(d[(d.declares == 1) & d.clean_v].copy())
    rows = []
    for (y, g), x in s.groupby(["year", "group"]):
        Q, M = x.Q.sum(), x.M.sum()
        rows.append(dict(year=y, group=g, n_days=len(x), Q_gwh=Q / 1e3, gap_eur_mwh=M / Q,
                         W_eur_mwh=x.W.sum() / Q, F_eur_mwh=x.F.sum() / Q, E_eur_mwh=(M - x.W.sum() - x.F.sum()) / Q,
                         F_share_of_gap=x.F.sum() / M if M > 0 else np.nan,
                         W_share_of_gap=x.W.sum() / M if M > 0 else np.nan,
                         F_plus_W_share_of_gap=(x.F.sum() + x.W.sum()) / M if M > 0 else np.nan,
                         median_V_over_c=(x.V / x.c_bid).median(), readable=len(x) >= MIN_DAYS))
    return pd.DataFrame(rows)


def identity(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, m in [("clean-V declaring days (the gate)", d.declares.eq(1) & d.clean_v),
                    ("all declaring days with V < 999", d.declares.eq(1) & ~d.v_never)]:
        s = with_all(d[m])
        for (y, g), x in s.groupby(["year", "group"]):
            bad = x[x.E < -TOL]
            rows.append(dict(sample=name, year=y, group=g, n_days=len(x), share_E_ok=1 - len(bad) / len(x),
                             median_E_eur=x.E.median(), median_shortfall_of_failures_eur=bad.E.median() if len(bad) else 0.0))
    return pd.DataFrame(rows)


def selection(d: pd.DataFrame, cab_all: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = with_all(d[d.declares.notna()].copy())
    rows = []
    for (y, g), x in s.groupby(["year", "group"]):
        dec, non = x[x.declares == 1], x[x.declares == 0]
        rows.append(dict(year=y, group=g, n_days=len(x), declare_share_days=len(dec) / len(x),
                         declare_share_volume=dec.Q.sum() / x.Q.sum(),
                         gap_eur_mwh_declaring=dec.M.sum() / dec.Q.sum() if len(dec) else np.nan,
                         gap_eur_mwh_nondeclaring=non.M.sum() / non.Q.sum() if len(non) else np.nan,
                         n_nondeclaring_days=len(non)))
    sel = pd.DataFrame(rows)
    dec_all = cab_all[(cab_all.F > 0) | ((cab_all.V > 0) & (cab_all.V < NEVER))]
    dec_all = dec_all.assign(year=dec_all.date.dt.year, ours=dec_all.unit.isin(d.unit.unique()))
    fleet = dec_all.groupby("year").agg(declaring_unit_days_all=("unit", "size"), declaring_units_all=("unit", "nunique"),
                                        declaring_unit_days_ours=("ours", "sum"))
    fleet["our_share_of_declaring_unit_days"] = fleet.declaring_unit_days_ours / fleet.declaring_unit_days_all
    fleet["declaring_units_per_day_all"] = dec_all.groupby("year").apply(
        lambda x: x.groupby("date").size().mean(), include_groups=False)
    return sel, fleet.reset_index()


def variants(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, m, cost in [("V1 main: bid cost, cap window excluded", ~d.in_cap, "M"),
                          ("V2 bid cost, all days", pd.Series(True, index=d.index), "M"),
                          ("V3 subsidised bid cost, all days", pd.Series(True, index=d.index), "M_sub")]:
        h = headline(d[m], cost)
        h.insert(0, "variant", name)
        rows.append(h)
    v = pd.concat(rows, ignore_index=True)
    return v[["variant", "year", "group", "n_declaring_days", "readable", "gap_eur_mwh_all", "F_eur_mwh_all",
              "sumF_over_sumM_all", "sumF_over_sumM_posgap", "gap_net_of_F_posgap", "share_gap_le0", "band"]]


def by_unit(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for u, x in d.groupby("unit"):
        dec = x[x.declares == 1]
        pos = dec[dec.M > 0]
        rows.append(dict(unit=u, group=x.group.iloc[0], n_days=len(x), Q_gwh=x.Q.sum() / 1e3,
                         declare_share=(x.declares == 1).mean(), gap_eur_mwh=x.M.sum() / x.Q.sum(),
                         F_eur_mwh=dec.F.sum() / dec.Q.sum() if len(dec) else np.nan,
                         sumF_over_sumM_posgap=pos.F.sum() / pos.M.sum() if len(pos) else np.nan,
                         share_F_positive=(dec.F > 0).mean() if len(dec) else np.nan))
    return pd.DataFrame(rows).sort_values("Q_gwh", ascending=False)


def vre_share() -> pd.Series:
    g = pd.read_parquet(DATA / "ree/ree_generation_daily.parquet", columns=["local_date", "series", "value"])
    g["date"] = pd.to_datetime(g.local_date)
    w = g.pivot_table(index="date", columns="series", values="value", aggfunc="sum")
    comp = w.drop(columns=["Total generation"])
    return ((w["Wind"] + w["Solar photovoltaic"]) / comp.sum(axis=1)).rename("vre")


def cluster_slope(x: np.ndarray, y: np.ndarray, cl: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    b = (w * x * y).sum() / (w * x * x).sum()
    e = y - b * x
    g = pd.factorize(cl)[0]
    s = np.bincount(g, weights=w * x * e)
    return b, np.sqrt((s ** 2).sum()) / (w * x * x).sum()


def vre_tables(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    v = vre_share()
    s = d[(d.declares == 1) & ~d.in_cap].merge(v, left_on="date", right_index=True, how="left")
    s = s[s.vre.notna()].copy()
    s["tercile"] = s.groupby("year").vre.transform(lambda x: pd.qcut(x, 3, labels=["low", "mid", "high"])
                                                    if x.nunique() > 3 else np.nan)
    rows = []
    for (y, t), x in s[s.fuel == "gas"].groupby(["year", "tercile"], observed=True):   # gas only: coal's share of the sample falls over the years
        pos = x[x.M > 0]
        rows.append(dict(year=y, tercile=t, n_days=len(x), vre_mean=x.vre.mean(),
                         gap_eur_mwh=x.M.sum() / x.Q.sum(), F_eur_mwh=x.F.sum() / x.Q.sum(),
                         sumF_over_sumM_posgap=pos.F.sum() / pos.M.sum() if len(pos) else np.nan))
    terc = pd.DataFrame(rows)
    s["ym"] = s.date.dt.to_period("M").astype(str)
    s["uy"] = s.unit + s.year.astype(str)
    slopes = []
    for g in ["all", "gas", "ES gas", "PT gas", "coal"]:
        x = s if g == "all" else s[s.fuel == "gas"] if g == "gas" else s[s.group == g]
        x = x[x.Q > 0]
        for ynm, y in [("F_per_MWh", x.F / x.Q), ("gap_per_MWh", x.M / x.Q)]:
            for wnm in ["unweighted", "volume-weighted"]:
                y = y.replace([np.inf, -np.inf], np.nan)
                ok = y.notna()
                xx, yy, uy, ym = x.vre[ok], y[ok], x.uy[ok], x.ym[ok]
                w = np.ones(ok.sum()) if wnm == "unweighted" else x.Q[ok].to_numpy()
                xd = (xx - xx.groupby(uy).transform("mean")).to_numpy()
                yd = (yy - yy.groupby(uy).transform("mean")).to_numpy()
                b, se = cluster_slope(xd, yd, ym.to_numpy(), w)
                slopes.append(dict(group=g, outcome=ynm, weights=wnm, slope_per_unit_vre_share=b, se=se, t=b / se,
                                   n=int(ok.sum()), n_month_clusters=ym.nunique(), per_10pp_vre=b * 0.1))
    return terc, pd.DataFrame(slopes)


def tables(d: pd.DataFrame, cab_all: pd.DataFrame) -> dict:
    out = {}
    main_d = d[~d.in_cap]
    out["headline"] = headline(main_d)
    out["decomposition"] = decomposition(main_d)
    out["identity"] = identity(main_d)
    sel, fleet = selection(main_d, cab_all)
    out["selection"], out["fleet_declaring"] = sel, fleet
    out["variants"] = variants(d)
    out["units"] = by_unit(main_d)
    parts = []
    for lab, m in [("all cleared", main_d.declares.notna()), ("declaring", main_d.declares.eq(1)),
                   ("non-declaring", main_d.declares.eq(0))]:
        r = ratio_rows(with_all(main_d[m]), ["year", "group"])
        r.insert(0, "set", lab)
        parts.append(r)
    out["summary"] = pd.concat(parts, ignore_index=True)
    out["vre_terciles"], out["vre_slopes"] = vre_tables(main_d)
    return out


def short_diagnosis(d: pd.DataFrame) -> pd.DataFrame:
    """Does the identity fail only on short runs? Declaring clean-V days by number of cleared periods."""
    x = d[~d.in_cap & d.declares.eq(1) & d.clean_v].copy()
    x["periods"] = pd.cut(x.n_periods, [0, 1, 2, 3, 4, 6, 12, 25], labels=["1", "2", "3", "4", "5-6", "7-12", "13+"])
    x["starts_at_1"] = x.first_period == 1
    r = x.groupby(["periods", "starts_at_1"], observed=True).apply(
        lambda y: pd.Series(dict(n_days=len(y), share_E_ok=(y.E >= -TOL).mean(), sumF=y.F.sum(), Q_gwh=y.Q.sum() / 1e3)),
        include_groups=False).reset_index()
    return r[r.n_days > 0]


def show(out: dict) -> None:
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
    print("IDENTITY (join gate), pooled groups")
    print(out["identity"][out["identity"].group.isin(["gas", "coal"])].round(3).to_string(index=False))
    print("\nHEADLINE (declaring days)")
    print(out["headline"][["year", "group", "n_declaring_days", "share_F_positive", "gap_eur_mwh_all", "F_eur_mwh_all",
                           "sumF_over_sumM_all", "sumF_over_sumM_posgap", "gap_net_of_F_posgap",
                           "median_F_over_M_posgap", "share_gap_le0", "share_F_gt_gap", "band"]].round(3).to_string(index=False))
    print("\nDECOMPOSITION (clean-V days)")
    print(out["decomposition"].round(3).to_string(index=False))
    print("\nSELECTION")
    print(out["selection"].round(3).to_string(index=False))
    print("\nVARIANTS (pooled)")
    print(out["variants"][out["variants"].group == "gas"].round(3).to_string(index=False))
    print("\nVRE slopes")
    print(out["vre_slopes"].round(4).to_string(index=False))
    print(out["vre_terciles"].round(3).to_string(index=False))


SCO_START = pd.Timestamp("2025-03-19")
SCO_MONTHS = pd.period_range("2025-03", "2026-06", freq="M")


def sco_stage() -> None:
    """Note §5: upper bound D = Fijo + sum b q - c Q against the gap M, Scalable Complex Order era.

    Cleared rows of SCO offers carry -500, so the tranche value sum b q fills the cleared quantity up the
    offered curve in price order, per unit and period.
    """
    u = units()
    U = u.unit.tolist()
    country = u.set_index("unit").country
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "price_es", "price_pt"])
    p["date"] = pd.to_datetime(p.date)
    last = p.date.max()
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "marginal_cost_bid_eur_mwh"], filters=[("unit", "in", U)])
    c["date"] = pd.to_datetime(c.date)
    c = c.rename(columns={"marginal_cost_bid_eur_mwh": "c"})

    hd, days = [], []
    for per in SCO_MONTHS:
        ym = per.strftime("%Y%m")
        h = pd.read_parquet(DATA / f"omie/cab/parquet/cab_{ym}.parquet",
                            columns=["date", "unit", "side", "ofer_plazo", "sco_fixed_eur"], filters=[("unit", "in", U)])
        h["date"] = pd.to_datetime(h.date)
        h = h[(h.side == "V") & (h.date >= SCO_START) & (h.date <= last)]
        h = h.sort_values("ofer_plazo", key=lambda x: x.ne("O")).drop_duplicates(["unit", "date"])[["unit", "date", "sco_fixed_eur"]]
        hd.append(h)
        b = pd.read_parquet(DATA / f"omie/bids/parquet/bids_{ym}.parquet",
                            columns=["date", "period", "unit", "power_mw", "price_eur_mwh", "status", "resolution_min"],
                            filters=[("unit", "in", U), ("side", "=", "V")])
        b["date"] = pd.to_datetime(b.date)
        b = b[(b.date >= SCO_START) & (b.date <= last)]
        cl = b[b.status == "C"].groupby(["unit", "date", "period"], as_index=False).agg(qc=("power_mw", "sum"),
                                                                                       res=("resolution_min", "first"))
        cl = cl[cl.qc > 1e-6]
        o = b[b.status == "O"].sort_values(["unit", "date", "period", "price_eur_mwh"]).copy()
        o["cum"] = o.groupby(["unit", "date", "period"]).power_mw.cumsum()
        o = o.merge(cl[["unit", "date", "period", "qc"]], on=["unit", "date", "period"])
        o["tk"] = np.clip(o.qc - (o.cum - o.power_mw), 0, o.power_mw)
        o["bq"] = o.tk * o.price_eur_mwh * o.resolution_min / 60
        fill = o.groupby(["unit", "date", "period"], as_index=False).agg(tk=("tk", "sum"), bq=("bq", "sum"))
        cl = cl.merge(fill, on=["unit", "date", "period"], how="left").merge(p, on=["date", "period"])
        cl["price"] = np.where(cl.unit.map(country) == "ES", cl.price_es, cl.price_pt)
        cl["q"] = cl.qc * cl.res / 60
        cl["covered"] = cl.tk.fillna(0) >= cl.qc - 0.1
        days.append(cl.assign(r=cl.q * cl.price).groupby(["unit", "date"], as_index=False).agg(
            Q=("q", "sum"), R=("r", "sum"), BQ=("bq", "sum"), n_periods=("period", "nunique"), covered=("covered", "mean")))
        print(f"  {ym}: {len(days[-1]):,} cleared unit-days", flush=True)
    h = pd.concat(hd, ignore_index=True)
    q = pd.concat(days, ignore_index=True)
    d = h.merge(u, on="unit").merge(q, on=["unit", "date"], how="left").merge(c, on=["unit", "date"], how="left")
    d["Q"] = d.Q.fillna(0.0)
    d["decl"] = d.sco_fixed_eur.fillna(0) > 0
    print(f"{len(d):,} unit-days with a sell header, {d.decl.sum():,} declaring, last price day {last.date()}; "
          f"cleared periods covered by the offered curve {q.covered.mean():.4f}")

    sel = d.groupby(["group", "decl"]).agg(unit_days=("Q", "size"), cleared_share=("Q", lambda s: (s > 0).mean()),
                                         GWh=("Q", lambda s: s.sum() / 1e3)).reset_index()
    print(sel.round(3).to_string(index=False))
    sel.to_csv(OUT / "startup_cost_correction_sco_selection.csv", index=False)

    a = d[d.decl & (d.Q > 0) & (d.n_periods > SHORT) & d.c.notna()].copy()
    a["M"] = a.R - a.c * a.Q
    a["D"] = a.sco_fixed_eur + a.BQ - a.c * a.Q
    a["gate"] = a.R >= a.sco_fixed_eur + a.BQ - TOL
    a["slack"] = (a.R - a.sco_fixed_eur - a.BQ) / a.sco_fixed_eur
    a["quarter"] = a.date.dt.to_period("Q").astype(str)

    def row(x, label, cell):
        return {"group": label, "cell": cell, "n_days": len(x), "GWh": x.Q.sum() / 1e3, "gap_eur_mwh": x.M.sum() / x.Q.sum(),
                "D_share_of_gap": x.D.sum() / x.M.sum(), "Fijo_share_of_gap": x.sco_fixed_eur.sum() / x.M.sum(),
                "gate_pass": x.gate.mean(), "slack_median": x.slack.median()}
    rows = [row(x, g, "all") for g, x in a.groupby("group")]
    rows.append(row(a[a.group != "coal"], "gas", "all"))
    rows += [row(x, "ES gas", qq) for qq, x in a[a.group == "ES gas"].groupby("quarter")]
    t = pd.DataFrame(rows)
    print(t.round(3).to_string(index=False))
    t.to_csv(OUT / "startup_cost_correction_sco.csv", index=False)
    for g, x in a.groupby("group"):
        if x.gate.mean() < 0.95:
            print(f"GATE FAILS for {g}: {x.gate.mean():.3f} < 0.95 -> stop and report")


def main() -> None:
    if "--sco" in sys.argv:
        sco_stage()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(PANEL) if "--from-panel" in sys.argv else build_panel()
    d, n = prepare(d)
    print("sample bookkeeping:", n)
    cab_all = declared(None)
    print("cap-window unit-days dropped from the main sample:", int(d.in_cap.sum()))
    sd = short_diagnosis(d)
    sd.to_csv(OUT / "startup_cost_correction_short_runs.csv", index=False)
    print("\nIDENTITY BY NUMBER OF CLEARED PERIODS (original rule set, declaring clean-V days)")
    print(sd.round(3).to_string(index=False))
    # Original rule set: every unit-day with Q > 0.  Amended (note §3.1): drop runs of <= SHORT cleared periods.
    for tag, dd in [("_orig", d), ("", d[~d.short])]:
        print(f"\n==================== SAMPLE {tag or 'amended (runs of more than %d periods)' % SHORT}: {len(dd[~dd.in_cap])} main unit-days")
        out = tables(dd, cab_all)
        for k, v in out.items():
            v.to_csv(OUT / f"startup_cost_correction_{k}{tag}.csv", index=False)
        show(out)


if __name__ == "__main__":
    main()
