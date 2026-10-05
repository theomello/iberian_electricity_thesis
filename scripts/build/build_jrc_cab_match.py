#!/usr/bin/env python3
"""Match JRC-PPDB-OPEN's per-unit thermal efficiency onto OMIE `cab` unit
codes -- the crosswalk `fetch_jrc_ppdb_efficiency.py` deliberately left
unbuilt, because JRC and OMIE share no key.

    .venv/bin/python scripts/build/build_jrc_cab_match.py

Writes data/jrc_ppdb/jrc_cab_match.parquet, one row per accepted match:
`unit` (OMIE code) -> `eff` (JRC efficiency) plus both names, both
capacities and the evidence that justified the match. Nothing here is
inferred silently -- every accepted pairing is printed at build time with
both descriptions, same discipline `build_unit_agents.py` uses for its own
name-matching (its "twin layer" in particular), and unresolved candidates
are printed too rather than guessed at.

WHY THIS IS ITS OWN STEP, NOT PART OF THE FETCHER

JRC identifies a generating unit by ENTSO-E EIC code (`18WESCCC1-123-0T`);
OMIE identifies it by its own alphanumeric code (`ESCCC1`). There is no
shared field. Worse, the two databases don't even agree on *what counts as
one unit* -- see the three real cases below, all confirmed by hand before
writing this matcher:

  * **Escombreras -- the easy case.** JRC's own `name_g` field for each of
    its three Escombreras plants (`ESCCC1`, `ESCCC2`, `ESCCC3`) already
    equals the OMIE code. A bare string match resolves these.
  * **Castellon 3 -- a granularity mismatch.** OMIE bids `CTN3` as one
    782.0 MW unit. JRC splits the same physical plant into three
    generators under one `eic_p` -- two gas turbines and a steam turbine,
    249.2 + 249.7 + 283.1 = 782.0 MW. Matching therefore has to *aggregate
    JRC up to `eic_p`* before comparing to OMIE, not match generator rows
    directly.
  * **Castejon -- a case that must NOT match.** JRC has a real 378.9 MW
    CCGT named "CASTEJO2 I" / "CASTEJON 2". OMIE's only Castejon-named
    codes (`CJON3X`, `CTJON1X`) are declared at 3.0 MW -- a different kind
    of registration entirely (not the plant) -- and the numbering doesn't
    even agree (JRC's "2" against OMIE's "3"/"1"). A name-only matcher
    would pair these; the capacity gate below refuses to.

METHOD: TWO GATES, BOTH REQUIRED, MIRRORING THE TWIN-LAYER DISCIPLINE

For every OMIE unit against every JRC plant (aggregated to `eic_p`):

  1. **Capacity gate** -- the two capacities must agree within 6%. This is
     the strong signal: plant capacities are close to unique to the MW, so
     this alone rules out nearly every wrong pairing (Castejon fails here:
     3.0 MW against 378.9 MW is nowhere close).
  2. **Name gate** -- normalise both names (strip accents, strip boilerplate
     like "C.C."/"CENTRAL"/"CICLO COMBINADO", drop digits into a separate
     trailing-unit-number field) and require `difflib` similarity >= 0.6 on
     what's left. Catches JRC's own inconsistencies against `cab`, e.g.
     "CASTELLO" (JRC, apparently truncated) against "CASTELLON" (`cab`).
     Where both sides carry a trailing unit number and they disagree
     (JRC's "CASTEJON 2" against a same-named "...3"), that's treated as
     negative evidence and blocks the match even if it slipped past gate 1.

A pairing is accepted only if it passes both gates AND is the **unique**
candidate on both sides -- if an OMIE unit matches more than one JRC plant
(or vice versa) after both gates, none of the pairings are accepted; both
sides are printed under "ambiguous, left unmapped" rather than guessed at.

CANDIDATE POOL

Every ES unit in `unit_agents.parquet` with a `max_power_mw` is a
candidate -- not just the ones `tech_from_name` already labelled
`combined_cycle`/`thermal`, since that classifier is itself incomplete
(CLAUDE.md: 63.3% regime coverage, weaker still for a specific technology)
and pre-filtering on it here would silently drop genuine CCGT/thermal units
its regex missed. The JRC side is `type_g` in `{Fossil Gas, Fossil Hard
coal, Fossil Brown coal/Lignite}` -- the only technologies JRC gives a
non-null `eff` for -- with plants JRC marks `DECOMMISSIONED` before 2018
excluded (this repo's window starts 2018-01-01, so those can't appear in
any bid file regardless of match quality).

A MATCH BEING ACCEPTED DOES NOT MEAN THE EFFICIENCY IS TRUSTWORTHY

Found only after a first pass matched cleanly and looked done: JRC's `eff`
is not one kind of number. `JRC_OPEN_PERFORMANCE.csv` carries a
`best_source` field the fetcher kept but this matcher had been ignoring,
and it splits three ways for Spain's Fossil Gas units:

  * **`OEM_derived`** (66 of 482 generator rows) -- from the manufacturer's
    own equipment specification. This is the real thing: mean 0.53, range
    0.52-0.55, exactly where a modern CCGT belongs.
  * **`emissions_15_derived` / `emissions_16_derived`** (2 rows) -- back-
    calculated from that specific plant's reported fuel and CO2, so still
    plant-specific, just indirect.
  * **`Class_derived`** (620 rows, the majority) -- JRC had no plant-level
    figure and filled in the *technology class average* instead. Mean 0.31,
    and it clusters at suspiciously round values (0.23, 0.35, 0.36) that are
    class defaults, not measurements -- nowhere near a real CCGT's range.

Of the 53 matches this build finds, only **31 have an OEM-derived
generator**; a further several rest on `emissions_*_derived` (still
plant-specific, all in the coal fleet); the small cogeneration units
(Sevares, Snica, GE Plastics, Repsol Tarragona, ...) match on capacity and
name perfectly well but their `eff` is a `Class_derived` default -- accurate
about what class of plant it is, not about this specific unit. `eff_source`
and `eff_is_generic` are carried into the output explicitly so this can't be
missed downstream by filtering on match quality alone. Treat
`eff_is_generic == True` rows as "we know its capacity and that it's a real
match, not that we know its efficiency."
"""

from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_unit_agents import has_twin_marker  # noqa: E402

OUT = DATA / "jrc_ppdb" / "jrc_cab_match.parquet"
CAPACITY_TOLERANCE = 0.06
NAME_SIMILARITY_MIN = 0.6
JRC_FUEL_TYPES = {"Fossil Gas", "Fossil Hard coal", "Fossil Brown coal/Lignite"}

# Hand-verified, JRC name_p -> OMIE unit code. Every one of these failed
# both automatic gates for the same reason: JRC and cab abbreviate the same
# plant differently in a way no string-similarity metric bridges --
# "P.G.RODR" against "PUENTES", "ESC IBER" against "ESCOMBRERAS", "CART"
# against "CARTAGENA" -- or use different internal unit numbering for the
# same physical turbines ("CAMPGIB1/2" against cab's "CAMGI10/CAMGI20").
# Verified 2026-08-18 by capacity cross-check (all within 1.9%, most exact
# to 0.3%) plus the plant being a real, findable one under that name --
# not encoded on name resemblance alone. Checked against the capacity
# tiebreak the same way an automatic candidate would be, by hand, because
# no gate combination found these on its own; a wrong guess here would
# silently misprice a real plant's marginal cost.
MANUAL_ALIASES: dict[str, str] = {
    "P.G.RODR 5": "PGR5",     # C.C. PUENTES 5, 855.6 vs 855.6 MW -- exact
    "P.G.RODR 1": "PGR1",     # C.T. PUENTES 1, 350.9 vs 351.1 MW
    "P.G.RODR 2": "PGR2",     # C.T. PUENTES 2, 351.0 vs 351.1 MW
    "P.G.RODR 3": "PGR3",     # C.T. PUENTES 3, 350.2 vs 350.3 MW
    "P.G.RODR 4": "PGR4",     # C.T. PUENTES 4, 350.8 vs 350.9 MW
    "ESC IBER 6": "ESC6",     # C.C. ESCOMBRERAS 6, 815.6 vs 815.6 MW -- exact
    "ESC CART 1": "CTGN1",    # C.C. CARTAGENA 1, 418.2 vs 424.5 MW
    "ESC CART 2": "CTGN2",    # C.C. CARTAGENA 2, 417.8 vs 424.6 MW
    "ESC CART 3": "CTGN3",    # C.C. CARTAGENA 3, 412.7 vs 419.3 MW
    "CAMPGIB1": "CAMGI10",    # C.C. CAMPO DE GIBRALTAR 10, 392.6 vs 392.7 MW
    "CAMPGIB2": "CAMGI20",    # C.C. CAMPO DE GIBRALTAR 20, 387.9 vs 388.0 MW
}

# PORTUGAL (2026-10-05). JRC lists each Portuguese thermal plant generator by
# generator, and the generators are OMIE's units one for one (Lares - G1 is LARES1),
# so they are matched at the generator (eic_g), not aggregated to the plant as for
# Spain. Hand-made, like MANUAL_ALIASES, because two names share nothing: OMIE's
# Turbogas units are JRC's "T.Outeiro C.C." (Tapada do Outeiro, Turbogas's plant).
# Each pairing is checked at build time: capacity within CAPACITY_TOL, the same
# unit number, the same fuel.
PT_GENERATOR_MATCH: dict[str, str] = {
    "LARES1": "Lares - G1", "LARES2": "Lares - G2",                       # EDP, CCGT
    "RIBATE1": "Ribatejo - G1", "RIBATE2": "Ribatejo - G2", "RIBATE3": "Ribatejo - G3",  # EDP, CCGT
    "PEGO3": "Pego C.C. - G3", "PEGO4": "Pego C.C. - G4",                 # Elecgas, CCGT
    "RTG01": "T.Outeiro C.C. - G1", "RTG02": "T.Outeiro C.C. - G2",       # Turbogas, CCGT
    "RTG03": "T.Outeiro C.C. - G3",
    "SINES1": "Sines - G1", "SINES2": "Sines - G2", "SINES3": "Sines - G3",  # EDP, coal (closed 2021)
    "SINES4": "Sines - G4",
    "RPG01": "Pego - G1", "RPG02": "Pego - G2",                           # Tejo Energia, coal (closed 2021)
}
CAPACITY_TOL = 0.06
PT_FUEL = {"combined_cycle": "Fossil Gas", "thermal": "Fossil Hard coal"}


BOILERPLATE = [
    "C.C.", "C.C", "C.T.", "C.T", "UOF", "CENTRAL", "TERMICA", "TÉRMICA",
    "CICLO COMBINADO", "GRUPO", "GENERICA", "GENÉRICA", "VENTA", "VENDA",
    "REPRESENTADA", "REPR", "IBER", "GDF", "GAS", "NATURAL",
]


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")


def normalise(descr: str) -> str:
    s = strip_accents(str(descr)).upper()
    for word in BOILERPLATE:
        s = s.replace(word, " ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def root_and_digit(descr: str) -> tuple[str, str | None]:
    """Split a normalised name into its letters-only root and a trailing
    unit number, whether that number is its own token ("CASTELLO 3") or
    glued onto the last word ("SOTO5", "ESCAT3") -- JRC uses both styles
    and a parser that only caught the space-separated case cost a real
    mismatch (see the module docstring's SOTO5/SOTORIBE 4 case: SRI4R is
    OMIE's unit 4, and the capacity tiebreak nearly paired it with JRC's
    unit 5 because "SOTO5" parsed as a digit-less root and dodged the
    digit-mismatch gate entirely)."""
    norm = normalise(descr)
    tokens = norm.split()
    if not tokens:
        return norm, None
    m = re.match(r"^(.*?)(\d+)$", tokens[-1])
    if not m:
        return norm, None
    prefix, digit = m.group(1), m.group(2)
    root_tokens = tokens[:-1] + ([prefix] if prefix else [])
    return " ".join(root_tokens), digit


def has_digit(x) -> bool:
    """True iff x is a real digit-string, not the no-digit sentinel.

    Assigning a column of `root_and_digit`'s (str | None) tuples into a
    DataFrame via `zip(*series.map(root_and_digit))` silently coerces every
    `None` to `float('nan')` (confirmed 2026-08-18: 3,882 of 4,945 cab rows
    and 306 of 344 JRC rows). `x is not None` is then True for a NaN, and
    `nan != nan` is *also* always True in Python, so the old
    `c.digit is not None and j.digit is not None and c.digit != j.digit`
    check silently rejected every pair where BOTH sides genuinely have no
    trailing unit number -- exactly the case for single-block plants like
    Meirama, Castelnou and Los Barrios. This is why they were missing
    from the matched set entirely rather than showing up as a capacity/name
    near-miss: the digit gate, meant to be negative evidence only when both
    sides disagree, was firing on both sides agreeing they have no digit at
    all. Checking `isinstance(x, str)` is immune to the coercion either way."""
    return isinstance(x, str)


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def load_cab_candidates() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "omie" / "registry" / "unit_agents.parquet")
    df = df[(df.country == "ES") & df.max_power_mw.notna() & (df.max_power_mw > 0)
            & df.descr.notna()].copy()
    df["root"], df["digit"] = zip(*df.descr.map(root_and_digit))
    return df[["unit", "descr", "max_power_mw", "root", "digit", "tech"]].reset_index(drop=True)



# best_source priority, most trustworthy first -- see the module docstring's
# "a match being accepted does not mean the efficiency is trustworthy".
SOURCE_RANK = {"OEM_derived": 0, "emissions_15_derived": 1,
               "emissions_16_derived": 1, "Class_derived": 2}


def load_jrc_candidates() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_spain_units.parquet")
    df = df[df.type_g.isin(JRC_FUEL_TYPES) & df.eff.notna()].copy()
    # A plant decommissioned before this repo's window starts can't appear
    # in any bid file regardless of how well its name matches.
    before_window = df.year_decommissioned.notna() & (df.year_decommissioned < 2018)
    df = df[(df.status_g != "DECOMMISSIONED") & ~before_window]
    df["source_rank"] = df.best_source.map(SOURCE_RANK).fillna(99)

    def best_source_for_plant(g: pd.DataFrame) -> str:
        best = g.loc[g.source_rank.idxmin()]
        return best.best_source if pd.notna(best.best_source) else "unknown"

    agg = df.groupby("eic_p").apply(
        lambda g: pd.Series({
            "name_p": g.name_p.iloc[0],
            "capacity_mw": g.capacity_g.sum(),
            "eff": (g.eff * g.capacity_g).sum() / g.capacity_g.sum(),
            "n_generators": len(g),
            "name_g_set": frozenset(g.name_g.dropna().unique()),
            # The best (lowest-rank) source among the plant's generators --
            # a plant with even one OEM-derived generator is reported as
            # OEM_derived, since that's the trustworthy figure to trust.
            "eff_source": best_source_for_plant(g),
            "eff_is_generic": bool((g.source_rank == SOURCE_RANK["Class_derived"]).all()),
        }),
        include_groups=False,
    ).reset_index()
    agg["name_g_list"] = agg.name_g_set.map(lambda s: ", ".join(sorted(s)))
    agg["root"], agg["digit"] = zip(*agg.name_p.map(root_and_digit))
    return agg


def exact_code_matches(cab: pd.DataFrame, jrc: pd.DataFrame) -> tuple[list[dict], set, set]:
    """Path A: JRC's own `name_g` (or `name_p`) is, for a plant JRC didn't
    split further, literally the OMIE code -- e.g. eic_p 18WESCCC2-123-0L
    carries name_p "ESC GDF 2" but name_g "ESCCC2", which is `cab`'s own
    unit code. This is near-certain evidence once a code appears in only
    one JRC plant, so it's tried before any fuzzy name comparison, with
    only a loose capacity sanity check (25%, not the tight 6% the fuzzy
    path uses) to catch an accidental collision rather than to discriminate."""
    code_to_plants: dict[str, set] = {}
    for ji, j in jrc.iterrows():
        for code in j.name_g_set | {j.name_p}:
            code_to_plants.setdefault(code, set()).add(ji)

    accepted, used_cab, used_jrc = [], set(), set()
    ambiguous_codes = []
    for ci, c in cab.iterrows():
        plants = code_to_plants.get(c.unit)
        if not plants:
            continue
        plausible = {ji for ji in plants
                     if abs(c.max_power_mw - jrc.loc[ji].capacity_mw) / c.max_power_mw < 0.25}
        if len(plausible) != 1:
            if plausible:
                ambiguous_codes.append(c.unit)
            continue
        ji = next(iter(plausible))
        j = jrc.loc[ji]
        accepted.append({
            "unit": c.unit, "cab_descr": c.descr, "cab_max_power_mw": c.max_power_mw,
            "cab_tech": c.tech,
            "jrc_eic_p": j.eic_p, "jrc_name_p": j.name_p, "jrc_capacity_mw": j.capacity_mw,
            "jrc_n_generators": j.n_generators, "jrc_name_g_list": j.name_g_list,
            "eff": j.eff, "eff_source": j.eff_source, "eff_is_generic": j.eff_is_generic,
            "capacity_ratio_diff": abs(c.max_power_mw - j.capacity_mw) / c.max_power_mw,
            "name_similarity": 1.0, "match_path": "exact_code",
        })
        used_cab.add(ci)
        used_jrc.add(ji)
    if ambiguous_codes:
        print(f"  (exact-code path: {len(ambiguous_codes)} codes matched a JRC name but at an "
              f"implausible capacity, skipped: {ambiguous_codes})")
    return accepted, used_cab, used_jrc


def fuzzy_matches(cab: pd.DataFrame, jrc: pd.DataFrame) -> tuple[list[dict], list, list]:
    """Path B, for the plants Path A didn't resolve -- capacity gate plus
    normalised-name similarity, see the module docstring."""
    # Sorted by position for the searchsorted below, but index labels are
    # NOT reset -- ji below must stay a label into the caller's jrc frame,
    # since main() reports ambiguous/unmatched JRC plants by that same index.
    jrc_sorted = jrc.sort_values("capacity_mw")
    cap = jrc_sorted.capacity_mw.to_numpy()
    lo_idx = cap.searchsorted(cab.max_power_mw.to_numpy() * (1 - CAPACITY_TOLERANCE), side="left")
    hi_idx = cap.searchsorted(cab.max_power_mw.to_numpy() * (1 + CAPACITY_TOLERANCE), side="right")

    accepted = []
    cab_candidate_counts: dict[int, int] = {}
    jrc_candidate_counts: dict[int, int] = {}
    pairs = []

    for pos, (ci, c) in enumerate(cab.iterrows()):
        lo, hi = lo_idx[pos], hi_idx[pos]
        if lo >= hi:
            continue
        for ji, j in jrc_sorted.iloc[lo:hi].iterrows():
            cap_ratio = abs(c.max_power_mw - j.capacity_mw) / max(c.max_power_mw, j.capacity_mw)
            if has_digit(c.digit) and has_digit(j.digit) and c.digit != j.digit:
                continue  # disagreeing unit numbers is negative evidence
            sim = name_similarity(c.root, j.root)
            if sim < NAME_SIMILARITY_MIN:
                continue
            pairs.append((ci, ji, cap_ratio, sim))
            cab_candidate_counts[ci] = cab_candidate_counts.get(ci, 0) + 1
            jrc_candidate_counts[ji] = jrc_candidate_counts.get(ji, 0) + 1

    def make_row(c, j, cap_ratio, sim, path):
        return {
            "unit": c.unit, "cab_descr": c.descr, "cab_max_power_mw": c.max_power_mw,
            "cab_tech": c.tech,
            "jrc_eic_p": j.eic_p, "jrc_name_p": j.name_p, "jrc_capacity_mw": j.capacity_mw,
            "jrc_n_generators": j.n_generators, "jrc_name_g_list": j.name_g_list,
            "eff": j.eff, "eff_source": j.eff_source, "eff_is_generic": j.eff_is_generic,
            "capacity_ratio_diff": cap_ratio, "name_similarity": sim,
            "match_path": path,
        }

    unambiguous = [p for p in pairs if cab_candidate_counts[p[0]] == 1
                   and jrc_candidate_counts[p[1]] == 1]
    tied = [p for p in pairs if cab_candidate_counts[p[0]] > 1
            or jrc_candidate_counts[p[1]] > 1]

    for ci, ji, cap_ratio, sim in unambiguous:
        accepted.append(make_row(cab.loc[ci], jrc.loc[ji], cap_ratio, sim, "fuzzy_name"))

    # Twin-marker tiebreak: BOILERPLATE already strips "REPR"/"REPRESENTADA"
    # before computing similarity (needed to find the true match at all), so
    # a base registration and its "representada" twin normalise to nearly the
    # same root and both tie for the same JRC plant (e.g. BRR1 "C.T. LOS
    # BARRIOS" and BRR1R1 "CT LOS BARRIOS REPR" both matching "BARRIOS").
    # `has_twin_marker` reads the *original* description, not the stripped
    # one, so it still sees the marker BOILERPLATE removed -- positive
    # evidence for which registration is the base one, same discipline
    # `build_unit_agents.py`'s own twin layer uses. Applied before the
    # capacity tiebreak since a name-based marker is more direct evidence
    # than capacity proximity.
    still_tied = []
    for ji in {p[1] for p in tied}:
        cands = [p for p in tied if p[1] == ji]
        unmarked = [p for p in cands if not has_twin_marker(cab.loc[p[0]].descr)]
        if len(unmarked) == 1 and len(cands) > 1:
            ci, _, cap_ratio, sim = unmarked[0]
            accepted.append(make_row(cab.loc[ci], jrc.loc[ji], cap_ratio, sim,
                                      "fuzzy_name_twin_marker"))
        else:
            still_tied.extend(cands)
    resolved_by_twin = {ci for ci, ji, *_ in
                         [p for p in tied if p not in still_tied]}
    tied = [p for p in still_tied if p[0] not in resolved_by_twin]

    # Tiebreak: two names can both legitimately clear the similarity gate
    # against each other's true partner when neither carries a digit to
    # disambiguate (CASTELLON/CASTELNOU is the case that motivated this --
    # see the module docstring). Capacity is the more discriminating signal
    # of the two, so where it points to a single, mutually-best pairing
    # among the tied candidates, take it -- this is a refinement of
    # candidates that already passed both real gates, not new leniency.
    tiebroken = []
    resolved_ci, resolved_ji = set(), set()
    for ci in {p[0] for p in tied}:
        cands = sorted([p for p in tied if p[0] == ci], key=lambda p: p[2])
        if len(cands) < 2 or cands[0][2] * 1.5 >= cands[1][2]:
            continue  # no clear best, or best isn't well clear of runner-up
        _, best_ji, best_cap, best_sim = cands[0]
        ji_cands = sorted([p for p in tied if p[1] == best_ji], key=lambda p: p[2])
        if ji_cands[0][0] != ci:
            continue  # not mutual: this isn't best_ji's own best cab candidate
        tiebroken.append((ci, best_ji, best_cap, best_sim))
        resolved_ci.add(ci)
        resolved_ji.add(best_ji)

    for ci, ji, cap_ratio, sim in tiebroken:
        accepted.append(make_row(cab.loc[ci], jrc.loc[ji], cap_ratio, sim,
                                  "fuzzy_name_capacity_tiebreak"))

    ambiguous_cab = {p[0] for p in tied if p[0] not in resolved_ci}
    ambiguous_jrc = {p[1] for p in tied if p[1] not in resolved_ji}
    return accepted, sorted(ambiguous_cab), sorted(ambiguous_jrc)


def manual_alias_matches(cab: pd.DataFrame, jrc: pd.DataFrame) -> tuple[list[dict], set, set]:
    """Path C: MANUAL_ALIASES, tried last since it's the most expensive
    evidence (a human, not a gate) and should only be asked to resolve what
    the two automatic paths genuinely couldn't."""
    cab_by_unit = {c.unit: ci for ci, c in cab.iterrows()}
    jrc_by_name = {j.name_p: ji for ji, j in jrc.iterrows()}

    accepted, used_cab, used_jrc = [], set(), set()
    for jrc_name, unit in MANUAL_ALIASES.items():
        if jrc_name not in jrc_by_name or unit not in cab_by_unit:
            continue  # already matched by an earlier path, or filtered out upstream
        ji, ci = jrc_by_name[jrc_name], cab_by_unit[unit]
        c, j = cab.loc[ci], jrc.loc[ji]
        cap_ratio = abs(c.max_power_mw - j.capacity_mw) / c.max_power_mw
        accepted.append({
            "unit": c.unit, "cab_descr": c.descr, "cab_max_power_mw": c.max_power_mw,
            "cab_tech": c.tech,
            "jrc_eic_p": j.eic_p, "jrc_name_p": j.name_p, "jrc_capacity_mw": j.capacity_mw,
            "jrc_n_generators": j.n_generators, "jrc_name_g_list": j.name_g_list,
            "eff": j.eff, "eff_source": j.eff_source, "eff_is_generic": j.eff_is_generic,
            "capacity_ratio_diff": cap_ratio, "name_similarity": name_similarity(c.root, j.root),
            "match_path": "manual_alias",
        })
        used_cab.add(ci)
        used_jrc.add(ji)
    return accepted, used_cab, used_jrc


def portugal_matches() -> pd.DataFrame:
    """PT_GENERATOR_MATCH, checked: capacity, unit number and fuel must agree."""
    ua = pd.read_parquet(DATA / "omie" / "registry" / "unit_agents.parquet")
    ua = ua[ua.unit.isin(PT_GENERATOR_MATCH)].set_index("unit")
    g = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_portugal_units.parquet").set_index("name_g")
    rows, bad = [], []
    for unit, name_g in PT_GENERATOR_MATCH.items():
        if unit not in ua.index or name_g not in g.index:
            bad.append(f"{unit} / {name_g}: missing")
            continue
        c, j = ua.loc[unit], g.loc[name_g]
        cap = abs(c.max_power_mw - j.capacity_g) / c.max_power_mw
        if cap > CAPACITY_TOL:
            bad.append(f"{unit} {c.max_power_mw} MW vs {name_g} {j.capacity_g} MW")
        if re.sub(r"\D", "", unit)[-1] != re.sub(r"\D", "", name_g)[-1]:
            bad.append(f"{unit} / {name_g}: unit numbers differ")
        if PT_FUEL.get(c.tech) != j.type_g:
            bad.append(f"{unit} ({c.tech}) / {name_g} ({j.type_g}): fuels differ")
        rank = SOURCE_RANK.get(j.best_source, 99)
        rows.append({
            "unit": unit, "cab_descr": c.descr, "cab_max_power_mw": c.max_power_mw, "cab_tech": c.tech,
            "jrc_eic_p": j.eic_p, "jrc_name_p": j.name_p, "jrc_capacity_mw": j.capacity_g,
            "jrc_n_generators": 1, "jrc_name_g_list": name_g, "eff": j.eff,
            "eff_source": j.best_source, "eff_is_generic": rank == SOURCE_RANK["Class_derived"],
            "capacity_ratio_diff": cap, "name_similarity": np.nan, "match_path": "pt_generator",
            "jrc_eic_g": j.eic_g, "country": "PT",
        })
    if bad:
        raise SystemExit("Portuguese generator matches fail their checks:\n  " + "\n  ".join(bad))
    return pd.DataFrame(rows)


def find_matches(cab: pd.DataFrame, jrc: pd.DataFrame) -> tuple[pd.DataFrame, list, list]:
    exact_rows, used_cab, used_jrc = exact_code_matches(cab, jrc)
    print(f"  exact-code path: {len(exact_rows)} matches")

    cab_remaining = cab[~cab.index.isin(used_cab)]
    jrc_remaining = jrc[~jrc.index.isin(used_jrc)]
    fuzzy_rows, ambiguous_cab_idx, ambiguous_jrc_idx = fuzzy_matches(cab_remaining, jrc_remaining)
    print(f"  fuzzy-name path: {len(fuzzy_rows)} matches "
          f"(over {len(cab_remaining)} remaining OMIE / {len(jrc_remaining)} remaining JRC)")

    fuzzy_used_cab = {r["unit"] for r in fuzzy_rows}
    fuzzy_used_jrc = {r["jrc_eic_p"] for r in fuzzy_rows}
    cab_remaining2 = cab_remaining[~cab_remaining.unit.isin(fuzzy_used_cab)]
    jrc_remaining2 = jrc_remaining[~jrc_remaining.eic_p.isin(fuzzy_used_jrc)]
    alias_rows, _, _ = manual_alias_matches(cab_remaining2, jrc_remaining2)
    print(f"  manual-alias path: {len(alias_rows)} matches")

    matches = pd.DataFrame(exact_rows + fuzzy_rows + alias_rows)
    alias_units = {r["unit"] for r in alias_rows}
    alias_eic_p = {r["jrc_eic_p"] for r in alias_rows}
    ambiguous_cab_idx = [ci for ci in ambiguous_cab_idx if cab.loc[ci].unit not in alias_units]
    ambiguous_jrc_idx = [ji for ji in ambiguous_jrc_idx if jrc.loc[ji].eic_p not in alias_eic_p]
    return matches, ambiguous_cab_idx, ambiguous_jrc_idx


def main() -> int:
    cab = load_cab_candidates()
    jrc = load_jrc_candidates()
    print(f"  {len(cab)} candidate OMIE (ES) units with a capacity")
    print(f"  {len(jrc)} candidate JRC plants (Fossil Gas/Coal/Lignite, eff known, in-window)")

    matches, ambiguous_cab_idx, ambiguous_jrc_idx = find_matches(cab, jrc)
    matches["country"] = "ES"
    pt = portugal_matches()
    print(f"  Portugal, generator-level hand match: {len(pt)} units, all checks passed")
    matches = pd.concat([matches, pt], ignore_index=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    matches.to_parquet(OUT, index=False)
    print(f"\n  wrote {OUT}")

    es = matches[matches.country == "ES"]
    print(f"\n{len(matches)} accepted matches: {len(es)} Spanish (of {len(jrc)} JRC candidates, "
          f"{len(es)/len(jrc):.1%} of JRC plants; of {len(cab)} OMIE candidates) and "
          f"{len(matches) - len(es)} Portuguese")
    if len(matches):
        n_generic = int(matches.eff_is_generic.sum())
        print(f"  of which {len(matches) - n_generic} carry a plant-specific efficiency "
              f"(OEM- or emissions-derived) and {n_generic} carry only a "
              f"technology-class default (eff_is_generic=True) -- see the module docstring")
    print("\n  accepted matches:")
    for _, r in matches.sort_values("cab_max_power_mw", ascending=False).iterrows():
        flag = " GENERIC" if r.eff_is_generic else ""
        print(f"    {r.unit:<10}{r.cab_descr:<28}{r.cab_max_power_mw:>8.1f} MW  <->  "
              f"{r.jrc_name_p:<16}{r.jrc_capacity_mw:>8.1f} MW  eff={r.eff:.3f} "
              f"({r.eff_source}{flag})  [{r.match_path}]  (name_sim={r.name_similarity:.2f}, "
              f"{r.jrc_n_generators} JRC generator(s))")

    if ambiguous_cab_idx:
        print(f"\n  {len(ambiguous_cab_idx)} OMIE units ambiguous (>1 JRC candidate passed both "
              f"gates), left unmapped:")
        for ci in ambiguous_cab_idx:
            c = cab.loc[ci]
            print(f"    {c.unit:<10}{c.descr:<28}{c.max_power_mw:>8.1f} MW")

    if ambiguous_jrc_idx:
        print(f"\n  {len(ambiguous_jrc_idx)} JRC plants ambiguous (>1 OMIE candidate passed both "
              f"gates), left unmapped:")
        for ji in ambiguous_jrc_idx:
            j = jrc.loc[ji]
            print(f"    {j.name_p:<16}{j.capacity_mw:>8.1f} MW")

    matched_jrc_ids = set(matches.jrc_eic_p) if len(matches) else set()
    unmatched_jrc = jrc[~jrc.eic_p.isin(matched_jrc_ids)
                        & ~jrc.index.isin(ambiguous_jrc_idx)]
    print(f"\n  {len(unmatched_jrc)} JRC plants with no OMIE candidate passing both gates "
          f"at all:")
    for _, j in unmatched_jrc.sort_values("capacity_mw", ascending=False).iterrows():
        print(f"    {j.name_p:<16}{j.capacity_mw:>8.1f} MW  eff={j.eff:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
