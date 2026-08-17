#!/usr/bin/env python3
"""The 2021 levy, identified from differential contract exposure within Spain.

    .venv/bin/python scripts/analysis/levy_contract_exposure.py

WHY A THIRD DESIGN

The Spain-versus-Portugal comparison is contaminated. Three specifications --
the monthly offer level, the intertemporal spread, and the within-month capture
rate -- all show the same thing: any regressor shaped like the gas-price path
predicts the ES-PT hydro gap in years when no levy existed. The two fleets differ
in mix, hydrology and capture rate and simply respond differently to gas. The
level test's placebo appeared to pass only because that outcome is seven times
noisier; a sharper outcome exposed the same contamination at t = 2.21.

This design removes Portugal entirely.

THE IDENTIFYING VARIATION

RDL 23/2021 exempted energy sold under **fixed-price forward contracts** from the
levy. So two Spanish hydro plants facing the same gas price faced very different
effective levies, according to how much of their output was already contracted:

    effective intensity_it  =  (1 - contracted share_i) * intensity_t

Exposure is measured from PDBF role-4 bilateral volume **strictly before
September 2021**, so it is predetermined: it cannot be a response to the policy.
The variation is strong and close to bimodal -- of 23 Spanish hydro storage units
with pre-levy schedule volume, 12 sit at zero contract cover and 9 above 50%,
with a maximum of 92.5%.

Identification then comes from *within Spain, within hydro*: unit and month fixed
effects absorb the level of each plant and every market-wide shock, including the
gas price itself. What identifies beta is that a heavily contracted plant and an
unhedged one experienced different levies in the same month.

`beta > 0` means the more exposed plants raised their offers by more when the
levy bit harder -- the sign a real cost shock predicts.

TWO WEAKNESSES, STATED UP FRONT

1. **Only physical contracts are observable.** A financially settled hedge is
   equally exempt and invisible in PDBF, so exposure is measured with error and
   beta is biased toward zero. This is attenuation, not confounding: it makes a
   true effect harder to find, not a false one easier.
2. **Contract share is a firm's choice.** Using the pre-levy average removes any
   response to the policy, but not the possibility that plants which contract
   heavily differ systematically in ways that also drive bidding. The placebo
   below is the check: if exposed and unexposed plants simply respond differently
   to gas prices, the placebo will find an effect where there is no policy.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawback_intensity_did import gas_intensity, twfe  # noqa: E402

LEVY_START_M = pd.Period("2021-09")


def spanish_hydro() -> set[str]:
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet").to_pandas()
    return {u for u, c, t in zip(ua.unit, ua.country, ua.tech)
            if c == "ES" and t == "hydro_ugh"}


def contract_exposure(units: set[str]) -> pd.Series:
    """1 - physical contract share, from PDBF role 4, strictly pre-levy."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/pdbf/parquet/pdbf_*.parquet"))):
        ym = Path(f).stem.split("_")[1]
        if ym >= "202109":
            continue
        t = pq.read_table(f, columns=["unit", "schedule_mw", "resolution_min",
                                      "role_code"]).to_pandas()
        t = t[t.unit.isin(units)]
        if t.empty:
            continue
        t["e"] = t.schedule_mw * t.resolution_min / 60.0
        s = t[t.e > 0]
        frames.append(pd.DataFrame({
            "tot": s.groupby("unit").e.sum(),
            "bil": s[s.role_code == "4"].groupby("unit").e.sum(),
        }))
    d = pd.concat(frames).groupby(level=0).sum().fillna({"bil": 0.0})
    d = d[d.tot > 1e4]
    return (1.0 - d.bil / d.tot).rename("exposure")


def panel(units: set[str]) -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)
    px["month"] = px.date.dt.to_period("M")
    pbar = px.groupby("month").price_es.mean().rename("pbar")

    def wmed(v, w):
        o = np.argsort(v)
        v, w = np.asarray(v)[o], np.asarray(w)[o]
        c = np.cumsum(w)
        return float(v[np.searchsorted(c, c[-1] / 2.0)]) if c[-1] > 0 else np.nan

    out = []
    for f in sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet")):
        # Offers give the bid margin; cleared volume gives the timing margin.
        t = ds.dataset(f).to_table(
            filter=(pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh", "power_mw",
                     "resolution_min", "status"]).to_pandas()
        t = t[t.unit.isin(units)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        t = t.merge(px[["date", "period", "price_es"]], on=["date", "period"],
                    how="inner")
        t["month"] = t.date.dt.to_period("M")

        off = t[(t.status == "O") & (t.price_eur_mwh > 0) & (t.price_eur_mwh < 3000)]
        a = (off.groupby(["month", "unit"])
                .apply(lambda x: wmed(x.price_eur_mwh.values, x.power_mw.values),
                       include_groups=False)
                .rename("offer").reset_index())

        # The MARGINAL ACCEPTED offer: the highest-priced step of this unit that
        # actually cleared. In a uniform-price auction a unit's cleared steps are
        # those priced at or below the clearing price, so this is the price at
        # which the plant revealed itself willing to run -- its opportunity cost,
        # which for a reservoir is the water value.
        #
        # This is the right outcome and the median submitted offer is not. A
        # plant that does not want to generate submits a deliberately unclearable
        # bid; that price expresses an intention *not* to run and reflects no
        # marginal cost at all. Pooling the two is what made the levels estimate
        # swing from 0.13 to 1.82 depending on where the sample was trimmed.
        #
        # It is censored above by the clearing price: a unit whose water value
        # exceeds the market price simply does not appear that period. That is
        # selection, and it biases toward finding no effect when the levy pushes
        # plants out of the market entirely.
        acc = t[(t.status == "C") & (t.price_eur_mwh > 0)]
        mrg = (acc.groupby(["month", "unit", "date", "period"]).price_eur_mwh.max()
                  .groupby(level=["month", "unit"]).mean()
                  .rename("marginal_accepted").reset_index())
        a = a.merge(mrg, on=["month", "unit"], how="outer")

        cl = t[t.status == "C"].copy()
        cl["q"] = cl.power_mw * cl.resolution_min / 60.0
        cl["qp"] = cl.q * cl.price_es
        b = cl.groupby(["month", "unit"], as_index=False)[["q", "qp"]].sum()
        out.append(a.merge(b, on=["month", "unit"], how="outer"))

    d = pd.concat(out, ignore_index=True)
    d = d.groupby(["month", "unit"], as_index=False).agg(
        offer=("offer", "mean"),
        marginal_accepted=("marginal_accepted", "mean"),
        q=("q", "sum"), qp=("qp", "sum"))
    d = d.merge(pbar, left_on="month", right_index=True)
    d["ratio"] = d.offer / d.pbar
    d["capture"] = np.where(d.q > 0, d.qp / (d.q * d.pbar), np.nan)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    units = spanish_hydro()
    exp = contract_exposure(units)
    d = panel(units)
    d["exposure"] = d.unit.map(exp)
    d = d.dropna(subset=["exposure"])
    inten = gas_intensity()
    d["intensity"] = d.month.map(inten)
    d = d.dropna(subset=["intensity"])
    d["treat"] = d.exposure * d.intensity

    print("SPANISH HYDRO STORAGE ONLY — no Portugal, no cross-country comparison\n")
    print(f"  units {d.unit.nunique()},  unit-months {len(d):,},  "
          f"{d.month.min()} to {d.month.max()}")
    print(f"  exposure (1 - pre-levy contract share): mean {exp.mean():.2f}, "
          f"{(exp > 0.99).sum()} fully exposed, {(exp < 0.5).sum()} more than half hedged\n")

    print("y = log(offer / market price);  unit + month FE;  SE clustered on unit\n")
    print(f"{'specification':<38}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    for lbl, col in (("offer level", "ratio"), ("capture rate", "capture")):
        x = d.dropna(subset=[col]).copy()
        x["y"] = np.log(x[col].clip(lower=1e-6))
        b, se, t, n, k = twfe(x, "y", "treat", "unit", "month")
        print(f"{'exposure x intensity — ' + lbl:<38}{b:>10.5f}{se:>9.5f}"
              f"{t:>7.2f}{n:>8,}{k:>7}")

    # ---- calibration -------------------------------------------------------
    # The levy is a per-MWh cost, so full pass-through means the offer rises by
    # exactly the levy. Run in LEVELS and beta is the pass-through rate itself:
    # 1.0 complete, below 1 partial, above 1 over-shifting. The log
    # specification above cannot be read that way -- its coefficient has to be
    # multiplied by the offer level to mean anything, which is why it looked
    # implausibly large.
    print(f"\nPASS-THROUGH, in levels (EUR/MWh of offer per EUR/MWh of levy)\n")
    print(f"{'outcome':<38}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    for lbl, col in (("median submitted offer", "offer"),
                     ("MARGINAL ACCEPTED offer", "marginal_accepted")):
        lv = d.dropna(subset=[col]).copy()
        bl, sel, tl, nl, kl = twfe(lv, col, "treat", "unit", "month")
        lo, hi = bl - 1.96 * sel, bl + 1.96 * sel
        print(f"{lbl:<38}{bl:>10.4f}{sel:>9.4f}{tl:>7.2f}{nl:>8,}{kl:>7}")
        print(f"      95% CI [{lo:6.3f}, {hi:6.3f}]   full pass-through "
              f"{'inside' if lo <= 1 <= hi else 'OUTSIDE'}, zero "
              f"{'inside' if lo <= 0 <= hi else 'OUTSIDE'}")
        # robustness to sample choice is what broke the previous outcome
        row = []
        for q in (0.99, 0.95, 0.90):
            x = lv[lv[col] <= lv[col].quantile(q)]
            b2, _, _, _, _ = twfe(x, col, "treat", "unit", "month")
            row.append(f"p{int(q*100)} {b2:.3f}")
        print(f"      trimmed: {'   '.join(row)}")
    bl = 0.0

    # Cross-check: the log coefficient should equal the levels one divided by
    # the offer level it is evaluated at. If these disagree the two are not
    # measuring the same thing.
    win = d[(d.month >= LEVY_START_M) & (d.month <= pd.Period("2023-12"))]
    mo = win.offer.median()
    x = d.dropna(subset=["ratio"]).copy()
    x["y"] = np.log(x.ratio.clip(lower=1e-6))
    blog, *_ = twfe(x, "y", "treat", "unit", "month")
    print(f"\n    median offer in the levy window: {mo:,.1f} EUR/MWh")
    print(f"    log coefficient {blog:.5f} x median offer = {blog * mo:.3f}"
          f"   vs levels beta {bl:.3f}")

    # Placebo: real intensity path, 36 months earlier, pre-levy sample only.
    fake = inten[(inten.index >= LEVY_START_M) &
                 (inten.index <= pd.Period("2023-12"))].copy()
    fake.index = fake.index - 36
    pre = d[d.month < LEVY_START_M].copy()
    pre["treat"] = pre.exposure * pre.month.map(fake).fillna(0.0)
    for lbl, col in (("offer level", "ratio"), ("capture rate", "capture")):
        x = pre.dropna(subset=[col]).copy()
        if x.treat.abs().sum() == 0:
            continue
        x["y"] = np.log(x[col].clip(lower=1e-6))
        b, se, t, n, k = twfe(x, "y", "treat", "unit", "month")
        print(f"{'placebo -36m — ' + lbl:<38}{b:>10.5f}{se:>9.5f}"
              f"{t:>7.2f}{n:>8,}{k:>7}")

    if args.save:
        p = ROOT / "outputs" / "tables" / "levy_contract_exposure_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
