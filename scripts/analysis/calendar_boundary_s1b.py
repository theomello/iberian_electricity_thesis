"""S1b of docs/specs/2026-11-17-calendar-boundary-design.md (amendment 2026-11-16): pooled, year-clustered detectability. Uses only outputs/tables/calendar_boundary_noise*.csv and calendar_boundary_dose.csv.

    .venv/bin/python scripts/analysis/calendar_boundary_s1b.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs" / "tables"


def icc(values, groups):
    df = pd.DataFrame({"v": values, "g": groups}).dropna()
    g = df.groupby("g").v
    k = g.size().to_numpy().astype(float)
    n, a = k.sum(), len(k)
    mean = df.v.mean()
    msb = float((k * (g.mean().to_numpy() - mean) ** 2).sum() / (a - 1))
    msw = float(((df.v - g.transform("mean")) ** 2).sum() / (n - a))
    k0 = (n - (k ** 2).sum() / n) / (a - 1)
    r = (msb - msw) / (msb + (k0 - 1) * msw)
    return float(min(max(r, 0.0), 1.0)), msb, msw


def main():
    ev = pd.read_csv(T / "calendar_boundary_noise.csv")
    dz = pd.read_csv(T / "calendar_boundary_dose.csv")
    pl, mid = ev[ev.kind == "placebo"], ev[ev.kind == "mid-month"]
    sd_pl, sd_mid = float(pl.DD_serv.std(ddof=1)), float(mid.DD_serv.std(ddof=1))
    ss = float((dz.log_dose ** 2).sum())
    rho, msb, msw = icc(mid.DD_serv.to_numpy(), mid.year.to_numpy())
    m = len(dz) / dz.year.nunique()
    deff = 1 + (m - 1) * rho
    se_ind = sd_pl / np.sqrt(ss)
    res = {"events": len(dz), "sum_dose2": ss, "sd_placebo": sd_pl, "sd_midmonth": sd_mid, "rho_midmonth": rho, "MSB": msb, "MSW": msw, "m_per_year": m, "DEFF": deff,
           "SE_independent": se_ind, "detectable_independent": 2.8 * se_ind, "SE_pooled": se_ind * np.sqrt(deff), "detectable_S1b": 2.8 * se_ind * np.sqrt(deff)}
    res["detectable_midmonth_sd"] = 2.8 * sd_mid / np.sqrt(ss) * np.sqrt(deff)
    res["detectable_rho_0.5"] = 2.8 * se_ind * np.sqrt(1 + (m - 1) * 0.5)
    res["S1b_pass"] = bool(res["detectable_S1b"] <= 0.15)
    pd.DataFrame([res]).round(5).to_csv(T / "calendar_boundary_s1b.csv", index=False)
    for k, v in res.items():
        print(f"{k}: {round(v, 4) if isinstance(v, float) else v}")
    print(f"S1b: detectable elasticity {res['detectable_S1b']:.3f} (bar 0.15) -> {'PASS' if res['S1b_pass'] else 'FAIL, close the design'}")


if __name__ == "__main__":
    main()
