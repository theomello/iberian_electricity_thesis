# Extreme weather as an economic natural experiment, and what that buys in an
# electricity market

Written 2026-08-21, in response to the question "would extreme weather events
provide variation we could use to find a causal effect?" The short answer the
literature gives is **yes for exogeneity, no for the thing that is actually
scarce here** — and the second half is where the design work is.

Sources are marked **[v]** where the citation was verified against the
publisher or NBER this session, and **[bg]** where it is background knowledge
that has not been checked and must be before it is cited in writing.

---

## 1. The framing that matters: exogeneity is not the binding constraint

Every design in this repo already has exogenous variation available. Weather is
the cleanest instrument in applied economics — nothing an electricity firm does
changes next week's rainfall. The scarce good is a **control group**.

MIBEL (Mercado Ibérico de Electricidad, the joint Spanish–Portuguese day-ahead
market) is a single price zone. Storm Filomena (7–11 January 2021), the 2022
heatwaves and the Valencia DANA (*depresión aislada en niveles altos*,
29 October 2024) each hit every unit in the same auction in the same hour. An
event study on any of them is an interrupted time series with N = 1, sitting
inside a window where the gas price moved five-fold underneath.

So the usable question is never "was the weather exogenous" but **"does the
weather event generate differential exposure across units trading in the same
auction at the same instant?"** That reframing is what makes the literature
below relevant or irrelevant, one paper at a time.

---

## 2. The methodological canon: weather as identification

**Dell, Jones & Olken (2014), "What Do We Learn from the Weather? The New
Climate-Economy Literature", *Journal of Economic Literature* 52(3): 740–98.**
[v] The survey that defined the panel-weather design: unit and time fixed
effects, with year-to-year weather realisations as the exogenous variation.
Documents effects on agricultural output, industrial output, labour
productivity, health, conflict and growth. Its own framing of the advantage —
harnessing exogenous within-unit variation to identify *channels*, *nonlinear
effects* and *heterogeneous treatment effects* — is exactly the three things a
market-conduct design would want.

**Hsiang (2016), "Climate Econometrics", *Annual Review of Resource Economics*
8: 43–75.** [v] Formalises the weather/climate distinction econometrically and
derives conditions under which weather variation exactly identifies climate
effects. Also, and more usefully here, notes that papers using weather variation
generally do **not** check the assumptions needed for outcomes to be read as
solutions to a constrained maximisation problem — which is precisely what a
bid is.

**Auffhammer, Hsiang, Schlenker & Sobel (2013), "Using Weather Data and Climate
Model Output in Economic Analyses of Climate Change", *REEP* 7(2): 181–98.** [v]
The practical guide: available datasets, and five common pitfalls economists hit
with historical weather data. Directly relevant to this repo's ERA5 usage — our
own weather series are reanalysis, not station data, and the note in
`fetch_weather.py` about representative-site versus capacity-weighted
aggregation is one of the pitfalls this paper catalogues.

**Hsiang & Jina (2014), "The Causal Effect of Environmental Catastrophe on
Long-Run Economic Growth: Evidence from 6,700 Cyclones", NBER WP 20352.** [v]
The template for doing this with *events* rather than smooth variation — and the
number in the title is the point. National incomes fall relative to trend and do
not recover within twenty years. Their identification is within-country
year-to-year variation in cyclone strikes across a universe of 6,700 events.

**Deryugina (2017), "The Fiscal Cost of Hurricanes", *AEJ: Economic Policy*.**
[bg] Transfers and social insurance as the dominant channel of disaster cost —
the "look where the money actually moves" result.

### The one debate we get to skip

The main controversy in this literature is **external validity**: whether
short-run weather responses identify long-run *climate* responses once agents
adapt (Deschênes & Greenstone; Hsiang 2016; Kolstad & Moore; Lemoine) [v for the
existence of the debate, bg for individual attributions].

That debate does not bind on an industrial-organisation question. We do not want
the climate effect. We want the response of a firm's *offer function* to an
exogenous shift in its state variable, in the sample period, under the market
rules then in force. The short-run weather response **is** the estimand. This is
worth stating explicitly in any write-up, because a referee trained on climate
econometrics will reach for the adaptation critique by reflex.

---

## 3. Extreme events are a different object from marginal weather variation

This is the part the design work turns on, and it is under-emphasised in the
survey literature because most of it studies means.

### 3.1 Nonlinearity — tail effects do not extrapolate from the middle

Schlenker & Roberts (2009) on crop yields and Barreca, Clay, Deschênes,
Greenstone & Shapiro (2016, *JPE*) on temperature and mortality both find sharply
nonlinear responses concentrated in the tails. [bg — verify both before citing]
The methodological consequence is direct: a specification linear in a weather
variable, fitted mostly on ordinary days, does not deliver a tail effect. It
delivers an extrapolation. Anything claiming to measure an *extreme* event needs
either a threshold/indicator form or a flexible bin specification.

The spill-window probe in
[`hydro-water-value-design.md`](hydro-water-value-design.md) ran into exactly
this: the linear-in-wetness interaction and the threshold form gave materially
different answers (−0.17, p = 0.15 versus −0.30, p = 0.04), and neither survived
the event study.

### 3.2 Anticipation — and why this bites hard on bid data

**An extreme weather event is forecast days ahead.** This is the single most
important thing on this page for our setting and it was not recognised until
this pass.

OMIE day-ahead offers for delivery day *t* are submitted at noon on day *t−1*,
with the meteorological forecast in hand. Realised precipitation, wind, or
temperature on day *t* is therefore **not a surprise** to the bidder. Treating a
realised weather outcome as a shock to the firm's information set is wrong on
its face; the object the firm conditions on is the **forecast**, and the residual
(forecast error) is a different and much smaller treatment.

Consequences, all of which cut against the designs sketched so far:

- A realisation-based design measures a blend of the anticipated component
  (which the firm has already optimised against, so no response is expected in
  the offer *function*, only in the quantity offered) and the unanticipated
  component.
- Hydrological state variables are the partial exception — reservoir storage
  integrates weeks of past inflow, so the *level* is known but the *arrival* of
  new water still shifts a state variable rather than surprising anyone.
- The clean version of any weather design here would use a forecast/realisation
  split. Neither ERA5 nor anything else currently in `data/weather/` contains a
  forecast; that is a real data gap, and ECMWF/AEMET forecast archives would be
  a genuine acquisition rather than a reprocessing of what we hold.

### 3.3 Compound structure — effective sample size collapses

Extremes cluster in space and time. Nine hydrographic demarcations and 219
distinct rain episodes over eight years is not 2,007 independent observations,
and the wild cluster bootstrap on nine basins in
`hydro_spill_window_did.py` was doing real work — it moved a t of −2.55 to a
p-value of 0.148. Any extreme-weather design in this setting inherits a small
effective N, and should carry cluster-robust inference designed for few
clusters from the start rather than as a robustness check.

---

## 4. The intersection: extreme weather and electricity markets

### 4.1 The one paper whose design is the closest precedent

**Allcott, Collard-Wexler & O'Connell (2016), "How Do Electricity Shortages
Affect Industry? Evidence from India", *AER* 106(3): 587–624.** [v] Estimates
the effect of electricity shortages on Indian manufacturers, **instrumenting
shortages with supply shifts from hydroelectric availability** driven by
river-basin water conditions. Headline: shortages cut the average plant's
revenue and producer surplus by 5–10%, but productivity losses are much smaller
because inputs are storable; shortages distort the plant size distribution
through scale economies in own-generator costs.

This is the basin-hydrology design, executed at industrial-outcome level, in a
top journal. It is the citation that establishes basin-level hydrological
variation as a legitimate instrument, and it should anchor any write-up of the
hydro designs here. Worth acquiring in full — the NBER version is w19977.

### 4.2 Hydro-dominated markets and conduct — already in `papers/`

`mcrae_and_wolak_columbia_0.pdf` (McRae & Wolak, Colombia) and
`w32616.pdf` (McRae & Wolak, NBER WP 32616) are the hydro market-power
precedents already read; `ssrn-5736763.pdf` (Arzhintar, Leslie, Neill & Wyrwoll)
is the water-value estimation. See `literature-to-thesis.md` §9. Nothing in that
group treats an extreme event as the identifying variation — they use the
hydrological *state*, which is the distinction §3 above is about.

### 4.3 Demand-side: the temperature canon

**Auffhammer, Baylis & Hausman (2017), "Climate change is projected to have
severe impacts on the frequency and intensity of peak electricity demand across
the United States", *PNAS* 114: 1886–91.** [v] Parameterises the demand/temperature
relationship across 166 load-balancing authorities, and the substantive point is
that **peak** effects are much larger than average-consumption effects. The
relevant lesson for us is not the climate projection but the shape: temperature
enters demand nonlinearly and asymmetrically, so a linear temperature control —
which is what `eta_vre_iv.py` currently uses, temperature and its square — is a
coarse approximation in the tails.

There is also a Spain-specific demand study (*Climatic Change*, 2021, "Impact of
climate change on Spanish electricity demand") [v, unread] worth a look for a
Spanish temperature-response function.

### 4.4 Extreme events in wholesale markets: a large, mostly non-causal literature

Winter Storm Uri (Texas, February 2021) is the most-studied event. What exists is
overwhelmingly **market design and description**, not identification: ERCOT's
energy-only market and its operating reserve demand curve, the $9,000/MWh cap,
the allocation of reliability costs to load-shed consumers, and counterfactual
arithmetic (ratepayers would have saved $11.4bn at a $100/MWh cap). [v for the
existence and content of this literature; individual papers unread] Damage
estimates of $80–130bn are widely quoted. There is a companion literature on
Winter Storm Elliott (2022) and the 2023 Texas heatwave.

**Wolak**'s low-VRE-output-duration method (`wolak_eepe_final.pdf`, already in
`papers/`, covering California August 2020 and Texas February 2021) is the piece
of this that transfers: it is a measurement recipe runnable on REE 5-minute
realtime data, noted in `papers/README.md` as reusable.

The European analogue is the **Dunkelflaute** literature — prolonged
simultaneous wind and solar shortfalls. It is real and quantitatively serious
(Nature Communications and Communications Earth & Environment 2025–26; ~1.6
events per European market per year; the most extreme historical event, winter
1996/97, lasted 55 days at 47% of mean renewable availability) but it is
**energy-systems modelling, not economics** — storage sizing and adequacy, not
firm behaviour. [v]

There is also a price-*volatility* time-series literature (e.g. a GARCH-MIDAS
study of Italian prices with extreme-weather indicators, *North American Journal
of Economics and Finance*, 2025) [v, unread]. It establishes that extreme weather
predicts volatility. It does not identify conduct, and its "Granger causality"
language should not be confused with the causal claims this repo is after.

### 4.5 The gap, stated plainly

Across §4.4 there is almost nothing that uses an extreme weather event to
identify **firm conduct from unit-level bid data**. The work is engineering
reliability, price-volatility forecasting, or market-design commentary. The
combination this repo holds — 354 million unit-level day-ahead offers, both
accepted and rejected, with an ownership mapping and a declared start-up cost —
is not what that literature runs on.

That is an opening. It is also a warning: the absence may be because the
identification is genuinely hard for the reasons in §1 and §3.2, not because
nobody thought of it.

---

## 5. What this changes for designs already on the table

**A drought/gas-cap confound, now documented externally.** The Iberian
Exception gas cap took effect 15 June 2022, in the middle of a severe Iberian
drought — Spanish and Portuguese hydro generation hit one of its lowest levels
since the 1990s, with reserves ~28% below the ten-year average in late 2022. At
least one published assessment of the cap states outright that the drought and
the cap **jointly** explain the summer 2022 fall in hydro generation and are
difficult to separate. [v] This bears directly on
[`rq-gas-cap-conduct.md`](rq-gas-cap-conduct.md): hydro is in the cap's
*untreated* group, and its untreated behaviour was being moved by a
simultaneous, unrelated shock. Any difference-in-differences using hydro as a
control across 15 June 2022 needs to address this explicitly, and the reservoir
series fetched on 2026-08-18 is what would let it be controlled for.

**Heatwaves are not a clean demand instrument.** The attraction of temperature
was that it is disqualified as an instrument for renewable output *because* it
moves demand directly — which appeared to make it a clean instrument for demand
itself, and hence a conduct test (does the offer function shift when demand
shifts exogenously?). The 2026 European heatwave reporting undercuts that: heat
simultaneously **cut nuclear and hydro output** through cooling-water and
hydrological constraints while raising demand. [v] Spain's own nuclear fleet at
Ascó and Vandellós is river-cooled on the Ebro. A heat shock is therefore a
joint demand *and* supply shock, and the exclusion restriction fails in the
direction that matters. This does not kill the conduct test, but it means the
test must control for own-technology availability rather than treating heat as a
pure demand shifter — and `indisp`/`indisppt` (OMIE unit unavailability, listed
in CLAUDE.md's catalogue and **not yet fetched**) is what that would need.

**Start with forecasts, not realisations.** §3.2. This applies to every weather
design in the repo, including the VRE instrument in `eta_vre_iv.py`, where the
first stage relates *realised* wind speed to *realised* output — defensible for
an output instrument, weaker for anything asking how a firm's strategy responds.

---

## 6. Worth acquiring

Ranked by what they would actually change here:

1. **Allcott, Collard-Wexler & O'Connell (2016)**, NBER w19977 / *AER* 106(3) —
   the design precedent for basin-level hydrological instruments. Free at NBER.
2. **Dell, Jones & Olken (2014)**, *JEL* 52(3) — the survey to cite for the
   panel-weather design and to pre-empt the adaptation critique. NBER w19578 is
   free.
3. **Hsiang (2016)**, *Annual Review of Resource Economics* 8 — for the
   constrained-maximisation caveat, which is the one that bites on bid data.
   NBER w22181 is free.
4. **Auffhammer, Hsiang, Schlenker & Sobel (2013)**, *REEP* 7(2) — the ERA5
   pitfalls checklist. NBER w19087 is free.
5. A Spanish temperature/demand response function (*Climatic Change* 2021) if
   the demand-shifter route is pursued.

Nothing in §4.4 is worth acquiring in full unless the thesis takes an
event-study turn; the Uri literature is voluminous and mostly not about
identification.
