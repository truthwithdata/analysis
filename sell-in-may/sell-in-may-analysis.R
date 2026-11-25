# Does "Sell in May and go away" beat buy-and-hold? Independent R re-implementation (Truth with Data, Nov 2026).
# Rebuilds monthly returns from the panel, recomputes the summer/winter statistics, the month averages and
# the switching backtest (with costs and tax), and checks them against the files written by
# sell-in-may-analysis.py. Bootstrap intervals use R's own random numbers, so they differ slightly.
#
# Usage: Rscript sell-in-may-analysis.R DATA_DIR      (base R only)

args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "."
p <- read.csv(file.path(dir, "us-stocks-cash-monthly-panel-1871-2026.csv"))
n <- nrow(p)
P <- p$sp_composite_price; Dv <- p$dividend_12m; C <- p$cpi; R <- p$cash_rate_pct
m <- data.frame(date = p$date[-1], year = as.integer(substr(p$date[-1], 1, 4)), month = as.integer(substr(p$date[-1], 6, 7)))
m$tr <- (P[-1] + Dv[-1] / 12) / P[-n] - 1
m$cash <- R[-n] / 1200
m$infl <- C[-1] / C[-n] - 1
m$real <- (1 + m$tr) / (1 + m$infl) - 1
N <- nrow(m)
cat(sprintf("Monthly returns %s to %s: %d months\n", m$date[1], m$date[N], N))

key <- m$year * 12 + m$month - 1
half <- function(start, col) { s <- key >= start & key <= start + 5; if (sum(s) == 6) prod(1 + m[[col]][s]) - 1 else NA }
yrs <- 1871:2025
summer <- sapply(yrs, function(y) half(y * 12 + 4, "real"))
winter <- sapply(yrs, function(y) half(y * 12 + 10, "real"))     # Nov y .. Apr y+1, the winter after summer y
s_nom <- sapply(yrs, function(y) half(y * 12 + 4, "tr"))
s_cash <- sapply(yrs, function(y) half(y * 12 + 4, "cash"))
ok <- !is.na(winter)
gap <- winter[ok] - summer[ok]
excess <- (1 + s_nom) / (1 + s_cash) - 1
set.seed(2026)
bci <- function(x) quantile(replicate(10000, mean(sample(x, replace = TRUE))), c(0.025, 0.975)) * 100
cat(sprintf("Summers %d-%d: mean real %.2f%%, median %.2f%%; winters: mean %.2f%%, median %.2f%%\n",
            min(yrs), max(yrs), 100 * mean(summer), 100 * median(summer), 100 * mean(winter[ok]), 100 * median(winter[ok])))
ci <- bci(gap)
cat(sprintf("Gap winter - summer: %.2f pts [%.2f, %.2f]; winter won %.1f%% of %d years; t = %.2f\n",
            100 * mean(gap), ci[1], ci[2], 100 * mean(gap > 0), length(gap), mean(gap) / (sd(gap) / sqrt(length(gap)))))
cat(sprintf("Summer stocks beat cash in %.1f%% of summers; mean excess %.2f%%\n", 100 * mean(excess > 0), 100 * mean(excess)))

py <- read.csv(file.path(dir, "sell-in-may-half-years-1871-2026.csv"))
py <- py[py$year %in% yrs, ]
cat(sprintf("Max |R - Python| summer real return: %.2e\n", max(abs(py$summer_stock_real - summer))))

# Month averages
pm <- read.csv(file.path(dir, "sell-in-may-month-averages.csv"))
mm <- tapply(m$real, m$month, mean) * 100
cat(sprintf("Month means (real %%): %s\n", paste(sprintf("%s %.2f", month.abb, mm), collapse = ", ")))
cat(sprintf("Max |R - Python| month mean: %.4f pts\n", max(abs(mm - pm$mean_real_pct))))

# Backtest
sim <- function(i0, i1, inm, cost = 0, tax = 0) {
  v <- 1; basis <- 1; carry <- 0; bh <- 1
  inv <- m$month[i0] %in% inm
  for (k in i0:i1) {
    want <- m$month[k] %in% inm
    if (want != inv) {
      if (inv) { g <- v - basis + carry; if (g > 0) { v <- v - tax * g; carry <- 0 } else carry <- g; v <- v * (1 - cost) }
      else { v <- v * (1 - cost); basis <- v }
      inv <- want
    }
    v <- if (inv) v * (1 + m$tr[k]) else v * (1 + m$cash[k] * (1 - tax))
    bh <- bh * (1 + m$tr[k])
  }
  if (inv) v <- v - tax * max(0, v - basis + carry)
  bh <- bh - tax * max(0, bh - 1)
  infl <- prod(1 + m$infl[i0:i1]); y <- (i1 - i0 + 1) / 12
  c(switch = 100 * ((v / infl)^(1 / y) - 1), hold = 100 * ((bh / infl)^(1 / y) - 1))
}
ps <- read.csv(file.path(dir, "sell-in-may-backtest-scenarios.csv"))
for (q in seq_len(nrow(ps))) {
  r <- sim(1, N, c(11, 12, 1, 2, 3, 4), ps$cost_per_switch_pct[q] / 100, ps$tax_rate_pct[q] / 100)
  cat(sprintf("cost %.2f%% tax %2.0f%%: real CAGR switch %.2f%% vs hold %.2f%% (Python %.2f, %.2f)\n",
              ps$cost_per_switch_pct[q], ps$tax_rate_pct[q], r[1], r[2], ps$strategy_real_cagr_pct[q], ps$buyhold_real_cagr_pct[q]))
}
for (era in list(c(1871, 2001), c(2002, 2025))) {
  s <- yrs >= era[1] & yrs <= era[2] & ok
  i0 <- which(m$date == sprintf("%d-05", era[1])); i1 <- min(N, which(m$date == sprintf("%d-04", era[2] + 1)))
  r <- sim(i0, i1, c(11, 12, 1, 2, 3, 4))
  cat(sprintf("Summers %d-%d: gap %.2f pts, winter won %.0f%%; switch minus hold %.2f pts a year\n",
              era[1], era[2], 100 * mean(winter[s] - summer[s]), 100 * mean(winter[s] > summer[s]), r[1] - r[2]))
}
