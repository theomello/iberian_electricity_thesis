#!/usr/bin/env python3
"""Stage 1 of the within-Iberia counterfactual: out-of-sample accuracy before any rho (notes/rq-crisis-quantity.md, H8, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_predictive_stage1.py

Per country (Iberia; Italy as the placebo's recipe) and variant (gas in, gas out): ridge penalty by rolling-origin cross-validation on the fit weeks; out-of-sample R^2 relative to the
unit-mean-only model at the four origins; the high-gas holdout; for Iberia the MAE against the Italy-based gsc (r = 0) on the same cells. Gates (a)-(c) of H8.
Writes outputs/tables/gas_cap_quantity_predictive_stage1.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_predictive import HORIZON, LAMBDAS, ORIGINS, T, VARIANTS, clip01, gsc_r0, load, mean_only, ridge_fit, ridge_predict  # noqa: E402


def r2_rel(y, pred, base):
    o = ~np.isnan(y) & ~np.isnan(pred) & ~np.isnan(base)
    return 1 - np.sum((y[o] - pred[o]) ** 2) / np.sum((y[o] - base[o]) ** 2)


def mae(y, pred):
    o = ~np.isnan(y) & ~np.isnan(pred)
    return float(np.mean(np.abs(y[o] - pred[o])))


def main() -> int:
    s = load()
    M, ib, cols, fit, cond = s["M"], s["ib"], s["cols"], s["fit"], s["cond"]
    rows = []
    for country, mask in (("ES", ib), ("IT", ~ib)):
        Y = M[mask]
        for var, names in VARIANTS[country].items():
            X = cond[names].to_numpy()
            # penalty by pooled rolling-origin squared error
            sse = {}
            for lam in LAMBDAS:
                tot = []
                for t in ORIGINS:
                    tr, te = fit[:t], fit[t:t + HORIZON]
                    pr = clip01(ridge_predict(ridge_fit(Y, X, tr, lam), te))
                    o = ~np.isnan(Y[:, te]) & ~np.isnan(pr)
                    tot.append(((Y[:, te] - pr)[o] ** 2).sum() / o.sum())
                sse[lam] = float(np.mean(tot))
            lam = min(sse, key=sse.get)
            r2s, ys, pm, pb = [], [], [], []
            for t in ORIGINS:
                tr, te = fit[:t], fit[t:t + HORIZON]
                pr = clip01(ridge_predict(ridge_fit(Y, X, tr, lam), te))
                base = mean_only(Y, tr, len(te))
                r2s.append(r2_rel(Y[:, te], pr, base))
                ys.append(Y[:, te])
                pm.append(pr)
                if country == "ES":
                    pb.append(clip01(gsc_r0(M, ib, tr, te)[ib]))
            r2_pos = int(sum(r > 0 for r in r2s))
            mae_m = mae(np.hstack(ys), np.hstack(pm))
            mae_b = mae(np.hstack(ys), np.hstack(pb)) if pb else np.nan
            # high-gas holdout
            psv = cond["psv_bid"].to_numpy()
            med = np.median(psv[fit])
            tr = fit[psv[fit] <= med]
            te = fit[psv[fit] > med]
            pr = clip01(ridge_predict(ridge_fit(Y, X, tr, lam), te))
            r2_h = r2_rel(Y[:, te], pr, mean_only(Y, tr, len(te)))
            mae_hm = mae(Y[:, te], pr)
            mae_hb = mae(Y[:, te], clip01(gsc_r0(M, ib, tr, te)[ib])) if country == "ES" else np.nan
            gate_a = r2_pos >= 3
            gate_b = r2_h > 0
            gate_c = True if country == "IT" else (mae_m <= 0.8 * mae_b and mae_hm <= 0.8 * mae_hb)
            rows.append({"country": country, "variant": var, "predictors": "+".join(names), "lambda": lam, "r2_origins": [round(r, 3) for r in r2s],
                         "origins_positive": r2_pos, "r2_high_gas": r2_h, "mae_model": mae_m, "mae_gsc": mae_b, "mae_hg_model": mae_hm, "mae_hg_gsc": mae_hb,
                         "gate_a": gate_a, "gate_b": gate_b, "gate_c": gate_c, "pass": gate_a and gate_b and gate_c})
            print(f"\n{country} {var} ({'+'.join(names)}): lambda {lam}; pooled CV mse by lambda " + ", ".join(f"{k}: {v:.4f}" for k, v in sse.items()))
            print(f"  (a) R2 vs unit mean at origins {[round(r, 3) for r in r2s]} -> {r2_pos} of 4 positive: {'ok' if gate_a else 'FAIL'}")
            print(f"  (b) high-gas holdout R2 {r2_h:+.3f} ({len(tr)} train, {len(te)} test weeks): {'ok' if gate_b else 'FAIL'}")
            if country == "ES":
                print(f"  (c) MAE model {mae_m:.4f} vs gsc r=0 {mae_b:.4f} (ratio {mae_m / mae_b:.2f}); high-gas {mae_hm:.4f} vs {mae_hb:.4f} (ratio {mae_hm / mae_hb:.2f}); need <= 0.80: {'ok' if gate_c else 'FAIL'}")
            print(f"  => {'PASS' if rows[-1]['pass'] else 'FAIL'}")
    D = pd.DataFrame(rows)
    D.to_csv(T / "gas_cap_quantity_predictive_stage1.csv", index=False)
    print("\nStage 1 summary:\n" + D[["country", "variant", "lambda", "origins_positive", "r2_high_gas", "gate_a", "gate_b", "gate_c", "pass"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
