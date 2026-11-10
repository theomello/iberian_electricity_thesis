# papers/

Reference literature. The PDFs are the authoritative copies and are never
edited; `md/` holds machine-generated Markdown for reading, grepping and
quoting into notes.

```
papers/
  *.pdf     originals, untouched
  md/       generated -- regenerate, do not hand-edit
```

Regenerate with:

```bash
.venv/bin/python scripts/build/convert_papers.py
```

The converter rebuilds heading structure from each PDF's own outline and
stamps every page with an anchor carrying the paper's **printed** page number
(these are book chapters, so they start at 615 and 81, not 1):

```
<!-- pdf page 41 | printed p. 655 -->
```

Cite printed pages in notes — they match the PDF's own numbering. Equations,
tables and footnote placement are lossy in the Markdown; check the PDF before
relying on any formula.

## What is here

| file | pages | why it matters |
|---|---|---|
| Hortaçsu & Perrigne (2021), *Empirical perspectives on auctions*, Handbook of IO vol. 5 ch. 11 | printed 81–175 | §7 is electricity auctions; §8.1 is Treasury auctions, which share the same divisible-good maths and carry the discrete-bid identification results |
| Kellogg & Reguant (2021), *Energy and environmental markets, industrial organization, and regulation*, Handbook of IO vol. 5 ch. 17 | printed 615–742 | §4 is electricity markets end to end. Reguant is the author of the canonical Spanish-market papers, and Fig. 2 of the chapter is drawn from Spanish bid data |
| Hortaçsu & Puller (2008), *Understanding strategic bidding in multi-unit auctions: a case study of the Texas electricity spot market*, RAND JoE 39(1) | printed 86–114 | the source of the "contract positions for free" identification trick used in `notes/literature-to-thesis.md` §3: where a firm's bid crosses its own marginal cost, the markup term vanishes, so θ (forward position) is recoverable without contract data |
| Borenstein, Bushnell, Knittel & Wolfram (2008), *Inefficiencies and Market Power in Financial Arbitrage: A Study of California's Electricity Markets*, JIE 56(2) | printed 1–32 | day-ahead vs. real-time price gaps in California persisted because arbitrageurs had market power in the trade itself, not because no one noticed — the reference case for treating MIBEL's day-ahead/intraday spread (and `pdbf` contract positions) as something to check, not assume convergent |
| Sánchez Canales, Xu, Fusar Bassini, Kaack & Hirth (2026), *An empirical estimate of the electricity supply curve from market outcomes*, Energy Economics 161 | printed 1–22 | estimates supply curves from price/quantity equilibria alone (no bids needed), by finding "regimes" where fundamentals are stable enough that demand shocks trace out supply; cites Fabra & Reguant (2014) and the Iberian-exception literature directly, and flags the Iberian gas-price mechanism as a natural application of its own framework |

Reading guidance and the mapping from these chapters onto this repo's data is
in [`notes/literature-to-thesis.md`](../notes/literature-to-thesis.md).

## Second pass (2026-08-18) — 14 more papers

Read against the two active designs (`notes/hydro-water-value-design.md`,
`notes/rq-gas-cap-conduct.md`) and the candidate-question menu in
`notes/literature-to-thesis.md` §9. Detail lives in whichever note each
paper bears on; this table is the index.

| file | what it is | why it matters |
|---|---|---|
| `ssrn-5736763.pdf` | Arzhintar, Leslie, Neill & Wyrwoll (2025 preprint), *Inferring the Value of Stored Water in Hydroelectric Schemes*, Snowy Scheme, Australia | the paper `hydro-water-value-design.md` named as the source of `c(pf, Vol, Snow)` before anyone had read it — turns out to be OLS on an FOC-implied cost measure with `pf`/`Vol`/`Snow` as separate additive regressors, restricted to marginal-unit intervals; cheaper than assumed, see the design note's 2026-08-18 section |
| `pena.pdf` | Peña (2024), *Utilities Policy* 87, *A note on hydropower as a marginal price setter for Spain's electricity market in 2021–2022* | Spain-specific precedent for "hydro priced above its opportunity cost"; its CCGT-lag cost proxy shares the exact price-co-movement confound our own design was built to avoid, and its own reservoir-level robustness check is null too — citation, not a shortcut |
| `mcrae_and_wolak_columbia_0.pdf` | McRae & Wolak (2017 draft), *Market Power in a Hydro-Dominated Wholesale Electricity Market*, Colombia (filename's spelling is wrong) | a bid-data-only conduct test — firm-level residual demand elasticity/pivotal-supplier status — that needs no opportunity-cost model at all; a cheap complement to the structural water-value route, see `rq-gas-cap-conduct.md` |
| `mrae_wolak_how_do_firms_exercise_market_power.pdf` | McRae & Wolak, *How do firms exercise unilateral market power? Empirical evidence from a bid-based wholesale electricity market* (book ch. 18, New Zealand) | scanned, no text layer (rendered to page images to read); the finite-difference residual-demand-slope recipe for step-function bids, the η/η^C ability/incentive indices, and a hydro-storage exclusion-restriction market-power test — see `literature-to-thesis.md` §9.1 |
| `Hortasu-StrategicAbilityAffect-2019.pdf` | Hortaçsu, Luco, Puller & Zhu (2019, *AER* 109(12)), *Does Strategic Ability Affect Efficiency? Evidence from Electricity Markets* | structural (cognitive-hierarchy) explanation for Hortaçsu & Puller (2008)'s "small firms bid too steep"; the portable part is its reduced-form design — bid-steepness response to a public cost/capacity shock — see `literature-to-thesis.md` §9.1 |
| `ssrn-3603627.pdf` | Jha & Leslie, *Start-up Costs and Market Power: Lessons from the Renewable Energy Transition* | already summarised in `CLAUDE.md`; this pass extracted the operational equations (production/cost function, dynamic dispatch, competitive-pricing rule, 48-lag solar regression) and a concrete extension using `cab`'s **declared** minimum-income condition where their paper had to estimate one — see `literature-to-thesis.md` §9.2 |
| `energies-17-03102.pdf` | González-de Miguel, van Wunnik & Sumper (2024), *Energies* 17:3102, *Mapping the Wholesale Day-Ahead Market Effects of the Gas Subsidy in the Iberian Exception* | the closest existing paper to our gas-cap design; quantifies the settled effects and states outright it can't address unit/firm-level conduct — its passthrough assumption is the literal null our test is built to reject or confirm, see `literature-iberian-exception.md` |
| `The_Competitive_Effects_of_Linking_Electricity_Markets_Across_Space_April_2021.pdf` | Tangerås & Wolak (2021), *The Competitive Effects of Linking Electricity Markets Across Space* | theory of forward-contract linkage across space (US nodal markets); doesn't map onto MIBEL's spot-price splitting without first confirming how OMIP forwards settle — parked, see `literature-iberian-exception.md` |
| `Fabra-PassThroughEmissionsCosts-2014.pdf` | Fabra & Reguant (2014, *AER* 104(9)), emissions cost pass-through, Spain 2004–2006 | the direct precedent for the gas-cap markup/passthrough equation and the engineering marginal-cost construction; ~86% pass-through prior for a market-wide symmetric shock, with the mechanism explaining why the cap's asymmetric design could plausibly break that benchmark — see `rq-gas-cap-conduct.md` |
| `Fabra et al - 2021 - Estimating the elasticity to real-time pricing.pdf` | Fabra, Rapson, Reguant & Wang (2021, *AER: P&P*), real-time pricing elasticity, Spain | on-setting but the wrong market side (retail households); elasticity ≈ 0 — background support for treating demand as inelastic, not directly usable |
| `ssrn-3601485.pdf` | Leslie, Stern, Shanker & Hogan, *Designing Electricity Markets for High Penetrations of Zero or Low Marginal Cost Intermittent Energy Sources*, Australia NEM | citation/framing value — `cab`'s minimum-income condition is literally the "missing dynamic-cost instrument" this literature says VRE-heavy markets need; also flags a cheap duck-curve/evening-price-ramp check on data already in hand |
| `wolak_eepe_final.pdf` | Wolak, *Long-Term Resource Adequacy in Wholesale Electricity Markets with Significant Intermittent Renewables* (California Aug 2020, Texas Feb 2021) | no confirmed Spain analogue event, but the low-combined-VRE-output-duration method (their Tables 3–6) is directly reusable on REE realtime 5-min data |
| `w32616.pdf` | McRae & Wolak, *Reliability Options in Renewables-Dominated Electricity Markets* (NBER WP 32616), Colombia | the policy mechanism has no Spanish counterpart; two techniques transfer regardless — unilateral-scarcity testing and water-opportunity-cost-by-dispatch-matching |
| `SFPFC_paper_published.pdf` | Thurber et al., game-based study of standardized forward contracting for resource adequacy | experimental study, fictional players, no real market microdata — citation-only |

## Third pass (2026-10-06) — 6 papers from the ScienceDirect *Energy Economics* alerts

Screened from ~130 new *Energy Economics* 2026 articles on abstract and a
keyword check, **not read in full** — the "why it matters" column is what the
abstract supports, to be confirmed on a real read. The two papers below marked
†  are the closest to an active design.

| file | what it is | why it matters |
|---|---|---|
| `The-Iberian-exception--What-was-the-cost-of-distorting-electri_2026_Energy-E.pdf` † | Lou, Pollitt, Robinson & Arcos-Vargas (2026, *Energy Economics* 157, 109288), cost of the Iberian exception | published version of the "Cambridge CWPE 2535" row in `literature-iberian-exception.md`. Rebuilds the OMIE day-ahead bid stack with and without the subsidy: day-ahead price falls, but net exports to France/Morocco rise and partly offset it; gas-for-power demand +25% in Iberia (+3.2% EU), no detectable TTF effect. Aggregate welfare accounting with no strategic-bidding analysis — a benchmark for `rq-gas-cap-conduct.md` alongside `energies-17-03102.pdf` |
| `Strategic-bid-response-under-automated-market-power-mitigat_2026_Energy-Econ.pdf` † | 2026, *Energy Economics*, US markets 2019 | regression discontinuity: a price cap with penalty switches on only when a structural market-power index crosses a cutoff, then measures the bid response (30–40% of bidders affected). Same design pattern as `rq-clawback-size-rdd.md` and the gas-cap work, built on Wolak-style indices |
| `Machine-learning-for-detecting-collusion-and-capacity-withhol_2026_Energy-Ec.pdf` | 2026, *Energy Economics* 162, 109557, Italy | supervised-ML cartel screens on offer-price distributions plus new day-ahead capacity-withholding screens. Citation / robustness idea for the 2024-01-15 withdrawn-supply wedge; cites Fabra & Toro (2005) (not held yet) |
| `Trading-electrons--Predicting-DART-spread-spikes-in-ISO-el_2026_Energy-Econo.pdf` | 2026, *Energy Economics*, NYISO | spike forecasting plus a price-impact model from day-ahead bid stacks (impact = local supply slope). Framing complement to Borenstein et al. (2008) and Ito & Reguant (2016) for `rq-da-id-premium.md` |
| `Watt-s-better--Pay-as-bid-vs--Uniform-pricing-in-electric_2026_Energy-Econom.pdf` | 2026, *Energy Economics* 109284 | supply-function-equilibrium theory of pay-as-bid vs uniform pricing; peak prices lower under pay-as-bid. Theory citation for the bid-slope / markup designs, MIBEL being uniform-price |
| `Price-formation-in-a-highly-renewable--sector-coupled-ene_2026_Energy-Econom.pdf` | 2026, *Energy Economics*, PyPSA-DE Germany | builds full supply/demand curves from optimisation dual variables; price setting shifts from fossil units to storage and demand as VRE grows. Reference point for candidate B, a model not an empirical study |

`main.pdf` (Sánchez Canales et al. 2026) was also re-downloaded in this batch;
it is the same paper (same DOI 10.1016/j.eneco.2026.109523), so no new file.

## Fourth pass (2026-11-10) — 12 papers on demand elasticities and cogeneration

Added for the demand-side chapter (`docs/specs/2026-11-10-cogeneration-design.md`).
Read from the Markdown at the sections cited, **not in full**.

| file | what it is | why it matters |
|---|---|---|
| `Survey_AR_Energy_Transition.pdf` | Fabra & Reguant (2027, *Annual Review of Economics*, submitted draft of 26 Aug 2026), *Powering the Energy Transition* | §4.3 (p. 22) is the current statement on demand response: household short-run elasticity ≈ 0 in Spain, and footnote 6 reports it is **again ≈ 0 in 2021–2023** (Fabra et al. 2026c), which closes the regulated-tariff household idea. §5.3 (p. 29) cites the plant-level industrial evidence (von Graevenitz & Rottner 2022, German manufacturing; not held) |
| `4-Time_of_Use_Impacts_Enrich_Li_Mizrahi_Reguant.pdf` | Enrich, Li, Mizrahi & Reguant (2024, *JEEM* 123, postprint), Spain's June 2021 time-of-use reform | households cut peak use 9–10%; elasticity −0.08 to −0.135. Method to reuse: a LASSO model of consumption fitted on the pre-period only, then difference-in-differences on its prediction errors, Portugal as the untreated unit |
| `The_real_time_price_elasticity_of_electr.pdf` | Lijesen (2007, *Energy Economics* 29), real-time elasticity, Netherlands | aggregate peak demand against spot prices; a low elasticity benchmark |
| `eprg-wp0623.pdf` | Bonilla (2006, Cambridge EPRG WP 0623), cogeneration adoption in UK and Dutch manufacturing | adoption, not the run decision; its footnote 13 points to Fox-Penner (1990b), who derives the price effects on cogeneration's two operating modes, selling to the grid and displacing purchases — the theory behind the cost in the design spec §2 (not held) |
| `w13507.pdf` | Bushnell, Mansur & Saravia (2007, NBER WP 13507; *AER* 2008), vertical arrangements in US markets | retail obligations as the reason integrated firms price near cost: the supply-side counterpart of this repo's net-position results |
| `w18533.pdf` | Ito (NBER WP 18533; *AER* 2014) | households respond to average, not marginal, price |
| `w18344.pdf` | Jessoe & Rapson (NBER WP 18344; *AER* 2014) | information raises households' price response |
| `hourly_pricing_aer_paper.pdf` | Wolak (2011, *AER P&P* 101(3)) | residential response to hourly prices in an experiment |
| `Berndt-TechnologyPricesDerived-1975.pdf`, `Pindyck-InterfuelSubstitutionIndustrial-1979.pdf` | Berndt & Wood (1975); Pindyck (1979) | the translog cost-share framework for substitution between energy and other inputs, and between fuels. **Scanned: the Markdown is page images, no text** |
| `w8213.pdf` | Patrick & Wolak (2001, NBER WP 8213), industrial customers on half-hourly prices, England and Wales | the framework for substitution across hours within the day. **The Markdown is garbled** (font encoding); read the PDF |
| `w8248.pdf` | NBER WP 8248, not identified | **the Markdown is garbled**; title to be read from the PDF |

Not yet held and worth getting: Hirth, Khanna & Ruhnau (2024, *Energy Economics*), wind
as an instrument for the German wholesale price, elasticity ≈ −0.05 attributed to
industry; Fox-Penner (1990b); von Graevenitz & Rottner (2022).

### Added later the same day (2026-11-10) — 19 more files

Abstracts only, except where a section is cited.

| file | what it is | why it matters |
|---|---|---|
| `ssrn-4251564.pdf` | von Graevenitz & Rottner (ZEW DP 22-038, version Feb 2024), German manufacturing plants | **the closest precedent for the cogeneration design**: plant-level own-price elasticity of electricity *procurement* −0.4 to −0.6, and plants replace procurement with electricity generated on site. Annual census data and network-charge variation; no run decision, no hourly prices |
| `cesifo1_wp12093.pdf` | Fabra, Leblanc & Souza (CESifo WP 12093), distributional effects of the crisis and the Iberian mechanism | Spanish firms and consumer groups, machine-learning counterfactuals. A text search finds no treatment of cogeneration, so the design's event is not covered there (search only, not a full read) |
| `1-s2.0-S0928765501000495-main copy.pdf` | Bjørner & Jensen (2002, *Resource and Energy Economics* 24), Danish industrial micro-panel | energy price elasticity −0.44, lower for energy-intensive companies |
| `1-s2.0-0140988389900017-main copy.pdf` | Considine (1989, *Energy Economics*), functional form in interfuel substitution | the linear logit model of cost shares keeps own-price elasticities negative where the translog does not: the functional form to use if input substitution is ever estimated |
| `cwpe1032 copy.pdf` | Steinbuks (Cambridge WP 1032 / EPRG 1015), interfuel substitution in UK manufacturing | sector-level fuel substitution |
| `0945&EPRG0925.pdf` | Kelly (EPRG 0925), combined heat and power with district heating in the UK | viability and policy; background only |
| `MIT-EL-77-026WP-03830744 copy.pdf` | Pindyck (1977 MIT working paper), the working-paper version of Pindyck (1979) | **readable text**, unlike the journal scan |
| `C_WPTEXT_tppap.PDF.pdf`, `w82482.pdf` | second copies of `w8213.pdf` and `w8248.pdf` | **still garbled** (the PDFs' fonts carry no character map); they need OCR or another source |
| `Halvorsen-EnergySubstitutionUS-1977 copy.pdf`, `Interfuel Substitution and the Industrial Demand for Energy_ An International Comparison.pdf`, `Dynamic Factor Demands and the Effects of Energy Price Shocks.pdf`, `Varian, Hal - Economic models - 1978 Nov copy.pdf` | Halvorsen (1977); Pindyck (1979); Pindyck & Rotemberg (1983); a Varian text | **scans, no text layer** |
| `1391971 copy.pdf`, `1392391 copy.pdf`, `1924999 copy.pdf`, `2525642 copy.pdf` | JSTOR scans, **not identified** (no text layer) | — |
| `CostMin copy.pdf` | lecture notes on cost minimisation (V. Lima) | converted empty |

No OCR tool is installed here (`tesseract`, `pdftoppm` absent); the scans and the two
garbled NBER papers cannot be read until one is.
