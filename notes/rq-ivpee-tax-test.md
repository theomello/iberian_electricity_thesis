# The 2024 IVPEE steps: a test of the cost term

Framework spec §9.6 and §9.7 step 3. Run 2026-10-06.
Script: `analysis/ivpee_tax_test.py`. Outputs: `outputs/tables/ivpee_tax_test.csv`,
`ivpee_tax_event_study.csv`, `ivpee_tax_step_windows.csv`,
`outputs/figures/ivpee_tax_event_study.png`. Log:
`.superpowers/sdd/2026-10-06-ivpee/run.log`.

**In one line.** The test runs, but it cannot see a tax this small. On the day the
rate went to 7% the Spanish − Portuguese gap rose by about the predicted amount, but
the gap jumps as much on ordinary month starts.

## 1. The idea

Spain's tax on the value of generation (IVPEE) takes a share τ of a Spanish plant's
revenue and none of a Portuguese plant's in the same auction. To keep its revenue
after tax, a Spanish plant must ask 1/(1 − τ) times as much. Example: a plant whose
gas costs 100 €/MWh must ask 107.5 €/MWh at τ = 7%.

The tax came back in three steps after its suspension (2021-07 → 2023-12):

| from | τ | predicted rise of a Spanish declared cost, relative to Portugal |
|---|---|---|
| 2024-01-01 | 3.5% | +3.6% |
| 2024-04-01 | 5.25% | +1.8% more |
| 2024-07-01 | 7% | +1.9% more |

**Portugal is untreated in 2024.** Its clawback, the charge that offsets the IVPEE, hits
a combined cycle only beyond 2,000 equivalent hours a year. In 2024 every Portuguese
combined cycle ran 14–1,190 hours (PDBF; the script checks it).

## 2. What is measured

**The declared variable cost, not the offer price.** With each offer a unit may set a
minimum-income condition: a fixed €/day plus a variable €/MWh it must earn. The
variable term is the cost the unit declares:

- combined cycles in both countries declare it on 89–100% of days;
- it changes on 96% (Spain) and 88% (Portugal) of unit-days;
- it sits at a median 1.3× (Spain) and 1.1× (Portugal) the implied fuel and carbon
  cost.

Portuguese combined cycles offered most of their 2024 volume at 0 €/MWh, so their
offer prices carry no cost. The term ended on 2025-03-18, which ends the sample.

**Model.** log of the declared term on Spain × log(1/(1 − τ)), with unit and date
effects; full pass-through gives θ = 1. Two problems found in the first run, and
fixed:

- **Turbogás closed.** Its three units declared a quarter of their cost in February
  and March 2024 and left the market on 2024-03-30. Dropped, with terms below half or
  above three times the implied cost.
- **The declared term does not scale with fuel cost.** Within a unit, before the tax,
  it moves 0.95% per 1% of cost in Spain and 0.70% in Portugal. Each unit gets its own
  slope on its log cost.

50 combined cycles (43 Spanish, 7 Portuguese), 27,880 unit-days, 2023-04 → 2025-03.

## 3. Results

| specification | θ (predicted 1) | se | p, θ = 0 | p, θ = 1 |
|---|---|---|---|---|
| **unit + date effects, unit cost slopes** | **0.04** | 0.56 | 0.95 | 0.18 |
| unit + date effects only | −0.21 | 0.51 | 0.69 | 0.02 |
| from 2021-07, cost slopes | −0.11 | 0.70 | 0.89 | 0.24 |
| from 2021-07, cost slopes, Spain × calendar month | −0.08 | 0.68 | 0.91 | 0.24 |

p-values from a wild cluster bootstrap by unit. The model without cost slopes is the
misspecified one.

In €/MWh: full pass-through at 7% would add 9.3 €/MWh to the median Spanish term
(128 €/MWh); the estimate is +0.3, with a 95% band of about ±10.

**The quarterly averages drift.** The step from 5.25% to 7% reads −8% where +1.9% is
predicted, and Spain × calendar-month effects from 2.5 untreated years do not change
it: the drift is particular to 2024, not seasonal.

**On the step days.** Declared terms are revised daily, so the jump on the day a rate
starts avoids the drift. Benchmark: the same jump on all 41 first-of-month dates from
2021-08 with no tax change.

| step | predicted | jump, ±7 days | ±14 days | ordinary month starts as large (±14) |
|---|---|---|---|---|
| 2024-01-01 | +3.6% | −1.2% (2.2) | −0.7% (2.3) | 59% |
| 2024-04-01 | +1.8% | +6.0% (1.8) | +7.2% (1.6) | 2% |
| 2024-07-01 | +1.9% | **+2.1% (1.1)** | +3.2% (1.3) | 12% |

Ordinary month starts jump with a standard deviation of 5.5% (±7 days) and 3.5%
(±14 days).

- **July**, the cleanest step (mid-year, no holiday), rises on the day by about the
  predicted amount. But 12–32% of ordinary month starts jump as much.
- **April** rises four times too much. It follows Easter (31 March), and the gap dips
  over the Easter weekend.
- **January** shows nothing. It is New Year's Day, a holiday, when yearly contracts
  and charges also change, so the step is not clean.

## 4. What it means

- **The 2024 steps are too small to test c.** A step must be about twice the
  month-start noise, 7–11%, to be seen. The largest 2024 step is 3.6%.
- **Nothing here rejects full pass-through**, and nothing confirms it.
- **The test is worth running on a full 7% step**: the IVPEE's return on
  2019-04-01, after the 2018 Q4 – 2019 Q1 suspension (RDL 15/2018). A 7.5% step is
  about twice the ±14-day noise. Portugal's 2019 clawback was set only on 2019-09-26
  (Despacho 8521/2019), so Portuguese costs did not change on 1 April. The suspension
  itself (October 2018) is confounded: the same decree removed the hydrocarbon tax
  on fuel for power plants. July 2021 is confounded by the clawback's own
  suspension. Portugal's two coal plants (Sines, Pego) add controls in 2019.
