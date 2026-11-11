"""Where does the cogeneration price response go after the gas cap (15 June 2022)?

Pre-cap, gas cogeneration's output rises with the wind-moved price and biomass and waste does not
(cogeneration_price_response.py). Post-cap the biomass placebo responds too. This splits the post-cap days by period:
  cap          2022-06-15 -> 2022-09-30  (gas plants outside the regulated scheme are inside the mechanism; the rest cannot opt in)
  opt-in       2022-10-01 -> 2023-03-31  (regulated-scheme plants may give it up and join)
  opt-in early 2022-10-01 -> 2022-12-31
  opt-in late  2023-01-01 -> 2023-03-31  (REE's gas cogeneration steps up on 30 Jan - 2 Feb 2023)
and by plant group (frequent switchers, stable) for gas, with biomass and waste as the placebo. Same regression as
cogeneration_price_response.py: group load factor on the price, price moved by the day's wind forecast, controls gas
price, degree hours, weekday and month; HAC 7 lags. Pass rule, set before the run: if the biomass placebo is
within two standard errors of zero in a window, that window's gas response can be read as before; if not, the window
cannot separate the price response from what moves biomass. Writes outputs/tables/cogeneration_price_response_postcap.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response import OUT, drivers  # noqa: E402
from cogeneration_price_response_checks import tsls_multi, unit_panel  # noqa: E402

WINDOWS = {"pre-cap, 2021-01 -> 2022-06-14": ("2021-01-01", "2022-06-14"),
           "cap, 15 Jun -> 30 Sep 2022": ("2022-06-15", "2022-09-30"),
           "opt-in, 1 Oct 2022 -> 31 Mar 2023": ("2022-10-01", "2023-03-31"),
           "opt-in early, Oct -> Dec 2022": ("2022-10-01", "2022-12-31"),
           "opt-in late, Jan -> Mar 2023": ("2023-01-01", "2023-03-31")}


def main():
    mw, u = unit_panel()
    dv = drivers()
    post = mw[mw.index >= "2022-06-15"]
    on = post > 0.1 * mw.max()
    sw = on.astype(int).diff().abs().sum(axis=0)
    groups = {}
    for fuel in ["gas", "biomass_waste"]:
        cols = [c for c in mw.columns if u.fuel[c] == fuel and (post[c] > 0).sum() > 30]
        groups[f"{fuel}, all"] = cols
        if fuel == "gas":
            groups["gas, switchers"] = [c for c in cols if sw[c] >= 10]
            groups["gas, stable"] = [c for c in cols if sw[c] < 10]
    rows = []
    for wn, (a, b) in WINDOWS.items():
        for gn, cols in groups.items():
            y = (mw[cols].sum(axis=1) / u.cap[cols].sum()).rename("y")
            t = dv.join(y, how="inner").loc[a:b].dropna()
            dow = pd.get_dummies(t.index.dayofweek, drop_first=True, dtype=float).to_numpy()
            mon = pd.get_dummies(t.index.month, drop_first=True, dtype=float).to_numpy()
            X = np.column_stack([np.ones(len(t)), t.gas, t.cdh_es, t.hdh_es, dow, mon])
            # first-stage F, HAC
            Z = np.column_stack([t.wind, X])
            pi = np.linalg.lstsq(Z, t.price, rcond=None)[0]
            e1 = t.price.to_numpy() - Z @ pi
            from cogeneration_price_response import hac
            Vz = np.linalg.inv(Z.T @ Z) @ hac(Z, e1, 7) @ np.linalg.inv(Z.T @ Z)
            F = pi[0] ** 2 / Vz[0, 0]
            b_, se = tsls_multi(t.y.to_numpy(), t[["price"]].to_numpy(), t[["wind"]].to_numpy(), X)
            rows.append(dict(window=wn, group=gn, n=len(t), plants=len(cols), mw=u.cap[cols].sum(), mean_price=t.price.mean(),
                             mean_lf=t.y.mean(), d_lf_per_10eur=10 * b_[0], se=10 * se[0], t=b_[0] / se[0], first_stage_F=F))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "cogeneration_price_response_postcap.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
