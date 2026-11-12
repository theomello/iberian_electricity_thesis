# Spanish electricity market — data project

Operational instructions for this repo. The detail on each dataset is **verified fact**
and lives in [`docs/data-reference/`](docs/data-reference/README.md); this file holds only
what is needed on every task. Read the matching reference file before touching a source.

## Status

**Setting:** Spain / MIBEL. Candidate setting for a thesis, adopted
2026-08-07 after retiring an earlier Brazil-based question.

**Research question: none yet — intentionally.** The data came first so that
the question can be chosen against what the data can actually identify,
rather than the reverse. Do not add an RQ section here until one is chosen;
do not import framing from the previous project.

**A descriptive chapter is under way** — design in
[`docs/specs/2026-08-24-descriptive-price-formation-design.md`](docs/specs/2026-08-24-descriptive-price-formation-design.md),
running note in [`notes/rq-descriptive-price-formation.md`](notes/rq-descriptive-price-formation.md).
Findings live there, not here.

The previous Brazil project remains intact at
`~/Desktop/vre_hydro_thesis` and is not to be modified. Nothing was copied
from it. If something there turns out to be needed, port that one piece
deliberately, restated in Spanish-market terms.

## Environment

Python lives in `.venv` (Python 3.14, pandas 3.0, pyarrow 25; also xarray, netCDF4,
shapely, pyshp, xlrd, scikit-learn). Always use `.venv/bin/python`, never bare
`python3`. There is no requirements file. **`.venv` broke on 2026-11-11** when Homebrew
removed `python@3.14`: if `.venv/bin/python -c "import pandas"` fails, point
`.venv/bin/python3.14` and `home` in `.venv/pyvenv.cfg` at another CPython 3.14 (the
packages in `.venv/lib/python3.14` are intact).

```bash
.venv/bin/python scripts/fetch/fetch_omie_prices.py
```

Scripts resolve the repo root from their own location — `lib/` modules use
`Path(__file__).resolve().parent.parent.parent`. Never hardcode paths. See
`scripts/README.md` for the layout and `data/README.md` for what each output folder holds.

**This repo is at `~/projects/`, deliberately NOT on the Desktop.** The Desktop is
iCloud-synced, which silently evicts large data files to 182-byte `.<name>.icloud`
stubs; reads then fail with a bare "No such file or directory". Keep `data/` off iCloud.

## Scripts

```
scripts/
  lib/       shared modules — omie_common (parsing, DST, resolution), config (tokens),
             regions (coordinate → country/region), holidays, rd, unit_ownership
  fetch/     one script per source; each writes raw + parquet under data/
  build/     derived artefacts assembled from fetched data
  qa/        integrity checks that re-derive facts from the files
  analysis/  descriptive statistics and figures
```

The full table (source, token, output of every script) is in
[`docs/data-reference/scripts.md`](docs/data-reference/scripts.md). Tokens (`ESIOS_TOKEN`,
`GIE_API_KEY`, ENTSO-E) load from the gitignored `.env` via `lib/config.py`.

## Data window

**2018-01-01 → 2026-05-31**, set by the bid archive's start. Bids and intraday run past
it, to **2026-06-29** (~3-month publication lag), so June 2026 has no matching prices,
REE or REN yet. All of `data/` is gitignored and re-fetchable, **except the files below**.

**Not re-fetchable — keep them:**
- `data/omie/unit_lists/` (12 OMIE *Listado de Unidades* PDFs): OMIE keeps no history.
  A tarball with a checksum is in `~/projects/vre_spain_backup_staging/`.
- `data/snirh/raw/` (39 CSVs): SNIRH answers only to LMU's eduVPN address. Never route
  around the block.
- `data/investing/raw/*.csv` (EUA, coal, UKA prices): browser-captured by hand.

## Where to read what

| Before you touch… | Read |
|---|---|
| any OMIE bid, price, `cab`, PDBF or intraday file | [`omie-market-data.md`](docs/data-reference/omie-market-data.md) |
| a unit→firm mapping, ownership, direct consumers, cogeneration, technology labels | [`ownership-and-units.md`](docs/data-reference/ownership-and-units.md), [`docs/unit-agent-mapping.md`](docs/unit-agent-mapping.md) |
| REE, REN, ESIOS (forecasts, capacity, I90, reserves), MITECO | [`ree-ren-esios-miteco.md`](docs/data-reference/ree-ren-esios-miteco.md) |
| marginal cost, gas cap, hydro cost, reservoirs, rainfall | [`costs-and-hydro.md`](docs/data-reference/costs-and-hydro.md) |
| outages, wind/solar locations, holidays, France, Italy, GB, GIE, `indisp`, interconnection | [`outages-renewables-other.md`](docs/data-reference/outages-renewables-other.md) |
| anything at all, once | [`traps.md`](docs/data-reference/traps.md) |

## The traps that bite most (all fail silently; detail in `traps.md`)

- **Bids:** `status` `O` is the offered curve, `C` the cleared part. Never sum both.
  `role == "generation"` drops CCGT, nuclear and hydro; use the four `SUPPLY_ROLES`.
  Units withdrawn by minimum income stay in the offered curve, and `MIEU` (France) appears
  only as `C` rows, so re-clear on the effective curve.
- **Resolution:** day-ahead went 15-minute on **2025-10-01**; intraday, PDBF and `cab` on
  **2025-03-19**. Read `resolution_min` per file. Energy = `power_mw * resolution_min / 60`
  (PDBF `schedule_mw` too). DST days have 23/25 periods (92/100 at 15 minutes).
- **Parsing:** `marginalpdbc` is **PT then ES**. `curva_pbc_uof` uses a comma decimal,
  `marginalpdbc` and `cab` a dot; all latin-1. `cab` is fixed-width with two layouts
  (169 and 94 chars): dispatch on width, slice by position.
- **Rules that moved the data:** offers were capped at €0–180.30 until 2021-07-06; cleared
  rows of SCO offers carry −500 from 2025-03-19; the gas cap (15 June 2022 → Dec 2023) means
  use `marginal_cost_subsidised_*`, not the market-price cost; use the `_bid` cost columns
  for anything modelling the offer decision.
- **Ownership is a projection from snapshots**, not a history; use `lib/unit_ownership.py`
  for dated shares, exclude regulated pass-through suppliers from net positions, and measure
  coverage on the **near-marginal band**, never on total volume.
- **Source anomalies:** 63 days with a broken clearing identity (2018-06-14, 2022-10-12,
  and 61 days 2025-03-19 → 06-09); 43 of 100 `indisp` months are partial at source. Detect
  from the clearing identity, never from a hardcoded date list.
- **Clocks:** REE is local Madrid time; REN uses Lisbon for production and Madrid for prices.
  Join across countries through UTC.
- **Frontier-month zip:** a month at the publication frontier grows,
  so a valid zip on disk is not final (`month_may_grow()` in `lib/omie_common.py`).

## Auditing

```bash
.venv/bin/python scripts/qa/audit_data.py
```

Re-derives coverage, duplicates, schema and value ranges from the files themselves. Run it
after any re-fetch; it exits non-zero on any problem. Known, verified exceptions are listed
at the end of `traps.md`.

## Conventions

- Raw downloads are never modified; re-fetch instead.
- Derived outputs go to `outputs/`; raw and parsed data to `data/`.
- Fetchers are resumable — they skip what is already on disk. **Exceptions:**
  `fetch_eua_carbon_price.py`, `fetch_coal_price.py` and `fetch_uka_carbon_price.py` (parse
  a browser-captured CSV) and `fetch_snirh_reservoirs.py` (LMU eduVPN only).
- Commit messages: imperative, present tense, ≤72-char subject.
- Never commit `.env` or anything under `data/`.
- When a new fact about the data is verified, add it to the matching file in
  `docs/data-reference/`, not here; keep this file under ~150 lines.
