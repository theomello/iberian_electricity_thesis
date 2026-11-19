# T3: did the reform change the price signal, and does the price change feed back into demand? (pre-registration, proposed)

**Status: proposed 2026-11-19, not registered. Binding when the user confirms and this file is committed; the script
is committed after that and the run follows.** Framework: `notes/thesis-demand-supply-link.md` §2 (equations D and E).
Inputs, all done: the price effect (`2026-11-13-tou-price-effect-design.md`, R1–R4 pass), T1
(`2026-11-19-short-notice-share-design.md`, all rules pass), T2's hour file
(`outputs/tables/tou_reform_market_power_hours.csv`).

**In one example.** At 03:00 on a June 2021 weekday the reform raised the price by about €2/MWh. Two questions.
(a) Is the hourly price still the same signal? Before the reform, 1 GW less wind at 03:00 raised the price by, say,
€4; if after it the same gigawatt raises it by €4.1, the signal consumers and storage owners see is unchanged.
(b) Does the €2 come back as demand? A household on the regulated hourly tariff (PVPC, precio voluntario para el
pequeño consumidor) pays it; if it cuts night load in response, the reform's load shift is partly undone, and the
measured shift is not the whole story. With the elasticities we have, that response is (b) = σ·λ·θ·(€2 / price) of
night load. We compute it at its largest plausible size and compare it with the shift itself.

## Part (a): the price signal

**(a1) Shape, descriptive, no rule.** Both numbers are already known (the reform's contrast and the observed price),
so a rule would test nothing. Reported: the reform's effect on the evening (18–21) minus night (0–7) price,
−2.39 (range −1.69 to −2.39 over the three levels), against
- the observed evening-minus-night spread on the window's 1,761 valid weekday hours, 2021-06-01 → 2021-09-14;
- the same spread on the same calendar weekdays of 2019 and 2020, and in the nine 106-day placebo windows of the
  price-effect test (2019-01 → 2019-09): its range across years and windows.
Statement form: "the reform moved the evening-minus-night spread by x% of its level, against a year-to-year range
of y".

**(a2) Sensitivity to a surprise (rule P1).** The price moves with a day-ahead surprise (wind, outages) by
κ_h = 1 / slope of the market's net curve at the clearing price, in €/MWh per GW. With the band of T2,
slope_h = band_h / (2h), h = €5/MWh, band_h = all offers (buy and sell, status O) within ±h of the price, so

  κ_h = 1,000 × 2h / band_h,   Δκ_h = κ_h(at p*_h) − κ_h(at p*_h − Δp_h)

with Δp_h the price-effect test's neutral-level point effect, exactly as in T2 (`band_p_star`, `band_pcf_neutral`,
one row per hour after removing the firm duplication). Arithmetic on an existing output; no curve is re-read.

## Part (b): feedback

The price change re-enters demand through equation D. For group i and block k (evening 18–21, night 0–7):

  feedback MW_ik = |σ_i| · λ_i · θ_i · (|Δp_k| / r̄_ik) · L_ik

summed over households (E0) and large industry (6.2–6.4), compared with the reform's load shift |ΔQ_k| (MW, E0,
neutral level; `dq_neutral` of T2's hour file), block means over the window's valid weekday hours.

| Input | Worst case (rule B1) | Point (reported) | Source |
|---|---|---|---|
| σ, households | 0.12 | 0.09 (midpoint) | reform, six placebo summers (−0.06 to −0.12) |
| λ, households | 1 (not identified) | 1 | no same-hour instrument for E0 |
| θ, households | 0.30 | 0.25 | PVPC share of E0, ESIOS 352 / E0, summer 0.23–0.25, winter up to 0.30 |
| σ, industry | 0.544 | 0.177 | period price, six summers, interval end |
| λ, industry | 0.71 | 0.01 | T1 (θ = 0.32 bound) |
| θ, industry | 0.49 | 0.32 | CNMC IS/DE/031/24 |
| r̄ | wholesale price p alone | p + tolls + charges (industry: T1's s = 0.851) | the lower r̄, the larger the feedback |
| L | E0 load; 6.2–6.4 load | same | ESIOS 1201; 1216–1218 |

Using r̄ = p for both groups overstates the feedback (households pay roughly twice the wholesale price), so the
worst case is an upper bound on every input at once.

## Rules (set before the run)
- **P1 Signal unchanged:** |mean Δκ| ≤ **10% of mean κ** over the window, overall and in the evening and night blocks
  separately. (Relative to the level, not to the window's sd: T2 showed an sd-based bar is strict for hour-varying
  quantities; this choice is made before any κ is computed.)
- **B1 No feedback:** at the worst-case inputs, feedback MW ≤ **10% of |ΔQ_k|** in the evening and in the night
  block. If |ΔQ_k| in a block is below 50 MW the block is reported, not judged (a ratio to near zero says nothing).
- **B2 Second round:** the implied multiplier 1 / (1 − feedback share) is reported; no rule beyond B1.

## What each outcome means
- **P1 passes:** the reform shifted the price level by hour but left the price's response to a surprise unchanged
  within 10%; the hourly signal is the same signal. **P1 fails:** the reform changed how strongly the price reacts to
  surprises in that block, by the reported amount; the thesis says so.
- **B1 passes:** even with every input at its least favourable end, the price change undoes at most a tenth of the
  load shift; the measured shift is the equilibrium one and the re-cleared price effect needs no second round.
  **B1 fails:** the bound is not tight enough to rule out a feedback of that size; the point-input feedback is
  reported as the central value and the thesis does not claim "no feedback".
- No other bar, block, level or input is tried after a failure.

## Reported, no rule
- (a2) and (b) at the REN (F) and regulated-unit (M) levels.
- (a2) by hour of the day.
- (b) at the point inputs, and split into households and industry.

## Threats
- κ from a ±€5 band is noisy hour by hour; the rule uses window means.
- Offers are held fixed, as in the price effect and T2.
- Households' λ is not identified; λ = 1 is the bound, not an estimate. PVPC customers see tomorrow's price only
  one day ahead, so their real response is the short-notice one and λ = 1 overstates it.
- σ for households is a within-day period response; applying it to an hourly price change assumes the same
  substitution across hours.
- Industrial load 6.2–6.4 is a tariff series, not the industry; other industrial tariffs are left out of L. Their
  exposure is at most that of 6.2–6.4, and the households' worst case dominates in any case.

## Outputs
`scripts/analysis/tou_price_signal_feedback.py`; `outputs/tables/tou_price_signal_feedback{,_checks}.csv`. Reads
the price-effect and T2 hour files, OMIE prices and the ESIOS load series; writes nothing else.
