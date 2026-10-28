#!/usr/bin/env python3
"""Gas cap: Iberia's jump at 2022-06-15 minus Italy's on the same days (difference in discontinuities).

    .venv/bin/python scripts/analysis/gas_cap_diff_disc.py [--reps 499]

The sharp break within Iberia (step 2b, `gas_cap_within_iberia.py`) stopped because ordinary
weeks move Iberian offers by EUR 35-130. If part of that is common to Italy (gas-price news),
differencing it out sharpens the break. Per country, J_bar = mean over units of
[mean(offer - gross cost) over the k days from t] - [the same over the k days before t];
D(t) = J_bar(Iberia) - J_bar(Italy). At the break, bidding at cost gives D = -Y_bar, ignoring the
subsidy D = 0: rho = -D / Y_bar. Same rule as step 2b: D is read only if the 2.5-97.5% range of
D(t) over every pre-period day (windows ending before 2022-05-14) lies within +-Y_bar/5
(0.05 for run20). Outcomes om (p_mid) and run20; p_band is the clearing price, not conduct, and is
shown only for completeness. Firm block bootstrap, within each country.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gas_cap_within_iberia import COLS, KS, PANEL, PUBLISHED, T0, jumps  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables" / "gas_cap_diff_disc.csv"


def daily() -> pd.DataFrame:
    h = pd.read_parquet(PANEL, columns=COLS + ["iberia"])
    h["ob"] = h.p_band - h.cost_gross
    h["om"] = h.p_mid - h.cost_gross
    d = h.groupby(["iberia", "unit", "date"]).agg(firm=("firm", "first"), ob=("ob", "mean"), om=("om", "mean"),
                                                 run20=("run20", "mean"), Y=("subsidy", "first")).reset_index()
    d["firm"] = d.firm.fillna(d.unit)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=499)
    a = ap.parse_args()
    rng = np.random.default_rng(20261028)
    d = daily()
    Yd = d[d.iberia].drop_duplicates("date").set_index("date").Y.sort_index()
    firm = d.drop_duplicates("unit").set_index("unit").firm
    ib, it = d[d.iberia], d[~d.iberia]
    rows = []
    for k in KS:
        Ybar = Yd[T0:T0 + pd.Timedelta(days=k - 1)].mean()
        days = pd.date_range(d.date.min() + pd.Timedelta(days=k), PUBLISHED - pd.Timedelta(days=k))
        for y, thr in (("om", Ybar / 5), ("run20", 0.05), ("ob", Ybar / 5)):
            Ji, Jt = jumps(ib, y, T0, k), jumps(it, y, T0, k)
            D = Ji.mean() - Jt.mean()
            fi, ft = firm.reindex(Ji.index), firm.reindex(Jt.index)
            bi = {f: Ji[fi == f].to_numpy() for f in fi.unique()}
            bt = {f: Jt[ft == f].to_numpy() for f in ft.unique()}
            draws = [np.mean(np.concatenate([bi[f] for f in rng.choice(list(bi), len(bi))]))
                     - np.mean(np.concatenate([bt[f] for f in rng.choice(list(bt), len(bt))])) for _ in range(a.reps)]
            lo, hi = np.percentile(draws, [2.5, 97.5])
            pl_ib = np.array([jumps(ib, y, t, k).mean() for t in days])
            pl_it = np.array([jumps(it, y, t, k).mean() for t in days])
            pl = pl_ib - pl_it
            ok = ~np.isnan(pl)
            p_lo, p_hi = np.percentile(pl[ok], [2.5, 97.5])
            i_lo, i_hi = np.percentile(pl_ib[ok], [2.5, 97.5])
            common = np.corrcoef(pl_ib[ok], pl_it[ok])[0, 1]
            passed = max(abs(p_lo), abs(p_hi)) <= thr
            rho = -D / Ybar if y != "run20" else np.nan
            print(f"k={k:2d} {y:5s} units {len(Ji)}/{len(Jt)}  J Iberia {Ji.mean():+8.2f}  Italy {Jt.mean():+8.2f}"
                  f"  D {D:+8.2f} [{lo:+.2f}, {hi:+.2f}]  rho {rho:+.2f}  Ybar {Ybar:.1f}\n"
                  f"        placebo 95%: D [{p_lo:+.2f}, {p_hi:+.2f}] vs +-{thr:.2f} -> {'PASS' if passed else 'FAIL'};"
                  f" Iberia alone [{i_lo:+.2f}, {i_hi:+.2f}]; corr of daily jumps {common:+.2f}")
            rows.append(dict(k=k, outcome=y, n_ib=len(Ji), n_it=len(Jt), J_ib=Ji.mean(), J_it=Jt.mean(), D=D,
                             lo=lo, hi=hi, rho=rho, Ybar=Ybar, pl_lo=p_lo, pl_hi=p_hi, ib_pl_lo=i_lo, ib_pl_hi=i_hi,
                             corr=common, passed=passed))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
