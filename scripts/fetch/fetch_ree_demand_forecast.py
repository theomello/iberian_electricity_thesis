#!/usr/bin/env python3
"""REE's day-ahead demand forecast — the anticipated/unanticipated split.

    .venv/bin/python scripts/fetch/fetch_ree_demand_forecast.py
    .venv/bin/python scripts/fetch/fetch_ree_demand_forecast.py --verify

Writes data/ree/ree_demand_forecast_5min.parquet. Token-free. Resumable.

WHY

`literature-extreme-weather-economics.md` §3.2 records the flaw shared by every
weather design in this repo: **day-ahead offers are submitted at noon on D-1
against a forecast**, so realised weather on day D is not a surprise to the
bidder. Treating a realisation as a shock to the firm's information set is wrong
on its face, and the repo held no forecast of any kind.

This closes half of that gap. `demanda.ree.es`'s `prevProgPeninsula` endpoint
publishes, at 5-minute resolution and back to at least 2018:

    pre   prevista    — REE's demand FORECAST
    pro   programada  — the SCHEDULED demand after the market clears

884,880 instants, 3,072 of 3,073 days, matched 1:1 against REE's own realtime
actuals. Full-sample: forecast error mean −147.6 MW, sd 798.1, MAE 404.6 (1.39%
of demand).

**THREE PERIODS MUST BE EXCLUDED BEFORE USING THIS, and the headline number
changes once they are.**

| period | error sd | MAE | corr(forecast, actual) |
|---|---|---|---|
| before 2025-12-12 | 694 | 336 | 0.9896 |
| from 2025-12-12 | **1,737** | **1,569** | 0.9376 |

1. **2025-12-12 onward.** CLAUDE.md documents that `demanda.ree.es` changed its
   request contract that day (``curva=NACIONAL`` stops being accepted, and three
   fields are replaced). The forecast/actual match degrades with it — MAE goes
   336 → 1,569 and the correlation 0.990 → 0.938. This is a comparability break
   in the *actuals*, not worse forecasting.
2. **2025Q2, error sd 2,394** — the quarter containing the **28 April 2025
   Iberian blackout**. A national blackout makes any demand forecast
   catastrophically wrong for days. Genuine, and genuinely unusable.
3. **2023Q1, mean error −1,204 MW with sd 819** — a large systematic bias in one
   quarter with no counterpart before or after. **Unexplained.** Do not use
   2023Q1 without establishing what it is.

On the clean quarters (2018-2025Q1 excluding 2023Q1) the error standard
deviation runs **200-490 MW**. That is *comparable to*, not double, the 537 MW
one-sd heat shock this repo has used as a demand shifter — an earlier note in
this file claiming "nearly double" was computed from a 1,800-instant single-day
sample and does not survive the full series. What it does add over temperature is
that it is, by construction, the part nobody anticipated.

WHAT THIS DOES NOT GIVE

**Not a wind forecast.** That is the series the day-ahead/intraday premium design
actually needs, because systematic under-forecasting of wind at gate closure
generates a premium with no conduct at all, and mimics the arbitrage channel
exactly. Checked 2026-08-21 and there is **no token-free route**:

* `demanda.ree.es` publishes no renewable forecast endpoint —
  `prevProgRenovablePeninsula`, `prevRenovablePeninsula`, `prevProgEolicaPeninsula`
  and `eolicaPeninsula` all 404.
* ESIOS indicator 541 (*previsión eólica*) returns **HTTP 403** without a token,
  as does `/archives` itself — so the token-free archive route that works for
  archives 82 and 83 does not extend to it.
* ENTSO-E's transparency platform requires a token too.

A personal ESIOS token is free but must be requested by email
(`consultasios@ree.es`; see `scripts/lib/config.py`). Until someone does that,
the wind-forecast-error confound in `rq-sequential-market-premium.md` §6 cannot
be separated from the arbitrage channel.

TIMEZONE — AND THE TRAP THIS FILE WALKED INTO ANYWAY

`ts` is **local Madrid time**, like every other `demanda.ree.es` series. The
autumn DST hour is written `2A` (first pass, CEST) and `2B` (second pass, CET),
so `pd.to_datetime` raises on `2018-10-28 2A:00`. This is documented in
CLAUDE.md, was cited in this docstring's first version, and was still not handled
in the code — the assembly step crashed after every day had been downloaded.

Fixed by importing `parse_local_ts` from `fetch_ree_realtime.py`, which already
solved it for the sibling endpoint, rather than writing a second implementation:
two copies of the same DST rule would diverge silently and produce wrong
timestamps rather than an error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, END, START, session  # noqa: E402

OUT = DATA / "ree" / "ree_demand_forecast_5min.parquet"
PART = DATA / "ree" / "_forecast_parts"
URL = ("https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/"
       "prevProgPeninsula")


def fetch_day(sess, d: date) -> pd.DataFrame | None:
    r = sess.get(URL, params={"curva": "NACIONAL", "fecha": d.isoformat()},
                 timeout=45)
    if r.status_code != 200 or len(r.text) < 50:
        return None
    body = re.sub(r"^\s*null\(|\);\s*$", "", r.text)
    try:
        j = json.loads(body)
    except json.JSONDecodeError:
        return None
    rec = j.get("valoresPrevistaProgramada")
    if not rec:
        return None
    df = pd.DataFrame(rec)
    df["local_date"] = d
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        return verify()

    PART.mkdir(parents=True, exist_ok=True)
    sess = session()
    d, missing = START, []
    n = 0
    while d <= END:
        p = PART / f"{d.isoformat()}.parquet"
        if not p.exists():
            df = fetch_day(sess, d)
            if df is None:
                missing.append(d)
            else:
                df.to_parquet(p, index=False)
        n += 1
        if n % 250 == 0:
            print(f"  {d} ({n} days, {len(missing)} missing)", flush=True)
        d += timedelta(days=1)

    parts = sorted(PART.glob("*.parquet"))
    all_ = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    # The autumn DST hour is written 2A (first pass, CEST) and 2B (second pass,
    # CET), so pandas' parser raises on it. `fetch_ree_realtime.py` already
    # solved this for the sibling endpoint; reuse that parser rather than
    # writing a second one, since a divergence between two implementations of
    # the same DST rule would be invisible until it produced wrong timestamps.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_ree_realtime import parse_local_ts  # noqa: E402
    all_["utc_timestamp"] = all_.ts.map(parse_local_ts)
    bad = all_.utc_timestamp.isna().sum()
    if bad:
        print(f"  {bad:,} timestamps unparseable — dropped")
        all_ = all_[all_.utc_timestamp.notna()]
    all_["utc_timestamp"] = pd.to_datetime(all_.utc_timestamp, utc=True)
    all_ = all_.rename(columns={"pre": "demand_forecast_mw",
                                "pro": "demand_scheduled_mw"})
    all_ = all_.drop_duplicates(subset=["utc_timestamp"]).sort_values("utc_timestamp")
    all_ = all_.drop(columns=["ts"])
    all_.to_parquet(OUT, index=False)
    print(f"\n  {len(all_):,} instants, {all_.local_date.nunique():,} days, "
          f"{len(missing)} days missing")
    print(f"  wrote {OUT}")
    return 0


def verify() -> int:
    import pyarrow.parquet as pq
    f = pd.read_parquet(OUT)
    rt = pq.read_table(DATA / "ree/ree_realtime_5min.parquet",
                       columns=["utc_timestamp", "demand"]).to_pandas()
    m = f.merge(rt, on="utc_timestamp", how="inner").dropna(
        subset=["demand_forecast_mw", "demand"])
    print(f"{len(f):,} forecast instants, {len(m):,} matched to actuals")
    print(f"  span {f.utc_timestamp.min()} to {f.utc_timestamp.max()}")
    for c, lbl in (("demand_forecast_mw", "pre (forecast)"),
                   ("demand_scheduled_mw", "pro (scheduled)")):
        e = m[c] - m.demand
        print(f"  {lbl:<18} mean {e.mean():+8.1f}  sd {e.std():8.1f}  "
              f"MAE {e.abs().mean():8.1f}  ({e.abs().mean()/m.demand.mean():.2%})")
    m["year"] = m.utc_timestamp.dt.year
    print("\n  forecast error sd by year (MW):")
    print((m.demand_forecast_mw - m.demand).groupby(m.year).std()
          .round(0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
