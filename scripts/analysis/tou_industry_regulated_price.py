"""Industrial elasticity to the regulated per-period price (docs/specs/2026-11-18-industry-regulated-price-elasticity-design.md).

    .venv/bin/python scripts/analysis/tou_industry_regulated_price.py --check   # Z2 readability of the dose only
    .venv/bin/python scripts/analysis/tou_industry_regulated_price.py           # Z2, E1-E6, descriptions

Dose: ln[(E + T_new + W_new) / (E + T_old + W_old)] by tariff, date and hour, where T is the energy toll (+ charge from
June 2021) of the hour's period (tou_tariff_schedule) and W = power-term price of the period (EUR/kW-year; old: Orden
IET/107/2014 annex I and IET/2444/2014 for 6.1A, 3.1A from IET/107/2014; new: CNMC BOE-A-2021-4565 annex I 1.a (T&D)
plus charges Orden TED/371/2021 art. 2.a, segments 3-6 = 6.1TD-6.4TD) divided by the period's hours in a non-leap year
(2019 calendar, schedule-module holidays), x1000 to EUR/MWh. Values read twice (XML and PDF) and checked on
2026-11-18 (Z1). Errors, windows and inference as tou_industry_six_summer (leave-one-year-out LASSO, cached).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = S6.OUT
POOL = ["6.2", "6.3", "6.4"]
SERIES = POOL + ["E1+E2"]
# power-term prices, EUR/kW-year, periods 1..6 (old 3.1A has three periods)
PW_OLD = {"6.1": [39.139427, 19.586654, 14.334178, 14.334178, 14.334178, 6.540177],
          "6.2": [22.158348, 11.088763, 8.115134, 8.115134, 8.115134, 3.702649],
          "6.3": [18.916198, 9.466286, 6.927750, 6.927750, 6.927750, 3.160887],
          "6.4": [13.706285, 6.859077, 5.019707, 5.019707, 5.019707, 2.290315],
          "3.1": [59.173468, 36.490689, 8.367731]}
PW_TOLL = {"6.1": [21.245192, 21.245192, 11.530748, 8.716048, 0.560259, 0.560259],
           "6.2": [15.272489, 15.272489, 7.484607, 6.676931, 0.459003, 0.459003],
           "6.3": [11.548232, 11.548232, 6.320362, 3.694683, 0.708338, 0.708338],
           "6.4": [12.051156, 9.236539, 4.442575, 3.369751, 0.628452, 0.628452]}
PW_CHARGE = {"6.1": [9.290603, 4.649513, 3.378401, 3.378401, 3.378401, 1.548434],
             "6.2": [5.455758, 2.730784, 1.983912, 1.983912, 1.983912, 0.909293],
             "6.3": [4.368324, 2.186024, 1.588236, 1.588236, 1.588236, 0.728054],
             "6.4": [2.136839, 1.069310, 0.777032, 0.777032, 0.777032, 0.356140]}
PW_NEW = {k: [a + b for a, b in zip(PW_TOLL[k], PW_CHARGE[k])] for k in PW_TOLL}


def power_table():
    s = TS.schedule(pd.date_range("2019-01-01", "2019-12-31"))
    rows = []
    for tar in ("6.1", "6.2", "6.3", "6.4", "3.1->6.1"):
        g = s[s.tariff == tar]
        h_old, h_new = g.groupby("old_period").size(), g.groupby("new_period").size()
        old_key = "3.1" if tar == "3.1->6.1" else tar
        new_key = "6.1" if tar == "3.1->6.1" else tar
        for p, h in h_old.items():
            rows.append(dict(tariff=tar, regime="old", period=p, hours=int(h), eur_kw_year=PW_OLD[old_key][p - 1],
                             w_eur_mwh=1000 * PW_OLD[old_key][p - 1] / h))
        for p, h in h_new.items():
            rows.append(dict(tariff=tar, regime="new", period=p, hours=int(h), eur_kw_year=PW_NEW[new_key][p - 1],
                             w_eur_mwh=1000 * PW_NEW[new_key][p - 1] / h))
    return pd.DataFrame(rows)


def tables(dates, pt, variant, wp=None, contract_w=0.5):
    """Per-tariff (date, hour) tables with old_price/new_price for CT.series_dose. variant: full, energy, power, contract."""
    s = TS.schedule(dates)
    out = {}
    for tar, g in s.groupby("tariff"):
        if tar == "3.0":
            continue
        w = pt[pt.tariff == tar]
        wo = g.old_period.map(w[w.regime == "old"].set_index("period").w_eur_mwh).to_numpy()
        wn = g.new_period.map(w[w.regime == "new"].set_index("period").w_eur_mwh).to_numpy()
        to, tn = g.old_price.to_numpy(), g.new_price.to_numpy()
        if variant == "energy":
            o, n = to, tn
        elif variant == "power":
            o, n = to + wo, to + wn
        else:
            o, n = to + wo, tn + wn
        if variant == "contract":  # fixed/mixed share: period-average wholesale minus hourly mean, half weight
            key = g.set_index(["date", "hour"]).index
            e = wp.reindex(key).to_numpy()
            dfp = pd.DataFrame({"e": e, "po": g.old_period.to_numpy(), "pn": g.new_period.to_numpy(), "m": g.date.dt.month.to_numpy()})
            ao = dfp.groupby(["m", "po"]).e.transform("mean") - dfp.groupby("m").e.transform("mean")
            an = dfp.groupby(["m", "pn"]).e.transform("mean") - dfp.groupby("m").e.transform("mean")
            o, n = o + contract_w * ao.to_numpy(), n + contract_w * an.to_numpy()
        out[tar] = pd.DataFrame({"old_price": o, "new_price": n}, index=pd.MultiIndex.from_frame(g[["date", "hour"]]))
    return out


def pooled_eta(x, errs, key, dpxs, mask, names):
    """One eta over the stacked series (each with its own Portugal block); all fixed effects series-specific."""
    parts, pv = [], []
    for j, n in enumerate(names):
        st = CT.make_stack(x, errs[(n, key)], errs[("PT", key)], "PT", mask)
        st["area"] = st.area + 2 * j
        st["ym"] = f"{j}_" + st.date.dt.strftime("%Y-%m")
        pv.append(np.where(st.area.to_numpy() == 2 * j, dpxs[n][st.src.to_numpy()], 0.0))
        parts.append(st)
    s = pd.concat(parts, ignore_index=True)
    F = CT.fe3(s)
    y = CT.EL.resid(F, s.e)
    p = CT.EL.resid(F, np.concatenate(pv))
    g = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
    b, V, G = CT.ols_cl(y, p, g)
    return float(b[0]), float(np.sqrt(V[0, 0]))


def ptest(real, pl):
    pl = np.asarray(pl, float)
    S, m, sd = len(pl), pl.mean(), pl.std(ddof=1)
    se = sd * np.sqrt(1 + 1 / S)
    t = (real - m) / se
    q = stats.t.ppf(0.975, S - 1)
    return dict(S=S, eta_2021=real, placebo_mean=m, placebo_sd=sd, t=t, p_t=float(stats.t.cdf(t, S - 1)),
                p_rank=(1 + int((pl <= real).sum())) / (1 + S), lo=real - (m + q * se), hi=real - (m - q * se))


def main():
    x = S6.build()
    clean = S6.gates(x)
    pt = power_table()
    pt.round(6).to_csv(OUT / "tou_power_term_6x.csv", index=False)
    print(pt[pt.tariff.isin(POOL)].round(3).to_string(index=False))

    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    shares = {k: float(x.loc[pre & (x.date >= "2018-01-01"), f"load_c_{k}"].mean()) for k in S6.COMP}
    wts = {k: v / sum(shares.values()) for k, v in shares.items()}

    ren = pd.read_parquet(T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()

    tabs = {v: tables(dates, pt, v, wp=wp) for v in ("full", "energy", "power", "contract")}

    def dose(n, v):
        tb = tabs[v]
        if n == "IND":
            return sum(wts[k] * to_x(CT.series_dose(S6.COMP_TARIFF[k], tb, ebar)) for k in S6.COMP)
        return to_x(CT.series_dose(n, tb, ebar))

    win = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
    print("\nZ2 readable dose (within-day sd over the post window >= 0.02):")
    keep = []
    for n in SERIES:
        sds = {v: float(x[win].assign(dp=dose(n, v)[win]).groupby("date").dp.std().mean()) for v in ("full", "energy")}
        ok = sds["full"] >= 0.02
        print(f"  {n}: full {sds['full']:.4f} (energy-only {sds['energy']:.4f}) -> {'pass' if ok else 'FAIL'}")
        if ok and n in POOL:
            keep.append(n)
    if "--check" in sys.argv:
        return
    errs = S6.errors(x, clean)

    res, summ = [], []
    for v in ("full", "energy", "power", "contract"):
        dp = {n: dose(n, v) for n in SERIES}
        w_dp = {n: np.where(win, dp[n], 0.0) for n in SERIES}
        real = pooled_eta(x, errs, "()", w_dp, pre | pd.Series(win, index=x.index), keep)
        pls = {}
        for y in S6.SUMMERS:
            a, b = S6.aligned(y)
            w = ((x.date >= a) & (x.date <= b)).to_numpy()
            pls[y] = pooled_eta(x, errs, f"({y},)", {n: np.where(w, dp[n], 0.0) for n in SERIES}, pre, keep)[0]
        t = ptest(real[0], list(pls.values()))
        summ.append(dict(series="pool " + "+".join(keep), dose=v, se_2021=real[1], **t, placebos=" ".join(f"{k}:{p:+.3f}" for k, p in pls.items())))
        if v == "full":
            loso = [ptest(real[0], [p for k, p in pls.items() if k != d])["p_t"] for d in pls]
            for n in SERIES:
                ys = [y for y in S6.SUMMERS if y in clean[n]]
                rr = pooled_eta(x, errs, "()", {n: w_dp[n]}, pre | pd.Series(win, index=x.index), [n])[0]
                pp = []
                for y in ys:
                    a, b = S6.aligned(y)
                    w = ((x.date >= a) & (x.date <= b)).to_numpy()
                    pp.append(pooled_eta(x, errs, f"({y},)", {n: np.where(w, dp[n], 0.0)}, pre, [n])[0])
                summ.append(dict(series=n, dose=v, **ptest(rr, pp), placebos=" ".join(f"{y}:{p:+.3f}" for y, p in zip(ys, pp))))
        print(v, "done", flush=True)
    S_ = pd.DataFrame(summ)
    S_.round(5).to_csv(OUT / "tou_industry_regulated_price_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(S_.drop(columns=["placebos"]).round(3).to_string(index=False))
    print(S_[["series", "dose", "placebos"]].to_string(index=False))

    # E6 reduced form: hour share on working days, Jun-Sep, 2021 minus mean of placebo years, on rank change (old - new)
    hol = TS.holidays()
    sched = TS.schedule(pd.date_range("2021-06-01", "2021-09-30"))
    rk = sched[(sched.date.dt.dayofweek < 5) & ~sched.date.isin(hol)].assign(m=lambda d: d.date.dt.month, d_rank=lambda d: d.old_period - d.new_period)
    rk = rk.groupby(["tariff", "m", "hour"]).d_rank.mean()
    cells = []
    for n in keep:
        d = CT.esios_load(S6.IDS[n])
        d = d[(d.date.dt.dayofweek < 5) & ~d.date.isin(hol) & d.date.dt.month.between(6, 9)]
        d = d.assign(s=d.v / d.groupby("date").v.transform("mean"), y=d.date.dt.year, m=d.date.dt.month)
        c = d.groupby(["y", "m", "hour"]).s.mean().unstack("y")
        c["d_rank"] = [rk.get((n, m, h), np.nan) for m, h in c.index]
        c["series"] = n
        cells.append(c)
    C = pd.concat(cells)
    years = [y for y in S6.SUMMERS if y in C.columns]

    def slope(col, others):
        dev = C[col] - C[others].mean(axis=1)
        X = np.c_[np.ones(len(C)), C.d_rank]
        return float(np.linalg.lstsq(X, dev.to_numpy(), rcond=None)[0][1])
    rf_real = slope(2021, years)
    rf_pl = [slope(y, [o for o in years if o != y]) for y in years]
    rf = ptest(rf_real, rf_pl)
    print(f"\nE6 reduced form: share change per one-step dearer period {rf_real:+.4f}; placebo years {[round(v, 4) for v in rf_pl]}; p_t {rf['p_t']:.4f}")

    f = S_[(S_.dose == "full") & S_.series.str.startswith("pool")].iloc[0]
    inner = S_[(S_.dose == "full") & S_.series.isin(keep)]
    print("\nRULES (pool:", keep, ")")
    print(f"E1 detection: eta {f.eta_2021:+.4f} < 0 and p_t {f.p_t:.4f} <= 0.05: {bool(f.eta_2021 < 0 and f.p_t <= 0.05)}")
    print(f"E2 rank: p_rank {f.p_rank:.3f} == 1/7: {bool(np.isclose(f.p_rank, 1 / (f.S + 1)))}")
    print(f"E3 null centred: |m| {abs(f.placebo_mean):.4f} <= |eta|/3 {abs(f.eta_2021) / 3:.4f}: {bool(abs(f.placebo_mean) <= abs(f.eta_2021) / 3)}")
    print(f"E4 leave-one-summer-out p {[round(p, 4) for p in loso]} all <= 0.10: {bool(max(loso) <= 0.10)}")
    print(f"E5 proportionality: series eta {inner.set_index('series').eta_2021.round(3).to_dict()} inside [{f.lo:+.3f}, {f.hi:+.3f}]: "
          f"{bool(inner.eta_2021.between(f.lo, f.hi).all())}")
    print(f"E6 reduced form: slope {rf_real:+.4f} < 0 and p_t {rf['p_t']:.4f} <= 0.05: {bool(rf_real < 0 and rf['p_t'] <= 0.05)}")


T_ROOT = S6.T.ROOT

if __name__ == "__main__":
    main()
