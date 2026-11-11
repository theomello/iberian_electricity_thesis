"""Does the wholesale-driven pre-tax price, not the tax, account for the fall in Spanish E0 relative to Portugal? (spec section 7)

Daily regression, 2021-06-01 -> 2024-12-31 and -> 2023-12-31: mean over the day of ln E0 minus ln Portuguese load (tax_did.build) on
ln pre-tax PVPC energy term (ESIOS 1001) and ln tax factor (outputs/tables/tax_price_shape.csv), with month, weekday, holiday,
temperature-difference effects; Newey-West 14 lags. Placebo outcomes: the same on industry (E1-E6, ESIOS 1202-1207), which is not
on the PVPC; and, in 2018-01 -> 2021-05 with the tax constant (March-June 2020 out), E0 on ln PVPC 2.0A energy term (ESIOS 1013).
Writes outputs/tables/tax_pretax_price.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tax_did  # noqa: E402

OUT = ROOT / "outputs" / "tables"


def daily(x):
    g = x.groupby("date")
    return pd.DataFrame({"d": g.d.mean(), "hdh": g.hdh_d.mean(), "cdh": g.cdh_d.mean(), "hol_es": g.hol_es.mean(), "hol_pt": g.hol_pt.mean(),
                         "dow": g.dow.first(), "month": g.month.first()})


def nw(X, e, L=14):
    n = len(e)
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, L + 1):
        G = Xe[l:].T @ Xe[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    A = np.linalg.pinv(X.T @ X)
    return A @ S @ A


def reg(y, regs, ctrl, trend=False):
    parts = [pd.DataFrame(regs), ctrl[["hdh", "cdh", "hol_es", "hol_pt"]],
             pd.get_dummies(ctrl.month.astype(str), prefix="m", drop_first=True, dtype=float),
             pd.get_dummies(ctrl.dow.astype(str), prefix="w", drop_first=True, dtype=float)]
    if trend:
        parts.append(pd.DataFrame({"trend": (ctrl.index - ctrl.index.min()).days / 365.0}, index=ctrl.index))
    X = pd.concat(parts, axis=1)
    X.insert(0, "const", 1.0)
    Xv, yv = X.to_numpy(float), y.to_numpy(float)
    b = np.linalg.pinv(Xv) @ yv
    V = nw(Xv, yv - Xv @ b)
    names = list(X.columns)
    return {n: (100 * b[names.index(n)] if False else b[names.index(n)], np.sqrt(V[names.index(n), names.index(n)])) for n in regs}, len(yv)


def main():
    tp = pd.read_csv(OUT / "tax_price_shape.csv", parse_dates=["date"]).set_index("date")
    e0 = daily(tax_did.build())
    ind = sum(pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp").value for i in range(1202, 1208))
    ind_d = daily(tax_did.build(ind))
    rows = []
    for out_name, dd in (("E0 (low voltage)", e0), ("placebo: E1-E6 (industry, not PVPC)", ind_d)):
        for end in ("2024-12-31", "2023-12-31"):
            w = dd.loc["2021-06-01":end].join(tp[["pretax_energy_term", "tax_factor"]], how="inner")
            w["lp"] = np.log(w.pretax_energy_term)
            w["lt"] = np.log(w.tax_factor)
            for lab, regs, tr in (("pre-tax price only", ["lp"], False), ("tax factor only", ["lt"], False), ("both", ["lp", "lt"], False), ("both + trend", ["lp", "lt"], True)):
                r, n = reg(w.d, w[regs], w, tr)
                for k, (b, se) in r.items():
                    rows.append(dict(outcome=out_name, window=f"2021-06 -> {end[:7]}", spec=lab, var="ln pre-tax price" if k == "lp" else "ln tax factor", coef=b, se=se, n_days=n))
    # pre-period placebo: tax constant, E0 on ln PVPC 2.0A energy term
    p13 = pd.read_parquet(ROOT / "data/esios/esios_1013.parquet").drop_duplicates("utc_timestamp")
    p13["date"] = p13.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    pr = p13.groupby("date").value.mean()
    omie = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    omie["date"] = pd.to_datetime(omie.date)
    om = omie.groupby("date").price_es.mean()
    for out_name, dd in (("E0 (low voltage)", e0), ("placebo: E1-E6 (industry, not PVPC)", ind_d)):
        w = dd.loc["2018-01-01":"2021-05-31"]
        w = w[~w.index.to_series().between(*tax_did.COVID)].copy()
        for pname, ps in (("ln PVPC 2.0A energy term", pr), ("ln OMIE day-ahead", om)):
            w["lp"] = np.log(ps.reindex(w.index))
            ww = w.dropna(subset=["lp"])
            r, n = reg(ww.d, ww[["lp"]], ww, False)
            rows.append(dict(outcome=out_name, window="2018-01 -> 2021-05 (tax constant, no Mar-Jun 2020)", spec=pname, var="ln pre-tax price",
                             coef=r["lp"][0], se=r["lp"][1], n_days=n))
    r = pd.DataFrame(rows)
    r.round(4).to_csv(OUT / "tax_pretax_price.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
