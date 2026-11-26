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

## Results (run 2026-11-26, `scripts/analysis/tou_offset_stability.py`; `outputs/tables/tou_offset_stability.csv`)
**R0 passes** (summer 6.4: η_2021 −0.33676, placebo mean +0.32562, sd 0.08300).

Spring-window betas for 6.4: 2014 −0.054, 2015 −0.038, 2016 −0.085, 2017 −0.019, 2018 −0.196, 2019 −0.321; **2021 +0.029**.
Spring placebo mean −0.119 (sd 0.117).

| rule | result | verdict |
|---|---|---|
| O1 stable in 2021 | t = +1.16 (bound 2.57) | pass |
| O2 proxy valid (spring mean positive, at least +0.16) | −0.119, **negative** | **fail** |

**Reading, as registered.** O2 fails, so the check is not informative about the summer offset and **no claim is made in either
direction**: the 2021 spring beta sits inside the earlier springs (O1), but the spring offset has the opposite sign to the
summer offset (+0.33), so the spring is not a stand-in for the summer. What it shows: the 6.4 offset is a property of
the season (positive in the summer windows, negative in spring), i.e. of how this tariff's load profile lines up with the
dose pattern at that time of year, not a constant. That raises the weight on the summer window alignment and means the
stability of the summer offset in 2021 cannot be tested with another season. The 6.4 effect (−0.57 to −0.66) stays a
placebo-based estimate whose key assumption (the summer offset in 2021 equals the earlier summers') is untested.
Spring betas also fall in 2018-19 (−0.196, −0.321), again a shape drift, now visible in a second season.
