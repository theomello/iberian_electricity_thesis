#!/usr/bin/env python3
"""Locate Spain's wind and solar farms: REE's physical units matched by name to OSM and WRI.

    .venv/bin/python scripts/fetch/fetch_osm_renewables.py     # input: OSM plants
    .venv/bin/python scripts/fetch/fetch_wri_gppd.py           # input: WRI GPPD plants
    .venv/bin/python scripts/build/build_renewable_locations.py

Framework spec §9.3, rank 3: each firm's own regional wind and solar. REE's register
of physical units (ESIOS archive 81, `esios_physical_units.parquet`, a 2026-08-12
snapshot) lists every wind and solar farm with its capacity, its REE programming unit
(`up`) and its market agent; it gives no location. OpenStreetMap and WRI's Global
Power Plant Database give locations and names. This links them by name: OSM first
(more complete and current), then GPPD for what OSM leaves unmatched. Either source
is used if present.

OWNER. REE's programming units for wind and solar never bid in OMIE (0 of 455 wind
codes are OMIE units): farms sell through their agents' aggregated units ("eolica
habilitada"). So a farm's firm comes from its REE `agent`, mapped to the firm the
inference chain gives that agent's OMIE units (`unit_agents.parquet`, modal firm per
agent): 97.6% of wind MW and 94.9% of solar. It is the 2026 snapshot, not dated, and
for representatives (Nexus, Ignis, Gesternova) it is the agent that bids, not the owner.

MATCH. Names are normalised (accents and punctuation stripped, boilerplate such as
"parque eolico", "P.E.", "planta fotovoltaica", "FV", "PSF" dropped) to a root and
a trailing unit number. A REE farm and an OSM plant of the same source pair when:
  - their roots agree exactly, or difflib similarity >= MIN_SIM;
  - unit numbers do not disagree (both present and different blocks the pair);
  - capacities, when the candidate has one, are within a factor CAP_FACTOR for an
    exact root and FUZZY_CAP for a fuzzy one (a fuzzy pair needs a capacity);
  - WRI candidates are Spanish plants only (REE's register is Spain's);
  - the pairing is the best on both sides and unique (ties are left unmatched).
Exact-root pairs are taken first, then fuzzy pairs among what is left.

REGION. Each located farm gets its autonomous community from Eurostat's NUTS 2021
polygons (`lib/regions.py`), with ESIOS's id for that region, so located capacity can
be set against ESIOS's installed capacity by region (indicators 1485 wind, 1486 PV).

OUTPUT (data/osm/):
  renewable_unit_locations.parquet   uf, up, tech, max_power_mw, descr_long, osm_id,
                                     osm_name, osm_mw, lat, lon, method, sim,
                                     source (osm / wri), agent, firm, nuts_id, country,
                                     region, esios_geo_id, region_how
Coverage is printed by technology, by the owner group of the farm's OMIE unit, and by
region against ESIOS's capacity. Data (c) OpenStreetMap contributors, ODbL 1.0.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from regions import locate  # noqa: E402

DATA = ROOT / "data"
OSM = DATA / "osm/osm_renewable_plants.parquet"
WRI = DATA / "wri/wri_gppd_iberia.parquet"
REG = DATA / "esios/esios_physical_units.parquet"
OUT = DATA / "osm/renewable_unit_locations.parquet"
TECH = {"Eólica terrestre": "wind", "Eólica marina": "wind", "Solar fotovoltaica": "solar", "Solar térmica": "solar"}
MIN_SIM = 0.85
CAP_FACTOR = 2.0
FUZZY_CAP = 1.35
BOILER = [r"\bPARQUES?\b", r"\bEOLIC[OA]S?\b", r"\bP\s?E\b", r"\bPE\b", r"\bPLANTAS?\b", r"\bSOLAR(ES)?\b",
          r"\bFOTOVOLTAIC[OA]S?\b", r"\bFV\b", r"\bPSFV?\b", r"\bHSF\b", r"\bINSTALACION(ES)?\b", r"\bCENTRAL\b",
          r"\bTERMOSOLAR\b", r"\bCSP\b", r"\bHUERTO\b", r"\bWIND ?FARM\b", r"\bSOLAR ?FARM\b", r"\bPV\b",
          r"\bDE\b", r"\bDEL\b", r"\bLA\b", r"\bEL\b", r"\bLOS\b", r"\bLAS\b", r"\bY\b", r"\bDA\b",
          r"\bDO\b"]
ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}


def norm(s) -> tuple[str, str | None]:
    """(root, unit number) of a farm name."""
    if not isinstance(s, str):
        return "", None
    s = "".join(c for c in unicodedata.normalize("NFD", s.upper()) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = " ".join(ROMAN.get(t, t) for t in s.split())
    for b in BOILER:
        s = re.sub(b, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(.*?)\s*(\d+)$", s)
    if m and m.group(1):
        return m.group(1).strip(), m.group(2)
    return s, None


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    r = pd.read_parquet(REG)
    r = r[r.tech.isin(TECH)].copy()
    r["src"] = r.tech.map(TECH)
    r["root"], r["num"] = zip(*r.descr_long.map(norm))
    parts = []
    if OSM.exists():
        o = pd.read_parquet(OSM)
        o = o[o.name.notna() & o.lat.notna() & o.source.notna()].copy()
        o["src"] = o.source.str.contains("wind").map({True: "wind", False: "solar"})
        parts.append(o.assign(origin="osm", osm_id="osm" + o.osm_id.astype(str))[
            ["origin", "osm_id", "name", "mw", "lat", "lon", "src"]])
    if WRI.exists():
        w = pd.read_parquet(WRI)
        w = w[w.primary_fuel.isin(["Wind", "Solar"]) & w.country.eq("ESP")].copy()
        parts.append(pd.DataFrame({"origin": "wri", "osm_id": "wri" + w.gppd_idnr.astype(str), "name": w.name,
                                   "mw": w.capacity_mw, "lat": w.latitude, "lon": w.longitude,
                                   "src": w.primary_fuel.str.lower()}))
    o = pd.concat(parts, ignore_index=True)
    o["root"], o["num"] = zip(*o.name.map(norm))
    return r[r.root.str.len() >= 3], o[o.root.str.len() >= 3]


def ok_pair(rn, on, rmw, omw, fuzzy: bool = False) -> bool:
    if isinstance(rn, str) and isinstance(on, str) and rn != on:
        return False
    has = pd.notna(omw) and omw > 0
    if fuzzy and not has:
        return False
    f = FUZZY_CAP if fuzzy else CAP_FACTOR
    if has and not (1 / f <= rmw / omw <= f):
        return False
    return True


def unique_best(c: pd.DataFrame) -> pd.DataFrame:
    """Keep pairs that are each side's single best candidate."""
    c = c.sort_values("sim", ascending=False)
    best_r = c.groupby("uf").sim.transform("max")
    best_o = c.groupby("osm_id").sim.transform("max")
    c = c[(c.sim == best_r) & (c.sim == best_o)]
    c = c[~c.duplicated("uf", keep=False) & ~c.duplicated("osm_id", keep=False)]
    return c


def match(r: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
    """OSM first; GPPD for the REE farms OSM leaves unmatched."""
    out = []
    for origin in ("osm", "wri"):
        oo = o[o.origin == origin]
        if oo.empty:
            continue
        done = set(pd.concat(out).uf) if out else set()
        m = match_one(r[~r.uf.isin(done)], oo)
        out.append(m.assign(source=origin))
    return pd.concat(out, ignore_index=True)


def match_one(r: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for src in ("wind", "solar"):
        rs, os_ = r[r.src == src], o[o.src == src]
        ex = rs.merge(os_, on="root", suffixes=("", "_o"))
        ex = ex[[ok_pair(a, b, c, d) for a, b, c, d in zip(ex.num, ex.num_o, ex.max_power_mw, ex.mw)]]
        ex = unique_best(ex.assign(sim=1.0))
        rows.append(ex.assign(method="exact root"))
        rest_r = rs[~rs.uf.isin(ex.uf)]
        rest_o = os_[~os_.osm_id.isin(ex.osm_id)]
        cand = []
        oroots = rest_o.root.to_numpy()
        for row in rest_r.itertuples():
            # cheap prefilter: share the first three letters
            m = np.array([x[:3] == row.root[:3] for x in oroots])
            for j in np.flatnonzero(m):
                sim = SequenceMatcher(None, row.root, oroots[j]).ratio()
                if sim >= MIN_SIM:
                    ob = rest_o.iloc[j]
                    if ok_pair(row.num, ob.num, row.max_power_mw, ob.mw, fuzzy=True):
                        cand.append({"uf": row.uf, "osm_id": ob.osm_id, "sim": sim})
        if cand:
            cf = unique_best(pd.DataFrame(cand))
            fz = cf.merge(rest_r, on="uf").merge(rest_o, on="osm_id", suffixes=("", "_o"))
            rows.append(fz.assign(method="fuzzy root"))
    m = pd.concat(rows, ignore_index=True)
    return m.rename(columns={"name": "osm_name", "mw": "osm_mw"})[
        ["uf", "up", "tech", "max_power_mw", "descr_long", "osm_id", "osm_name", "osm_mw", "lat", "lon", "method", "sim"]]



def main() -> int:
    r, o = load()
    print(f"REE farms with a usable name: {len(r):,} ({r.max_power_mw.sum() / 1000:,.1f} GW); "
          f"OSM plants with a name: {len(o):,}")
    m = match(r, o)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    m.to_parquet(OUT, index=False)
    reg = pd.read_parquet(REG)
    reg = reg[reg.tech.isin(TECH)].copy()
    reg["matched"] = reg.uf.isin(m.uf)
    print(f"\nmatched {len(m):,} farms ({m.groupby(['source', 'method']).size().to_dict()})")
    cov = reg.groupby("tech").apply(lambda g: pd.Series({"farms": len(g), "GW": g.max_power_mw.sum() / 1000,
                                                         "matched_GW": g[g.matched].max_power_mw.sum() / 1000}),
                                    include_groups=False)
    cov["share"] = cov.matched_GW / cov.GW
    print("\ncoverage by technology:\n" + cov.round(2).to_string())
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    agent_firm = ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0])
    reg["firm"] = reg.agent.map(agent_firm)
    g = reg.groupby(["firm", "tech"]).apply(
        lambda x: pd.Series({"GW": x.max_power_mw.sum() / 1000,
                             "located": x[x.matched].max_power_mw.sum() / x.max_power_mw.sum()
                             if x.max_power_mw.sum() > 0 else np.nan}),
        include_groups=False).unstack("tech")
    g = g.loc[g["GW"].sum(axis=1).sort_values(ascending=False).index]
    print("\ncoverage by the farm's agent's firm (2026 snapshot), largest 15:\n" + g.head(15).round(2).to_string())
    m = m.merge(reg[["uf", "agent", "firm"]], on="uf", how="left")
    r = locate(m.lat, m.lon)
    m = pd.concat([m, r.drop(columns="how").assign(region_how=r.how)], axis=1)
    m.to_parquet(OUT, index=False)
    print(f"\nregion of the located farms: {m.region_how.value_counts().to_dict()}, "
          f"country {m.country.value_counts(dropna=False).to_dict()}")
    cap = pd.read_parquet(DATA / "esios/esios_installed_capacity.parquet")
    cap = cap[cap.indicator_id.isin([1485, 1486]) & (cap.datetime.str[:7] == "2026-08")]
    cap = cap.pivot_table(index=["geo_id", "geo_name"], columns="indicator_id", values="value").reset_index()
    loc = m.assign(t=m.tech.map(TECH)).pivot_table(index="esios_geo_id", columns="t", values="max_power_mw",
                                                    aggfunc="sum")
    cap = cap.join(loc, on="geo_id")
    tab = pd.DataFrame({"region": cap.geo_name, "wind_GW": cap[1485] / 1000,
                        "wind_located": cap.get("wind") / cap[1485], "pv_GW": cap[1486] / 1000,
                        "pv_located": cap.get("solar") / cap[1486]}).sort_values("wind_GW", ascending=False)
    print("\nlocated share of ESIOS's capacity by region, August 2026 (REE's register is a 2026-08-12 snapshot):\n"
          + tab[tab.wind_GW + tab.pv_GW > 0.05].round(2).to_string(index=False))
    print("\na sample of fuzzy matches to read:")
    print(m[m.method == "fuzzy root"].sample(min(15, (m.method == "fuzzy root").sum()), random_state=0)[
        ["descr_long", "osm_name", "max_power_mw", "osm_mw", "sim"]].to_string(index=False))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
