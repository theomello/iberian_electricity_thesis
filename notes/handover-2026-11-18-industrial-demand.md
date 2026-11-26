# Handover, 2026-11-18: industry and business demand designs

Written to start a fresh session. Branch `tou-replication-closure`, PR https://github.com/theomello/iberian_electricity_thesis/pull/13. Everything below is committed and pushed except this file. Use `.venv/bin/python` (with `-I` for scripts that read downloaded files).

## Where we stand in one paragraph

On every margin we tried, **no industrial electricity-demand elasticity has been detected**, and the designs that could have detected one failed their own power gates or checks. Same-hour response (wind-speed instrument): a precise zero. Whole-day response: no detection, and the placebo fails by magnitude, so it is not interpreted. Metered consumption of plants under a consumption floor: uninformative, it detects only about -0.3. Within-day price shape (substitution): wrong-sign estimates, and the wind and solar instruments disagree. The sustained-price-level margin, the one the literature finds large, was scoped and dropped (no way to separate electricity from gas at sector level). The thread is closed unless a new data source or a new identification idea turns up.

## Rules that govern the work (user's, keep them)

- Pre-register every test with stop rules **before** running; failures are kept, not rescued.
- Ask the user before any new estimation run (their answer: "Confirmed, run it").
- Randomization inference (permutations across days within year-month, 1,000, seed 20261117), not two-draw placebo pass/fail.
- Do not choose designs by whether they give a negative interval.
- Downloads need an explicit yes; no subagents unless asked.
- Closed instrument routes (outage, bid-curve, slope, regression discontinuity) may be reopened when the setting calls for them; justify first.
- Style: math first, then a worked example; brief and direct; expand acronyms on first use.

## Specs (pre-registrations, with results appended)

| File | What |
|---|---|
| `docs/specs/2026-11-17-industry-iv-day-level-and-metered-design.md` | Part A day and cross-day level; Part B metered interruptible load; amendments (interruptibility floor, CNMC exposure share, duration and shifting, instrument scope, deviations); step 0 and step 1 results |
| `docs/specs/2026-11-17-industry-iv-price-shape-design.md` | substitution design on log(L_E/L_M); primary 2019-23 and extension 2024-25; amendments (blackout exclusion, N2/N3 learner calibration); all results |
| `docs/specs/2026-11-18-industry-iv-solar-channel-probe-design.md` | probe of S1's direct effect on plants under a floor; result: power gate fails |

## Scripts

| File | What |
|---|---|
| `scripts/analysis/industry_iv_day_level.py` | shared builders and Part A (`--step 0\|1`) |
| `scripts/analysis/industry_iv_metered.py` | Part B on ESIOS 836-846 interruptible load |
| `scripts/analysis/industry_iv_price_shape.py` | `--sample primary\|ext --step 0\|1 [--method N1\|N2\|N3]` |
| `scripts/analysis/industry_iv_solar_probe.py` | reduced-form probe, benchmark D |
| `scripts/analysis/industry_sector_intensity_scoping.py` | sector electricity vs gas intensity (INE) |
| `scripts/analysis/industry_iv_estimation.py`, `industry_iv_noise_reducers.py`, `tou_did.py` | estimation core, noise reducers, shared paths |

Result tables: `outputs/tables/industry_iv_*.csv` and `industry_sector_intensity_scoping.csv`.

## Results

Instruments: C1 realised wind speed through a power-curve transform (the only instrument that passed every registered check); W1 wind shape (evening minus midday power curve); S1 midday solar radiation (registered threat: sunshine lowers metered midday load directly).

| Margin | Estimate | Verdict |
|---|---|---|
| same hour, aggregate E3-E6 (2019-23) | +0.0001 [-0.021, +0.028] | precise zero |
| day level | -0.001 [-0.027, +0.028] | passes power gate at -0.05, not sharper than hourly; placebo fails by magnitude; not interpreted |
| exposed groups, same hour | -0.033 [-0.116, +0.017] (ESIOS 353), -0.007 (process units), -0.069 (refinery units) | none detected |
| metered 2019, plants under a floor | -0.015 [-0.133, +0.149] (hour) | uninformative; detects only about -0.3 |
| price shape, S1 (2019-23) | sigma -0.065 [-0.141, -0.030] | wrong sign (sigma must be at least 0) |
| price shape, W1 (2019-23) | sigma -0.016 [-0.047, +0.005] | no detection; Hansen test of S1 and W1 rejects (p 0.029) |
| price shape, extension 2024-25 | N1 with S1 and N2 with W1 run both ways | no detection either way; thread closed |
| solar probe (2019 interruptible load) | planted D detected by t-rank but randomization interval contains zero | power gate fails; S1 neither condemned nor cleared |
| sector-level sustained price | electricity and gas intensity rank correlation 0.87-0.92 (20 sector groups, 2017-22) | design dropped; cannot separate the two fuels |

Lessons recorded: the planted-effect table contains the real-outcome component (step 0 is not blind; an offset equals the real sigma); constant offsets are not proportional attenuation.

## Facts that explain the nulls

- **Interruptibility service:** participants must keep a contractual consumption floor, so their metered load cannot respond; last auction December 2019; the series halves in January 2020 and ends July 2020 (`memory/interruptibility-and-exposure-facts.md`; BOE orders in `literature/`).
- **Exposure to hourly prices (CNMC IS/DE/031/24, pp. 26-27):** about 49% of industrial contracts indexed, 32% hourly.
- **Price limits:** offers capped at €0-180.30 until 2021-07-06, then -€500 to €3,000; day-ahead went 15-minute on 2025-10-01; the 2025-04-28 Iberian blackout is excluded in the extension.
- **Midday prices (descriptive, our data):** never negative in 2019-23; share of midday hours (11-15) negative 8.9% in 2024, 12.6% in 2025, 40.4% in 2026; at or below zero 23.2%, 18.9%, 56.0%; lowest -€2 (2024), -€15 (2025); no floor ever binds.
- **Direct-consumer units:** 322 buyers with hourly cleared MW and bid curves (`docs/data-reference/ownership-and-units.md`); only 21-32 process-industry units active in a year, noisier than the national series; not the same as plant metering for retailer-served industry.
- **Portugal (control only, by user decision):** ERSE access tariffs change only on 1 January (none on 1 June 2021), so Portugal is clean as a control for the Spanish June 2021 reform; not an untreated control for the gas cap (Iberian exception). Data gap: E-REDES publishes monthly consumption by voltage level from 2020-11 and 15-minute national consumption by voltage level from 2023-01 only.

## Data used or fetched

- ESIOS 836-846 (interruptible load by sector), REE IRE (`data/ree/ire/Brutos_Sep2026.csv`, `Corregidos_Sep2026.csv`), OMIE prices and direct-consumer panel, ERA/wind and radiation weather as in the scripts.
- Downloaded 2026-11-18 (gitignored, re-fetchable): `data/ine/` (input-output tables 2016-22, energy-consumption survey tables 01001 and 02001, production index tables 60274, 60282, 60286); `data/erse/tariffs/` (2021 tariff dossier and tariff-structure document).
- Not downloaded: the I90 full-panel (on hold for disk space, a separate user task); physical-unit energy accounts (CFFE).

## Literature

Table by margin with where we sit: `notes/literature-industrial-demand-elasticities.md`. Full texts in `literature/` (gitignored) with markdown in `literature/md/`: Patrick and Wolak (NBER 8213); Boisvert, Cappers, Neenan and Scott (2004); Ambrosio (Niagara Mohawk case); Hirth, Khanna and Ruhnau (2024); Jessoe and Rapson (2015); Blonz (2022); von Graevenitz and Rottner (2024); Gerster and Lamp (2024); Labandeira, Labeaga and López-Otero (FEDEA DT 2009-18); Moral-Carcedo and Pérez-García (Applied Energy 2015; Energy 2019); Ciarreta and Espinosa (three papers); Ganapati et al. (output-price pass-through, not onsite generation); Torriti, Hassan and Leach (2010, Energy 35(4)); Enrich, Li, Mizrahi and Reguant (2024), the replication target.

Reference points by margin: within-day, Patrick-Wolak 0 to 0.27; substitution, Boisvert et al. 0.10-0.18 and 0.20-0.27, Niagara Mohawk industrial 0.11; sustained level, von Graevenitz-Rottner -0.4 to -0.6, Gerster-Lamp implied -0.09 to -0.20; Spain, Labandeira et al. households -0.247, companies -0.024, large consumers -0.015.

## Notes and other documents

- `docs/business-demand-evidence.md`: the evidence table (rows 17-21 and the 2026-11-18 update).
- `notes/idea-portugal-access-tariff-swing.md`: Portugal ideas, ERSE read, E-REDES catalogue, decision to use Portugal as control only, request sent.
- `notes/draft-request-portuguese-load-history.md`: the request (sent to `premio.opendata@e-redes.pt` on 2026-11-18).
- `notes/idea-calendar-boundary-business-tariffs.md`: seasonal-boundary idea for business tariffs (untracked, undecided; not mine).
- Memory: `no-outage-instrument.md`, `interruptibility-and-exposure-facts.md`, `portuguese-control-open.md`, `control-group-is-a-goal.md`.

## Open items

1. **Portugal control data:** waiting on E-REDES; REN (data hub) and ERSE not yet asked for 2018-22 voltage-level history. Choose any control by the 2018-19 placebo spread only, criteria pre-registered.
2. **I90 full-panel download** waits on the user freeing disk space.
3. **Herter "18% of customers give 75% of the response"** source still unidentified; Ciarreta and Espinosa (2006) working paper not in `literature/`.
4. **Meta-analysis table** once a reliable estimate exists.
5. **Not covered anywhere:** the sustained price level (needs plant-level or procurement data), purchases against consumption outside 2019, and plants' own generation.
6. **Undecided file:** the calendar-boundary note.
