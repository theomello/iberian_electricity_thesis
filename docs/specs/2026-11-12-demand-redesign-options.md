# Demand designs after the placebo failures: what the papers offer, and what to test next

**Status: proposed 2026-11-12, nothing run.** Branch `tax-gascap-demand`. Follows `2026-11-12-tax-gascap-demand-design.md` §6–7
(gas-cap Step 2: placebo sd of the night − midday contrast is 4.1% for 352 against Portugal, minimum detectable effect 11.4%
against an implied 2.9%). Papers are in `papers/`; page-level reading is in `papers/md/`.

**In one example.** The placebo test says: pick a date when nothing happened, run the design, and see how big a "effect" appears
by chance. For 352 against Portugal's total load the chance effect is about ±4% on the contrast we care about, so a true
−3% would be invisible. That is a **noise** problem, not a bias problem. The question is which of the papers' specifications
lowers the noise, and which only describes it honestly.

## 1. What Enrich, Li, Mizrahi and Reguant did that we did not

Read from `papers/md/4-time-of-use-impacts-...md` (data section, lines ~572–800):
1. **Regulated demand, by distribution area.** Their outcome is the hourly demand of the *regulated* programming units from REE,
   for **five Spanish distribution areas**, against **Portugal's regulated** (domestic) consumption from OMIE; 142,000 hourly
   observations; observations weighted by customers, outcome per capita; standard errors clustered by area-month. We use one
   Spanish total (ESIOS 352) against **Portugal's whole-country load** (REN), which includes industry and commerce. A regulated
   household load against an all-sector load is a composition mismatch, and it is the likeliest source of our placebo noise.
2. **Their outcome is also a scheduled series** (REE programming units). So "352 is a forecast" is not a point against us
   that is not equally against the paper.
3. **A very large price change** (system charges cut 96% in September 2021, 3.0TD-style peak charge moves of €100+/MWh)
   and a sample that ends before the crisis. Ours: +29 log points on one contrast.
4. **Weekends as a within-policy placebo** and hour-by-weekend-by-area-by-month effects.

## 2. The papers' tools, matched to our two failures

| paper (file) | what it offers | fixes noise? | fixes bias? | use |
|---|---|---|---|---|
| Enrich et al. (above) | regulated-to-regulated, area panel | **yes, likely** (like-for-like control, 6 units, weights) | partly | **R1 below** |
| Arkhangelsky et al., synthetic DiD (`synth_did_feb17.pdf`); Athey et al., matrix completion (`w25132.pdf`) | weight several controls by pre-period fit; the Enrich paper itself says its LASSO step resembles this | **yes**: a combination of Portugal-regulated, Portugal-total, France and 351 tracks 352 better than one control | partly | R1 secondary |
| Rambachan & Roth (`HonestParallelTrends...pdf`) | not a pass/fail test: a confidence set that allows the post-period violation to be up to M̄ times the largest placebo deviation | **no** (honest about noise, does not remove it) | yes (turns "fails placebo" into a stated bound) | reporting, any run |
| Roth, "Pre-test with caution" (`15847.pdf`) | passing or failing a pre-trend test distorts the estimate; low-power pre-tests mislead | no | yes | argues against gating on a pass |
| Triple-difference papers (`2502.16126v3`, `2502.19620v3`, `2505.09942v3`) | a within-day contrast needs its own comparison group and covariate-conditional parallel trends; naive two-way triple differences can be biased when effects are heterogeneous | no | yes | our night − midday × treated × post is this object; use their estimators |
| Callaway, Goodman-Bacon, Sant'Anna (`w32117.pdf`) | DiD with a continuous dose | no | yes | the cross-tariff dose-response of the main thread, not this one |
| Belloni, Chernozhukov, Hansen (`belloni-et-al-2014...pdf`) | post-double-selection LASSO: selected controls with valid inference on the treatment coefficient | modest | modest | alternative to the prediction-error step |
| MacKinnon et al. (`J of Applied Econometrics 2023...pdf`) | wild bootstrap with few clusters | no | inference | six areas is few; placebo (randomisation) inference is the safer default |
| Bai (2009), Bai & Ng, Pesaran (`2009_Panel_data...`, `BaiNg2002`, `cesifo1_wp1331`); 2026 IFE papers (`2605.0061x`) | interactive fixed effects | no | factors common to units | needs many units; six is too few (and the gas-cap supply thread's IFE check already failed) |
| Fabra et al. (2021, `Fabra et al ... real-time pricing.pdf`), Ito (`w18533.pdf`), Jessoe & Rapson (`w18344.pdf`) | Spanish household elasticity ≈ 0; marginal-vs-average price; information | no | context | the prior: an elasticity near 0 to −0.1 needs a very large price move to detect |

**Reading.** Nothing in the folder removes noise by specification alone except better units and better controls (rows 1–2).
Sensitivity analysis (Rambachan–Roth) is the right way to report what the data cannot rule out.

## 3. Proposed design R1: regulated-to-regulated area panel (recommended next test)

- **Treated:** Spain's regulated demand by area: the PBF schedules of the five reference-supplier units (Endesa Energía XXI,
  Iberdrola Curenergía, Naturgy's and EDP's last-resort units, Viesgo's), from the `pdbf` parquet and
  `lib/omie_owner.is_pass_through`; their sum should reproduce ESIOS 352 (0.97–1.00 of volume, `CLAUDE.md`).
- **Control:** Portugal's regulated supplier (SU Eletricidade) purchases in OMIE, hourly (the paper's own Portuguese series is
  OMIE's); extra controls for the synthetic-weight version: Portugal's total load (REN), France (`eco2mix`), ESIOS 351.
- **Events to run it on:** the gas-cap net price step (2022-06-15, night − midday contrast) only after R0 passes; and the
  candidates in §4.
- **Estimators:** (i) the paper's per-area-hour LASSO prediction errors then DiD; (ii) the plain DiD with hour × weekday × area ×
  month effects; (iii) synthetic weights over the controls; (iv) Rambachan–Roth confidence sets on every reported effect.
- **R0, the only thing asked now: a power gate with the event sealed**, like Step 2: build the area series, check their sum
  against 352, then run the same 26 placebo breaks and report the placebo sd and MDE of the night − midday contrast for
  (a) the five-area panel against SU Eletricidade, (b) the same with synthetic weights.
  - **Proceed** to an event run if MDE ≤ 1.45% (detects −0.10 on the 29-point contrast) or ≤ 14.5% (bound only), as before.
  - **Stop R1** if the placebo sd is not below 3% (the whole-Spain-versus-Portugal figure was 4.1%): the control is not the problem.
  - The honest expectation: the noise falls but probably not by the factor of four needed to detect −0.10.

## 4. Other natural experiments for the DiD + LASSO method (candidates; each needs its own price gate and power gate first)

1. **The PVPC forward-price phase-in, 2024-01-01 / 2025-01-01 / 2026-01-01.** RD 446/2023 (BOE-A-2023-14048) puts a weight of 25%
   on forward products in 2024, rising by 15 points a year (the preamble's path; 40% in 2025 is by that rule, not read in the text)
   to 55% in 2026, so the spot weight falls 75% → 60% → 45%. That **flattens the hourly shape of the regulated price**: the
   evening-minus-midday gap shrinks by about a fifth, then a quarter. It is a price change on a fixed, legislated, calendar date,
   unrelated to Spanish demand, it leaves Portugal's flat regulated price untouched, and a tax change cannot confound the within-day
   contrast because VAT scales every hour alike. **Weak points:** small relative price changes; 1 January also carries tax and
   charge updates; the spot share varies by year. Data on disk: ESIOS 1001 to 2026-04, 352 to 2026-11. This is the best candidate.
2. **Gas cap end, 2023-02-26 (the charge falls to zero)** and the end of the cap, 2023-12-31: already in the gas-cap spec as the
   symmetry check; weak (winter to spring).
3. **Not Spanish, listed to be complete:** France's Tempo red days; not pursued (the thesis is Spanish).
4. **Not found:** any other Spanish retail step that changes the hourly shape. The June 2021 reform and the September 2021 charge
   cut are the main thread. A scan of CNMC and ERSE tariff histories for a Portuguese regulated-price change inside any window would
   be worth a day; Portugal's tariff is set annually, so I expect none mid-year.

## 5. Verdict on the question asked

- **Specification:** the literature supports moving to like-for-like regulated units (R1) and reporting with Rambachan–Roth
  sets; it does not supply a specification that detects a small effect with a noisy control.
- **Policy change:** the gas cap stays alive only through R1; the PVPC forward phase-in is the one new event worth a price gate.
- **Fallback, if R0 stops:** state the elasticity as a bound (Fabra's near-zero prior plus our hourly-design ceiling of −0.1 to
  −0.15) and rest the demand side of the thesis on the time-of-use replication.

## 6. R0 results (2026-11-12, user's go-ahead; `scripts/analysis/gascap_demand_r0.py` → `outputs/tables/gascap_demand_r0*.csv`; real window not computed)

Four reference-supplier areas (Endesa XXI `EE21C01`, Iberdrola Curenergía `IBCUC01`, Naturgy `GNSUC01`, EDP `HCURC01`; two units under 1.5% of volume left out)
from OMIE PDBF, summed over roles; their sum is 0.98–0.99 of ESIOS 352. Control: SU Eletricidade's purchases (`EDPUC2`, mean
about 380 MW). 26 placebo breaks, 28 days pre and 14 post, DST days dropped; night − midday contrast.

| variant | placebo sd | MDE (2.8 sd) | P1 (≤ 1.45%) | P2 (≤ 14.5%) |
|---|---|---|---|---|
| four areas summed vs SU Eletricidade | 3.6% | 10.0% | fail | pass |
| ESIOS 352 vs SU Eletricidade | 3.6% | 10.0% | fail | pass |
| four areas pooled, area-by-area contrasts averaged | 4.0% | 11.1% | fail | pass |
| synthetic weights (SU 0.42, Portuguese total 0.01, 351 0.04) | 3.5% | 9.7% | fail | pass |
| reference: four areas vs Portuguese total (Step 2's control) | 3.9% | 10.8% | fail | pass |

**Stop rule (placebo sd below 3%): not met, R1 stops.** The regulated-to-regulated control cuts the noise only from 4.1% to
3.6%, and weights fitted on the window's own pre-period do not help further. The noise is in Spanish regulated load's within-day shape
over a six-week window, not in the control's composition. The sum of the four areas reproduces 352 (ratio 0.985), so the
series choice does not matter either. Under P2 the real date could still be run as a bound (MDE 10%), which would say only that
the elasticity is above about −0.35.

## 7. PVPC forward phase-in: price gate, rules set before the run (2026-11-12, user's go-ahead)

**In one example.** If the regulated price followed the day-ahead price fully, a €60 gap between the evening and midday day-ahead price would be
a €60 gap in the PVPC energy term (slope 1.0). With a 25% forward weight the forward part is the same in every hour, so the PVPC gap is €45 (slope 0.75).
The step is therefore a change in the **slope of the PVPC within-day gap on the day-ahead within-day gap**, which is also free of season.

**Measure.** For each day, E − M = mean of the 19–22 local hours minus mean of the 11–14 local hours, for ESIOS 1001 and for the OMIE
day-ahead price (hourly mean). Slope = regression of the 1001 gap on the OMIE gap, over the 60 days before (b0) and the 60 days after (b1) a
break; step effect Δ = b1 − b0. Expected: 2024-01-01 −0.25 (1.00 → 0.75), 2025-01-01 −0.15, 2026-01-01 −0.15 (RD 446/2023, BOE-A-2023-14048;
the 2025 value 40% is by the 15-point rule). Placebo breaks: the 1st and 15th of March to November in 2023, 2024 and 2025 (weights constant inside a year), same 60/60 windows.
**Rules (price gate only; no demand series):**
- **F1** pre-slope before the first step (2023-11-01 → 12-31) in 0.85–1.15; otherwise 1001 is not fully spot-indexed and the expected steps are wrong, stop.
- **F2** each step's |Δ| ≥ 0.10 and above the 95th percentile of the placebo |Δ|.
- **F3** each step's Δ within 0.5–1.5 times its expected value, with the expected sign.
A step that fails F2 or F3 is dropped. If no step passes, kill; if some pass, the next step is a power gate on placebo breaks as in Step 2, run only on the passing steps.
