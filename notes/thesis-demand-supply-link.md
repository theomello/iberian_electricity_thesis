# How the demand results connect to the supply side (recommendation, revised 2026-11-19)

**Status:** framework proposal for the user. Nothing run. Each test below needs a pre-registration and a yes.
**User decisions (2026-11-19):** the thesis headline is the demand side; the supply results take no part in it and
enter only in the descriptive part, linked to the demand story; show that market power and price signals were left
unaffected; door D1 (the 1 June 2021 confound) is promising.

Sources read: `CLAUDE.md`, memory index, `docs/specs/2026-11-02-paper-outline.md`,
`docs/specs/2026-11-08-conduct-evidence-table.md`, `notes/rq-descriptive-price-formation.md`, the time-of-use (TOU)
specs (`2026-11-13-tou-price-effect-design.md`, `2026-11-17-industry-iv-estimation-design.md`,
`2026-11-18-industry-regulated-price-elasticity-design.md`, `2026-11-18-industry-six-summer-ri-design.md`),
`notes/scope-period-change-design.md`, `notes/tou-headline-outline.md`, `notes/handover-2026-11-18-industrial-demand.md`.

## 1. In one example

A plant faces two price changes of the same size, +€10/MWh at 20:00. One is the regulated toll for period 1, fixed
months ahead: the plant moves a shift to the night. The other is a day-ahead price spike because tomorrow's wind
forecast is low, known one day ahead: the plant does nothing. One demand curve, two notice lengths. The framework
below writes that down, prices both kinds of change from our estimates, and puts the result into the market-clearing
equation, which is where the supply side enters.

## 2. The framework (three equations)

**Notation.** Hour h of day d, consumer group i (households E0, industry 6.2–6.4). Wholesale day-ahead price
p_hd. Regulated per-period charge τ_{i,k(h)} (toll, charges and power term of period k). Exposure θ_i: share of the
group's energy bought at the hourly wholesale price (PVPC households 1; industry about 0.32 hourly-indexed, 0.49
indexed at all, CNMC IS/DE/031/24). Split the wholesale price into a part known in advance and a surprise:

  p_hd = p̄_h,m + u_hd    (p̄: expected hourly shape for the month; u: day-ahead surprise, e.g. wind)

The scheduled retail price is r̄_ih = θ_i p̄_h,m + τ_{i,k(h)}.

**(D) Demand.** Within-day allocation with day fixed effects (the log-linear form of the constant-elasticity-of-
substitution share equation the replication already uses):

  ln q_ihd = α_id + γ_ih − σ_i · ln r̄_ih − σ_i · λ_i · θ_i · u_hd / r̄_ih + e_ihd

σ_i is the response to a price change the consumer plans around; λ_i ∈ [0, 1] is the share of that response a
one-day-notice change gets. Microfoundation: production is scheduled ahead; rescheduling at one day's notice costs
extra (crews, contracts, process start-ups), so the short-notice response is a fraction λ of the planned one
(λ = 1: no rescheduling cost; λ = 0: schedule fixed at one day's notice).

**(S) Supply.** Firm j's offer at the margin (the supply side's own condition):

  b_jh − c_jh = β · q_jh^net / |RD'_jh|,  with  |RD'_jh| = |D'_h| + |X'_h| + S'_{−j,h}

where RD is j's residual demand, X the buy bids that are not final consumers (pumping, exports, retailers' price-
sensitive bids), S_{−j} rivals' offers. Final consumers enter the slope only through
D'_h = −Σ_i σ_i λ_i θ_i q_ih / r̄_ih.

**(E) Clearing.** S_h(p) = D_h(p; τ) + X_h(p), hour by hour, on the observed offer curves.

**What the reform is in this model:** a change in τ (the period calendar and the toll levels). It shifts D_h through
σ; it changes D's slope only through λθσ.

## 3. What each piece of evidence identifies

| Parameter | Evidence (already estimated) | Value |
|---|---|---|
| σ, households | reform within-day contrast, six placebo summers | elasticity −0.06 to −0.12 |
| σ, industry | regulated per-period price, six summers | −0.18 [−0.54, −0.10]; E3 (drifted null) and E5 (not proportional) fail |
| σλθ·(p/r), industry | wind-speed instrument C1 (the one instrument passing every settlement check), E3–E6, 2019–23 | +0.0001 [−0.021, +0.028]: a bounded null |
| same, second instrument | bid-curve instrument (placebo-clean, but F 17 < 20, closed by the settlement) | −0.036 [−0.080, +0.010] |
| λ, households (qualitative) | PVPC customers, who see the hourly price, respond less than the rest | consistent with λ near 0 |
| S'_{−j}, X', β | bid curves; conduct evidence table | offers near cost (β about 0; hydro 2019–21H1 +0.25) |

**The bridge parameter is λ.** Illustrative arithmetic on existing numbers, post hoc, not a test: at λ = 1, industry's
same-hour elasticity would be σ·θ·p/r ≈ −0.18 × 0.32 × 0.7 ≈ −0.04 (−0.06 with θ = 0.49).
- Wind-speed instrument: rules out below −0.021, so λ ≲ 0.5 (≲ 0.35 at θ = 0.49), point estimate λ ≈ 0.
- Bid-curve instrument: central −0.036, so λ ≈ 0.85, interval wide enough to allow anything from 0 to above 1.
- **Correction (2026-11-19):** the first version of this note said "rules out below −0.005, λ ≲ 0.1–0.15". That bound
  came from the forecast instrument, whose placebo failed; it should not have been used. The honest statement is
  weaker: the settled instrument puts λ below about one half at the central σ; the second instrument does not agree.
  T1 (`docs/specs/2026-11-19-short-notice-share-design.md`) makes it a registered test on the same consumers as σ.

## 4. Three registered tests that make the link (proposed, none run)

**T1. Short-notice share λ (the price-signal test).** Estimate λ jointly: σ from the reform (period dose), σλθ from
the instrument, with θ from CNMC and its range as a sensitivity. Same series (6.2–6.4, or E3–E6 for both), same
years where they overlap, one randomization scheme so the two intervals combine. Hypotheses fixed in advance:
λ = 1 rejected; report the upper bound. Caveat to carry: the instrument's exclusion check failed.

**T2. Market power unaffected (contains D1).** Re-clear each June–September 2021 weekday hour without the reform's
load shift (the counterfactual demand already built for the price-effect test) and recompute each firm's markup
incentive X_jh = q_jh^net / |RD'_jh| on both curves. Outcome: ΔX_jh by firm and hour block, and the implied markup
change β·ΔX at the estimated β (and at β = 1 as the Nash bound). Rule (number set at registration): the reform's ΔX is
smaller than the normal day-to-day variation of X in the placebo windows. **D1 is the hydro row:** if ΔX for
Iberdrola's and EDP's hydro is small against the gap that closed in June 2021 (+0.24 in May → −0.13 in June), the
reform cannot have ended the hydro markup, and the clawback reading strengthens.

**T3. Price signal unaffected, and no feedback.** (a) The reform's effect on the hourly price shape (−1.7 to
−2.4 €/MWh evening minus night, done) against the shape itself (the actual evening-minus-night spread in summer
2021, and its placebo-window range): a descriptive ratio. (b) Feedback: the price change re-enters demand through
σλθ·Δp/r̄; with λ from T1 it is computed and shown to be negligible. This also justifies reading the demand estimates
as equilibrium ones: with λ near 0, the supply response cannot feed back into the measured load shift.

**Order:** T1 first (it sets λ, which T3b needs); T2 independent and can run in parallel; T3a is arithmetic on
existing outputs.

## 5. The thesis, demand-led

**Headline (draft):** *Spain's June 2021 time-of-use reform shows that electricity consumers respond to prices they
can plan around, not to the hourly market signal: households about −0.1, large industry about −0.18 to the scheduled
period price, and [T1's bound] of that to a day-ahead price surprise. Passed through the wholesale market, the
reform moved prices by a couple of euros and left generators' market power unchanged.*

| Chapter | Content | Supply results used |
|---|---|---|
| 1 Introduction | | none |
| 2 Market and descriptive part | tariffs, periods, exposure; price formation: who sets the price (44% a unit with a cost, 16% the open France line, 23% buy bids), offers near cost, the gas cap's pass-through as context | **all supply results live here**, as description |
| 3 Framework | equations D, S, E | S as given |
| 4 Households | reform, six summers | none |
| 5 Industry | period price, reduced form, instrument zero, T1 | none |
| 6 Through the market | price effect (done), T2, T3 | curves, β as input |
| 7 Conclusion | | |

## 6. "Finish before writing" under the new frame

You said these can be finished. With supply as description only, they no longer carry the same weight:

| Item | Under the demand-led frame | Recommendation |
|---|---|---|
| Hydro departure firm by firm | needed to read D1 (T2) | **keep**; descriptive, from existing outputs |
| Welfare at ρ 0.87 | a gas-cap paper item; the descriptive part can quote ρ without welfare | drop, or keep for an appendix |
| Outage regression on corrected ownership | thermal conduct bound; chapter 2 can cite the step estimator (graded A) instead | drop |
| Gas-cap hour-of-day counterfactual | gas-cap paper item | drop |

Your call; nothing is run without a yes.
