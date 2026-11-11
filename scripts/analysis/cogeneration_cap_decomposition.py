"""How much of the June 2022 fall in gas cogeneration does the pre-cap price response explain?

Fits the pre-cap model (gas group's capacity-weighted load factor on the day-ahead price, price moved by the wind
forecast; controls gas price, degree hours, weekday, month; 2021-01-01 -> 2022-06-14) and predicts the days after it
from the actual price and gas price. Reports, for the 14 days before and after 15 June 2022 and for each month to
March 2023: actual load factor, predicted, and the residual (actual minus predicted). The share of the fall that the
price and gas paths explain is 1 - (change in residual) / (change in actual). The model is the structural price
response only: the residual is what the price path through this model cannot explain, including the cap's own effect
on plants' economics. Biomass and waste (placebo) gets the same treatment. Writes outputs/tables/cogeneration_cap_decomposition.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response import OUT, drivers  # noqa: E402
from cogeneration_price_response_checks import unit_panel  # noqa: E402


def design(t):
    dow = pd.get_dummies(t.index.dayofweek, dtype=float).reindex(columns=range(1, 7), fill_value=0.0).to_numpy()
    mon = pd.get_dummies(t.index.month, dtype=float).reindex(columns=range(2, 13), fill_value=0.0).to_numpy()
    return np.column_stack([np.ones(len(t)), t.gas, t.cdh_es, t.hdh_es, dow, mon])


def fit_iv(y, price, wind, X):
    Z = np.column_stack([wind, X])
    P = Z @ np.linalg.pinv(Z.T @ Z) @ Z.T
    Xf = np.column_stack([price, X])
    Xh = P @ Xf
    return np.linalg.pinv(Xh.T @ Xf) @ Xh.T @ y


def main():
    mw, u = unit_panel()
    dv = drivers()
    rows = []
    for fuel in ["gas", "biomass_waste"]:
        cols = [c for c in mw.columns if u.fuel[c] == fuel]
        y = (mw[cols].sum(axis=1) / u.cap[cols].sum()).rename("y")
        t = dv.join(y, how="inner").dropna()
        pre = t.loc["2021-01-01":"2022-06-14"]
        b = fit_iv(pre.y.to_numpy(), pre.price.to_numpy(), pre.wind.to_numpy(), design(pre))
        tt = t.loc["2022-04-01":"2023-03-31"].copy()
        tt["pred"] = np.column_stack([tt.price, design(tt)]) @ b
        tt["resid"] = tt.y - tt.pred
        print(f"{fuel}: price coef {10*b[0]:+.4f} per EUR10, gas coef {b[2]:+.4f} per EUR/MWh (index 2)")
        win = {"14 d before 15 Jun": ("2022-06-01", "2022-06-14"), "14 d after 15 Jun": ("2022-06-15", "2022-06-28")}
        for k, (a, e) in win.items():
            s = tt.loc[a:e]
            rows.append(dict(fuel=fuel, period=k, days=len(s), price=s.price.mean(), gas=s.gas.mean(), actual=s.y.mean(),
                             predicted=s.pred.mean(), resid=s.resid.mean()))
        for m, s in tt.loc["2022-07-01":"2023-03-31"].groupby(tt.loc["2022-07-01":"2023-03-31"].index.to_period("M")):
            rows.append(dict(fuel=fuel, period=str(m), days=len(s), price=s.price.mean(), gas=s.gas.mean(), actual=s.y.mean(),
                             predicted=s.pred.mean(), resid=s.resid.mean()))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "cogeneration_cap_decomposition.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    for fuel in ["gas", "biomass_waste"]:
        g = out[out.fuel == fuel].set_index("period")
        da = g.loc["14 d after 15 Jun", "actual"] - g.loc["14 d before 15 Jun", "actual"]
        dp = g.loc["14 d after 15 Jun", "predicted"] - g.loc["14 d before 15 Jun", "predicted"]
        print(f"{fuel}: actual change {da:+.3f}, predicted by price and gas {dp:+.3f}, residual change {da-dp:+.3f}")


if __name__ == "__main__":
    main()
