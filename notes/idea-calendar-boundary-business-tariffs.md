# Idea: the season calendar of the business tariffs as a repeated price shock

**Status: idea only, written 2026-11-16. Nothing estimated, nothing downloaded, no rules set.** If it is taken up it needs its
own design file in `docs/specs/` with a step-zero noise check before any response is computed.

## In one example

A shop on tariff 3.0TD (low voltage, contracted power above 15 kW) pays about €32/MWh in tolls and charges for a weekday
afternoon hour on 30 June and about €77/MWh on 1 July, because July is a "high season" month in the legislated calendar and
June is a "medium" one. The night price stays near €5 and weekends stay at the lowest period all day. On 1 August the
afternoon price drops back to €32. A household on 2.0TD sees no change on either date: its three periods are the same all year.

If business customers respond to price, their weekday daytime use should fall on 1 July and recover on 1 August, relative to
their own nights and weekends, and relative to households. It should not have done so in 2018–2020, when the old tariff had no
such boundary.

## The shock

Since 1 June 2021 the six-period tariffs (3.0TD and 6.1TD to 6.4TD) assign each month to a season, and the season decides which
two price periods apply to the daytime hours of a working day (Circular 3/2020 of the CNMC, the Spanish markets and competition
regulator, art. 7; calendar verified in `docs/tou-policy-sources.md`):

| season | months | weekday 9–14h and 18–22h | weekday 8–9h, 14–18h, 22–24h | 0–8h, weekends, holidays |
|---|---|---|---|---|
| high | Jan, Feb, Jul, Dec | P1 | P2 | P6 |
| medium-high | Mar, Nov | P2 | P3 | P6 |
| medium | Jun, Aug, Sep | P3 | P4 | P6 |
| low | Apr, May, Oct | P4 | P5 | P6 |

That gives **eight boundaries a year** where the daytime price steps and the night and weekend price does not. With the 2021
energy-term prices (tolls plus charges, €/MWh, from `outputs/tables/tou_tariff_prices_2021.csv`), the step in the top daytime
period is:

| boundary | seasons | 3.0TD | 6.1TD |
|---|---|---|---|
| 1 March | high → medium-high | −18 | −12 |
| 1 April | medium-high → low | −42 | −27 |
| 1 June | low → medium | +15 | +10 |
| 1 July | medium → high | +45 | +29 |
| 1 August | high → medium | −45 | −29 |
| 1 October | medium → low | −15 | −10 |
| 1 November | low → medium-high | +42 | +27 |
| 1 December | medium-high → high | +18 | +12 |

These are 2021 values. The charges changed several times afterwards (cut by 96% on 16 September 2021, restored in 2022, cut
again on 31 March 2022, new values each January), so the size of each step differs by year. That is extra variation in the
dose on the same calendar date. The steps for 6.2TD to 6.4TD are a half to a quarter of the 6.1TD ones. The power (capacity)
term also follows the six periods and is not in this table.

## The comparison

Per boundary and year, in a short window either side (for example two to three weeks):

1. **day minus night** removes anything that moves the whole day (temperature level, activity);
2. **working day minus weekend** removes anything that moves daytime on every day (daylight, heat); weekends are P6 all day, so
   they carry no price step;
3. **after minus before** the boundary;
4. **post-reform years minus 2018–2020** at the same calendar date removes the usual seasonal turn at that date;
5. **business minus household** series, since 2.0TD has no boundary.

The old tariffs help step 4. Tariff 3.0A had no month boundaries at all (its periods moved only with the clock change, and it
made no weekend distinction), so its pre-reform years are a clean placebo. The old 6.x tariffs had boundaries, but different
ones: August was off-peak all month, June was split on the 16th, and so the same date carries a different dose before and after
the reform (hours in Orden ITC/2794/2007, read in `docs/tou-policy-sources.md`).

The elasticity is the response divided by the log change in the all-in price (wholesale price plus tolls and charges), as in the
paper's Wald ratio.

## Why it might work where the earlier business designs stopped

The industry designs in this repo (`2026-11-12-industry-voltage-design.md`, `2026-11-13-industry-noise-check.md`,
`2026-11-16-industry-adjusted-design.md`) used one event, the June 2021 reform, and one long window, and they failed on noise
and level drift. Here there are about eight events a year over five years, short local windows, a predicted sign that alternates
(up in July, down in August), and a dose that differs by tariff and by year. Many events suit the randomization inference
already built (`2026-11-17-randomization-inference-design.md`): the placebo distribution comes from the same statistic at
non-boundary dates and at boundary dates in pre-reform years.

## Data

- **On disk:** ESIOS hourly demand by voltage level (E0 below 1 kV, which mixes 2.0TD households with 3.0TD businesses; E1 to
  E6), to April 2026; the tariff tables and the period calendars, old and new; the per-hour LASSO pipeline.
- **New, not fetched:** Barcelona City Council's open dataset "Consum d'electricitat per codi postal, sector econòmic i tram
  horari" (source Datadis, the distributors' data platform; CC BY 4.0). Daily, 2019 to 2025, one file a year (about 14 MB,
  244,000 rows), by postal code, by sector (Residencial, Serveis, Indústria, No especificat) and by four six-hour bands
  (0–6, 6–12, 12–18, 18–24). It separates services from households in the same postal codes, which the national series cannot.
  **Seen so far: 30 sample rows of 2021 only.** The number of postal codes, the units (the page says MWh, the values look like
  kWh), suppression rules and revisions are unconfirmed.

## Weak points

- **Unknown tariff mix.** "Services" in a postal code mixes 2.0TD shops, 3.0TD and some 6.1TD buildings; E0 mixes households and
  3.0TD. The dose is assumed, or bracketed.
- **Fixed-price contracts.** Many businesses pay a retailer price per period that may not pass the season steps through, or may
  smooth them over the year. The effective dose could be much smaller than the table. Retailer price sheets for 3.0TD would
  show this.
- **Boundaries coincide with seasonal turns.** 1 July and 1 August are holiday and heat dates. Steps 1, 2 and 4 are the guard,
  not a proof; working patterns in August differ between weekdays and weekends.
- **Six-hour bands in the Barcelona data.** The 6–12 band holds P6, P2 and P1 hours; only 0–6 is clean.
- **COVID in the pre-period.** 2020 and early 2021 are poor placebo years for services; that leaves 2019 for Barcelona and
  2018–2019 for the national series.
- **Anticipation and adjustment within the month.** The steps are known a year ahead, so the estimate is a response to an
  anticipated, recurring price change. Firms may adjust schedules by month, which is the response of interest, or not at all.
- **A precise zero is a likely result.** The literature on firms mostly finds little response. A tight bound is still an
  identified elasticity for a group the paper does not cover.
- **Power is unknown** until a noise check on non-boundary dates is run.

## References

In `literature/md/`:
- Enrich, Li, Mizrahi and Reguant (2024): the method (per-hour LASSO, triple difference, Wald ratio).
- Burlig, Knittel, Rapson, Reguant and Wolfram (`w23908`): the prediction-error method.
- Triple-difference papers (`250216126v3`, `250219620v3`, `250509942v3`, `utac010`) and `240912353v2` (synthetic control on a
  triple difference).
- Conley and Taber (`t0312`) and MacKinnon and Webb (`qed-wp-1314`): inference with few treated units.
- Callaway, Goodman-Bacon and Sant'Anna (`w32117`): difference-in-differences with a continuous dose.
- von Graevenitz and co-authors (`ssrn-4251564`): German manufacturing, own-price elasticity −0.4 to −0.6 from network-charge
  variation; the closest result for firms.
- Ito (`w18533`): which price consumers respond to (marginal against average), relevant to the fixed-contract problem.

Not in the repo, cited from memory or from a search result, **not read**:
- Jessoe and Rapson (2015), *Journal of Industrial Economics* 63(3): mandatory time-of-use pricing for commercial and
  industrial firms assigned by a load threshold; little or no change in usage.
- Hausman and Rapson (2018), *Annual Review of Resource Economics*: regression discontinuity in time and its pitfalls
  (seasonality, serial correlation, short windows), which apply to each boundary here.
- Aigner, Newman and Tishler (1994), *Journal of Applied Econometrics* 9(3): time-of-use experiment on small and medium
  businesses in Israel; small shifts from peak.
- Blonz (2022): critical-peak pricing for small commercial and industrial customers in California (seen only as a citation).

Data sources:
- https://opendata-ajuntament.barcelona.cat/data/en/dataset/consum-electricitat-bcn
- https://datos.gob.es/en/catalogo/l01080193-consumo-de-electricidad-mwh-por-codigo-postal-sector-economico-y-tramo-horario

## What a first look would involve (not started)

1. Download the seven Barcelona files and describe them (postal codes, units, gaps, sector shares).
2. Build the dose table per boundary, tariff and year from the toll resolutions and charge orders (2022–2026 tolls not yet read).
3. Find two or three retailer price sheets for 3.0TD to see whether the season steps reach the customer.
4. A noise check on non-boundary dates only, with the boundary windows sealed.
