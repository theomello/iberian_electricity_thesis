"""Validity tests with the industrial load shift added (docs/specs/2026-11-21-validity-industrial-shift-design.md).

    .venv/bin/python scripts/analysis/tou_validity_industrial.py

Reruns the price effect (R1-R4), T2 (G0, G1, M1, M2, D1) and T3 (P1, B1) with the counterfactual demand
dQ_h = dQ^E0_h + sum_k dQ^ind_kh, where dQ^ind_kh = -b * r~_kdh * Lbar_kd (extra demand without the reform, MW):
b the pooled E6 reduced-form slope, r = old_period - new_period (positive = dearer), r~ recentred within the day,
Lbar the day's mean hourly load of tariff series k (6.2-6.4, ESIOS 1216-1218). Variants: main, S-cell (observed 2021
cell deviation instead of b * r~), S-wide (6.4's pattern on E1-E6). The three existing scripts are imported, not
changed; T2 and T3 write into a scratch folder that this script reads, so their registered outputs stay untouched.
Writes outputs/tables/tou_validity_industrial{,_hours,_checks}.csv.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_price_effect as PE  # noqa: E402
import tou_price_signal_feedback as T3  # noqa: E402
import tou_reform_market_power as T2  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = T.OUT
POOL = ["6.2", "6.3", "6.4"]
WIDE_IDS = [1202, 1203, 1204, 1205, 1206, 1207]
B_REGISTERED = -0.0100


# ---------------------------------------------------------------- the industrial shift
def cells():
    """Hour share of the daily mean (working days, June-September) by series, month, hour and year; and the
    mean period step by (tariff, month, hour) of the reform calendar. Same code as E6 of tou_industry_regulated_price."""
    hol = TS.holidays()
    sched = TS.schedule(pd.date_range("2021-06-01", "2021-09-30"))
    rk = sched[(sched.date.dt.dayofweek < 5) & ~sched.date.isin(hol)].assign(m=lambda d: d.date.dt.month, d_rank=lambda d: d.old_period - d.new_period)
    rk = rk.groupby(["tariff", "m", "hour"]).d_rank.mean()
    out = []
    for n in POOL:
        d = CT.esios_load(S6.IDS[n])
        d = d[(d.date.dt.dayofweek < 5) & ~d.date.isin(hol) & d.date.dt.month.between(6, 9)]
        d = d.assign(s=d.v / d.groupby("date").v.transform("mean"), y=d.date.dt.year, m=d.date.dt.month)
        c = d.groupby(["y", "m", "hour"]).s.mean().unstack("y")
        c["d_rank"] = [rk.get((n, m, h), np.nan) for m, h in c.index]
        c["series"] = n
        out.append(c)
    return pd.concat(out)


def slopes(C):
    years = [y for y in S6.SUMMERS if y in C.columns]

    def slope(col, others):
        dev = C[col] - C[others].mean(axis=1)
        X = np.c_[np.ones(len(C)), C.d_rank]
        return float(np.linalg.lstsq(X, dev.to_numpy(), rcond=None)[0][1])
    return slope(2021, years), {y: slope(y, [o for o in years if o != y]) for y in years}


def cell_dev(C, year):
    """Observed share deviation of `year` from the other summers' mean, by (series, month, hour)."""
    years = [y for y in S6.SUMMERS if y in C.columns]
    others = [y for y in years if y != year]
    dev = (C[year] - C[others].mean(axis=1)).rename("dev").reset_index()
    dev["series"] = C.series.to_numpy()
    return dev.set_index(["series", "m", "hour"]).dev


def daily_mean(ids):
    d = CT.esios_load(ids)
    return d.groupby("date").v.mean()


def xind(dates, variant, b, dev, loads):
    """Extra demand without the reform (MW) by (date, hour) on weekdays that are not holidays, summed over series."""
    hol = TS.holidays()
    days = pd.DatetimeIndex([d for d in pd.DatetimeIndex(dates) if d.dayofweek < 5 and d not in set(hol)])
    s = TS.schedule(days)
    s = s.assign(m=s.date.dt.month, r=s.old_period - s.new_period)
    tot = None
    series = ["6.4"] if variant == "S-wide" else POOL
    for n in series:
        g = s[s.tariff == n][["date", "hour", "m", "r"]].copy()
        if variant == "S-cell":
            g["ds"] = [dev.get((n, m, h), np.nan) for m, h in zip(g.m, g.hour)]
        else:
            g["ds"] = b * g.r
        g["ds"] = g.ds - g.groupby("date").ds.transform("mean")          # energy-neutral by day
        L = loads["wide" if variant == "S-wide" else n]
        g["x"] = -g.ds * g.date.map(L).to_numpy()
        part = g.set_index(["date", "hour"]).x
        tot = part if tot is None else tot.add(part, fill_value=0.0)
    return tot


# ---------------------------------------------------------------- re-clearing with the combined shift
def price_effect_plus(cv, h, LT, B, mode, gap, xi):
    """PE.price_effect with the industrial extra demand xi (MW, aligned to h) added to E0's."""
    if mode == "neutral":
        C = np.log(np.exp(-B) @ LT.to_numpy().T / LT.to_numpy().sum(1))
        c = C[:, h.day.to_numpy()]
    elif mode == "F":
        c = np.zeros((B.shape[0], len(h)))
    else:
        c = np.full((B.shape[0], len(h)), gap)
    tau = B[:, h.k.to_numpy()] + c
    X = h.load_es.to_numpy()[None, :] * (np.exp(-tau) - 1.0) + xi[None, :]
    dt, hid = h.d_tot.to_numpy(), h.hid.to_numpy()
    out = np.empty_like(X)
    for j in range(len(h)):
        p0 = cv.clear(hid[j], dt[j])
        out[:, j] = p0 - cv.clear(hid[j], dt[j] + X[:, j])
    return out


def align(h, xi):
    return np.nan_to_num(xi.reindex(pd.MultiIndex.from_arrays([h.date, h.hour])).to_numpy())


def main():
    C = cells()
    b, b_pl = slopes(C)
    print(f"reduced-form slope b {b:+.5f} (registered {B_REGISTERED:+.4f}); placebo slopes {dict((k, round(v, 5)) for k, v in b_pl.items())}", flush=True)
    assert abs(b - B_REGISTERED) < 0.0005, "reduced form does not reproduce the registered slope"
    dev21, dev19 = cell_dev(C, 2021), cell_dev(C, 2019)
    loads = {n: daily_mean(S6.IDS[n]) for n in POOL}
    loads["wide"] = daily_mean(WIDE_IDS)

    x = D.prep(T.build("e0", end="2021-09-14"))
    errs = PE.get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    mask = pre | ((x.date >= PE.POST0) & (x.date <= PE.POST1))
    be, V = PE.effects(x, errs[("ES", "()")], errs[("PT", "()")], mask, PE.POST0, PE.POST1)
    pc = pd.read_csv(OUT / "tou_area_panel_pc_effects.csv")
    g_ = lambda spec, t: pc[(pc.spec == spec) & (pc.term == t)].iloc[0].b
    gap = float(np.mean([g_("M weighted", t) - g_("F REN control", t) for t in PE.TY]))
    cv = PE.Curves(PE.month_list("2019-01-01", "2019-12-31") + PE.month_list("2021-06-01", "2021-09-30"))
    h, LT = PE.window_hours(x, cv, PE.POST0, PE.POST1)
    allw = cv.h[(cv.h.date >= PE.POST0) & (cv.h.date <= PE.POST1) & (cv.h.date.dt.dayofweek < 5)]
    rng = np.random.default_rng(PE.SEED)
    Bd = rng.multivariate_normal(be, V, size=PE.NDRAW)
    B1 = be[None, :]
    C0 = np.log(np.exp(-B1) @ LT.to_numpy().T / LT.to_numpy().sum(1))[0, h.day.to_numpy()]
    xe0 = h.load_es.to_numpy() * (np.exp(-(be[h.k.to_numpy()] + C0)) - 1.0)

    def cf(n):
        a, bb = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], bb[x.date.reindex(bb.index).dt.year == 2019]])
    eEc, ePc = cf("ES"), cf("PT")
    pmask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    pwin = []
    for s0 in PE.PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        bp, _ = PE.effects(x, eEc, ePc, pmask, s0, s1)
        hp, LTp = PE.window_hours(x, cv, s0, s1)
        pwin.append((s0, s1, bp, hp, LTp))

    rows, checks, hours = [], [], []
    scratch = Path(tempfile.mkdtemp(prefix="validity_ind_"))
    for variant in ("main", "S-cell", "S-wide"):
        xi_all = xind(pd.date_range(PE.POST0, PE.POST1), variant, b, dev21, loads)
        xi = align(h, xi_all)
        ev, ni = h.hour.isin(PE.EVENING).to_numpy(), h.hour.isin(PE.NIGHT).to_numpy()
        for blk, m in (("evening", ev), ("night", ni)):
            rows.append(dict(variant=variant, part="V0", item=f"mean |dQ_ind| / mean |dQ_E0|, {blk}",
                             value=np.abs(xi[m]).mean() / np.abs(xe0[m]).mean(), dq_ind_mw=xi[m].mean(), dq_e0_mw=xe0[m].mean()))
        # price effect, three levels + subsamples
        res, dpn = {}, None
        for lev in ("neutral", "F", "M"):
            dp = price_effect_plus(cv, h, LT, Bd, lev, gap, xi)
            d1 = price_effect_plus(cv, h, LT, B1, lev, gap, xi)
            e, n_, c = PE.stats(dp, h)
            e1, n1, c1 = PE.stats(d1, h)
            res[lev] = dict(e=e1[0], n=n1[0], c=c1[0], lo=np.percentile(c, 2.5), hi=np.percentile(c, 97.5))
            rows.append(dict(variant=variant, part="price effect", item=f"level {lev}", evening=e1[0], night=n1[0], contrast=c1[0],
                             contrast_lo=res[lev]["lo"], contrast_hi=res[lev]["hi"], hours=len(h)))
            h[f"dp_{lev}"] = d1[0]
            if lev == "neutral":
                dpn, d1n = dp, d1
        for lab, sel in (("excl. July", (h.date.dt.month != 7).to_numpy()), ("excl. first week of June", (h.date > pd.Timestamp("2021-06-07")).to_numpy())):
            e1, n1, c1 = PE.stats(d1n, h, sel)
            _, _, c = PE.stats(dpn, h, sel)
            res[lab] = dict(c=c1[0])
            rows.append(dict(variant=variant, part="price effect", item=lab, evening=e1[0], night=n1[0], contrast=c1[0],
                             contrast_lo=np.percentile(c, 2.5), contrast_hi=np.percentile(c, 97.5), hours=int(sel.sum())))
        pl = []
        for s0, s1, bp, hp, LTp in pwin:
            if variant == "S-cell":
                xp = align(hp, xind(pd.date_range(s0, s1), variant, b, dev19, loads))
            else:
                xp = align(hp, xind(pd.date_range(s0, s1), variant, b_pl[2019], dev19, loads))
            dp = price_effect_plus(cv, hp, LTp, bp[None, :], "neutral", gap, xp)
            e, n_, c = PE.stats(dp, hp)
            pl.append(c[0])
            rows.append(dict(variant=variant, part="placebo", item=f"{s0:%Y-%m}", contrast=c[0], hours=len(hp)))
        pl = pd.Series(pl)
        r = res["neutral"]
        rank = int((pl.abs() >= abs(r["c"])).sum()) + 1
        checks += [
            dict(variant=variant, rule="R1", passed=bool(allw.valid.astype(bool).mean() >= 0.70), detail=f"valid share {allw.valid.astype(bool).mean():.3f}"),
            dict(variant=variant, rule="R2", passed=bool(r["c"] < 0 and r["hi"] < 0 and 0.5 <= abs(r["c"]) <= 20 and r["e"] < 0),
                 detail=f"contrast {r['c']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}], evening {r['e']:+.2f}, night {r['n']:+.2f}"),
            dict(variant=variant, rule="R3", passed=bool(rank <= 2 and abs(r["c"]) >= 1.5 * pl.std()),
                 detail=f"rank {rank} of {len(pl) + 1}; placebo sd {pl.std():.2f}; range {pl.min():+.2f}..{pl.max():+.2f}"),
            dict(variant=variant, rule="R4", passed=bool(all(v["c"] < 0 for v in res.values())),
                 detail="; ".join(f"{k} {v['c']:+.2f}" for k, v in res.items())),
        ]
        print(f"[{variant}] contrast {r['c']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] evening {r['e']:+.2f} night {r['n']:+.2f}; placebo rank {rank}, sd {pl.std():.2f}", flush=True)

        # T2 with the combined shift: patch its counterfactual and output folder
        hh = h[["date", "hour", "dp_neutral", "dp_F", "dp_M"]].copy()
        hh["dq_neutral"] = xe0 + xi
        hours.append(hh.assign(variant=variant, dq_e0=xe0, dq_ind=xi))
        vdir = scratch / variant
        vdir.mkdir()
        T2.counterfactual = lambda hh=hh: hh.copy()
        T2.OUT = vdir
        T2.main()
        c2 = pd.read_csv(vdir / "tou_reform_market_power_checks.csv")
        for _, rr in c2.iterrows():
            checks.append(dict(variant=variant, rule="T2 " + rr["rule"], passed=rr["pass"], detail=rr["detail"]))
        r2 = pd.read_csv(vdir / "tou_reform_market_power.csv")
        for _, rr in r2.iterrows():
            rows.append(dict(variant=variant, part="T2", item=rr.firm, **{k: rr[k] for k in ("dX_all", "dX_evening", "dX_night", "X_sd", "dX_all_F", "dX_all_M")}))

        # T3: price-effect summary and T2 hours from the scratch folder; F and M load shifts include industry
        pd.DataFrame([dict(sample="post window", level=lev, contrast=res[lev]["c"]) for lev in ("neutral", "F", "M")]).to_csv(vdir / "tou_price_effect_summary.csv", index=False)
        T3.OUT = vdir
        hf = pd.read_csv(vdir / "tou_reform_market_power_hours.csv", parse_dates=["date"])
        hf = hf.merge(pd.DataFrame({"date": h.date, "hour": h.hour, "xi": xi}), on=["date", "hour"], how="left")
        hf.to_csv(vdir / "tou_reform_market_power_hours.csv", index=False)
        T3_main_plus(vdir)
        c3 = pd.read_csv(vdir / "tou_price_signal_feedback_checks.csv")
        for _, rr in c3.iterrows():
            checks.append(dict(variant=variant, rule=f"T3 {rr['rule']} {rr['block']}", passed=rr["verdict"] == "pass" if rr["verdict"] in ("pass", "FAIL") else None,
                               detail=f"value {rr['value']:.4f} (bar {rr['bar']}); {rr['verdict']}"))
        r3 = pd.read_csv(vdir / "tou_price_signal_feedback.csv")
        for _, rr in r3[r3.part == "b"].iterrows():
            rows.append(dict(variant=variant, part="T3 b", item=rr["item"], value=rr["value"], ratio=rr["ratio"], f_hh=rr["f_hh"], f_ind=rr["f_ind"], dq_abs_mean=rr["dq_abs_mean"]))
        for _, rr in r3[(r3.part == "a2") & r3["item"].str.startswith("kappa neutral")].iterrows():
            rows.append(dict(variant=variant, part="T3 a2", item=rr["item"], value=rr["value"], ratio=rr["ratio"]))

    pd.DataFrame(rows).round(5).to_csv(OUT / "tou_validity_industrial.csv", index=False)
    pd.concat(hours).round(4).to_csv(OUT / "tou_validity_industrial_hours.csv", index=False)
    CH = pd.DataFrame(checks)
    CH.to_csv(OUT / "tou_validity_industrial_checks.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 140, "display.max_rows", 300):
        print(CH.to_string(index=False))
    print("scratch", scratch)


def T3_main_plus(vdir):
    """T3.main (parts a1, a2/P1 as written), then part (b)/B1 recomputed with the industrial extra demand added to dQ
    at every level (column xi of T2's hour file); T3.main builds dQ_F and dQ_M from E0 alone."""
    orig_read = pd.read_csv
    T3.main()
    hf = orig_read(vdir / "tou_reform_market_power_hours.csv", parse_dates=["date"])
    h = hf.drop_duplicates(["date", "period"]).reset_index(drop=True)
    idx = pd.MultiIndex.from_arrays([h.date, h.hour])
    p = T3.CT.omie_hourly()
    pp = p.reindex(idx).to_numpy()
    blk = T3.block(h.hour.to_numpy())
    e0 = T3.N.hourly(1201).reindex(idx).to_numpy()
    ind = sum(T3.N.hourly(i) for i in (1216, 1217, 1218)).reindex(idx).to_numpy()
    bt = np.array([T3.B_TYPE[t] for t in T3.htype(h.hour.to_numpy())])
    xi = h.xi.fillna(0.0).to_numpy()
    dq = {"neutral": h.dq_neutral.to_numpy(), "F": e0 * (np.exp(-bt) - 1.0) + xi, "M": e0 * (np.exp(-(bt + T3.GAP)) - 1.0) + xi}
    rows, checks = [], []
    for case, inp in T3.INPUTS.items():
        for lev in ("neutral", "F", "M"):
            adp = np.abs(h[f"dp_{lev}"].to_numpy())
            fb = {}
            for g, L in (("hh", e0), ("ind", ind)):
                sg, la, th, mode = inp[g]
                rbar = pp if mode == "p" else pp / T3.S_IND
                fb[g] = sg * la * th * adp / rbar * L
            for b in ("evening", "night"):
                m = (blk == b) & np.isfinite(fb["hh"]) & np.isfinite(fb["ind"]) & (pp > 0)
                f_hh, f_ind = fb["hh"][m].mean(), fb["ind"][m].mean()
                dqm = abs(dq[lev][m].mean())
                share = (f_hh + f_ind) / dqm
                rows.append(dict(part="b", item=f"{case} {lev} {b}", value=f_hh + f_ind, f_hh=f_hh, f_ind=f_ind, dq_abs_mean=dqm, ratio=share))
                if case == "worst" and lev == "neutral":
                    v = "reported (|dQ| < 50 MW)" if dqm < T3.MIN_DQ else ("pass" if share <= T3.B1_BAR else "FAIL")
                    checks.append(dict(rule="B1", block=b, value=share, bar=T3.B1_BAR, verdict=v))
    # keep T3's P1 rows (they use the band at p* - dp, already combined) and replace its B1 rows and part b
    R0 = orig_read(vdir / "tou_price_signal_feedback.csv")
    C0 = orig_read(vdir / "tou_price_signal_feedback_checks.csv")
    R = pd.concat([R0[R0.part != "b"], pd.DataFrame(rows)], ignore_index=True)
    C = pd.concat([C0[C0.rule != "B1"], pd.DataFrame(checks)], ignore_index=True)
    R.to_csv(vdir / "tou_price_signal_feedback.csv", index=False)
    C.to_csv(vdir / "tou_price_signal_feedback_checks.csv", index=False)


if __name__ == "__main__":
    main()
