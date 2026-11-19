# Hydro conduct: the four open points, settled for the descriptive chapter (2026-11-19)

**No new estimate.** Items 1 and 3 by gates computed before any run
(`docs/specs/2026-11-19-hydro-conduct-settlement-design.md`; both fail, so no run); items 2 and 4 from stored outputs
(`fixed_step_band_reading.csv`, `price_taking_simulation_hydro_*_reading.csv`, `hmoments_*` step cache).

Notation: β = share of the Nash markup X a firm adds over its water value (0 = price-taking, 1 = Nash).
"Price-takers" = ten simulated seeds with β = 0 (the estimator is biased: −0.14 to −0.26 for true price-takers without
the correction). "Gap" = actual β − seeds' mean.

## 1. Pooled hydro: not settled, and not settleable with this design

**Quote:** *"Hydro offers reject Nash conduct (β = 1) in every specification. Pooled over 2019–2025-09, β = +0.06
[−0.05, 0.15] lies inside the price-taker band (−0.00 … +0.09), so price-taking is not rejected. It is not
established either: the equivalence test that accepted price-taking for thermal (β < 0.1, fixed in advance) does not
accept it for hydro, whose conduct is bounded at 0.15 of the Nash markup. Within days (unit × day effects) the test
does accept (upper end 0.09), but there the actual estimate lies below the price-takers'."*

Why it cannot be tightened: if hydro firms were exact price-takers, the pre-fixed rule would accept with probability
0.18 today. More seeds lower this (0.13 at 20, 0.09 at 50: the rule subtracts the band's minimum); bids to 2026-05 raise
it to 0.20–0.27; a perfect bias correction to 0.46; 0.80 needs about four times the data.

## 2. Why the two hydro designs disagree

**Quote:** *"The two hydro designs read different parts of the offer. The step estimator reads the steps the price
lands on; the fixed step reads one point of each ladder (the expected running share) in every hour, including hours
where that step cannot set the price. Both put hydro far from Nash and, pooled, close to price-taking. They do not
contradict each other on the 2019–21H1 departure: the fixed step's half-year gaps in 2019H2–2020H2 are of the same
size (+0.14 to +0.42 against +0.16 to +0.30), but its price-taker band is two to three times wider, and its intervals
contain the step estimator's gap in every half-year of 2019–21H1. The fixed step's 2023 departure is Iberdrola's, sits
at reads that are rarely near the price, and in Iberdrola's buying hours is hydro moved from contracts with its own
retailer into the auction; it is not a price markup the step estimator could see."*

The evidence, from stored outputs:

| half-year | step estimator gap [bias-adjusted range] | fixed step gap [range] |
|---|---|---|
| 2019H1 | +0.24 [−0.01, 0.47] | −0.04 [−0.39, 0.30] |
| 2019H2 | +0.16 [−0.12, 0.51] | +0.14 [−0.37, 0.63] |
| 2020H1 | +0.25 [−0.01, 0.49] | +0.42 [−0.33, 1.27] |
| 2020H2 | **+0.30 [0.07, 0.52]** | +0.33 [−0.26, 0.85] |
| 2021H1 | **+0.35 [0.07, 0.66]** | +0.05 [−0.65, 0.80] |
| 2023H1 | −0.11 [−0.50, 0.32] | **+0.90 [0.01, 1.67]** |
| 2023H2 | −0.07 [−0.35, 0.21] | **+1.51 [0.54, 2.53]** |

(Bold: differs from price-takers. The fixed step's "departure" cell pools 2019–21H1 with 2024–25: +0.14 [−0.13,
0.43], which contains the step estimator's +0.29.)

1. **Precision, not sign, in 2019–21H1.** At the fixed step, the read at a share of the ladder lands on a different step
   when the firm changes the ladder's volume or step count, which moves with its stake; price-takers' estimates then
   spread up to 0.5 within a half-year (`rq-fixed-step.md`, step 2).
2. **Iberdrola's selling prices rise with its sales in both designs.** At the fixed step they load on the net position
   n (Iberdrola seller: +€6.8/MWh per GW of net sales over price-takers [3.2, 10.6], differs; 2019 alone, raw
   coefficient +7.8 [3.7, 12.0]) rather
   than on X = n / slope. With n held, Iberdrola's seller Zb slope is −0.27; that is the figure the firm table quoted,
   not a contradiction. Zb alone, Iberdrola seller 2019: gap +0.64 [−0.31, 1.47].
3. **2023 is outside the step estimator's object.** The fixed-step read sits at 1.26 × λ* in 2023 and within €10 of the
   price in 14% of hours (56–60% in 2019–20). Without Iberdrola, neither 2023 half-year differs. In Iberdrola's buyer
   hours the slope is routing: holding its bilateral share fixed takes 2023 from +2.46 to +0.68 (inside the band). The
   fixed step also finds a slope where the step cannot set the price (+0.23 over the band), which no price motive gives.
   Left unexplained: the 2023H2 seller-side cell (gap +1.82 [0.19, 3.49]), which also rests on Iberdrola.

## 3. 2024–25: does not differ, and that is final

**Quote:** *"After the gas cap (2024–2025-09), hydro β is +0.19 [0.08, 0.33] against price-takers' −0.06 … +0.09; one
seed of ten reaches the interval, so under the rule fixed in advance it does not differ from price-taking. Nor is it
shown to be price-taking (bias-allowed upper end 0.39). No half-year after the cap departs. Its size, if real, is at
most €0.17/MWh on the price."*

Final because more seeds only widen the band (cannot turn "does not differ" into "differs"), and new data cannot
decide it: the reading rule would detect a departure of this size with probability 0.10 on the eight months not yet
read (2025-10 → 2026-05), and 0.60 even reusing the 21 months already read (gate G3 fails).

## 4. The June 2021 stop

**Quote:** *"The hydro departure ends between May and June 2021 (May β +0.24 [0.13, 0.36]; June −0.08 [−0.27, 0.15]).
The change of OMIE's offer limits on 7 July 2021 cannot be the cause: the stop is visible in June, before it, and no
hydro step that set the price between January 2019 and July 2021 was at either old limit (€0 or €180.30; the highest
in May–June 2021 was €120). The time-of-use reform of 1 June 2021 changed Iberdrola's Nash markup on its selling hours
by +€0.11 against €5.1 before (test D1), so it gave no incentive reason. The end coincides with the government's
announcement on 1 June 2021 of the clawback of non-emitting plants' CO2 windfall, and with the start of the rise in gas
prices and the fall in reservoirs. No test available separates the clawback from these: all hydro units face the same
price, gas and offer rules; the units outside the Spanish clawback (EDP's Portuguese hydro) show no departure of their
own to lose (without Iberdrola, 2019–21H1 is −0.01 [−0.12, 0.10]); and β is identified only by comparing firms within
an hour, so one firm's or one country's change cannot be estimated. The timing is consistent with regulatory risk; it
is a coincidence of dates, not a test."*

Offer-limit check (descriptive, `hmoments_*`, steps setting the price in at least one draw): 0 of 253,068 hydro
steps at ≥ €180 or ≤ €0 in 2019-01 → 2021-07; the first appear in 2021-08 (1.4% of weight). The clawback-exemption
route (contract exemption as a dated shift in the stake, `docs/specs/2026-10-21-clawback-exemption-design.md`) failed
its premises on 2026-10-21.
