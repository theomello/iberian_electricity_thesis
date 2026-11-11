"""Hourly within-day check of the pre-cap cogeneration price response (notes/rq-cogeneration.md, check C3).

Gas group and biomass-and-waste group hourly load factor (REE P48, capacity-weighted, as groups_daily) on the hourly day-ahead price
(OMIE, Spain), instrumented with the hourly day-ahead wind forecast (ESIOS 1777). Date effects, hour x month and hour x weekday
effects, clustered by week. Pre-cap days with hourly data on disk (2021-01-01 -> 2022-06-14, DST days out). Shift placebo: price and
instrument from the day k away, k = -10..10 except 0. Writes outputs/tables/cogeneration_hourly*.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response import ROOT, OUT  # noqa: E402


def hourly_groups():
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    d = pd.concat(pd.read_parquet(f) for f in sorted((OUT / "cogeneration_ree" / "hourly").glob("h_*.parquet")))
    d = d[d.unit.isin(u.index)]
    d["fuel"] = d.unit.map(u.fuel)
    d["cap"] = d.unit.map(u.cap)
    d["mw"] = np.minimum(d.p48_mwh.clip(lower=0), d.cap)
    g = d.groupby(["date", "hour", "fuel"]).mw.sum().unstack()
    caps = u.groupby("fuel").cap.sum()
    lf = pd.DataFrame({f"lf_{f}": g[f] / caps[f] for f in ("gas", "biomass_waste")})
    lf = lf.reset_index()
    lf["date"] = pd.to_datetime(lf.date)
    return lf


def hourly_drivers():
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    p = p[p.resolution_min == 60].copy()
    p["date"] = pd.to_datetime(p.date)
    p["hour"] = p.period - 1
    p = p[["date", "hour", "price_es"]].rename(columns={"price_es": "price"}).drop_duplicates(["date", "hour"])
    w = pd.read_parquet(ROOT / "data/esios/esios_1777.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp")
    loc = w.utc_timestamp.dt.tz_convert("Europe/Madrid")
    w = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "wind": w.value.to_numpy() / 1000}).drop_duplicates(["date", "hour"])
    return p.merge(w, on=["date", "hour"], how="inner")


def shifted(dv, k):
    s = dv.copy()
    s["date"] = s.date - pd.Timedelta(days=k)
    return s


def clsum(a, g):
    return pd.DataFrame(a).groupby(g).sum().to_numpy()


def fit(M, y, wk):
    M = M.dropna(subset=[y, "price", "wind"])
    if len(M) < 2000:
        return None
    key = M.date
    W = pd.concat([pd.get_dummies(M.hour.astype(str) + "_" + M.date.dt.month.astype(str), dtype=float),
                   pd.get_dummies(M.hour.astype(str) + "_" + M.date.dt.dayofweek.astype(str), dtype=float)], axis=1).to_numpy()
    out = {}
    for c in (y, "price", "wind"):
        v = M[c] - M.groupby(key)[c].transform("mean")
        out[c] = v.to_numpy()
    Wd = W - pd.DataFrame(W).groupby(key.to_numpy()).transform("mean").to_numpy()
    for c in out:
        out[c] = out[c] - Wd @ np.linalg.lstsq(Wd, out[c], rcond=None)[0]
    yy, p, z = out[y], out["price"], out["wind"]
    g = wk.loc[M.index].to_numpy()
    pi = (z @ p) / (z @ z)
    ph = pi * z
    b = (ph @ yy) / (ph @ p)
    e = yy - b * p
    se = np.sqrt((clsum(ph * e, g) ** 2).sum()) / (ph @ p)
    u = p - ph
    Fst = pi ** 2 * (z @ z) ** 2 / (clsum(z * u, g) ** 2).sum()
    return dict(n=len(yy), coef_per_10eur=10 * b, se=10 * se, t=b / se, F=Fst)


def main():
    lf = hourly_groups()
    dv = hourly_drivers()
    print(f"{lf.date.nunique()} days of hourly cogeneration data")
    base = lf.merge(dv, on=["date", "hour"], how="inner")
    wk_all = lambda M: pd.Series(M.date.dt.to_period("W").astype(str).factorize()[0], index=M.index)
    rows = []
    for y in ("lf_gas", "lf_biomass_waste"):
        r = fit(base, y, wk_all(base))
        r.update(outcome=y, k=0)
        rows.append(r)
        print(y, {k: round(float(v), 4) for k, v in r.items() if k not in ("outcome",)}, flush=True)
    for k in [j for j in range(-10, 11) if j != 0]:
        s = lf.merge(shifted(dv, k), on=["date", "hour"], how="inner")
        r = fit(s, "lf_gas", wk_all(s))
        if r:
            r.update(outcome="lf_gas shifted price", k=k)
            rows.append(r)
    r = pd.DataFrame(rows)
    r.round(4).to_csv(OUT / "cogeneration_hourly.csv", index=False)
    real = r[(r.outcome == "lf_gas") & (r.k == 0)].coef_per_10eur.iloc[0]
    sh = r[r.outcome == "lf_gas shifted price"].coef_per_10eur
    print(f"real {real:+.4f}; {len(sh)} shifts: median {sh.median():+.4f}, 5-95% [{sh.quantile(.05):+.4f}, {sh.quantile(.95):+.4f}], rank by |.| {int((sh.abs() >= abs(real)).sum()) + 1} of {len(sh) + 1}")


if __name__ == "__main__":
    main()
