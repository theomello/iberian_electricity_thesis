# Near-misses of the minimum-income condition: β in the intraday auctions

**Status: step 1 run 2026-10-20: STOP (`notes/rq-mic-near-miss.md`).** Acceptance jumps 0 → 0.89
at the threshold and a withdrawn plant sells about 90 MW more intraday, but the density of r_A
(log ratio 0.77) and the declared v (+€17) jump there. Not days when the condition cannot bind
(it can on 99%), nor an overstated re-clearing. On single-plant days (304) v balances but the
density still jumps (3×, p 8·10⁻⁶) and the intraday first stage is 22 MW (se 16). **Stopped at
step 1**; the design does not go on to step 2. Window 2019-01-01 → 2025-03-18
(2018 moved to step 5: the re-clearing curves start in 2019). The second of four
designs chosen on 2026-10-20 for sharper identification. The first, regional holidays,
stopped at its first stage (`notes/rq-regional-holidays.md`): firms absorbed the shock by
quantity in bilateral contracts. Framework:
[`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md). It reuses
the intraday panels of the intraday surprise design (`notes/rq-intraday-surprise.md`,
`analysis/intraday_firm_panel.py`).

**In one example.** On 3 January 2019 Naturgy declared that its combined cycle Sagunto 1
(417 MW) needed to earn €68.42/MWh on average over the day, and San Roque 1 (390 MW)
€68.00. At that day's prices, Sagunto 1's offered output would have averaged €0.06/MWh less
than it asked, so the clearing algorithm withdrew it for the whole day. San Roque 1 cleared
its condition by €0.23 and ran 20 hours. The firm set both conditions at noon the day before
without knowing the prices, so close to the threshold which side a plant lands on is luck.
A withdrawn plant is idle but still available: its owner can sell its output in the
intraday auctions that evening and the next day. If it does, the owner becomes a larger
seller there. A price-taker then offers its other plants as before. A firm with market power
raises their offers, because a higher intraday price now pays on more MW.

---

## 1. Why this design

- **The shock happens inside the auction.** The holiday shock was absorbed before it reached
  the auction: retail load fell, and the firm cut the generation it sells its own retailer
  through bilateral contracts. A withdrawal is the auction's own outcome, so it reaches the
  firm's auction position by construction.
- **The firm knows it before every intraday session** (the day-ahead result is published
  around 13:00 on D-1) **but did not choose it.** Near the threshold, the clearing algorithm
  draws it. The earlier intraday instrument (REE's wind forecast error) failed because firms
  partly knew it at the day-ahead (`rq-intraday-surprise.md` §4). This one cannot be known at
  the day-ahead: it is the day-ahead's result.
- **Intraday positions are small and slopes steep**: tens of MW a session, 110–200 MW per
  €/MWh against about 500 at the day-ahead. A plant of 240 MW entering an intraday session
  moves its owner's stake X = n/|RD′| by 1.2–2.2 €/MWh, more than a holiday moved it in the
  day-ahead (1.3 at best).
- **It recurs thousands of times** (§2), mostly at the four large firms.

**The condition.** Per session s, the firm's first-order condition is the framework's
p_s − c = β · n_s / |RD′_s|, with n_s the firm's net sales in that session (as in
`intraday_firm_panel.py`). Ito & Reguant (2016, AER) show firms with market power use the
sequence of day-ahead and intraday markets strategically; here the sequence supplies the
instrument.

## 2. What the data show (throwaway count, 2026-10-20)

Every sell unit-day in `cab` declaring a minimum-income condition (fixed term F > 0 or
variable term v > 0), 2018-01-01 → 2025-03-18: **169,233 unit-days on 131 units.** For each,
the margin at the published prices,

    r = (Σ_h p_h q_h − F) / Σ_h q_h − v        (€/MWh)

with q_h the unit's offered sell MW at or below the hour's price (Portuguese price for
Portuguese units). r ≥ 0 means the offered output would have met the condition.

| r (€/MWh) | unit-days | cleared in any hour | cleared in ≥ 4 hours |
|---|---|---|---|
| −5 to −2 | 7,694 | 9.9% | 0.0% |
| −2 to −1 | 2,509 | 15.6% | 0.1% |
| −1 to −0.5 | 1,294 | 15.8% | 0.0% |
| −0.5 to 0 | 1,266 | 18.1% | 1.3% |
| 0 to 0.5 | 2,088 | 64.7% | 56.8% |
| 0.5 to 1 | 1,665 | 84.0% | 80.1% |
| 1 to 2 | 3,224 | 91.2% | 89.5% |
| 2 to 5 | 9,064 | 97.8% | 97.1% |

- **Within €2/MWh of the threshold: 12,046 unit-days on 2,097 days**, 85% at the large firms
  (Naturgy 3,823, EDP 2,545, Endesa 2,067, Iberdrola 1,284). They thin out over time: 3,255 in
  2019, 1,151 in 2021, 618 in 2024. In the window of the intraday panels (2019-01-01 →
  2024-06-13): 8,664 unit-days on 1,600 days, 4,940 firm-days, **1,971 of them with more than
  one near-miss unit** (often units of one plant, as Sagunto 1 and 2 on 3 January 2019).
- **A withdrawn plant would have produced a median 236 MW** over the day (p25 189, p75 279).

Three design rules follow:

1. **Count a plant as accepted only if it clears in at least 4 hours.** Below the threshold,
   plants that clear do so in 1–3 hours only (452, 99 and 256 unit-days within €2): a withdrawn
   plant ramped down at the start of the day (OMIE's scheduled-stop condition, to confirm in
   OMIE's rules). With that, the left side is sharp.
2. **Measure the margin as if the plant were accepted (r_A).** The remaining fuzziness is to
   the right of zero: 43% of plants with r in [0, 0.5) are withdrawn. That is the plant's own
   price effect. Withdrawing 240 MW raises the price, so a withdrawn plant's margin at the
   final prices overstates what it would have earned had it run. Evaluated at the prices with
   the plant in, those plants move left of zero. The design should then be close to sharp, and
   the running variable no longer depends on the treatment.
3. **Several near-misses per firm-day are common**, so the treatment is defined per firm-day
   (§3.4).

## 3. The design

### 3.1 The running variable

r_A for every declaring unit-day: the margin above, at the prices that would clear **with
the unit's offers in**.
- **Accepted units**: the published prices; r_A = r.
- **Withdrawn units**: re-clear each hour on the effective curve (`analysis/step_curves.py`,
  `effective` and `reclear`: accepted rows on the accepted side of the price, offered rows
  beyond it) with the unit's offered sell steps added, and evaluate r at the new prices and
  the unit's offered MW at those prices.
- Other units with a condition keep their status: the re-clearing is first-order, not
  OMIE's joint search.
- **The formula and the scheduled stop come from OMIE's market rules**, not from the table
  above: confirm that the condition is Σ p·q ≥ F + v·Σq over the hours cleared, and how many
  hours a scheduled stop may clear.

### 3.2 What a withdrawn plant does (describe before estimating)

Three things can happen to a withdrawn plant between the day-ahead result and delivery:
- **REE schedules it for grid security** (technical constraints). It then runs, paid as bid,
  outside the intraday price. OMIE publishes the schedule after that step as `pdvd`
  (*Programa Diario Viable Definitivo*, the viable day-ahead schedule), monthly zips from
  2018-01, token-free; not yet fetched.
- **Its owner sells it in the intraday auctions**, possibly with a minimum-income condition
  again (allowed in MIBEL's intraday sessions).
- **It stays idle.**

Shares of each, by year and firm, on either side of the threshold.

### 3.3 The first stage

The owner's intraday net sales n_s and stake X_s = n_s / |RD′_s| per session, date and period,
from `intraday_firm_panel.parquet` (exposed position, ownership by date and share). Expected:
both jump up at r_A = 0 from the accepted side to the withdrawn side. Also the firm-day sum of
n over sessions, as the plainest first stage.

### 3.4 The outcomes and the estimate

**Outcome:** the sell offers of the owner's *other* dispatchable units in each intraday
session (storage hydro, pumped-storage turbines, combined cycles, coal: leg D's units),
excluding every near-miss unit of that firm-day. The offer price at 25% and 50% of the unit's
offered volume (`intraday_offer_panel.parquet`, `o25`, `o50`), minus its cost
(`marginal_cost_capped_bid_eur_mwh` for gas and coal, λ*30s from `hydro_cost_daily` for
hydro). **Rivals' units are in the same regression**, so the comparison is within the hour:
under price-taking the owner's other units respond to the withdrawal like rivals' units do.

**Estimate:** per unit u, session s, date d, period h,

    y_usdh = β · X_f(u)sdh + g_f(r_A) + date×session×period + unit×month + e

- A unit's firm is its largest owner that day (`majority_group`), the near-miss unit's too.
- Instrument: W_fd = 1[the firm's near-miss unit is withdrawn, r_A < 0], zero for firms
  without a near-miss that day.
- Sample: every leg-D unit on dates with at least one near-miss firm-day.
- g_f: local linear in r_A on each side, for firm-days with a near-miss; zero otherwise.
  Triangular kernel, bandwidth €2/MWh.
- **Main sample: firm-days with exactly one near-miss unit** within the bandwidth. Firm-days
  with several enter in a check, with the instrument as the MW share of near-miss units
  withdrawn.
- Errors clustered by date; by week as a check.
- **Reduced form first** (does y jump?), then β by instrumental variables.

### 3.5 The test

- **Price-taking** predicts no jump in the owner's other offers beyond rivals'. **Nash**
  predicts the full β = 1 response to ΔX. With 240 MW sold intraday and slopes of 110–200,
  Nash means 1.2–2.2 €/MWh on the owner's other offers, scaled down by the share of withdrawn
  plants that are actually sold intraday.
- **A test between models** (Duarte, Magnolfi, Sølvsten & Sullivan 2024, *Quantitative
  Economics*): a Rivers–Vuong test of price-taking against Nash with W as instrument, with
  their diagnostic for whether it is strong enough to tell them apart. Reported beside the
  Anderson–Rubin set on β.
- **By firm** where the first stage allows: Naturgy, EDP, Endesa, Iberdrola.
- **No simulated price-takers exist for the intraday auctions.** The within-hour comparison
  with rivals and the day-ahead placebo (§5) stand in for them. Build them only if the
  reduced form finds a jump.

## 4. Steps, each with a stop rule (each run needs a yes first)

1. **Running variable and description.** Fetch `pdvd`; build r_A for every declaring
   unit-day, 2018-01-01 → 2025-03-18; §3.2's description. Checks at r_A = 0: the jump in the
   accepted share; the density of r_A (Cattaneo, Jansson & Ma 2020); balance of pre-set
   covariates: v, F, REE's D-1 forecasts of demand, wind and solar (ESIOS 1775, 1777, 1779,
   from 2019), the gas price known at the bid (MIBGAS, D-2), whether the unit ran on D-1, day
   of week. *Stop* if the jump in the accepted share is below 0.5; if the density test
   rejects at 1%; if two or more covariates jump at 1%; or if fewer than 1,000 single-unit
   firm-days fall within €2 in 2019-01-01 → 2024-06-13.
2. **First stage and power.** §3.3. *Stop* if the firm-day F on W is below 20 for the owner's
   n and X, or if the minimum detectable β at 80% power exceeds 1 (2.80 × se under β = 0,
   from the outcome's noise only, as in the holiday step 2).
3. **Main estimate.** §3.4–3.5: reduced form, β, Rivers–Vuong, by firm.
4. **Checks** (§5).
5. **Extensions**, if power is short or the result is worth extending: 2018 and the
   European intraday auctions (2024-06-14 → 2025-03-18) by rebuilding the intraday panels
   there.

## 5. Threats and checks

- **Day-ahead placebo.** The owner's day-ahead offers for day D were submitted before the
  result. They must not jump at the threshold. Neither may the near-miss unit's own day-ahead
  offer ladder.
- **Manipulation.** Firms re-declare v almost every day. A firm that could aim at the
  threshold would leave a pile-up just above it; the density test looks for one.
- **REE's grid-security schedule** (§3.2). A withdrawn plant scheduled by REE is sold outside
  the intraday price, which weakens the first stage but not the exclusion. Report the split.
- **The withdrawal moves the market.** 240 MW out raises the day-ahead price by roughly
  €0.5/MWh (240 / 500) and changes every firm's intraday residual demand. The
  date×session×period effects absorb what is common; rivals' own X carries the rest.
- **Gas.** A withdrawn plant frees gas for its owner's other plants, a cost change that could
  look like conduct. Gas trades daily on MIBGAS, so its value should be the market price;
  check by splitting firms with large gas portfolios (Naturgy, Endesa) from the others.
- **Same site, same grid zone.** Units at the near-miss plant's site (Sagunto 3 when Sagunto 1
  is withdrawn) or in its grid zone may respond for grid reasons. Drop them as a check.
- **Bandwidth and the re-clearing error**: €1 and €3, the data-driven bandwidth of Calonico,
  Cattaneo & Titiunik as checks; a donut dropping |r_A| < €0.25.
- **Sessions**: D-1 evening sessions (1–2) against D's (3–6).
- **Windows**: the gas cap (2022-06-15 → 2023-12-31) uses the capped cost; COVID-19
  (March–June 2020) with and without; the two whole-day dropout days (2018-06-14, 2022-10-12)
  dropped.

## 6. Data

| what | source | status |
|---|---|---|
| Minimum-income terms F, v | `cab` | on disk, to 2025-03-18 |
| Day-ahead offers, cleared rows, prices | `curva_pbc_uof`, `marginalpdbc` | on disk |
| Re-clearing on the effective curve | `analysis/step_curves.py` | code on disk |
| Schedule after REE's grid-security step | OMIE `pdvd`, monthly zips from 2018-01 | to fetch; layout to check against `pdbf` |
| Intraday offers, positions, slopes | `intraday_firm_panel.parquet`, `intraday_offer_panel.parquet` | on disk, 2019-01-01 → 2024-06-13 |
| Costs | `implied_marginal_cost_daily`, `hydro_cost_daily` | on disk |
| Covariates | ESIOS 1775/1777/1779, MIBGAS | on disk |
| Ownership | `lib/unit_ownership.py` | on disk |
| OMIE's rule for the condition and the scheduled stop | OMIE market rules | to read |

## 7. Goals and limits

- **Goal:** β in the intraday auctions, from a shock firms cannot route through contracts;
  then by firm.
- **Not a goal:** whether firms hold idle plants back from the intraday auctions (Ito &
  Reguant's sequential-market question). §3.2 describes it, but it is not the test.
- **Limit:** intraday conduct only. It says nothing directly about β in the day-ahead.
- **Limit:** the condition ends on 2025-03-18, and near-misses thin out after 2020.
- **Limit:** local to days when a combined cycle sits at its threshold, which are days when
  combined cycles are near the margin.

## 8. Left to the builder

- **The offer read** (my call: `o25`/`o50` as in the earlier intraday work, for comparability;
  as a check, the price at which a unit offers a fixed level of output, its schedule plus
  intraday sales minus buy-backs, since that read does not move with the day-ahead schedule).
- **Firm-days with several near-misses** (my call: §3.4, single-unit first).
- **Hours where the effective curve misses the published price** by more than €0.50 (my call:
  leave them out of r_A, and flag the day if more than four are left out). The same for
  hours when Spain and Portugal split, where one curve cannot be re-cleared.
- Clustering: by date as the main, by week as a check.
