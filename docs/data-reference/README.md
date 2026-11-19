# Data reference

The verified facts about each dataset, moved out of `CLAUDE.md` on 2026-11-12 so that
file stays short. The text was moved verbatim: nothing was rewritten, and the older
history is in git (`git log -- CLAUDE.md`). Read the file for the source you are about
to touch **before** touching it; the traps are the cheapest way to avoid a silent error.

| File | Covers |
|---|---|
| [`scripts.md`](scripts.md) | every fetch / build / QA script, its source, token need and output |
| [`omie-market-data.md`](omie-market-data.md) | day-ahead prices, bid curves, unit registry, `cab`, PDBF, intraday bids and prices |
| [`ownership-and-units.md`](ownership-and-units.md) | who controls a bid, OMIE unit lists, direct consumers, cogeneration, technology coverage |
| [`ree-ren-esios-miteco.md`](ree-ren-esios-miteco.md) | REE, REN, ESIOS indicators and archives, MITECO reservoirs |
| [`costs-and-hydro.md`](costs-and-hydro.md) | implied gas/coal cost, hydro cost, JRC hydro, SNIRH, E-OBS, HydroBASINS |
| [`outages-renewables-other.md`](outages-renewables-other.md) | outages, wind/solar locations, holidays, PDVD, France, Italy, GB, GIE, `indisp`, interconnection |
| [`goiener-household-smart-meters.md`](goiener-household-smart-meters.md) | GoiEner household smart-meter series, tariffs, 3.0TD pre-period gap |
| [`barcelona-electricity-by-postal-code.md`](barcelona-electricity-by-postal-code.md) | Barcelona consumption by postal code, sector and six-hour band (unit kWh, not MWh) |
| [`eredes-consumption-by-voltage.md`](eredes-consumption-by-voltage.md) | Portugal 15-minute load by voltage (2023+), monthly billed HV vs BT (2020-11+), retailer-control check |
| [`traps.md`](traps.md) | every silent-failure trap, the whole-day dropouts, audit exceptions |

Related: [`../unit-agent-mapping.md`](../unit-agent-mapping.md) (the agent mapping in full),
[`../../scripts/README.md`](../../scripts/README.md), [`../../data/README.md`](../../data/README.md).
