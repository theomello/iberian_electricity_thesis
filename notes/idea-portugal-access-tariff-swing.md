# Idea: the Portuguese access-tariff swing of 2022–2024, with Spain as the control

**Status: idea only, written 2026-11-16. Nothing estimated, nothing downloaded, no rules set.** The tariff figures below come
from summaries of web search results, **not from ERSE's documents**; every number needs to be read in the source before it is
used. If the idea is taken up it needs its own design file in `docs/specs/`, starting with a price gate.

## In one example

A Portuguese factory on medium voltage pays its retailer the wholesale energy price plus a regulated access tariff for the
network and the system's policy costs. In 2022 that tariff added, say, €30/MWh in the peak period. In 2023 the regulator set it
**negative**: the same peak hour now subtracts from the bill. In 2024 it turned positive again. A Spanish factory across the
border buys in the same wholesale market at the same hourly price and saw none of this. If Portuguese demand responds to
price, it should rise relative to Spain in 2023 and fall back in 2024, and if the tariff's spread between peak and off-peak
hours moved too, the within-day shape should move with it.

(The €30 is a placeholder to show the mechanism, not a read value.)

## The shock

- **What moved.** ERSE (Entidade Reguladora dos Serviços Energéticos, the Portuguese energy regulator) sets the network access
  tariffs (*tarifas de acesso às redes*) that every customer pays, in the regulated and the free market alike. They include the
  CIEG (*custos de interesse económico geral*, the policy costs: mainly the support paid to renewable and other special-regime
  generators above the market price).
- **Why it went negative.** When the wholesale price is very high, supported generators are paid less than the market price,
  so the support cost turns into a surplus, which is returned to consumers through the access tariff. For 2023 the reported
  change against 2022 was about −188% for medium voltage, −108% for special low voltage and about −205% for normal low
  voltage (the last from the proposal, not the decision). For 2024 the tariffs turned positive again, reported as +316%.
- **Dates.** Annual tariffs each 1 January, plus exceptional mid-year settings: July 2022, 1 July 2023 and 1 June 2024. The
  2023 and 2024 exceptional settings raised the access tariffs because the wholesale price had fallen. That gives roughly six
  steps in three years, in both directions.
- **Why it is plausibly exogenous.** The driver is the wholesale price level through an accounting rule, with a lag (tariffs
  are set on forecasts and corrected), not Portuguese demand. Spain shares the wholesale price, so the difference between the
  two countries removes the direct effect of the wholesale price itself.

## The comparison

The paper's design mirrored: Portugal treated, Spain the control, per-hour LASSO errors from a pre-period, then

1. **Level:** Portugal minus Spain, after minus before each step. This is a level elasticity, which the Spanish reform could not give.
2. **Shape, if the price gate shows one:** the access tariff differs by period (*ponta*, *cheias*, *vazio*, *super vazio*: peak,
   mid, off-peak, deep off-peak) and by voltage level. If the swing changed the spread between periods, (peak minus off-peak) ×
   (Portugal minus Spain) × (after minus before) is the paper's triple difference. Whether the spread moved is **not known yet**.
3. **Dose across voltage levels:** the percentage changes differ by voltage level (−188% against −108% above), so the response
   should scale with the dose across groups inside Portugal, at the same dates.

Many dated steps in both directions suit the randomization inference already built.

## Data

- **On disk:** REN's Portuguese load (15-minute production and daily balance), the purchases of the Portuguese regulated
  supplier SU Eletricidade in OMIE (unit `EDPUC2`), the Spanish series by voltage level (ESIOS), OMIE prices, weather.
- **On disk but not what is needed:** the ERSE monthly bulletins in `data/erse/` are retail-market summaries (switching, market
  shares, customer numbers by segment). They do not hold the tariff tables (checked on `boletim_202301.pdf`). They may give
  consumption and customer counts by segment.
- **Needed:** ERSE's tariff directives and press dossiers for 2021–2025 (access-tariff prices by voltage level and period, and
  the exceptional settings); Portuguese consumption by voltage level or by customer segment at daily or hourly resolution.
  E-REDES (the Portuguese distributor) has an open-data portal with hourly consumption by postal code and other series; its
  start date and whether it splits by voltage level are **unconfirmed**.

## Weak points

- **Spain is a noisy control in 2022–2023.** The gas cap's adjustment charge, the tax cuts and the charge changes all moved
  Spanish retail prices in the same years. The Spanish price path is known and can be netted out, but the design then rests
  on two countries' price changes, not one.
- **Pass-through to the customer.** Free-market contracts in Portugal may pass the access tariff through at once, with a lag,
  or not at all for fixed-price contracts. The regulated tariff for households is set as an all-in price, so the access-tariff
  swing may not show in what a regulated household pays. The effective dose is unknown until retail prices are read.
- **Mass switching to the regulated supplier.** In 2022–2023 the Portuguese regulated tariff undercut the market and customers
  moved back, so SU Eletricidade's purchases changed composition. The same series was the paper's control; here it is in the
  treated country and unreliable as a household measure.
- **The swing follows the wholesale price.** A high wholesale price lowers the access tariff, so the all-in price moves less
  than either part. The dose has to be the all-in price change relative to Spain, which may be much smaller than the headline
  percentages. This is the first thing a price gate must measure.
- **The crisis itself.** Gas prices, industrial output and the 2022 drought differ between the two countries; a level
  difference-in-differences over a year is exposed to all of them. The mid-year exceptional steps are sharper than the January ones.
- **Portuguese demand by group.** Without a series by voltage level or segment, only the national total is available, and the
  dose-across-groups comparison is lost.

## References

In `papers/md/`: Enrich, Li, Mizrahi and Reguant (2024) for the method; Burlig et al. (`w23908`); the triple-difference papers
(`250216126v3`, `250219620v3`, `250509942v3`); Conley and Taber (`t0312`); Callaway, Goodman-Bacon and Sant'Anna (`w32117`) for a
continuous dose; von Graevenitz and co-authors (`ssrn-4251564`) for firms' response to network charges; Rambachan and Roth
(`honestparalleltrends-main-july21`) for reporting under a level drift.

Web pages found by search, **not read in full**:
- ERSE, exceptional tariff setting from 1 July 2023: https://www.erse.pt/comunicacao/comunicados/fixacao-excecional-de-tarifas-de-eletricidade-a-vigorarem-a-partir-de-1-de-julho-de-2023/
- ERSE press dossier, 2023 tariffs: https://www.erse.pt/media/redjinrl/dossier-de-imprensa_-tarifas-ee-2023.pdf
- ERSE, exceptional tariff proposal from 1 June 2024: https://www.erse.pt/communication/press-releases/proposta-de-fixacao-excecional-de-tarifas-de-eletricidade-a-vigorarem-a-partir-de-1-de-junho-de-2024/
- Observador on the 2024 increase: https://observador.pt/2023/10/17/injecao-maior-que-a-anunciada-e-divida-a-duplicar-o-que-explica-a-subida-conhecida-quase-a-meia-noite-de-19-na-luz-em-2024/
- E-REDES open data (mirror listing): https://opennetzero.org/ep-electricidade-de-portugal-e-redes/hourly-consumption-by-postal-code

## What a first look would involve (not started)

1. Read ERSE's tariff tables 2021–2025: access-tariff price by voltage level and period at each step, and whether the period spread moved.
2. Build the all-in price change (wholesale plus access tariff) for Portugal against Spain at each step: the price gate.
3. Read two or three Portuguese retailer price sheets or ERSE's reference prices to see the pass-through.
4. Establish what E-REDES publishes by voltage level or segment, and from when.

## Update 2026-11-18: what E-REDES publishes (catalogue metadata only, nothing downloaded)

Read from the open-data API (`e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets`, 70 datasets), first and last period by query:

| Dataset id | What | Period | Rows |
|---|---|---|---|
| `consumo-total-nacional` | national consumption every 15 minutes, **by voltage level (BT, MT, AT, MAT)** | 2023-01-01 → 2026-11-16 | 135,761 |
| `3-consumos-faturados-por-municipio-ultimos-10-anos` | monthly billed energy by parish and **voltage level** | 2020-11 → 2026-07 | 310,745 |
| `consumos-faturados-por-periodo-tarifario` | monthly billed energy by parish and tariff period (ponta, cheias, vazio, super vazio) | 2023-01 → 2025-12 | 103,760 |
| `diagrama_carga_subestacao_*` | substation load, 15-minute | 2025-03 → 2026-03 (sliding) | about 4 M each |
| `consumoshorariocodigopostal*` | hourly by postal code | 30-day sliding window, no history | - |

What this settles: **nothing hourly before 2023 exists** (so no 2018-21 control for the Spanish 2021 reform), but the access-tariff swing (July 2022 to June 2024) has **monthly consumption by voltage level from November 2020** and **15-minute consumption by voltage level from January 2023**, which covers the 1 July 2023 and 1 June 2024 steps. The dose-across-voltage-levels comparison (point 3 above) is therefore possible at monthly resolution, and the within-day shape only from 2023. Whether the BT/MT/AT/MAT split in `consumo-total-nacional` is a billing or a metering split, and whether the monthly file is complete for 2020-11 to 2022, is **not checked**.

## Decision 2026-11-18: Portugal is used only as a control, never as the treated country

The user decided to use Portugal only as a control. The treated-Portugal design above (access-tariff swing 2022-24) is **not pursued**; the sections above are kept as the record of the idea. What follows is the first read of ERSE documents for the control use (downloaded to `data/erse/tariffs/`: `dossier_tarifas_ee_2021.pdf`, `estrutura_tarifaria_se_2021.pdf`, with text copies; read from the files, not from search summaries).

**Facts read (ERSE press dossier of 15 December 2020, tariffs for 2021).**
- Access tariffs are fixed once a year, **valid 1 January to 31 December**, and retailers revise their tariffs in January. There is no mid-year step in the 2017-21 history the dossier shows.
- Annual variation of the access tariffs, mainland Portugal (read from the dossier's figure data), 2017 / 2018 / 2019 / 2020 / 2021: MAT+AT+MT +4.7%, -4.4%, -10.6%, +1.3%, 0.0%; BTE +4.7, -4.4, -10.6, +1.3, +6.2; BTN +4.7, -4.4, -16.7, +1.3, +6.3 (cumulative -9.3%, -3.8%, -10.2%).
- The 2021 increase in BTE and BTN comes from a 6.2% rise in the global system use tariff (policy costs), not from the networks.
- The transitional regulated sales tariffs were already abolished in MAT and AT; **MT's legal end date is the end of 2021, BTE's the end of 2022, BTN's 2025.** So MT customers still on regulated tariffs moved to the market on 1 January 2022, which is a structural event in the Portuguese medium-voltage segment right after the Spanish reform (1 June 2021).
- The time-of-use periods (ponta, cheias, vazio normal, super vazio) are set in the daily and weekly cycles, with a separate transitional daily cycle for MT in 2021. The cycle tables are Quadros 5-6 to 5-9 of the tariff-structure document; not compared hour by hour with Spain's 2021 periods.

**What this says for the control.** On the tariff side Portugal is clean for the Spanish June 2021 reform: its access tariffs did not change at that date, and the previous steps are all annual on 1 January. Caveats: (1) MT regulated-tariff extinction on 1 January 2022 sits in the post window; (2) COVID restrictions differed in timing between the countries; (3) Portugal and Spain share the Iberian gas-cap exception from June 2022, so Portugal is **not** an untreated control for the gas cap.

**What it does not fix.** The data side is unchanged: E-REDES has monthly consumption by voltage level only from November 2020 and nothing hourly before 2023, so the 2018-21 pre-period for an hourly or industrial control is still missing. Whether REN's data hub or an E-REDES/ERSE request holds earlier voltage-level history is **not known**.

## Request sent 2026-11-18

The user sent the data request (`notes/draft-request-portuguese-load-history.md`) to `premio.opendata@e-redes.pt`, the open-data team's address on E-REDES's Open Data Academy Challenge page. Nothing received yet. Not yet asked: REN (data hub) and ERSE, which may hold voltage-level history before 2023. If E-REDES answers with a series, check the BT/MT/AT/MAT definition against the 2023 `consumo-total-nacional` before joining.
