"""Cogeneration output against the power price, the price moved by the wind forecast (the E2 first cut).

Gas cogeneration burns gas and recovers the heat, so its engine runs when the power price is above its net cost: its
output should rise with the price at a given gas price. Biomass and waste plants burn no gas and are paid mainly
outside the market: they are the placebo (output should not respond). Daily capacity-weighted load factor per group
from REE's programming units (P48), on days REE's workbooks are on disk. Price = mean day-ahead price; instrument =
mean day-ahead wind forecast (ESIOS 1777, and 1779 solar in the second row); controls: MIBGAS gas price, heating and
cooling degree hours (the host's heat load), day of week, month. HAC (Bartlett, 7 lags) standard errors.
Windows: pre-cap (2021-01-01 -> 2022-06-14 on days present) and post-cap (2022-06-15 -> 2023-03-31).
Writes outputs/tables/cogeneration_price_response.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
LAGS = 7


def groups_daily() -> pd.DataFrame:
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    files = [f for f in sorted((OUT / "cogeneration_ree" / "days").glob("ree_*.parquet"))
             if "20210101" <= f.stem[-8:] <= "20230331"]
    d = pd.concat(pd.read_parquet(f, columns=["date", "unit", "p48_mwh"]) for f in files)
    w = d[d.unit.isin(u.index)].pivot_table(index="date", columns="unit", values="p48_mwh", aggfunc="sum").fillna(0.0)
    mw = (w / 24).clip(lower=0)
    cap = u.cap.reindex(mw.columns)
    out = {}
    for g in ["gas", "other_fossil", "biomass_waste"]:
        cols = [c for c in mw.columns if u.fuel[c] == g]
        out[f"lf_{g}"] = (mw[cols].clip(upper=cap[cols], axis=1).sum(axis=1)) / cap[cols].sum()
        out[f"cap_{g}"] = cap[cols].sum()
    r = pd.DataFrame({k: v for k, v in out.items() if k.startswith("lf_")})
    r.index = pd.to_datetime(r.index)
    r.attrs["cap"] = {k: v for k, v in out.items() if k.startswith("cap_")}
    return r


def drivers() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    p["d"] = pd.to_datetime(p.date)
    price = p.groupby("d").price_es.mean().rename("price")
    f = {}
    for i, n in [(1777, "wind"), (1779, "solar")]:
        x = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp")
        x["d"] = pd.to_datetime(x.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.date)
        f[n] = x.groupby("d").value.mean() / 1000
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_index.parquet")
    t["d"] = pd.to_datetime(t.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.date)
    t = t.groupby("d")[["cdh_es", "hdh_es"]].mean()
    g = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet")
    g["d"] = pd.to_datetime(g.date)
    gas = g.set_index("d").mibgas_es_eur_mwh.rename("gas")
    return pd.concat([price, f["wind"].rename("wind"), f["solar"].rename("solar"), t, gas], axis=1)


def hac(X, e, lags):
    n = len(e)
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = Xe[l:].T @ Xe[:-l]
        S += w * (G + G.T)
    return S


def tsls(y, price, Zexc, Xexc, lags=LAGS):
    """y on [price, Xexc] with instruments Zexc; Xexc includes the constant. Returns b_price, se, first-stage F."""
    Z = np.column_stack([Zexc, Xexc])
    X = np.column_stack([price, Xexc])
    P = Z @ np.linalg.solve(Z.T @ Z, Z.T)
    Xh = P @ X
    b = np.linalg.solve(Xh.T @ X, Xh.T @ y)
    e = y - X @ b
    A = np.linalg.inv(Xh.T @ X)
    V = A @ hac(Xh, e, lags) @ A.T
    # first stage F on the excluded instruments, HAC
    pi = np.linalg.lstsq(Z, price, rcond=None)[0]
    e1 = price - Z @ pi
    Vz = np.linalg.inv(Z.T @ Z) @ hac(Z, e1, lags) @ np.linalg.inv(Z.T @ Z)
    k = Zexc.shape[1]
    F = float(pi[:k] @ np.linalg.solve(Vz[:k, :k], pi[:k]) / k)
    return b[0], float(np.sqrt(V[0, 0])), F


def main():
    lf = groups_daily()
    dv = drivers()
    d = lf.join(dv, how="left").dropna().sort_index()
    d["diff_gas_minus_bio"] = d.lf_gas - d.lf_biomass_waste
    print(f"{len(d)} days {d.index.min().date()} -> {d.index.max().date()}; caps (MW):",
          {k: round(v) for k, v in lf.attrs['cap'].items()})
    wins = {"pre-cap": (d.index <= "2022-06-14"), "post-cap": (d.index >= "2022-06-15")}
    rows = []
    for wn, m in wins.items():
        s = d[m]
        dow = pd.get_dummies(s.index.dayofweek, drop_first=True, dtype=float).to_numpy()
        mon = pd.get_dummies(s.index.month, drop_first=True, dtype=float).to_numpy()
        Xexc = np.column_stack([np.ones(len(s)), s.gas, s.cdh_es, s.hdh_es, dow, mon])
        for zn, zc in [("wind", ["wind"]), ("wind+solar", ["wind", "solar"])]:
            Z = s[zc].to_numpy()
            for y in ["lf_gas", "lf_other_fossil", "lf_biomass_waste", "diff_gas_minus_bio"]:
                b, se, F = tsls(s[y].to_numpy(), s.price.to_numpy(), Z, Xexc)
                rows.append(dict(window=wn, instrument=zn, outcome=y, n=len(s), mean_price=s.price.mean(),
                                 mean_y=s[y].mean(), d_lf_per_10eur=10 * b, se=10 * se, t=b / se, first_stage_F=F,
                                 elasticity_at_mean=b * s.price.mean() / s[y].mean()))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "cogeneration_price_response.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
