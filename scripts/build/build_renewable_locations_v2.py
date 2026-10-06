#!/usr/bin/env python3
"""Second pass at locating Spain's onshore wind farms, for the farms the first pass left.

    .venv/bin/python scripts/build/build_renewable_locations.py      # first pass (input)
    .venv/bin/python scripts/build/build_renewable_locations_v2.py

The first pass (`build_renewable_locations.py`) matched REE's wind and solar farms by
name to OpenStreetMap plants and WRI's GPPD. This pass keeps every one of its rows
exactly as they are and tries again, for onshore wind only, on the farms it did not
locate. It writes a new file; the first-pass file is not touched. What the instruments
need (`regional_wind_offer_test.py`, `own_wind_surprise.py`) is each firm's wind
capacity by region, so a farm in the right region counts and a wrong placement is worse
than none: every rule below refuses rather than guesses.

WHAT IS NEW.
  1. Better names on the REE side. The first pass read only `descr_long`. Here a farm
     also gets keys from `descr_short`, and from its code `uf` when it has no name of
     two or more words (`descr_long` an EIC code "18W...", or one word). More
     boilerplate is dropped: "UF"/"UFI" (unidad fisica), "I+D", "ELICO" (a broken
     "EOLICO"), "UNIFICADO", legal forms, a leading "SE", Galician and Catalan articles
     (A, O, AS, DAS, DELS, ...); "FASE n" and "n FASE" give unit number n, a trailing
     A-F is a phase letter (SAN LORENZO A, LAS MAJAS VIB). Names are compared with spaces
     removed (MONTETOURADO = MONTE TOURADO), and once more with the articles kept
     (PE DEL MORO = DELMORO). A glued "UF" or "PE" in front of a code (UFCOLMENAR,
     PECUEVA) is also tried stripped, and GALP's codes, all 30 of which are "G" + a
     name (GBRENA1, GBOIRA1), also without the G.
  2. More candidates, Spanish only (NUTS polygons): the OSM and GPPD plants the first
     pass left unused, and OSM's single turbines grouped into farms - turbines whose
     name carries a farm name ("La Peña - LP04") or whose operator does ("Gecalsa - El
     Hierro", "Comiolica, S.L."), grouped by that name and 3 km single linkage, plus
     the unnamed turbines in the same 1 km cluster when it holds only that group. A
     group's capacity sums its turbines' rated power, from the output tag (a bare
     number above 10 is kW) or the model ("G52/850", "SG 3.4-132", "V90"), unknown
     turbines at the group's median. An OSM plant with no capacity tag gets the
     turbines within 2 km that lie nearer to it than to any other OSM wind plant.

RULES. A REE farm and a candidate pair when
  - names agree, in one of three tiers:
      exact   a key equal to the candidate's (spaces removed). A one-word short form
              of a longer name (descr_short "PARAMO" for PARAMO DE LOS ANGOSTILLOS)
              counts only if no other name in the pool contains it;
      code    for a farm with no name of two or more words, its code (>= 5 letters)
              is the start of the candidate's name (CERROSID -> CERRO SIDRICO), and of
              no other name in the whole pool (VILLA matches many: refused);
      fuzzy   difflib ratio >= MIN_SIM between the names' distinctive parts (generic
              place words such as SIERRA, MONTE, CERRO dropped), >= 5 letters (7 for a
              one-word name), first two letters equal;
  - unit numbers, phase letters and the "ampliacion" mark do not disagree;
  - capacity is known and plausible: REE MW / candidate MW within a factor CAP_EXACT
    (exact), CAP_LOOSE (code, fuzzy), CAP_ONE_NUM (fuzzy with a unit number on one
    side only);
  - neither side has a better-tier name match that failed only on capacity (a
    candidate whose exact name is another farm's is not handed to a look-alike);
  - the pair is each side's unique best: by tier, then unit numbers (equal > both
    absent > one absent), then similarity. Every REE farm competes, the first pass's
    included, in every source round (OSM plants, turbine names, turbine operators,
    GPPD, in that order), so a candidate better explained by an already located farm
    is never taken. A farm with several equally good candidates takes the closest
    capacity; a candidate wanted equally by several farms goes to none;
  - all of a farm's passing candidates lie in one region; otherwise it is ambiguous
    and left out (LA MUELA, LOS LLANOS, BOIRA ... are in several regions).
  Group: several unlocated farms of one agent and one name root, which no other farm
  shares, pair together with one candidate of that root when their summed capacity is
  within CAP_LOOSE of it (GPPD's "ALTO PALANCIA III", 94 MW, for Alto Palancia I-III).
  Sibling: an unlocated farm whose name root (or code stem: CODES01/CODES02) is that of
  located farms of the SAME REE agent, all within SAME_PLACE_KM of one another, takes
  their centroid. Weaker than a match - there is no capacity to check - so labelled.

OUTPUT (data/osm/):
  renewable_unit_locations_v2.parquet   the first-pass rows, unchanged, then the new
                                        onshore wind rows; same columns. `method`: "v2
                                        exact", "v2 code prefix", "v2 fuzzy", "v2 group",
                                        "v2 sibling". `source`: osm, wri, turbines,
                                        turbines-operator, sibling. A turbine group's
                                        `osm_id` is "turb" (name) or "turbop" (operator)
                                        + its lowest OSM node id; a sibling's is "sib:"
                                        + the siblings' uf.

COVERAGE, measured 2026-10-06 (REE register 2026-08-12, 1,173 onshore wind farms,
32.3 GW): located 577 farms / 17.5 GW (54.3%) after the first pass, 745 / 22.4 GW
(69.5%) after this one; 67.1% without siblings. Added 168 farms, 4.9 GW: exact 99
(3.19 GW), code prefix 14 (0.29), fuzzy 20 (0.53), group 5 (0.11), sibling 30 (0.77);
of the 138 matched farms 122 sit on OSM plants, 7 on GPPD plants, 9 on turbine groups. Share of each firm's REE
wind capacity located, first pass -> v2: Iberdrola 75 -> 85%, Acciona 58 -> 68%,
Endesa 65 -> 73%, Naturgy 55 -> 67%, EDP 63 -> 77%, Repsol 28 -> 29%, Ignis 33 -> 82%,
Galp 0 -> 34%. Against ESIOS's August 2026 wind capacity by region: Castilla y León 63
-> 75%, Aragón 49 -> 66%, Castilla-La Mancha 49 -> 67%, Galicia 52 -> 65%, Andalucía
70 -> 81%, Navarra 39 -> 50%, Cataluña 15 -> 37%, Valencia 42 -> 64%. Extremadura
reads 110%: the Merengue farms (89 MW) exceed ESIOS's ~100 MW there.
Validation (printed): REE / candidate capacity has median 1.00, 81% within 10%, 5-95%
0.74-1.33; no candidate and no turbine used twice. Of 33 matched candidates whose OSM
operator tag and the farm's firm are both known, 15 name the firm, 3 name another
large firm (Ágreda, Cerro Revolcado and Uzkita read Acciona), the rest name a project
company or a turbine maker. What is left unlocated is mostly codes with no name (GESTERNOVA's GST..., the
EOALP.. and SCZ.. series), farms with no OSM or GPPD entry of that name, and names
that occur in several regions.

Data (c) OpenStreetMap contributors, ODbL 1.0; WRI GPPD CC BY 4.0.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from regions import locate  # noqa: E402

DATA = ROOT / "data"
OSM = DATA / "osm/osm_renewable_plants.parquet"
TURB = DATA / "osm/osm_wind_turbines.parquet"
WRI = DATA / "wri/wri_gppd_iberia.parquet"
REG = DATA / "esios/esios_physical_units.parquet"
PASS1 = DATA / "osm/renewable_unit_locations.parquet"
OUT = DATA / "osm/renewable_unit_locations_v2.parquet"
WIND = "Eólica terrestre"

MIN_SIM = 0.88          # fuzzy: difflib ratio on the distinctive part of the name
CAP_EXACT = 2.0         # exact name: REE MW / candidate MW within [1/2, 2]
CAP_LOOSE = 1.35        # code-prefix or fuzzy name, tagged capacity
CAP_ONE_NUM = 1.15      # fuzzy name where only one side carries a unit number
SAME_PLACE_KM = 15.0    # located siblings farther apart than this are two places
TURB_LINK_KM = 3.0      # turbines of one named group: single linkage
TURB_CLUSTER_KM = 1.0   # spatial clusters used to add unnamed turbines to a named group
MIN_KEY = 4             # shortest name key used at all
MIN_CODE = 5            # shortest code used as a prefix
MIN_FUZZY = 5           # shortest distinctive part compared fuzzily
MIN_FUZZY_WORD = 7      # ... when the description is a single word
SOURCE_ORDER = {"osm": 0, "turbines": 1, "turbines-operator": 2, "wri": 3}
EARTH_KM = 6371.0

ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9",
         "X": "10", "XI": "11", "XII": "12"}
# whole-word boilerplate, removed anywhere in the name
BOILER = {"PARQUE", "PARQUES", "PARQ", "PARC", "EOLICO", "EOLICA", "EOLICOS", "EOLICAS", "ELICO", "EOLIC", "PE", "UF",
          "UFI", "UFS", "CENTRAL", "INSTALACION", "WINDFARM", "AEROGENERADOR", "AEROGENERADORES", "SL", "SLU", "SA",
          "SAU", "ID", "ET", "DE", "DEL", "DELS", "LA", "EL", "LOS", "LAS", "LES", "ELS", "Y", "DA", "DO", "DAS",
          "DOS", "NA", "NO", "EN", "OS", "AS", "FASE", "UNIFICADO"}
# generic place words: kept in the name, ignored when names are compared fuzzily
GENERIC = {"SIERRA", "SERRA", "MONTE", "MONTES", "CERRO", "CERROS", "ALTO", "ALTOS", "ALTA", "LOMA", "LOMAS", "PENA",
           "PENAS", "PLANA", "PLANAS", "CABEZO", "PUERTO", "VIRGEN", "SAN", "SANTA", "SANTO", "LLANO", "LLANOS",
           "CASA", "CASAS", "COLL", "TORRE", "VALLE", "MUELA", "DEHESA", "CORRAL", "CAMPO", "RIO", "MOLINO",
           "MOLINOS", "AMPLIACION", "WIND", "NORTE", "SUR", "ESTE", "OESTE"}
ARTICLES = {"DE", "DEL", "DELS", "LA", "EL", "LOS", "LAS", "LES", "ELS", "DA", "DO", "DAS", "DOS", "NA", "NO", "EN",
            "OS", "AS"}
AMP = {"AMPLIACION", "AMPL", "AMPLIAC", "AMPLIACIN", "REPOTENCIACION"}
# operator tags: company words dropped before the rest is read as a farm name
OPERATOR_WORDS = {"EXPLOTACIONES", "SISTEMAS", "ENERGETICOS", "ENERGETICAS", "ENERGIA", "ENERGIAS", "DESARROLLOS",
                  "DESARROLLO", "SOCIEDAD", "GENERACION", "GENERACIONES", "RENOVABLES", "PROYECTOS", "FUERZAS",
                  "EOLICO", "EOLICOS", "EOLICA", "EOLICAS", "PARQUE", "SL", "SLU", "SA", "SAU", "GRUPO"}
# rated power of turbine models named by rotor only (manufacturers' data sheets)
MODEL_MW = {"G47": 0.66, "G52": 0.85, "G58": 0.85, "G80": 2.0, "G83": 2.0, "G87": 2.0, "G90": 2.0, "G97": 2.0,
            "G114": 2.0, "V44": 0.6, "V47": 0.66, "V52": 0.85, "V80": 2.0, "V90": 2.0, "AE30": 0.3, "AE46": 0.66,
            "AE52": 0.8, "AE56": 0.8, "AE59": 0.8, "AE61": 1.32, "ECOTECNIA44": 0.64, "ECOTECNIA48": 0.75,
            "ECOTECNIA74": 1.67, "ECOTECNIA80": 1.67, "ECO44": 0.64, "ECO48": 0.75, "ECO74": 1.67, "ECO80": 1.67}


def plain(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s.upper()) if unicodedata.category(c) != "Mn")
    return s


def name_key(s, code: bool = False) -> dict | None:
    """Root, unit number, phase letter and ampliacion mark of a farm name.

    `code` marks a unit code or short description: a glued "UF" or "PE" prefix is
    then offered stripped as well (returned under "alts")."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = plain(s)
    s = re.sub(r"I\s*\+\s*D", " ", s)                               # investigacion y desarrollo
    s = re.sub(r"(\d+)\s*[ªº]", r"\1 ", s)                         # 1ª FASE
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = s.split()
    amp = any(t in AMP for t in toks)
    toks = [t for t in toks if t not in AMP]
    out = []
    for t in toks:                                                  # VIB -> 6 B (LAS MAJAS VIB)
        m = re.fullmatch(r"(I{1,3}|IV|VI{0,3}|IX|X)([A-F])", t)
        if m and out:
            out += [ROMAN[m.group(1)], m.group(2)]
        else:
            out.append(ROMAN.get(t, t))
    toks = out
    num = None
    # FASE n / n FASE
    for i, t in enumerate(toks):
        if t == "FASE":
            if i + 1 < len(toks) and toks[i + 1].isdigit():
                num = toks[i + 1]
                toks = toks[:i] + toks[i + 2:]
            elif i > 0 and toks[i - 1].isdigit():
                num = toks[i - 1]
                toks = toks[:i - 1] + toks[i + 1:]
            break
    while toks and toks[0] in {"SE", "UF", "UFI", "PE", "P", "E"}:   # leading SE (subestacion), P E
        toks = toks[1:]
    toks_art = [t for t in toks if t not in BOILER or t in ARTICLES]
    toks = [t for t in toks if t not in BOILER]
    letter = None
    if len(toks) >= 2 and re.fullmatch(r"[A-F]", toks[-1]) and (len(toks) >= 3 or toks[-2].isdigit()
                                                                 or len(toks[-2]) >= 4):
        letter = toks.pop()
    if toks and num is None:
        m = re.fullmatch(r"([A-Z]{3,})(\d{1,2})([A-F]?)", toks[-1])   # glued code: GBRENA1, UFSERON1A
        if m:
            toks[-1] = m.group(1)
            num = m.group(2)
            letter = letter or (m.group(3) or None)
        elif toks[-1].isdigit() and len(toks) >= 2:
            num = toks.pop()
    toks = [t for t in toks if len(t) > 1]                          # stray single letters: D', L', A, O
    if num is not None:
        num = str(int(num))
    root = " ".join(toks)
    comp = root.replace(" ", "")
    if len(comp) < MIN_KEY:
        return None
    alts = []
    if code and len(toks) == 1:
        for p in ("UF", "PE"):
            if comp.startswith(p) and len(comp) - len(p) >= MIN_KEY:
                alts.append(comp[len(p):])
    if not code:                                                    # articles kept: PE DEL MORO = DELMORO
        a = "".join(t for t in toks_art if len(t) > 1 and not t.isdigit())
        if a != comp and len(a) >= MIN_KEY:
            alts.append(a)
    dist = "".join(t for t in toks if t not in GENERIC)
    return {"root": root, "comp": comp, "num": num, "letter": letter, "amp": amp, "dist": dist, "alts": alts}


def is_named(descr) -> bool:
    """Whether a REE description is a farm name of two or more words, not a code."""
    if not isinstance(descr, str) or plain(descr).strip().startswith("18W"):
        return False
    return len(re.sub(r"[^A-Z0-9 ]", " ", plain(descr)).split()) >= 2


def ree_keys(r: pd.DataFrame) -> pd.DataFrame:
    """One row per (farm, key).

    kind "name": a description of two or more words, or a one-word description compared
    fuzzily; kind "code": a one-word description or, for a farm with no name of two or
    more words, its `uf` code. Codes match exactly or as a prefix, never fuzzily."""
    rows = []
    for x in r.itertuples():
        named = is_named(x.descr_long) or is_named(x.descr_short)
        srcs = []
        for d in (x.descr_long, x.descr_short):
            if not isinstance(d, str) or plain(d).strip().startswith("18W"):
                continue
            if is_named(d):
                srcs.append(("name", d, False))
            elif not named:
                srcs += [("code", d, True), ("name", d, False)]
            else:                                                  # a one-word short form of a longer name
                srcs.append(("short", d, False))
        if not named:
            srcs.append(("code", x.uf, True))
            if x.agent == "GALP" and x.uf.startswith("G"):      # GALP: "G" + name, all 30 codes
                srcs.append(("code", x.uf[1:], True))
        seen = set()
        for kind, d, code in srcs:
            k = name_key(d, code=code)
            if k is None:
                continue
            for comp in [k["comp"]] + k["alts"]:
                if (kind, comp) in seen:
                    continue
                seen.add((kind, comp))
                dist = k["dist"] if comp == k["comp"] and kind == "name" else ""
                if not is_named(d) and len(dist) < MIN_FUZZY_WORD:
                    dist = ""                                     # a short one-word name is not compared fuzzily
                rows.append({"uf": x.uf, "kind": kind, "comp": comp, "num": k["num"], "letter": k["letter"],
                             "amp": k["amp"], "dist": dist})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- turbines
def turbine_mw(t: pd.DataFrame) -> pd.Series:
    """Rated MW of each turbine from its output tag or model; NaN when unknown."""
    mw = t.mw.copy()
    mw = mw.where(~(mw > 10), mw / 1000)          # a bare number above 10 is kW (1800 = 1.8 MW)
    mw = mw.where(mw >= 0.05)
    tags = t.tags.map(json.loads)
    model = tags.map(lambda d: d.get("model") or d.get("generator:model") or d.get("manufacturer:type")
                     or d.get("name") or "")

    def from_model(s: str) -> float:
        s = plain(s)
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*MW", s)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"\b(\d\.\d{1,2})\s*-\s*\d{2,3}\b", s) or re.search(r"\b(\d\.\d{1,2})\s*S", s)
        if m:                                       # SG 3.4-132, GE 1.5sle
            return float(m.group(1))
        m = re.search(r"\b(\d{3,4})\s*/\s*\d{2,3}\b", s)   # AW 1500/77
        if m and 200 <= int(m.group(1)) <= 8000:
            return int(m.group(1)) / 1000
        m = re.search(r"[/-]\s*(\d{3,4})\b", s)            # G52/850, V90/2000
        if m and 200 <= int(m.group(1)) <= 8000:
            return int(m.group(1)) / 1000
        sq = re.sub(r"[^A-Z0-9]", "", s)
        for k in sorted(MODEL_MW, key=len, reverse=True):
            if re.search(rf"(^|[A-Z]){k}($|\D)", sq) or sq.endswith(k) or sq.startswith(k):
                return MODEL_MW[k]
        return np.nan

    est = model.map(from_model)
    return mw.fillna(est)


def turbine_farm_name(name) -> str | None:
    """The farm part of a turbine's name, or None for a bare id or a model name."""
    if not isinstance(name, str):
        return None
    s = plain(name)
    if " - " in s:
        s = s.split(" - ")[0]
    s = re.sub(r"\s+-\s*\S*$", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = s.split()
    idtok = re.compile(r"^(AE|A|AG|T|WTG|WT|M|G|P|PE|AY|TN|LP|SCM)?-?\d{1,3}[A-Z]?$|^AE\d*$|^[A-Z]{1,3}\d[A-Z]?\d{1,3}$")
    while toks and idtok.match(toks[-1]):
        toks.pop()
    s = " ".join(toks)
    if not s or re.match(r"^(AEROGENERADOR(ES)?|MOLINO( EOLICO)?|AE|WTG|TURBINA|GENERADOR EOLICO)$", s):
        return None
    if re.match(r"^(ECOTECNIA|ECOTECNIA ECO|GAMESA|MADE|VESTAS|ENERCON|NORDEX|ACCIONA|SIEMENS|GE|G\d|V\d|AW)\b", s):
        return None
    return s


def operator_farm_names(op) -> list[str]:
    """Farm names an operator tag may carry: each ' - ' part, company words dropped."""
    if not isinstance(op, str):
        return []
    out = []
    for part in re.split(r"\s+-\s+|/", op):
        s = re.sub(r"[^A-Z0-9 ]", " ", plain(part))
        toks = [t for t in s.split() if t not in OPERATOR_WORDS]
        if toks:
            out.append(" ".join(toks))
    return out


def link_components(lat, lon, km: float) -> np.ndarray:
    """Single-linkage components of points within `km` of each other."""
    lat, lon = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    xyz = np.c_[np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)]
    if len(xyz) == 1:
        return np.zeros(1, int)
    pairs = cKDTree(xyz).query_pairs(km / EARTH_KM, output_type="ndarray")
    n = len(xyz)
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) else \
        coo_matrix((n, n))
    return connected_components(g, directed=False)[1]


def turbine_groups() -> pd.DataFrame:
    """Candidate farms from OSM's single turbines in Spain, by turbine name and by operator."""
    t = pd.read_parquet(TURB)
    t = t[t.country == "ES"].reset_index(drop=True)
    t["mw_est"] = turbine_mw(t)
    t["cl"] = link_components(t.lat, t.lon, TURB_CLUSTER_KM)
    out = []
    for origin, names in (("turbines", t.name.map(turbine_farm_name)),
                          ("turbines-operator", t.operator.map(operator_farm_names))):
        if origin == "turbines":
            lab = names.dropna()
            idx = lab.index.to_numpy()
            labels = lab.to_numpy()
        else:
            ex = names.explode().dropna()
            idx = ex.index.to_numpy()
            labels = ex.to_numpy()
        d = pd.DataFrame({"i": idx, "label": labels})
        for label, g in d.groupby("label"):
            ii = g.i.to_numpy()
            comp = link_components(t.lat.to_numpy()[ii], t.lon.to_numpy()[ii], TURB_LINK_KM)
            for c in np.unique(comp):
                members = set(ii[comp == c])
                out.append({"origin": origin, "name": label, "members": members})
    groups = pd.DataFrame(out)
    # unnamed turbines join a named group when their 1 km cluster holds only that group
    for origin in ("turbines", "turbines-operator"):
        sel = groups.origin == origin
        named = {}
        for gi, mem in zip(groups.index[sel], groups.members[sel]):
            for i in mem:
                named.setdefault(t.cl.iat[i], set()).add(gi)
        tagged = set().union(*groups.members[sel]) if sel.any() else set()
        cl_members = t.groupby("cl").groups
        for cl, gis in named.items():
            if len(gis) == 1:
                gi = next(iter(gis))
                extra = {i for i in cl_members[cl] if i not in tagged}
                groups.at[gi, "members"] = groups.at[gi, "members"] | extra
    rows = []
    for g in groups.itertuples():
        ii = np.fromiter(g.members, int)
        mw = t.mw_est.to_numpy()[ii]
        known = ~np.isnan(mw)
        med = np.nanmedian(mw) if known.any() else np.nan
        cap = np.nansum(mw) + (~known).sum() * med if known.any() else np.nan
        prefix = "turb" if g.origin == "turbines" else "turbop"
        rows.append({"origin": g.origin, "osm_id": f"{prefix}{t.osm_id.to_numpy()[ii].min()}", "name": g.name,
                     "members": ",".join(map(str, sorted(t.osm_id.to_numpy()[ii]))),
                     "mw": cap, "mw_known_share": known.mean(), "n_turbines": len(ii),
                     "lat": t.lat.to_numpy()[ii].mean(), "lon": t.lon.to_numpy()[ii].mean(),
                     "operator": "; ".join(sorted(set(t.operator.to_numpy()[ii][t.operator.notna().to_numpy()[ii]])))[:120]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- candidates
def candidates(used: set[str]) -> tuple[pd.DataFrame, set[str]]:
    """Spanish candidate farms the first pass did not use, and the name pool of all of them."""
    o = pd.read_parquet(OSM)
    o = o[o.source.str.contains("wind", na=False) & o.name.notna() & (o.country == "ES")]
    osm = pd.DataFrame({"origin": "osm", "osm_id": "osm" + o.osm_id.astype(str), "name": o.name, "mw": o.mw,
                        "lat": o.lat, "lon": o.lon, "operator": o.operator if "operator" in o else None})
    w = pd.read_parquet(WRI)
    w = w[(w.primary_fuel == "Wind") & (w.country == "ESP")]
    wri = pd.DataFrame({"origin": "wri", "osm_id": "wri" + w.gppd_idnr.astype(str), "name": w.name,
                        "mw": w.capacity_mw, "lat": w.latitude, "lon": w.longitude, "operator": w.owner})
    wri = wri[locate(wri.lat, wri.lon).country.eq("ES").fillna(False).to_numpy(bool)]
    tg = turbine_groups()
    c = pd.concat([osm, wri, tg], ignore_index=True)
    pool = {k["comp"] for k in c.name.map(name_key) if k}
    c = c[~c.osm_id.isin(used)].reset_index(drop=True)
    # OSM plants without a capacity tag: the turbines around them
    c["cap_from"] = np.where(c.origin.str.startswith("turbines"), "turbines", np.where(c.mw > 0, "tag", "none"))
    c.loc[c.cap_from == "none", "mw"] = np.nan
    loc = locate(c.lat, c.lon)
    c["nuts_id"], c["region"] = loc.nuts_id.to_numpy(), loc.region.to_numpy()
    keys = c.name.map(name_key)
    c = c[keys.notna()].copy()
    keys = keys[keys.notna()]
    for f in ("root", "comp", "num", "letter", "amp", "dist"):
        c[f] = keys.map(lambda k: k[f])
    return c.reset_index(drop=True), pool


def plant_turbine_capacity(c: pd.DataFrame) -> pd.Series:
    """Capacity of OSM/GPPD plants lacking a tag: turbines within 2 km nearer to it than to any other plant."""
    t = pd.read_parquet(TURB)
    t = t[t.country == "ES"].reset_index(drop=True)
    t["mw_est"] = turbine_mw(t)
    t["mw_est"] = t.mw_est.fillna(t.mw_est.median())
    allp = pd.read_parquet(OSM)
    allp = allp[allp.source.str.contains("wind", na=False) & allp.lat.notna()].reset_index(drop=True)

    def xyz(lat, lon):
        lat, lon = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
        return np.c_[np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)]

    tree = cKDTree(xyz(allp.lat, allp.lon))
    d, j = tree.query(xyz(t.lat, t.lon))
    near = d * EARTH_KM <= 2.0
    owner = pd.Series(np.where(near, "osm" + allp.osm_id.astype(str).to_numpy()[j], None))
    cap = t.mw_est.groupby(owner).sum()
    return c.osm_id.map(cap)


# --------------------------------------------------------------------------- matching
def km_between(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlat, dlon = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


def candidate_pairs(rk: pd.DataFrame, c: pd.DataFrame, pool: set[str]) -> pd.DataFrame:
    """All (farm key, candidate) pairs whose names agree, with the name tier.

    `pool` is every candidate name (spaces removed), the first pass's included: a code is
    used as a prefix only when exactly one name in the pool starts with it."""
    out = []
    ex = rk.merge(c[["comp"]].reset_index().rename(columns={"index": "ci"}), on="comp")
    # a one-word short form of a longer name (PARAMO for PARAMO DE LOS ANGOSTILLOS) counts
    # only if no other name in the pool contains it
    pool_arr = np.array(sorted(pool), dtype=str)
    short = ex.kind.eq("short")
    n_in = ex.comp[short].map(lambda w: int((np.char.find(pool_arr, w) >= 0).sum()))
    ex = ex[~short | ex.index.isin(n_in[n_in == 1].index)]
    out.append(ex.assign(tier=3, sim=1.0))
    code = rk[(rk.kind == "code") & (rk.comp.str.len() >= MIN_CODE)]
    ccomp = c.comp.to_numpy().astype(str)
    rows = []
    for x in code.itertuples():
        if (np.char.startswith(pool_arr, x.comp) & (pool_arr != x.comp)).sum() != 1:
            continue
        for ci in np.flatnonzero(np.char.startswith(ccomp, x.comp)):
            if ccomp[ci] != x.comp:
                rows.append({**x._asdict(), "ci": ci, "tier": 2, "sim": len(x.comp) / len(ccomp[ci])})
    if rows:
        out.append(pd.DataFrame(rows).drop(columns="Index"))
    rows = []
    cd = c.dist.to_numpy()
    for x in rk[(rk.kind == "name") & (rk.dist.str.len() >= MIN_FUZZY)].itertuples():
        for ci in np.flatnonzero([len(y) >= MIN_FUZZY and y[:2] == x.dist[:2] for y in cd]):
            if ccomp[ci] == x.comp:
                continue
            s = SequenceMatcher(None, x.dist, cd[ci]).ratio()
            if s >= MIN_SIM:
                rows.append({**x._asdict(), "ci": ci, "tier": 1, "sim": s})
    if rows:
        out.append(pd.DataFrame(rows).drop(columns="Index"))
    return pd.concat(out, ignore_index=True)


def gate(p: pd.DataFrame, c: pd.DataFrame, r: pd.DataFrame) -> pd.DataFrame:
    """Unit number, phase letter, ampliacion and capacity gates; adds the ranking fields.

    A pair survives only if its name tier is the best either side reaches on names
    alone, before capacity: a candidate whose exact name belongs to another farm (whose
    capacity then fails) is not handed to a farm that only resembles it."""
    cc = c.add_prefix("c_")
    p = p.join(cc, on="ci").merge(r[["uf", "max_power_mw", "agent", "located"]], on="uf")
    both_num = p.num.notna() & p.c_num.notna()
    p = p[~(both_num & (p.num != p.c_num))]
    p = p[~(p.letter.notna() & p.c_letter.notna() & (p.letter != p.c_letter))]
    p = p[p.amp == p.c_amp].copy()
    top_r = p.groupby("uf").tier.transform("max")
    top_c = p.groupby("ci").tier.transform("max")
    n0 = len(p)
    p["num_rank"] = np.where(p.num.notna() & p.c_num.notna(), 2, np.where(p.num.isna() & p.c_num.isna(), 1, 0))
    p = p[p.c_mw > 0].copy()
    ratio = p.max_power_mw / p.c_mw
    f = np.where(p.tier == 3, CAP_EXACT, np.where((p.tier == 1) & (p.num_rank == 0), CAP_ONE_NUM, CAP_LOOSE))
    p = p[(ratio >= 1 / f) & (ratio <= f)]
    dominated = (p.tier < top_r.loc[p.index]) | (p.tier < top_c.loc[p.index])
    print(f"name pairs after number/letter gates: {n0:,}; pass capacity: {len(p):,}; "
          f"of these refused because a better name exists on one side: {dominated.sum()}")
    p = p[~dominated].copy()
    p["cap_dev"] = np.abs(np.log(p.max_power_mw / p.c_mw))
    p = p.sort_values(["uf", "ci", "tier", "num_rank", "sim"], ascending=[True, True, False, False, False])
    return p.drop_duplicates(["uf", "ci"])


def unique_best(p: pd.DataFrame) -> pd.DataFrame:
    """Pairs that are each side's single best, by (tier, num_rank, sim).

    A farm with several equally named candidates takes the one closest in capacity (all
    its candidates lie in one region by then); a candidate with several equally named
    farms is left alone."""
    p = p.copy()
    p["score"] = p.tier * 10 + p.num_rank * 2 + p.sim
    p["score_r"] = p.score - 1e-3 * p.cap_dev
    best_r = p.groupby("uf").score_r.transform("max")
    best_c = p.groupby("ci").score.transform("max")
    q = p[(p.score_r == best_r) & (p.score == best_c)]
    q = q[~q.duplicated("uf", keep=False)]
    n_c = p[p.score == best_c].groupby("ci").uf.nunique()
    return q[q.ci.map(n_c).eq(1)]


def match(r: pd.DataFrame, c: pd.DataFrame, pool: set[str]) -> pd.DataFrame:
    rk = ree_keys(r)
    p = gate(candidate_pairs(rk, c, pool), c, r)
    # one region per farm: an unlocated farm whose passing candidates fall in two
    # regions is ambiguous and left out. Two candidates in one region may be two
    # descriptions of one farm (GPPD's points can sit 20 km off) or two farms of one
    # name; either way the region, which is what the instruments use, is right.
    nreg = p[~p.located].groupby("uf").c_nuts_id.nunique()
    spread = nreg[nreg > 1].index
    amb = p[p.uf.isin(spread)]
    p = p[~p.uf.isin(spread)]
    p = p.assign(src_rank=p.c_origin.map(SOURCE_ORDER))
    best = []
    taken_uf: set[str] = set()
    taken_ci: set[int] = set()
    # source by source, each unlocated farm and each candidate used once; the first
    # pass's farms compete in every round, so they keep the candidates that are theirs
    for s in sorted(p.src_rank.unique()):
        q = p[(p.src_rank == s) & ~p.uf.isin(taken_uf) & ~p.ci.isin(taken_ci)]
        u = unique_best(q)
        best.append(u)
        taken_uf |= set(u.uf[~u.located])
        taken_ci |= set(u.ci)
    b = pd.concat(best)
    print(f"\nfarms left out because their candidates lie in two regions: {amb.uf.nunique()}")
    if len(amb):
        print(amb[["uf", "c_name", "max_power_mw", "c_mw", "c_origin", "c_region"]].round(1).to_string(index=False))
    return b[~b.located]


def groups(r: pd.DataFrame, c: pd.DataFrame, located: set[str], taken: set[str]) -> pd.DataFrame:
    """Several unlocated farms of one agent and one name, matched together to one candidate.

    OSM or GPPD sometimes maps a farm's phases as one plant (GPPD's "ALTO PALANCIA III",
    94 MW, for REE's Alto Palancia I, II and III, 104 MW). The farms pair with it when
    they share agent and name root (spaces removed), no other farm has that root, the
    candidate's unit number (if any) is one of theirs, their summed capacity is within
    CAP_LOOSE of the candidate's, and the candidates of that root lie in one region."""
    rk = ree_keys(r).drop_duplicates(["uf", "comp"]).merge(r[["uf", "agent", "max_power_mw"]], on="uf")
    owners = rk.groupby("comp").agent.nunique()
    todo = rk[~rk.uf.isin(located) & rk.comp.map(owners).eq(1)]
    has_located = set(rk[rk.uf.isin(located)].comp)
    rows = []
    for (agent, comp), g in todo.groupby(["agent", "comp"]):
        if g.uf.nunique() < 2 or comp in has_located:
            continue
        cand = c[(c.comp == comp) & ~c.osm_id.isin(taken) & (c.mw > 0)]
        if cand.empty or cand.nuts_id.nunique() != 1:
            continue
        cand = cand[cand.num.isna() | cand.num.isin(set(g.num.dropna()))]
        mw = g.drop_duplicates("uf").max_power_mw.sum()
        cand = cand.assign(dev=np.abs(np.log(mw / cand.mw)), src=cand.origin.map(SOURCE_ORDER))
        cand = cand[cand.dev <= np.log(CAP_LOOSE)].sort_values(["dev", "src"])
        if cand.empty:
            continue
        b = cand.iloc[0]
        for uf in g.uf.unique():
            rows.append({"uf": uf, "osm_id": b.osm_id, "osm_name": b["name"], "osm_mw": b.mw, "lat": b.lat,
                         "lon": b.lon, "sim": 1.0, "source": b.origin, "c_operator": b.operator,
                         "cap_from": b.cap_from, "members": b.get("members")})
    return pd.DataFrame(rows)


def siblings(r: pd.DataFrame, located: pd.DataFrame) -> pd.DataFrame:
    """Unlocated farms placed with located farms of the same name root and agent."""
    rk = ree_keys(r)
    rk = rk.drop_duplicates(["uf", "comp"])
    loc = located[["uf", "lat", "lon"]].merge(r[["uf", "agent"]], on="uf")
    lk = rk.merge(loc, on="uf")
    todo = rk[~rk.uf.isin(located.uf)].merge(r[["uf", "agent", "max_power_mw"]], on="uf")
    m = todo.merge(lk[["comp", "agent", "uf", "lat", "lon"]], on=["comp", "agent"], suffixes=("", "_sib"))
    rows = []
    for uf, g in m.groupby("uf"):
        sib = g.drop_duplicates("uf_sib")
        d = km_between(sib.lat.to_numpy()[:, None], sib.lon.to_numpy()[:, None], sib.lat.to_numpy()[None, :],
                       sib.lon.to_numpy()[None, :])
        if d.max() > SAME_PLACE_KM:
            continue
        rows.append({"uf": uf, "lat": sib.lat.mean(), "lon": sib.lon.mean(), "osm_id": "sib:" + ",".join(sib.uf_sib),
                     "osm_name": g.comp.iat[0], "osm_mw": np.nan, "sim": np.nan, "n_sib": len(sib)})
    return pd.DataFrame(rows)


def main() -> int:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 2000)
    pd.set_option("display.max_colwidth", 42)
    m1 = pd.read_parquet(PASS1)
    reg = pd.read_parquet(REG)
    r = reg[reg.tech == WIND].copy()
    r["located"] = r.uf.isin(m1.uf)
    print(f"REE onshore wind farms: {len(r):,}, {r.max_power_mw.sum() / 1000:.1f} GW; first pass located "
          f"{r.located.sum():,}, {r[r.located].max_power_mw.sum() / 1000:.1f} GW")
    c, pool = candidates(set(m1.osm_id))
    fill = c.mw.isna() & ~c.origin.str.startswith("turbines")
    c.loc[fill, "mw"] = plant_turbine_capacity(c[fill])
    c.loc[fill & c.mw.notna(), "cap_from"] = "turbines near"
    print(f"candidates (Spain, not used by the first pass): {c.origin.value_counts().to_dict()}; "
          f"with a capacity {c.mw.notna().mean():.0%}")
    b = match(r, c, pool)
    new = pd.DataFrame({"uf": b.uf, "osm_id": b.c_osm_id, "osm_name": b.c_name, "osm_mw": b.c_mw, "lat": b.c_lat,
                        "lon": b.c_lon, "sim": b.sim,
                        "method": b.tier.map({3: "v2 exact", 2: "v2 code prefix", 1: "v2 fuzzy"}),
                        "source": b.c_origin, "c_operator": b.c_operator, "cap_from": b.c_cap_from,
                        "members": b.c_members})
    grp = groups(r, c, set(m1.uf) | set(new.uf), set(new.osm_id))
    if len(grp):
        new = pd.concat([new, grp.assign(method="v2 group")], ignore_index=True)
    located = pd.concat([m1[["uf", "lat", "lon"]], new[["uf", "lat", "lon"]]])
    sib = siblings(r, located)
    if len(sib):
        new = pd.concat([new, sib.assign(method="v2 sibling", source="sibling")], ignore_index=True)
    new = new.merge(r[["uf", "up", "tech", "max_power_mw", "descr_long", "descr_short", "agent"]], on="uf")
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    agent_firm = ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0])
    new["firm"] = new.agent.map(agent_firm)
    loc = locate(new.lat, new.lon)
    new = pd.concat([new.reset_index(drop=True), loc.drop(columns="how").assign(region_how=loc.how)], axis=1)
    report(r, m1, new)
    out = pd.concat([m1, new[m1.columns]], ignore_index=True)
    if out.uf.duplicated().any():
        raise SystemExit("a farm is located twice")
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}: {len(m1):,} first-pass rows + {len(new):,} new")
    return 0


def report(r: pd.DataFrame, m1: pd.DataFrame, new: pd.DataFrame) -> None:
    cols = ["uf", "descr_long", "osm_name", "max_power_mw", "osm_mw", "source", "cap_from", "region", "firm"]
    for meth in ("v2 exact", "v2 code prefix", "v2 fuzzy", "v2 group", "v2 sibling"):
        x = new[new.method == meth].sort_values("max_power_mw", ascending=False)
        print(f"\n{meth}: {len(x)} farms, {x.max_power_mw.sum() / 1000:.2f} GW")
        if len(x):
            extra = ["c_operator"] if meth != "v2 sibling" else []
            print(x[cols + extra].assign(c_operator=x.get("c_operator", pd.Series(dtype=str)).astype(str).str[:30])
                  .to_string(index=False))

    print("\n--- validation")
    mm = new[new.method != "v2 sibling"]
    per_c = mm.groupby("osm_id").agg(ree=("max_power_mw", "sum"), cand=("osm_mw", "first"))
    ratio = per_c.ree / per_c.cand
    print("capacity ratio REE / candidate, per matched candidate (a group's farms summed; siblings have none):")
    print(ratio.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).round(2).to_string())
    print(f"within 10%: {(ratio.sub(1).abs() <= 0.10).mean():.0%}; within 25%: {(ratio.sub(1).abs() <= 0.25).mean():.0%}")
    print(f"candidates used twice: {mm[mm.method != 'v2 group'].osm_id.duplicated().sum()} "
          f"(a group shares its candidate by design)")
    seen: dict[str, str] = {}
    shared = 0
    one = mm.drop_duplicates("osm_id")
    mem = one.members.dropna().str.split(",")
    for uf, ids in zip(one.uf[mem.index], mem):
        for i in ids:
            if i in seen and seen[i] != uf:
                shared += 1
            seen[i] = uf
    print(f"turbines in two matched turbine groups: {shared}")
    allloc = pd.concat([m1[["uf", "lat", "lon"]], new[["uf", "lat", "lon"]]], ignore_index=True)
    d = km_between(new.lat.to_numpy()[:, None], new.lon.to_numpy()[:, None], allloc.lat.to_numpy()[None, :],
                   allloc.lon.to_numpy()[None, :])
    d[new.uf.to_numpy()[:, None] == allloc.uf.to_numpy()[None, :]] = np.inf
    near = d.min(axis=1)
    print(f"new farms within 0.5 km of another located farm: {(near < 0.5).sum()} "
          f"(siblings {(near[new.method.eq('v2 sibling').to_numpy()] < 0.5).sum()}); median distance to the nearest "
          f"other located farm {np.median(near):.1f} km")
    op = mm[mm.c_operator.notna() & mm.c_operator.astype(str).str.len().gt(0) & mm.firm.notna()]
    firm_words = {"IBERDROLA": "IBERDROLA", "ENDESA": "ENDESA|ENEL", "EDP": "EDP|HIDROCANT", "ACCIONA": "ACCIONA",
                  "NATURGY": "NATURGY|GAS NATURAL|FENOSA", "REPSOL": "REPSOL|VIESGO"}
    big = op[op.firm.isin(firm_words)]
    agree = [bool(re.search(firm_words[f], plain(o))) for f, o in zip(big.firm, big.c_operator)]
    print(f"matched candidates with an operator tag and a big-six firm: {len(big)}; operator names that firm: "
          f"{sum(agree)}")
    if len(big):
        print(big.assign(agree=agree)[["uf", "firm", "c_operator", "agree"]].to_string(index=False))
    print("\nspot check, 20 random new pairs (seed 1):")
    print(mm.sample(min(20, len(mm)), random_state=1)[["uf", "descr_long", "descr_short", "osm_name", "max_power_mw",
                                                      "osm_mw", "method", "region"]].to_string(index=False))

    print("\n--- coverage, onshore wind (REE register 2026-08-12)")
    r = r.copy()
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["agent", "firm"]).dropna()
    r["firm"] = r.agent.map(ua.groupby("agent").firm.agg(lambda x: x.value_counts().index[0]))
    v2 = set(m1.uf) | set(new.uf)
    v2_strict = set(m1.uf) | set(new.uf[new.method != "v2 sibling"])
    r["p1"], r["v2s"], r["v2"] = r.uf.isin(m1.uf), r.uf.isin(v2_strict), r.uf.isin(v2)
    gw = lambda x, col: x.loc[x[col], "max_power_mw"].sum() / 1000  # noqa: E731
    tot = r.max_power_mw.sum() / 1000
    print(f"located GW: first pass {gw(r, 'p1'):.2f} ({gw(r, 'p1') / tot:.1%}), v2 without siblings "
          f"{gw(r, 'v2s'):.2f} ({gw(r, 'v2s') / tot:.1%}), v2 {gw(r, 'v2'):.2f} ({gw(r, 'v2') / tot:.1%}) of {tot:.2f}; "
          f"farms {r.p1.sum()} -> {r.v2.sum()} of {len(r)}")
    f = r[r.max_power_mw > 0].groupby(r.firm.fillna("(none)")).apply(
        lambda x: pd.Series({"GW": x.max_power_mw.sum() / 1000, "pass1": gw(x, "p1") / (x.max_power_mw.sum() / 1000),
                             "v2": gw(x, "v2") / (x.max_power_mw.sum() / 1000), "added_GW": gw(x, "v2") - gw(x, "p1")}),
        include_groups=False).sort_values("GW", ascending=False)
    print("\nby firm (share of the firm's REE wind capacity located):\n" + f.head(18).round(2).to_string())
    cap = pd.read_parquet(DATA / "esios/esios_installed_capacity.parquet")
    cap = cap[(cap.indicator_id == 1485) & (cap.datetime.str[:7] == "2026-08")].groupby(["geo_id", "geo_name"]).value.sum()
    out = pd.concat([m1[m1.tech == WIND][["uf", "esios_geo_id", "max_power_mw"]].assign(p="pass1"),
                     new[["uf", "esios_geo_id", "max_power_mw"]].assign(p="new")])
    t = out.pivot_table(index="esios_geo_id", columns="p", values="max_power_mw", aggfunc="sum").fillna(0)
    cap = cap.reset_index().join(t, on="geo_id").fillna(0)
    tab = pd.DataFrame({"region": cap.geo_name, "esios_wind_GW": cap.value / 1000,
                        "pass1": cap.pass1 / cap.value, "v2": (cap.pass1 + cap.new) / cap.value,
                        "added_GW": cap.new / 1000}).sort_values("esios_wind_GW", ascending=False)
    print("\nlocated share of ESIOS's wind capacity by region, August 2026:\n"
          + tab[tab.esios_wind_GW > 0.05].round(2).to_string(index=False))


if __name__ == "__main__":
    raise SystemExit(main())
