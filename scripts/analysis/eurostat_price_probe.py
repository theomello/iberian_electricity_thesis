"""Power check for the Portuguese-price designs: Eurostat semiannual retail prices, Spain vs Portugal, against relative demand.

Households (nrg_pc_204, 2,500-4,999 kWh band, incl. and excl. taxes) and non-households (nrg_pc_205, 2,000-19,999 MWh band, excl.
VAT), EUR/kWh, 2019-S1 -> 2025-S2. Outcome: ln(E0/Portugal) and ln(industry E1-E6/Portugal), half-year mean of daily loads.
Year-on-year changes in the same half (removes season). Prints the slope and its standard error; this is a power check, not a design.
Writes outputs/tables/eurostat_price_probe.csv.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"


def eurostat(ds, q):
    raw = subprocess.run(["curl", "-s", "--max-time", "60", f"{BASE}{ds}?format=JSON&lang=en&{q}&sinceTimePeriod=2019-S1"], capture_output=True, text=True).stdout
    d = json.loads(raw)
    dims = d["id"]
    sizes = d["size"]
    cats = {k: list(d["dimension"][k]["category"]["index"]) for k in dims}
    rows = []
    for flat, v in d["value"].items():
        i = int(flat)
        idx = {}
        for k, s in zip(reversed(dims), reversed(sizes)):
            idx[k] = cats[k][i % s]
            i //= s
        rows.append({**idx, "v": v})
    return pd.DataFrame(rows)


def half(s):
    s = s.copy()
    s.index = pd.PeriodIndex(s.index, freq="M")
    return s


def main():
    hh = eurostat("nrg_pc_204", "geo=ES&geo=PT&nrg_cons=KWH2500-4999&unit=KWH&currency=EUR&tax=I_TAX&tax=X_TAX")
    nh = eurostat("nrg_pc_205", "geo=ES&geo=PT&nrg_cons=MWH2000-19999&unit=KWH&currency=EUR&tax=X_TAX")
    hh["time"] = hh.time.astype(str)
    p_hh_tax = hh[hh.tax == "I_TAX"].pivot(index="time", columns="geo", values="v")
    p_hh_ex = hh[hh.tax == "X_TAX"].pivot(index="time", columns="geo", values="v")
    p_nh = nh.pivot(index="time", columns="geo", values="v")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import tax_did
    ind = sum(pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp").value for i in range(1202, 1208))
    dem = {}
    for nm, ser in (("E0", None), ("industry", ind)):
        x = tax_did.build(ser)
        x["h"] = x.date.dt.year.astype(str) + "-S" + np.where(x.date.dt.month <= 6, "1", "2")
        dem[nm] = x.groupby("h").d.mean()
    tab = pd.DataFrame({"hh_price_tax": np.log(p_hh_tax.ES / p_hh_tax.PT), "hh_price_ex": np.log(p_hh_ex.ES / p_hh_ex.PT), "nh_price_ex": np.log(p_nh.ES / p_nh.PT),
                        "d_E0": dem["E0"], "d_ind": dem["industry"]}).dropna()
    tab.index.name = "half"
    tab = tab[tab.index <= "2024-S2"]
    yoy = tab.copy()
    yoy.index = pd.MultiIndex.from_arrays([[i[:4] for i in tab.index], [i[-2:] for i in tab.index]])
    yoy = yoy.groupby(level=1).diff().dropna()
    tab.round(4).to_csv(OUT / "eurostat_price_probe.csv")
    print(tab.round(3).to_string())
    print(f"\nyear-on-year changes, {len(yoy)} half-years")
    for y, xx in (("d_E0", "hh_price_tax"), ("d_E0", "hh_price_ex"), ("d_ind", "nh_price_ex"), ("d_E0", "nh_price_ex")):
        X = np.column_stack([np.ones(len(yoy)), yoy[xx]])
        b = np.linalg.lstsq(X, yoy[y], rcond=None)[0]
        e = yoy[y] - X @ b
        se = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (e @ e) / (len(yoy) - 2))
        print(f"{y} on {xx}: slope {b[1]:+.3f} (se {se[1]:.3f}), n={len(yoy)}")


if __name__ == "__main__":
    main()
