# The intraday squeeze: do rivals exploit a firm that has just lost a reactor?

Design: `docs/specs/2026-10-19-intraday-squeeze-design.md`. Running note.

## Step 1: the event table (2026-10-19)

`build/build_intraday_squeeze_events.py` (`--summarise` recomputes the summary from the
stored files) → `outputs/tables/intraday_squeeze_trips.csv` (one row per trip),
`intraday_squeeze_cells.parquet` (44,344 trip × day class × session × hour cells:
29,914 pre, 4,975 window, 9,455 post). Log:
`.superpowers/sdd/2026-10-19-outage-runs/squeeze_step1_summary.log`. Descriptive only.

**Where it ends (2026-10-19, §2.1).** After a trip the intraday price rises about €4/MWh
in the sessions that can react, and across trips it follows the price-taking slide along
the whole market's offers (1.2 + 1.95 × slide, se 1.8 and 0.8; price-taking is 0 + 1).
No sign that rivals squeeze the owner; the remainder is the size of a placebo day's swing.

**In one line.** After a trip, the reactor buys back a median 65% of its day-ahead
schedule in the intraday auctions. The owners' other plants cover part of it
themselves, so what the owners take from rivals is a median 34% of the lost schedule:
6% of the window's cleared intraday sales, and very different from trip to trip. The
stop rule passes (79% of main-sample trips buy back at least 30%).

**Trips.** 40 unplanned trips that take a reactor below 300 MW while it is still
scheduled day-ahead (≥ 200 MW on average in the window); one dropped, Ascó 2 on the
night of the 28 April 2025 blackout. By year: 2018 5, 2019 4, 2020 5, 2021 7, 2022 8,
2023 0, 2024 6, 2025 4. Main sample (six MIBEL sessions, to 2024-06-13): 33; IDA era: 6.
**22 trips have at least one post-window day** with the reactor still out, the
no-forced-buyer control.

**Who covers the trip** (main sample; MW are means over the window's hours, summed over
sessions; "change" is against the same sessions and hours on the 7 days before):

| | median | middle half |
|---|---|---|
| reactor's net intraday buy / its day-ahead schedule | 0.65 | 0.45–0.80 |
| owners' other units' extra intraday sales | +144 MW | |
| owners' net take from rivals (change) / day-ahead schedule | **0.34** | 0.01–0.67 |
| that take / the window's cleared intraday sales | **0.06** | 0.00–0.11 |

IDA era (6 trips): reactor buy-back 0.48, net take 0.26, 7% of cleared sales.

- **The reactor's unit buys back itself**, in the first session that can react: session 2
  on 12 of the 33 trips (the first session for the next day), session 5 or 6 on 10. In two
  trips there is no auction buy-back at all.
- **Owners cover part from their own plants, and how much varies widely.** On Vandellós II
  in April 2019 the owners' other units sold 740 MW more intraday, so they took almost
  nothing from rivals. On Cofrentes in April 2022 they sold slightly less, and took 933 MW.
  This variation is useful for step 2: the squeeze should grow with what the owners take
  from rivals, not with the size of the trip.
- **The take is endogenous** (the owners' other plants respond to intraday prices too).
  The exogenous shock is the trip, with the reactor's day-ahead schedule in the window as
  its size; the take is its first stage.

**Implications for step 2.**
- Outcome cells and controls are in the cells file: prices (ES and PT intraday, ES
  day-ahead) are attached, rivals' offers are not yet.
- Dose: the reactor's day-ahead schedule in the window (exogenous), with the owners' take
  as the first stage and as a heterogeneity check.
- The forced demand is about 6% of the session's cleared sales, so the slide along rivals'
  curves (Δp_mech) will be modest. Measure it before reading any premium.

## Step 2: the premium, the slide and rivals' offers (2026-10-19)

`analysis/intraday_squeeze_test.py` → `intraday_squeeze_results.csv` (every comparison),
`intraday_squeeze_trip_effects.csv` (one row per trip and session class),
`intraday_squeeze_cells_offers.parquet`; log `squeeze_step2.log`. Each outcome is its
change against the trip's own 7 pre days in the same session and local hour, averaged
over a trip's cells, then over trips (standard errors across trips).

**In one line.** The intraday price does rise after a trip, by about €4/MWh in the
sessions that can react, and not in the sessions that closed before it or on the days
after the window. Less than half of that is the slide along rivals' curves. The rest
does not grow with what the owners buy from rivals, and is no bigger than a placebo day's
swing, so there is **no sign that rivals squeeze the owner**. The rise looks like the
price catching up with a scarcity the day-ahead price did not know about.

**Main sample** (33 trips to 2024-06-13; €/MWh, MW):

| cells | trips | premium change | slide | premium − slide | owners' take | rivals' MW at ≤ anchor + €10 |
|---|---|---|---|---|---|---|
| window, sessions that can react | 31 | **+4.23 (1.45)** | +1.58 (0.53) | +2.66 (1.60) | +136 (37) | −195 (184) |
| window, sessions closed before the trip | 25 | +0.46 (0.55) | −0.48 (0.36) | +0.93 (0.55) | −38 (32) | −78 (224) |
| post-window days (reactor out, no forced buyer) | 18 | +0.74 (1.06) | −0.46 (0.42) | +1.20 (1.04) | −12 (17) | −71 (261) |
| placebo: last pre day against the six before | 33 | **−2.14 (0.99)** | +1.62 (0.96) | **−3.76 (1.76)** | +13 (15) | +137 (181) |

All 39 trips (IDA era included): reacting sessions +5.26 (1.39), slide +3.66 (1.38),
remainder +1.60 (1.68). With a ±€10 band for the slope: remainder +2.72 (1.56).

- **The premium is real and specific.** 25 of 31 trips show a rise in the reacting
  sessions (sign test p = 0.001; median +2.0). The sessions that closed before the trip
  (15 of 25, p 0.58) and the post-window days do not.
- **The slide explains less than half** (mean 1.6, median 0.4): the owners' net take of
  136 MW against a local slope of about 131 MW per €/MWh.
- **The remainder passes a rank test but fails the other two.** Median +1.4, Wilcoxon
  p = 0.026. But:
  - **No dose response.** Across trips, the premium falls by 0.62 per 100 MW of take
    (se 0.71); a squeeze needs it to rise. The largest rises come on trips where the
    owners took nothing from rivals: Cofrentes 8 April 2022 +32 €/MWh with −55 MW;
    Almaraz 1 3 June 2024 +27 with +21; Vandellós II November 2022 +15 with −47.
  - **The placebo swings as much**: the last pre day sits 2.1 below the six before it,
    and its remainder is −3.8 (1.8). Day-to-day noise is the size of the effect.
- **Rivals' offered MW do not move** distinguishably: −195 MW at the anchor + €10 (se
  184), against placebo swings of ±150–250 MW.

**Reading.** In the window the day-ahead price was set with the reactor in, so the
intraday price has a scarcity to catch up with. It does, about €4/MWh. It does so
whether the owners buy the shortfall from rivals or cover it with their own plants,
which is what a price-taking market does: the owners' replacement units bid at their
higher cost too. **The slide as designed (net take over rivals' slope) leaves those
units out.** The benchmark that fits price-taking is the reactor's gross buy-back over
the whole market's slope, owners' units included. That is the one check left before the
squeeze can be called absent rather than merely undetected.

### 2.1 The whole-market slide (2026-10-19)

`intraday_squeeze_test.py --gross` (on the stored cells) → `intraday_squeeze_gross.csv`;
log `squeeze_gross.log`. The price-taking benchmark with the owners' replacement plants
counted: the reactor's gross buy-back change over the slope of everyone else's offers
within ±€5 of the price (owners' units in). Median slope 189 MW per €/MWh, against 131
for rivals only.

| main sample (€/MWh) | trips | premium change | whole-market slide | remainder | median remainder (Wilcoxon p) |
|---|---|---|---|---|---|
| window, sessions that can react | 31 | +4.23 (1.45) | +1.53 (0.32) | +2.70 (1.35) | +1.16 (0.04) |
| window, sessions closed before the trip | 25 | +0.46 (0.55) | +0.03 (0.04) | +0.43 (0.53) | +0.63 (0.58) |
| post-window days | 18 | +0.74 (1.06) | −0.00 (0.04) | +0.74 (1.04) | +0.42 (0.28) |
| placebo: last pre day | 33 | −2.14 (0.99) | +0.03 (0.02) | −2.17 (1.00) | −0.42 (0.20) |

**Across the 31 trips, the premium follows the slide:** premium change = +1.24 (1.78) +
1.95 (0.77) × whole-market slide. Price-taking predicts 0 + 1 × slide. Neither part
rejects it: the intercept is 0.7 standard errors from 0, the slope 1.2 from 1. With the
±€10 band the remainder is +2.79 (1.41). All 39 trips, IDA era included: intercept
+4.07 (1.44), slope 0.32 (0.15), carried by two IDA trips with large buy-backs.

- **The dose response that failed in step 2 holds here.** It failed because the owners'
  net take from rivals was the wrong dose. The price rises along everyone's curve,
  including the owners' own replacement plants, so the reactor's gross buy-back is what
  moves it.
- **What is left is about the size of noise.** The remainder averages +2.7 (se 1.35),
  marginal on a t-test and a rank test, and a placebo day swings by −2.2 (se 1.0).
- **A bound, not a zero.** At 95% the remainder lies between about 0 and €5.3/MWh, and
  the slope between 0.4 and 3.5 times the slide. So the data cannot rule out rivals
  doubling the slide, but they give no reason to think they do.

**Where the squeeze ends.** After a trip, the intraday price catches up with a scarcity
the day-ahead price did not know about, and by about the amount a price-taking market
would move along its offer curves. There is no sign that rivals exploit an owner forced
to buy. Together with the nuclear-cuts result (`rq-nuclear-cuts.md` §6), outages shift
positions and prices as a competitive market would, and none of these designs finds
them changing how firms use market power.
