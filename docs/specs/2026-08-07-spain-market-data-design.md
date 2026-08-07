# Spanish market data acquisition — design

**Date:** 2026-08-07
**Status:** IMPLEMENTED (token-gated portion pending user action)

## Context

The previous project (`~/Desktop/vre_hydro_thesis`) studied VRE market value
in Brazil's cost-based, hydro-buffered system. That research question was
retired on 2026-08-07. Spain is adopted as a candidate setting.

The decision taken deliberately: **acquire data first, choose the question
second.** No framing, literature, or concepts were carried over. The Brazil
repo remains intact and unmodified.

## Why Spain

Brazil is cost-based — dispatch and prices come out of NEWAVE/DESSEM and no
bids exist. Spain is bid-based, and OMIE publishes every offer submitted by
every unit, accepted and rejected, at ~2,000 units/day. That is a class of
micro data the previous setting structurally could not provide.

## Scope

Window **2018-01-01 → 2026-05-31**, bounded by the bid archive's start.

| Dataset | Source | Token | Granularity |
|---|---|---|---|
| Day-ahead prices (ES + PT) | OMIE `marginalpdbc` | no | hourly → 15-min from 2025-10 |
| Unit-level bid curves | OMIE `curva_pbc_uof` | no | hourly, per unit |
| Generation / demand / balance | REE `apidatos` | no | daily |
| Hourly generation, demand, capacity | ESIOS | **yes** | hourly |
| Load, generation, capacity, flows | ENTSO-E | **yes** | hourly |

## Decisions

**Location `~/projects/vre_spain_thesis`, not the Desktop.** The Desktop is
iCloud-synced and silently evicts large files to stubs; the Brazil repo had
31 evicted files at the time of this decision. Keeping `data/` off iCloud
removes that failure mode permanently.

**Minimal scaffolding, zero inherited content.** Repo carries fetch scripts,
a data-facts-only CLAUDE.md, and nothing else. No RQ section until a question
is chosen.

**Keep both zips and parquet.** Zips (~1.7 GB) are the reproducible archive;
re-downloading 101 months to fix a parser bug is slow. Parquet compresses far
better than estimated (108 MB raw → ~8 MB), so the total is ~2.6 GB, not the
5 GB budgeted — comfortable against 18 GB free.

**Keep all bids, not only cleared ones.** Rejected offers are the point: the
gap between 63,599 MWh offered and 24,872 MWh cleared in a single hour *is*
the object of interest for any bid-behaviour design.

**Stream zips to parquet without unpacking.** Peak disk stays near
zip+parquet rather than the ~11 GB unpacked size.

**Resolve ESIOS indicators by name, never by hardcoded id.** ESIOS ids are
unstable and poorly documented; guessing produces silently wrong series.

## Verification performed

- **Bid parse validated by the market-clearing identity.** Matched buy must
  equal matched sell in every hour. Holds at 0.0000% gap across every month
  processed, with one documented exception (2018-06-14).
- **Price column order established empirically**, not assumed — cross-checked
  against matched bids on a market-splitting hour.
- **Row counts reconcile exactly.** Hourly era 2,830 days × 24 − 8 + 7 =
  67,919; 15-min era 243 × 96 = 23,328; total 91,247, zero bad timestamps.
- **DST handled in both resolutions** — 23/25 and 92/100 period days.

## Findings that changed the implementation

1. **OMIE switched to 15-minute MTU on 2025-10-01.** Caught only because
   row counts came to 29.7 periods/day instead of 24. An hourly assumption
   would have silently mis-stamped 17,496 rows.
2. **Prices for 2018–2022 exist only as yearly zips.** The first full run
   lost 1,829 of 3,073 days before this was found.
3. **REE hourly and capacity endpoints are broken**, which is what makes the
   ESIOS/ENTSO-E tokens load-bearing rather than optional.
4. **REE balance nests its series** one level deeper than the other endpoints.
5. **REE timestamps are local**, so naive UTC conversion shifts every daily
   observation back a day.

## Outstanding

- **User action:** request ESIOS and ENTSO-E tokens (both free, both require
  a human). Until then there is no hourly generation, hourly demand, or
  installed capacity.
- Both token scripts are written but have never been executed. Run `--probe`
  first; if a contract differs, that is where it surfaces.
- No research question. Deliberate.
