#!/usr/bin/env python3
"""Does basin rainfall move a hydro plant's own offers? A cheap probe before
the structural water-value model.

    .venv/bin/python scripts/analysis/hydro_water_value_precip.py

THE PROBLEM THIS SOLVES

`notes/candidate-natural-experiments.md` records four designs for the 2021
windfall levy, the last of which (differential contract exposure) identifies
cleanly and still yields nothing reportable, because the sign flips across
outcome variables. The diagnosis there: "the binding problem is measurement,
not identification" -- hydro's opportunity cost (water value) has no clean
proxy, and every proxy built from the bid data is contaminated, censored, or
unstable.

This script asks a smaller, prior question before committing to the full
structural model `notes/hydro-water-value-design.md` describes (reservoir
volume + snowpack + forward price, jointly estimated): does basin-level
rainfall move a storage plant's own offers *at all*? Rain is not a function
of bidding, so if it has power here, it is a genuinely exogenous shifter of
water value -- the ingredient every other proxy lacked.

DESIGN

For each `hydro_ugh` unit whose `cab` name identifies its river basin (see
`build_unit_agents.py`'s TECH_PATTERNS and the basin points chosen in
`fetch_hydro_precipitation.py`), regress the unit's monthly offer on a
90-day trailing rainfall anomaly in its OWN basin, with unit and month fixed
effects:

    y_it = beta * rain_anomaly_i,t + unit FE + month FE

Month FE absorb the market-wide gas-price cycle, which is what contaminated
every cross-country and cross-technology design tried so far -- rain in one
Spanish basin does not move MIBGAS.

THE PLACEBO THIS DESIGN NEEDS

Rain is regional, so two basins can be correlated with each other and with
national weather patterns for reasons that have nothing to do with any one
plant's reservoir. The check: refit with each unit's OWN-basin anomaly
replaced by a WRONG basin's anomaly (a fixed rotation, not the unit's own).
If wrong-basin rain predicts the same unit's offers about as well as its own
basin's rain, the effect is not basin-specific and this proxy is no better
than the ones that already failed. If own-basin dominates, that is the
signature this design needs.

ANOMALY, NOT LEVEL

Rainfall has a strong seasonal cycle and reservoirs are managed against that
cycle, so the level of rain in a given month says little on its own. The
anomaly is trailing 90-day cumulative precipitation minus that basin's own
mean 90-day sum for the same calendar day-of-year, i.e. deviation from what
is normal for that basin at that time of year -- the same logic as the
wind/radiation instruments in `bid_steepness_iv.py`, adapted to a slower,
accumulating process (rain today does not raise a reservoir tomorrow; it
takes weeks of inflow).

WHAT A RESULT HERE DOES AND DOES NOT SETTLE

A live coefficient here is evidence the channel exists -- not a finished
water-value measure. Rainfall is one input to inflow, not inflow itself, and
`hydro-water-value-design.md` is explicit that the *expected future price*
channel (which moved hydro's offer 154 -> 615 -> 100 EUR/MWh across
2021-2024, tracking the gas crisis, not any calendar date) still needs the
structural model to net out. This script's job is only to say whether
building that model is worth the three more data series it costs.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawback_intensity_did import twfe  # noqa: E402
from levy_contract_exposure import panel as offer_panel  # noqa: E402

# unit descr -> basin, read off the same river/basin vocabulary
# build_unit_agents.py uses for the Portuguese cascades, applied to the
# Spanish UGH names. Left unmapped rather than guessed where the name is a
# plant/company label with no basin cue (e.g. "GRDZ", "TRC2").
BASIN_PATTERNS: list[tuple[str, str]] = [
    (r"\bDUERO\b|\bESLA\b|\bTERA\b", "duero"),
    (r"\bEBRO\b", "ebro"),
    (r"\bTAJO\b", "tajo"),
    (r"\bGUADIANA\b", "guadiana"),
    (r"\bGUADALQUIVIR\b", "guadalquivir"),
    (r"\bJUCAR\b|J[UÚ]CAR", "jucar"),
    (r"\bSIL\b|\bMI[NÑ]O\b|\bBIBEY\b|\bEUME\b|GALICIA", "galicia_sil_mino"),
    (r"\bVIESGO\b|\bAG[UÜ]ERA\b|HIDROCANT[AÁ]BRICO|CANT[AÁ]BRICO", "cantabrico"),
    (r"\bABAR[AÁ]N\b|\bARCHENA\b|\bULEA\b|\bSEGURA\b", "segura"),
]

# Fixed wrong-basin rotation for the placebo: never a basin's own name.
PLACEBO_ROTATION = {
    "duero": "guadalquivir", "ebro": "jucar", "tajo": "ebro",
    "guadiana": "tajo", "guadalquivir": "duero", "jucar": "guadiana",
    "galicia_sil_mino": "segura", "cantabrico": "galicia_sil_mino",
    "segura": "cantabrico",
}


def basin_from_descr(descr: str) -> str | None:
    d = descr.upper()
    for pat, basin in BASIN_PATTERNS:
        if re.search(pat, d):
            return basin
    return None


def hydro_units_with_basin() -> pd.DataFrame:
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet",
                       columns=["unit", "country", "tech", "descr"]).to_pandas()
    hy = ua[(ua.country == "ES") & (ua.tech == "hydro_ugh")].copy()
    hy["basin"] = hy.descr.map(basin_from_descr)
    return hy


def rain_anomaly() -> pd.DataFrame:
    """90-day trailing precipitation, minus that basin's own mean 90-day sum
    for the same calendar day-of-year -- deviation from what's normal."""
    p = pd.read_parquet(DATA / "weather/precipitation_basins_daily.parquet")
    p = p.sort_values(["basin", "date"])
    p["trail90"] = (p.groupby("basin").precipitation_sum
                     .transform(lambda s: s.rolling(90, min_periods=60).sum()))
    p["doy"] = p.date.dt.dayofyear
    clim = p.groupby(["basin", "doy"]).trail90.transform("mean")
    p["anomaly"] = p.trail90 - clim
    p["month"] = p.date.dt.to_period("M")
    # Monthly mean anomaly is the unit of variation the offer panel is built at.
    return p.groupby(["basin", "month"], as_index=False).anomaly.mean()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    hy = hydro_units_with_basin()
    mapped = hy.dropna(subset=["basin"])
    print(f"HYDRO STORAGE UNITS AND THEIR BASIN\n")
    print(f"  {len(hy)} hydro_ugh units total, {len(mapped)} basin-identified "
          f"from cab names, {hy.basin.isna().sum()} left unmapped\n")
    print(mapped.basin.value_counts().to_string())

    d = offer_panel(set(mapped.unit))
    d["basin"] = d.unit.map(dict(zip(mapped.unit, mapped.basin)))
    d["placebo_basin"] = d.basin.map(PLACEBO_ROTATION)

    ra = rain_anomaly().set_index(["basin", "month"]).anomaly
    d["own_rain"] = d.set_index(["basin", "month"]).index.map(ra)
    d["placebo_rain"] = d.set_index(["placebo_basin", "month"]).index.map(ra)

    print(f"\n\nPANEL\n")
    print(f"  {d.unit.nunique()} units, {len(d):,} unit-months, "
          f"{d.month.min()} to {d.month.max()}")
    print(f"  own-basin rain anomaly matched: {d.own_rain.notna().sum():,} rows")

    print(f"\ny = level EUR/MWh;  unit + month FE;  SE clustered on unit\n")
    print(f"{'outcome':<26}{'regressor':<14}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    for lbl, col in (("median submitted offer", "offer"),
                     ("MARGINAL ACCEPTED offer", "marginal_accepted")):
        for rlbl, rcol in (("own-basin rain", "own_rain"),
                           ("placebo-basin rain", "placebo_rain")):
            x = d.dropna(subset=[col, rcol]).copy()
            b, se, t, n, k = twfe(x, col, rcol, "unit", "month")
            print(f"{lbl:<26}{rlbl:<14}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")
        print()

    print("Read: own-basin should beat placebo-basin, and the sign should be\n"
          "NEGATIVE -- more rain than usual, lower opportunity cost of water,\n"
          "lower offer. If own and placebo look similar, this is picking up a\n"
          "national or seasonal pattern, not basin-specific water value, and\n"
          "adds nothing the four earlier proxies didn't already have.")

    if args.save:
        p = ROOT / "outputs" / "tables" / "hydro_precip_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
