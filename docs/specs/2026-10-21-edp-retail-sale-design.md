# EDP's sale of its Spanish retail business as an event study of its stake

**Status: data checked 2026-10-21 (a scratch script, not committed; no estimates). The premise
fails, and I recommend not building it.** §2 gives the facts, §3 what they mean, §4 what is left.
One fact matters beyond this door: the six Douro dams EDP sold on 2020-12-17 were still offered
inside EDP's `ADOURO` until 2021-09-08, and the ownership mapping counts them as EDP's (§3). Builds
on the fixed-step design (`notes/rq-fixed-step.md`) and dated ownership (`lib/unit_ownership.py`).

**The idea, in one example.** On 1 December 2020 TotalEnergies bought EDP's Spanish residential
retail business and two combined cycles. Suppose the retailer bought 1,000 MW of load that EDP's
plants supplied. After the sale, the same plants sell that 1,000 MW in the auction instead, so
EDP's net position n rises by 1,000 MW on a known date, for reasons that have nothing to do with
the hour's prices. A firm with market power then raises its offers; a price-taker does not. With
the fixed step and the ten-seed band, one firm and one date give an event study of β.

The checks below ask how far n moved at the date. It barely moved: what Total took off EDP's books
was about 300 MW of load and about 200 MW of output.

---

## 1. What the design needed from the data

- **A large step in EDP's n at 2020-12-01**, against its usual variation.
- **No other change to EDP's stake in the same weeks.**
- **EDP units in the fixed-step sample on both sides of the date.** The stake is the firm's, so
  all of EDP's units are treated, the Portuguese cascades included.

## 2. What the data show (checked 2026-10-21)

**The deal** (EDP market notification of 2 December 2020, via
[Executive Digest](https://executivedigest.sapo.pt/?p=135473);
[Argus](https://www.argusmedia.com/de/news-and-insights/latest-market-news/2106238-edp-sells-spanish-ccgts-power-and-gas-clients-to-total)):
the residential (B2C) portfolio, about 2.1 million power and gas contracts, plus Castejón 1 and 3
(425 + 418 MW), for an enterprise value of €515 million. Separately, EDP's 50% of the retailer CHC
Energía was due to go to its partner CIDE in February 2021.

**What moved in PDBF** (*Programa Diario Base de Funcionamiento*, the operating schedule), MW,
monthly means. EDP's Spanish retail units are all supplied on contracts by EDP's resale unit
`HCGC01`, which buys in the auction. None of the load came from EDP's own plants.

| unit (owner) | 2020-06 | 2020-10 | 2020-11 | 2020-12 | 2021-01 | 2021-06 |
|---|---|---|---|---|---|---|
| `NAGAC01` (EDP Comercializadora; sold) | 754 | 763 | 36 | 0 | 0 | 0 |
| `EDPCC01` (EDP Clientes; kept by EDP) | 0 | 0 | 739 | 675 | 729 | 1,199 |
| `HCENE01` (EDP Energía; the B2C book), supplied by EDP | 216 | 212 | 246 | 295 | 0 | 0 |
| `HCENE01`, supplied by Total's retailer `TGYEC01` | 0 | 0 | 0 | 0 | 329 | 201 |
| `CHCC01` (CHC; already a separate group), supplied by EDP | 133 | 130 | 147 | 169 | 191 | 123 |
| Castejón 1 + 3 output | 268 | 139 | 169 | 35 | 114 | 500 |

- **EDP moved its largest Spanish retail book to a company it kept, a month before the sale.**
  `NAGAC01`'s ~750 MW went to EDP Clientes in November 2020, and EDP Clientes grew to 1,200 MW
  by mid-2021.
- **What Total took was `HCENE01`'s book, about 250–330 MW.** From January 2021 Total's retailer
  supplies it, and Total's own purchases rose by about 450 MW (300–350 → 790).
- **Castejón went with it.** It produced about 200 MW on average in 2020 to November, 280 MW in
  2019H2.

So EDP's auction purchases fell by about 250–330 MW and its auction sales by about 200 MW: **n rose
by about +100 MW at the date**, give or take 100.

**Against EDP's usual variation** (`firm_x.parquet`, 2019-01 → 2021-08): EDP's n has a standard
deviation of 1,044 MW across days and 1,375 MW across hours. Monthly means run from −1,800 to
+500 MW (December 2020 −1,302, February 2021 +502). With EDP's median residual-demand slope of
450 MW per €/MWh, +100 MW is a stake (Zb) of about **€0.2/MWh**. In the fixed-step rows
(2019-01 → 2021-07), EDP's Zb has a within-month standard deviation of €2.3–9.7, and its monthly
mean runs from −5.5 to +4.6.

**The fixed-step rows are there**: 7 EDP units (`ACAVADO`, `ADOURO`, `ALIMA`, `GUADIA`, `HCHI`,
`MONDEGO`, `TEMON`; only `HCHI` is Spanish), about 5,000 unit-hours a month, 600–3,000 a month in
the main sample.

**A second EDP sale in the same month.** EDP sold six Douro plants (1,689 MW) to Movhera, an
ENGIE-led consortium, on 2020-12-17
([EDP](https://edp.com/en/investors/investor-information/market-notifications/edp-concludes-sale-portfolio-6-hydro-plants)).
In the data they stayed inside EDP's `ADOURO` until 2021-09-08. Its `cab` max power was 2,849 MW
to that day and 1,147 MW from 2021-09-09, when Movhera's `DOUSUP` (1,709 MW) first appears.
`ADOURO` produced 885 MW in December 2020, 1,994 MW in February 2021, 1,529 MW in March and
520 MW in June. The dams are about 60% of its capacity.

## 3. What this means

- **The sale is not an event for EDP's stake.** EDP had moved the larger book to a company it
  kept. The load it did lose was about the size of the output it sold with it. A step of about
  +€0.2/MWh in Zb sits under a within-month spread of €2–10. Even at β = 1 (Nash), offers would
  move €0.2. An event study of one firm on one date cannot see that.
- **The premise was wrong about the routing.** EDP's Spanish plants never supplied the retailer
  directly: the retail load was bought in the auction through the resale pair. So the sale could
  not move plant output into the auction, as the example assumed.
- **The Douro dams are a measurement problem for EDP in 2020-12-17 → 2021-09-08.** Movhera owned
  them, EDP offered them, and `lib/unit_ownership.py` counts `ADOURO` wholly as EDP's. If EDP
  offered them for Movhera's account, EDP's measured n is too high by Movhera's output in those
  months. If output splits like capacity, that is about 500–1,200 MW from December to March and
  about 300 MW in summer: a Zb of about €0.7–2.7/MWh, against the sale's €0.2. Nothing public says whose account it was. It touches EDP's cells in 2020H2 and
  2021H1 in the fixed-step and simulation notes, and every EDP panel built on dated ownership.
- **The ownership mapping misses the B2C company.** `ENTITY_CHANGES` moves `EDP COMERCIALIZADORA`'s
  units to TotalEnergies from 2020-12-01. But the book Total took sits on `HCENE01`, owned by
  "EDP ENERGÍA S.A." in the listings until 2022-02-08 and "TOTALENERGIES MERCADO ESPAÑA" from
  2023-05-16. `HCENE01` buys only on contracts (from EDP before, from Total after), so n, which
  counts the auction, is unaffected. A measure of EDP's own load built from its retail units'
  schedules (as in the holiday and own-wind panels) counts about 200–330 MW of Total's customers
  as EDP's from 2021.
- **CLAUDE.md dates the Douro move to January 2022.** The `cab` break is on 2021-09-09.
  (`hydro_cost_daily`'s spell flag puts it in 2021-10, the month after.)

## 4. What is left, and whether to build it

| residual | worth building? |
|---|---|
| The sale as an event study of EDP's offers | No. The stake moves about €0.2/MWh. |
| The Douro dams, offered by EDP for Movhera from 2020-12-17 to 2021-09-08 | Not as a design: whose account they were offered for is not public, and the second date falls in the crisis. As a correction, yes (below). |
| `HCENE01` in EDP's own-load measures from 2021 | A one-line ownership fix (dated change for `HCENE01` to TotalEnergies at 2021-01-01, where the supplier switches). |

**Recommendation: do not build the design.** Two corrections are worth making, each a separate
change proposed before it is run:
1. **`ADOURO` from 2020-12-17 to 2021-09-08**: either leave the dams in EDP's n and say so, or
   take Movhera's 60% share of `ADOURO` out of EDP's n for those months (`UNIT_CHANGES` with a
   share). Then rerun the EDP cells that touch the window. My recommendation is the share, as a
   check, since EDP's 2021H1 results rest on it.
2. **`HCENE01` to TotalEnergies from 2021-01-01**, and fix the Douro date in CLAUDE.md.

**Done 2026-10-21:** both ownership fixes are in `lib/unit_ownership.py`. `UNIT_SHARES` gives
Movhera 60% of `ADOURO` from 2020-12-17 to 2021-09-08. An `ENTITY_CHANGES` entry dates EDP
Energía to TotalEnergies from 2021-01-01; it covers all 24 of its units, as the 2023 listing
does, and only `HCENE01` carries volume. Both are pinned in `qa/check_unit_ownership.py`. The
Douro date is fixed in CLAUDE.md. No panel has been rebuilt yet. Under the fix, `majority_group`
names Movhera for `ADOURO` inside the window.

**Stage 1 rerun (2026-10-21).** Rebuilt with the fixes: `firm_residual_demand_full_owner`,
`firm_incentive_net` and `firm_x`. The old files are in `outputs/cache/backup/2026-10-21-ownership/`.
Only EDP's rows from 2020-12-17 to 2021-09-08 changed (6,383 periods), and Movhera appears as a
group in `firm_incentive_net` over the same days. Nothing else moved; the `HCENE01` change moves
none of these panels. EDP's stake inside the window:

| | Dec 2020* | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug |
|---|---|---|---|---|---|---|---|---|---|
| n, old → new (MW) | −1,302 → −1,575 | −881 → −1,511 | +502 → −694 | −194 → −1,112 | −844 → −1,408 | −1,817 → −2,140 | −1,339 → −1,652 | −1,576 → −1,954 | −1,522 → −1,833 |
| X, old → new | −4.1 → −4.5 | −4.2 → −6.2 | +2.5 → −2.5 | −1.5 → −4.9 | −3.5 → −5.3 | −8.0 → −8.8 | −6.3 → −7.0 | −8.9 → −9.6 | −9.1 → −10.0 |

\*From the 17th. On average n falls by 563 MW and X by 1.8. EDP is a net seller in 10% of
the window's periods, against 26% before; 15% of periods switch from seller to buyer. Over
2021H1 its mean X goes from −3.6 to −5.9. The residual-demand slope rises 5–12%, because
Movhera's share of `ADOURO` now counts as a rival's offers.
`check_exposed_position.py` passes. `check_unit_ownership.py` fails on one item, as it should:
the stored leg A panel (`edp_hydro_panel`) still carries the old X on 42,807 EDP rows inside the
window. Not rebuilt yet: leg A, the leg C/D panels and tests, and the step caches. The fixed
step's Zb is computed from the step caches, not from `firm_x`.

**Stage 2 rerun (2026-10-21): legs A, C and D.** Logs in `.superpowers/logs/rerun-2026-10-21/`.
Every check passes, `check_unit_ownership.py` included once leg A's panel was rebuilt. That check now
expects `ADOURO` → Movhera inside the window.
- **Leg A** (`edp_hydro_panel.py --attach-x`, then the four leg A scripts, before and after). Inside
  the window `ADOURO` takes Movhera as its group and has no X, so about 6,100 of its unit-periods
  leave the X-based samples. Within-day β at 50% of offered volume, pooled: +0.089 [−0.13, 0.33]
  before and after; 2021–2023 −0.019 → −0.017. At 75%: +1.351 → +1.357. Quantity at the median,
  pooled: −0.074 → −0.075 pp per €/MWh of X (implied β +0.03 both). Markup bound p90: 1.74 → 1.75.
  Leg B, across days: no first stage before or after (F ≤ 4.8). Nothing changes a conclusion.
- **Leg C.** The committed `leg_c_results.csv` predates commit 0850a60 (2026-10-05: Portugal's
  thermal plants, the cost known at bidding), and leg C had not been rerun on it. To separate the
  fix, leg C was also run on current code with the old ownership and the old firm panels. Pooled β:
  3.094 committed (n 363,867), 2.900 on current code with the old ownership (n 545,217), 2.902 with
  the fix [2.49, 3.18]. Largest move from the fix in any row: 0.37, on the variant whose slope moves.
  So the new table differs from the committed one because of 0850a60, not because of the fix; β ≈ 3
  still holds.
- **Leg D.** Code and inputs are unchanged since the committed results; the rebuilt rival files
  differ only by two new Turbogás columns. So the diff is the fix: `ADOURO`'s 6,132 window rows
  move from EDP to the fringe. Pooled g₊ 4.21 → 4.32, g₋ −1.62 → −1.63; EDP g₊ 5.57 → 6.66, g₋
  −2.41 → −2.77. The weak-instrument readings and the empty common AR sets are as before.

**Stage 2 rerun: the fixed step.** The ten window months were rebuilt, with `ADOURO` left out over the window. One of 318 ten-seed readings changes: a profile cell at 1.5 cf_s in the departure periods no longer differs. The EDP and 2021H1 cells move but keep their readings (`notes/rq-fixed-step.md`, "Rerun on corrected ownership").

**Stage 3 (2026-10-22): Castejón's represented units.** `CTJON1R` and `CTJON3R` ("CC. CASTEJON1
REPR", "CC CASTEJON 3 REPR") were BAJA and still listed under EDP España to 2022-02-08, and
TotalEnergies Gas and Power's on 2025-01-31. They offer from 2024-02-01 and clear from 2024-02-05,
after CTJON1/3's last offer on 2024-01-31, so the nearest preceding listing (2022) gave a year of
Castejón back to EDP. `UNIT_CHANGES` now dates them with CTJON1/3 at 2020-12-01, and a dated unit
sale takes effect at the first later listing whose group differs from the seller's; only these
two units' spells change. Rerun with `.superpowers/sdd/2026-10-22-castejon-rerun/chain.sh` (logs in
`.superpowers/logs/rerun-2026-10-22/`); every check passes.
- **Firm panels.** Only EDP's rows change in `firm_x`: 2,050 periods, 2024-02-01 → 2025-01-30. Over
  the clean periods n goes from −814 to −934 MW (December 2024: −468 → −890), the net-buyer share
  from 0.784 to 0.824, and the sign flips in 4.0% of periods (18% in December). X's median goes
  from −2.33 to −3.05; the slope barely moves (708 → 710). In `firm_incentive_net`,
  TotalEnergies' cleared sales on the changed firm-periods go from 10 to 545 MW.
- **Leg A.** Within-day β at 50% of offered volume, pooled: +0.089 → +0.091 [−0.13, 0.33]; at 75%:
  +1.357 → +1.378 [0.78, 2.10]. Quantity at the median, pooled: −0.075 → −0.076 pp per €/MWh of X
  (implied β +0.03 both). Markup bound p90: 1.75 → 1.74. Leg B, across days: still no first stage
  (F ≤ 3).
- **Leg C.** Unchanged, byte for byte: its panel has no EDP rows in the window, and the R units
  have no plant-specific efficiency.
- **Leg D.** 15,434 unit-hours move from EDP to the fringe. Pooled g₊ 4.32 → 4.53, g₋ −1.63 →
  −1.63; EDP g₊ 6.66 → 7.95, g₋ −2.77 → −2.98. No row's status, sign reading or common AR set
  changes. The forecast-instrument table and the two first stages (`forecast_first_stage`,
  `hydro_rain_first_stage`) had last been run on 2026-10-05, so their diffs also carry the
  stage 2 changes; no reading changes there either, and no first stage crosses F = 10.
- **Fixed step.** None of the 318 ten-seed readings changes (`notes/rq-fixed-step.md`, "Rerun for
  Castejón's represented units").

No recorded conclusion moves.

**Left to whoever picks this up:** whether EDP Clientes' growth to 1,200 MW by mid-2021 took in
business customers from the sold company; whether anything public (EDP's 2020–21 reports,
Movhera's licence transfer) says who bore the dams' price risk before 2021-09-09.
