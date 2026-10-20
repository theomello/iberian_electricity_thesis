#!/usr/bin/env python3
"""The France line's state by hour, and its prediction from French conditions and published capacity.

    .venv/bin/python scripts/build/build_france_link.py

Spec `docs/specs/2026-10-20-france-link-design.md` §3.1–3.2. One row per OMIE (date, period),
2018-01-01 → 2025-09-30 (hourly; the estimation sample's window).

STATE, from OMIE's interconnection file (border FR, after the day-ahead auction): import-full
when no import room is left (free import ≤ 1 MW), export-full when no export room is left,
open otherwise. Free capacity nets the counter-flow, so it is read as published: import
figures are negative there and are turned positive here. Checked against prices: open hours
should have equal Spanish and French prices (Ember), full hours different ones.

PREDICTION, one multinomial logit over the three states (open the reference), each year
predicted from a fit on the other years (`fit_loyo_mn`). Open is the middle state: the line
is full one way when France is clearly cheaper, the other way when it is clearly dearer, and
open when the two are close, so a separate logit per state (the first try, 2026-10-20) missed
it (out-of-sample correlation 0.08). On variables known before offers close and outside the Iberian firms' control:
  cap_imp, cap_exp  the import and export capacity OMIE publishes for the period, GW (set by
                    the operators before the auction; occupation is an outcome, not used)
  fr_load_fc        RTE's D-1 forecast of French demand for the hour, GW
  fr_nuc_lag        French nuclear output, mean of the daily means over D−8 … D−2, GW (a
                    proxy for availability known at the bid)
  month, hour       dummies, additive (the plan's ruling: 36 columns, not 288)
Iberian conditions are left out on purpose (spec §3.2).

SPLIT (note §1.5, `split`): the same model with REE's D-1 Iberian forecasts added gives
p_open_full; holding the French predictors and capacity at their calendar month's mean gives
p_open_ib, the part Iberian conditions give (a control); z_open = p_open_full − p_open_ib is
what France and capacity add (the instrument). From 2019.

Writes outputs/tables/france_link_hours.parquet: date, period, utc, year, month, hour,
cap_imp, cap_exp, free_imp, free_exp (MW), state, price_es, price_fr, gap (ES − FR),
fr_load_fc, fr_nuc_lag (MW), p_open, p_import_full, p_export_full, ib_demand_fc, ib_wind_fc,
ib_solar_fc (MW), p_open_full, p_open_ib, z_open.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs/tables/france_link_hours.parquet"
START, END = pd.Timestamp("2018-01-01"), pd.Timestamp("2025-09-30")
FULL = 1.0                                   # MW of free capacity at or below which a direction is full
STATES = ["open", "import_full", "export_full"]
PREDICTORS = ["cap_imp", "cap_exp", "fr_load_fc", "fr_nuc_lag"]
IBERIAN = ["ib_demand_fc", "ib_wind_fc", "ib_solar_fc"]
ESIOS = {"ib_demand_fc": 1775, "ib_wind_fc": 1777, "ib_solar_fc": 1779}


def fit_loyo_mn(df: pd.DataFrame, y: str, xs: list[str], base: str, year_col: str = "year",
                hold: pd.DataFrame | None = None):
    """Multinomial logit of the category y on xs plus month and hour dummies, `base` the reference
    category; each year predicted from a fit on the others. One column of probabilities per
    category, summing to 1; NaN where a predictor is missing. With `hold` (same index, some of
    xs), also returns the predictions of the same fits with those columns replaced."""
    cats = [base] + sorted(c for c in df[y].dropna().unique() if c != base)
    code = df[y].map({c: i for i, c in enumerate(cats)})
    X = pd.concat([df[xs].astype(float),
                   pd.get_dummies(df["month"], prefix="m", drop_first=True, dtype=float),
                   pd.get_dummies(df["hour"], prefix="h", drop_first=True, dtype=float)], axis=1)
    X.insert(0, "const", 1.0)
    ok = X.notna().all(axis=1) & code.notna()
    out = pd.DataFrame(np.nan, index=df.index, columns=cats)
    held = out.copy()
    Xh = X.copy()
    if hold is not None:
        Xh[list(hold.columns)] = hold.astype(float)
    for yr in sorted(df.loc[ok, year_col].unique()):
        train, test = ok & (df[year_col] != yr), ok & (df[year_col] == yr)
        m = sm.MNLogit(code[train].astype(int), X.loc[train]).fit(disp=0, maxiter=300, method="newton")
        out.loc[test, :] = np.asarray(m.predict(X.loc[test]))
        if hold is not None:
            held.loc[test, :] = np.asarray(m.predict(Xh.loc[test]))
    return out if hold is None else (out, held)


def nuclear_lag() -> pd.Series:
    """Mean of RTE's daily nuclear output over D−8 … D−2, MW, indexed by date."""
    r = pd.read_parquet(DATA / "rte/eco2mix_national.parquet", columns=["utc", "nucleaire"])
    daily = r.groupby(r.utc.dt.tz_convert(None).dt.normalize()).nucleaire.mean()
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"))
    return daily.rolling(7, min_periods=5).mean().shift(2).rename("fr_nuc_lag")


def iberian_forecasts() -> pd.DataFrame:
    """utc and REE's D-1 forecasts of peninsular demand, wind and solar, MW (ESIOS; from 2019)."""
    out = None
    for name, i in ESIOS.items():
        f = pd.read_parquet(DATA / f"esios/esios_{i}.parquet", columns=["value", "utc_timestamp"])
        f = f.assign(utc=pd.to_datetime(f.utc_timestamp, utc=True).dt.floor("h")).groupby("utc").value.mean().rename(name)
        out = f.to_frame() if out is None else out.join(f, how="outer")
    return out.reset_index()


def split(h: pd.DataFrame) -> pd.DataFrame:
    """Note §1.5: the open prediction with French, capacity and Iberian predictors (p_open_full),
    the same fits with the French predictors and capacity held at their calendar month's mean over
    the sample (p_open_ib, a control), and the difference, what France and capacity add (z_open,
    the instrument). From 2019, when REE's forecasts start."""
    xs = PREDICTORS + IBERIAN
    fit = pd.concat([h[["year", "month", "hour"]], h[xs] / 1000.0], axis=1)
    fit["state"] = h.state.where(h[xs].notna().all(axis=1))
    held = fit[PREDICTORS].copy()
    for c in PREDICTORS:
        held[c] = fit.groupby("month")[c].transform("mean")
    P, H = fit_loyo_mn(fit, "state", xs, base="open", hold=held)
    return pd.DataFrame({"p_open_full": P["open"], "p_open_ib": H["open"], "z_open": P["open"] - H["open"]})


def main() -> int:
    ic = pd.read_parquet(DATA / "omie/interconnection/omie_interconnection_capacity.parquet")
    ic = ic[(ic.border == "FR") & (ic.resolution_min == 60)].copy()
    ic["date"] = pd.to_datetime(ic.date)
    ic = ic[(ic.date >= START) & (ic.date <= END)]
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "utc_timestamp", "price_es"])
    px["date"] = pd.to_datetime(px.date)
    h = ic.merge(px, on=["date", "period"], how="inner")
    h["utc"] = pd.to_datetime(h.utc_timestamp, utc=True)
    h["cap_imp"] = -h.import_capacity_mw
    h["cap_exp"] = h.export_capacity_mw
    h["free_imp"] = -h.import_free_mw
    h["free_exp"] = h.export_free_mw
    imp, exp = h.free_imp <= FULL, h.free_exp <= FULL
    net = h.export_occupied_mw + h.import_occupied_mw          # > 0: Spain exports
    h["state"] = np.select([imp & exp & (net < 0), imp & exp, imp, exp], ["import_full", "export_full",
                           "import_full", "export_full"], "open")
    print(f"  {len(h):,} hours; both directions full on {int((imp & exp).sum())} (assigned by flow direction)")

    e = pd.read_parquet(DATA / "ember/ember_prices_hourly.parquet")
    h = h.merge(e[e.country == "FRA"][["utc", "price_eur_mwh"]].rename(columns={"price_eur_mwh": "price_fr"}),
                on="utc", how="left")
    h["gap"] = h.price_es - h.price_fr
    r = pd.read_parquet(DATA / "rte/eco2mix_national.parquet", columns=["utc", "prevision_j1"])
    h = h.merge(r.rename(columns={"prevision_j1": "fr_load_fc"}), on="utc", how="left")
    h = h.merge(nuclear_lag(), left_on="date", right_index=True, how="left")

    loc = h.utc.dt.tz_convert("Europe/Madrid")
    h["year"], h["month"], h["hour"] = h.date.dt.year, h.date.dt.month, loc.dt.hour
    gw = h[PREDICTORS] / 1000.0
    fit = pd.concat([h[["year", "month", "hour"]], gw], axis=1)
    fit["state"] = h.state.where(h[PREDICTORS].notna().all(axis=1))
    P = fit_loyo_mn(fit, "state", PREDICTORS, base="open")
    for s in STATES:
        h[f"p_{s}"] = P[s]
        print(f"  {s}: share {(h.state == s).mean():.3f}; out-of-sample corr "
              f"{h[f'p_{s}'].corr((h.state == s).astype(float)):.3f}")

    h = h.merge(iberian_forecasts(), on="utc", how="left")
    h = pd.concat([h, split(h)], axis=1)
    print(f"  split: open out-of-sample corr {h.p_open_full.corr((h.state == 'open').astype(float)):.3f} "
          f"(with Iberian forecasts), z_open sd {h.z_open.std():.3f}, p_open_ib sd {h.p_open_ib.std():.3f}")

    cols = ["date", "period", "utc", "year", "month", "hour", "cap_imp", "cap_exp", "free_imp", "free_exp", "state",
            "price_es", "price_fr", "gap", "fr_load_fc", "fr_nuc_lag", "p_open", "p_import_full", "p_export_full",
            "ib_demand_fc", "ib_wind_fc", "ib_solar_fc", "p_open_full", "p_open_ib", "z_open"]
    h[cols].to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(h):,} hours, predictors missing on "
          f"{int(h[PREDICTORS].isna().any(axis=1).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
