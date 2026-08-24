"""Band-slope primitives for residual demand, shared by the market-level and
firm-level scripts.

Extracted from scripts/analysis/residual_demand_slope.py, which is the proven
implementation; that script now imports these rather than defining them, so
the two levels cannot drift apart.

THE OBJECT

Offer curves are step functions and have no derivative. Differencing the
cumulative curve over a price window h is equivalent to counting offered MW
within +/-h of the clearing price:

    |RD'(p*)| ~= (sell MW in band + buy MW in band) / 2h

so the "derivative" is literally the density of offers near the clearing price,
and h is the only tuning knob.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

BANDWIDTHS: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0)
IDENTITY_TOL = 0.001   # relative gap between matched buy and matched sell
ZERO_PRICE = 1.0       # euro/MWh; at or below this, eta is not meaningful

KEY = ["date", "period"]


def cleared_by_period(bids: pd.DataFrame) -> pd.DataFrame:
    """Matched sell and buy volume per period, with the clearing-identity gap.

    side "V" is venta (sell) and "C" is compra (buy). Note that status "C"
    means *cleared*, a different column with a different meaning.
    """
    mat = bids[bids.status == "C"]
    m = (mat.groupby(KEY + ["side"])["power_mw"].sum()
            .unstack("side").reindex(columns=["V", "C"]).fillna(0.0))
    m.columns = ["sell_matched", "buy_matched"]
    m = m[m.sell_matched > 0].reset_index()
    m["identity_gap"] = (m.sell_matched - m.buy_matched).abs() / m.sell_matched
    return m


def band_offers(bids: pd.DataFrame, p_star: pd.DataFrame, h: float) -> pd.DataFrame:
    """Submitted offers within +/-h euro/MWh of the clearing price.

    p_star must carry KEY plus a "p_star" column.
    """
    off = bids[bids.status == "O"].merge(p_star[KEY + ["p_star"]], on=KEY, how="inner")
    off = off.assign(dev=(off.price_eur_mwh - off.p_star).abs())
    return off[off.dev <= h]


def slope_from_band_mw(band_mw: pd.Series, h: float,
                       p_star: pd.Series, q: pd.Series):
    """(slope, impact, eta) from MW sitting inside a +/-h band.

    eta = |RD'| p / Q is the scale-free version. Price impact alone is NOT
    comparable across years: a fixed +/-h euro band is a *narrower relative*
    window when the price level is 200 than when it is 50, which mechanically
    thins the band and inflates impact in 2022.
    """
    slope = band_mw.fillna(0.0) / (2 * h)
    impact = np.where(slope > 0, 1 / slope.replace(0, np.nan), np.nan)
    eta = np.where((slope > 0) & (p_star > 0), slope * p_star / q, np.nan)
    return slope, impact, eta
