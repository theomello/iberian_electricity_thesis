# Generalized random forest for heterogeneity by conditions (docs/specs/2026-11-17-causal-forest-design.md, rules F0-F4).
#   Rscript scripts/analysis/tou_forest.R      (after scripts/analysis/tou_forest_prep.py)
# Real forest (tuned, 4000 trees, clusters = week) on data/cache_tou/forest/real.csv; placebo forests (tuned parameters of the real one, 1000 trees) on the season-matched windows of placebo.csv.
suppressMessages(library(grf))
root <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), "..", ".."))
fd <- file.path(root, "data", "cache_tou", "forest")
out <- file.path(root, "outputs", "tables")
real <- read.csv(file.path(fd, "real.csv"))
pl <- read.csv(file.path(fd, "placebo.csv"))
covs <- c("hour","wkd","month","doy","tmean","tmin","tmax","temp_es","t3","hdh","cdh","heatwave","price","price_prev","f_wind","f_solar","f_demand","dose","period","days_since","bridge")
noprice <- setdiff(covs, c("price", "price_prev"))
prm <- function(f) { p <- f$tuning.output$params; if (is.null(p)) list() else as.list(p) }
fit <- function(d, cv, seed, trees, params = NULL, tune = "none") {
  X <- as.matrix(d[, cv]); cl <- as.integer(factor(d$week))
  args <- c(list(X = X, Y = d$y_dm, W = d$w_dm, clusters = cl, num.trees = trees, seed = seed, tune.parameters = tune), params)
  do.call(causal_forest, args)
}
set.seed(20261117)
cat("real forest: n =", nrow(real), "window rows =", sum(real$in_window), "\n")
f1 <- fit(real, covs, 1, 4000, tune = "all")
P <- prm(f1)
cat("tuned parameters:", paste(names(P), unlist(P), sep = "=", collapse = ", "), "\n")
iw <- real$in_window == 1
ate_all <- average_treatment_effect(f1, target.sample = "all")
ate_win <- average_treatment_effect(f1, subset = iw)
cal <- test_calibration(f1)
tau1 <- predict(f1)$predictions
sd_real <- sd(tau1[iw])
imp <- variable_importance(f1); names(imp) <- covs
cat(sprintf("ATE all rows %.4f (se %.4f); window days %.4f (se %.4f)\n", ate_all[1], ate_all[2], ate_win[1], ate_win[2]))
print(round(cal, 4))
cat(sprintf("sd of OOB tau on window days: %.4f\n", sd_real))
print(round(sort(imp, decreasing = TRUE)[1:10], 3))

# stability
f2 <- fit(real, covs, 2, 2000, params = P)
f3 <- fit(real, noprice, 3, 2000, params = P)
t2 <- predict(f2)$predictions; t3 <- predict(f3)$predictions
rho2 <- cor(tau1[iw], t2[iw], method = "spearman"); rho3 <- cor(tau1[iw], t3[iw], method = "spearman")
i2 <- variable_importance(f2); names(i2) <- covs
i3 <- variable_importance(f3); names(i3) <- noprice
top3 <- names(sort(imp[noprice], decreasing = TRUE))[1:3]
in5 <- function(i) all(top3 %in% names(sort(i, decreasing = TRUE))[1:5])
cat(sprintf("stability: rank corr with seed-2 forest %.3f, with no-price forest %.3f; top-3 (non-price) %s in top-5 of seed-2: %s, of no-price: %s\n", rho2, rho3, paste(top3, collapse = ","), in5(i2), in5(i3)))

# partial dependence on window days (deciles of the top covariates)
w <- real[iw, ]; tw <- tau1[iw]
pdp <- do.call(rbind, lapply(names(sort(imp, decreasing = TRUE))[1:8], function(v) {
  x <- w[[v]]; if (length(unique(x)) < 3) return(NULL)
  b <- cut(x, unique(quantile(x, seq(0, 1, 0.1), na.rm = TRUE)), include.lowest = TRUE)
  data.frame(var = v, bin = as.integer(b), x_mean = tapply(x, b, mean), tau = tapply(tw, b, mean))
}))
mono <- sapply(split(pdp, pdp$var), function(d) abs(cor(d$x_mean, d$tau, method = "spearman")))
print(round(mono, 2))

# best linear projection
A <- w[, c("tmean", "hour", "wkd", "price", "days_since")]
blp <- tryCatch(best_linear_projection(f1, A = real[, c("tmean", "hour", "wkd", "price", "days_since")], subset = iw), error = function(e) NULL)
if (!is.null(blp)) print(round(blp, 4))

# placebo forests
ks <- sort(unique(pl$k)); sds <- numeric(0); ates <- numeric(0)
for (k in ks) {
  d <- pl[pl$k == k, ]
  f <- fit(d, covs, 100 + k, 1000, params = P)
  tp <- predict(f)$predictions
  sds <- c(sds, sd(tp[d$in_window == 1])); ates <- c(ates, average_treatment_effect(f, subset = d$in_window == 1)[1])
  cat(sprintf("  placebo k=%d  sd %.4f  ATE %.4f\n", k, tail(sds, 1), tail(ates, 1)))
}
q95 <- quantile(sds, 0.95)
write.csv(data.frame(k = ks, sd_tau = sds, ate = ates), file.path(out, "tou_forest_placebo.csv"), row.names = FALSE)
write.csv(data.frame(var = names(imp), importance = imp, importance_seed2 = i2[names(imp)]), file.path(out, "tou_forest_importance.csv"), row.names = FALSE)
write.csv(pdp, file.path(out, "tou_forest_pdp.csv"), row.names = FALSE)
if (!is.null(blp)) write.csv(as.data.frame(unclass(blp)), file.path(out, "tou_forest_blp.csv"))
share_w <- mean(iw)
t_ate <- ate_all[1] / ate_all[2]
cat("\n")
cat(sprintf("F0 ATE %.4f (t %.2f) negative with t <= -2; window rows %.1f%% >= 10%%: %s\n", ate_all[1], t_ate, 100 * share_w, ate_all[1] < 0 && t_ate <= -2 && share_w >= 0.10))
cat(sprintf("F1 calibration differential coefficient %.3f, p %.4f: %s\n", cal["differential.forest.prediction", 1], cal["differential.forest.prediction", 4], cal["differential.forest.prediction", 1] > 0 && cal["differential.forest.prediction", 4] <= 0.05))
cat(sprintf("F2 real sd %.4f vs placebo 95th percentile %.4f (placebo median %.4f, max %.4f; %d windows): %s\n", sd_real, q95, median(sds), max(sds), length(sds), sd_real > q95))
cat(sprintf("F3 stable: rho %.3f / %.3f >= 0.7 and top-3 in top-5: %s\n", rho2, rho3, rho2 >= 0.7 && rho3 >= 0.7 && in5(i2) && in5(i3)))
write.csv(data.frame(item = c("ate_all", "ate_all_se", "ate_window", "ate_window_se", "calib_coef", "calib_p", "sd_real", "sd_placebo_q95", "sd_placebo_median", "rho_seed2", "rho_noprice"),
                     value = c(ate_all[1], ate_all[2], ate_win[1], ate_win[2], cal["differential.forest.prediction", 1], cal["differential.forest.prediction", 4], sd_real, q95, median(sds), rho2, rho3)),
          file.path(out, "tou_forest_summary.csv"), row.names = FALSE)
