#!/usr/bin/env python3
"""Fetch the JRC-PPDB-OPEN power-plant database -- the missing unit-level
thermal efficiency, the input marginal cost needs and nothing else in this
repo publishes.

    .venv/bin/python scripts/fetch/fetch_jrc_ppdb_efficiency.py
    .venv/bin/python scripts/fetch/fetch_jrc_ppdb_efficiency.py --verify

Writes data/jrc_ppdb/jrc_spain_units.parquet, one row per Spanish generating
unit, and since 2026-10-05 data/jrc_ppdb/jrc_portugal_units.parquet, the same for
Portugal (75 units; its 10 gas and 6 coal generators all carry an efficiency).
Portugal is inside MIBEL, so its thermal plants bid in the same auction; EDP's
Lares and Ribatejo and Endesa's Pego combined cycles had no cost until then.
Since 2026-10-28 also data/jrc_ppdb/jrc_italy_units.parquet, for the Italian gas plants
that serve as the control group in the gas-cap design (GME offers, `fetch_gme_offers.py`). Not resumable in the per-day sense the OMIE fetchers are -- the JRC
publishes one static historical database, not a live archive -- so this just
re-downloads and re-parses unless the output already exists.

WHY

CLAUDE.md's cost section is explicit that nothing token-free in this repo
gives an actual engineering marginal cost: `cab`'s minimum-income condition
is a *declared*, strategic number, not a fuel cost. Building an implied
marginal cost (fuel_price / efficiency + emission_factor * CO2_price /
efficiency) needs a thermal efficiency per unit, and neither OMIE, REE, ESIOS
nor ENTSO-E's token-free surface publishes one. This does.

SOURCE

Kanellopoulos, K. et al., "The JRC Open Power Plants Database (JRC-PPDB-OPEN)",
JRC117303. An open-data-only version of the JRC's power plant database, built
primarily from ENTSO-E's own unit-level "Production and Generation Units"
registry and extended with WRI Global Power Watch, Global Energy Observatory
and FRESNA. Static file, CC-BY 4.0, no registration:

    https://zenodo.org/records/3574566/files/JRC-PPDB-OPEN.ver1.0.zip

Confirmed 2026-08-18: 1,742 Spanish generating units, of which 456 carry a
non-null efficiency -- concentrated almost entirely in the marginal
technology (416 of 420 "Fossil Gas" units, i.e. CCGT; 30 coal; 1 lignite).
Hydro, wind, solar and nuclear rows exist but carry no `eff` value, which is
fine: fuel-cost-driven marginal cost is not the object for those
technologies anyway.

TWO GRAINS, THREE FILES IN THE ZIP

`JRC_OPEN_UNITS.csv` is one row per *generating* unit (`eic_g`), each tied to
a *plant* (`eic_p`) that can hold several units -- capacity, technology,
commissioning year, location. `JRC_OPEN_PERFORMANCE.csv` is unit-level
technical parameters (efficiency, ramp rates, min up/down time), joined on
`eic_g`. `JRC_OPEN_TEMPORAL.csv` is a third, coarser grain -- one row per
unit per *year* (`cyear`), carrying realised generation, capacity factor and
CO2 emitted; not joined in here since it doesn't share a key with the other
two beyond `eic_g`, and is written through unmodified for whoever needs the
annual series.

THE EMPTY-`eic_g` TRAP

A meaningful share of Spanish rows in `JRC_OPEN_UNITS.csv` -- mostly wind,
solar and small hydro -- carry a **blank** `eic_g` (renewable portfolios are
often registered at the plant level only, with no distinct generating-unit
code). Joining `UNITS` to `PERFORMANCE` on `eic_g` with a naive key any
tool that treats `""` as a valid key will silently match every Spanish
blank-`eic_g` row against every *other country's* blank-`eic_g` row in
`PERFORMANCE` -- caught here by hand: a first pass returned German- and
Polish-looking EIC codes attached to nominally-Spanish rows. This build
drops blank `eic_g` before joining rather than matching on it.

`eic_g` IS ALSO NOT UNIQUE ON ITS OWN

A handful of units -- La Muela's pumped-storage generators among them -- are
registered twice in JRC's own source data, once under a pumping-plant
`eic_p` and once under a generation-plant `eic_p`, both carrying the same
`eic_g`. `PERFORMANCE` mirrors the same duplication (7 `eic_g` values, 14
rows). None of the 14 falls in "Fossil Gas" or coal, so it doesn't touch
efficiency coverage, but a naive merge still fans out into duplicate
`(eic_p, eic_g)` rows. `PERFORMANCE` is deduplicated on `eic_g` before the
join, preferring the row with a non-null `eff` where one exists.

WHAT `eic_g`/`eic_p` ARE NOT

These are ENTSO-E Energy Identification Codes, not OMIE unit codes -- there
is no shared key with `cab`, `pdbc` or the unit registry. `name_p`/`name_g`
are the only bridge (e.g. "ESC IBER 6" / "ESCCC2" here is the same physical
unit CLAUDE.md's `cab` section calls "C.C. ESCOMBRERAS"), and matching them
to `cab` unit codes is name-matching work of the same kind
`build_unit_agents.py` already does for agents -- not attempted here.
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT_DIR = DATA / "jrc_ppdb"
RAW_DIR = OUT_DIR / "raw"
OUT_UNITS = OUT_DIR / "jrc_spain_units.parquet"
OUT_TEMPORAL = OUT_DIR / "jrc_spain_temporal.parquet"
OUT_PT_UNITS = OUT_DIR / "jrc_portugal_units.parquet"
OUT_PT_TEMPORAL = OUT_DIR / "jrc_portugal_temporal.parquet"
OUT_IT_UNITS = OUT_DIR / "jrc_italy_units.parquet"
OUT_IT_TEMPORAL = OUT_DIR / "jrc_italy_temporal.parquet"
ZIP_URL = "https://zenodo.org/records/3574566/files/JRC-PPDB-OPEN.ver1.0.zip?download=1"
COUNTRY = "Spain"


def download(sess) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "JRC-PPDB-OPEN.ver1.0.zip"
    if zip_path.exists():
        print(f"  raw zip cached at {zip_path}")
        return zip_path
    r = sess.get(ZIP_URL, timeout=300)
    r.raise_for_status()
    zip_path.write_bytes(r.content)
    print(f"  downloaded {len(r.content):,} bytes")
    return zip_path


def parse(zip_path: Path, country: str = COUNTRY) -> tuple[pd.DataFrame, pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as z:
        units = pd.read_csv(io.BytesIO(z.read("JRC_OPEN_UNITS.csv")))
        perf = pd.read_csv(io.BytesIO(z.read("JRC_OPEN_PERFORMANCE.csv")))
        temporal = pd.read_csv(io.BytesIO(z.read("JRC_OPEN_TEMPORAL.csv")))

    units = units[units.country == country].copy()
    temporal_es = temporal[temporal.eic_g.isin(units.eic_g)].copy()

    # Join on eic_g, but only where it's a real key -- see the empty-eic_g
    # trap in the module docstring. Blank eic_g rows keep their unit-level
    # fields as null rather than being matched to an arbitrary other country.
    has_key = units.eic_g.notna() & (units.eic_g.str.strip() != "")
    perf_keyed = perf[perf.eic_g.notna() & (perf.eic_g.str.strip() != "")]
    # eic_g is not always unique in PERFORMANCE either (see the module
    # docstring) -- dedupe, preferring a row with a real eff over a blank one.
    perf_keyed = (perf_keyed.sort_values("eff", na_position="last")
                             .drop_duplicates("eic_g", keep="first"))
    merged = units[has_key].merge(perf_keyed, on="eic_g", how="left", suffixes=("", "_perf"))
    unmatched = units[~has_key].copy()
    for col in perf_keyed.columns:
        if col not in ("eic_p", "eic_g") and col not in unmatched.columns:
            unmatched[col] = pd.NA
    df = pd.concat([merged, unmatched], ignore_index=True, sort=False)
    df = df.drop(columns=[c for c in df.columns if c.endswith("_perf")])
    return df.reset_index(drop=True), temporal_es.reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="re-parse even if the output parquet already exists")
    args = ap.parse_args()

    if OUT_UNITS.exists() and not args.refresh and not args.verify:
        print(f"  {OUT_UNITS} already exists; pass --refresh to re-parse")
        df = pd.read_parquet(OUT_UNITS)
        temporal = pd.read_parquet(OUT_TEMPORAL)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = download(session())
        df, temporal = parse(zip_path)
        df.to_parquet(OUT_UNITS, index=False)
        temporal.to_parquet(OUT_TEMPORAL, index=False)
        print(f"  wrote {OUT_UNITS}")
        print(f"  wrote {OUT_TEMPORAL}")
        pt, pt_temporal = parse(zip_path, "Portugal")
        pt.to_parquet(OUT_PT_UNITS, index=False)
        pt_temporal.to_parquet(OUT_PT_TEMPORAL, index=False)
        print(f"  wrote {OUT_PT_UNITS} ({len(pt)} units, {int(pt.eff.notna().sum())} with an efficiency)")

    if not OUT_IT_UNITS.exists() or args.refresh:
        it, it_temporal = parse(download(session()), "Italy")
        it.to_parquet(OUT_IT_UNITS, index=False)
        it_temporal.to_parquet(OUT_IT_TEMPORAL, index=False)
        print(f"  wrote {OUT_IT_UNITS} ({len(it)} units, {int(it.eff.notna().sum())} with an efficiency)")

    n_eff = df.eff.notna().sum()
    print(f"\n{len(df):,} Spanish generating units, {n_eff} with a non-null efficiency")
    print("\n  by technology (total / with eff):")
    with_eff = df[df.eff.notna()]
    for t, n in df.type_g.value_counts().items():
        print(f"    {t:<35}{n:>5,}  {with_eff.type_g.value_counts().get(t, 0):>5,}")

    if args.verify:
        assert n_eff > 400, f"expected >400 Spanish units with efficiency, got {n_eff}"
        gas = df[df.type_g == "Fossil Gas"]
        assert gas.eff.notna().mean() > 0.9, "Fossil Gas (CCGT) efficiency coverage regressed"
        dupe = df.duplicated(["eic_p", "eic_g"]).sum()
        assert dupe == 0, "duplicate (eic_p, eic_g) rows -- not a key"
        pt = pd.read_parquet(OUT_PT_UNITS)
        fossil = pt[pt.type_g.str.startswith("Fossil", na=False)]
        assert len(fossil) == 16 and fossil.eff.notna().all(), "Portugal: expected 16 fossil units, all with eff"
        assert pt.duplicated(["eic_p", "eic_g"]).sum() == 0, "Portugal: duplicate (eic_p, eic_g) rows"
        it = pd.read_parquet(OUT_IT_UNITS)
        assert it.duplicated(["eic_p", "eic_g"]).sum() == 0, "Italy: duplicate (eic_p, eic_g) rows"
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
