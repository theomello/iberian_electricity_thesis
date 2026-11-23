# Medium-firm (6.1TD, 1–36 kV) response to the 2021 period calendar, with six placebo summers (proposal)

**Status: registered 2026-11-23 (user: "Register both"); binding from this commit.** Step zero
(placebo years and price tables only) runs after the commit. The estimation rules are registered now, before any
noise is seen, and run only if step zero passes and the user says yes. The user asked for medium firms on 2026-11-23
and chose the placebo years: add 2014 under its own data gate, and 2015–16 from the 6.1A series as a stand-in, gated
on matching E1+E2 in the overlap years. Companion: `2026-11-23-small-business-season-mirror-design.md` (same
inference).

Terms. **E1+E2**: measured demand at 1–36 kV, ESIOS indicators 1202 + 1203 (ESIOS is the data portal of REE, Red
Eléctrica, the grid operator). Its mix is about 72% old tariff 6.1A, 20% old 3.1A and 7% old 6.1B, all of which became
**6.1TD** in June 2021. **1369**: ESIOS measured demand on tariff 6.1A alone; until May 2021 it excludes 3.1A.
**MDE**: minimum detectable effect.

## In one example
Before June 2021, a medium plant on 6.1A had no peak periods in August: every August hour was the cheapest period
(P6). From June 2021 the new calendar treats August as a medium-season month: on working days, 9–14h and 18–22h become
P3 and the other daytime hours P4, so daytime is three or two periods dearer than before, while nights stay P6. In
the second half of June it goes the other way: most daytime hours fell one to three periods (old summer P1/P2 → new
P3/P4), so they became cheaper. In July, 9–10h and 19–21h moved up one period and 14–17h down one. If medium firms
respond to the calendar the way large industry did (−1.0 point of hour share per period step), their August daytime
share should fall, and their late-June daytime share should rise. This pattern does not exist in any year before
2021.

**Where the identification comes from** (within-hour variation of the step, from `schedule()`): **August 53%, late
June 44%**, early June, July and September 3%. Late June is about 10 working days a year with the opposite sign.
Without August the statistic rests on those days (rules E6 and E6b).

## What is new, and what is not blind
- **Already known.**
  - E1+E2's 2021 regulated-price elasticity: −0.084, interval [−0.20, +0.06], against 2017–19, S = 3, p 0.077.
    Description in `2026-11-18-industry-regulated-price-elasticity-design.md`.
  - Its hour-by-month pattern in summer 2021 (`notes/scope-2021-high-voltage-shift.md`): July and August nights +3,
    daytime −2 to −3, with a smaller version of the same in June and September. Its monthly evening-minus-night,
    2021 minus normal years: June −5.3, July −7.2, August −7.4, September −6.0 (normal-year sd 0.5–1.5). So an
    August-against-June gap of about −2 points was seen. For August this points the predicted way. **For late June it
    does not**: the prediction there is a daytime rise, and June showed a daytime fall.
  - This treatment and a placebo design for E1+E2 were proposed in `notes/scope-period-change-design.md`
    (2026-11-18). Large industry's version was registered and run; E1+E2's was not.
  - E1+E2 was already off in January–May 2021 (−9 to −3 points evening against night), before the reform.
- **New.** The null distribution: three more placebo summers (2014, 2015, 2016), and a statistic with hour fixed
  effects that removes any change shared by all summer months (such as the pre-reform deviation, if it holds every
  month). The registered rules are also new. As with the industry six-summer test, this is a new test with new data,
  not a re-reading of the earlier description, which stands.

## Data
- **E1+E2**: ESIOS 1202 + 1203, hourly, on disk from 2014-01-01, loaded with `tou_cross_tariff.esios_load([1202, 1203])`
  (local clock hour, labelled by its start). 2015 and 2016 are incomplete at source (1.1–1.6 TWh a month against
  5–7) and are not used.
- **Stand-in for 2015 and 2016**: ESIOS 1369 (6.1A only, 1–30 kV; it excludes old 3.1A, about 20% of E1+E2, and 6.1B,
  about 7%). On disk from 2018 only. **To fetch:** `fetch_esios_spain.py --ids 1369 --geo 0 --start 2015-01-01`, with
  the end left at its default. The fetcher rewrites the parquet from the requested chunks, so an end date would drop
  2018 onwards. M0 asserts rows in 2015–2017 and 2018–2019 after the fetch. 2017–2019 are the overlap years.
- **Holidays** (national, 2014 →), and **periods** from `tou_tariff_schedule.schedule()`, tariff "6.1": old 6.1A periods
  by day type (`old_period_6`, `old_day_type`) and new 6.1TD periods (`new_period_6`), both on the P1–P6 scale.
- **Prices (elasticity scale only)**: `outputs/tables/tou_power_term_6x.csv` (old 6.1A and new 6.1TD power terms,
  already read twice, Z1 of the industry spec), `tou_tariff_prices_2021.csv` and `tou_tariff_schedule.OLD` (energy terms).
- For the price-shape check: the Spanish day-ahead hourly price from REN (the Portuguese grid operator),
  `data/ren/ren_market_prices.parquet`, series ES, from 2014, joined through UTC. The OMIE file (OMIE is the Iberian
  power exchange) starts only in 2018.

## Years and cells
- **Summers:** working days (not weekend, not national holiday, not 6 January), **1 June → 30 September**.
- **Treated: 2021.** **Placebo: 2014, 2015, 2016, 2017, 2018, 2019** (S = 6; 2015 and 2016 from the stand-in).
  2020 is not used.
- **Cells:** (month, hour). June is split into two halves (1–15 and 16–30), because the old calendar changed on 16
  June. So there are 5 periods of the year by 24 hours = 120 cells. A cell's value in year Y is the mean hour share
  over Y's working days in it.
- **Hour share:** s(d,h) = 100 × load(d,h) / mean over the day's 24 hours.

## The statistic
1. **Period step d(c) = old period number − new period number** for 6.1A → 6.1TD (positive = the hour became
   dearer), averaged over the cell's working days. This is the scale of large industry's reduced form.
2. **Per-year regression, raw:** s_Y(c) = α_Y(h) + b_Y · d(c) + error, unweighted.
   - The hour effects absorb every change that is the same in all five parts of the summer. That includes a
     pre-reform deviation shared by every month.
   - **Old 3.1A customers (about 20%) are not absorbed.** Their old calendar is the same from June to September. The
     new one makes every working-day hour from 8h to 23h about two periods dearer in July (P1/P2) than in June,
     August and September (P3/P4). So 3.1A has a July-specific step that is not in d(c), while 6.1A's July step is
     near zero. Rule E6c drops July.
   - b_Y is identified only from how the step differs between months within each hour. August (old: all P6) carries
     most of it.
3. **Reported, not ruled:** the industry form, s_Y(c) = a_Y + b_Y · d(c) with no hour effects. Its b_R − m (not a
   single year's b_Y) is directly comparable with large industry's −1.0 point per step.

## Inference (as in the companion spec)
m and s are the mean and standard deviation of the placebo b_Y. Mean null: t = (b_R − m) / (s·√(1 + 1/S)), Student's t
with S − 1 degrees of freedom, one-sided. Trend null: a straight line in year through the placebo b_Y, predicted at
2021, se_pred = s_e·√(1 + 1/S + (2021 − ȳear)² / Σ(year − ȳear)²), S − 2 degrees of freedom. Rank: (1 + #{b_Y ≤ b_R}) /
(S + 1). MDE in points per step = (t_{S−1, 0.95} + t_{S−1, 0.80}) · s · √(1 + 1/S), i.e. 2.94 · s · √(7/6) for S = 6. The
normal version (2.49) is reported beside it.

## Step zero (placebo years and prices only; run after the commit)
- **M0 Data (gate).**
  - E1 and E2 have at least 99% of the June–September hours in 2014, 2017, 2018 and 2019.
  - **2014 gate:** each month's E1+E2 energy (June–September 2014) lies within ±15% of the 2017–2019 mean for that
    month. This gate is specific to E1+E2. The earlier exclusion of 2014 came from a different check (all voltage
    levels against total demand, +2.6% in July 2014), which stays recorded for the designs that used it.
  - 1369 has at least 99% of the June–September hours in 2015, 2016 and 2017.
  - *Fails:* the failing year leaves the placebo set.
- **M1 Stand-in (gate for 2015–16).** For each overlap summer (2017, 2018, 2019), b_Y is computed on 1369 and on E1+E2.
  The stand-in passes if both the largest absolute difference and the mean difference are at most half the standard
  deviation of E1+E2's b_Y over its own clean years (2014 if M0 kept it, 2017, 2018, 2019). The correlation of the
  two series' cell shares is reported beside it. With three overlap years this gate has little power, and 1369 is 72%
  of E1+E2, so the two series share most of their load. E5 below is the real check. *Fails:* 2015 and 2016 leave, and S = 4 (or 3 without 2014). This fallback is fixed now.
- **M2 Seal.** The step-zero script keeps E1+E2 and 1369 rows only up to 2019-09-30, asserted on the filtered frame.
- **M3 Noise (gate).**
  - The MDE in points per step for the final placebo set, and its elasticity equivalent η_MDE = (MDE / s̄) / d̄.
  - s̄ is E1+E2's mean hour share in the cells where d varies across months (placebo years).
  - d̄ is the slope from regressing Δ ln p(c) on d(c) over the 120 cells, both demeaned within hour (the same hour
    effects as the main statistic), unweighted. p is the 6.1 regulated price: energy toll and charge, plus the power
    term spread over its period's hours, at 2021 values and E = €100.81, old 6.1A against new 6.1TD (the industry
    spec's full dose). The version without hour effects is reported beside it.
  - The gate is on detection (E1) only. The trend-null MDE is reported beside it and is larger, so E3 can fail on
    power alone. This is stated now.
  - **Pass if η_MDE ≤ 0.15.**
  - Reported beside it: the placebo b_Y by year, m, the trend slope, and the industry-form MDE.
  - *Fails:* closed, and the treated summer is never computed.
- **M3 passes:** stop and ask the user before the estimation runs.

## Estimation rules (registered now; run only after M3 passes and the user says yes)
- **E1 Detection (primary).** b_R − m < 0, mean-null one-sided p ≤ 0.05.
- **E2 Rank.** b_R below every placebo summer (p_rank = 1/(S + 1)).
- **E3 Trend null.** b_R − ŷ < 0, trend-null one-sided p ≤ 0.10.
- **E4 Not one summer.** Leaving out each placebo summer in turn, the mean-null p ≤ 0.10.
- **E5 Without the stand-in.** With E1+E2's own placebo summers only (2014 if kept, 2017–19), b_R − m < 0 and the
  mean-null one-sided p ≤ 0.10.
- **E6 Not August alone.** Without the August cells, b_R − m keeps its sign. August is also the holiday month, so its
  normal-year profile is unusual.
- **E6b Not late June alone.** Without the 16–30 June cells, b_R − m keeps its sign.
- **E6c Without July.** Without the July cells (old 3.1A customers' July step), b_R − m keeps its sign.
- **E7 Wrong hours (one-sided).** Hours 0–7 are P6 under both calendars (d = 0). Regression on the 20 cells of hours
  1–4 (five parts of the summer × four hours), with hour effects. The fake step is the mean d over hours 8–23 of the
  same part of the summer, with June split at the 16th. **Fails only if** its b_R − m is below the lower 95% bound of
  its own placebo prediction interval.
- **E8 Price shape.** Add the cell's mean price share (hourly Spanish day-ahead price over its daily mean, REN series)
  to every year's regression. b_R − m keeps its sign and stays inside the main 95% interval,
  (b_R − m) ± t_{S−1, 0.975} · s · √(1 + 1/S). The wholesale price rose through summer 2021, and its hourly shape
  differs by month. Sub-statistics recompute m and s from their own placebo values.
- **Reported, no rule:**
  1. The industry form (no hour effects) beside large industry's −1.0.
  2. The elasticity equivalent.
  3. September split at the 16th (the charges were cut on 16 September 2021; ranks are unchanged, so this is a check
     on level effects).

Failed rules are recorded and kept. No other months, cells, stand-in, gate, control or step coding is tried after a
failure.

## What each outcome means (the most severe failure decides)
- **M0 or M1 failures** shrink the placebo set as fixed above. **M3 fails:** medium firms cannot be read with this data;
  recorded, and the gap stays.
- **E1–E8 pass:** medium firms responded to the reform's period calendar. Reported as points per step, with the
  industry form beside large industry's −1.0 and the elasticity equivalent.
- **E1 or E2 fails:** no detected response; the prediction interval is the bound.
- **E6b fails:** it rests on late June. **E6c fails:** it may be the old 3.1A customers' July step. Either way, not
  reported as a 6.1 calendar response.
- **Significantly positive (one-sided p ≤ 0.05 the other way):** sign failure, no estimate.
- **E3 or E4 fails, with E1 and E2 passing:** it rests on a drift or on one summer; reported as such, not as an
  estimate.
- **E5 fails:** it rests on the stand-in summers; not reported as an estimate.
- **E6 fails:** it rests on August (holiday month); reported as August only.
- **E7 or E8 fails:** the pattern is not specific to the tariff hours, or it follows the wholesale price shape; not
  reported as a calendar response.

## Threats
- **Not blind** (above): the 2021 month gradient was seen. The protection is the six-summer null and the rules, both
  fixed before the null is computed.
- **Stand-in composition.** 1369 excludes old 3.1A (about 20% of E1+E2), whose profile may differ. M1 gates this, and
  E5 checks the result without the stand-in.
- **2014's level.** The ±15% gate checks volume, not shape.
- **August holidays and COVID recovery in summer 2021.** These are month-specific, non-price changes. E6 and E4 cover
  them in part.
- **Contracts priced by period** may move with the calendar. For large industry the contract bound barely mattered.
- **The 3.1A share** (about 20%) has a July step that d does not model (E6c). Elsewhere it dilutes the response by
  about a fifth.
- **The late-June cells** carry 44% of the identification on about 10 days a year, and the seen June pattern goes
  against the prediction there.

## Changes made before registration (review of 2026-11-23)
These were made after the review, and no statistic had been computed:
- Fetch command fixed (start only).
- The identification split declared (August 53%, late June 44%), and the late-June cheapening added to the example.
- The seen monthly values declared, with late June against the prediction.
- 3.1A's July step stated, with E6b and E6c added.
- REN prices for E8 (OMIE starts in 2018).
- Dose per step defined as a within-hour slope.
- Stand-in gate given a level condition.
- 1369's coverage stated.
- The LASSO item dropped (it would need a new fit).
- Wrong-hours regression specified.

## Code and outputs
Fetch of 1369 for 2015–2017 (resumable fetcher, new range only); `scripts/analysis/mf_period_calendar_step0.py`
(M0–M3); outputs `outputs/tables/mf_period_calendar_step0{,_years}.csv`. Estimation:
`scripts/analysis/mf_period_calendar_estimate.py`, outputs `outputs/tables/mf_period_calendar_estimate{,_summary}.csv`.
Deterministic; no random draws. `scripts/qa/audit_data.py` runs after the fetch.

## Results of step zero (run 2026-11-23; `scripts/analysis/mf_period_calendar_step0.py`, committed in 416fb0d before the run; outputs `outputs/tables/mf_period_calendar_step0{,_years}.csv`)

- **Identification split** (as registered): August 52.8%, late June 44.3%, the other parts 2.9%.
- **M2:** E1+E2 and 1369 were cut at 2019-09-30 right after loading (asserted).
- **M0 passes.** E1+E2 has every June–September hour in 2014 and 2017–2019. 1369 was fetched from 2015 (complete for
  2015–2019). **2014 gate:** June–September energy over the 2017–19 mean is 0.919 / 0.931 / 0.907 / 0.965, inside
  ±15%, **so 2014 stays**.
- **M1 fails.** b(1369) − b(E1+E2) is +0.132, +0.147 and +0.122 in 2017, 2018 and 2019. Max 0.147 and mean 0.134,
  against a bar of 0.024 (half the sd of E1+E2's b). The cell shares correlate at 0.997, but 1369 (6.1A only, without
  old 3.1A and 6.1B) follows the step systematically more strongly. **So 2015 and 2016 leave, and S = 4** (2014,
  2017, 2018, 2019), as the fallback fixed in advance. E5 (without the stand-in) is now the same as E1.
- **Placebo b_Y** (points of the daily mean per period step, hour effects): 2014 0.228, 2017 0.293, 2018 0.177,
  2019 0.233. Mean 0.233, sd 0.047, trend −0.003 per year. Industry form (no hour effects): 0.514, 0.511, 0.403,
  0.456.
- **M3 passes.** MDE 0.176 points per step (t quantiles, 3 degrees of freedom; normal 0.131). s̄ = 107.2,
  d̄ = 0.105 log points per step, so **η_MDE = 0.016** against the bar of 0.15 (trend null 0.031). Industry form:
  MDE 0.196, η_MDE 0.016.

**Step zero passes with S = 4.** E1+E2's month-by-hour pattern is very stable across normal summers, so a
medium-firm elasticity of about 0.02 to the regulated period price would be detectable. Per the spec, the estimation
(E1–E8 on summer 2021) waits for the user's yes.

## Results of the estimation (run 2026-11-23; `scripts/analysis/mf_period_calendar_estimate.py`, committed in 0fec50a before the single run; outputs `outputs/tables/mf_period_calendar_estimate{,_summary}.csv`)

The pre-run review found a data trap, fixed before the run and recorded in `docs/data-reference/ree-ren-esios-miteco.md`.
REN's Spanish price for 2014–2017 comes as each day's 24 hourly prices sent twice on a 30-minute grid, so reading it by
timestamp scrambles the hours. It affected only E8's placebo controls.

Placebo summers 2014, 2017, 2018, 2019 (S = 4). b by year (points of the daily mean per period step, hour effects):
0.228, 0.293, 0.177, 0.233; **2021: 0.058**.

| statistic | effect b_R − m | one-sided p | 95% interval | rank | trend-null effect, p |
|---|---|---|---|---|---|
| **main (hour effects)** | **−0.175** | **0.023** | [−0.343, −0.007] | 1/5 | −0.164, p 0.103 |
| E6 without August | −0.016 | 0.45 | [−0.41, +0.38] | | |
| E6b without late June | −0.357 | 0.001 | [−0.45, −0.26] | | |
| E6c without July | −0.164 | 0.027 | [−0.33, +0.01] | | |
| E7 wrong hours 1–4 | +0.317 | (0.97) | [−0.00, +0.64] | | |
| E8 price-share control | −0.104 | 0.15 | [−0.37, +0.16] | | |
| industry form (no hour effects) | −0.348 | 0.005 | [−0.54, −0.16] | | −0.283, p 0.031 |
| September split at the 16th | −0.186 | 0.019 | [−0.35, −0.02] | | |

**Rules.**
- E1 detection **passes** (p 0.023).
- E2 rank **passes** (below all four summers, the floor 1/5).
- **E3 trend null fails**: effect −0.164 with p 0.103, against the bar of 0.10. The trend through four summers is
  nearly flat (−0.003 a year), so it fails on power: with S − 2 = 2 degrees of freedom the extrapolated prediction is
  wide. This was stated in advance as possible.
- E4 leave-one-out **passes** (p 0.059, 0.025, 0.022, 0.060).
- E5 (same sample as E1) **passes**.
- E6, E6b and E6c keep the sign: **pass**.
- E7 **passes** (the wrong-hours effect is positive).
- E8 **passes** (−0.104 keeps the sign and lies inside [−0.343, −0.007]).
- No significant wrong sign.

**Verdict, as registered.** E1 and E2 pass but E3 fails, so the registered outcome is "it rests on a drift; reported
as such, not as an estimate". Medium firms' summer-2021 month-by-hour load moved with the new period calendar,
beyond all four normal summers (mean null). It is not reported as an elasticity, because it does not clear the
trend null.

**Descriptive, not rules.**
- **Size.** −0.175 points of the daily mean per period step. The elasticity equivalent is **−0.016**
  (interval −0.031 to −0.001). In the industry form, −0.35 points per step against large industry's −1.0, an
  elasticity equivalent of −0.03. Medium firms moved about a third as much per period step as large plants, and very
  little per unit of regulated price.
- **It comes from August.** Without August the effect is −0.016 (p 0.45); without late June it is larger (−0.36). E6
  asked only for the sign, so it passes, but the response is an August response: the month the old calendar made
  all-off-peak, and also the holiday month.
- **Price shape.** With the wholesale price-share control, the effect shrinks to −0.10 (p 0.15). Part of the 2021
  pattern lines up with the hourly price shape.
