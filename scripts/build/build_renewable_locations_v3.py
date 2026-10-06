#!/usr/bin/env python3
"""Third pass: the autonomous community of onshore wind farms still unlocated, from MITECO's register.

    .venv/bin/python scripts/build/build_renewable_locations_v2.py   # input: the v2 file
    .venv/bin/python scripts/build/build_renewable_locations_v3.py

The instruments that use located wind (`regional_wind_offer_test.own_capacity`, and
through it `own_wind_surprise.py`) need each farm's autonomous community (NUTS 2), not
its coordinates: `own_capacity` sums `max_power_mw` by firm and `nuts_id` and never reads
lat/lon. MITECO's register of electricity producers ("Electra",
https://energia.serviciosmin.gob.es/Electra/BuscarDatos.aspx, file ElectraExp.csv,
downloaded 2026-10-06 into data/miteco/electra/raw/, latin-1, ";") lists 71,727
installations with a name and an autonomous community and nothing else: no technology,
capacity, owner or registration number. This pass gives a community to the REE wind
farms the first two passes left, by name alone. Every v2 row is kept exactly as it is.

NAMES. Both sides go through the v2 normalisation (`build_renewable_locations_v2`:
`name_key`, `ree_keys`): the same REE keys (descr_long; descr_short; `uf` only for a
farm with no name of two or more words), boilerplate and articles dropped, spaces
removed, unit number, phase letter and "ampliacion" mark read off. An Electra name is
cut before a parenthesis, a stated size ("... DE 17,55 MW DE ...") and a legal form
(", S.L"). Electra rows are sorted by what their name says:
  wind     EOLIC, AEROGENERADOR, WIND, P.E./PE, and no mark of another technology;
  other    a mark of solar, hydro, cogeneration, biomass, waste, thermal (FOTOVOLT,
           SOLAR, the PV abbreviations I.F., H.S.F., S.F., P.S., SFV, PSFV, ..., HUERTO,
           TRACKER, HIDR, COGENERA, ...), a rooftop owner (AYUNTAMIENTO, COLEGIO), or,
           for a row with no wind mark, a legal form (a company, not an installation):
           never used;
  unmarked the rest (place names, mostly small solar plants).
Rows in the Balearic and Canary Islands, Ceuta and Melilla are dropped: REE's register is
the peninsular system's (no island power station appears in it: Jinamar, Candelaria,
Alcudia, Son Reus), and a "SAN BARTOLOME" in the Canaries is not Repsol's.

RULES. For each farm, the Electra rows whose names agree with one of its keys, whose
unit number, phase letter and ampliacion mark do not disagree, taken from the first of:
  1. exact name, wind rows;
  2. exact name, unmarked rows named by two or more words;
  3. code prefix (v2's rule: the code starts exactly one name in the pool), wind rows,
     only for a farm with no exact match of any kind.
An unmarked row named by one word (CORBERA, MUDEFER, EL PORTILLO) is too often a solar
plant of that place and is not used, but it still blocks rule 3. The farm takes the
community of its rows when they all lie in ONE community; rows in two or more make it
ambiguous and it is left out (LA MUELA in 4, SAN BARTOLOME in 5, LOMA GORDA in 2). A
farm larger than all the wind ESIOS reports in that community is refused (none was).
No fuzzy names: without a capacity to check, they agreed with the located community on
only 80% of located farms (27 of 34) once nothing stronger existed; the same went for
code prefixes onto unmarked rows (10 of 15: company names such as "SEGURA INVERSIONS").

VALIDATION. The same rules run on the 745 farms v1 and v2 located; Electra's community
is compared with the one their coordinates give. 552 get an Electra community (30 more
are ambiguous): 543 agree, 98.4% (98.8% by capacity). Rule 1: 499/508; rule 2: 30/30;
rule 3: 14/14; with unit numbers on one side only: 57/57. Of the 9 disagreements, 5 are
farms within 0.3 km of the community Electra names (Campisabalos, Hijes, Somolinos,
Sierra Menera on the Guadalajara border, La Cotera on the Cantabria one), where a farm
can straddle the line. The other 4 look like errors in the earlier passes: ASOAN
"Alabe Soan" (v1, put in Extremadura; Electra: Galicia), CODES02 (v2 sibling of the
Galician Codesas; Electra: "PARQUE EOLICO CODES 2", Navarra), UFVVILA "PE VILALBA" (v2,
put in Catalonia; Electra: Galicia), COLLADO "Los Collados" (v1, Castilla y Leon;
Electra: Castilla-La Mancha, 104 km away). Checked by hand (CORRECT, DROP): ASOAN's WRI
point is a rounded placeholder (38.4000, -6.4667) and UFVVILA's OSM plant is 36.8 MW
against REE's 48.9, so both take Electra's Galicia; CODES02 is dropped, its sibling
saying Galicia and Electra Navarra; COLLADO is kept, its OSM plant matching REE's 11.2
MW exactly, so Electra's Los Collados is taken to be another farm.

OUTPUT (data/osm/):
  renewable_unit_locations_v3.parquet   the v2 rows (CORRECT and DROP applied), then the new rows; same
                                        columns. New rows: method "v3 electra"; source
                                        "electra exact", "electra exact unmarked" or
                                        "electra code prefix"; osm_name the Electra
                                        name(s); lat, lon, osm_id, osm_mw empty;
                                        nuts_id, country, region, esios_geo_id from the
                                        community; region_how "electra".

COVERAGE, measured 2026-10-06 (REE register 2026-08-12, 1,173 onshore wind farms, 32.3
GW): v2 745 farms / 22.4 GW (69.5%), v3 878 / 25.4 GW (78.6%): 133 farms, 2.95 GW added
(rule 1: 108, 2.44 GW; rule 2: 16, 0.30; rule 3: 9, 0.21). By firm, v2 -> v3:
Iberdrola 85 -> 91%, Acciona 68 -> 83%, Endesa 73 -> 82%, Naturgy 67 -> 81%, EDP 77 ->
88%, Repsol 29 -> 29%, Ignis 82 -> 91%, Galp 34 -> 49%. Against ESIOS's August 2026 wind
by community: Castilla y Leon 75 -> 81%, Aragon 66 -> 70%, Castilla-La Mancha 67 -> 73%,
Galicia 65 -> 80%, Andalucia 81 -> 90%, Navarra 50 -> 71%, Catalonia 37 -> 55%, Valencia
64 -> 73%, Asturias 64 -> 80%. Murcia reads 104% and Extremadura 110%: REE's farm
capacities there sum to slightly more than ESIOS's.
Still unlocated: 295 farms, 6.9 GW: 185 farms (4.45 GW) have only a code for a name
(Repsol's CNR/SCZ/PSAR..., HISPE's EOALP.., Gesternova's GST..); 98 (2.08 GW) have a
name Electra does not hold in a usable form; 12 (0.38 GW) have a name found in several
communities.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from regions import ESIOS_GEO  # noqa: E402
from build_renewable_locations_v2 import MIN_CODE, WIND, name_key, plain, ree_keys  # noqa: E402

DATA = ROOT / "data"
ELECTRA = DATA / "miteco/electra/raw/ElectraExp.csv"
REG = DATA / "esios/esios_physical_units.parquet"
V2 = DATA / "osm/renewable_unit_locations_v2.parquet"
OUT = DATA / "osm/renewable_unit_locations_v3.parquet"
NUTS = DATA / "gisco/nuts2_iberia.parquet"

# Electra's community names (no accents) -> NUTS 2021 level 2
COMMUNITY_NUTS = {"Galicia": "ES11", "Principado de Asturias": "ES12", "Cantabria": "ES13", "Pais Vasco": "ES21",
                  "Navarra": "ES22", "La Rioja": "ES23", "Aragon": "ES24", "Comunidad de Madrid": "ES30",
                  "Castilla y Leon": "ES41", "Castilla-La Mancha": "ES42", "Extremadura": "ES43", "Cataluna": "ES51",
                  "Comunidad Valenciana": "ES52", "Baleares": "ES53", "Andalucia": "ES61", "Region de Murcia": "ES62",
                  "Ceuta": "ES63", "Melilla": "ES64", "Canarias": "ES70"}
WIND_MARK = re.compile(r"EOLIC|AEROGENERADOR|\bWIND|\bP\s*E\b|\bPARQUE E")     # on the name, punctuation blanked
OTHER_MARK = re.compile(
    r"FOTOV|SOLAR|\bISFV?\b|\bIFV?\b|\bI\s*F\b|\bI\s*S\s*F|\bH\s*S\s*F?\b|\bS\s*F\s*V?\b|\bP\s*F\s*V?\b|\bINFV\b"
    r"|\bPSFV?\b|\bPSV\b|\bESF\b|\bC\s*F\b|\bI\s*S\b|\bP\s*S\b|\bPQUE\s*S\b|\bFV|\bPV\b|TRACKER|HUERTO|HELIO"
    r"|CUBIERTA|TEJADO|PLACAS|AUTOCONSUM|AYUNTAMIENTO|AJUNTAMENT|\bAYTO\b|COLEGIO|\bIES\b|HIDR|MINIH|\bC\s*H\b"
    r"|SALTO|COGENER|BIOMAS|BIOGAS|PURIN|TERMOSOL|TERMIC|CTCC|CICLO COMB|RESIDUO|VERTEDERO|DEPURADORA|\bEDAR\b"
    r"|\bGAS\b|DIESEL|MOTOR|GRANJA|NAVE\b|CERAMICA")
OFF_PENINSULA = {"ES53", "ES63", "ES64", "ES70"}   # REE's register is the peninsular system's
CORRECT = {"ASOAN": "ES11", "UFVVILA": "ES11"}   # earlier-pass rows Electra corrects; see the docstring
DROP = {"CODES02"}                                 # conflicting evidence, left unlocated
SOURCE = {1: "electra exact", 2: "electra exact unmarked", 3: "electra code prefix"}


def clean_electra(s: str) -> str:
    """Cut an Electra name before a stated size, a company or a parenthesis."""
    s = plain(s)
    s = re.split(r"\(", s)[0]
    s = re.split(r"\bDE\s+\d[\d.,\s]*(?:K|M)WN?\b|,\s*S\.?\s*[AL]\b|\bS\.?\s*L\.?\s*U?\b\s*$", s)[0]
    return s.strip(" ,-.")


def electra() -> pd.DataFrame:
    """Electra rows with their community, wind/neutral/other mark and name keys (one row per key)."""
    e = pd.read_csv(ELECTRA, sep=";", encoding="latin-1", dtype=str)
    unknown = set(e.AUTONOMIA.dropna()) - set(COMMUNITY_NUTS)
    if unknown:
        raise SystemExit(f"Electra community names not mapped: {sorted(unknown)}")
    e = e[e.INSTALACION.notna()].copy()
    e["nuts_id"] = e.AUTONOMIA.map(COMMUNITY_NUTS)
    e = e[~e.nuts_id.isin(OFF_PENINSULA)]
    up = e.INSTALACION.map(lambda x: re.sub(r"[^A-Z0-9 ]", " ", plain(x)))
    e["mark"] = np.where(up.str.contains(OTHER_MARK), "other", np.where(up.str.contains(WIND_MARK), "wind", "neutral"))
    # an unmarked row carrying a legal form is a company's name, not an installation's
    e.loc[e.mark.eq("neutral") & up.str.contains(r"\bS\s*[AL]\s*U?\s*$|\bS\s*[AL]\s*U?\b\s*,|\bSLU?\b|\bSAU?\b"),
          "mark"] = "other"
    e = e[e.mark != "other"]
    keys = e.INSTALACION.map(lambda s: name_key(clean_electra(s)))
    e = e[keys.notna()].copy()
    keys = keys[keys.notna()]
    for f in ("comp", "num", "letter", "amp", "dist", "alts"):
        e[f] = keys.map(lambda k: k[f])
    e["ntok"] = keys.map(lambda k: len(k["root"].split()))
    e["eid"] = e.AUTOID
    rows = e.assign(key=[[c] + a for c, a in zip(e.comp, e.alts)]).explode("key")
    return rows.drop(columns="alts").reset_index(drop=True)


def pairs(rk: pd.DataFrame, e: pd.DataFrame) -> pd.DataFrame:
    """(farm key, Electra row) pairs whose names agree: exact (tier 3) or code prefix (tier 2)."""
    pool_arr = e.comp.drop_duplicates().to_numpy().astype(str)
    out = []
    ex = rk.merge(e[["eid", "key"]].rename(columns={"key": "comp"}), on="comp")
    short = ex.kind.eq("short")
    n_in = ex.comp[short].map(lambda w: int((np.char.find(pool_arr, w) >= 0).sum()))
    ex = ex[~short | ex.index.isin(n_in[n_in == 1].index)]
    out.append(ex.assign(tier=3))
    rows = []
    for x in rk[(rk.kind == "code") & (rk.comp.str.len() >= MIN_CODE)].drop_duplicates(["uf", "comp"]).itertuples():
        hit = np.char.startswith(pool_arr, x.comp) & (pool_arr != x.comp)
        if hit.sum() == 1:
            for eid in e.eid[e.comp == pool_arr[hit][0]].unique():
                rows.append({**x._asdict(), "eid": eid, "tier": 2})
    if rows:
        out.append(pd.DataFrame(rows).drop(columns="Index"))
    p = pd.concat(out, ignore_index=True)
    er = e.drop_duplicates("eid").set_index("eid")[["INSTALACION", "nuts_id", "mark", "num", "letter", "amp", "ntok"]]
    p = p.join(er.add_prefix("e_"), on="eid")
    p = p[~(p.num.notna() & p.e_num.notna() & (p.num != p.e_num))]
    p = p[~(p.letter.notna() & p.e_letter.notna() & (p.letter != p.e_letter))]
    p = p[p.amp == p.e_amp]
    return p.drop_duplicates(["uf", "eid", "tier"])


def decide(p: pd.DataFrame) -> pd.DataFrame:
    """Per farm: the first rule with rows, and its community if the rows lie in one.

    Rules, in order: 1 exact name, wind rows; 2 exact name, unmarked rows named by two
    or more words; 3 code prefix, wind rows, only for a farm with no exact match of any
    kind. An unmarked row named by one word (CORBERA, MUDEFER, EL PORTILLO) is as often
    a solar plant or a company of that place, so it is not used; but it still blocks
    rule 3, as a better name does in v2."""
    has_exact = set(p.uf[p.tier == 3])
    rank = np.select([p.tier.eq(3) & p.e_mark.eq("wind"),
                      p.tier.eq(3) & p.e_mark.eq("neutral") & p.e_ntok.ge(2),
                      p.tier.eq(2) & p.e_mark.eq("wind") & ~p.uf.isin(has_exact)], [1, 2, 3], 9)
    p = p.assign(rank=rank)
    p = p[p["rank"] < 9]
    q = p[p["rank"] == p.groupby("uf")["rank"].transform("min")]
    q = q.assign(numrel=np.where(q.num.notna() & q.e_num.notna(), "equal",
                                 np.where(q.num.isna() & q.e_num.isna(), "both absent", "one side")))
    g = q.groupby("uf").agg(rank=("rank", "first"), n_regions=("e_nuts_id", "nunique"),
                            numrel=("numrel", "max"),
                            nuts_id=("e_nuts_id", "first"), n_rows=("eid", "nunique"),
                            names=("e_INSTALACION", lambda x: " | ".join(sorted(set(x)))[:200]))
    # strict variant for the validation: every usable exact row, wind or unmarked, in one community
    ex = p[p["rank"] <= 2].groupby("uf").e_nuts_id.nunique()
    g["exact_all_one_region"] = g.index.to_series().map(ex).fillna(0).le(1)
    g["source"] = g["rank"].map(SOURCE)
    g["sim"] = 1.0
    return g.reset_index()


def main() -> int:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 2000)
    pd.set_option("display.max_colwidth", 60)
    v2 = pd.read_parquet(V2)
    reg = pd.read_parquet(REG)
    r = reg[reg.tech == WIND].copy()
    r["located"] = r.uf.isin(v2.uf)
    e = electra()
    print(f"Electra rows usable: {e.eid.nunique():,} ({e.drop_duplicates('eid').mark.value_counts().to_dict()}); "
          f"onshore wind farms: {len(r):,}, located by v1/v2 {r.located.sum():,}")
    rk = ree_keys(r)
    d = decide(pairs(rk, e)).merge(r[["uf", "max_power_mw", "located", "descr_long", "descr_short", "agent"]], on="uf")
    # a farm larger than all the wind ESIOS reports in its community cannot be there
    cap = pd.read_parquet(DATA / "esios/esios_installed_capacity.parquet")
    cap = cap[(cap.indicator_id == 1485) & (cap.datetime.str[:7] == "2026-08")].groupby("geo_id").value.sum()
    d["region_cap_mw"] = d.nuts_id.map(ESIOS_GEO).map(cap).fillna(0)
    too_big = (d.n_regions == 1) & (d.max_power_mw > d.region_cap_mw)
    print(f"refused, farm larger than its community's wind capacity: {too_big.sum()} "
          f"{d[too_big][['uf', 'nuts_id', 'max_power_mw', 'region_cap_mw']].to_dict('records')}")
    one = d[(d.n_regions == 1) & ~too_big]

    # ---- validation on farms v1/v2 located
    loc = v2[v2.tech == WIND][["uf", "nuts_id", "method"]].rename(columns={"nuts_id": "loc_nuts"})
    val = one.merge(loc, on="uf")
    val["agree"] = val.nuts_id == val.loc_nuts
    print("\n--- validation: Electra's community against the located community, farms v1/v2 located")
    print(f"located farms with an Electra region: {len(val)} of {r.located.sum()} "
          f"(+{(d.located & (d.n_regions > 1)).sum()} ambiguous); agree {val.agree.mean():.1%} "
          f"({val.agree.sum()}/{len(val)}), capacity-weighted "
          f"{val.loc[val.agree, 'max_power_mw'].sum() / val.max_power_mw.sum():.1%}")
    print(val.groupby("source").agree.agg(["size", "mean"]).round(3).to_string())
    print("\nby unit numbers (REE vs Electra):")
    print(val.groupby("numrel").agree.agg(["size", "mean"]).round(3).to_string())
    print("\nby the located row's method:")
    print(val.groupby(val.method.str.startswith("v2").map({True: "v2", False: "v1"})).agree.agg(["size", "mean"])
          .round(3).to_string())
    print("\nstrict variant (all exact rows, wind or neutral, in one community):")
    s = val[val.exact_all_one_region]
    print(f"  {len(s)} farms, agree {s.agree.mean():.1%}")
    print("\ndisagreements:")
    print(val[~val.agree][["uf", "descr_long", "names", "nuts_id", "loc_nuts", "method", "source", "max_power_mw"]]
          .to_string(index=False))
    return finish(r, v2, d, one, val)


def finish(r, v2, d, one, val) -> int:
    nuts = pd.read_parquet(NUTS, columns=["nuts_id", "country", "name"]).set_index("nuts_id")
    new = one[~one.located].copy()
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    agent_firm = ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0])
    new = new.merge(r[["uf", "up", "tech"]], on="uf")
    rows = pd.DataFrame({
        "uf": new.uf, "up": new.up, "tech": new.tech, "max_power_mw": new.max_power_mw, "descr_long": new.descr_long,
        "osm_id": pd.Series([None] * len(new), dtype="str"), "osm_name": new.names, "osm_mw": np.nan,
        "lat": np.nan, "lon": np.nan, "method": "v3 electra", "sim": new.sim, "source": new.source,
        "agent": new.agent, "firm": new.agent.map(agent_firm),
        "nuts_id": pd.Series(new.nuts_id.to_numpy(), dtype="string"),
        "country": pd.Series(new.nuts_id.map(nuts.country).to_numpy(), dtype="string"),
        "region": pd.Series(new.nuts_id.map(nuts.name).to_numpy(), dtype="string"),
        "esios_geo_id": pd.Series(new.nuts_id.map(ESIOS_GEO).to_numpy(), dtype="Int64"),
        "region_how": "electra"})
    rows = rows[v2.columns].astype(v2.dtypes.to_dict())
    v2 = v2[~v2.uf.isin(DROP)].copy()
    fix = v2.uf.isin(CORRECT)
    v2.loc[fix, "nuts_id"] = v2.loc[fix, "uf"].map(CORRECT)
    v2.loc[fix, "country"] = v2.loc[fix, "nuts_id"].map(nuts.country)
    v2.loc[fix, "region"] = v2.loc[fix, "nuts_id"].map(nuts.name)
    v2.loc[fix, "esios_geo_id"] = v2.loc[fix, "nuts_id"].map(ESIOS_GEO)
    v2.loc[fix, ["lat", "lon"]] = np.nan
    v2.loc[fix, "region_how"] = "electra"
    out = pd.concat([v2, rows], ignore_index=True)
    if out.uf.duplicated().any():
        raise SystemExit("a farm is located twice")
    report(r, v2, rows, d, one)
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}: {len(v2):,} v2 rows + {len(rows):,} new")
    return 0


def report(r, v2, new, d, one) -> None:
    todo = r[~r.located]
    print(f"\n--- the {len(todo)} unlocated farms ({todo.max_power_mw.sum() / 1000:.2f} GW)")
    dd = d[~d.located]
    print(f"with an Electra name match: {len(dd)}; in one community: {(dd.n_regions == 1).sum()}; "
          f"ambiguous (several communities): {(dd.n_regions > 1).sum()} "
          f"({dd[dd.n_regions > 1].max_power_mw.sum() / 1000:.2f} GW)")
    print(new.groupby("source").max_power_mw.agg(["size", "sum"]).round(1).to_string())
    print("\nnew rows:")
    print(new.sort_values("max_power_mw", ascending=False)[["uf", "descr_long", "osm_name", "max_power_mw", "region",
                                                             "firm", "source"]].to_string(index=False))
    print("\nambiguous farms, largest 25:")
    amb = dd[dd.n_regions > 1].sort_values("max_power_mw", ascending=False).head(25)
    print(amb[["uf", "descr_long", "max_power_mw", "n_regions", "names"]].to_string(index=False))

    print("\n--- coverage, onshore wind (REE register 2026-08-12)")
    r = r.copy()
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    r["firm"] = r.agent.map(ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0]))
    r["v2"], r["v3"] = r.uf.isin(v2.uf), r.uf.isin(set(v2.uf) | set(new.uf))
    tot = r.max_power_mw.sum() / 1000
    gw = lambda x, col: x.loc[x[col], "max_power_mw"].sum() / 1000  # noqa: E731
    print(f"located GW: v2 {gw(r, 'v2'):.2f} ({gw(r, 'v2') / tot:.1%}), v3 {gw(r, 'v3'):.2f} ({gw(r, 'v3') / tot:.1%}) "
          f"of {tot:.2f}; farms {r.v2.sum()} -> {r.v3.sum()} of {len(r)}")
    rr = r[r.max_power_mw > 0]
    f = rr.groupby(rr.firm.fillna("(none)")).apply(
        lambda x: pd.Series({"GW": x.max_power_mw.sum() / 1000, "v2": gw(x, "v2") / (x.max_power_mw.sum() / 1000),
                             "v3": gw(x, "v3") / (x.max_power_mw.sum() / 1000), "added_GW": gw(x, "v3") - gw(x, "v2")}),
        include_groups=False).sort_values("GW", ascending=False)
    print("\nby firm (share of the firm's REE wind capacity located):\n" + f.head(18).round(2).to_string())
    cap = pd.read_parquet(DATA / "esios/esios_installed_capacity.parquet")
    cap = cap[(cap.indicator_id == 1485) & (cap.datetime.str[:7] == "2026-08")].groupby(["geo_id", "geo_name"]).value.sum()
    out = pd.concat([v2[v2.tech == WIND][["esios_geo_id", "max_power_mw"]].assign(p="v2"),
                     new[["esios_geo_id", "max_power_mw"]].assign(p="new")])
    t = out.pivot_table(index="esios_geo_id", columns="p", values="max_power_mw", aggfunc="sum").fillna(0)
    cap = cap.reset_index().join(t, on="geo_id").fillna(0)
    tab = pd.DataFrame({"region": cap.geo_name, "esios_wind_GW": cap.value / 1000, "v2": cap.v2 / cap.value,
                        "v3": (cap.v2 + cap.new) / cap.value, "added_GW": cap.new / 1000}
                       ).sort_values("esios_wind_GW", ascending=False)
    print("\nlocated share of ESIOS's wind capacity by region, August 2026:\n"
          + tab[tab.esios_wind_GW > 0.05].round(2).to_string(index=False))
    left = r[~r.v3]
    code = ~left.descr_long.map(lambda s: isinstance(s, str) and not plain(s).startswith("18W")
                                and len(re.sub(r"[^A-Z0-9 ]", " ", plain(s)).split()) >= 2)
    left = left.assign(why=np.where(left.uf.isin(d.uf[d.n_regions > 1]), "name in several communities",
                                    np.where(left.uf.isin(d.uf), "?", np.where(code, "code, no name",
                                                                                "name not in Electra"))))
    print("\nstill unlocated, by reason:")
    print(left.groupby("why").max_power_mw.agg(["size", "sum"]).round(1).to_string())


if __name__ == "__main__":
    raise SystemExit(main())
