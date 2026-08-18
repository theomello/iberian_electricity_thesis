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
