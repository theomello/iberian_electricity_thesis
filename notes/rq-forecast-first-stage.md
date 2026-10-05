# Day-ahead forecasts as instruments — the first stage

Step-offer design (`docs/specs/2026-10-01-step-offer-design.md`) §5.1 and §10
step 3. Run 2026-10-02. Script: `analysis/forecast_first_stage.py`. Results:
`outputs/tables/forecast_first_stage.csv`. Data: `qa/check_esios.py`.

**In one line.** REE's day-ahead forecasts move the price strongly and each
firm's markup term X enough to instrument it for four of the five firms, but not
in the way §5.1 expected. A windy or sunny forecast **lowers** every firm's net
position, including the firms that own the most wind, because it pushes their
gas and hydro out of the dispatch. That loss outweighs what their own wind and
solar add.

*§2–§3 quote the run on static owners. §6 has the figures on owners by date and
share (rerun 2026-10-03): the first stage gets stronger for Endesa and Naturgy, and
the reading does not change.*

## 1. Design

For each firm f, on the periods the legs use (`clean & ~zero_price`):

    y_ft = a_W W_t + a_S S_t + a_D D_t + FE + e_ft,   y in {n, |RD'|, X, p}

- **W, S, D**: REE's wind, solar and demand forecasts for D+1, published before
  11:00 on D-1, an hour before day-ahead offers close (ESIOS 1777, 1779, 1775),
  in GW. Peninsular Spain only.
- **n**: the price-exposed net position. **|RD′|**: the slope of rivals' supply
  within ±5 €/MWh of the price. **X = n/|RD′|**. **p**: the Spanish price. All
  from `firm_x.parquet`.
- **Fixed effects**: year-month × local hour, which absorbs capacity build-out
  and the seasonal shape of solar, and day of week. What remains is weather
  relative to that month and hour. Standard errors are clustered by week.
- **F** is the cluster-robust Wald statistic for the three forecasts jointly,
  divided by three.
- **Sample**: the hourly era, 2019-01-01 → 2025-09-30, 387 weeks. From
  2025-10-01 each hour has four quarter-hour rows, and those eight months would
  carry 28% of the weight. With them the results are close (in the CSV).

**Own versus rivals' fleets.** There is one national forecast per technology. A
firm holding a fixed share s_W of national wind and s_S of solar has own exposure
s_W·W + s_S·S and rivals' exposure (1 − s_W)·W + (1 − s_S)·S. Whenever
s_W ≠ s_S these are two different combinations of W and S, so regressing on W and
S is the own/rivals split, reparametrised.

| firm | share of offered wind | share of offered solar |
|---|---|---|
| EDP | 8.4% | 0.8% |
| Iberdrola | 8.1% | 3.6% |
| Endesa | 9.0% | 1.4% |
| Naturgy | 4.1% | 1.3% |
| Repsol | 2.6% | 1.6% |

## 2. Results (hourly era)

Coefficients per GW of forecast, standard errors in brackets.

| firm | y | wind W | solar S | demand D | F |
|---|---|---|---|---|---|
| all five | p (€/MWh) | −4.8 (0.2) | −5.0 (0.4) | +4.7 (0.4) | 163 |
| EDP | n (MW) | −142 (7) | −208 (12) | +94 (9) | 241 |
| Iberdrola | n | −79 (9) | −248 (15) | +54 (13) | 109 |
| Endesa | n | −43 (4) | −56 (10) | −99 (8) | 87 |
| Naturgy | n | −40 (7) | −86 (12) | +53 (11) | 24 |
| Repsol | n | −19 (3) | +3 (5) | +29 (4) | 33 |
| EDP | \|RD′\| (MW per €/MWh) | +31 (5) | +7 (6) | −14 (4) | 16 |
| (the other four) | \|RD′\| | +26 to +32 | +3 to +6 | −9 to −12 | 13–15 |
| EDP | X (€/MWh) | −1.1 (0.1) | −1.5 (0.2) | +0.9 (0.1) | 64 |
| Iberdrola | X | −0.6 (0.1) | −2.5 (0.2) | +0.4 (0.1) | 53 |
| Naturgy | X | −0.3 (0.1) | −0.6 (0.1) | +0.4 (0.1) | 18 |
| Repsol | X | −0.1 (0.0) | 0.0 (0.0) | +0.1 (0.0) | 14 |
| Endesa | X | −0.2 (0.1) | −0.6 (0.2) | −0.2 (0.1) | 10 |

One within-sample standard deviation of the wind forecast moves n by 0.2–0.5 of
its own standard deviation, the price by 0.57, X by 0.04–0.20.

## 3. Reading

1. **The price.** Each GW of forecast wind or solar lowers p by about 5 €/MWh, and
   each GW of forecast demand raises it by as much. F = 163; the forecasts
   explain 39% of the price's variation within month-hour.
2. **The net position falls with renewables, for every firm.** EDP holds 8.4% of
   offered wind; if only its own fleet mattered, 1 GW more forecast wind would
   raise its n by up to 84 MW. Instead n falls by 142 MW. The forecast lowers
   the price, the firm's gas and hydro clear less, and that outweighs its own
   wind. Iberdrola's −248 MW per GW of solar probably has the same cause, in
   leg A's setting: hydro moved out of sunny hours (not checked unit by unit). **§5.1 expected the own-fleet
   forecast to raise n. For these five firms it does not show.**
3. **Endesa responds to demand the other way** (−99 MW per GW). It is a net buyer
   in every period of the sample: more demand adds more to its retail purchases
   than to its sales.
4. **Rivals' slope rises with wind** (+26 to +32 MW per €/MWh per GW, F 13–16),
   not with solar. Likely because a lower price sits where offers bunch more
   densely (not checked).
5. **X.** The three forecasts instrument X with F = 64 (EDP), 53 (Iberdrola),
   18 (Naturgy), 14 (Repsol) and 10 (Endesa, borderline). Three instruments for
   one endogenous variable leave two overidentifying restrictions: the design's
   test that β is the same whichever forecast moves X.
6. **For leg D.** The forecasts are the pre-auction, day-level shifter of n that
   leg D lacked: 0.2–0.5 standard deviations per standard deviation of wind.
   Endesa cannot help there, being a net buyer throughout. Shares of periods
   with n > 0: Repsol 68%, Iberdrola 38%, EDP 21%, Naturgy 18%.

## 4. Limits

- **Zero-price periods are excluded**, as in the legs. They are 12% of periods in
  2024 and 15% in 2025, mostly windy or sunny ones, so from 2024 the sample is
  selected on the instrument. Before 2023 they are under 1%.
- **Exclusion is not shown here.** A first stage says the forecasts move X; it
  cannot say they move p − c only through X. A windy forecast also changes which
  plants run, hence start-up and minimum-load costs (design §3, §5.1).
- **Spain only.** Portugal's forecast needs the ENTSO-E token; EDP's Portuguese
  fleet is not in W or S.
- **No 2018.** REE's forecasts start in 2019.
- **The shares are offered volume**, which is partly a choice. They are used only
  to read the coefficients, not in the regressions.

## 5. Next

- Use W, S and D as the instruments of the step-offer estimator (design §8 step
  5b), thermal firm-periods and the gas-cap window first. Report the
  overidentification test.
- Leg D: rerun the sign-of-n test with the forecasts as the shifter of n, on
  EDP, Iberdrola, Naturgy and Repsol.
- Revise §5.1's own-versus-rivals split. The forecasts are better described as
  shifters of the residual demand's level, which move p, n (through dispatch) and
  |RD′|.

## 6. Rerun on owners by date and share (2026-10-03)

n and X now count each co-owned reactor for every co-owner by share and dated
sales at their dates. The price and the slope barely move; n moves where the
reactors and the sales sit. F on the hourly era, static → dated:

| firm | F on n | b_W / b_S on n (MW per GW) | F on X |
|---|---|---|---|
| EDP | 241 → 261 | −142 / −208 → −134 / −207 | 63.7 → 66.4 |
| Endesa | 87 → 115 | −43 / −56 → −42 / −46 | 9.8 → 14.6 |
| Iberdrola | 109 → 114 | −79 / −248 → −74 / −255 | 53.0 → 53.0 |
| Naturgy | 24 → 31 | −40 / −86 → −47 / −89 | 18.2 → 20.9 |
| Repsol | 33 → 33 | unchanged | 14.3 → 14.3 |

Over all periods (the handoff's figures): F on n Endesa 87 → 115, Naturgy 17 → 23,
Iberdrola 79 → 79, EDP 112 → 115. Every firm's n still falls with a windy or
sunny forecast.
