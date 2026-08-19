#!/usr/bin/env python3
"""First build of the structural hydro opportunity-cost function.

    .venv/bin/python scripts/analysis/hydro_water_value_structural.py

Follows Arzhintar, Leslie, Neill & Wyrwoll's template (`papers/md/ssrn-5736763.md`,
see `notes/hydro-water-value-design.md`'s 2026-08-18 section), scoped and adapted
to what this repo holds. Scoping check (`hydro_marginal_hours.py`) found 12,470
marginal-hydro periods, 2018-2026, concentrated in a handful of large cascades
(Duero, Tajo, Sil, Hidrocantabrico = 70% of the sample) -- so read any result
here as "how these major cascades value water", not "hydro in general".

STEP 1 -- THE FOC-IMPLIED OPPORTUNITY COST

For periods where a target hydro unit i is the marginal one (its own accepted
offer sets the clearing price), the profit-maximising FOC (Hortacsu & Puller
2008 eq. 2; Arzhintar et al.'s eq. 2-4) rearranges to

    c_i  =  p*  -  (q_i - Q_C_i) / |RD'_i(p*)|

`p*` is the clearing price, `q_i` the unit's own cleared quantity that period,
`Q_C_i` its contract position (PDBF role-code 4, physical bilateral only --
zero where none is on record, the same simplification the rest of this repo's
theta measure carries), and `|RD'_i(p*)|` the slope of the residual demand it
faces at the clearing price.

SIMPLIFICATION, STATED PLAINLY: |RD'_i| IS THE AGGREGATE SLOPE, NOT i's OWN

`residual_demand_slope.py` already computes |RD'(p*)| = density of ALL offers
(every unit, both sides) within +/-h EUR of the clearing price -- explicitly
documented there as "residual demand facing an infinitesimal participant...
every real firm faces a residual demand weakly steeper than this one". Using
it here rather than rebuilding a unit-specific residual demand curve (netting
out unit i's own offers) means `c_i` is a **lower bound** on the true
opportunity cost for large cascades: a unit whose own supply is a meaningful
share of what's near the price band makes the true (netted) curve steeper
than the aggregate one, understating the markup term and therefore
overstating how much of the price is "just cost". Correcting this is
possible (subtract unit i's own quantity from the near-price-band mass
before taking the density) but is not done in this first cut -- flagged
here rather than silently accepted, and worth doing before treating a point
estimate as final. h = 5 EUR/MWh, the middle of `residual_demand_slope.py`'s
own bandwidths.

STEP 2 -- THE REGRESSION

Per Arzhintar et al.'s eq. 5 (their p.26): c_it = b0 + b1*pf_t + b2*Vol_it + e_it,
plain OLS, no interaction between pf and Vol (checked in the paper's own
appendix -- never multiplied together in any specification they run). Two
versions reported: pooled (matching their spec, one facility across time,
implicit b0 for the whole sample) and with unit fixed effects (a robustness
check their setting can't offer, since we have several cascades and they
have one scheme).

- pf: front-quarter OMIP baseload forward, national, monthly
  (`levy_contract_exposure_forward.py`'s own helper).
- Vol: basin-aggregate stored volume level (hm3), MITECO, monthly mean of the
  weekly series, matched to the marginal unit's own basin.

Snow is not included. Iberian hydro is far less snowpack-driven than the
Snowy Scheme this template is built on, and the repo's own rain probe
(`hydro_water_value_precip.py`) already found no signal from precipitation --
adding a variable already shown null elsewhere would not sharpen anything.
"""

from __future__ import annotations

import glob
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_water_value_precip import hydro_units_with_basin  # noqa: E402
from hydro_water_value_reservoir import AMBITO_TO_BASIN  # noqa: E402
from levy_contract_exposure_forward import front_quarter_forward  # noqa: E402
from residual_demand_slope import IDENTITY_TOL, ZERO_PRICE, load_prices, month_slopes  # noqa: E402

BANDWIDTH = "5"  # matches residual_demand_slope.py's slope_h5 / eta_h5
SLOPE_PCTL = 0.01  # drop the thinnest 1% of residual-demand-slope estimates


def basin_volume_level() -> pd.DataFrame:
    """Basin x month mean stored volume (hm3) -- level, not seasonal anomaly."""
    r = pq.read_table(DATA / "miteco/embalses_historico.parquet").to_pandas()
    r["basin"] = r.ambito.map(AMBITO_TO_BASIN)
    r = r.dropna(subset=["basin", "capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]
    weekly = r.groupby(["basin", "date"]).stored_hm3.sum().reset_index()
    weekly["month"] = weekly.date.dt.to_period("M")
    return (weekly.groupby(["basin", "month"], as_index=False)
                  .stored_hm3.mean().rename(columns={"stored_hm3": "vol"}))


def contract_position(units: set[str]) -> pd.DataFrame:
    """PDBF role-4 (bilateral) quantity, per unit-period, MWh. Zero elsewhere."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/pdbf/parquet/pdbf_*.parquet"))):
        t = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw",
                                      "resolution_min", "role_code"]).to_pandas()
        t = t[(t.unit.isin(units)) & (t.role_code == "4")]
        if t.empty:
            continue
        t["qc"] = t.schedule_mw * t.resolution_min / 60.0
        frames.append(t[["date", "period", "unit", "qc"]])
    if not frames:
        return pd.DataFrame(columns=["date", "period", "unit", "qc"])
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d


def build_panel(units: set[str]) -> pd.DataFrame:
    px = load_prices()
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    cols = ["date", "period", "side", "status", "power_mw", "price_eur_mwh",
            "unit", "resolution_min"]

    rows = []
    for i, f in enumerate(files, 1):
        ym = f.stem.replace("bids_", "")
        lo = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").date()
        hi = (pd.Timestamp(lo) + pd.offsets.MonthEnd(1)).date()
        px_m = px[(px.date >= lo) & (px.date <= hi)]
        if px_m.empty:
            continue
        tbl = ds.dataset(f).to_table(
            filter=(pc.field("date") >= lo) & (pc.field("date") <= hi), columns=cols)
        if tbl.num_rows == 0:
            continue
        b = tbl.to_pandas()

        ms = month_slopes(b[["date", "period", "side", "status", "power_mw",
                             "price_eur_mwh"]], px_m)

        mat = b[(b.status == "C") & (b.side == "V")]
        if mat.empty:
            continue
        marg = mat.loc[mat.groupby(["date", "period"]).price_eur_mwh.idxmax(),
                       ["date", "period", "unit"]].rename(columns={"unit": "marginal_unit"})

        own = mat[mat.unit.isin(units)].copy()
        own["q"] = own.power_mw * own.resolution_min / 60.0
        own = own.groupby(["date", "period", "unit"], as_index=False).q.sum()

        m = ms.merge(marg, on=["date", "period"], how="inner")
        m = m[m.marginal_unit.isin(units)]
        if m.empty:
            print(f"  [{i:3d}/{len(files)}] {ym}  0 marginal-hydro periods", end="\r")
            continue
        m = m.merge(own, left_on=["date", "period", "marginal_unit"],
                    right_on=["date", "period", "unit"], how="left")
        m["q_i"] = m.q.fillna(0.0)
        rows.append(m[["date", "period", "marginal_unit", f"slope_h{BANDWIDTH}",
                       "p_star", "q_i", "split", "identity_gap"]])
        print(f"  [{i:3d}/{len(files)}] {ym}  {len(m):,} marginal-hydro periods",
              end="\r", flush=True)

    print(" " * 60, end="\r")
    d = pd.concat(rows, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d.rename(columns={f"slope_h{BANDWIDTH}": "slope"})


def ols(df: pd.DataFrame, y: str, xcols: list[str], cluster: str | None = None):
    X = sm.add_constant(df[xcols])
    m = sm.OLS(df[y], X)
    if cluster:
        return m.fit(cov_type="cluster", cov_kwds={"groups": df[cluster]})
    return m.fit(cov_type="HC1")


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    hy = hydro_units_with_basin()
    mapped = hy.dropna(subset=["basin"])
    units = set(mapped.unit)
    basin_of = dict(zip(mapped.unit, mapped.basin))

    print(f"target set: {len(units)} hydro_ugh units with an identified basin\n")
    print("BUILDING PANEL — one pass over the bid archive\n")
    d = build_panel(units)

    n0 = len(d)
    d = d[(~d.split) & (d.identity_gap <= IDENTITY_TOL) & (d.slope > 0)]
    print(f"periods: {n0:,} marginal-hydro raw -> {len(d):,} after dropping "
          f"split/identity/zero-slope periods\n")

    qc = contract_position(units)
    d = d.merge(qc, left_on=["date", "period", "marginal_unit"],
               right_on=["date", "period", "unit"], how="left")
    d["qc"] = d.qc.fillna(0.0)
    print(f"contract position (PDBF role 4) matched: {(d.qc > 0).mean():.1%} "
          f"of unit-periods; zero (no bilateral on record) elsewhere\n")

    d["c"] = d.p_star - (d.q_i - d.qc) / d.slope

    d["basin"] = d.marginal_unit.map(basin_of)
    d["month"] = d.date.dt.to_period("M")
    vol = basin_volume_level()
    d = d.merge(vol, on=["basin", "month"], how="left")
    pf = front_quarter_forward()
    d["pf"] = d.month.map(pf)
    d = d.dropna(subset=["vol", "pf", "c"])

    print(f"pre-filter sample: {len(d):,} unit-periods, "
          f"{d.marginal_unit.nunique()} units, {d.month.min()} to {d.month.max()}")
    print("implied opportunity cost c, EUR/MWh, before the outlier fix:")
    print(d.c.describe().to_string())

    # TWO DISTINCT OUTLIER MECHANISMS, FIXED AT THE SOURCE, NOT BY TRIMMING c
    #
    # (1) Near-zero-slope blowups. c's max (6,111 EUR/MWh) traces to ONE
    #     period (SIL, 2023-01-25 h20) with slope=0.08 MW/EUR against a
    #     sample median of 354 -- a residual-demand estimate too thin to
    #     trust, not a real opportunity cost. Dropping the bottom 1% of
    #     `slope` removes it and every observation like it.
    # (2) Near-zero/negative price periods. Every negative c in the sample
    #     comes from p_star at or below ~1 EUR/MWh (several below zero).
    #     At these prices a hydro unit is typically being curtailed or
    #     forced to run, not revealing an opportunity cost the FOC this
    #     script uses was built to describe -- a different economic regime,
    #     not noise in the same regime. `residual_demand_slope.py` already
    #     draws this line at ZERO_PRICE = 1 EUR/MWh for the same reason;
    #     reused here rather than picking a new threshold.
    n_pre = len(d)
    slope_floor = d.slope.quantile(SLOPE_PCTL)
    n_thin = int((d.slope < slope_floor).sum())
    n_lowp = int((d.p_star <= ZERO_PRICE).sum())
    d = d[(d.slope >= slope_floor) & (d.p_star > ZERO_PRICE)]
    print(f"\ndropped {n_thin} periods with slope below its p{int(SLOPE_PCTL*100)} "
          f"({slope_floor:.2f} MW/EUR) -- the near-zero-slope blowups")
    print(f"dropped {n_lowp} periods with p_star <= {ZERO_PRICE:g} EUR/MWh -- "
          f"curtailment/must-run, not a cost-revealing bid")
    print(f"final estimation sample: {len(d):,} of {n_pre:,} unit-periods\n")

    print("implied opportunity cost c, EUR/MWh, after the fix:")
    print(d.c.describe().to_string())
    print(f"negative c remaining: {(d.c < 0).mean():.2%}\n")

    print("=" * 72)
    print("REGRESSION: c_it = b0 + b1*pf_t + b2*Vol_it + e_it")
    print("=" * 72)

    r_pooled = ols(d, "c", ["pf", "vol"], cluster="marginal_unit")
    print("\nPOOLED (Arzhintar et al.'s own spec, SE clustered on unit)\n")
    print(r_pooled.summary().tables[1])

    dummies = pd.get_dummies(d.marginal_unit, prefix="u", drop_first=True, dtype=float)
    d_fe = pd.concat([d, dummies], axis=1)
    r_fe = ols(d_fe, "c", ["pf", "vol"] + list(dummies.columns),
              cluster="marginal_unit")
    print("\nWITH UNIT FIXED EFFECTS (robustness -- their setting can't offer this)\n")
    tab = r_fe.summary().tables[1]
    print(tab)  # includes unit dummies; pf/vol rows are what matter

    print("\nREAD: b1 > 0 means the opportunity cost rises with the forward "
          "price (near-complete passthrough of expectations, as Arzhintar et "
          "al. find, b1~1.26). b2 < 0 means fuller reservoirs imply a LOWER "
          "opportunity cost -- the textbook scarcity prediction. Compare "
          "against Arzhintar et al.'s own b1=1.260, b2=-0.028 (their Table 1, "
          "printed p.28) -- same sign as expected, magnitude need not match "
          "given the aggregate-slope simplification above.")

    if args.save:
        p = ROOT / "outputs" / "tables" / "hydro_water_value_structural_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
