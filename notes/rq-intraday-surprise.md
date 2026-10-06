# The intraday surprise design: does not identify β

Framework spec §9.5 and §9.7 step 5. Run 2026-10-06.
Scripts: `analysis/intraday_firm_panel.py` (builds the panels),
`analysis/intraday_surprise_test.py` (tests; `--part`, run in parallel). Outputs:
`outputs/tables/intraday_firm_panel.parquet` (7.1 M group-session-periods),
`intraday_offer_panel.parquet` (6.5 M unit offers), `intraday_surprise_results.csv`.
Logs: `.superpowers/sdd/2026-10-06-intraday/`.

**In one line.** The design fails three checks. A wind surprise reaches each firm
through its whole fleet, not its wind farms. Letting each firm respond in its own way
gives a first stage but instruments that contradict each other. And the "surprise"
predicts day-ahead positions, so firms knew part of it before REE's forecast missed.

## 1. The idea

Day-ahead positions are fixed at noon on D-1 against REE's forecasts. When the wind
then blows harder than forecast, every farm has more to sell. A firm holding 20% of
Spain's wind should find 20% of the surplus in the intraday auctions, which moves its
intraday position n, and so its X = n / |RD′| there, for a reason no offer chose:

    Z_ft = s_f^wind × (realised − D-1 forecast wind)_t     (and the same for solar)

s_f: the firm's share of REE's registered wind (20% Iberdrola, 12% Acciona, 9%
Endesa, 8% Ignis, 8% Naturgy, 6% EDP, …). Realised: ESIOS 1159 / 1161 by province;
forecasts 1777 / 1779.

**What was built.** `firm_x.py`'s computation on OMIE's intraday auctions: each
group's exposed net position and residual-demand slope in each of MIBEL's six
sessions, and the offer price at 50% (25%) of each dispatchable unit's sell volume.
2019-01-01 → 2024-06-13 (after that the European IDA auctions replace the sessions).
Intraday positions are small, tens of MW a session; slopes 110–200 MW per €/MWh
(day-ahead about 500).

## 2. Check one: the first stage

**The shift-share has none, and the wrong sign**: per GW of a firm's share of the
surprise its intraday position moves −10 MW (se 5), F 3.3 (X: F 5.8).

**Why: firms answer the surprise with their whole fleet.** Each firm's intraday
position, summed over sessions, per GW of national wind surprise (year-month × hour
effects):

| firm | wind share | MW per GW of surprise | se |
|---|---|---|---|
| EDP | 6% | −52 | 6 |
| Iberdrola | 20% | −30 | 8 |
| Naturgy | 8% | −18 | 6 |
| Endesa | 9% | +25 | 5 |
| Acciona | 12% | +38 | 2 |
| Nexus | 4% | +6 | 1 |
| Ignis | 8% | +2 | 1 |

When the wind beats its forecast the price falls, and the hydro owners buy back their
own output more cheaply than they sell surplus wind. Only Acciona, almost all
renewables, sells the surplus. Representatives (Ignis, Nexus) barely trade it in the
auctions. The same displacement broke the national forecasts as an own-wind
instrument at the day-ahead (`rq-forecast-first-stage.md`).

**Letting each firm respond in its own way** (firm dummy × wind and × solar surprise,
the ten firms with 1 GW or more; 20 instruments) gives a first stage: F 28 on the
position and 13 on X at the firm level, 10–14 in sessions 3–6. At the unit level, on
the five firms that own thermal plant, it is weaker: F 4.6–6.4.

## 3. Check two: the instruments must agree

On combined cycles and coal (2.2 M unit-session-periods, 90 units; unit × week and
class × session × date × period effects), X instrumented by the firm-specific surprise:

| sample | β | se | F | 95% set (Anderson–Rubin) |
|---|---|---|---|---|
| all sessions | −10.8 | 4.0 | 6.4 | empty (p < 10⁻¹¹ at 0 and at 1) |
| sessions 1–2 (D-1) | −1.6 | 2.8 | 4.6 | empty |
| sessions 3–6 (D) | −21.7 | 5.2 | 5.2 | empty |
| shift-share, all sessions | +14.2 | 9.3 | 3.9 | empty |

An empty set means no single β fits all the instruments: the surprise reaches thermal
offers by some route other than the owner's X. The point estimates mean nothing.

**Not the plants' own efficiency.** A less efficient plant may react to a surprise
whoever owns it. Controlling for each plant's efficiency × the wind and solar surprise
(units with a plant-specific efficiency) leaves the same picture: β −12.6 (4.6), F 5.3,
set empty.

## 4. Check three: the placebo

Day-ahead offers close at noon on D-1, before the surprise. So day-ahead positions and
offers must not respond to it. They do:

| outcome | shift-share F | firm-specific F |
|---|---|---|
| day-ahead X, thermal units' firms | 31.4 | 12.2 |
| day-ahead offer at 50%, thermal | 3.6 | 4.4 |
| five firms' day-ahead X, all hours | 10.1 | 8.2 |
| … day-ahead price above 20 €/MWh | 12.2 | not computable* |
| … day-ahead price above 40 €/MWh | 6.3 | 4.7 |

*Covariance not positive definite in that subsample.

**Not curtailment.** Measured output falls when farms shed at low prices, which would
make it a market outcome. But the placebo fails as much at prices above 20 and 40
€/MWh, where little is shed.

**Not REE's forecast bias.** Within year-month × hour, REE's forecasts explain 2% of
the wind error and 5% of the solar error.

**Most likely, firms forecast their own farms better than REE.** They schedule their
wind at the day-ahead on their own forecasts, so the error against REE's forecast is
partly news they already had. The surprise that matters is the error against the
firm's own forecast, which is not published.

## 5. What it means

- **Intraday surprises do not identify β here**, with either instrument. The
  sequential-market version of the condition needs a shock to a firm's intraday
  position that the firm did not see at the day-ahead. REE's forecast error is not
  one.
- **The fleet-response table is a result in its own right.** When wind beats its
  forecast, EDP, Iberdrola and Naturgy buy back output in the intraday auctions, and
  Acciona and Endesa sell. Big hydro owners absorb wind surprises.
- **What could rescue it**: a firm's own surprise, its farms' realised output (located
  farms × provincial output) minus its own day-ahead wind schedule. That needs the
  firm's wind units in OMIE and leans on the 54% of wind that is located; not built.
