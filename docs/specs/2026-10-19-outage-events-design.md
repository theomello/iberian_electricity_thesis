# Every large unplanned outage as a shock to the owner's position

**Status: proposed 2026-10-19. Nothing here is built or run.** It extends the reactor
instrument (`notes/rq-reactor-outages.md`, framework spec §9.3) from 7 reactors to every
large plant in the outage register. Its doses also feed the nuclear-cuts design
([`2026-10-19-nuclear-cuts-design.md`](2026-10-19-nuclear-cuts-design.md), T3).

**In one example.** A boiler leak takes 350 MW of one of Repsol's gas plants offline for
two days. Repsol now has less to sell, so it gains less from a high price. If firms price
to their net position, Repsol's other plants should offer lower than rivals' comparable
plants on those two days. Price-takers would not change their offers.

**Why.** The reactor outages are a clean shock (not timed on prices, F 121 at the firm
level), but too few to pin β down: 49 unplanned spells, almost all at Endesa and
Iberdrola, and a unit-level F of about 10. The outage register holds far more faults, at
every large firm.

---

## 1. What the register holds (counted 2026-10-19)

OMIE's outage register (`indisp`), last revision of each declaration, linked to OMIE units
through REE's physical-unit register (ESIOS archive 81, `uf` → `up`; 93.7% of records
link). The filter: at least 100 MW lost (unit max power minus declared available), at
least 6 hours long, declared under 24 hours before it starts, and a reason naming a fault
(DISPARO, AVERÍA, FALLO, FUGA, ROTURA, INCIDENCIA, DEFECTO, ANOMALÍA, REPARACIÓN, VIBRACIÓN,
PROBLEMA, FISURA, NO PROGRAMADA). **1,605 declarations; median 48 hours, median 261 MW.**

| technology | faults |
|---|---|
| combined cycle (`Ciclo combinado`) | 657 |
| steam turbines (`Vapor`, `Turbina vapor - Fuel gas`) | 258 + 45 |
| pumped storage, pumping and generating (`Consumo bombeo`, `Turbinación bombeo`) | 210 + 80 |
| reservoir hydro (`Embalse`) | 204 |
| coal (`Hulla sub-bituminosa`, `Hulla antracita`) | 78 + 71 |

REE's technology labels in brackets; which plants sit under `Vapor` (coal or oil-fired
steam) is not yet checked.

By owner (the static `firm` column; dated owners will move some): Iberdrola about 620,
Endesa about 400, Repsol about 140, Naturgy about 90, EDP about 80, smaller firms the
rest. Faults fall from 2024 on (the register's partial months, §6).

**These counts are an upper bound on events.** They are declarations, not spells:
revisions and overlapping declarations of one breakdown have not been merged, and a
plant that was off anyway contributes nothing (§3).

**The other short-notice declarations are not faults and stay out of the main
instrument.** Same filter, 5,270 declarations in all, sorted by keyword (first match
in the order shown in the table):

| class | count | reasons (examples) | why out |
|---|---|---|---|
| fault | 1,605 | as above | the instrument |
| cold start | 536, mostly coal | "NECESIDADES DE ARRANQUE EN FRÍO" | cold-start lead time: the plant is off, a consequence, not a shock |
| operational | 297 | "INDISPONIBILIDAD OPERACIONAL" | says nothing about cause; could be a choice |
| water | 842 | reservoir level too low or high, Junta de Extremadura and Albufeira flow requirements | moves the hydro unit's own cost |
| planned | 923 | "PARADA PROGRAMADA", "MANTENIMIENTO", inspections, annual revisions | a separate class, as for reactors |
| unclassified | 1,067 | the long tail | out until read |

The reactor classifier (`CAUSES` in `build_reactor_outages.py`) defaults unknown text
to "unplanned", which would put all of these in. Non-nuclear outages need their own
classifier, with the default "unclassified, out".

## 2. Events: from declarations to spells

- Merge declarations of one unit that overlap or touch into one spell (the declaration
  leaving the least capacity sets each hour's loss, as for reactors).
- Event = the spell's first hour; the main sample keeps spells whose unit ran normally
  in the 7 days before (as the event study did for reactors).
- Spells inside a planned outage, or extending one, go to their own class.

## 3. Dose: what the outage takes from the owner's position

**A plant that was not going to run loses nothing.** A reactor runs flat out, so its lost
capacity is lost output. A gas plant that trips at 3 a.m. on a windy Sunday may have been
scheduled at zero anyway. So:

    dose_ft = Σ over the firm's tripped units of share_f × max(0, lost MW − headroom)
    headroom = unit capacity − expected output

A fault binds only where it cuts into what the unit would have produced. A 400 MW unit
expected at 250 MW loses 250 MW of output to a full trip, and nothing to a 100 MW
derate. The same rule covers a generator group inside a hydro cascade unit (`DUER` is 57
groups): the group's fault binds only if the rest of the cascade cannot carry the
expected schedule.

- **Expected output:** the unit's PDBF schedule in the same hour over the 7 days before
  the spell began. *My call*; the builder may replace it with a prediction from D-1
  forecasts if that fits pre-spell schedules better.
- **Sign:** a fault on a generating leg lowers the owner's n. A fault on a **pumping**
  leg (`Consumo bombeo`) cuts what it buys, so it **raises** n. The two are separate
  instruments, or one with the sign carried.
- **Owner shares by date:** `lib/unit_ownership.py`.
- **Firm-level first stage first:** n on dose, firm × month and hour effects, week
  clusters, as `rq-reactor-outages.md` §4. If faults reach n as reactor outages do
  (about 0.86 MW per MW), the dose is right.

## 4. Are the faults chosen?

Two checks, the second new.

1. **Timing on prices**, as for reactors (§3 of the note): the price deviation from its
   month × hour mean in the 48 hours before each spell. Unplanned reactor trips showed
   none.
2. **Timing on the owner's stake.** Do faults happen more often when the owner is a large
   net seller, or the residual demand it faces is steep? A logit or linear probability
   of a fault starting, unit × month effects, on the owner's expected n / |RD′|. If faults
   follow the stake, they are withholding dressed as breakdowns. That would end their use
   as an instrument, and it would be a finding in its own right, the thermal version of
   the nuclear-cuts question.

**Stop rule, fixed now:** if check 2 finds that faults follow the stake (p < 0.05), the
fault doses are not used as instruments anywhere, including the nuclear-cuts design.

## 5. Which offers can a fault move, other than through n

The reactor instrument was clean partly because its outcome was a different technology
from the shock. A fault can reach sister plants of the same kind in other ways:

| fault on | other channel | consequence |
|---|---|---|
| gas plant | shared gas supply: contracted gas freed up lowers the gas's opportunity cost for the firm's other gas plants | same-technology offers fall for a reason other than n; biases β up |
| hydro unit | the water stays in the reservoir: the basin's other units have more of it and a lower water value | same-basin hydro offers fall; biases β up |
| any | shared crews, the same grid node (technical constraints) | location check as in §6 of the note |

**So the main specification crosses technologies.** Gas, coal and steam faults instrument
the firm's hydro offers. Hydro faults instrument its thermal offers. Same-technology
results are reported as a check, read against the bias above. The failed unit's own
offers are never in the outcome.

## 6. Coverage

- **The register is partial at source from 2023** (43 of 100 monthly zips; the short-
  notice declarations are the part lost). Main sample: 2018-01 → 2022-12 plus later days
  the register covers. The 2024–2025 solar years are thinly covered; say so with every
  result.
- **The physical-unit register is a 2026-08-12 snapshot.** Plants closed before then
  (most coal, 2020–2021) may be missing. Measure the link rate by year and technology
  before relying on pre-2021 coal.
- **ENTSO-E's outage data** (Transparency Platform, Article 15.1: units of 100 MW and
  above, every version timestamped) would fill the post-2023 gaps once the token arrives
  (ticket #9472601).

## 7. Estimators

All exist already. Only the instrument changes.

1. **Firm-level first stage** (§3).
2. **Offer regression:** `outage_offer_test.py` (unit offer at 25% and 50% of volume,
   technology × date × hour and unit × week effects). The fault dose replaces or joins
   the reactor doses.
3. **Event study:** `outage_event_study.py`, owner's units against rivals' of the same
   technology, day by day around each fault.
4. **Step estimator:** `step_estimator.py` (thermal) and `step_estimator_hydro.py`, with
   the fault dose as instrument for the step's expected n / |RD′|.
5. **Null band:** the price-taking simulation (`price_taking_simulation.py`) with the
   fault dose, since the reactor instrument was biased under price-taking (hydro −0.40).
   Every estimate is read against its band.

**Order, each run proposed before it starts:** classifier and spell table → §3 first stage
and §4 checks (descriptive, cheap) → stop or continue → estimators 2–5.

**Power rule, fixed now:** if the firm-level first stage has F < 20, or the unit-level
first stage F < 10 with unit × week effects, report the first stage and stop. More
events are only worth it if they buy precision.

## 8. Left to the builder

- The fault keyword list beyond §1's, after reading the remaining reason texts (Spanish,
  inconsistently cased, some English: "PREVENTIVE MAINTENANCE HRSG").
- Merging rules for overlapping declarations.
- Whether a unit-level F computed on cross-technology outcomes needs unit × week or unit
  × month effects (faults last two days, so week effects should leave them alone, unlike
  refuelling).

**My calls, to check:** the 100 MW / 6 h / 24 h filter; expected output from the previous
7 days; the cross-technology main specification; the two stop rules.

**Two calls made while building (2026-10-19), not in the design as approved:**
- **One kind per OMIE unit.** Twelve combined cycles register their steam turbine as a
  separate `Vapor` group. Classed by group, one plant had two kinds, and its outages were
  cut into one-hour spells (52,784 "steam" spells, median 2 hours). Any unit with a
  combined-cycle group is now gas.
- **The dose counts the first 14 days of a spell.** Some faults last a year (Castelnou
  from May 2019, 9,720 hours). The week before says nothing about what the plant would
  have run months later, and a year-long dose repeats one daily profile that firm ×
  month effects do not remove.
