# Does the interruptibility service explain the industry drift, and how much does its end threaten 2021? (registered on commit)

**Status: registered when this file is committed (user: "Yes, register it", 2026-11-27); the script is committed before
its run.** Descriptive: raw load shapes only, no LASSO, nothing refitted. Follows `2026-11-26-drift-location-design.md`
(the industry drift is a shape drift, about three quarters in Spain's own profile) and `2026-11-26-tariff-drift-design.md`
(it sits in 6.3; the wholesale price spread does not explain it).

## Why
The **interruptibility service** paid large high-voltage consumers to accept curtailment on request (Orden IET/2013/2013).
Participants had to consume at least 50% (40 MW product) or 55% (5 MW product) of their energy in tariff period 6
(nights, weekends, national holidays and all of August), a contractual push toward night load. ESIOS 836–846 give the
participants' metered load by sector (10-minute MW) **from 2015-01-01**: about 3.0–3.5 GW in summers 2015–2017, 3.0 GW in
2018, 2.8 GW in 2019, then halved from January 2020 and near zero from July 2020. Their summer working-day
evening-versus-night log ratio is about −0.13 in every year 2015–2019. Raw 6.3 shape moved from −0.114 (2014) to −0.055
(2018) on the same measure; 6.4 stayed near −0.06.

Two questions:
1. **Explanation.** Did a shrinking, night-heavy participant group make the aggregate high-voltage shape drift toward the
   evening?
2. **Validity.** Every placebo summer had the scheme and 2021 did not. If participants, once free of the period-6 rule,
   moved load out of the night, the no-reform shape for 2021 differs from the placebo summers.

**What is not blind.** The participant totals and their shape by summer above, and the raw 6.3/6.4/E3 shapes 2014–2025
(computed 2026-11-27 while deciding to register). Not computed: the nesting check, the remainder series, the shift-share
split, the bound.

## Data and definitions
- **Participants P:** sum of ESIOS 836–842 and 844–846 (843 is a different indicator), 10-minute MW averaged to the hour
  (= MWh per hour), converted to Madrid local time.
- **Nesting set T:** E3 + E4 + E5 + E6 (ESIOS 1204–1207, 36 kV and above, = the 6.2–6.4 tariffs less 6.2's 30–36 kV
  part), with absent E5 hours counted as zero. Fallback E1–E6 (1202–1207) if T fails S1.
- **Remainder R = T − P.** Shares s = mean P / mean T.
- **Window:** 1 June – 15 September, working days (Monday–Friday, not a national holiday); summers 2015–2019. 2014 has no
  P; 2020 is out (COVID, scheme halved). **Shape** = ln(mean load 18–21h / mean load 0–7h).

## Steps and rules, set now
- **S1 nesting (gate).** P ≤ T in at least 99.5% of window hours 2015–2019, and the hourly correlation of P with T above
  0.5. If T fails, try E1–E6; if both fail, stop: P cannot be removed from any series and only the bound (S3, with s from
  the scheme's published size) is reported.
- **S2 explanation (shift-share).** Slopes per year (OLS over the five summers) of shape(T), shape(R), shape(P) and s. Split
  the change in shape(T) 2015→2019 into a **within** part (changes in shape(R) and shape(P) at the 2015 share) and a
  **composition** part (change in s at 2015 shapes), exactly additive with an interaction term reported.
  - **D1:** participants explain the drift if the composition part is at least half of the change in shape(T) **and** the
    slope of shape(R) is less than half the slope of shape(T).
  - **D2:** if shape(T) has no upward slope over 2015–2019 (slope ≤ 0 or below one se), the window does not contain the
    drift and S2 is uninformative (reported, not read).
- **S3 validity bound.** The shift in the 2021 no-reform shape of T caused by the scheme's end lies between 0 (participants
  keep their pattern) and B = shape(T with P's shape replaced by R's, at the 2019 share) − shape(T, 2019) (participants
  become like non-participants). Compare |B| to the raw 2021 reform shift of the industry pool on the same measure (2021
  shape(T) minus the 2015–2019 mean).
  - **V1:** |B| < one quarter of that shift → the scheme's end is a minor threat, stated in chapter 9. Otherwise it is a
    major threat: chapter 7 reports the industry effect with B beside it, and its sign says which way the 2021 estimate
    is biased.

## Not covered
Per-tariff attribution (P is published by sector, not by tariff or voltage), on-site cogeneration (REE data from 2021
only), plant closures. No estimate is changed by this design; any re-estimation it suggests needs its own go-ahead.

## Results (run 2026-11-27, `scripts/analysis/interruptibility_drift.py`, committed before the run as f5288c5; `outputs/tables/interruptibility_drift.csv`)

**S1 passes on E3–E6:** P ≤ T in every one of 9,015 window hours, hourly correlation 0.75. The participants are inside
the 36-kV-and-above series and are **about half of it**: share 0.57 (2015), 0.52, 0.54, 0.49, 0.47 (2019), 0.01 (2021).

| summer | T (MW) | P (MW) | share P | shape T | shape R (non-participants) | shape P (participants) |
|---|---|---|---|---|---|---|
| 2015 | 5,973 | 3,395 | 0.568 | −0.053 | +0.045 | −0.124 |
| 2016 | 6,024 | 3,132 | 0.520 | −0.044 | +0.059 | −0.134 |
| 2017 | 6,252 | 3,366 | 0.538 | −0.049 | +0.053 | −0.133 |
| 2018 | 6,137 | 2,984 | 0.486 | −0.033 | +0.065 | −0.133 |
| 2019 | 5,851 | 2,761 | 0.472 | −0.035 | +0.061 | −0.137 |
| 2021 | 5,722 | 50 | 0.009 | −0.068 | −0.068 | — |

**S2.** Slopes per year: shape T +0.0046 (se 0.0017), shape R +0.0037 (se 0.0018), shape P −0.0025 (se 0.0010), share
P −0.023 (se 0.006). Shift-share 2015→2019: total +0.018 = composition +0.016 + within −0.001 + interaction +0.003.
**D1: NO.** Composition is 90% of the endpoint change (first condition met), but the non-participants' own shape also
drifts up at 0.80 of the aggregate slope (second condition fails). The "within" part is near zero only because the two
groups move in opposite directions (R toward the evening, P toward the night).

**S3. V1: major threat.** B = +0.096 (participants take the non-participants' shape at the 2019 share) against a raw 2021
shift of shape T of −0.025 from the 2015–2019 mean: |B| is 3.8 times the shift.

**Reading, as registered.**
- The drift is **not explained** by the scheme under D1: half of high-voltage load shrank as a share and was night-heavy,
  which by itself would move the aggregate the way it moved, but the rest of the load drifted the same way on its own.
  Both forces are present; neither is shown to be the cause.
- The scheme's end is a **major threat to the 2021 industry comparison** and goes into chapter 7 beside the industry
  effect. Its **sign is known**: the period-6 rule was a floor on night consumption, and removing a binding floor at
  unchanged prices can only move load out of the night, never into it. So the no-reform 2021 shape lies between the
  placebo-based one and +0.096 above it, and the industry reform effect **is biased toward zero, not away from it**.
  The registered size of B is an upper bound (participants becoming exactly like non-participants), not an estimate.

**Post hoc, not registered.** In 2021, with the scheme gone, the whole 36-kV-and-above aggregate has shape −0.068, below
both groups' 2015–2019 mix (−0.035 to −0.053) and far below the non-participants alone (+0.05 to +0.065): the 2021 fall
happened despite a change that, if anything, pushes the other way.
