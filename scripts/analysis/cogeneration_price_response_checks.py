"""Two checks on cogeneration_price_response.py (pre-cap window 2021-01-01 -> 2022-06-14).

1. Lead and lag placebo. Gas cogeneration's output on day t against the price of day t+1 and of day t-1, each moved by
   its own day's wind forecast, jointly with the day's own price. If the response is a response to the price, only
   the own-day coefficient is non-zero; weather persistence or demand correlated with wind would load on the lead
   and lag. Pass rule, set before the run: lead and lag each within two standard errors of zero.
2. Dose-response by how easily a plant switches. Plants are classed by their number of run/stop switches in the
   post-cap period 2022-06-15 -> 2023-03-31 (independent of the estimation window): frequent switchers (>= 10) are
   marginal, plants that almost never switch are baseload. Prediction: the response is concentrated in the frequent
   switchers and the never-stoppers show less. Pass rule: switchers' response larger than the stable plants' and
   the stable plants' within two standard errors of zero. Run on gas plants, biomass and waste as the placebo.
Writes outputs/tables/cogeneration_price_response_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response import OUT, drivers, hac, LAGS  # noqa: E402


def tsls_multi(y, P, Zexc, Xexc, lags=LAGS):
    Z = np.column_stack([Zexc, Xexc])
    X = np.column_stack([P, Xexc])
    Pm = Z @ np.linalg.solve(Z.T @ Z, Z.T)
    Xh = Pm @ X
    b = np.linalg.solve(Xh.T @ X, Xh.T @ y)
    e = y - X @ b
    A = np.linalg.inv(Xh.T @ X)
    V = A @ hac(Xh, e, lags) @ A.T
    k = P.shape[1] if P.ndim > 1 else 1
    return b[:k], np.sqrt(np.diag(V))[:k]


def unit_panel():
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    files = [f for f in sorted((OUT / "cogeneration_ree" / "days").glob("ree_*.parquet"))
             if "20210101" <= f.stem[-8:] <= "20230331"]
    d = pd.concat(pd.read_parquet(f, columns=["date", "unit", "p48_mwh"]) for f in files)
    w = d[d.unit.isin(u.index)].pivot_table(index="date", columns="unit", values="p48_mwh", aggfunc="sum").fillna(0.0)
    w.index = pd.to_datetime(w.index)
    mw = (w / 24).clip(lower=0)
    cap = u.cap.reindex(mw.columns)
    return mw.clip(upper=cap, axis=1), u.loc[mw.columns]


def main():
    mw, u = unit_panel()
    dv = drivers()
    rows = []
    # ---- 1. lead and lag placebo
    gas = [c for c in mw.columns if u.fuel[c] == "gas"]
    lf = (mw[gas].sum(axis=1) / u.cap[gas].sum()).rename("lf_gas")
    full = pd.date_range("2021-01-01", "2022-06-14")
    D = dv.reindex(pd.date_range("2020-12-30", "2022-06-16"))
    D["price_lead"], D["price_lag"] = D.price.shift(-1), D.price.shift(1)
    D["wind_lead"], D["wind_lag"] = D.wind.shift(-1), D.wind.shift(1)
    s = D.loc[full].join(lf, how="inner").dropna(subset=["price", "wind", "price_lead", "price_lag", "wind_lead",
                                                          "wind_lag", "gas", "cdh_es", "hdh_es", "lf_gas"])
    dow = pd.get_dummies(s.index.dayofweek, drop_first=True, dtype=float).to_numpy()
    mon = pd.get_dummies(s.index.month, drop_first=True, dtype=float).to_numpy()
    Xexc = np.column_stack([np.ones(len(s)), s.gas, s.cdh_es, s.hdh_es, dow, mon])
    for name, pc, zc in [("own day", ["price"], ["wind"]),
                         ("own + lead", ["price", "price_lead"], ["wind", "wind_lead"]),
                         ("own + lag", ["price", "price_lag"], ["wind", "wind_lag"]),
                         ("own + lead + lag", ["price", "price_lead", "price_lag"], ["wind", "wind_lead", "wind_lag"])]:
        b, se = tsls_multi(s.lf_gas.to_numpy(), s[pc].to_numpy(), s[zc].to_numpy(), Xexc)
        for k, nm in enumerate(pc):
            rows.append(dict(check="lead/lag placebo", spec=name, term=nm, n=len(s), d_lf_per_10eur=10 * b[k],
                             se=10 * se[k], t=b[k] / se[k]))
    # ---- 2. dose-response by switching
    post = mw[mw.index >= "2022-06-15"]
    thr = 0.1 * mw.max()
    on = (post > thr)
    switches = (on.astype(int).diff().abs().sum(axis=0))
    pre = mw[(mw.index >= "2021-01-01") & (mw.index <= "2022-06-14")]
    days_post = on.shape[0]
    cls = pd.Series("na", index=mw.columns)
    ok = (post.shape[0] > 0) & (mw.max() > 0)
    cls[(switches >= 10)] = "switcher"
    cls[(switches < 10)] = "stable"
    for fuel in ["gas", "biomass_waste"]:
        cols = [c for c in mw.columns if u.fuel[c] == fuel and c in post.columns and (post[c] > 0).sum() > 30]
        for g in ["switcher", "stable"]:
            cc = [c for c in cols if cls[c] == g]
            if len(cc) < 5:
                continue
            y = (pre[cc].sum(axis=1) / u.cap[cc].sum()).rename("y")
            t = dv.loc[y.index].join(y).dropna()
            dow = pd.get_dummies(t.index.dayofweek, drop_first=True, dtype=float).to_numpy()
            mon = pd.get_dummies(t.index.month, drop_first=True, dtype=float).to_numpy()
            X = np.column_stack([np.ones(len(t)), t.gas, t.cdh_es, t.hdh_es, dow, mon])
            b, se = tsls_multi(t.y.to_numpy(), t[["price"]].to_numpy(), t[["wind"]].to_numpy(), X)
            rows.append(dict(check="dose by switching", spec=fuel, term=g, n=len(t), n_plants=len(cc),
                             cap_mw=u.cap[cc].sum(), mean_lf=t.y.mean(), d_lf_per_10eur=10 * b[0], se=10 * se[0],
                             t=b[0] / se[0]))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "cogeneration_price_response_checks.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
