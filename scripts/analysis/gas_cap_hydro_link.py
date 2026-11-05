#!/usr/bin/env python3
"""Does hydro react to the gas cap's cost shock the way thermal declared costs did? Firm by firm.

    OMP_NUM_THREADS=1 .venv/bin/python scripts/analysis/gas_cap_hydro_link.py

Rules were written into `notes/rq-gas-cap-hydro-link.md` §1 before this was run. Short version:

  y(unit, day) = ln(ocf / λ*30s): the offered price at the unit's expected running share of its
  offered hydro volume (`outputs/cache/step/hydro_YYYYMM.parquet`), over the price-taking water
  value (`hydro_cost_daily.parquet`). Sample: not pumped, zero_share in [0, 0.5], no `cab` spell
  break inside the window, offer above EUR 1. Firm = owner group in force on the day
  (`lib/unit_ownership.majority_group`).

  EVENT   J(D) = median over units of (mean y over D..D+6) - (mean y over D-7..D-1), as in
          `gas_cap_declared_cost.py`. D = 2022-06-15 against 273 placebo dates 2021-09-08 ->
          2022-06-07. Secondary: D = 2021-06-01 (clawback) against 2019-01-08 -> 2021-05-18.
          Also J of ln(ocf) and of ln(λ*) alone, and EDP minus Iberdrola paired by date.
  DOSE    y = a_u + phi * x_d (+ b * ln gas), x_d = the log fall of a gas plant's cost from the
          subsidy; window 2022-06-01 -> 2023-03-31; placebo = the same regression on windows
          shifted by k days with the subsidy hump shifted with them.
  CHECKS  read at the 20% / 50% quantile, λ*90s, λ* without storage, net of the day's bilateral
          contracts, y clipped, leave-one-unit-out.

Writes outputs/tables/gas_cap_hydro_link_{summary,event,dose,checks,units,monthly,daily}.csv.
"""
from __future__ import annotations

import faulthandler
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

faulthandler.dump_traceback_later(900, exit=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts/lib"))
sys.path.insert(0, str(ROOT / "scripts/analysis"))
from unit_ownership import attach_owners, majority_group, spells  # noqa: E402
import water_value_forward_check as wvf  # noqa: E402  (bilateral, day_hours helpers only)

T = ROOT / "outputs" / "tables"
CACHE = ROOT / "outputs/cache/step"
DATA = ROOT / "data"
FIRST, LAST = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-09-30")
CAP = pd.Timestamp("2022-06-15")
CLAW = pd.Timestamp("2021-06-01")
CAP_PLACEBO = pd.date_range("2021-09-08", CAP - pd.Timedelta(days=8))
CLAW_PLACEBO = pd.date_range("2019-01-08", CLAW - pd.Timedelta(days=14))
DOSE = (pd.Timestamp("2022-06-01"), pd.Timestamp("2023-03-31"))
ZERO = 1.0
MIN_SIDE, MIN_UNITS = 4, 3
THERMAL_J, THERMAL_FULL = -0.544, -0.721      # gas_cap_declared_cost_event.csv
FIRMS = ["EDP", "IBERDROLA", "ENDESA", "NATURGY"]
GROUPS = FIRMS + ["ALL"]


# ---------------------------------------------------------------- panel
def offers(units: list[str], cf: pd.DataFrame) -> pd.DataFrame:
    """unit, date, o20, o50, ocf, ocf_day, cap: read points of each unit-day's offered hydro curve."""
    parts = []
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        ym = f.stem.split("_")[1]
        if not (FIRST <= pd.Timestamp(ym + "01") <= LAST):
            continue
        h = pd.read_parquet(f, columns=["date", "unit", "price", "mw", "cap_mw", "withdrawn"])
        h = h[h.unit.isin(units) & ~h.withdrawn & (h.mw > 0)]
        if h.empty:
            continue
        h["date"] = pd.to_datetime(h.date)
        h = h.merge(cf, on=["unit", "date"]).sort_values(["unit", "date", "price"])
        g = h.groupby(["unit", "date"])
        h["cum"] = g.mw.cumsum() / g.mw.transform("sum")
        at = lambda col: h[h.cum >= h[col]].groupby(["unit", "date"]).price.first()  # noqa: E731
        h["q20"], h["q50"] = 0.2, 0.5
        u = g.agg(o=("mw", "sum"), cap=("cap_mw", "max"), cf_s=("cf_s", "first")).reset_index()
        b = wvf.bilateral(ym, u.unit.unique().tolist())
        u = u.merge(b, on=["unit", "date"], how="left").fillna({"bil": 0.0})
        u["r_day"] = (u.cf_s * u.cap * wvf.day_hours(u.date) - u.bil) / u.o
        h = h.merge(u[["unit", "date", "r_day"]], on=["unit", "date"])
        parts.append(pd.concat([at("q20").rename("o20"), at("q50").rename("o50"), at("cf_s").rename("ocf"),
                                wvf.read_at(h, "r_day").rename("ocf_day"),
                                u.set_index(["unit", "date"]).cap], axis=1))
    return pd.concat(parts).reset_index()


def build_panel() -> pd.DataFrame:
    hc = pd.read_parquet(T / "hydro_cost_daily.parquet")
    hc["date"] = pd.to_datetime(hc.date)
    hc = hc[hc.date.between(FIRST, LAST) & ~hc.pumped & hc.zero_share.notna() & (hc.zero_share <= 0.5)]
    hc = hc[hc.cost_eur_mwh > 0]
    o = offers(sorted(hc.unit.unique()), hc[["unit", "date", "cf_s"]])
    p = hc.merge(o, on=["unit", "date"], how="inner")
    sp = spells()
    keys = p[["unit", "date"]].drop_duplicates()
    split = attach_owners(keys, sp, value_cols=())
    split = split[(split.share < 1 - 1e-9) & split.date.between("2021-05-01", "2023-04-30")]
    print(f"eligible unit-days with split ownership, 2021-05 -> 2023-04: {len(split)} "
          f"({', '.join(sorted(split.unit.unique())) or 'none'})")
    p["firm"] = majority_group(p, sp, exposed=True).to_numpy()
    p = p[p.firm.notna()]
    lam, l90, lns = p.cost_eur_mwh, p.cost_90_eur_mwh, p.cost_nostorage_eur_mwh

    def lr(off, den):
        return np.log(off.where(off > ZERO) / den.where(den > 0))

    p["y"] = lr(p.ocf, lam)
    p["lo"] = np.log(p.ocf.where(p.ocf > ZERO))
    p["ll"] = np.log(lam.where(p.ocf > ZERO))
    p["y_o20"], p["y_o50"] = lr(p.o20, lam), lr(p.o50, lam)
    p["y_l90"], p["y_nos"] = lr(p.ocf, l90), lr(p.ocf, lns)
    p["y_net"] = lr(p.ocf_day, lam)
    p["y_clip"] = p.y.clip(np.log(0.2), np.log(5))
    return p


def matrices(p: pd.DataFrame, cols: list[str]) -> dict:
    """date x unit matrices for each outcome, plus the spell, firm and capacity matrices."""
    dates = pd.date_range(FIRST, LAST)
    units = sorted(p.unit.unique())
    out = {"dates": dates, "units": units}
    for c in cols:
        out[c] = p.pivot(index="date", columns="unit", values=c).reindex(index=dates, columns=units).to_numpy()
    firms = sorted(p.firm.unique())
    fid = {f: i for i, f in enumerate(firms)}
    out["firm"] = p.assign(f=p.firm.map(fid)).pivot(index="date", columns="unit", values="f").reindex(
        index=dates, columns=units).to_numpy()
    out["spell"] = p.pivot(index="date", columns="unit", values="spell").reindex(index=dates, columns=units).to_numpy()
    out["cap"] = p.pivot(index="date", columns="unit", values="cap").reindex(index=dates, columns=units).to_numpy()
    out["fid"] = fid
    out["valid_firm"] = {f: i for f, i in fid.items()}
    return out


# ---------------------------------------------------------------- the jump
def unit_jumps(M: dict, col: str, D: pd.Timestamp, firm: str, drop: str | None = None, side: int = 7,
               min_side: int = MIN_SIDE) -> pd.DataFrame:
    """Per unit: change in mean y from the `side` days before D to the `side` days from it (7 in the rules; 1 for
    the post-hoc day-one statistic). Units with a spell break or a change of owner inside the window, or fewer than
    min_side days on a side, are out."""
    i = M["dates"].get_loc(D)
    lo, hi = i - side, i + side
    x = M[col]
    pre, post = x[lo:i], x[i:hi]
    n_pre, n_post = np.isfinite(pre).sum(0), np.isfinite(post).sum(0)
    d = np.nanmean(post, 0) - np.nanmean(pre, 0)
    ok = (n_pre >= min_side) & (n_post >= min_side)
    s = M["spell"][lo:hi]
    ok &= np.nan_to_num(np.nanmax(s, 0) - np.nanmin(s, 0), nan=1.0) == 0
    f = M["firm"][lo:hi]
    fmax, fmin = np.nanmax(f, 0), np.nanmin(f, 0)
    ok &= np.isfinite(fmax) & (fmax == fmin)
    if firm != "ALL":
        ok &= fmax == M["fid"].get(firm, -99)
    ok &= np.isfinite(d)
    r = pd.DataFrame({"unit": np.array(M["units"])[ok], "d": d[ok], "cap": np.nanmean(M["cap"][lo:hi], 0)[ok],
                      "n_days": (n_pre + n_post)[ok]})
    if drop is not None:
        r = r[r.unit != drop]
    return r


def jump(M, col, D, firm, drop=None, side: int = 7, min_side: int = MIN_SIDE) -> tuple[float, float, int, int]:
    r = unit_jumps(M, col, D, firm, drop, side, min_side)
    if len(r) < MIN_UNITS:
        return np.nan, np.nan, len(r), int(r.n_days.sum())
    w = r.cap.fillna(r.cap.mean())
    return float(r.d.median()), float(np.average(r.d, weights=w)), len(r), int(r.n_days.sum())


def event_table(M, cols, actual, placebos, tag, side: int = 7, min_side: int = MIN_SIDE) -> pd.DataFrame:
    rows = []
    for firm in GROUPS:
        for col in cols:
            for kind, D in [("actual", actual)] + [("placebo", d) for d in placebos]:
                j, jw, n, nd = jump(M, col, D, firm, side=side, min_side=min_side)
                rows.append({"event": tag, "firm": firm, "measure": col, "kind": kind, "date": D, "J": j,
                             "J_capweighted": jw, "n_units": n, "n_unit_days": nd})
    return pd.DataFrame(rows)


def contrast(e: pd.DataFrame, a: str, b: str, col: str) -> pd.DataFrame:
    x = e[(e.measure == col)].pivot_table(index=["date", "kind"], columns="firm", values="J")
    return (x[a] - x[b]).rename("J").reset_index()


def read_band(actual: float, pl: np.ndarray, n_units: int) -> dict:
    pl = pl[np.isfinite(pl)]
    if len(pl) < 200 or not np.isfinite(actual):
        return {"n_placebo": len(pl), "status": "STOP: no usable placebo band (rule 1)"}
    lo, med, hi = np.percentile(pl, [2.5, 50, 97.5])
    h = (hi - lo) / 2
    out = {"n_placebo": len(pl), "pl_2.5": lo, "pl_50": med, "pl_97.5": hi, "half_width": h,
           "pct_of_placebo_below": float((pl <= actual).mean()),
           "two_sided_share": float((np.abs(pl) >= abs(actual)).mean()), "pl_min": pl.min(), "pl_max": pl.max()}
    informative = h < abs(THERMAL_J)
    where = "inside band" if lo <= actual <= hi else ("below band" if actual < lo else "above band")
    out["position"] = where
    out["status"] = ("read: " + where) if informative else f"STOP: band half-width {h:.2f} >= {abs(THERMAL_J)}"
    if n_units < 5:
        out["status"] += " (fewer than 5 units: not a finding)"
    return out


def summarise(e: pd.DataFrame, tag: str, extra_contrast: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for firm in GROUPS:
        for col in ("y", "lo", "ll"):
            x = e[(e.firm == firm) & (e.measure == col)]
            a = x[x.kind == "actual"].iloc[0]
            row = {"event": tag, "firm": firm, "measure": col, "n_units": a.n_units, "n_unit_days": a.n_unit_days,
                   "J": a.J, "J_capweighted": a.J_capweighted, "J_share_of_full_thermal_fall": a.J / THERMAL_FULL}
            row |= read_band(a.J, x[x.kind == "placebo"].J.to_numpy(), a.n_units)
            # ADDED AFTER SEEING RESULTS (not a rule in the note's section 1): the capacity-weighted J
            # against the capacity-weighted placebo J on the same dates.
            pw = x[x.kind == "placebo"].J_capweighted.dropna().to_numpy()
            if len(pw) >= 200 and np.isfinite(a.J_capweighted):
                row["posthoc_capw_pct_of_placebo_below"] = float((pw <= a.J_capweighted).mean())
                row["posthoc_capw_two_sided_share"] = float((np.abs(pw) >= abs(a.J_capweighted)).mean())
            rows.append(row)
    if extra_contrast is not None:
        c = extra_contrast
        a = c[c.kind == "actual"].J.iloc[0]
        rows.append({"event": tag, "firm": "EDP minus IBERDROLA", "measure": "y", "J": a,
                     **read_band(a, c[c.kind == "placebo"].J.to_numpy(), 7)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the dose
def thermal_x() -> pd.DataFrame:
    """date, x (median over the gas units of ln(net/gross), bid-time) and ln gas (bid-time MIBGAS)."""
    pa = pd.read_parquet(T / "gas_cap_offer_panel.parquet", columns=["unit", "iberia"]).drop_duplicates()
    units = pa[pa.iberia & ~pa.unit.str.startswith("RTG")].unit.unique()
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "marginal_cost_bid_eur_mwh", "subsidy_bid_eur_mwh",
                                 "mibgas_es_eur_mwh_bid"])
    c = c[c.unit.isin(units)]
    c["date"] = pd.to_datetime(c.date)
    g = c.marginal_cost_bid_eur_mwh
    c["lx"] = np.log((g - c.subsidy_bid_eur_mwh) / g)
    d = c.groupby("date").agg(x=("lx", "median"), gas=("mibgas_es_eur_mwh_bid", "median"))
    d["lgas"] = np.log(d.gas)
    return d[["x", "lgas"]]


def fe_ols(y, X, unit, week):
    """Unit-demeaned OLS slope(s) and week-clustered SE. X is n x k."""
    cols = [f"x{j}" for j in range(X.shape[1])]
    df = pd.DataFrame(X, columns=cols)
    df["y"] = y
    g = pd.Series(unit)
    dm = df - df.groupby(g.to_numpy()).transform("mean")
    Xd, yd = dm[cols].to_numpy(), dm["y"].to_numpy()
    xtx = Xd.T @ Xd
    if np.linalg.det(xtx) < 1e-12:
        return np.full(Xd.shape[1], np.nan), np.full(Xd.shape[1], np.nan)
    inv = np.linalg.inv(xtx)
    beta = inv @ (Xd.T @ yd)
    e = yd - Xd @ beta
    k = Xd.shape[1]
    meat = np.zeros((k, k))
    for _, idx in pd.Series(np.arange(len(e))).groupby(week.to_numpy()):
        s = Xd[idx.to_numpy()].T @ e[idx.to_numpy()]
        meat += np.outer(s, s)
    n_cl = week.nunique()
    v = inv @ meat @ inv * n_cl / max(n_cl - 1, 1)
    return beta, np.sqrt(np.diag(v))


def dose_window(p: pd.DataFrame, th: pd.DataFrame, firm: str, k: int, gas: bool):
    """phi (and se) for a window shifted by k days; None if the firm lacks data there."""
    a, b = DOSE[0] + pd.Timedelta(days=k), DOSE[1] + pd.Timedelta(days=k)
    w = p[p.date.between(a, b) & p.y.notna()]
    if firm != "ALL":
        w = w[w.firm == firm]
    # keep each unit's longest spell inside the window (a unit whose contents changed is one unit twice)
    top = w.groupby(["unit", "spell"]).size().rename("n").reset_index().sort_values("n").drop_duplicates("unit", keep="last")
    w = w.merge(top[["unit", "spell"]], on=["unit", "spell"])
    n = w.groupby("unit").size()
    w = w[w.unit.isin(n[n >= 60].index)]
    if w.unit.nunique() < MIN_UNITS or len(w) < 150:
        return None
    x = th.x.reindex(w.date - pd.Timedelta(days=k)).fillna(0.0).to_numpy()     # the hump, moved with the window
    cols = [x]
    if gas:
        g = th.lgas.reindex(w.date).to_numpy()
        keep = np.isfinite(g)
        if keep.sum() < 150:
            return None
        w, x = w[keep], x[keep]
        cols = [x, g[keep]]
    wk = w.date.dt.strftime("%G-%V").reset_index(drop=True)
    beta, se = fe_ols(w.y.to_numpy(), np.column_stack(cols), w.unit.to_numpy(), wk)
    return float(beta[0]), float(se[0]), w.unit.nunique(), len(w)


def dose_table(p: pd.DataFrame) -> pd.DataFrame:
    th = thermal_x()
    ks = [k for k in range(-1247, 914, 7) if abs(k) >= 245]
    rows = []
    for firm in GROUPS:
        for gas in (False, True):
            act = dose_window(p, th, firm, 0, gas)
            if act is None:
                continue
            pl = np.array([r[0] for r in (dose_window(p, th, firm, k, gas) for k in ks) if r is not None])
            row = {"firm": firm, "gas_control": gas, "n_units": act[2], "n_unit_days": act[3], "phi": act[0],
                   "se_week_cluster": act[1], "n_placebo": len(pl)}
            if len(pl) >= 50:
                lo, med, hi = np.percentile(pl, [2.5, 50, 97.5])
                h = (hi - lo) / 2
                pos = "inside band" if lo <= act[0] <= hi else ("below band" if act[0] < lo else "above band")
                row |= {"pl_2.5": lo, "pl_50": med, "pl_97.5": hi, "half_width": h,
                        "pct_of_placebo_below": float((pl <= act[0]).mean()), "position": pos,
                        "status": ("read: " + pos) if h < 1 else f"STOP: band half-width {h:.2f} >= 1"}
                if act[2] < 5:
                    row["status"] += " (fewer than 5 units: not a finding)"
            else:
                row["status"] = "STOP: fewer than 50 placebo windows"
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- descriptive
def monthly_daily(p: pd.DataFrame):
    q = p[p.y.notna()].assign(ratio=lambda d: np.exp(d.y))
    rows = []
    for firm in GROUPS:
        x = q if firm == "ALL" else q[q.firm == firm]
        m = x[x.date.between("2021-06-01", "2023-06-30")]
        r = m.groupby(m.date.dt.strftime("%Y-%m")).agg(units=("unit", "nunique"), unit_days=("y", "size"),
                                                       ratio_median=("ratio", "median"), ocf_median=("ocf", "median"),
                                                       lam_median=("cost_eur_mwh", "median")).round(3)
        rows.append(r.assign(firm=firm).reset_index().rename(columns={"index": "month", "date": "month"}))
    daily = []
    for firm in GROUPS:
        x = q if firm == "ALL" else q[q.firm == firm]
        m = x[x.date.between(CAP - pd.Timedelta(days=21), CAP + pd.Timedelta(days=20))]
        r = m.groupby("date").agg(units=("unit", "nunique"), ratio_median=("ratio", "median"),
                                  ocf_median=("ocf", "median"), lam_median=("cost_eur_mwh", "median")).round(3)
        daily.append(r.assign(firm=firm).reset_index())
    return pd.concat(rows), pd.concat(daily)


def main() -> int:
    p = build_panel()
    print(f"panel: {len(p):,} unit-days, {p.unit.nunique()} units, {p.date.min().date()} -> {p.date.max().date()}")
    chk_cols = ["y_o20", "y_o50", "y_l90", "y_nos", "y_net", "y_clip"]
    M = matrices(p, ["y", "lo", "ll"] + chk_cols)

    # days at or below EUR 1 around the cap (selection check): of the days with cf_s offers
    z = p[p.date.between(CAP - pd.Timedelta(days=7), CAP + pd.Timedelta(days=6))]
    print("share of unit-days in the cap windows with ocf <= EUR 1 (dropped from y):",
          f"{(z.ocf <= ZERO).mean():.3f}")

    e_cap = event_table(M, ["y", "lo", "ll"], CAP, CAP_PLACEBO, "cap_2022-06-15")
    e_claw = event_table(M, ["y", "lo", "ll"], CLAW, CLAW_PLACEBO, "clawback_2021-06-01")
    c_cap = contrast(e_cap, "EDP", "IBERDROLA", "y")
    c_claw = contrast(e_claw, "EDP", "IBERDROLA", "y")
    # POST HOC (not in the note's section 1): the one-day change, D-1 to D, against the same placebo dates
    e_d1 = event_table(M, ["y", "lo", "ll"], CAP, CAP_PLACEBO, "posthoc_day_one_cap", side=1, min_side=1)
    summ = pd.concat([summarise(e_cap, "cap_2022-06-15", c_cap), summarise(e_claw, "clawback_2021-06-01", c_claw),
                      summarise(e_d1, "posthoc_day_one_cap")])
    e_claw = pd.concat([e_claw, e_d1])
    summ.to_csv(T / "gas_cap_hydro_link_summary.csv", index=False)
    pd.concat([e_cap, e_claw]).to_csv(T / "gas_cap_hydro_link_event.csv", index=False)

    # checks: same J and band, firm rows, cap date and clawback date
    rows = []
    for tag, D, pl in [("cap_2022-06-15", CAP, CAP_PLACEBO), ("clawback_2021-06-01", CLAW, CLAW_PLACEBO)]:
        for col in ["y"] + chk_cols:
            for firm in GROUPS:
                j = jump(M, col, D, firm)
                pj = np.array([jump(M, col, d, firm)[0] for d in pl])
                rows.append({"event": tag, "firm": firm, "check": col, "n_units": j[2], "J": j[0],
                             **read_band(j[0], pj, j[2])})
        for firm in GROUPS:
            r = unit_jumps(M, "y", D, firm)
            loo = [jump(M, "y", D, firm, drop=u)[0] for u in r.unit]
            if loo:
                rows.append({"event": tag, "firm": firm, "check": "leave_one_unit_out", "n_units": len(r),
                             "J": float(np.nanmin(loo)), "pl_97.5": float(np.nanmax(loo)),
                             "status": "J = min, pl_97.5 column = max of J with each unit dropped"})
    chk = pd.DataFrame(rows)
    chk.to_csv(T / "gas_cap_hydro_link_checks.csv", index=False)

    ufirm = p.groupby("unit").firm.agg(lambda x: x.mode().iat[0])
    ur = []
    for tag, D in [("cap_2022-06-15", CAP), ("clawback_2021-06-01", CLAW)]:
        for col in ("y", "lo", "ll"):
            r = unit_jumps(M, col, D, "ALL")
            pls = CAP_PLACEBO if D == CAP else CLAW_PLACEBO
            pl = pd.concat([unit_jumps(M, col, d, "ALL").assign(date=d) for d in pls])
            own = pl.groupby("unit").d.apply(lambda v: v.to_numpy())
            r["own_placebo_n"] = r.unit.map(lambda u: len(own.get(u, [])))
            r["own_pct_below"] = [float((own[u] <= d).mean()) if len(own.get(u, [])) >= 100 else np.nan
                                  for u, d in zip(r.unit, r.d)]
            r["own_two_sided"] = [float((np.abs(own[u]) >= abs(d)).mean()) if len(own.get(u, [])) >= 100 else np.nan
                                  for u, d in zip(r.unit, r.d)]
            ur.append(r.assign(event=tag, measure=col, firm=r.unit.map(ufirm)))
    pd.concat(ur)[["event", "measure", "firm", "unit", "d", "cap", "n_days", "own_placebo_n", "own_pct_below", "own_two_sided"]].rename(columns={"d": "J_unit"}).sort_values(
        ["event", "measure", "firm", "unit"]).to_csv(T / "gas_cap_hydro_link_units.csv", index=False)

    dose = dose_table(p)
    dose.to_csv(T / "gas_cap_hydro_link_dose.csv", index=False)
    mon, day = monthly_daily(p)
    mon.to_csv(T / "gas_cap_hydro_link_monthly.csv", index=False)
    day.to_csv(T / "gas_cap_hydro_link_daily.csv", index=False)

    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["event", "firm", "measure", "n_units", "n_unit_days", "J", "J_capweighted", "n_placebo", "pl_2.5", "pl_50",
            "pl_97.5", "pct_of_placebo_below", "two_sided_share", "status"]
    print("\nSUMMARY\n", summ[[c for c in cols if c in summ.columns]].round(3).to_string(index=False))
    print("\nCHECKS (y only, firm rows)\n", chk[["event", "firm", "check", "n_units", "J", "pl_2.5", "pl_97.5", "status"]]
          .round(3).to_string(index=False))
    print("\nDOSE\n", dose.round(3).to_string(index=False))
    print("\nDAILY ratio around the cap\n", day.pivot(index="date", columns="firm", values="ratio_median").round(2).to_string())
    print("\nMONTHLY ratio\n", mon.pivot(index="month", columns="firm", values="ratio_median").round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
