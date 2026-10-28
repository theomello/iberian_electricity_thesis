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

**Step 2 — pass-through.** m_i,h = α_i + δ_country×hour-of-day + δ_date + ρ̃·(Iberia_i × Y_d) + ε,
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
