# Every large unplanned outage as a shock to the owner's position

Design: `docs/specs/2026-10-19-outage-events-design.md`. Built and checked 2026-10-19.
Scripts: `build/build_outage_events.py` (`--verify`) → `outputs/tables/outage_event_hours.parquet`,
`outage_event_dose.parquet`, `outage_event_spells.csv`; `analysis/outage_events_checks.py`
→ `outage_events_checks.csv`. Logs: `.superpowers/sdd/2026-10-19-outage-runs/`.

**In one line.** Faults do not follow the owner's stake, so they are not withholding in
disguise. But they move the owner's position too little to help: a binding gas-plant
fault reaches the firm's net position at 40% of the lost output (se 21%, F 3.7), against
77–86% for a reactor. **The stop rule fixed in the design applies** (firm-level F below
20): the fault doses are not used as instruments, here or in the nuclear-cuts design.

## 1. What was built

- **Declarations:** 17,268 of dispatchable generator groups (gas, coal, hydro, pumped
  storage; reactors are built apart), last revision of each, linked to 64 OMIE units
  through REE's physical-unit register.
- **Classes from the reason text**, with the default "unclassified, out": fault 3,845,
  planned 4,800, water 1,604, operational 863, cold start 676, unclassified 5,480.
- **Kept:** 1,678 faults (≥ 100 MW lost, ≥ 6 h, declared under 24 h ahead) and 1,574
  planned stops (≥ 100 MW, ≥ 6 h, any lead).
- **Dose** = the owner's share of max(0, lost − (capacity − expected output)), expected
  output from the unit's PDBF schedule over the 7 days before, the first 14 days of a
  spell only.

Two fixes on the way, both now in the design (§8):

- **A combined cycle is one kind.** Twelve register their steam turbine as a `Vapor`
  group; classed group by group, their outages were cut into one-hour spells.
- **Year-long faults count for 14 days.** Castelnou's steam-turbine failure ran 9,720
  hours from May 2019, Castejón 2's 6,851 hours from May 2022.

## 2. Which faults bind

| kind | fault spells | ran in the week before | bind | GWh bound |
|---|---|---|---|---|
| gas | 535 | 55% | 42% | 2,464 |
| coal | 107 | 42% | 36% | 197 |
| hydro | 142 | 99% | **0%** | 0 |
| pumped storage, generating | 62 | 100% | 3% | 3 |
| pumped storage, pumping | 139 | 92% | 4% | 23 |

- **Hydro faults never bind.** A cascade unit (`DUER` is 57 groups) runs far below its
  capacity, so a 100–300 MW group fault leaves the rest able to carry the schedule. The
  cross-technology design (hydro faults instrumenting thermal offers) has nothing to work
  with.
- **Almost half the gas faults hit a plant that had not run that week.**
- **Binding fault spells at the five firms, 2018–2026:** Endesa 64, Iberdrola 58, EDP 50,
  Naturgy 37, Repsol 29. Mean dose, all hours: Endesa 8.7 MW, Iberdrola 8.3, Repsol 5.4,
  Naturgy 3.8, EDP 3.3. Unplanned reactor doses: Endesa 87, Iberdrola 41. **Five times the
  events, a tenth of the mean dose**, and spread to Naturgy, EDP and Repsol.

## 3. First stage

Firm's exposed n (GW) on each dose (GW), firm × month and hour effects, week clusters,
2018–2026. A dose that reaches n one for one reads −1 (+1 for pumping).

| dose | coefficient | reading |
|---|---|---|
| gas faults | **−0.40 (0.21)** | 40% reaches n; F 3.7 alone |
| coal faults | −2.78 (0.68); +6.19 (1.91) in 2023–2026 | more than one for one, then the other sign: not credible (EDP only, 2.4 MW mean) |
| pumped storage generating | +33.7 (5.7) | wrong sign, 34 times too large, 3 GWh of dose: noise |
| pumping faults | +0.84 (1.84) | right sign, no precision |
| planned stops, generating | +0.06 (0.27) | planned stops do not reach n |
| reactors, unplanned / planned | −0.77 (0.08) / −0.79 (0.08) | as before (`rq-reactor-outages.md` §4) |

- **Joint F of the fault doses: 15.8** (2018–2022: 13.2; 2023–2026: 14.2). Below the stop
  rule's 20, and it is carried by the two implausible coefficients. The one credible
  piece, gas, has F 3.7.
- **Why gas reaches n only partly** (*not tested*): a firm with several combined cycles
  covers a tripped one with the others, which a reactor owner cannot do for 1 GW; and the
  week before may overstate what the plant would have run.

## 4. Are faults chosen?

**On prices** (deviation from the month × hour mean before binding spells start, €/MWh):

| | 48–25 h before | 24–1 h before |
|---|---|---|
| gas faults (224) | +1.6 (1.9) | +2.1 (1.9) |
| coal faults (39) | **+12.3 (4.2)** | **+11.6 (5.2)** |
| planned gas stops (136) | +3.4 (2.4) | +2.0 (2.6) |
| planned pumped-storage stops (11) | −23 to −26 | −24 to −35 |

- **Gas faults follow ordinary prices.**
- **Coal faults follow high prices.** A plant can break only while running, and coal runs
  when prices are high, so this need not be a choice. Hour effects absorb it as an
  instrument; as evidence of timing it is ambiguous.
- **Planned pumped-storage work is put in cheap hours**, as for reactor refuelling.

**On the owner's stake** (check 2; 39,758 unit-days of units that ran the day before,
largest owner one of the five, 370 fault starts, daily rate 0.93%):

| owner's stake the day before | unit × month + date effects | unit × month |
|---|---|---|
| X = n / \|RD′\| (€/MWh) | −0.0014 pp (se 0.0078), p 0.86 | p 0.50 |
| n (GW) | −0.0011 pp (se 0.090), p 0.99 | p 0.80 |

- **No sign that faults follow the stake.** One standard deviation of X (11.5 €/MWh)
  moves the fault rate by −1.7%, with a 95% interval of about −21% to +17%.
- **This is a finding in its own right**: CCGT and coal breakdowns are not withholding
  dressed as faults, at least not in a way that tracks the owner's position. It is the
  thermal counterpart of the nuclear-cuts question, and it comes out price-taking.

## 5. What follows

- **Stop**, as the design's power rule says. Five times the events did not buy precision,
  because each event moves n far less than a reactor trip.
- **The reactor doses stay the outage instrument.** For the nuclear conduct test (T3),
  the instruments for the owner's position are the other reactors' outages (not the same
  site), regional wind and own-catchment rain.
- **Kept for reuse:** the classifier and spell table, for any later question about
  breakdowns (and ENTSO-E's outage data, if the token arrives, would fill the post-2023
  register gaps).
