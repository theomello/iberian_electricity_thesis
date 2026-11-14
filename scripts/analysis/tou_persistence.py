"""Part B of docs/specs/2026-11-12-placebo-persistence-design.md: persistence of the E0 evening-versus-night response, June 1 - September 15 of each of 2021 .. 2025.

E0 (ESIOS 1201) against Portugal (REN), the paper's per-hour LASSO trained 2018-01-01 -> 2020-12-31 without March-June 2020 and never retrained (tou_lasso_paper.errors). Per summer: DDD of errors (evening 18-21h
against night 0-7h, working days against weekends and holidays; weekly clusters); drift guard = the evening-versus-night contrast on weekends and holidays only; Wald ratio = DDD / change in ln relative price of
2.0TD evening against night including the summer's OMIE energy price, tolls+charges from ESIOS 1876, against the old flat toll 44.027 (also with the PVPC energy term 1001 - 1876). Writes outputs/tables/tou_persistence.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_elasticity_paper as EL  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

EVE, NIGHT = [18, 19, 20, 21], list(range(8))
OLD = 44.027


def drift(x, err, s, e):
    sub = x[(x.date >= s) & (x.date <= e) & (x.kind == "wknd") & (x.hour.isin(EVE + NIGHT))].copy()
    sub["err"] = err.reindex(sub.index)
    sub = sub.dropna(subset=["err"])
    ev = sub.hour.isin(EVE).astype(float).to_numpy()
    X = np.column_stack([np.ones(len(sub)), ev])
    b = np.linalg.pinv(X) @ sub.err.to_numpy()
    r = sub.err.to_numpy() - X @ b
    V = T.hac_cluster(X, r, sub.date.dt.to_period("W").astype(str).factorize()[0])
    return b[1], np.sqrt(V[1, 1])


def main():
    x = D.prep(T.build("e0", end="2025-09-15"))
    print(f"x: {len(x)} rows, {x.date.min().date()} -> {x.date.max().date()}", flush=True)
    es, pt = L.errors(x)
    err = es - pt
    eh = CT.omie_hourly()
    c = EL.hourly(1876).set_index(["date", "hour"]).v1876
    p1001 = EL.hourly(1001).set_index(["date", "hour"]).v1001
    c, p1001, eh = (v[~v.index.duplicated()] for v in (c, p1001, eh))  # repeated autumn hour
    rows = []
    for y in range(2021, 2026):
        s, e = pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-15")
        b, se = L.cell_ddd(x, err, s, e)
        db, dse = drift(x, err, s, e)
        w = x[(x.date >= s) & (x.date <= e) & (x.kind == "work")]
        ev_idx = pd.MultiIndex.from_frame(w[w.hour.isin(EVE)][["date", "hour"]])
        ni_idx = pd.MultiIndex.from_frame(w[w.hour.isin(NIGHT)][["date", "hour"]])
        E_ev, E_ni = eh.reindex(ev_idx).mean(), eh.reindex(ni_idx).mean()
        T_ev, T_ni = c.reindex(ev_idx).mean(), c.reindex(ni_idx).mean()
        new = np.log((E_ev + T_ev) / (E_ni + T_ni))
        old = np.log((E_ev + OLD) / (E_ni + OLD))
        d_rel = new - old
        pv_ev, pv_ni = p1001.reindex(ev_idx).mean(), p1001.reindex(ni_idx).mean()
        en_ev, en_ni = pv_ev - T_ev, pv_ni - T_ni
        d_rel_pv = np.log(pv_ev / pv_ni) - np.log((en_ev + OLD) / (en_ni + OLD))
        rows.append(dict(summer=y, ddd=b, se=se, t=b / se, drift=db, drift_se=dse, E_ev=E_ev, E_ni=E_ni, T_ev=T_ev, T_ni=T_ni, dln_rel_price=d_rel, wald=b / d_rel, dln_rel_price_pvpc=d_rel_pv,
                         wald_pvpc=b / d_rel_pv))
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(CT.OUT / "tou_persistence.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    a = R.set_index("summer")
    print("B1 data: all five summers have errors and prices:", bool(a.ddd.notna().all() and a.dln_rel_price.notna().all()))
    print(f"B2 anchor 2021: {100 * a.loc[2021, 'ddd']:.2f}% (se {100 * a.loc[2021, 'se']:.2f}) vs -3.79%: within 0.5 pts:", bool(abs(100 * a.loc[2021, 'ddd'] + 3.79) <= 0.5))
    read = {y: bool(abs(100 * a.loc[y, "drift"]) <= 1.0) for y in a.index}
    print("B3 drift guard (|weekend evening-night| <= 1.0 pt), readable summers:", read, {y: round(100 * a.loc[y, 'drift'], 2) for y in a.index})
    later = [y for y in range(2022, 2026) if read[y]]
    ok = [y for y in later if a.loc[y, "ddd"] < 0 and a.loc[y, "t"] <= -2 and a.loc[y, "ddd"] <= 0.5 * a.loc[2021, "ddd"]]
    weak = [y for y in later if a.loc[y, "ddd"] > 0.5 * a.loc[2021, "ddd"] or abs(a.loc[y, "t"]) < 2]
    verdict = "persists" if later and len(ok) == len(later) else ("fades" if len(weak) >= 2 else "mixed")
    print(f"B4 persistence: readable later summers {later}; meet the bar {ok}; below half or |t|<2 {weak}; verdict: {verdict}")
    w = a.wald[[y for y in a.index if read[y]]]
    print("B5 Wald ratios (readable):", w.round(3).to_dict(), "range", round(w.min(), 3), round(w.max(), 3),
          "| 2022 relative price change vs 2021:", round(a.loc[2022, "dln_rel_price"] / a.loc[2021, "dln_rel_price"], 2), "| 2022 effect vs 2021:", round(a.loc[2022, "ddd"] / a.loc[2021, "ddd"], 2))


if __name__ == "__main__":
    main()
