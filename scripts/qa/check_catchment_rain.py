#!/usr/bin/env python3
"""Rain over each hydro plant's upstream catchment: geometry, coverage, and fit to inflows.

    .venv/bin/python scripts/qa/check_catchment_rain.py

Checks `build/build_catchment_rain.py`:
  - upstream tracing on a toy river network (a confluence and a branch);
  - every JRC plant has a catchment, and its area (summed sub-basins) equals
    HydroBASINS' own UP_AREA of the plant's sub-basin;
  - cell weights are positive and the daily series is complete 1991-01-01 onwards;
  - rainfall is plausible across the peninsula: the north-west far wetter than the
    south;
  - for Portuguese reservoirs with measured inflow (SNIRH), monthly catchment rain
    tracks monthly inflow.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_catchment_rain import CATCH, RAIN, WEIGHTS, upstream  # noqa: E402

SNIRH = ROOT / "data/snirh/snirh_reservoir_series.parquet"
# JRC plant name fragment -> SNIRH station name fragment (the dam the plant sits on)
INFLOW_PAIRS = {"ALTO LINDOSO": "Alto Lindoso", "CASTELO DO BODE": "Castelo do Bode",
                "AGUIEIRA": "Aguieira", "ALQUEVA": "Alqueva", "ALTO RABAGAO": "Alto Rabagão",
                "MIRANDA": "Miranda", "CANICADA": "Caniçada", "CABRIL": "Cabril",
                "PARADELA": "Paradela", "VILARINHO": "Vilarinho das Furnas"}


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    #   1 -> 3 <- 2 ; 3 -> 5 ; 4 -> 5 ; 5 -> 0 (sea)
    toy = pd.DataFrame({"HYBAS_ID": [1, 2, 3, 4, 5], "NEXT_DOWN": [3, 3, 5, 5, 0]})
    check(upstream(toy, 3) == {1, 2, 3} and upstream(toy, 5) == {1, 2, 3, 4, 5} and upstream(toy, 1) == {1},
          "upstream: a confluence and a branch")
    check(upstream(toy.assign(ENDO=[0, 1, 0, 0, 0]), 5) == {1, 3, 4, 5},
          "upstream: an endorheic sub-basin is left out")

    for p in (CATCH, WEIGHTS, RAIN):
        if not p.exists():
            check(False, f"{p.relative_to(ROOT)} missing -- run scripts/build/build_catchment_rain.py")
    if fails:
        print(f"{len(fails)} failure(s)")
        return 1
    c = pd.read_parquet(CATCH)
    w = pd.read_parquet(WEIGHTS)
    r = pd.read_parquet(RAIN)
    jrc = pd.read_parquet(ROOT / "data/jrc_hydro/jrc_hydro_plants.parquet")
    print(f"{len(c)} plants, {w.plant_id.nunique()} with weights, {r.plant_id.nunique()} with rain, "
          f"{r.date.min().date()} -> {r.date.max().date()}")
    check(set(c.plant_id) == set(jrc.id), "every JRC plant has a catchment row")
    ok = c.dropna(subset=["catch_km2"])
    rel = (ok.catch_km2 / ok.up_area_km2 - 1).abs()
    check(len(ok) == len(c) and rel.max() < 0.01,
          f"catchment area = HydroBASINS UP_AREA within 1% (worst {rel.max():.4f}; {len(c) - len(ok)} without)")
    check(bool((w.weight > 0).all()) and set(w.plant_id) == set(c.plant_id), "every plant has positive cell weights")
    days = pd.date_range(r.date.min(), r.date.max())
    n = r.groupby("plant_id").date.nunique()
    check(r.date.min() == pd.Timestamp("1991-01-01") and (n == len(days)).all() and r.rr.notna().all(),
          f"complete daily series per plant ({n.min()}..{n.max()} of {len(days)} days)")
    annual = r[r.date.dt.year.between(1991, 2020)].groupby("plant_id").rr.mean() * 365.25
    a = c.set_index("plant_id").join(annual.rename("mm"))
    nw = a[(a.lat > 41.5) & (a.lon < -7.5)].mm.median()
    so = a[a.lat < 38.5].mm.median()   # the south: Guadalquivir, lower Guadiana, Segura, Andalusia
    print(f"      median annual rain over catchments: north-west {nw:.0f} mm ({((a.lat > 41.5) & (a.lon < -7.5)).sum()} "
          f"plants), south {so:.0f} mm ({(a.lat < 38.5).sum()} plants)")
    check(nw > 2 * so, "the north-west's catchments get more than twice the south's rain")

    if SNIRH.exists():
        s = pd.read_parquet(SNIRH, columns=["station", "parameter", "date", "value", "suspect"])
        s = s[(s.parameter == "inflow_m3s") & ~s.suspect]
        corrs = {}
        for jn, sn in INFLOW_PAIRS.items():
            pid = jrc.loc[jrc.name.str.upper().str.contains(jn), "id"]
            st = s[s.station == sn]
            if pid.empty or st.empty:
                continue
            rm = r[r.plant_id == pid.iloc[0]].set_index("date").rr.resample("MS").sum()
            im = st.groupby(pd.to_datetime(st.date)).value.mean().resample("MS").mean()
            j = pd.concat([rm.rename("rain"), im.rename("inflow")], axis=1).dropna()
            corrs[jn] = float(np.corrcoef(j.rain, j.inflow)[0, 1]) if len(j) > 24 else np.nan
        print(f"      monthly catchment rain vs SNIRH inflow, correlation: { {k: round(v, 2) for k, v in corrs.items()} }")
        good = [v for v in corrs.values() if np.isfinite(v)]
        check(len(good) >= 3 and np.median(good) >= 0.5,
              f"monthly rain tracks measured inflow at Portuguese reservoirs (median corr >= 0.5 over {len(good)})")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
