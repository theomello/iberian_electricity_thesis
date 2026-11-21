# Validity tests with the industrial load shift added (proposal)

**Status: proposed 2026-11-21, not registered. Binding when the user confirms and this file is committed; the first
run follows that commit. Nothing below has been computed.** It reruns three registered tests with a larger input; it
does not re-judge their first results, which stand as registered and are reported beside the new ones.

## Why
The price effect (`2026-11-13-tou-price-effect-design.md`, R1–R4 pass), T2 (`2026-11-19-reform-market-power-design.md`,
M2 and D1 pass, M1 fails for three firms) and T3 (`2026-11-19-price-signal-feedback-design.md`, P1 and B1 pass) all
re-clear the day-ahead market with **only E0's load shift** put back (households and small business, below 1 kV). When
they were registered, industry had no detected response. Since 2026-11-18 it has one: large plants moved load out of the
hours that became dearer periods (`2026-11-18-industry-regulated-price-elasticity-design.md`, reduced form −1.0 point
of the daily mean per one-step dearer period, p 0.0001). The thesis's validity section says the supply side did not
react to the reform's demand shift; that statement must hold for the whole shift, not for part of it.

## In one example
At 20h on a July weekday in 2021, E0's shift removed about 5% of its load. Tariff 6.4 moved 20h from period 2 to
period 1, one step dearer, so the reduced form removes about 1% of 6.4's daily mean load from that hour as well, and
adds it back in hours that became cheaper (14–17h in July; the night in August). The counterfactual market then has
both amounts put back, and the price effect, the firms' incentive change and the feedback are recomputed with it.

## The industrial shift (fixed before the run)
For tariff series k ∈ {6.2, 6.3, 6.4} (ESIOS 1216–1218), weekday non-holiday hour h of day d in the window:

  **ΔQ^ind_kh = −b · r̃_kdh · L̄_kd**, in MW (load removed by the reform; negative where load was added)

- **b = −0.0100**, the pooled E6 reduced-form slope (share of the daily mean per one-step dearer period), as computed
  by `tou_industry_regulated_price.py`; not re-estimated.
- **r_kdh = old_period − new_period** of that tariff, date and hour from `tou_tariff_schedule.schedule` (positive =
  dearer); **r̃** is r recentred within the day (minus its daily mean), so the shift is **energy-neutral by day**, the
  same rule as E0's main ("neutral") level. Without the recentring the shift would add or remove energy by
  construction, which the reduced form does not identify.
- **L̄_kd** = the day's mean hourly load of series k (actual).
- The counterfactual adds ΔQ^ind to E0's `dq_neutral` hour by hour: **ΔQ_h = ΔQ^E0_h + Σ_k ΔQ^ind_kh**.

**Sensitivities (reported, the rules are applied to each):**
- **S-cell:** instead of b · r̃, the observed 2021 cell deviation (2021 hour share minus the mean of 2014–19, by tariff,
  month, hour; recentred by day), so the shift is not forced to be linear in the period step.
- **S-wide:** the same b · r̃ pattern (6.4's calendar) applied to the whole high-voltage load E1–E6 (ESIOS 1202–1207,
  fixed loader, absent E5 = 0) instead of 6.2–6.4. An upper bound on the MW: E1–E6 includes 6.1TD, whose period
  calendar changed the same way, but also E1+E2's pre-reform 2021 deviation, which this pattern does not carry.

## Sample and pipeline (unchanged)
Weekdays that are not holidays, 2021-06-01 → 2021-09-14, the 1,761 valid hours of the price-effect test; effective
curves from `outputs/cache/step`; E0's three levels (neutral, F, M) as before, with the industrial shift added at its
own neutral level in all three. Firms, bands, conduct scales, worst-case inputs and the 10% bars of T2 and T3 as
registered. The industrial inputs of T3 (σ, λ, θ) are unchanged; only |ΔQ_k| (the denominator) and the price change
Δp (the numerator's driver) change.

**Placebo for R3:** in each of the nine 2019 windows the industrial shift is b_2019 · r̃ laid on the 2019 calendar,
with b_2019 the reduced-form slope of 2019 computed against the other placebo summers (the E6 placebo value already
produced by the same script), added to E0's placebo shift as before.

## Rules (the registered ones, applied to the combined shift)
- **R1–R4** as in the price-effect design (curve valid ≥ 70%; contrast negative, interval excludes zero, magnitude
  €0.50–20; real contrast in the top 2 of 10 windows and ≥ 1.5 placebo sd; sign stable under the three levels, without
  July and without the first week of June).
- **G0, G1, M1, M2, D1** as in T2.
- **P1, B1** as in T3 (B1 against the combined |ΔQ_k|; blocks under 50 MW reported, not judged).
- **V0 Size gate (new, before any rule):** report the mean |ΔQ^ind| / mean |ΔQ^E0| in the evening and night blocks.
  This is informational; no rule depends on it.

## What each outcome means
- **Every rule keeps its first verdict:** the validity section's statements hold for the whole shift. The thesis
  quotes the combined numbers (price contrast, ΔX, feedback share), with the E0-only ones in a footnote.
- **A rule that passed now fails:** that statement is withdrawn from the validity section and replaced by what the
  combined run shows. No other window, slope, level or bar is tried after a failure.
- **M1, which failed, now passes or fails:** reported; it was already stated as "shifted the incentive between hours by
  under €1, nets to about zero", and that wording is updated with the combined figures.
- **Sensitivities disagree with the main run:** reported as such; the main run decides.

## What is known before the run (not blind)
The first results of all three tests, and the reduced-form slope b. Not known: the size of the industrial shift in MW
relative to E0's, and every combined number.

## Threats
- The reduced form is linear in the period step; S-cell relaxes it.
- Recentring by day assumes industry neither consumed less nor more energy because of the reform; the reform's price
  level effect on industry is not identified (the wholesale same-hour response is zero; T1).
- 6.2–6.4 is a tariff series, not all industry; S-wide bounds the rest.
- Weekends are out, as in the first runs, although 6.3 and 6.4 also moved at weekends.

## Outputs and code
New script `scripts/analysis/tou_validity_industrial.py`, committed before the run; it imports the three existing
scripts' functions and passes the combined ΔQ, changing none of them. Outputs
`outputs/tables/tou_validity_industrial{,_hours,_checks}.csv`. Results go in a section below, with each rule's first
and combined verdict side by side.

## Results

### Run 1 (2026-11-21, commit 8f76467): not valid, stale prediction-error cache
The run completed (`outputs/tables/tou_validity_industrial*.csv`), but its E0 baseline does not reproduce the
registered price effect: with the industrial shift set to zero it gives evening −0.55, night +1.52, contrast **−2.07**
against the registered −0.65, +1.74, **−2.39**, and E0's period-type effects come out −4.40 / −3.13 / +1.41 instead of
−5.28 / −3.64 / +1.43.

**Cause.** `tou_price_effect.get_errors` reads `data/cache_tou/price_effect_e0_errors.parquet` (written 2026-11-13,
32,463 rows, a RangeIndex) and attaches it by index label to the panel `D.prep(T.build("e0", …))`. Since the data
extension of 2026-11-18 (commit 54be556: holidays, temperature and REN back to 2014) that panel has **32,487 rows**:
the first day, 2017-12-31, is now present (23 hours), plus one more row. Every error is therefore attached to a row
about one day away from its own. Nothing checks the length, so the run gives no error. The 2026-11-13 price effect was
run before the extension and is not affected.

**What else this touches.** Every script that reads this cache and ran after 2026-11-18: T2
(`2026-11-19-reform-market-power-design.md`; its `dp` mean evening −0.553, night +1.515 is the misaligned baseline) and
T3 (`2026-11-19-price-signal-feedback-design.md`, which takes `dp` and `dq_neutral` from T2's hour file). Their results
rest on misaligned E0 effects and need a rerun once the cache is rebuilt. Scripts that read the cache but ran before
2026-11-18 (levy, forest, pooled placebo, industry-adjusted, dose search, cross-tariff, area panel) are unaffected as
run; any rerun of them would be.

**What run 1 still shows (descriptive, not a result):** on the same (misaligned) baseline, adding the industrial shift
changes the contrast by −0.22 (main), −0.25 (S-cell), −0.56 (S-wide) €/MWh; the industrial shift is 23% (evening) and
14% (night) of E0's in MW (main), 31–54% in the sensitivities; every rule keeps the verdict it had in the first T2/T3
runs (M1 fails for Endesa, Naturgy and EDP; all else passes; S-wide adds a narrow M1 failure for Iberdrola).

**Not done, waiting for the user:** rebuilding the cache (`--refit`, the registered LASSO, unchanged), a guard that
stops any run when the cache and the panel differ in length or dates, then rerunning this design, and T2 and T3 as
registered.

### Fix and rerun (2026-11-21, approved by the user: "Yes, rebuild and rerun")
`get_errors` now stores each row's date and hour in the cache and stops the run if the cache does not match the panel
row for row. The stale cache is kept as `price_effect_e0_errors.stale-2026-11-13.parquet`; the new one is the same
registered LASSO refitted on the current panel. **Check:** E0 period-type effects −5.23 / −3.62 / +1.46 (registered
−5.28 / −3.64 / +1.43; the difference is the added day of data), E0-only contrast **−2.39** (registered −2.39). T2 and
T3 were then rerun as registered (their errata are in their own files), and this design after them.

### Run 2 results (the valid run)
**V0 size.** The industrial shift (main) is 19% of E0's in the evening (52 MW against 289 MW removed) and 12% at night
(20 MW against 374 MW added); 45% and 28% in S-cell and S-wide.

| | E0 only (rerun) | main (E0 + 6.2–6.4) | S-cell | S-wide (E0 + E1–E6) |
|---|---|---|---|---|
| price contrast, evening − night (€/MWh) | −2.39 | **−2.62** [−2.84, −2.41] | −2.61 | −2.93 |
| evening / night | −0.65 / +1.74 | −0.78 / +1.84 | −0.92 / +1.69 | −0.93 / +2.01 |
| R1–R4 | pass | **pass** (rank 1 of 10; placebo sd 0.14; R4 −1.86 … −2.70) | pass | pass |
| M2 (all five firms, |ΔX| at Nash < €0.50) | pass (max 0.17) | **pass** (max 0.22, EDP) | pass | pass |
| M1 | fails Iberdrola, Endesa, Naturgy, EDP | **fails the same four** | same | same |
| D1 (Iberdrola June / June–Aug; EDP) | pass (+0.13 / +0.02; bar 0.51) | **pass** (+0.04 / −0.01) | pass | pass |
| T3 P1 (all / evening / night) | 2.1% / 0.0% / 5.8% | **2.7% / 0.6% / 7.3%** | pass | pass |
| T3 B1 worst case (evening / night) | 3.5% / 7.4% | **3.6% / 7.3%** | 3.5% / 7.2% | 3.5% / 7.3% |

**Verdict, as registered: every rule keeps its verdict.** Adding industry's shift makes the reform's evening-minus-
night price effect about a tenth larger (−2.62 against −2.39; −2.93 at the S-wide upper bound) and changes nothing
else that is judged: market power unchanged on average (M2), the hydro stop not explained by the reform (D1), the price
signal unchanged (P1), feedback under a tenth (B1). M1 fails for four firms with and without industry; the incentive
moves between hours (night up by €0.5–1.2, evening down by €0.1–0.4 at Nash) and nets to about zero.

**Change against the first T2 run (from the cache fix, not from industry):** Iberdrola's M1 now fails (night +0.50
against a bar of 0.44; it passed narrowly at +0.42 on the misaligned baseline). The thesis wording ("shifted the
market-power incentive between hours by under a euro, nets to about zero over the day") is unchanged; the list of firms
is four, not three.

**Quotable for the validity section:** price contrast −2.39 (households) and −2.62 (households and large industry),
range −1.9 to −2.9 across levels and sensitivities.
