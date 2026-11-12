# OMIE market data: prices, bids, cab, PDBF, intraday

_Day-ahead prices, bid curves, unit registry, `cab`, PDBF, intraday bids and prices. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

### OMIE day-ahead prices — complete
91,247 rows, 3,073 days, zero missing. Columns: `date`, `period`,
`price_pt`, `price_es`, `utc_timestamp`, `resolution_min`.
Spain mean 73.31 €/MWh, range −15.00 to 700.00. ES and PT differ in 6.7% of
periods (market splitting).

### OMIE bid curves — complete to the publication frontier
**102 months 2018-01 → 2026-06, 382,400,912 rows, uniform schema.** Refreshed
2026-09-28; the clearing-identity gap is 0.00% on both new months.

The frontier is **2026-06-29**, 91 days before the refresh — the same
**~3-month publication lag** measured at the first fetch (2026-05-08 on
2026-08-07), as expected for commercially sensitive unit-level offers. No daily
bid files exist (the listing has none, and direct fetches 404); OMIE extends the
frontier month's zip as days are released.

The first fetch left May 2026 at 8 days, and re-running did **not** extend it
until 2026-09-28 — see the frontier-zip trap. Re-running now does. The last ~3
months of any other series will never have matching bids at the time of a
fetch; re-fetch prices, REE and REN before using June 2026.

Unit-level day-ahead offers for **both** Spanish and Portuguese units, since
MIBEL clears jointly. ~2.3–3.6 M rows/month in the hourly era, ~14 M/month
from 2025-10 when the 15-minute MTU quadrupled the period count.

Columns: `date`, `period`, `hour`, `quarter`, `resolution_min`, `country`,
`unit`, `side`, `power_mw`, `price_eur_mwh`, `status`, `offer_type`.

Both accepted and rejected offers are present — that is the point. In a
single hour (2024-01-01 h12) 63,599 MWh was offered against 24,872 MWh
cleared; the gap is the unaccepted supply.

`power_mw` unifies the two eras: hourly files publish MWh over one hour,
numerically identical to average MW. Derive energy as
`power_mw * resolution_min / 60`.

### OMIE unit registry — the key to the bid data
`data/omie/registry/unit_registry.parquet`, built by
`build/build_unit_registry.py` from `pdbc` + `pdbcpt` + `pdbce`. **5,137 units**
over the window (rebuilt with `--full` on 2026-08-12; the earlier 2-day-per-month
sample gave 5,049), columns `unit, country, role_code, role, group_tag,
first_seen, last_seen, days_observed, net_cleared_mwh`.

- **country** — ES 4,960 / PT 150 / 27 unknown. The ES and PT unit sets are
  **disjoint** (zero overlap), so membership is a clean assignment. This is
  the only reliable way to select Portuguese units.
- **role** — generation 3,719, purchase_retail 770, purchase_other 354,
  generation_large 211, storage_mixed 45, pumping 22. Decoded from cleared
  quantity sign/volume, constant within a unit. Separating **generators from
  retailers** is what any supply-curve or bidding work needs.

  **Supply is spread over FOUR roles, and `generation` alone is the wrong
  filter.** `role == "generation"` reads like "keep the generators" and in fact
  drops **all 62 combined-cycle units (29.6 GW), all 7 nuclear (7.2 GW), the 44
  hydro cascade units (14.2 GW) and every pumped-storage unit** — Ascó 1 is
  `generation_large`, not `generation`. What survives is wind and solar, which
  offer at zero, so any bidding measure built on it collapses to a mass point
  at €0 and shows no merit order. Cost a day on 2026-08-18 before it was
  caught. Use `generation`, `generation_large`, `storage_mixed`, `pumping` —
  see `SUPPLY_ROLES` in `scripts/analysis/capacity_quantile_offer.py`.
- **group_tag** — corporate tags (`IB`, `REP`, `GE`, …), 9 distinct,
  populated for only some units.

Validated against Jan-2024 bids: **99.2% of units and 95.1% of cleared volume
match**, `purchase_retail` units never appear on the sell side, and
`storage_mixed` sells a small volume — all consistent with the decoding,
which was derived without reference to those tests.

**No fuel or technology, and no nameplate capacity — in the registry.** The
role code separates generation from demand and isolates storage but will not
distinguish a CCGT from a wind farm.

**Both are now available from `cab` instead** (2026-08-11), token-free — see
the OMIE offer-header section below. `cab` publishes a descriptive plant name
whose prefix encodes technology (`C.C.` ciclo combinado, `C.N.` central
nuclear, `C.T.` térmica, `UOF HIDRO`/`C.H.` hydro, `PS`/`FV` solar, `PE` wind)
and a max-power column validated against published figures. ESIOS/ENTSO-E
tokens are **not** needed for this. The registry itself has not yet been
rebuilt on `cab`.

Now built with `--full` (every day). The earlier default was a
**2-day-per-month sample** (1st and 16th), which left ~5% of cleared volume
with unmatched units. The full parse added 88 units and better first/last-seen
dates, but **not** more `group_tag` coverage — still 9 distinct tags. The tag
is sparse at source, not sparse from sampling.

### OMIE `cab` — the offer header, and what unlocks unit attributes
`data/omie/cab/parquet/`, **113 months 2017-01 → 2026-05, 5,954,579 rows**,
fetched 2026-08-11. One record per unit per day. Token-free.

This is the header accompanying the day-ahead offers in `curva_pbc_uof`, and
it carries three things nothing else token-free publishes:

- **Descriptive plant name** — `ESCCC1` → "C.C. ESCOMBRERAS 1". Technology is
  in the prefix (see the registry note above).
- **Max power in MW** — validated: Ascó 1 reads 1028.0 (published ~1032),
  Escombreras 1 reads 408.6 (~400).
- **The minimum income condition**, as a fixed term (€/day) and a variable
  term (€/MWh). This is the complex condition behind the whole-day withdrawals,
  and the primitive Reguant (2014) uses to identify startup costs.

Fixed-width, latin-1, **dot decimal** — unlike `curva_pbc_uof`, which uses a
comma. Do not share a number parser between them. **Two layouts: 169 chars
until 2025-03-18, 94 chars from 2025-03-19** — see the trap below.

**The minimum income variable term ends at 2025-03-18 — because the market
design changed, not because OMIE withheld it.** Resolved 2026-09-03 from
OMIE's own published spec (see below). On 2025-03-19 the old complex condition
was replaced by the **SCO** (*Scalable Complex Order*) for the European single
day-ahead coupling, and the header now publishes **one** lump-sum `Fijoeuro` in
EUR instead of a fixed €/day plus a variable €/MWh term. The variable term no
longer exists as a separately declared parameter; what replaces it is the SCO's
own scalable price tranches in `det`, which from the same date carry a **MAV**
(Minimum Acceptable Volume) per offer.

**The two fixed terms are different quantities and must never be spliced.**
ABO1 (C.T. Aboño 1, 351 MW) declares 24,000 €/day fixed and 127.50 €/MWh
variable on 18 March, and a single 601,620 € on 19 March. Nor is it the same
population: across those two days 19 units declare a wide fixed term and 53 a
variable one, against 31 declaring an SCO fixed term. They are held in separate
columns, `min_income_fixed_eur` and `sco_fixed_eur`. So the conclusion is
unchanged in substance — **declared start-up costs on a consistent basis run
2017-01-01 → 2025-03-18** — but `sco_fixed_eur` is a usable primitive after
that date, not a hole.

Validated on January 2024: units declaring no minimum-income condition
withdraw for a whole day **4.1%** of the time; units declaring one, **81.1%**;
and units whose variable term exceeds the day's *highest* clearing price,
**94.2%**. The condition does what the market rule says it does.

**All nine numeric fields are now named**, from OMIE's own specification —
*Modelo de Ficheros para la distribución pública de Información pública*,
**v1.35** (the last edition describing the wide layout) and **v1.37** (current),
public PDFs at
`https://www.omie.es/sites/default/files/<YYYY-MM>/formato_ficheros_inf_pub_<v>.pdf`.
Of the six previously carried unnamed, **two are documented as unused** (verified
`0.000` on every row) and **four are ramp rates** — `MaxRamSub`, `MaxRamBaj`,
`MaxRamArr`, `MaxRamPar`. Do not get excited about the ramps: on 2025-03-18 only
5 of 2,454 units declare a non-zero up or down ramp and none declare a startup or
shutdown ramp, and **the spec gives no unit of measure**, so they are carried
under OMIE's field names without a unit suffix.

Fetch the spec before touching any OMIE fixed-width parser. Every position in
this repo's `cab` parser was reverse-engineered from the files until 2026-09-03,
and one of those guesses was wrong — see the whitespace-splitting trap below.

#### The minimum income condition is a *declared* start-up cost

Worth stating plainly, because it is the single most unusual thing in this
dataset. `cab` publishes, **per unit per day**, a firm's own statement of what
it needs to earn to run: a fixed term in €/day and a variable term in €/MWh.

The empirical literature treats that quantity as something to be *recovered*:

- Reguant (2014) models the optimal declaration of the condition in order to
  identify start-up costs structurally.
- Jha & Leslie, *Start-up Costs and Market Power: Lessons from the Renewable
  Energy Transition* (SSRN 3603627), build a dynamic competitive benchmark that
  estimates start-up costs from production data, and show that **static markups
  overstate the rents attributable to market power** when start-up costs are
  ignored. Their headline correction depends on a primitive they must estimate.

Here it is published daily. That is a genuine data advantage and it cuts both
ways for our own results: any static Lerner index computed in this repo is
**biased upward** for the same reason Jha & Leslie identify, and this file is
what would let the correction be made with a declared rather than an estimated
number.

**It is not marginal cost, and must not be used as one.** The declaration is a
strategic choice — that is precisely why Reguant models it. What it supports is
a *bound*: a firm that says it needs `fixed + variable × q` will not accept less,
so its avoidable cost is at most that, and `price − (variable + fixed/q)` is a
lower bound on realised markup, revealed by the firm itself.

Three limits on the selection. Only units that *declare* a condition give this
(53 of them on 2024-01-15, 48 of which are combined cycle — the marginal
technology, but a narrow and non-random slice). The condition binds on **daily**
revenue, not per period. And the declaring units are precisely those with
binding start-up costs, so the sample is selected on the variable of interest.

### `cab` names identify the bidding **agent**, not the plant owner
Unit codes carry a 3-character alphabetic mnemonic (`EDP`, `IBE`, `GGN`,
`GRE`, `EGE`) that identifies the market agent. **344 distinct prefixes across
3,940 generation units; 54 prefixes cover 80% of generation volume, 100 cover
94%** — so a hand-built mnemonic→firm dictionary is bounded work.

It cannot be learned from OMIE's own labels: `group_tag` covers 121 units
(18.8% of volume), and propagating it along prefixes reaches only **22.4%**,
because the labelled set excludes the largest players.

Two cautions. Several large prefixes are **traders representing third-party
assets** — `EGV` is Axpo, 394 units and 6.7% of volume — and unit names like
"UOF REPRESENTADA DE ARRUBAL 1" say so explicitly. And the largest units are
**owner-level portfolios**, not plants: `EDPSVD1` "VENTA RE" at 6,500 MW,
`IBEVD11` "EÓLICA HABILITADA" at 5,906 MW. For market power that is arguably
the right object — the agent controlling the bid — but it is *not* plant
ownership, and the two must not be conflated.

### OMIE `pdbf` — the operating schedule, and the contract position
`data/omie/pdbf/parquet/`, fetched 2026-08-13, token-free. Same field layout as
`pdbce`, so no new parsing was needed. One row per unit per period.

Columns: `date`, `period`, `resolution_min`, `unit`, `unit_id`, `schedule_mw`,
`role_code`, `group_tag`.

**Why it is here.** It publishes the **physical contract position** — energy
committed at a price fixed outside the auction. That is the `theta` term in
Wolak (2000) and Hortaçsu & Puller (2008): volume already sold forward earns
nothing extra when the day-ahead price rises, so a heavily contracted firm has
a weaker incentive to withhold whatever its share. Jha & Leslie spend an
appendix inferring it because Australian contracts are not public.

**`role_code == "4"` is the bilateral contract — read it directly, do not
compute PDBF minus PDBC.** Its sell and buy legs are exactly equal (0.0000 gap
in every month tested 2018–2026), which is the matching identity a bilateral
contract must satisfy and the subtraction cannot check.

| year | scheduled sell | under bilateral contract |
|---|---|---|
| 2018 | 413.6 TWh | **46.5%** |
| 2022 | 416.3 TWh | **48.5%** |
| 2024 | 346.7 TWh | **38.9%** |

**PDBF has several rows per unit-period, one per role code**, so
`(date, period, unit)` is *not* a key — joining cleared volume onto it without
aggregating first fans the auction volume across those rows. That produced a
spurious "36% → 5% collapse" in an early cut; the measured decline is 8pp.
Only role 4 carries a `group_tag`, and on those rows `unit_id` is the contract
id rather than the registration id.

**Still a proxy for theta, not theta.** It captures *physical* bilateral
contracts only and misses **financial** hedges entirely — an OMIP future or a
financially settled PPA fixes revenue while the energy still clears in the
auction. Since what matters is whether *revenue* is fixed rather than whether
electrons flow bilaterally, that omission is the more serious one. Bound it; do
not claim to measure it.

`--verify` re-derives PDBF against the auction per month and flags any month
where PDBF sell falls below cleared sell, which would be a parse failure rather
than a market fact. January 2024 gives **1.73×**, independently reproducing the
figure below.

**`schedule_mw` is average MW, not MWh** — see the trap below.

### CNMC publishes shares on PDBF, not on the day-ahead auction
**PDBF** = *Programa Diario Base de Funcionamiento*, the daily operating
schedule: the day-ahead auction result (**PDBC**, *Programa Diario Base de
Casación*) **plus bilateral physical contracts and self-scheduling**. On
January 2024 the PDBF sell total is **1.73×** day-ahead cleared volume.

Comparing CNMC's shares to day-ahead cleared shares therefore makes firms look
under-mapped when they are not. Measured on PDBF our mapping gives Iberdrola
22.2% against CNMC's 20%, Naturgy 5.2% against 6%, Acciona 4.3% against 4%.

This is economically substantive, not bookkeeping. For market power **in the
day-ahead auction** the relevant share is day-ahead exposure: volume sold
forward at a fixed price earns nothing extra when the day-ahead price rises —
the contract-position term in Wolak (2000) and Hortaçsu & Puller (2008). Using
PDBF-based shares **overstates** the day-ahead markup incentive.

OMIE publishes `pdbf` as its own dataset, same schema as `pdbce`, so a
like-for-like comparison needs no new parsing.

### The intraday session regimes overlap — they did not switch cleanly
MIBEL's own 6-7 intraday sessions and the European IDA auctions **ran in
parallel from 2025-03 to 2025-06**, and the two are distinguished only by the
width of the session digits in the filename: two digits (`01`..`07`) for the
old sessions, one (`1`..`3`) for IDA1-IDA3. Full changeover is 2025-07.

This bites twice. A regex requiring two digits returns **zero rows** for
2025-07 onward — which fails loudly — but during the overlap it silently
parses *part* of a month and reports success: 2025-06 yielded only 22 of 90
files that way, 2025-03 90 of 101, 2025-05 91 of 96. Audit member counts
against the zip rather than trusting a clean exit.

`session` is therefore **not comparable across the boundary**: 1-7 before,
1-3 after, with different meanings and an overlap period where both appear.

**Intraday adopted the 15-minute MTU on 2025-03-19, over six months before
the day-ahead market did (2025-10-01).** Corrected 2026-09-03: an earlier note
here said June 2025 and was simply wrong. Re-derived from `resolution_min` in
the files — 2025-03-18 is the last day carrying any 60-minute rows (it carries
both, the first quarter-hourly intraday auction having been held that afternoon
for delivery on the 19th) and every day from 2025-03-19 is pure 15-minute. The
two markets run at different resolutions for those six months, so read
`resolution_min` per file rather than inferring it from the date.

### OMIE intraday bid curves — complete
**102 months 2018-01 → 2026-06, 588,054,115 rows**, uniform schema — larger than the
day-ahead archive. Unit-level offers for each intraday **session**, where
wind and solar forecast errors get corrected after the day-ahead auction.

Same row format as the day-ahead files, so `parse_member` is shared; the
session index exists **only in the filename**
(`curva_pibc_uof_YYYYMMDD<SS>.1`) and is added as a `session` column. Rows
carry their own delivery date, which can differ from the filename date — the
row date is authoritative.

Cleared intraday sell volume is ~18% of day-ahead (Jan 2024), as expected for
an adjustment market. The frontier is 2026-06-29, the same as the day-ahead
bid frontier (refreshed 2026-09-28; it was 2026-05-11). A few session files are
published **empty** (e.g. session 4 on 2020-04-01) and correctly yield no rows.

Parsing is streamed one row-group per source file: the IDA-era months are
~17 M rows each and buffering a month in memory exhausts it.

### OMIE `marginalpibc` — published intraday prices, and why deriving fails
`data/omie/intraday_prices/omie_intraday_prices.parquet`, fetched 2026-08-21,
token-free. **411,263 rows, 2017-12-31 → 2026-08-20, sessions 1-6.** Columns:
`date`, `session`, `period`, `price_a` (Portugal), `price_b` (Spain).

**`price_a` is Portugal and `price_b` is Spain — the same PT-then-ES order as
`marginalpdbc`, confirmed from the data rather than assumed by analogy.** On the
864 periods of 2018 where *both* markets split, `price_a` sits 3.94 €/MWh from
the day-ahead PT price and 9.19 from ES, while `price_b` sits 2.71 from ES and
7.68 from PT.

**The intraday clearing price cannot be derived accurately from the bid
archive.** In a uniform-price auction it is bracketed by `max(cleared sell) ≤
p* ≤ min(cleared buy)`, but checked against the published files on 1,875
date-session-periods:

| estimator | median abs err | p95 | exact | mean err |
|---|---|---|---|---|
| max cleared sell | 0.010 | 7.802 | 48.8% | **+1.069** |
| min cleared buy | 0.000 | 3.876 | 53.7% | −0.651 |
| bracket midpoint | 0.245 | 7.139 | 22.2% | +0.209 |

The day-ahead/intraday premium is about 1 €/MWh, so a p95 error of 3.9-7.8
swamps it. And `max(cleared sell)` is a *lower* bound whose error should never be
positive — it is positive on 10% of rows, averaging +5.28 there.

**Filenames are `marginalpibc_YYYYMMDD<SS>.1` — date PLUS a two-digit session
index**, not one file per day. A date-only guess 404s on every request and reads
as "the dataset does not exist" rather than "the pattern is wrong". As with
`marginalpdbc`, **2018-2022 exist only as yearly zips** and 2023 onward as daily
files.
