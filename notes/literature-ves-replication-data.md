# Replicating Jo & Miftakhova (2024): where the data actually is

Jo, A. & Miftakhova, A., "How constant is constant elasticity of substitution?
Endogenous substitution between clean and dirty energy", *JEEM* 125, 102982.

This note answers one question: **which country's data can carry the paper's
Section 4 identification strategy?** Researched 2026-08-20. Every access claim
below was checked against the source, not recalled.

---

## 1. What the design needs

Section 4 is two pages of an otherwise theoretical paper. It estimates the
combined first-order conditions of the VES (Variable Elasticity of
Substitution) production function:

```
Y_dit / Y_cit  =  −β  +  ((1−α)/α) · (p_cit / p_dit)
```

`c` = clean bundle (electricity + steam + renewables), `d` = dirty bundle (gas,
petroleum, coal). The object of interest is the **constant**: β = 0 collapses
VES to Cobb–Douglas. Estimated in levels, pooled, **no plant fixed effects** —
FE would absorb the constant they need, and they want the long-run
cross-sectional elasticity, not the short-run within one.

The instrument (Linn 2008 / Sato et al. 2019 family) is:

```
p^IV_cit  =  p_ci,t0 × Π_{j=1..t} (1 + G^N_cj)
```

each plant's **pre-sample unit price** rolled forward at the **national**
growth rate for that bundle; the ratio of the two instruments instruments the
price ratio. Clustered at plant. Robustness: 10-year rolling-window CES
(Constant Elasticity of Substitution) σ from the log-log version, and quantile
regressions.

So the data must deliver **four things at once**:

| # | Requirement | Why it binds |
|---|---|---|
| R1 | Panel of energy **end-users** (plants/firms) | The FOCs describe a cost-minimising *consumer* of energy |
| R2 | **Quantity AND expenditure per fuel** | Unit price = expenditure / quantity. This *is* the identifying variation |
| R3 | Fuels separable into clean/dirty bundles | Need `p_c` and `p_d` as distinct objects |
| R4 | A pre-sample year + national price series per bundle | The instrument is built from both |

R2 is the killer. Most industrial energy statistics collect quantity *or*
money, rarely both by fuel.

The source is EACEI (*Enquête Annuelle sur les Consommations d'Énergie dans
l'Industrie*), French plants ≥20 employees, 1990–2017, 30,142 plants,
169,182 observations, confidential, accessed through CASD.

---

## 2. Verdict across settings

| Setting | R1 | R2 | R3 | R4 | Access | Verdict |
|---|---|---|---|---|---|---|
| **India — ASI** | ✅ plant | ✅ qty + value + rate/unit | ✅ 5 fuel lines | ✅ 1986→2024 | **Free download, no application** | **Do this** |
| **US — MECS public tables** | ⚠️ NAICS × region | ✅ matched qty/$ tables | ✅ | ✅ 1991→2022 | Free XLS | **Good fallback / robustness** |
| France — EACEI | ✅ | ✅ | ✅ | ✅ | CASD: CSS approval + in-person enrolment + ~€3.5k/yr | Exact replication, slow |
| **Germany — AFiD** | ✅ plant | ❌ **cost is firm-level aggregate only** | ❌ | ✅ | FDZ, remote execution incl. Bavaria | **Fails R2** |
| **Spain — ECE** | ✅ legal unit | ❌ **monetary only, no quantities** | ❌ | — | No microdata release | **Fails R2** |
| Spain — ESEE | ✅ firm | ❌ total energy cost + price change rate | ❌ | ✅ | Fundación SEPI, researcher access | Fails R2 |
| US — MECS microdata | ✅ | ✅ | ✅ | ✅ | Census FSRDC, US-based only | Infeasible externally |
| UK — QFI / ARD | ✅ | ✅ | ✅ | ✅ | ONS Secure Research Service | Infeasible externally |

---

## 3. India — Annual Survey of Industries (recommended)

Registered manufacturing factories. **52 studies on `microdata.gov.in`, 1986-87
through 2023-24, licensed "Public use data files"** — free, no project
application, no secure environment.

The schedule splits into blocks A–J. Two matter:

**Block A** (identification, 22 variables): `a1` DSL, **`a2` PSL No.** — the
permanent serial number that links a factory across years, `a3` scheme code
(Census-1 / Sample-2), `a4`/`a5` NIC industry, `a7` state, `a9` rural/urban,
`mult` sampling multiplier.

**Block H** (indigenous input items consumed, 9 variables per item-row):

| variable | content |
|---|---|
| `HI3` | item code (NPCMS 2011) |
| `HI4` | unit of quantity (code) |
| `HI5` | **quantity consumed** |
| `HI6` | **purchase value (Rs.)** |
| `HI7` | **rate per unit (Rs.)** — the unit price, reported directly |

And the item lines are exactly the clean/dirty split the design needs
(numbering per the ASI Instruction Manual §3.9):

- item 15 — electricity **own generated** (kWh, quantity only)
- item 16 — **electricity purchased and consumed** (kWh, quantity + value)
- item 17 — **petrol, diesel, oil, lubricants**
- item 18 — **coal** (tonnes; includes coke, charcoal)
- item 19 — **gas** (kg; LPG, biogas)
- item 20 — **other fuel** (firewood)
- item 24 — *any additional requirement of electricity (unmet demand)*

The survey's own edit checks confirm the rate field is live and policed:
`CE33` flags "Rate of Electricity purchased and consumed (Bl H Item 16)" outside
2–25 Rs/kWh; `CE32` flags coal (item 18) outside 1,000–50,000 Rs/tonne.

This is a **finer** fuel breakdown than the paper's own French clean/dirty
aggregation, and the unit price is published rather than derived.

### What to watch

- **The clean label does not survive the trip.** India's grid is coal-dominated,
  so "electricity = clean" is untenable in the way France's ~90% nuclear+
  renewable grid makes it tenable. See §6 — this is an opportunity, not just a
  caveat.
- **Panel is unbalanced and selected.** Census units (large factories) are
  surveyed every year; sample units rotate. Since the paper deliberately runs
  *without* plant FE, this hurts less than it would otherwise, but the
  cross-section is not a random sample of factories.
- **Block lettering and item codes migrate.** Older ASI vintages use different
  block letters (indigenous inputs were Block G) and ASICC rather than NPCMS
  item codes; MoSPI publishes an ASICC↔NPCMS concordance. Same class of problem
  as `cab`'s 2025-03-19 layout switch — dispatch on observed structure, not on
  the year.
- **Heterogeneous units.** Coal in tonnes, gas in kg, electricity in kWh. A
  dirty bundle needs calorific conversion, exactly as
  `build_implied_marginal_cost.py` already does for API2 coal.
- **National price series for R4**: WPI fuel and power sub-indices (MoSPI/RBI)
  and CEA industrial tariff series.

---

## 4. US — MECS (fast, fully public, coarser)

EIA's Manufacturing Energy Consumption Survey. Microdata is Census-confidential
(FSRDC only), but the **published tables give a matched quantity/expenditure
pair at the same granularity**, which is all the design strictly needs if you
accept industry × region as the unit:

- **Table 7.6** — *Quantity of Purchased Energy Sources*, physical units:
  Electricity (million kWh), Natural Gas (billion cu ft), Residual and
  Distillate Fuel Oil (million bbl), HGL, Coal, Coke & Breeze, Other.
- **Table 7.9** — *Expenditures for Purchased Energy Sources*, million USD, same
  rows and columns.

Rows are NAICS at 3–6 digits; level is "National and Regional Data" (4 Census
regions). Downloadable XLS. Waves: 1991, 1994, 1998, 2002, 2006, 2010, 2014,
2018, 2022.

Filenames differ per wave — verified: `xls/Table7_6.xlsx` (2014, 2018),
`xls/Table1.1_02.xls` (2002), `xls/Table1_1.xls` (2006, 2010), `xls/d98c1_1.xls`
(1998), `xls/m94_01a.xls` (1994), `xls/mecs01a.xls` (1991). A fetcher needs
per-year dispatch.

Two real limits: **SIC→NAICS break at 1998** (so a clean panel is 1998–2022,
7 waves, with 1998 as the pre-sample base and estimation on 2002–2022), and
suppression flags (`D` withheld, `Q` poor RSE, `*` below half a unit) that thin
the regional cells. With ~50 industries × 4 regions × 6 waves you still get on
the order of 1,000 observations — enough to estimate a constant.

The instrument transfers **structurally intact**: pre-sample industry×region
unit price × cumulative national price growth. Cross-sectional unit fixed at
base, time variation from national prices — the same logic, one level up.

---

## 5. Why Germany and Spain fail

**Germany — AFiD.** The `Energieverwendung` module has plant-level quantities
for 14 energy carriers, plants ≥20 employees, standalone annual survey since
2003 (1995–2021 available via FDZ; controlled remote execution covers Bavaria,
so LMU-feasible in principle). Destatis's own Erhebungsprogramm lists only
*Menge* — quantity of purchase, stock, consumption and delivery by carrier. No
euro field.

Energy **costs** come from a different module, the Kostenstrukturerhebung, and
von Graevenitz & Rottner (2023, *JBNST*) state it plainly in their footnote 8:
energy costs are reported "as an aggregate measure for the firm, but not the
expenditure on individual fuels or electricity." One number, one firm, all
fuels. You cannot form `p_c` and `p_d` separately. **R2 fails.**

The only workaround is to *assign* prices from national schedules by
consumption band rather than observe them — which removes the quantity-discount
variation the paper says drives plant-level price differences, and leaves you
running OLS on something that is essentially the instrument. It changes the
estimand. Worth stating as a fallback; not worth calling a replication.

**Spain — ECE.** INE's *Encuesta de Consumos Energéticos* is the literal
analogue (legal units ≥20 employees, CNAE B and C, biennial to 2021, annual
from 2022). Its methodology states that consumption is measured "en términos
monetarios, a precios corrientes" — **money, not physical units**. No unit
price is constructible, and there is no microdata release; published output is
CNAE 1/2/3-digit × autonomous community. **R2 fails twice.**

**Spain — ESEE.** Fundación SEPI's panel, ~1,800 manufacturing firms/year,
1990–2024, ≥10 employees, genuinely accessible to researchers. Records a total
energy cost and a firm-level *annual rate of change of energy prices* — not
consumption and expenditure fuel by fuel. **R2/R3 fail.** (Worth one direct
check of the variable list before closing the door; it's the only Spanish micro
panel with any chance.)

**And it cannot be moved to the generation side.** Tempting given what this
repo holds, but equations (11)–(12) describe a producer choosing input
quantities against *observed input prices*. A generator's clean input is wind
and sun: price unobserved, quantity weather-determined rather than chosen, so
`p_c/p_d` is degenerate, and substitution in MIBEL is executed by the clearing
algorithm under merit order and must-run constraints, not by a firm equating a
marginal rate of technical substitution to a price ratio. This is not a hunch —
it is why Stöckl & Zerrahn (2023, *JAERE*), the paper's own footnote-16
citation, estimate generation-side substitution from a **numerical bottom-up
model** rather than from observed prices and quantities.

**France — EACEI**, for completeness. EU-based researchers face the same
accreditation criteria as French ones, but the route is: Comité du Secret
Statistique approval + producer agreement + a contract with CASD + an
**in-person enrolment session in France**, then ~€253/month for the standard
package plus €37/month for the SD-Box, 12-month minimum, with student
discounts. Call it several months and low four figures. Feasible with
supervisor sponsorship and a long runway; not on a seminar timeline.

---

## 6. The angle that makes this more than a replication

The paper's footnote 11 defends classifying electricity as clean in France by
arguing end-users are **agnostic about the source of electricity, which is
beyond their control** — citing Papageorgiou et al. (2017), who find σ ≈ 2–3
using sector data from countries with very different grid mixes.

That is an assumption, asserted rather than tested, and it is load-bearing for
the whole clean/dirty literature.

India and the US let you test it directly. India's grid is coal-heavy, the US
grid is mixed and shifted hard toward gas and renewables across the MECS waves,
France's is nuclear. If β and σ come out similar across all three, footnote 11
is vindicated and the VES result generalises. If they diverge with grid
carbon intensity, then "clean vs dirty" in this literature is really
"electricity vs on-site fossil fuel", and every calibration built on it —
including this paper's own — inherits that.

Either result is a seminar paper. The replication is the vehicle, not the point.

---

## 7. Recommended path

1. **ASI first.** Free, immediate, plant-level, and the variable structure is a
   closer match to the design than the French data (the unit price is published,
   not derived). One fetcher + one block-layout concordance and you are
   estimating.
2. **MECS in parallel** as the low-risk sanity check — a day of work, and it
   gives an independent estimate on the *same* instrument logic at sector level.
3. **Do not open a Germany or Spain track.** Both fail R2 for documented
   reasons. Say so explicitly in the paper; a clean negative on data
   availability is worth a paragraph.
4. Read **Jo (2025)**, "Substitution between Clean and Dirty Energy with Biased
   Technical Change", *IER* — same author, same EACEI data, the natural
   companion and the thing a referee will ask whether you have read.

---

## 8. Piece-by-piece feasibility check of the India setting (2026-08-20)

Every claim below was checked against the source. Nothing was downloaded except
documentation.

### Present and verified

| Piece | Status |
|---|---|
| **Fuel quantity + value + unit price, per plant** | ✅ Block H, 9 variables, verified in every era 2005-06 → 2023-24 |
| **Fuel-line identification** | ✅ dual key — serial numbers 15–20 *and* fixed NPCMS pseudo-codes |
| **Industry / state / sector / weights** | ✅ Block A: `scheme`, NIC 4- and 5-digit, state, district, rural-urban, `mult` |
| **Year coverage** | ✅ 52 studies; continuous unit-level 1996-97 → 2023-24; all `data_access_type: public` |
| **Per-year documentation** | ✅ schedule PDF, instruction manual, code list, volume reports |
| **National fuel price series** | ✅ WPI *Fuel & Power* = Coal / Mineral Oils / Electricity, exactly the split needed |
| **Chaining across WPI base years** | ✅ official **WPI Linking Factor** page (bases 2022-23, 2011-12, 2004-05, 1993-94 …) |
| **State-level electricity tariffs** | ✅ CEA annual *Electricity Tariff & Duty and Average Rates of Electricity Supply*, plus data.gov.in state-wise industrial rate |
| **Calorific conversion** | ✅ MoSPI *Energy Statistics India*, annual |
| **Grid carbon intensity** | ✅ CEA *CO2 Baseline Database*, v21.0 = 0.7117 tCO₂/MWh (FY2024-25), versions back to v1.1, regional factors too |
| **Access** | ✅ free, but a **free account registration** is required to download (33,357 downloads recorded on the 2022-23 study) |

The **NPCMS fuel codes**, from the official ASI 2010-11 schedule, Block H:

| Sl.No. | Item | Code | Unit |
|---|---|---|---|
| 15 | Electricity own generated | 9990400 | KWH |
| 16 | Electricity purchased & consumed | 9990500 | KWH |
| 17 | Petrol, diesel, oil, lubricants | 9990600 | *not fixed* |
| 18 | Coal consumed | 9990700 | Tonne |
| 19 | Gas consumed | 9990900 | KG |
| 20 | Other fuel consumed | 9920400 | *not fixed* |
| 24 | Additional electricity requirement (unmet demand) | — | KWH |

Two redundant keys — serial number *and* a fixed 99xxxxx code — so a fuel line
stays identifiable even if the numbering shifts.

### Time-window alignment of the auxiliary series (checked 2026-08-20)

§8's first table verified that each source *exists*. It did not verify that
their coverage lines up with ASI. Checked properly, by downloading the index
files:

| series | financial years actually covered |
|---|---|
| **ASI unit-level** | 1996-97 → 2023-24 |
| **WPI, 2004-05 base** (`indx_download_0405/yearlyf.xls`) | **FY2005-06 → FY2016-17** |
| **WPI, 2011-12 base** (`indx_download_1112/fin_year_index.xls`) | **FY2012-13 → FY2025-26** |
| **WPI, 2022-23 base** (`indx_download_2223/wpi_yearly_index_202606.xlsx`) | FY2023-24 → FY2025-26 |

No single WPI base spans the ASI window. But the two relevant bases **overlap
for five financial years (FY2012-13 → FY2016-17)**, so they can be spliced on a
ratio estimated over the common years rather than trusting the official linking
factor alone. Chained, **2004-05 + 2011-12 covers FY2005-06 → FY2025-26
continuously** — which contains the recommended ASI window 2005-06 → 2023-24
with no gap at either end.

Fuel & Power sub-groups are present in both bases, with the right granularity:

| | 2004-05 base | 2011-12 base |
|---|---|---|
| Fuel & Power | 1200000000 (wt 14.91) | 1200000000 (wt 13.15) |
| Coal | 1200010000 — coking / non-coking | 1201000000 — coking / non-coking, **and by GCV grade band** |
| Mineral Oils | 1200020000 — LPG, ATF, **High Speed Diesel** (wt 4.67), LDO | 1202000000 — LPG, Petrol, …, Petroleum Coke |
| Electricity | 1200030000 — **split by consumer class** | 1203000000 — **aggregate only** |

Two things that bite, both found only by opening the files:

- **Natural gas is not in Fuel & Power.** It sits under Primary Articles, in
  *Crude Petroleum & Natural Gas* (`1104000002`). A dirty-bundle deflator that
  reads only the Fuel & Power group silently omits gas — which is ASI Block H
  item 19.
- **The consumer-class electricity split dies with the base change.** The
  2004-05 base publishes *Electricity (Industry)* (`1200030005`, wt 1.302)
  alongside domestic, commercial, agricultural and railway traction. The
  2011-12 base collapses all of it into one "Electricity" index. So an
  **industry-specific** electricity shifter exists only to **FY2016-17**. After
  that you either accept the aggregate index (whose composition is dominated by
  subsidised domestic and agricultural tariffs, which move for political
  reasons) or switch to CEA tariffs.

### Downgraded: state-level industrial tariffs

§8 listed this as verified. It is not. The `data.gov.in` catalogue
"State-wise average rate of electricity for domestic and industrial consumers"
is an **Economic Survey 2012-13 annex** — published 26/06/2013, last updated
08/09/2020, grouped under "Economic Survey 2012-13". It is a one-off table, not
a maintained series, and almost certainly stops around FY2011-12.

CEA's own annual *Electricity Tariff & Duty and Average Rates of Electricity
Supply in India*, and the average-rate-of-sale tables in CEA's *General Review*,
are the real source — but the CEA report pages are JS-rendered and the available
years could not be enumerated without a browser. **Unverified.** Treat
state-level tariffs as a lead, not a confirmed input, until someone opens those
pages.

Also unverified: the earliest year of the CEA *CO2 Baseline Database* (the host
for the old version guides fails TLS verification). Low stakes — it feeds the
framing, not the estimation.

### Absent, and it is the instrument's piece

**`PSL`, the panel key, is masked.** The Permanent Serial Number is officially
"unique in State × NIC × Sector" — the intended cross-year plant identifier.
In the public-use files it is a **constant 99999 in 100% of records**, verified
numerically in four years spanning the archive:

| year | cases | PSL min / max / mean | share = 99999 |
|---|---|---|---|
| 2000-01 | 41,096 | 99999 / 99999 / 99999 | 100% |
| 2012-13 | 59,162 | 99999 / 99999 / 99999 | 100% |
| 2013-14 | 57,968 | 99999 / 99999 / 99999 | 100% |
| 2014-15 | 63,296 | 99999 / 99999 / 99999 | 100% |

In the remaining years PSL is typed **character**, so NADA computes no
statistics and the metadata cannot settle it — but four masked years spread
across fifteen years of the archive make blanket masking near-certain.
`DSL` is the *dispatch* serial: the within-year join key across blocks A–J,
documented as not stable across years.

This is not what the literature says. Allcott, Collard-Wexler & O'Connell
(*AER* 2016) state that "the publicly available ASI includes establishment
identifiers that are consistent across years beginning in 1998", and that they
needed special in-India access only for **pre**-1998. That was written against
the older paid-CD distribution; the free portal, which replaced it from 2019,
appears to mask what the CDs carried. Separately, Boston University's guide to
its Indian firm data describes a MoSPI-supplied ASI with a
`Panel_data_supporting_Documents` folder — so a panel-enabled version exists,
as a separate acquisition, not as the free download.

### What that costs, and the substitute

- **Equation (12) is unaffected.** It is pooled and deliberately carries *no
  plant fixed effects* — Greene's constant-term argument, §4.2 of the paper.
  Repeated cross-sections are sufficient. The β ≠ 0 test survives intact.
- **The paper's own instrument is not constructible.** `p_ci,t0` has to be
  merged onto plant *i* in year *t*.
- **The paper names the substitute itself.** Footnote 13 describes the
  shift-share instrument of Linn (2008), Sato et al. (2019) and Marin & Vona
  (2021): national fuel prices weighted by the **pre-sample fuel mix**. Jo &
  Miftakhova rejected it *for France* because electricity is 98% of the clean
  bundle there, so the mix barely varies across plants and the instrument is
  weak.

  **India inverts that objection exactly.** Block H carries five separate fuel
  lines and the mix varies enormously — coal-fired, gas-fired, grid-only. Build
  the pre-sample mix at the **NIC × state cell** level from a pre-sample
  cross-section and no panel key is needed. State-level CEA tariffs give a
  second source of cross-sectional price variation the French data did not have.

  So the honest framing is not "degraded replication" — it is *the instrument
  this literature uses, in the setting where the paper's own stated reason for
  avoiding it does not apply.*

### Update: the identifiers may be recoverable — MoSPI ships two editions

Singer (2026, LSE), who builds a ~500,000-observation ASI plant panel for
1998–2013, states in his data section:

> "By matching **panel and cross-sectional ASI editions**, I retrieve panel
> identifiers and district codes only available in each edition."

So MoSPI distributes a **separate "panel" edition** alongside the cross-sectional
one, and the identifier lives in the former while district codes live in the
latter. That reconciles the ACWO claim with the masked `PSL` observed above: the
masking is a property of the cross-sectional edition, which is what the catalogue
pages checked here describe.

**This is now the single highest-value thing to verify** — if the panel edition
is on the free portal, the paper's own plant-level instrument is back on the
table and the shift-share substitute becomes a robustness check rather than the
main design.

### Two questions one small download would settle

Not done yet, deliberately:

1. Are `PSL`, `DSL` and `CIN` populated in the character-typed years (2009-10,
   2010-11, 2016-17 → 2023-24)? One `blkA` file answers it. `blkB` carries
   `b03` **Corporate Identification Number**, width 21 — a real MCA CIN — which
   would be a firm-level cross-year key *and* a bridge to Prowess if uncensored.
2. Does `DSL` overlap across adjacent years for census-scheme factories?

### Other traps found while checking

- **Item 17 and item 20 have no fixed unit** on the schedule — the
  unit-of-quantity code must be decoded per row against that year's code list.
  Coal (tonne), gas (kg) and electricity (kWh) are fixed.
- **Block structure changed twice.** Numbered blocks through ~1997 (fuels in
  their own "Block 9"); A–J with a **separate Block H1** in the early 2000s —
  and 2000-01's H1 has only 6 variables, quantity and value, with **no
  unit-of-quantity and no rate-per-unit**; A–J with fuels folded into Block H
  from 2005-06. **The rich version starts 2005-06.**
- **Variable names change roughly every three years, semantics identical**:
  `Qty_cons`/`Purchase_val`/`Rate_per_unit` (2005-06) → `H_Itm5/6/7` (2009-10) →
  `QtyConsumed`/`PurchaseValue`/`RatePerUnit` (2016-17) → `H15/H16/H17`
  (2018-19) → `HI5/HI6/HI7` (2022-23). Same class of trap as `cab`'s
  2025-03-19 switch — dispatch on the observed schema, never on the year.
- **Item codes migrate ASICC → NPCMS** at ~2010-11. MoSPI's concordance PDF is
  live. The fuel lines use fixed 99xxxxx codes either way, so this bites the
  *materials* items, not the fuels.
- **Electricity own-generated (item 15) has quantity but no value** — and Indian
  factories self-generate heavily on diesel, whose cost lands in item 17.
  Counting own-generated kWh as clean while its diesel sits in the dirty bundle
  double-counts. Decide this explicitly.
- **Sampling**: census scheme (≥100 workers, plus all factories in some smaller
  states/UTs) surveyed every year; sample scheme ≈20% of smaller registered
  factories, rotating every 3–5 years.
- **Frame**: registered factories only. ~80% of manufacturing *employment* is
  unregistered and out of frame, though that segment is only ~⅓ of output.

### Verdict

Ten of eleven required pieces are present and verified. The eleventh — the
cross-year plant key — is absent from the free files, and the fix is to swap the
paper's plant-level price instrument for the shift-share instrument its own
footnote 13 describes, built on pre-sample NIC × state cells. Nothing else in
the design changes.

Recommended window: **2005-06 → 2023-24**, base year 2005-06, estimation from
2006-07.

---

## 9. Has this been done? Novelty check (2026-08-20)

### The specific test is unclaimed

Jo & Miftakhova has **12 citations** (Semantic Scholar). None replicate the
empirical strategy in a new setting:

- **Jo (2024), *IER*, "Substitution between Clean and Dirty Energy with Biased
  Technical Change"** — same author, same French data; its abstract still says
  "empirical assessments of this key parameter remain scarce."
- **Mortha & Arimura (2024), *Energy Economics*, "Purchase or generate?"** — the
  closest citing paper. Japanese manufacturing plants, inter-fuel substitution
  *and* the purchase-vs-self-generate margin. Finds a 1% electricity price rise
  raises in-plant fossil fuel use 6.55%, with substitution capacity only in pulp
  & paper, iron & steel, chemicals, cement. Elasticities, not a VES test.
- **Leuthard (2025), *Swiss J. Econ. Stat.*** — endogenous energy substitution
  inside a Swiss carbon-tax model. Modelling, not micro-estimation.
- **Mardones & Henríquez (2025), *Energy*** — substitution and price elasticities
  of industrial demand across levels of aggregation.

**No VES/Revankar test of clean-dirty substitution exists outside France.**

### But ASI + electricity prices + IV is occupied territory

Three papers must be read and positioned against:

1. **Singer (2026, LSE), "Complementary Inputs and Industrial Development: Can
   Lower Electricity Prices Improve Energy Efficiency?"** — the closest. ~500k
   ASI plant observations, 1998–2013. Constructs the **plant-level electricity
   price as value ÷ quantity of electricity purchased** and validates it. Two
   instruments: *IV A*, a leave-out mean of electricity prices of other plants in
   the same state but a **different 2-digit industry**; *IV B*, a Bartik —
   national coal price **for power utilities** × pre-sample (March 1998)
   coal-fired share of state installed capacity.

   Critically, one of his ~14 model-prediction outcomes is the **electricity-to-
   coal quantity ratio** (MWh per tonne): −10.1 OLS, −23.3 IV A, −21.5 IV B on
   log electricity price. That is the substitution margin, on Indian plant data,
   already estimated.

   What he does *not* do: estimate σ, test CES against VES, or let the constant
   mean anything. The ratio is a mechanism check inside a paper about industrial
   development, not the object of study.

2. **Abeberese (2017), *REStat*, "Electricity Cost and Firm Performance: Evidence
   from India"** — ASI; instrument is the coal price paid by power utilities ×
   initial thermal share of state generation capacity. The template Singer's
   IV B follows, and the reason coal prices for utilities are argued exogenous to
   industrial coal users in India.

3. **Allcott, Collard-Wexler & O'Connell (2016), *AER*** — ASI, electricity
   shortages, hydro-rainfall instrument.

### The Indian inter-fuel literature proper is old and aggregate

Kar & Chakraborty (1986), translog on Indian manufacturing industries; Roy &
Sanstad (2006), inter-country pooled translog; Faizi & Mohammad (2025),
*Discover Energy*, translog production function at industry level; plus a body
of energy-*intensity* work (Sahu & Narayanan; Golder 2011) that does not estimate
substitution at all. Nothing plant-level, nothing VES.

### Net position

Novelty is intact but **narrower than it looked**, and the framing has to be
precise:

- **Not** "first estimate of fuel substitution in Indian manufacturing" — Singer
  has the electricity-to-coal ratio with two instruments.
- **Yes** "first test of whether the substitution elasticity between clean and
  dirty energy is *constant*" — the β ≠ 0 test, anywhere outside France.
- **Yes** the first such test in a **coal-heavy grid**, which turns the paper's
  own footnote 11 (end-users are agnostic about electricity's source) from an
  assumption into a testable claim.
- **Bonus**: Singer hands over both hard problems solved — how to recover the
  panel identifier, and a stronger India-specific instrument than the paper's.

Read Singer before writing anything.

---

## 10. Ingredient-by-ingredient map, with verified windows (2026-08-20)

### Has VES been estimated for India?

No — not for energy, and not for clean/dirty anywhere but France.

- **VES applied to clean vs dirty energy**: a search on the exact phrase returns
  15 works in total. Only Jo & Miftakhova (2024) does it. Adjacent but distinct:
  Aleti & Hochman (2020), non-constant elasticity of substitution and
  *intermittent renewables*; Stöckl & Zerrahn (2023), numerical bottom-up.
- **VES (Revankar) applied in India**: exists, but for **capital–labour only** —
  Iyer (2011) on the Indian chemical industry, Monga (1978) comparing France,
  India, Israel and Japan. Nothing on energy inputs.
- **Indian inter-fuel substitution**: translog, industry-level — Kar &
  Chakraborty (1986), Roy & Sanstad (2006), Faizi & Mohammad (2025).

So the VES/clean-dirty/India cell is empty. What is *not* empty is
ASI + plant-level electricity prices + IV — see §9 on Singer, Abeberese, ACWO.

### The ingredient map

| # | Ingredient (paper §4) | Paper's source & window | India equivalent | India window | Status |
|---|---|---|---|---|---|
| 1 | **Y_c** clean quantity, plant | EACEI, 1990–2017 | ASI Block H, *Electricity purchased & consumed*, ASICC `99905` → NPCMS `9990500`, KWH | 2000-01 → 2023-24 | ✅ verified |
| 2 | **Y_d** dirty quantity, plant | EACEI | Block H: coal `99907`/`9990700` (tonne); petrol-diesel-oil-lubricants `99906`/`9990600`; gas `99909`/`9990900` (kg); other fuel `99204`/`9920400` | 2000-01 → 2023-24 | ✅ but see gas break |
| 3 | **p_c** = expenditure ÷ quantity | EACEI | `HI6`÷`HI5`; from 2001-02 also `HI7` *Rate per unit* published directly | **1998-99 → 2023-24** | ✅ |
| 4 | **p_d** | EACEI | same, summed over the dirty lines | as above | ✅ |
| 5 | **p_i,t0** pre-sample plant price | EACEI 1989 | needs the factory-ID edition | **1998-99 → 2017-18** | ⚠️ **binding constraint** |
| 6 | **G^N_c** national clean price growth | French national prices | WPI *Electricity for Industry* `1200030004` (1993-94 base) → *Electricity (Industry)* `1200030005` (2004-05 base); aggregate *Electricity* `1203000000` thereafter | **industry-specific FY1994-95 → FY2016-17**; aggregate to FY2025-26 | ✅ / ⚠️ |
| 7 | **G^N_d** national dirty price growth | French national prices | WPI Coal `1200010000`/`1201000000`, Mineral Oils `1200020000`/`1202000000`, **Natural Gas `1104000002` (Primary Articles, *not* Fuel & Power)** | FY1994-95 → FY2025-26, chained over 3 bases | ✅ with the gas gotcha |
| 8 | **Deflator** | GDP deflator | WPI *All Commodities* in the same files, or MoSPI national accounts | same as WPI | ✅ |
| 9 | **Industry FE** (19 industries) | French NAF | Block A `a4` NIC 4-digit, `a5` NIC 5-digit | NIC-04 to 2007-08; **NIC-08 from 2008-09**; both carried in 2009-10 | ✅ concordance needed |
| 10 | **Region FE** | French regions | Block A `a7` state, `a8` district | throughout | ✅ |
| 11 | **Year FE** | 1990–2017 | survey year | throughout | ✅ |
| 12 | **Weights** (total energy consumption) | EACEI | derive from Block H; `mult` is the *sampling* multiplier, a different object | throughout | ✅ |
| 13 | **Clustering unit** | plant | factory-ID; `DSL` only joins blocks within a year | 1998-99 → 2017-18 | ⚠️ |
| 14 | **Frame** | plants ≥20 employees | registered factories (Factories Act: ≥10 workers with power, ≥20 without) | — | ⚠️ different frame |
| 15 | **"Clean" justification** | France ~90% nuclear+RE | CEA *CO2 Baseline Database* | v21.0 = FY2024-25; **earliest version year unverified** | ⚠️ |
| 16 | **Calorific conversion** | not needed (EACEI in common units) | MoSPI *Energy Statistics India*, Annexure II — incl. GCV of Indian coal by year | annual, archived from ~2007 | ✅ |
| 17 | **State electricity tariffs** (optional, India-only upside) | n/a | CEA *Electricity Tariff & Duty and Average Rates of Electricity Supply* | **unverified**; the data.gov.in table is a stale Economic Survey 2012-13 annex | ❌ downgraded |

### What the unit of observation actually is

Two different things, which are easy to conflate:

- **Unit of observation** — what a row describes. This is the **factory**, in
  every year, with no caveat. Not in doubt.
- **Cross-year identifier** — whether this year's factory *X* is last year's
  factory *X*. This is what `PSL` was for and what is blanked.

`DSL` does the **within-year** join: Block A `a1 DSL` ↔ Block H `AH01 DSL`, so a
factory's fuel lines attach to its industry, state, employment, output and
capital in any single year. That works everywhere. It is only across years that
DSL is not stable.

From the ASI Instruction Manual:

- §1.6.3: "The **primary unit of enumeration** in the survey is a **factory** in
  the case of manufacturing industries, a workshop in the case of repair
  services, an undertaking or a licensee in the case of electricity, gas and
  water supply undertakings and an establishment in the case of bidi and cigar
  industries." The manual draws the *enterprise* vs *establishment* distinction
  explicitly — a factory is an establishment, a single location.
- §2.3: a factory is one registered under **Sections 2m(i) and 2m(ii) of the
  Factories Act, 1948** — premises with **≥10 workers with power**, or **≥20
  workers without power**, on any day of the preceding twelve months.
- §2.2: the accounting year is **1 April – 31 March**.

So the unit matches EACEI's *établissement* closely. ASI's threshold reaches
*smaller* plants than EACEI's ≥20 employees, which is the favourable direction;
restrict to ≥20 workers if an exact match is wanted.

Two frame caveats found in the manual, both material:

- **Threshold amendments break the frame mid-panel.** For **Rajasthan and
  Maharashtra from ASI 2015-16**, and **Goa from ASI 2022-23**, §2m(i) moves
  from 10→20 workers with power and §2m(ii) from 20→40 without. Maharashtra is
  India's largest manufacturing state, so small factories there leave the frame
  in 2015-16 — a compositional break landing right at the end of the
  recommended window. Either stop at 2014-15, restrict to ≥20 workers
  throughout, or control for it explicitly.
- **Joint Returns.** An owner with two or more establishments in the same state,
  same sector and same 3-digit industry, under the census scheme, may file one
  consolidated return. Those rows are multi-plant aggregates, not plants. The
  manual says this is common for bidi/cigar and electricity undertakings rather
  than for manufacturing generally, but it is present.

What the missing cross-year id does and does not cost:

| use | needs cross-year id? |
|---|---|
| Estimating equation (12), pooled, no plant FE | **no** |
| Clustering at plant across years | yes — fall back to industry × state, coarser and more conservative |
| The paper's pre-sample price instrument | **yes** — this is the only real casualty |

### Two structural breaks inside Block H

**Serial numbers are not a stable key — the item code is.** Verified across four
schedules:

| ASI year | electricity purchased | coal | gas |
|---|---|---|---|
| 2001-02 | item **11** | item 13 | — |
| 2004-05 | item **16** | item 18 | — |
| 2006-07 | item **16** | item 18 | — |
| 2009-10 | item **16** | item 18 | item **19**, `99909` |
| 2010-11 | item **16** | item 18 | item **19**, `9990900` |

Only five "major basic items" were collected in 2001-02 versus ten from 2004-05,
which shifts every downstream serial by five. The pseudo-item codes (`99905` etc.)
never move, and the NPCMS code is simply the ASICC code with `00` appended — so
the fuel-line concordance across the ASICC→NPCMS switch is trivial.

**Gas got its own line between 2006-07 and 2009-10** (absent in the 2006-07
schedule, present in 2009-10). Before that it sits inside *Other fuel consumed*.
Fix: always sum gas + other fuel into one "other fossil" line, and the dirty
bundle is consistent across the whole window.

### A WPI trap that would corrupt the instrument silently

**The consumer-class codes are swapped between the two bases.**

| code | 1993-94 base | 2004-05 base |
|---|---|---|
| `1200030004` | **Electricity for Industry** (wt 2.169) | **Electricity (Railway Traction)** (wt 0.092) |
| `1200030005` | Electricity for Railway Traction (wt 0.132) | **Electricity (Industry)** (wt 1.302) |

Exactly transposed. Chaining the industrial electricity series across the base
change by joining on the commodity code silently substitutes railway-traction
tariffs for industrial ones — and returns plausible-looking numbers either way.
**Join on the name, and assert the weight.**

### The intersection — revised

An earlier version of this note recommended 1998-99 → 2016-17 and claimed
"everything verified present". That was wrong on three counts, all found after
it was written:

1. **The released data files were only verified from 2005-06.** The portal
   publishes data dictionaries for 2005-06 onward. For 1998-99 → 2004-05 only
   the *schedules* were checked — and 2000-01 proves the schedule is not the
   file: its questionnaire shows a six-column Block H, but the released data
   splits fuels into an `H1` block carrying only serial number, quantity and
   value, with item code and unit dropped.
2. **The Factories Act threshold changes mid-window.** Rajasthan and
   Maharashtra move to 20 workers with power / 40 without **from ASI 2015-16**.
   Maharashtra is India's largest manufacturing state. That is a frame break
   inside the last two years of the window that was recommended.
3. **The base year presumed an edition not yet in hand.** "Base 1998-99" only
   works if the factory-ID edition is obtained, and that rests on a secondary
   source (IIM Bangalore's guide), with no verified route to the files.

| tier | window | waves | what it assumes |
|---|---|---|---|
| **Core — everything verified from primary sources** | **2005-06 → 2014-15** | **10** | nothing outstanding |
| Extended | 2005-06 → 2016-17 | 12 | the Rajasthan/Maharashtra frame break is handled — restrict to ≥20 workers with power throughout, or drop those states, or control for it |
| Maximal | 1998-99 → 2017-18 | 20 | factory-ID edition obtained; data-file structure verified for 1998-99 → 2004-05; WPI chained across bases without hitting the code swap above |

**Recommendation: build the core first, 2005-06 → 2014-15.** Base 2005-06,
estimation 2006-07 → 2014-15, nine estimation years.

Its decisive advantage is not the length but that **the WPI 2004-05 base alone
spans FY2005-06 → FY2016-17**, so the core window needs *no* base chaining, no
linking factor, and never touches the code-swap trap. The frame is stable
throughout, NIC changes once (2008-09), and gas can be folded into "other
fossil" for a compositionally constant dirty bundle.

Nine years is short against the paper's 28, but the identification is
cross-sectional: ASI carries roughly 55,000–68,000 factories per wave, so the
core window still yields far more observations than the paper's 169,182.

Extend outward only after the core runs.

**Still unverified**: released data-file structure for 1998-99 → 2004-05;
whether gas was reported inside "other fuel" before it got its own line, or not
collected at all; the CEA tariff series years; the earliest CEA CO2 Baseline
year; and how to obtain the factory-ID edition.

## Sources

- Jo & Miftakhova (2024), *JEEM* 125, 102982.
- India ASI microdata catalogue: https://microdata.gov.in/NADA/index.php/catalog/ASI
- ASI Instruction Manual (Concepts, Definitions and Procedures), 2023, §3.9 and edit checks CE32/CE33.
- EIA MECS: https://www.eia.gov/consumption/manufacturing/ (Tables 7.6, 7.9).
- von Graevenitz, K. & Rottner, E. (2023), "Energy Use Patterns in German Manufacturing from 2003 to 2017", *JBNST* 243(3–4), fn. 8.
- FDZ AFiD-Modul Energieverwendung: https://www.forschungsdatenzentrum.de/de/energie/afid-modul-energieverwendung
- Destatis Qualitätsbericht, Jahreserhebung über die Energieverwendung, §2.1.1.
- INE, Encuesta de Consumos Energéticos, Metodología (May 2025).
- CASD price list and authorisation procedure: https://www.casd.eu/en/tarifs-2/
- Stöckl, F. & Zerrahn, A. (2023), "Substituting Clean for Dirty Energy: A Bottom-Up Analysis", *JAERE* 10(3).
- ASI Schedule 2010-11 (Block H item table with NPCMS fuel codes): https://microdata.gov.in/NADA/index.php/catalog/23/download/3632
- ASI PSL variable definition and value distribution: https://microdata.gov.in/NADA/index.php/catalog/2/variable/F1/V4?name=PSL
- Allcott, H., Collard-Wexler, A. & O'Connell, S. (2016), "How Do Electricity Shortages Affect Industry? Evidence from India", *AER* 106(3), §I.C.
- Amirapu, A. & Gechter, M., "Presentation on BU's Indian Firm Data": https://www.bu.edu/econ/files/2016/01/Presentation-on-BU-Indian-Firm-Data-April-3-2014-Aug-2015-update.pdf
- Office of the Economic Adviser, WPI download and linking factor: https://eaindustry.nic.in/download_data_1112.asp , https://eaindustry.nic.in/wpi_linking_factor.asp
- CEA, *CO2 Baseline Database for the Indian Power Sector*, User Guide v21.0: https://cea.nic.in/wp-content/uploads/baseline/2025/12/User_Guide_V_21.0.pdf
- data.gov.in, state-wise average rate of electricity for domestic and industrial consumers.
- MoSPI, *Energy Statistics India* (calorific values).
- MoSPI, ASICC↔NPCMS concordance: https://mospi.gov.in/sites/default/files/main_menu/national_product_classification/Concordance_of_ASICC_with_NPCMS_18apr12.pdf

---

## 11. Sweden and Colombia, checked to the same depth (2026-08-20)

### Sweden — ISEN (Industrins energianvändning)

Statistics authority: Energimyndigheten; collection by SCB. Unit: **arbetsställe**
(establishment), **all** of them in SNI 05-33 with ≥10 employees — a census,
population drawn from SCB's business register (FDB/SAMU freeze).

| # | Ingredient | Sweden equivalent | Window | Status |
|---|---|---|---|---|
| 1 | Y_c clean quantity | Section A *Använd mängd el*; Section B *vattenburen energi* (fjärrvärme, ånga) | 2004 → 2024 census | ✅ |
| 2 | Y_d dirty quantity | Section C *bränslen* — diesel, motorbensin, natur- och stadsgas, propan/butan, sten- och brunkol, koks, eldningsolja nr 1 and nr 2–6 | same | ✅ |
| 3 | p_c | A: `Inköpsvärde exkl. moms` ÷ `Använd elmängd`; the form itself computes **Pris per enhet** | same | ✅ |
| 4 | p_d | **C4 `Inköpsvärdet av bränslen`** ÷ `Inköpt mängd`; form computes **Pris per enhet (rimlighetskontroll)** | same | ✅ |
| 5 | p_i,t0 pre-sample | register-based establishment ID | should hold | ⚠️ unverified in practice |
| 6 | G^N_c | SCB *Elpriser och elavtal*; Eurostat `nrg_pc_205` industrial bands | ✅ | ✅ |
| 7 | G^N_d | Eurostat `nrg_pc_203` gas; Swedish energy and CO₂ taxes are large and fuel-specific | — | ⚠️ tax-heavy |
| 8 | Deflator | SCB producer price index | — | ✅ |
| 9 | Industry FE | SNI 2007, 2–5 digit | — | ✅ |
| 10 | Region FE | kommun / län from FDB | — | ✅ |
| 11 | Year FE | annual | 1999 → 2024 documented | ✅ |
| 12 | Weights | census — none needed | — | ✅ |
| 13 | Clustering | establishment ID | — | ✅ |
| 14 | Frame | ≥10 employees, SNI 05-33. **2001–2003 were sample years**; census from 2004 | — | ⚠️ |
| 15 | "Clean" justification | Sweden ≈98% fossil-free | — | ✅ **best in class** |
| 16 | Calorific conversion | **värmevärden collected inside the survey** per fuel | — | ✅ **best in class** |
| 17 | Access | **Swedish organisation required**; **40,000–60,000 SEK** small jobs, 50,000–300,000 complex; **1–6 months** after a case officer is assigned | — | ❌ **the blocker** |

**The near-miss worth recording.** Two SCB documents point at a German-style
failure and are both wrong about the microdata: the published cost table
`EN01131D` has *no* energy-carrier dimension (cost is one aggregate per
industry), and the quality declaration's §1.2.2 target-variable list names a
purchase cost for electricity and heat but **not** for fuels. The questionnaire
(STEMFS 2025:7, Bilaga 1, section **C4**) collects purchase value per fuel with
a price-per-unit check. *Never infer microdata content from published tables.*

### Colombia — EAM (Encuesta Anual Manufacturera)

Unit: industrial establishment. Módulo IV, *Energía eléctrica – otros
energéticos consumidos*.

| # | Ingredient | Colombia equivalent | Window | Status |
|---|---|---|---|---|
| 1 | Y_c clean quantity | Numeral 1 col 1 `kWh comprados`; col 7 `energía consumida` (= 1+3+4−5) | 1992 → 2024 | ✅ |
| 2 | Y_d dirty quantity | **Numeral 2 `Otros energéticos`** — "para dar movimiento a la maquinaria…, combustible para los hornos o para la generación de vapor o energía eléctrica": `cantidad consumida`, units **pre-filled by DANE** | same | ✅ |
| 3 | p_c | col 2 `valor` ÷ col 1 `kWh`. DANE's own edit check is `(valor × 1000) / kWh` | same | ✅ |
| 4 | p_d | Numeral 2 `valor total del consumo` (miles de pesos) ÷ `cantidad` | same | ✅ |
| 5 | p_i,t0 pre-sample | needs a stable establishment ID in the anonymised files | — | ⚠️ **unverified — the India risk** |
| 6 | G^N_c | electricity tariffs — XM, SUI, CREG; DANE IPP | — | ⚠️ unverified |
| 7 | G^N_d | DANE IPP energy components; UPME fuel prices | — | ⚠️ unverified |
| 8 | Deflator | DANE IPP / IPC | — | ✅ |
| 9 | Industry FE | CIIU Rev. 4 A.C. | — | ✅ |
| 10 | Region FE | departamento / municipio | — | ✅ |
| 11 | Year FE | annual | 1992 → 2024 | ✅ |
| 12 | Weights | census-type frame | — | ✅ |
| 13 | Clustering | establishment ID (see 5) | — | ⚠️ |
| 14 | Frame | establishments ≥10 persons or above a production-value threshold | — | ⚠️ confirm |
| 15 | "Clean" justification | grid ≈70% hydro | — | ✅ good |
| 16 | Calorific conversion | units pre-filled; conversion factors from UPME | — | ⚠️ |
| 17 | Access | **anonymised microdata public since 1992, no application, no fee** | — | ✅ **best in class** |

DANE's microdata portal (`microdatos.dane.gov.co`) returns HTTP 403 to every
non-interactive client tried, including the in-app browser — likely geo or bot
filtering. The variable list therefore could not be read directly; the module
structure above comes from DANE's own *Manual de Diligenciamiento* (2016 and
2020 editions), which is served openly from `formularios.dane.gov.co`.

### How the three now rank

| | Sweden | Colombia | India |
|---|---|---|---|
| Fuel-level quantity **and** value | ✅ + price in form | ✅ + price in edit check | ✅ + published rate |
| Panel identifier | ✅ register-based | ⚠️ unverified | ❌ blanked |
| Grid | ≈98% fossil-free | ≈70% hydro | coal, 0.71 tCO₂/MWh |
| Access | ❌ Swedish affiliation, 40–60k SEK, 1–6 months | ✅ free, immediate | ✅ free + registration |
| Calorific conversion | ✅ in-survey | ⚠️ external | ⚠️ external |

**Sweden has the best data and the worst access. Colombia has the best access
and one unverified ingredient. India has the richest fuel detail, free access,
a missing panel key and a coal grid.**

The design worth building remains **one clean-grid country against India** —
same equation, opposite grids, which is footnote 11 tested rather than assumed.
Colombia is the version of that a master's student can actually execute alone;
Sweden is the version worth proposing if a Swedish co-author is available.

---

## 12. Colombia, run to ground (2026-08-20)

### Solved

- **Frame**: establishments with **ten or more employees, or a production value
  above a threshold updated annually by the PPI** — exhaustive, not a sample
  (DANE, *Annual Manufacturing Survey Methodology*, English edition).
- **Fuel block**: Módulo IV Numeral 2 covers **all** fuel use — "para dar
  movimiento a la maquinaria…, combustible para los hornos o para la generación
  de vapor o energía eléctrica" — with `cantidad consumida` and `valor total del
  consumo`, units **pre-filled by DANE** per carrier.
- **Electricity**: Numeral 1, col 1 `kWh comprados` and col 2 `valor`; DANE's own
  edit check computes `(valor × 1000) / kWh`.
- **Grid carbon intensity** (ingredient 15): **XM publishes the SIN emission
  factor — 164.38 gCO₂/kWh**, annual, via UPME's emissions calculator and XM's
  Sinergox portal. That is *cleaner than assumed* — roughly one quarter of
  India's 711 g and within striking distance of a European clean grid.
- **Calorific conversion** (ingredient 16): UPME's **BECO** (*Balance Energético
  Colombiano*, same methodology since 1975) plus the dedicated **FECOC**
  document, *Factores de emisión de los combustibles*.

### The blocker, in DANE's own words

*Metodología general EAM*, `DSO-EAM-MET-001` v11, §2.5.2 *Anonimización de
microdatos*:

> "La anonimización se hace usando diferentes técnicas para **agregar** la
> información de las fuentes que se consideren identificables después de
> realizar un estudio de riesgo. Los usuarios de la información pueden acceder a
> los datos en la **sala de procesamiento especializado** en la cual encuentran
> bases a nivel de microdato **sin variables de identificación**. Con estas
> bases, quienes usan la información, generan las salidas que requieren y pueden
> disponer de los resultados, **únicamente a nivel agregado**."

Three things follow, and they compound:

1. **No identification variables even in the secure room.** If the on-site
   version has none, the freely downloadable anonymised files certainly have
   none. There is no cross-year establishment key — the same wall as India's
   blanked `PSL`, but without India's separately-distributed factory-ID edition
   to fall back on.
2. **Identified microdata means a physical visit** to a DANE *sala de
   procesamiento especializado*, and **only aggregate outputs may leave**.
   Regression coefficients qualify as aggregate output, but this is Bogotá, not
   a download.
3. **The public files are perturbed on exactly the units that matter.** §2.5.3
   describes the pipeline as risk-scenario identification followed by
   "aplicación de técnicas de anonimización"; DANE's 2024 anonymisation guide
   names **microaggregation** — replacing an observed value with a group mean —
   as its preferred technique for skewed continuous variables. In a business
   survey the risky records are the large plants. A microaggregated quantity or
   value makes the plant-level unit price **partly synthetic**, which is worse
   than a missing panel key: an instrument can be substituted, a perturbed price
   cannot be un-perturbed.

### Verdict

Colombia's variable structure is right and its grid is clean, but the accessible
data cannot carry a plant-level price the design can trust, and carries no
cross-year link at all. **Downgraded from "best access" to "perturbed data or a
trip to Bogotá".**

Still unverified: the national price series for industrial electricity (XM /
SUI / CREG) and fuels (DANE IPP, UPME) — ingredients 6 and 7. Not worth chasing
until the anonymisation question is settled with DANE directly, since it decides
whether the setting is usable at all.

### Where the three now stand

| | data | grid | access | verdict |
|---|---|---|---|---|
| **India** | richest fuel detail; published unit price | ❌ coal, 711 g | free, immediate; panel key blanked but a factory-ID edition exists | **still the front-runner** |
| **Sweden** | best; price computed in the form; calorific values in-survey | ✅ ~98% fossil-free | ❌ Swedish research principal required, 40–60k SEK, 1–6 months | best data, closed door |
| **Colombia** | right variables, **but perturbed and unkeyed** | ✅ 164 gCO₂/kWh | free download is perturbed; clean data is on-site only | downgraded |
