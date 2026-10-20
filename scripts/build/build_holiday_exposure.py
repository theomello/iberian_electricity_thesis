#!/usr/bin/env python3
"""How many MW each firm's retail schedule falls on each area's holidays (e_fr).

    .venv/bin/python scripts/build/build_holiday_exposure.py [--reuse-panel]

Step 1 of `docs/specs/2026-10-20-regional-holidays-design.md`. A holiday in one region
lowers demand there; the group whose retailer serves that region buys less. This
measures how much less, per group and area, from the groups' own retail schedules,
so the dose in later steps needs no outside retail shares.

Retail schedule
---------------
`retail_mw` of group g on day d: the purchases of g's retail units in PDBF, every role
code summed, so auction purchases AND bilateral contracts (role 4), as MWh =
-schedule_mw x resolution_min / 60, divided by the hours in the local day (23, 24 or
25). Auction purchases alone are not the load: Iberdrola moves volume between
contracts with its own retailer and the auction (on the Diada 2024 its auction
purchases ROSE 287 MW while its schedule fell 210).

Retail units are `unit_registry` role `purchase_retail`, grouped by their largest
exposed owner that day (`majority_group`), plus the regulated pass-through suppliers'
units (Energía XXI, Curenergía, Comercializadora Regulada, Régsiti, Baser), which the
registry codes `purchase_other`; those form `PASS`. `ALL` is both together. Other
`purchase_other` units (direct consumers, exports) are left out.

Differences
-----------
A clean day is a weekday that is not a holiday or bridge day in any MIBEL area and
falls outside 20 December - 7 January. Each day's references are, on each side, the
nearer of +/-7 and +/-14 days that is clean; a day lacking one on either side gets no
difference. delta_mw = retail_mw - mean(references).

Exposures
---------
Per group, on weekdays that are not market-wide holidays and fall outside 20 December
- 7 January, OLS with HC1 errors of y = -delta_mw (MW less bought) on:

  - a LOCAL indicator per area, on days when at most three mainland Spanish regions
    are off: e_fr, the MW the group buys less on that area's own holiday;
  - `ES`, on days when four or more mainland regions are off (Spain-only national
    days, Holy Thursday, San José ...): the share of mainland demand that is off
    (REData, 2018-2025 mean). Its coefficient is the drop if all of mainland Spain is
    off. Without it, those 18 days loaded onto the sum of the regional coefficients;
  - `PT`, Portugal's own holidays, on any day;
  - two bridge terms: the share of mainland demand on a bridge day, and Portugal's.

Areas that are off together on at least 70% of the local days of either (Asturias and
Extremadura on 8 September, Murcia and La Rioja on 9 June, Aragón and Castilla y León
on 23 April) are merged and reported jointly ("AS+EX"); estimated apart, they took
large offsetting values (La Rioja +831 MW against about 170 MW of demand, Murcia -365).
An area with fewer than 5 local days is left out (listed). The placebo areas
(Balearic and Canary Islands, Ceuta, Melilla) are in: their load is not bought in
MIBEL, so their e should be zero.

Also: every year left out in turn, each year alone (descriptive), and a size check:
the mainland demand series' drop on Spain-only national days (`ree_realtime_5min`,
before its 2025-12-12 contract change) times each region's mean demand (REData,
2018-2025) against ALL's e_r.

Stop rule (spec §4 step 1): CONTINUE if some firm has t >= 2 in at least three areas
(local areas and PT; not the ES term), else STOP.

Outputs (outputs/tables/): holiday_retail_days.parquet (group, date, retail_mw, hours,
ref_mw, delta_mw, ref_dates, in_sample), holiday_exposure.csv, holiday_exposure_loyo.csv,
holiday_exposure_by_year.csv, holiday_exposure_size.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from holidays import AREAS, ES_MAINLAND, MIBEL, PLACEBO, bridges, market_wide, unshared  # noqa: E402
from unit_ownership import majority_group, spells  # noqa: E402

PDBF = ROOT / "data" / "omie" / "pdbf" / "parquet"
REG = ROOT / "data" / "omie" / "registry" / "unit_registry.parquet"
REALTIME = ROOT / "data" / "ree" / "ree_realtime_5min.parquet"
REGIONAL = ROOT / "data" / "ree" / "ree_demand_ccaa_monthly.parquet"
OUT = ROOT / "outputs" / "tables"
PANEL = OUT / "holiday_retail_days.parquet"

MIN_DAYS = 5          # local holiday days an area needs in a sample to get its own e
MAX_LOCAL = 3         # at most this many mainland regions off: a local day
MERGE_SHARE = 0.7     # areas off together on this share of either's local days merge
MIN_RETAIL_MW = 100   # groups smaller than this (mean retail_mw) are not estimated
REALTIME_END = pd.Timestamp("2025-12-12")  # REE realtime contract change
SPANISH = tuple(a for a in AREAS if a != "PT")


def retail_panel() -> pd.DataFrame:
    reg = pd.read_parquet(REG, columns=["unit", "role"])
    keep = set(reg.loc[reg.role.isin(["purchase_retail", "purchase_other"]), "unit"])
    role = reg.set_index("unit").role
    sp = spells()
    parts, hours = [], []
    for f in sorted(PDBF.glob("pdbf_*.parquet")):
        p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw"])
        p["date"] = pd.to_datetime(p.date)
        h = p.groupby("date").agg(n=("period", "max"), res=("resolution_min", "max"))
        hours.append((h.n * h.res / 60).rename("hours"))
        p = p[p.unit.isin(keep)]
        p["mwh"] = -p.schedule_mw * p.resolution_min / 60
        parts.append(p.groupby(["unit", "date"], as_index=False).mwh.sum())
    u = pd.concat(parts, ignore_index=True)
    hrs = pd.concat(hours).groupby(level=0).max()
    exp = majority_group(u, sp, exposed=True)
    anyg = majority_group(u, sp, exposed=False)
    retail = u.unit.map(role).eq("purchase_retail").to_numpy()
    passthrough = (exp.isna() & anyg.notna()).to_numpy()
    u["group"] = np.where(retail & exp.notna().to_numpy(), exp,
                          np.where(passthrough, "PASS", np.where(retail, "UNKNOWN", None)))
    u = u[u.group.notna()]
    g = pd.concat([u.groupby(["group", "date"], as_index=False).mwh.sum(),
                   u.groupby("date", as_index=False).mwh.sum().assign(group="ALL")], ignore_index=True)
    g["hours"] = g.date.map(hrs)
    g["retail_mw"] = g.mwh / g.hours
    return g.drop(columns="mwh")


def references(days: pd.DatetimeIndex) -> pd.DataFrame:
    """For each day, the nearer clean day on each side (+/-7, else +/-14)."""
    span = pd.date_range(days.min() - pd.Timedelta(days=14), days.max() + pd.Timedelta(days=14))
    un, br, mw = unshared(span), bridges(span), market_wide(span)
    md = span.month * 100 + span.day
    season = (md >= 1220) | (md <= 107)
    clean = pd.Series((span.dayofweek < 5) & ~season & ~mw.to_numpy()
                      & (un[list(MIBEL)].sum(axis=1).to_numpy() == 0)
                      & (br[list(MIBEL)].sum(axis=1).to_numpy() == 0), index=span)

    def side(sign: int) -> pd.Series:
        out = pd.Series(pd.NaT, index=days)
        for k in (14, 7):  # 7 last, so it wins where both are clean
            cand = days + pd.Timedelta(days=sign * k)
            ok = clean.reindex(cand).fillna(False).astype(bool).to_numpy()
            out[ok] = cand[ok]
        return out

    return pd.DataFrame({"left": side(-1), "right": side(1)})


def add_deltas(g: pd.DataFrame) -> pd.DataFrame:
    days = pd.DatetimeIndex(sorted(g.date.unique()))
    ref = references(days)
    out = []
    for _, d in g.groupby("group"):
        s = d.set_index("date").retail_mw
        r = ref.copy()
        r["ref_mw"] = (s.reindex(r.left).to_numpy() + s.reindex(r.right).to_numpy()) / 2
        r["ref_dates"] = r.left.dt.strftime("%Y-%m-%d") + "," + r.right.dt.strftime("%Y-%m-%d")
        d = d.merge(r[["ref_mw", "ref_dates"]], left_on="date", right_index=True, how="left")
        d["delta_mw"] = d.retail_mw - d.ref_mw
        out.append(d)
    return pd.concat(out, ignore_index=True)


def mainland_shares() -> pd.Series:
    reg = pd.read_parquet(REGIONAL)
    reg = reg[(reg.month < "2026-01-01") & reg.area.isin(ES_MAINLAND)]
    tot = reg.groupby("area").demand_mwh.sum()
    return tot / tot.sum()


def design(days: pd.DatetimeIndex, shares: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Holiday terms (LOCAL area indicators, ES, PT) and nuisance terms (bridges)."""
    un, br = unshared(days), bridges(days)
    n_es = un[list(ES_MAINLAND)].sum(axis=1)
    local = n_es.le(MAX_LOCAL).to_numpy()
    hol = un[list(SPANISH)].mul(local, axis=0)
    hol["ES"] = (un[list(ES_MAINLAND)] * shares.reindex(ES_MAINLAND).to_numpy()).sum(axis=1) * ~local
    hol["PT"] = un["PT"]
    nuis = pd.DataFrame({"bridge_es": (br[list(ES_MAINLAND)] * shares.reindex(ES_MAINLAND).to_numpy()).sum(axis=1),
                         "bridge_pt": br["PT"]}, index=days)
    return hol.astype(float), nuis.astype(float)


def merge_areas(hol: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Merge Spanish areas that are off together on MERGE_SHARE of either's local days."""
    notes, cols = [], [c for c in hol.columns if c in SPANISH]
    groups = {c: {c} for c in cols}
    changed = True
    while changed:
        changed = False
        keys = list(groups)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                xa = hol[list(groups[a])].max(axis=1)
                xb = hol[list(groups[b])].max(axis=1)
                both, na, nb = (xa * xb).sum(), xa.sum(), xb.sum()
                if min(na, nb) > 0 and both / min(na, nb) >= MERGE_SHARE:
                    groups[a] |= groups.pop(b)
                    notes.append(f"{'+'.join(sorted(groups[a]))}: off together on {int(both)} of "
                                 f"{int(min(na, nb))} local days, merged")
                    changed = True
                    break
            if changed:
                break
    out = hol.drop(columns=cols)
    for members in groups.values():
        name = "+".join(a for a in AREAS if a in members)
        out[name] = hol[list(members)].max(axis=1)
    return out, notes


def fit(y: pd.Series, hol: pd.DataFrame, nuis: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    hol, notes = merge_areas(hol)
    small = [c for c in hol.columns if c != "ES" and 0 < (hol[c] > 0).sum() < MIN_DAYS]
    notes += [f"{c}: {int((hol[c] > 0).sum())} holiday days, left out" for c in small]
    hol = hol.drop(columns=small + [c for c in hol.columns if (hol[c] > 0).sum() == 0])
    X = pd.concat([pd.Series(1.0, index=y.index, name="const"), hol, nuis.loc[:, nuis.std() > 0]], axis=1)
    Xm, ym = X.to_numpy(), y.to_numpy()
    rank = np.linalg.matrix_rank(Xm)
    if rank < Xm.shape[1]:
        notes.append(f"design rank {rank} < {Xm.shape[1]} columns")
    xtx_inv = np.linalg.pinv(Xm.T @ Xm)
    beta = xtx_inv @ Xm.T @ ym
    resid = ym - Xm @ beta
    n, k = Xm.shape
    cov = xtx_inv @ ((Xm * resid[:, None] ** 2).T @ Xm) @ xtx_inv * n / (n - k)
    res = pd.DataFrame({"area": X.columns, "e_mw": beta, "se": np.sqrt(np.diag(cov))})
    res = res[res.area.isin(hol.columns)].copy()
    res["n_days"] = [int((hol[a] > 0).sum()) for a in res.area]
    res["t"] = res.e_mw / res.se
    return res, notes


def estimate(panel: pd.DataFrame, groups: list[str], shares: pd.Series, years: list[int] | None = None,
             label: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    rows, notes = [], []
    for grp in groups:
        d = panel[(panel.group == grp) & panel.in_sample & panel.delta_mw.notna()]
        if years is not None:
            d = d[d.date.dt.year.isin(years)]
        if len(d) < 50:
            continue
        idx = pd.DatetimeIndex(d.date)
        hol, nuis = design(idx, shares)
        r, nt = fit(pd.Series(-d.delta_mw.to_numpy(), index=idx), hol, nuis)
        r.insert(0, "group", grp)
        for k, v in (label or {}).items():
            r[k] = v
        rows.append(r)
        notes += [f"{grp}: {x}" for x in nt]
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), notes


def size_check(ex: pd.DataFrame, shares: pd.Series) -> pd.DataFrame:
    rt = pd.read_parquet(REALTIME, columns=["local_date", "demand"])
    rt["date"] = pd.to_datetime(rt.local_date)
    s = rt[rt.date < REALTIME_END].groupby("date").demand.mean()
    d = add_deltas(pd.DataFrame({"group": "NATIONAL", "date": s.index, "retail_mw": s.to_numpy()}))
    span = pd.DatetimeIndex(d.date)
    un = unshared(span)
    es_only = (un[list(ES_MAINLAND)].sum(axis=1) == len(ES_MAINLAND)) & (un["PT"] == 0)
    sel = es_only.to_numpy() & (span.dayofweek < 5) & d.delta_mw.notna().to_numpy()
    rate = float((-d.delta_mw[sel] / d.ref_mw[sel]).mean())
    mainland_mw = float(s[(s.index >= "2018-01-01") & (s.index < "2026-01-01")].mean())
    allx = ex[ex.group == "ALL"].set_index("area").e_mw
    out = []
    for area in allx.index:
        if area == "PT":
            continue
        base = mainland_mw if area == "ES" else mainland_mw * shares.reindex(area.split("+")).fillna(0).sum()
        pred = rate * base
        out.append((area, allx[area], pred, allx[area] / pred if pred else np.nan))
    print(f"\nsize check: mainland demand falls {rate:.1%} on Spain-only national days ({int(sel.sum())} days); "
          f"placebo areas have no mainland demand, so no prediction")
    return pd.DataFrame(out, columns=["area", "e_all_mw", "predicted_mw", "ratio"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse-panel", action="store_true", help="skip PDBF; read the stored day panel")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.reuse_panel:
        g = pd.read_parquet(PANEL)
    else:
        g = add_deltas(retail_panel())
        days = pd.DatetimeIndex(g.date)
        md = days.month * 100 + days.day
        mw = market_wide(pd.DatetimeIndex(sorted(g.date.unique())))
        g["in_sample"] = (days.dayofweek < 5) & ~((md >= 1220) | (md <= 107)) & ~mw.reindex(days).to_numpy()
        g[["group", "date", "retail_mw", "hours", "ref_mw", "delta_mw", "ref_dates", "in_sample"]].to_parquet(
            PANEL, index=False)
    shares = mainland_shares()

    size = g[g.in_sample].groupby("group").retail_mw.mean()
    groups = ["ALL", "PASS"] + [x for x in size[size >= MIN_RETAIL_MW].sort_values(ascending=False).index
                                if x not in ("ALL", "PASS", "UNKNOWN")]
    ex, notes = estimate(g, groups, shares)
    ex["share_of_retail"] = ex.e_mw / ex.group.map(size)
    ex.to_csv(OUT / "holiday_exposure.csv", index=False)
    print("notes (ALL):\n  " + "\n  ".join(n for n in sorted(set(notes)) if n.startswith("ALL:")))

    years = sorted(g.date.dt.year.unique())
    loyo = [estimate(g, groups, shares, [y for y in years if y != out], {"year_out": out})[0] for out in years]
    pd.concat(loyo, ignore_index=True).to_csv(OUT / "holiday_exposure_loyo.csv", index=False)
    by = [estimate(g, groups, shares, [y], {"year": y})[0] for y in years]
    pd.concat(by, ignore_index=True).to_csv(OUT / "holiday_exposure_by_year.csv", index=False)

    sz = size_check(ex, shares)
    sz.to_csv(OUT / "holiday_exposure_size.csv", index=False)
    print(sz.round(2).to_string(index=False))

    tab = ex.assign(cell=ex.e_mw.round(0).astype(int).astype(str) + np.where(ex.t >= 2, "*", "")) \
        .pivot(index="group", columns="area", values="cell").reindex(groups)
    first = ["ES", "PT"]
    mib = [c for c in tab.columns if c not in first and c.split("+")[0] in MIBEL]
    plc = [c for c in tab.columns if c not in first and c.split("+")[0] in PLACEBO]
    pd.set_option("display.width", 250)
    print("\ne_fr, MW less bought on the area's holiday (* t >= 2; ES = all of mainland Spain off):")
    print(tab[first + mib + plc].fillna("").to_string())

    firms = ex[~ex.group.isin(["ALL", "PASS"]) & (ex.area != "ES")
               & ex.area.map(lambda x: x.split("+")[0] in MIBEL)]
    strong = firms[firms.t >= 2].groupby("group").area.apply(list)
    print("\nareas with t >= 2 (local areas and PT), by group:")
    for grp, areas in strong.items():
        print(f"  {grp}: {len(areas)}  {', '.join(areas)}")
    ok = (strong.map(len) >= 3).any()
    print("\nstop rule:", "CONTINUE" if ok else "STOP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
