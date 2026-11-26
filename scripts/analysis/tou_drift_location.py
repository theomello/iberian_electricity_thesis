"""Where does the placebo drift live? Area split and fixed-effect ladder (docs/specs/2026-11-26-drift-location-design.md).

Cached leave-one-year-out LASSO errors only (nothing is refitted). For the industry pool (6.2+6.3+6.4, full regulated-price
dose) and for E0 (toll-and-charge dose, six-summer test), in 2021 and each placebo summer 2014-2019:
  baseline  the committed estimator (Spain minus Portugal, fe3)
  ES, PT    Spain's error on its dose / Portugal's error on the same dose laid on Portuguese rows (no area terms)
  L1        weekend x area x month term uses one label for the whole evaluated window
  L2        Spain rows only
  L3        L1 and L2
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
COMMITTED = {"pool": dict(eta=-0.17705, mean=0.14286, sd=0.08083), "E0": dict(eta=-0.11572, mean=-0.00491, sd=0.03686)}


def eta_variant(x, errs, key, dpxs, mask, names, win_range, variant):
    """One beta over the stacked series. variant in baseline, ES, PT, L1, L2, L3."""
    a, b = win_range
    parts, pv = [], []
    for j, n in enumerate(names):
        st = CT.make_stack(x, errs[(n, key)], errs[("PT", key)], "PT", mask)
        st["area"] = st.area + 2 * j
        st["ym"] = f"{j}_" + st.date.dt.strftime("%Y-%m")
        inwin = ((st.date >= a) & (st.date <= b)).to_numpy()
        st["ymL"] = np.where(inwin, f"{j}_W", st.ym)
        if variant == "PT":  # Portugal rows, the same dose laid on them
            d = dpxs[n][st.src.to_numpy()]
            p = np.where(st.area.to_numpy() == 2 * j + 1, d, 0.0)
        else:
            p = np.where(st.area.to_numpy() == 2 * j, dpxs[n][st.src.to_numpy()], 0.0)
        keep = np.ones(len(st), bool)
        if variant in ("ES", "L2", "L3"):
            keep = st.area.to_numpy() == 2 * j
        elif variant == "PT":
            keep = st.area.to_numpy() == 2 * j + 1
        parts.append(st[keep]); pv.append(p[keep])
    s = pd.concat(parts, ignore_index=True)
    dose = np.concatenate(pv)
    if variant in ("ES", "PT"):
        F = sp.hstack([CT.onehot(s.hour, s.wk, s.area), CT.onehot(s.wk, s.ym)]).tocsr()
    else:
        coarse = variant in ("L1", "L3")
        F = sp.hstack([CT.onehot(s.hour, s.wk, s.area), CT.onehot(s.hour, s.wk, s.ym),
                       CT.onehot(s.wk, s.area, s.ymL if coarse else s.ym)]).tocsr()
    y = CT.EL.resid(F, s.e)
    p = CT.EL.resid(F, dose)
    g = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
    bb, V, _ = CT.ols_cl(y, p, g)
    return float(bb[0]), float(np.sqrt(V[0, 0]))


def slope(vals):
    yrs = np.array(list(vals.keys()), float)
    v = np.array(list(vals.values()), float)
    X = np.c_[np.ones(len(yrs)), yrs - yrs.mean()]
    c, *_ = np.linalg.lstsq(X, v, rcond=None)
    r = v - X @ c
    se = np.sqrt(r @ r / (len(v) - 2) / ((yrs - yrs.mean()) ** 2).sum())
    return float(c[1]), float(se)


def main():
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    pt = RP.power_table()
    tab_full = RP.tables(dates, pt, "full", wp=wp)
    tab_e0 = CT.old_new_tables(dates)
    errs = S6.errors(x, clean)

    sets = {"pool": (RP.POOL, {n: to_x(CT.series_dose(n, tab_full, ebar)) for n in RP.POOL}),
            "E0": (["E0"], {"E0": to_x(CT.series_dose("E0", tab_e0, ebar))})}
    win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
    rows = []
    for tag, (names, dp) in sets.items():
        for variant in ("baseline", "ES", "PT", "L1", "L2", "L3"):
            res = {}
            for yr in [2021] + S6.SUMMERS:
                if yr == 2021:
                    w, key, mask, rng = win21, "()", pre | pd.Series(win21, index=x.index), (S6.R0, S6.R1)
                else:
                    a, b = S6.aligned(yr)
                    w = ((x.date >= a) & (x.date <= b)).to_numpy()
                    key, mask, rng = f"({yr},)", pre, (a, b)
                res[yr] = eta_variant(x, errs, key, {n: np.where(w, dp[n], 0.0) for n in names}, mask, names, rng,
                                      "baseline" if variant == "baseline" else variant)[0]
                rows.append(dict(set=tag, variant=variant, summer=yr, beta=res[yr]))
            pl = {k: v for k, v in res.items() if k != 2021}
            m, sd = np.mean(list(pl.values())), np.std(list(pl.values()), ddof=1)
            sl, se = slope(pl)
            print(f"{tag:5s} {variant:8s} eta_2021 {res[2021]:+.4f}  placebo mean {m:+.4f} sd {sd:.4f}  slope {sl:+.4f}/yr (se {se:.4f})  "
                  + " ".join(f"{k}:{v:+.3f}" for k, v in pl.items()), flush=True)
            if variant == "baseline":  # R0 gate
                c = COMMITTED[tag]
                ok = abs(res[2021] - c["eta"]) < 0.0015 and abs(m - c["mean"]) < 0.0015 and abs(sd - c["sd"]) < 0.0015
                print(f"R0 {tag}: committed {c} -> {'pass' if ok else 'FAIL'}", flush=True)
                if not ok:
                    pd.DataFrame(rows).to_csv(OUT / "tou_drift_location_betas.csv", index=False)
                    sys.exit("R0 failed: stop and find why")
            pd.DataFrame(rows).to_csv(OUT / "tou_drift_location_betas.csv", index=False)

    R = pd.DataFrame(rows)
    out = []
    for tag in sets:
        for v in ("baseline", "ES", "PT", "L1", "L2", "L3"):
            r = R[(R.set == tag) & (R.variant == v)].set_index("summer").beta
            pl = r.drop(2021)
            sl, se = slope(pl.to_dict())
            out.append(dict(set=tag, variant=v, eta_2021=r.loc[2021], placebo_mean=pl.mean(), placebo_sd=pl.std(ddof=1), slope=sl, slope_se=se))
    S_ = pd.DataFrame(out)
    S_.round(5).to_csv(OUT / "tou_drift_location_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(S_.round(4).to_string(index=False))

    g = S_[S_.set == "pool"].set_index("variant")
    base = g.loc["baseline"]
    print("\nRULES")
    est = base.slope < 0 and abs(base.slope) >= 1.5 * base.slope_se
    print(f"A1 baseline slope {base.slope:+.4f} (se {base.slope_se:.4f}) established: {bool(est)}")
    if est:
        s_es, s_pt = g.loc["ES"].slope / base.slope, -g.loc["PT"].slope / base.slope
        where = "Spain" if s_es >= 0.75 else "Portugal" if s_pt >= 0.75 else "shared"
        print(f"A1 s_ES {s_es:.2f}  s_PT {s_pt:.2f} -> drift is {where}")
    rel = g.loc["L1"].slope / base.slope - 1
    print(f"B1 L1 slope {g.loc['L1'].slope:+.4f} vs baseline {base.slope:+.4f} (change {rel:+.0%}) -> {'shape' if abs(rel) <= 0.25 else 'level'} drift")
    e = S_[S_.set == "E0"].set_index("variant")
    print("B2 E0 eta_2021 by rung (baseline, then change; double LASSO -0.0816, threshold 0.018):")
    for v in ("baseline", "L1", "L2", "L3"):
        print(f"   {v:8s} {e.loc[v].eta_2021:+.4f}  change {e.loc[v].eta_2021 - e.loc['baseline'].eta_2021:+.4f}  moves: {abs(e.loc[v].eta_2021 - e.loc['baseline'].eta_2021) >= 0.018}")


if __name__ == "__main__":
    main()
