#!/usr/bin/env python3
"""Thermal offers on X with WHERE the firm's wind blows as instrument.

    .venv/bin/python scripts/fetch/fetch_esios_spain.py --provinces --capacity   # input: wind by province
    .venv/bin/python scripts/build/build_renewable_locations.py                  # input: farms by region
    .venv/bin/python scripts/analysis/outage_offer_panel.py                      # input: offers, X, doses
    .venv/bin/python scripts/analysis/regional_wind_offer_test.py

Framework spec §9.3, rank 3. On an hour when Galicia is windy and Aragón calm, a firm
whose farms sit in Galicia sells more than one whose farms sit in Aragón, at the same
national wind. The instrument is that difference:

    Wdev_gt = sum over regions r of  K_gr x (cf_rt - cf_t)          (GW)

K_gr   group g's located onshore wind capacity in region r (renewable_unit_locations,
       REE's 2026-08-12 register; owner via the farm's agent; 54% of wind located)
cf_rt  region r's capacity factor in UTC hour t: measured wind output of its provinces
       (ESIOS 1159) over its installed wind capacity that month (ESIOS 1485)
cf_t   the same for the peninsula: national wind relative to national capacity

WHY THE DEVIATION AND NOT THE LEVEL. A firm's own wind, sum K_gr cf_rt, moves mostly
with national wind, and national wind moves each firm's n in its own way: it pushes
the firm's gas and hydro out of the dispatch, by more for EDP than for Repsol
(`notes/rq-forecast-first-stage.md`). Technology x date x hour effects absorb only
what is common to every firm. So the level carries each firm's displacement and is not
an own-wind instrument (it gave F 0.1 with the level of the forecast version). The
deviation is zero whenever wind is spread across regions as capacity is, and the
controls below take out each group's own response to national wind, solar and demand.

Two versions of cf:
  real   as measured
  fc     REE's D-1 peninsular wind forecast (ESIOS 1777, published before offers
         close) split across regions by the measured shares: the national level is
         what bidders knew, the split across regions is realised.
Measured output includes what farms shed at low prices; a region's output sums every
owner's farms, so one firm's shedding barely moves it.

CONTROLS, partialled out after the fixed effects: group x REE's D-1 forecast of wind,
of solar (1779) and of demand (1775), one slope per group and forecast.

EXCLUSION. A region's wind may also reach a thermal unit's offer through local grid
constraints (restricciones técnicas), not through its owner's n. Two answers:
  A  technology x date x hour effects, plus the capacity factor in the unit's own
     region as a control (units outside the Spanish wind regions are dropped);
  B  technology x region x date x hour effects: a unit is compared only with units of
     the same technology in the same region and hour, owned by other groups.
Units take their region from JRC coordinates (`jrc_cab_match`).

THE 2026 SNAPSHOT. Farms built after 2018 count from the start. That is error in the
instrument, not a reason for it to be correlated with offers; the sample from 2022 on
is reported as a check.

Unit x week effects, week clusters. Thermal units (combined cycle, coal) with an
implied cost, from 2019-01-01 (the forecasts' start) to the panel's end; both versions
on the same sample. Writes outputs/tables/regional_wind_offer_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from midday_hydro_iv import ols  # noqa: E402
from outage_offer_test import demean  # noqa: E402
from outage_rain_offer_test import iv  # noqa: E402
from regions import ESIOS_GEO, locate, province_nuts2  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
PANEL = TABLES / "outage_offer_panel.parquet"
PROV = DATA / "esios/esios_measured_generation_province.parquet"
OUT = TABLES / "regional_wind_offer_results.csv"
START = "2019-01-01"      # REE's D-1 forecasts (1775, 1777, 1779) start here
MIN_PROVINCES = 30        # an hour with fewer reporting provinces is a gap, not calm
MIN_CAP_MW = 10.0         # Madrid reports wind output against ~0 MW of capacity
FORECASTS = {"F_wind": 1777, "F_solar": 1779, "F_demand": 1775}


def utc_hours(d: pd.DataFrame) -> pd.Series:
    return d.utc_timestamp.dt.floor("h")


def forecasts() -> pd.DataFrame:
    """utc, F_wind, F_solar, F_demand: REE's D-1 peninsular forecasts, GW."""
    out = None
    for name, i in FORECASTS.items():
        f = pd.read_parquet(DATA / f"esios/esios_{i}.parquet", columns=["value", "utc_timestamp"])
        f = f.assign(utc=utc_hours(f)).groupby("utc").value.mean().div(1000).rename(name)
        out = f.to_frame() if out is None else out.join(f, how="outer")
    return out.reset_index()


def regional_cf(fc: pd.DataFrame) -> pd.DataFrame:
    """utc, nuts_id, cf_real, cf_fc, dev_real, dev_fc: each region's wind capacity factor
    by hour, and its deviation from the peninsula's."""
    p = pd.read_parquet(PROV)
    p = p[p.indicator_id == 1159]
    p["nuts_id"] = province_nuts2(p.geo_name).to_numpy()
    p["utc"] = utc_hours(p)
    n_prov = p.groupby("utc").geo_id.nunique()
    good = n_prov.index[n_prov >= MIN_PROVINCES]
    print(f"wind by province: {p.geo_id.nunique()} provinces, {len(n_prov):,} hours, "
          f"{len(n_prov) - len(good):,} with fewer than {MIN_PROVINCES} provinces dropped")
    out = (p[p.utc.isin(good)].groupby(["utc", "nuts_id"]).value.sum()
           .unstack(fill_value=0.0).stack().rename("out_mwh").reset_index())
    cap = pd.read_parquet(DATA / "esios/esios_installed_capacity.parquet")
    cap = cap[cap.indicator_id == 1485]
    geo_nuts = {v: k for k, v in ESIOS_GEO.items()}
    cap = pd.DataFrame({"nuts_id": cap.geo_id.map(geo_nuts), "ym": cap.datetime.str[:7], "cap_mw": cap.value})
    out["ym"] = out.utc.dt.tz_convert("Europe/Madrid").dt.strftime("%Y-%m")
    out = out.merge(cap, on=["nuts_id", "ym"], how="left")
    out = out[out.cap_mw >= MIN_CAP_MW]
    g = out.groupby("utc")
    out["tot_out"], out["tot_cap"] = g.out_mwh.transform("sum"), g.cap_mw.transform("sum")
    out["cf_real"] = out.out_mwh / out.cap_mw
    out = out.merge(fc[["utc", "F_wind"]], on="utc", how="left")
    out["cf_fc"] = out.F_wind * 1000 * out.out_mwh / out.tot_out / out.cap_mw
    out["dev_real"] = out.cf_real - out.tot_out / out.tot_cap
    out["dev_fc"] = out.cf_fc - out.F_wind * 1000 / out.tot_cap
    if ((out.dev_real * out.cap_mw).groupby(out.utc).sum().abs() > 1e-6).any():
        raise SystemExit("capacity-weighted deviations do not sum to zero in some hour")
    print(out.groupby("nuts_id")[["cap_mw", "cf_real", "cf_fc", "dev_real"]]
          .agg(["mean", "std"]).round(3).to_string())
    return out[["utc", "nuts_id", "cf_real", "cf_fc", "dev_real", "dev_fc"]]


def own_capacity(groups) -> pd.DataFrame:
    """group, nuts_id, K_gw: located onshore wind capacity by group and region."""
    m = pd.read_parquet(DATA / "osm/renewable_unit_locations.parquet")
    m = m[(m.tech == "Eólica terrestre") & m.firm.isin(groups) & m.nuts_id.notna()]
    k = m.groupby(["firm", "nuts_id"]).max_power_mw.sum().div(1000).rename("K_gw").reset_index()
    print("\nlocated wind GW by group and region:")
    print(k.pivot_table(index="firm", columns="nuts_id", values="K_gw", fill_value=0).round(2).to_string())
    return k.rename(columns={"firm": "group"})


def unit_region() -> pd.DataFrame:
    j = pd.concat([pd.read_parquet(DATA / f"jrc_ppdb/jrc_{c}_units.parquet") for c in ("spain", "portugal")])
    jp = j.dropna(subset=["lat"]).drop_duplicates("eic_p").set_index("eic_p")[["lat", "lon"]]
    m = pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet", columns=["unit", "jrc_eic_p"])
    u = m.join(jp, on="jrc_eic_p").dropna(subset=["lat"]).drop_duplicates("unit")
    u["unit_nuts"] = locate(u.lat, u.lon).nuts_id.to_numpy()
    return u[["unit", "unit_nuts"]]


def panel() -> tuple[pd.DataFrame, list[str]]:
    fc = forecasts()
    cf = regional_cf(fc)
    d = pd.read_parquet(PANEL, columns=["unit", "group", "cls", "date", "hour", "o25", "o50", "c_bid", "X",
                                        "dose_unpl", "dose_plan", "wk"])
    d = d[d.cls.isin(["ccgt", "coal"]) & d.c_bid.notna() & (d.date >= START)].copy()
    k = own_capacity(d.group.unique())
    s = pd.read_parquet(TABLES / "solar_instrument.parquet", columns=["date", "period", "resolution_min", "utc_timestamp"])
    s["date"] = pd.to_datetime(s.date)
    s["hour"] = (s.period - 1) // (60 // s.resolution_min)
    s["utc"] = pd.to_datetime(s.utc_timestamp, utc=True).dt.floor("h")
    s = s.groupby(["date", "hour"], as_index=False).utc.first()
    d = d.merge(s, on=["date", "hour"])
    d = d[d.utc.isin(cf.utc.unique())]

    w = k.merge(cf, on="nuts_id")
    for v in ("real", "fc"):
        w[f"W_{v}"] = w.K_gw * w[f"cf_{v}"]
        w[f"Wdev_{v}"] = w.K_gw * w[f"dev_{v}"]
    inst = ["W_real", "W_fc", "Wdev_real", "Wdev_fc"]
    w = w.groupby(["group", "utc"])[inst].sum(min_count=1).reset_index()
    d = d.merge(w, on=["group", "utc"], how="left")
    d.loc[~d.group.isin(k.group), inst] = 0.0         # no located wind: no own wind
    d = d.merge(fc, on="utc", how="left")
    print("\nown wind by group, GW of expected output (level and regional deviation):")
    print(d.groupby("group")[inst].agg(["mean", "std"]).round(3).to_string())
    print("\ncorrelation of each group's Wdev_fc with the national wind forecast:")
    print(d[d.group.isin(k.group)].groupby("group").apply(
        lambda x: x.Wdev_fc.corr(x.F_wind), include_groups=False).round(3).to_string())

    d = d.merge(unit_region(), on="unit", how="left")
    d = d.merge(cf[["utc", "nuts_id", "cf_real"]].rename(columns={"nuts_id": "unit_nuts", "cf_real": "cf_unit"}),
                on=["unit_nuts", "utc"], how="left")
    d["oc50"] = d.o50 - d.c_bid
    d["uw"] = d.unit + "_" + d.wk.astype(str)
    dh = d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    d["cdh"] = d.cls + "_" + dh
    d["crdh"] = d.cls + "_" + d.unit_nuts.fillna("none") + "_" + dh
    ctrl = []
    for g in sorted(d.group.unique()):
        on = (d.group == g).to_numpy(float)
        for f in FORECASTS:
            d[f"{f}_{g}"] = on * d[f].to_numpy()
            ctrl.append(f"{f}_{g}")
    return d, ctrl


def partial_out(T: np.ndarray, C: np.ndarray) -> np.ndarray:
    """T less its projection on C, through an orthonormal basis of C's scaled columns.
    Least squares on the raw columns is unstable here: after the fixed effects some
    group x forecast columns are nearly zero or collinear, and the residual came out
    larger than T itself."""
    nrm = np.linalg.norm(C, axis=0)
    C = C[:, nrm > 1e-9 * nrm.max()] / nrm[nrm > 1e-9 * nrm.max()]
    Q, _ = np.linalg.qr(C)
    R = T - Q @ (Q.T @ T)
    if (np.linalg.norm(R, axis=0) > np.linalg.norm(T, axis=0) * (1 + 1e-9)).any():
        raise SystemExit("partialling out the controls increased a column's norm")
    return R


def main() -> int:
    d, ctrl = panel()
    ys, inst = ["o25", "o50", "oc50"], ["W_real", "W_fc", "Wdev_real", "Wdev_fc"]
    rows = []
    for period, lo in (("2019+", None), ("2022+", "2022-01-01")):
        for fe, fe_col, own in (("A: tech x date x hour", "cdh", True),
                                ("B: tech x region x date x hour", "crdh", False)):
            e = d if lo is None else d[d.date >= lo]
            need = ys + ["X", "dose_unpl", "dose_plan"] + inst + ["F_wind", "F_solar", "F_demand"]
            e = e.dropna(subset=need + (["cf_unit"] if own else ["unit_nuts"])).reset_index(drop=True)
            if not own:     # a cell with one group's units identifies nothing
                e = e[e.groupby("crdh").group.transform("nunique") > 1].reset_index(drop=True)
            cc = [c for c in ctrl if e[c].abs().sum() > 0] + (["cf_unit"] if own else [])
            cols = ys + ["X", "dose_unpl", "dose_plan"] + inst
            M = demean(e[cols + cc].to_numpy(float), [pd.factorize(e.uw)[0], pd.factorize(e[fe_col])[0]])
            C, T = M[:, len(cols):], M[:, :len(cols)]
            T = partial_out(T, C)
            D = pd.DataFrame(T, columns=cols)
            print(f"\n{period}, {fe}: {len(e):,} unit-hours, {e.unit.nunique()} units, {e.group.nunique()} groups, "
                  f"{len(cc)} controls; within sd X {D.X.std():.2f}, Wdev_fc {D.Wdev_fc.std():.4f}, "
                  f"W_fc {D.W_fc.std():.4f}")
            for z in inst:
                b, se = ols(D.X.to_numpy(), D[[z]].to_numpy(), e.wk.to_numpy())
                print(f"  first stage X on {z:9s}: {b[0]:+.3f} ({se[0]:.3f}), F {(b[0] / se[0]) ** 2:.1f}")
                rows.append({"sample": period, "effects": fe, "y": "X (first stage)", "instruments": z,
                             "b": b[0], "se": se[0], "F": (b[0] / se[0]) ** 2, "n": len(e)})
            specs = [("regional fc", ["Wdev_fc"]), ("regional real", ["Wdev_real"]),
                     ("regional fc + outages", ["Wdev_fc", "dose_unpl", "dose_plan"])]
            for y in ys:
                for lab, zs in specs:
                    rows.append(iv(e, D, y, zs, f"{period} {lab}", fe, "wk"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
