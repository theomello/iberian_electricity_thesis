#!/usr/bin/env python3
"""Resampled residual demand for every thermal owner's offer curve: where each of its steps clears.

    .venv/bin/python scripts/analysis/step_curves.py              # input
    .venv/bin/python scripts/analysis/step_engine.py --months 201906 [...]

Step-offer design (`docs/specs/2026-10-01-step-offer-design.md` §3). A firm offers a
step curve before it knows its residual demand. Each step's price and length satisfy
a first-order condition in expectation over the residual demands it could face
(Wolak 2007; Kastl 2011; Reguant 2014). This script builds those expectations.

FOR EACH TARGET (group f, hour H) where f offers a gas or coal step:
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

WRITES outputs/cache/step/moments_YYYYMM.parquet, one row per (H, f, own price q_k)
at which f offers gas or coal: v_sell, v_buy, q_next, n_draws, and over the draws:
  m_n, m_s, m_x, m_xn        marginal: count; sums of n, |RD′|, X; count with X defined
  g_n, g_p, g_x, g_xn, g_s   gap above q_k: count; sums of p*, X; X defined; |RD′|
and realised: r_event (1 marginal at q_k, 2 gap above q_k, 0 neither), r_p, r_n, r_s.
Also moments_targets_YYYYMM.parquet: per target, the draws' mean and sd of p*, H's p*
and the realised clearing price.
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
MIN_SLOPE = 5.0        # MW per €/MWh
OFF, W = 1000.0, 20000.0          # price keys: hour_index * W + price + OFF
OFF2, W2 = 2.0e5, 1.0e6           # value keys: hour_index * W2 + ES + OFF2
SENTINEL = -999.0


def months_around(ym: str) -> list[str]:
    p = pd.Period(ym, "M")
    return [str(p + k).replace("-", "") for k in (-1, 0, 1)]


def load(ym: str) -> tuple:
    have = [m for m in months_around(ym) if (CACHE / f"hours_{m}.parquet").exists()]
    hours = pd.concat([pd.read_parquet(CACHE / f"hours_{m}.parquet") for m in have], ignore_index=True)
    hours = hours.sort_values("hid", ignore_index=True)
    market = pd.concat([pd.read_parquet(CACHE / f"market_{m}.parquet") for m in have], ignore_index=True)
    own = pd.concat([pd.read_parquet(CACHE / f"own_{m}.parquet") for m in have], ignore_index=True)
    units = pd.read_parquet(CACHE / f"units_{ym}.parquet")
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
    kstar = np.where(at_q, kk, -1)
    kgap = np.where(at_q, -1, k - 1)          # -1: below every own price
    return {"p": p, "n": n, "s": s, "kstar": kstar, "kgap": kgap}


def month(ym: str, sh: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hours, market, own, units = load(ym)
    blk = Block(hours, market, own)
    h = hours.copy()
    h["nl"] = h.F_demand - h.F_wind - h.F_solar
    h["day"] = (pd.to_datetime(h.date) - pd.Timestamp("2018-01-01")).dt.days
    valid = h.valid.fillna(False).to_numpy()
    t_units = units[units.group.notna() & ~units.withdrawn]
    own_idx = own.set_index(["hid", "group"]).sort_index()
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
            r = clear(blk, g, q, vs, vb, cand, shift)
            rr = clear(blk, g, q, vs, vb, np.array([hi_]), np.zeros(1))
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
                "m_s": acc(mk[mm], r["s"][mm]), "m_x": acc(mk[mm & xd], x[mm & xd]),
                "m_xn": acc(mk[mm & xd], np.ones((mm & xd).sum())),
                "g_n": acc(gk[gm], np.ones(gm.sum())), "g_p": acc(gk[gm], r["p"][gm]),
                "g_x": acc(gk[gm & xd], x[gm & xd]), "g_xn": acc(gk[gm & xd], np.ones((gm & xd).sum())),
                "g_s": acc(gk[gm], r["s"][gm]), "g_sn": acc(gk[gm], r["n"][gm]),
            })
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
    return pd.concat(out, ignore_index=True), pd.DataFrame(tg)


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="+", required=True)
    args = ap.parse_args()
    sh = shares()
    for ym in args.months:
        t0 = time.time()
        m, t = month(ym, sh)
        m.to_parquet(CACHE / f"moments_{ym}.parquet", index=False)
        t.to_parquet(CACHE / f"moments_targets_{ym}.parquet", index=False)
        ok = (t.r_p - t.p_clear).abs() < 0.011
        print(f"  {ym}: {len(t):,} targets, {len(m):,} thermal own prices; realised clearing reproduces the "
              f"re-clear in {ok.mean():.3f}; draws' mean p* − p* median {(t.draw_p_mean - t.p_star).median():+.2f}, "
              f"sd of p* across draws median {t.draw_p_sd.median():.2f} ({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
