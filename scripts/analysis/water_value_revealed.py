#!/usr/bin/env python3
"""The revealed water value per unit-day, and what moves it (M2 and M3, rebuilt).

    .venv/bin/python scripts/analysis/water_value_revealed.py            # build + report
    .venv/bin/python scripts/analysis/water_value_revealed.py --report   # report only

Step 4 of `docs/specs/2026-09-29-water-value-design.md` §9. The first M3
(`hydro_water_value_structural.py`) recovered lambda from the first-order
condition in the periods where a hydro unit set the price. It is invalid on
three counts: it subtracts contracts twice (q - theta), it uses the market's
slope rather than the firm's, and it keeps only price-setting periods, which
selects on the shock (`notes/rq-midday-hydro.md` §3.11).

THE MEASURE -- every unit-day, no conditioning on price-setting

    lambda_k(u, d) = the k-th quantile (k = 25, 50, 75) of unit u's offered sell
                     prices on day d, volume-weighted over all the day's periods

the same reference prices as `edp_quantity_at_price.py`. On a flat day this IS
the offer curve, and under A1 and price-taking within the day the offer curve is
the water-value curve of the cascade's plants (spec §3). No tranche needs to be
the same across hours (A2), because the quantile is taken over the whole day.

Within-day markups are subtracted as a bound, not assumed away: under the §2 FOC
the offer is lambda + beta * X, so `lambda50_adj = lambda50 - BETA_HI * mean X`,
with BETA_HI = 0.12 the largest implied beta in §3.14. The day-level markup --
the across-day margin -- stays in lambda: this measures the water value AS
OFFERED, which is what the across-day question will have to decompose.

Offers at or above PRICE_OUT are water withheld from the day, not a price for
it. A quantile landing there is censored and is dropped from the regressions,
with its share reported.

WHAT MOVES IT

A price-taking storage unit's water value is the expected price of the hours in
which the water will be used (spec §2), so it should track the forward price.
Regressed per group, unit x calendar-month fixed effects (seasonality differs by
cascade), errors clustered by year-month:

    lambda50(u, d) = a(u, month) + b * forward(d-1) [+ c * gas(d-1)] [+ f * fill(d-1)] + e

* forward -- OMIP Spanish front-MONTH baseload, settlement of the last trading
  day before d. OMIP publishes only daily contracts for Portugal, and the zones
  split in 6.7% of periods, so the Spanish curve is used for all units.
* gas -- MIBGAS Spanish day-ahead index, last value before d. Collinear with the
  forward; reported separately and together.
* fill -- MITECO reservoir fill of the SPANISH basin the cascade sits in or below,
  as a deviation from that basin's week-of-year mean, last bulletin before d.
  For the Portuguese cascades it proxies upstream inflow conditions, not their
  own storage (Portugal's reservoir data is geo-blocked; spec §6 M4). Cavado and
  Mondego lie wholly in Portugal and get none.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from edp_quantity_at_price import RESHAPING, STABLE, weighted_quantile  # noqa: E402
from hydro_water_value_reservoir import AMBITO_TO_BASIN  # noqa: E402
from solar_first_stage import cluster_ols, demean  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/edp_hydro_panel.parquet"
OUT = ROOT / "outputs/tables/water_value_revealed.parquet"

PRICE_OUT = 300.0   # EUR/MWh, as in edp_hydro_panel.py
BETA_HI = 0.12      # largest implied within-day beta, notes/rq-midday-hydro.md §3.14
QS = (0.25, 0.50, 0.75)
GROUPS = {
    "EDP stable (identical curve all day)": STABLE,
    "EDP reshaping (A2 fails)": RESHAPING,
    "Movhera (Douro Internacional)": ["DOUSUP"],
    "Repsol (Viesgo)": ["VIES"],
}
# The Spanish basin each cascade sits in, or below. Cavado and Mondego: none.
BASIN_OF = {
    "ADOURO": "duero", "DOUSUP": "duero",       # the Douro rises in Spain as the Duero
    "TEMON": "tajo",                            # Tejo = Tajo
    "GUADIA": "guadiana",
    "ALIMA": "galicia_sil_mino",                # the Lima rises in Ourense as the Limia
    "HCHI": "cantabrico", "VIES": "cantabrico",  # Asturian and Cantabrian rivers
}


def unit_days(ym: str, units: list[str]) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh", "resolution_min"],
                      filters=[("unit", "in", units), ("side", "==", "V")]).to_pandas()
    if b.empty:
        return pd.DataFrame()
    b["date"] = pd.to_datetime(b.date)
    b["mwh"] = b.power_mw * b.resolution_min / 60
    o = b[b.status == "O"]
    rows = []
    for (u, d), g in o.groupby(["unit", "date"]):
        p, w = g.price_eur_mwh.to_numpy(), g.mwh.to_numpy()
        if w.sum() <= 0:
            continue
        r = {"unit": u, "date": d, "offered_mwh": w.sum(),
             "priced_out_share": w[p >= PRICE_OUT].sum() / w.sum()}
        for q in QS:
            r[f"lambda{int(q * 100)}"] = weighted_quantile(p, w, q)
        rows.append(r)
    out = pd.DataFrame(rows)
    c = b[b.status == "C"].groupby(["unit", "date"]).mwh.sum().rename("cleared_mwh")
    return out.merge(c.reset_index(), on=["unit", "date"], how="left").fillna({"cleared_mwh": 0.0})


def forward_front_month() -> pd.Series:
    """OMIP ES front-month baseload by trade date."""
    files = sorted((DATA / "omip/parquet").glob("omip_forwards_ES_*.parquet"))
    q = pd.concat([pq.read_table(f, columns=["trade_date", "maturity", "contract",
                                              "price_ref_eur_mwh", "price_ref_prev_eur_mwh"])
                   .to_pandas() for f in files], ignore_index=True)
    q = q[q.maturity == "Month"].copy()
    q["trade_date"] = pd.to_datetime(q.trade_date)
    q["price"] = q.price_ref_eur_mwh.fillna(q.price_ref_prev_eur_mwh)
    q = q.dropna(subset=["price"])
    q["mstart"] = pd.to_datetime("1 " + q.contract.str.slice(2), format="%d %b-%y")
    q = q[q.mstart > q.trade_date]   # delivery not yet started
    front = q.loc[q.groupby("trade_date").mstart.idxmin()]
    return front.set_index("trade_date").price.sort_index().rename("forward")


def gas_daily() -> pd.Series:
    g = pd.read_parquet(DATA / "mibgas/mibgas_price_index_daily.parquet",
                        columns=["date", "mibgas_es_eur_mwh"]).dropna()
    g["date"] = pd.to_datetime(g.date)
    return g.set_index("date").mibgas_es_eur_mwh.sort_index().rename("gas")


def fill_weekly() -> pd.DataFrame:
    """Basin fill ratio minus the basin's week-of-year mean, per weekly bulletin."""
    r = pq.read_table(DATA / "miteco/embalses_historico.parquet",
                      columns=["date", "ambito", "capacity_hm3", "stored_hm3"]).to_pandas()
    r["basin"] = r.ambito.map(AMBITO_TO_BASIN)
    r = r.dropna(subset=["basin", "capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]
    w = (r.groupby(["basin", "date"]).agg(stored=("stored_hm3", "sum"), cap=("capacity_hm3", "sum"))
         .reset_index())
    w["date"] = pd.to_datetime(w.date)
    w = w[w.date >= "2010-01-01"]
    w["fill"] = w.stored / w.cap
    wk = w.date.dt.isocalendar().week.astype(int)
    w["fill_anom"] = w.fill - w.groupby([w.basin, wk]).fill.transform("mean")
    return w[["basin", "date", "fill", "fill_anom"]]


def last_before(days: pd.Series, s: pd.Series) -> np.ndarray:
    """Value of series s on the last date strictly before each day."""
    idx = s.index.searchsorted(days.to_numpy(), side="left") - 1
    v = np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan)
    return v


def build() -> pd.DataFrame:
    units = sorted({u for us in GROUPS.values() for u in us})
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    parts = []
    for ym in months:
        parts.append(unit_days(ym, units))
        print(f"  {ym}", flush=True, file=sys.stderr)
    d = pd.concat([p for p in parts if not p.empty], ignore_index=True)

    # Day-mean markup term and zone price, from the offer panel.
    p = pd.read_parquet(PANEL, columns=["unit", "date", "X", "p_zone"])
    p["date"] = pd.to_datetime(p.date)
    day = p.groupby(["unit", "date"]).agg(X_mean=("X", "mean"), p_zone=("p_zone", "mean")).reset_index()
    d = d.merge(day, on=["unit", "date"], how="left")

    d["forward"] = last_before(d.date, forward_front_month())
    d["gas"] = last_before(d.date, gas_daily())
    d["basin"] = d.unit.map(BASIN_OF)
    fw = fill_weekly()
    d["fill_anom"] = np.nan
    for b, g in fw.groupby("basin"):
        s = g.set_index("date").fill_anom.sort_index()
        m = d.basin == b
        d.loc[m, "fill_anom"] = last_before(d.loc[m, "date"], s)
    d["group"] = d.unit.map({u: k for k, us in GROUPS.items() for u in us})
    d["lambda50_adj"] = d.lambda50 - BETA_HI * d.X_mean
    d["year"] = d.date.dt.year
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-days)")
    return d


def fe_ols(d: pd.DataFrame, y: str, xs: list[str]) -> tuple[np.ndarray, np.ndarray, int, int]:
    d = d.dropna(subset=[y] + xs)
    d = d.assign(um=d.unit + "_" + d.date.dt.month.astype(str))
    w = demean(d, [y] + xs, ["um"])
    cl = (d.date.dt.year * 100 + d.date.dt.month).to_numpy()
    b, V = cluster_ols(w[y].to_numpy(), w[xs].to_numpy(), cl)
    return b, np.sqrt(np.diag(V)), len(d), len(np.unique(cl))


def fmt(b: float, se: float) -> str:
    return f"{b:+.3f} ({se:.3f})"


def report(d: pd.DataFrame) -> None:
    d = d.copy()
    for q in QS:
        k = f"lambda{int(q * 100)}"
        d.loc[d[k] >= PRICE_OUT, k] = np.nan
    d["lambda50_adj"] = d.lambda50 - BETA_HI * d.X_mean

    print("\nREVEALED WATER VALUE: median over unit-days of lambda50, EUR/MWh "
          "(volume-weighted median offer price)")
    t = d.groupby(["unit", "year"]).lambda50.median().unstack()
    print(t.round(1).to_string())
    print("\n  forward (OMIP ES front month), median by year:")
    print(d.drop_duplicates("date").groupby("year").forward.median().round(1).to_frame().T.to_string())
    print("\n  lambda50 / forward, median by unit and year:")
    print((d.lambda50 / d.forward).groupby([d.unit, d.year]).median().unstack().round(2).to_string())

    raw = pd.read_parquet(OUT, columns=["unit", "lambda25", "lambda50", "lambda75"])
    print("\n  CENSORED (quantile at or above the price-out threshold, water withheld):")
    print(raw.groupby("unit")[["lambda25", "lambda50", "lambda75"]]
          .agg(lambda s: (s >= PRICE_OUT).mean()).round(3).to_string())
    adj = (BETA_HI * d.X_mean).abs()
    print(f"\n  within-day markup bound, |{BETA_HI} x mean X|: median {adj.median():.2f}, "
          f"p90 {adj.quantile(.9):.2f} EUR/MWh (EDP and Repsol unit-days)")

    print("\nWHAT MOVES IT: unit x calendar-month FE, clustered by year-month. "
          "Coefficient (se); price-taking predicts a positive pass-through of the forward.")
    specs = [("forward", ["forward"]), ("gas", ["gas"]), ("both", ["forward", "gas"])]
    for g, gd in d.groupby("group"):
        print(f"\n  {g}")
        for lab, xs in specs:
            b, se, n, nc = fe_ols(gd, "lambda50", xs)
            print(f"    lambda50 on {lab:8s} " + "  ".join(f"{x} {fmt(bb, s)}" for x, bb, s in zip(xs, b, se))
                  + f"   n={n:,}, {nc} clusters")
        for k in ("lambda25", "lambda75", "lambda50_adj"):
            if gd[k].notna().sum() < 100:
                continue
            b, se, n, nc = fe_ols(gd, k, ["forward"])
            print(f"    {k:12s} on forward {fmt(b[0], se[0])}   n={n:,}")
        gf = gd[gd.basin.notna()]
        if len(gf):
            b, se, n, nc = fe_ols(gf, "lambda50", ["forward", "fill_anom"])
            print(f"    lambda50 on forward + fill anomaly (x100 = per pp of fill): "
                  f"forward {fmt(b[0], se[0])}  fill {fmt(b[1] / 100, se[1] / 100)}   n={n:,}")
        for era, (lo, hi) in {"2018-20": (2018, 2020), "2021-23": (2021, 2023),
                              "2024-26": (2024, 2026)}.items():
            e = gd[gd.year.between(lo, hi)]
            if e.lambda50.notna().sum() < 100:
                continue
            b, se, n, nc = fe_ols(e, "lambda50", ["forward"])
            print(f"    {era}: lambda50 on forward {fmt(b[0], se[0])}   n={n:,}, {nc} clusters")


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    d = pd.read_parquet(OUT) if args.report else build()
    report(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
