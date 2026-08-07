"""Shared helpers for the OMIE fetchers.

Everything here encodes a trap that was verified empirically against real
OMIE files on 2026-08-07. See CLAUDE.md for the full list.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

OMIE_DOWNLOAD = "https://www.omie.es/es/file-download"
OMIE_LIST = "https://www.omie.es/es/file-access-list"

MADRID = ZoneInfo("Europe/Madrid")

# Portugal runs one hour behind Spain (WET/WEST vs CET/CEST) despite sharing
# a single electricity market. REN publishes in Lisbon local time, OMIE and
# REE in Madrid local time. Confirmed empirically on 2026-08-07 by solar-noon
# geometry: under the Lisbon reading, PT and ES solar noon coincide at 12:22
# UTC on 2024-06-15; under a Madrid reading PT would fall 60 minutes *earlier*
# than Spain, which is impossible for a country lying further west.
LISBON = ZoneInfo("Europe/Lisbon")

# Study window. Start is set by the bid archive, which begins 2018-01.
START = date(2018, 1, 1)
END = date(2026, 5, 31)


def session() -> requests.Session:
    """A requests session with retries on the transient 5xx/429 codes."""
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    s.headers.update({"User-Agent": "vre-spain-thesis/research (academic use)"})
    return s


def omie_url(dataset: str, filename: str) -> str:
    return f"{OMIE_DOWNLOAD}?parents%5B0%5D={dataset}&filename={filename}"


def day_span_utc(d: date, tz: ZoneInfo = MADRID) -> tuple[datetime, datetime]:
    """UTC bounds of local (Europe/Madrid) day `d`.

    The Madrid DST transition happens at 02:00/03:00 local, so local midnight
    is never ambiguous and can be constructed directly.
    """
    start = datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc)
    nxt = d + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).astimezone(timezone.utc)
    return start, end


def day_periods_utc(d: date, n_periods: int, tz: ZoneInfo = MADRID) -> list[datetime]:
    """UTC instants for each OMIE period index of local day `d`.

    OMIE indexes market periods 1..N within the *local* day. N encodes both
    the market resolution and DST:

    ===========  ==============  ====================================
    N            resolution      day
    ===========  ==============  ====================================
    23 / 24 / 25 hourly          spring DST / normal / autumn DST
    92 / 96 / 100 quarter-hourly spring DST / normal / autumn DST
    ===========  ==============  ====================================

    **OMIE moved from hourly to 15-minute market time units on 2025-10-01**
    (the EU-wide MTU change). Any code that assumes 24 periods per day breaks
    on every day from that date onward, and any code that assumes a fixed
    step breaks on the two DST days a year. Deriving the step from the actual
    local-day span handles all six cases without special-casing.
    """
    start, end = day_span_utc(d, tz)
    step = (end - start) / n_periods
    return [start + step * i for i in range(n_periods)]


def resolution_minutes(n_periods: int) -> int:
    """Infer the market resolution from the number of periods in a day."""
    return 60 if n_periods <= 25 else 15


def parse_price_number(s: str) -> float:
    """`marginalpdbc` uses a DOT decimal separator (e.g. `77.7`).

    This differs from `curva_pbc_uof`, which uses a comma. Do not share a
    number parser between the two files.
    """
    return float(s.strip())


def parse_bid_number(s: str) -> float:
    """`curva_pbc_uof` uses a COMMA decimal and a DOT thousands separator.

    `1.500,00` is 1500.0, not 1.5.
    """
    return float(s.strip().replace(".", "").replace(",", "."))


def month_range(start: date, end: date) -> list[str]:
    """YYYYMM strings spanning start..end inclusive."""
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y}{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
