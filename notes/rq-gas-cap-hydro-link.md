# Does hydro react to the gas cap's cost shock the way thermal declared costs did?

Started 2026-11-05. Script `scripts/analysis/gas_cap_hydro_link.py`; outputs
`outputs/tables/gas_cap_hydro_link_{summary,event,dose,checks,monthly,daily}.csv`. Builds on
`rq-gas-cap-declared-cost.md` §2 (thermal: day-one jump J = −0.544, against placebo band ±0.12),
`rq-water-value-forward.md` (λ*, the price-taking water value) and `rq-leg-b-levels.md`.

**Status of this file: §1 (the rules) was written before the script was run. §2 onward is added
after the run. Anything changed after seeing results is marked "RULE CHANGED" and the original kept.**

## 0. The question, with an example

On 14 June 2022 a gas plant's cost was €173/MWh; on 15 June the decree began paying it €71, so
its cost net of the subsidy was €102, and plants declared costs that fell about as much
(§2 of the declared-cost note). Now take a hydro unit whose price-taking water value λ* is €150 on
both days, and which offers its water at €150 on 14 June. Three things can happen on the 15th:

- it stays at €150: it follows λ*, so the ratio offer/λ* does not move (J = 0);
- it drops to about €73 (the thermal fall, log −0.72): it priced off the visible gas cost and not off
  its water, so the ratio falls (J ≈ −0.7);
- it drops with λ*, because the forwards λ* is built from had already priced the cap: the offer and
  λ* both fall, the ratio does not move. That is price-taking too, and is why the table keeps three
  columns: the offer, λ*, and their ratio.

The premise from the discussion: hydro firms track a visible thermal cost shifter, but left their
water value in 2019 – 2021H1 (+0.25 in the offer regression, resting on Iberdrola). If so, Iberdrola
is the firm most likely to have moved with the cap. EDP, whose revealed water value matches λ* within
6% (`rq-water-value-forward.md` §3), is the control that should not.

## 1. Rules (written before running, 2026-11-05)

**Outcome, per unit and day.** `y = ln(ocf / λ*30s)`.
- `ocf` = the offered price at which the unit's cumulative offered hydro volume (all hours of the day,
  withdrawn steps out) reaches its expected running share `cf_s`. The same read point as
  `rq-water-value-forward.md` §5.3, from `outputs/cache/step/hydro_YYYYMM.parquet`.
- `λ*30s` = `cost_eur_mwh` in `outputs/tables/hydro_cost_daily.parquet` (forwards settled by D−2).
- Also kept, to say which side moved: `ln(ocf)` and `ln(λ*)` separately.
- A unit-day needs `ocf > €1` (the repo's zero convention) and `λ* > 0`. Days at or below €1 are
  counted and reported, because a unit crossing the threshold at the event would drop out of the sample.

**Sample (fixed).** Units in `hydro_cost_daily` that are not `pumped`; unit-day `zero_share` not NaN and
at most 0.5 (the flag's own rule); a unit is dropped from a window if its `spell` changes inside it
(a >25% move in `cab` max power: the unit's contents changed); pass-through owners out. Firm = the owner
group in force on the day from `lib/unit_ownership.py` (`majority_group`, so dated, and share-based;
the script checks that no eligible unit is split between groups inside the windows and says so).
From the June 2022 list this gives EDP 7 units, Iberdrola 7, Endesa 4, Naturgy 3 (the minimum),
Movhera 1. **A firm gets its own row only with at least 3 eligible units having at least 4 days on each
side of the date**; Movhera and every other group enter the "all eligible" row only.

**Event statistic.** As in the thermal analysis: `J(D)` = median over units of
(mean y over D..D+6) − (mean y over D−7..D−1), per firm and pooled. Capacity-weighted mean (by `cab`
max power) kept as a second column. Actual date D = **2022-06-15**. Placebo dates: the same 273 dates,
**2021-09-08 → 2022-06-07** (windows wholly before the cap). For each firm: n units, n unit-days, J,
placebo 2.5 / 50 / 97.5 percentiles, the actual's percentile among placebos, and the two-sided share
of placebos with |J| at least as large.

**What counts as informative.** Let `h` = half the width of the placebo 2.5–97.5% band. The firm's
number is read only if `h < 0.544`, the size of the thermal jump: a thermal-sized response would then
lie outside the band. Otherwise **STOP for that firm**: the number is printed and not read.

**Reading for an informative firm.**
- J inside the band: the ratio did not move; the offer followed λ* (price-taking, or λ* had already
  priced the cap).
- J below the band: offers fell more than λ*; J above: rose more than λ*. Reported with
  J / (−0.721), the share of a full thermal-style fall.
- Which side moved is read from the `ln(ocf)` and `ln(λ*)` columns.
- **EDP against Iberdrola:** the difference J(EDP) − J(Iberdrola) against the same difference on the
  placebo dates (paired by date), same band rule, with `h` of the difference.

**Dose.** Window 2022-06-01 → 2023-03-31 (the subsidy is positive 2022-06-15 → 2023-02-25 and zero
before and after). Per firm, `y_ud = a_u + φ · x_d + e`, where `x_d` = the daily median over the
thermal sample (`gas_cap_declared_cost.py` units) of `ln(net_bid / gross_bid)`, i.e. the log fall in a
gas plant's cost from the subsidy, known at D−1 noon. φ = 1 is a hydro offer that falls, relative to
λ*, as much as a gas plant's cost does; φ = 0 is no movement relative to λ*. Two specifications: unit
effects only; unit effects plus `ln` of the bid-time MIBGAS price (λ* may lag gas). Standard error
clustered by ISO week, indicative only (one episode, few firms).
- **Placebo for the dose.** The same regression on the same-length window shifted by k days, with the
  subsidy hump shifted with it (so each placebo window has a fake subsidy of the true shape), for k in
  steps of 7 from −1,247 to +913 with |k| ≥ 245 (windows overlap the true one by under a fifth; the
  upper end keeps the window before the day-ahead market's 15-minute switch, 2025-10-01).
  About 270 placebo windows, but only ~8 do not overlap one another; read the percentile as rough.
- Informative only if the placebo band's half-width is under 1 (a φ of 1 would lie outside it).
  Otherwise STOP for that firm.

**Secondary, labelled as such.** The same J at the clawback announcement, **2021-06-01**, against
placebo dates 2019-01-08 → 2021-05-18 (windows wholly before it), same samples, same rules. Offers were
capped at €180.30 until 2021-07-06 (CLAUDE.md trap), which applies to the actual window and to the
placebos alike. No dose for it.

**Checks (same J, same placebo scheme, firm rows only; reported in `_checks.csv`).**
(a) `ocf` read at the fixed quantiles 20% and 50% of offered volume instead of `cf_s`;
(b) benchmark `λ*90s`; (c) benchmark without storage (`cost_nostorage`); (d) the read point net of the
day's bilateral contracts (`ocf_day` of `water_value_forward_check.py`; undefined on days the contracts take
all the expected water, which are left out); (e) y clipped to [ln 0.2, ln 5]; (f) leave-one-unit-out for
each firm's J (the range). A conclusion counts as robust only if (a), (b), (c) and (e) leave J's
position relative to the band unchanged.

**Stops.** (1) No usable placebo band for a firm (under 3 units on fewer than 200 placebo dates):
STOP for that firm. (2) If the pooled ratio has a pre-trend that the placebo band absorbs (band
half-width above 0.544 pooled): STOP for the whole test. (3) A result is never called a finding from
one firm with fewer than 5 units.

**What the number can and cannot say (fixed in advance).**
- Few firms: 4 clusters at most, 3 to 7 units each. The placebo band is the inference; there are no
  standard errors on J, and the 273 placebo windows overlap, so about 20 are independent.
- λ* is built from OMIP forwards that may have priced the cap before 15 June (public reporting dates the Commission's
  approval of the Iberian mechanism to 8 June 2022, not checked here). A flat ratio therefore says the offer
  followed λ*, not that hydro "ignored" the cap.
- It cannot say hydro firms priced off gas or exercised market power. It says only whether the offer,
  relative to a price-taking benchmark, moved at the date, and by how much, firm by firm.
- A dose coefficient is one episode with the subsidy path collinear with the winter gas-price hump; the
  gas-controlled version and the shifted-window placebo are the only guards.

## 2. Results (run 2026-11-05)

`.venv/bin/python scripts/analysis/gas_cap_hydro_link.py` (3.5 minutes). Panel: 52,231 unit-days,
39 units, 2019-01 → 2025-09. In the cap windows 7.8% of eligible unit-days have `ocf` at or below €1 and
drop out of y.

**No rule in §1 was changed after seeing results.** Four things were added or turned out differently, all
marked: (i) the sample counts in §1 came from the flags alone; the €1 rule shrinks them (below);
(ii) the dose keeps each unit's longest `cab` spell inside the window, a detail §1 left open; (iii) the dose
placebo windows use their own window's gas price as the control and move only the subsidy hump; (iv) the
**post-hoc** items, each labelled: the capacity-weighted band, the day-one statistic, and the unit-level
table. The post-hoc ones are not part of the pre-written test and are read as hints.

**Ownership.** The only eligible unit split between groups in the windows is `ADOURO` (EDP 40% / Movhera
60%, 2020-12-17 → 2021-09-08, 262 unit-days), which touches only the clawback window; there it counts as
Movhera's (the larger share), so EDP's clawback row leaves it out. No split unit in the cap windows.

### 2.1 Who is in the sample

| firm | units in the cap windows | placebo dates with ≥ 3 units | status |
|---|---|---|---|
| EDP | 5: ACAVADO, ALIMA, GUADIA, MONDEGO, HCHI | 273 of 273 | read |
| Iberdrola | 7: DUER, EBRA, IBEVD14, JUCA, SIL, TAJO, TAMEGA | 273 of 273 | read |
| Endesa | 1: EBRFEN | 109 | **STOP** |
| Naturgy | 3: UFGC, UFMI, UFTA | 19 | **STOP** |
| Movhera, Ignis, Repsol, Acciona | 1 each | — | in "all eligible" only |
| all eligible | 20 | 273 | read |

- EDP loses TEMON and ADOURO: in summer 2022 their `cf_s` sits at its 0.01 floor (the drought), below their
  zero-priced share (2–4%), so the read point is a €0 step and `ocf` ≤ €1.
- **Endesa**: only EBRFEN offers on most days. SBEU offered on 8 days of June 2022, TEES on 2, TERE on none:
  the rest of its hydro is not offered in the day-ahead auction (as in `rq-water-value-forward.md` §5.6).
- **Naturgy**: UFTA offers 56–77% of its volume at or below €1 in most months before May 2022, so the flag
  removes it and two units are left on most placebo dates.

### 2.2 The cap start, 2022-06-15: J against placebo dates (the pre-written test)

J = median over units of the change in mean y (offer over λ*, in logs), 7 days before against 7 days from.
Placebo: 273 dates, 2021-09-08 → 2022-06-07. Thermal declared cost, for scale: J = −0.544 (placebo band ±0.12);
full pass-through would give −0.721.

| firm | units | unit-days | J, offer / λ* | placebo 2.5 / 97.5% | rank of true date | two-sided share | J, offer alone | J, λ* alone |
|---|---|---|---|---|---|---|---|---|
| EDP | 5 | 69 | **−0.102** | −0.311 / +0.280 | 8th pct | 0.21 | −0.159 | −0.057 |
| Iberdrola | 7 | 98 | **−0.075** | −0.162 / +0.206 | 11th pct | 0.33 | −0.127 | −0.054 |
| all eligible | 20 | 278 | −0.061 | −0.120 / +0.193 | 14th pct | 0.35 | −0.127 | −0.056 |
| EDP − Iberdrola | | | −0.027 | −0.357 / +0.304 | | 0.60 | | |
| Endesa, Naturgy | | | STOP (rule 1) | | | | | |

- **Rule outcome: inside the band for both firms, and for the contrast.** Both bands are informative
  (half-widths 0.30 and 0.18, under 0.544), and **a thermal-sized fall (−0.544) lies far outside both**. The
  measured J is 14% (EDP) and 10% (Iberdrola) of a full thermal-style fall. The pooled row passes the stop
  test (half-width 0.16).
- **Checks, all unchanged in position for EDP and Iberdrola** (J, EDP / Iberdrola): offer read at 20% of
  volume −0.049 / −0.075, at 50% −0.026 / −0.015; λ*90s −0.178 / −0.138; λ* without storage −0.105 / −0.075;
  net of the day's bilateral contracts −0.075 / −0.075; y clipped −0.102 / −0.075; leaving out each unit in
  turn: EDP −0.102 to −0.087, Iberdrola −0.152 to −0.055. The pooled row moves to "below band" under λ*90s
  (−0.148 against −0.132), so the pooled number is not robust by the §1 rule; the firm rows are.
- The secondary date, **the clawback announcement 2021-06-01** (placebo 2019-01-08 → 2021-05-18): EDP −0.037
  (5 units, band −0.30 / +0.35), Iberdrola +0.007 (5 units, −0.11 / +0.15), Endesa −0.035 (4 units, not a
  finding), all eligible −0.026, EDP − Iberdrola −0.043. All inside. Nothing at that date in any firm.

### 2.3 What the days around the cap show (descriptive)

Median offer, λ* and their ratio, EDP | Iberdrola:

| date | EDP offer | EDP λ* | EDP ratio | Iberdrola offer | Iberdrola λ* | Iberdrola ratio |
|---|---|---|---|---|---|---|
| 8 Jun | 219 | 222 | 0.99 | 259 | 220 | 1.17 |
| 10 Jun | 216 | 201 | 1.08 | 237 | 193 | 1.18 |
| 12 Jun | 221 | 196 | 1.19 | 237 | 174 | 1.31 |
| 14 Jun | 239 | 178 | **1.36** | 237 | 171 | **1.32** |
| **15 Jun** | **182** | 166 | **1.10** | **167** | 164 | **0.97** |
| 18 Jun | 173 | 189 | 0.92 | 167 | 188 | 0.86 |
| 22 Jun | 173 | 185 | 0.94 | 204 | 183 | 1.14 |

- **λ* fell first.** The forwards it is built from dropped about 20% between 8 and 14 June (EDP's 222 → 178, Iberdrola's
  220 → 171; public reporting dates the Commission's approval to 8 June, not checked here), while the offers did not follow: the ratio climbed to its highest point of the
  month on 14 June. **The offers dropped on 15 June itself**, by about 24% (EDP) and 30% (Iberdrola).
- So hydro caught up with the forwards on the day the cap began, not when the forwards moved. The
  pre-written 7-day statistic puts the elevated 8 – 14 June ratio in the "before" mean, which is why J is only
  −0.1.
- Monthly median ratio, EDP | Iberdrola: 2022-03 0.85 | 1.39; 04 0.89 | 0.97; 05 0.98 | 0.95; 06 1.04 | 1.14;
  07 0.96 | 0.95; 08 0.88 | 1.11; 09 0.89 | 1.18; 10 1.00 | 1.24; 11 0.77 | 1.02; 12 0.88 | 0.96. Naturgy sits at
  1.7 – 3.1 from March 2022 to May 2023 (and Endesa is too thin to read).

### 2.4 Post hoc: the one-day change, and which units moved

*Not in §1. Written after seeing §2.2 and §2.3, to ask whether the 7-day window hides a day-one fall.*

| firm | units | one-day change D−1 → D, offer / λ* | placebo 2.5 / 97.5% (269 dates) | offer alone | λ* alone |
|---|---|---|---|---|---|
| EDP | 5 | **−0.214** (1.5th pct) | −0.168 / +0.182 | −0.255 | −0.041 (inside) |
| Iberdrola | 7 | **−0.275** (1.1th pct) | −0.184 / +0.166 | −0.316 | −0.041 (inside) |
| all eligible | 20 | −0.155 (1.5th pct) | −0.126 / +0.155 | −0.197 | −0.041 (inside) |

- **On day one the offers fell below the placebo band in both firms**, λ* did not, and the two firms are
  indistinguishable. That is 30–40% of a thermal-style fall (−0.72). Caveat: 14 June is the ratio's peak
  (above), so a one-day change from it partly undoes the run-up; the early-June level is the better
  baseline, and the fall below it (ratio 0.92 – 0.97 from 18 June) is the 7-day J of −0.1.
- **Capacity-weighted J** (the second column of §1, band computed after the fact): EDP −0.140 (6.6th
  percentile, two-sided 0.12); **Iberdrola −0.225 (2.6th percentile, two-sided 0.055)**; all eligible
  −0.143 (2.2nd, 0.08). The median over units does not see it because it comes from the big units.
- **By unit, J (own-placebo two-sided share), cap start** (`gas_cap_hydro_link_units.csv`): Iberdrola DUER
  −0.275 (0.04), TAJO −0.301 (0.02), SIL −0.229 (0.18), TAMEGA −0.075, JUCA −0.030, EBRA −0.035. EDP's Spanish
  HCHI **−0.749 (0.00)**, but its Portuguese cascades ACAVADO −0.071, GUADIA −0.102, MONDEGO −0.103, ALIMA
  +0.029 (none unusual against its own placebo). Endesa EBRFEN −0.151; Naturgy UFGC −0.057, UFMI −0.048.
  Three of Iberdrola's four largest units (two of them unusual against their own placebo, 0.04 and 0.02)
  and EDP's Spanish unit moved by 0.2 – 0.75; the Portuguese cascades and the smaller Spanish units did
  not. With 20 units looked at, one or two extreme ones are expected by chance: this is a lead for a
  unit-level design, not a result.

### 2.5 Dose: does the ratio move with the day's subsidy (pre-written)

φ = change in offer/λ* (logs) per unit of the log fall in a gas plant's cost from the subsidy, window
2022-06-01 → 2023-03-31 (that fall has median −0.65 and minimum −1.39 over the 256 days 2022-06-15 → 2023-02-25, so
φ = 0.15 means a 10% fall in the ratio at the median day). φ = 1 would be a thermal-style response. Placebo:
239 shifted windows (|k| ≥ 245 days), about 8 independent. Standard error clustered by week, indicative.

| firm | units | unit-days | φ, unit effects | placebo 2.5 / 97.5% | φ, + gas price | placebo 2.5 / 97.5% |
|---|---|---|---|---|---|---|
| EDP | 7 | 1,677 | 0.052 (0.076), 75th pct, inside | −0.39 / +0.30 | **0.447 (0.171), 99.6th pct, above** | −0.39 / +0.28 |
| Iberdrola | 9 | 2,352 | 0.171 (0.046), 78th pct, inside | −0.39 / +0.34 | 0.157 (0.141), 82nd pct, inside | −0.21 / +0.25 |
| all eligible | 27 | 6,261 | 0.145 (0.043), 85th pct, inside | −0.32 / +0.32 | 0.223 (0.100), 97th pct, inside | −0.15 / +0.30 |
| Endesa | 3 | 300 | 0.23 / 0.51 | | | not a finding (3 units) |
| Naturgy | 4 | 1,085 | 0.43 / 0.39 | | | STOP without gas control (band ±1.2); not a finding (4 units) |

- **No stable dose response.** Iberdrola and the pooled row are inside the placebo band in both
  specifications, at 0.15 – 0.22: a fifth of a thermal-style response at most.
- **EDP's answer depends on the control** (0.05 without, 0.45 with, the only cell above its band): one
  specification of four for the two firms, so not read as evidence that EDP follows the gas shifter more
  than Iberdrola. If anything it is the opposite of the premise (Iberdrola the one who tracks it).

### 2.6 What this can and cannot say

- Few firms: two informative rows, 5 and 7 units. The placebo band is the only inference; the 273
  placebo windows overlap, so about 20 are independent, and a rank of 8th or 11th percentile is not
  distinguishable from the middle.
- λ* moved before the cap (above), so "the ratio did not move" means offers caught up with the forwards
  within the week, not that hydro ignored the cap. The test cannot say what the offers followed: the gas
  cost, the lower expected price, or the new rule itself.
- Day-one and unit-level results are post hoc, found after the registered test came out inside the band.
- Endesa and Naturgy, two of the four large hydro firms, cannot be read: they do not offer their water in
  the day-ahead auction on enough days, or offer it at zero.
- The dose rests on one episode in which the subsidy path and the winter gas-price hump move together.

## 3. Reading in five lines

1. **Hydro did not follow the gas plants' cost down at the cap start.** Offers relative to the price-taking
   water value moved by −0.10 (EDP) and −0.075 (Iberdrola) over the week, inside the range of ordinary weeks
   and 10 – 14% of a full thermal-style fall (−0.72); EDP and Iberdrola do not differ (−0.03).
2. **Offers did drop on the day the cap began** (post hoc: −0.21 and −0.28 in a day, below the ordinary
   range), after the forwards behind λ* had fallen the week before and the offers had not. That is hydro
   catching up with a price level the cap had already moved, not a thermal-style response to the subsidy.
3. **The firm contrast the premise asked for is not there.** Iberdrola is not distinguishable from EDP on the
   week or the day; a capacity-weighted Iberdrola fall (−0.23, two-sided 0.055) comes from its three big
   Spanish units, as does EDP's Spanish HCHI (−0.75): a lead for a unit-level look, not a firm result.
4. **No dose response to the subsidy** that survives the placebo windows and both specifications
   (0.15 – 0.22 against 1 for thermal); EDP's 0.45 appears only with the gas control.
5. **Endesa and Naturgy cannot be read** (one and three usable units, 109 and 19 placebo dates); the
   clawback date shows nothing in any firm.

## 4. Next (each needs a yes)

- Unit-level version for the lead in §2.4: Spanish basin units against Portuguese cascades at the cap
  start, with the rules written first (units, the share of the fall that precedes the ratio's spike, one
  baseline); it would treat DUER, TAJO, SIL and HCHI as a set fixed by the §2.4 look, which is a selection to
  state.
- Fix the baseline problem by a window that leaves out the days between the Commission's approval (8 June)
  and the start (D−7 → D−1 swept by the forward fall), as a new pre-written variant.
- Endesa and Naturgy would need the read point net of contracts on days they do offer, which the zero-priced
  share and the missing offers make thin; not worth it unless a quantity design is wanted for them.
