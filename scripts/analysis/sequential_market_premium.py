#!/usr/bin/env python3
"""The day-ahead / intraday price premium — Ito & Reguant (2016) on 2018-2026.

    .venv/bin/python scripts/analysis/sequential_market_premium.py --rebuild
    .venv/bin/python scripts/analysis/sequential_market_premium.py

Caches outputs/tables/sequential_premium_panel.parquet.

WHY THIS DESIGN

Every conduct test in this repo has failed on the same thing: the marginal-cost
measure. Six of them, across two shocks and two margins, and wiring in `cab`'s
declared minimum-income condition — a firm's own daily statement of what it needs
to earn, cross-validated at 0.87 in logs against independent engineering data —
did not rescue any of them (see `min-income-condition.md`).

Ito & Reguant (2016, *AER* 106(7): 1921-57) study this exact market and **use no
marginal cost at all**. Their object is the systematic price premium between the
forward (day-ahead) and spot (intraday) markets. It arises, in their model, from
two things together: dominant firms exercising market power in the forward
market, and **limited entry into arbitrage** between the two. Wind farms
arbitrage part of the premium but do not eliminate it. Welfare is not monotone in
arbitrage — with market power, full arbitrage cuts consumer costs while raising
deadweight loss.

The premium is measured from prices and participation. That is the whole appeal:
it routes around the constraint that has bound everything else here.

WHAT IS NEW RELATIVE TO THE PAPER

Published 2016, so its sample cannot include any of the following, all of which
are in this repo's window and all of which bear on its mechanism:

* **Wind and solar went from 23.9% of generation (2018) to 41.8% (2024).** Wind
  is *their arbitrageur*. If limited arbitrage entry is what sustains the
  premium, a several-fold larger arbitrageur should have compressed it. That is
  a sharp, directional prediction on data they could not have had.
* The 2021 clawback and the 2022-23 Iberian gas cap.
* The 15-minute market time unit — **intraday adopted it in June 2025, four
  months before the day-ahead market did on 2025-10-01**, so the two markets ran
  at different resolutions in between.
* The replacement of MIBEL's 6-7 intraday sessions by the European IDA auctions,
  which **ran in parallel from 2025-03 to 2025-06** before full changeover in
  2025-07. Session indices are therefore not comparable across that boundary:
  1-7 before, 1-3 after, with different meanings.

HOW THE INTRADAY PRICE IS OBTAINED

Derived from the bid archive already on disk rather than fetched. In a uniform-
price auction every cleared sell step is at or below the clearing price and
every cleared buy step at or above it, so the clearing price is bracketed by

    max(cleared sell price)  <=  p*  <=  min(cleared buy price)

Both bounds are computed and the bracket width is reported; where it is zero the
price is exact. `--validate` additionally fetches a sample of OMIE's published
`marginalpibc` files and checks the derived price against them, because a
derived price that is quietly wrong would invert the sign of the whole design.

THREE THREATS, STATED BEFORE THE RESULTS

1. **The premium is not by itself evidence of market power.** Risk premia,
   forecast errors and unit-commitment constraints all generate systematic
   day-ahead/intraday gaps in competitive models. Ito & Reguant's identification
   comes from how the premium varies with concentration and arbitrage entry, not
   from its existence.
2. **Selection into intraday.** The units trading in intraday are not a random
   sample; a premium computed over sessions with thin participation is a
   different object from one computed over deep sessions.
3. **The market-splitting and dropout filters** that apply to the day-ahead
   archive apply here too, and the 61-day 2025 clearing-identity anomaly cluster
   sits inside the IDA transition window.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402

PANEL = OUT / "sequential_premium_panel.parquet"
IDA_SWITCH = pd.Timestamp("2025-07-01")


def build_panel() -> pd.DataFrame:
    out = []
    files = sorted((DATA / "omie/intraday/parquet").glob("intraday_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C"),
            columns=["date", "period", "session", "side", "price_eur_mwh",
                     "power_mw", "resolution_min", "unit"]).to_pandas()
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        sell = t[t.side == "V"]
        buy = t[t.side == "C"]
        a = (sell.groupby(["date", "period", "session"], as_index=False)
                 .agg(id_sell_max=("price_eur_mwh", "max"),
                      id_vol=("power_mw", "sum"),
                      n_units=("unit", "nunique"),
                      res=("resolution_min", "first")))
        b = (buy.groupby(["date", "period", "session"], as_index=False)
                .agg(id_buy_min=("price_eur_mwh", "min")))
        out.append(a.merge(b, on=["date", "period", "session"], how="outer"))
        print(f"  [{i}/{len(files)}] {f.stem}", end="\r", flush=True)
    d = pd.concat(out, ignore_index=True)
    print(f"\n  {len(d):,} date-period-session rows")
    return d


def validate(n_days: int = 6) -> int:
    """Check the derived intraday price against OMIE's published marginalpibc."""
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    from omie_common import omie_url, session  # noqa: E402
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)
    s = session()
    days = (d[d.date.dt.year >= 2023].date.drop_duplicates()
             .sample(n_days, random_state=0).sort_values())
    # Filenames are marginalpibc_YYYYMMDD<SS>.1 — date PLUS a two-digit session
    # index, not one file per day. A date-only guess 404s on every request and
    # looks like "the dataset is missing" rather than "the pattern is wrong".
    rows = []
    for day in days:
        got = 0
        for sess in range(1, 8):
            for rev in (1, 2):
                u = omie_url(
                    "marginalpibc",
                    f"marginalpibc_{day.strftime('%Y%m%d')}{sess:02d}.{rev}")
                r = s.get(u, timeout=60)
                if r.status_code != 200 or "<html" in r.text[:200].lower():
                    continue
                for line in r.text.splitlines():
                    fl = line.strip().rstrip(";").split(";")
                    if len(fl) < 6 or not fl[0].isdigit():
                        continue
                    try:
                        rows.append(dict(
                            date=pd.Timestamp(int(fl[0]), int(fl[1]), int(fl[2])),
                            session=sess, period=int(fl[3]),
                            pub_pt=float(fl[4].replace(",", ".")),
                            pub=float(fl[5].replace(",", "."))))
                    except ValueError:
                        continue
                got += 1
                break
        print(f"  {day.date()}: {got} session files fetched")
    if not rows:
        print("  no published files parsed — cannot validate")
        return 1
    p = pd.DataFrame(rows)
    m = d.merge(p, on=["date", "session", "period"], how="inner")
    if m.empty:
        print("  no overlap after merge — check session/period conventions")
        return 1
    m["gap"] = (m.id_sell_max - m.pub).abs()
    print(f"\n  {len(m):,} matched date-session-periods")
    print(f"  exact matches (<0.01): {(m.gap < 0.01).mean():.1%}")
    print(f"  median |derived - published|: {m.gap.median():.4f} EUR/MWh")
    print(f"  p95: {m.gap.quantile(.95):.4f}")
    return 0


def fit(d, y, xs, j, fe1, fe2, cl):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]))
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 300:
        return None
    M = demean(s[[y] + xs].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    k = xs.index(j)
    if M[:, 1 + k].std() < 1e-9:
        return None
    g = pd.factorize(s[cl])[0]
    b, se, _ = ols_cluster(M[:, 0], M[:, 1:], g)
    return dict(beta=b[k], se=se[k], t=b[k] / se[k], n=len(s),
                nclust=len(np.unique(g)))


def row(lbl, r, w=46):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>42}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    if args.rebuild or not PANEL.exists():
        print("deriving intraday clearing prices from the bid archive...")
        OUT.mkdir(parents=True, exist_ok=True)
        build_panel().to_parquet(PANEL, index=False)
    if args.validate:
        return validate()

    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)
    d["bracket"] = d.id_buy_min - d.id_sell_max

    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt",
                                  "resolution_min", "utc_timestamp"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    d = d.merge(px, on=["date", "period"], how="inner", suffixes=("", "_da"))

    # The two markets adopt the 15-minute MTU on DIFFERENT dates -- intraday in
    # June 2025, day-ahead on 2025-10-01 -- so a period index means different
    # things in each between those dates. Comparing them there is comparing a
    # quarter-hour to an hour. Dropped and counted rather than silently mixed.
    mismatch = d.res != d.resolution_min
    n_mm = int(mismatch.sum())
    d = d[~mismatch]

    # PUBLISHED intraday prices replace the derived ones. The derived estimator
    # is kept alongside, because the gap between them is the measurement error
    # this design nearly ran on: see fetch_omie_intraday_prices.py for the
    # comparison table.
    ip = DATA / "omie/intraday_prices/omie_intraday_prices.parquet"
    if ip.exists():
        q = pd.read_parquet(ip)
        q["date"] = pd.to_datetime(q.date)
        # price_a is Portugal, price_b Spain — the marginalpdbc convention,
        # confirmed against the day-ahead series by --verify on the fetcher.
        q = q.rename(columns={"price_a": "id_pt", "price_b": "id_es"})
        q["id_split"] = q.id_pt != q.id_es
        d = d.merge(q[["date", "session", "period", "id_es", "id_pt",
                       "id_split"]],
                    on=["date", "session", "period"], how="inner")
        d["premium_derived"] = d.price_es - d.id_sell_max
        d["premium"] = d.price_es - d.id_es
        USING_PUBLISHED = True
    else:
        d["premium"] = d.price_es - d.id_sell_max
        d["id_split"] = False
        USING_PUBLISHED = False
    # A premium expressed as a share of the day-ahead price explodes whenever
    # that price approaches zero, which Spain now does routinely at solar noon
    # (the archive's minimum is -15 EUR/MWh). The first cut reported a 2024 mean
    # of -155.94% from exactly this. Computed only where the denominator is
    # meaningfully positive, and winsorised.
    d["prem_pct"] = np.where(d.price_es > 5.0,
                             d.premium / d.price_es, np.nan)
    lo, hi = pd.Series(d.prem_pct).quantile([0.01, 0.99])
    d["prem_pct"] = pd.Series(d.prem_pct).clip(lo, hi)
    d["ida"] = (d.date >= IDA_SWITCH).astype(int)
    d["year"] = d.date.dt.year
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d["hh"] = pd.to_datetime(d.utc_timestamp).dt.hour

    print("=" * 100)
    print("DAY-AHEAD / INTRADAY PRICE PREMIUM — Ito & Reguant (2016) on 2018-2026")
    print("=" * 100)
    print(f"  {len(d):,} date-period-session observations, "
          f"{d.date.min().date()} to {d.date.max().date()}")
    print(f"  dropped {n_mm:,} rows where the two markets ran at different "
          f"resolutions\n    (intraday went 15-min in June 2025, day-ahead on "
          f"2025-10-01)")
    if USING_PUBLISHED:
        e = (d.id_sell_max - d.id_es)
        print(f"  using PUBLISHED intraday prices; the derived estimator was "
              f"off by\n    median {e.abs().median():.3f}, p95 "
              f"{e.abs().quantile(.95):.3f}, mean {e.mean():+.3f} EUR/MWh")
        print(f"  intraday market splits on {d.id_split.mean():.1%} of periods "
              f"(day-ahead: {d.split.mean():.1%})")
    ex = (d.bracket.abs() < 0.01).mean()
    print(f"  clearing price bracketed exactly (|buy_min - sell_max| < 0.01): "
          f"{ex:.1%}")
    print(f"  median bracket width {d.bracket.abs().median():.3f} EUR/MWh")

    # THE INTRADAY MARKET SPLITS INDEPENDENTLY of the day-ahead market — ES and
    # PT intraday prices differ on ~13% of periods, and the bid archive tags
    # almost every unit `MI` rather than by zone. Filtering only on day-ahead
    # splitting, as the first cut did, leaves those in and biases the premium.
    ns = d[(~d.split) & (~d.id_split)]
    print(f"\n  PREMIUM (day-ahead minus intraday), non-splitting periods only "
          f"({len(ns):,} obs)")
    print(f"    mean {ns.premium.mean():+.3f} EUR/MWh, median "
          f"{ns.premium.median():+.3f}, sd {ns.premium.std():.2f}")
    print(f"    share of periods with a POSITIVE premium: "
          f"{(ns.premium > 0.005).mean():.1%}, negative "
          f"{(ns.premium < -0.005).mean():.1%}, exactly zero "
          f"{(ns.premium.abs() < 0.005).mean():.1%}")
    # The mean is a small number on a large standard deviation, so it needs a
    # clustered standard error and a trimming check before it is called a
    # premium at all. Observations are serially correlated within day and month.
    y = ns.premium.to_numpy(float)
    X = np.ones((len(y), 1))
    for lbl, key in (("month", ns.ym), ("day", ns.date)):
        g = pd.factorize(key)[0]
        b, se, _ = ols_cluster(y, X, g)
        print(f"    mean, SE clustered on {lbl:<6} ({len(np.unique(g)):>5,} "
              f"clusters): {b[0]:+.4f}  se {se[0]:.4f}  t {b[0]/se[0]:+.2f}")
    print("    trimmed means (is it a tail?): ", end="")
    for p in (1, 5, 10):
        lo, hi = ns.premium.quantile([p / 100, 1 - p / 100])
        t = ns.premium[(ns.premium >= lo) & (ns.premium <= hi)].mean()
        print(f"{p}% {t:+.3f}   ", end="")
    print()
    print(f"    positive tail mean {ns.premium[ns.premium > 0.005].mean():+.2f}"
          f"  |  negative tail mean "
          f"{ns.premium[ns.premium < -0.005].mean():+.2f}")
    for lbl, sub in (("pre-IDA", ns[ns.ida == 0]), ("IDA", ns[ns.ida == 1])):
        g = pd.factorize(sub.ym)[0]
        b, se, _ = ols_cluster(sub.premium.to_numpy(float),
                               np.ones((len(sub), 1)), g)
        print(f"    {lbl:<8} n={len(sub):>8,}  mean {b[0]:+.3f}  se {se[0]:.3f}"
              f"  t {b[0]/se[0]:+.2f}")

    print("\n  BY SESSION  (1-7 before 2025-07, 1-3 after — not comparable)")
    print(f"    {'session':>8}{'era':>10}{'n':>10}{'mean prem':>12}"
          f"{'median':>10}{'share>0':>10}")
    for era, sub in (("pre-IDA", ns[ns.ida == 0]), ("IDA", ns[ns.ida == 1])):
        for sess in sorted(sub.session.unique()):
            s = sub[sub.session == sess]
            if len(s) < 500:
                continue
            print(f"    {sess:>8}{era:>10}{len(s):>10,}"
                  f"{s.premium.mean():>12.3f}{s.premium.median():>10.3f}"
                  f"{(s.premium > 0).mean():>10.1%}")

    print("\n  BY YEAR — session 1 only (the closest analogue to the paper's "
          "first spot market)")
    s1 = ns[ns.session == 1]
    print(f"    {'year':>6}{'n':>9}{'mean prem':>12}{'median':>10}"
          f"{'share>0':>10}{'DA price':>10}{'prem %':>9}")
    for y in sorted(s1.year.unique()):
        s = s1[s1.year == y]
        print(f"    {y:>6}{len(s):>9,}{s.premium.mean():>12.3f}"
              f"{s.premium.median():>10.3f}{(s.premium > 0).mean():>10.1%}"
              f"{s.price_es.mean():>10.1f}{100*s.prem_pct.mean():>8.2f}%")

    # ---- the mechanism: wind is their arbitrageur, and wind has grown ----
    rd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                         columns=["date", "period", "vre_share", "demand"])
    rd["date"] = pd.to_datetime(rd.date)
    s1 = s1.merge(rd, on=["date", "period"], how="left")
    s1["ldem"] = np.log(s1.demand.clip(lower=1))

    print("\n" + "-" * 100)
    print("MECHANISM — if limited arbitrage entry sustains the premium, a bigger")
    print("  arbitrageur should compress it. Wind is the arbitrageur in the "
          "paper.")
    print("-" * 100)
    print(f"\n{'specification':<46}{'beta':>12}{'se':>10}{'t':>7}"
          f"{'obs':>10}{'clust':>8}")
    row("VRE share -> premium (hour + year-month FE)",
        fit(s1, "premium", ["vre_share", "ldem"], "vre_share", "hh", "ym", "ym"))
    row("VRE share -> premium, %% of DA price",
        fit(s1, "prem_pct", ["vre_share", "ldem"], "vre_share", "hh", "ym", "ym"))
    row("intraday depth (units trading) -> premium",
        fit(s1, "premium", ["n_units", "ldem"], "n_units", "hh", "ym", "ym"))
    print("\n  premium and intraday participation, by year (session 1)")
    print(f"    {'year':>6}{'mean units in ID':>20}{'mean ID volume MWh':>22}"
          f"{'mean premium':>15}")
    for y in sorted(s1.year.unique()):
        s = s1[s1.year == y]
        print(f"    {y:>6}{s.n_units.mean():>20.0f}{s.id_vol.mean():>22,.0f}"
              f"{s.premium.mean():>15.3f}")

    print("\nRead: a positive premium is necessary but not sufficient — risk "
          "premia and\nforecast errors generate one under competition too. The "
          "mechanism rows are\nwhere the identification is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
