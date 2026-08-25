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

**Iberdrola's incentive index is persistently negative while its ability is
positive** [established]. That is the Hortaçsu & Puller (2008) contract-position
sign flip: `θ > q`, so the firm is a **net buyer** in the day-ahead auction and
wants the price *down*, whatever its ability to push it up. It is consistent
with Iberdrola dominating the bilateral-contract panel (621 TWh of θ, more than
three times the next firm).

**Correction to the earlier reading: Iberdrola is not alone** [established].
Naturgy's incentive is negative from 2019 onward, and Endesa's is negative in
2018–2023 before turning positive in 2024. Three of the six largest firms spend
substantial stretches of this window as net day-ahead buyers. The sign flip is a
feature of the Iberian contracting structure, not one firm's idiosyncrasy, and
any design that reads ability as an incentive will get the sign wrong for a
large share of the market.

**Axpo's θ is ≈ 0, so its ability and incentive coincide exactly** [established]
— consistent with `CLAUDE.md`'s note that Axpo is a *representante* trading
third-party assets rather than an asset owner.

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
in years, standard errors clustered on year-month. Six columns; `clean` pools the
two clean blocks with one slope, `clean+block` adds a late-block dummy so the
slope is identified from **within-block** variation only and cannot borrow
strength from the level gap across the excluded years.

| outcome (log) | full | clean | clean+block | early 18–20 | late 24–26 |
|---|---|---|---|---|---|
| `eta_h5` | −0.152 (t −12.9) | −0.154 (t −13.0) | −0.206 (t −4.8) | −0.289 (t −7.3) | −0.073 (t −0.9) |
| **`p_star`** | +0.008 (t 0.5) | +0.013 (t 1.0) | −0.184 (t −3.5) | **−0.285 (t −8.7)** | +0.003 (t 0.0) |
| **`eta_h5 / p_star`** | −0.161 (t −12.6) | −0.167 (t −20.1) | **−0.022 (t −0.7)** | **−0.004 (t −0.2)** | −0.076 (t −1.1) |
| `hhi_margin_h5` | +0.076 (t 15.2) | +0.080 (t 16.3) | **+0.015 (t 0.8)** | **−0.036 (t −2.5)** | +0.094 (t 3.9) |
| `hhi_margin` × cov² | +0.032 (t 5.8) | +0.035 (t 7.1) | +0.028 (t 1.5) | −0.035 (t −2.5) | +0.087 (t 3.1) |
| `hhi_total` | −0.020 (t −6.4) | −0.019 (t −6.2) | −0.049 (t −4.3) | −0.047 (t −2.9) | −0.036 (t −3.7) |
| `band_density_h5` | −0.161 (t −11.4) | −0.166 (t −19.9) | −0.016 (t −0.5) | −0.033 (t −1.8) | −0.023 (t −0.3) |
| `share_at_zero` (level) | +0.0149 (t 20.4) | +0.0153 (t 21.4) | +0.0090 (t 3.1) | +0.0104 (t 4.5) | +0.0078 (t 1.4) |

**Verdict, in three parts.**

**(a) Dropping 2021–2023 changes nothing on its own** [established]. Every
`clean` coefficient is within 10% of its `full` counterpart. The crisis years are
not what produces either trend, and the naive worry — that a straight line
through the gas spike manufactured the result — is dead.

**(b) But the raw `eta` decline is substantially a price-level effect**
[established, and this is new]. `η = |RD′| · p*/q`, so it is proportional to the
clearing price and a fuel-price move drags it around with no change whatever in
the stack. Within 2018–2020, log `p*` falls at −0.285/yr and log `η` falls at
−0.289/yr — the two are numerically indistinguishable. Netting the price out
leaves `η/p* = |RD′|/q`, a pure quantity object, and its early-block trend is
**−0.004 (t = −0.18): zero**. The price-netted decline holds at every bandwidth
(early-block estimates −0.018, −0.015, −0.004, +0.014 for h1, h2, h5, h10; none
significant).

**(c) Both spine trends are level shifts across the crisis, not slopes through
it** [established]. Under `clean+block`, the price-netted elasticity trend is
−0.022 (95% CI [−0.084, +0.040]) and the `hhi_margin` trend is +0.015
(CI [−0.019, +0.049]). In both cases the pooled slope (−0.167, +0.080) lies
**outside** that interval, so this is a rejection rather than a power failure.
And within 2018–2020, `hhi_margin` runs the *wrong way* — −0.036/yr, t = −2.51,
negative at every bandwidth. Concentration at the margin was flat-to-falling
before the crisis, rose across it, and has kept rising since (late block +0.094,
t = 3.90) without reverting.

**What this means for the chapter, stated plainly.** The spine is **not** a
smooth secular trend driven by renewable growth. It is a **step change
concentrated at the 2021–2023 crisis that did not reverse**, plus a genuine
continuation in the late block. The chapter must be written as that, not as a
gradual re-organisation. The honest sentence is: *price formation in MIBEL
re-organised around the gas crisis and stayed re-organised* — which is a more
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

The raw row is not the like-for-like comparison, because median `p*` is 77.5 in
September and 93.5 in October and a fixed ±5 €/MWh band is a narrower *relative*
window at the higher price. **Price-matched, the break is worth about +6% against
a +79% window trend** [bounded]. Raw, it runs *negative*. Either reading leaves
the break an order of magnitude too small to produce the result, and the raw one
has the wrong sign to produce it at all — so the conclusion the superseded figure
supported still stands, on numbers that reproduce.

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
in-band volume is atomistic, `HHI_true ≈ HHI × coverage²`. On that adjustment the
2018 → 2026 rise is **+54%, not +79%**. The headline survives at reduced
magnitude.

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

Note the family resemblance to §5.2(b): **twice now, an apparent strengthening
over time has turned out to be the price level.** Any trend in a €/MWh-denominated
quantity over this window should be checked against `p*` before it is believed.

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

1. **The step, not the slope.** §5.2 turns the crisis from a nuisance into the
   design. Price formation re-organised across 2021–2023 and did not revert; the
   question is what made it permanent. Contract positions (θ), entry and exit in
   the near-marginal band, and the gas-to-hydro substitution are all observable
   here, and the fact that `hhi_margin` was *falling* before 2021 is what makes
   the break identifiable rather than a trend to be extrapolated.
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
| `η` fell 1.83 → 0.45 | **established** | none; direct panel measurement |
| the `η` fall is *structural* rather than a price-level effect | **confounded** | early-block price-netted trend is zero (§5.2b) |
| `hhi_total` fell, matching CNMC | **established** | significant in every specification and both blocks |
| `hhi_margin` rose +79% | **established as a level** | +54% coverage-adjusted (§5.4) |
| `hhi_margin`'s rise is a secular *trend* | **rejected** | it is a step across 2021–2023 (§5.2c); pre-2021 slope is negative |
| the divergence between the two HHIs is real | **established** | survives price-matching, which *strengthens* it (§5.5) |
| `share_at_zero` rose 0.235 → 0.343 | **established, lower bound** | dropped zero-price periods are where it is largest |
| band density fell ~2/3 | **established** | falls as a step 2020→2022, not a slide |
| the collapse is an *evening ramp* phenomenon | **rejected** | it is a midday phenomenon (§4.3) |
| gas left the margin, hydro took it | **bounded** | resolved periods only, 69–81% coverage |
| Iberdrola is a net day-ahead buyer | **established** | so are Naturgy and (to 2023) Endesa |
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
