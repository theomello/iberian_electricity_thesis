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
