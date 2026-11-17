# G5 of docs/specs/2026-11-17-goiener-household-design.md: regression forest of each household's window response on pre-period covariates, calibrated against the placebo windows.
#   Rscript scripts/analysis/goiener_g5_forest.R
# Inputs from goiener_g5_prep.py. Rules (registered): (a) spread = sd of out-of-bag predictions of the real forest above the 95th percentile of the 26 placebo-window spreads (same forest settings, same seed);
# (b) grf::test_calibration differential forest prediction coefficient > 0 with p <= 0.05; (c) second seed: rank correlation of the OOB predictions >= 0.7. All three must hold, else no household-heterogeneity claim.
# No response is estimated or printed. Forest: 2000 trees, honest, grf defaults, seeds 20261117 and 20261118. Writes outputs/tables/goiener_g5.csv (+ variable importance only if all rules pass).
suppressMessages({library(grf); library(arrow)})
root <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), "..", ".."))
real <- as.data.frame(read_parquet(file.path(root, "data/goiener/daily/g5_real.parquet")))
pl <- as.data.frame(read_parquet(file.path(root, "data/goiener/daily/g5_placebo.parquet")))
covs <- c("p1", "p2", "years_data", "mean_kwh", "share_peak", "share_mid", "share_night", "temp_slope", "missing_pct", "province", "cnae2")
fit <- function(d, seed) regression_forest(as.matrix(d[, covs]), d$y, num.trees = 2000, seed = seed, num.threads = 4)
oob <- function(f) as.numeric(predict(f)$predictions)
f1 <- fit(real, 20261117); p1 <- oob(f1); s_real <- sd(p1)
cal <- test_calibration(f1)
f2 <- fit(real, 20261118); p2 <- oob(f2)
rk <- cor(p1, p2, method = "spearman")
spreads <- sapply(sort(unique(pl$window)), function(k) { d <- pl[pl$window == k, ]; sd(oob(fit(d, 20261117))) })
q95 <- as.numeric(quantile(spreads, 0.95))
rank_p <- (1 + sum(spreads >= s_real)) / (1 + length(spreads))
a <- s_real > q95
b <- cal["differential.forest.prediction", "Estimate"] > 0 && cal["differential.forest.prediction", "Pr(>t)"] <= 0.05
cc <- rk >= 0.7
cat(sprintf("households %d; real OOB spread %.4f; placebo spreads median %.4f, q95 %.4f, max %.4f (%d windows); rank p %.3f\n", nrow(real), s_real, median(spreads), q95, max(spreads), length(spreads), rank_p))
cat(sprintf("calibration: mean.forest.prediction %.3f (p %.3f), differential %.3f (one-sided p %.3f)\n", cal["mean.forest.prediction", "Estimate"], cal["mean.forest.prediction", "Pr(>t)"], cal["differential.forest.prediction", "Estimate"], cal["differential.forest.prediction", "Pr(>t)"]))
cat(sprintf("second seed rank correlation %.3f\n", rk))
cat(sprintf("G5 (a) spread above placebo q95: %s; (b) differential > 0, p <= 0.05: %s; (c) rank corr >= 0.7: %s -> %s\n", a, b, cc, if (a && b && cc) "PASS" else "FAIL, no household-heterogeneity claim"))
out <- data.frame(real_spread = s_real, placebo_q95 = q95, placebo_median = median(spreads), placebo_max = max(spreads), rank_p = rank_p, calib_diff = cal["differential.forest.prediction", "Estimate"], calib_p = cal["differential.forest.prediction", "Pr(>t)"], seed_rank_corr = rk, a = a, b = b, c = cc, pass = a && b && cc)
write.csv(out, file.path(root, "outputs/tables/goiener_g5.csv"), row.names = FALSE)
if (a && b && cc) { vi <- data.frame(covariate = covs, importance = variable_importance(f1)[, 1]); write.csv(vi[order(-vi$importance), ], file.path(root, "outputs/tables/goiener_g5_importance.csv"), row.names = FALSE) }
cat("DONE\n")
