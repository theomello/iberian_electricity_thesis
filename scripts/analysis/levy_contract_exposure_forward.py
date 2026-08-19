#!/usr/bin/env python3
"""Stage C: does controlling for the forward price stabilise Design 4's beta?

    .venv/bin/python scripts/analysis/levy_contract_exposure_forward.py

THE DIAGNOSIS THIS TESTS

`levy_contract_exposure.py` ("Design 4" in `notes/rq-gas-cap-conduct.md`) is
the best-identified design tried for the 2021 windfall levy: both placebos
pass, but the sign of beta flips across functional form and across trimming
in levels. `levy_contract_exposure_reservoir.py` ("Stage B") tested whether
reservoir fill level was the omitted variable behind that instability --
fill level carries real signal, but partialling it out barely moved beta
(third decimal place), ruling out the simplest omitted-variable story.

This script tests the other candidate the paper read for
`hydro-water-value-design.md` (Arzhintar, Leslie, Neill & Wyrwoll) actually
points at: hydro's offer tracks the *expected future price*, not (only) the
current reservoir state, and that paper's own fix for exactly this confound
is to put the forward price in the same regression as the water-state
variable, rather than regressing offer on water state alone. Design 4's
treatment variable is `exposure_i * intensity_t` -- built from the *current*
gas price, not the forward price -- so if a heavily-exposed plant's water
value tracks the *forward* curve more than an unhedged plant's does (a
hedged plant has less reason to trade off today's dispatch against tomorrow's
price), the omitted variable is not the forward price itself (it's a single
national series, absorbed entirely by month fixed effects) but its
INTERACTION with exposure -- the same functional shape `treat` already has.

METHOD: FRISCH-WAUGH-LOVELL, SAME PATTERN AS STAGE B

Partial `exposure_i * pf_t` (front-quarter OMIP forward price, national,
monthly) out of `treat = exposure_i * intensity_t`, after unit+month
demeaning, exactly as Stage B partials out `exposure_i`-implicit fill
anomaly. A raw, un-interacted `pf_t` cannot do this job at all: it varies
only by month, so it would be absorbed completely by the month fixed effects
already in the specification and could never move beta. The interaction with
exposure is what survives fixed-effect demeaning and is the only form in
which "the forward price" is a candidate omitted variable here.

THE FORWARD SERIES

Front-quarter OMIP baseload forward (`data/omip/parquet/omip_forwards_ES_*`,
maturity == "Quarter"): for each trading day, the nearest quarterly contract
whose delivery has not yet started, price taken as the settlement
(`price_ref_eur_mwh`, falling back to the previous session's settlement
where the current one is missing), averaged to the month. 101 months,
2018-01 to 2026-05, no gaps.

SAMPLE

Same restriction as Stage B: the 25 `hydro_ugh` units whose basin is
identifiable from the `cab` name, a different (smaller) filter than Design
4's original 23-unit contract-exposure sample, so baseline is rerun on this
sample too -- the comparison that matters is baseline vs. controlled WITHIN
this script, on the same units.
"""

from __future__ import annotations

import glob
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawback_intensity_did import gas_intensity, twfe  # noqa: E402
from hydro_water_value_precip import hydro_units_with_basin  # noqa: E402
from levy_contract_exposure import LEVY_START_M, contract_exposure  # noqa: E402
from levy_contract_exposure import panel as offer_panel  # noqa: E402
from levy_contract_exposure_reservoir import orthogonalise  # noqa: E402


def front_quarter_forward() -> pd.Series:
    """Monthly front-quarter OMIP baseload forward, EUR/MWh, ES zone."""
    files = sorted(glob.glob(str(DATA / "omip/parquet/omip_forwards_ES_*.parquet")))
    q = pd.concat([pq.read_table(f, columns=[
        "trade_date", "maturity", "contract", "price_ref_eur_mwh",
        "price_ref_prev_eur_mwh"]).to_pandas() for f in files], ignore_index=True)
    q = q[q.maturity == "Quarter"].copy()
    q["trade_date"] = pd.to_datetime(q.trade_date)
    q["price"] = q.price_ref_eur_mwh.fillna(q.price_ref_prev_eur_mwh)
    q = q.dropna(subset=["price"])

    m = q.contract.str.extract(r"Q(\d)-(\d\d)")
    qtr, yr = m[0].astype(int), 2000 + m[1].astype(int)
    q["qstart"] = pd.to_datetime(dict(year=yr, month=(qtr - 1) * 3 + 1, day=1))
    q = q[q.qstart > q.trade_date]  # a genuine forward: delivery not yet started

    front = q.loc[q.groupby("trade_date").qstart.idxmin()]
    front = front.set_index("trade_date").price.rename("pf")
    front.index = front.index.to_period("M")
    return front.groupby(level=0).mean()


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    hy = hydro_units_with_basin()
    units = set(hy.dropna(subset=["basin"]).unit)

    exp = contract_exposure(units)
    d = offer_panel(units)
    d["exposure"] = d.unit.map(exp)
    d = d.dropna(subset=["exposure"])
    inten = gas_intensity()
    d["intensity"] = d.month.map(inten)
    d = d.dropna(subset=["intensity"])
    d["treat"] = d.exposure * d.intensity

    pf = front_quarter_forward()
    d["pf"] = d.month.map(pf)
    d = d.dropna(subset=["pf"])
    d["fwd_level"] = d.exposure * d.pf
    # The level control is collinear with treat: intensity is built from the
    # current gas price, and the forward price tracked the same 2021-22 crisis
    # (corr(intensity, pf) = 0.88 at the month level). A control this collinear
    # cannot cleanly test the omitted-variable story -- it just removes power.
    # The spread strips the common trend, isolating the forward-LOOKING signal
    # (corr with intensity drops to 0.22) -- the better-identified test.
    d["spread"] = d.pf - d.pbar
    d["fwd_spread"] = d.exposure * d.spread

    print("SAMPLE\n")
    print(f"  {d.unit.nunique()} units (basin-identified subset of Design 4's "
          f"exposure sample), {len(d):,} unit-months, "
          f"{d.month.min()} to {d.month.max()}")
    print(f"  exposure (1 - pre-levy contract share): mean "
          f"{d.groupby('unit').exposure.first().mean():.2f}")
    print(f"  front-quarter forward price: mean {pf.mean():.1f}, "
          f"range {pf.min():.1f}-{pf.max():.1f} EUR/MWh")
    print(f"  corr(treat, exposure x pf level): "
          f"{d[['treat','fwd_level']].corr().iloc[0,1]:.2f}  -- too collinear to "
          f"trust as a test")
    print(f"  corr(treat, exposure x [pf - spot]): "
          f"{d[['treat','fwd_spread']].corr().iloc[0,1]:.2f}  -- the control used "
          f"below\n")

    d["orth_treat"] = orthogonalise(d, "treat", "fwd_spread", "unit", "month")

    print("BASELINE vs. CONTROLLED (exposure x forward price partialled out)\n")
    print("unit + month FE;  SE clustered on unit;  levels = EUR/MWh of offer "
          "per EUR/MWh of levy intensity\n")
    print(f"{'outcome':<32}{'spec':<12}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}")

    for lbl, col in (("median submitted offer", "offer"),
                      ("marginal accepted offer", "marginal_accepted")):
        x = d.dropna(subset=[col]).copy()
        b0, se0, t0, n0, k0 = twfe(x, col, "treat", "unit", "month")
        b1, se1, t1, n1, k1 = twfe(x, col, "orth_treat", "unit", "month")
        print(f"{lbl:<32}{'baseline':<12}{b0:>10.4f}{se0:>9.4f}{t0:>7.2f}{n0:>8,}")
        print(f"{'':<32}{'controlled':<12}{b1:>10.4f}{se1:>9.4f}{t1:>7.2f}{n1:>8,}")
        row0, row1 = [], []
        for q in (0.99, 0.95, 0.90):
            xt = x[x[col] <= x[col].quantile(q)]
            b0q, *_ = twfe(xt, col, "treat", "unit", "month")
            b1q, *_ = twfe(xt, col, "orth_treat", "unit", "month")
            row0.append(f"p{int(q * 100)} {b0q:+.3f}")
            row1.append(f"p{int(q * 100)} {b1q:+.3f}")
        print(f"{'':<32}{'  baseline trim':<12}{'   '.join(row0)}")
        print(f"{'':<32}{'  ctrl trim':<12}{'   '.join(row1)}")
        print()

    d["y"] = np.log(d.ratio.clip(lower=1e-6))
    b0, se0, t0, n0, k0 = twfe(d, "y", "treat", "unit", "month")
    b1, se1, t1, n1, k1 = twfe(d, "y", "orth_treat", "unit", "month")
    print(f"{'log(offer/market)':<32}{'baseline':<12}{b0:>10.5f}{se0:>9.5f}{t0:>7.2f}{n0:>8,}")
    print(f"{'':<32}{'controlled':<12}{b1:>10.5f}{se1:>9.5f}{t1:>7.2f}{n1:>8,}\n")

    # Placebo: real intensity path 36 months earlier, pre-levy sample only.
    fake = inten[(inten.index >= LEVY_START_M) &
                 (inten.index <= pd.Period("2023-12"))].copy()
    fake.index = fake.index - 36
    pre = d[d.month < LEVY_START_M].copy()
    pre["treat"] = pre.exposure * pre.month.map(fake).fillna(0.0)
    pre["orth_treat"] = orthogonalise(pre, "treat", "fwd_spread", "unit", "month")
    print("PLACEBO -- real intensity path, -36 months, pre-levy sample only\n")
    for lbl, col in (("baseline", "treat"), ("controlled", "orth_treat")):
        x = pre.dropna(subset=["ratio"]).copy()
        if x[col].abs().sum() == 0:
            continue
        x["y"] = np.log(x.ratio.clip(lower=1e-6))
        b, se, t, n, k = twfe(x, "y", col, "unit", "month")
        print(f"{'placebo -36m — ' + lbl:<32}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")

    print("\nRead: this tests whether Design 4's LEVELS sign instability was an\n"
          "omitted-variable problem the forward price can fix. If controlled\n"
          "trims agree in sign where baseline trims didn't, that supports the\n"
          "expected-price-channel diagnosis. If controlled is just as unstable,\n"
          "the instability has some other source (Stage B already ruled out\n"
          "reservoir fill level) -- consistent with 'structural or nothing'.")

    if args.save:
        p = ROOT / "outputs" / "tables" / "levy_contract_exposure_forward_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
