"""High-voltage demand against low-voltage demand (the household control), instrumented price.

Outcomes: log of each voltage level E1..E6 (ESIOS 1202-1207) and of E4+E5+E6 (>= 72.5 kV), and the log ratio of each to
E0 (low voltage, ESIOS 1201). Instrument: wind forecast (ESIOS 1777). Variants as in demand_placebo_diagnosis.py:
V0 baseline (both forecasts), V3 wind only + rich weather, V4 = V3 at night. V3 also by era. Pass rule, set before the
run: a level counts as responding differently from households only if its ratio to E0 is negative and more than two
standard errors from zero in V3 and V4. Writes outputs/tables/demand_industry_vs_households.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demand_reduced_form import OUT, load  # noqa: E402
from demand_placebo_diagnosis import design, resid_mat, iv  # noqa: E402


def main():
    d0 = load().dropna().reset_index(drop=True)
    d0["E456"] = d0.E4_1205 + d0.E5_1206 + d0.E6_1207
    lv = {"E1": "E1_1202", "E2": "E2_1203", "E3": "E3_1204", "E4": "E4_1205", "E5": "E5_1206", "E6": "E6_1207",
          "E4+E5+E6": "E456"}
    print("mean GW:", {k: round(d0[c].mean() / 1000, 3) for k, c in lv.items()}, "E0", round(d0.E0_lowvolt_1201.mean() / 1000, 2))
    Y = {}
    for k, c in lv.items():
        ok = d0[c] > 0
        Y[k] = np.log(d0[c].where(ok))
        Y[k + " / E0"] = np.log(d0[c].where(ok) / d0.E0_lowvolt_1201)
    Y = pd.DataFrame(Y)
    specs = [("V0 baseline", False, False, ["wind_fc", "solar_fc"], None),
             ("V3 wind + rich weather", False, True, ["wind_fc"], None),
             ("V4 night + rich weather", True, True, ["wind_fc"], None),
             ("V3 2019-2021", False, True, ["wind_fc"], (2019, 2021)),
             ("V3 2022-2023", False, True, ["wind_fc"], (2022, 2023)),
             ("V3 2024-2025", False, True, ["wind_fc"], (2024, 2025))]
    rows = []
    for name, night, rich, zc, era in specs:
        m = np.ones(len(d0), bool)
        if night:
            m &= (d0.hour <= 6).to_numpy()
        if era:
            yr = d0.ym.str[:4].astype(int)
            m &= ((yr >= era[0]) & (yr <= era[1])).to_numpy()
        d = d0[m].reset_index(drop=True)
        y = Y[m].reset_index(drop=True)
        W = design(d, rich)
        keep = np.isfinite(W).all(axis=1)
        d, y, W = d[keep].reset_index(drop=True), y[keep].reset_index(drop=True), W[keep]
        g = d.date.factorize()[0]
        rp = resid_mat(d.price_es.to_numpy()[:, None], W)[:, 0]
        Z = resid_mat(d[zc].to_numpy(), W)
        mp = d.price_es.mean()
        # each outcome on its own finite rows would change the sample; require finite everywhere
        fin = np.isfinite(y).all(axis=1).to_numpy()
        if not fin.all():
            d, y, W = d[fin].reset_index(drop=True), y[fin].reset_index(drop=True), W[fin]
            g = d.date.factorize()[0]
            rp = resid_mat(d.price_es.to_numpy()[:, None], W)[:, 0]
            Z = resid_mat(d[zc].to_numpy(), W)
        Ym = resid_mat(y.to_numpy(), W)
        F, res = iv(Ym, rp, Z, g)
        for (b, se), k in zip(res, y.columns):
            rows.append(dict(variant=name, outcome=k, n=len(d), first_stage_F=F, semi_elast_pct_per_eur=100 * b,
                             se=100 * se, elasticity_at_mean=b * mp, t=b / se))
        print(name, "n", len(d), "F", round(F, 0), flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "demand_industry_vs_households.csv", index=False)
    pd.set_option("display.width", 200)
    p = out.pivot(index="outcome", columns="variant", values="semi_elast_pct_per_eur").round(3)
    t = out.pivot(index="outcome", columns="variant", values="t").round(1)
    print("semi-elasticity (% per EUR/MWh)\n", p.to_string(), "\n\nt\n", t.to_string())


if __name__ == "__main__":
    main()
