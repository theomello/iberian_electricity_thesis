#!/usr/bin/env python3
"""Gas-cap pass-through within Iberia: the sharp break at 2022-06-15, and monthly Design B.

    .venv/bin/python scripts/analysis/gas_cap_within_iberia.py [--reps 499]

Steps 2b and 2c of docs/specs/2026-10-28-gas-cap-conduct-design.md, fixed there before running.
Both use only Iberian units, after the comparison with Italy failed to identify pass-through.

**2b, the sharp break.** The subsidy Y starts on delivery day 2022-06-15 for every plant. Per unit,
J_i = mean(offer - gross cost) over the k delivery days from 15 June minus the same over the k days
before. Bidding at cost gives J = -Y_bar, ignoring the subsidy J = 0, so rho_break = -J_bar / Y_bar.
For run20 (MW at or below net cost + 20, over K) bidding at cost gives no change and ignoring the
subsidy a fall. The reference is the same statistic at every pre-period day whose windows end
before the decree's publication (2022-05-14); the break is read only if the 2.5-97.5% range of those
placebo jumps lies within +-Y_bar/5 (0.05 for run20).

**2c, monthly Design B.** Unit-month means: o = a_i + b_g*c + b_n*(c - Y) [+ controls], c the
bid-time gross cost. At cost (b_g, b_n) = (0, 1); ignoring the subsidy (1, 0); rho = b_n/(b_g + b_n).
Premise check: on the months with Y = 0 the slope of o on c is within 0.3 of one. Threat check: c in
quintile bins, the coefficient on -Y then read against the pre-cap slope.

Gas is the main group; coal, whose cost the subsidy nearly wiped out, is shown beside it. Inference:
firm block bootstrap. The coal unit-hours are built here with the gas panel's own rules and cached
in outputs/tables/gas_cap_coal_panel.parquet.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gas_cap_offer_panel as gp  # noqa: E402
from gas_cap_conditional_pretrend import controls, ZS  # noqa: E402

PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
COAL = ROOT / "outputs" / "tables" / "gas_cap_coal_panel.parquet"
OUT = ROOT / "outputs" / "tables" / "gas_cap_within_iberia.csv"
T0 = pd.Timestamp("2022-06-15")
PUBLISHED = pd.Timestamp("2022-05-14")
KS = (7, 3, 14)
COLS = ["unit", "date", "firm", "p_band", "p_mid", "run20", "cost", "cost_gross", "subsidy"]


def coal_panel() -> pd.DataFrame:
    if COAL.exists():
        return pd.read_parquet(COAL)
    s, cost = gp.iberia_steps("coal")
    h = gp.unit_hour(s, cost).merge(cost, on=["unit", "date"], how="left")
    h["firm"] = gp.majority_group(h[["unit", "date"]], exposed=False).to_numpy()
    h.to_parquet(COAL, index=False)
    return h


def daily() -> pd.DataFrame:
    g = pd.read_parquet(PANEL, columns=COLS + ["iberia"]).query("iberia").drop(columns="iberia").assign(fuel="gas")
    c = coal_panel()[COLS].assign(fuel="coal")
    h = pd.concat([g, c], ignore_index=True)
    h["ob"] = h.p_band - h.cost_gross
    h["om"] = h.p_mid - h.cost_gross
    d = h.groupby(["fuel", "unit", "date"]).agg(
        firm=("firm", "first"), ob=("ob", "mean"), om=("om", "mean"), run20=("run20", "mean"),
        p_band=("p_band", "mean"), p_mid=("p_mid", "mean"), c=("cost_gross", "first"),
        Y=("subsidy", "first")).reset_index()
    d["firm"] = d.firm.fillna(d.unit)
    return d


def jumps(d: pd.DataFrame, y: str, t0: pd.Timestamp, k: int) -> pd.Series:
    """J_i per unit: mean of y over [t0, t0+k) minus over [t0-k, t0); units with half the days in each."""
    w = d[(d.date >= t0 - pd.Timedelta(days=k)) & (d.date < t0 + pd.Timedelta(days=k))].dropna(subset=[y])
    after = w.date >= t0
    g = w.groupby(["unit", after])[y].agg(["mean", "size"]).unstack()
    if g.empty or not {True, False} <= set(g["mean"].columns):
        return pd.Series(dtype=float)
    ok = (g["size"] >= k / 2).all(axis=1)
    return (g["mean"][True] - g["mean"][False])[ok]


def boot_mean(J: pd.Series, firm: pd.Series, reps: int, rng) -> tuple[float, float]:
    f = firm.reindex(J.index)
    fs = f.unique()
    by = {x: J[f == x].to_numpy() for x in fs}
    m = [np.mean(np.concatenate([by[x] for x in rng.choice(fs, len(fs))])) for _ in range(reps)]
    return tuple(np.nanpercentile(m, [2.5, 97.5]))


def sharp_break(d: pd.DataFrame, reps: int, rng, rows: list) -> None:
    Yd = d.drop_duplicates("date").set_index("date").Y.sort_index()
    firm = d.drop_duplicates("unit").set_index("unit").firm
    print("\n=== 2b. sharp break at 2022-06-15 (delivery day) ===")
    for fuel in ("gas", "coal"):
        x = d[d.fuel == fuel]
        for k in KS:
            Ybar = Yd[T0:T0 + pd.Timedelta(days=k - 1)].mean()
            pl_days = pd.date_range(x.date.min() + pd.Timedelta(days=k), PUBLISHED - pd.Timedelta(days=k))
            for y, thr in (("ob", Ybar / 5), ("om", Ybar / 5), ("run20", 0.05)):
                J = jumps(x, y, T0, k)
                if J.empty:
                    continue
                lo, hi = boot_mean(J, firm, reps, rng)
                pl = np.array([jumps(x, y, t, k).mean() for t in pl_days])
                p_lo, p_hi = np.nanpercentile(pl, [2.5, 97.5])
                passed = max(abs(p_lo), abs(p_hi)) <= thr
                rho = -J.mean() / Ybar if y != "run20" else np.nan
                print(f"  {fuel:4s} k={k:2d} {y:5s} units {len(J):2d}  J {J.mean():+8.2f} [{lo:+.2f}, {hi:+.2f}]"
                      f"  Ybar {Ybar:6.1f}  rho {rho:+.2f}  placebo 95% [{p_lo:+.2f}, {p_hi:+.2f}]"
                      f" vs +-{thr:.2f}: {'PASS' if passed else 'FAIL'}")
                rows.append(dict(design="break", fuel=fuel, k=k, outcome=y, n=len(J), est=J.mean(), lo=lo,
                                 hi=hi, Ybar=Ybar, rho=rho, pl_lo=p_lo, pl_hi=p_hi, passed=passed))
    g = d[(d.fuel == "gas") & d.date.between("2022-04-15", "2022-07-31")]
    wk = g.groupby(g.date.dt.to_period("W").dt.start_time)[["ob", "om", "run20", "c", "Y"]].mean()
    print("\n  gas, weekly means around the break (anticipation window from 2022-05-14):\n" + wk.round(2).to_string())


def fe_ols(m: pd.DataFrame, y: str, X: list[str]) -> np.ndarray:
    z = m[[y] + X].astype(float)
    z = z - z.groupby(m.unit.to_numpy()).transform("mean")
    return np.linalg.lstsq(z[X].to_numpy(), z[y].to_numpy(), rcond=None)[0]


def design_b(d: pd.DataFrame, reps: int, rng, rows: list) -> None:
    print("\n=== 2c. monthly Design B ===")
    z = controls()
    z["ym"] = z.date.dt.to_period("M")
    Z = z.groupby("ym")[ZS].mean()
    d = d.assign(ym=d.date.dt.to_period("M"))
    m = d.groupby(["fuel", "unit", "ym"]).agg(firm=("firm", "first"), p_band=("p_band", "mean"),
                                             p_mid=("p_mid", "mean"), c=("c", "mean"), Y=("Y", "mean")).reset_index()
    m["net"] = m.c - m.Y
    m["negY"] = -m.Y
    m = m.join(Z, on="ym")
    m["cbin"] = pd.qcut(m.c, 5, labels=False)
    bins = pd.get_dummies(m.cbin, prefix="cb", drop_first=True).astype(float)
    m = pd.concat([m, bins], axis=1)
    specs = {"linear": ["c", "net"], "controls": ["c", "net"] + ZS, "bins": list(bins.columns) + ["negY"]}
    for sample in ("gas", "gas+coal"):
        for y in ("p_band", "p_mid"):
            s = m[m.fuel.isin(sample.split("+"))].dropna(subset=[y, "c"] + ZS)
            s = s[s.groupby("unit").ym.transform("size") >= 12]
            pre = s[s.Y == 0]
            b0 = fe_ols(pre, y, ["c"])[0]
            firms = s.firm.unique()
            for name, X in specs.items():
                def est(t):
                    b = fe_ols(t, y, X)
                    if name == "bins":
                        return np.array([np.nan, b[-1], np.nan])
                    return np.array([b[0], b[1], b[1] / (b[0] + b[1])])
                e = est(s)
                dr = []
                for _ in range(reps):
                    pick = rng.choice(firms, len(firms))
                    t = pd.concat([s[s.firm == f].assign(unit=s[s.firm == f].unit + f"#{i}") for i, f in enumerate(pick)])
                    dr.append(est(t))
                lo, hi = np.nanpercentile(np.array(dr), [2.5, 97.5], axis=0)
                tag = "PASS" if abs(b0 - 1) < 0.3 else "FAIL"
                print(f"  {sample:8s} {y:6s} {name:8s} units {s.unit.nunique():2d}  pre slope {b0:.2f} ({tag})"
                      f"  b_g {e[0]:+.2f} [{lo[0]:+.2f}, {hi[0]:+.2f}]  b_n {e[1]:+.2f} [{lo[1]:+.2f}, {hi[1]:+.2f}]"
                      f"  rho {e[2]:+.2f} [{lo[2]:+.2f}, {hi[2]:+.2f}]")
                rows.append(dict(design=f"B_{name}", fuel=sample, k=np.nan, outcome=y, n=s.unit.nunique(),
                                 est=e[1], lo=lo[1], hi=hi[1], rho=e[2], b_g=e[0], pre_slope=b0,
                                 passed=abs(b0 - 1) < 0.3))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=499)
    a = ap.parse_args()
    rng = np.random.default_rng(20261028)
    d = daily()
    print(d.groupby("fuel").agg(units=("unit", "nunique"), days=("date", "nunique")).to_string())
    rows: list = []
    sharp_break(d, a.reps, rng, rows)
    design_b(d, a.reps, rng, rows)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
