# The clawback's contract exemption as a dated shift in firms' stakes

**Status: data checked 2026-10-21 (a scratch script, not committed; no estimates). The premise
fails, and I recommend not building it.** §3 gives the facts, §4 what they mean, §5 what is
left. Two of the facts are worth keeping whatever is built: physical bilateral shares follow the
clawback and gas-cap rules, and the earlier levy design measured exemption wrongly (§4). Builds
on `notes/rq-hedge-ratios.md` (the stop in 2021H2) and `notes/rq-gas-cap-conduct.md` (Design 4,
`analysis/levy_contract_exposure.py`).

**The idea, in one example.** From September 2021, Spanish hydro and nuclear output paid a
clawback (RDL 17/2021, *Real Decreto-ley*) on every MWh produced, set each month by how far the gas
price sat above €20/MWh. Output sold forward at a fixed price to a third party was later exempted. So a seller
like Endesa gained by moving hydro out of the auction into fixed-price contracts after the
exemption. Each MW sold that way leaves the day-ahead market and lowers the firm's net position
n by a MW. The reason is a tax, and it arrives on a known date. Two uses would follow:

1. **a dated shift in n** for an event study of offers, like the reactor outages but firm-wide;
2. **an explanation of why the sellers' hydro markup stops in 2021H2**: if firms sold forward
   after the exemption and the contracts were financial, n overstates their stake in the crisis
   (`rq-hedge-ratios.md`).

The checks below ask whether contracts moved at the dates. Third-party contracts did not. The one
dated change moved cover between two routes inside a group, which leaves n where it was.

**Correction to the door-2 proposal.** It said the earlier clawback notes used only the 10 MW
threshold. They also used the exemption: Design 4 (`rq-gas-cap-conduct.md`) took each unit's
pre-levy contract share as its exposure to the levy. §4 shows that measure is wrong.

---

## 1. What the design needed from the data

- **Third-party fixed-price contracts that rise at the exemption dates**, on the firms' hydro and
  nuclear, larger for the firms the clawback hit hardest.
- **Visible in the operating schedule**: PDBF (*Programa Diario Base de Funcionamiento*) role 4,
  the physical bilateral contracts. If they are not visible there, OMIP (the Iberian forward
  exchange) volumes should at least rise market-wide.
- **n moving with them**, since n is what the conduct tests use.

## 2. The rules, by date

| date | rule | what it rewards |
|---|---|---|
| 2021-09-16 | RDL 17/2021: clawback on peninsular non-emitting output above 10 MW without a regulated regime, per MWh produced, "whatever the form of contracting" (art. 6) | nothing yet |
| 2021-10-27 | RDL 23/2021 (published that day): fixed-price forward contracts signed before 16 Sept 2021, and later ones of at least a year, exempt; physical or financial. Sales to the group's own retailer stay subject (Andersen's and Garrigues' notes on the decree). In the consolidated text, exempt energy is counted against **the group's net selling position**, and contracts that name no plant are spread over the owner's plants (DA 8ª.2–3) | fixed-price sales to third parties |
| 2022-03-31 | RDL 6/2022: new contracts exempt only at or below €67/MWh. **Energy passed to the group's own retailer** ("bilateralizada", physically or by an equivalent intra-group hedge) is now priced at what the retailer charges consumers. It is clawed back only on the excess over €67 plus the sector's average retail margin (consolidated text, DA 8ª.4; method in CNMC CNS/DE/595/22, 12 May 2022) | passing own output to own retailer on contracts below €67 + margin |
| 2022-06-15 | RDL 10/2022, the gas cap: buyers pay the cap's cost. Energy of fixed-price retail contracts signed before 26 April 2022 and passed intra-group is exempt (art. 8.6; from search summaries of CNMC documents, not read) | passing own output to own retailer, again |

Sources: [BOE consolidated text of RDL 17/2021](https://www.boe.es/buscar/act.php?id=BOE-A-2021-14974);
[Andersen on RDL 23/2021](https://es.andersen.com/supuestos-de-exclusion-de-la-aplicacion-del-mecanismo-de-minoracion-del-exceso-de-retribucion-del-mercado-electrico/);
[CNMC CNS/DE/595/22](https://www.cnmc.es/sites/default/files/4113358.pdf);
[Garrigues on RDL 6/2022](https://www.garrigues.com/es_ES/noticia/real-decreto-ley-62022-principales-medidas-sector-electrico-generacion-energia-electrica).
The pre-RDL 6/2022 wording on intra-group sales was not read in the BOE itself.

This corrects `rq-hedge-ratios.md`, which dated the exemption from 2021-09-16. The clawback
started then; the exemption came on 2021-10-27.

## 3. What the data show (checked 2026-10-21)

Each group's hydro (storage and pumped) and nuclear, by dated ownership (`lib/unit_ownership.py`;
a co-owned reactor's sale to a co-owner's retailer counts as that co-owner's own). PDBF role 4 sell
legs paired with their buy legs by contract id. Monthly mean MW. Each cell is the % to own
retailers / the % to third parties:

| month | Iberdrola | Endesa | Naturgy | EDP* | Repsol |
|---|---|---|---|---|---|
| 2021-06 | 74 / 0 | 71 / 0 | 0 / 0 | 49 / 6 | 0 / 0 |
| 2021-09 (clawback) | 78 / 0 | 94 / 0 | 0 / 0 | 52 / 8 | 0 / 0 |
| 2021-12 (after the exemption) | 83 / 0 | 85 / 0 | 2 / 0 | 38 / 7 | 0 / 0 |
| 2022-03 | 83 / 0 | 91 / 0 | 14 / 0 | 53 / 6 | 0 / 0 |
| **2022-04 (own retail at €67 + margin)** | 87 / 0 | 88 / 0 | **62** / 0 | 56 / 6 | 0 / 0 |
| 2022-07 (gas cap) | 92 / 0 | 96 / 0 | 93 / 0 | 74 / 0 | 0 / 0 |
| 2022-12 | 86 / 0 | 68 / 0 | 96 / 0 | 36 / 0 | 0 / 0 |
| 2023-06 | 93 / 0 | 80 / 0 | 96 / 0 | 55 / 0 | 0 / 0 |

\*EDP's hydro is mostly Portuguese, outside the clawback.

**No third-party contracts appeared.** No group sold its hydro or nuclear to a third party on a
physical contract at any date, apart from EDP's 120–180 MW, which ended in June 2022. Iberdrola and
Endesa had 70–95% of this output on contracts with their own retailers before the clawback, and
it stayed there through every date.

**The one dated change is Naturgy's, and it is a change of route.** MW to own retail / MW scheduled:

| | 2022-02 | 2022-03 | 2022-04 | 2022-07 | 2022-10 | 2023-01 |
|---|---|---|---|---|---|---|
| nuclear | 0 / 567 | 26 / 568 | **400 / 566** | 519 / 555 | 420 / 450 | 391 / 538 |
| hydro | 60 / 209 | 79 / 199 | 87 / 220 | 117 / 129 | 123 / 125 | 1,050 / 1,083 |
| wind and solar | 0 | 0 | 0 | 138 / 466 | 282 / 519 | 400 / 628 |
| resale pair `GGNCOV1` to own retail | 2,557 | 2,397 | 1,910 | 1,797 | 1,175 | 483 |

The reactors switched in the month RDL 6/2022 took effect. Hydro moved gradually from December
2021, and wind and solar from July 2022. What they replaced was cover Naturgy's retailer had bought
through its generic resale pair. That pair buys energy and passes it to the retailer on a
contract (`rq-self-supply-cost.md`: each sale unit is matched hour by hour by a purchase twin).
The retailer's total contract cover stayed at about 2.0–2.6 GW.

**Naturgy's net position did not move at the date**: −1,609 MW in March 2022, −1,307 in April,
−1,439 in May (`firm_x.parquet`). When a group's own plant supplies its own retailer, both legs
leave the auction. The large moves come later. Naturgy's n rose from about −1,400 to about +1,000
MW, and EDP's from −1,700 to near 0, in June–October 2022. Over the same months their thermal
plants' schedules, mostly combined cycles, rose (Naturgy 380 → 2,640 MW, EDP 800 → 2,560 MW,
April/May → July). That is the
gas cap's months, not a contract change. EDP's resale pair to its own retailer ended at the same
time (2,100 MW in May, 0 from July). Not decomposed further.

**Exchange-traded forwards fell rather than rose.** OMIP's Spanish base-load futures traded
0.7–1.3 TWh a month in 2021 and 0.02–0.16 TWh in 2022. Registered over-the-counter volume stayed
at 0.2–1.6 TWh a month (apart from 4–6 TWh in April–May 2021), with no rise after 2021-10-27. These are market-wide figures, not by firm.

## 4. What this means

- **The exemption gives no dated shift in n.** The contracts that would move n, fixed-price sales
  to third parties, did not appear physically at any date. The one dated change, Naturgy's in
  April 2022, moved cover between two routes inside the group and left n where it was.
- **No support for the hedge explanation of the 2021H2 stop.** No physical contracting at
  2021-10-27, and no rise in exchange volumes. Financial contracts by firm remain unseen
  (`rq-hedge-ratios.md`: CNMC redacts the exempt volumes). This agrees with the hedge-ratio note.
- **Physical bilateral shares follow the rules, so do not read them as hedge ratios.** Whether a
  group supplies its retailer from its own plant on a contract, or through a resale pair that
  buys in the auction, changed with the clawback (April 2022) and the gas cap (June 2022). The net
  position is the same either way. Only the route, and the tax, differ.
- **Design 4 measured exemption wrongly** (`levy_contract_exposure.py`, `rq-gas-cap-conduct.md`).
  Its exposure is one minus the role-4 share of a unit's own output before September 2021. That
  reads Naturgy's three hydro units (`UFGC`, `UFMI`, `UFTA`), EDP's `HCHI` and Repsol's three
  (`GRDZ`, `TRCD`, `VIES`) as 0% covered. Yet their retailers were covered through resale pairs.
  The cover it does count, on Iberdrola's and Endesa's units, all goes to their own retailers.
  Under RDL 23/2021 that cover was not exempt before 31 March 2022. So in the levy's first six
  months the treatment variable measured routing, not exemption. The design was already shelved
  ("reduced form exhausted"). This is a further reason not to revive it as it stands.

## 5. What is left, and whether to build it

| residual | worth building? |
|---|---|
| Naturgy, April 2022, as a routing test: n unchanged, its auction sales and the resale pair's purchases each about 400–500 MW lower. The framework says offers should not move. | No. Its reactors offer at €0, so they have no margin to test. Its hydro moved gradually, not on the date, and ran 125–220 MW in 2022. The gas cap starts ten weeks later. And it is one firm. The fixed-step note's Iberdrola result already covers routing. |
| The gas cap's own pull towards intra-group cover (June 2022) | Belongs to a gas-cap chapter, if there is one. Not a conduct test. |
| Third-party financial forwards by firm | Not public. The one piece that could be: the results by firm of the RDL 17/2021 forward auctions (searched 2026-10-21, not found). |

**Recommendation: do not build the design.** Record §3 as facts about the data. Three consequences:
- the clawback gives the conduct tests no instrument for n;
- role-4 shares are routing, set partly by regulation, and should not stand in for hedging;
- Design 4's exposure measure should not be reused.

**Left to whoever picks this up:** decomposing Naturgy's and EDP's mid-2022 net-position rise
into combined-cycle sales and retail purchases; the months beyond 2023-12, when the clawback ended.
