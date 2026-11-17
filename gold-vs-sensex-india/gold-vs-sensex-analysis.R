# Has gold beaten the Sensex for Indian investors? Independent R re-implementation (Truth with Data, Nov 2026).
# It rebuilds the gold and Sensex series from the monthly panel, recomputes the trailing returns, the rolling
# win rates, risk and the SIP backtest, and checks them against the CSVs written by gold-vs-sensex-analysis.py.
#
# Usage: Rscript gold-vs-sensex-analysis.R DATA_DIR      (base R only)

args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "."
p <- read.csv(file.path(dir, "india-gold-sensex-monthly-panel-1990-2026.csv"))
p$gold <- p$gold_usd_per_oz * p$usd_inr * 10 / 31.1034768
k <- which(p$date == "2014-01")
p$cpi <- ifelse(p$date >= "2014-01", p$mospi_cpi_combined_2012_100,
                p$oecd_cpi_2015_100 * p$mospi_cpi_combined_2012_100[k] / p$oecd_cpi_2015_100[k])
m <- p[p$date >= "1993-04", ]
N <- nrow(m); G <- m$gold; S <- m$oecd_india_share_price_2015_100
withdiv <- function(d) S * (1 + d)^((seq_len(N) - 1) / 12)
SD <- withdiv(0.0125)
cagr <- function(a, i, j) (a[j] / a[i])^(12 / (j - i)) - 1

cat(sprintf("Panel %s to %s: %d months; gold Rs/10g %.0f -> %.0f\n", m$date[1], m$date[N], N, G[1], G[N]))

# Trailing returns
py <- read.csv(file.path(dir, "gold-vs-sensex-trailing-returns-2026-10.csv"))
yrs <- c(1, 3, 5, 10, 15, 20, 25, 30)
mx <- 0
for (q in seq_along(yrs)) {
  i <- N - 12 * yrs[q]
  r <- 100 * c(cagr(G, i, N), cagr(S, i, N), cagr(SD, i, N))
  mx <- max(mx, abs(r - unlist(py[q, c("gold_cagr_pct", "sensex_price_cagr_pct", "sensex_with_dividends_cagr_pct")])))
  cat(sprintf("%2d yrs: gold %5.2f%%  Sensex %5.2f%%  with dividends %5.2f%%\n", yrs[q], r[1], r[2], r[3]))
}
cat(sprintf("Since Apr 1993: gold %.2f%%, Sensex %.2f%%, with dividends %.2f%%\n",
            100 * cagr(G, 1, N), 100 * cagr(S, 1, N), 100 * cagr(SD, 1, N)))
cat(sprintf("Trailing returns: max |R - Python| = %.4f pts\n", mx))

# Rolling win rates
pw <- read.csv(file.path(dir, "gold-vs-sensex-win-rates.csv"))
for (h in c(5, 10, 15, 20)) {
  n <- 12 * h; i <- 1:(N - n); j <- i + n
  w0 <- mean(G[j] / G[i] > S[j] / S[i]) * 100
  w1 <- mean(G[j] / G[i] > SD[j] / SD[i]) * 100
  ref <- pw[pw$horizon_years == h, ]
  cat(sprintf("%2d-yr windows (%d): gold won %.1f%% vs price, %.1f%% vs 1.25%% dividends (Python %.1f, %.1f)\n",
              h, length(i), w0, w1, ref$gold_won_price_only_pct, ref$gold_won_vs_dividends_1_25_pct))
}

# Risk
vol <- function(a) sd(diff(log(a))) * sqrt(12) * 100
mdd <- function(a) min(a / cummax(a) - 1) * 100
cat(sprintf("Volatility: gold %.1f%%, Sensex %.1f%%; max drawdown: gold %.1f%%, Sensex %.1f%%; correlation %.2f\n",
            vol(G), vol(S), mdd(G), mdd(S), cor(diff(log(G)), diff(log(S)))))

# SIP backtest (10-year SIPs, annual rebalancing), worst and median XIRR for 0% and 20% gold
xirr <- function(flows) {
  f <- function(r) sum(flows / (1 + ((1 + r)^(1 / 12) - 1))^(seq_along(flows) - 1))
  uniroot(f, c(-0.99, 2), tol = 1e-10)$root
}
sip <- function(w, i, n) {
  hg <- 0; hs <- 0
  for (q in i:(i + n - 1)) {
    if (q > i && (q - i) %% 12 == 0) { v <- hg * G[q] + hs * SD[q]; hg <- w * v / G[q]; hs <- (1 - w) * v / SD[q] }
    hg <- hg + w / G[q]; hs <- hs + (1 - w) / SD[q]
  }
  xirr(c(rep(-1, n), hg * G[i + n] + hs * SD[i + n]))
}
pm <- read.csv(file.path(dir, "gold-vs-sensex-mix-summary.csv"))
for (w in c(0, 0.2)) {
  x <- sapply(1:(N - 120), function(i) sip(w, i, 120)) * 100
  ref <- pm[pm$horizon_years == 10 & pm$gold_share_pct == 100 * w, ]
  cat(sprintf("10-yr SIP, %2.0f%% gold: median XIRR %.2f%%, worst %.2f%% (Python %.2f, %.2f)\n",
              100 * w, median(x), min(x), ref$sip_median_xirr_pct, ref$sip_worst_xirr_pct))
}

# Real returns to the last CPI month
j <- max(which(!is.na(m$cpi)))
inf <- cagr(m$cpi, 1, j)
cat(sprintf("Real, %s to %s: inflation %.2f%%, gold %.2f%%, Sensex %.2f%%, with dividends %.2f%%\n", m$date[1], m$date[j],
            100 * inf, 100 * ((1 + cagr(G, 1, j)) / (1 + inf) - 1), 100 * ((1 + cagr(S, 1, j)) / (1 + inf) - 1),
            100 * ((1 + cagr(SD, 1, j)) / (1 + inf) - 1)))
