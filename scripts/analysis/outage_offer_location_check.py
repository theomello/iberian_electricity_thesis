#!/usr/bin/env python3
"""Exclusion check for the outage instrument: do thermal offers respond to a reactor
outage because of WHERE the unit is, not WHO owns it?

    .venv/bin/python scripts/analysis/outage_offer_panel.py      # input
    .venv/bin/python scripts/analysis/outage_offer_location_check.py

Hypothesis: when a reactor stops, REE needs nearby plant for voltage and constraint
management (restricciones tecnicas, paid as bid after the day-ahead market). A nearby
combined cycle expecting that call prices itself up in the day-ahead market. Owners'
plants sit near their own reactors (Endesa in Catalonia, Iberdrola in Valencia), so
the own-firm dose would pick this up and violate the exclusion restriction.

Test: reduced forms of thermal offers on the own-firm dose AND the dose of reactors
within R km of the unit, whoever owns them. Unit x week and technology x date x hour
effects, week clusters, as in outage_offer_test.py. Coordinates from JRC-PPDB (thermal
units through `jrc_cab_match`, reactors by name); 86 of the panel's 97 thermal units
have one. Result in `notes/rq-reactor-outages.md` §6.

Writes outputs/tables/outage_offer_location_check.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from midday_hydro_iv import ols  # noqa: E402
from outage_offer_test import demean  # noqa: E402

REACTOR_JRC = {"ALZ1": "ALMARAZ 1", "ALZ2": "ALMARAZ 2", "ASC1": "ASCO 1", "ASC2": "ASCO 2",
               "COF1": "COFRENTES", "TRL1": "TRILLO", "VAN2": "VANDELLOS"}
RADII = (150, 300)


def km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def coords() -> tuple[pd.DataFrame, pd.DataFrame]:
    j = pd.concat([pd.read_parquet(ROOT / f"data/jrc_ppdb/jrc_{c}_units.parquet") for c in ("spain", "portugal")])
    jp = j.dropna(subset=["lat"]).drop_duplicates("eic_p").set_index("eic_p")[["lat", "lon"]]
    m = pd.read_parquet(ROOT / "data/jrc_ppdb/jrc_cab_match.parquet", columns=["unit", "jrc_eic_p"])
    u = m.join(jp, on="jrc_eic_p").dropna(subset=["lat"])[["unit", "lat", "lon"]].drop_duplicates("unit")
    js = j[j.name_g.isin(REACTOR_JRC.values())].drop_duplicates("name_g").set_index("name_g")
    r = pd.DataFrame({"reactor": list(REACTOR_JRC),
                      "lat": [js.lat[v] for v in REACTOR_JRC.values()],
                      "lon": [js.lon[v] for v in REACTOR_JRC.values()]})
    return u, r


def main() -> int:
    u, r = coords()
    d = pd.read_parquet(ROOT / "outputs/tables/outage_offer_panel.parquet",
                        columns=["unit", "group", "cls", "date", "hour", "o25", "o50", "off_share", "X",
                                 "dose_unpl", "dose_plan", "wk"])
    d = d[d.cls.isin(["ccgt", "coal"])].merge(u, on="unit")
    print(f"thermal unit-hours with coordinates: {len(d):,}, units {d.unit.nunique()}")

    # local (date, hour) -> UTC hour, as the panel builder maps them
    s = pd.read_parquet(ROOT / "outputs/tables/solar_instrument.parquet",
                        columns=["date", "period", "resolution_min", "utc_timestamp"])
    s["date"] = pd.to_datetime(s.date)
    s["hour"] = (s.period - 1) // (60 // s.resolution_min)
    s["utc"] = pd.to_datetime(s.utc_timestamp, utc=True).dt.floor("h")
    s = s.groupby(["date", "hour"], as_index=False).utc.first()
    d = d.merge(s, on=["date", "hour"])

    h = pd.read_parquet(ROOT / "outputs/tables/reactor_outage_hours.parquet",
                        columns=["unit", "utc", "cls", "lost_decl_mw"])
    h = h[h.cls.isin(["unplanned", "planned"]) & (h.lost_decl_mw > 0)]
    lost = h.pivot_table(index="utc", columns=["cls", "unit"], values="lost_decl_mw", aggfunc="sum").fillna(0) / 1000

    units = d[["unit", "lat", "lon"]].drop_duplicates("unit")
    for R in RADII:
        for c, tag in (("unplanned", "unpl"), ("planned", "plan")):
            near = {}
            for row in units.itertuples():
                dist = km(row.lat, row.lon, r.lat.to_numpy(), r.lon.to_numpy())
                rs = [x for x, k in zip(r.reactor, dist) if k <= R and (c, x) in lost.columns]
                near[row.unit] = rs
            col = f"near{R}_{tag}"
            vals = np.zeros(len(d))
            for un, rs in near.items():
                if not rs:
                    continue
                idx = np.flatnonzero(d.unit.to_numpy() == un)
                ser = lost[[(c, x) for x in rs]].sum(axis=1)
                vals[idx] = ser.reindex(d.utc.iloc[idx]).fillna(0).to_numpy()
            d[col] = vals
        n_near = {un: len(rs) for un, rs in near.items()}
        print(f"  R={R} km: units with a reactor nearby {sum(v > 0 for v in n_near.values())} of {len(n_near)}")

    d["uw"] = d.unit + "_" + d.wk.astype(str)
    d["cdh"] = d.cls + "_" + d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    ys = ["o25", "o50", "off_share", "X"]
    zs = ["dose_unpl", "dose_plan"] + [f"near{R}_{t}" for R in RADII for t in ("unpl", "plan")]
    d = d.dropna(subset=ys + zs)
    print(f"complete rows: {len(d):,}")
    print("corr(own unplanned dose, near150 unplanned):",
          round(float(np.corrcoef(d.dose_unpl, d.near150_unpl)[0, 1]), 3))
    M = demean(d[ys + zs].to_numpy(float), [pd.factorize(d.uw)[0], pd.factorize(d.cdh)[0]])
    D = pd.DataFrame(M, columns=ys + zs, index=d.index)
    cl = d.wk.to_numpy()
    out = []
    for sample, mask in (("thermal", np.ones(len(d), bool)), ("ccgt", (d.cls == "ccgt").to_numpy()),
                         ("coal", (d.cls == "coal").to_numpy())):
        for y in ys:
            for spec, z in (("own only", ["dose_unpl", "dose_plan"]),
                            ("own + near150", ["dose_unpl", "dose_plan", "near150_unpl", "near150_plan"]),
                            ("own + near300", ["dose_unpl", "dose_plan", "near300_unpl", "near300_plan"])):
                b, se = ols(D.loc[mask, y].to_numpy(), D.loc[mask, z].to_numpy(), cl[mask])
                txt = "  ".join(f"{k} {b[i]:+.4f} ({se[i]:.4f})" for i, k in enumerate(z))
                print(f"  {sample:8s} {y:9s} {spec:14s} {txt}")
                out.append({"sample": sample, "y": y, "spec": spec,
                            **{f"b_{k}": b[i] for i, k in enumerate(z)}, **{f"se_{k}": se[i] for i, k in enumerate(z)}})
    pd.DataFrame(out).to_csv(ROOT / "outputs/tables/outage_offer_location_check.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
