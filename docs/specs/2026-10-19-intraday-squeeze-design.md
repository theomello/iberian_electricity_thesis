# The intraday squeeze: do rivals exploit a firm that has just lost a reactor?

**Status: proposed 2026-10-19. Nothing here is built or run.** The data facts in §2 were
checked on the files the same day, with throwaway queries (no committed script). Builds on
the reactor outage table (`build/build_reactor_outages.py`, `notes/rq-reactor-outages.md`)
and the nuclear-cuts work (`notes/rq-nuclear-cuts.md`). Framework:
[`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md).
Statements marked *to verify* come from memory or secondary sources.

**In one example.** On 4 January 2019 at 20:20, Ascó 2 tripped (a steam leak in the
high-pressure turbine). Its day-ahead schedule for 5 January had been fixed at noon on
the 4th, with the reactor in it. So Endesa was suddenly short for the whole of the 5th,
and in the first intraday session after the trip it bought back the reactor's entire
day-ahead schedule, 324 MW every hour, with buy bids at €66–80/MWh. Everyone could see
the shortage, because owners declare a trip in OMIE's outage register within minutes.
**The question: when a large, visible, price-insensitive buyer appears for reasons it
cannot help, do rival sellers raise their intraday offers?**

**Why this is a market-power test and not just a price effect.** The same 1 GW of nuclear
supply is missing on the days after the window too, once the day-ahead schedule has
caught up with the outage. On those days nobody is forced to buy it back intraday. So the
design compares two situations with the same scarcity: one with a forced buyer (the
window) and one without (after it). Price-taking rivals offer at cost in both. Rivals
with market power raise their offers in the window, when the residual demand they face
in the intraday auction has jumped by the buy-back.

---

## 1. The idea in the framework's terms

Each rival i in an intraday session faces residual demand that the trip has shifted out
by the owner's net buy-back B (MW). By the framework's condition, i's offer above cost is
β · nᵢ / |RD′ᵢ| (nᵢ i's net sales in the session). The buy-back raises nᵢ for every rival
that supplies part of it, so:

- **β = 0 (price-taking):** rivals' intraday offer curves do not move. The price rises only
  by sliding along their curves: Δp ≈ B / (slope of rivals' intraday supply near the price).
- **β > 0:** rivals' curves move up in the window, and the price rises by more than the
  slide. The excess is the squeeze.

The owner is the other half. A buyer with market power would shade its bids (bid below its
value to pay less). **The owner's bids are mostly at €180.30 or €500**, the top of the
price range (§2), so it does not. That is a finding in itself and simplifies the design:
B is close to price-inelastic demand.

## 2. What the data show (checked 2026-10-19)

**Trips.** From the outage register (`indisp`), unplanned declarations taking a reactor
below 300 MW: 69. The trip time is the declaration's own `start`, not the reactor table's
spell start, which is the next day's schedule at 00:00. The owner declares at a median of
0.1 h after the start (middle half −15 h to +2 h; declarations made ahead are
short-notice stops). Trip hours spread over the whole day.

**The window** = delivery hours from the trip to the end of the last day whose day-ahead
schedule was fixed before the owner knew (the earlier of the declared start and the
declaration time; day-ahead offers close at 12:00 on D−1):

- 52 of the 69 declarations leave one; median 25 hours (middle half 20–31, range 3–36);
- after grouping declarations of one breakdown (same reactor, within 3 days) and keeping
  windows where the reactor was scheduled (≥ 200 MW): **40 distinct trips**, 2018: 5,
  2019: 4, 2020: 5, 2021: 7, 2022: 8, 2023: 0, 2024: 6, 2025: 5.

**The owner buys back in the intraday auctions.** The reactor's own unit buys (side C,
cleared) in the window. Net of its intraday sales, as a share of its day-ahead schedule in
the window: median 0.65 to June 2024 (six MIBEL sessions), 0.44 after (three European IDA
auctions), across 1–5 sessions; middle half over all trips 0.44–0.85.

- **Buy bids are mostly price-insensitive:** examples, cleared nearly in full: Almaraz 2,
  27 June 2020, 992 MW at €180.30 against a session price of €31; Almaraz 2, 6 December
  2022, 824 MW at €500 against €153; Ascó 2, 13 February 2024, 132–700 MW at €72–105
  against €58–69. Trillo, 17 February 2021, is the exception: bids near the price, half
  cleared.
- **In 2025 several trips show no auction buy-back at all** (Ascó 2 12 February, Almaraz 1
  1 June). Since June 2018 the continuous intraday market (MIC, the European SIDC
  platform) runs alongside the auctions, and the repo does not hold it (§6).

**After the window.** 18 of the 40 trips keep the reactor out (≥ 90% of the day) for at
least one full day after the window, 6 of them for 7 days or more. Those are the
no-forced-buyer days of the comparison.

**Prices.** OMIE `marginalpibc` (`data/omie/intraday_prices/`): price by session and
period, `price_a` Portugal, `price_b` Spain, sessions 1–6 to 2024, 1–3 from 2025.
**Bids:** `curva_pibc_uof` (`data/omie/intraday/parquet/`), unit-level, offered (O) and
cleared (C), session index from the filename.

## 3. Outcomes

For each trip, each session s and delivery hour h in the window, and the matched
comparison cells (§4):

1. **The squeeze premium:** the session's Spanish price minus the day-ahead Spanish price
   for h, p_ID − p_DA (the day-ahead price was set before the trip, so it is a clean
   baseline).
2. **Rivals' offer curves:** each rival group's intraday sell offers (status O) in the
   session, summarised as the MW offered at or below p_DA + k for k on a grid (−10, −5,
   0, +5, +10, +20 €/MWh). A squeeze shows as less supply at a given price.
3. **The mechanical effect:** the slide along rivals' offered curve caused by the owner's
   net buy-back B, Δp_mech, computed from rivals' offered MW near the clearing price
   (local slope), and as a check by re-clearing the session without the owner's buy bids
   (§6 says why re-clearing is not trusted by default).
4. **The squeeze** = premium − Δp_mech, and its counterpart in rivals' offers.

Rivals are every seller not in the owner groups of the tripped reactor (dated ownership,
`lib/unit_ownership.py`). The five large groups are reported one by one; the fringe as one.

## 4. Comparisons

- **After the window (main control):** the same sessions and hours on the days after the
  window when the reactor is still out (18 trips). Same missing supply, no forced buyer.
- **Before the trip:** the same sessions and hours on the 7 days before.
- **Matched days (all 40 trips):** the same session index and hour, days in the same month
  without a trip or a reactor declared out, weighted to match REE's D-1 forecasts of
  demand, wind and solar (ESIOS 1775/1777/1779, from 2019) and the day-ahead price.
- **Sessions that closed before the trip:** window hours are also traded in sessions
  whose gate closed before the trip (a trip at 20:20 comes after the first session for
  the next day). Those sessions cannot react to it: a placebo inside the window.
- **Placebos:** (a) planned refuellings, where the day-ahead schedule already excludes the
  reactor and nobody buys it back intraday, so the squeeze should be zero; (b) pseudo-trip
  dates drawn from the matched days.

Estimation: a stacked event study (trip × relative day × session × hour), cells relative
to the 7 days before; window and post-window effects with hour and session effects.
**Inference by trip**: cluster on the trip, and randomisation inference over pseudo-trip
dates, since there are 40 events.

**The prediction, fixed in advance:** squeeze in the window > 0 and in the post-window days
≈ 0 under market power; both ≈ 0 under price-taking. Its size is read against Δp_mech:
the squeeze as a share of the mechanical effect.

## 5. The owner's own response

The owner can also cover the trip by selling less intraday from its other plants or by
raising their output. Its **net** intraday position (all its units) is the right B; the
reactor's own buy-back is the main part. Check: the owner's other units' intraday sales in
the window against the post-window days.

## 6. Threats

| threat | answer |
|---|---|
| **The continuous market.** The owner may cover part of the trip in continuous trading, unseen in the auction data (2025: several trips with no auction buy-back) | main sample to 2024-06-13 (six sessions; median buy-back 0.65); the continuous data are public by unit after 90 days (`pibcic`, ~66 MB for 2019–2025, token-free, `notes/continuous-intraday-data.md`). **A separate fetch, proposed when needed, not assumed** |
| Rivals cannot see the trip | owners declare within minutes (median 0.1 h); OMIE republishes the register many times a day. Our copy keeps the day's last snapshot only, so the visible time is bounded by `declared`, not measured |
| Re-clearing the intraday auction from bids is inaccurate | measured: deriving the intraday price from bids errs by a p95 of €3.9–7.8 (CLAUDE.md, `marginalpibc`), partly because zones split and most bid rows are tagged `MI`. The published price is the outcome; the mechanical effect uses the local slope; re-clearing only after it reproduces the published price on non-trip sessions |
| Spain and Portugal split in the intraday market (about 13% of periods from 2022) | Spanish reactors: Spanish price (`price_b`); split periods reported apart |
| Session schedules changed: six MIBEL sessions to 2024-06-13, three IDA auctions from 2024-06-14, both running in 2025-03 → 06; 15-minute periods from 2025-03-19 | regimes estimated apart; session horizons read from the data; gate-closure times from OMIE's rules (*to verify*: MIBEL sessions 3–6 cover hours 5, 8, 12, 16 onward, which the data confirm) |
| The trip itself raises the price in later hours through scarcity | that is what the post-window days hold fixed |
| The window's hours are a special set (a trip at 20:00 gives a window of the next day) | hour effects, and comparisons in the same hours |
| Few events | 40 trips, 18 with post-window days; inference by trip and by randomisation. The buy-back is large for the market (about 600 MW an hour against roughly 4–5 GW cleared intraday an hour, *to verify per regime*), so the mechanical effect is visible event by event |
| The 28 April 2025 blackout | Ascó 2's trip at 22:00 that day is dropped |

## 7. Steps, each a separate run proposed before it starts

1. **Event table.** Build the trips, windows, post-window days, and the owner's net
   buy-back per session and hour (`build/build_intraday_squeeze_events.py`). Descriptive.
2. **Premium and offers.** The event study of p_ID − p_DA and of rivals' offered MW (§3–4).
3. **Mechanical effect and the squeeze.** Local slopes; re-clearing only if validated.
4. *(If needed)* **The continuous market.** Fetch `pibcic` (and `precios_pibcic`), add the
   continuous buy-back to B, and extend the sample past June 2024.

**Stop rule, fixed now.** If step 1 finds the owner's net auction buy-back below 30% of its
day-ahead schedule on most main-sample trips, the auctions are not where a squeeze would
show: propose step 4 or stop.

## 8. Left to the builder

- The grid of price levels for rivals' offered MW, and the band defining the local slope.
- How matched days are weighted (nearest neighbours or regression on the forecasts).
- How declarations of one breakdown are grouped (same reactor within 3 days was used for
  the counts above).
- Gate-closure times per session and regime, from OMIE's market rules (*to verify*). If
  they cannot be pinned down, the owner's first session with a buy-back after the trip
  marks the first session that could react.
- The 2018 trips (5) have no REE D-1 forecasts (they start in 2019): match them on REE's
  realised demand and wind instead, or leave them to the before/after comparisons.
- Offered intraday curves may hold rows that cannot clear, as day-ahead ones do (CLAUDE.md,
  "OMIE's offered curves do not re-clear"). If the local slope looks off, use the
  effective curve (accepted rows below the price, offered rows at or above it).

**My calls, to check:** the post-window days as the main control; the main sample to
2024-06-13; the owner's net position (all its units) as B; dropping the blackout trip;
rivals defined as everyone outside the tripped reactor's owner groups; the continuous
market as a later, conditional fetch rather than part of step 1.
