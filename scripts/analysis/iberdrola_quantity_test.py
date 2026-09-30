#!/usr/bin/env python3
"""Within-day test by quantities: does Iberdrola allocate its water like a price-taker?

    .venv/bin/python scripts/analysis/hydro_schedule_routes.py   # input (hourly energy)
    .venv/bin/python scripts/analysis/own_demand_in_band.py      # input (firm slope)
    .venv/bin/python scripts/build/build_solar_instrument.py     # input (instrument)
    .venv/bin/python scripts/analysis/iberdrola_quantity_test.py

Spec §8.1 of `docs/specs/2026-09-29-water-value-design.md`; step 8 of
`notes/rq-midday-hydro.md`. Iberdrola's auction offers are residuals: most of its
storage hydro reaches its own retail units by bilateral contract (§3.7-3.8), so
the offer curve is not where the water is allocated. The quantities are.

THE BENCHMARK

Take the unit-day's scheduled energy E (bilateral + auction + intraday net, all
routes) as given -- its level is the ACROSS-day margin, not tested here. A
price-taker with a water value constant within the day (A1) puts E into the
day's dearest hours first, each up to turbine capacity q_bar:

    q*_h = clip(E - (capacity already filled in dearer hours), 0, q_bar)

With market power the firm ranks hours by marginal revenue instead,
p_h - beta * X_h, X = net auction position / |RD'| (spec §3). Iberdrola is a net
BUYER (n < 0), so X is mostly negative, and market power moves water towards the
hours where X is most negative -- where extra output lowers the price it pays
most.

TWO TESTS

1. MODEL FIT. For beta on a grid, rank hours by p - beta X, rebuild the
   benchmark, and measure its overlap with the actual allocation,
   sum_h min(q, q*) / E. The beta with the best overlap is where the allocation
   fits. beta = 0 is price-taking; beta = 1 supply-function Nash. Descriptive:
   p and X are both equilibrium outcomes.
2. IV. dev_h = (q_h - q*_h) / q_bar, the deviation from the price-taking
   benchmark, regressed on X instrumented by offered solar; unit-day and
   hour x year-month fixed effects; demand-forecast control; errors clustered on
   date; closed-form Anderson-Rubin sets. Market power predicts a NEGATIVE
   coefficient. **It fails validation** (2026-09-29): EDP's flat-bidding
   cascades come out at -0.31 (AR [-0.42, -0.21]) where price-taking predicts 0.
   The benchmark switches straight between q_lo and q_hi, real plants ramp, and
   on sunny days that ramping leaves output in the midday shoulder, when X is
   low -- a mechanical correlation between the instrument and the deviation.
   Reported, and read only RELATIVE to the validation group.

VALIDATION

EDP's stable cascades (Cavado, Lima, Guadiana, Hidrocantabrico) offer an
identical curve all day (§3.13), so the market dispatches them at one water
value: they should sit close to the benchmark and fit best at beta near 0. If
they do not, the benchmark is wrong, not Iberdrola.

THE BENCHMARK'S LIMITS ARE THE DAY'S OWN

A first version filled each unit to NAMEPLATE capacity in the dearest hours.
It failed its own validation: EDP's stable cascades, which offer one curve all
day, came out strongly "negative" (-0.61 pp per EUR/MWh, AR [-0.82, -0.43]).
They offer only 50-70% of nameplate, so they spread the same energy over more
hours -- including midday, when X is low -- and the deviation picked that up
mechanically. The benchmark now uses the unit-day's EFFECTIVE limits: its own
lowest hourly output q_lo (held in every hour, a minimum flow) and its own
highest q_hi (what was actually available that day). The rest of E goes above
q_lo into the dearest hours, up to q_hi:

    q*_h = q_lo + clip(E - n_hours * q_lo - (headroom filled in dearer hours),
                       0, q_hi - q_lo)

Both limits are day-level, so the unit-day fixed effect still applies. Ramp
limits and cascade coupling remain, so no real plant reaches an overlap of 1;
the tests are about how the deviation co-moves with X, not its size. La Muela (MUEL) is pumped storage cycling daily, where A1
fails by construction, and is reported but kept out of the pooled test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from hydro_within_day_probe import storage_hydro  # noqa: E402
from midday_hydro_iv import ar_closed, ols, tsls  # noqa: E402
from solar_first_stage import demean  # noqa: E402

DATA = ROOT / "data"
ROUTES = ROOT / "outputs/tables/hydro_schedule_routes.parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"   # firm_x.py
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
OUT = ROOT / "outputs/tables/iberdrola_quantity_test.parquet"

IBERDROLA = ["DUER", "EBRA", "JUCA", "SIL", "TAJO", "TAMEGA"]
PUMPED = ["MUEL"]
EDP_STABLE = ["ACAVADO", "ALIMA", "GUADIA", "HCHI"]
BETAS = np.round(np.arange(-1.0, 3.01, 0.25), 2)


def to_hour(period, res):
    return ((period - 1) * res // 60 + 1).astype(int)


def hourly_market() -> pd.DataFrame:
    """Hourly zone prices, offered solar and the demand forecast."""
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "resolution_min", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px["hour"] = to_hour(px.period, px.resolution_min)
    s = pd.read_parquet(SOLAR, columns=["date", "period", "utc_timestamp", "resolution_min",
                                        "z_offered"])
    s["date"] = pd.to_datetime(s.date)
    s["hour"] = to_hour(s.period, s.resolution_min)
    fc = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                         columns=["utc_timestamp", "demand_forecast_mw"])
    fc["ts"] = pd.to_datetime(fc.utc_timestamp, utc=True)
    s["start"] = pd.to_datetime(s.utc_timestamp, utc=True)
    parts = []
    for res, g in s.groupby("resolution_min"):
        m = fc.set_index("ts").demand_forecast_mw.resample(f"{res}min").mean()
        parts.append(pd.Series(m.reindex(pd.DatetimeIndex(g.start)).to_numpy(), index=g.index))
    s["fcst"] = pd.concat(parts)
    a = px.groupby(["date", "hour"])[["price_es", "price_pt"]].mean()
    b = s.groupby(["date", "hour"])[["z_offered", "fcst"]].mean()
    return a.join(b).reset_index()


def firm_x(firm: str) -> pd.DataFrame:
    """Hourly X = exposed net position / |RD'| for one firm (firm_x.py; framework
    spec §2.4), on the firm panel's periods: clean and priced above ZERO_PRICE."""
    d = pd.read_parquet(FIRM_X, columns=["date", "period", "resolution_min", "firm", "net_mw", "X",
                                         "clean", "zero_price"])
    d = d[(d.firm == firm) & d.clean & ~d.zero_price].copy()
    d["date"] = pd.to_datetime(d.date)
    d["hour"] = to_hour(d.period, d.resolution_min)
    return d.groupby(["date", "hour"])[["X", "net_mw"]].mean().reset_index()


def allocate(d: pd.DataFrame, rank: pd.Series, lo: str = "q_lo", hi: str = "q_hi") -> pd.Series:
    """Fill each unit-day's energy E into its hours in descending order of `rank`:
    `lo` in every hour, then the rest up to `hi` in rank order -- the price-taking
    allocation when rank is the price."""
    t = d.assign(r=rank).sort_values(["unit", "date", "r"], ascending=[True, True, False],
                                     kind="stable")
    head = t[hi] - t[lo]
    rest = t.E - t.groupby(["unit", "date"]).q.transform("size") * t[lo]
    filled = head.groupby([t.unit, t.date]).cumsum() - head
    q = t[lo] + np.clip(rest - filled, 0, head)
    return pd.Series(q.to_numpy(), index=t.index).reindex(d.index)


def overlap(d: pd.DataFrame, q_star: pd.Series) -> pd.Series:
    m = np.minimum(d.q, q_star)
    return m.groupby([d.unit, d.date]).sum() / d.groupby(["unit", "date"]).E.first()


def iv_row(d: pd.DataFrame, label: str) -> None:
    cols = ["dev", "X", "z_offered", "fcst"]
    d = d.dropna(subset=cols)
    if len(d) < 500:
        print(f"    {label:32s} too few ({len(d)})")
        return
    d = d.assign(dev=d.dev * 100)   # percentage points of capacity
    w = demean(d, cols, ["ud", "hym"])
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    Y, X, Z, W = (w[c].to_numpy() for c in cols)
    b_fs, se_fs = ols(X, np.column_stack([Z, W]), cl)
    b_ols, _ = ols(Y, np.column_stack([X, W]), cl)
    b, se = tsls(Y, X, Z, W, cl)
    print(f"    {label:32s} n={len(d):>7,}  F {(b_fs[0]/se_fs[0])**2:6.1f}  OLS {b_ols[0]:+.3f}  "
          f"2SLS {b:+.3f} pp per EUR/MWh ({se:.3f})  AR95 {ar_closed(Y, X, Z, W, cl)}")


def build() -> pd.DataFrame:
    cap = storage_hydro().set_index("unit").cap
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "country"])
    country = u.set_index("unit").country
    r = pd.read_parquet(ROUTES, columns=["unit", "date", "hour", "total", "group"])
    units = IBERDROLA + PUMPED + EDP_STABLE
    r = r[r.unit.isin(units) & (r.hour <= 24)].copy()
    r["date"] = pd.to_datetime(r.date)
    r["cap"] = r.unit.map(cap)
    r["q"] = r.total.clip(lower=0).clip(upper=r.cap)
    r["E"] = r.groupby(["unit", "date"]).q.transform("sum")
    r = r[r.E > 0]

    m = hourly_market()
    r = r.merge(m, on=["date", "hour"], how="left")
    r["p"] = np.where(r.unit.map(country).eq("PT"), r.price_pt, r.price_es)
    xs = pd.concat([firm_x("IBERDROLA").assign(group="IBERDROLA"),
                    firm_x("EDP").assign(group="EDP")])
    r = r.merge(xs, on=["date", "hour", "group"], how="left")
    r["zero"] = 0.0
    r["q_lo"] = r.groupby(["unit", "date"]).q.transform("min")
    r["q_hi"] = r.groupby(["unit", "date"]).q.transform("max")
    r["q_star_naive"] = allocate(r, r.p, lo="zero", hi="cap")     # nameplate: kept for the record
    r["q_star"] = allocate(r, r.p)
    r["dev"] = (r.q - r.q_star) / r.cap
    r["ud"] = r.unit + "_" + r.date.dt.strftime("%Y%m%d")
    r["hym"] = r.hour.astype(str) + "_" + r.date.dt.strftime("%Y%m")
    r["era"] = pd.cut(r.date.dt.year, [2017, 2020, 2023, 2026],
                      labels=["2018-2020", "2021-2023", "2024-2026"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    r.to_parquet(OUT, index=False)
    return r


def main() -> int:
    r = build()
    sets = {"IBERDROLA storage (ex La Muela)": IBERDROLA, "La Muela (pumped, A1 fails)": PUMPED,
            "EDP stable cascades (validation)": EDP_STABLE}

    print("1. HOW CLOSE IS THE ALLOCATION TO THE PRICE-TAKING BENCHMARK?")
    print("   overlap = sum_h min(q, q*) / E, mean over unit-days (1 = identical)")
    for col, tag in (("q_star_naive", "nameplate limits (first version, failed validation)"),
                     ("q_star", "the day's own limits")):
        ov = overlap(r, r[col]).rename("overlap").reset_index()
        ov["year"] = ov.date.dt.year
        print(f"  {tag}")
        print(ov.pivot_table(index="unit", columns="year", values="overlap").round(2).to_string())

    print("\n2. MODEL FIT: rank hours by p - beta X; overlap by beta (unit-days with X in every hour)")
    full = r.groupby(["unit", "date"]).X.transform(lambda x: x.notna().all())
    rf = r[full].copy()
    rows = []
    for bta in BETAS:
        ob = overlap(rf, allocate(rf, rf.p - bta * rf.X)).rename("ov").reset_index()
        ob["beta"] = bta
        rows.append(ob)
    ob = pd.concat(rows)
    ob["year"] = ob.date.dt.year
    ob["era"] = pd.cut(ob.year, [2017, 2020, 2023, 2026], labels=["2018-2020", "2021-2023", "2024-2026"])
    for name, us in sets.items():
        g = ob[ob.unit.isin(us)]
        t = g.groupby(["era", "beta"], observed=True).ov.mean().unstack("era")
        best = t.idxmax()
        print(f"  {name}: best-fitting beta by era {best.to_dict()}")
        print("   " + t.loc[[b for b in (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0) if b in t.index]]
              .round(3).T.to_string().replace("\n", "\n   "))

    print("\n3. IV: deviation from the price-taking benchmark (pp of capacity) on X instrumented.")
    print("   Net buyer with market power -> NEGATIVE; price-taking -> 0.")
    for name, us in sets.items():
        print(f"  {name}")
        g = r[r.unit.isin(us)]
        iv_row(g, "pooled")
        for era, e in g.groupby("era", observed=True):
            iv_row(e, str(era))
    print("\n  IBERDROLA by unit, pooled")
    for u, g in r[r.unit.isin(IBERDROLA)].groupby("unit"):
        iv_row(g, u)
    print(f"\n  X coverage (hours with X defined): {r.X.notna().mean():.3f}; "
          f"Iberdrola median X {r[r.unit.isin(IBERDROLA)].X.median():.1f} EUR/MWh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
