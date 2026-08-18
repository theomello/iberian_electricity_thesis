#!/usr/bin/env python3
"""Differential renewable exposure, with an outcome that can carry it.

    .venv/bin/python scripts/analysis/exposure_capacity_quantile.py

WHAT THIS COMBINES

Two halves that have each been established separately and never together.

From `af5812a`, the treatment: a firm's own pre-2021 wind-and-solar share
interacted with the market renewable share,

    treat_it  =  vre_exposure_i  x  vre_share_t

which varies ACROSS firms within an hour and therefore permits full date-by-
period fixed effects. Those absorb the renewable share itself, demand, the
clearing price, fuel costs and every other market-wide shock, known or unknown.
It is the only treatment tried here with cross-sectional variation.

From `99226e9`, the outcome: the price at which a unit has offered a fixed
quantile of its OWN nameplate capacity. It reproduces the merit order unprompted,
holds its sign across quantiles and winsorising where bid steepness reversed
outright, and survives two-way clustering at t = 3.7-4.3.

WHY THE PAIRING FIXES af5812a's STATED THREAT

That commit named its own weakness: the markup is `(q - theta)/|RD'|`, so it
scales with the firm's own output, and a wind-heavy firm mechanically produces
more in a windy hour. The interaction then predicts the outcome with no conduct
involved, and controlling for `q` is a bad control because `q` is an outcome of
the treatment.

This outcome contains no `q`. It is the price a dispatchable plant names for a
fixed physical slice of its own capacity -- a decision, not an accounting
identity, and the wind belongs to other units of the same firm. The mechanical
channel is removed by construction rather than bounded by a bad control.

WHY THE PAIRING FIXES 99226e9's STATED FAILURE

That commit died on date fixed effects: with market-wide renewable share as the
treatment, absorbing daily market-wide shocks collapsed the estimate to zero.
Date effects cannot do that here, because they do not absorb an interaction that
varies across firms within a period. The earlier failure is the reason to run
this, not an argument against it.

SAMPLE

Dispatchable technologies only -- combined cycle, hydro, cascades, pumped
storage, thermal, cogeneration, nuclear. Wind and solar offer at zero to
guarantee dispatch; market power is not defined for them, and on the full
supply-side sample the measure flips sign.

Note the asymmetry this creates, and it is the design's real subtlety: the
outcome is measured on a firm's DISPATCHABLE plant while its exposure is
measured on its whole portfolio. That is the question -- does a firm whose
portfolio is renewable-heavy bid its gas and hydro differently in a windy hour
than a thermal-heavy firm does?
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts/analysis"))

from capacity_quantile_offer import DISPATCHABLE, demean, ols, sandwich  # noqa: E402
from renewable_exposure_did import maps, vre_exposure  # noqa: E402

CACHE = ROOT / "outputs/tables/capacity_quantile_offer.parquet"
QUANTILES = ("p25", "p50", "p75")


def exposure_parent(min_gwh: float) -> tuple[pd.Series, dict]:
    """Renewable exposure at the PARENT FIRM, not the market agent.

    `agent_owner` in omie_unit_lists is the agent that submits the offer.
    CLAUDE.md is explicit that this is not the firm: IBEG, IGNU and IBGT are
    three agents and one Iberdrola. If a group's wind sits in one agent and its
    gas in another, the gas-owning agent measures at zero exposure and the
    treatment is attenuated toward zero -- which is what the agent-level run
    returned. `unit_agents.firm` is the roll-up to parent.

    The cost is coverage: the parent mapping reaches 81.5% of PDBF volume
    against 100% for the agent mapping, so a parent's exposure is computed on
    the attributable part of its portfolio only. Reported, not hidden.

    `min_gwh` drops firms too small for the ratio to mean anything -- at the
    agent level the top of the exposure distribution was retailers with a
    median size of 7.4 GWh whose entire generation was one solar farm.
    """
    ua = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet")
    ua = ua.dropna(subset=["firm"])
    parent = dict(zip(ua.unit, ua.firm))
    _, tech, _ = maps()

    frames = []
    for ym in ["201804", "201810", "201904", "201910", "202004", "202010"]:
        f = ROOT / "data/omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
        if not f.exists():
            continue
        t = pd.read_parquet(f, columns=["unit", "schedule_mw", "resolution_min"])
        t = t[t.schedule_mw > 0].copy()
        t["e"] = t.schedule_mw * t.resolution_min / 60.0
        t["firm"] = t.unit.map(parent)
        t["tech"] = t.unit.map(tech).astype(str)
        t["vre"] = t.tech.str.contains("Eólica|Solar", case=False, regex=True)
        frames.append(t.dropna(subset=["firm"]).groupby("firm").apply(
            lambda x: pd.Series({"tot": x.e.sum(), "v": x[x.vre].e.sum()}),
            include_groups=False))
    d = pd.concat(frames).groupby(level=0).sum()
    kept = d[d.tot > min_gwh * 1e3]
    return (kept.v / kept.tot).rename("exposure"), parent


def build(parent: bool, min_gwh: float) -> pd.DataFrame:
    d = pd.read_parquet(CACHE)
    d = d[d.tech.isin(DISPATCHABLE)].copy()
    if parent:
        exp, omap = exposure_parent(min_gwh)
    else:
        owner, tech, _ = maps()
        exp, omap = vre_exposure(owner, tech), owner

    # The firm mapping must be the SAME one the exposure was computed on,
    # otherwise a unit is attributed to one firm and the treatment to another.
    d["firm"] = d.unit.map(omap)
    d["exposure"] = d.firm.map(exp)
    d["date"] = pd.to_datetime(d.date)
    d["pid"] = pd.factorize(
        d.date.astype("int64").astype(str) + "_" + d.period.astype(str))[0]
    d["treat"] = d.exposure * d.vre_share
    for z in ("wind", "wind3", "rad"):
        d[f"z_{z}"] = d.exposure * d[z]
    return d


def fit(s: pd.DataFrame, col: str, winsor: float) -> dict | None:
    s = s.dropna(subset=[col, "treat", "z_wind", "z_rad"]).copy()
    if winsor > 0:
        lo, hi = s[col].quantile([winsor, 1 - winsor])
        s = s[(s[col] >= lo) & (s[col] <= hi)]
    if len(s) < 1000 or s.firm.nunique() < 5:
        return None
    ui = pd.factorize(s.unit)[0]
    pi = pd.factorize(s.pid)[0]          # date x period: absorbs all market-wide
    y = demean(s[col].to_numpy(float), ui, pi)
    t_ = demean(s.treat.to_numpy(float), ui, pi)
    Z = np.column_stack([demean(s[f"z_{z}"].to_numpy(float), ui, pi)
                         for z in ("wind", "wind3", "rad")])
    bz, _ = ols(t_, Z)
    that = Z @ bz
    r = t_ - that
    F = ((t_.var() - r.var()) / 3) / (r.var() / max(len(t_) - 4, 1))
    b_ols, _ = ols(y, t_.reshape(-1, 1))
    b2, _ = ols(y, that.reshape(-1, 1))
    e = y - t_ * b2[0]
    cl = {"unit": pd.factorize(s.firm)[0], "date": pd.factorize(s.date)[0]}
    ses = sandwich(that.reshape(-1, 1), e, cl)
    return {"beta": b2[0], "ols": b_ols[0], "se_firm": ses["unit"][0][0],
            "se_date": ses["date"][0][0], "se_tw": ses["two-way"][0][0],
            "n": len(s), "firms": s.firm.nunique(), "units": s.unit.nunique(),
            "F": F}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", action="store_true",
                    help="use the market agent instead of the parent firm")
    ap.add_argument("--min-gwh", type=float, default=1000.0,
                    help="drop firms below this pre-2021 scheduled volume")
    args = ap.parse_args()

    d = build(parent=not args.agent, min_gwh=args.min_gwh)
    print(f"  mapping: {'market agent' if args.agent else 'PARENT FIRM'}, "
          f"size floor {args.min_gwh:,.0f} GWh")
    ok = d.dropna(subset=["exposure"])
    print("=" * 92)
    print("DIFFERENTIAL RENEWABLE EXPOSURE x CAPACITY-QUANTILE OFFER PRICE")
    print("=" * 92)
    print(f"  dispatchable unit-periods       : {len(d):,}")
    print(f"  with a firm and an exposure     : {len(ok):,} "
          f"({100*len(ok)/len(d):.1f}%)")
    print(f"  firms {ok.firm.nunique()}, units {ok.unit.nunique()}, "
          f"periods {ok.pid.nunique():,}, days {ok.date.nunique()}")
    e = ok.drop_duplicates("firm")[["firm", "exposure"]].sort_values("exposure")
    print(f"  exposure across those firms     : median {e.exposure.median():.3f}, "
          f"p10 {e.exposure.quantile(.1):.3f}, p90 {e.exposure.quantile(.9):.3f}")
    print("\n  most and least renewable-heavy firms owning dispatchable plant:")
    print("   ", "; ".join(f"{r.firm} {r.exposure:.2f}" for r in e.head(4).itertuples()))
    print("   ", "; ".join(f"{r.firm} {r.exposure:.2f}" for r in e.tail(4).itertuples()))

    print(f"\n  absorbed: unit and date-x-period fixed effects")
    print(f"  {'quantile':<9}{'winsor':>7}{'2SLS':>10}{'[OLS]':>10}"
          f"{'cl(firm)':>10}{'cl(date)':>10}{'two-way':>10}{'t':>7}"
          f"{'first-F':>10}{'n':>11}")
    for col in QUANTILES:
        for wz in (0.0, 0.01, 0.05):
            r = fit(ok, col, wz)
            if r is None:
                continue
            print(f"  {col:<9}{wz:>7.2f}{r['beta']:>10.4f}{r['ols']:>10.4f}"
                  f"{r['se_firm']:>10.4f}{r['se_date']:>10.4f}{r['se_tw']:>10.4f}"
                  f"{r['beta']/r['se_tw']:>7.2f}{r['F']:>10,.0f}{r['n']:>11,}")
    r = fit(ok, "p50", 0.0)
    if r:
        print(f"\n  clusters: {r['firms']} firms, {ok.date.nunique()} dates "
              f"-- firm clusters are few; treat the firm-clustered SE as "
              f"indicative and bootstrap before quoting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
