# Triple-difference papers, read against design K (2026-11-08)

Five papers the user added on 2026-11-08 (`papers/`, converted to `papers/md/`). Design K: Iberian gas plants,
plant × week, a continuous dose g_iw, week fixed effects; Italy as the third difference (`rq-crisis-quantity.md` §K).

| paper | what it says | what it means for design K |
|---|---|---|
| Olden & Møen (2022), *Econometrics Journal* (`utac010.pdf`) | A triple difference needs **one** parallel-trend assumption, not two: the bias in the treated country's DiD must equal the bias in the control country's. Equivalent to a DiD on a ratio. Few clusters: DiD and DDD over-reject alike; DDD has more power. Functional form is identifying (levels vs logs). | Our assumption: the gap between high- and low-dose plants would have moved the same way in Iberia and Italy without the subsidy. Step 3 suggests it fails as stated: before the cap Italy's gap moves with gas at −0.18 per €100, Iberia's at −0.04. With 10 Iberian firms, over-rejection applies to us. |
| Strezhnev (2023), arXiv 2307.02735 | Decomposes the triple-difference fixed-effects regression into 2×2×2 pieces. With staggered or varying treatment, some pieces use treated cells as controls, which needs strong homogeneity assumptions. Recommends imputation using only "clean" untreated cells. | Our dose varies week by week after the cap, so the regression also compares high-dose with low-dose post-cap weeks (treated against treated). Imputation is cheap here: fit unit and week effects on untreated cells only (pre-cap, S = 0 weeks, all of Italy), then regress the gap on g. |
| Zhuang (2024), arXiv 2409.12353 | Turns a triple difference into a DiD by subtracting the non-target group's mean each period within each state, then applies synthetic control or synthetic DiD to that. An unrefereed note; warns that a full synthetic DDD is over-parameterised. | The least useful of the five: with two countries there is no pool of control "states" to weight. Could be applied at plant level (synthetic weights over Italian plants), but this is close to what B3 already did and failed. |
| Leventer (2025), arXiv 2502.16126 | When covariate distributions differ across the two groups, the usual practice (a DiD with controls in each group, then the difference) is biased. Fix: re-weight the control group's DiD to the treated group's covariate distribution. Doubly robust estimator; R package `tdid`. | Directly relevant. The bias we found depends on near-cost mass z (c · gas · z), and z differs: Iberia 0.29, Italy 0.18. So the triple difference must re-weight Italian plants to Iberia's z (and efficiency) distribution. This supports the re-weighting step already proposed. |
| Caron (2026), arXiv 2502.19620 | When effects differ across units and covariates correlate with both effect size and group, the difference across subgroups is not the causal effect of group membership. Proposes a "controlled" difference, holding covariates fixed (IPW, regression adjustment, doubly robust). | Applies to the **headline**, not only the check: ρ is read off a slope across plants with different doses. If pass-through differs by plant and that correlates with dose (efficiency, owner, Portugal vs Spain), the slope is a weighted mix, not the average ρ. Check: ρ by firm or efficiency group, and the slope with dose interacted with those covariates. |

## What follows for the next step (not yet fixed as a rule)
1. Re-weight Italy to Iberia's z and efficiency (Leventer) before differencing; keep the gas term per country.
2. Imputation version of the main estimate (Strezhnev; Borusyak, Jaravel & Spiess 2024).
3. Effect heterogeneity (Caron): ρ by efficiency tercile and by firm; report the weights the regression puts on each.
4. Inference with 10 clusters (Olden & Møen §7): add a wild cluster bootstrap or randomisation inference beside the
   firm block bootstrap.

## Papers worth adding (not in `papers/` yet)
- Ortiz-Villavicencio & Sant'Anna (2025), *Better Understanding Triple Differences Estimators* (arXiv 2505.09942): the
  reference treatment of DDD with covariates and staggering; `triplediff` package.
- Callaway, Goodman-Bacon & Sant'Anna (2024/2026), *Difference-in-Differences with a Continuous Treatment*: our
  headline is a continuous-dose regression with unit and week effects; this says what it identifies.
- de Chaisemartin & D'Haultfœuille (2020, AER), *Two-Way Fixed Effects Estimators with Heterogeneous Treatment
  Effects*, and de Chaisemartin, D'Haultfœuille, Pasquier & Vazquez-Bare, *DiD for continuous treatments and
  instruments with stayers*.
- Borusyak, Jaravel & Spiess (2024, REStud), *Revisiting Event-Study Designs*: the imputation estimator.
- Rambachan & Roth (2023, REStud), *A More Credible Approach to Parallel Trends*; Roth (2022, AER: Insights),
  *Pretest with Caution*: bounds when placebo tests have low power, which is our situation with the gas term.
- MacKinnon, Nielsen & Webb (2023, J. Econometrics), *Cluster-robust inference: A guide to empirical practice*;
  Cameron, Gelbach & Miller (2008, REStat): inference with about 10 clusters.
- Hainmueller (2012, Political Analysis), *Entropy Balancing*: the re-weighting step.
- Roth, Sant'Anna, Bilinski & Poe (2023, J. Econometrics), *What's Trending in Difference-in-Differences?*: overview.
