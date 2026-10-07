#!/usr/bin/env python3
"""A competitive water value for every storage hydro unit, from forward prices.

    .venv/bin/python scripts/fetch/fetch_omip_forwards.py      # input: OMIP forward curves
    .venv/bin/python scripts/analysis/step_curves.py           # input: hydro units (hydro_YYYYMM)
    .venv/bin/python scripts/build/build_water_value_forward.py

The cost of a storage unit's marginal MWh is what the water would earn if kept: its
water value λ (framework spec §2.2). Nothing records it. This builds the value a
PRICE-TAKER would put on the water, from what was known when offers close, so that the
offered water value can be compared with it (leg B) and so that the at-cost instrument
of `step_estimator.py` §7 can run on hydro.

THE IDEA, WITH AN EXAMPLE. A reservoir whose turbines can run 25% of the hours of the
coming month, on the water it expects to have, does best by running in the month's
dearest quarter of hours. A price-taker therefore offers its water at the price that
only a quarter of the month's hours exceed: λ = the 75th percentile of the prices it
expects. If forwards say the month averages €60 and last year's same month had its
dearest quarter of hours above 1.25 × the month's mean, λ ≈ €75.

    λ*(u, D, H) = Q_{1 − cf(u, m)} of the prices expected over the H days from D

BUILT FROM, all known at noon on D−1, when day-ahead offers close:
  forwards   OMIP's Spanish settlement on the last trade date on or before D−2 (D−1's
             settles after the close). Each future day takes the finest contract
             covering it: day, weekend, week, month, quarter, year. Portugal's curve has
             settlements on 6% as many contract-days, and the zones share one price in
             93% of hours, so Portuguese units use the Spanish curve with their own shape.
  shape      the distribution of hourly price over its month's mean in the same calendar
             month a year earlier (OMIP trades base load only), as 99 percentiles.
  expected   for each day D' in [D, D + H): forward(D') × those 99 percentiles; pooled
  prices     over the H days with equal weight.
  cf         the unit's capacity factor in that calendar month in the OTHER years
             (scheduled output in PDBF over `cab` max power), so a year's own withholding
             does not set its own benchmark. A proxy for the water a unit expects; inflow
             and storage are not modelled yet.
H: 30 and 90 days. From 2019 (the shape needs a year of prices).

WHAT IT LEAVES OUT. Inflow uncertainty and the option value it gives the water, spill
and minimum-flow rules, the head's dependence on the level, and the reservoir's own
bounds (κ, κ̄ in §2.2). Pumped storage is included but its λ is an arbitrage value:
read it separately. It is a benchmark, not a measurement: under price-taking with
unbiased forwards and the unit's usual release, this is what λ would be.

WRITES outputs/tables/water_value_forward.parquet (unit, date, group, cls, zone, cf,
cf_years, fwd, lam30, lam90) and forward_price_quantiles.parquet (zone, date, H, q, price).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
OUT = TABLES / "water_value_forward.parquet"
OUT_Q = TABLES / "forward_price_quantiles.parquet"
START, END = "2019-01-01", "2026-05-31"
HORIZONS = (30, 90)
Q = np.arange(1, 100) / 100                    # percentiles of the expected price distribution
FINEST = {"Day": 0, "Weekend": 1, "Week": 2, "Month": 3, "Quarter": 4, "Year": 5}
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def delivery(contract: str, maturity: str) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """First and last delivery day of an OMIP base-load contract."""
    if maturity in ("Day", "Weekend"):
        m = re.search(r"(\d{2})([A-Z][a-z]{2})-(\d{2})$", contract)
        d = pd.Timestamp(2000 + int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        return d, d + pd.Timedelta(days=1 if maturity == "Weekend" else 0)
    if maturity == "Week":
        m = re.match(r"Wk(\d{2})-(\d{2})$", contract)
        d = pd.Timestamp.fromisocalendar(2000 + int(m.group(2)), int(m.group(1)), 1)
        return d, d + pd.Timedelta(days=6)
    if maturity == "Month":
        m = re.match(r"M ([A-Z][a-z]{2})-(\d{2})$", contract)
        d = pd.Timestamp(2000 + int(m.group(2)), MONTHS[m.group(1)], 1)
        return d, d + pd.offsets.MonthEnd(0)
    if maturity == "Quarter":
        m = re.match(r"Q(\d)-(\d{2})$", contract)
        d = pd.Timestamp(2000 + int(m.group(2)), 3 * int(m.group(1)) - 2, 1)
        return d, d + pd.offsets.QuarterEnd(0)
    if maturity == "Year":
        m = re.match(r"YR-(\d{2})$", contract)
        d = pd.Timestamp(2000 + int(m.group(1)), 1, 1)
        return d, pd.Timestamp(d.year, 12, 31)
    return None


def forward_days(zone: str, hmax: int) -> pd.DataFrame:
    """trade_date, day, fwd: each trade date's price for each delivery day up to hmax + 2
    days ahead, from the finest contract covering it."""
    f = pd.concat([pd.read_parquet(p, columns=["trade_date", "maturity", "contract", "price_ref_eur_mwh"])
                   for p in sorted((DATA / "omip/parquet").glob(f"omip_forwards_{zone}_*.parquet"))])
    f = f[f.maturity.isin(list(FINEST)) & f.price_ref_eur_mwh.notna()].reset_index(drop=True)
    span = {c: delivery(c, m) for c, m in f[["contract", "maturity"]].drop_duplicates().itertuples(index=False)}
    f["d0"] = f.contract.map(lambda c: span[c][0])
    f["d1"] = f.contract.map(lambda c: span[c][1])
    f["trade_date"] = pd.to_datetime(f.trade_date)
    f["rank"] = f.maturity.map(FINEST)
    lo = f.trade_date + pd.Timedelta(days=1)
    hi = f.trade_date + pd.Timedelta(days=hmax + 2)
    f["d0"] = f.d0.where(f.d0 > lo, lo)
    f["d1"] = f.d1.where(f.d1 < hi, hi)
    f = f[f.d1 >= f.d0]
    n = (f.d1 - f.d0).dt.days.to_numpy() + 1
    rows = f.loc[f.index.repeat(n)].reset_index(drop=True)
    rows["day"] = rows.d0 + pd.to_timedelta(np.concatenate([np.arange(k) for k in n]), unit="D")
    rows = rows.sort_values(["trade_date", "day", "rank"]).drop_duplicates(["trade_date", "day"])
    return rows[["trade_date", "day", "price_ref_eur_mwh"]].rename(columns={"price_ref_eur_mwh": "fwd"})


def shapes(zone: str) -> pd.DataFrame:
    """(ym, 99 percentiles of hourly price / month mean) of the same calendar month a year
    earlier, keyed by the delivery month ym."""
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet")
    col = "price_es" if zone == "ES" else "price_pt"
    p["utc"] = pd.to_datetime(p.utc_timestamp, utc=True).dt.floor("h")
    h = p.groupby("utc")[col].mean()
    loc = h.index.tz_convert("Europe/Madrid")
    ym = pd.PeriodIndex(loc, freq="M")
    r = h / h.groupby(ym).transform("mean")
    out = r.groupby(ym).apply(lambda x: pd.Series(np.quantile(x.to_numpy(), Q)))
    out = out.unstack()
    out.index = out.index + 12                   # used for the same month next year
    return out


def quantiles(zone: str) -> pd.DataFrame:
    """zone, date, H, q, price: percentiles of the prices expected over [D, D + H)."""
    fd = forward_days("ES", max(HORIZONS))      # PT's curve is thin: 6% of ES's contract-days
    sh = shapes(zone)
    trade = np.sort(fd.trade_date.unique())
    by_trade = {t: g.set_index("day").fwd for t, g in fd.groupby("trade_date")}
    out = []
    for D in pd.date_range(START, END, freq="D"):
        i = np.searchsorted(trade, np.datetime64(D - pd.Timedelta(days=2)), side="right") - 1
        if i < 0:
            continue
        t = trade[i]
        f = by_trade[pd.Timestamp(t)]
        for H in HORIZONS:
            days = pd.date_range(D, periods=H, freq="D")
            fw = f.reindex(days)
            if fw.isna().mean() > 0.1:
                continue
            fw = fw.ffill().bfill()
            per = pd.PeriodIndex(days, freq="M")
            if not set(per).issubset(sh.index):
                continue
            vals = (fw.to_numpy()[:, None] * sh.loc[per].to_numpy()).ravel()
            out.append(pd.DataFrame({"zone": zone, "date": D, "H": H, "q": Q, "price": np.quantile(vals, Q),
                                     "fwd": f.get(D, np.nan), "trade_date": t}))
    return pd.concat(out, ignore_index=True)


def hydro_units() -> pd.DataFrame:
    """unit, group, cls, zone: storage and pumped hydro units of the step caches."""
    h = pd.concat([pd.read_parquet(p, columns=["unit", "group", "cls"])
                   for p in sorted(CACHE.glob("hydro_2*.parquet"))]).dropna(subset=["unit"])
    h = h.drop_duplicates("unit", keep="last")
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "country"])
    h = h.merge(reg, on="unit", how="left")
    h["zone"] = np.where(h.country == "PT", "PT", "ES")
    return h[["unit", "group", "cls", "zone"]]


def capacity_factors(units: list[str]) -> pd.DataFrame:
    """unit, year, month, cf: scheduled output (PDBF, positive rows) over max power."""
    parts = []
    for f in sorted((DATA / "omie/pdbf/parquet").glob("pdbf_*.parquet")):
        p = pd.read_parquet(f, columns=["date", "unit", "schedule_mw", "resolution_min"],
                            filters=[("unit", "in", units)])
        if p.empty:
            continue
        p = p[p.schedule_mw > 0]
        p["mwh"] = p.schedule_mw * p.resolution_min / 60
        p["date"] = pd.to_datetime(p.date)
        parts.append(p.groupby(["unit", p.date.dt.year.rename("year"), p.date.dt.month.rename("month")]).mwh.sum())
    e = pd.concat(parts).groupby(level=[0, 1, 2]).sum().rename("mwh").reset_index()
    cap = []
    for f in sorted((DATA / "omie/cab/parquet").glob("cab_*.parquet")):
        c = pd.read_parquet(f, columns=["date", "unit", "max_power_mw"], filters=[("unit", "in", units)])
        if c.empty:
            continue
        c["date"] = pd.to_datetime(c.date)
        cap.append(c.groupby(["unit", c.date.dt.year.rename("year"), c.date.dt.month.rename("month")])
                   .max_power_mw.max())
    k = pd.concat(cap).groupby(level=[0, 1, 2]).max().rename("cap").reset_index()
    e = e.merge(k, on=["unit", "year", "month"], how="inner")
    hours = pd.to_datetime(dict(year=e.year, month=e.month, day=1)).dt.days_in_month * 24
    e["cf"] = (e.mwh / (e.cap * hours)).clip(0, 1)
    return e[["unit", "year", "month", "cf"]]


def leave_year_out(cf: pd.DataFrame) -> pd.DataFrame:
    """unit, year, month, cf, cf_years: the mean over the same calendar month of the other years."""
    g = cf.groupby(["unit", "month"]).cf.agg(["sum", "count"]).reset_index()
    full = cf[["unit", "month"]].drop_duplicates().merge(pd.DataFrame({"year": range(2019, 2027)}), how="cross")
    full = full.merge(g, on=["unit", "month"]).merge(cf.rename(columns={"cf": "own"}),
                                                     on=["unit", "year", "month"], how="left")
    own = full.own.fillna(0.0)
    n = full["count"] - full.own.notna()
    full["cf"] = (full["sum"] - own) / n.where(n > 0)
    full["cf_years"] = n
    return full[full.cf_years >= 2][["unit", "year", "month", "cf", "cf_years"]]


def main() -> int:
    qs = pd.concat([quantiles(z) for z in ("ES", "PT")], ignore_index=True)
    qs.to_parquet(OUT_Q, index=False)
    print(f"expected-price percentiles: {qs.groupby(['zone', 'H']).date.nunique().to_dict()} days")
    u = hydro_units()
    cf = leave_year_out(capacity_factors(u.unit.tolist()))
    print(f"hydro units {len(u)} ({u.cls.value_counts().to_dict()}); with a leave-year-out cf: {cf.unit.nunique()}")
    days = pd.DataFrame({"date": pd.date_range(START, END, freq="D")})
    d = u.merge(days, how="cross")
    d["year"], d["month"] = d.date.dt.year, d.date.dt.month
    d = d.merge(cf, on=["unit", "year", "month"], how="inner")
    for H in HORIZONS:
        g = qs[qs.H == H]
        piv = g.pivot_table(index=["zone", "date"], columns="q", values="price")
        key = pd.MultiIndex.from_arrays([d.zone, d.date])
        rows = piv.reindex(key).to_numpy()
        target = np.clip(1 - d.cf.to_numpy(), Q[0], Q[-1])
        d[f"lam{H}"] = [np.interp(t, Q, r) if np.isfinite(r).all() else np.nan for t, r in zip(target, rows)]
    fw = qs[qs.H == HORIZONS[0]].drop_duplicates(["zone", "date"]).set_index(["zone", "date"]).fwd
    d["fwd"] = fw.reindex(pd.MultiIndex.from_arrays([d.zone, d.date])).to_numpy()
    d = d.drop(columns=["year", "month"])
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(d):,} unit-days, {d.unit.nunique()} units; "
          f"λ30 defined on {d.lam30.notna().mean():.3f}")
    print(d.groupby(d.date.dt.year)[["fwd", "lam30", "lam90", "cf"]].median().round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
