# The Iberian gas cap as a conduct experiment, with Italy as control — design

2026-10-28. Status: **draft for the user's approval**. Nothing is estimated yet.

## 1. Intent

Ask whether Iberian gas plants bid at cost, using a cost change set by decree rather than one
the firms chose. From 2022-06-15 the Iberian exception (RDL 10/2022) paid each eligible plant
a subsidy for every MWh it produced from energy offered in the day-ahead market. A plant that
bids at cost passes the whole subsidy into its offer: its offer falls by exactly the subsidy.
A plant with market power passes through a different share. Italy had no cap, so Italian gas
plants show what offers would have done without it.

The question is **firm conduct**, which the published evaluations of the cap do not address
(§3). It is the same question as the step estimator's β (`notes/rq-step-estimator.md`), now
with a natural experiment behind it.

A worked example. On a day with MIBGAS at €164 and the reference price at €40, the subsidy is
(164 − 40) / 0.55 = €225 per MWh. Suppose a combined cycle's own cost that day is €330. Bidding
at cost, it offers at €105 under the cap. If instead its offers fall by only €150 relative to
Italian plants on the same day, it keeps €75 of the subsidy as a higher markup.

## 2. Goals, non-goals, anti-goals

**Goals**
1. The pass-through ρ of the subsidy into Iberian gas plants' offers, measured against Italian
   gas plants (difference in differences). ρ = 1 is bidding at cost.
2. ρ by firm, for the five large Iberian owners (Naturgy, Iberdrola, Endesa, Engie, EDP), and by
   whether the firm is a net seller or buyer that day (X, `analysis/firm_x.py`).
3. Later, and only after 1–2: a re-clearing of the auction without the cap that reproduces the
   price drop the synthetic-control papers measure (about 40%), as a check on the model, and
   the competitive-price benchmark on the same machinery (the 2026-10-28 conversation).

**Non-goals**
- The cap's effect on the price. Already estimated (§3); used here only as a check in goal 3.
- Welfare, consumer savings, the compensation charge. Possible later, not in this design.

**Anti-goals** (would make it a failure even if it runs)
- A ρ that rests on Iberia and Italy drifting apart for reasons other than the cap: the
  pre-period check (§6, step 1) decides whether there is a design at all.
- Re-doing Lou et al. or Haro Ruiz et al. under another name.

## 2b. Earlier work in this repo, and what this design adds

`notes/rq-gas-cap-conduct.md` (2026-08-14/21) proposed the same pass-through test **within Iberia, with
no control group**, on the premise that the statute gives the counterfactual. Its script,
`analysis/gas_cap_passthrough.py` (9481fc2), found the rate **not identified**: the subsidy is common to
every unit on a day, so date or month effects absorb it, and β came out −0.07 (se 1.45). The commit
concluded that identification "needs the capped-versus-uncapped contrast instead". Italy is that
contrast. The note's descriptive fact stands (CCGT offers 2.4–2.7× MIBGAS before, 0.66× in August
2022), and its later sections (Hortaçsu–Puller ex-post optimal bid; the 2022 drought as a control, not an
instrument) remain the follow-ups. Its description of the mechanism as a capped gas price is wrong; see
`docs/gas-cap-sources.md` §2.

All facts about the mechanism, with their primary sources and checks against our files, are in
[`docs/gas-cap-sources.md`](../gas-cap-sources.md).

## 3. Prior work (read before writing any result)

| paper | method | what it leaves open |
|---|---|---|
| Haro Ruiz, Schult & Wunder, Applied Economics Letters 2024 (IWH DP 5/2024) | synthetic control of the Iberian price | price only |
| Hidalgo-Pérez, Collado, Galindo & Mateo, Energy Policy 2024 | Bayesian structural time series | price, exports |
| Lou, Pollitt, Robinson & Arcos-Vargas, Energy Economics 2026 (CWPE 2535) | re-clears OMIE's bid stack without the subsidy | treats offers as given; no conduct |
| González-de Miguel, van Wunnik & Sumper, Energies 2024 | models from OMIE bids, with and without subsidy and trade | rents, not conduct |
| Robinson, Arcos-Vargas et al. 2023 (arXiv 2309.02608); Linares & Gómez-San Román 2023 | first 100 days; review | |

Cite each where its result is used. Our additions: unit-level offers in a control country, and
the conduct reading.

## 4. Treatment, exactly

- **Subsidy per MWh**, the decree's unit adjustment, art. 3.1: Y_d = (PGN_d − PRGN_d) / 0.55
  when PGN > PRGN, else 0. PGN is MIBGAS's day-ahead price for the delivery day, PRGN the
  reference path already in `build_implied_marginal_cost.py` (40 €/MWh to 2022-12, then 45, 50,
  55, and 56.1 → 65 over 2023). 0.55 is a fixed efficiency set in the decree, **not the plant's
  own**. Confirmed in text by the Commission's approval, SA.102454 / SA.102569, C(2022) 3942,
  8 June 2022, recital (36): "Y = (P_GN – P_GNT) / 0.55 … 0.55 reflects the assumed average
  efficiency (55 %) of gas-fired power plants". (The BOE prints the formula as an image.)
- **Bids are meant to fall by Y.** Same recital: beneficiaries "are expected to submit bids …
  taking into account the amount of support they will receive". Recital (33): the aim is to
  reduce "their production costs and, correspondingly, the bids they submit". So full
  pass-through is the regulator's own premise, which ρ tests.
- **The same Y_d for every eligible plant on a day.** So the dose varies over days (from 0 to
  roughly €350/MWh), not across plants within a day. My earlier remark that the cut "varies with
  each unit's efficiency" was wrong.
- **Eligible** (art. 2.1, peninsula; EC recital (29)): gas-fired plants, coal plants, and CHP
  plants without regulated remuneration, each eligible CHP plant with its own bidding unit
  (recital (42)). "All technologies eligible under the measure will receive the same amount of
  compensation, regardless of their input fuel or production costs" (recital (39)). **Energy under physical bilateral contracts gets no
  subsidy** (art. 2.2), only energy offered to the market operator. The marginal auction MWh
  always gets it.
- **A plant's effective cost under the cap** is c_i,d − Y_d, where c_i,d is its own cost
  (`marginal_cost_bid_eur_mwh`, prices final at 12:00 on D-1). This is not the repo's
  `marginal_cost_capped_*` column, which values gas at min(PGN, PRGN) over the plant's own
  efficiency; the two differ by (PGN − PRGN)(1/eff − 1/0.55), about €13/MWh for an efficiency
  of 0.52 in August 2022. See §8 on coal.
- **Dates**: first delivery day 2022-06-15 (Orden TED/517/2022). Y_d > 0 every day to 2023-02,
  then 0 from March 2023 because MIBGAS fell below PRGN, although the decree ran to 2023-12-31.
  That switch-off is a second event: offers should move back up by Y when it stops.
- **Portugal** is treated too (the mechanism is Iberian).

## 4b. Sources on disk (`papers/`, gitignored)

`BOE_RDL_10_2022_consolidado.pdf` (the decree, consolidated), `BOE_Orden_TED_517_2022.pdf`
(start date: internalised from the auction of 2022-06-14 for delivery on the 15th),
`EC_2022_SA102454_iberian_mechanism_decision.pdf` (the approval, with the formula in text),
`CNMC_2022_nota_aclaratoria_RDL10.pdf`, `CGEP_2023_Iberian_exception_commentary.pdf`,
`OIES_2023_EL50_Iberian_exception.pdf`, `HaroRuiz_Schult_Wunder_2024_IWH_DP.pdf`,
`Robinson_ArcosVargas_et_al_2023_arXiv_2309.02608.pdf`, and already there before this design
Lou et al. 2026 (Energy Economics) and González-de Miguel et al. 2024 (`energies-17-03102.pdf`).
Not obtained: Hidalgo-Pérez et al. (EsadeEcPol refused the download; Energy Policy is paywalled).

## 5. Data (all on disk, 5d28a8e)

- **Iberian offers**: OMIE `curva_pbc_uof`, status `O`, sell side, gas units with a cost:
  56 units, 25 GW, 12 owning firms (`lib/unit_ownership.py` for owners by date).
- **Italian offers**: GME public offers, 2021-06-01 → 2023-06-30, ACC/REJ/PREJ rows: 88 gas units
  of 100 MW or more, 36 GW, 15 operators, 73 with a plant-specific efficiency.
- **Costs**: Iberia from `implied_marginal_cost_daily.parquet` (`_bid` columns). Italy to be
  built the same way (§6, step 0): JRC efficiency × PSV (`gme_mgp_gas_daily.parquet`, sessions up
  to D-2) plus the same EUA price and emission factor.
- **Window**: 2021-06-15 → 2023-06-30: a year before, the binding period, and four months after
  the switch-off.

## 6. Steps, each with a stop rule

**Step 0 — the Italian cost and the outcome.** Build the Italian unit-day cost. Outcome: each
unit's offer price at fixed shares of its capacity (as `analysis/capacity_quantile_offer.py`),
the main one being the price of its last offered MW, minus own cost: the markup m_i,h. Report how
often a unit offers nothing, and the minimum-income condition separately (Iberian combined cycles
declare one in `cab`; it changes form on 2025-03-19, outside the window).
*Stop if* fewer than about 40 Italian units have a cost on most days.

**Step 1 — do the two groups move together before the cap?** Monthly mean markup, Iberia and
Italy, 2021-06 → 2022-06, and the difference. Placebo cap dates in the pre-period (2021-10,
2022-01, 2022-03).
*Stop if* the pre-period difference trends, or placebo dates give effects as large as a fifth of
the mean Y in the binding period. Then there is no control group, and that is the finding.

**Step 1, first run (2026-10-28): FAILED.** Outcome p50 − cost (and its minimum-income-aware
variant): weekly gap trend +€6.5/week (se 0.9; MIC-aware +7.3), placebos +163 to +224 (MIC-aware +179 to
+260) against a threshold of €20.5. Italy is stable (unit-demeaned −19 … +22 every month); Iberia swings
(−173 … +152). Diagnosis: the two countries withhold in different formats. From October 2021 a growing
share of Iberian unit-hours price capacity far above cost (over €200 above cost: 0% in mid-2021, 37% in
April 2022), while Italian plants withhold by not offering, which leaves p50 missing. p50 mixes how much a
plant withholds with the price it runs at, and records withholding differently in the two countries.

**Step 1, second run — the two-part outcome, fixed here before running.**
- **Part 1, willingness to run**: `run20` = MW offered at or below cost + €20, divided by K (the unit's
  pre-cap 99th-percentile offered MW). €10 and €50 as checks. Withholding by a high price and by not
  offering count the same.
- **Part 2, running price**: `m25` = p25 − cost, the markup at the first quarter of K, defined in 95–100% of
  unit-hours in both countries.
- Cost is the bid-time cost after the subsidy (Iberia) or without one (Italy), as before.
- **Stop rule**, per part: stop if the weekly pre-period gap trend is significant at 5% (Newey–West, 4
  lags) and over a year exceeds the threshold, or if any placebo cap (2021-10-01, 2022-01-01, 2022-03-01)
  reaches the threshold. Thresholds: €20.5 for m25 (a fifth of the mean subsidy, as before); 0.05 (5% of
  capacity) for run20.
- The first run's failure is reported next to this one whatever the result.

**Step 1b — what drives any remaining drift.** If either part fails: the gap by firm and by unit, its dating,
and the events that hit one side only (French nuclear outages and Iberian exports in 2022; the Iberian
drought; PSV against MIBGAS through the war-driven spikes). Descriptive; it decides whether a control can
be rebuilt (e.g. by conditioning on one of these) or whether the within-Iberia designs take over.

**Step 1, second run — result (2026-10-28): FAILED.** m25: trend +188/yr, placebos +86 to +124; run20:
trend +0.12/yr, placebos +0.066 to +0.069 (threshold 0.05). €10/€50 variants alike.

**Step 1b — two alternative gas costs** (`analysis/gas_cap_cost_test.py`): a 30-day lagged hub price in
both countries, and the higher of MIBGAS and PSV in Iberia. Neither removes the drift in m25 (placebos
+72 to +123); run20 with the lagged cost passes its placebos (+0.023 to +0.049) but not its trend. The
Iberian cost stands.

**Step 1c — conditional on pre-auction demand conditions** (`analysis/gas_cap_conditional_pretrend.py`,
eight controls: REE D-1 demand, wind, solar; RTE D-1 French demand; lagged French nuclear; predicted
open French line; lagged hydro storage; PSV − MIBGAS at D-2). m25: trend +33/yr (t 0.4), placebos +68
(se 41), +10, −11: fails on 2021-10-01 only. run20 worse.

**Why m25 drifts**: the Iberian price at a quarter of capacity barely follows cost (median €10 → €100
while cost went €76 → €231, June 2021 → March 2022), by every firm but Iberdrola: plants offer their
minimum-load block low under the protection of the minimum-income condition. Hence `p_mid`, the price
midway between JRC's minimum load and K. Its step 1 (`--outcomes mmid`) fails on the full window (trend
+391/yr, placebos +179 to +238) and from 2021-10-01 (conditional: +15, +53, −1): in means, p_mid often
lands inside the high-priced withholding blocks.

**Step 1d — four ways of building the comparison** (`analysis/gas_cap_identification_tests.py`, outcome
mmid, 19 controls adding the Iberian thermal gap, temperature in both countries, holidays in both, Italian
demand):

| method | placebos 2021-10 / 2022-01 / 2022-03 (threshold €20.5) |
|---|---|
| conditional DiD | +175 / +62 / +25 (trend +217/yr): fails |
| interactive fixed effects, r = 1 | +23 / +67 / +97: fails |
| r = 2 | −2 / +17 / +59: fails on one |
| **r = 3** | **+0.6 (se 12) / +0.3 (24) / +27 (22)**: fails narrowly, within one se of zero |
| unit-level synthetic control | +172 to +238 (means, driven by a few units; medians +75 to +139): fails |

Daily offers do not follow daily cost before the cap (slope Iberia 0.33, Italy 0.04), weekly barely
(0.39, 0.82), **monthly one-for-one (Iberia 1.00, se 0.14; Italy 0.91, se 0.21)**. So Design B (offers
against cost changes, within Iberia) works at a monthly horizon only.

**Decision (2026-10-28).** Main estimate: interactive fixed effects against Italy on the full window, the
number of factors chosen by Bai & Ng's (2002) criterion, not by the placebos; Moon & Weidner (2015) for
over-specification. To run once the user has the literature (Bai 2009; Bai & Ng 2002; Gobillon & Magnac
2016; Xu 2017; Athey et al. 2021; Arkhangelsky et al. 2021; Roth 2022; Rambachan & Roth 2023). Report the
pre-period placebos with Rambachan–Roth sensitivity rather than as a pass/fail, given Roth (2022) on
pretesting after this many attempts. Supporting: the sharp break at 2022-06-15 and a monthly Design B.

**Step 2, the main estimate — specification fixed 2026-10-28, before running.**
- **Panel**: weekly unit means of mmid (p_mid minus the bid-time cost after the subsidy), 2021-06-15 →
  2023-06-30; units with at most 30% of weeks missing over the window.
- **Dose**: Y_w, the week's mean bid-time subsidy (0 before 2022-06-15 and after 2023-02-25). On the
  markup scale, bidding at cost gives θ = 0 (the offer falls with the cost) and keeping the whole subsidy
  gives θ = 1 per € of Y. Pass-through ρ = 1 − θ.
- **Estimator A, Bai (2009) / Gobillon & Magnac (2016)**: y_iw = α_i + ξ_w + λ_i′F_w + θ·(Iberia_i × Y_w)
  + ε, all units, least squares alternating with principal components, missing cells imputed (EM).
  Also the binary version, θ_D on Iberia × binding.
- **Estimator B, Xu (2017)**: factors from Italian units only (two-way effects + r factors), each Iberian
  unit's loadings from the weeks before 2022-06-15, its no-cap path imputed; the weekly mean gap ATT_w,
  then θ from ATT_w on Y_w through the origin over the binding weeks, and the mean ATT over the weeks after
  2023-02-25 (should be ~0: no subsidy).
- **Number of factors**: Bai & Ng's IC_p2 on the Italian two-way-demeaned matrix, k_max = 8: the main
  choice. Xu's leave-one-out cross-validation on Iberian pre-cap weeks reported beside it. Both estimators
  at the IC_p2 choice; the other r = 0…5 shown as sensitivity, not chosen among.
- **Inference**: firm block bootstrap, resampling firms within each country, 199 draws.
- **Reading**: θ against 0 (bidding at cost, the regulator's premise) and 1 (offers ignored the subsidy).

**Step 2, the main estimate — result (2026-10-28, `analysis/gas_cap_ife.py`): NOT IDENTIFIED.**
50 Iberian and 40 Italian units × 107 weeks. IC_p2 falls monotonically to k_max = 8 (uninformative);
Xu's cross-validation picks 4. θ (markup change per € of subsidy) by r = 0…5: estimator A (Bai) −0.65,
+0.73, +0.17, −0.30, −0.30, −0.22; estimator B (Xu) −0.15 to −1.88. At r = 8: A −0.12 [−0.52, +0.65],
B −1.69 [−4.47, +0.68] (firm block bootstrap, 199). **B fails its own check**: the mean gap after
2023-02-25, when there was no subsidy, is +€168 [+25, +479] (+185 to +281 at every r), so factors
estimated on Italy do not predict Iberian markups once the cap ends. A changes sign with r. Reading: the
Italian comparison, tried with a fixed specification, does not identify pass-through; Iberian plants move
between a cheap minimum-load block, a near-cost band and withholding blocks in ways no common factor
shared with Italy captures. Next (to be approved): the sharp break at 2022-06-15 and the monthly Design B,
within Iberia. Weekly gaps in `outputs/tables/gas_cap_ife_att_weekly.csv`.

**Step 2b — within Iberia: the sharp break at 2022-06-15 (specification fixed 2026-10-28, before
running).** The subsidy starts at one moment for every Iberian plant: the bid-time Y is €71/MWh on the first
delivery day and €95–140 within the week (mean €106 over the first 7 days, €124 on delivery prices): the
offers of 14 June (delivery 15 June) were the first made under it. Nothing else in the offer problem
jumps that day, so the change in offers across the break, net of the change in own gross cost, measures
how much of the subsidy went into them.
- **Statistic**: for unit i, J_i = [mean of (offer − gross cost) over the k delivery days from 15 June] −
  [the same over the k days to 14 June]. Bidding at cost gives J = −Ȳ (the offer falls by the subsidy);
  ignoring it gives J = 0. So ρ_break = −J̄ / Ȳ, with Ȳ the bid-time subsidy over the k days after.
- **Outcomes**: p_band (steps within ±€10 of the clearing price, the main one), p_mid, and run20 (MW
  offered at or below net cost + €20, over K; for it the at-cost prediction is a rise).
- **Bandwidth**: k = 7 days (main), 3 and 14 as checks. Same weekdays on both sides.
- **Reference distribution (the stop rule)**: the same statistic at every day of the pre-period
  (2021-06-15 → 2022-05-13, before the decree was published), giving the jump in (offer − gross cost)
  that ordinary days produce. ρ_break is read only if the 2.5–97.5% range of those placebo jumps is
  narrower than ±Ȳ/5 (about ±€21 at k = 7); otherwise the break is no sharper than an ordinary week and the
  design stops. Inference on J̄: firm block bootstrap (resampling Iberian firms), and the placebo range.
- **Threats**: the cap also lowered the Iberian price and raised exports to France the same day, so
  residual demand moved with it. Offers that respond to that are conduct, not noise, but they mean
  ρ_break is pass-through *at the new residual demand*. Anticipation: the decree was published
  2022-05-14; the days 2022-05-14 → 06-14 are shown, not used as the pre-window.

**Step 2c — within Iberia: monthly Design B (fixed 2026-10-28, before running).** Before the cap,
monthly offers follow monthly gross cost one for one (slope 1.00, se 0.14; step 1d). Under the cap a
bidder at cost follows the *net* cost (gross − Y), one who ignores the subsidy follows the gross.
- **Regression**: o_im = α_i + β_g·c_im + β_n·(c_im − Y_m) + γ′X_m + ε, unit-month means 2021-06 →
  2023-06; o = p_band (main) and p_mid; c the bid-time gross cost; X the monthly means of step 1c's
  controls. Bidding at cost: (β_g, β_n) = (0, 1); ignoring the subsidy: (1, 0). ρ = β_n / (β_g + β_n).
- **What separates the two**: the gap c − (c − Y) = Y, which is 0 in 15 months and runs to €336 in the
  9 binding ones; and coal (Y is the same per MWh, but it is most of coal's cost), entered as a second
  group with its own α_i.
- **Stop rule**: the pre-period slope must stay at one in the estimating sample (β_g on months with
  Y = 0, |β − 1| < 0.3), else the design's premise fails. Inference: firm block bootstrap.
- **Threat, named**: Y is large exactly when gas was dearest, and step 1 showed that Iberian
  withholding rises with the gas price. A slope on gross cost that is not linear at high gas loads onto
  β_g. Check: the same regression with c entered in bins.

**Steps 2b and 2c — result (2026-10-28, `analysis/gas_cap_within_iberia.py`,
`outputs/tables/gas_cap_within_iberia.csv`; firm block bootstrap, 499).**

*Correction to the specification above, made before reading the result*: for run20, measured
against the net cost, bidding at cost predicts **no change** across the break and ignoring the
subsidy a fall (not a rise, as written).

*Found after running, and it changes the reading*: **p_band is the clearing price to within €10 by
construction** (median |p_band − price| €4.4; monthly correlation with the price 0.99). So the
p_band results measure how the Iberian **price** followed the subsidised cost — price pass-through,
already measured by Haro Ruiz et al. — not how plants' own offers did. **p_mid is the conduct
outcome**; the p_band rows are reported, not read as conduct.

2b, the sharp break: **STOP on every variant.** Ordinary pre-period weeks move (offer − gross cost)
by ±€35–130 (placebo 95% ranges), against a threshold of ±Ȳ/5 ≈ €16–25. Recorded anyway: at k = 7,
J(p_mid) = −190 [−422, −67] against Ȳ = 106 (ρ 1.8); J(p_band) = −89 [−104, −41] (ρ 0.83, 12 units);
run20 +0.02 [−0.04, +0.07]. The p_mid and p_band jumps lie outside the placebo range, so the break
is unusual, but it is not clean enough to size ρ by the rule fixed in advance.

2c, monthly Design B: **the premise passes** (slope on cost in the months with Y = 0: 1.05 for p_mid,
0.89 for p_band).

| outcome | spec | b_g (gross) | b_n (net) | ρ = b_n/(b_g+b_n) |
|---|---|---|---|---|
| p_mid | linear | −0.56 [−1.98, +0.39] | +1.51 [+0.25, +3.82] | 1.60 [0.48, 2.95] |
| p_mid | controls | −0.04 [−0.38, +0.37] | +0.76 [+0.20, +1.46] | **1.06 [0.58, 1.90]** |
| p_mid | cost bins | | +1.15 [+0.12, +3.03] | |
| p_band (price) | controls | −0.03 [−0.12, +0.11] | +0.94 [+0.79, +1.14] | 1.04 [0.90, 1.16] |
| p_band (price) | cost bins | | +0.63 [+0.47, +0.85] | |

Gas and coal together give the same numbers (2 coal units). Reading: Iberian offers above minimum
load followed the **net** cost, not the gross: ignoring the subsidy (ρ = 0) is rejected in every
p_mid specification, and bidding at cost (ρ = 1) is not. The interval is wide (lower bound
0.48–0.58), so keeping up to about half the subsidy is not ruled out. Identification here is
before/after within Iberia, conditional on a cost slope estimated on the uncapped months, so it
rests on that slope staying put at the crisis's high gas prices; the bins check is noisy (b_n
0.12–3.03) and does not settle it.

**Step 2d — Great Britain as a second comparison (data fetched 2026-10-28).** Great Britain was
uncapped and is not coupled to Iberia (it left the European coupling on 2021-01-01). Its unit-level
offers are balancing-mechanism offers (Elexon BOD, `fetch/fetch_elexon_bod.py`): prices to raise or
lower output relative to the plant's own final physical notification (FPN), not day-ahead offers.
Two analogues of the Iberian outcomes, fixed before looking:
- **Running price**: the offer on the first band above FPN (pair 1) minus gross cost: what the plant
  asks to run more.
- **Willingness to run**: FPN over capacity, the share the plant chose to generate.
Cost: (SAP gas + carbon)/efficiency (`fetch/fetch_ons_gas_sap.py`; JRC efficiencies join on
National Grid's unit name). Carbon: UK ETS from 2021-05-19 plus the £18/t Carbon Price Support —
**no free series yet**. Then step 1 (pre-trend, same placebos and thresholds) against Iberia.
Known issue: in 2021–22 British balancing offers carried large premia for constraint reasons, which
Ofgem pursued under the transmission constraint licence condition; the pre-trend test shows whether
that drifts.

**Step 2 — pass-through (earlier sketch).** m_i,h = α_i + δ_country×hour-of-day + δ_date + ρ̃·(Iberia_i × Y_d) + ε,
where ρ̃ = 0 is full pass-through on the markup scale (ρ = 1 − ρ̃ on the offer scale). Date
fixed effects take out the common European gas and carbon shocks. Also the binary version
(Iberia × binding period), and the switch-off in March 2023 on its own.
Inference: clustered by firm (27 firms), wild cluster bootstrap because only 12 are treated.
*Report* ρ with its interval; read it against price-taking (ρ = 1).

**Step 3 — by firm and by position.** ρ for each of the five large Iberian firms; ρ by the firm's
net position that day. With one to six units a firm, these intervals will be wide; say so.

**Step 4 (separate approval) — the re-clearing check.** Only if step 2 stands.

## 7. Threats, and what answers each

- **Italy's own 2022 measures** (windfall tax on past profits, revenue caps on renewables and the
  EU's €180/MWh inframarginal cap) do not change a gas plant's marginal gain from an offer.
  Check the dates against the markup series anyway.
- **Italian plants bid in MGP with an eye on the dispatching services market (MSD)**, and Iberian
  plants with an eye on REE's technical constraints (`pdvd`). Both are constant features of each
  country, absorbed by unit fixed effects, unless they changed in 2022. Check MSD volumes.
- **The cap changed Iberian residual demand** (exports to France rose over 80%), so a markup can
  move with demand conditions, not only with conduct. Step 2 measures the total change; the
  step estimator's X̃ separates the two and is the follow-up.
- **Different gas hubs** (PSV ran €25/MWh above MIBGAS in 2022): handled by using each plant's
  own cost, but a cost error that differs by country would bias ρ. Check with PSV in place of
  MIBGAS for Iberia as a bound.
- **Few treated firms**: wild cluster bootstrap; report the unit-level result as descriptive.
- **Anticipation**: the cap was agreed in March–April 2022 and published 2022-05-14. A cost that
  starts on 2022-06-15 should not move offers before then; step 1 shows whether it did.

## 8. To confirm before step 2

1. ~~The formula of Y~~ — confirmed (§4).
2. **Coal — settled and fixed 2026-10-28** (`subsidy_eur_mwh`, `marginal_cost_subsidised_*`; old
   columns unchanged; `markdown_contract_test.py` not yet rerun): coal plants receive the same per-MWh Y (EC recitals (24),
   (29), (39)), so coal's effective cost was c − Y. The repo gives coal its uncapped cost
   (`cap_applies` False), on the mistaken premise that the decree gives no conversion. Fix in
   `build_implied_marginal_cost.py` (a `subsidy_eur_mwh` column and a subsidised cost), then
   rerun `markdown_contract_test.py`, whose coal results change.
   **Timing of Y**: PGN is MIBGAS's price for the delivery day, final only after the gas session
   of D-1, later than the 12:00 offer deadline. A bid-time Y uses MIBGAS up to D-2, as the
   `_bid` costs do; report both.
3. Which cogeneration units were eligible (most cogeneration has regulated remuneration).

## 8b. Treatment intensity

Y is one number per day, so intensity varies over **days**, from 0 to €336/MWh, and Italy supplies each
day's counterfactual through the date effects. Three readings of intensity:
- **Dose-response**: ρ by bins of Y (say 0, 0–100, 100–200, over 200 €/MWh). Constant ρ is what bidding at
  cost predicts; a ρ that falls with Y means firms keep more of larger subsidies.
- **Relative to the plant's own cost**: Y/c differs across plants on the same day (a 0.50 plant loses a
  smaller share of its cost than a 0.55 one), and coal's cost fell far more in proportion (August 2022
  median: gas €306 → €113, coal €232 → €36).
- **The switch-off**: Y falls to 0 after 2023-02-25 while the decree stays in force; offers should rise
  back by Y.

## 9. Calls made in this draft (the user can overturn any)

- **Main outcome** (agreed 2026-10-28): the offer price of a unit's steps within a band of the clearing
  price, net of its cost after the subsidy. **Comparison outcomes**: the price of its last offered MW;
  capacity offered above cost after the subsidy, or not offered; and, Iberia only, the declared
  minimum-income variable term in `cab` (before and after, no Italian counterpart).
- Gas units only in the main estimate; coal as a second treated group (its cost is now fixed, §8.2).
- Plant-specific efficiencies only (56 Iberian, 73 Italian); generic ones as a robustness check.
- Window ends 2023-06-30, as fetched.
- Firm-level clustering with a wild bootstrap.
