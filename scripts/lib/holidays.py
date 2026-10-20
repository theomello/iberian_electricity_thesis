"""Holidays by area and day, for the regional-holiday design.

Reads `data/holidays/holidays_es_pt.parquet` (`fetch/fetch_holidays.py`) and turns it
into area x day indicators. Areas are ISO 3166-2:ES region codes and PT.

    MIBEL     the 15 mainland Spanish regions and Portugal: their load clears in MIBEL
    PLACEBO   the Balearic and Canary Islands, Ceuta and Melilla: separate electrical
              systems, whose load is not bought in MIBEL
    AREAS     MIBEL + PLACEBO, the column order of every indicator frame

    market_wide(days)  True where every MIBEL area has a holiday
    unshared(days)     1 where the area has a holiday that is not market-wide
    bridges(days)      1 on a weekday that is not the area's holiday but sits between
                       two non-working days of that area (weekend or holiday): the
                       Monday before a Tuesday holiday, the Friday after a Thursday one
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
TABLE = ROOT / "data" / "holidays" / "holidays_es_pt.parquet"

ES_MAINLAND = ("AN", "AR", "AS", "CB", "CM", "CL", "CT", "VC", "EX", "GA", "MD", "MC", "NC", "PV", "RI")
MIBEL = ES_MAINLAND + ("PT",)
PLACEBO = ("IB", "CN", "CE", "ML")
AREAS = MIBEL + PLACEBO


def load() -> pd.DataFrame:
    return pd.read_parquet(TABLE)


def _matrix(days: pd.DatetimeIndex) -> pd.DataFrame:
    """1 where the area has any holiday that day."""
    h = load()
    m = pd.DataFrame(0, index=pd.DatetimeIndex(days, name="date"), columns=list(AREAS), dtype=np.int8)
    h = h[h.date.isin(m.index)]
    for area, d in h.groupby("area").date:
        m.loc[d.to_numpy(), area] = 1
    return m


def market_wide(days: pd.DatetimeIndex) -> pd.Series:
    return _matrix(days)[list(MIBEL)].eq(1).all(axis=1)


def unshared(days: pd.DatetimeIndex) -> pd.DataFrame:
    m = _matrix(days)
    return m.mul(~market_wide(days), axis=0).astype(np.int8)


def bridges(days: pd.DatetimeIndex) -> pd.DataFrame:
    days = pd.DatetimeIndex(days)
    span = pd.date_range(days.min() - pd.Timedelta(days=1), days.max() + pd.Timedelta(days=1))
    hol = _matrix(span).astype(bool)
    weekend = (span.dayofweek >= 5)[:, None]
    off = pd.DataFrame(hol.to_numpy() | weekend, index=hol.index, columns=hol.columns)
    sandwiched = off.shift(1, fill_value=False) & off.shift(-1, fill_value=False)
    b = (~off) & sandwiched
    return b.loc[days].astype(np.int8)
