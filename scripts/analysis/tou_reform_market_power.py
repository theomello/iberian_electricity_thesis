"""T2: did the June 2021 reform change generators' market power? (docs/specs/2026-11-19-reform-market-power-design.md)

    .venv/bin/python scripts/analysis/tou_reform_market_power.py

For each valid weekday hour of 2021-06-01 -> 2021-09-14 the counterfactual price without the reform's load shift is
p_cf = p* - dp, dp the price effect of tou_price_effect.py (point effects, energy-neutral level; F and M levels
reported). For each firm, the Nash markup X = n_exp / slope_exp (EUR/MWh; = 100 x incentive_exp of
firm_incentive_rebuild.py) is recomputed at p* and at p_cf on the same day's offered curves, h = 5:
  slope_exp(p) = [all offers within +/-h of p - own supply-role sell offers in band - own buy offers in band
                  + own pass-through sell and buy offers in band] / 2h   (undefined below MIN_SLOPE)
  n_exp(p*)    = cleared sales - cleared purchases, pass-through units out (as stored)
  n_exp(p_cf)  = n_exp(p*) + [n_O(p_cf) - n_O(p*)], n_O(p) = own non-pass-through sell offers priced <= p minus own
                  buy offers priced >= p (the firm's own offers evaluated at that price).
Reported, no rule: the same with the firm's share of the added demand charged to its purchases (its share of cleared
buy volume in the hour), since the counterfactual demand is household load that integrated firms' retailers buy.
Writes outputs/tables/tou_reform_market_power{,_hours,_checks}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_price_effect as PE  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402

ROOT = T.ROOT
BIDS = ROOT / "data/omie/bids/parquet"
AGENTS = ROOT / "data/omie/registry/unit_agents.parquet"
STORED = ROOT / "outputs/tables/firm_incentive_net.parquet"
OUT = T.OUT
H = 5.0
MIN_SLOPE = 5.0
FIRMS = ["IBERDROLA", "ENDESA", "NATURGY", "EDP", "REPSOL"]
SUPPLY_ROLES = ("generation", "generation_large", "storage_mixed", "pumping")
# 2019-21H1 Nash markup on seller hours (notes/hydro-departure-by-firm.md section 2)
X_SELLER_1921 = {"IBERDROLA": 5.096, "EDP": 2.933, "ENDESA": 1.258}
LEVELS = ["neutral", "F", "M"]


def counterfactual():
    """Point price effect dp and added demand per valid weekday hour, three levels."""
    x = D.prep(T.build("e0", end="2021-09-14"))
    errs = PE.get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    mask = pre | ((x.date >= PE.POST0) & (x.date <= PE.POST1))
    b, _ = PE.effects(x, errs[("ES", "()")], errs[("PT", "()")], mask, PE.POST0, PE.POST1)
    pc = pd.read_csv(OUT / "tou_area_panel_pc_effects.csv")
    g = lambda spec, t: pc[(pc.spec == spec) & (pc.term == t)].iloc[0].b
    gap = float(np.mean([g("M weighted", t) - g("F REN control", t) for t in PE.TY]))
    cv = PE.Curves(PE.month_list("2021-06-01", "2021-09-30"))
    h, LT = PE.window_hours(x, cv, PE.POST0, PE.POST1)
    B = b[None, :]
    for lev in LEVELS:
        h[f"dp_{lev}"] = PE.price_effect(cv, h, LT, B, lev, gap)[0]
    C = np.log(np.exp(-B) @ LT.to_numpy().T / LT.to_numpy().sum(1))[0, h.day.to_numpy()]
    h["dq_neutral"] = h.load_es.to_numpy() * (np.exp(-(b[h.k.to_numpy()] + C)) - 1.0)
    print("effects", dict(zip(PE.TY, np.round(100 * b, 2))), f"gap {100 * gap:.2f}", f"hours {len(h)}", flush=True)
    return h[["date", "hour", "dp_neutral", "dp_F", "dp_M", "dq_neutral"]]


def month_x(ym, hrs, sup, allsp):
    """Per (date, period, firm): band pieces and n_O at p* and at each counterfactual price."""
    b = pq.read_table(BIDS / f"bids_{ym}.parquet", columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    for c in ("unit", "side", "status"):
        b[c] = b[c].astype(str)
    b = b.merge(hrs, on=["date", "period"], how="inner")
    if b.empty:
        return None
    prices = ["p_star"] + [f"pcf_{lev}" for lev in LEVELS]
    o = b[b.status == "O"]
    # market band at each price
    tot = []
    for pcol in prices:
        inb = (o.price_eur_mwh - o[pcol]).abs() <= H
        tot.append(o.power_mw.where(inb, 0.0).groupby([o.date, o.period]).sum().rename(f"band_{pcol}"))
    tot = pd.concat(tot, axis=1).reset_index()
    # own supply-role sell offers (slope_i of residual_demand_firm, owner tier)
    os_ = attach_owners(o[o.unit.isin(sup) & (o.side == "V")], allsp[allsp.unit.isin(sup)]).dropna(subset=["group"])
    # all owned units (own buy, pass-through, n_O; firm_incentive_rebuild)
    oa = attach_owners(o[o.unit.isin(set(allsp.unit))], allsp).dropna(subset=["group"])
    k = ["date", "period", "group"]
    parts = []
    for pcol in prices:
        sb = (os_.price_eur_mwh - os_[pcol]).abs() <= H
        parts.append(os_.power_mw.where(sb, 0.0).groupby([os_[c] for c in k]).sum().rename(f"own_sell_{pcol}"))
        ib = (oa.price_eur_mwh - oa[pcol]).abs() <= H
        buy, sell = ib & (oa.side == "C"), ib & (oa.side == "V")
        parts.append(oa.power_mw.where(buy, 0.0).groupby([oa[c] for c in k]).sum().rename(f"own_buy_{pcol}"))
        parts.append(oa.power_mw.where((buy | sell) & oa.pt, 0.0).groupby([oa[c] for c in k]).sum().rename(f"pt_band_{pcol}"))
        acc = ((oa.side == "V") & (oa.price_eur_mwh <= oa[pcol])) | ((oa.side == "C") & (oa.price_eur_mwh >= oa[pcol]))
        sg = np.where(oa.side == "V", 1.0, -1.0)
        parts.append(pd.Series(np.where(acc & ~oa.pt, sg * oa.power_mw, 0.0), index=oa.index).groupby([oa[c] for c in k]).sum().rename(f"nO_{pcol}"))
    # cleared purchases share (for the reported retail-share variant)
    c = b[(b.status == "C") & (b.side == "C")]
    ca = attach_owners(c[c.unit.isin(set(allsp.unit))], allsp).dropna(subset=["group"])
    ca = ca[~ca.pt]
    parts.append(ca.power_mw.groupby([ca[c_] for c_ in k]).sum().rename("buy_cleared"))
    f = pd.concat(parts, axis=1).fillna(0.0).reset_index().rename(columns={"group": "firm"})
    f = f.merge(tot, on=["date", "period"], how="left")
    allbuy = c.groupby(["date", "period"]).power_mw.sum().rename("buy_market").reset_index()
    return f.merge(allbuy, on=["date", "period"], how="left")


def main():
    h = counterfactual()
    h["period"] = h.hour + 1
    st = pq.read_table(STORED, columns=["date", "period", "firm", "p_star", "net_exp_mw", "slope_exp_h5", "incentive_exp_h5"]).to_pandas()
    st["date"] = pd.to_datetime(st.date)
    st = st[(st.date >= PE.POST0) & (st.date <= PE.POST1)]
    ps = st.drop_duplicates(["date", "period"])[["date", "period", "p_star"]]
    hrs = h.merge(ps, on=["date", "period"], how="inner")
    for lev in LEVELS:
        hrs[f"pcf_{lev}"] = hrs.p_star - hrs[f"dp_{lev}"]
    print(f"hours with a stored p* {len(hrs)} of {len(h)}", flush=True)
    a = pq.read_table(AGENTS, columns=["unit", "role"]).to_pandas()
    sup = set(a.loc[a.role.isin(SUPPLY_ROLES), "unit"].astype(str))
    allsp = spells().dropna(subset=["group"])
    allsp["unit"] = allsp.unit.astype(str)
    frames = [month_x(ym, hrs[["date", "period", "p_star"] + [f"pcf_{l}" for l in LEVELS]], sup, allsp) for ym in ("202106", "202107", "202108", "202109")]
    f = pd.concat([x for x in frames if x is not None], ignore_index=True)
    f = f[f.firm.isin(FIRMS)].merge(st[["date", "period", "firm", "net_exp_mw", "slope_exp_h5", "incentive_exp_h5"]], on=["date", "period", "firm"], how="inner")
    f = f.merge(hrs[["date", "period", "hour", "dq_neutral"] + [f"dp_{l}" for l in LEVELS]], on=["date", "period"], how="left")

    def xs(pcol, n):
        s = (f[f"band_{pcol}"] - f[f"own_sell_{pcol}"] - f[f"own_buy_{pcol}"] + f[f"pt_band_{pcol}"]) / (2 * H)
        return s, np.where(s >= MIN_SLOPE, n / s, np.nan)

    f["slope_act"], f["X_act"] = xs("p_star", f.net_exp_mw)
    for lev in LEVELS:
        n_cf = f.net_exp_mw + f[f"nO_pcf_{lev}"] - f["nO_p_star"]
        f[f"slope_cf_{lev}"], f[f"X_cf_{lev}"] = xs(f"pcf_{lev}", n_cf)
        f[f"dX_{lev}"] = f.X_act - f[f"X_cf_{lev}"]
    # reported: firm's share of the added demand charged to its purchases (counterfactual buys dq more in total)
    share = (f.buy_cleared / f.buy_market).fillna(0.0)
    n_ret = f.net_exp_mw + f["nO_pcf_neutral"] - f["nO_p_star"] - share * f.dq_neutral
    _, f["X_cf_retail"] = xs("pcf_neutral", n_ret)
    f["dX_retail"] = f.X_act - f.X_cf_retail
    f["X_stored"] = 100 * f.incentive_exp_h5
    f.round(5).to_csv(OUT / "tou_reform_market_power_hours.csv", index=False)

    ok = f.X_stored.notna() & np.isfinite(f.X_act)
    corr = float(np.corrcoef(f.X_stored[ok], f.X_act[ok])[0, 1])
    mad = float((f.X_stored[ok] - f.X_act[ok]).abs().median())
    ev, ni = f.hour.isin(PE.EVENING), f.hour.isin(PE.NIGHT)
    rows, ch = [], []
    ch.append(("G1 reproduction", bool(corr >= 0.99 and mad <= 0.05), f"corr {corr:.4f}, median |diff| {mad:.4f} EUR/MWh on {int(ok.sum())} firm-hours"))
    nh = f.drop_duplicates(["date", "period"]).shape[0]
    for firm in FIRMS:
        g = f[f.firm == firm]
        cov_a = np.isfinite(g.X_act).mean()
        cov_c = np.isfinite(g.X_cf_neutral).mean()
        g0 = bool(min(cov_a, cov_c) >= 0.70)
        ch.append((f"G0 coverage {firm}", g0, f"X defined at p* {cov_a:.3f}, at p_cf {cov_c:.3f} of {len(g)} hours"))
        okg = np.isfinite(g.dX_neutral)
        sd = float(np.nanstd(g.X_act[okg]))
        r = dict(firm=firm, hours=int(okg.sum()), X_mean=float(np.nanmean(g.X_act[okg])), X_sd=sd, share_net_seller=float((g.net_exp_mw > 0).mean()))
        for lab, sel in (("all", okg), ("evening", okg & ev[g.index]), ("night", okg & ni[g.index])):
            r[f"dX_{lab}"] = float(g.dX_neutral[sel].mean())
        for lev in ("F", "M", "retail"):
            r[f"dX_all_{lev}"] = float(np.nanmean(g[f"dX_{lev}"]))
        r["dX_evening_minus_night"] = r["dX_evening"] - r["dX_night"]
        rows.append(r)
        if g0:
            m1 = all(abs(r[f"dX_{lab}"]) <= 0.10 * sd for lab in ("all", "evening", "night"))
            ch.append((f"M1 {firm}", bool(m1), f"dX all {r['dX_all']:+.3f}, evening {r['dX_evening']:+.3f}, night {r['dX_night']:+.3f}; 10% of sd = {0.1 * sd:.3f}"))
            ch.append((f"M2 {firm}", bool(abs(r["dX_all"]) < 0.50), f"|dX| at beta 1 {abs(r['dX_all']):.3f} (bar 0.50); at beta 0.01 {0.01 * r['dX_all']:+.4f}, at beta 0.25 {0.25 * r['dX_all']:+.4f}"))
        if firm in X_SELLER_1921:
            for lab, sel in (("June 2021", g.date.dt.month == 6), ("June-August 2021", g.date.dt.month.isin([6, 7, 8]))):
                s = okg & sel & (g.net_exp_mw > 0)
                d = float(g.dX_neutral[s].mean()) if s.any() else np.nan
                bar = 0.10 * X_SELLER_1921[firm]
                ch.append((f"D1 {firm} {lab}", bool(abs(d) <= bar) if np.isfinite(d) else None, f"mean dX on net-seller hours {d:+.3f} ({int(s.sum())} hours); bar {bar:.3f}"))
    R = pd.DataFrame(rows)
    R.round(4).to_csv(OUT / "tou_reform_market_power.csv", index=False)
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(OUT / "tou_reform_market_power_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    print(f"\nmarket hours {nh}; dp neutral mean {hrs.dp_neutral.mean():+.3f}")
    print(R.round(3).to_string(index=False))
    print("\n", C.to_string(index=False))
    byh = f[f.firm.isin(FIRMS)].groupby(["firm", "hour"]).dX_neutral.mean().unstack(0).round(3)
    print("\nmean dX by hour (neutral)\n", byh.to_string())
    print("done")


if __name__ == "__main__":
    main()
