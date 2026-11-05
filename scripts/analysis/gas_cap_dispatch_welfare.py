#!/usr/bin/env python3
"""Welfare accounting of the gas cap's pass-through: who gains, who loses, and the dispatch distortion
(notes/rq-crisis-quantity.md, section J, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_dispatch_welfare.py [--months 202208 ...] [--rhos 0.55 0.73 1.0]

Two worlds on the effective day-ahead curve of `step_curves.py`, same valid hours as `gas_cap_consumer_saving.py`:
  observed        offers as they were (already net of the pass-through rho*S for the modelled gas units);
  counterfactual  the modelled gas units' sell rows raised by rho*S_day.
Each is re-cleared by `step_curves.reclear` (lowest price at which supply covers the buy volume strictly above it) and
then SETTLED: sell rows below the price run in full, rows at the price are cut pro rata to the volume
Q = min(supply at or below p, buy volume at or above p), the same on the buy side.
True resource cost: a modelled gas step costs its counterfactual offer (offer + rho*S); every other step its own offer.
Gross benefit: accepted buy MW x bid price. Interconnection pseudo-units (MIEU, MIE, MIP) are fixed-volume rows in both
worlds, so their value and cost cancel in every difference (checked); the Iberian view adds the price change on net exports.
Per rho it writes the buyers' payment change by class, revenue and true-cost change by seller class, the party ledger,
and DWL = W_cf - W_obs split into an allocation effect (extra cost of running the wrong plants at the observed volume)
and a quantity effect (taking more or less volume than the efficient point).

Writes outputs/tables/gas_cap_dispatch_welfare{,_ledger,_headline,_monthly,_hours,_checks}.csv and
gas_cap_dispatch_welfare_hourly.parquet (all months; a subset of months gets a suffix).
Run with OMP_NUM_THREADS=VECLIB_MAXIMUM_THREADS=OPENBLAS_NUM_THREADS=1.
"""
from __future__ import annotations

import faulthandler
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

faulthandler.dump_traceback_later(3600, exit=True)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from gas_cap_consumer_saving import MONTHS, RHOS, subsidy_and_units, wider  # noqa: E402
from gas_cap_group_net import esios  # noqa: E402
from residual_demand import IDENTITY_TOL, cleared_by_period  # noqa: E402
from step_curves import BIDS, DATA, KEY, VALID_ERR, effective, hid, reclear  # noqa: E402

T = ROOT / "outputs" / "tables"
ICN = {"MIEU", "MIE", "MIP"}
SELL = ["gas_es", "gas_pt", "oth_es", "oth_pt", "imp"]       # class codes 0..4
BUY = ["es", "pt", "exp"]                                    # class codes 5..7
CLS = SELL + BUY
HOUR_TOL_EUR = 1.0
BAL_TOL_MW = 0.01


def unit_flags(units_all: np.ndarray, gas: set, country: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """is interconnection pseudo-unit, is Portuguese (registry), is modelled gas, per row (via factorised units)."""
    codes, uniq = pd.factorize(units_all)
    u = pd.Series(uniq)
    icn = u.isin(ICN).to_numpy()[codes]
    pt = (u.map(country) == "PT").to_numpy()[codes]
    g = u.isin(gas).to_numpy()[codes]
    return icn, pt, g


def settle(idx: np.ndarray, sell: np.ndarray, price: np.ndarray, q: np.ndarray, p_h: np.ndarray, n: int) -> np.ndarray:
    """Accepted MW per row at clearing price p_h (per hour): below-price rows in full, rows at the price pro rata."""
    p = p_h[idx]
    lt_s, at_s = sell & (price < p), sell & (price == p)
    gt_b, at_b = ~sell & (price > p), ~sell & (price == p)
    bc = lambda m: np.bincount(idx, weights=q * m, minlength=n)  # noqa: E731
    slt, sat, dgt, dat = bc(lt_s), bc(at_s), bc(gt_b), bc(at_b)
    Q = np.minimum(slt + sat, dgt + dat)
    with np.errstate(divide="ignore", invalid="ignore"):
        fs = np.where(sat > 0, np.clip((Q - slt) / sat, 0.0, 1.0), 0.0)
        fb = np.where(dat > 0, np.clip((Q - dgt) / dat, 0.0, 1.0), 0.0)
    return q * (lt_s | gt_b) + q * at_s * fs[idx] + q * at_b * fb[idx]


def ladder_cost(idx: np.ndarray, sell: np.ndarray, price: np.ndarray, q: np.ndarray, Q_h: np.ndarray, n: int) -> np.ndarray:
    """TCmin(Q) per hour: cost of the cheapest supply of Q_h along the sell ladder sorted by `price`."""
    s = np.flatnonzero(sell)
    ii, pp, qq = idx[s], price[s], q[s]
    o = np.lexsort((pp, ii))
    ii, pp, qq = ii[o], pp[o], qq[o]
    cs = np.cumsum(qq)
    first = np.r_[True, ii[1:] != ii[:-1]]
    start = (cs - qq)[first]
    cnt = np.diff(np.r_[np.flatnonzero(first), len(ii)])
    before = cs - qq - np.repeat(start, cnt)
    take = np.clip(Q_h[ii] - before, 0.0, qq)
    return np.bincount(ii, weights=take * pp, minlength=n)


def month(ym: str, S: pd.Series, gas: set, px: pd.DataFrame, country: pd.Series, rhos: list[float]):
    t0 = time.time()
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    for c in ("unit", "side", "status"):
        b[c] = b[c].astype(str)
    days = b.groupby("date").period.max()
    b = b[b.date.isin(days[days == 24].index) & b.date.isin(S.index)]
    idg = cleared_by_period(b)[KEY + ["identity_gap"]]
    b = b.merge(px, on=KEY, how="inner")
    b["hid"] = hid(b.date, b.period)
    b["price_eur_mwh"] = b.price_eur_mwh.astype("float64")
    e = effective(b)
    rc, _ = reclear(e)
    hrs = (b[KEY + ["hid", "p_star", "split"]].drop_duplicates("hid").merge(idg, on=KEY, how="left").merge(rc, on="hid", how="left"))
    hrs["valid"] = ((~hrs.split) & (hrs.identity_gap <= IDENTITY_TOL) & ((hrs.p_clear - hrs.p_star).abs() <= VALID_ERR))
    hrs["S"] = hrs.date.map(S)
    cl = b[b.status == "C"]
    hrs = hrs.merge(cl[cl.side == "C"].groupby("hid").power_mw.sum().rename("buy_actual").astype("float64"), on="hid", how="left")
    hrs = hrs.merge(cl[(cl.side == "V") & cl.unit.isin(gas)].groupby("hid").power_mw.sum().rename("gas_actual").astype("float64"),
                    on="hid", how="left").fillna({"buy_actual": 0.0, "gas_actual": 0.0})
    del b, cl
    vh = hrs.loc[hrs.valid, "hid"].to_numpy()
    e = e[e.hid.isin(vh)]
    hidv = e.hid.to_numpy()
    uh, idx = np.unique(hidv, return_inverse=True)
    n = len(uh)
    sell = (e.side.to_numpy() == "V")
    q = e.power_mw.to_numpy().astype("float64")
    q32 = e.power_mw.to_numpy()
    price = e.price_eur_mwh.to_numpy().astype("float64")
    Sd = e.date.map(S).to_numpy().astype("float64")
    icn, pt, g = unit_flags(e.unit.to_numpy(), gas, country)
    mine = sell & g
    Sdm = np.where(mine, Sd, 0.0)
    sc = np.where(icn, 4, np.where(g & pt, 1, np.where(g, 0, np.where(pt, 3, 2))))
    bc_ = np.where(icn, 7, np.where(pt, 6, 5))
    cls = np.where(sell, sc, bc_)
    side_arr = e.side.to_numpy()
    p_o = rc.set_index("hid").p_clear.reindex(uh).to_numpy()
    acc_o = settle(idx, sell, price, q, p_o, n)
    Q_o = np.bincount(idx, weights=acc_o * sell, minlength=n)
    Qb_o = np.bincount(idx, weights=acc_o * ~sell, minlength=n)
    prow_o = p_o[idx]
    kc = lambda w: np.bincount(cls, weights=w, minlength=8)  # noqa: E731

    rows, hourly = [], []
    for r in rhos:
        price2 = price + r * Sdm
        e2 = pd.DataFrame({"hid": hidv, "price_eur_mwh": price2, "power_mw": q32, "side": side_arr})
        rc1, _ = reclear(e2)
        p_c = rc1.set_index("hid").p_clear.reindex(uh).to_numpy()
        ok = ~(np.isnan(p_o) | np.isnan(p_c))
        okr = ok[idx]
        acc_c = settle(idx, sell, price2, q, p_c, n)
        Q_c = np.bincount(idx, weights=acc_c * sell, minlength=n)
        Qb_c = np.bincount(idx, weights=acc_c * ~sell, minlength=n)
        prow_c = p_c[idx]
        # the true cost of an accepted sell row is `price2` in BOTH worlds (counterfactual offer = true cost)
        w_o = np.where(okr, acc_o, 0.0)
        w_c = np.where(okr, acc_c, 0.0)
        rev_o, rev_c = kc(w_o * np.nan_to_num(prow_o)), kc(w_c * np.nan_to_num(prow_c))   # payment for buys, revenue for sells
        val_o, val_c = kc(w_o * np.where(sell, price2, price)), kc(w_c * np.where(sell, price2, price))
        vol_o, vol_c = kc(w_o), kc(w_c)
        sub_o = kc(w_o * Sdm)                                # subsidy received in the observed world, by seller class
        gbh_o = np.bincount(idx, weights=w_o * ~sell * price, minlength=n)
        gbh_c = np.bincount(idx, weights=w_c * ~sell * price, minlength=n)
        tch_o = np.bincount(idx, weights=w_o * sell * price2, minlength=n)
        tch_c = np.bincount(idx, weights=w_c * sell * price2, minlength=n)
        tcmin_o = ladder_cost(idx, sell, price2, q, np.where(ok, Q_o, 0.0), n)
        tcmin_c = ladder_cost(idx, sell, price2, q, np.where(ok, Q_c, 0.0), n)
        okh = ok.astype("float64")
        W_o, W_c = (gbh_o - tch_o) * okh, (gbh_c - tch_c) * okh
        alloc = (tch_o - tcmin_o) * okh
        quant = ((gbh_c - tcmin_c) - (gbh_o - tcmin_o)) * okh
        row = {"month": ym, "rho": r, "hours_ok": int(ok.sum()), "hours_nan": int((~ok).sum())}
        for k, c in enumerate(CLS):
            row[f"vol_o_{c}"], row[f"vol_c_{c}"] = vol_o[k], vol_c[k]
            row[f"rev_o_{c}"], row[f"rev_c_{c}"] = rev_o[k], rev_c[k]
            row[f"val_o_{c}"], row[f"val_c_{c}"] = val_o[k], val_c[k]      # sells: true cost; buys: gross benefit
            row[f"sub_o_{c}"] = sub_o[k]
        row.update({"W_o": W_o.sum(), "W_c": W_c.sum(), "alloc": alloc.sum(), "quant": quant.sum(),
                    "tcmin_o": (tcmin_o * okh).sum(), "tcmin_c": (tcmin_c * okh).sum(), "tc_c": (tch_c * okh).sum(),
                    "tc_o": (tch_o * okh).sum(), "gb_o": (gbh_o * okh).sum(), "gb_c": (gbh_c * okh).sum()})
        # checks, hour by hour
        row["bal_o_bad"] = int((np.abs((Q_o - Qb_o))[ok] > BAL_TOL_MW).sum())
        row["bal_c_bad"] = int((np.abs((Q_c - Qb_c))[ok] > BAL_TOL_MW).sum())
        row["lad_c_maxabs"] = float(np.abs(tch_c - tcmin_c)[ok].max()) if ok.any() else 0.0
        dw = W_c - W_o
        row["neg_dwl_hours"] = int((dw[ok] < -HOUR_TOL_EUR).sum())
        row["neg_dwl_sum"] = float(dw[ok][dw[ok] < -HOUR_TOL_EUR].sum())
        row["fixed_leg_bad"] = int((np.abs(vol_o[[4, 7]] - vol_c[[4, 7]]) > 1e-6 * max(1.0, vol_o[[4, 7]].sum())).sum())
        row["pay_rev_gap_eur"] = float(abs(rev_o[5:].sum() - rev_o[:5].sum())) + float(abs(rev_c[5:].sum() - rev_c[:5].sum()))
        rows.append(row)
        hourly.append(pd.DataFrame({"hid": uh, "rho": r, "ok": ok, "p_o": p_o, "p_c": p_c, "Q_o": Q_o, "Q_c": Q_c,
                                    "dwl": dw, "alloc": alloc, "quant": quant}))
    hr = hrs.assign(month=ym)[["month", "hid", "date", "period", "valid", "S", "p_clear", "buy_actual", "gas_actual"]]
    hr = hr.merge(pd.DataFrame({"hid": uh, "q_obs_reclear": Q_o}), on="hid", how="left")
    print(f"  {ym}: {len(hrs)} hours, valid {hrs.valid.sum()} ({hrs.valid.mean():.3f}); "
          f"{len(e):,} effective rows; {time.time() - t0:.0f} s", flush=True)
    return rows, pd.concat(hourly, ignore_index=True), hr


def aggregate(R: pd.DataFrame, esios_bill: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ledger and headline per rho from summed monthly rows (EUR m)."""
    m = 1e6
    led, head = [], []
    for r, d in R.groupby("rho"):
        s = d.drop(columns=["month"]).sum()
        D = lambda kind, c: (s[f"{kind}_o_{c}"] - s[f"{kind}_c_{c}"]) / m  # noqa: E731
        sub_es, sub_pt = s["sub_o_gas_es"] / m, s["sub_o_gas_pt"] / m
        plug = esios_bill / m - sub_es
        P = {
            "Spanish buyers": D("val", "es") - D("rev", "es") - esios_bill / m,
            "Portuguese buyers": D("val", "pt") - D("rev", "pt") - sub_pt,
            "exporters (interconnection)": D("val", "exp") - D("rev", "exp"),
            "modelled gas, Spain": D("rev", "gas_es") - D("val", "gas_es") + sub_es,
            "modelled gas, Portugal": D("rev", "gas_pt") - D("val", "gas_pt") + sub_pt,
            "other recipients of the Spanish bill (not modelled)": plug,
            "other generators, Spain": D("rev", "oth_es") - D("val", "oth_es"),
            "other generators, Portugal": D("rev", "oth_pt") - D("val", "oth_pt"),
            "importers (interconnection)": D("rev", "imp") - D("val", "imp"),
        }
        where = {"Spanish buyers": "Spain", "Portuguese buyers": "outside Spain", "exporters (interconnection)": "outside Spain",
                 "modelled gas, Spain": "Spain", "modelled gas, Portugal": "outside Spain",
                 "other recipients of the Spanish bill (not modelled)": "Spain", "other generators, Spain": "Spain",
                 "other generators, Portugal": "outside Spain", "importers (interconnection)": "outside Spain"}
        for k, v in P.items():
            led.append({"rho": r, "party": k, "side": where[k], "change_eur_m": v})
        dW = (s["W_o"] - s["W_c"]) / m
        tot = sum(P.values())
        N = -P["Spanish buyers"]
        es_sellers = sum(v for k, v in P.items() if where[k] == "Spain" and k != "Spanish buyers")
        outside = sum(v for k, v in P.items() if where[k] == "outside Spain")
        dwl = -dW
        head.append({
            "rho": r, "spanish_buyers_net_loss": N, "dwl": dwl, "dwl_allocation": s["alloc"] / m, "dwl_quantity": s["quant"] / m,
            "net_gain_spanish_sellers": es_sellers, "net_gain_outside_spain": outside,
            "outside_portugal_buyers_and_plants": P["Portuguese buyers"] + P["modelled gas, Portugal"] + P["other generators, Portugal"],
            "outside_exporters": P["exporters (interconnection)"], "outside_importers": P["importers (interconnection)"],
            "ledger_total": tot, "welfare_change": dW,
            "identity_gap": tot - dW,
            "decomp_gap": N - (dwl + es_sellers + outside),
            "dwl_share_of_N": dwl / N if N else np.nan,
            "transfer_share_of_N": es_sellers / N if N else np.nan,
            "outside_share_of_N": outside / N if N else np.nan,
            "delta_pay_spain": D("rev", "es"), "delta_pay_portugal": D("rev", "pt"), "delta_pay_exports": D("rev", "exp"),
            "delta_gb_spain": D("val", "es"), "delta_gb_portugal": D("val", "pt"), "delta_gb_exports": D("val", "exp"),
            "delta_rev_gas_es": D("rev", "gas_es"), "delta_rev_gas_pt": D("rev", "gas_pt"),
            "delta_rev_other_es": D("rev", "oth_es"), "delta_rev_other_pt": D("rev", "oth_pt"), "delta_rev_imports": D("rev", "imp"),
            "delta_tc_gas": D("val", "gas_es") + D("val", "gas_pt"), "delta_tc_other": D("val", "oth_es") + D("val", "oth_pt"),
            "delta_tc_imports": D("val", "imp"),
            "subsidy_model_es": sub_es, "subsidy_model_pt": sub_pt, "esios_bill_spain": esios_bill / m,
            "bill_not_tied_to_modelled_plants": plug,
            "q_obs_gwh": sum(s[f"vol_o_{c}"] for c in SELL) / 1e3, "q_cf_gwh": sum(s[f"vol_c_{c}"] for c in SELL) / 1e3,
            "iberian_view_welfare_change": dW - (P["exporters (interconnection)"] + P["importers (interconnection)"]),
        })
    return pd.DataFrame(led), pd.DataFrame(head)


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    ap.add_argument("--rhos", nargs="*", type=float)
    ap.add_argument("--units", choices=["panel", "ccgt_coal"], default="panel")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    months = [m for m in MONTHS if not a.months or m in a.months]
    rhos = a.rhos or RHOS
    usfx = "" if a.units == "panel" else f"_{a.units}"
    sfx = usfx + ("" if len(months) == len(MONTHS) and not a.rhos else "_" + "_".join(months) + ("" if not a.rhos else "_r" + "-".join(f"{x:g}" for x in rhos)))
    S, gas = subsidy_and_units()
    gas = wider(gas, a.units)
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "country"]).drop_duplicates("unit")
    country = reg.set_index("unit").country
    print(f"{len(gas)} modelled gas units; subsidy on {len(S)} days (mean S {S.mean():.1f}); rhos {rhos}; months {months}", flush=True)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "price_es", "price_pt", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.resolution_min == 60]
    px = px.assign(split=px.price_es != px.price_pt).rename(columns={"price_es": "p_star"})[KEY + ["p_star", "split"]]
    t0 = time.time()
    rows, hours, hr = [], [], []
    if a.workers > 1:
        from multiprocessing import Pool
        with Pool(a.workers) as pool:
            res = pool.starmap(month, [(ym, S, gas, px, country, rhos) for ym in months])
    else:
        res = [month(ym, S, gas, px, country, rhos) for ym in months]
    for r_, h_, x_ in res:
        rows += r_
        hours.append(h_)
        hr.append(x_)
    print(f"all months: {time.time() - t0:.0f} s", flush=True)
    R = pd.DataFrame(rows)
    H = pd.concat(hours, ignore_index=True)
    HR = pd.concat(hr, ignore_index=True)
    HR["date"] = pd.to_datetime(HR.date)

    # valid-hour accounting
    V = HR[HR.valid]
    mo = HR.groupby("month").apply(lambda d: pd.Series({
        "hours": len(d), "valid": int(d.valid.sum()), "dropped": int((~d.valid).sum()),
        "bill_valid_eur_m": float((d.S * d.gas_actual)[d.valid].sum() / 1e6),
        "bill_dropped_eur_m": float((d.S * d.gas_actual)[~d.valid].sum() / 1e6)}), include_groups=False).reset_index()
    tot = mo.drop(columns="month").sum()
    mo = pd.concat([mo, pd.DataFrame([{"month": "all", **tot.to_dict()}])], ignore_index=True)
    mo.to_csv(T / f"gas_cap_dispatch_welfare_hours{sfx}.csv", index=False)
    print(mo.round(1).to_string(index=False), flush=True)

    # ESIOS charge on the same valid hours
    D = pd.concat([esios(i) for i in (351, 352, 353, 1907, 1908, 1909)], axis=1).reset_index()
    M = V[["date", "period"]].merge(D, on=KEY, how="left").fillna(0.0)
    esios_bill = float((M["1908"] * M["351"] + M["1909"] * M["352"] + M["1907"] * M["353"]).sum())

    led, head = aggregate(R, esios_bill)
    Hq = H.merge(HR[["hid", "buy_actual"]], on="hid", how="left")
    Hq = Hq[Hq.ok]
    fo = (Hq.assign(x=(Hq.p_c - Hq.p_o) * Hq.buy_actual).groupby("rho").x.sum() / 1e6).rename("first_order_saving_all_buyers")
    head = head.merge(fo.reset_index(), on="rho")
    head["surplus_gain_all_buyers_before_charge"] = head.delta_gb_spain + head.delta_gb_portugal + head.delta_gb_exports \
        - head.delta_pay_spain - head.delta_pay_portugal - head.delta_pay_exports
    head["volume_response_correction"] = head.surplus_gain_all_buyers_before_charge - head.first_order_saving_all_buyers
    R.to_csv(T / f"gas_cap_dispatch_welfare_monthly{sfx}.csv", index=False)
    led.to_csv(T / f"gas_cap_dispatch_welfare_ledger{sfx}.csv", index=False)
    head.to_csv(T / f"gas_cap_dispatch_welfare_headline{sfx}.csv", index=False)
    head.to_csv(T / f"gas_cap_dispatch_welfare{sfx}.csv", index=False)
    H = H.merge(HR[["hid", "month", "date", "period"]], on="hid", how="left")
    H.to_parquet(T / f"gas_cap_dispatch_welfare_hourly{sfx}.parquet", index=False)

    # checks
    chk = []
    sv = T / f"gas_cap_consumer_saving_hourly{usfx}.parquet"
    if sv.exists():
        S0 = pd.read_parquet(sv)
        Ho = H[H.ok]
        for r in rhos:
            x = Ho[Ho.rho == r].merge(S0[["hid", "p_clear", f"p0_{r:.2f}"]], on="hid", how="inner") if f"p0_{r:.2f}" in S0.columns else None
            if x is None:
                continue
            chk.append({"check": "C1 p_cf equals saving script's p0", "rho": r, "hours": len(x),
                        "value": float(((x.p_c - x[f"p0_{r:.2f}"]).abs() <= 0.011).mean()), "pass_if": ">= 0.999"})
        x = Ho[Ho.rho == rhos[0]].merge(S0[["hid", "p_clear"]], on="hid")
        chk.append({"check": "C1 p_obs equals saving script's p_clear", "rho": np.nan, "hours": len(x),
                    "value": float(((x.p_o - x.p_clear).abs() <= 0.011).mean()), "pass_if": ">= 0.999"})
    nh = int(R.groupby("rho").hours_ok.sum().iloc[0])
    d0 = T / f"gas_cap_consumer_saving{usfx}.csv"
    if d0.exists() and len(months) == len(MONTHS):
        G0 = pd.read_csv(d0).set_index("rho").gross_eur_m
        for r in rhos:
            if round(r, 2) in G0.index.round(2):
                g0 = float(G0[np.isclose(G0.index, r)].iloc[0])
                chk.append({"check": "C8 first-order saving (all buyers, EUR m) minus D's gross saving", "rho": r, "hours": nh,
                            "value": float(fo[r] - g0), "pass_if": "|.| <= 1"})
    chk.append({"check": "hours with no clearing price in a world (dropped from that rho)", "rho": np.nan, "hours": nh,
                "value": int(R.hours_nan.sum()), "pass_if": "report"})
    for k, lab, rule in (("bal_o_bad", "C2 hours volume bought != volume sold, observed", "<= 0.1% of hours"),
                         ("bal_c_bad", "C2 same, counterfactual", "<= 0.1% of hours"),
                         ("neg_dwl_hours", "C4 hours with W_cf < W_obs - EUR 1", "<= 0.1% of hours"),
                         ("fixed_leg_bad", "C6 interconnection volumes differ between worlds", "== 0")):
        chk.append({"check": lab, "rho": np.nan, "hours": nh, "value": int(R[k].sum()), "pass_if": rule})
    chk.append({"check": "C2 max |payments - revenue| per rho (EUR, total)", "rho": np.nan, "hours": nh,
                "value": float(R.pay_rev_gap_eur.max()), "pass_if": "<= EUR 1 per hour"})
    chk.append({"check": "C4 TC of counterfactual dispatch vs ladder TCmin(Q_cf), max |gap| in an hour (EUR)", "rho": np.nan,
                "hours": nh, "value": float(R.lad_c_maxabs.max()), "pass_if": "~0"})
    for r, d in R.groupby("rho"):
        chk.append({"check": "C4 sum of negative hourly DWL / total DWL", "rho": r, "hours": int(d.hours_ok.sum()),
                    "value": float(d.neg_dwl_sum.sum() / (d.W_c.sum() - d.W_o.sum())), "pass_if": "<= 0.001 in magnitude"})
    qv = V.dropna(subset=["q_obs_reclear"])
    gap = (qv.q_obs_reclear - qv.buy_actual) / qv.buy_actual
    chk.append({"check": "C5 re-cleared observed volume vs actual cleared buys: mean gap", "rho": np.nan, "hours": len(qv),
                "value": float(gap.mean()), "pass_if": "|mean| <= 0.005"})
    chk.append({"check": "C5 same: mean |gap|", "rho": np.nan, "hours": len(qv), "value": float(gap.abs().mean()), "pass_if": "report"})
    chk.append({"check": "C5 same: 95th percentile of |gap|", "rho": np.nan, "hours": len(qv), "value": float(gap.abs().quantile(0.95)),
                "pass_if": "report"})
    chk.append({"check": "bill: model subsidy S x re-cleared observed MWh (modelled units, EUR m)", "rho": np.nan, "hours": len(qv),
                "value": float((head.subsidy_model_es + head.subsidy_model_pt).iloc[0]), "pass_if": "vs S x actual cleared"})
    chk.append({"check": "bill: S x actual cleared MWh of the modelled units (EUR m)", "rho": np.nan, "hours": len(qv),
                "value": float((V.S * V.gas_actual).sum() / 1e6), "pass_if": "report"})
    for r, d in head.groupby("rho"):
        chk.append({"check": "C3 ledger total - welfare change (EUR m)", "rho": r, "hours": nh, "value": float(d.identity_gap.iloc[0]),
                    "pass_if": "|.| <= 0.01"})
        chk.append({"check": "C3 N - (DWL + Spanish sellers + outside Spain) (EUR m)", "rho": r, "hours": nh, "value": float(d.decomp_gap.iloc[0]),
                    "pass_if": "|.| <= 0.01"})
        chk.append({"check": "C3 DWL - (allocation + quantity) (EUR m)", "rho": r, "hours": nh,
                    "value": float((d.dwl - d.dwl_allocation - d.dwl_quantity).iloc[0]), "pass_if": "|.| <= 0.01"})
    dwl = head.sort_values("rho").dwl.to_numpy()
    chk.append({"check": "C7 DWL non-decreasing in rho (1 = yes)", "rho": np.nan, "hours": nh, "value": int(np.all(np.diff(dwl) >= -1e-6)),
                "pass_if": "report"})
    C = pd.DataFrame(chk)
    C.to_csv(T / f"gas_cap_dispatch_welfare_checks{sfx}.csv", index=False)
    pd.set_option("display.width", 220)
    print("\nchecks:\n" + C.to_string(index=False))
    show = head[head.rho.isin([0.55, 0.73, 1.0])].set_index("rho").T
    print("\nheadline (EUR m, valid hours):\n" + show.round(2).to_string())
    print("\nledger:\n" + led[led.rho.isin([0.55, 0.73, 1.0])].pivot(index="party", columns="rho", values="change_eur_m").round(0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
