# vre_spain_thesis

Market data for the Spanish / MIBEL electricity market: day-ahead prices,
unit-level bid curves, generation, demand and capacity.

**Window:** 2018-01-01 → 2026-05-31 (set by the OMIE bid archive).
**Coverage:** Spain *and* Portugal — MIBEL clears as one market, so Portugal
is part of the unit of analysis, not a neighbour.

**There is no research question yet.** The data was assembled first so a
question can be chosen against what it can actually identify. See
[CLAUDE.md](CLAUDE.md) for the verified data facts and the traps.

## Setup

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install pandas pyarrow requests
```

## Fetch

```bash
.venv/bin/python scripts/fetch/fetch_omie_prices.py     # day-ahead prices, no token
.venv/bin/python scripts/fetch/fetch_omie_bids.py --verify   # unit-level bids, no token
.venv/bin/python scripts/fetch/fetch_ree_daily.py       # daily generation/demand, no token
.venv/bin/python scripts/fetch/fetch_ree_realtime.py    # 5-min generation/demand/flows, no token
.venv/bin/python scripts/fetch/fetch_ren_portugal.py    # Portugal: 15-min generation, capacity, no token
```

Only **Spanish installed capacity** still needs a free API token (Portugal's
is already covered by REN). Copy
`.env.example` to `.env` and fill it in:

```bash
.venv/bin/python scripts/fetch/fetch_esios_spain.py --probe
.venv/bin/python scripts/fetch/fetch_entsoe_spain.py --probe
```

## What makes this setting distinctive

OMIE publishes every offer submitted by every unit — accepted **and
rejected** — for ~2,000 units per day. That supports designs requiring
observed bid functions, which markets without published bids cannot support
at all.

## Layout

```
scripts/lib      shared modules        scripts/qa        integrity audit
scripts/fetch    one per data source   scripts/analysis  descriptives (R)
scripts/build    derived artefacts
```

`data/` is gitignored but carries its own [README](data/README.md) describing
every subfolder. Everything in it is re-fetchable from `scripts/`.

Verify the data at any time:

```bash
.venv/bin/python scripts/qa/audit_data.py
Rscript scripts/analysis/descriptives.R
```
