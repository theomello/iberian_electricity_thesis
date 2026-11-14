"""Price effect of the time-of-use load shift (docs/specs/2026-11-13-tou-price-effect-design.md).

For each valid weekday hour of the reform window the day-ahead price is re-cleared on the day's effective offer curve (outputs/cache/step) with the demand
the reform removed or added put back: counterfactual demand = actual E0 load x exp(-(b_type + c)) in MW, b_type the period-type DiD effect of E0 against Portugal's
consumption (paper LASSO errors), c a level common to all hours (energy-neutral per day by default; the REN level and the regulated-unit level as sensitivities).
The counterfactual price is the first price on the curve at which cumulative supply-side volume reaches d_tot + extra demand (step_curves.reclear's identity), the
buy side being moved horizontally. Price effect = actual re-cleared price minus counterfactual price. Writes outputs/tables/tou_price_effect_*.csv and prints R1-R5.

Reusable: the window, the period types, the control and the level rule are parameters of the functions below.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

POST0, POST1 = AP.POST0, AP.POST1
STEP = T.ROOT / "outputs" / "cache" / "step"
CACHE = T.ROOT / "data" / "cache_tou" / "price_effect_e0_errors.parquet"
OUT = T.OUT
NDRAW, SEED = 2000, 20261113
EVENING, NIGHT = [18, 19, 20, 21], list(range(8))
PEAK_H = [10, 11, 12, 13, 18, 19, 20, 21]
TY = ["wd_peak", "wd_mid", "wd_off"]
PLACEBO_STARTS = list(pd.date_range("2019-01-01", "2019-09-01", freq="MS"))


def type_of(h):
    return np.where(h < 8, 2, np.where(np.isin(h, PEAK_H), 0, 1))  # 0 peak, 1 mid, 2 off (order of TY)


# ---------------------------------------------------------------- load errors
def one_task(name, x, load, temp, hol, excl):
    xx = x[x[load] > 0]
    return name, excl, L.area_errors(xx, load, temp, hol, excl)


def get_errors(x):
    if CACHE.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for ex in ((), (2018,), (2019,)):
        tasks.append(("ES", x, "load_es", "temp_es", "hol_es", ex))
        tasks.append(("PT", x, "load_pt", "temp_pt", "hol_pt", ex))
    res = Parallel(n_jobs=4, verbose=5)(delayed(one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE)
    return errs


def effects(x, eE, eP, mask, s0, s1):
    """Period-type DiD effects (weekday) and their covariance for the window [s0, s1]."""
    S = AP.long_stack(x, {"E0": eE}, eP, ["E0"], {"E0": 1.0, "PT": 1.0}, mask)
    names, b, V = AP.did_types(S, s0, s1, True, full=True)
    i = [names.index(n) for n in TY]
    return b[i], V[np.ix_(i, i)]


# ---------------------------------------------------------------- curves
class Curves:
    """Hours table and market table of the months touched, indexed by hid."""

    def __init__(self, months):
        hs, ms = [], []
        for ym in months:
            hs.append(pd.read_parquet(STEP / f"hours_{ym}.parquet"))
            ms.append(pd.read_parquet(STEP / f"market_{ym}.parquet"))
        self.h = pd.concat(hs, ignore_index=True)
        self.h["date"] = pd.to_datetime(self.h.date)
        m = pd.concat(ms, ignore_index=True).sort_values(["hid", "price"], kind="stable")
        self.price, self.a = m.price.to_numpy(float), m.a.to_numpy(float)
        uh, st = np.unique(m.hid.to_numpy(), return_index=True)
        self.start = dict(zip(uh, st))
        self.end = dict(zip(uh, list(st[1:]) + [len(m)]))

    def clear(self, hid, target):
        s, e = self.start[hid], self.end[hid]
        idx = np.minimum(np.searchsorted(self.a[s:e], target, side="left"), e - s - 1)
        return self.price[s:e][idx]


def window_hours(x, cv, s0, s1):
    """Valid weekday hours in [s0, s1] with the E0 load, the day's totals by type, and the curve keys."""
    h = cv.h[(cv.h.date >= s0) & (cv.h.date <= s1) & cv.h.valid.astype(bool)].copy()
    h["hour"] = h.period - 1
    xl = x[["date", "hour", "load_es", "kind"]]
    h = h.merge(xl, on=["date", "hour"], how="inner")
    h = h[h.kind == "work"].copy()
    h["k"] = type_of(h.hour.to_numpy())
    # day totals by type use every hour of the day in x
    xd = x[(x.date >= s0) & (x.date <= s1) & (x.kind == "work")].copy()
    xd["k"] = type_of(xd.hour.to_numpy())
    cnt = xd.groupby("date").hour.count()
    xd = xd[xd.date.isin(cnt[cnt == 24].index)]
    LT = xd.pivot_table(index="date", columns="k", values="load_es", aggfunc="sum").reindex(columns=[0, 1, 2])
    h = h[h.date.isin(LT.index)].reset_index(drop=True)
    h["day"] = LT.index.get_indexer(h.date)
    return h, LT


def price_effect(cv, h, LT, B, mode, gap=0.0):
    """Delta p (draws x hours): actual re-cleared price minus the counterfactual price. B: draws x 3 effects in TY order."""
    if mode == "neutral":
        C = np.log(np.exp(-B) @ LT.to_numpy().T / LT.to_numpy().sum(1))     # draws x days
        c = C[:, h.day.to_numpy()]
    elif mode == "F":
        c = np.zeros((B.shape[0], len(h)))
    else:  # "M": the regulated-unit level, F level plus the replication's gap between the controls
        c = np.full((B.shape[0], len(h)), gap)
    tau = B[:, h.k.to_numpy()] + c
    X = h.load_es.to_numpy()[None, :] * (np.exp(-tau) - 1.0)                # extra demand without the reform, MW
    dt = h.d_tot.to_numpy()
    out = np.empty_like(X)
    hid = h.hid.to_numpy()
    for j in range(len(h)):
        p0 = cv.clear(hid[j], dt[j])
        out[:, j] = p0 - cv.clear(hid[j], dt[j] + X[:, j])
    return out


def stats(dp, h, sel=None):
    """Mean Delta p in the evening and at night (per draw) and their contrast."""
    s = np.ones(len(h), bool) if sel is None else sel
    ev = s & h.hour.isin(EVENING).to_numpy()
    ni = s & h.hour.isin(NIGHT).to_numpy()
    e, n = dp[:, ev].mean(1), dp[:, ni].mean(1)
    return e, n, e - n


def month_list(a, b):
    return [d.strftime("%Y%m") for d in pd.date_range(pd.Timestamp(a).replace(day=1), b, freq="MS")]


# ---------------------------------------------------------------- markup (R5)
def marginal_markup(ym, hv):
    """Markup of the marginal gas unit by valid hour: p* minus the unit's bid-time cost, steps priced at p* and accepted."""
    u = pd.read_parquet(STEP / f"units_{ym}.parquet", columns=["hid", "unit", "fuel", "price", "cost", "cleared_mw", "withdrawn"])
    h = pd.read_parquet(STEP / f"hours_{ym}.parquet", columns=["hid", "p_star"])
    u = u[(u.fuel == "gas") & (u.cleared_mw > 0) & (~u.withdrawn)].merge(h, on="hid")
    u = u[(u.price - u.p_star).abs() <= 0.05]
    return (u.assign(m=u.p_star - u.cost).groupby("hid").m.mean().rename("markup")).reset_index()


def markup_contrast(cv, x, s0, s1, months, skip=None):
    h, _ = window_hours(x, cv, s0, s1)
    if skip is not None:
        h = h[~h.date.between(*skip)]
    mk = pd.concat([marginal_markup(ym, h) for ym in months], ignore_index=True)
    g = h.merge(mk, on="hid", how="inner")
    ev = g[g.hour.isin(EVENING)].markup.mean()
    ni = g[g.hour.isin(NIGHT)].markup.mean()
    return ev - ni, len(g)


def main():
    x = D.prep(T.build("e0", end="2021-09-14"))
    errs = get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    real_mask = pre | ((x.date >= POST0) & (x.date <= POST1))
    b, V = effects(x, errs[("ES", "()")], errs[("PT", "()")], real_mask, POST0, POST1)
    print("period-type effects, weekday, E0 vs Portugal (REN), real window:", dict(zip(TY, np.round(100 * b, 2))),
          "se", np.round(100 * np.sqrt(np.diag(V)), 2), flush=True)
    pc = pd.read_csv(OUT / "tou_area_panel_pc_effects.csv")
    g = lambda spec, t: pc[(pc.spec == spec) & (pc.term == t)].iloc[0].b
    gap = float(np.mean([g("M weighted", t) - g("F REN control", t) for t in TY]))
    print(f"level gap between the regulated-unit (M) and REN (F) controls in the replication: {100 * gap:.2f} points", flush=True)

    cv = Curves(month_list("2019-01-01", "2019-12-31") + month_list("2020-07-01", "2020-09-30") + month_list("2021-06-01", "2021-09-30"))
    h, LT = window_hours(x, cv, POST0, POST1)
    allw = cv.h[(cv.h.date >= POST0) & (cv.h.date <= POST1) & (cv.h.date.dt.dayofweek < 5)]
    print(f"R1: valid weekday hours in the window {len(h)} (before the E0-day filter: {int(allw.valid.astype(bool).sum())} of {len(allw)}, "
          f"{100 * allw.valid.astype(bool).mean():.1f}%) (>= 70% needed)", flush=True)

    rng = np.random.default_rng(SEED)
    Bd = rng.multivariate_normal(b, V, size=NDRAW)
    B1 = b[None, :]
    rows, results = [], {}
    variants = {"neutral": (h, "neutral"), "F level (REN)": (h, "F"), "M level (regulated unit)": (h, "M")}
    for lab, (hh, mode) in variants.items():
        dp = price_effect(cv, hh, LT, Bd, mode, gap)
        d1 = price_effect(cv, hh, LT, B1, mode, gap)
        e, n, c = stats(dp, hh)
        e1, n1, c1 = stats(d1, hh)
        results[lab] = dict(e=e1[0], n=n1[0], c=c1[0], lo=np.percentile(c, 2.5), hi=np.percentile(c, 97.5))
        rows.append(dict(sample="post window", level=lab, evening=e1[0], night=n1[0], contrast=c1[0], contrast_lo=np.percentile(c, 2.5), contrast_hi=np.percentile(c, 97.5),
                         evening_lo=np.percentile(e, 2.5), evening_hi=np.percentile(e, 97.5), night_lo=np.percentile(n, 2.5), night_hi=np.percentile(n, 97.5), hours=len(hh)))
        print(f"[{lab}] evening {e1[0]:+.2f} [{np.percentile(e, 2.5):+.2f}, {np.percentile(e, 97.5):+.2f}]  night {n1[0]:+.2f} [{np.percentile(n, 2.5):+.2f}, {np.percentile(n, 97.5):+.2f}]  "
              f"contrast {c1[0]:+.2f} [{np.percentile(c, 2.5):+.2f}, {np.percentile(c, 97.5):+.2f}] EUR/MWh", flush=True)
        if lab == "neutral":
            dp_n, d1_n = dp, d1
    # subsamples under the neutral level
    for lab, sel in (("excl. July", (h.date.dt.month != 7).to_numpy()), ("excl. first week of June", (h.date > pd.Timestamp("2021-06-07")).to_numpy())):
        d1 = d1_n
        e1, n1, c1 = stats(d1, h, sel)
        e, n, c = stats(dp_n, h, sel)
        results[lab] = dict(e=e1[0], n=n1[0], c=c1[0], lo=np.percentile(c, 2.5), hi=np.percentile(c, 97.5))
        rows.append(dict(sample=lab, level="neutral", evening=e1[0], night=n1[0], contrast=c1[0], contrast_lo=np.percentile(c, 2.5), contrast_hi=np.percentile(c, 97.5), hours=int(sel.sum())))
        print(f"[{lab}] contrast {c1[0]:+.2f} [{np.percentile(c, 2.5):+.2f}, {np.percentile(c, 97.5):+.2f}]", flush=True)
    pd.DataFrame(rows).round(4).to_csv(OUT / "tou_price_effect_summary.csv", index=False)

    # by hour of day, neutral level
    byh = pd.DataFrame({"hour": h.hour, "dp": d1_n[0], "load": h.load_es}).groupby("hour").agg(dp=("dp", "mean"), load=("load", "mean"), n=("dp", "size")).reset_index()
    lo_hi = pd.DataFrame(dp_n.T).assign(hour=h.hour.to_numpy()).groupby("hour").mean()
    byh["dp_lo"], byh["dp_hi"] = np.percentile(lo_hi.to_numpy(), 2.5, axis=1), np.percentile(lo_hi.to_numpy(), 97.5, axis=1)
    byh.round(4).to_csv(OUT / "tou_price_effect_hours.csv", index=False)
    eur = float((d1_n[0] * h.load_es.to_numpy()).sum())
    print(f"consumers' euros, E0 energy times the price effect over the {h.date.nunique()} valid weekdays: {eur / 1e6:+.2f} million EUR "
          f"({eur / h.load_es.sum():+.2f} EUR/MWh on E0 energy)", flush=True)

    # placebo windows (cross-fitted errors, same level rule)
    def cf(n):
        a, bb = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], bb[x.date.reindex(bb.index).dt.year == 2019]])
    eEc, ePc = cf("ES"), cf("PT")
    pmask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    pl = []
    for s0 in PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        bp, _ = effects(x, eEc, ePc, pmask, s0, s1)
        hp, LTp = window_hours(x, cv, s0, s1)
        dp = price_effect(cv, hp, LTp, bp[None, :], "neutral")
        e, n, c = stats(dp, hp)
        pl.append(dict(start=s0.date(), b_peak=bp[0], b_mid=bp[1], b_off=bp[2], evening=e[0], night=n[0], contrast=c[0], hours=len(hp)))
    PL = pd.DataFrame(pl)
    PL.round(4).to_csv(OUT / "tou_price_effect_placebo.csv", index=False)
    print(PL.round(3).to_string(index=False), flush=True)

    # markup (R5)
    ms = month_list("2021-06-01", "2021-09-30")
    m_real, n_real = markup_contrast(cv, x, POST0, POST1, ms)
    m19, n19 = markup_contrast(cv, x, pd.Timestamp("2019-06-01"), pd.Timestamp("2019-09-14"), month_list("2019-06-01", "2019-09-30"))
    m20, n20 = markup_contrast(cv, x, pd.Timestamp("2020-07-01"), pd.Timestamp("2020-09-14"), month_list("2020-07-01", "2020-09-30"))
    mp = []
    for s0 in PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        m, n = markup_contrast(cv, x, s0, s1, month_list(s0, s1))
        mp.append(dict(start=s0.date(), markup_contrast=m, hours=n))
    MP = pd.DataFrame(mp)
    chg_reg = m_real - np.mean([m19, m20])
    dev_real = abs(m_real - MP.markup_contrast.mean())
    dev_pl = (MP.markup_contrast - MP.markup_contrast.mean()).abs().max()
    pd.concat([pd.DataFrame([dict(start="real window", markup_contrast=m_real, hours=n_real), dict(start="2019 same days", markup_contrast=m19, hours=n19), dict(start="2020 same days (July-Sept 14)", markup_contrast=m20, hours=n20)]), MP]).round(4).to_csv(OUT / "tou_price_effect_markup.csv", index=False)
    print(f"markup contrast (evening minus night, EUR/MWh over cost): real {m_real:+.2f} ({n_real} hours), 2019 same days {m19:+.2f}, 2020 same days {m20:+.2f}; change as registered {chg_reg:+.2f}", flush=True)
    print(MP.round(2).to_string(index=False), flush=True)

    # rules
    r = results["neutral"]
    allc = pd.concat([PL.contrast.abs(), pd.Series([abs(r["c"])])])
    rank = int((PL.contrast.abs() >= abs(r["c"])).sum()) + 1
    ok1 = bool(allw.valid.astype(bool).mean() >= 0.70)
    ok2 = bool(r["c"] < 0 and r["hi"] < 0 and 0.5 <= abs(r["c"]) <= 20 and r["e"] < 0)
    ok3 = bool(rank <= 2 and abs(r["c"]) >= 1.5 * PL.contrast.std())
    signs = {k: bool(v["c"] < 0) for k, v in results.items()}
    ok4 = all(signs.values())
    ok5 = bool(dev_real > dev_pl)
    print(f"\nR1 curve valid: {ok1}")
    print(f"R2 sign and size: contrast {r['c']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}], evening {r['e']:+.2f} (negative, interval excludes zero, 0.5 <= |c| <= 20): {ok2}")
    print(f"R3 placebo: real contrast rank {rank} of {len(PL) + 1} (top 2 needed); placebo sd {PL.contrast.std():.2f}, 1.5 x sd = {1.5 * PL.contrast.std():.2f} against |real| {abs(r['c']):.2f}: {ok3}")
    print(f"R4 level robustness, contrast negative in every variant: {signs}: {ok4}")
    print(f"R5 markup (secondary): real window departs from the placebo mean by {dev_real:.2f}, largest placebo departure {dev_pl:.2f}: {'departs' if ok5 else 'no detectable response'}")


if __name__ == "__main__":
    main()
