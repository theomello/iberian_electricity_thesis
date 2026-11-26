"""Part B of docs/specs/2026-11-26-orthogonal-and-sensitivity-design.md: how much drift would overturn each result.

    tou_drift_sensitivity.py            # observed placebo betas 2014-2019 only
    tou_drift_sensitivity.py --with2020 # additionally fixes the 2020 placebo beta (Part C) as the observed anchor

Deterministic sensitivity bands (after Rambachan and Roth). Placebo betas are the bias path 2014-2019; the effect is b_2021 minus the
unobserved bias delta_2021. Second-difference restriction: |second difference| <= M = m * M_obs; relative-magnitude restriction:
|delta_2021 - delta_last| <= Mbar * gap * (largest year-to-year change). Series: E0 baseline, 6.2/6.3/6.4 baseline and joint regression.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent.parent.parent / "outputs" / "tables"
YEARS = [2014, 2015, 2016, 2017, 2018, 2019]
WITH2020 = "--with2020" in sys.argv
STEP3 = {"6.2": (-0.0832, -0.0792), "6.3": (-0.4304, -0.0198), "6.4": (-0.6624, -0.5719)}  # baseline mean-null, trend-null effects


def betas():
    out = {}
    s6 = pd.read_csv(OUT / "tou_industry_six_summer.csv")
    e0 = s6[(s6.series == "E0") & (s6["shift"] == 0)].set_index("summer").eta
    out["E0 baseline"] = (e0.loc[YEARS].to_numpy(), float(e0.loc[2021]))
    s3 = pd.read_csv(OUT / "tou_tariff_drift_step3.csv").set_index("series")
    for t in ("6.2", "6.3", "6.4"):
        pl = dict(p.split(":") for p in s3.loc[t, "placebos"].split())
        out[f"{t} baseline"] = (np.array([float(pl[str(y)]) for y in YEARS]), float(s3.loc[t, "eta_2021"]))
        J = pd.read_csv(OUT / f"tou_joint_regression_{t}.csv")
        b = J[J.variant == "main"].set_index("summer").beta
        out[f"{t} joint"] = (b.loc[YEARS].to_numpy(), float(b.loc[2021]))
    return out


def anchor2020():
    if not WITH2020:
        return {}
    p = OUT / "tou_placebo_2020.csv"
    d = pd.read_csv(p)
    return {(r.series, r.spec): r.beta for r in d.itertuples()}


def main():
    B, A = betas(), anchor2020()
    rows = []
    for name, (pl, b21) in B.items():
        series, spec = name.split()
        d20 = A.get((series, spec))
        path = list(pl) + ([d20] if d20 is not None else [])
        sd2 = np.abs(np.diff(pl, 2))
        M_obs = float(sd2.max())
        maxd = float(np.abs(np.diff(path)).max())
        last, gap = (path[-1], 1) if d20 is not None else (pl[-1], 2)
        for m in (1.0, 1.5, 2.0, 3.0):
            M = m * M_obs
            if d20 is None:
                x_lo, x_hi = 2 * pl[-1] - pl[-2] - M, 2 * pl[-1] - pl[-2] + M
                z_lo, z_hi = 2 * x_lo - pl[-1] - M, 2 * x_hi - pl[-1] + M
            else:
                z_lo, z_hi = 2 * d20 - pl[-1] - M, 2 * d20 - pl[-1] + M
            rows.append(dict(series=series, spec=spec, restriction="second difference", level=m, lo=b21 - z_hi, hi=b21 - z_lo, M_obs=M_obs, anchor_2020=d20))
        for mb in (0.5, 1.0, 1.5, 2.0):
            r = mb * gap * maxd
            rows.append(dict(series=series, spec=spec, restriction="relative magnitude", level=mb, lo=b21 - last - r, hi=b21 - last + r, M_obs=maxd, anchor_2020=d20))
        # breakdown values
        center = (3 * pl[-1] - 2 * pl[-2]) if d20 is None else (2 * d20 - pl[-1])
        bd_sd = abs(b21 - center) / ((3 if d20 is None else 1) * M_obs)
        bd_rm = abs(b21 - last) / (gap * maxd)
        rows.append(dict(series=series, spec=spec, restriction="breakdown second difference (m*)", level=bd_sd, lo=np.nan, hi=np.nan, M_obs=M_obs, anchor_2020=d20))
        rows.append(dict(series=series, spec=spec, restriction="breakdown relative magnitude (Mbar*)", level=bd_rm, lo=np.nan, hi=np.nan, M_obs=maxd, anchor_2020=d20))
    R = pd.DataFrame(rows)
    tag = "with2020" if WITH2020 else "base"
    R.round(5).to_csv(OUT / f"tou_drift_sensitivity_{tag}.csv", index=False)
    pd.set_option("display.width", 220)
    print(f"[{tag}] bands for the effect (2021 estimate minus bias):")
    for name in B:
        series, spec = name.split()
        g = R[(R.series == series) & (R.spec == spec)]
        sd1 = g[(g.restriction == "second difference") & (g.level == 1.0)].iloc[0]
        rm1 = g[(g.restriction == "relative magnitude") & (g.level == 1.0)].iloc[0]
        bsd = g[g.restriction.str.startswith("breakdown second")].level.iloc[0]
        brm = g[g.restriction.str.startswith("breakdown relative")].level.iloc[0]
        robust = (sd1.hi < 0 or sd1.lo > 0) and (rm1.hi < 0 or rm1.lo > 0)
        print(f"{name:14s} 2021 {B[name][1]:+.3f} | SD m=1: [{sd1.lo:+.3f}, {sd1.hi:+.3f}] breakdown m* {bsd:.2f} | RM Mbar=1: [{rm1.lo:+.3f}, {rm1.hi:+.3f}] breakdown Mbar* {brm:.2f} | B2 {'robust' if robust else 'fragile'}")
    print("\nB3 (baseline 6.x): mean-null and trend-null effects against the m=1 and Mbar=1 bands")
    for t, (mn, tr) in STEP3.items():
        g = R[(R.series == t) & (R.spec == "baseline")]
        sd1 = g[(g.restriction == "second difference") & (g.level == 1.0)].iloc[0]
        rm1 = g[(g.restriction == "relative magnitude") & (g.level == 1.0)].iloc[0]
        ins = lambda v, b: b.lo <= v <= b.hi
        print(f"  {t}: mean null {mn:+.3f} inside SD band {ins(mn, sd1)}, RM band {ins(mn, rm1)}; trend null {tr:+.3f} inside SD band {ins(tr, sd1)}, RM band {ins(tr, rm1)}")


if __name__ == "__main__":
    main()
