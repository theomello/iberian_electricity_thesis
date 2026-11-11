"""Within-day price response of regulated low-voltage load (docs/specs/2026-11-11-hourly-price-design.md).

y(d,h) = ln E0 - ln Portuguese load at the same local hour. Regressor: ln hourly PVPC energy term (ESIOS 1013 to 2021-05, 1001
from 2021-06). Date effects (within-day demeaning) and hour x month effects and hourly temperature differences are partialled
out; OLS and 2SLS with the day-ahead wind (1777) and solar (1779) forecasts as instruments; clustered by week. Periods:
2019-01 -> 2021-05 (no Mar-Jun 2020) and 2021-06 -> 2023-12. Placebo outcome: industry E1-E6. Shift placebo: price and
instruments taken from k days away, k = -10..10 except 0. Elasticity scaled by the exposed share 0.36 (CNMC, energy, end 2019).
Writes outputs/tables/hourly_price_response*.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tax_did  # noqa: E402

OUT = OUT_DIR = ROOT / "outputs" / "tables"
SHARE = 0.36
PERIODS = [("2019-01 -> 2021-05 (PVPC 2.0A)", "2019-01-01", "2021-05-31", 1013), ("2021-06 -> 2023-12 (PVPC 2.0TD)", "2021-06-01", "2023-12-31", 1001)]


def local_series(i):
    d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
    loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    out = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})
    return out.drop_duplicates(["date", "hour"])


def prepare(y_series=None):
    x = tax_did.build(y_series)
    for i in (1013, 1001, 1777, 1779):
        x = x.merge(local_series(i), on=["date", "hour"], how="left")
    return x


def shifted(x, k):
    s = x[["date", "hour", "v1013", "v1001", "v1777", "v1779"]].copy()
    s["date"] = s.date - pd.Timedelta(days=k)
    return x[["date", "hour"]].merge(s, on=["date", "hour"], how="left")


def partial_out(M, cols, groups_date, W):
    """Demean by date, then residualise on W (hour x month dummies, weather)."""
    out = {}
    for c in cols:
        v = M[c] - M.groupby(groups_date)[c].transform("mean")
        out[c] = v.to_numpy()
    Wv = W.to_numpy(float)
    Wd = pd.DataFrame(Wv).groupby(groups_date.to_numpy()).transform("mean").to_numpy()
    Wv = Wv - Wd
    for c in cols:
        b = np.linalg.lstsq(Wv, out[c], rcond=None)[0]
        out[c] = out[c] - Wv @ b
    return out


def cluster_sum(a, g):
    return pd.DataFrame(a).groupby(g).sum().to_numpy()


def fit(M, ycol, pcol, zcols, W, wk):
    M = M.dropna(subset=[ycol, pcol] + zcols)
    M = M[M[pcol] > 0]
    if len(M) < 2000:
        return None
    M = M.assign(lp=np.log(M[pcol]))
    Wc = W.loc[M.index]
    r = partial_out(M, [ycol, "lp"] + zcols, M.date, Wc)
    y, p = r[ycol], r["lp"]
    Z = np.column_stack([r[z] for z in zcols])
    g = wk.loc[M.index].to_numpy()
    b_ols = (p @ y) / (p @ p)
    e = y - b_ols * p
    se_ols = np.sqrt((cluster_sum(p * e, g) ** 2).sum()) / (p @ p)
    pi = np.linalg.lstsq(Z, p, rcond=None)[0]
    ph = Z @ pi
    b_iv = (ph @ y) / (ph @ p)
    ei = y - b_iv * p
    se_iv = np.sqrt((cluster_sum(ph * ei, g) ** 2).sum()) / (ph @ p)
    u = p - ph
    A = np.linalg.pinv(Z.T @ Z)
    S = cluster_sum(Z * u[:, None], g)
    V = A @ (S.T @ S) @ A
    F = float(pi @ np.linalg.pinv(V) @ pi / len(pi))
    return dict(n=len(y), ols=b_ols, se_ols=se_ols, iv=b_iv, se_iv=se_iv, F=F)


def main():
    ind = sum(pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp").value for i in range(1202, 1208))
    outcomes = {"E0": prepare(), "industry E1-E6 (placebo)": prepare(ind)}
    rows = []
    for oname, x in outcomes.items():
        wk = x.date.dt.to_period("W").astype(str).factorize()[0]
        wk = pd.Series(wk, index=x.index)
        W = pd.concat([pd.get_dummies((x.hour.astype(str) + "_" + x.month.astype(str)), dtype=float), x[["hdh_d", "cdh_d"]]], axis=1)
        for plab, lo, hi, pid in PERIODS:
            sel = (x.date >= lo) & (x.date <= hi) & ~x.date.between(*tax_did.COVID)
            base = x[sel].copy()
            base["price"] = base[f"v{pid}"]
            base["z1"], base["z2"] = base.v1777, base.v1779
            r = fit(base, "d", "price", ["z1", "z2"], W, wk)
            r.update(outcome=oname, period=plab, k=0)
            rows.append(r)
            print(oname, plab, {k: (round(float(v), 4) if not isinstance(v, str) else v) for k, v in r.items() if k not in ("outcome", "period")}, flush=True)
            if oname == "E0":
                for k in [j for j in range(-10, 11) if j != 0]:
                    s = shifted(x, k)
                    sb = x[sel].copy()
                    sb["price"] = s.loc[sb.index, f"v{pid}"]
                    sb["z1"], sb["z2"] = s.loc[sb.index, "v1777"], s.loc[sb.index, "v1779"]
                    rr = fit(sb, "d", "price", ["z1", "z2"], W, wk)
                    if rr:
                        rr.update(outcome="E0 shifted price", period=plab, k=k)
                        rows.append(rr)
    r = pd.DataFrame(rows)
    r["iv_scaled"] = r.iv / SHARE
    r["se_iv_scaled"] = r.se_iv / SHARE
    r.round(4).to_csv(OUT / "hourly_price_response.csv", index=False)
    pd.set_option("display.width", 200)
    print(r[r.k == 0].round(3).to_string(index=False))
    for plab, *_ in PERIODS:
        real = r[(r.outcome == "E0") & (r.period == plab)].iv.iloc[0]
        sh = r[(r.outcome == "E0 shifted price") & (r.period == plab)].iv
        print(f"{plab}: real IV {real:+.4f}; {len(sh)} shifts: 5-95% [{sh.quantile(.05):+.4f}, {sh.quantile(.95):+.4f}], rank by |.| {int((sh.abs() >= abs(real)).sum()) + 1} of {len(sh) + 1}")


if __name__ == "__main__":
    main()
