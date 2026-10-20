#!/usr/bin/env python3
"""One fixed step per unit and hour: the hydro departure without the price-taker simulation.

    .venv/bin/python scripts/analysis/fixed_step_test.py --build         # step 1: the rows
    .venv/bin/python scripts/analysis/fixed_step_test.py --summarise     # step 1: by year
    .venv/bin/python scripts/analysis/fixed_step_test.py --estimate      # step 2: the estimates
    .venv/bin/python scripts/analysis/fixed_step_test.py --simulated 1   # step 2: the code check

Design: `docs/specs/2026-10-19-fixed-step-design.md`; running note
`notes/rq-fixed-step.md`. The step estimator keeps a step only where the price reaches it,
so price-takers read β ≠ 0 and a simulated band is needed (`rq-price-taking-simulation.md`
§3). Here every unit-hour enters: each storage unit's offered hydro ladder in the hour
(withdrawn steps out, sorted by price) is read at a point fixed before the auction, its
expected running share cf_s that day (`build_water_value_forward.py`). Under price-taking
that step's gap over λ*30s does not move with the firm's at-cost stake Zb.

ROWS (one per unit, owner group and hour; `outputs/cache/step/fixed_step_YYYYMM.parquet`)
  p_cf            price of the first step at which the cumulative offered share reaches cf_s
  p_k010 … p_k200 the same at k × cf_s, k in GRID (shares above 1 read the top step)
  p_bot           at 5% of the ladder: a step that clears in any hour (the placebo)
  p_net           at r_net, the share the water left after bilateral contracts (PDBF role 4)
                  would fill, pooled over the month as in `water_value_forward_check.offered`;
                  none where the contracts take all the expected water (r_net ≤ 0)
  p_mw            at a fixed MW, q* = cf_s × the unit's mean offered MW in the month; none
                  where the hour's ladder is shorter (short)
  offered_mw, cap_mw, mw_le_lam (MW offered at or below λ*30s), cleared_mw, n_steps, n_prices
  Zb, Zc          the stake at cost (`leg_b_levels.at_cost`: X on the curve with the firm's
                  hydro at λ*, over the NEAR draws nearest the day's median λ* of the class or
                  the unit's own λ*; none below the slope floor)
  cp_mean         the at-cost draws' mean price (`hcompcostprice`); rel = cp_mean / λ*30s
  p_clear         the hour's clearing price
  λ*30s, cf_s, storage, fill, zero_share (`hydro_cost_daily`), cls (hydro, pumped)

`--summarise` writes outputs/tables/fixed_step_rows_summary.csv: by year and class, and by
owner group on the main sample (storage hydro, zero_share ≤ 0.5, Zb defined, rel ≥ 0.9).

STEP 2 (`--estimate` → outputs/tables/fixed_step_results.csv). g = read − λ*30s on Zb by least
squares, unit × month and class × hour effects, clusters by week: under price-taking the slope
is 0, with no band. Unit-months with more than half the offered MW at or below €2 are out.
Cells: pooled, departure periods (to 2021-06, from 2024-01) against the crisis, half-years,
seller (Zb > 0) and buyer side, and the side within EDP and within Iberdrola in one regression.
Profile along the ladder; the bottom step as a placebo to 2022; bands of at-cost price; checks
(net read, fixed MW, unit × day, unit × hour of day, the level control, quantities); pumped
apart. Differs: the 95% interval excludes 0; price-taking accepted: it lies within ±0.1.
`--simulated SEED` reads simulated price-takers' offers the same way: a code check (b ≈ 0).
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_engine import NEAR  # noqa: E402
from step_estimator import wdemean, with_slopes  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402
from water_value_forward_check import bilateral, day_hours  # noqa: E402

TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
WV = TABLES / "water_value_forward.parquet"
COST = TABLES / "hydro_cost_daily.parquet"
SUMMARY = TABLES / "fixed_step_rows_summary.csv"
GRID = (0.10, 0.25, 0.50, 1.50, 2.00)     # × cf_s
BOTTOM = 0.05                              # share of the ladder
ZERO_SHARE_MAX = 0.5                       # above it the cost does not describe the offers
IN_PLAY = 0.9                              # main sample: at-cost price ≥ 0.9 λ*
KEY = ["unit", "group", "hid"]


def read_share(h: pd.DataFrame, col: str) -> pd.Series:
    """KEY -> price of the first step at which the cumulative offered share reaches column col
    (capped at 1); none where col ≤ 0 or is missing."""
    r = h[col].clip(upper=1.0)
    return h[(r > 0) & (h.cum_share >= r - 1e-9)].groupby(KEY, sort=False).price.first()


def water(ym: str, wv: pd.DataFrame, cap: pd.Series) -> pd.Series:
    """unit -> expected water in the month, MWh: cf_s × max power × hours, every day."""
    m = wv[(wv.ym == ym) & wv.unit.isin(cap.index)]
    return (m.cf_s * m.unit.map(cap) * day_hours(m.date)).groupby(m.unit).sum()


def load_steps(ym: str) -> pd.DataFrame:
    """The month's offered hydro steps, withdrawn steps and empty steps out."""
    h = pd.read_parquet(CACHE / f"hydro_{ym}.parquet",
                        columns=["hid", "date", "unit", "group", "cls", "price", "mw", "mw_below", "cap_mw",
                                 "cleared_mw", "withdrawn"])
    h = h[~h.withdrawn & (h.mw > 0)].drop(columns="withdrawn")
    h["date"] = pd.to_datetime(h.date)
    return h


def build_month(ym: str, wv: pd.DataFrame, h: pd.DataFrame | None = None) -> pd.DataFrame:
    """The unit × hour rows of one month; `h` replaces the offered steps (the code check)."""
    h = load_steps(ym) if h is None else h
    h = h.drop(columns=["mw_below"], errors="ignore").merge(wv[["unit", "date", "cf_s", "lam30s", "storage", "fill", "zero_share"]], on=["unit", "date"],
                how="inner")
    h = h.sort_values([*KEY, "price"], kind="stable")
    g = h.groupby(KEY, sort=False)
    h["cum_mw"] = g.mw.cumsum()
    h["offered_mw"] = g.mw.transform("sum")
    h["cum_share"] = h.cum_mw / h.offered_mw
    u = g.agg(date=("date", "first"), cls=("cls", "first"), offered_mw=("mw", "sum"), cap_mw=("cap_mw", "max"),
              cleared_mw=("cleared_mw", "first"), n_steps=("mw", "size"), n_prices=("price", "nunique"),
              cf_s=("cf_s", "first"), lam30s=("lam30s", "first"), storage=("storage", "first"),
              fill=("fill", "first"), zero_share=("zero_share", "first")).reset_index()
    u["mw_le_lam"] = h[h.price <= h.lam30s].groupby(KEY, sort=False).mw.sum().reindex(
        pd.MultiIndex.from_frame(u[KEY])).fillna(0.0).to_numpy()

    # the month: expected water net of bilateral contracts, over the volume offered (MWh: hourly)
    cap = u.groupby("unit").cap_mw.max()
    wat = water(ym, wv, cap)
    b = bilateral(ym, cap.index.tolist())
    bil = b.groupby("unit").bil.sum().reindex(wat.index).fillna(0.0)
    off = u.groupby("unit").offered_mw.sum()
    u["r_net"] = u.unit.map((wat - bil) / off)
    u["contracted"] = u.unit.map(bil / wat)
    u["q_star"] = u.cf_s * u.unit.map(u.groupby("unit").offered_mw.mean())
    u["short"] = u.offered_mw < u.q_star

    h = h.merge(u[[*KEY, "r_net", "q_star"]], on=KEY, how="left")
    h["r_cf"] = h.cf_s
    h["r_bot"] = BOTTOM
    for k in GRID:
        h[f"r_k{int(round(k * 100)):03d}"] = h.cf_s * k
    reads = {"p_cf": "r_cf", "p_bot": "r_bot", "p_net": "r_net"} | {
        f"p_k{int(round(k * 100)):03d}": f"r_k{int(round(k * 100)):03d}" for k in GRID}
    idx = pd.MultiIndex.from_frame(u[KEY])
    for name, col in reads.items():
        u[name] = read_share(h, col).reindex(idx).to_numpy()
    mw = h[h.cum_mw >= h.q_star - 1e-6].groupby(KEY, sort=False).price.first()
    u["p_mw"] = mw.reindex(idx).to_numpy()
    u.loc[u.short, "p_mw"] = np.nan

    # the stake at cost, the at-cost price, the clearing price
    c = pd.read_parquet(CACHE / f"hcompcost_{ym}.parquet", columns=["hid", "group", "unit", "kn_sn", "kn_s", "kb_sn",
                                                                     "kb_s"]).drop_duplicates(KEY)
    u = u.merge(c, on=KEY, how="left")
    u["Zb"] = np.where(u.kb_s / NEAR >= sh.FLOOR, u.kb_sn / u.kb_s.where(u.kb_s > 0), np.nan)
    u["Zc"] = np.where(u.kn_s / NEAR >= sh.FLOOR, u.kn_sn / u.kn_s.where(u.kn_s > 0), np.nan)
    u = u.drop(columns=["kn_sn", "kn_s", "kb_sn", "kb_s"])
    cp = pd.read_parquet(CACHE / f"hcompcostprice_{ym}.parquet", columns=["hid", "group", "cp_mean"])
    u = u.merge(cp.drop_duplicates(["hid", "group"]), on=["hid", "group"], how="left")
    u["rel"] = u.cp_mean / u.lam30s
    hrs = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "period", "utc", "p_clear"])
    u = u.merge(hrs, on="hid", how="left")
    u["ym"] = ym
    return u


def water_values() -> pd.DataFrame:
    wv = pd.read_parquet(WV, columns=["unit", "date", "cf_s", "lam30s", "storage", "fill"])
    wv["date"] = pd.to_datetime(wv.date)
    zc = pd.read_parquet(COST, columns=["unit", "date", "zero_share"])
    zc["date"] = pd.to_datetime(zc.date)
    wv = wv.merge(zc, on=["unit", "date"], how="left")
    wv["ym"] = wv.date.dt.strftime("%Y%m")
    return wv


def build(months: list[str] | None) -> int:
    wv = water_values()
    files = sorted(CACHE.glob("hydro_2*.parquet"))
    yms = [f.stem.split("_")[1] for f in files]
    for ym in yms:
        if months and ym not in months:
            continue
        u = build_month(ym, wv)
        u.to_parquet(CACHE / f"fixed_step_{ym}.parquet", index=False)
        s = u[(u.cls == "hydro") & (u.zero_share.fillna(0) <= ZERO_SHARE_MAX)]
        print(f"{ym}: {len(u):,} unit-hours ({u.unit.nunique()} units); storage kept {len(s):,}: read at cf_s "
              f"{s.p_cf.notna().mean():.3f}, Zb {s.Zb.notna().mean():.3f}, rel ≥ {IN_PLAY} "
              f"{(s.rel >= IN_PLAY).mean():.3f}, median p_cf / λ* {(s.p_cf / s.lam30s).median():.3f}", flush=True)
    return 0


def describe(s: pd.DataFrame) -> dict:
    main = s.Zb.notna() & (s.rel >= IN_PLAY)
    m = s[main]
    q = lambda x: float(np.nanmedian(x)) if len(x) else np.nan  # noqa: E731
    return {"units": s.unit.nunique(), "gw": s.groupby("unit").cap_mw.max().sum() / 1000,
            "unit_hours": len(s), "main_rows": int(main.sum()),
            "one_price": (s.n_prices == 1).mean(), "steps_median": s.n_steps.median(),
            "cf_s": s.cf_s.median(), "offered_over_cap": (s.offered_mw / s.cap_mw).median(),
            "le_lam_over_offered": (s.mw_le_lam / s.offered_mw).median(),
            "zb_defined": s.Zb.notna().mean(), "zb_pos": (s.Zb > 0).mean(),
            "rel_below": (s.rel < IN_PLAY).mean(), "rel_play": ((s.rel >= IN_PLAY) & (s.rel <= 1.1)).mean(),
            "rel_above": (s.rel > 1.1).mean(),
            "net_defined": s.p_net.notna().mean(), "mw_defined": s.p_mw.notna().mean(),
            "contracted": s.drop_duplicates(["unit", "ym"]).contracted.median(),
            "lam": q(m.lam30s),
            "cf_over_lam": q(m.p_cf / m.lam30s), "bot_over_lam": q(m.p_bot / m.lam30s),
            **{f"k{c[3:]}_over_lam": q(m[c] / m.lam30s) for c in s.columns if c.startswith("p_k")},
            "net_over_lam": q(m.p_net / m.lam30s), "mw_over_lam": q(m.p_mw / m.lam30s),
            "cf_gap": q(m.p_cf - m.lam30s), "cf_minus_clear": q(m.p_cf - m.p_clear),
            "cf_within10_clear": ((m.p_cf - m.p_clear).abs() <= 10).mean() if len(m) else np.nan}


def summarise() -> int:
    d = pd.concat([pd.read_parquet(f) for f in sorted(CACHE.glob("fixed_step_2*.parquet"))], ignore_index=True)
    d["year"] = d.date.dt.year
    keep = d.zero_share.fillna(0) <= ZERO_SHARE_MAX
    print(f"{len(d):,} unit-hours, {d.unit.nunique()} units, {d.ym.nunique()} months; "
          f"zero_share ≤ {ZERO_SHARE_MAX}: {keep.mean():.3f} of rows")
    rows = []
    for (yr, cls), s in d[keep].groupby(["year", "cls"]):
        rows.append({"table": "by year", "key": f"{yr} {cls}"} | describe(s))
    st = d[keep & (d.cls == "hydro")]
    rows.append({"table": "by year", "key": "all storage"} | describe(st))
    for grp, s in st.groupby("group"):
        if s.unit.nunique() and len(s) >= 5000:
            rows.append({"table": "by group, storage", "key": grp} | describe(s))
    out = d[~keep & (d.cls == "hydro")]
    mostly = out.unit.value_counts() / d[d.cls == "hydro"].unit.value_counts().reindex(out.unit.unique())
    rows.append({"table": "left out", "key": "storage unit-days, zero_share > 0.5"} | describe(out))
    rows.append({"table": "left out", "key": "units out on most days"} | describe(out[out.unit.isin(mostly.index[mostly > 0.5])]))
    # who forms each side of the stake on the main sample
    m = st[st.Zb.notna() & (st.rel >= IN_PLAY)]
    for side, s in [("seller side (Zb > 0)", m[m.Zb > 0]), ("buyer side (Zb < 0)", m[m.Zb < 0])]:
        sh_ = s.group.value_counts(normalize=True)
        rows.append({"table": "side by group, main", "key": side, "units": s.unit.nunique(), "unit_hours": len(s)}
                    | {f"share_{g}": v for g, v in sh_.items() if v >= 0.005})
    t = pd.DataFrame(rows)
    t.to_csv(SUMMARY, index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    cols1 = ["table", "key", "units", "gw", "unit_hours", "main_rows", "one_price", "steps_median", "cf_s",
             "offered_over_cap", "le_lam_over_offered", "zb_defined", "zb_pos", "rel_below", "rel_play", "rel_above",
             "net_defined", "mw_defined", "contracted"]
    cols2 = ["table", "key", "lam", "cf_over_lam", "bot_over_lam"] + [c for c in t.columns if c[:2] in ("k0", "k1", "k2")] + [
        "net_over_lam", "mw_over_lam", "cf_gap", "cf_minus_clear", "cf_within10_clear"]
    print("\nCOVERAGE (all unit-hours of each cell):")
    print(t[~t.table.str.startswith("side")][cols1].round(3).to_string(index=False))
    print(f"\nREADS OVER λ*30s, medians on the main sample (Zb defined, at-cost price ≥ {IN_PLAY} λ*):")
    print(t[~t.table.str.startswith("side")][cols2].round(3).to_string(index=False))
    print("\nWHO FORMS EACH SIDE (main sample, share of unit-hours):")
    sc = ["key", "units", "unit_hours"] + [c for c in t.columns if c.startswith("share_")]
    print(t[t.table.str.startswith("side")][sc].round(3).dropna(axis=1, how="all").to_string(index=False))
    print(f"\nwrote {SUMMARY.relative_to(ROOT)}")
    return 0


# ---- step 2: the estimates --------------------------------------------------------------------
RESULTS = TABLES / "fixed_step_results.csv"
ZERO2 = CACHE / "fixed_step_zero2.parquet"
ZERO_PRICE = 2.0             # €/MWh: offers at or below it count as zero-priced (step 1, call 1)
DELTA = 0.1                  # price-taking accepted if the 95% set lies within ±δ (simulation note §7)
PLACEBO_TO = "2023-01-01"    # from 2023 the bottom step itself sits above λ* (step 1, call 3)
MIN_ROWS = 5000
DEPARTURE = ("2021-07-01", "2024-01-01")     # departure periods: before the first date, from the second
HALF_YEARS = [f"{y}H{h}" for y in range(2019, 2026) for h in (1, 2)][:-1]     # 2025-07 → 09 partial
READS = {"cf_s": "p_cf", "bottom 5%": "p_bot", "0.1 cf_s": "p_k010", "0.25 cf_s": "p_k025",
         "0.5 cf_s": "p_k050", "1.5 cf_s": "p_k150", "2 cf_s": "p_k200", "net of contracts": "p_net",
         "fixed MW": "p_mw"}
FIRMS = ("EDP", "IBERDROLA")


def zero_shares() -> pd.DataFrame:
    """unit, ym, zero2: the share of the unit's offered hydro MW in the month at or below ZERO_PRICE."""
    if ZERO2.exists():
        return pd.read_parquet(ZERO2)
    parts = []
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        h = pd.read_parquet(f, columns=["unit", "price", "mw", "withdrawn"])
        h = h[~h.withdrawn & (h.mw > 0)]
        z = h.assign(low=h.mw.where(h.price <= ZERO_PRICE, 0.0)).groupby("unit")[["low", "mw"]].sum()
        parts.append(pd.DataFrame({"unit": z.index, "ym": f.stem.split("_")[1], "zero2": (z.low / z.mw).to_numpy()}))
    z = pd.concat(parts, ignore_index=True)
    z.to_parquet(ZERO2, index=False)
    return z


def load_rows(pattern: str = "fixed_step_2*.parquet") -> pd.DataFrame:
    """Step 1's rows, zero-priced unit-months out (actual offers decide, also for the simulated
    rows), with the outcomes: g_<read> = read − λ*30s; q_offered, q_le_lam over capacity."""
    d = pd.concat([pd.read_parquet(f) for f in sorted(CACHE.glob(pattern))], ignore_index=True)
    d = d.merge(zero_shares(), on=["unit", "ym"], how="left")
    d = d[(d.zero_share.fillna(0) <= ZERO_SHARE_MAX) & (d.zero2.fillna(0) <= ZERO_SHARE_MAX)].copy()
    for c in READS.values():
        d[f"g_{c}"] = d[c] - d.lam30s
    d["q_offered"] = d.offered_mw / d.cap_mw
    d["q_le_lam"] = d.mw_le_lam / d.cap_mw
    d["P_rel"] = d.cp_mean - d.lam30s
    d["half"] = d.date.dt.year.astype(str) + np.where(d.date.dt.month <= 6, "H1", "H2")
    d["per"] = np.where((d.date < DEPARTURE[0]) | (d.date >= DEPARTURE[1]), "departure", "crisis")
    d["week"] = d.date.dt.strftime("%G%V")
    return d


def fe_codes(s: pd.DataFrame, fe: str) -> list[np.ndarray]:
    hour = pd.factorize(s.cls + s.hid.astype(str))[0]
    um = pd.factorize(s.unit + s.ym)[0]
    if fe == "unit × month":
        return [um, hour]
    if fe == "unit × day":
        return [pd.factorize(s.unit + s.date.dt.strftime("%Y%m%d"))[0], hour]
    if fe == "unit × month, unit × hour of day":
        return [um, hour, pd.factorize(s.unit + "|" + s.period.astype(str))[0]]
    raise ValueError(fe)


def est(s: pd.DataFrame, block: str, cell: str, y: str = "g_p_cf", xs: tuple = ("Zb",),
        fe: str = "unit × month", slopes: tuple = (), tests: tuple = ()) -> list[dict]:
    """Least squares of y on xs (the at-cost stake, no instrument: Zb is fixed before the auction
    and nothing selects the rows) with the fixed effects `fe` and a slope per unit on `slopes`;
    clusters by week. One row per regressor; `tests` (name, a, b) adds p(b_a = b_b)."""
    s = s.dropna(subset=[y, *xs, *slopes])
    s = s[np.isfinite(s[[y, *xs, *slopes]].to_numpy(float)).all(axis=1)]
    base = {"block": block, "cell": cell, "y": y, "fe": fe, "slopes": ", ".join(slopes), "n": len(s),
            "units": s.unit.nunique(), "groups": s.group.nunique()}
    if len(s) < MIN_ROWS:
        print(f"  {block:18s} {cell:34s} {y:9s} too few rows ({len(s):,})", flush=True)
        return [base | {"x": "+".join(xs), "status": "too few rows"}]
    w = np.ones(len(s))
    codes = with_slopes(fe_codes(s, fe), s, list(slopes), w)
    M = wdemean(s[[y, *xs]].to_numpy(float), codes, w)
    Y, X = M[:, 0], M[:, 1:]
    live = [j for j in range(X.shape[1]) if np.abs(X[:, j]).sum() > 1e-9]
    X = X[:, live]
    names = [xs[j] for j in live]
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ Y
    V = inv @ cluster_meat(X, Y - X @ b, s.week.to_numpy()) @ inv
    out, txt = [], []
    for j, xn in enumerate(names):
        se = float(np.sqrt(V[j, j]))
        lo, hi = b[j] - 1.96 * se, b[j] + 1.96 * se
        nz = s[xn] != 0
        out.append(base | {"x": xn, "n_x": int(nz.sum()), "mean_x": s.loc[nz, xn].mean(), "sd_x": s.loc[nz, xn].std(),
                           "mean_y": s[y].mean(), "b": b[j], "se": se, "lo": lo, "hi": hi,
                           "differs": bool(lo > 0 or hi < 0), "accepted": bool(lo >= -DELTA and hi <= DELTA),
                           "status": "ok"})
        txt.append(f"{xn} {b[j]:+.3f} [{lo:+.2f}, {hi:+.2f}]")
    for name, a, c in tests:
        if a in names and c in names:
            i, k = names.index(a), names.index(c)
            dl = b[i] - b[k]
            sd = np.sqrt(V[i, i] + V[k, k] - 2 * V[i, k])
            p = float(2 * (1 - __import__("scipy.stats").stats.norm.cdf(abs(dl / sd))))
            out.append(base | {"x": f"test: {name}", "b": dl, "se": sd, "p": p, "status": "ok"})
            txt.append(f"p({name}) {p:.3g}")
    print(f"  {block:18s} {cell:34s} {y:9s} n={len(s):>9,}  " + "  ".join(txt), flush=True)
    return out


def within_firm(m: pd.DataFrame) -> tuple[pd.DataFrame, tuple, tuple]:
    """Zb split by firm (EDP, Iberdrola, the rest) and side, for one regression on all rows: the
    class × hour effects come from every firm, which a regression on one firm cannot have (its
    Zb is one value per hour)."""
    m = m.copy()
    xs, tests = [], []
    for g in (*FIRMS, "others"):
        own = ~m.group.isin(FIRMS) if g == "others" else m.group == g
        for side, sel in (("seller", m.Zb > 0), ("buyer", m.Zb < 0)):
            c = f"Zb {g} {side}"
            m[c] = m.Zb.where(own & sel, 0.0)
            xs.append(c)
        tests.append((f"{g} seller = buyer", f"Zb {g} seller", f"Zb {g} buyer"))
    return m, tuple(xs), tuple(tests)


def cells(d: pd.DataFrame, tag: str = "", full: bool | None = None) -> list[dict]:
    """Every cell of step 2. With a tag and no `full`, the main cells only (the code check)."""
    full = not tag if full is None else full
    st = d[d.cls == "hydro"]
    main = st[st.Zb.notna() & (st.rel >= IN_PLAY)]
    pre = f"{tag}" if tag else ""
    res = []
    res += est(main, pre + "main", "pooled")
    for per in ("departure", "crisis"):
        res += est(main[main.per == per], pre + "period", per)
    sides = {"seller side": main.Zb > 0, "buyer side": main.Zb < 0}
    for side, sel in sides.items():
        res += est(main[sel], pre + "side", f"{side} | pooled")
        for per in ("departure", "crisis"):
            res += est(main[sel & (main.per == per)], pre + "side", f"{side} | {per}")
    wf, xs, tests = within_firm(main)
    res += est(wf, pre + "within firm", "pooled", xs=xs, tests=tests)
    for per in ("departure", "crisis"):
        res += est(wf[wf.per == per], pre + "within firm", per, xs=xs, tests=tests)
    if not full:                                # the code check: the main cells only
        return res
    for hy in HALF_YEARS:
        res += est(main[main.half == hy], "half-year", hy)
        for side, sel in sides.items():
            res += est(main[sel & (main.half == hy)], "side × half-year", f"{side} | {hy}")
    for lab, c in READS.items():
        if lab in ("net of contracts", "fixed MW"):
            continue
        for per, s in (("pooled", main), ("departure", main[main.per == "departure"]),
                       ("crisis", main[main.per == "crisis"])):
            res += est(s, "profile", f"{lab} | {per}", y=f"g_{c}")
    res += est(main[main.date < PLACEBO_TO], "placebo", "bottom 5% | 2019–2022", y="g_p_bot")
    res += est(main[main.date >= PLACEBO_TO], "placebo", "bottom 5% | 2023–2025 (caveat)", y="g_p_bot")
    res += est(main[main.date >= PLACEBO_TO], "placebo", "0.1 cf_s | 2023–2025 (caveat)", y="g_p_k010")
    allh = st[st.Zb.notna()]
    res += est(allh, "bands", "all hours")
    for lab, sel in (("at-cost price < 0.9 λ*", allh.rel < IN_PLAY),
                     ("0.9–1.1 λ*", (allh.rel >= IN_PLAY) & (allh.rel <= 1.1)), ("> 1.1 λ*", allh.rel > 1.1)):
        res += est(allh[sel], "bands", lab)
    for per, s in (("pooled", main), ("departure", main[main.per == "departure"]),
                   ("crisis", main[main.per == "crisis"])):
        res += est(s, "check", f"net of contracts | {per}", y="g_p_net")
        res += est(s, "check", f"fixed MW | {per}", y="g_p_mw")
        res += est(s, "check", f"unit × day | {per}", y="p_cf", fe="unit × day")
        res += est(s, "check", f"+ unit × hour of day | {per}", fe="unit × month, unit × hour of day")
        res += est(s, "check", f"level control | {per}", slopes=("P_rel",))
        res += est(s, "check", f"offered / capacity | {per}", y="q_offered")
        res += est(s, "check", f"MW ≤ λ* / capacity | {per}", y="q_le_lam")
    pm = d[(d.cls == "pumped") & d.Zb.notna() & (d.rel >= IN_PLAY)]
    res += est(pm, "pumped", "pooled")
    for per in ("departure", "crisis"):
        res += est(pm[pm.per == per], "pumped", per)
    return res


def estimate() -> int:
    d = load_rows()
    st = d[d.cls == "hydro"]
    print(f"{len(d):,} rows after zero-priced unit-months (≤ €{ZERO_PRICE:.0f}) are out; storage {len(st):,}, "
          f"main {(st.Zb.notna() & (st.rel >= IN_PLAY)).sum():,}", flush=True)
    t = pd.DataFrame(cells(d))
    t.to_csv(RESULTS, index=False)
    show(t)
    print(f"\nwrote {RESULTS.relative_to(ROOT)}")
    return 0


def show(t: pd.DataFrame) -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    cols = ["block", "cell", "y", "x", "n", "units", "mean_x", "sd_x", "b", "se", "lo", "hi", "differs", "accepted", "p"]
    print(t[[c for c in cols if c in t]].round(3).to_string(index=False))


def simulated(seed: int) -> int:
    """The code check: price-takers at λ*30s (`step_engine.simulate`, the same seeds as the
    simulation note, steps above €1 moved as the engine moves them), read the same way. No
    re-clearing: Zb, the at-cost price and the reads' positions do not depend on own prices."""
    from step_engine import MIN_PRICE_HYDRO, simulate
    from step_estimator_hydro import flat_days
    wv = water_values()
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        ym = f.stem.split("_")[1]
        out = CACHE / f"fixed_step_sim{seed}_{ym}.parquet"
        if out.exists():
            continue
        raw = pd.read_parquet(f)
        raw["date"] = raw.date.astype("datetime64[ns]")
        flat = flat_days(raw)
        h = load_steps(ym)
        h["date"] = h.date.astype("datetime64[ns]")
        h = h.merge(wv[["unit", "date", "lam30s"]].rename(columns={"lam30s": "cost"}), on=["unit", "date"], how="left")
        move = (h.price > MIN_PRICE_HYDRO) & h.cost.notna() & h.group.notna()
        s = simulate(h[move], ym, seed, flat)
        s["price"] = s.sim.astype("float32")
        h = pd.concat([h[~move], s[h.columns]], ignore_index=True).drop(columns="cost")
        build_month(ym, wv, h).to_parquet(out, index=False)
        print(f"{ym}: simulated seed {seed}", flush=True)
    d = load_rows(f"fixed_step_sim{seed}_*.parquet")
    t = pd.DataFrame(cells(d, tag=f"sim{seed} "))
    t.assign(seed=seed).to_csv(TABLES / f"fixed_step_results_sim{seed}.csv", index=False)
    show(t)
    return 0


# ---- Iberdrola's buyer hours (rq-fixed-step.md, "Next") ----------------------------------------
DOSE = TABLES / "reactor_outage_dose.parquet"
EXO_DOSE = ("planned", "unplanned")          # undeclared and economic cuts are choices, not shifts
OWNERS = ("IBERDROLA", "ENDESA", "NATURGY", "EDP")


def stake_parts(d: pd.DataFrame) -> pd.DataFrame:
    """Adds the two parts of Zb = n / |RD′| (both over the NEAR draws nearest the class's cost
    point, `hcompcost`): n_gw, the firm's net position there (GW), and slope (MW per €/MWh);
    and the firm's reactor-outage dose (planned and unplanned, owner's share): D (GW) and
    P = dose / slope (€/MWh), the Cournot markdown the lost output implies."""
    c = pd.concat([pd.read_parquet(f, columns=["hid", "group", "unit", "kb_sn", "kb_s"])
                   for f in sorted(CACHE.glob("hcompcost_2*.parquet"))], ignore_index=True)
    c = c.drop_duplicates(["hid", "group", "unit"])
    c["n_gw"] = c.kb_sn / NEAR / 1000
    c["slope"] = c.kb_s / NEAR
    d = d.merge(c[["hid", "group", "unit", "n_gw", "slope"]], on=["hid", "group", "unit"], how="left")
    z = pd.read_parquet(DOSE)
    z = z[z.cls.isin(EXO_DOSE)].groupby(["firm", "utc"]).lost_mw.sum().rename("dose_mw").reset_index()
    z["utc"] = z.utc.astype("datetime64[ns, UTC]")
    d["utc"] = d.utc.astype("datetime64[ns, UTC]")
    d = d.merge(z.rename(columns={"firm": "group"}), on=["group", "utc"], how="left")
    d["dose_mw"] = d.dose_mw.fillna(0.0)
    d["D"] = d.dose_mw / 1000
    d["P"] = d.dose_mw / d.slope.where(d.slope >= sh.FLOOR)
    return d


def iberdrola_cells(d: pd.DataFrame, tag: str) -> list[dict]:
    st = d[d.cls == "hydro"]
    m = stake_parts(st[st.Zb.notna() & (st.rel >= IN_PLAY)])
    res = []
    # (a) the stake split into position and slope: Zb and n by firm and side, one regression
    xz, xn, tests = [], [], []
    for g in (*FIRMS, "others"):
        own = ~m.group.isin(FIRMS) if g == "others" else m.group == g
        for side, sel in (("seller", m.Zb > 0), ("buyer", m.Zb < 0)):
            m[f"Zb {g} {side}"] = m.Zb.where(own & sel, 0.0)
            xz.append(f"Zb {g} {side}")
            if g != "others":
                m[f"n {g} {side}"] = m.n_gw.where(own & sel, 0.0)
                xn.append(f"n {g} {side}")
    zonly = [c for c in xz if not c.startswith("Zb IBERDROLA") and not c.startswith("Zb EDP")]
    yr = m.date.dt.year
    for lab, s in (("pooled", m), ("2019", m[yr == 2019]), ("2023", m[yr == 2023]),
                   ("other years", m[~yr.isin([2019, 2023])])):
        res += est(s, f"{tag}position and slope", f"Zb and n | {lab}", xs=tuple(xz + xn))
        res += est(s, f"{tag}position and slope", f"n only | {lab}", xs=tuple(zonly + xn))
    # (b) the reactor dose: a shift in n that leaves the slope of the firm's residual demand alone
    xd = []
    for g in OWNERS:
        for v in ("D", "P"):
            m[f"{v} {g}"] = m[v].where(m.group == g, 0.0).fillna(0.0)
            xd.append(f"{v} {g}")
    xd_d = [c for c in xd if c.startswith("D ")]
    for lab, s in (("pooled", m), ("departure", m[m.per == "departure"]), ("crisis", m[m.per == "crisis"])):
        res += est(s, f"{tag}reactor dose", f"D and P | {lab}", xs=tuple(xd))
        res += est(s, f"{tag}reactor dose", f"D only | {lab}", xs=tuple(xd_d))
    res += est(m, f"{tag}reactor dose", "first stage: n on D | pooled", y="n_gw", xs=tuple(xd_d))
    # (c) the high 2023 half-years without Iberdrola
    for hy in ("2023H1", "2023H2"):
        res += est(m[m.half == hy], f"{tag}2023", f"{hy} | all firms")
        res += est(m[(m.half == hy) & (m.group != "IBERDROLA")], f"{tag}2023", f"{hy} | without Iberdrola")
    return res


def iberdrola() -> int:
    out = []
    for seed, pattern in ((0, "fixed_step_2*.parquet"), (1, "fixed_step_sim1_*.parquet"),
                          (2, "fixed_step_sim2_*.parquet")):
        print(f"\n=== {'ACTUAL OFFERS' if seed == 0 else f'SEED {seed}: simulated price-takers'} ===", flush=True)
        out += [r | {"seed": seed} for r in iberdrola_cells(load_rows(pattern), "")]
    t = pd.DataFrame(out)
    t.to_csv(TABLES / "fixed_step_iberdrola.csv", index=False)
    show(t)
    print(f"\nwrote {(TABLES / 'fixed_step_iberdrola.csv').relative_to(ROOT)}")
    return 0


# ---- the after-auction contracts, and the band over every seed -------------------------------
BILATERAL = CACHE / "fixed_step_bilateral.parquet"
PDBF = ROOT / "data/omie/pdbf/parquet"


def bilateral_hours() -> pd.DataFrame:
    """unit, date, period, bil_mw: what each hydro unit of the rows delivers in the hour under
    bilateral contracts (PDBF role 4, which may be nominated up to 13:00 on D−1, after the
    day-ahead results: `rq-midday-hydro.md` §3.8). Quarter-hours from 2025-03-19 are summed to
    the hour's MWh, i.e. its mean MW. Cached."""
    if BILATERAL.exists():
        return pd.read_parquet(BILATERAL)
    units = sorted(set().union(*[set(pd.read_parquet(f, columns=["unit"]).unit)
                                 for f in sorted(CACHE.glob("fixed_step_2*.parquet"))]))
    yms = {f.stem.split("_")[1] for f in CACHE.glob("hydro_2*.parquet")}
    parts = []
    for f in sorted(PDBF.glob("pdbf_*.parquet")):
        if f.stem.split("_")[1] not in yms:
            continue
        p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"],
                            filters=[("unit", "in", units), ("role_code", "==", "4")])
        if p.empty:
            continue
        hour = np.where(p.resolution_min == 15, (p.period.astype(int) + 3) // 4, p.period.astype(int))
        p = p.assign(period=hour, mwh=p.schedule_mw * p.resolution_min / 60)
        parts.append(p.groupby(["unit", "date", "period"], as_index=False).mwh.sum().rename(columns={"mwh": "bil_mw"}))
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b.date).astype("datetime64[ns]")
    b.to_parquet(BILATERAL, index=False)
    return b


def with_bilateral(m: pd.DataFrame) -> pd.DataFrame:
    m = m.assign(period=m.period.astype(int), date=m.date.astype("datetime64[ns]"))
    b = bilateral_hours().assign(date=lambda x: x.date.astype("datetime64[ns]"))
    m = m.merge(b, on=["unit", "date", "period"], how="left")
    m["bil_mw"] = m.bil_mw.fillna(0.0)
    return m


def routing_cells(d: pd.DataFrame, quantities: bool = True) -> list[dict]:
    """Is Iberdrola's buyer-hour markdown hydro moved between its own retailer (bilateral, after
    the auction) and the auction? If so, its bilateral delivery falls in the hours its auction
    ladder gets longer and cheaper, its total hydro schedule barely moves, and controlling for
    the bilateral share removes the markdown. Quantities are actual behaviour, the same in every
    seed, so only the gap cells are run on the simulated rows."""
    st = d[d.cls == "hydro"]
    m = with_bilateral(st[st.Zb.notna() & (st.rel >= IN_PLAY)])
    m["q_bil"] = m.bil_mw / m.cap_mw
    m["q_cleared"] = m.cleared_mw / m.cap_mw
    m["q_total"] = (m.cleared_mw + m.bil_mw) / m.cap_mw
    wf, xs, tests = within_firm(m)
    yr = wf.date.dt.year
    res = []
    for lab, s in (("pooled", wf), ("2019", wf[yr == 2019]), ("2023", wf[yr == 2023])):
        if quantities:
            for y in ("q_bil", "q_cleared", "q_total"):
                res += est(s, "routing", f"{y} | {lab}", y=y, xs=xs, tests=tests)
        res += est(s, "routing", f"gap | {lab}", xs=xs, tests=tests)
        res += est(s, "routing", f"gap, bilateral share held | {lab}", xs=(*xs, "q_bil"), tests=tests)
    return res


def routing_describe(d: pd.DataFrame) -> None:
    """Iberdrola's and EDP's buyer hours in fifths of the stake, within unit-month: bilateral,
    offered, cleared and total MW, and the gap."""
    st = d[d.cls == "hydro"]
    m = with_bilateral(st[st.Zb.notna() & (st.rel >= IN_PLAY)])
    m["total_mw"] = m.cleared_mw + m.bil_mw
    pd.set_option("display.width", 250)
    for g in FIRMS:
        x = m[m.group == g].copy()
        print(f"\n{g}: bilateral share of its hydro schedule by year:",
              (x.groupby(x.date.dt.year).bil_mw.sum() / x.groupby(x.date.dt.year).total_mw.sum()).round(2).to_dict())
        cols = ["Zb", "g_p_cf", "bil_mw", "offered_mw", "cleared_mw", "total_mw"]
        for c in cols:
            x[c + "_d"] = x[c] - x.groupby(["unit", "ym"])[c].transform("mean")
        b = x[x.Zb < 0].copy()
        b["fifth"] = pd.qcut(b.Zb_d.rank(method="first"), 5, labels=["most buying", "2nd", "3rd", "4th", "least buying"])
        print(b.groupby("fifth", observed=True)[[c + "_d" for c in cols]].mean().round(2).to_string())


def band_seed(seed: int) -> int:
    """All of step 2's cells, the Iberdrola check and the routing gap cells for one seed (0 = the
    actual offers), cached for `--band-combine`."""
    pattern = "fixed_step_2*.parquet" if seed == 0 else f"fixed_step_sim{seed}_*.parquet"
    d = load_rows(pattern)
    if seed == 0:
        routing_describe(d)
    res = cells(d, "", full=True) + iberdrola_cells(d, "") + routing_cells(d, quantities=seed == 0)
    pd.DataFrame([r | {"seed": seed} for r in res]).to_csv(CACHE / f"fixed_step_band_s{seed}.csv", index=False)
    print(f"seed {seed}: {len(res)} rows", flush=True)
    return 0


def band_combine() -> int:
    """Actual against every simulated seed on disk, by the simulation note's rule: differs when
    the 95% interval misses the seeds' range; bias-adjusted range [low − seed max, high − seed
    min]; price-taking accepted when that range lies within ±δ."""
    parts = [pd.read_csv(f) for f in sorted(CACHE.glob("fixed_step_band_s*.csv"))]
    t = pd.concat(parts, ignore_index=True)
    t = t[(t.status == "ok") & ~t.x.astype(str).str.startswith("test")]
    key = ["block", "cell", "y", "x"]
    a = t[t.seed == 0].set_index(key)[["n", "b", "se", "lo", "hi"]]
    s = t[t.seed > 0].groupby(key).b.agg(seeds="count", null_lo="min", null_hi="max", null_mean="mean", null_sd="std")
    r = a.join(s, how="left").reset_index()
    r["gap"] = r.b - r.null_mean
    r["adj_lo"], r["adj_hi"] = r.lo - r.null_hi, r.hi - r.null_lo
    r["differs"] = (r.lo > r.null_hi) | (r.hi < r.null_lo)
    r["accepted"] = (r.adj_lo >= -DELTA) & (r.adj_hi <= DELTA)
    out = TABLES / "fixed_step_band_reading.csv"
    r.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 600)
    print(f"seeds: {sorted(t[t.seed > 0].seed.unique())}")
    print(r[["block", "cell", "y", "x", "n", "b", "lo", "hi", "seeds", "null_lo", "null_hi", "null_mean", "gap",
             "adj_lo", "adj_hi", "differs", "accepted"]].round(3).to_string(index=False))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="step 1: the unit × hour rows, one cache file a month")
    ap.add_argument("--months", nargs="+", help="with --build: only these months (YYYYMM)")
    ap.add_argument("--summarise", action="store_true", help="step 1: coverage and reads by year, class and group")
    ap.add_argument("--estimate", action="store_true", help="step 2: every cell, profile and check")
    ap.add_argument("--simulated", type=int, metavar="SEED", help="step 2: the code check on simulated price-takers")
    ap.add_argument("--band-seed", type=int, metavar="SEED", help="every cell for one seed (0 = actual), for --band-combine")
    ap.add_argument("--band-combine", action="store_true", help="actual against every simulated seed on disk")
    ap.add_argument("--iberdrola", action="store_true", help="Iberdrola's buyer hours: the stake split into position "
                    "and slope, the reactor dose, 2023 without Iberdrola (actual and both simulated seeds)")
    args = ap.parse_args()
    if args.build:
        return build(args.months)
    if args.summarise:
        return summarise()
    if args.estimate:
        return estimate()
    if args.simulated is not None:
        return simulated(args.simulated)
    if args.iberdrola:
        return iberdrola()
    if args.band_seed is not None:
        return band_seed(args.band_seed)
    if args.band_combine:
        return band_combine()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
