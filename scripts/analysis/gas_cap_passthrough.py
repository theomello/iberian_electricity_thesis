#!/usr/bin/env python3
"""Did capped gas plants pass the subsidy through, or keep part of it?

    .venv/bin/python scripts/analysis/gas_cap_passthrough.py

THE TEST

From 15 June 2022 the Iberian mechanism capped the gas price a plant may use in
its bid and compensated it for the difference against the market price. A
covered plant's fuel cost therefore fell by a **known** amount:

    delta_MC_t  =  (market gas_t  -  capped gas_t) / efficiency

If the plant passes the cut through completely, its offer falls by exactly that.
If it falls by less, the firm retained part of the subsidy -- which is a conduct
finding, measured per unit.

    passthrough  =  observed fall in offer  /  predicted fall in marginal cost

CARBON CANCELS, WHICH IS WHY IT IS NOT FETCHED HERE

Marginal cost is fuel plus carbon plus variable O&M. The cap applies **only to
gas**: a plant's carbon cost is identical on 14 and 16 June 2022. So carbon
appears on both sides of the difference and drops out. A carbon price series is
needed to state a markup in absolute euros -- it is not needed to test
passthrough, which is the question. The same is true of variable O&M.

EFFICIENCY IS ESTIMATED FROM THE PLANT'S OWN PRE-CAP BIDDING

Rather than assigning engineering heat rates from a table, regress each unit's
offer on the market gas price using **pre-cap months only**:

    offer_it  =  a_i  +  b_i * gas_t  +  e_it

`b_i` is the implied heat rate, 1/efficiency: how many euros the offer moves per
euro of gas. `a_i` absorbs carbon and O&M, which is exactly the part that
cancels. This disciplines the cost model with the plant's own revealed
behaviour, and it means a plant that never responded to gas prices before the
cap is visible as such rather than being assigned a textbook efficiency.

A plausible CCGT has efficiency 0.40-0.60, so b_i should land near 1.7-2.5.
Units outside that range are reported but excluded from the headline: a slope of
0.2 or 8 is not a heat rate, it is a unit whose bidding is driven by something
else.

THE CAP SCHEDULE

Article 3 of RDL 10/2022 sets the reference gas price at 40 EUR/MWh for the
first six months and then rising by 5 EUR/MWh per month, reaching 65 by December
2023. Encoded below; the mechanism ran from 15 June 2022.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

CAP_START = pd.Period("2022-06")
CAP_END = pd.Period("2023-12")


def cap_path() -> pd.Series:
    """Reference gas price in EUR/MWh, by month, per Article 3 of RDL 10/2022."""
    sched = {}
    for m in pd.period_range("2022-06", "2022-12", freq="M"):
        sched[m] = 40.0
    step = 45.0
    for m in pd.period_range("2023-01", "2023-12", freq="M"):
        sched[m] = min(step, 65.0)
        step += 5.0
    return pd.Series(sched).rename("cap")


def gas_monthly() -> pd.Series:
    mg = pq.read_table(DATA / "mibgas/mibgas_prices.parquet").to_pandas()
    mg = mg[mg["product"].eq("GDAES_D+1") & mg.area.eq("ES")]
    mg["month"] = pd.to_datetime(mg.trading_day).dt.to_period("M")
    return mg.groupby("month").price_eur_mwh.mean().rename("gas")


def ccgt_units() -> set[str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    lab = ul.dropna(subset=["technology"]).drop_duplicates("unit", keep="last")
    return {u for u, t in zip(lab.unit, lab.technology)
            if "Ciclo Combinado" in str(t)}


def offers(units: set[str]) -> pd.DataFrame:
    def wmed(v, w):
        o = np.argsort(v)
        v, w = np.asarray(v)[o], np.asarray(w)[o]
        c = np.cumsum(w)
        return float(v[np.searchsorted(c, c[-1] / 2.0)]) if c[-1] > 0 else np.nan

    out = []
    for f in sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet")):
        ym = f.stem.split("_")[1]
        if not ("202101" <= ym <= "202312"):
            continue
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O") & (pc.field("side") == "V"),
            columns=["date", "unit", "price_eur_mwh", "power_mw"]).to_pandas()
        t = t[t.unit.isin(units) & (t.price_eur_mwh > 0) & (t.price_eur_mwh < 3000)]
        if t.empty:
            continue
        m = pd.to_datetime(t.date).dt.to_period("M")
        g = (t.groupby([m, "unit"])
               .apply(lambda x: wmed(x.price_eur_mwh.values, x.power_mw.values),
                      include_groups=False)
               .rename("offer").reset_index())
        g.columns = ["month", "unit", "offer"]
        out.append(g)
    return pd.concat(out, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    gas, cap = gas_monthly(), cap_path()
    units = ccgt_units()
    d = offers(units)
    d["gas"] = d.month.map(gas)
    d = d.dropna(subset=["gas", "offer"])

    pre = d[d.month < CAP_START]
    post = d[(d.month >= CAP_START) & (d.month <= CAP_END)]

    # Implied heat rate per unit, from pre-cap bidding only.
    hr = {}
    for u, x in pre.groupby("unit"):
        if len(x) < 8 or x.gas.std() == 0:
            continue
        b, a = np.polyfit(x.gas.values, x.offer.values, 1)
        hr[u] = (b, a, len(x))
    h = pd.DataFrame(hr, index=["slope", "intercept", "n"]).T
    ok = h[(h.slope > 1.5) & (h.slope < 3.0)]
    print(f"IMPLIED HEAT RATE from pre-cap bidding ({len(h)} units with >=8 months)\n")
    print(f"  slope in a plausible CCGT range (1.5-3.0): {len(ok)} units")
    print(f"  median slope {h.slope.median():.2f}  ->  implied efficiency "
          f"{1/h.slope.median():.0%}")
    print(f"  units outside the range: {len(h) - len(ok)} "
          f"(reported, excluded from the headline)\n")

    # Predicted vs observed fall, per unit-month, over the capped window.
    p = post[post.unit.isin(ok.index)].copy()
    p["cap"] = p.month.map(cap)
    p = p.dropna(subset=["cap"])
    p["slope"] = p.unit.map(ok.slope)
    p["intercept"] = p.unit.map(ok.intercept)
    # What the plant would have offered at the market gas price, on its own
    # pre-cap cost relationship.
    p["counterfactual"] = p.intercept + p.slope * p.gas
    p["predicted"] = p.intercept + p.slope * p.cap
    p["dMC"] = p.counterfactual - p.predicted           # the subsidy, EUR/MWh
    p["dOffer"] = p.counterfactual - p.offer            # what actually happened
    p = p[p.dMC > 5]                                    # cap must actually bind

    print(f"PASS-THROUGH over {p.month.min()} to {p.month.max()}, "
          f"{p.unit.nunique()} units, {len(p):,} unit-months\n")
    print(f"{'month':<9}{'gas':>8}{'cap':>7}{'predicted fall':>16}"
          f"{'observed fall':>15}{'pass-through':>14}")
    for m, x in p.groupby("month"):
        pt = x.dOffer.sum() / x.dMC.sum()
        print(f"{str(m):<9}{x.gas.iloc[0]:>8.1f}{x.cap.iloc[0]:>7.1f}"
              f"{x.dMC.mean():>16.1f}{x.dOffer.mean():>15.1f}{pt:>14.2f}")
    # A ratio of means explodes once the cap stops binding: by February 2023 the
    # market price is 51.9 and the cap 50.0, so the predicted fall is 5.2 EUR and
    # ordinary noise in offers produces a "pass-through" of -42. Regress instead
    # -- the slope is the same object, estimated without dividing by a number
    # approaching zero, and it comes with a standard error.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from clawback_intensity_did import twfe  # noqa: E402

    print(f"\nPASS-THROUGH AS A REGRESSION SLOPE")
    print(f"  dOffer_it = beta * dMC_it + unit FE + month FE\n")
    print(f"{'sample':<34}{'beta':>9}{'se':>8}{'t':>7}{'obs':>7}{'units':>7}")
    for lbl, x in (("all capped months", p),
                   ("months where the cap bound >20 EUR", p[p.dMC > 20]),
                   ("2022 only (cap binding hard)",
                    p[p.month <= pd.Period("2022-12")])):
        if len(x) < 30:
            continue
        b, se, t, n, k = twfe(x, "dOffer", "dMC", "unit", "month")
        print(f"{lbl:<34}{b:>9.3f}{se:>8.3f}{t:>7.2f}{n:>7,}{k:>7}")
        lo, hi = b - 1.96 * se, b + 1.96 * se
        print(f"      95% CI [{lo:5.2f}, {hi:5.2f}]   full pass-through "
              f"{'inside' if lo <= 1 <= hi else 'OUTSIDE'}")

    if args.save:
        o = ROOT / "outputs" / "tables" / "gas_cap_passthrough.parquet"
        o.parent.mkdir(parents=True, exist_ok=True)
        p.assign(month=p.month.astype(str)).to_parquet(o, index=False)
        print(f"\nwrote {o}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
