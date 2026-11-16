"""Area-weather rerun of the per-capita area panel (docs/specs/2026-11-12-area-weather-design.md).

Identical to tou_area_panel_pc.py except the temperature fed to each area's LASSO: the area's own population-weighted MERRA-2
temperature (outputs/tables/regulated_area_panel/area_temperature_merra2_hourly.parquet). Spanish areas are joined on Madrid local
date and hour, Portugal on Lisbon local date and hour (as the national series are in tou_did.build); ESIOS 352 gets the mean of the five
Spanish areas' temperatures weighted by their mean regulated points. Writes outputs/tables/tou_area_panel_pcw_*.csv, separate error cache.
Prints the per-capita rules 2-8 for reference and the five area-weather rules.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel_pc as P  # noqa: E402
import tou_did as T  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

AREAS = P.AREAS
W = pd.read_parquet(T.ROOT / "outputs/tables/regulated_area_panel/area_temperature_merra2_hourly.parquet")
W["utc_timestamp"] = pd.to_datetime(W.utc_timestamp, utc=True)


def local_series(area, tz):
    s = W[W.area == area].set_index("utc_timestamp").temp_c
    loc = s.index.tz_convert(tz)
    d = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, f"temp_{area}": s.to_numpy()})
    return d.drop_duplicates(["date", "hour"])


def prep(x, cs, ptc):
    for a in AREAS:
        d = local_series(a, "Europe/Madrid")
        m = x[["date", "hour"]].merge(d, on=["date", "hour"], how="left")
        x[f"temp_{a}"] = m[f"temp_{a}"].to_numpy()
    d = local_series("PT", "Europe/Lisbon")
    x["temp_PTA"] = x[["date", "hour"]].merge(d, on=["date", "hour"], how="left")["temp_PT"].to_numpy()
    pre = (x.date >= P.START) & (x.date <= "2020-12-31")
    w = {a: float(x.loc[pre, "date"].map(cs[a]).mean()) for a in AREAS}
    x["temp_352"] = sum(w[a] * x[f"temp_{a}"] for a in AREAS) / sum(w.values())
    cols = [f"temp_{a}" for a in AREAS] + ["temp_PTA", "temp_352"]
    x.attrs["missing_temp_hours"] = int(x[cols].isna().any(axis=1).sum())
    print("hours with a missing area temperature:", x.attrs["missing_temp_hours"], flush=True)


def get_errors_w(x):
    path = P.CACHE / "area_panel_pcw_errors.parquet"
    if path.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(path)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for ex in ((), (2018,), (2019,)):
        for a in AREAS:
            tasks.append((f"{a}_p48", x, f"pc_{a}_p48", f"temp_{a}", "hol_es", ex))
        tasks.append(("PTU", x, "pc_PTU", "temp_PTA", "hol_pt", ex))
        tasks.append(("PTREN", x, "load_pt", "temp_PTA", "hol_pt", ex))
    for a in AREAS:
        tasks.append((f"{a}_pdbf", x, f"pc_{a}_pdbf", f"temp_{a}", "hol_es", ()))
        tasks.append((f"{a}_up", x, f"pc_{a}_p48_up", f"temp_{a}", "hol_es", ()))
        tasks.append((f"{a}_dn", x, f"pc_{a}_p48_dn", f"temp_{a}", "hol_es", ()))
        tasks.append((f"{a}_nq3", x, f"pc_{a}_p48_nq3", f"temp_{a}", "hol_es", ()))
    tasks.append(("E352", x, "load_352", "temp_352", "hol_es", ()))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(P.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    P.CACHE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(path)
    return errs


def main():
    o = P.compute(get_errors_w, prefix="tou_area_panel_pcw", prep=prep)
    ok = P.report(o)
    R, PL, PLm = o["R"], o["PL"], o["PLm"]
    g_ = lambda spec, term: R[(R.spec == spec) & (R.term == term)].iloc[0]
    pkM, pkF = g_("M weighted", "wd_peak").b, g_("F REN control", "wd_peak").b
    sdM, sdF = 100 * PLm.wd_off.std(), 100 * PL[PL.version == "F"].wd_off.std()
    print("\n--- area-weather rules (docs/specs/2026-11-12-area-weather-design.md) ---")
    print("W1 no missing area temperature hours:", o["x"].attrs.get("missing_temp_hours", -1) == 0)
    print("W2 no regression, per-capita rules 2,3,4,5,6:", {k: ok[k] for k in (2, 3, 4, 5, 6)}, all(ok[k] for k in (2, 3, 4, 5, 6)))
    verdict = "pass" if sdM <= 2.34 else ("partial" if sdM <= 4.15 else "fail")
    print(f"W3 placebo sd of weekday off-peak level effect: M {sdM:.2f} pts ({verdict}; pass <= 2.34, partial <= 4.15; per-capita run 6.23), F {sdF:.2f}")
    print(f"W4 control swap moves the weekday peak by {100 * abs(pkM - pkF):.2f} points (< 2 needed; was 4.57):", bool(abs(pkM - pkF) < 0.02))
    print(f"W5 weekday peak M {100 * pkM:.2f}% against -7.76% (within 2 points):", bool(abs(pkM + 0.0776) < 0.02))
    print("diagnostic per-area placebo sd of weekday off-peak not computed here (areas pooled)")


if __name__ == "__main__":
    main()
