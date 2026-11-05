#!/usr/bin/env python3
"""Is the gas-price control in the gas-cap dose-response (B3) right? (notes/rq-gas-cap-control.md, rules fixed before running)

    .venv/bin/python scripts/analysis/gas_cap_control_tests.py --stage draws        # ATT_w and 199 firm-block draws (cached)
    .venv/bin/python scripts/analysis/gas_cap_control_tests.py --stage nodose       # (1) gas response in weeks with no dose
    .venv/bin/python scripts/analysis/gas_cap_control_tests.py --stage confounders  # (2) candidates: dose, outcome, rho shift
    .venv/bin/python scripts/analysis/gas_cap_control_tests.py --stage controls     # (3) rho under better control sets
    .venv/bin/python scripts/analysis/gas_cap_control_tests.py --stage all

B3's outcome ATT_w (Xu 2017 generalised synthetic control, r by cross-validation = 0) is regressed on weekly gas prices and other candidates
in the two samples with zero dose (pre-cap weeks; weeks after the subsidy ended). Intervals: double bootstrap (199 firm-block draws of B3,
seed 20261102, then moving blocks of 4 weeks within each sample), firm bootstrap alone, Newey-West. Writes outputs/tables/gas_cap_control_*.csv
and gas_cap_control_att_draws.npz (the cached draws). Reads data/ and outputs/tables only; no fetching.
"""
from __future__ import annotations

import argparse
import faulthandler
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import build_weekly_conditions as bwc  # noqa: E402
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
DRAWS = T / "gas_cap_control_att_draws.npz"
SEED = 20261102          # B3's and H6's seed
BLOCK = 4                # moving-block length in weeks
NW_LAGS = 3
PRE0, PRE1 = pd.Timestamp("2021-10-04"), pd.Timestamp("2022-06-06")
WK0613 = pd.Timestamp("2022-06-13")
PRE_EARLY = pd.Timestamp("2022-03-21")
POST0 = pd.Timestamp("2023-02-27")
GAS_NAMES = ["mibgas_bid", "psv_bid", "spread_bid", "mibgas_dd", "spread_dd"]


# ---------------------------------------------------------------- core objects

def core():
    h = panel()
    W, _ = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    fi = meta.firm.reindex(W.index).to_numpy()
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    return dict(M=M, ib=ib, fi=fi, cols=cols, pre=pre, g=g)


def make_draws(c, reps: int, r: int | None = None):
    """ATT_w and firm-block draws at Xu's cross-validated r (must be 0, as in B3); `r` overrides for sensitivities and nothing is saved."""
    if r is None:
        cv = xu_cv(c["M"], c["ib"], c["pre"])
        r = int(np.argmin(cv))
        print(f"Xu cross-validation errors {np.round(cv, 5).tolist()} -> r = {r}")
        if r != 0:
            raise SystemExit("CV does not pick r = 0 as in B3: stop and rewrite the rules")
        save = True
    else:
        save = False
    att = gsc(c["M"], c["ib"], c["pre"], r)
    rng = np.random.default_rng(SEED)
    fi, ib = pd.Series(c["fi"]).to_numpy(), c["ib"]
    groups = {k: pd.Series(fi[ib == k]).unique() for k in (True, False)}
    D = []
    for _ in range(reps):
        idx = np.concatenate([np.flatnonzero((fi == f_) & (ib == k))
                              for k in (True, False) for f_ in rng.choice(groups[k], size=len(groups[k]), replace=True)])
        D.append(gsc(c["M"][idx], ib[idx], c["pre"], r))
    D = np.array(D)
    if save:
        np.savez(DRAWS, att=att, draws=D, cols=c["cols"].to_numpy().astype("datetime64[ns]"), g=c["g"])
    print(f"{reps} draws {'saved' if save else 'made'} (r = {r}); {len(groups[True])} Iberian, {len(groups[False])} Italian firms")
    return att, D


def load_draws(c, reps: int):
    if DRAWS.exists():
        z = np.load(DRAWS)
        if z["draws"].shape[0] == reps:
            return z["att"], z["draws"]
    return make_draws(c, reps)


# ---------------------------------------------------------------- weekly candidate series

def build_series(cols: pd.DatetimeIndex) -> pd.DataFrame:
    S = pd.read_parquet(T / "gas_cap_weekly_conditions.parquet").reindex(cols)
    S["spread_bid"] = S.psv_bid - S.mibgas_bid
    wg = weekly_gas(cols)
    S["mibgas_dd"], S["spread_dd"] = wg[:, 0], wg[:, 1]
    for i, n in ((1777, "wind_fc"), (1779, "pv_fc"), (1775, "dem_fc")):
        d = pd.read_parquet(DATA / f"esios/esios_{i}.parquet")
        S[n] = bwc.weekly(bwc.local_daily(d, "value", "Europe/Madrid")).reindex(cols)
    # MITECO, all reservoirs: national fill share, and its deviation from the same ISO week's 2000-2021 mean
    m = pd.read_parquet(DATA / "miteco/embalses_historico.parquet").dropna(subset=["stored_hm3", "capacity_hm3"])
    dd = m.groupby("date")[["stored_hm3", "capacity_hm3"]].sum()
    fill = (dd.stored_hm3 / dd.capacity_hm3)
    wk = fill.groupby(fill.index.to_period("W").start_time).mean()
    iso = pd.Series(wk.index.isocalendar().week.clip(upper=52).to_numpy(), index=wk.index)
    base = wk[(wk.index.year >= 2000) & (wk.index.year <= 2021)].groupby(iso[(wk.index.year >= 2000) & (wk.index.year <= 2021)]).mean()
    S["hydro_fill"] = wk.reindex(cols)
    S["hydro_fill_anom"] = (wk - iso.map(base)).reindex(cols)
    x = pd.read_parquet(DATA / "esios/esios_623.parquet")
    s623 = pd.Series(x.value.to_numpy() / 1e6, index=pd.to_datetime(x.datetime.str[:10]))
    S["hydro_esios623_twh"] = s623.reindex(cols)
    f = pd.read_parquet(T / "france_link_hours.parquet", columns=["date", "fr_nuc_lag", "fr_load_fc", "p_import_full", "p_export_full"])
    fd = f.groupby("date").mean()
    for n in fd.columns:
        s = fd[n].copy()
        s.index = pd.to_datetime(s.index)
        S["fr_" + n if not n.startswith("fr_") else n] = bwc.weekly(s).reindex(cols)
    mid = (cols + pd.Timedelta(days=3)).dayofyear.to_numpy()
    S["season_sin"] = np.sin(2 * np.pi * mid / 365.25)
    S["season_cos"] = np.cos(2 * np.pi * mid / 365.25)
    S = S.rename(columns={"fr_p_import_full": "fr_import_full_p", "fr_p_export_full": "fr_export_full_p"})
    return S


def zs(S: pd.DataFrame) -> pd.DataFrame:
    return (S - S.mean()) / S.std()


# ---------------------------------------------------------------- regression helpers

class Samples:
    """Row sets for the two no-dose samples, and moving-block draws over their observed weeks."""

    def __init__(self, cols, att, reps, variant="main"):
        ok = ~np.isnan(att)
        pre_end = {"main": PRE1, "with0613": WK0613, "early": PRE_EARLY}[variant]
        self.pre = np.flatnonzero(ok & (cols >= PRE0) & (cols <= pre_end))
        self.post = np.flatnonzero(ok & (cols >= POST0))
        self.t = np.arange(len(cols), dtype=float)
        rng = np.random.default_rng(5)
        self.blk = {k: [self._blocks(len(rows), rng) for _ in range(reps)] for k, rows in (("pre", self.pre), ("post", self.post))}

    @staticmethod
    def _blocks(n, rng):
        nb = -(-n // BLOCK)
        st = rng.integers(0, max(n - BLOCK + 1, 1), size=nb)
        return np.concatenate([np.arange(s, s + BLOCK) for s in st])[:n]

    def rows(self, which, d=None):
        """(rows, labels) for sample `which` in {pre, post, pooled}; draw d resamples weeks in blocks."""
        parts = []
        for k, base in (("pre", self.pre), ("post", self.post)):
            if which not in (k, "pooled"):
                continue
            rr = base if d is None else base[self.blk[k][d]]
            parts.append((rr, np.full(len(rr), 0 if k == "pre" else 1)))
        return np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts])


def coef(y, X, rows, lab, trend=False):
    """Slopes on X (n x k) with a separate intercept per sample label; optional common linear trend."""
    ok = ~np.isnan(y[rows]) & ~np.isnan(X[rows]).any(axis=1)
    rows, lab = rows[ok], lab[ok]
    ls = np.unique(lab)
    Z = [(lab == l).astype(float) for l in ls] + [X[rows]]
    if trend:
        t = rows.astype(float)
        Z.append(t - t.mean())
    Z = np.column_stack(Z)
    beta = np.linalg.lstsq(Z, y[rows], rcond=None)[0]
    return beta[len(ls):len(ls) + X.shape[1]]


def newey_west(y, X, rows, lab, trend=False):
    """HAC standard errors of the X slopes; kernel on calendar-week distance, no covariance across samples."""
    ok = ~np.isnan(y[rows]) & ~np.isnan(X[rows]).any(axis=1)
    rows, lab = rows[ok], lab[ok]
    ls = np.unique(lab)
    Z = [(lab == l).astype(float) for l in ls] + [X[rows]]
    if trend:
        t = rows.astype(float)
        Z.append(t - t.mean())
    Z = np.column_stack(Z)
    beta = np.linalg.lstsq(Z, y[rows], rcond=None)[0]
    u = y[rows] - Z @ beta
    S = np.zeros((Z.shape[1],) * 2)
    for l in ls:
        i = np.flatnonzero(lab == l)
        for a in i:
            for b in i:
                h = abs(rows[a] - rows[b])
                if h <= NW_LAGS:
                    S += (1 - h / (NW_LAGS + 1)) * u[a] * u[b] * np.outer(Z[a], Z[b])
    A = np.linalg.pinv(Z.T @ Z)
    V = A @ S @ A * len(rows) / max(len(rows) - Z.shape[1], 1)
    k0 = len(ls)
    return np.sqrt(np.diag(V))[k0:k0 + X.shape[1]]


def pct(a):
    return np.nanpercentile(a, [2.5, 97.5])


# ---------------------------------------------------------------- stage 1

def stage_nodose(c, S, att, D, reps):
    cols = c["cols"]
    # the gap world: omitted-variable bias b_u = b_c + c * delta
    postg = ~c["pre"] & ~np.isnan(c["g"]) & ~np.isnan(att)
    rho_u = 1 + slope(att, c["g"], ~c["pre"], None, False)
    rho_m = 1 + slope(att, c["g"], ~c["pre"], S[["mibgas_dd"]].to_numpy(), False)
    rho_b = 1 + slope(att, c["g"], ~c["pre"], S[["mibgas_dd", "spread_dd"]].to_numpy(), False)
    print(f"B3 reproduced: rho {rho_u:.3f}; MIBGAS {rho_m:.3f}; both {rho_b:.3f}  (H6: 0.726, 0.583, 0.544)")
    assert abs(rho_u - 0.726) < 5e-4 and abs(rho_m - 0.583) < 5e-4 and abs(rho_b - 0.544) < 5e-4, "does not reproduce H6"
    rows = []
    delta = {}
    for v in ("mibgas_dd", "mibgas_bid", "spread_dd", "spread_bid", "psv_bid"):
        x, gg = S[v].to_numpy()[postg], c["g"][postg]
        delta[v] = np.polyfit(gg, x, 1)[0]
    gap_both, gap_m = rho_u - rho_b, rho_u - rho_m
    cs = {"mibgas_all_through (gap 0.726->both)": gap_both / delta["mibgas_dd"],
          "mibgas_only (gap 0.726->MIBGAS)": gap_m / delta["mibgas_dd"],
          "spread_all_through (gap 0.726->both)": gap_both / delta["spread_dd"]}
    pd.DataFrame([{"world": k, "c_star_per_eur_mwh": v, "per_100_eur": 100 * v} for k, v in cs.items()]
                 + [{"world": f"delta {k} on g (post-cap, {postg.sum()} weeks)", "c_star_per_eur_mwh": v} for k, v in delta.items()]
                 ).to_csv(T / "gas_cap_control_cstar.csv", index=False)
    cstar = cs["mibgas_all_through (gap 0.726->both)"]
    print(f"deltas {({k: round(v, 1) for k, v in delta.items()})}; c* = {cstar:+.5f} per EUR/MWh ({100 * cstar:+.1f} pp per EUR 100)")

    specs = {"mibgas": ["mibgas_bid"], "psv": ["psv_bid"], "spread": ["spread_bid"], "mibgas+psv": ["mibgas_bid", "psv_bid"]}
    variants = [("main", "main", False, att, D), ("trend", "main", True, att, D), ("early_pre", "early", False, att, D),
                ("with0613", "with0613", False, att, D)]
    for r_ in (1, 2):   # ATT built with r factors instead of 0 (fresh draws; not cached)
        a_r, D_r = make_draws(c, reps, r=r_)
        variants.append((f"r{r_}", "main", False, a_r, D_r))
    out, diff = [], []

    def emit(vname, which, sp, vs, y, Dy, sm, trend, rr, lab):
        X = S[vs].to_numpy()
        b0 = coef(y, X, rr, lab, trend)
        se_nw = newey_west(y, X, rr, lab, trend)
        firm = np.array([coef(Dy[d], X, rr, lab, trend) for d in range(reps)])
        dbl = np.array([coef(Dy[d], X, *sm.rows(which, d), trend) for d in range(reps)])
        for j, v in enumerate(vs):
            flo, fhi = pct(firm[:, j])
            dlo, dhi = pct(dbl[:, j])
            se_b = np.nanstd(dbl[:, j], ddof=1)
            power = norm.cdf(abs(cstar) / se_b - 1.96) + norm.cdf(-abs(cstar) / se_b - 1.96)
            out.append({"variant": vname, "sample": which, "spec": sp, "var": v, "n": len(rr), "sd_x": float(np.nanstd(S[v].to_numpy()[rr])),
                        "coef": b0[j], "se_nw": se_nw[j], "nw_lo": b0[j] - 1.96 * se_nw[j], "nw_hi": b0[j] + 1.96 * se_nw[j],
                        "firm_lo": flo, "firm_hi": fhi, "dbl_lo": dlo, "dbl_hi": dhi, "se_dbl": se_b,
                        "mde_80": 2.8 * se_b, "power_at_cstar": power, "cstar": cstar, "per100": 100 * b0[j]})

    for vname, var, trend, y, Dy in variants:
        sm = Samples(cols, y, reps, var)
        for which in ("pre", "post", "pooled"):
            rr, lab = sm.rows(which)
            if len(rr) < 10:
                continue
            for sp, vs in specs.items():
                if vname.startswith("r") and sp == "mibgas+psv":
                    continue
                emit(vname, which, sp, vs, y, Dy, sm, trend, rr, lab)
            if which == "pooled":
                for sp, vs in specs.items():
                    X = S[vs].to_numpy()
                    rp, lp = sm.rows("pre")
                    rq, lq = sm.rows("post")
                    dd = np.array([coef(Dy[d], X, *sm.rows("post", d), trend) - coef(Dy[d], X, *sm.rows("pre", d), trend) for d in range(reps)])
                    p0 = coef(y, X, rq, lq, trend) - coef(y, X, rp, lp, trend)
                    for j, v in enumerate(vs):
                        lo, hi = pct(dd[:, j])
                        diff.append({"variant": vname, "spec": sp, "var": v, "post_minus_pre": p0[j], "lo": lo, "hi": hi, "compatible": lo <= 0 <= hi})
    R, Dd = pd.DataFrame(out), pd.DataFrame(diff)
    R.to_csv(T / "gas_cap_control_nodose.csv", index=False)
    Dd.to_csv(T / "gas_cap_control_nodose_diff.csv", index=False)
    pd.set_option("display.width", 220)
    print(R[(R.variant == "main")][["sample", "spec", "var", "n", "sd_x", "coef", "se_nw", "dbl_lo", "dbl_hi", "firm_lo", "firm_hi", "mde_80", "power_at_cstar"]]
          .round(5).to_string(index=False))
    # the verdict on the pooled MIBGAS slope, main specification
    p = R[(R.variant == "main") & (R["sample"] == "pooled") & (R.spec == "mibgas")].iloc[0]
    nw_ex = (p.nw_lo > 0) or (p.nw_hi < 0)
    dbl_ex = (p.dbl_lo > 0) or (p.dbl_hi < 0)
    if dbl_ex and nw_ex:
        verdict = "gas response detected (" + ("+" if p.coef > 0 else "-") + ")"
    elif (cstar < p.dbl_lo or cstar > p.dbl_hi) and p.power_at_cstar >= 0.8:
        verdict = "gap world rejected"
    else:
        verdict = "uninformative"
    print(f"\nVERDICT (pooled MIBGAS, double bootstrap): coef {p.coef:+.5f} [{p.dbl_lo:+.5f}, {p.dbl_hi:+.5f}], NW [{p.nw_lo:+.5f}, {p.nw_hi:+.5f}], "
          f"c* {cstar:+.5f}, power at c* {p.power_at_cstar:.2f} -> {verdict}")
    pd.DataFrame([{"verdict": verdict, "coef": p.coef, "dbl_lo": p.dbl_lo, "dbl_hi": p.dbl_hi, "nw_lo": p.nw_lo, "nw_hi": p.nw_hi,
                   "cstar": cstar, "power_at_cstar": p.power_at_cstar}]).to_csv(T / "gas_cap_control_nodose_verdict.csv", index=False)
    print(Dd[Dd.variant == "main"].round(5).to_string(index=False))


# ---------------------------------------------------------------- stage 2

def rho_with(att, c, X):
    return 1 + slope(att, c["g"], ~c["pre"], X, False)


def stage_confounders(c, S, att, D, reps):
    cols = c["cols"]
    Z = zs(S)
    sm = Samples(cols, att, reps, "main")
    postg = ~c["pre"] & ~np.isnan(c["g"]) & ~np.isnan(att)
    rho0 = rho_with(att, c, None)
    rho0_d = np.array([rho_with(D[d], c, None) for d in range(reps)])
    rows = []
    rp, lp = sm.rows("pre")
    rq, lq = sm.rows("post")
    rr, ll = sm.rows("pooled")
    for v in Z.columns:
        z = Z[v].to_numpy()
        if np.isnan(z[postg]).any() or np.isnan(z[rr]).any():
            print(f"  {v}: missing weeks inside the samples, skipped"); continue
        a = np.corrcoef(c["g"][postg], z[postg])[0, 1]
        cp = np.corrcoef(att[rp], z[rp])[0, 1]
        cq = np.corrcoef(att[rq], z[rq])[0, 1]
        ya = att.copy()
        for rws in (rp, rq):
            ya[rws] = att[rws] - att[rws].mean()
        zb = z.copy()
        for rws in (rp, rq):
            zb[rws] = z[rws] - z[rws].mean()
        cw = np.corrcoef(ya[rr], zb[rr])[0, 1]
        X = z[:, None]
        slope_nd = coef(att, X, rr, ll)[0]
        dbl = np.array([coef(D[d], X, *sm.rows("pooled", d))[0] for d in range(reps)])
        lo, hi = pct(dbl)
        rho_c = rho_with(att, c, X)
        rho_cd = np.array([rho_with(D[d], c, X) for d in range(reps)])
        dlo, dhi = pct(rho_cd - rho0_d)
        delta_z = np.polyfit(c["g"][postg], z[postg], 1)[0]
        pred = -slope_nd * delta_z
        move_b = (lo > 0) or (hi < 0)
        rows.append({"candidate": v, "gas": v in GAS_NAMES, "a_corr_dose": a, "b_corr_pre": cp, "b_corr_post": cq, "b_corr_pooled_within": cw,
                     "b_slope_z": slope_nd, "b_lo": lo, "b_hi": hi, "b_excludes0": move_b,
                     "rho_with": rho_c, "d_rho": rho_c - rho0, "d_rho_lo": dlo, "d_rho_hi": dhi,
                     "pred_d_rho": pred, "delta_z_on_g": delta_z,
                     "pass_a": abs(a) >= 0.30, "pass_b": move_b, "pass_c": abs(rho_c - rho0) >= 0.10})
    R = pd.DataFrame(rows)
    R["flag"] = R.pass_a & R.pass_b & R.pass_c
    R.to_csv(T / "gas_cap_control_confounders.csv", index=False)
    pd.set_option("display.width", 250)
    print(f"rho (none) {rho0:.3f}; {len(R)} candidates")
    print(R[["candidate", "a_corr_dose", "b_corr_pre", "b_corr_post", "b_corr_pooled_within", "b_slope_z", "b_lo", "b_hi", "rho_with", "d_rho",
             "d_rho_lo", "d_rho_hi", "pred_d_rho", "pass_a", "pass_b", "pass_c", "flag"]].round(3).to_string(index=False))
    print("flagged:", R[R.flag].candidate.tolist())
    return R


# ---------------------------------------------------------------- stage 3

def cv_error(att, X, sm, folds_blk=BLOCK):
    """Blocked CV over the pooled no-dose weeks, sample intercepts; returns (mse with X, mse intercept-only)."""
    rr, ll = sm.rows("pooled")
    fold = np.empty(len(rr), dtype=int)
    k = 0
    for l in (0, 1):
        i = np.flatnonzero(ll == l)
        for s in range(0, len(i), folds_blk):
            fold[i[s:s + folds_blk]] = k
            k += 1
    out = {}
    for name, XX in (("x", X), ("0", np.zeros((len(att), 0)))):
        e = []
        for f in range(k):
            tr, te = fold != f, fold == f
            def design(m):
                return np.column_stack([(ll[m] == l).astype(float) for l in (0, 1)] + ([XX[rr[m]]] if XX.shape[1] else []))
            beta = np.linalg.lstsq(design(tr), att[rr[tr]], rcond=None)[0]
            e.append(att[rr[te]] - design(te) @ beta)
        out[name] = float(np.mean(np.concatenate(e) ** 2))
    return out["x"], out["0"]


def pre_to_post(att, X, sm):
    """Fit on pre-cap weeks, predict post-subsidy weeks, intercept re-centred; ratio of squared error to demeaned post."""
    rp, _ = sm.rows("pre")
    rq, _ = sm.rows("post")
    Z = np.column_stack([np.ones(len(rp)), X[rp]])
    beta = np.linalg.lstsq(Z, att[rp], rcond=None)[0]
    pred = X[rq] @ beta[1:]
    res = att[rq] - pred
    return float(np.mean((res - res.mean()) ** 2) / np.mean((att[rq] - att[rq].mean()) ** 2))


def stage_controls(c, S, att, D, reps, R2=None):
    cols = c["cols"]
    Z = zs(S)
    sm = Samples(cols, att, reps, "main")
    flagged = []
    if R2 is None and (T / "gas_cap_control_confounders.csv").exists():
        R2 = pd.read_csv(T / "gas_cap_control_confounders.csv")
    if R2 is not None:
        flagged = [v for v in R2[R2.flag & ~R2.gas].candidate]
    print("flagged non-gas candidates:", flagged)
    nongas = ["eua_bid", "netload_fc", "temp_es", "temp_it"]
    sets = {"none": [], "existing MIBGAS (delivery-day)": ["mibgas_dd"], "existing MIBGAS + spread (delivery-day)": ["mibgas_dd", "spread_dd"],
            "bid-time MIBGAS": ["mibgas_bid"], "bid-time MIBGAS + PSV": ["mibgas_bid", "psv_bid"], "PSV alone (bid-time)": ["psv_bid"],
            "conditions without gas": nongas, "conditions with both gas prices": ["mibgas_bid", "psv_bid"] + nongas}
    if flagged:
        sets["survivors of (2) + MIBGAS + PSV"] = ["mibgas_bid", "psv_bid"] + flagged
        sets["survivors of (2) alone"] = flagged
    rho0_d = np.array([rho_with(D[d], c, None) for d in range(reps)])
    rows = []
    for name, vs in sets.items():
        X = Z[vs].to_numpy() if vs else None
        pt = rho_with(att, c, X)
        dr = np.array([rho_with(D[d], c, X) for d in range(reps)])
        lo, hi = pct(dr)
        clo, chi = pct(dr - rho0_d)
        if vs:
            cve, cv0 = cv_error(att, Z[vs].to_numpy(), sm)
            p2p = pre_to_post(att, Z[vs].to_numpy(), sm)
        else:
            cve = cv0 = cv_error(att, np.zeros((len(att), 0)), sm)[1]
            p2p = np.nan
        rows.append({"set": name, "vars": "+".join(vs), "k": len(vs), "rho": pt, "boot_mean": dr.mean(), "lo": lo, "hi": hi, "width": hi - lo,
                     "contrast_vs_none": pt - rho_with(att, c, None), "contrast_lo": clo, "contrast_hi": chi,
                     "cv_mse": cve, "cv_mse_intercept_only": cv0, "cv_gain": 1 - cve / cv0, "pre_to_post_mse_ratio": p2p})
    R = pd.DataFrame(rows)
    base = R.loc[R.set == "none", "width"].iloc[0]
    R["width_ratio"] = R.width / base
    cand = R[R.k > 0]
    best = cand.loc[cand.cv_mse.idxmin()]
    R["favoured"] = (R.set == best.set) & (best.cv_gain >= 0.10)
    R.to_csv(T / "gas_cap_control_sets.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["set", "k", "rho", "lo", "hi", "width_ratio", "contrast_vs_none", "contrast_lo", "contrast_hi", "cv_gain", "pre_to_post_mse_ratio", "favoured"]].round(3).to_string(index=False))
    print(f"lowest blocked-CV error among control sets: {best.set} (gain {best.cv_gain:+.3f} over intercept-only); favoured by the 10% rule: {bool(best.cv_gain >= 0.10)}")
    # diagnostic added after seeing the results (not in the rules): how much of each gas control is left once the dose is removed
    postg = ~c["pre"] & ~np.isnan(c["g"]) & ~np.isnan(att)
    gg = c["g"][postg]
    res, rows_i = {}, []
    for v in ("mibgas_dd", "mibgas_bid", "psv_bid", "spread_dd", "spread_bid"):
        x = S[v].to_numpy()[postg]
        b = np.polyfit(gg, x, 1)
        res[v] = x - np.polyval(b, gg)
        r_ = np.corrcoef(gg, x)[0, 1]
        rows_i.append({"var": v, "corr_with_dose": r_, "vif": 1 / (1 - r_ ** 2), "share_variance_left_after_dose": 1 - r_ ** 2, "sd_residual": res[v].std()})
    I = pd.DataFrame(rows_i)
    pair = {"mibgas_dd": "mibgas_bid", "mibgas_bid": "mibgas_dd", "spread_dd": "spread_bid", "spread_bid": "spread_dd"}
    I["corr_residual_other_vintage"] = [np.corrcoef(res[v], res[pair[v]])[0, 1] if v in pair else np.nan for v in I["var"]]
    I.to_csv(T / "gas_cap_control_identification.csv", index=False)
    print(I.round(3).to_string(index=False))
    return R


# ---------------------------------------------------------------- main

def main() -> int:
    faulthandler.dump_traceback_later(900, exit=True)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["draws", "nodose", "confounders", "controls", "all"], default="all")
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    c = core()
    att, D = load_draws(c, a.reps)
    S = build_series(c["cols"])
    out = S.copy()
    out["att"], out["g"] = att, c["g"]
    out.to_csv(T / "gas_cap_control_series.csv")
    if a.stage == "draws":
        return 0
    if a.stage in ("nodose", "all"):
        stage_nodose(c, S, att, D, a.reps)
    R2 = None
    if a.stage in ("confounders", "all"):
        R2 = stage_confounders(c, S, att, D, a.reps)
    if a.stage in ("controls", "all"):
        stage_controls(c, S, att, D, a.reps, R2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
