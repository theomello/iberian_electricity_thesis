# Regional holidays: running note

Design: `docs/specs/2026-10-20-regional-holidays-design.md`. Plan for step 1:
`docs/plans/2026-10-20-regional-holidays-step1.md`.

## Step 1: the holiday table and each firm's exposure (2026-10-20)

Scripts: `fetch/fetch_holidays.py` (+ `lib/holidays.py`, `qa/check_holidays.py`),
`fetch/fetch_ree_regional_demand.py`, `build/build_holiday_exposure.py`
(+ `qa/check_holiday_exposure.py`). Outputs in `outputs/tables/holiday_exposure*.csv` and
`holiday_retail_days.parquet`. Logs `.superpowers/sdd/2026-10-20-regional-holidays-step1/`.
Descriptive only: no β.

**In one line.** The stop rule passes. A holiday visibly lowers the retail purchases of the
firms whose customers live there. When all of mainland Spain is off, Endesa and Iberdrola each
buy about 1,150 MW less, Naturgy 410 and EDP nothing. On Catalonia's own holidays Endesa buys
414 MW less, Iberdrola 204 and Naturgy 99. On Portugal's, EDP buys 261 MW less. The all-firm
total matches REE's demand on the national days to 1%. Single regions are noisier: about
±200 MW for the whole market, ±50–100 for one firm.

### The data built

- **Holidays, 2018–2026**: 2,134 rows, one per date and area, for the 17 regions, Ceuta,
  Melilla and Portugal. Spain from the nine BOE resolutions (XML), Portugal by law. Each mainland
  region has 12–13 holidays a year; the Canary Islands 11 (each island's own day is in the
  footnotes, left out). All 17 checks pass.
- **Regional demand, monthly**: REE's REData, 2018-01 → 2026-08. The 15 mainland regions sum to
  the peninsular total to 0.00% in every year 2018–2025. 2026 is provisional (5.8% above).
  Daily or hourly demand by region does not exist on REData.
- **Retail schedules by firm and day**, 2018-01 → 2026-05, from PDBF (the daily operating
  schedule), auction purchases **plus** bilateral contracts. Regulated suppliers (Energía XXI,
  Curenergía, …) apart, as `PASS`.

### Three things the build taught

1. **The whole schedule, not auction purchases.** On the Diada 2024 Endesa's auction purchases
   fell 674 MW, but its whole schedule only 457 (−6%). Iberdrola's auction purchases *rose* 287
   MW while its schedule fell 210: it moves volume between its own-retail contracts and the
   auction. The spec's example used the auction figure; corrected there.
2. **Regions that share a holiday cannot be told apart.** Asturias and Extremadura are only
   ever off together (8 September), Murcia and La Rioja (9 June), Aragón and Castilla y León
   (23 April). Estimated apart they took offsetting values (La Rioja +831 MW against about 170
   MW of demand, Murcia −365). They are now merged.
3. **Days when most of Spain is off need their own term.** 41 weekdays have four or more
   mainland regions off: the Spain-only national days (6 January, 12 October, 6 December) and
   Holy Thursday, San José and the like. Spread over the regional coefficients they distorted
   all of them. One term (`ES`), scaled by the share of mainland demand that is off, now takes
   them. Regional exposures come only from days with at most three regions off.

### Exposures, MW less bought on the area's holiday (standard error)

Full sample, weekdays, 20 December – 7 January left out. `ES` = all of mainland Spain off.
Placebo areas (islands, Ceuta, Melilla) are separate electrical systems: their load is not
bought in MIBEL.

| group | ES | PT | Catalonia | Madrid | Castilla-La Mancha | Valencia | Andalusia | Aragón + C. y León | Galicia |
|---|---|---|---|---|---|---|---|---|---|
| all retail | **4,125** (218) | **562** (180) | **1,090** (163) | **838** (191) | 315 (191) | 159 (185) | 461 (317) | **289** (128) | −145 (220) |
| Endesa | **1,147** (66) | **142** (43) | **414** (63) | **302** (90) | 100 (55) | 70 (56) | 59 (79) | 123 (65) | −92 (51) |
| Iberdrola | **1,153** (54) | **101** (48) | **204** (43) | 108 (129) | **95** (46) | **128** (37) | 4 (74) | 84 (45) | 32 (69) |
| Naturgy | **410** (37) | −24 (16) | **99** (21) | **68** (23) | **60** (16) | 18 (20) | 18 (22) | 26 (16) | 18 (19) |
| EDP | 23 (22) | **261** (13) | 26 (20) | 68 (38) | −56 (20) | −7 (32) | 127 (87) | **57** (19) | 13 (27) |
| TotalEnergies | **170** (21) | 12 (24) | | | | 36 (17) | | | |
| Repsol | **60** (11) | 3 (11) | 13 (12) | | −8 (12) | 6 (9) | −1 (7) | 5 (6) | −6 (11) |
| regulated (`PASS`) | −6 (33) | −24 (23) | 60 (30) | −42 (38) | 21 (27) | 2 (26) | −27 (61) | 55 (34) | −96 (48) |

Bold: t ≥ 2. Holiday days behind each term: ES 41, PT 29, Catalonia 12, Madrid 5, Castilla-La
Mancha 13, Valencia 14, Andalusia 8, Aragón + Castilla y León 8, Galicia 9.

**Placebos pass**: all retail −226 (Balearics, se 364), +158 (Canaries, 307), −131 (Ceuta,
281), −205 (Melilla, 315); Endesa −34, +12, −54, −28 (se 103–120). None has t ≥ 2. They also
show the noise floor for one area: about ±200 MW for all retail.

**Size check**: mainland demand falls 14.4% on the Spain-only national days (11 days, REE's
realtime series). Times the mainland's mean demand that predicts 4,180 MW; all retail buys
4,125 MW less (ratio **0.99**). By region the ratio is 0.67 (Andalusia), 0.69 (Aragón + C. y
León), 0.73 (Asturias + Extremadura), 1.17 (Murcia + La Rioja), 1.39 (Catalonia), 1.52
(Castilla-La Mancha), 1.73 (Madrid), 0.34 (Valencia), and negative for Galicia and Cantabria.
Retail is not all load (direct consumers buy apart), so ratios under 1 are expected; above 1
and negative ones are noise or confounding.

**Leave one year out** (range over the years left out): Endesa ES 1,099–1,199, Catalonia
372–468, PT 118–167; Iberdrola ES 1,117–1,185, Catalonia 182–231, Valencia 115–147; Naturgy ES
349–434; EDP PT 253–268. Stable. Madrid rests on 5 days, and is estimated only when no year
holding one of them is left out: thin.

**By year**, only the ES term can be estimated (each region has under five local days a
year): Endesa 874–1,702 MW, Iberdrola 967–1,643, Naturgy 271–765 (765 in 2018, when its
retail was 3.5 GW against 1.9–2.3 after).

### Against the old distribution areas

| firm | where its customers should be | holds | does not |
|---|---|---|---|
| Endesa | Catalonia, Aragón, Andalusia, Badajoz | Catalonia (414), Aragón + C. y León (123, t 1.9) | Andalusia (59) |
| Iberdrola | Valencia, Castilla-La Mancha, Madrid, Basque Country, Murcia | Valencia (128), Castilla-La Mancha (95) | Madrid (108, se 129); Basque Country not estimable (2 days) |
| Naturgy | Galicia, Madrid, Castilla-La Mancha | Madrid (68), Castilla-La Mancha (60) | Galicia (18) |
| EDP | Portugal (Asturias until 2020-11) | Portugal (261) | |
| Repsol | Cantabria (ex-Viesgo) | | Cantabria (−28, se 47) |

So the exposures follow the old areas where a region has its own well-separated days
(Catalonia, Valencia, Portugal), and not where it has few (Andalusia 8 days, Galicia 9).

### Problems left

- **Three cells are significantly negative**: Iberdrola in Cantabria −97 (35), EDP in
  Castilla-La Mancha −56 (20), Repsol in the Balearics −33 (14). Castilla-La Mancha's Corpus
  Christi is also Portugal's, so EDP's Portuguese drop is split between the two (off together
  on 6 of its 13 local days, below the 70% merge bar). Cantabria's 28 July follows Santiago (25
  July), a holiday in Galicia, the Basque Country and Navarra. Both are the splitting problem of
  point 2, at a smaller scale.
- **TotalEnergies' Spanish retail is not visible before December 2023.** It bought EDP
  Comercializadora on 2020-12-01, but its own retail units (`TOTRM01` …) appear only from
  2023-12; EDP Comercializadora's purchases before then are not under any unit mapped to it
  (`EDPCOX`, its only purchase unit, is 30 GWh in all). EDP's Spanish retail unit `HCGC01`
  falls from about 300 MW (2020) to 100 (2024). Where TotalEnergies' customers were bought in
  2021–2023 is open, and it bears on EDP's and TotalEnergies' n in those years, not only here.
- **Regional exposures are averages over 2018–2026.** Per year they cannot be estimated.

### What this means for step 2

- **Endesa's dose comes mostly from the ES days and Catalonia**: about 1,150 MW on each of the
  41 multi-region days (scaled by their share), 414 on each of 12 Catalan days, 142 on each of 29
  Portuguese days.
- **On the ES days Endesa and Iberdrola get the same MW.** The contrast within the hour then
  comes from Naturgy (410), EDP (about zero), the smaller firms, and from the slopes of their
  residual demand. On Catalan days Endesa gets twice Iberdrola's dose and four times Naturgy's.
  On Portuguese days EDP is the treated firm.
- **The dose is built from these exposures, as the spec says**, with the ES term replacing the
  spec's "H = 1 for every Spanish region at once": dose = Σ local e_fr · H + e_f,ES · (share of
  mainland demand off) + e_f,PT · H_PT, times the hourly profile, exposures leaving the year out.

## Step 2: the dose, the first stage and the power (2026-10-20) — STOP

`analysis/holiday_first_stage.py --dose / --first-stage / --power` (+ `qa/check_holiday_dose.py`,
`qa/check_holiday_first_stage.py`), `analysis/holiday_schedule_legs.py`. Outputs
`outputs/tables/holiday_dose.parquet`, `holiday_profile.csv`, `holiday_first_stage.csv`,
`holiday_power.csv`, `holiday_schedule_legs.csv`. Logs
`.superpowers/sdd/2026-10-20-regional-holidays-step2/`. The outcome's response to the dose was
not estimated.

**In one line.** Both stop rules trigger. A firm's holiday dose does not move its exposed position:
when its customers buy less, it cuts the generation it supplies them through bilateral contracts
by about as much, and sells nothing extra in the auction. So the holiday is not an instrument for
the stake, and Endesa's β⁻ cannot be detected (smallest detectable β⁻ 27 on thermal offers, 297 on
hydro, against Nash = 1).

### The dose

Step 1's exposures leaving the day's year out, times an hourly profile from the 11 Spain-only
national days (the mainland drop runs from 0.5 GW at night to 8.4 GW at midday; profile 0.11–2.0,
mean 1). Weekday holidays only. Endesa has a dose on 147 days, Iberdrola 140, EDP 130. All 10
checks pass.

### First stage

Coefficient (F, date clusters; week clusters agree within 15%):

| sample | stake on dose | pooled | Endesa |
|---|---|---|---|
| hydro owners, firm × hour, at cost (`hcompcost`) | n (GW) on dose (GW) | −0.12 (1.4) | +0.05 (0.4) |
| | Zb on dose / \|RD′\| | −0.19 (3.5) | −0.23 (3.5) |
| five firms, firm × hour, actual (`firm_x`) | n on dose | +0.04 (0.1) | +0.14 (1.2) |
| | X on dose / \|RD′\| | +0.06 (0.1) | −0.65 (22.1) |
| fixed-step hydro rows (step 3's sample) | Zb on dose / \|RD′\| | −0.06 (0.1) | +0.04 (0.1) |
| thermal offer panel | X on dose (GW) | +0.51 (0.7) | +0.80 (2.2) |

Expected: about +1 on n (a buyer that buys a MW less is a MW longer). Endesa's F of 22 on its
actual X is the wrong sign, and its n does not move (+0.14, F 1.2): with the slope in both X and
the instrument, the slope's own variation carries it. Not a first stage.

### Why: the legs of the schedule

MW per MW of dose, five firms, firm-days, date and firm × year effects, date clusters:

| leg | auction | bilateral contracts |
|---|---|---|
| retail purchases (less bought) | +0.29 (0.13) | **+0.69** (0.14) |
| generation sales | +0.02 (0.19) | **−0.54** (0.13) |
| net position | **+0.27** (0.17) | |

When a firm's customers take a holiday, about two thirds of their lower purchases fall on its
bilateral contracts with its own retailer, and the generation it sells under those contracts falls
by about half a MW per MW. It does not offer the freed generation in the auction. Its net position
in the auction rises by about a quarter of the dose, imprecisely.

This is the third time the same behaviour appears: reactors' owners keep their own retail covered
when a reactor is out (`rq-nuclear-cuts.md` §6.2), Iberdrola moves hydro between its own-retail
contracts and the auction (`rq-fixed-step.md`), and now generation follows own retail load. The
vertical-integration mechanism the design assumed (Bushnell, Mansur & Saravia 2008: retail bought
at the spot price offsets the gain from a higher price) does not operate here, because retail is
covered physically by own generation, and adjusted by quantity.

### What the result is good for

The design fails as an instrument for the stake. It may work as a test on quantities. With the
date effects in, the market price is common to all firms, so a price-taker's generation should
not depend on its own customers' demand. A firm that cuts output when its own customers buy less
is doing one of two things:
- **exercising market power**: a firm that buys less gains more from a high price and withholds
  (Cournot). The cut should then scale with 1/|RD′| and stay below one;
- **balancing its book by quantity**: matching own generation to own load, whatever the slope.

The holiday dose separates them with the same slope test that settled the nuclear cuts
(`rq-nuclear-cuts.md` §6.2). Not run; a design question for the user.

## The quantity test, step 1 (2026-10-20): CONTINUE

Spec `docs/specs/2026-10-20-holiday-quantity-test-design.md`; plan
`docs/plans/2026-10-20-holiday-quantity-test.md`; script `analysis/holiday_quantity_test.py`
(`--panel`, `--test --step 1`); outputs `holiday_quantity_panel.parquet` (gitignored),
`holiday_quantity_step1.csv`.

**The question.** Firms cut the output they sell their own customers on those customers'
holidays. Market power predicts the cut follows the dose's price effect P = dose / |RD′| (larger
in steep hours); a rule matching own generation to own load predicts it follows the dose itself.

**The panel.** The five firms by date and hour, weekdays 2019-01 → 2025-09: 211,320 firm-hours,
13,608 with a dose (12,760 with a slope). Its daily means reproduce step 2's legs: generation sold
bilaterally −0.57 per MW of dose (se 0.16; step 2 −0.54), retail bought bilaterally +0.72 (0.17;
+0.69).

**Hourly, with date × hour and firm × month effects** (MW per MW of dose; 1/|RD′| as a control):

| outcome | per MW of dose | se |
|---|---|---|
| retail purchases, both legs (first stage) | +0.53 | 0.06 |
| … in the auction | +0.07 | 0.10 |
| … bilateral | +0.46 | 0.10 |
| generation, both legs | **−0.26** | 0.10 |
| … in the auction | +0.12 | 0.14 |
| … bilateral | −0.37 | 0.10 |

**The firm's own offer slope near the price** (s, its sell offers within ±€5 per €/MWh): 72 MW
per €/MWh, dose-weighted. It is zero in 30% of firm-hours: at prices above €5 Endesa, Iberdrola,
Naturgy and Repsol often have nothing on offer within €5 of the price (31–42% of hours; EDP 4%).
A price-taker with nothing near the price would not change its output for a €1 markup.

**Power.** Computed without forming the test's coefficient: se(b_P) under b_P = 0 is 13.9 MW per
€/MWh on total generation, so the smallest detectable β is **0.54** (bilateral 0.37, auction 0.70).
P on dosed hours: median €0.21/MWh, 90th percentile €2.51.

**Stop rule: CONTINUE** (generation responds, t −2.6; MDE 0.54 < 1).

**A refinement for step 2, beside the spec's test.** Since s varies by hour and is zero in many,
Nash predicts −s · P hour by hour rather than −s̄ · P on average. Regressing on s · P gives β
directly (Nash −1, book balancing 0).
