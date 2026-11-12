"""Paper-style elasticity regression (docs/specs/2026-11-11-tou-hardening-design.md, "Pre-registration: the paper-style elasticity regression"; Enrich, Li, Mizrahi, Reguant Eq. 4, Table 6).

Hourly panel of two areas, Spain (E0) and Portugal. Outcome: paper-LASSO prediction error of log load (tou_lasso_paper). Price: Spain's ln PVPC price (ESIOS 1013 before June 2021, 1001 after), Portugal constant.
Instrument: ln(hour's charge + average pre-policy energy cost): charge from ESIOS 1876 after June 2021, the old flat 44 before; Portugal constant. 2SLS; fixed effects absorbed by sparse least squares.
Columns: (1) hour x weekend x month-of-sample and hour x weekend x area; (2) adds hour x weekend x area x month-of-year; (3) adds temperature (heating and cooling degree hours) x hour x weekend;
(4) adds weekend x area x month-of-sample (the paper's Table 6 lists it as an added fixed effect in column 4); (5) column (2) with the price interacted with the percentile of the day's average
post-policy energy cost (25-75, 75-90, above 90). Standard errors clustered by area x month-of-sample. Pre 2018-01-01 -> 2020-12-31 without March-June 2020; post 2021-06-01 -> 2021-12-31.
Placebo: 2018-2019 with cross-fitted errors, the real charge pattern (by month, hour, weekend) laid on 2019-06 -> 2019-12 as price and instrument. Writes outputs/tables/tou_elasticity_paper.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.linalg import lsmr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as E  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

TS = pd.Timestamp
POST0, POST1 = TS("2021-06-01"), TS("2021-12-31")
OLD = E.OLD
WALD_REF = -0.059  # evening-vs-night paper-LASSO Wald ratio, window A (tou_pvpc_only)


def hourly(i):
    d = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
    loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": loc.dt.tz_localize(None).dt.normalize().to_numpy(), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})


def prices():
    p = hourly(1013).merge(hourly(1001), on=["date", "hour"], how="outer").merge(hourly(1876), on=["date", "hour"], how="left")
    post = p.date >= POST0
    p["price"] = np.where(post, p.v1001, p.v1013)
    p["charge"] = np.where(post, p.v1876, OLD)
    ebar = (p[(p.date >= "2019-01-01") & (p.date <= "2021-05-31")].v1013 - OLD).mean()
    p["energy"] = np.where(post, p.v1001 - p.v1876, p.v1013 - OLD)
    return p[["date", "hour", "price", "charge", "energy"]], ebar


def stack(x, e_es, e_pt, p, ebar, dates):
    d = x[dates].copy()
    d["e_es"], d["e_pt"] = e_es[d.index], e_pt[d.index]
    d = d.merge(p, on=["date", "hour"], how="left")
    sp_ = pd.DataFrame({"area": 0, "date": d.date, "hour": d.hour, "wk": d.weekend.astype(int), "e": d.e_es, "lnp": np.log(d.price), "z": np.log(d.charge + ebar),
                        "hdh": np.maximum(18 - d.temp_es, 0), "cdh": np.maximum(d.temp_es - 18, 0), "energy": d.energy})
    pt = pd.DataFrame({"area": 1, "date": d.date, "hour": d.hour, "wk": ((d.dow >= 5) | (d.hol_pt == 1)).astype(int), "e": d.e_pt, "lnp": 0.0, "z": 0.0,
                       "hdh": np.maximum(18 - d.temp_pt, 0), "cdh": np.maximum(d.temp_pt - 18, 0), "energy": np.nan})
    s = pd.concat([sp_, pt], ignore_index=True)
    s["ym"] = s.date.dt.strftime("%Y-%m")
    s["moy"] = s.date.dt.month
    return s.dropna(subset=["e", "lnp", "z"]).reset_index(drop=True)


def onehot(*cols):
    code = pd.factorize(pd.Series(list(zip(*cols))))[0] if len(cols) > 1 else pd.factorize(cols[0])[0]
    n = len(code)
    return sp.csr_matrix((np.ones(n), (np.arange(n), code)), shape=(n, code.max() + 1))


def fe_matrix(s, col):
    parts = [onehot(s.hour, s.wk, s.area), onehot(s.hour, s.wk, s.ym)]
    if col >= 2:
        parts.append(onehot(s.hour, s.wk, s.area, s.moy))
    if col >= 3:
        H = pd.get_dummies(s.hour.astype(str) + "_" + s.wk.astype(str), dtype=float).to_numpy()
        parts.append(sp.csr_matrix(H * s.hdh.to_numpy()[:, None]))
        parts.append(sp.csr_matrix(H * s.cdh.to_numpy()[:, None]))
    if col >= 4:
        parts.append(onehot(s.wk, s.area, s.ym))
    return sp.hstack(parts).tocsr()


def resid(F, v):
    sol = lsmr(F, np.asarray(v, float), atol=1e-9, btol=1e-9, conlim=1e9, maxiter=2000)[0]
    return np.asarray(v, float) - F @ sol


def iv(y, X, Z, g):
    X, Z = np.atleast_2d(X.T).T if X.ndim == 1 else X, np.atleast_2d(Z.T).T if Z.ndim == 1 else Z
    A = Z.T @ X
    b = np.linalg.solve(A, Z.T @ y)
    u = y - X @ b
    k = Z.shape[1]
    S = np.zeros((k, k))
    for gi in np.unique(g):
        m = g == gi
        v = Z[m].T @ u[m]
        S += np.outer(v, v)
    G = len(np.unique(g))
    Ai = np.linalg.inv(A)
    V = Ai @ S @ Ai.T * G / (G - 1)
    return b, np.sqrt(np.diag(V)), G


def fit_columns(s, g):
    out = []
    for col in (1, 2, 3, 4):
        F = fe_matrix(s, col)
        y, p, z = resid(F, s.e), resid(F, s.lnp), resid(F, s.z)
        b, se, G = iv(y, p, z, g)
        pi = (z @ p) / (z @ z)
        e1 = p - pi * z
        S = sum((z[g == gi] @ e1[g == gi]) ** 2 for gi in np.unique(g))
        F1 = (pi / (np.sqrt(S) / (z @ z) * np.sqrt(G / (G - 1)))) ** 2
        bo, seo, _ = iv(y, p, p, g)
        brf, serf, _ = iv(y, z, z, g)
        out.append(dict(col=col, eta=b[0], se=se[0], t=b[0] / se[0], first_stage_F=F1, ols=bo[0], ols_se=seo[0], reduced_form=brf[0], rf_se=serf[0], n=len(y), clusters=G))
        print(out[-1], flush=True)
    return out


def column5(s, g):
    post = (s.area == 0) & (s.date >= POST0)
    day_e = s[post].groupby("date").energy.mean()
    q = day_e.rank(pct=True)
    grp = pd.Series(0, index=s.index)
    mp = s.date.map(q)
    grp[post & (mp > 0.25) & (mp <= 0.75)] = 1
    grp[post & (mp > 0.75) & (mp <= 0.90)] = 2
    grp[post & (mp > 0.90)] = 3
    F = fe_matrix(s, 2)
    names = ["ln price", "x 25-75th", "x 75-90th", "x >90th"]
    Xc = [s.lnp.to_numpy()] + [(s.lnp * (grp == k)).to_numpy() for k in (1, 2, 3)]
    Zc = [s.z.to_numpy()] + [(s.z * (grp == k)).to_numpy() for k in (1, 2, 3)]
    X = np.column_stack([resid(F, v) for v in Xc])
    Z = np.column_stack([resid(F, v) for v in Zc])
    y = resid(F, s.e)
    b, se, G = iv(y, X, Z, g)
    rows = [dict(term=n, coef=bb, se=ss, t=bb / ss) for n, bb, ss in zip(names, b, se)]
    print(rows, flush=True)
    return rows


def main():
    x = D.prep(T.build("e0", end="2021-12-31"))
    es, pt = L.errors(x)
    print("real errors done", flush=True)
    p, ebar = prices()
    print(f"average pre-policy energy cost {ebar:.1f}", flush=True)
    dates = (((x.date >= "2018-01-01") & (x.date <= "2020-12-31")) | ((x.date >= POST0) & (x.date <= POST1))) & ~x.date.between(*E.COVID)
    s = stack(x, es, pt, p, ebar, dates)
    g = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
    cols = fit_columns(s, g)
    c5 = column5(s, g)
    # placebo 2018-2019, cross-fitted errors
    cf_es, cf_pt = pd.Series(np.nan, index=x.index), pd.Series(np.nan, index=x.index)
    for yr in (2018, 2019):
        a, b_ = L.errors(x, exclude_years=(yr,))
        m = x.date.dt.year == yr
        cf_es[m], cf_pt[m] = a[m], b_[m]
        print("cross-fit", yr, flush=True)
    real = p[(p.date >= POST0) & (p.date <= POST1)].copy()
    real["m"] = real.date.dt.month
    real["wk"] = ((real.date.dt.dayofweek >= 5)).astype(int)
    pat = real.groupby(["m", "hour", "wk"]).charge.mean()
    pdates = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    sp_ = stack(x, cf_es, cf_pt, p, ebar, pdates)
    postp = (sp_.area == 0) & (sp_.date >= "2019-06-01") & (sp_.date <= "2019-12-31")
    idx = pd.MultiIndex.from_arrays([sp_.date.dt.month[postp], sp_.hour[postp], sp_.wk[postp]])
    cpat = pd.Series(pat.reindex(idx).to_numpy(), index=sp_.index[postp])
    sp_["z"] = np.where((sp_.area == 0), np.log(OLD + ebar), 0.0)
    ok = cpat.notna()
    sp_.loc[cpat.index[ok], "z"] = np.log(cpat[ok] + ebar)
    sp_["lnp"] = sp_.z
    gp = pd.factorize(sp_.area.astype(str) + "_" + sp_.ym)[0]
    F = fe_matrix(sp_, 1)
    yp, pp = resid(F, sp_.e), resid(F, sp_.lnp)
    bp, sep, _ = iv(yp, pp, pp, gp)
    print(f"placebo 2019 (cross-fitted): eta {bp[0]:.3f} (se {sep[0]:.3f}, t {bp[0] / sep[0]:.2f})", flush=True)
    c = pd.DataFrame(cols)
    c["placebo_eta"], c["placebo_se"] = bp[0], sep[0]
    pd.concat([c, pd.DataFrame(c5).assign(spec="col5")], ignore_index=True).round(5).to_csv(T.OUT / "tou_elasticity_paper.csv", index=False)
    pd.set_option("display.width", 220)
    print(c.round(4).to_string(index=False))
    eta = c.set_index("col").eta
    first4 = c[c.col <= 4]
    print("RULE 1 first stage F >= 10:", bool((first4.first_stage_F >= 10).all()), first4.first_stage_F.round(1).tolist())
    print("RULE 2 negative, t <= -2:", bool(((first4.eta < 0) & (first4.t <= -2)).all()), first4.t.round(2).tolist())
    print("RULE 3 between -0.25 and -0.03:", bool(((first4.eta >= -0.25) & (first4.eta <= -0.03)).all()), first4.eta.round(3).tolist())
    r = first4.eta.min() / first4.eta.max() if (first4.eta < 0).all() else np.nan
    print("RULE 4 columns within factor two:", bool(r <= 2) if r == r else False, f"(ratio {r:.2f})")
    print("RULE 5 percentile interactions |t| < 2:", all(abs(d["t"]) < 2 for d in c5[1:]), [round(d["t"], 2) for d in c5[1:]])
    med = float(first4.eta.median())
    print("RULE 6 Wald ratio within factor two of the median eta:", 0.5 <= WALD_REF / med <= 2, f"(median {med:.3f}, Wald {WALD_REF})")
    print("RULE 7 placebo t > -2 and real column 1 below placebo:", bool(bp[0] / sep[0] > -2 and eta[1] < bp[0]), f"(placebo {bp[0]:.3f}, t {bp[0] / sep[0]:.2f}; real {eta[1]:.3f})")


if __name__ == "__main__":
    main()
