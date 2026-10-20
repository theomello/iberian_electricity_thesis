# Feed-in tariff exits (design 4): checked before building — not viable in this window

2026-10-20. The fourth of the designs chosen that day for sharper identification (the first
three: `rq-regional-holidays.md`, `rq-mic-near-miss.md`, `rq-france-link.md`, all stopped). Goal
agreed with the user: a within-firm test of EDP's buyer-side markdown (β⁻), from EDP's Portuguese
wind farms leaving their guaranteed tariffs on dates fixed when they were licensed. No spec was
written: the facts below came first.

## What the idea needed

A wind farm under a guaranteed tariff sells at a fixed price through the regulated supplier
(SU Eletricidade, OMIE unit `EDPSVD1` "VENTA RE"), so its output is outside its owner's stake in
the price. When the tariff ends, the farm earns the market price for its owner. EDP is a net
buyer in most hours, so each exit makes it less of a buyer, most in windy hours; a markdown
should shrink, a price-taker's offers should not move.

## What the data and the rules say

- **Who owns Portuguese wind** (e2p, INEGI/APREN, open WFS, CC BY-NC-ND; 268 farms, 6.0 GW):
  Finerge 1.6 GW, EDP Renováveis 1.4 GW, Ventient 0.9, Trustenergy 0.5, Generg 0.5, Iberdrola
  0.09. Start years mostly 2004–2010. Of the large firms only EDP has a material dose.
- **The tariff does not end at year 15 for EDP's farms.** EDPR's own briefing of 3 September 2012
  (the 2012 agreement later enacted through Decreto-Lei 35/2013): 615 MW of EDPR's Portuguese wind
  were under the old regime (DL 33-A/2005), whose 15 years run from February 2005 or the start of
  operation if later. EDPR chose a **7-year extension (years 16–22)** in which each MWh is paid
  the **day's average market price, but no less than €74/MWh and no more than €98/MWh** (June-2020
  terms, indexed to inflation). Full market exposure starts in year 23: **2027–2032 for these
  farms, after the window** (data end 2026-05; step caches 2025-09). Farms tendered later (ENEOP)
  were outside the agreement.
- **Inside the extension the stake exists only on days the average price falls in the band.**
  Share of days with the Portuguese daily average price within the band (as set, and +20% for
  inflation as an upper bound):

  | year | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
  |---|---|---|---|---|---|---|
  | in the band | 0% | 18–24% | 4–11% | 29–41% | 21–22% | 21–24% |
  | above the cap | 0% | 33–42% | 83–92% | 15–43% | 8–20% | 7–18% |

  And the exposure is to the *daily average* price, so a day's output is exposed to every hour
  equally, not to its own hour.
- **OMIE shows no EDP unit whose Portuguese renewable sales grow** as tariffs reach year 15:
  EDP's only special-regime sale units in Portugal (`EDPGPV2`, `LEZIV02`, `EDPV2`) sell under
  0.3 TWh a year, while `EDPSVD1` still sells 16–19 TWh. Most likely extension-period output is
  still sold by the regulated supplier, and only the settlement changes (an inference, not
  checked against the rules).

## Why it is not built

At most 615 MW of EDP wind, about 170 MW of average output, gains a stake on about a fifth of
days. At a slope of about 500 MW per €/MWh that moves EDP's stake by about €0.3/MWh on those
days. Nash would then move EDP's offers by €0.3. The France design moved stakes by about €3.4
in 30% of hours and could detect nothing below β = 2–10 (`rq-france-link.md` §2.2); this one is
an order of magnitude smaller, and the in-band days are chosen by the price itself.

**When it would work**: from 2027, as the extensions end and the farms sell at the market price
for good. With the bid archive's three-month lag, that is data from about 2028 on.

## What was done

- The data request to DGEG and ERSE is drafted (`email-dgeg-fit-dates.md`) and **on hold**: the
  farm dates matter for the post-2027 version, not for anything testable now.
- Sources: EDPR, *Wind sector and Portuguese Government reached agreement for the extension of
  the remuneration framework*, 3 Sep 2012 (copy at
  `https://www.edp.com/sites/default/files/document/2025-03/PortugueseRegulationEN.pdf`);
  Decreto-Lei 35/2013 (Diário da República); e2p WFS
  (`https://dservices5.arcgis.com/AMh9EzyFGgthLT1q/arcgis/services/e2p/WFSServer`).
