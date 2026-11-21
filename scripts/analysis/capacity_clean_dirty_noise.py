"""Step zero of the installed-capacity clean-dirty design (proposed 2026-11-16; thresholds set before this run): variation, first stage, placebos and noise only. No elasticity is printed.

    .venv/bin/python scripts/analysis/capacity_clean_dirty_noise.py

Spec: docs/specs/2026-11-16-capacity-clean-dirty-design.md.
Panel: 11 peninsular regions with combined-cycle capacity in every month x 2021-01 -> 2026-08 (68 months).
y = ln[(wind 1485 + PV 1486)/(combined cycle 1483 + coal 1478)]; x = q_rt * s_t; z = q_r * s_t (q_r: 2018-2019 resource index, predetermined);
s_t = mean of ln(MIBGAS/0.55 + 0.37*EUA) over months t-35..t-24. Equation: y = eps*x + region + month effects, 2SLS, region-clustered.

Rules (set now). Any failure: record and stop, no other shock, lag, region set or index.
 C1 residual sd of z after region+month effects >= 0.03, and also after adding region linear trends.
 C2 residual sd of ln(combined-cycle capacity) after region+month effects >= 0.03 (coal closures are regulatory and do not count).
 C3 first-stage F (region-clustered, small-sample corrected, region+month effects) >= 10.
 C4 real F above the 95th percentile of F under (a) 2000 permutations of q_r across regions, (b) every circular shift of s_t by 12..T-12 months.
 C5 effective independent time points of s_t, T(1-rho)/(1+rho), rho = lag-1 autocorrelation after a linear detrend, >= 8.
 C6 detectable elasticity 2.8*max(clustered SE of eps under beta=0, sd of permutation-placebo reduced form / |first-stage slope|) <= 2.
Writes outputs/tables/capacity_clean_dirty_noise.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = ROOT if (ROOT / "data/esios").exists() else Path("/Users/theodor/projects/vre_spain_thesis")  # worktrees carry no data
sys.path.insert(0, str(ROOT / "scripts/lib"))
import regions as RG  # noqa: E402

OUT = ROOT / "outputs/tables"
OUT.mkdir(parents=True, exist_ok=True)
THR = dict(c1=0.03, c2=0.03, c3=10.0, c4=0.95, c5=8.0, c6=2.0)
START, END = pd.Period("2021-01", "M"), pd.Period("2026-08", "M")
PRE = (pd.Period("2018-01", "M"), pd.Period("2019-12", "M"))
LAG0, LAG1 = 24, 35
NPERM, SEED = 2000, 20261116
NONPEN = {"Islas Baleares", "Islas Canarias", "Ceuta", "Melilla"}


def capacity():
    c = pd.read_parquet(DATA / "data/esios/esios_installed_capacity.parquet")
    c["m"] = c.utc_timestamp.dt.tz_convert(None).dt.to_period("M")
    c = c[~c.geo_name.isin(NONPEN)]
    return c.pivot_table(index=["geo_name", "m"], columns="indicator_id", values="value").fillna(0.0)


def region_output():
    """Monthly measured wind and PV MWh by autonomous community (geo_name as in the capacity file)."""
    p = pd.read_parquet(DATA / "data/esios/esios_measured_generation_province.parquet", columns=["indicator_id", "value", "utc_timestamp", "geo_name"])
    p["m"] = p.utc_timestamp.dt.tz_convert(None).dt.to_period("M")
    p["nuts"] = RG.province_nuts2(p.geo_name).to_numpy()
    p["geo_id"] = p.nuts.map(RG.ESIOS_GEO)
    g = p.groupby(["geo_id", "m", "indicator_id"]).value.sum().unstack("indicator_id")
    return g.rename(columns={1159: "wind_mwh", 1161: "pv_mwh"}).fillna(0.0)


def two_way(a):
    """Remove region and month means from an (R, T) array."""
    return a - a.mean(1, keepdims=True) - a.mean(0, keepdims=True) + a.mean()


def trend_out(a):
    """Remove region and month means, then each region's linear trend."""
    a = two_way(a)
    t = np.arange(a.shape[1], dtype=float)
    t = t - t.mean()
    # trends orthogonal to month effects: demean t across regions is zero already, so region-specific slopes on t
    return a - (a @ t)[:, None] * t[None, :] / (t @ t)


def cluster_f(y, x, z, ref=two_way):
    """First-stage slope and clustered F of x on z, y is not used. Arrays (R, T); clusters = rows."""
    xt, zt = ref(x), ref(z)
    pi = (zt * xt).sum() / (zt**2).sum()
    e = xt - pi * zt
    g = (zt * e).sum(1)
    n, k, G = xt.size, 1 + xt.shape[0] + xt.shape[1] - 1, xt.shape[0]
    var = (g**2).sum() / (zt**2).sum() ** 2 * G / (G - 1) * (n - 1) / (n - k)
    return pi, pi**2 / var


def main():
    cap = capacity()
    out = region_output()
    keep = [r for r, d in cap.groupby("geo_name") if (d[1483] > 0).all()]
    ids = cap.reset_index().drop_duplicates("geo_name").set_index("geo_name")
    name_to_id = pd.read_parquet(DATA / "data/esios/esios_installed_capacity.parquet", columns=["geo_name", "geo_id"]).drop_duplicates().set_index("geo_name").geo_id
    gid = {r: int(name_to_id[r]) for r in keep}
    months = pd.period_range(START, END, freq="M")
    T = len(months)
    full = pd.period_range("2018-01", END, freq="M")

    # capacity and output as (R, month) arrays on the full range
    R = len(keep)
    C = {k: np.vstack([cap.loc[r, k].reindex(full).to_numpy() for r in keep]) for k in (1478, 1483, 1485, 1486)}
    O = {k: np.vstack([out.loc[gid[r], k].reindex(full).fillna(0.0).to_numpy() for r in keep]) for k in ("wind_mwh", "pv_mwh")}
    hrs = np.array([m.days_in_month * 24 for m in full], dtype=float)
    idx = {m: i for i, m in enumerate(full)}

    def quality(i0, i1):
        """Resource index over month columns i0..i1 inclusive (50/50 wind and PV, each relative to the 11-region pooled CF; <100 MW average capacity left out)."""
        res = []
        for tech, ok in (("wind_mwh", 1485), ("pv_mwh", 1486)):
            en = O[tech][:, i0 : i1 + 1].sum(1)
            mwh = (C[ok][:, i0 : i1 + 1] * hrs[i0 : i1 + 1]).sum(1)
            cf = en / np.where(mwh > 0, mwh, np.nan)
            cf = cf / (en.sum() / np.nansum(mwh))
            cf[C[ok][:, i0 : i1 + 1].mean(1) < 100] = np.nan
            res.append(cf)
        return np.nanmean(np.vstack(res), axis=0)

    q_pre = quality(idx[PRE[0]], idx[PRE[1]])
    q_real = np.vstack([quality(idx[m] - 12, idx[m] - 1) for m in months]).T  # (R, T), trailing 12 months to t-1

    # common shock
    mg = pd.read_parquet(DATA / "data/mibgas/mibgas_price_index_daily.parquet")[["date", "mibgas_es_eur_mwh"]]
    mg["m"] = pd.to_datetime(mg.date).dt.to_period("M")
    eua = pd.read_parquet(DATA / "data/investing/eua_carbon_price_daily.parquet")[["date", "close"]]
    eua["m"] = pd.to_datetime(eua.date).dt.to_period("M")
    mc = (mg.groupby("m").mibgas_es_eur_mwh.mean() / 0.55 + 0.37 * eua.groupby("m").close.mean()).dropna()
    lmc = np.log(mc)
    s = np.array([lmc.loc[m - LAG1 : m - LAG0].mean() for m in months])
    assert not np.isnan(s).any() and not np.isnan(q_real).any() and not np.isnan(q_pre).any()

    y = np.log((C[1485] + C[1486])[:, [idx[m] for m in months]] / (C[1478] + C[1483])[:, [idx[m] for m in months]])
    lccgt = np.log(C[1483][:, [idx[m] for m in months]])
    x = q_real * s[None, :]
    z = q_pre[:, None] * s[None, :]

    rows = []

    def add(rule, value, thr, ok, note=""):
        rows.append(dict(rule=rule, value=round(float(value), 4), threshold=thr, pass_=bool(ok), note=note))

    # C1
    sd2 = two_way(z).std()
    sdt = trend_out(z).std()
    add("C1 sd(z | region, month)", sd2, THR["c1"], sd2 >= THR["c1"])
    add("C1 sd(z | region, month, region trends)", sdt, THR["c1"], sdt >= THR["c1"])
    # C2
    sdd = two_way(lccgt).std()
    add("C2 sd(ln combined-cycle capacity | region, month)", sdd, THR["c2"], sdd >= THR["c2"], "coal closures excluded by design")
    # share of outcome variance from the dirty side is reported, not a rule
    v = two_way(y).var()
    ld = np.log(C[1478] + C[1483])[:, [idx[m] for m in months]]
    add("info: sd(ln dirty incl. coal | region, month) / sd(y | region, month)", two_way(ld).std() / np.sqrt(v), "report", True)
    # C3
    pi, F = cluster_f(y, x, z)
    add("C3 first-stage F (region-clustered)", F, THR["c3"], F >= THR["c3"])
    # C4a permutations of q_r across regions
    rng = np.random.default_rng(SEED)
    Fp = np.array([cluster_f(y, x, q_pre[rng.permutation(R)][:, None] * s[None, :])[1] for _ in range(NPERM)])
    p95 = np.quantile(Fp, THR["c4"])
    add("C4a real F vs 95th pct of F, 2000 region permutations", F, round(float(p95), 3), F > p95, f"share of permutations with F >= real: {(Fp >= F).mean():.4f}")
    # C4b circular shifts of s
    shifts = range(12, T - 11)
    Fs = np.array([cluster_f(y, x, q_pre[:, None] * np.roll(s, k)[None, :])[1] for k in shifts])
    q95 = np.quantile(Fs, THR["c4"])
    add("C4b real F vs 95th pct of F, circular shifts of s", F, round(float(q95), 3), F > q95, f"{len(Fs)} shifts; share with F >= real: {(Fs >= F).mean():.4f}")
    # C5
    tt = np.arange(T, dtype=float)
    sd_ = s - np.polyval(np.polyfit(tt, s, 1), tt)
    rho = np.corrcoef(sd_[:-1], sd_[1:])[0, 1]
    neff = T * (1 - rho) / (1 + rho)
    add("C5 effective independent time points of s", neff, THR["c5"], neff >= THR["c5"], f"lag-1 autocorrelation {rho:.3f}")
    # C6: null-imposed clustered SE and permutation sd of reduced form, outcome only through ytilde (no slope printed)
    zt, xt, yt = two_way(z), two_way(x), two_way(y)
    denom = (zt * xt).sum()
    G = R
    n, k = yt.size, R + T
    se_c = np.sqrt(((zt * yt).sum(1) ** 2).sum()) / abs(denom) * np.sqrt(G / (G - 1) * (n - 1) / (n - k))
    rf_p = []
    for _ in range(NPERM):
        zp = two_way(q_pre[rng.permutation(R)][:, None] * s[None, :])
        rf_p.append((zp * yt).sum() / (zp**2).sum())
    pi_real = denom / (zt**2).sum()
    se_p = np.std(rf_p) / abs(pi_real)
    det = 2.8 * max(se_c, se_p)
    add("C6 detectable elasticity 2.8*max(SE_cluster, SE_perm)", det, THR["c6"], det <= THR["c6"], f"SE_cluster {se_c:.3f}, SE_perm {se_p:.3f}")

    tab = pd.DataFrame(rows).rename(columns={"pass_": "pass"})
    tab.to_csv(OUT / "capacity_clean_dirty_noise.csv", index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 80)
    print(f"regions ({R}): {keep}\nmonths {T}")
    print(tab.to_string(index=False))
    gates = tab[tab.threshold.astype(str) != "report"]
    print("\nALL PASS" if gates["pass"].all() else "\nSTOP: " + "; ".join(gates[~gates["pass"]].rule))


if __name__ == "__main__":
    main()
