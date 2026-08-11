# `scripts/` — what is in each folder

Grouped by what a script *does*, not by which source it touches.

```
lib/       shared modules — imported, never run directly
fetch/     one script per data source; each writes raw + parquet under data/
build/     derived artefacts assembled from already-fetched data
qa/        integrity checks that re-derive facts from the files themselves
analysis/  descriptive statistics and figures (R)
```

Always use the project interpreter — `.venv/bin/python`, never bare `python3`.

---

## `lib/` — shared modules

| file | what |
|---|---|
| `omie_common.py` | the study window, an HTTP session with retries, OMIE URL builders, and the DST/resolution logic (`day_periods_utc`, `resolution_minutes`) plus the two **incompatible number parsers** |
| `config.py` | loads `ESIOS_TOKEN` / `ENTSOE_TOKEN` from a gitignored `.env`, and fails with instructions when one is missing |

Two things in here exist because getting them wrong is silent:

- **`parse_price_number` vs `parse_bid_number`.** OMIE's price files use a dot
  decimal (`77.7`); the bid files use a comma decimal with a dot thousands
  separator (`1.500,00` = 1500.0). Never share one parser between them.
- **`day_periods_utc(d, n, tz)`** derives the time step from the actual local
  day span, so it handles 23/24/25-hour days *and* the 92/96/100-period
  quarter-hourly equivalents without special-casing.

Scripts outside `lib/` reach it with:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
```

`lib/` modules resolve the repo root as `Path(__file__).resolve().parent.parent.parent`
(they sit two levels below it). Never hardcode paths.

---

## `fetch/` — one script per source

All are **resumable**: they skip what is already on disk, so re-running is
cheap and safe. Raw downloads are never modified — to fix a parse, change the
parser and re-run.

| script | source | token | what it gets |
|---|---|---|---|
| `fetch_omie_prices.py` | OMIE `marginalpdbc` | no | day-ahead price, ES + PT |
| `fetch_omie_bids.py` | OMIE `curva_pbc_uof` | no | day-ahead unit-level offer curves |
| `fetch_omie_intraday.py` | OMIE `curva_pibc_uof` | no | intraday offer curves, per session |
| `fetch_ree_daily.py` | REE `apidatos` | no | daily generation / demand / balance (ES) |
| `fetch_ree_realtime.py` | REE `demanda.ree.es` | no | 5-minute generation, demand, cross-border flows (ES) |
| `fetch_ren_portugal.py` | REN DataHub | no | 15-minute production, prices, balance, **installed capacity** (PT) |
| `fetch_esios_spain.py` | ESIOS | **yes** | hourly series and Spanish installed capacity |
| `fetch_entsoe_spain.py` | ENTSO-E | **yes** | load, generation, capacity, flows |

The two token scripts have **never been executed** — no token existed when
they were written. Run `--probe` first; that is where a contract mismatch will
surface.

Useful flags:

```bash
.venv/bin/python scripts/fetch/fetch_omie_bids.py --verify     # clearing-identity check per month
.venv/bin/python scripts/fetch/fetch_omie_bids.py --rebuild    # migrate old-schema parquet in place
.venv/bin/python scripts/fetch/fetch_omie_bids.py --list       # what the source actually offers
.venv/bin/python scripts/fetch/fetch_omie_prices.py --start 2024-01-01
```

---

## `build/` — derived artefacts

| script | builds |
|---|---|
| `build_unit_registry.py` | `data/omie/registry/unit_registry.parquet` — 5,049 units with country, market role, corporate tag |

Assembled from OMIE's `pdbc` / `pdbcpt` / `pdbce` schedules, whose zips are
streamed and **deleted after parsing** (the cleared schedule they carry is
already in the bid archive; only the derived attributes are new). Pass
`--keep-zips` to retain them.

Defaults to a **2-day-per-month sample**, which is why ~5% of cleared volume
sits with unmatched units. `--full` parses every day and closes that gap, at
roughly a billion rows of CPU.

---

## `qa/` — integrity checks

| script | checks |
|---|---|
| `audit_data.py` | coverage, gaps, duplicates, schema uniformity, null rates, value ranges, and cross-source agreement |

```bash
.venv/bin/python scripts/qa/audit_data.py     # exits non-zero on any problem
```

**Run this after any re-fetch.** It re-derives everything from the files
rather than trusting fetch logs, because two failures in this project were
silent: a fetcher exiting 0 having parsed 22 of 90 files in a month, and a
timestamp column quietly full of `NaT`. Days that are genuinely absent at
source are listed explicitly in `KNOWN_ABSENT`, so a *new* gap still fails.

---

## `analysis/` — descriptives

| script | produces |
|---|---|
| `descriptives.R` | 7 figures in `outputs/figures/`, 5 tables in `outputs/tables/` |

```bash
Rscript scripts/analysis/descriptives.R
```

Needs R with `arrow`, `dplyr`, `ggplot2`, `tidyr`, `scales`. The bid archives
are ~913 M rows, so it opens them with `arrow::open_dataset()` and lets dplyr
push filtering and aggregation down into Arrow — only summaries are collected.

Avoid non-ASCII characters in plot text: the default R graphics device here
renders `€` and `±` as `...`.

---

## Order of operations, from an empty `data/`

```bash
.venv/bin/python scripts/fetch/fetch_omie_prices.py
.venv/bin/python scripts/fetch/fetch_omie_bids.py --verify
.venv/bin/python scripts/fetch/fetch_omie_intraday.py
.venv/bin/python scripts/fetch/fetch_ree_daily.py
.venv/bin/python scripts/fetch/fetch_ree_realtime.py
.venv/bin/python scripts/fetch/fetch_ren_portugal.py
.venv/bin/python scripts/build/build_unit_registry.py   # needs nothing pre-fetched
.venv/bin/python scripts/qa/audit_data.py
Rscript scripts/analysis/descriptives.R
```

Only `build/` and `analysis/` depend on order; the fetchers are independent of
each other. Budget several hours and ~8 GB for a full rebuild.

See [`../data/README.md`](../data/README.md) for what each output folder
contains, and `../CLAUDE.md` for the verified data facts and traps.
