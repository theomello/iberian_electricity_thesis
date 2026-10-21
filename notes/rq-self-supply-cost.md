# What does self-supply cost? Running note

Design: `docs/specs/2026-10-21-self-supply-cost-design.md`. Plan:
`docs/plans/2026-10-21-self-supply-cost-step1a.md`. Script `analysis/self_supply_cost.py`
(`--build`, `--describe`), check `qa/check_self_supply_cost.py`. Outputs:
`self_supply_panel.parquet` and `self_supply_hydro_unitday.parquet` (gitignored),
`self_supply_{composition,above_cost,hydro_timing,generic,power}.csv`. Logs
`.superpowers/sdd/2026-10-21-self-supply-cost-step1a/`.

## Step 1a (2026-10-21): STOP on power, with four descriptive results

**In one line.** The firms supply their own customers with nuclear, hydro, wind and solar,
plus energy they buy and resell through "generic" units. Self-supply runs plants below cost about
as often as the same firms' auction sales do (hydro 65% against 59% of MWh; nuclear less
often, 9% against 22%), and is timed about as well, except Naturgy's hydro, which runs flat. On holidays the cut falls on hydro and wind. Pricing
it, the € test could not tell a real loss from no loss (smallest detectable effect €53 per MWh
of lost load against a reference of €17), so step 1b is not run.

**The panel.** The five firms' generation, unit by hour, 2019-01 → 2025-09, PDBF both legs,
each unit to its largest owner that day, priced at its country's day-ahead price and costed
(design §2): 2.04 M group × hour × class × leg rows. On weekdays its generation equals the
holiday quantity panel's in every group-hour (0.0000 MW gap over 211,320).

### 1. Who supplies own customers

TWh, 2019-01 → 2025-09, five firms:

| class | auction | bilateral | bilateral share |
|---|---|---|---|
| nuclear | 74.2 | 289.1 | 80% |
| **generic units** (bought energy, resold) | 0.2 | **232.5** | 100% |
| storage hydro | 126.2 | 106.2 | 46% |
| wind | 111.8 | 67.9 | 38% |
| solar | 13.7 | 22.7 | 62% |
| coal | 14.0 | 3.0 | 18% |
| combined cycle, costed / not costed | 132.0 / 25.1 | 0.7 / 1.1 | 0.5% / 4% |
| cogeneration and other, no cost | 33.1 | 3.9 | 11% |
| pumped storage | 18.7 | 0.4 | 2% |

Bilateral share of each firm's physical output (generic units out): Iberdrola 70%, Endesa 55%,
Naturgy 28%, Repsol 6%, EDP 3%.

**The generic units are not output.** OMIE lists 322 units of type *GENERICA*. Each sale unit
(code ending V) is matched hour by hour by a purchase twin (ending C) buying the same energy:
99.6–100% of the volume matches, for every pair. Among the five firms: Naturgy `GGNCOV1` /
`GGNCOC1` 109.7 TWh (and `GGASNV1` 8.7 TWh in 2019), EDP `GEDPGV2` / `GEDPGC2` 97.4 TWh (EDP GEM
Portugal), Repsol `GREPSV1` / `GREPSC1` 17.7 TWh. The sale leg is a bilateral contract (role 4);
the purchase leg is not. So a large part of Naturgy's and EDP's "bilateral generation" is energy
bought and passed to the retailer. They were in the quantity test's generation (`gen`), but on
holidays they do not fall (below), so that test's reading stands.

**Costed share** of physical output: 87–92% every year (lowest 2025). By firm: Repsol 38–60%
(cogeneration, Escatrón 3 without a plant-specific efficiency), EDP 2022 77%; the rest above 82%.

### 2. Self-supply above cost

Share of costed MWh produced when the price was below the plant's cost, 2019-01 → 2025-09:

| | auction | bilateral |
|---|---|---|
| storage hydro (price below the water value λ*) | 59% | 65% |
| nuclear (below fuel at book value, ~€25) | 22% | 9% |
| coal | 27% | 39% (3 TWh) |
| combined cycle | 7% | 8% (0.7 TWh) |
| wind, solar (price below 0) | 0.5–4% | 0.5–8% |

- **Hydro runs below its water value most of the time, whichever leg.** λ* is the value of
  water for a plant that runs flat out in the dearest hours; real cascades run part-load over
  many more hours (minimum flows, cascades, irrigation), so this is not a self-supply effect. By
  firm the bilateral share is 64–67% against 56–70% for auction hydro (Endesa's auction hydro
  is the higher; Repsol has almost no bilateral hydro).
- **Nuclear sold bilaterally runs below cost less often than nuclear sold in the auction**
  (9% against 22%; 2025: 19% against 36%).
- **In €**: bilateral output below cost costs €92–573M a year (2019–2025), against a bilateral
  margin of €0.6–9.5bn. Hydro is €2.1bn of the €2.5bn over the window, nuclear €0.35bn;
  Iberdrola's bilateral output accounts for €250–290M a year from 2022.

### 3. Timing of hydro

Capture ratio Σ p q / Σ p̄ q (above 1: output in the day's dearer hours), storage hydro:

| | 2019 | 2021 | 2023 | 2025 |
|---|---|---|---|---|
| EDP, all (3% bilateral; the reference) | 1.06 | 1.07 | 1.10 | 1.20 |
| Iberdrola, auction / bilateral | 1.04 / 1.04 | 1.05 / 1.05 | 1.20 / 1.12 | 1.32 / 1.22 |
| Endesa, auction / bilateral | 1.04 / 1.02 | 1.03 / 1.03 | 1.06 / 1.07 | 0.99 / 1.28 |
| Naturgy, auction / bilateral | 1.03 / – | 1.05 / 1.02 | 0.85 / 1.01 | 1.37 / 1.01 |

- **Iberdrola and Endesa time their self-supplied hydro about as well as the auction part**
  (Iberdrola a little worse from 2022, Endesa better from 2022) and as well as EDP.
- **Naturgy's bilateral hydro is flat** (1.00–1.02 every year). Timed like EDP's, it would have
  earned €16–34M a year more in 2022–2025 (€111M in all). Within a unit, days with more of it
  sold bilaterally are flatter (capture −0.24 per unit of bilateral share, se 0.03; Endesa
  −0.05, se 0.01; Iberdrola and EDP ≈ 0). Rivers differ (Naturgy's are Galician, EDP's
  Portuguese), and a full river raises both flat running and bilateral sales, so this is an
  upper bound on a timing cost, not a measurement.

### 4. On holidays: what is cut, and the power of the € test

Weekday firm-days (8,805, 567 with a dose), MWh per MWh of holiday dose, date and firm × month
effects, date clusters:

| outcome | per MWh of dose | mean margin of the class on dosed days, €/MWh |
|---|---|---|
| generation, all | **−0.38 (0.12)** | |
| … physical (generic out) | **−0.43 (0.11)** | |
| … bilateral / auction | −0.50 (0.12) / +0.12 (0.16) | |
| storage hydro | **−0.20 (0.06)** | −10.2 (it ran below λ* on those days) |
| wind | **−0.18 (0.07)** | 84.0 |
| nuclear | −0.06 (0.06) | 65.9 |
| generic units | +0.05 (0.02) | none |
| gas, coal, solar, other | −0.01 to +0.05 | |

- **The holiday cut falls on hydro and wind**, not nuclear. Cutting hydro that was running below
  its water value saves money (+€2 per MWh of dose); cutting wind gives up the whole price (−€15).
- **Reference A** (every cut MWh lost at its class's margin): **−€17 per MWh of dose**.
  se(b) under b = 0: €18.8, so the smallest detectable b is **€53**. **Stop rule: STOP** (design
  §3, 1a). The € test cannot tell the reference from zero.

**The wind cut is the open puzzle.** A firm's wind blows whatever its customers do. If the
schedule falls by 0.18 MWh per MWh of lost load and the auction does not take it, the wind is
either curtailed (losing the full price), sold in the intraday auctions, or the bilateral "wind"
volume is a contract quantity rather than physical output. Or it is chance: 567 dosed days, and
regional holidays fall on dates when a firm's own region may be more or less windy. Each is
checkable: own regional wind (`regional_wind_offer_test.py` Wdev) as a control; the firms' wind
units' intraday sales on dosed days; ESIOS measured output by province against the schedule.

### What step 1a settles

- **Self-supply is not where the firms run plants out of merit.** It runs on cheap plants. Its
  above-cost share is about that of the same firms' auction sales (hydro a little higher,
  nuclear lower), and its
  timing is as good, except Naturgy's flat hydro (at most about €30M a year).
- **The holiday cut itself cannot be priced precisely**: about €17 per MWh of lost load if all
  lost, with an interval four times as wide.
- **Book balancing looks cheap.** The rule matches own supply to own customers, mostly with
  plants whose output costs little to move (hydro below its water value), and the parts that
  could cost money (wind, Naturgy's timing) are small or unexplained.

## The wind checks (2026-10-21): the wind cut was weather

`self_supply_cost.py --wind` → `outputs/tables/self_supply_wind_checks.csv`; log `wind.log`.
Asked after step 1a, to explain why the firms scheduled less wind on their customers' holidays.

**In one line.** The firms' own wind happened to blow less on their customers' holidays. With
that controlled, the wind schedule does not fall, nothing moves to the intraday auctions, and
the only change is on paper: some wind leaves the own-retail bilateral contract for the auction.

**Own wind.** Each firm's located onshore wind capacity by region (`renewable_unit_locations_v3`,
78.5% of wind) times its regions' measured capacity factor (ESIOS output by province over
installed capacity), MWh per day (`regional_wind_offer_test` tools). It tracks the firms' wind
schedule closely: 0.87 MWh of schedule per MWh of it (t 72), within firm-month and day.

Weekday firm-days, MWh per MWh of holiday dose, date and firm × month effects, date clusters:

| outcome | on the dose | with own wind controlled |
|---|---|---|
| wind schedule (PDBF) | −0.18 (0.07) | **−0.04 (0.03)** |
| own wind (physical proxy) | **−0.17 (0.07)** | |
| own wind's regional deviation from the peninsula | −0.01 (0.01) | |
| … bilateral wind | | −0.10 (0.05) |
| … auction wind | | +0.07 (0.05) |
| net intraday wind sales | | +0.00 (0.01) |
| wind after intraday | | −0.03 (0.03) |
| schedule, national / regional days | | −0.04 (0.03) / −0.04 (0.05) |
| schedule, week clusters | | −0.04 (0.03) |

- **The cut was the wind, not the firms.** Own wind blew 0.17 MWh less per MWh of dose, which
  at 0.87 explains 0.15 of the 0.18. What is left (−0.04) is not significant, on national and on
  regional days alike.
- **Why holidays and wind line up**: not through the regions (the regional deviation does not
  move), so through the level. A firm's own wind moves with national wind in proportion to its
  capacity, and the doses sit mostly with Endesa and Iberdrola (2.1 of 2.8 TWh of dose; Iberdrola
  has the most located wind, 5.9 GW). The holiday dates were calmer than the rest of their months,
  which lowers the big-wind, big-dose firms' wind more than the others'. Chance, on 133 dates.
- **Nothing is sold intraday instead** (+0.004).
- **Book balancing on paper**: on its customers' holidays a firm puts about 0.10 MWh less wind per
  MWh of dose under the bilateral contract with its retailer and sells about as much more in the
  auction. The wind is the same; its label follows the retail load.

**What it changes.**
- **The holiday cut, net of weather**, is hydro (−0.20) and nuclear (−0.06): physical generation
  about −0.29 per MWh of dose rather than −0.43.
- **The € reference** with wind at its weather-controlled −0.04 becomes about **−€5 per MWh of
  lost load** (nuclear −3.9, wind −3.0, hydro +2.0, others +0.0) instead of −€17. Book balancing
  on holidays is close to free.
- **Yesterday's quantity test included this weather** in its generation response (b_Z −0.33
  hourly). Its slope test (b_P) is not about the size of the cut, so its verdict should stand, but
  b_Z overstates the cut by about a third. A rerun with own wind as a control would settle it.
