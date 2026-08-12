#!/usr/bin/env python3
"""Firm shares and implied Lerner index at market-period resolution.

    .venv/bin/python scripts/analysis/firm_shares_hourly.py            # all tiers
    .venv/bin/python scripts/analysis/firm_shares_hourly.py --tier confirmed
    .venv/bin/python scripts/analysis/firm_shares_hourly.py --save

Replaces CNMC's annual, MIBEL-wide shares with shares computed per market
period from the cleared bid data, so that

    L_it = s_it / eta_t

varies hour by hour on both sides instead of pairing a per-period elasticity
with a share held fixed for a year.

WHAT IS AND IS NOT MEASURED

`s_it` is firm i's share of **total** cleared sell volume in period t, with the
unmapped units left in the denominator. Shares are therefore understated by
construction, and so is every Lerner index below -- the same direction as the
market-wide `eta` bound. Normalising to mapped volume only would flatter the
result and is not done.

THE TIER SPLIT MATTERS, so run it both ways

`--tier confirmed` uses only units whose agent is established by the data:
ESIOS exact match, or an ESIOS agent code appearing inside the cab plant name.
The default `all` additionally uses the inferred prefix assignments
(EDP, IBE, IGN, GGN, NXV, the Portuguese hydro cascades, GED), each of which
rests on a mnemonic corroborated by the CNMC share gap rather than on direct
evidence. Coverage of generation volume is 45% versus 74%.

If a conclusion holds under both tiers, the inference does not matter. If it
does not, the conclusion depends on an assumption that no public Spanish source
can currently verify, and it must be reported that way.

COVERAGE DRIFTS UPWARD -- DO NOT READ TIME TRENDS OFF THESE SHARES

Mapped share of cleared sell volume rises from 49.0% in 2018 to 70.1% in 2026.
The cause is that ESIOS is a snapshot of today's registry, so units that traded
early in the window and have since exited are simply absent. Because unmapped
volume stays in the denominator, a firm's measured share rises over time even
if nothing about the firm changed.

Consequences, and they are strict:

* **Within-year comparisons are valid.** Contrasting high-VRE against low-VRE
  hours inside one year holds coverage fixed, so the gradient is real.
* **Across-year trends in these shares are contaminated** and must not be
  reported as growth in market share or in the Lerner index. For trends use the
  CNMC-based estimates in markup_from_shares.py, which do not depend on this
  mapping at all.

VALIDATION

Annual means of the hourly shares are printed against CNMC's published figures.
That comparison is the check on whether the mapping is good enough to use --
not a target to fit. The prefix assignments were fixed before this ran.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BIDS = DATA / "omie" / "bids" / "parquet"
ETA = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"
FIRMS = ["IBERDROLA", "ENDESA", "EDP", "NATURGY", "AXPO", "ACCIONA", "REPSOL"]


def firm_period_volume(unit_firm: dict[str, str]) -> pd.DataFrame:
    """Cleared sell volume by (date, period, firm), whole archive."""
    frames = []
    files = sorted(BIDS.glob("bids_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "power_mw"]).to_pandas()
        t["firm"] = t.unit.map(unit_firm)
        tot = t.groupby(["date", "period"]).power_mw.sum().rename("total_mw")
        g = (t[t.firm.notna()].groupby(["date", "period", "firm"]).power_mw.sum()
             .rename("firm_mw").reset_index().merge(tot, on=["date", "period"]))
        frames.append(g)
        print(f"  [{i:3d}/{len(files)}] {f.stem}", end="\r", flush=True)
    print(" " * 40, end="\r")
    out = pd.concat(frames, ignore_index=True)
    out["share"] = out.firm_mw / out.total_mw
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["all", "confirmed"], default="all")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    reg = (DATA / "omie" / "registry" /
           ("unit_agents.parquet" if args.tier == "all" else "unit_agents_confirmed.parquet"))
    if not reg.exists():
        print(f"missing {reg.name} -- run build_unit_agents.py --tier {args.tier}",
              file=sys.stderr)
        return 1
    ua = pq.read_table(reg).to_pandas()
    unit_firm = dict(zip(ua.loc[ua.firm.notna(), "unit"], ua.loc[ua.firm.notna(), "firm"]))
    print(f"tier={args.tier}: {len(unit_firm):,} units carry a firm\n")

    fv = firm_period_volume(unit_firm)
    eta = pq.read_table(ETA, columns=["date", "period", "eta_h5", "p_star",
                                      "vre_share", "year"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)
    fv["date"] = pd.to_datetime(fv.date)
    m = fv.merge(eta, on=["date", "period"], how="inner")
    m["lerner"] = m.share / m.eta_h5

    print(f"{len(m):,} firm-period observations over "
          f"{m[['date','period']].drop_duplicates().shape[0]:,} periods\n")

    print("=" * 72)
    print("VALIDATION: annual mean of hourly shares vs CNMC published (%)")
    print("=" * 72)
    cnmc = pq.read_table(DATA / "cnmc" / "cnmc_generation_shares.parquet").to_pandas().set_index("year")
    ann = m.pivot_table(index="year", columns="firm", values="share", aggfunc="mean") * 100
    yrs = [y for y in ann.index if y in cnmc.index]
    comp = pd.concat({"ours": ann.loc[yrs, [f for f in FIRMS if f in ann.columns]],
                      "CNMC": cnmc.loc[yrs, [f for f in FIRMS if f in cnmc.columns]]}, axis=1)
    print(comp.round(1).to_string())

    print("\n" + "=" * 72)
    print("IMPLIED LERNER from hourly shares, median by year (%)")
    print("=" * 72)
    lt = m.pivot_table(index="year", columns="firm", values="lerner", aggfunc="median") * 100
    print(lt[[f for f in FIRMS if f in lt.columns]].round(1).to_string())

    print("\n" + "=" * 72)
    print("BY VRE TERCILE, median Lerner (%) -- the within-year gradient")
    print("=" * 72)
    m["vre_t"] = m.groupby("year").vre_share.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    for f in ["IBERDROLA", "ENDESA", "EDP"]:
        if f not in set(m.firm):
            continue
        p = m[m.firm == f].pivot_table(index="year", columns="vre_t",
                                       values="lerner", aggfunc="median", observed=True) * 100
        p["high/low"] = p["high"] / p["low"]
        print(f"\n  {f}")
        print(p.round(2).to_string())

    print("\n  Mapped share of cleared sell volume by year (coverage drift --")
    print("  rising coverage inflates later-year shares; see the docstring):")
    cov = (m.groupby(["year", "date", "period"])
             .agg(mapped=("firm_mw", "sum"), tot=("total_mw", "first")).reset_index()
             .groupby("year").apply(lambda g: g.mapped.sum() / g.tot.sum(),
                                    include_groups=False))
    print("   " + "  ".join(f"{y}:{v:.0%}" for y, v in cov.items()))

    print("\n  Hourly share dispersion (a firm's share is NOT constant within a year):")
    d = m.groupby(["year", "firm"]).share.agg(["mean", "std"]).reset_index()
    d["cv"] = d["std"] / d["mean"]
    print(d[d.firm.isin(FIRMS)].pivot_table(index="year", columns="firm",
                                            values="cv").round(2).to_string())

    if args.save:
        out = ROOT / "outputs" / "tables" / f"firm_shares_hourly_{args.tier}.parquet"
        m.to_parquet(out, index=False)
        print(f"\nwrote {out.relative_to(ROOT)}  ({len(m):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
