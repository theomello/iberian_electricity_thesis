#!/usr/bin/env python3
"""Step 1c of the gas-cap design: do Iberian and Italian gas plants move together before the
cap once Iberia's demand conditions are held fixed? (conditional parallel trends;
docs/specs/2026-10-28-gas-cap-conduct-design.md)

    .venv/bin/python scripts/analysis/gas_cap_conditional_pretrend.py

Same outcomes (m25, run20; base cost), pre-period, thresholds and placebo dates as step 1.
Unit-day means; unit and date fixed effects; standard errors clustered by firm. Controls enter
as Iberia x Z_d, so they absorb Iberia-specific movements tied to Z and nothing common to both
countries. Every Z is fixed before the day-ahead auction, so the cap cannot move it:

* `ib_demand_fc`, `ib_wind_fc`, `ib_solar_fc`: REE's D-1 forecasts (ESIOS 1775/1777/1779),
  daily means of the hourly values in `france_link_hours`;
* `fr_load_fc`: RTE's D-1 French demand forecast; `fr_nuc_lag`: French nuclear output over
  D-8..D-2; `p_open`: the line's predicted chance of being open, from French fundamentals and
  the capacities set before the auction (`build_france_link.py`);
* `storage`: peninsular stored hydro energy, ESIOS 623, the last week published by D-10;
* `spread`: PSV minus MIBGAS at D-2.

Each is standardised. Tests, per outcome: (1) the Iberia x linear-time coefficient (the
conditional trend), failing when significant at 5% and as large as the threshold over a year;
(2) the three placebo caps, failing when one reaches the threshold. Unconditional results are
printed beside them, from the same code, as the check that it reproduces step 1.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
PRE_END = pd.Timestamp("2022-06-14")
PLACEBOS = ["2021-10-01", "2022-01-01", "2022-03-01"]
ZS = ["ib_demand_fc", "ib_wind_fc", "ib_solar_fc", "fr_load_fc", "fr_nuc_lag", "p_open", "storage", "spread"]


def controls() -> pd.DataFrame:
    f = pd.read_parquet(ROOT / "outputs" / "tables" / "france_link_hours.parquet",
                        columns=["date", "ib_demand_fc", "ib_wind_fc", "ib_solar_fc", "fr_load_fc",
                                 "fr_nuc_lag", "p_open"])
    z = f.groupby("date").mean().reset_index()
    z["date"] = pd.to_datetime(z.date).astype("datetime64[ns]")
    e = pd.read_parquet(DATA / "esios" / "esios_623.parquet")
    e = e[e.geo_name == "Península"]
    st = pd.Series(e.value.to_numpy(), index=pd.to_datetime(e.datetime.str[:10])).sort_index()
    st.index = st.index + pd.Timedelta(days=10)          # known for offers from about M + 10
    z = pd.merge_asof(z.sort_values("date"), st.rename("storage").rename_axis("date").reset_index()
                      .assign(date=lambda x: x.date.astype("datetime64[ns]")), on="date")
    mib = pd.read_parquet(DATA / "mibgas" / "mibgas_price_index_daily.parquet")
    mib = mib.assign(date=pd.to_datetime(mib.date)).set_index("date").mibgas_es_eur_mwh
    g = pd.read_parquet(DATA / "gme" / "gas" / "gme_mgp_gas_daily.parquet").sort_values(["gas_day", "session"])
    g["px"] = g.price_mean.fillna(g.price_ref)
    psv = g.dropna(subset=["px"]).groupby("gas_day").px.last()
    sp = (psv - mib).asfreq("D").ffill(limit=5).shift(2).rename("spread").rename_axis("date").reset_index()
    z = z.merge(sp.assign(date=lambda x: x.date.astype("datetime64[ns]")), on="date", how="left")
    return z


def demean2(M: np.ndarray, a: np.ndarray, b: np.ndarray, it: int = 100) -> np.ndarray:
    R = M.astype(float).copy()
    for _ in range(it):
        R -= pd.DataFrame(R).groupby(a).transform("mean").to_numpy()
        R -= pd.DataFrame(R).groupby(b).transform("mean").to_numpy()
    return R


def ols_fe(d: pd.DataFrame, y: str, X: list[str]) -> tuple[np.ndarray, np.ndarray]:
    a, b = pd.factorize(d.unit)[0], pd.factorize(d.date)[0]
    M = demean2(d[[y] + X].to_numpy(), a, b)
    Y, Xm = M[:, 0], M[:, 1:]
    iXX = np.linalg.inv(Xm.T @ Xm)
    beta = iXX @ Xm.T @ Y
    e = Y - Xm @ beta
    g = pd.factorize(d.firm)[0]
    S = pd.DataFrame(Xm * e[:, None]).groupby(g).sum().to_numpy()
    G = S.shape[0]
    V = iXX @ (S.T @ S) @ iXX * G / (G - 1)
    return beta, np.sqrt(np.diag(V))


def tests(d: pd.DataFrame, y: str, thr: float, conditional: bool) -> str:
    zc = [f"ibx_{z}" for z in ZS] if conditional else []
    d = d.assign(ibx_t=d.iberia * (d.date - d.date.min()).dt.days / 7.0)
    b, se = ols_fe(d, y, ["ibx_t"] + zc)
    tr, tse = b[0], se[0]
    fail_t = abs(tr / tse) > 1.96 and abs(tr * 52) >= thr
    out = [f"trend/yr {tr * 52:+.3g} (t {tr / tse:.1f}){' FAIL' if fail_t else ''}"]
    fail_p = False
    pl = []
    for p in PLACEBOS:
        dd = d.assign(ibx_pl=(d.iberia & (d.date >= p)).astype(float))
        bp, sp = ols_fe(dd, y, ["ibx_pl"] + zc)
        fail_p |= abs(bp[0]) >= thr
        pl.append(f"{bp[0]:+.3g} ({sp[0]:.2g})")
    out.append("placebos " + ", ".join(pl) + (" FAIL" if fail_p else ""))
    return "; ".join(out) + ("  => PASSES" if not (fail_t or fail_p) else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outcomes", default="m25,run20")
    ap.add_argument("--start", default="2021-06-15")
    ap.add_argument("--placebos", default=",".join(PLACEBOS))
    a = ap.parse_args()
    PLACEBOS[:] = a.placebos.split(",")
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p25", "p_mid", "cost", "run20", "subsidy"])
    ybar = h[h.subsidy > 0].drop_duplicates("date").subsidy.mean()
    h = h[(h.date <= PRE_END) & (h.date >= a.start)].dropna(subset=["cost"])
    h["m25"] = h.p25 - h.cost
    h["mmid"] = h.p_mid - h.cost
    print(f"window {a.start} -> {PRE_END.date()}, placebos {PLACEBOS}")
    d = h.groupby(["unit", "date"], as_index=False).agg(m25=("m25", "mean"), mmid=("mmid", "mean"), run20=("run20", "mean"),
                                                        iberia=("iberia", "first"), firm=("firm", "first"))
    d["firm"] = d.firm.fillna(d.unit)
    d["date"] = d.date.astype("datetime64[ns]")
    z = controls()
    d = d.merge(z, on="date", how="left")
    miss = d[ZS].isna().any(axis=1)
    print(f"unit-days {len(d):,}; dropped for a missing control: {int(miss.sum()):,}")
    d = d[~miss].copy()
    for c in ZS:
        s = (d[c] - d[c].mean()) / d[c].std()
        d[f"ibx_{c}"] = d.iberia * s
    for y in a.outcomes.split(","):
        thr = 0.05 if y.startswith("run") else ybar / 5
        dy = d.dropna(subset=[y])
        print(f"\n{y} (threshold {thr:.3g}, {len(dy):,} unit-days)")
        print("  unconditional:", tests(dy, y, thr, False))
        print("  conditional:  ", tests(dy, y, thr, True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
