# Is 6.4's placebo offset stable in 2021? A spring-window check (proposal, registered on commit)

**Status: registered when this file is committed; the run follows.** Cached errors only. Follows
`2026-11-26-tariff-drift-design.md`: tariff 6.4's placebo betas are +0.36, +0.42, +0.35, +0.25, +0.20, +0.37 (mean +0.33,
sd 0.083) and its 2021 effect (−0.57 to −0.66) is measured by subtracting that offset from a raw −0.337.

**What is not blind.** The 6.4 summer placebos and the 2021 summer estimate are known. Nothing computed for any spring window.

## The question and why it cannot be answered directly
The offset in summer 2021 is the beta the estimator would give with no reform, which is not observable. What is observable: the
same estimator on a window just before the reform in 2021, when the old calendar was in force. If the estimator's offset had
shifted in 2021 (a year-specific shift), it would show up there too.

## Design
- **Spring window of year Y** (Y = 2014-2019 and 2021): 107 days starting 112 days (16 weeks, same weekday) before the
  aligned summer window start. For 2021 that is 2021-02-09 → 2021-05-26, all before the reform (1 June).
- **Estimator:** the baseline for 6.4 (`tou_drift_location.eta_variant`, full regulated-price dose laid on the window,
  series-specific fixed effects), errors from the cached leave-one-year-out models for placebo years and the model trained on
  2014-2020 for 2021, exactly as the summer test.
- **Statistic:** the 2021 spring beta against the six spring placebo betas: prediction t-test with 5 degrees of freedom,
  t = (b_2021 − mean) / (sd·sqrt(1 + 1/6)).

## Rules, set before the run
- **R0 Gate.** The same code reproduces the 6.4 summer numbers: η_2021 −0.33676, placebo mean +0.32562, sd 0.08300 (to 0.0015).
- **O1 Stable in 2021.** |t| ≤ 2.57 (the 95% prediction bound): the 2021 spring offset is inside the range of earlier years.
- **O2 Proxy valid.** The spring placebo mean has the sign of the summer offset (positive) and is at least half of it
  (≥ +0.16). If O2 fails, the spring windows are not informative about the summer offset and O1 is reported as such.
- **O3 Not a COVID or winter artefact.** The check for 2021 uses only days after 2021-02-09; days in 2021's state of alarm
  (to 2021-05-09) are kept (the six-summer test excluded only March-June 2020).

## What each outcome means
O1 and O2 pass: nothing in 2021 shifted the offset before the reform; subtracting the stable offset for 6.4 is supported, and
−0.57 to −0.66 stands as a placebo-based estimate. O1 fails (O2 passes): the offset had already moved in 2021 before the
reform; the 6.4 effect is not trustworthy and is reported as a raw −0.34 with the offset unresolved. O2 fails: the check is
not informative; no claim either way.

## Threats
One window per year and one year of interest; the spring is a different season with a different load shape, so passing O1 shows
no year-specific shift in the estimator, not that summer 2021 is free of one; 2021 spring had pandemic restrictions.
