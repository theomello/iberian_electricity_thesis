#!/usr/bin/env python3
"""Portugal reservoir storage, reconstructed from Wayback Machine snapshots.

    .venv/bin/python scripts/fetch/fetch_snirh_reservoirs_wayback.py

WHY THIS EXISTS

`snirh.apambiente.pt` -- Portugal's APA-run equivalent of MITECO -- returns
403 to every client tried, including a full browser session (see
`notes/hydro-water-value-design.md`'s 2026-08-19 section), and no bulk
historical export was found anywhere else: not on ArcGIS Online (two dead
APA publications, one a single-month snapshot, one a ten-month 2018-2019
web map), not via LNEG (wrong agency, groundwater not surface reservoirs),
not via a CRAN/GitHub tool (the only two found go the wrong direction --
uploading lab results TO SNIRH -- or have no live instance), and a broad
scan of the top 3,000 archived URLs under this domain for anything
export/CSV/historical-shaped turned up nothing beyond a client-side
table-to-CSV utility script that only ever converts whatever the live
AJAX backend already rendered -- no hidden bulk data behind it.

What the Wayback Machine (web.archive.org) has instead: repeated crawls of
the exact blocked "Boletim de Armazenamento de Albufeiras" page, one
snapshot per crawl, each showing that basin's reservoirs and their fill
percentage AT THAT MOMENT. Not a bulk archive -- a scattered set of
point-in-time snapshots, whatever the Internet Archive's crawler happened
to visit. This script turns those into a usable (if sparse) panel.

RESOLUTION, HONESTLY, AGAINST MITECO

MITECO gives Spain a continuous weekly series. Scoped 2026-08-19 (see the
design note): each of the six basins here gets roughly 3-9 captures/year
in 2018-2021, thins to 1-2/year in 2022-2023, and 2024 is essentially
empty (only Lima has any). Call it 13-17x sparser than Spain in the best
years, and a real gap in the worst one. Treat this as a rough, irregular
check on levels, not a series fine enough for month-to-month inference.

WHAT GETS PARSED

The page's own text states its basin and the calendar month/year the
snapshot describes (e.g. "Situação das Albufeiras em Novembro de 2023 na
bacia TEJO") -- that is the DATA date, and is used here, not the crawl
timestamp (which can lag the data by days). Reservoir names and fill
percentages are read off the three severity buckets the page groups them
into ("superior a 80%", "entre 50% e 80%", "inferior a 50%") -- the bucket
label itself is discarded; only the per-reservoir figure is kept.

The interactive charts and "Dados em tabela" export on the live page both
depend on the site's AJAX backend, which is NOT archived (confirmed
2026-08-19: clicking either on an archived page does nothing) -- so a
single capture is genuinely one data point per reservoir, not a hidden
multi-month history. No multiplier available.

FRAGILE ON PURPOSE, NOT SILENTLY

The site's front end almost certainly changed layout over the 2014-2025
span these captures cover. Rather than guess at every era's markup, this
parses the one layout confirmed against a real page (Tejo, Nov 2023) and
reports, per capture, how many reservoirs it found -- zero is a visible
parse failure, not a silent gap. Restricted to captures from 2018 onward
(the repo's analysis window); nothing here needs the pre-2018 captures
that also exist.

About one in five captures parses to zero rows even after the fixes above
-- checked directly (Tejo, 2019-03-22): the page rendered that reservoir's
status as a clickable image map (`usemap="#bolalbufbacia"`) instead of the
text table this parser reads, so the percentages simply are not present
in that capture's HTML at all. Not a bug to chase further -- a genuine
rendering-mode gap in what was archived.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "snirh"
OUT.mkdir(parents=True, exist_ok=True)

# Portuguese hydrographic basin IDs used by snirh.apambiente.pt's own
# sbaciaid parameter -- confirmed 2026-08-19 against the December 2018
# reservoir-level snapshot embedded in APA's own "Albufeiras do Boletim
# SNIRH" ArcGIS web map (see the design note), matched to the basins our
# target hydro_ugh/Portuguese cascades sit in.
BASINS = {
    17: "tejo",
    12: "douro",
    1551779250: "lima",
    47: "mondego",
    107: "cavado",
    23: "guadiana",
}

CDX = "https://web.archive.org/cdx/search/cdx"
MIN_TIMESTAMP = "20180101"
DELAY = 0.5  # polite; a public archive, not an API meant for bulk scraping

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (academic research; MIBEL/MIBEL hydro thesis)"})


def get_with_retry(url: str, retries: int = 7, **kw) -> requests.Response:
    """archive.org is intermittently slow/times out under repeated requests
    -- confirmed while scoping this fetch (curl hit the same thing) -- so
    every request gets retried with backoff rather than failing the whole
    run on one flaky response."""
    last = None
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=kw.pop("timeout", 30), **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last

MONTH_MAP = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

HEADER_RE = re.compile(
    r"Situa[cç][aã]o das Albufeiras em (\w+) de (\d{4})\s*na bacia", re.I)
# Reservoirs are comma-separated within a severity bucket, with a Portuguese
# "e" (and) before the last one instead of a comma -- e.g. "Apartadura
# (<strong>89.8%</strong>), Cova do Viriato (<strong>99.6%</strong>) e Idanha
# (<strong>81.4%</strong>)". The name capture must exclude '>' as well as '<'
# -- omitting it let an early version of this regex swallow the tail of the
# PRECEDING </td><td> markup into the next bucket's first reservoir name
# (caught as "td>Cabril" instead of "Cabril" when checked against real
# fetched pages, 2026-08-19). The leading "e " conjunction is stripped
# afterward, not excluded from the character class, since excluding the
# letter "e" itself would break every name containing one.
RESERVOIR_RE = re.compile(r"([^,()<>\n\t]+?)\s*\(<strong>([\d.]+)%</strong>\)")


def captures(baciaid: int) -> list[str]:
    """All capture timestamps for this basin's synthesised-data page,
    restricted to MIN_TIMESTAMP onward."""
    url = f"https://snirh.apambiente.pt/index.php?idMain=1&idItem=1.3&sbaciaid={baciaid}"
    r = get_with_retry(CDX, params={"url": url, "output": "json", "fl": "timestamp",
                                    "limit": 200, "from": MIN_TIMESTAMP})
    rows = r.json()
    return [row[0] for row in rows[1:]]


def parse_page(raw_html: str, baciaid: int, timestamp: str) -> list[dict]:
    text = html.unescape(raw_html)
    m = HEADER_RE.search(text)
    if not m:
        return []
    month_name, year = m.group(1).lower(), int(m.group(2))
    month = MONTH_MAP.get(month_name)
    rows = []
    for name, pct in RESERVOIR_RE.findall(text):
        name = re.sub(r"^e\s+", "", name.strip())  # strip the "and" before the last item
        rows.append({
            "baciaid": baciaid,
            "basin": BASINS[baciaid],
            "reservoir": name,
            "fill_pct": float(pct),
            "data_year": year,
            "data_month": month,
            "data_month_name": m.group(1),
            "capture_timestamp": timestamp,
        })
    return rows


def fetch_basin(baciaid: int) -> list[dict]:
    name = BASINS[baciaid]
    ts_list = captures(baciaid)
    print(f"\n{name} (baciaid={baciaid}): {len(ts_list)} captures from {MIN_TIMESTAMP} onward")
    out: list[dict] = []
    n_empty = 0
    for i, ts in enumerate(ts_list, 1):
        url = (f"https://web.archive.org/web/{ts}/https://snirh.apambiente.pt/"
               f"index.php?idMain=1&idItem=1.3&sbaciaid={baciaid}")
        try:
            r = get_with_retry(url)
        except requests.RequestException as e:
            print(f"  [{i:2d}/{len(ts_list)}] {ts}  FETCH FAILED ({e})")
            continue
        rows = parse_page(r.text, baciaid, ts)
        if not rows:
            n_empty += 1
        print(f"  [{i:2d}/{len(ts_list)}] {ts}  {len(rows)} reservoirs"
              + ("  <- PARSE FAILURE" if not rows else ""))
        out.extend(rows)
        time.sleep(DELAY)
    if n_empty:
        print(f"  {n_empty}/{len(ts_list)} captures for {name} parsed to zero "
              f"rows -- likely a different-era page layout, not missing data")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--basin", type=int, help="single baciaid, for testing")
    args = ap.parse_args()

    targets = {args.basin: BASINS[args.basin]} if args.basin else BASINS
    all_rows: list[dict] = []
    for baciaid in targets:
        # One basin failing outright (e.g. a longer archive.org outage than
        # the retry budget covers) must not lose the other basins' results
        # -- confirmed necessary 2026-08-19, when a mid-run CDX timeout
        # crashed the whole script and discarded everything fetched so far.
        try:
            all_rows.extend(fetch_basin(baciaid))
        except requests.RequestException as e:
            print(f"\n{BASINS[baciaid]} (baciaid={baciaid}): FAILED entirely ({e}) "
                  f"-- continuing with the other basins, re-run --basin {baciaid} "
                  f"later to fill this one in")

    if not all_rows:
        print("\nno rows parsed at all", file=sys.stderr)
        return 1

    df = pd.DataFrame(all_rows)
    path = OUT / "reservoirs_wayback.parquet"
    if path.exists():
        # Merge with whatever is already on disk rather than overwrite it --
        # so re-running with --basin to fill in one basin that failed a
        # prior full run doesn't discard the basins that already succeeded.
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    df = df.drop_duplicates(subset=["baciaid", "reservoir", "data_year", "data_month",
                                    "capture_timestamp"])

    print(f"\n{'=' * 72}")
    print(f"TOTAL: {len(df):,} reservoir-snapshot rows, "
          f"{df.reservoir.nunique()} distinct reservoir names, "
          f"{df.basin.nunique()} basins")
    print(f"date range: {df.data_year.min()}-{df.data_month.min():02d} to "
          f"{df.data_year.max()}-{df.data_month.max():02d}")
    print("\nsnapshots per basin per year:")
    print(pd.crosstab(df.basin, df.data_year).to_string())

    df.to_parquet(path, index=False)
    print(f"\nwrote {path.relative_to(ROOT)}  ({len(df):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
