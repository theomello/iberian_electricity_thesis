# Cogeneration and the gas cap: sources (read 2026-11-10)

For `docs/specs/2026-11-10-cogeneration-design.md`. What each rule says, where it was read, and how far it was
verified. "Secondary" means a law-firm or regulator summary found by web search, not the BOE text itself.

## Who is inside the mechanism

**Real Decreto-ley 10/2022, article 2.1.c** (BOE-A-2022-7843, consolidated text held in
`papers/md/boe-rdl-10-2022-consolidado.md`, read directly). Inside from the start: plants of group a.1 of Real
Decreto 413/2014 (cogeneration) "provided they have no remuneration framework among those regulated in article 14 of
Law 24/2013", and Portuguese gas cogeneration under the general remuneration regime. So gas cogeneration **without**
a regulated payment is eligible from 15 June 2022; cogeneration inside the regulated scheme (*régimen retributivo
específico*) is not.

**One offer unit per plant** (same decree, article on offer units, and OMIE's market rules as amended): a unit
receiving the adjustment may hold one installation only; cogeneration units of article 2.1.c may group several
installations if all are entitled. Read directly.

## The opt-in

**Real Decreto-ley 17/2022** of 20 September 2022 (BOE-A-2022-15354), in force 22 September. Secondary (Gómez-Acebo &
Pombo, Clifford Chance, Pérez-Llorca, PwC notes):
- cogeneration plants (and slurry and olive-sludge treatment plants) in the regulated scheme may give it up
  voluntarily and temporarily, and then ask the market operator and the system operator to be included in the
  mechanism;
- the waiver runs from the first day of the month after it is notified to the settlement body, until the mechanism
  ends; the notes describe a minimum of two working days before month end for a notice to count for the next month.
  **The earliest effective date is therefore 1 October 2022**;
- to return, the plant first leaves the mechanism, then asks the CNMC to end the waiver; the regulated scheme
  resumes on the first day of the following month.
- **Not verified in the BOE text:** the exact deadline wording, and whether the investment payment is lost along
  with the operating payment during the waiver.

## Is there a public list of units in the mechanism?

**None found** (one search, 2026-11-10). Registration goes through REE: its guide
(`https://www.ree.es/sites/default/files/12_CLIENTES/Documentos/Guia_mecanismo_de_ajuste.pdf`) says units and
installations are notified through a query in its customer portal. OMIE determined and settled the mechanism daily
(CNMC resolution DCOOR/DE/006/22), which is settlement, not a list. Not checked: OMIE's public file catalogue for a
per-unit settlement file of the adjustment; CNMC's monitoring reports. Until one is found, entry is inferred from new
offer units (`mechanism_source == "new_unit"` in `cogeneration_units.parquet`) and, in REE's data, new programming units.

## The regulated payment in 2022

Secondary throughout (PwC, Garrigues, a Congress briefing, CNMC reports found by search):
- **Real Decreto-ley 6/2022** of 29 March 2022 (BOE-A-2022-4972) brought the update of the scheme's remuneration
  parameters forward to **1 January 2022**, splitting the 2020-2022 half-period in two, and ordered a **new method for
  the operating payment** (*retribución a la operación*) of plant types whose costs depend on fuel and carbon prices.
- The 2022 parameters were approved by **Orden TED/1232/2022** of 2 December 2022, and the operating payment for the
  second half of 2022 by **Orden TED/1295/2022** of 22 December 2022. So from April to December 2022 a plant in the
  scheme was running against a payment that had been announced as changing and was not yet fixed.
- From 2024 the operating payment is updated quarterly (Orden TED/526/2024 replaced Orden IET/1345/2015).
- **Not read:** the two December orders' tables. So it is **not yet known** how many gas cogeneration plant types
  there are, what identifies a type, or what provisional values applied between April and December 2022.

**Reading for the design.** Gas cogeneration output falls in April 2022 (spec §1), the month after RDL 6/2022, and
before the cap. The decree is the first suspect: it made the 2022 operating payment uncertain and due to be revised
against much higher market prices. This is a reading of the dates, not a finding; gate G2 of the spec tests it.

## Can a unit's standard plant type be recovered?

**Not from data held here.** The registers on disk (OMIE listings, ESIOS archives 81 to 83, MITECO's `ElectraExp.csv`)
carry no plant type. The scheme's own register (*Registro de régimen retributivo específico*, kept by MITECO) assigns
each installation its type code (IT-xxxxx); whether it can be downloaded with plant names was not checked.
