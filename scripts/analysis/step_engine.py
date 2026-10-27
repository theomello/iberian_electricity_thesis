#!/usr/bin/env python3
"""Resampled residual demand for every thermal owner's offer curve: where each of its steps clears.

    .venv/bin/python scripts/analysis/step_curves.py              # input
    .venv/bin/python scripts/analysis/step_engine.py --months 201906 [...]

Step-offer design (`docs/specs/2026-10-01-step-offer-design.md` §3). A firm offers a
step curve before it knows its residual demand. Each step's price and length satisfy
a first-order condition in expectation over the residual demands it could face
(Wolak 2007; Kastl 2011; Reguant 2014). This script builds those expectations.

FOR EACH TARGET (group f, hour H) where f offers a gas or coal step (`--kind thermal`), or
a storage or pumped-storage hydro step above MIN_PRICE_HYDRO (`--kind hydro`, 2026-10-06):
  own curve   f's exposed offers in H (effective curve, `step_curves.py`), both sides
  draws       N_DRAWS hours at the same clock hour within ±WINDOW days (H's own day
              left out), valid, nearest to H in REE's D-1 forecast of net load
              (demand − wind − solar). In each, the rivals' curve is that hour's curve
              minus f's own offers in it, shifted horizontally to H's forecasts:
                  Δ = (1 − d_f)·ΔF_demand − (1 − w_f)·ΔF_wind − (1 − s_f)·ΔF_solar
              d_f: f's share of the hour's buy offers; w_f, s_f: f's share of REE's
              registered wind and PV (`intraday_surprise_test.shares`). A forecast moves
              rivals' demand and zero-priced renewables, which are horizontal shifts.
  clearing    f's own curve against each draw's rivals: the price p*, f's net position
              n at p*, rivals' slope |RD′| (rivals' MW offered within ±H_BAND of p*,
              both sides, over 2·H_BAND, as in firm_x.py), X = n / |RD′| (NaN below
              MIN_SLOPE MW per €/MWh).
  events      for each of f's own price points q_k: MARGINAL when p* = q_k (the firm's
              step sets the price), GAP when q_k < p* < q_k+1 (rivals set the price
              between f's step k and its next one).

THE REALISED DRAW. The same clearing on H's own rivals with no shift is the one-draw
(ex-post) case; it must reproduce p*, which `realised_ok` checks.

WRITES outputs/cache/step/moments_YYYYMM.parquet (hydro: hmoments_YYYYMM), one row per
(H, f, own price q_k) at which f offers gas or coal (hydro): v_sell, v_buy, q_next, n_draws, and over the draws:
  m_n, m_sn, m_s, m_x, m_xn  marginal: count; sums of n, |RD′|, X; count with X defined
  m_s_rel                    sum of |RD′| on a band of ±5% of p (at least ±2.5 €/MWh),
                             which keeps the window's width relative to the price level
  g_n, g_p, g_x, g_xn, g_s   gap above q_k: count; sums of p*, X; X defined; |RD′|
and realised: r_event (1 marginal at q_k, 2 gap above q_k, 0 neither), r_p, r_n, r_s.
Also moments_targets_YYYYMM.parquet: per target, the draws' mean and sd of p*, H's p*
and the realised clearing price.

AT COST (`--comp`; thermal 2026-10-07, hydro `--kind hydro --comp` the same day). The same draws, with f's own gas and coal
steps moved from their offer prices to their unit's cost (`cost` in units_YYYYMM): the
curve f would offer as a price-taker in its thermal plant, everything else as offered.
X evaluated there does not depend on f's thermal offer prices, so it does not carry an
unobserved part of their cost; it is the instrument for X̃ in `step_estimator.py`
(evaluating the endogenous term at the unobservable's value zero, as Berry, Levinsohn &
Pakes 1999 approximate optimal instruments). Writes compcost_YYYYMM.parquet, one row per
(H, f, unit) for f's non-withdrawn thermal units:
  cm_n, cm_sn, cm_s   draws in which the unit's cost point sets the price: count, sums of n, |RD′|
  ck_n, ck_sn, ck_s   draws whose price lies within ±H_BAND of the unit's cost
  ak_n, ak_sn, ak_s   the same band on the ACTUAL curve (a check: it keeps f's other offers)
  kn_sn, kn_s, kn_dist  the NEAR draws whose price is nearest the cost: sums of n, |RD′|, and
                      their mean distance from it (always defined)
  cbar, kb_sn, kb_s   the same at the day's median cost of the unit's fuel instead of its own
                      cost, so that an error in one unit's cost cannot enter
  moved_mw, offer_mw  thermal MW found in f's curve at the unit's offer prices and moved
HYDRO AT COST writes hcompcost_YYYYMM.parquet, the same columns: f's storage and pumped
hydro steps above MIN_PRICE_HYDRO moved to the unit's price-taking water value λ*30s
(`build_water_value_forward.py`, known at D−2), and "fuel" is the hydro class, so cbar is
the day's median λ* over the class. Units without λ* keep their offers.

SIMULATED PRICE-TAKERS (`--sim SEED`, 2026-10-08). Is a negative β an artefact of the
estimator? f's thermal (hydro: storage and pumped above MIN_PRICE_HYDRO, with λ*30s) steps
are moved to cost + noise that ignores f's stake in the price, so β = 0 by construction,
and the moments are rebuilt on that curve with the same draws (rivals as offered). The
noise is the unit's own offers reshuffled (`simulate`). Writes sim<SEED>_units_YYYYMM
(hydro: hsim<SEED>_units), the units file with `price` the simulated price and
`price_offer` the offer, and sim<SEED>_moments_YYYYMM (hsim<SEED>_moments), the moments
file's columns at the simulated prices (the realised-draw columns left out). The
estimators read them with `--sim SEED` (`price_taking_simulation.py`).

DRAW PRICES AT COST (`--comp-price`, 2026-10-08). The simulation shows the cause: a step
enters only where draws' prices reach it, so the kept steps' gap rises with where the
hour's prices sit above the unit's cost, and the instruments move with that too. The
correction controls for it, read where f's own offers cannot enter: the same draws as
`--comp`, f at cost, and per target (H, f) the mean, sd and 10/50/90th percentiles of the
draws' prices (cp_*). Writes compcostprice_YYYYMM (hydro hcompcostprice_YYYYMM).
"""
from __future__ import annotations

import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from intraday_surprise_test import shares  # noqa: E402

CACHE = ROOT / "outputs/cache/step"
N_DRAWS = 40
WINDOW = 28            # days
H_BAND = 5.0           # €/MWh
REL_BAND = 0.05        # the price-scaled band: ±5% of p ...
MIN_REL_BAND = 2.5     # ... and at least ±2.5 €/MWh (equal to H_BAND at p = 100)
MIN_SLOPE = 5.0        # MW per €/MWh
OFF, W = 1000.0, 20000.0          # price keys: hour_index * W + price + OFF
OFF2, W2 = 2.0e5, 1.0e6           # value keys: hour_index * W2 + ES + OFF2
SENTINEL = -999.0
NEAR = 5               # --comp: draws nearest the unit's cost


def months_around(ym: str) -> list[str]:
    p = pd.Period(ym, "M")
    return [str(p + k).replace("-", "") for k in (-1, 0, 1)]


KINDS = {"thermal": ("units", "moments"), "hydro": ("hydro", "hmoments")}
COMP_OUT = {"thermal": "compcost", "hydro": "hcompcost"}
SIM_OUT = {"thermal": "sim", "hydro": "hsim"}
WATER_VALUE = ROOT / "outputs/tables/water_value_forward.parquet"
MIN_PRICE_HYDRO = 1.0   # €/MWh: hydro blocks at zero tie with every renewable and never carry a choice
# --sim-scale: a firm-specific water value m × λ*30s for the simulated price-takers, m the firm's
# offer / λ*30s at its expected running share net of bilateral contracts (rq-water-value-forward.md
# §5.5; Movhera gross, §5; others 1). Tests whether firms that simply value water differently
# from λ* make β look positive.
WATER_SCALE = {"EDP": 0.95, "IBERDROLA": 1.11, "NATURGY": 1.22, "ENDESA": 1.35, "MOVHERA": 0.93}


def load(ym: str, kind: str = "thermal") -> tuple:
    have = [m for m in months_around(ym) if (CACHE / f"hours_{m}.parquet").exists()]
    hours = pd.concat([pd.read_parquet(CACHE / f"hours_{m}.parquet") for m in have], ignore_index=True)
    hours = hours.sort_values("hid", ignore_index=True)
    market = pd.concat([pd.read_parquet(CACHE / f"market_{m}.parquet") for m in have], ignore_index=True)
    own = pd.concat([pd.read_parquet(CACHE / f"own_{m}.parquet") for m in have], ignore_index=True)
    units = pd.read_parquet(CACHE / f"{KINDS[kind][0]}_{ym}.parquet")
    if kind == "hydro":
        units = units[units.price > MIN_PRICE_HYDRO]
    return hours, market, own, units


class Block:
    """Market and own curves of every hour in a 3-month block, as flat sorted arrays."""

    def __init__(self, hours: pd.DataFrame, market: pd.DataFrame, own: pd.DataFrame):
        self.hours = hours
        self.hidx = pd.Series(np.arange(len(hours)), index=hours.hid.to_numpy())
        sent = pd.DataFrame({"hid": hours.hid.to_numpy(), "price": SENTINEL, "a": 0.0})
        mk = pd.concat([sent, market[market.hid.isin(hours.hid)]], ignore_index=True)
        mk = mk.sort_values(["hid", "price"], kind="stable", ignore_index=True)
        self.mk = mk
        hi = self.hidx.reindex(mk.hid.to_numpy()).to_numpy()
        self.mk_hi = hi
        self.kp = hi * W + mk.price.to_numpy() + OFF
        self.price = mk.price.to_numpy()
        self.a = mk.a.to_numpy()
        self.d_tot = hours.d_tot.fillna(0.0).to_numpy()
        self.start = np.searchsorted(hi, np.arange(len(hours)), side="left")
        self.end = np.searchsorted(hi, np.arange(len(hours)), side="right")
        self.own = own
        self._g: dict = {}

    def rivals(self, g: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """For group g: rivals' cumulative MW at each market row (a − own), rivals'
        total buy MW per hour, and the value keys of rivals' excess supply."""
        if g in self._g:
            return self._g[g]
        o = self.own[self.own.group == g]
        o = o.assign(v=o.v_sell + o.v_buy)
        m = self.mk[["hid", "price"]].merge(o[["hid", "price", "v"]], on=["hid", "price"], how="left")
        own_a = m.v.fillna(0.0).groupby(m.hid.to_numpy()).cumsum().to_numpy()
        a_r = self.a - own_a
        d_own = o.groupby("hid").v_buy.sum().reindex(self.hours.hid).fillna(0.0).to_numpy()
        d_r = self.d_tot - d_own
        es = a_r - d_r[self.mk_hi]
        kv = self.mk_hi * W2 + es + OFF2
        self._g[g] = (a_r, d_r, kv)
        return self._g[g]


def clear(blk: Block, g: str, q: np.ndarray, vs: np.ndarray, vb: np.ndarray, draws: np.ndarray,
          shift: np.ndarray) -> dict:
    """Clear own curve (q sorted, sell and buy MW at each) against rivals of each draw hour
    (block indices `draws`), each shifted right by `shift` MW. Returns per draw: p, n, s,
    kstar (index of own price at p, or -1), kgap (own price index below p, -1 if none)."""
    a_r, d_r, kv = blk.rivals(g)
    v = vs + vb
    A = np.cumsum(v)
    Down = vb.sum()
    ns_hi = A - Down
    ns_lo = ns_hi - v
    D, K = len(draws), len(q)
    qk = draws[:, None] * W + q[None, :] + OFF
    i_hi = np.searchsorted(blk.kp, qk, side="right") - 1
    i_lo = np.searchsorted(blk.kp, qk, side="left") - 1
    base = (d_r[draws] + shift)[:, None]
    es_r_hi = a_r[i_hi] - base
    es_r_lo = a_r[i_lo] - base
    tot_hi = es_r_hi + ns_hi[None, :]
    tot_lo = es_r_lo + ns_lo[None, :]
    ok = tot_hi >= 0
    has = ok.any(axis=1)
    k = np.where(has, ok.argmax(axis=1), K)
    rows = np.arange(D)
    kk = np.minimum(k, K - 1)
    at_q = has & (tot_lo[rows, kk] < 0)
    # rivals set the price: own net position constant between own prices
    n_const = np.where(k > 0, ns_hi[np.maximum(k - 1, 0)], ns_lo[0])
    # rivals' excess supply es_r = a_r - d_r - shift >= -n_const  <=>  a_r - d_r >= shift - n_const
    target = draws * W2 + (shift - n_const) + OFF2
    j = np.searchsorted(kv, target, side="left")
    j = np.minimum(j, blk.end[draws] - 1)
    p_gap = blk.price[j]
    p = np.where(at_q, q[kk], p_gap)
    # n at the clearing: pro rata on the vertical segment when the price sits on an own price
    need = -tot_lo[rows, kk]
    riv_at = es_r_hi[rows, kk] - es_r_lo[rows, kk]
    frac = np.clip(need / np.maximum(v[kk] + riv_at, 1e-9), 0.0, 1.0)
    n = np.where(at_q, ns_lo[kk] + frac * v[kk], n_const)
    # rivals' slope at p
    lo = np.searchsorted(blk.kp, draws * W + p - H_BAND + OFF, side="left") - 1
    hi = np.searchsorted(blk.kp, draws * W + p + H_BAND + OFF, side="right") - 1
    s = (a_r[hi] - a_r[lo]) / (2 * H_BAND)
    # the same with a band that scales with the price: ±REL_BAND of p, at least ±MIN_REL_BAND
    h_rel = np.maximum(MIN_REL_BAND, REL_BAND * np.abs(p))
    lo = np.searchsorted(blk.kp, draws * W + p - h_rel + OFF, side="left") - 1
    hi = np.searchsorted(blk.kp, draws * W + p + h_rel + OFF, side="right") - 1
    s_rel = (a_r[hi] - a_r[lo]) / (2 * h_rel)
    kstar = np.where(at_q, kk, -1)
    kgap = np.where(at_q, -1, k - 1)          # -1: below every own price
    return {"p": p, "n": n, "s": s, "s_rel": s_rel, "kstar": kstar, "kgap": kgap}


def at_cost(q: np.ndarray, vs: np.ndarray, vb: np.ndarray, uu: pd.DataFrame) -> tuple:
    """Own curve with the thermal steps in `uu` (price, mw, cost) moved to their cost.
    Only the MW actually present at a step's price is moved (the effective curve can hold
    less than offered). Returns q, vs, vb of the new curve and the moved MW per uu row."""
    pr = uu.price.to_numpy(float)
    th = pd.Series(uu.mw.to_numpy(float), index=pr).groupby(level=0).sum()
    have = pd.Series(vs, index=q).groupby(level=0).sum()
    scale = (np.minimum(th, have.reindex(th.index).fillna(0.0)) / th).fillna(0.0)
    moved = uu.mw.to_numpy(float) * scale.reindex(pr).to_numpy()
    take = pd.Series(moved, index=pr).groupby(level=0).sum()
    vs2 = vs - take.reindex(q).fillna(0.0).to_numpy()
    c = np.round(uu.cost.to_numpy(float), 2)
    cur = pd.DataFrame({"price": np.concatenate([q, c]), "vs": np.concatenate([vs2, moved]),
                        "vb": np.concatenate([vb, np.zeros(len(c))])})
    cur = cur.groupby("price", sort=True)[["vs", "vb"]].sum()
    cur = cur[(cur.vs > 1e-9) | (cur.vb > 1e-9)]
    return cur.index.to_numpy(float), cur.vs.to_numpy(float), cur.vb.to_numpy(float), moved


def draw(pool_key: np.ndarray, vals: np.ndarray, key: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """For each entry of `key`, one of `vals` drawn at random (with replacement) from the
    entries whose `pool_key` equals it."""
    o = np.argsort(pool_key, kind="stable")
    uniq, start, size = np.unique(pool_key[o], return_index=True, return_counts=True)
    i = np.searchsorted(uniq, key)
    return vals[o][start[i] + (rng.random(len(key)) * size[i]).astype(int)]


def simulate(t: pd.DataFrame, ym: str, seed: int, flat: pd.DataFrame | None,
             scale: dict[str, float] | None = None) -> pd.DataFrame:
    """Price-taking offers, β = 0 within the month by construction: every step of `t` (rows
    with a cost and a date) moved to cost + μ + δ + ε, rounded to cents. Not bounded: holding
    a price at the unit's lowest or highest offer would tie its gap to the cost (a fixed cap
    step's gap falls as λ* rises), a second mechanism; the estimators' own rules (hydro above
    €1, price-setting in a draw) select rows as for offers. `sim_out` marks prices outside the
    unit's offers that month, for a check.

    μ is the unit's mean gap (offer − cost) in the month, so the level is the unit's own and
    unit × month effects remove it; across months the simulated offers keep whatever the
    actual means carry, so only within-month estimates test the estimator. δ is a day effect
    drawn from the unit's day means in the month less their mean, ε a step deviation drawn
    from its steps less their day mean: the noise is as dispersed as the unit's offers that
    month, split the same way between days and steps, and independent of the hour it lands
    in. Within an hour the draws are sorted onto the steps in their order, which keeps the
    ladder (mw_below); on a flat unit-day (one curve for all 24 hours) the draws are made
    once for the day.

    `scale` (firm → m): the price-takers' true cost is m × cost, while `cost` stays as it was
    for the estimators. The random draws are the same as without it for the same seed."""
    rng = np.random.default_rng([seed, int(ym)])
    s = t.reset_index(drop=True).copy()
    unit = s.unit.astype(str).to_numpy()
    s["true"] = s.cost * (s.group.map(scale).fillna(1.0) if scale else 1.0)
    s["g"] = s.price.astype(float) - s.true
    s["mu"] = s.groupby("unit").g.transform("mean")
    s["a"] = s.groupby(["unit", "date"]).g.transform("mean")
    dy = s.groupby(["unit", "date"]).a.first().reset_index()
    du = dy.unit.astype(str).to_numpy()
    dev = (dy.a - dy.groupby("unit").a.transform("mean")).to_numpy()
    dy["delta"] = draw(du, dev, du, rng)
    s = s.merge(dy[["unit", "date", "delta"]], on=["unit", "date"], how="left")
    s["r"] = s.groupby(["unit", "hid"]).price.rank(method="first").astype(int) - 1
    fl = np.zeros(len(s), dtype=bool)
    if flat is not None:
        fl = s[["unit", "date"]].merge(flat, on=["unit", "date"], how="left").flat.fillna(False).to_numpy(bool)
    s["c"] = np.where(fl, unit + "|d" + s.date.dt.strftime("%Y%m%d").to_numpy(), unit + "|h" + s.hid.astype(str).to_numpy())
    cr = s[["c", "unit", "r"]].drop_duplicates(["c", "r"]).reset_index(drop=True)
    cr["eps"] = draw(unit, (s.g - s.a).to_numpy(), cr.unit.astype(str).to_numpy(), rng)
    cr = cr.sort_values(["c", "eps"], kind="stable")
    cr["r"] = cr.groupby("c").cumcount().to_numpy()
    s = s.merge(cr[["c", "r", "eps"]], on=["c", "r"], how="left")
    raw = np.round(s.true + s.mu + s.delta + s.eps, 2)
    lo = np.round(s.groupby("unit").price.transform("min").astype(float), 2)
    hi = np.round(s.groupby("unit").price.transform("max").astype(float), 2)
    s["sim_out"] = (raw < lo) | (raw > hi)
    s["sim"] = raw
    return s.drop(columns=["true", "g", "mu", "a", "delta", "r", "c", "eps"])


def month(ym: str, sh: pd.DataFrame, kind: str = "thermal", comp: bool = False, sim: int | None = None,
          price_only: bool = False, sim_scale: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    hours, market, own, units = load(ym, kind)
    if (comp or sim is not None) and kind == "hydro":    # cost = λ*30s, fuel = hydro class
        w = pd.read_parquet(WATER_VALUE, columns=["unit", "date", "lam30s"])
        w["date"] = w.date.astype("datetime64[ns]")
        units = units.assign(date=units.date.astype("datetime64[ns]")).merge(w, on=["unit", "date"], how="left")
        units = units.rename(columns={"lam30s": "cost"}).assign(fuel=units.cls)
    blk = Block(hours, market, own)
    h = hours.copy()
    h["nl"] = h.F_demand - h.F_wind - h.F_solar
    h["day"] = (pd.to_datetime(h.date) - pd.Timestamp("2018-01-01")).dt.days
    valid = h.valid.fillna(False).to_numpy()
    t_units = units[units.group.notna() & ~units.withdrawn]
    if sim is not None:
        t_units = t_units[t_units.cost.notna()].copy()
        flat = None
        if kind == "hydro":
            from step_estimator_hydro import flat_days          # heavy import, simulation only
            fh = pd.read_parquet(CACHE / f"hydro_{ym}.parquet")
            fh["date"] = fh.date.astype("datetime64[ns]")
            flat = flat_days(fh)
        else:
            t_units["date"] = t_units.hid.map(h.set_index("hid").date).astype("datetime64[ns]")
        t_units = simulate(t_units, ym, sim, flat, WATER_SCALE if sim_scale else None)
    own_idx = own.set_index(["hid", "group"]).sort_index()
    # --comp: the day's typical cost of each fuel, median over the units offering it (plain
    # hydro units carry no cost)
    cbar = (t_units.assign(date=t_units.hid.map(h.set_index("hid").date))
            .groupby(["date", "fuel"]).cost.median()) if comp else None
    shw = sh.set_index("group")
    out, tg = [], []
    in_month = pd.to_datetime(h.date).dt.strftime("%Y%m") == ym
    for hi_ in np.flatnonzero(in_month.to_numpy() & valid):
        H = h.iloc[hi_]
        cand = np.flatnonzero(valid & (h.period.to_numpy() == H.period) & (h.day.to_numpy() != H.day)
                              & (np.abs(h.day.to_numpy() - H.day) <= WINDOW))
        if len(cand) < 10:
            continue
        cand = cand[np.argsort(np.abs(h.nl.to_numpy()[cand] - H.nl), kind="stable")[:N_DRAWS]]
        gs = t_units.loc[t_units.hid == H.hid, "group"].unique()
        for g in gs:
            try:
                o = own_idx.loc[(H.hid, g)]
            except KeyError:
                continue
            o = o.sort_values("price")
            q = o.price.to_numpy(float)
            vs = o.v_sell.to_numpy(float)
            vb = o.v_buy.to_numpy(float)
            d_f = vb.sum() / H.d_tot if H.d_tot > 0 else 0.0
            w_f = shw.s_wind.get(g, 0.0)
            s_f = shw.s_pv.get(g, 0.0)
            dF = h.iloc[cand]
            shift = ((1 - d_f) * (H.F_demand - dF.F_demand.to_numpy())
                     - (1 - w_f) * (H.F_wind - dF.F_wind.to_numpy())
                     - (1 - s_f) * (H.F_solar - dF.F_solar.to_numpy()))
            if comp:
                uu = t_units[(t_units.hid == H.hid) & (t_units.group == g)]
                uu = uu[uu.cost.notna()]
                if uu.empty:
                    continue
                q2, vs2, vb2, moved = at_cost(q, vs, vb, uu)
                rc = clear(blk, g, q2, vs2, vb2, cand, shift)
                if price_only:                   # where the draws' prices sit with f at cost
                    pq = np.quantile(rc["p"], [0.1, 0.5, 0.9])
                    out.append(pd.DataFrame({"hid": [H.hid], "group": [g], "cp_mean": [rc["p"].mean()],
                                             "cp_sd": [rc["p"].std()], "cp_q10": [pq[0]], "cp_q50": [pq[1]],
                                             "cp_q90": [pq[2]], "n_draws": [len(cand)]}))
                    continue
                ra = clear(blk, g, q, vs, vb, cand, shift)
                cu = np.round(uu.cost.to_numpy(float), 2)
                ku = np.minimum(np.searchsorted(q2, cu), len(q2) - 1)
                ku = np.where(q2[ku] == cu, ku, -2)                 # -2: nothing offered at the cost
                cm = rc["kstar"][None, :] == ku[:, None]             # units x draws
                ck = np.abs(rc["p"][None, :] - cu[:, None]) <= H_BAND
                ak = np.abs(ra["p"][None, :] - cu[:, None]) <= H_BAND
                dist = np.abs(rc["p"][None, :] - cu[:, None])
                near = np.zeros_like(dist, dtype=bool)
                np.put_along_axis(near, np.argsort(dist, axis=1, kind="stable")[:, :NEAR], True, axis=1)
                cb = np.round(uu.fuel.map(cbar.loc[H.date]).to_numpy(float), 2)
                distb = np.abs(rc["p"][None, :] - cb[:, None])
                nearb = np.zeros_like(distb, dtype=bool)
                np.put_along_axis(nearb, np.argsort(distb, axis=1, kind="stable")[:, :NEAR], True, axis=1)
                out.append(pd.DataFrame({
                    "hid": H.hid, "group": g, "unit": uu.unit.to_numpy(), "offer": uu.price.to_numpy(float),
                    "cost": cu, "n_draws": len(cand),
                    "cm_n": cm.sum(1), "cm_sn": cm @ rc["n"], "cm_s": cm @ rc["s"],
                    "ck_n": ck.sum(1), "ck_sn": ck @ rc["n"], "ck_s": ck @ rc["s"],
                    "ak_n": ak.sum(1), "ak_sn": ak @ ra["n"], "ak_s": ak @ ra["s"],
                    "kn_sn": near @ rc["n"], "kn_s": near @ rc["s"], "kn_dist": (near * dist).sum(1) / NEAR,
                    "cbar": cb, "kb_sn": nearb @ rc["n"], "kb_s": nearb @ rc["s"],
                    "moved_mw": moved, "offer_mw": uu.mw.to_numpy(float)}))
                continue
            if sim is not None:                  # f's steps at their simulated prices
                uu = t_units[(t_units.hid == H.hid) & (t_units.group == g)]
                q, vs, vb, _ = at_cost(q, vs, vb, uu.assign(cost=uu.sim))
            r = clear(blk, g, q, vs, vb, cand, shift)
            K = len(q)
            x = np.where(r["s"] >= MIN_SLOPE, r["n"] / np.maximum(r["s"], 1e-9), np.nan)
            xd = np.isfinite(x)
            mk, gk = r["kstar"], r["kgap"]
            mm, gm = mk >= 0, gk >= 0

            def acc(idx, w):
                return np.bincount(idx, weights=w, minlength=K)

            row = pd.DataFrame({
                "hid": H.hid, "group": g, "price": q, "v_sell": vs, "v_buy": vb,
                "q_next": np.append(q[1:], np.inf), "n_draws": len(cand),
                "m_n": acc(mk[mm], np.ones(mm.sum())), "m_sn": acc(mk[mm], r["n"][mm]),
                "m_s": acc(mk[mm], r["s"][mm]), "m_s_rel": acc(mk[mm], r["s_rel"][mm]),
                "m_x": acc(mk[mm & xd], x[mm & xd]),
                "m_xn": acc(mk[mm & xd], np.ones((mm & xd).sum())),
                "g_n": acc(gk[gm], np.ones(gm.sum())), "g_p": acc(gk[gm], r["p"][gm]),
                "g_x": acc(gk[gm & xd], x[gm & xd]), "g_xn": acc(gk[gm & xd], np.ones((gm & xd).sum())),
                "g_s": acc(gk[gm], r["s"][gm]), "g_sn": acc(gk[gm], r["n"][gm]),
            })
            if sim is not None:
                out.append(row[row.price.isin(set(uu.sim.astype(float)))])
                continue
            rr = clear(blk, g, q, vs, vb, np.array([hi_]), np.zeros(1))
            ev = np.zeros(K, dtype=np.int8)
            if rr["kstar"][0] >= 0:
                ev[rr["kstar"][0]] = 1
            elif rr["kgap"][0] >= 0:
                ev[rr["kgap"][0]] = 2
            row["r_event"] = ev
            row["r_p"], row["r_n"], row["r_s"] = rr["p"][0], rr["n"][0], rr["s"][0]
            tp = set(t_units.loc[(t_units.hid == H.hid) & (t_units.group == g), "price"].astype(float))
            out.append(row[row.price.isin(tp)])
            tg.append({"hid": H.hid, "group": g, "p_star": H.p_star, "p_clear": H.p_clear,
                       "r_p": rr["p"][0], "draw_p_mean": r["p"].mean(), "draw_p_sd": r["p"].std(),
                       "n_own_prices": K, "shift_abs_mean": np.abs(shift).mean()})
    if comp:
        return pd.concat(out, ignore_index=True), pd.DataFrame()
    if sim is not None:
        sim_units = t_units.rename(columns={"price": "price_offer"}).rename(columns={"sim": "price"})
        return pd.concat(out, ignore_index=True), sim_units
    return pd.concat(out, ignore_index=True), pd.DataFrame(tg)


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="+", required=True)
    ap.add_argument("--kind", choices=list(KINDS), default="thermal")
    ap.add_argument("--comp", action="store_true",
                    help="own steps at cost: thermal (compcost_YYYYMM) or, with --kind hydro, at λ* (hcompcost)")
    ap.add_argument("--sim", type=int, default=None, metavar="SEED",
                    help="own steps at simulated price-taking prices (sim<SEED>_*, hydro hsim<SEED>_*)")
    ap.add_argument("--comp-price", action="store_true",
                    help="only the draws' prices on the at-cost curve (compcostprice_YYYYMM, hydro hcompcostprice)")
    ap.add_argument("--sim-scale", action="store_true",
                    help="with --sim, hydro: price-takers at WATER_SCALE × λ*30s (hsimw<SEED>_*)")
    args = ap.parse_args()
    if args.sim_scale and (args.sim is None or args.kind != "hydro"):
        ap.error("--sim-scale needs --sim and --kind hydro")
    sh = shares()
    out = KINDS[args.kind][1]
    for ym in args.months:
        t0 = time.time()
        if args.comp_price:
            m, _ = month(ym, sh, args.kind, comp=True, price_only=True)
            m.to_parquet(CACHE / f"{COMP_OUT[args.kind]}price_{ym}.parquet", index=False)
            print(f"  {ym}: {len(m):,} targets; draws' mean price at cost median {m.cp_mean.median():.1f}, "
                  f"sd median {m.cp_sd.median():.1f} ({time.time() - t0:.0f} s)", flush=True)
            continue
        if args.sim is not None:
            m, u = month(ym, sh, args.kind, sim=args.sim, sim_scale=args.sim_scale)
            pre = f"{SIM_OUT[args.kind]}{'w' if args.sim_scale else ''}{args.sim}"
            m.to_parquet(CACHE / f"{pre}_moments_{ym}.parquet", index=False)
            u.to_parquet(CACHE / f"{pre}_units_{ym}.parquet", index=False)
            sets = m.groupby(["hid", "group", "price"]).m_n.first() > 0
            print(f"  {ym}: {len(u):,} simulated steps (outside the unit's offers {u.sim_out.mean():.3f}); corr(simulated, "
                  f"offered) {np.corrcoef(u.price, u.price_offer)[0, 1]:.2f}; sd of the gap simulated "
                  f"{(u.price - u.cost).std():.1f} vs offered {(u.price_offer - u.cost).std():.1f}; "
                  f"price points setting p in ≥1 draw {sets.mean():.3f} ({time.time() - t0:.0f} s)", flush=True)
            continue
        if args.comp:
            m, _ = month(ym, sh, args.kind, comp=True)
            m.to_parquet(CACHE / f"{COMP_OUT[args.kind]}_{ym}.parquet", index=False)
            print(f"  {ym}: {len(m):,} unit-hours; MW moved {m.moved_mw.sum() / m.offer_mw.sum():.3f} of offered; "
                  f"cost point sets p in ≥1 draw {(m.cm_n > 0).mean():.3f}, price within ±{H_BAND:g} of cost in "
                  f"≥1 draw {(m.ck_n > 0).mean():.3f} ({time.time() - t0:.0f} s)", flush=True)
            continue
        m, t = month(ym, sh, args.kind)
        m.to_parquet(CACHE / f"{out}_{ym}.parquet", index=False)
        t.to_parquet(CACHE / f"{out}_targets_{ym}.parquet", index=False)
        ok = (t.r_p - t.p_clear).abs() < 0.011
        print(f"  {ym}: {len(t):,} targets, {len(m):,} {args.kind} own prices; realised clearing reproduces the "
              f"re-clear in {ok.mean():.3f}; draws' mean p* − p* median {(t.draw_p_mean - t.p_star).median():+.2f}, "
              f"sd of p* across draws median {t.draw_p_sd.median():.2f} ({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
