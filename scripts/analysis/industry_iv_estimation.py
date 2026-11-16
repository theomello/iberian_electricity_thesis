"""Estimation of docs/specs/2026-11-17-industry-iv-estimation-design.md (rules E1-E8).

    .venv/bin/python scripts/analysis/industry_iv_estimation.py

Variants V1, V2, V3 (primary V3) of industrial hourly load (ESIOS 1204-1207) on the day-ahead price, instruments D-1 wind and solar forecasts and squares. Inference: randomization (1,000 permutations of the
residualised instruments across days within year-month, hour matched): p from the rank of |t|; interval = slopes not rejected by the permutation Anderson-Rubin statistic. Normal and chi-square AR sets alongside.
Subsets (V3): wind-only, solar-only instruments; years 2019, 2021, 2022, 2023; hour blocks night 0-7, day 8-17, evening 18-23. Placebo outcome: 7-day-lagged differenced load. Seed 20261117.
Writes outputs/tables/industry_iv_estimation.csv and industry_iv_estimation_checks.csv. Residualised sets are cached in data/cache_tou/industry_iv_sets.pkl.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

NPERM, NGRID = 1000, 2001
CACHE = T.ROOT / "data/cache_tou/industry_iv_sets.pkl"


def starts_of(g):
    ch = np.r_[True, g[1:] != g[:-1]]
    return np.flatnonzero(ch)


class Sub:
    """A subset of rows of one residualised set (rows sorted by date); instrument columns `cols`."""

    def __init__(self, d, y, p, Z, mask, cols):
        self.idx = np.flatnonzero(mask)
        self.y, self.p, self.cols = y[self.idx], p[self.idx], cols
        self.Z0 = Z[self.idx][:, cols]
        g = d.date.to_numpy()[self.idx]
        self.st = starts_of(g)
        self.k = len(cols)

    def cs(self, M):
        return np.add.reduceat(M, self.st, axis=0)

    def fast(self, Z):
        b = np.linalg.solve(Z.T @ Z, Z.T @ self.p)
        fit = Z @ b
        beta = float(fit @ self.y / (fit @ self.p))
        u = self.y - beta * self.p
        se = float(np.sqrt((self.cs((fit * u)[:, None]) ** 2).sum()) / abs(fit @ self.p))
        return beta, se

    def first_stage_F(self, Z):
        b = np.linalg.solve(Z.T @ Z, Z.T @ self.p)
        e = self.p - Z @ b
        A = np.linalg.inv(Z.T @ Z)
        sc = self.cs(Z * e[:, None])
        V = A @ (sc.T @ sc) @ A
        return float(b @ np.linalg.inv(V) @ b / Z.shape[1])

    def ar(self, Z, grid):
        """Anderson-Rubin statistic on a grid of slopes (cluster-robust, no projection)."""
        A, B = self.cs(Z * self.y[:, None]), self.cs(Z * self.p[:, None])
        a, b = A.sum(0), B.sum(0)
        AA, AB, BB = A.T @ A, A.T @ B, B.T @ B
        V = AA[None] - grid[:, None, None] * (AB + AB.T)[None] + grid[:, None, None] ** 2 * BB[None]
        gv = a[None] - grid[:, None] * b[None]
        return np.einsum("mi,mi->m", gv, np.linalg.solve(V, gv[:, :, None])[:, :, 0])

    def hansen(self, Z):
        b = np.linalg.solve(Z.T @ Z, Z.T @ self.p)
        fit = Z @ b
        beta = float(fit @ self.y / (fit @ self.p))
        u = self.y - beta * self.p
        S = self.cs(Z * u[:, None])
        W = np.linalg.inv(S.T @ S)
        zp, zy = Z.T @ self.p, Z.T @ self.y
        b2 = float(zp @ W @ zy / (zp @ W @ zp))
        u2 = self.y - b2 * self.p
        S2 = self.cs(Z * u2[:, None])
        gs = Z.T @ u2
        J = float(gs @ np.linalg.inv(S2.T @ S2) @ gs)
        return J, float(stats.chi2.sf(J, Z.shape[1] - 1))


def perm_sources(d, rng, nper):
    """Row-index maps: each row takes the same hour of another day of the same year-month (own row if that hour is missing)."""
    day = pd.factorize(d.date)[0]
    nd = day.max() + 1
    hour = d.hour.to_numpy()
    tab = np.full((nd, 24), -1)
    tab[day, hour] = np.arange(len(d))
    ym = d.date.dt.strftime("%Y-%m").to_numpy()
    first = np.r_[0, np.flatnonzero(day[1:] != day[:-1]) + 1]
    day_ym = ym[first]
    groups = [np.flatnonzero(day_ym == m) for m in np.unique(day_ym)]
    own = np.arange(len(d))
    out = np.empty((nper, len(d)), dtype=np.int32)
    for r in range(nper):
        pd_ = np.arange(nd)
        for gdx in groups:
            pd_[gdx] = rng.permutation(gdx)
        src = tab[pd_[day], hour]
        out[r] = np.where(src < 0, own, src)
    return out


def run_sub(sub, srcs, pbar, grid_scale=15.0):
    Z = sub.Z0
    beta, se = sub.fast(Z)
    F = sub.first_stage_F(Z)
    grid = beta + np.linspace(-grid_scale, grid_scale, NGRID) * se
    ar_real = sub.ar(Z, grid)
    t_real = beta / se
    tp = np.empty(len(srcs))
    arp = np.empty((len(srcs), NGRID))
    ar0_perm = np.empty(len(srcs))
    for r, src in enumerate(srcs):
        Zp = Z_full_perm(sub, src)
        b, s = sub.fast(Zp)
        tp[r] = b / s
        arp[r] = sub.ar(Zp, grid)
    ar0_real = sub.ar(Z, np.array([0.0]))[0]
    ar0_perm = np.array([sub.ar(Z_full_perm(sub, src), np.array([0.0]))[0] for src in srcs])
    p_t = (1 + np.sum(np.abs(tp) >= abs(t_real))) / (len(srcs) + 1)
    p_ar0 = (1 + np.sum(ar0_perm >= ar0_real)) / (len(srcs) + 1)
    pv = (1 + (arp >= ar_real[None]).sum(0)) / (len(srcs) + 1)
    keep_r = grid[pv > 0.05]
    lo_r, hi_r = (float(keep_r.min()), float(keep_r.max())) if len(keep_r) else (np.nan, np.nan)
    keep_n = grid[ar_real <= stats.chi2.ppf(0.95, sub.k)]
    lo_a, hi_a = (float(keep_n.min()), float(keep_n.max())) if len(keep_n) else (np.nan, np.nan)
    unb = bool(len(keep_r) and (keep_r.min() <= grid[0] or keep_r.max() >= grid[-1]))
    loo = np.array([(1 + np.sum(np.delete(np.abs(tp), i) >= abs(tp[i]))) / len(tp) for i in range(len(tp))])
    return dict(n=len(sub.y), days=len(sub.st), F=F, slope=beta, se_slope=se, elasticity=beta * pbar, se_elasticity=se * pbar,
                norm_lo=(beta - 1.96 * se) * pbar, norm_hi=(beta + 1.96 * se) * pbar, ar_lo=lo_a * pbar, ar_hi=hi_a * pbar, rand_lo=lo_r * pbar, rand_hi=hi_r * pbar,
                rand_unbounded=unb, p_t_rank=p_t, p_ar0_rank=p_ar0, perm_share_t_gt196=float((np.abs(tp) > 1.96).mean()), loo_share_p_lt05=float((loo < 0.05).mean())), tp


def Z_full_perm(sub, src):
    return sub.Zfull[src[sub.idx]][:, sub.cols]


def main():
    if CACHE.exists():
        sets, pbar = pickle.load(open(CACHE, "rb"))
    else:
        sets, pbar = N.build_sets(placebo=True)
        CACHE.parent.mkdir(exist_ok=True)
        pickle.dump((sets, pbar), open(CACHE, "wb"))
    rng = np.random.default_rng(N.SEED)
    rows, extra = [], {}
    all4 = [0, 1, 2, 3]
    jobs = {"V1 week-on-week difference": ["full"], "V2 double ML (boosting)": ["full"], "V3 placebo": ["full"],
            "V3 difference + double ML": ["full", "wind only", "solar only", "2019", "2021", "2022", "2023", "night 0-7", "day 8-17", "evening 18-23"]}
    for name, blocks in jobs.items():
        s = sets[name]
        d = s["d"]
        assert d.date.is_monotonic_increasing
        srcs = perm_sources(d, rng, NPERM)
        yr, hr = d.date.dt.year.to_numpy(), d.hour.to_numpy()
        masks = {"full": (np.ones(len(d), bool), all4), "wind only": (np.ones(len(d), bool), [0, 2]), "solar only": (np.ones(len(d), bool), [1, 3]),
                 **{str(y): (yr == y, all4) for y in (2019, 2021, 2022, 2023)}, "night 0-7": (hr <= 7, all4), "day 8-17": ((hr >= 8) & (hr <= 17), all4), "evening 18-23": (hr >= 18, all4)}
        for b in blocks:
            m, cols = masks[b]
            sub = Sub(d, s["y"], s["p"], s["Z"], m, cols)
            sub.Zfull = s["Z"]
            r, tp = run_sub(sub, srcs, pbar)
            if name.startswith("V3 diff") and b == "full":
                r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
            rows.append(dict(variant=name, block=b, **r))
            print(name, b, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_estimation.csv", index=False)

    g = lambda v, b: R[(R.variant == v) & (R.block == b)].iloc[0]
    V3, P = "V3 difference + double ML", "V3 placebo"
    main_ = g(V3, "full")
    ch = []
    ch.append(("E1 sign and plausibility", bool(main_.elasticity < 0 and abs(main_.elasticity) <= 1), f"elasticity {main_.elasticity:.4f}"))
    ch.append(("E2 detected", bool(main_.p_t_rank <= 0.05 and (main_.rand_hi < 0 or main_.rand_lo > 0)), f"p_t {main_.p_t_rank:.3f}, p_AR0 {main_.p_ar0_rank:.3f}, rand [{main_.rand_lo:.4f}, {main_.rand_hi:.4f}]"))
    pl = g(P, "full")
    ch.append(("E3 placebo outcome", bool(pl.p_t_rank > 0.05 and abs(pl.elasticity) < 0.01), f"elasticity {pl.elasticity:.4f}, p_t {pl.p_t_rank:.3f}"))
    w, so = g(V3, "wind only"), g(V3, "solar only")
    inside = lambda a, b: bool(b.rand_lo <= a.elasticity <= b.rand_hi)
    ch.append(("E4 overidentification", bool(main_.hansen_p > 0.05 and inside(w, so) and inside(so, w)), f"J {main_.hansen_J:.2f} p {main_.hansen_p:.3f}; wind {w.elasticity:.4f} [{w.rand_lo:.4f},{w.rand_hi:.4f}], solar {so.elasticity:.4f} [{so.rand_lo:.4f},{so.rand_hi:.4f}]"))
    ys = [g(V3, y) for y in ("2019", "2021", "2022", "2023")]
    b_, s_ = np.array([y.slope for y in ys]), np.array([y.se_slope for y in ys])
    wbar = np.sum(b_ / s_ ** 2) / np.sum(1 / s_ ** 2)
    wp = float(stats.chi2.sf(np.sum((b_ - wbar) ** 2 / s_ ** 2), 3))
    ch.append(("E5 stability over years", bool(len(set(np.sign(b_))) == 1 and wp > 0.05), "elasticities " + ", ".join(f"{y.elasticity:.4f}" for y in ys) + f"; equality p {wp:.3f}"))
    ch.append(("E6 hour blocks (exploratory)", None, "; ".join(f"{b} {g(V3, b).elasticity:.4f} [{g(V3, b).rand_lo:.4f},{g(V3, b).rand_hi:.4f}]" for b in ("night 0-7", "day 8-17", "evening 18-23"))))
    v1, v2 = g("V1 week-on-week difference", "full"), g("V2 double ML (boosting)", "full")
    ch.append(("E7 variant agreement", bool(main_.rand_lo <= v1.elasticity <= main_.rand_hi and main_.rand_lo <= v2.elasticity <= main_.rand_hi), f"V1 {v1.elasticity:.4f}, V2 {v2.elasticity:.4f}, V3 {main_.elasticity:.4f} [{main_.rand_lo:.4f},{main_.rand_hi:.4f}]"))
    ch.append(("E8 calibration of permutation test", bool(0.02 <= main_.loo_share_p_lt05 <= 0.10), f"leave-one-out share p<0.05 {main_.loo_share_p_lt05:.3f} (near-tautological); share |t|>1.96 {main_.perm_share_t_gt196:.3f}"))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_estimation_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    print("\n", R[["variant", "block", "n", "F", "elasticity", "se_elasticity", "norm_lo", "norm_hi", "ar_lo", "ar_hi", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank"]].round(4).to_string(index=False))
    print("\n", C.to_string(index=False))


if __name__ == "__main__":
    main()
