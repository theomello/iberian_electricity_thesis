# Reactor outages by cause: the instrument for n

Framework spec §9.3 (rank 1) and §9.7 step 1. Built 2026-10-05.
Script: `build/build_reactor_outages.py` (`--verify`). Outputs:
`outputs/tables/reactor_outage_hours.parquet`, `reactor_outage_dose.parquet`,
`reactor_outage_spells.csv`. First-stage probe:
`.superpowers/sdd/2026-10-05-reactor-outages/first_stage_probe.py` (not committed).

**In one line.** An unplanned reactor outage lowers each owner's exposed net position
by 0.86 MW per MW of its share of the lost output, with hour effects absorbing the
price (F 121). The outages are not preceded by unusual prices. The undeclared cuts
of 2024–2026 are price responses and are kept out.

## 1. What is built

- **Lost output**, hour by hour, for the seven reactors (Almaraz 1 and 2, Ascó 1 and
  2, Cofrentes, Trillo, Vandellós II): the month's `cab` max power minus the PDBF
  schedule (all role codes; fixed the day before delivery), when above 3% of capacity.
  516,257 reactor-hours, 2018-01 → 2026-05.
- **Cause**, from the OMIE `indisp` declaration covering each hour (451 declarations,
  classified by keyword, first match wins). A declaration explains at most the
  capacity it takes away; the rest of the hour's loss is **undeclared**.
- **Dose**, each owner's share of the lost MW that day (`lib/unit_ownership.py`).
  The shares are the ones the bilateral flows confirm
  (`report-ownership-mapping.md` §4).

Classes:

| class | causes | known when offers close? |
|---|---|---|
| planned | refuelling (42 spells), programmed maintenance, tests, end-of-cycle derates | yes, scheduled weeks or months ahead |
| unplanned | trips, faults, leaks, unplanned maintenance, Vandellós II's 2018 long stop, a refuelling extension | no: enters the schedule the next day |
| regulatory | waiting for authorisation (Cofrentes 2022), grid-caused trips | partly |
| economic | declared "flexible operation" (Almaraz 1 and Cofrentes, April–May 2025), the April 2020 lockdown derate | chosen |
| undeclared | lost output no declaration covers; 465 of its 601 spells fall on days `indisp` has no snapshot for | mostly chosen (§3) |

## 2. How much, and when

Lost output by class, TWh:

| year | planned | unplanned | regulatory | economic | undeclared |
|---|---|---|---|---|---|
| 2018 | 3.46 | 4.62 | 0.13 | 0 | 0.71 |
| 2019 | 4.66 | 0.53 | 0 | 0 | 1.04 |
| 2020 | 4.28 | 0.58 | 0 | 0.08 | 1.46 |
| 2021 | 5.60 | 0.84 | 0.03 | 0 | 1.18 |
| 2022 | 3.90 | 0.78 | 0.20 | 0 | 1.08 |
| 2023 | 4.67 | 0.57 | 0.26 | 0 | 1.89 |
| 2024 | 4.72 | 1.23 | 0 | 0 | **7.80** |
| 2025 | 5.26 | 0.44 | 0 | 0.92 | **5.08** |
| 2026 (to May) | 2.98 | 0 | 0 | 0 | **5.45** |

Spells of at least 50% lost: 51 planned (median 915 hours), 49 unplanned (median 41
hours), 3 regulatory, 2 economic, 601 undeclared (median 10 hours). Unplanned spells
by reactor: Cofrentes 13, Ascó 1 and 2 10 each, Vandellós II 9, Almaraz 1 3, Almaraz 2 2,
Trillo 2.

**Nuclear has become flexible.** Undeclared lost output rose from about 1 TWh a year
to 5–8 TWh from 2024, a fifth to a third of capacity in 2024–2026. It is a price
response (§3), and a descriptive finding in its own right: reactors now cut output at
low prices.

## 3. Are the outages timed on prices?

Price deviation from its month × hour mean, before each spell starts, €/MWh:

| class | spells | 48–25 h before | 24–1 h before |
|---|---|---|---|
| unplanned | 49 | +0.61 (3.41) | +2.69 (3.32) |
| planned | 51 | −5.76 (2.83) | −3.04 (3.20) |
| undeclared | 601 | −6.48 (0.90) | −8.70 (0.88) |

- **Unplanned outages follow ordinary prices.** Nothing suggests they are timed.
- **Planned outages follow somewhat low prices**, consistent with refuelling placed
  in cheap weeks. The date is chosen; what it does to each co-owner is fixed by the
  shares, and the timing is common to all co-owners in the period, so period effects
  absorb it.
- **Undeclared cuts follow low prices**, clearly. They are excluded from the
  instrument.

## 4. First stage

Each firm's exposed n (`firm_x.parquet`, net_mw) on its dose by class, firm × month
and hour effects (the hour effect absorbs the price and every common shock), week
clusters, five large firms:

| class | n, MW per MW lost (F) | X, €/MWh per MW lost (F) |
|---|---|---|
| **unplanned** | **−0.861 (0.078; F 121)** | −0.004 (F 35) |
| **planned** | **−0.890 (0.076; F 138)** | −0.005 (F 36) |
| regulatory | −0.981 (F 57) | −0.010 (F 15) |
| undeclared | −0.682 (F 216) | −0.001 (F 2) |
| economic | −1.629 (F 42) | −0.012 (F 22) |

Clean, priced periods only give the same (unplanned −0.871, F 117; planned −0.875,
F 146). One GW lost lowers X by about 5 €/MWh.

- **About 86–89% of the lost output reaches n.** The co-owner's retail buys in the
  auction what the reactor no longer supplies; the rest is replaced by the firm's
  own other plant.
- **The instrument is firm-specific with hour effects in**, which is what §9.2 needs.
  National forecasts are absorbed by the same effects.

## 5. Limits

- **Thin for Naturgy and EDP.** Their doses come only through Almaraz (Naturgy 11.3%)
  and Trillo (Naturgy 34.5%, EDP 15.5%), which have 7 unplanned spells between them.
  Mean unplanned dose: Endesa 94 MW, Iberdrola 44, Naturgy 2.1, EDP 0.6. Unplanned
  outages identify Endesa and Iberdrola; refuelling adds Naturgy and EDP.
- **`indisp` gaps after 2023.** 465 undeclared spells fall on days with no snapshot,
  so some unplanned trips there are counted as undeclared. They drop out of the
  instrument, which loses power but does not add bias. ENTSO-E's Article 15.1 data
  (token pending) would recover them.
- **Lead times from `indisp` are not planning horizons.** The register is seen only a
  few days ahead (median first sight 8 hours before a planned spell), while refuelling
  is scheduled months ahead.
- **PDBF is the day-ahead schedule.** A trip during day D shows from D+1; that is the
  timing that matters for day-ahead offers.
- **"Economic" moves n by more than its loss (−1.6).** Two flexible-operation spells,
  coinciding with the firms' other cuts; excluded anyway.

## 6. Next

The §9.2 regression: unit offers on X with unit × day and technology × hour effects,
X instrumented by the unplanned and planned doses. Then β⁺ and β⁻ within firm, since
an outage can push a firm across n = 0.
