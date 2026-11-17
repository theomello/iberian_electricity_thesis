# Second settlement: the bid-curve instrument with its own controls (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been estimated.** Follows `2026-11-17-industry-iv-instrument-settlement-design.md` (first settlement, run 2026-11-17; scores in `outputs/tables/industry_iv_instrument_settlement*.csv`).

**What the first settlement left open.** Its common-controls amendment removed realised wind and solar from the predictors so that C1 (realised wind speed) would not be absorbed. The bid-curve instrument is the forecast miss turned into a price effect on the day's offer curve, and its original pipeline (`industry_iv_bid_curve.py`, first stage F 19.7) conditioned on realised wind and solar. Without them it scored F about 2. C2 and C3 stay recorded as failed under the first settlement's rules; this registration scores the bid-curve instrument as it was designed, plus two named variants, and does not change that record.

**In one example.** On a Tuesday the wind forecast overshoots realised wind by 2 GW. The instrument is "how many euros per MWh would the day's own offer curve move for a 2 GW miss": large when the curve is steep at that hour, small when flat. It is only a shock to the price if we hold fixed how windy the hour actually was; that is what the controls do.

## Candidates (closed list; no others will be added)
Same rows, week-on-week differences, double ML (10 time blocks, 14 days purged) and common-sample rows as the first settlement (19,388 weekday hours, 2019-2023).
- **C1**: re-scored here under the first settlement's predictors (no realised wind), because the first settlement's placebo (S2) was invalid (see its Results section: the placebo outcome sat among its own predictors). F1 and F3 are recomputed and should reproduce the earlier values.
- **B0** the original bid-curve instruments d_dpw and d_dps (wind and PV forecast-miss price effects), no hour weights, predictors = the first-settlement set **plus** the original bid-curve controls: d and level of realised wind and solar (d_wr, d_sr, wr, sr), their daily means, the offer-curve slope and the first-quantity price a0 with their daily means.
- **B1** B0 instruments each divided by their hour-of-day sd in 2019; same predictors as B0.
- **B2** B0 instruments plus B0 instruments x the one-week-lagged offer-curve slope (standardised), same predictors as B0.

## Scores and rules (same as the first settlement; thresholds not changed)
- **S1** F at least 20 in the full sample and at least 10 in each of 2019-21H1 and 2021H2-23 (date-clustered).
- **S2** placebo outcome (ln load 7 days earlier): permutation p above 0.10 in all three blocks (1,000 permutations across days within year-month, seed 20261117).
- **S3** zero-first-stage on the wind component (d_dpw for B0, B1 its weighted form, B2 the d_dpw column): rows with national mean wind speed below 5 m/s in both weeks, at least 800 rows; permutation p above 0.05 **and** idle/full coefficient ratio at most 0.5 in absolute value.
- **S4 Use.** C1 passed the first settlement (min F 71) and is the primary instrument for the industrial elasticity whatever happens here. Every B candidate passing S1-S3 becomes a **second instrument for a robustness estimate** (best minimum F first, ties to B0). If none passes, the bid curve is closed as an instrument and only its stated-curve use (row 12 of `docs/business-demand-evidence.md`) remains.
- **J Joint first stage (only if C1 and at least one B pass).** First stage of the price on C1's instruments plus the best B's, first stage only: the incremental F of B over C1 (and of C1 over B), date-clustered. *Incremental F of B over C1 at least 10:* the offer-curve instrument carries price variation C1 does not, so using both is worth a separate registration. *Below 10:* B repeats what C1 already identifies and is reported as agreement only.
- **S5 Stop.** No further candidate after this list. If B0 fails S1 even with its controls, the earlier F 19.7 was specific to the original sample rows (the common sample drops 2,248 rows) and that is recorded, not rescued.

## Not done here
No elasticity on the real outcome is computed or stored. The C1 elasticity (and any B robustness estimate) needs its own registration and go-ahead.

## Data and code
Script `scripts/analysis/industry_iv_second_settlement.py` (to be written and committed before it is run); reuses the first settlement's frame builder and `industry_iv_estimation.py` helpers. Output `outputs/tables/industry_iv_second_settlement{,_rules,_f3}.csv`.

## Pre-run amendments (2026-11-17, after the placebo flaw, before this run)
1. **Placebo residualised without its own lag.** For every candidate the placebo outcome d ln load(t-7d) is residualised with the predictor set **excluding** d ln load at lag 7 (as in `industry_iv_noise_reducers.py`).
2. **Two predictor sets.** C1 uses the first settlement's set (no realised wind, so that it is not absorbed). B0-B2 use that set plus the realised-wind and offer-curve controls. Each candidate's price and instruments are residualised with its own set.
3. **J is computed in each candidate's home set.** (a) Under C1's set: incremental F of B's instruments (raw, no realised-wind control) over C1's. (b) Under B's set: incremental F of C1's instruments over B's (C1 is mostly absorbed by realised wind there). B adds to C1 only if (a) is at least 10; (b) is reported as context. Because B only has power after conditioning on realised wind, which C1 is close to collinear with, the two are likely substitutes; J says whether that is so.
