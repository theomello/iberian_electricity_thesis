# The continuous intraday market — what OMIE and REE publish

Checked 2026-10-06 from OMIE's file listings and file-format specification and
REE's operating procedures. **Nothing was downloaded.** Every field statement below
is from the specification, not from a real file; see §6 for the test that would
confirm it.

**Why this note exists.** `notes/rq-intraday-surprise.md`: when a firm's own wind
farms produce more than it scheduled day-ahead, it sells only 8–26% of that surplus
in the intraday auctions. The rest goes to the continuous intraday market (MIC,
*mercado intradiario continuo*: the European SIDC/XBID platform, live in MIBEL
since June 2018), to schedule changes reported to REE, or to imbalance. The repo
has never fetched the continuous market.

**In one line.** OMIE publishes the continuous market **by unit, with agent and
unit codes, after 90 days**. `pibcic` gives each unit's net continuous-market
volume per round and period, in the same unit codes as `curva_pibc_uof`. It is
about 66 MB for 2019–2025. So a firm-level continuous position comparable to the
auction positions can be built. Imbalance cannot: it needs metered output per unit,
which is not public.

## 1. The datasets

Section 5.3 of OMIE's *Modelo de Ficheros*, v1.37 (dated 30/09/2025), pages 48–59.
Listings read 2026-10-06 at
`https://www.omie.es/es/file-access-list?parents%5B0%5D=<code>&realdir=<code>`.

| code | spec § | what it is | listing |
|---|---|---|---|
| `trades` | 5.3.2.7 | every executed trade | 98 monthly zips, `trades_YYYYMM.zip`, 2018-06 → 2026-07 |
| `orders` | 5.3.3.1 | every order sent to XBID | 98 monthly zips, `orders_YYYYMM.zip`, 2018-06 → 2026-07 |
| `pibcic` | 5.3.2.2 | net matched volume **per unit**, per round, per period (incremental) | 98 monthly zips, `pibcic_YYYYMM.zip`, 2018-06 → 2026-07 |
| `phfc` | 5.3.2.4 | final schedule **per unit** after each round (cumulative), as received from REE | 98 monthly zips, `phfc_YYYYMM.zip`, 2018-06 → 2026-07 |
| `precios_pibcic` | 5.3.1.1 | max, min and volume-weighted mean price per period and zone | 1,387 entries: yearly zips (2018–2021 seen) plus daily `precios_pibcic_YYYYMMDD.1` |

Also in the spec, **listings not checked**: `pibcac` (5.3.2.1, per-unit cumulative
result), `pibcice` (5.3.2.3, per unit with the corporate group tag),
`pibcic_stot` / `pibcic_tot` (5.3.2.5–6, daily totals by unit type and country),
`precios_pibcic_ronda` (5.3.1.2, weighted mean price per round, from v1.33, 2021),
`capacidad_inter_phfc` (5.3.4.1), and `omanulaintrac` (5.3.5.1, periods OMIE
annulled).

**A round** (*ronda*) is how OMIE batches continuous trading for scheduling. When a
round closes, OMIE passes its trades to REE, and REE updates the schedule (REE
P.O. 3.1 §11.2). The spec allows 1–25 rounds a day.

**Daily files inside monthly zips.** The spec names the members `trades_aaaammdd.v`,
`orders_aammdd.v` (two-digit year, as printed), `pibcic_AAAAA_aaaammddrr.v` and
`phfc_AAAAA_aaaammddrr.v`, where `AAAAA` is the agent requesting the file. The
public `pdbc`/`pdbf` files drop that agent field although the spec shows it for
them too, so expect `pibcic_aaaammddrr.v`. That is not checked.

**Resolution.** Hourly contracts until 2025-03-18. Quarter-hour contracts from
2025-03-19 (the spec's revision note for v1.36: "MIC/ MC en resolución 15 minutos"), the same date intraday
and `pdbf` moved. `Periodo` runs 1–100.

**Publication lag: 90 days**, the confidentiality period. The `orders` spec says
"(90 días)" explicitly. The listing dates agree: `trades_202605.zip` was posted
29/08/2026 and `pibcic_202606.zip` 28/09/2026. **The frontier month grows.**
`*_202607.zip` was posted 06/10/2026 and is about a quarter of a full month, so
this is the same frontier-zip trap as the bids (`month_may_grow`). `precios_pibcic`
has no lag: 2026-10-05 was posted 06/10/2026.

## 2. The fields: units and agents are identified

**`trades`** (one row per trade). Fields: `Fecha` (session date), `Contrato`
(delivery window as text, e.g. `20180814 19:00-20180814 20:00`), `AgenteC`,
`UnidadC`, `ZonaComp` (buyer's agent, unit and zone), `AgenteV`, `UnidadV`,
`ZonaVent` (the same for the seller), `Precio` (€/MWh), `Cantidad` (matched
quantity), then day, month, year, hour, minute and second of the match.

- **Agent and unit codes on both sides.** In the spec's example the buy side is
  blank and the sell side reads `IBGES;SIL;10YES-REE------0`. That fits a
  cross-border trade, where the counterparty is in another country and OMIE does
  not know it. So a foreign counterparty is anonymous and a MIBEL one is not.
  The spec's examples "do not contain real data", so this is the first thing to
  confirm on a real file.
- **Zone** is the EIC code (Energy Identification Code): `10YES-REE------0` is
  Spain, and Portugal has its own code. So Spain and Portugal are separable.
- **Contract, execution time to the second, price and quantity** are all present.
- Comma decimal (`64,7;2,9`), like `curva_pbc_uof`.

**`orders`** (one row per order sent): date, contract, zone, `Agente`, `Código`
(offer unit), price, quantity (MW), side (`C` buy or `V` sell), execution
condition (iceberg), validity condition (e.g. GTD, good till date), reduced
quantity, PPD (peak price delta), and the time sent to the second. It is
identified too.

**`pibcic`**: year, month, day, period, round, `Código` (unit, 7 characters),
`Potencia asignada` (MW, signed). One row per unit, round and period with a
change. This is the per-unit continuous-market result, the counterpart of the
matched (`C`) rows of `curva_pibc_uof` for the auctions.

**`phfc`**: the same fields, holding the cumulative final schedule after each
round. It is the schedule after day-ahead, the auctions and the continuous market.

**`precios_pibcic`**: date, period, then maximum, minimum and mean for each zone
(ES, PT, MO for Morocco). Prices only, no units.

Quantities are MW over the contract, as in the bid files. Energy is
`MW × contract minutes / 60`. The spec gives no unit for `Cantidad` in `trades`.

**Before parsing, read the older spec.** v1.37 describes only the current formats
("para información anterior al 30 de septiembre del 2025 será necesario comprobarlo
en la versión anterior"). v1.36 and v1.32 are at the URLs under Sources. They were
not read.

## 3. Size

Zipped sizes from the listings, in MB:

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | **2019–2025** |
|---|---|---|---|---|---|---|---|---|
| `pibcic` | 3.7 | 6.2 | 7.6 | 7.2 | 7.7 | 8.7 | 24.9 | **66** |
| `trades` | 6.9 | 16.1 | 21.5 | 21.2 | 33.1 | 39.4 | 132.1 | **270** |
| `orders` | 26.9 | 51.0 | 72.5 | 81.2 | 78.4 | 148.6 | 701.1 | **1,160** |
| `phfc` | 784 | 1,266 | 1,388 | 1,457 | 1,589 | 1,780 | 6,824 | **15,087** |

`precios_pibcic` is under 5 MB in all. Daily files: `trades` about 0.1 MB a day
zipped in 2024 and 0.6 MB in mid-2026, and `phfc` about 26 MB a day in 2026.
Unzipped sizes are not published.

**The jump in 2025 is mostly the quarter-hour switch**, which quadruples the
contracts. Over 2019–2024 `trades` grew about 6×, so the continuous market was
small early in the window used by the surprise analysis (2019 → 2024-06-13).

## 4. Per-unit schedules after the continuous market

**OMIE: yes, two.** `pibcic` holds each unit's continuous-market trades.
`phfc` holds each unit's final schedule after every round (*Plan Horario Final del
Mercado Continuo recibido del OS*). Both use OMIE offer-unit codes, the namespace
that `cab`, `pdbf`, `curva_pibc_uof` and `unit_ownership` already use.

**REE: yes, but in programming units (UP, *unidad de programación*), not OMIE's
offer units (UO, *unidad de oferta*).** The schedules after the continuous market
are defined in P.O. 3.1 (BOE-A-2026-17285):

- **PHFC** (*Programa Final definitivo*): PDVP (*programa diario viable
  provisional*, the day-ahead schedule after technical constraints) plus the
  intraday auctions and continuous rounds. Each round's publication lists only
  the UPs that changed.
- **PHFCIERRE**: the final schedule of every UP for the whole day, without round
  detail.
- **P48**: PHFC plus schedule changes between BRPs (balance responsible parties)
  notified after the continuous market, real-time constraints, balancing energy,
  and redispatch for outages and notified deviations. **P48CIERRE** is the complete
  day, published once the day is over.

P.O. 9.1 (BOE-A-2024-11535, annex §1.9) sets publication. Programmes by market
participant are released after one month. After 90 days "toda la información será
pública por unidad de programación, sin nivel alguno de agregación". **The P48 by
UP is released "en el plazo máximo de una hora desde su publicación"**, so with no
90-day wait.

Where these sit on ESIOS (*e·sios*, REE's information system):

- **I90DIA** (ESIOS archive 34) is the daily per-UP workbook released at 90 days.
  Secondary sources list sheets I90DIA19–25 as PHF-1 to PHF-7 and I90DIA26 as
  PBF. Whether it has a PHFC or continuous-market sheet was **not confirmed**.
  **Reserve sheets (2026-10-08, from a 2018 master's thesis, Rodríguez López, Oviedo,
  p. 21; nothing downloaded):** 36 tabs in one .xls, about 5 MB a day. I90DIA05 is
  the hourly secondary regulation band (aFRR) allocated to each UP; I90DIA29 the
  additional upward reserve; I90DIA07 tertiary energy; I90DIA06 deviation management;
  I90DIA03 day-ahead technical constraints. The layout may have changed since (aFRR
  through PICASSO from 2022, 15-minute products from 2025).
  **Checked on a real file, 2026-10-08** (`data/esios/raw/archives/34/I90DIA_20230615.zip`,
  6.7 MB zipped, one 28 MB .xls, 37 sheets; sheet I90DIA00 lists them). In 2023 sheet 29
  is declared start-up times, not additional reserve; 05 is the secondary band allocated
  by UP and direction in 96 quarter-hour columns, and its sum equals ESIOS 632 to the MW;
  13 is the secondary band offers; 02 the P48 (final schedule by UP, after every market);
  36 the PHFC (final intraday schedule, continuous trading included); 12 and 16
  unavailability; 27 bilateral contracts. So P48 and PHFC by UP are in the same file. REE's UP codes for hydro
  are OMIE's (`DUER`, `EBRFEN`: the `up` of archive 81). The ESIOS indicator catalogue
  (`indicator_catalogue.parquet`, 1,983 indicators) has reserves only as system totals
  (632/633 secondary band up/down, 627 additional upward reserve) and qualified aFRR
  capacity by technology (2329–2337; hydro 2335), none by unit or agent.
- **P48cierre** is a daily XML file of schedules by UP (energychisquared.com
  works with it).

Both are ESIOS archives. `CLAUDE.md` records that `/archives` answers 403 without
a token, apart from the `download_json` route for archives 82/83. The project
token was **not used**, so whether these two can be fetched without it is not
checked.

UP ≠ UO: an offer unit can contain several UPs (P.O. 3.1 annex II). The wind UPs
in archive 81 never appear in OMIE (`CLAUDE.md`, wind and solar farm locations).
REE's files would need their own UP → firm mapping.

## 5. Judgement

**Where the surplus goes: mostly answerable.** Take one firm and one period. Its
farms produce 100 MW more than the wind part of its day-ahead schedule.
`curva_pibc_uof` already shows how much its units sold in the auctions (say 15).
`pibcic` would show how much they sold in the continuous market, at the same unit
codes. The rest has three possible homes:

- REE's P48: BRP transfers and balancing after the continuous market.
- The firm's other units, which may buy back or ramp down. `pibcic` shows those
  too, because it covers every unit, so the firm-level net already nets them.
- Imbalance: metered output minus the final schedule.

Metered output per unit is not public. The repo would use its located-farm estimate
(ESIOS 1159 by province), as `rq-intraday-surprise.md` already does. So
**auction + continuous is measurable per unit; the residual is "everything after
the market", and can only be bounded at firm level.**

`trades` adds two things:

- whether the surplus goes **abroad**: a blank counterparty and a non-Iberian zone;
- whether a firm **trades with itself**: the same agent or group on both sides.

**A firm-level continuous position comparable to the auction one: yes for n, no for
|RD′|.**

- **n works.** `pibcic` → `attach_owners` → net position by group, round and
  period. That is the same construction as the auction panel in
  `intraday_firm_panel.py`, on the same unit namespace, with the same exclusion of
  pass-through suppliers.
- **|RD′| does not.** The continuous market is pay-as-bid with no clearing price
  and no aggregate curve per round. `orders` gives the order book, but a
  residual-demand slope built from a continuous book is a different object from
  the auction's. So X = n / |RD′| does not carry over.

**Limits.**

- Firms sell wind through portfolio units (`IBEVD11` "EÓLICA HABILITADA",
  `EDPSVD1` "VENTA RE"), so wind cannot be told apart from solar within a firm's
  continuous sales, the same as in the auctions.
- Volumes were small in 2019–2021.
- The 90-day lag means 2026 data stops at about June.

## 6. Files for a test download — for approval

A test needs one month in the surprise analysis's window. **January 2024** is
suggested: it is the repo's usual validation month, and it is hourly and before
the IDA auctions.

The URL pattern is the one `lib/omie_common.omie_url` already builds:
`https://www.omie.es/es/file-download?parents%5B0%5D=<code>&filename=<file>`

| file | why | size (zipped) |
|---|---|---|
| `pibcic_202401.zip` | the per-unit continuous result: the essential one | ~0.7 MB (2024 monthly average) |
| `trades_202401.zip` | confirms the agent and unit fields are filled; prices, counterparties, zones | **3.01 MB** (exact, from the listing) |
| `phfc_202401.zip` | optional: checks PDVP + auctions + `pibcic` = final schedule | ~150 MB (2024 monthly average) |
| `orders_202401.zip` | optional: the order book, only if order behaviour is wanted | ~12 MB (2024 monthly average) |

The minimum test is the first two, **about 4 MB**. Things to check on them:

- the unit fields are populated, and their codes join `unit_registry`;
- the sign convention of `Potencia asignada`;
- whether Portuguese units appear;
- whether summing `pibcic` over a day matches `pibcic_tot`;
- the share of January 2024 continuous volume on the five firms' units.

## Sources (all read 2026-10-06)

- OMIE listings: `https://www.omie.es/es/file-access-list?parents%5B0%5D=<code>&realdir=<code>`
  for `trades`, `orders`, `pibcic`, `phfc`, `precios_pibcic`.
- OMIE, *Modelo de Ficheros para la distribución pública de Información del mercado
  de electricidad*, v1.37, 30/09/2025, §5.3 pp. 48–59:
  https://www.omie.es/sites/default/files/2025-09/formato_ficheros_inf_pub_137.pdf
- Earlier versions, not read:
  https://www.omie.es/sites/default/files/2025-03/formato_ficheros_inf_pub_136.pdf
  (v1.36), https://www.omie.es/sites/default/files/2020-10/formato_ficheros_inf_pub_132.pdf (v1.32).
- REE, P.O. 3.1 *Proceso de programación* (BOE-A-2026-17285): definitions of PHFC,
  PHFCIERRE, P48, P48CIERRE, and §11.2:
  https://www.ree.es/sites/default/files/2026-09/PO_3_1-BOE-A-2026-17285.pdf
- REE, P.O. 9.1 (BOE-A-2024-11535), annex §1.9, publication by UP:
  https://www.ree.es/sites/default/files/2024-11/PO_9_1_BOE-A-2024-11535.pdf
- I90DIA as ESIOS archive 34 and its sheets (secondary):
  https://datons.com/blog/i90-electricity-market-analysis-python and
  https://github.com/JoyaAlbert/i90
- P48cierre by UP (secondary):
  https://www.energychisquared.com/post/analizando-las-curvas-de-energ%C3%ADa-de-los-sujetos-de-mercado-i/

## 7. Test download, 2026-10-06 (approved by the user)

`pibcic_202401.zip` (624 KB, 744 daily-round members `pibcic_AAAAMMDDRR.1`, 3.1 MB
unzipped) and `trades_202401.zip` (3.16 MB, 31 daily members `trades_AAAAMMDD.1`,
43.8 MB unzipped), saved in `data/omie/continuous/raw/`. The download URL needs
`parents=<code>` (unbracketed): `parents%5B0%5D=` answers with an HTML redirect page
of 810 bytes, which a fetcher must not take for the file.

**The specification holds on the files:**
- `pibcic`: header `PIBCIC;`, then `year;month;day;round;period;unit;MW;…`, one row per
  unit, round and period, signed net volume, **OMIE unit codes** (`GASVD12`,
  `EGEDRE1`, `CENTC01`: the same codes as the auction files). Dot decimal.
- `trades`: a title line, a blank line, then `Fecha;Contrato;Agente compra;Unidad
  compra;Zona compra;Agente venta;Unidad venta;Zona venta;Precio;Cantidad;Momento
  casación;`, **comma decimal**. The foreign side of a cross-border trade is blank.

So each firm's net continuous-market position by hour can be built with the ownership
module, as for the auctions.
