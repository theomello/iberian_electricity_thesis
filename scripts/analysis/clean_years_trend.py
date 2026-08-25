#!/usr/bin/env python3
"""Is the price-formation trend secular, or is it the 2021-2023 crisis?

    .venv/bin/python scripts/analysis/clean_years_trend.py
    .venv/bin/python scripts/analysis/clean_years_trend.py --weighted
    .venv/bin/python scripts/analysis/clean_years_trend.py --bandwidth 1

Inputs: outputs/tables/{residual_demand_slope_full,concentration_panel,
supply_anatomy_panel}.parquet. Prints; writes nothing.

WHY THIS EXISTS

The descriptive chapter's spine is two time trends: residual-demand elasticity
(eta) fell and near-marginal concentration (hhi_margin) rose across 2018-2026.
The middle of that window is not a normal market. 2021-2023 holds the European
gas crisis, the windfall levy (RDL 17/2021, 16 Sep 2021 -> 31 Dec 2023) and the
Iberian gas cap (RDL 10/2022, 15 Jun 2022 -> 31 Dec 2023), and eta is not even
monotone through it -- it RISES to 1.21 in 2021 before falling again.

So the trends could be one of two very different things:

  * a secular re-organisation of price formation as variable renewable energy
    (VRE) grew, with the crisis as an episode sitting on top of it; or
  * a crisis story -- an artefact of the 2021-2023 gas spike -- dressed up as a
    trend by fitting a straight line through it.

The spec (docs/specs/2026-08-24-descriptive-price-formation-design.md, §5)
requires this to be settled before anyone reads a mechanism into the series.
The test is to throw 2021-2023 away entirely and re-estimate on 2018-2020 +
2024-2026 only. **If the trends do not survive, the chapter's spine is a crisis
story and the note must say so plainly.**

SPECIFICATIONS

    y_t = b * t + hour-of-day FE + month-of-year FE + (block FE) + e_t

`t` is years since 2018-01-01, so `b` is a per-year rate; in logs it is a
proportional rate. Hour-of-day and month-of-year fixed effects absorb the
diurnal and seasonal composition of who is near the margin; note these are
month-OF-YEAR (12 levels), never year-month, which would absorb the trend
itself. Standard errors are clustered on year-month, since periods within a
month share hydrology, outage and fuel-price conditions.

Six columns per outcome:

    full          all years 2018-2026 -- the number the chapter currently quotes
    clean         2018-2020 + 2024-2026 pooled, one common slope
    clean+block   the same, plus a late-block dummy, so the slope is identified
                  from WITHIN-block variation only and cannot borrow strength
                  from the level gap across the excluded years
    early         2018-2020 alone
    late          2024-2026 alone
    clean+15min   clean pooled, plus a dummy for the 15-minute market time unit

`clean+block` is the strict test and `clean` the lenient one. They answer
different questions and both are reported: `clean` asks whether a line through
the two clean blocks still slopes the right way, `clean+block` asks whether
each block slopes the right way on its own. A trend that survives `clean` but
dies under `clean+block` is a level shift between the two eras, not a trend --
which is a real and reportable finding, not a failure of the test.

`clean+15min` matters because the day-ahead market moved to a 15-minute market
time unit on 2025-10-01, which mechanically thins any fixed-EUR/MWh band and so
could depress eta and inflate hhi_margin in exactly the late block that carries
the clean-years identification. The dummy is collinear with nothing else here
(the 15-minute era is a strict subset of the late block) and absorbs the level
part of that break; it cannot absorb a within-era trend.

WEIGHTING

`--weighted` weights each period by resolution_min/60, so a day contributes the
same total weight whether it is 24 hourly periods or 96 quarter-hourly ones.
Unweighted is the headline (it is the sample as built) and weighted is the
check; if the two disagree the trend is being carried by the mechanical
period-count increase rather than by the market.

WHAT THIS CANNOT FIX

The late years are heavily and non-randomly thinned by the upstream filters --
retained share of periods falls from 94.5% (2018) to 66.1% (2026), driven by
near-zero clearing prices (17.8% of 2026) and market splitting (16.0%), which
are precisely the high-renewable hours. Excluding 2021-2023 does nothing about
that; the clean-years trend is estimated on the same selected late sample as
the full-sample trend. This script tests one confound only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from hydro_spill_window_did import ols_cluster  # noqa: E402

TABLES = ROOT / "outputs" / "tables"

EARLY = (2018, 2019, 2020)
LATE = (2024, 2025, 2026)
CRISIS = (2021, 2022, 2023)

T0 = pd.Timestamp("2018-01-01")


def load_panel(bandwidth: float) -> pd.DataFrame:
    """One period-level frame carrying every outcome, on the common key."""
    h = f"h{bandwidth:g}"
    mkt = pd.read_parquet(
        TABLES / "residual_demand_slope_full.parquet",
        columns=["date", "period", "resolution_min", "p_star",
                 f"eta_{h}", "utc_timestamp"],
    )
    con = pd.read_parquet(
        TABLES / "concentration_panel.parquet",
        columns=["date", "period", "hhi_total",
                 f"hhi_margin_{h}", f"n_firms_margin_{h}",
                 f"mapped_share_margin_{h}"],
    )
    ana = pd.read_parquet(
        TABLES / "supply_anatomy_panel.parquet",
        columns=["date", "period", "share_at_zero", f"band_density_{h}"],
    )
    d = mkt.merge(con, on=["date", "period"], how="inner")
    d = d.merge(ana, on=["date", "period"], how="inner")
    if len(d) != len(mkt):
        raise SystemExit(
            f"panels do not share a key: market {len(mkt):,}, merged {len(d):,}"
        )

    d["year"] = d.date.dt.year
    # Madrid local hour, from the market panel's own UTC stamp -- the other two
    # panels have no timestamp, which is why the merge carries it across.
    local = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    d["hour"] = local.dt.hour.astype(int)
    d["month"] = d.date.dt.month.astype(int)
    d["ym"] = d.year * 100 + d["month"]
    d["t"] = (d.date - T0).dt.days / 365.25
    d["late"] = d.year.isin(LATE).astype(float)
    d["mtu15"] = (d.resolution_min == 15).astype(float)
    d["w"] = d.resolution_min / 60.0

    # Coverage-adjusted concentration. If the in-band volume that could not be
    # mapped to a firm is atomistic -- spread over many small unmapped players
    # rather than concentrated in one -- then HHI_true ~= HHI * coverage^2,
    # because each of the two shares in every term of the HHI sum picks up one
    # factor of the true, coverage-scaled share. Renormalising over a SHRINKING
    # mapped set mechanically raises measured HHI, so this is the bound that
    # matters, not a decoration: coverage falls over this window and the
    # unadjusted trend inherits part of that fall.
    d[f"hhi_margin_adj_{h}"] = (
        d[f"hhi_margin_{h}"] * d[f"mapped_share_margin_{h}"] ** 2
    )

    # Elasticity net of the price level. eta = |RD'| * p* / q, so eta is
    # proportional to the clearing price and a fuel-price move drags it around
    # with no change whatever in the stack's shape. Dividing it out leaves
    # |RD'| / q -- band density per unit of cleared volume, a pure quantity
    # object and the structural half of eta. If the eta decline is really about
    # a thinning stack rather than about gas, this is where it has to show up.
    d[f"eta_norm_{h}"] = d[f"eta_{h}"] / d["p_star"]
    return d


def design(d: pd.DataFrame, extra: list[str]) -> np.ndarray:
    """[t, extra..., hour dummies, month dummies, const], drop-first."""
    cols = [d["t"].to_numpy(float)]
    for c in extra:
        cols.append(d[c].to_numpy(float))
    for name, k in (("hour", 24), ("month", 12)):
        v = d[name].to_numpy(int)
        levels = sorted(set(v))[1:]          # drop first
        for lv in levels:
            cols.append((v == lv).astype(float))
    cols.append(np.ones(len(d)))
    return np.column_stack(cols)


def fit(d: pd.DataFrame, outcome: str, log: bool,
        extra: list[str], weighted: bool) -> tuple[float, float, int, int]:
    """Return (b_per_year, se, n, n_clusters) for the trend coefficient."""
    y = d[outcome].to_numpy(float)
    ok = np.isfinite(y)
    if log:
        ok &= y > 0
    sub = d.loc[ok]
    y = y[ok]
    if log:
        y = np.log(y)
    X = design(sub, extra)
    cl = sub["ym"].to_numpy(int)
    if weighted:
        rw = np.sqrt(sub["w"].to_numpy(float))
        y = y * rw
        X = X * rw[:, None]
    b, se, _ = ols_cluster(y, X, cl)
    return float(b[0]), float(se[0]), len(y), len(np.unique(cl))


def run_outcome(d: pd.DataFrame, outcome: str, log: bool, label: str,
                weighted: bool) -> dict[str, tuple[float, float, int, int]]:
    clean = d[~d.year.isin(CRISIS)]
    specs = {
        "full": (d, []),
        "clean": (clean, []),
        "clean+block": (clean, ["late"]),
        "early": (d[d.year.isin(EARLY)], []),
        "late": (d[d.year.isin(LATE)], []),
        "clean+15min": (clean, ["mtu15"]),
    }
    out = {}
    unit = "log pts/yr" if log else "units/yr"
    print(f"\n  {label}   ({unit})")
    print(f"    {'spec':<13} {'b/yr':>10} {'se':>9} {'t':>8} "
          f"{'95% CI':>20} {'n':>9}")
    for name, (frame, extra) in specs.items():
        if frame.empty:
            continue
        b, se, n, g = fit(frame, outcome, log, extra, weighted)
        out[name] = (b, se, n, g)
        t = b / se if se > 0 else np.nan
        ci = f"[{b - 1.96 * se:+.4f},{b + 1.96 * se:+.4f}]"
        print(f"    {name:<13} {b:>+10.4f} {se:>9.4f} {t:>+8.2f} "
              f"{ci:>20} {n:>9,}")
    return out


def verdict(name: str, r: dict[str, tuple[float, float, int, int]],
            expect_sign: int) -> str:
    """Does the clean-years trend reproduce the full-sample one?"""
    bf = r["full"][0]
    b_pool = r["clean"][0]
    lines = []
    for spec in ("clean", "clean+block"):
        b, se, _, _ = r[spec]
        t = b / se if se > 0 else np.nan
        same = np.sign(b) == np.sign(bf) and np.sign(b) == expect_sign
        sig = abs(t) >= 2.0
        ratio = b / bf if bf != 0 else np.nan
        if same and sig:
            tag = "SURVIVES"
        elif same and not sig:
            tag = "same sign, not significant"
        else:
            tag = "FAILS"
        note = ""
        if spec == "clean+block":
            # A null here is only informative if the pooled slope is actually
            # OUTSIDE this interval. Inside it, the block-FE spec simply lacks
            # the power to tell a trend from a step, and says nothing either
            # way -- a distinction worth printing rather than leaving to be
            # inferred from a t-statistic.
            lo, hi = b - 1.96 * se, b + 1.96 * se
            note = ("  [pooled slope RULED OUT by this CI]"
                    if not (lo <= b_pool <= hi)
                    else "  [pooled slope inside this CI -- underpowered, "
                         "not a rejection]")
        lines.append(f"    {spec:<13} {tag:<28} "
                     f"{ratio:>5.2f}x the full-sample slope{note}")
    return f"  {name}\n" + "\n".join(lines)


def resolution_break(d: pd.DataFrame, bandwidth: float) -> None:
    """The 15-minute market time unit arrived on 2025-10-01. Compare the two
    adjacent months either side of it.

    RAW AND PRICE-MATCHED, because the raw comparison is not interpretable on
    its own: median p* is 77.5 in Sep-2025 and 93.5 in Oct-2025, and a fixed
    +/-h EUR/MWh band is a narrower RELATIVE window at a higher price level.
    Restricting both months to a common p* window is the like-for-like version.
    An earlier note recorded this check as "4808 vs 5016, +4%"; that does not
    reproduce on this panel at any bandwidth and is superseded by what prints
    here.
    """
    h = f"h{bandwidth:g}"
    d = d.copy()
    d["ym"] = d.date.dt.strftime("%Y-%m")
    s = d[d.ym.isin(["2025-09", "2025-10"])]
    print("\n" + "=" * 72)
    print("THE 15-MINUTE BREAK, 2025-10-01 -- adjacent months")
    print("=" * 72)
    print(f"    {'window':<18} {'Sep-2025 (60min)':>18} "
          f"{'Oct-2025 (15min)':>18} {'step':>8}")
    windows = [("raw", None), ("p* in [70,100]", (70, 100)),
               ("p* in [75, 95]", (75, 95))]
    for label, w in windows:
        t = s if w is None else s[(s.p_star >= w[0]) & (s.p_star <= w[1])]
        g = t.groupby("ym")[f"hhi_margin_{h}"].median()
        if len(g) < 2:
            continue
        a, b = g.get("2025-09"), g.get("2025-10")
        print(f"    {label:<18} {a:>18,.0f} {b:>18,.0f} "
              f"{(b / a - 1):>+7.1%}")
    med = s.groupby("ym").p_star.median()
    print(f"    median p*: Sep {med.get('2025-09'):.1f}, "
          f"Oct {med.get('2025-10'):.1f} -- why the raw row is not the "
          f"like-for-like one")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bandwidth", type=float, default=5.0,
                    help="band half-width in EUR/MWh (1, 2, 5 or 10)")
    ap.add_argument("--weighted", action="store_true",
                    help="weight periods by resolution_min/60")
    args = ap.parse_args()

    d = load_panel(args.bandwidth)
    h = f"h{args.bandwidth:g}"
    print(f"CLEAN-YEARS TREND RE-ESTIMATION   bandwidth {h}"
          f"{'   [weighted]' if args.weighted else ''}")
    print(f"  {len(d):,} periods, {d.date.min().date()} -> {d.date.max().date()}")
    print(f"  excluded from the clean sample: {CRISIS} "
          f"({d.year.isin(CRISIS).mean():.1%} of periods)")

    print("\n  median by year, for reference")
    yr = d.groupby("year").agg(
        eta=(f"eta_{h}", "median"),
        hhi_margin=(f"hhi_margin_{h}", "median"),
        hhi_total=("hhi_total", "median"),
        n_firms=(f"n_firms_margin_{h}", "median"),
        p_star=("p_star", "median"),
    )
    print(yr.round(3).to_string().replace("\n", "\n    ").rjust(4))

    print("\n" + "=" * 72)
    print("THE TWO SPINE TRENDS")
    print("=" * 72)
    eta = run_outcome(d, f"eta_{h}", True,
                      f"log eta_{h}  -- residual-demand elasticity",
                      args.weighted)
    hhi = run_outcome(d, f"hhi_margin_{h}", True,
                      f"log hhi_margin_{h}  -- near-marginal concentration",
                      args.weighted)
    nrm = run_outcome(d, f"eta_norm_{h}", True,
                      f"log eta_norm_{h}  -- eta / p*, the price-netted "
                      f"elasticity (|RD'| / q)", args.weighted)
    adj = run_outcome(d, f"hhi_margin_adj_{h}", True,
                      f"log hhi_margin_adj_{h}  -- the same, times coverage^2",
                      args.weighted)

    print("\n" + "=" * 72)
    print("SUPPORTING SERIES")
    print("=" * 72)
    run_outcome(d, "hhi_total", True,
                "log hhi_total  -- aggregate concentration (CNMC-style)",
                args.weighted)
    # eta = |RD'| * p* / q, so it is proportional to the clearing price. A
    # falling price level lowers eta with no change in the stack's shape --
    # which is why the price trend is reported next to it rather than left
    # implicit. Median p* runs 60.4 (2018) -> 34.7 (2020) -> 63.0 (2026).
    run_outcome(d, "p_star", True,
                "log p_star  -- the clearing price, which eta scales with",
                args.weighted)
    run_outcome(d, f"n_firms_margin_{h}", False,
                f"n_firms_margin_{h}  -- firms in the band", args.weighted)
    run_outcome(d, f"band_density_{h}", True,
                f"log band_density_{h}  -- offered MW near p*", args.weighted)
    run_outcome(d, "share_at_zero", False,
                "share_at_zero  -- offered volume at or below 0 EUR/MWh",
                args.weighted)
    run_outcome(d, f"mapped_share_margin_{h}", False,
                f"mapped_share_margin_{h}  -- firm-mapping coverage in the "
                f"band (NOT a market outcome: a falling coverage trend "
                f"mechanically inflates hhi_margin)", args.weighted)

    resolution_break(d, args.bandwidth)

    print("\n" + "=" * 72)
    print("VERDICT -- does the chapter's spine survive without 2021-2023?")
    print("=" * 72)
    print(verdict("eta falls", eta, -1))
    print(verdict("eta falls, net of the price level", nrm, -1))
    print(verdict("hhi_margin rises", hhi, +1))
    print(verdict("hhi_margin rises, coverage-adjusted", adj, +1))
    print("\n  'clean' pools the two blocks with one slope; 'clean+block' adds")
    print("  a late-block dummy so the slope comes from within-block variation")
    print("  only. A trend surviving 'clean' but not 'clean+block' is a level")
    print("  shift between the two eras rather than a trend through them.")


if __name__ == "__main__":
    main()
