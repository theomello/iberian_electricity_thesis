"""Check 1 of docs/specs/2026-11-11-tou-replication-design.md: the shape of the regulated price at the June 2021 reform.

Peninsular PVPC (regulated tariff) from ESIOS: 1018 is the access charge of the old 2.0A tariff (flat), 1876 the
charges component of the new 2.0TD by hour, 1002 the tariff period of each hour (1 peak, 2 mid-peak, 3 off-peak),
1001 the total energy term. EUR/MWh. Reports the charges component by period against the old flat charge and against the
new tariff's own average, and the peak-to-off-peak ratio. Writes outputs/tables/tou_price_shape.csv.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"


def load(i):
    d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name.isin(["Península", "España"])]
    return d.drop_duplicates("utc_timestamp").set_index("utc_timestamp").value.rename(str(i))


def main():
    x = pd.concat([load(i) for i in (1013, 1018, 1001, 1002, 1876)], axis=1).sort_index()
    old = x.loc["2021-04-01":"2021-05-31"]
    new = x.loc["2021-06-01":"2021-12-31"]
    flat = old["1018"].mean()
    avg_new = new["1876"].mean()
    g = new.groupby("1002").agg(charges=("1876", "mean"), total_energy_term=("1001", "mean"), hours=("1876", "size"))
    g["vs_old_flat_pct"] = 100 * (g.charges / flat - 1)
    g["vs_new_average_pct"] = 100 * (g.charges / avg_new - 1)
    g.index = g.index.map({1.0: "peak", 2.0: "mid-peak", 3.0: "off-peak"})
    g.round(1).to_csv(OUT / "tou_price_shape.csv")
    print(f"old 2.0A access charge, Apr-May 2021: {flat:.1f} EUR/MWh (sd {old['1018'].std():.2f}); new 2.0TD charges, mean {avg_new:.1f}")
    print(g.round(1).to_string())
    print(f"peak / off-peak charges ratio: {g.loc['peak', 'charges'] / g.loc['off-peak', 'charges']:.1f}")


if __name__ == "__main__":
    main()
