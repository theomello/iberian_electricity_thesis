"""T1: short-notice share lambda (docs/specs/2026-11-19-short-notice-share-design.md).

    .venv/bin/python scripts/analysis/tou_short_notice_share.py --step0   # coverage of 6.2-6.4 and s = p/r, no estimation
    .venv/bin/python scripts/analysis/tou_short_notice_share.py           # G1, G2, L1-L3

lambda = eps_u / (sigma * theta * s). eps_u: wind-speed instrument C1, pipeline of industry_iv_wind_speed_estimation.py
with the outcome changed from ESIOS 1204-1207 to the tariff series 6.2+6.3+6.4 (1216-1218) on the same rows; the
outcome's week-on-week difference and its 7/14/28-day lags (predictors) are rebuilt from that series exactly as in
industry_iv_noise_reducers.build_sets (V3). sigma = -0.177 [-0.544, -0.095] (2026-11-18, pooled full dose, not
re-estimated). s = p / (p + T + W) per hour with the tariff regime in force (old to 2021-05-31, new after), load-weighted.
Writes outputs/tables/tou_short_notice_share.csv and tou_short_notice_share_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_instrument_settlement as S  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import industry_iv_second_settlement as S2  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402

IDS = {"6.2": 1216, "6.3": 1217, "6.4": 1218}
SIGMA, SIGMA_LO, SIGMA_HI = -0.177, -0.544, -0.095
THETAS = [0.32, 0.49, 1.0]
REFORM = pd.Timestamp("2021-06-01")


def grid_load():
    grid = pd.MultiIndex.from_product([pd.date_range("2018-10-01", "2023-12-31"), range(24)], names=["date", "hour"])
    parts = {k: N.hourly(i).reindex(grid) for k, i in IDS.items()}
    return grid, parts


def swap_outcome(d, grid, load):
    """Rebuild d_lnL and its lags on d's rows from `load` on the full hourly grid (shifts by rows, as build_sets)."""
    g = pd.DataFrame({"lnL": np.log(load.where(load > 0)).to_numpy()}, index=grid).reset_index()
    for k in (7, 14, 21, 28, 35):
        g[f"l{k}"] = g.lnL.shift(k * 24)
    g = g.set_index(["date", "hour"])
    r = g.reindex(pd.MultiIndex.from_arrays([d.date, d.hour]))
    d = d.copy()
    d["d_lnL"] = (r.lnL - r.l7).to_numpy()
    d["d_lnL_7"] = (r.l7 - r.l14).to_numpy()
    d["d_lnL_14"] = (r.l14 - r.l21).to_numpy()
    d["d_lnL_28"] = (r.l28 - r.l35).to_numpy()
    return d


def share_s(d, parts):
    """Load-weighted s = p / (p + T + W) over d's rows, regime in force; also by regime."""
    pt = RP.power_table()
    dates = sorted(set(d.date))
    tabs = RP.tables(dates, pt, "full")
    idx = pd.MultiIndex.from_arrays([d.date, d.hour])
    p = d.p.to_numpy()
    new = (d.date >= REFORM).to_numpy()
    num, den = np.zeros(len(d)), np.zeros(len(d))
    for k in IDS:
        tb = tabs[k].reindex(idx)
        tw = np.where(new, tb.new_price.to_numpy(), tb.old_price.to_numpy())
        w = parts[k].reindex(idx).to_numpy()
        s = p / (p + tw)
        ok = np.isfinite(s) & np.isfinite(w) & (p + tw > 0)
        num += np.where(ok, w * s, 0.0)
        den += np.where(ok, w, 0.0)
    out = {"all": num.sum() / den.sum(), "old regime": num[~new].sum() / den[~new].sum(), "new regime": num[new].sum() / den[new].sum()}
    return out


def main():
    d = S.build_frame()
    assert d.date.is_monotonic_increasing
    grid, parts = grid_load()
    load = sum(parts.values())
    miss = pd.Series(load.reindex(pd.MultiIndex.from_arrays([d.date, d.hour])).isna().to_numpy())
    print(f"rows {len(d)}; 6.2+6.3+6.4 missing on {int(miss.sum())} sample rows")
    s = share_s(d, parts)
    print("s = p/(p+T+W), load-weighted:", {k: round(v, 4) for k, v in s.items()})
    if "--step0" in sys.argv:
        return
    d = swap_outcome(d, grid, load)
    need = ["d_lnL", "d_lnL_7", "d_lnL_14", "d_lnL_28"]
    n0 = len(d)
    d = d.dropna(subset=need).reset_index(drop=True)
    print(f"rows after outcome swap {len(d)} (dropped {n0 - len(d)})")
    pbar = float(d.p.mean())
    R = S2.residualise(d, False, {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2})
    Z = np.column_stack([R["d_pc"], R["d_pc2"]])
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    allm = np.ones(len(d), bool)
    jobs = [("primary", "full", R["y"], allm),
            ("primary", "2019-21H1", R["y"], (d.date < "2021-07-01").to_numpy()),
            ("primary", "2021H2-23", R["y"], (d.date >= "2021-07-01").to_numpy()),
            ("placebo", "full", R["yplac"], allm)]
    rows = []
    for name, block, y, mask in jobs:
        sub = E.Sub(d, y, R["p"], Z, mask, [0, 1])
        sub.Zfull = Z
        r, _ = E.run_sub(sub, srcs, pbar)
        rows.append(dict(variant=name, block=block, mean_price=pbar, **r))
        print(name, block, {k: round(float(v), 4) for k, v in r.items() if k in ("F", "elasticity", "rand_lo", "rand_hi", "p_t_rank")}, flush=True)
    Rr = pd.DataFrame(rows)
    m = Rr[(Rr.variant == "primary") & (Rr.block == "full")].iloc[0]
    pl = Rr[Rr.variant == "placebo"].iloc[0]
    sa = s["all"]
    lam = []
    for th in THETAS:
        lam_hat = m.elasticity / (SIGMA * th * sa)
        lam_u = max(0.0, -m.rand_lo) / (abs(SIGMA_HI) * th * sa)
        lam.append(dict(theta=th, s=sa, eps_u=m.elasticity, eps_lo=m.rand_lo, eps_hi=m.rand_hi, lambda_hat=lam_hat, lambda_U=lam_u))
        print(f"theta {th}: lambda_hat {lam_hat:.3f}, lambda_U {lam_u:.3f}")
    # reported, no rule: the earlier E3-E6 estimates
    for lab, e, lo in (("E3-E6 wind speed C1", 0.0001, -0.021), ("E3-E6 bid curve", -0.036, -0.080)):
        for th in THETAS:
            lam.append(dict(theta=th, s=sa, eps_u=e, eps_lo=lo, lambda_hat=e / (SIGMA * th * sa),
                            lambda_U=max(0.0, -lo) / (abs(SIGMA_HI) * th * sa), source=lab))
    L = pd.DataFrame(lam)
    L["source"] = L.get("source").fillna("6.2-6.4 wind speed C1 (T1)")
    out = pd.concat([Rr.assign(table="iv"), L.assign(table="lambda")], ignore_index=True)
    out.round(5).to_csv(T.OUT / "tou_short_notice_share.csv", index=False)
    l32 = L[(L.source.str.startswith("6.2")) & (L.theta == 0.32)].iloc[0]
    l49 = L[(L.source.str.startswith("6.2")) & (L.theta == 0.49)].iloc[0]
    ch = [("G1 first stage F >= 20", bool(m.F >= 20), f"F {m.F:.1f}"),
          ("G2 placebo outcome p > 0.05", bool(pl.p_t_rank > 0.05), f"elasticity {pl.elasticity:.4f}, p_t {pl.p_t_rank:.3f}"),
          ("L1 lambda_U < 1 at theta 0.32", bool(l32.lambda_U < 1), f"lambda_U {l32.lambda_U:.3f}, lambda_hat {l32.lambda_hat:.3f}"),
          ("L2 lambda_U < 1 at theta 0.49", bool(l49.lambda_U < 1), f"lambda_U {l49.lambda_U:.3f}"),
          ("L3 sign eps_u <= 0.02", bool(m.elasticity <= 0.02), f"eps_u {m.elasticity:.4f} [{m.rand_lo:.4f}, {m.rand_hi:.4f}]"),
          ("s (step 0)", None, ", ".join(f"{k} {v:.4f}" for k, v in s.items()))]
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "tou_short_notice_share_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    print("\n", L.round(4).to_string(index=False))
    print("\n", C.to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
