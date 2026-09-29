# Where did market power go? Price formation in MIBEL, 2018–2026

Written 2026-08-25. Design:
[`docs/specs/2026-08-24-descriptive-price-formation-design.md`](../docs/specs/2026-08-24-descriptive-price-formation-design.md).
Scripts: `scripts/analysis/{residual_demand_firm,concentration_margin,
supply_curve_anatomy,clean_years_trend,descriptive_figures}.py` and
`scripts/build/build_contract_position.py`.

**This is the first chapter in this repo that uses no marginal cost anywhere.**
That is not a stylistic choice; it is the direct response to six failed causal
designs whose common cause was the cost measure.

Every claim below is labelled **[established]**, **[bounded]** or
**[confounded]**. Nothing is asserted without one.

---

## 1. Why a descriptive chapter

Six causal designs were built and withdrawn here: the levy reduced form,
differential renewable exposure, bid steepness, the markup instrumental-variable
design, gas-cap pass-through, and clawback intensity. Their own scorecard, in
[`rq-heat-demand-conduct.md`](rq-heat-demand-conduct.md) §8.3, diagnoses the
common cause:

> Every conduct estimate is null or wrong-signed; every precisely estimated
> result is merit order. … **the markup measure, not the shock, is the binding
> constraint.**

`net_load_iv.py` had a first-stage F of 184.8 and still returned nulls, so the
problem was never identification power. An implied marginal cost that omits
operations & maintenance, part-load efficiency and start-up amortisation cannot
support a markup test at this resolution, and wiring in `cab`'s declared
minimum-income condition did not rescue it either
([`min-income-condition.md`](min-income-condition.md)).

The chapter takes the opposite route deliberately. It asks what *changed* in the
structure of price formation, using only objects the bid archive observes
directly. It is the step that decides which causal question is worth asking.

**The puzzle it starts from.** Market residual-demand elasticity `η` roughly
quartered over the window while the Comisión Nacional de los Mercados y la
Competencia (CNMC, the Spanish energy and competition regulator) reported
aggregate concentration *falling*, 1314 → 1007. Under the Lerner identity those
pull in opposite directions and the bound on markups roughly doubled. The
chapter's claim is that this is a **relocation, not a paradox**: the
price-setting margin moved to a thinner, differently-owned part of the stack.

---

## 2. The identity, and the three objects

Kellogg & Reguant (2021), Handbook ch. 17 eq. 23, rearranged. For firm *i* in
period *t*:

```
L_it = (p*_t − C′_it) / p*_t  =  q_it / (|RD′_it| · p*_t)  ≡  s_it / η_t
```

with `RD_it(p) = D_t(p) − Σ_{j≠i} S_jt(p)`. Three objects, and no cost term:

- **s** — who supplies, and *where in the stack*. Measured as HHI on cleared
  volume (`hhi_total`) and on offers within ±h €/MWh of `p*` (`hhi_margin`).
- **η** — how steep residual demand is *where the price is actually set*.
  Offer curves are step functions with no derivative, so
  `|RD′(p*)| ≈ (sell MW + buy MW within ±h) / 2h` — the "derivative" is
  literally the density of offers near the clearing price, and `h` is the only
  tuning knob.
- **θ** — how much output is already sold forward, which scales the incentive
  to withhold (Wolak 2000; Hortaçsu & Puller 2008). Read from PDBF
  (*Programa Diario Base de Funcionamiento*, the daily operating schedule)
  `role_code == "4"`, the bilateral contract.

Two derived indices, McRae & Wolak eqs. 3.4 and 3.10:

```
ability    η_i   = q_it / (100 · |RD′_it|)          €/MWh per 1% withheld
incentive  η_i^C = η_i · (q_it − θ_it) / q_it
```

---

## 3. Measurement

Four panels, all on the same 79,036 retained market-periods, 2018-01-02 →
2026-05-08 (the bid archive's own publication frontier — see `CLAUDE.md` on the
~3-month lag).

| panel | rows | what it holds |
|---|---|---|
| `residual_demand_slope_full.parquet` | 79,036 | market `η` at four bandwidths |
| `firm_residual_demand_full.parquet` | 2,634,522 | firm slope, ability, incentive, θ |
| `concentration_panel.parquet` | 79,036 | `hhi_total`, `hhi_margin`, coverage, firm counts |
| `supply_anatomy_panel.parquet` | 79,036 | stack shape, band density, marginal technology |

All three period-level panels retain **exactly** the same 79,036 keys, which is
the check that one filter block was applied identically across the pipeline.

### 3.1 The firm mapping, and the two coverage numbers

Nothing in OMIE's files publishes who controls a unit's bid.
`build_unit_agents.py` layers ESIOS registry matches, `cab` plant-name matches, a
hand-checked prefix dictionary and a twin-registration rule to reach **89.1% of
near-marginal offered volume** for ownership. Technology, from parsing `cab`
plant names, reaches only **41.2% of generation volume**.

**Coverage is measured on the near-marginal band, never on total volume**
[established]. A 5 GW wind portfolio offering at €0 is inframarginal almost
always; total-volume coverage flatters the mapping for exactly the units that
matter least.

**Technology coverage on the *marginal unit* is much better than 41.2%, and
that is not a contradiction** [established]. `marginal_tech` resolves on
68.7–80.7% of retained periods by year, because the marginal unit is
disproportionately a large conventional plant whose `cab` name carries an
explicit marker (`C.C.`, `C.H.`, a river or basin name). The 41.2% is a
volume-weighted average across the whole fleet, diluted by thousands of small,
generically-named wind and solar units that rarely set the price.

### 3.2 θ is a proxy and is labelled one

`role_code == "4"`'s sell and buy legs match to 0.0000 in every month tested —
the identity a subtraction of PDBF minus PDBC cannot check. But it captures
**physical** bilateral contracts only and misses financial hedges entirely. An
OMIP future or a financially settled power purchase agreement fixes revenue
while the energy still clears in the auction, and since what matters is whether
*revenue* is fixed, that omission is the more serious one. **θ is bounded, not
measured** [bounded].

**θ and `q` are measured over different unit populations, and the gap is not
neutral across firms** [bounded]. `build_contract_position.py` maps role-4 sell
legs through the *unrestricted* unit→firm table, while `residual_demand_firm.py`
builds `q` from cleared sell volume on `SUPPLY_ROLES` only (`generation`,
`generation_large`, `storage_mixed`, `pumping`). On 2024-01, **14.1% of role-4
contracted sell MW sits on `purchase_retail` registrations** — MW that enter θ
and can never enter `q`. The share is wildly uneven by firm: **EDP 83.4%,
Acciona 77.5%, ENGIE 56.6%, Naturgy 6.0%, Endesa 0.6%, Iberdrola 0.0%.**

Since `incentive = ability · (q − θ)/q`, θ carrying volume that `q` structurally
cannot pushes that factor down, so **measured incentive is biased downward for
exactly those firms** — a known direction, in proportion to how much of the
firm's contract book sits on retail registrations, which makes it a bound rather
than noise. Iberdrola's 0.0% is why §4.5's net-buyer result is untouched by
this; EDP's and Acciona's levels are not, and §4.5 says so where they are read.
The asymmetry is deliberate, not a bug: restricting θ to supply roles would drop
real contracted volume, and widening `q` would put retail registrations into a
supply-side elasticity. It is documented instead of resolved.

### 3.3 A measurement note that will otherwise be re-litigated

Firm-specific `eta_i` comes out **above** market `η` in every year (median
474 vs 1.84 in 2018), not below it. This is the mechanical consequence of the
formula, not a join error: `eta_i = |RD′_i| · p* / q_i` divides by the *firm's*
cleared volume while market `η` divides by the *market's*, and the median firm
share is 0.17–0.58%. The invariant that does hold, and is the one asserted in
`verify()`, is on the **slope**: `slope_i ≤ slope_market` on 0.0000% violation.
Use `lerner_bound = 1/eta_i` for anything scale-sensitive.

---

## 4. Results

### 4.1 The two spine series

Medians by year, `h = 5 €/MWh`, re-verified directly against the panels for this
note.

| year | `eta_h5` | `hhi_total` | `hhi_margin_h5` | `n_firms_margin_h5` | median `p*` |
|---|---|---|---|---|---|
| 2018 | 1.835 | 1512 | 2877 | 8 | 60.4 |
| 2019 | 1.463 | 1298 | 2406 | 12 | 49.0 |
| 2020 | 0.967 | 1406 | 2729 | 10 | 34.7 |
| 2021 | 1.209 | 1365 | 3809 | 6 | 90.0 |
| 2022 | 0.888 | 1180 | 4736 | 4 | 165.0 |
| 2023 | 0.845 | 1191 | 3715 | 5 | 94.7 |
| 2024 | 0.663 | 1342 | 4284 | 5 | 75.6 |
| 2025 | 0.591 | 1285 | 4407 | 4 | 80.0 |
| 2026 | 0.455 | 1318 | 5137 | 3 | 63.0 |

**The predicted divergence is present** [established]. `hhi_total` is
flat-to-declining (1512 → 1318), directionally matching CNMC's own decline;
`hhi_margin_h5` rises +79% (2877 → 5137); the median count of distinct mapped
firms with an offer inside the ±5 €/MWh band falls from 8 to 3. The same rise
appears at every bandwidth (h1: 3707 → 8003; h2: 3356 → 6523; h10: 2421 → 4270),
so it is not an artefact of the band width.

### 4.2 The mechanism, in the shape of the stack

| year | `share_at_zero` | `share_below_p` | `band_density_h5` |
|---|---|---|---|
| 2018 | 0.235 | 0.583 | 8,339 |
| 2020 | 0.260 | 0.522 | 7,359 |
| 2022 | 0.268 | 0.568 | 1,468 |
| 2024 | 0.320 | 0.488 | 2,540 |
| 2026 | 0.343 | 0.458 | 2,731 |

**Both halves of the predicted shape change hold** [established]. Offered volume
at or below €0 rises from 23.5% to 34.3%, and offer density within ±5 €/MWh of
the clearing price falls by roughly two-thirds. A thinner band *is* a steeper
residual demand — this is the same quantity as `η`'s numerator, so it is the
mechanism rather than a second piece of evidence.

**`band_density_h5` falls as a step, not a slide** [established]. It drops ~5×
between 2020 and 2022 and then stabilises at 2,300–2,700 for 2023–2026. Reading
the whole window as one smooth decline misdescribes it.

### 4.3 The collapse is a midday phenomenon, not an evening one — against prediction

Figure 4 was built to run the Jha & Leslie test: does the elasticity collapse
concentrate in the **evening ramp**, where start-up costs bite? Median `eta_h5`
by Madrid local hour:

| hour | 2018 | 2020 | 2022 | 2024 | 2026 | change |
|---|---|---|---|---|---|---|
| 04 (night) | 1.20 | 0.70 | 0.84 | 0.70 | 0.45 | −63% |
| 12 (solar noon) | 1.99 | 1.05 | 0.73 | 0.46 | **0.25** | **−87%** |
| 21 (evening ramp) | 2.13 | 1.31 | 1.10 | 0.87 | 0.78 | −63% |

**The prediction is wrong-signed and this is a real result, not a null**
[established]. In 2018 the day was essentially flat — midday 1.99 against
evening 2.13, a ratio of 1.07. By 2026 the evening is **3.1× more elastic than
midday**, and in 2025 hour 13 reads 0.17 against hour 22's 1.20, a ratio of 7.1.
The evening ramp is now the *most* competitive part of the day; the thin,
concentrated margin sits at solar noon.

That inverts the mechanism the figure was built to test. It is also the more
interesting fact: it says the price-setting margin has been hollowed out
precisely where solar displaced the conventional stack, which is a
renewable-displacement story rather than a start-up-cost story.

### 4.4 The marginal technology moved from gas to water

Share of periods where `marginal_tech` resolves (68.7–80.7% of retained periods
by year — read this table only with that coverage beside it):

| marginal technology | 2019 | 2022 | 2024 | 2026 |
|---|---|---|---|---|
| combined cycle | 34.9% | 35.0% | 9.8% | **2.3%** |
| hydro + hydro cascades | 50.7% | 53.8% | 77.8% | **76.4%** |
| wind | 0.5% | 0.4% | 5.0% | 8.3% |
| nuclear | 0.0% | 0.0% | 3.4% | 3.6% |

**Combined-cycle gas has essentially left the margin** [bounded — on resolved
periods only]. Hydro and the large hydro cascades now set the price in about
three-quarters of periods where the technology can be identified.

This is the single most consequential result in the chapter for what comes next,
because **hydro's marginal cost is an opportunity cost, not a fuel cost**. There
is no invoice for water. That is precisely why every cost-based design in this
repo failed, and it means the failure was not a data-quality problem to be fixed
with a better fuel series — the marginal unit genuinely does not have an
observable marginal cost.

### 4.5 Firm ability and incentive, and a contract-position sign flip

> **Correction, 2026-09-28 — the incentive index double-subtracts contracts,
> and Endesa never flips.** `incentive = ability · (q − θ)/q` takes q from the
> firm's **auction-cleared** sell volume and θ from its **bilateral** schedule
> (PDBF role 4). Bilateral energy never enters the auction, so it is subtracted
> twice — the same error `hortacsu_puller_test.py` caught in its first pass
> (`6c900ec`). θ > q means a firm sells more through contracts than through the
> auction, **not** that it is a net buyer. Everything below that reads a sign or
> a flip off `incentive` inherits this; `ability` does not.
>
> The right measure is the firm's **net auction position**: cleared sales minus
> cleared purchases over all its units. `scripts/analysis/firm_net_position.py`,
> TWh over Feb + Jun + Oct of each year:
>
> | firm | 2018 | 2020 | 2022 | 2023 | 2024 | 2025 | 2026 | panel `q − θ` says |
> |---|---|---|---|---|---|---|---|---|
> | Iberdrola | −4.32 | −3.38 | −3.99 | −3.65 | −1.97 | −1.63 | −2.18 | buyer, up to 4× too large |
> | **Endesa** | −4.10 | −7.69 | −5.30 | −6.62 | **−8.00** | **−6.44** | **−5.27** | **seller from 2024** ✗ |
> | Naturgy | −3.24 | −1.70 | −0.38 | −1.53 | −0.98 | −1.18 | −0.45 | buyer ✓ |
> | Repsol | +1.42 | +0.93 | +1.09 | +0.97 | −0.66 | −0.53 | −0.54 | ≈ the same ✓ |
> | EDP (+ EDP Comercial) | +1.92 | +2.50 | +0.26 | +1.26 | +2.11 | +0.76 | +0.38 | seller ✓ |
>
> - **Iberdrola, Naturgy and (from 2024) Repsol are net day-ahead buyers on the
>   correct measure** — the sign survives, for the right reason now.
> - **Endesa is a net buyer in every year, 2024–2026 included.** Its "flip"
>   below — whether to +0.076 in 2024 on the chain tier or in 2025 on the owner
>   tier — is an artefact: Endesa moved its storage hydro out of bilateral
>   self-supply into the auction from 2024 (bilateral share 0.93 → 0.34,
>   `notes/rq-midday-hydro.md` §3.7), so θ fell and q rose while its net
>   position did not change. **Withdrawn.**
> - **EDP is a net seller** throughout, but much less so once its Portuguese
>   retailer EDP Comercial — a separate group in `owner_groups.parquet` — is
>   counted (2022: +2.48 alone, +0.26 together). EDP Comercial's purchases vanish
>   from 2025; unexplained, possibly an ownership change across snapshots.
>
> **Rebuilt 2026-09-29** — see the tables directly below this box. Every
> `incentive` figure after them in this section is superseded and kept only as
> the record of what was reported.
>
> **A second, smaller issue touches `ability` too** (2026-09-28,
> `scripts/analysis/own_demand_in_band.py`). The firm slope removes a firm's own
> *sell* offers from the band but maps only supply-role units, so its own
> **demand** bids near p* are counted as everyone else's, overstating |RD′_i| and
> understating `ability`. In the median firm-period the correction is zero for
> every firm. In the tail it is not, and it is Iberdrola's: its own demand is
> 4–13% of the band on average, and in its worst 10% of periods from 2023 the
> slope is overstated 2.1–2.5×. EDP's is its pumping (worst decile 31–45% in
> 2018–22, ≤ 10% from 2024); Endesa, Naturgy and Repsol are ≤ 8%. So
> Iberdrola's `ability` is a lower bound, more so after 2022.

**The indices rebuilt, 2026-09-29.** `scripts/analysis/firm_incentive_rebuild.py`
reads the owner-tier firm panel and adds corrected columns beside the old ones
(`outputs/tables/firm_incentive_net.parquet`, 5,499,066 firm-periods). Two
changes: every unit a firm owns is mapped, so its own **buy** offers near p* are
removed from its slope along with its sell offers (`slope_net`, `ability_net`);
and the incentive uses the **net auction position**, `incentive_net = ability ×
n/q = n / (100 |RD′_net|)`, with n = cleared sales − cleared purchases. Both are
in €/MWh per 1% of output withheld; the incentive is negative for a net buyer.
Indices are undefined where the corrected slope falls below 5 MW per €/MWh (0.02%
of firm-periods at h = 5). Figure 5 (`firm_ability.png`) now plots these.

Median `ability_net_h5`:

| firm | 2018 | 2020 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| EDP | 0.101 | 0.109 | 0.444 | 0.216 | 0.200 | 0.218 | 0.184 |
| IBERDROLA | 0.035 | 0.037 | 0.183 | 0.098 | 0.149 | 0.114 | 0.181 |
| ENDESA | 0.033 | 0.011 | 0.123 | 0.046 | 0.077 | 0.108 | 0.087 |
| NATURGY | 0.028 | 0.034 | 0.120 | 0.023 | 0.015 | 0.034 | 0.023 |
| ACCIONA | 0.023 | 0.021 | 0.098 | 0.056 | 0.053 | 0.063 | 0.052 |
| AXPO | 0.025 | 0.035 | 0.167 | 0.093 | 0.077 | 0.077 | 0.053 |
| REPSOL | 0.017 | 0.016 | 0.085 | 0.049 | 0.033 | 0.042 | 0.027 |

Removing own demand raises ability for EDP and Iberdrola only (Iberdrola 2024:
0.121 → 0.149; 2026: 0.147 → 0.181); the rest move in the third decimal. **The
ability results above stand, with Iberdrola's slightly higher from 2021.**

Median `incentive_net_h5`, and the share of firm-periods as a net buyer:

| firm | 2018 | 2020 | 2022 | 2023 | 2024 | 2025 | 2026 | net buyer, 2018 → 2026 |
|---|---|---|---|---|---|---|---|---|
| EDP | +0.019 | +0.018 | +0.166 | +0.131 | +0.045 | +0.031 | +0.024 | 14% → 27% (seller) |
| IBERDROLA | −0.032 | −0.025 | −0.164 | −0.096 | −0.022 | −0.029 | 0.000 | **96% → 50%** |
| ENDESA | −0.029 | −0.051 | −0.169 | −0.144 | −0.147 | −0.138 | −0.093 | **97% → 100%** |
| NATURGY | −0.023 | −0.012 | −0.044 | −0.028 | −0.025 | −0.023 | −0.020 | 93% → 78% |
| ACCIONA | +0.014 | +0.011 | +0.030 | +0.004 | +0.005 | +0.010 | +0.013 | 4% → 22% |
| AXPO | +0.021 | +0.028 | +0.130 | +0.066 | +0.049 | +0.041 | +0.017 | 0% → 10% |
| REPSOL | +0.008 | +0.005 | +0.024 | +0.007 | −0.010 | −0.013 | −0.017 | **1% → 90%** |

What the rebuilt incentive says:

- **Iberdrola, Endesa and Naturgy are net day-ahead buyers**; EDP, Acciona and
  Axpo are sellers; Repsol becomes a buyer from 2024. The signs of the old index
  mostly survive, but its magnitudes did not: Iberdrola's 2022 value was
  −0.617 and is −0.164.
- **Endesa never flips.** It is a net buyer in 97–100% of periods in every year;
  the old index showed a flip to positive in 2024 (chain) or 2025 (owner) because
  Endesa moved its storage hydro from bilateral self-supply into the auction,
  which shrank θ and raised q without changing its net position.
- **Iberdrola is drifting towards balance**: a net buyer in 96% of periods in
  2018 and 50% in 2026 (a partial year), with the median incentive reaching zero.
  New, and not yet explained.

**A mapping issue this exposes.** `ENEL` (Enel Green Power España, 47 TWh of
cleared sales in the panel) stands as a separate group from `ENDESA`, although it
is Endesa's renewables subsidiary. It is a net seller in every period and would
not change Endesa's sign, but Endesa's slope currently counts those offers as a
rival's. `build_owner_groups.py` leaves it unmerged for want of evidence in the
data; merging it would take a hand-verified case there.

Median `ability_h5` and `incentive_h5` (€/MWh per 1% withheld), top firms by
cleared volume:

| firm | ability 2018 | ability 2022 | ability 2026 | incentive 2018 | incentive 2026 |
|---|---|---|---|---|---|
| EDP | 0.096 | 0.413 | 0.183 | +0.076 | +0.133 |
| IBERDROLA | 0.044 | 0.163 | 0.128 | **−0.115** | **−0.126** |
| ENDESA | 0.039 | 0.158 | 0.129 | −0.008 | +0.091 |
| ACCIONA | 0.023 | 0.097 | 0.054 | +0.023 | +0.039 |
| AXPO | 0.024 | 0.140 | 0.055 | +0.024 | +0.055 |
| NATURGY | 0.018 | 0.101 | 0.010 | +0.015 | **−0.046** |

**Ability rose for every major firm except Naturgy, and peaked in 2022**
[established]. The peak coincides exactly with the gas crisis, which is what
§5.2 is about.

**The incentive column carried a coverage trend that the ability column does
not — and as of 2026-09-04 that trend is removable.** `incentive = ability ·
(q − θ)/q` depends on θ, and θ's coverage under the inference chain is not
stable. Under OMIE's published owner it is:

| year | 2018 | 2020 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| inferred `firm` | 0.741 | 0.887 | 0.902 | **0.929** | 0.848 | 0.809 | 0.774 |
| **`agent_owner`** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | 0.993 | 0.983 |

(PDBF `role_code == "4"` sell leg, Feb/Jun/Oct of each year. The `firm` row
re-measures the same quantity the 0.739–0.942 series above reported; small
differences are the 2026-08 mapping rebuilds.)

**θ is fully attributable for 2018–2024 and ≥98% after.** The mechanism behind
the old warning — unmapped θ being θ attributed to no firm, so a firm's own θ
looks smaller when the mapping worsens, pushing `(q − θ)/q` and hence incentive
*up* — has nothing left to operate on. Rebuild the θ panel on `agent_owner`
before reporting incentive; on the inference chain the warning below still
stands.

**Where ability and incentive disagree on the old panel, ability is still the
clean series** [established] — that judgement was correct and is why the
ability results were reportable while the incentive ones were not.

**Iberdrola's incentive index is persistently negative while its ability is
positive** [bounded]. That is the Hortaçsu & Puller (2008) contract-position sign
flip: `θ > q`, so the firm is a **net buyer** in the day-ahead auction and wants
the price *down*, whatever its ability to push it up. It is consistent with
Iberdrola dominating the bilateral-contract panel (**621 TWh** of θ — 3.4× the
next *named* firm, Endesa at 182 TWh, but only 2.8× the whole UNMAPPED bucket at
221 TWh, so "three times the next firm" holds against a firm and not against the
unattributed residual), and it is the one incentive result robust to the drift —
the sign holds in every year including the 2023 coverage peak, and the magnitude
is far too large to be a mapping artefact.

**Iberdrola is not alone, and on the rebuilt panel the others are no longer
confounded** [established, 2026-09-04]. Naturgy's incentive is negative in
**every** year and Endesa's in 2018–**2024**, so three of the six largest firms
are net day-ahead buyers across essentially the whole window — the sign flip is
a feature of Iberian contracting, not one firm's idiosyncrasy. **Endesa's flip to positive in 2024 (−0.049 → +0.076)
lands in exactly the year θ coverage drops 0.942 → 0.838**, which is precisely
the confound above and precisely the direction it predicts — so on the current
panel it must not be read as a change in Endesa's contract position. Its
*ability* series shows no such break (0.071 → 0.114 → 0.134), which is the
reason to trust ability here.

**Rebuilt 2026-09-04, and the flip was an artefact** [established]. θ and the
residual-demand panel now exist on both mappings —
`contract_position_panel_owner.parquet` (3,553,773 rows) and
`firm_residual_demand_full_owner.parquet` (5,499,066 firm-periods), via
`--tier owner`. Ownership is rolled up to corporate groups by
`build/build_owner_groups.py` (see below). θ coverage on the owner tier is
**1.000 for 2018–2024**, 0.997 and 0.980 after, against 0.738–0.940 on the
inference chain. Median `incentive_h5`:

| firm | tier | 2018 | 2020 | 2022 | 2023 | **2024** | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| IBERDROLA | chain | −0.115 | −0.116 | −0.658 | −0.181 | −0.163 | −0.149 | −0.126 |
| IBERDROLA | **owner** | −0.098 | −0.095 | −0.617 | −0.130 | −0.099 | −0.088 | −0.092 |
| ENDESA | chain | −0.008 | −0.031 | −0.056 | −0.049 | **+0.076** | 0.099 | 0.091 |
| ENDESA | **owner** | −0.017 | −0.023 | −0.063 | −0.066 | **−0.010** | 0.077 | 0.060 |
| NATURGY | chain | **+0.015** | −0.024 | −0.077 | −0.052 | −0.033 | −0.038 | −0.046 |
| NATURGY | **owner** | **−0.030** | −0.025 | −0.109 | −0.070 | −0.050 | −0.090 | −0.069 |
| REPSOL | **owner** | 0.011 | 0.010 | 0.041 | 0.018 | −0.000 | −0.001 | −0.011 |
| EDP | chain | 0.076 | 0.076 | 0.287 | 0.161 | 0.154 | 0.160 | 0.133 |
| EDP | **owner** | 0.035 | 0.034 | 0.173 | 0.161 | 0.068 | 0.048 | 0.031 |

**Endesa does not flip in 2024.** On flat θ coverage 2023 → 2024 runs
−0.066 → **−0.010**, not −0.049 → +0.076. It stays a net day-ahead buyer through
2024 and flips in **2025**. The caution above was right, and right for the
reason it gave.

**Naturgy is a net buyer in every year**, its 2018 sign reversing (+0.015 →
−0.030). **Repsol joins them at the end**, crossing to ≈0 in 2024 and negative
by 2026. So **four of the seven largest firms are net day-ahead buyers over
substantial stretches**, which strengthens the "feature of Iberian contracting"
reading rather than weakening it.

**Iberdrola's negative incentive survives everywhere** [established], 10–40%
smaller. It was already the one result called robust to the drift, and it is.

**EDP's magnitudes halve without changing sign** — its Portuguese regulated
supplier `SU ELETRICIDADE` (7.3% of supply volume) is now grouped into EDP, so
θ rises and `(q − θ)/q` falls. A correction, not drift, but EDP's *levels* here
supersede every earlier version of this table.

**Cross-firm levels are now usable, with one limit.**
`data/omie/registry/owner_groups.parquet` maps 1,451 owner strings to 1,098
groups on three evidence layers — the independent ESIOS chain's verdict on an
entity's own units (81.7% of supply volume), a stem match onto a group that
layer established (2.0%), and seven hand-verified cases (0.3%) — leaving 13.3%
standing as their own group because no merge evidence was found. That last
number is the limit: an unmerged entity understates its group, visibly and in a
known direction. It does not merge competitors, which is the failure that would
corrupt a share table.

**The incentive *levels* are not comparable across rows of this table** — a
second reason, independent of the coverage drift above. §3.2's measurement
asymmetry lands directly here: on 2024-01, 83.4% of EDP's θ and 77.5% of
Acciona's sits on `purchase_retail` registrations whose MW can never enter `q`,
against 6.0% for Naturgy, 0.6% for Endesa and 0.0% for Iberdrola (ENGIE, not
tabulated, is 56.6%). EDP's and Acciona's incentive columns are therefore biased
**downward** relative to the rest, so EDP's +0.076 → +0.133 should be read as a
floor rather than a level, and the cross-firm ranking of the incentive columns is
not like-for-like. The within-firm time profile is the safer reading, and
`ability` is unaffected.

The general lesson for any design built on these indices: **ability is measured
from the bid archive alone and inherits only the ownership mapping; incentive
inherits the ownership mapping twice over, through θ as well.**

**Axpo's θ is ≈ 0, so its ability and incentive very nearly coincide**
[established] — not exactly: θ is non-zero in **10.5%** of Axpo's 79,036 periods,
the largest gap between the two indices anywhere in the panel is **0.0297**
€/MWh per 1% withheld, and the 2026 medians read **0.0546 against 0.0545**. The
divergence is real but negligible, which is consistent with `CLAUDE.md`'s note
that Axpo is a *representante* trading third-party assets rather than an asset
owner.

---

## 5. Validation

Four checks, each able to kill a claim.

### 5.1 Bandwidth sensitivity — passes

Every `η` and `hhi_margin` figure above is reported at h ∈ {1, 2, 5, 10} €/MWh in
the panels. The `hhi_margin` rise and the `η` decline appear at all four. The
divergence is not a property of the band [established].

### 5.2 The clean-years trend — **the chapter's spine is a step, not a slope**

`scripts/analysis/clean_years_trend.py`. 2021–2023 holds the gas crisis, the
windfall levy (RDL 17/2021) and the Iberian gas cap (RDL 10/2022), and `η` is not
even monotone through it. The spec required re-estimating both trends on
**2018–2020 + 2024–2026 only**, before anyone reads a mechanism into the series.

Specification: `y_t = b·t + hour-of-day FE + month-of-year FE (+ block FE)`, `t`
in years, standard errors clustered on year-month. Six specifications; `clean`
pools the two clean blocks with one slope, `clean+block` adds a late-block dummy
so the slope is identified from **within-block** variation only and cannot borrow
strength from the level gap across the excluded years, and `clean+15min` adds a
dummy for the 15-minute market time unit.

| outcome (log) | full | clean | clean+block | clean+15min | early 18–20 | late 24–26 |
|---|---|---|---|---|---|---|
| **`eta_h5`** | −0.152 (t −12.9) | −0.154 (t −13.0) | **−0.206 (t −4.8)** | −0.175 (t −11.9) | −0.289 (t −7.3) | −0.073 (t −0.9) |
| `p_star` | +0.008 (t 0.5) | +0.013 (t 1.0) | −0.184 (t −3.5) | +0.015 (t 0.8) | −0.285 (t −8.7) | +0.003 (t 0.0) |
| `eta_h5 / p_star` | −0.161 (t −12.6) | −0.167 (t −20.1) | −0.022 (t −0.7) | −0.190 (t −16.0) | −0.004 (t −0.2) | −0.076 (t −1.1) |
| **`hhi_margin_h5`** | +0.076 (t 15.2) | +0.080 (t 16.3) | **+0.015 (t 0.8)** | +0.079 (t 12.5) | **−0.036 (t −2.5)** | +0.094 (t 3.9) |
| `hhi_margin` × cov² | +0.032 (t 5.8) | +0.035 (t 7.1) | +0.028 (t 1.5) | +0.024 (t 3.9) | −0.035 (t −2.5) | +0.087 (t 3.1) |
| `hhi_total` | −0.020 (t −6.4) | −0.019 (t −6.2) | −0.049 (t −4.3) | −0.012 (t −3.0) | −0.047 (t −2.9) | −0.036 (t −3.7) |
| `band_density_h5` | −0.161 (t −11.4) | −0.166 (t −19.9) | −0.016 (t −0.5) | −0.195 (t −16.7) | −0.033 (t −1.8) | −0.023 (t −0.3) |
| `share_at_zero` (level) | +0.0149 (t 20.4) | +0.0153 (t 21.4) | +0.0090 (t 3.1) | +0.0165 (t 18.0) | +0.0104 (t 4.5) | +0.0078 (t 1.4) |

Clusters: 101 (full), 65 (clean), **36 (early)**, 29 (late). The early block's 36
year-month clusters are what the −0.036 (t = −2.51) below rests on.

**Verdict, in three parts.**

**(a) Dropping 2021–2023 changes nothing on its own** [established]. Every
`clean` coefficient is within 10% of its `full` counterpart. The crisis years are
not what produces either trend, and the naive worry — that a straight line
through the gas spike manufactured the result — is dead.

**(b) The `η` decline cannot be separated from the price level in the early
block — but `η` is still the right series** [confounded].

Within 2018–2020, log `p*` falls at −0.285/yr and log `η` at −0.289/yr, and
`η/p* = |RD′|/Q` is flat (−0.004, t = −0.18) at every bandwidth (−0.018, −0.015,
−0.004, +0.014 for h1/h2/h5/h10, none significant). An earlier draft of this note
read that as `η` being contaminated by the price level and `η/p*` being the clean
structural object. **That is backwards, and the correction matters.**

Take a pure proportional rescaling of the whole stack by λ — a fuel shock,
nothing structural. `|RD′|` counts offered MW inside a band that is **fixed in
euros**, so that band now spans 1/λ of the relative price range and
`|RD′| ∝ 1/λ`. Then `η = |RD′|·p*/Q` is **invariant**, exactly as an elasticity
should be, while `η/p*` scales as 1/λ. Confirmed numerically on simulated step
curves: for λ = 0.5, 1, 2 the elasticity reads 0.829, 0.830, 0.830 while `η/p*`
halves at each step. So it is `η/p*`, not `η`, that a price move drags around.
This is the same fixed-€-band mechanic §5.5 already invokes, and the earlier
draft contradicted itself between the two sections.

The identity settles which series belongs in the chapter. `L = s/η` is a
**proportional** markup, so a lower `η` at a lower `p*` is a genuinely larger
proportional markup bound, not an artefact. `η/p*` is a semi-elasticity and
appears nowhere in the identity. **Raw `η` is the headline series and Figure 1 is
correct as drawn.**

What the data show is therefore an **observational equivalence**, not an
attribution: `|RD′|/Q` was flat while `p*` fell. That is consistent with
€-sticky offer steps (a stack that did not rescale, so a falling price walked
down a fixed ladder and `η` fell mechanically) *and* with real proportional
steepening that happened to offset. **Nothing in this data separates them**, and
the direction is not settled either way. Both series are reported; neither is
presented as the corrected version of the other.

**(c) The margin-concentration rise is a level shift; the elasticity decline is
not** [established]. These must be stated separately, because they behave
differently:

- **`η` survives the strict test.** Under `clean+block` it is −0.206 with
  t = −4.77, at 1.35× the pooled slope. The elasticity decline is robust in every
  *pooled* specification — full, clean, within-block, with a 15-minute dummy, and
  at all four bandwidths — and within the early block alone (−0.289, t = −7.3).
  **It is not identified within the late block alone** (−0.073, t = −0.91;
  insignificant at all four bandwidths, t = −0.29 / −0.44 / −0.91 / −0.97 for
  h1/h2/h5/h10), on 29 clusters and 2.4 years. That is the reverse of
  `hhi_margin`, which *is* identified within the late block, and §7 states the
  asymmetry that way round.
- **`hhi_margin` does not.** Under `clean+block` it is +0.015 (t = 0.84). The
  load-bearing evidence is the two blocks estimated separately, which are
  independent samples: **within 2018–2020 it runs the wrong way at −0.036,
  t = −2.51 on 36 clusters, negative at all four bandwidths**, and within
  2024–2026 it rises at +0.094, t = +3.90. Concentration at the margin was
  flat-to-falling before the crisis, stepped up across it, and has kept rising
  since without reverting. (The `clean+block` point estimate sits outside the
  pooled CI, but that comparison is a heuristic — the two estimates come from the
  same data and are not independent — so nothing rests on it.)

**What this means for the chapter.** The elasticity story is a trend and can be
written as one. The **concentration** story is not: it is a step change
concentrated at the 2021–2023 crisis that did not reverse, plus genuine
continuation after 2024. The honest sentence is: *residual demand steepened
throughout, while the ownership of the margin re-organised around the gas crisis
and stayed re-organised* — which is a more 
specific and more interesting claim than the one the design started with, and a
harder one to attribute to VRE growth alone.

**What survives unambiguously:** `hhi_total`'s decline (significant in every
column including both blocks separately) and `share_at_zero`'s rise (significant
in `clean+block` at t = 3.1). The divergence between aggregate and
near-marginal concentration is therefore real in *both* eras even where the
`hhi_margin` trend is not.

Weighting periods by `resolution_min/60`, so a day counts equally whether it has
24 or 96 periods, leaves every conclusion intact and pushes the `hhi_margin`
block-FE estimate slightly negative (−0.002) — reinforcing the step reading.

### 5.3 The 15-minute break — passes

The day-ahead market moved to a 15-minute market time unit on 2025-10-01, which
mechanically thins any fixed-€ band. Two checks.

**A 15-minute dummy** added to the clean-years regressions changes no sign and no
verdict, for any outcome (`clean+15min` column throughout §5.2) [established].

**The adjacent-month comparison, corrected.** An earlier record of this check
reported "Sep-2025 hourly 4808 vs Oct-2025 15-minute 5016, a +4% step".
**That does not reproduce on this panel** at any bandwidth, on the median or the
mean, and it is superseded. The reproducible version:

| window | Sep-2025 (60 min) | Oct-2025 (15 min) | step |
|---|---|---|---|
| raw | 4,514 | 3,895 | **−13.7%** |
| `p* ∈ [70,100]` | 4,567 | 4,841 | +6.0% |
| `p* ∈ [75,95]` | 4,888 | 5,194 | +6.2% |

The raw row is **not** a usable comparison and is shown only to document what the
uncorrected number looks like: median `p*` is 77.5 in September and 93.5 in
October, and a fixed ±5 €/MWh band is a narrower *relative* window at the higher
price, so the two months are not measuring the same object. The conclusion rests
on the price-matched rows alone.

**Price-matched, the break is worth about +6% against a +79% window trend**
[bounded] — an order of magnitude too small to produce the result.

**`η` by resolution era** [established], which the spec asks for and the
`hhi_margin` check above does not cover:

| era | by year |
|---|---|
| 60-minute (62,721 periods) | 2018 1.83 · 2020 0.97 · 2022 0.89 · 2024 0.66 · 2025 0.49 |
| 15-minute (16,315 periods) | 2025 **0.65** · 2026 0.45 |

Nothing is at risk here — 2026 is wholly 15-minute, so the 2026 figure needs no
splitting — but note the direction: *within* 2025 the 15-minute periods read
**higher** `η` (0.65) than the hourly ones (0.49), which is the opposite of the
mechanical band-thinning worry, and the decline continues inside the 15-minute
era alone (0.65 → 0.45).

### 5.4 Coverage drift — the bound, and one place it bites

Firm-mapping coverage inside the band is **not** stable, and its direction
matters: renormalising HHI over a shrinking mapped set mechanically **raises**
it, because departing share is redistributed onto the firms that remain.
`corr(hhi_margin_h5, mapped_share_margin_h5) = −0.292` confirms the mechanical
sign in this data.

| year | coverage, mean | coverage, p10 | coverage, median |
|---|---|---|---|
| 2018 | 0.966 | 0.943 | 0.974 |
| 2022 | 0.940 | 0.849 | 0.978 |
| 2025 | 0.882 | **0.650** | 0.964 |
| 2026 | 0.896 | 0.755 | 0.950 |

**Report the mean and p10, never the median** [established] — the median is
0.950–0.987 throughout and hides the entire drift.

**The bounded figure, and it is the one to quote** [bounded]: if the unmapped
in-band volume is atomistic, `HHI_true ≈ HHI × coverage²`. Constructed **per
period** — `hhi_margin_h5 × mapped_share_margin_h5²` on each of the 79,036 rows,
then the median by year, which is exactly the series `clean_years_trend.py`
regresses — the 2018 → 2026 rise is **+62.5%** (2,694 → 4,378) against **+78.6%**
raw (2,877 → 5,137). The headline survives at reduced magnitude.

**State the construction, because it is not unique and the spread is wide.**
Aggregating before multiplying instead of after gives +69.9% (median HHI × median
coverage²) or +53.7% (median HHI × *mean* coverage²) on the same panel. An
earlier draft quoted the last of these as "+54%" without saying so, which made
the note's own adjusted figure inconsistent with the adjusted *series* every
regression in §5.2 uses. The per-period product is the one quoted throughout.

Two things worth noting about the adjustment. It *weakens* the full-sample
magnitude but *strengthens* the within-block reading — the coverage-adjusted
`clean+block` estimate is +0.028 against +0.015 raw, and the pooled slope now
lies inside its confidence interval rather than outside it. That is because
coverage itself steps across the crisis (`clean+block` coverage trend −0.001,
t = −0.32, against a pooled −0.0135, t = −14.0), so part of what made raw
`hhi_margin` look like a step was coverage looking like a step.

### 5.5 The price-matched check — the headline's strongest defence

A fixed ±h €/MWh band is a narrower *relative* window when prices are high, which
could thin the band and inflate `hhi_margin` for reasons unrelated to
concentration. Median `p*` is 60.4 (2018) and 63.0 (2026), so the window's
endpoints are not far apart — but the sharper test holds the price level fixed
and lets years vary. Restricting to `p* ∈ [55, 70]` €/MWh, a constant relative
band width in both years:

| | `hhi_margin_h5` | firms in band | n periods |
|---|---|---|---|
| 2018 | 2900 | 8 | 4,595 |
| 2026 | **7347** | **2** | 711 |

**The rise is larger on the price-matched subsample than on the unrestricted
panel** [established] — 2900 → 7347 against 2877 → 5137. That is the opposite of
what band-thinning-at-high-prices predicts, and it is the single strongest
defence of the headline.

### 5.6 Selection: the late years describe a shrinking, non-random subset

This is the limit that most constrains what the chapter can say, and it belongs
in the text rather than in a filter.

| year | retained | market splitting | zero-price (unconditional) |
|---|---|---|---|
| 2018 | 94.5% | 5.2% | 0.0% |
| 2021 | 96.9% | 2.6% | 0.5% |
| 2024 | 83.4% | 6.2% | 12.4% |
| 2026 | **66.1%** | **16.0%** | **25.0%** |

Re-derived independently from the raw price file for this note, not copied from a
panel's own diagnostic.

**Every 2026 number describes about two-thirds of that year's periods, and the
missing third is not random** [confounded]. Both dropped classes are exactly the
high-renewable hours: market splitting is congestion, and near-zero prices are
VRE oversupply. Zero-price periods are excluded upstream because `η` and the
Lerner index are undefined at `p* = 0`; splitting periods are excluded because
there is no single curve to take a margin from.

Two consequences, both directional:

- **`share_at_zero` is a LOWER bound on true growth** [bounded]. The dropped
  periods are precisely where offered-at-zero volume is largest, so 0.235 → 0.343
  understates the rise, and understates it by more in the later years.
- **Concentration and steepness figures are lower bounds too** [bounded].
  Splitting periods are the congested hours when residual demand is steepest and
  ownership most concentrated.

The 61-day 2025 dropout cluster (2025-03-19 → 2025-06-09) thins 2025 in a
correlated way on top of this.

---

## 6. Two designs that will not be re-attempted

Recorded here so neither is rebuilt from scratch. Both are in the spec §7.

**The demand-forecast-level instrument: WITHDRAWN on the exclusion restriction,
not on vintage.** Vintage passed — REE's forecast has mean absolute error 297.5
MW against the market's own day-ahead schedule at 292.1 MW, a ratio of 1.02, so
it is a genuine D−1 vintage and not a nowcast. It fails for a different reason:
**suppliers observe the same D−1 forecast the retailers do**, so it shifts the
clearing point and the submitted supply curve simultaneously — which is precisely
the mechanical-versus-behavioural distinction it was meant to break. The only
component genuinely unknown at gate closure is the residual, and that is revealed
*after* the auction clears. There is no wedge here.

**The forecast-residual → intraday-premium design: DEMOTED to one fact.** The
residual does move the premium with the economically correct sign, at −0.694
(t = −2.80) for 2018–2020 and −1.407 (t = −2.89) for 2023–2025 €/MWh per GW.
**The apparent doubling is a price-level artefact** — median price went 35–61
€/MWh early to 67–93 late — and once scaled by price neither period is
significant. So *"a demand surprise moves the intraday price by roughly 0.7–1.4
€/MWh per GW, correctly signed"* is defensible; *"absorption capacity changed as
VRE grew"* is **not** and must not be claimed.

The general lesson, and §5.2(b) is the other instance of it: **the price level
moved by a factor of five across this window, so any trend in a
€/MWh-denominated quantity has to be checked against `p*` before it is
believed.** Note that the check cuts both ways — here it *demoted* a result,
while in §5.2(b) it turned out that the fixed-€ band already makes `η`
scale-invariant and the naive correction was the contaminated one. Work out how
the specific measure scales; do not reach for a ratio by reflex.

**The fact worth keeping:** Spanish demand became harder to forecast, and two
independent predictors degraded in step — REE's forecast error sd 143 → 369 MW
and the market's own schedule error 250 → 421 MW on the same clean sample. When
two unrelated forecasters get worse together, the thing being predicted got
harder. Figure 6.

---

## 7. What this opens

The descriptives point at one question, and §4.4 is why.

**The marginal unit in MIBEL is now hydro, and hydro has no invoice.** Combined
cycle set the price in 35% of resolved periods in 2022 and 2.3% in 2026; hydro
and the cascades now set it in about three-quarters. Every failed conduct design
in this repo tried to measure a markup against a *fuel* cost. That was never
going to work for a water-value marginal unit, and the failure was structural
rather than a data-quality problem.

Three candidate next steps, in order of how much of this chapter's machinery they
re-use:

1. **The two series move in *different sub-periods*.** §5.2 turns the crisis
   from a nuisance into a design, but the asymmetry has to be stated the way the
   estimates actually run, and it is not the trend-versus-step contrast an
   earlier draft of this section claimed. `η` falls steeply *before* the crisis
   (−0.289, t = −7.3 in 2018–2020) and is **not identified within 2024–2026
   alone** (−0.073, t = −0.91, insignificant at all four bandwidths).
   `hhi_margin` does the opposite: negative before 2021 (−0.036, t = −2.51) and
   rising only after (+0.094, t = +3.90). So each series is identified in the
   block where the other is not.

   **What that does to the pitch.** The original motivation — a *smooth* trend in
   steepness set against a *step* in ownership, where "a gradual driver cannot
   explain a step" — does not survive, because `η` is not measurably a trend in
   the late block. What survives is narrower and still worth a design: the two
   objects are sequenced differently around the crisis, so no single driver with
   one time profile explains both. The narrower claim carries a caveat the wider
   one did not: with 29 clusters and 2.4 years, the late-block `η` null is as much
   a power result as a substantive one, and it should be treated as *not measured*
   rather than as *shown to be flat*. Contract positions (θ), entry and exit in
   the near-marginal band, and the gas-to-hydro substitution are all observable
   here.
2. **The midday margin.** §4.3 says the thin, concentrated part of the day is
   solar noon, not the evening ramp. That is a within-day comparison with a
   plausible exogenous driver (the solar profile) and it does not need a cost
   measure at all.
3. **Water value as the object, estimated jointly.** The honest version of the
   cost question for a hydro-marginal market —
   [`hydro-water-value-design.md`](hydro-water-value-design.md) already has the
   state variable (MITECO reservoir levels) and shows why a single-equation
   reduced form gets the sign backwards.

**The hard ceiling to check first.** Only **32 parent firms own dispatchable
plant at all**, 26 with a computable pre-2021 renewable exposure and 11 above
1,000 GWh. Any design whose treatment varies at parent-firm level has at most a
few dozen clusters. That is the population, not a sample, and it is what
withdrew the differential renewable exposure design. Check it *before* building,
not after.

---

## 8. Standing scorecard

| claim | status | where it can break |
|---|---|---|
| `η` fell 1.83 → 0.45 | **established** | none for the *level* fall; direct panel measurement. The *trend* is not identified within the late block alone (§5.2c) |
| the `η` fall can be separated from the price level in the early block | **confounded — cannot** | band MW per unit of cleared volume is flat while `p*` falls; €-sticky offer steps and real steepening are observationally equivalent here. Note the fixed-€ band makes `η` itself scale-invariant, so this is *not* a reason to prefer `η/p*` (§5.2b) |
| `hhi_total` fell, matching CNMC | **established** | significant in every specification and both blocks |
| `hhi_margin` rose +79% | **established as a level** | +62.5% on the per-period coverage-adjusted series (§5.4) |
| the `η` decline is a trend, not a crisis step | **established** | survives `clean+block` at −0.206, t = −4.77, and all four bandwidths — but **not identified within the late block alone** (−0.073, t = −0.91), so it is a trend across the window, not a demonstrated one after 2024 (§5.2c, §7) |
| `hhi_margin`'s rise is a secular *trend* | **rejected** | it is a step across 2021–2023 (§5.2c); pre-2021 slope is negative, t = −2.51 on 36 clusters |
| the divergence between the two HHIs is real | **established** | survives price-matching, which *strengthens* it (§5.5) |
| `share_at_zero` rose 0.235 → 0.343 | **established, lower bound** | dropped zero-price periods are where it is largest |
| band density fell ~2/3 | **established** | falls as a step 2020→2022, not a slide |
| the collapse is an *evening ramp* phenomenon | **rejected** | it is a midday phenomenon (§4.3) |
| gas left the margin, hydro took it | **bounded** | resolved periods only, 69–81% coverage |
| Iberdrola is a net day-ahead buyer | **established, on the net auction position** (rebuilt 2026-09-29) | so are Naturgy and Endesa in every year, and Repsol from 2024. Iberdrola's net-buyer share falls from 96% of periods (2018) to 50% (2026). The earlier evidence, `incentive`'s `(q − θ)`, double-subtracted contracts (§4.5) |
| firm ability (price impact) rose across the window, peaking in 2022 | **established, rebuilt** | own demand now removed from the slope; changes only EDP and Iberdrola, upwards |
| Endesa's flip to a positive incentive | **withdrawn** (2026-09-28) | an artefact of the double subtraction: Endesa moved hydro from bilateral into the auction in 2024 and stayed a net buyer (§4.5) |
| θ measures contract position | **bounded** | physical bilateral only; misses financial hedges |
| any 2026 figure | **confounded** | 66.1% retention, selected against high-VRE hours |

**Six designs failed on the cost measure; this one produced results because it
needs none.** The two that came out against prediction — the midday-not-evening
inversion, and `hhi_margin` being a step rather than a trend — are the two most
useful things in the chapter, and both would have been missed by a design that
only checked whether its headline had the expected sign.

Reproduce the trend table with:

```bash
.venv/bin/python scripts/analysis/clean_years_trend.py
.venv/bin/python scripts/analysis/clean_years_trend.py --weighted
.venv/bin/python scripts/analysis/clean_years_trend.py --bandwidth 1
```
