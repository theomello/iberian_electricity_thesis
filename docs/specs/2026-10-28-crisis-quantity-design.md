# Quantity withholding through the crisis: the invasion, the cap, and market power

Status: draft, 2026-10-28. Written from a design discussion with the user. Nothing in it has been run.
Builds on `docs/specs/2026-10-28-gas-cap-conduct-design.md` (the gas-cap design; its §6 step 1 second run
and §10 drift question) and `notes/rq-gas-cap-declared-cost.md` (§1 offer limits, §2 declared cost, §5
capacity near cost in in-money hours).

## 1. Intent

The sentence the thesis should be able to write (the user's): through the 2022 crisis, Iberian firms
either passed the gas cap's subsidy on to consumers or used market power, judged against an Italian
benchmark.

**By example.** On 15 June 2022 a combined cycle's gross cost is €173/MWh and the subsidy €71, so its
net cost is €102. If it passes the subsidy on, it offers its capacity near €102 and its share of
capacity offered near net cost stays where it was. If it keeps the subsidy, it keeps offering near
€173, €71 above net cost, and that share collapses. In predicted in-money hours Iberia's share stayed
at 0.63–0.73 after the cap (§5 of the declared-cost note), and plants' declared costs passed on about
nine-tenths of the subsidy (§2 there). This design turns those descriptions into estimates with a
counterfactual.

**Why a quantity outcome.** Every earlier version of the gas-cap question used offer prices (p50, m25,
p_mid). They read high-priced blocks that almost never clear, and Iberia could not post such blocks
at all until 2021-07-07 (offer limits €0–180.30). Capacity offered near cost in hours the plant can
expect to run is what sets output and the price; a block at €800 that never runs does not move it.

## 2. The three questions

| | Question | Period | Branch |
|---|---|---|---|
| Q1 | When the invasion hit, did firms with larger stakes and steeper residual demand hold back more, in Italy and in Iberia? | 2022-02-24 → 2022-06-14 | A |
| Q2 | Did the subsidy reach consumers through the offers? | around 2022-06-15 | B |
| Q3 | Under the cap, did Iberian firms with large stakes still hold back? | 2022-06-15 → 2023-02-25 | A |

**Priority (the user's): Q2 is the most interesting; all three are tested, each only as far as it can
reach a finding or open a new door.** Q1 feeds Q2: the invasion is the common shock from which
interactive fixed effects learn how each plant responds (§5).

## 3. Goals, non-goals, anti-goals

- **Goal**: for each question, an estimate precise enough to separate the claims it is meant to
  separate (pass-through near 1 against near 0; β near 0 against the Italian β).
- **Non-goals**: a price outcome; a model of Great Britain (descriptive only: no public firm stakes,
  and its balancing mechanism is pay-as-bid, so the uniform-price stake logic does not apply); a
  welfare figure in euros for consumers (a later step if Q2 lands).
- **Anti-goal (the user's)**: a result that supports none of the possible claims. A clean run with
  bands from 0 to 1 is a failure. A precise null is a finding.

## 4. Outcome, shared by both branches

Unit-hour panel `outputs/tables/gas_cap_offer_panel.parquet` (Iberian and Italian gas units with a
plant-specific efficiency, 2021-06-15 → 2023-06-30, built by `gas_cap_offer_panel.py`).

- **`run20`**: MW offered at or below cost + €20, over K (K = the unit's 99th percentile of hourly
  offered MW in the year before the cap). Cost is bid-time (prices final at 12:00 on D-1) and, in
  Iberia, net of the subsidy.
- **Twin outcome `run20_gross`** (new column): the same against `cost_gross`. The two bracket
  pass-through: full pass-through leaves `run20` unchanged and raises `run20_gross`; none leaves
  `run20_gross` unchanged and collapses `run20`. Identical before the cap and in Italy.
- **Sample: predicted in-money unit-hours**: the same zone-hour price the day before minus the unit's
  cost above €50 (main), €20 (check). Known when offers close, so not chosen by the price the offers
  set. As in `gas_cap_inmoney_pretrend.py`.
  - **Selection under the cap**: with net cost lower, more Iberian hours qualify after 2022-06-15. Main
    sample uses net cost (what the plant faced). A gross-cost sample is not usable as the check: the
    lagged Iberian price is itself lowered by the cap, so few hours would qualify in summer 2022.
    Checks instead: (a) all hours, no in-money condition; (b) margin €20 on net cost; (c) the main
    sample reweighted to the pre-cap mix of hour of day × month. Report all; if they disagree, say so.
- `run50` as a check, as before.
- **Iberia has almost no predicted in-money hours before September 2021** (31 unit-days in September,
  1,097 in October). The effective pre-period is 2021-10-01 → 2022-06-14.
- **Italian essential units** (must-run under regulated offer rules; ARERA 563/21 lists the 2022 set,
  rules in ARERA 111/06) are flagged by hand and dropped from the main Italian sample.

## 5. Branch B: Q2, the subsidy against a counterfactual from Italy

**Idea.** Interactive fixed effects let common shocks (gas prices, the invasion) hit each plant with
its own loading. Estimate the factors from Italian units over the whole window and each Iberian
unit's loadings from the weeks before the cap; impute each Iberian unit's no-cap path after
2022-06-15; the gap between actual and imputed is the effect of the cap. The invasion is what makes
the loadings informative: it is the largest common shock inside the pre-period.

**Specification (to fix before running; follows `gas_cap_ife.py`, which ran it on p_mid).**
- Weekly unit means of `run20` (and `run20_gross`) over predicted in-money hours; weeks with no
  in-money hour are missing (EM imputation, as in `gas_cap_ife.py`). Units with at most 30% of weeks
  missing over 2021-10-01 → 2023-06-30. **Fixed now, before counting**: if fewer than 25 Iberian
  units pass, the threshold is 50%; if fewer than 25 pass at 50%, Branch B stops.
- Clusters for the bootstrap: Iberian owner groups; Italian operators as in the panel for now, rerun
  on the §8 group roll-up when it exists (reported beside, not replacing).
- Estimator B (Xu 2017) as main, estimator A (Bai 2009) beside it. Number of factors: Xu's
  cross-validation on Iberian pre-cap weeks (IC_p2 was uninformative last time, falling to k_max);
  r = 0…5 reported as sensitivity, not chosen among.
- Firm block bootstrap within country, 199 draws.
- **Reading.** Under no pass-through the cap lowers `run20` by roughly the share of capacity priced
  between net cost + €20 and gross cost + €20; under full pass-through it leaves `run20` unchanged.
  ρ is read off the two outcomes jointly; the exact mapping is the first thing step B1 fixes (§7).

**Its own check, from the last run.** Estimator B failed on p_mid because the gap after 2023-02-25,
when there was no subsidy, was +€168. Here the same check applies: mean gap after 2023-02-25 should be
near 0. It is the stop rule, not a diagnostic.

**What Iberia's flat line implies (a guess to test).** If the invasion's effect is mostly
Italy-specific (MSD, dependence on Russian gas), Iberian units load on no factor, the counterfactual
is "Iberia stays flat", and B reduces to the before-and-after. That is a valid answer, and the
report must say that this is what happened.

## 6. Branch A: Q1 and Q3, who holds back

**Idea.** Within each country, compare firms and hours. Theory (p − c = β·n/|RD′|, framework in this
repo): a firm holds back more when it sells more at the market price than it buys there (stake n)
and when the price reacts more to what it holds back (steeper residual demand, small |RD′|).

- **Regressor** P = n/|RD′| per firm and hour. Iberia: every owner of a gas unit in the panel, not
  only the five large firms of `firm_x.py` (TotalEnergies, Axpo, Engie, Cepsa, Bahía, RWE own gas
  units too): n exposed as in `firm_incentive_rebuild.py` (which agrees exactly with `firm_x.py` on
  the five), slope by `firm_x.py`'s band rule, on dated ownership. Italy: to be built (§8).
- **Outcome** `run20` of the firm's gas units in predicted in-money hours.
- **Specification** run20_iht = a_i + d_{date×hour, country} + β·P_ft + controls + e; within-country
  effects only, so Italy's March 2022 break does not enter.
- **Q1**: β in each country, 2022-02-24 → 2022-06-14 against 2021-10-01 → 2022-02-23 (does β rise
  with the invasion?). **Q3**: β in Iberia over the cap against Italy over the same weeks.
- **Endogeneity.** n and |RD′| are set in the same auction as the offers. Main: P built from
  quantities known before the auction (previous day's same-hour n and slope). Iberia has
  instruments tried before (reactor outages, own-region wind; F 22–33); Italy has none yet. An IV
  version is a later step, not part of this design.
- **Power is the known risk.** The own-wind test stopped because its minimum detectable β (1.16)
  exceeded 1.

## 7. Steps, each with a stop rule fixed before running

Every step needs the user's yes before it runs.

**B0. Build** `run20_gross` and the gross-cost in-money sample in the panel; flag Italian essential
units. Check: before 2022-06-15 and in Italy `run20_gross == run20` exactly.

**B1. Power and mapping, before any estimate.** Both ends are built from each unit's **pre-cap
behaviour carried forward**, never from its actual post-cap steps (those are the outcome; shifting
them would count pass-through twice). For each Iberian unit, take its offer steps over the last eight
weeks before the cap as markups over gross cost, by hour of day. After 2022-06-15, place those
markups (i) over net cost (full pass-through) and (ii) over gross cost (none). Compute `run20` and
`run20_gross` under each, on the main sample. The gap between (i) and (ii) is the effect B must
detect; the mapping from the actual outcome to ρ is linear interpolation between the two ends. Then
the minimum detectable effect of estimator B on placebo cap dates (2022-01-01, 2022-03-01) with the
bootstrap. **Stop if the MDE exceeds half the (i)–(ii) gap.**

**B2. Estimate** (only if B1 passes). **Stop rule**: the mean gap after 2023-02-25 outside
[−0.05, +0.05] of capacity at the chosen r means the counterfactual does not hold; report and stop.
Otherwise report ρ with its band, and the r = 0…5 sensitivity.

**A0. Power for Q1/Q3, before building Italian stakes.** On Iberia only (data on disk): minimum
detectable coefficient for run20 on lagged P in 2022-02-24 → 2023-02-25, firm-clustered. Stated in
the outcome's own units, so no conversion to €/MWh is needed: **stop Branch A if the MDE of a move in
P from its 25th to its 75th percentile exceeds 0.05 of capacity** (the threshold the gas-cap step-1
rule already uses for run20). Iberia goes first because if Iberia cannot detect it, Italy's
benchmark has nothing to compare with.

**A1. Italian stakes** (only if A0 passes; the data work of §8). **A2. Estimate Q1, then Q3.** Stop
rule for each: the Italian β not distinguishable from 0. Then there is no benchmark, which is the
failure in §3.

## 8. Data still missing (Italy, for Branch A)

- **Group positions.** GME bids carry the operator for ~81% of accepted volume (one day checked,
  2022-09-28); 449 units appear only as "Bilateralista", 18–19% of volume each side. Bilateral rows
  carry no counterparty (one transaction per row). Recover units by name and zone where possible.
  Roll up groups (Enel Produzione + Enel Energia; Eni + Eni Plenitude; …). Exclude Acquirente Unico
  (regulated buyer, 6.5% of purchases), as Spain's pass-through suppliers are excluded.
- **Italian residual-demand slope** per group: from the GME curves, same band rule as `firm_x.py`,
  zonal (the price is zonal).
- **MSD offers** (Terna's balancing and redispatch market). GME's MSD download page offers the same
  `OffertePubbliche` "Public Domain" archive; not yet downloaded, start date and fields unconfirmed.
  Needed because Italian plants hold capacity out of the day-ahead market to sell it in MSD, which
  looks like withholding in `run20`. Used as a control (MSD capacity offered by the unit) and to read
  the March 2022 drop.
- **Essential units**: hand list from ARERA's decisions.

Fetching anything needs the user's yes.

## 9. Threats

| Threat | Answer |
|---|---|
| In-money sample changes at the cap | net-cost and gross-cost samples both reported (§4) |
| Italy's own March 2022 break | B: absorbed as a factor; A: within-country only |
| MSD value in Italy | MSD offers as control (§8) |
| Italy's 2022 windfall tax on energy firms' extra profits (*contributo straordinario*, Aiuti decrees; from memory, to verify) | charged on profits after the fact, so no change in cost per MWh, but it could shift Italian conduct; date it and check for a break in Italian run20 around it |
| Minimum-income condition: Iberian plants protect a low block | run20 counts MW near cost whatever the condition; declared cost as a separate check (declared-cost note §2) |
| Offer limits | effective pre-period starts 2021-10-01, after the limits moved |
| Pretesting after many attempts (Roth 2022) | stop rules here are fixed before running and are the only pretests |

## 10. Calls made in this draft (the user can overturn any)

- Outcome `run20` in predicted in-money hours, margin €50; twin `run20_gross`.
- Selection checks: all hours, margin €20, and the pre-cap hour × month mix (not a gross-cost sample,
  which the capped price would empty).
- B1's two ends from each unit's last eight pre-cap weeks of markups over gross cost, carried forward
  over net cost (full) and gross cost (none); ρ by linear interpolation between them.
- Unit filter 30% missing weeks, 50% if fewer than 25 Iberian units pass, stop below that.
- Branch A covers every Iberian gas owner, not only the five large firms.
- Bootstrap clusters in Italy: operators now, the group roll-up later as a check.
- Estimator B (Xu) as main for Q2, r by cross-validation.
- B1's stop threshold: MDE above half the full-versus-none gap.
- A0's threshold: an interquartile move in P must be detectable at 0.05 of capacity.
- Iberia's power check before any Italian data work.
- Effective pre-period 2021-10-01 → 2022-06-14.
- Italian essential units dropped from the main sample.
