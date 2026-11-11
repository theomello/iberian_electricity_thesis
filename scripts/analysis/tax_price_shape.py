"""Check 1 of docs/specs/2026-11-11-tax-change-design.md: the tax-inclusive retail price around the 2021 steps.

Tax factor = (1 + electricity tax) x (1 + VAT) on the bill's energy and power terms. Rates from the BOE (RDL 12/2021, 17/2021,
29/2021); the VAT rate needs the previous month's mean OMIE price above 45 EUR/MWh, checked here from the data. Pre-tax price:
PVPC total energy term (ESIOS 1001, peninsular), on disk to 2021-12-31 only. Writes outputs/tables/tax_price_shape.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"


def main():
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    p["date"] = pd.to_datetime(p.date)
    omie = p.groupby(p.date.dt.to_period("M")).price_es.mean()
    d = pd.read_parquet(ROOT / "data/esios/esios_1001.parquet")
    d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
    d["date"] = d.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    day = d.groupby("date").value.mean()
    day = day["2021-04-01":"2024-12-31"]
    vat = pd.Series(0.21, index=day.index)
    iee = pd.Series(0.0511269632, index=day.index)
    prev = pd.Series([omie[(dt.to_period("M") - 1)] for dt in day.index], index=day.index)
    ix = day.index
    # VAT: 10% from 2021-06-26 (RDL 12/2021) while the previous month's price is above 45; 5% from 2022-07-01 (RDL 11/2022, to
    # end 2023); from 2024-01-01 10%, back to 21% in months after a previous-month price below 45 (RDL 8/2023)
    vat[(ix >= "2021-06-26") & (prev > 45)] = 0.10
    vat[(ix >= "2022-07-01") & (ix < "2024-01-01")] = 0.05
    vat[(ix >= "2024-01-01") & (prev > 45)] = 0.10
    # electricity tax: 0.5% from 2021-09-16 to 2023-12-31, 2.5% in Q1 2024, 3.8% Apr-Jun 2024, then 5.11% (RDL 17/2021, 29/2021,
    # 11/2022, 20/2022, 8/2023)
    iee[(ix >= "2021-09-16") & (ix < "2024-01-01")] = 0.005
    iee[(ix >= "2024-01-01") & (ix < "2024-04-01")] = 0.025
    iee[(ix >= "2024-04-01") & (ix < "2024-07-01")] = 0.038
    f = (1 + iee) * (1 + vat)
    x = pd.DataFrame({"pretax_energy_term": day, "vat": vat, "iee": iee, "tax_factor": f, "inclusive": day * f})
    x.to_csv(OUT / "tax_price_shape.csv")
    print(f"previous-month price above 45 on every day 2021-06-26 -> 2023-12-31: {bool((prev[(day.index >= '2021-06-26') & (day.index < '2024-01-01')] > 45).all())}")
    for a, b, lab in (("2021-06-01", "2021-06-25", "before VAT cut"), ("2021-06-26", "2021-09-15", "after VAT cut"), ("2021-09-16", "2022-06-30", "after tax cut"),
                      ("2022-07-01", "2022-12-31", "VAT 5%"), ("2023-01-01", "2023-12-31", "2023")):
        s = x.loc[a:b]
        print(f"{lab:16s} factor {s.tax_factor.mean():.4f}  pre-tax {s.pretax_energy_term.mean():6.1f}  inclusive {s.inclusive.mean():6.1f}")
    print(f"VAT step: ln factor {np.log(1.1/1.21)*100:+.1f}%; electricity-tax step: {np.log(1.005/1.0511269632)*100:+.1f}%; both {np.log(1.1*1.005/(1.21*1.0511269632))*100:+.1f}%")
    m = x.groupby(x.index.to_period("M")).mean()
    m["ln_pretax_vs_Jul"] = 100 * np.log(m.pretax_energy_term / m.pretax_energy_term.iloc[1])
    m["ln_incl_vs_Jul"] = 100 * np.log(m.inclusive / m.inclusive.iloc[1])
    print(m.round(3).to_string())


if __name__ == "__main__":
    main()
