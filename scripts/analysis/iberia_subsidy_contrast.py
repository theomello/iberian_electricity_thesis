"""Within Iberia: subsidised combined cycles against unsubsidised gas cogeneration at the gas cap.

Gas combined cycles (the 55 Iberian units of 100 MW or more, OMIE PDBF) were paid the gas-cap subsidy from 15 June 2022;
gas cogeneration inside the regulated payment scheme was outside the mechanism until 1 October, and the rest (not eligible
for the heat-adjusted subsidy in practice) is the group this repo follows on REE's units. Both burn gas, both faced the
same European gas shock and weather that week. Statistic: change in the mean daily load factor over the 14 days after
15 June 2022 against the 14 days before, combined cycles minus cogeneration. Placebos: the same window on every
Wednesday where both series cover it (2021-06-16 -> 2021-12-15, 2022-04-15 -> 2022-05-17, 2022-07-13 -> 2022-12-28),
excluding +-28 days of the break. Pass rule, set before the run: an effect of the subsidy differential needs the real
difference outside the placebos' 5th-95th percentile and a rank within the top 5% by absolute size. The same-calendar
window of 2021 is printed on its own. Writes outputs/tables/iberia_subsidy_contrast.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response_checks import unit_panel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
BREAK = pd.Timestamp("2022-06-15")
HALF = pd.Timedelta(days=14)


def chg(s, b):
    return s.loc[b:b + HALF - pd.Timedelta(days=1)].mean() - s.loc[b - HALF:b - pd.Timedelta(days=1)].mean()


def main():
    cc = pd.read_csv(OUT / "gas_plants_daily_iberia_italy.csv", index_col=0, parse_dates=True).iberia.rename("ccgt")
    mw, u = unit_panel()
    gas = [c for c in mw.columns if u.fuel[c] == "gas"]
    co = (mw[gas].sum(axis=1) / u.cap[gas].sum()).rename("cogen")
    d = pd.concat([cc, co], axis=1, sort=True).dropna()
    print(f"{len(d)} days with both series, {d.index.min().date()} -> {d.index.max().date()}")
    real = {"ccgt": chg(d.ccgt, BREAK), "cogen": chg(d.cogen, BREAK)}
    real["diff"] = real["ccgt"] - real["cogen"]
    dates = [pb for pb in pd.date_range("2021-06-16", "2022-12-28", freq="7D")
             if abs((pb - BREAK).days) >= 28 and (pb - HALF) >= d.index.min() and (pb + HALF - pd.Timedelta(days=1)) <= d.index.max()
             and d.loc[pb - HALF:pb + HALF - pd.Timedelta(days=1)].shape[0] == 28]
    plac = {k: [] for k in real}
    for pb in dates:
        a, b = chg(d.ccgt, pb), chg(d.cogen, pb)
        plac["ccgt"].append(a); plac["cogen"].append(b); plac["diff"].append(a - b)
    rows = []
    for k, v in plac.items():
        p = np.array(v)
        rows.append(dict(series=k, real_change=real[k], placebos=len(p), placebo_sd=p.std(), p05=np.percentile(p, 5),
                         p95=np.percentile(p, 95), rank_abs=int((np.abs(p) >= abs(real[k])).sum()) + 1))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "iberia_subsidy_contrast.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    # same calendar window a year earlier, and a few neighbours
    for pb in [pd.Timestamp("2021-06-16"), pd.Timestamp("2021-06-09"), pd.Timestamp("2021-06-23")]:
        if pb in d.index or True:
            a, b = chg(d.ccgt, pb), chg(d.cogen, pb)
            print(f"placebo break {pb.date()}: ccgt {a:+.3f}, cogen {b:+.3f}, diff {a-b:+.3f}")
    p = pd.Series(plac["diff"], index=dates)
    print("\nlargest absolute placebo differences\n", p.reindex(p.abs().sort_values(ascending=False).index).head(8).round(3).to_string())
    print("\nreal windows: before and after means")
    for k in ["ccgt", "cogen"]:
        print(k, round(d[k].loc[BREAK - HALF:BREAK - pd.Timedelta(days=1)].mean(), 3), "->", round(d[k].loc[BREAK:BREAK + HALF - pd.Timedelta(days=1)].mean(), 3))


if __name__ == "__main__":
    main()
