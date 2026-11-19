# The hydro departure, firm by firm (table, 2026-11-19)

**Assembled from existing outputs; nothing estimated.** Sources (corrected ownership, 2026-10-28):
`outputs/tables/price_taking_simulation_hydro_without_firm_reading.csv` (leave one firm out),
`price_taking_simulation_hydro_size.csv` (size by firm), `price_taking_simulation_hydro_by_month2021_single_reading.csv`
(months of 2021), `fixed_step_iberdrola.csv` (second hydro design). Background: `notes/rq-price-taking-simulation.md` §8.

**Why leave-one-out and not a β per firm.** β is identified by comparing firms in the same hour (class × hour effects
absorb a single firm's incentive: first-stage F 0.0 for every firm alone, §8). So "which firm carries it" is answered
by dropping each firm and seeing whether the departure survives.

**How to read β.** Share of the Nash markup a firm adds to its water value λ*: 0 = price-taking, 1 = Nash. "Departs"
means the 95% set lies outside the band simulated price-takers give.

## 1. Leave one firm out

| Sample without… | 2019–21H1 β [95% set] | departs? | 2024–2025-09 β [95% set] | departs? |
|---|---|---|---|---|
| (all firms) | +0.25 [0.15, 0.34] | yes | +0.19 [0.08, 0.33] | yes, narrowly |
| EDP | +0.20 [0.10, 0.31] | yes | +0.25 [0.11, 0.41] | yes |
| Endesa | +0.32 [0.20, 0.42] | yes | +0.13 [0.00, 0.28] | **no** |
| **Iberdrola** | **−0.01 [−0.12, 0.10]** | **no** | **+0.10 [−0.04, 0.24]** | **no** |
| Naturgy | +0.29 [0.17, 0.39] | yes | +0.22 [0.10, 0.36] | no (touches band) |
| Repsol | +0.29 [0.17, 0.40] | yes | +0.18 [0.06, 0.33] | no (touches band) |

Price-taker bands differ by sample (2019–21H1 roughly −0.2 … +0.05, 2024–25 roughly −0.17 … +0.11); each row's band is in the csv.
Movhera is absent from 2019–21H1 (its Douro dams sat in EDP's unit until 2021-09-08), so it is not a row.

## 2. Size, by firm (at the pooled β; markup = β × the firm's Nash markup x)

| Period | Firm | Units | Net-seller share of hours | Nash markup x, seller hours (€/MWh) | Markup on seller steps, €/MWh [95%] | Share of hours its hydro sets the price |
|---|---|---|---|---|---|---|
| 2019–21H1 | all | 37 | 48% | 3.3 | 0.98 [0.44, 1.53] | 35% |
| | **Iberdrola** | 6 | 60% | 5.1 | **1.49 [0.67, 2.33]** | 9% |
| | EDP | 7 | 52% | 2.9 | 0.86 [0.39, 1.34] | 18% |
| | Endesa | 10 | 0.2% (net buyer) | 1.3 | 0.37 [0.17, 0.58] | 4% |
| | others | 14 | 50% | 1.2 | 0.34 [0.15, 0.53] | 5% |
| 2024–2025-09 | all | 38 | 51% | 12.0 | 2.08 [−0.13, 4.66] | 35% |
| | **Iberdrola** | 7 | 70% | 16.3 | **2.83 [−0.18, 6.33]** | 13% |
| | EDP | 7 | 37% | 10.9 | 1.89 [−0.12, 4.23] | 12% |
| | Endesa | 10 | 0.5% (net buyer) | 1.6 | 0.28 [−0.02, 0.62] | 3% |
| | others | 14 | 63% | 4.5 | 0.78 [−0.05, 1.75] | 7% |

Effect on the clearing price, all firms: 2019–21H1 −€0.01/MWh per hour on average (sellers' markups offset by
buyers' markdowns). The pooled β in the size file is the single-seed 0.29 used for scaling; the ten-seed headline is
0.25, so markups above are about 15% high.

## 3. When it stops (all firms, by month of 2021)

| Month | β [95% set] | departs? |
|---|---|---|
| 2021-04 | +0.44 [0.24, 0.73] | yes |
| 2021-05 | +0.24 [0.13, 0.36] | yes |
| **2021-06** | **−0.08 [−0.27, 0.15]** | no |
| 2021-07 | −0.04 [−0.22, 0.10] | no |
| 2021-08 | −0.01 [−0.11, 0.07] | no |

## 4. The second hydro design disagrees

The fixed-step design (offer at the expected running share; pooled 2019–2025-09) finds Iberdrola's **seller** steps
*below* price-taking in the slope on Zb (−0.27 [−0.45, −0.08]) and its **buyer** steps far above (+1.80 [0.97, 2.63]),
traced to routing hydro from own-retail contracts into the auction (memory, 2026-10-21). It does not find the
2019–21H1 departure, and finds a 2023 Iberdrola one instead.

## Reading

The 2019–21H1 departure is **Iberdrola's**: it survives dropping any other firm and disappears without Iberdrola.
Iberdrola's markup there is about €1.5/MWh on seller steps, on 9% of price-setting hours. It stops between May and June
2021. The 2024–25 departure rests on Iberdrola and Endesa together and is fragile. Any claim about the June 2021 stop
(test T2 / D1, `docs/specs/2026-11-19-reform-market-power-design.md`) is therefore a claim about Iberdrola's hydro.
