"""Area-weather rerun of the per-capita area panel (docs/specs/2026-11-12-area-weather-design.md).

The only change from tou_area_panel_pc.py is the temperature fed to each area's LASSO: the area's own
population-weighted MERRA-2 temperature instead of one national series. Spanish area a (and its variants) uses
area a's series at Madrid local hours; the Portuguese regulated unit and REN national use the Portuguese area at
Lisbon local hours; ESIOS 352 uses the pre-window-load-weighted mean of the five Spanish areas.
Writes outputs/tables/tou_area_panel_pcw_{effects,placebo,elasticity,ddd}.csv and prints the weather rules W1-W5.

Reusable: AREA_WEATHER, the output prefix and the error cache are the only things tied to this run; point them at
another temperature source (or another country's areas) and the design runs unchanged.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_area_panel_pc as PC  # noqa: E402
import tou_did as T  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

AREAS = AP.AREAS
PANEL = T.ROOT / "outputs" / "tables" / "regulated_area_panel"
AREA_WEATHER = PANEL / "area_temperature_merra2_hourly.parquet"
ERA5_AREA = PANEL / "area_temperature_hourly.parquet"
PREFIX = "tou_area_panel_pcw"
CACHE = T.ROOT / "data" / "cache_tou" / "area_panel_pcw_errors.parquet"
TZ = {a: "Europe/Madrid" for a in AREAS} | {"PT": "Europe/Lisbon"}


def local_series(w, area):
    """Hourly temperature of an area indexed by local (date, hour), first pass of a repeated autumn hour kept (as T.build does)."""
    s = w[w.area == area].sort_values("utc_timestamp")
    loc = s.utc_timestamp.dt.tz_convert(TZ[area])
    d = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "t": s.temp_c.to_numpy()})
    return d.drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).t


def add_weather(x, cs, ptc):
    w = pd.read_parquet(AREA_WEATHER)
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    for a in AREAS + ["PT"]:
        x[f"tw_{a}"] = local_series(w, a).reindex(idx).to_numpy()
    pre = (x.date >= PC.START) & (x.date <= "2020-12-31")
    wt = {a: float(x.loc[pre, f"load_{a}_p48"].mean()) for a in AREAS}
    x["tw_352"] = sum(wt[a] * x[f"tw_{a}"] for a in AREAS) / sum(wt.values())
    # W1: no missing hour in the sample, and agreement with the ERA5 area series
    miss = {c: int(x.loc[x.date <= PC.POST1, c].isna().sum()) for c in [f"tw_{a}" for a in AREAS + ["PT"]] + ["tw_352"]}
    e5 = pd.read_parquet(ERA5_AREA)
    cor = {}
    for a in AREAS + ["PT"]:
        m = w[w.area == a].set_index("utc_timestamp").temp_c.rename("m").to_frame().join(e5[e5.area == a].set_index("utc_timestamp").temp_c.rename("e"), how="inner")
        cor[a] = round(float(m.corr().iloc[0, 1]), 3)
    print("W1 missing hours per series:", miss, "| correlation with ERA5 area series:", cor, flush=True)
    x.attrs["w1"] = bool(sum(miss.values()) == 0 and min(cor.values()) >= 0.9)
    print("W1 weather valid:", x.attrs["w1"], flush=True)


def get_errors(x):
    if CACHE.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for ex in ((), (2018,), (2019,)):
        for a in AREAS:
            tasks.append((f"{a}_p48", x, f"pc_{a}_p48", f"tw_{a}", "hol_es", ex))
        tasks.append(("PTU", x, "pc_PTU", "tw_PT", "hol_pt", ex))
        tasks.append(("PTREN", x, "load_pt", "tw_PT", "hol_pt", ex))
    for a in AREAS:
        tasks.append((f"{a}_pdbf", x, f"pc_{a}_pdbf", f"tw_{a}", "hol_es", ()))
        tasks.append((f"{a}_up", x, f"pc_{a}_p48_up", f"tw_{a}", "hol_es", ()))
        tasks.append((f"{a}_dn", x, f"pc_{a}_p48_dn", f"tw_{a}", "hol_es", ()))
        tasks.append((f"{a}_nq3", x, f"pc_{a}_p48_nq3", f"tw_{a}", "hol_es", ()))
    tasks.append(("E352", x, "load_352", "tw_352", "hol_es", ()))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(PC.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE)
    return errs


def main():
    o = PC.compute(get_errors, PREFIX, prep=add_weather)
    print("\n=== per-capita rules 2-8, with area weather ===", flush=True)
    ok = PC.report(o)
    R, PLm, PL = o["R"], o["PLm"], o["PL"]
    old = pd.read_csv(T.OUT / "tou_area_panel_pc_effects.csv")
    g = lambda d, spec, term: d[(d.spec == spec) & (d.term == term)].iloc[0].b
    print("\n=== weather rules ===")
    w2 = all(ok[k] for k in (2, 3, 4, 5, 6))
    print("W2 no regression (per-capita rules 2-6 hold on M):", w2, {k: ok[k] for k in (2, 3, 4, 5, 6)})
    sdm, sdf = PLm.wd_off.std(), PL[PL.version == "F"].wd_off.std()
    verdict = "PASS" if sdm <= 0.0234 else "PARTIAL" if sdm <= 0.0415 else "FAIL"
    print(f"W3 sd of weekday off-peak placebo effects: M {100 * sdm:.2f} pts, F {100 * sdf:.2f} (pass <= 2.34, partial <= 4.15; previous 6.23 / 3.66): {verdict}")
    gap = abs(g(R, "M weighted", "wd_peak") - g(R, "F REN control", "wd_peak"))
    print(f"W4 control gap, weekday peak M vs F: {100 * gap:.2f} points (< 2 needed; previously 4.57):", bool(gap < 0.02))
    shift = abs(g(R, "M weighted", "wd_peak") - g(old, "M weighted", "wd_peak"))
    print(f"W5 weekday peak M {100 * g(R, 'M weighted', 'wd_peak'):.2f}% against previous {100 * g(old, 'M weighted', 'wd_peak'):.2f}%: moved {100 * shift:.2f} points (< 2 needed):", bool(shift < 0.02))
    # diagnostics: per-area placebo sd of weekday off-peak, this run against the national-temperature run
    oldpl = pd.read_csv(T.OUT / "tou_area_panel_pc_placebo.csv")
    print("diagnostic: weekday off-peak placebo sd by version, weather run vs national-temperature run:",
          {v: (round(100 * PL[PL.version == v].wd_off.std(), 2), round(100 * oldpl[oldpl.version == v].wd_off.std(), 2)) for v in ("M", "F")})


if __name__ == "__main__":
    main()
