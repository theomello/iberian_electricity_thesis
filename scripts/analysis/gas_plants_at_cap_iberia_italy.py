"""Gas plants' day-ahead output at the Iberian cap, Iberia against Italy.

Daily capacity-weighted load factor of gas units of 100 MW or more: Iberian units in the gas-cap offer panel (OMIE PDBF
schedule, all role codes summed, floor 0) and Italian units with a JRC cost (GME accepted offers). Change in the mean over
the 14 days after 15 June 2022 against the 14 days before, per country and the difference. Placebos: the same window on
every Wednesday 2021-06-09 -> 2022-12-28 outside +-28 days of the break; rank of the real difference. Pass rule, set
before the run: an Iberia-specific change in gas-plant output at the cap needs the real difference outside the placebos'
5th-95th percentile. Writes outputs/tables/gas_plants_at_cap_iberia_italy.csv and the daily series.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
BREAK = pd.Timestamp("2022-06-15")
HALF = pd.Timedelta(days=14)


def italy():
    c = pd.read_parquet(ROOT / "data/jrc_ppdb/italy_implied_marginal_cost_daily.parquet", columns=["unit", "capacity_g"]).drop_duplicates("unit")
    c = c[c.capacity_g >= 100].set_index("unit").capacity_g
    rows = []
    for f in sorted((ROOT / "data/gme/offers/parquet").glob("offers_*.parquet")):
        d = pd.read_parquet(f, columns=["side", "status", "unit", "date", "awarded_mwh", "period"])
        d = d[(d.side == "OFF") & (d.status == "ACC") & d.unit.isin(c.index)]
        if d.empty:
            continue
        g = d.groupby(["unit", "date"], observed=True).awarded_mwh.sum() / 24
        rows.append(g.reset_index())
    r = pd.concat(rows)
    r["lf"] = r.awarded_mwh / r.unit.map(c)
    return r.pivot_table(index="date", columns="unit", values="lf", aggfunc="sum").fillna(0.0), c


def iberia():
    p = pd.read_parquet(ROOT / "outputs/tables/gas_cap_offer_panel.parquet", columns=["unit", "iberia", "K", "date"])
    p = p[p.iberia]
    k = p.groupby("unit").K.median()
    k = k[k >= 100]
    rows = []
    for f in sorted((ROOT / "data/omie/pdbf/parquet").glob("pdbf_*.parquet")):
        ym = f.stem[-6:]
        if not ("202106" <= ym <= "202306"):
            continue
        d = pd.read_parquet(f, columns=["date", "period", "unit", "schedule_mw"])
        d = d[d.unit.isin(k.index)]
        s = d.groupby(["unit", "date", "period"]).schedule_mw.sum().clip(lower=0)
        rows.append(s.groupby(["unit", "date"]).mean().reset_index())
    r = pd.concat(rows)
    r["lf"] = r.schedule_mw / r.unit.map(k)
    return r.pivot_table(index="date", columns="unit", values="lf", aggfunc="sum").fillna(0.0), k


def cw(lf, cap):
    cols = [c for c in lf.columns if c in cap.index]
    s = (lf[cols].clip(upper=1.2) * cap[cols]).sum(axis=1) / cap[cols].sum()
    s.index = pd.to_datetime(s.index)
    return s


def chg(s, b):
    return s.loc[b:b + HALF - pd.Timedelta(days=1)].mean() - s.loc[b - HALF:b - pd.Timedelta(days=1)].mean()


def main():
    li, ci = italy()
    lb, cb = iberia()
    it, ib = cw(li, ci), cw(lb, cb)
    d = pd.concat([ib.rename("iberia"), it.rename("italy")], axis=1).dropna()
    d.to_csv(OUT / "gas_plants_daily_iberia_italy.csv")
    print(f"Iberian units {len(cb)} ({cb.sum():.0f} MW), Italian units {len(ci)} ({ci.sum():.0f} MW); days {len(d)}; mean lf Iberia {d.iberia.mean():.2f}, Italy {d.italy.mean():.2f}")
    real = {"iberia": chg(d.iberia, BREAK), "italy": chg(d.italy, BREAK)}
    real["diff"] = real["iberia"] - real["italy"]
    plac = {"iberia": [], "italy": [], "diff": []}
    for pb in pd.date_range("2021-06-09", "2022-12-28", freq="7D"):
        if abs((pb - BREAK).days) < 28 or pb - HALF < d.index.min() or pb + HALF > d.index.max():
            continue
        a, b = chg(d.iberia, pb), chg(d.italy, pb)
        plac["iberia"].append(a); plac["italy"].append(b); plac["diff"].append(a - b)
    rows = []
    for k, v in plac.items():
        p = np.array(v)
        rows.append(dict(series=k, real_change=real[k], placebos=len(p), placebo_sd=p.std(), p05=np.percentile(p, 5),
                         p95=np.percentile(p, 95), rank_abs=int((np.abs(p) >= abs(real[k])).sum()) + 1))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "gas_plants_at_cap_iberia_italy.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    w = d.loc["2022-06-01":"2022-06-28"].round(2)
    print(w.T.to_string())


if __name__ == "__main__":
    main()
