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
             does not set its own benchmark. A proxy for the water a unit expects.
H: 30 and 90 days. From 2019 (the shape needs a year of prices).

WITH STORAGE (lam30s, lam90s). A unit whose reservoirs are fuller than usual for the
time of year expects to release more, so its water is worth less. Example: the Duero
basin 10 points fuller than usual, where in other years each point of fill added 0.43
points to Iberdrola's DUER capacity factor in the coming month: cf 0.19 becomes 0.23,
and λ moves from the 81st to the 77th percentile of expected prices.

    cf_s(u, D) = α_m + b × (fill(u, D) − normal fill for D's week of the year)

  fill       Spain: MITECO's weekly stored over capacity, all reservoirs of the unit's
             demarcation(s), for units whose own basin ranked in the top three of 16 in
             `qa/check_hydro_storage_spain.py` (so not JUCA, TEES, VIES). Portugal: SNIRH's
             weekly volume of the unit's own reservoirs over each reservoir's largest
             volume 2018-2026, by river after `build_storage_hours.py`. The latest reading
             on or before D−2, at most 21 days old.
  normal     the mean fill in the same ISO week of the OTHER years.
  α_m, b     per unit, the monthly capacity factor on calendar-month dummies and the fill
             anomaly on the first day of the month, fitted on the OTHER years.
Units without storage keep cf. Iberdrola's TAMEGA has no SNIRH volume; pumped storage
is left unadjusted.

WHAT IT LEAVES OUT. Inflow uncertainty and the option value it gives the water, spill
and minimum-flow rules, the head's dependence on the level, and the reservoir's own
bounds (κ, κ̄ in §2.2). Pumped storage is included but its λ is an arbitrage value:
read it separately. It is a benchmark, not a measurement: under price-taking with
unbiased forwards and the unit's usual release, this is what λ would be.

WRITES outputs/tables/water_value_forward.parquet (unit, date, group, cls, zone, cf,
cf_years, fwd, lam30, lam90, storage, fill, fill_anom, b_fill, cf_s, lam30s, lam90s) and
forward_price_quantiles.parquet (zone, date, H, q, price).
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

# Spain: unit -> MITECO demarcations, the units whose own basin ranked in the top three
ES_BASINS = {
    "DUER": ["Duero"], "TAJO": ["Tajo"], "SIL": ["Miño - Sil"], "EBRA": ["Ebro"],          # Iberdrola
    "EBRFEN": ["Ebro"], "SBEU": ["Miño - Sil", "Galicia Costa"], "GDLQ": ["Guadalquivir"],
    "GDNA": ["Guadiana"], "TERE": ["Cuencas Internas de Cataluña"],                       # Endesa
    "UFMI": ["Miño - Sil"], "UFTA": ["Tajo"], "UFGC": ["Galicia Costa"],                  # Naturgy
    "HCHI": ["Cantábrico Occidental"],                                                    # EDP
}
# Portugal: SNIRH station codes by river, after build_storage_hours.py
LIMA = ["02H/01A", "03G/01A"]                                                 # Alto Lindoso, Touvedo
CAVADO = ["03H/01A", "03I/01A", "03J/01A", "03J/03A", "03J/04A", "04H/01A"]   # Vilarinho ... Caniçada
DOURO = ["07G/01A", "07H/01A", "07I/01A", "07K/01A", "07K/02A", "07M/02A", "07O/02A", "08L/01A"]
MOVHERA = ["05S/01A", "05T/01A", "06M/06A", "06O/09A", "06S/01A"]             # Picote ... Bemposta
MONDEGO = ["10M/01A", "11H/01A", "12H/01A"]                                   # Caldeirão, Aguieira, Raiva
TEJO = ["13J/01A", "14H/01A", "14I/01A", "16H/01A", "16K/01A", "16K/02A", "17J/01A"]
# (unit, stations, first day, last day): from 2024-03 ~1,000 MW moved from ACAVADO to ALIMA
PT_SPELLS = [
    ("ALIMA", LIMA, "2018-01-01", "2024-02-29"), ("ALIMA", LIMA + CAVADO, "2024-03-01", END),
    ("ACAVADO", CAVADO, "2018-01-01", "2024-02-29"), ("ACAVADO", LIMA + CAVADO, "2024-03-01", END),
    ("ADOURO", DOURO + MOVHERA, "2018-01-01", "2021-12-31"), ("ADOURO", DOURO, "2022-01-01", END),
    ("DOUSUP", MOVHERA, "2022-01-01", END),
    ("GUADIA", ["24M/07A"], "2018-01-01", END),                                # Alqueva
    ("TEMON", TEJO, "2018-01-01", END), ("MONDEGO", MONDEGO, "2018-01-01", END),
]
KNOWN_LAG = 2      # a reading is used from two days after its date
STALE = 21         # days after which a reading is no longer used


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


def known(obs: pd.Series, days: pd.DatetimeIndex) -> np.ndarray:
    """Each day's latest reading on or before D − KNOWN_LAG, if at most STALE days old."""
    o = obs.dropna().sort_index()
    o.index = o.index.astype("datetime64[ns]")
    q = pd.DataFrame({"t": (days - pd.Timedelta(days=KNOWN_LAG)).astype("datetime64[ns]")})
    r = pd.merge_asof(q, o.rename("v").rename_axis("t").reset_index(), on="t",
                      direction="backward", tolerance=pd.Timedelta(days=STALE))
    return r.v.to_numpy()


def storage_fill(days: pd.DatetimeIndex) -> pd.DataFrame:
    """unit, date, storage, fill: the share of the unit's reservoirs full, as known for D."""
    out = []
    m = pd.read_parquet(DATA / "miteco/embalses_historico.parquet")
    m = m[(m.date >= days[0] - pd.Timedelta(days=60)) & m.stored_hm3.notna() & m.capacity_hm3.notna()]
    for unit, basins in ES_BASINS.items():
        g = m[m.ambito.isin(basins)].groupby("date")[["stored_hm3", "capacity_hm3"]].sum()
        out.append(pd.DataFrame({"unit": unit, "date": days, "storage": "miteco",
                                 "fill": known(g.stored_hm3 / g.capacity_hm3, days)}))
    s = pd.read_parquet(DATA / "snirh/snirh_reservoir_series.parquet",
                        columns=["station_code", "parameter", "date", "value", "suspect"])
    s = s[(s.parameter == "volume_dam3") & ~s.suspect.fillna(False).astype(bool)]
    s["date"] = pd.to_datetime(s.date)
    vol = {c: g.groupby("date").value.last() for c, g in s.groupby("station_code")}
    for unit, stations, first, last in PT_SPELLS:
        dd = days[(days >= first) & (days <= last)]
        v = np.column_stack([known(vol[c], dd) for c in stations])
        vmax = np.array([vol[c].max() for c in stations])
        have = np.isfinite(v)
        fill = np.where(have, v, 0).sum(axis=1) / np.where(have, vmax, 0).sum(axis=1).clip(min=1e-9)
        out.append(pd.DataFrame({"unit": unit, "date": dd, "storage": "snirh",
                                 "fill": np.where(have.any(axis=1), fill, np.nan)}))
    f = pd.concat(out, ignore_index=True)
    # the fill anomaly: against the same ISO week of the other years
    f["year"], f["woy"] = f.date.dt.year, f.date.dt.isocalendar().week.clip(upper=52).astype(int)
    tot = f.groupby(["unit", "woy"]).fill.agg(["sum", "count"])
    own = f.groupby(["unit", "woy", "year"]).fill.agg(["sum", "count"])
    j = f.join(tot, on=["unit", "woy"]).join(own, on=["unit", "woy", "year"], rsuffix="_own")
    f["fill_anom"] = f.fill - (j["sum"] - j.sum_own) / (j["count"] - j.count_own).where(lambda n: n > 0)
    return f.drop(columns=["woy"])


def storage_cf(fill: pd.DataFrame, cf_raw: pd.DataFrame) -> pd.DataFrame:
    """unit, year, month, alpha, b_fill: the monthly capacity factor on month dummies and the
    fill anomaly on the month's first day, fitted per unit on the other years."""
    a = fill[fill.date.dt.day == 1].assign(month=lambda x: x.date.dt.month)[["unit", "year", "month", "fill_anom"]]
    p = cf_raw.merge(a, on=["unit", "year", "month"]).dropna()
    rows = []
    for (unit, Y), _ in p.groupby(["unit", "year"]).size().items():
        o = p[(p.unit == unit) & (p.year != Y)]
        if Y < 2019 or len(o) < 36:
            continue
        mc, ma = o.groupby("month").cf.transform("mean"), o.groupby("month").fill_anom.transform("mean")
        x, y = o.fill_anom - ma, o.cf - mc
        b = (x @ y) / (x @ x)
        alpha = o.groupby("month").cf.mean() - b * o.groupby("month").fill_anom.mean()
        rows += [{"unit": unit, "year": Y, "month": mo, "alpha": al, "b_fill": b} for mo, al in alpha.items()]
    return pd.DataFrame(rows)


def lam(d: pd.DataFrame, cf: str, piv: pd.DataFrame) -> np.ndarray:
    """λ at the 1 − cf percentile of the zone-day's expected prices."""
    rows = piv.reindex(pd.MultiIndex.from_arrays([d.zone, d.date])).to_numpy()
    target = np.clip(1 - d[cf].to_numpy(), Q[0], Q[-1])
    return np.array([np.interp(t, Q, r) if np.isfinite(r).all() and np.isfinite(t) else np.nan
                     for t, r in zip(target, rows)])


def main() -> int:
    qs = pd.concat([quantiles(z) for z in ("ES", "PT")], ignore_index=True)
    qs.to_parquet(OUT_Q, index=False)
    print(f"expected-price percentiles: {qs.groupby(['zone', 'H']).date.nunique().to_dict()} days")
    u = hydro_units()
    cf_raw = capacity_factors(u.unit.tolist())
    cf = leave_year_out(cf_raw)
    print(f"hydro units {len(u)} ({u.cls.value_counts().to_dict()}); with a leave-year-out cf: {cf.unit.nunique()}")
    fill = storage_fill(pd.date_range("2018-01-01", END, freq="D"))
    fit = storage_cf(fill, cf_raw)
    days = pd.DataFrame({"date": pd.date_range(START, END, freq="D")})
    d = u.merge(days, how="cross")
    d["year"], d["month"] = d.date.dt.year, d.date.dt.month
    d = d.merge(cf, on=["unit", "year", "month"], how="inner")
    d = d.merge(fill.drop(columns="year"), on=["unit", "date"], how="left")
    d = d.merge(fit, on=["unit", "year", "month"], how="left")
    d.loc[d.cls != "hydro", ["fill_anom", "alpha", "b_fill"]] = np.nan
    d["cf_s"] = (d.alpha + d.b_fill * d.fill_anom).clip(0.01, 0.99)
    d["cf_s"] = d.cf_s.fillna(d.cf)
    d["storage"] = np.where(d.alpha.notna() & d.fill_anom.notna(), d.storage, "none")
    for H in HORIZONS:
        piv = qs[qs.H == H].pivot_table(index=["zone", "date"], columns="q", values="price")
        d[f"lam{H}"] = lam(d, "cf", piv)
        d[f"lam{H}s"] = lam(d, "cf_s", piv)
    fw = qs[qs.H == HORIZONS[0]].drop_duplicates(["zone", "date"]).set_index(["zone", "date"]).fwd
    d["fwd"] = fw.reindex(pd.MultiIndex.from_arrays([d.zone, d.date])).to_numpy()
    d = d.drop(columns=["year", "month", "alpha"])
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(d):,} unit-days, {d.unit.nunique()} units; "
          f"λ30 defined on {d.lam30.notna().mean():.3f}; storage {d.storage.value_counts().to_dict()}")
    print(d.groupby(d.date.dt.year)[["fwd", "lam30", "lam90", "lam30s", "cf", "cf_s"]].median().round(2).to_string())
    check_storage(d, cf_raw, cf)
    return 0


def check_storage(d: pd.DataFrame, cf_raw: pd.DataFrame, cf: pd.DataFrame) -> None:
    """Out of sample: does cf_s on the month's first day predict the month's capacity factor
    better than cf? Per storage unit, root mean squared error of both."""
    first = d[(d.date.dt.day == 1) & (d.storage != "none")][["unit", "date", "storage", "b_fill", "cf_s", "cf"]]
    first = first.assign(year=first.date.dt.year, month=first.date.dt.month)
    e = first.merge(cf_raw.rename(columns={"cf": "real"}), on=["unit", "year", "month"])
    g = e.groupby(["storage", "unit"]).apply(lambda x: pd.Series({
        "months": len(x), "b_fill": x.b_fill.median(),
        "rmse_cf": np.sqrt(((x.real - x.cf) ** 2).mean()), "rmse_cf_s": np.sqrt(((x.real - x.cf_s) ** 2).mean())}),
        include_groups=False)
    g["gain"] = 1 - g.rmse_cf_s / g.rmse_cf
    print("\nstorage: the month's capacity factor predicted on its first day, out of sample")
    print(g.round(3).to_string())
    print(f"error falls for {(g.gain > 0).sum()} of {len(g)} units; median fall {g.gain.median():.1%}")


if __name__ == "__main__":
    raise SystemExit(main())
