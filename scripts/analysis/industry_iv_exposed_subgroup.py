"""Run of docs/specs/2026-11-17-industry-iv-exposed-subgroup-design.md (rules X1-X4).

    .venv/bin/python scripts/analysis/industry_iv_exposed_subgroup.py
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
import tou_did as T  # noqa: E402

ROOT = T.ROOT


def unit_group_series(sample):
    dc = pd.read_parquet(ROOT / "data/omie/registry/direct_consumers.parquet")
    us = set(dc[dc["sample"] == sample].unit)
    parts = []
    for f in sorted((ROOT / "outputs/tables/direct_consumer_panel").glob("panel_*.parquet")):
        ym = f.stem[-6:]
        if not ("201809" <= ym <= "202312"):
            continue
        p = pd.read_parquet(f, columns=["unit", "utc", "total_buy_mw"])
        parts.append(p[p.unit.isin(us)])
    p = pd.concat(parts)
    dt_, hr_ = S.local(p.utc)
    p = p.assign(date=dt_.to_numpy(), hour=hr_.to_numpy())
    return p.groupby(["date", "hour"]).total_buy_mw.sum()


def series_to_columns(s, d):
    grid = pd.MultiIndex.from_product([pd.date_range("2018-08-01", "2023-12-31"), range(24)], names=["date", "hour"])
    v = s.reindex(grid)
    ln = np.log(v.where(v > 0))
    sh = lambda k: ln.shift(k * 24)
    out = pd.DataFrame({"d_lnL": ln - sh(7), "d_lnL_7": sh(7) - sh(14), "d_lnL_14": sh(14) - sh(21), "d_lnL_28": sh(28) - sh(35)}, index=grid).reset_index()
    g = d.drop(columns=["d_lnL", "d_lnL_7", "d_lnL_14", "d_lnL_28"]).merge(out, on=["date", "hour"], how="left")
    return g.dropna(subset=["d_lnL", "d_lnL_7", "d_lnL_14", "d_lnL_28"]).reset_index(drop=True)


def main():
    d0 = S.build_frame()
    pbar = float(d0.p.mean())
    agg_mw = float(d0.load.mean())
    groups = {"G1 ESIOS 353 direct consumers": N.hourly(353), "G2 process units": unit_group_series("process"), "G3 refinery units": unit_group_series("refinery")}
    rows = []
    for gname, ser in groups.items():
        d = series_to_columns(ser, d0)
        share = float(ser.reindex(pd.MultiIndex.from_arrays([d.date, d.hour])).mean() / agg_mw)
        print(gname, f"rows {len(d)}, mean {ser.mean():.0f} MW, share of E3-E6 {share:.3f}", flush=True)
        R = S2.residualise(d, False, {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2})
        Z = np.column_stack([R["d_pc"], R["d_pc2"]])
        X = S2.predictors(d, False)
        order = d.date.rank(method="dense").to_numpy()
        blocks = np.minimum((order / order.max() * 10).astype(int), 9)
        srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
        allm = np.ones(len(d), bool)
        jobs = [("real", None, R["y"]), ("placebo", None, R["yplac"])]
        for beta in (-0.1, -0.3):
            yp = np.asarray(d.d_lnL, float) + beta / pbar * np.asarray(d.d_p, float)
            jobs.append((f"planted {beta}", beta, N.gb_resid(yp[:, None], X, blocks, d.date.to_numpy())[:, 0]))
        for nm, beta, y in jobs:
            sub = E.Sub(d, y, R["p"], Z, allm, [0, 1])
            sub.Zfull = Z
            r, _ = E.run_sub(sub, srcs, pbar)
            rows.append(dict(group=gname, outcome=nm, planted=beta, share_of_E3E6=share, **r))
            print(" ", nm, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "rand_lo", "rand_hi", "p_t_rank")}, flush=True)
    P = pd.DataFrame(rows)
    P.round(5).to_csv(T.OUT / "industry_iv_exposed_subgroup.csv", index=False)
    ch = []
    for gname in groups:
        g = P[P.group == gname].set_index("outcome")
        det = lambda r: bool(r.p_t_rank <= 0.05 and (r.rand_hi < 0 or r.rand_lo > 0))
        pl3 = g.loc["planted -0.3"]
        x1 = bool(det(pl3) and pl3.rand_lo <= -0.3 <= pl3.rand_hi)
        x2 = bool(g.loc["placebo"].p_t_rank > 0.05)
        re = g.loc["real"]
        x3 = bool(x1 and x2 and det(re))
        ch.append(dict(group=gname, X1_informative=x1, X2_placebo=x2, X3_detected=x3, real=f"{re.elasticity:.4f} [{re.rand_lo:.4f},{re.rand_hi:.4f}] p {re.p_t_rank:.3f}",
                       planted_01=f"{g.loc['planted -0.1'].elasticity:.4f} [{g.loc['planted -0.1'].rand_lo:.4f},{g.loc['planted -0.1'].rand_hi:.4f}]",
                       planted_03=f"{pl3.elasticity:.4f} [{pl3.rand_lo:.4f},{pl3.rand_hi:.4f}]", share=float(re.share_of_E3E6)))
    C = pd.DataFrame(ch)
    C.to_csv(T.OUT / "industry_iv_exposed_subgroup_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 80)
    print(P[["group", "outcome", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank"]].round(4).to_string(index=False))
    print(C.to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
