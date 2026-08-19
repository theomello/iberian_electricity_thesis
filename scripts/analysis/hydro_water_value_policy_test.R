#!/usr/bin/env Rscript
# The actual RQ test: does hydro's implied cost move beyond what fundamentals
# predict, specifically during the 2021 levy and the 2022 gas cap?
#
#   Rscript scripts/analysis/hydro_water_value_policy_test.R
#
# Everything up to this point (hydro_water_value_structural.R/.py, the two
# outlier fixes, the netted slope, the cluster bootstrap) built and validated
# the TOOL -- a model that predicts a cascade's opportunity cost from
# fundamentals alone (forward price, own reservoir level). This script is
# the first use of that tool for the actual question: conditional on
# fundamentals, does the model's residual shift during the two policy
# windows, in the direction each policy would predict?
#
# THE OVERLAP PROBLEM, HANDLED THE WAY THE NOTES ALREADY SAY TO
#
# RDL 17/2021 (the levy) runs 16 Sep 2021 -> 31 Dec 2023. RDL 10/2022 (the
# gas cap) runs 15 Jun 2022 -> 31 Dec 2023. They overlap for 18.5 months --
# `candidate-natural-experiments.md` is explicit that a single "post" dummy
# spanning both policies conflates them. Its own resolution: the 15 Jun 2022
# cutoff is clean *within the levy-active period*, because the levy is
# already in force on both sides of it and differences out. That gives two
# separate, non-contaminated tests instead of one confounded one:
#
#   GAS CAP TEST   -- sample restricted to 16 Sep 2021 - 31 Dec 2023 (levy
#                     active throughout), dummy = 1 from 15 Jun 2022 on.
#   LEVY TEST      -- sample restricted to dates before 15 Jun 2022 (before
#                     the gas cap ever starts), dummy = 1 from 16 Sep 2021.
#
# Both regressions add the policy dummy to the already-validated model:
#
#   c_it = b0 + b1*pf_t + b2*Vol_it + b3*Post_t + unit FE + e_it
#
# b3 is the test. A cost estimate that's already conditioned on the forward
# price and the cascade's own reservoir level has no further legitimate
# reason to move at a policy date -- if it does, that's conduct, not
# fundamentals. Same cluster-robust SE and cluster bootstrap discipline as
# the base model, since the same few-cluster problem applies here too.

suppressPackageStartupMessages({
  library(arrow); library(dplyr); library(sandwich); library(lmtest); library(boot)
})

ROOT <- getwd()
if (!file.exists(file.path(ROOT, "CLAUDE.md"))) {
  for (i in 1:6) {
    ROOT <- dirname(ROOT)
    if (file.exists(file.path(ROOT, "CLAUDE.md"))) break
  }
}
PANEL <- file.path(ROOT, "outputs", "tables", "hydro_water_value_structural_panel_R.parquet")
if (!file.exists(PANEL)) stop(sprintf("%s not found -- run hydro_water_value_structural.R first.", PANEL))

LEVY_START   <- as.Date("2021-09-16")
LEVY_END     <- as.Date("2023-12-31")
GASCAP_START <- as.Date("2022-06-15")
GASCAP_END   <- as.Date("2023-12-31")
N_BOOT <- 2000

d <- read_parquet(PANEL) |> mutate(date = as.Date(date))
cat(sprintf("full panel: %d rows, %d units, %s to %s\n\n",
            nrow(d), n_distinct(d$marginal_unit), format(min(d$date)), format(max(d$date))))

report_cluster <- function(fit, cluster, label, vars) {
  ct <- coeftest(fit, vcov = vcovCL(fit, cluster = cluster, type = "HC1"))
  cat(sprintf("\n%s\n", label))
  print(ct[vars, , drop = FALSE])
}

cluster_boot <- function(data, formula, coef_name, n_boot = N_BOOT) {
  data$marginal_unit <- factor(data$marginal_unit)
  units_list <- levels(data$marginal_unit)
  by_unit <- split(data, data$marginal_unit)
  stat <- function(data_ignored, idx) {
    resampled <- bind_rows(by_unit[units_list[idx]])
    resampled$marginal_unit <- factor(resampled$marginal_unit)
    fit <- tryCatch(lm(formula, data = resampled), error = function(e) NULL)
    if (is.null(fit) || !(coef_name %in% names(coef(fit)))) return(NA_real_)
    coef(fit)[coef_name]
  }
  set.seed(20260819)
  b <- boot(seq_along(units_list), stat, R = n_boot)
  ok <- !is.na(b$t[, 1])
  ci <- quantile(b$t[ok, 1], c(0.025, 0.975))
  cat(sprintf("  cluster bootstrap (%d/%d valid): point est %8.4f  boot SE %7.4f  95%% CI [%8.4f, %8.4f]\n",
              sum(ok), n_boot, b$t0, sd(b$t[ok, 1]), ci[1], ci[2]))
}

# ============================================================================
# GAS CAP TEST -- restricted to the levy-active window, so the levy itself
# (constant = 1 throughout this sample) differences out and Post_gascap
# isolates the cap's own increment.
# ============================================================================
cat(strrep("=", 72), "\n")
cat("GAS CAP TEST\n")
cat(sprintf("sample: %s to %s (levy active throughout -- differences out)\n",
            LEVY_START, LEVY_END))
cat(strrep("=", 72), "\n")

d_cap <- d |> filter(date >= LEVY_START, date <= LEVY_END) |>
  mutate(post_gascap = as.integer(date >= GASCAP_START),
         marginal_unit = factor(marginal_unit))

cat(sprintf("\nn = %d marginal-hydro periods, %d units, %d pre-cap, %d post-cap\n",
            nrow(d_cap), n_distinct(d_cap$marginal_unit),
            sum(d_cap$post_gascap == 0), sum(d_cap$post_gascap == 1)))

if (nrow(d_cap) > 30 && n_distinct(d_cap$marginal_unit) >= 3) {
  m_cap <- lm(c ~ pf + vol + post_gascap + marginal_unit, data = d_cap)
  report_cluster(m_cap, d_cap$marginal_unit,
                  "c_it = b0 + b1*pf + b2*vol + b3*post_gascap + unit FE",
                  c("(Intercept)", "pf", "vol", "post_gascap"))
  cat("\n")
  cluster_boot(d_cap, c ~ pf + vol + post_gascap + marginal_unit, "post_gascap")
} else {
  cat("\nTOO FEW OBSERVATIONS/CLUSTERS TO ESTIMATE -- reporting the gap honestly, not forcing a number.\n")
}

# ============================================================================
# LEVY TEST -- restricted to dates before the gas cap ever starts, so the
# levy's own window (16 Sep 2021 - 14 Jun 2022) is compared against a clean
# pre-period with neither policy in force.
# ============================================================================
cat(sprintf("\n%s\nLEVY TEST\n", strrep("=", 72)))
cat(sprintf("sample: all dates before %s (gas cap not yet in force)\n", GASCAP_START))
cat(strrep("=", 72), "\n")

d_levy <- d |> filter(date < GASCAP_START) |>
  mutate(post_levy = as.integer(date >= LEVY_START),
         marginal_unit = factor(marginal_unit))

cat(sprintf("\nn = %d marginal-hydro periods, %d units, %d pre-levy, %d post-levy\n",
            nrow(d_levy), n_distinct(d_levy$marginal_unit),
            sum(d_levy$post_levy == 0), sum(d_levy$post_levy == 1)))

if (nrow(d_levy) > 30 && n_distinct(d_levy$marginal_unit) >= 3) {
  m_levy <- lm(c ~ pf + vol + post_levy + marginal_unit, data = d_levy)
  report_cluster(m_levy, d_levy$marginal_unit,
                  "c_it = b0 + b1*pf + b2*vol + b3*post_levy + unit FE",
                  c("(Intercept)", "pf", "vol", "post_levy"))
  cat("\n")
  cluster_boot(d_levy, c ~ pf + vol + post_levy + marginal_unit, "post_levy")
} else {
  cat("\nTOO FEW OBSERVATIONS/CLUSTERS TO ESTIMATE -- reporting the gap honestly, not forcing a number.\n")
}

cat("\n", strrep("=", 72), "\n", sep = "")
cat("READ: post_gascap/post_levy > 0 means hydro's implied cost rose beyond\n",
    "what the forward price and its own reservoir level predict, during that\n",
    "policy window -- evidence of conduct, not just fundamentals. A null\n",
    "result here is also informative: it would say hydro priced water the\n",
    "same way it always does once you control for what water is actually\n",
    "worth, i.e. no detectable strategic response on this test.\n", sep = "")
