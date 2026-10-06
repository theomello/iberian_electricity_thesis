# The IVPEE: a test of the cost term

Framework spec §9.6 and §9.7 step 3. Run 2026-10-06.
Scripts: `analysis/ivpee_tax_test.py` (2024 steps, §1–4), `analysis/ivpee_2019_test.py`
(the full 7% steps, §5). Outputs of the first: `outputs/tables/ivpee_tax_test.csv`,
`ivpee_tax_event_study.csv`, `ivpee_tax_step_windows.csv`,
`outputs/figures/ivpee_tax_event_study.png`. Log:
`.superpowers/sdd/2026-10-06-ivpee/run.log`.

**In one line.** The full 7% steps reach the declared costs: on each of the three
days the Spanish − Portuguese gap moves the predicted way, by more than on 95–100% of
ordinary month starts; stacked, pass-through θ 1.45 (p 0.18 for θ = 1, < 0.001 for
θ = 0). The 2024 steps (1.8–3.6%) are too small to see.

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
- **The test is worth running on a full 7% step**: done in §5.

## 5. The full 7% steps: 2019-04-01, 2018-10-07, 2021-07-01

`analysis/ivpee_2019_test.py` → `outputs/tables/ivpee_2019_test.csv`,
`ivpee_2019_daily.csv`, `ivpee_2019_by_side.csv`,
`outputs/figures/ivpee_2019_event_study.png`. Log:
`.superpowers/sdd/2026-10-06-ivpee/run_2019.log`.

**Events.** The rate moves by the full 7% in one day, a predicted jump of
log(1/0.93) = 7.3% in a Spanish unit's declared cost relative to a Portuguese one's:

- **2019-04-01, back to 7%** after the 2018 Q4 – 2019 Q1 suspension (RDL 15/2018). The
  main event: Portugal's 2019 clawback was set only on 2019-09-26 (Despacho
  8521/2019), so nothing Portuguese is known to change that day.
- **2018-10-07, suspended.** RDL 15/2018 was approved on Friday 5 October, after that
  day's offers closed, and also removed the hydrocarbon tax on power-plant fuel from
  the 7th: the drop should exceed 7.3%.
- **2021-07-01, suspended** (RDL 12/2021). Portugal's clawback was suspended for the
  same months, which would shrink the gap if Portuguese units priced it in.

**Sample.** Combined cycles and coal plants with a plant-specific efficiency: gas 44
Spanish and 10 Portuguese, coal 22 and 6 (Sines and Pego, until 2021). 91,692
unit-days, 2018-01-04 → 2021-12. Same model as §2, with date × fuel effects. Benchmark:
the jump on 39 ordinary first-of-month dates from 2018-02 to 2021-06 (sd 4.0% at
±7 days, 4.2% at ±14).

| event | predicted | jump ±7 days | ±14 days | gas, ±14 | coal, ±14 | month starts as far |
|---|---|---|---|---|---|---|
| **2019-04-01** | +7.3% | **+12.9% (2.8)** | +11.9% (2.4) | +13.2% | +10.0% | 3% |
| 2018-10-07 | < −7.3% | −7.8% (1.4) | −8.3% (1.8) | −12.2% | −3.5% | 3–5% |
| 2021-07-01 | −7.3% | −11.2% (3.1) | −11.3% (2.8) | −11.8% | −9.5% | 0% |

**Pass-through** (θ = jump / 7.3%; p-values from the month starts):

| | θ | month-start sd | p, θ = 0 | p, θ = 1 |
|---|---|---|---|---|
| 2019-04-01 alone, ±7 / ±14 days | 1.78 / 1.64 | 0.55 / 0.58 | 0.03 | 0.13 / 0.26 |
| three events stacked, ±7 / ±14 | 1.46 / 1.45 | 0.31 / 0.32 | < 0.001 | 0.14 / 0.18 |

Pooled over 2018-01 → 2021-06 (the whole suspension against the months either side),
θ is 2.12 (0.28): as in 2024, the gap drifts over months, so the step days are the
measure.

**Day by day** (figure): in April 2019 the gap is flat for two weeks, steps up on
1 April and stays there. October 2018 steps down on the day and drifts further over
the next ten days. July 2021 is too noisy to read: at the start of the gas crisis
the days before swing as much.

**Which side moved.** The regression sees only the gap, so the table below gives each
country's change on the day (medians, day 0 against day −1), net of the change in its
own implied cost:

| event | Spain, coal | Spain, gas | Portugal, coal | Portugal, gas |
|---|---|---|---|---|
| 2019-04-01 (+7.3%) | **+8.0%** | +5.9% | 0.0% | −5.0% |
| 2018-10-07 (−7.3% or more) | −9.7% | −1.2% (−7.7% over ±14 days) | −12.8% | +2.8% |
| 2021-07-01 (−7.3%) | −5.2% | −4.6% | −0.6% | +1.9% |

- **The Spanish side moves the predicted way at every event and fuel**, by 5–10% on
  the day (gas in October 2018 over two weeks).
- **Coal on 1 April 2019 is the cleanest case**: Spanish coal plants raised their
  median declared cost from 56.2 to 60.8 €/MWh (+8.0% in logs, against 7.3%) with
  cost unchanged, and Portugal's did not move.
- **Two Portuguese moves on the same days are unexplained**: gas −5% (Pego, Turbogás,
  Lares) on 1 April 2019, coal −13% on 7 October 2018. They make the gap overshoot,
  which is why θ reads 1.5–1.8.

## 6. What it means for c

- **The declared costs carry a known tax**, in the right direction, at every full
  step. Zero pass-through is rejected; full pass-through is not.
- **So the declared minimum-income term behaves like a cost**: it is the cost series
  a firm's own offer condition reveals, and it moves with a cost shock it did not
  choose. The offer prices of thermal plants were not tested here (Portuguese ones
  carry no cost in 2024; Spanish ones could be, against the declared term).
- **Limits.** One country, three days, 16 Portuguese units at most. The overshoot
  comes from Portuguese moves whose cause is unknown.
