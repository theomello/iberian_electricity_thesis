# The day-ahead − intraday premium: the buyers' test

Framework spec §9.5 and §9.7 step 4. Run 2026-10-06.
Script: `analysis/da_id_premium.py`. Outputs: `outputs/tables/da_id_premium_results.csv`,
`da_id_premium_bins.csv`, `outputs/figures/da_id_premium.png`. Log:
`.superpowers/sdd/2026-10-06-premium/run.log`.

**In one line.** The premium is small and positive (+0.6 €/MWh) and does not move with
the five firms' combined position in the raw data. When planned reactor outages shift
that position, it moves the predicted way (+0.95 €/MWh per GW, se 0.39).

## 1. The idea

Ito & Reguant (2016). A firm that sells more than it buys in the day-ahead auction
gains from a high day-ahead price. So it holds back there and sells the rest in the
first intraday auction a few hours later, at a lower price. Example: a firm long 2 GW
withholds 200 MW at the day-ahead and sells it at the intraday: the day-ahead price
rises, the intraday price does not, and the premium p_DA − p_ID is positive.

A net buyer does the opposite: it buys less at the day-ahead to push that price down
and buys the rest later. So the premium should rise with the strategic firms'
combined net position N and turn negative when they are net buyers.

**The five firms are net buyers.** Combined (EDP, Endesa, Iberdrola, Naturgy, Repsol;
exposed positions, `firm_x.py`), N < 0 in 92.5% of hours, mean −4.4 GW. Endesa
is a buyer almost always, Repsol mostly a seller.

## 2. Data

- **Premium**: Spanish day-ahead price minus the first intraday auction's: MIBEL's
  session 1 (about 17:00 on D-1) until 2024-06-13, the European IDA1 (15:00 on D-1)
  after.
- **Sample**: 2019-01-01 (REE's D-1 forecasts) → 2025-03-18 (intraday prices quarter-
  hourly from the 19th): 54,170 hours. 2018 without forecast controls.
- **Controls**: realised minus D-1 forecast wind, solar and demand; year-month × hour
  effects; week clusters.

**Missing PV rows are zeros.** ESIOS publishes provincial PV output only when it is
not zero, so night hours have few or no provinces. The first run dropped them as gaps
(38% of hours); their D-1 forecast averages 0.1 MWh.

## 3. Results

**The premium is positive and flat in N.** Mean +0.62 €/MWh, median 0, sd 4.7. By sign
of N: +0.62 when the five are net buyers, +0.58 when net sellers.

| specification | premium per GW of N | se |
|---|---|---|
| hour effects | −0.028 | 0.029 |
| + forecast errors | −0.025 | 0.029 |
| **+ year-month × hour effects (main)** | **−0.029** | 0.035 |
| main, clean periods (no split, clearing identity holds) | −0.017 | 0.036 |
| 2019 – 2021 H1 | −0.003 | 0.026 |
| 2021 H2 – 2023 | −0.037 | 0.067 |
| 2024 – 2025 Q1 | −0.036 | 0.082 |
| 2018, no forecast controls | +0.141 | 0.049 |

In 20 bins of N the premium sits at +0.5 to +0.9 €/MWh from −8 to −2 GW and falls
to −0.1 only in the top bin (N about −0.5 GW).

**The forecast errors barely move it.** Demand above forecast lowers the premium
(−0.40 per GW, se 0.09); wind and solar errors do nothing. Sensibly so: the first
intraday auction is held on the afternoon of D-1, before most of the error is known.

**By firm** (each firm's n, the others' sum as a control): EDP +0.28 (0.08) and
Iberdrola +0.17 (0.05) go the predicted way, Naturgy −0.79 (0.10) and Repsol −0.36
(0.20) the opposite. These are comparisons between firms, not shocks to one.

**Moved by planned reactor outages.** Refuelling is set months ahead and every reactor
belongs to the five, so a planned outage lowers N by part of its lost output without
being a surprise to anyone:

| | estimate | se |
|---|---|---|
| first stage: N per GW of planned outage | −0.49 | 0.12 (F 17.9) |
| premium per GW of N | **+0.95** | 0.39 |

During planned outages the premium falls by about 0.46 €/MWh per GW, as the buyers'
story predicts. The outage also tightens the whole market, which could change the
premium by another route.

## 4. What it means

- **The raw relation is absent.** The premium does not track how much the five buy,
  and it is positive when they are net buyers.
- **Under exogenous shifts in N, it moves the predicted way**: one GW less net buying
  raises the premium by about 1 €/MWh. On one instrument with one plausible exclusion
  threat, it is a lead, not a result.
- **The level is not explained by the five's position.** A positive premium with net
  buyers could come from a risk premium for selling early, or from the fringe; this
  test does not separate them.
- **Next (§9.7 step 5)**: the intraday positions themselves, where the forecast error
  moves each firm's position by its fleet.
