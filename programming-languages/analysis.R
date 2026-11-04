# Independent R check of analysis.py (base R only).
# Recomputes the four WORLD signals, the momentum ranking and the backtest slope,
# then compares them with data/processed/momentum-by-language-and-country.csv.
# Run: Rscript analysis.R
setwd(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))))
raw <- "data/inputs"
L <- c("Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "Kotlin",
       "Swift", "PHP", "Ruby", "R", "SQL", "Dart", "Scala", "Julia")
lr <- function(a, b) ifelse(a > 0 & b > 0, log(a / b), NA)

# Usage: GitHub share of programming-language pushers, Q3 2021-Q2 2022 vs Q3 2025-Q2 2026
gh <- read.csv(file.path(raw, "github-innovation-graph-pushers.csv"), check.names = FALSE)
gh <- gh[gh$geo == "WORLD", ]
win <- function(y0) { m <- (gh$year == y0 & gh$quarter >= 3) | (gh$year == y0 + 1 & gh$quarter <= 2)
  sapply(setdiff(L, "SQL"), function(x) sum(gh[m, x]) / sum(gh[m, "ALL_PROGRAMMING"])) }
usage <- setNames(rep(NA, length(L)), L); u <- lr(win(2025), win(2021)); usage[names(u)] <- u

# Learning: share of "want to work with" ticks, 2022 vs 2026 (0.0 = not offered)
sv <- read.csv(file.path(raw, "so-survey-language-shares.csv"), check.names = FALSE)
sv <- sv[sv$geo == "ALL", ]
wrel <- function(y) { w <- unlist(sv[sv$year == y & sv$metric == "w", L]); uu <- unlist(sv[sv$year == y & sv$metric == "u", L])
  w[uu == 0] <- NA; w / sum(w, na.rm = TRUE) }
learning <- log(wrel(2026) / wrel(2022))

# Hiring: share of language mentions in HN "Who is hiring?", Nov 2021-Oct 2022 vs Nov 2025-Oct 2026
hn <- read.csv(file.path(raw, "hn-whos-hiring-language-mentions.csv"), check.names = FALSE)
hcore <- intersect(L, names(hn))
hw <- function(a, b) colSums(hn[hn$month >= a & hn$month <= b, hcore])
hb <- hw("2021-11", "2022-10"); ha <- hw("2025-11", "2026-10")
hiring <- setNames(rep(NA, length(L)), L)
ok <- pmin(hb, ha) >= 20
hiring[hcore[ok]] <- log((ha / sum(ha)) / (hb / sum(hb)))[ok]

# Interest: Google Trends share among the 17 languages, mean of GB and US log-ratios
tr_geo <- function(g) {
  parts <- lapply(1:4, function(i) read.csv(file.path(raw, sprintf("google-trends/%s-batch%d.csv", g, i)), check.names = FALSE))
  df <- Reduce(function(a, b) merge(a, b[, setdiff(names(b), "Java")], by = "Time"), parts)
  df$m <- substr(df$Time, 1, 7)
  sb <- colSums(df[df$m >= "2021-11" & df$m <= "2022-10", L]); sa <- colSums(df[df$m >= "2025-11" & df$m <= "2026-10", L])
  out <- log((sa / sum(sa)) / (sb / sum(sb))); out[sb < 24] <- NA; out }
ti <- rbind(tr_geo("GB"), tr_geo("US"))
interest <- apply(ti, 2, function(x) if (all(is.na(x))) NA else mean(x, na.rm = TRUE))

S <- cbind(usage = usage, learning = learning[L], hiring = hiring, interest = interest[L])
Z <- scale(S)
n <- rowSums(!is.na(S))
momentum <- ifelse(n >= 3, rowMeans(Z, na.rm = TRUE), NA)
res <- data.frame(language = L, S, momentum = momentum)
res <- res[order(-res$momentum), ]
print(round(res[, -1], 3))

py <- read.csv("data/processed/momentum-by-language-and-country.csv", check.names = FALSE)
py <- py[py$geo == "WORLD", ]
m <- merge(res, py[, c("language", "momentum", "usage", "hiring", "learning", "interest")], by = "language", suffixes = c("_r", "_py"))
d <- with(m, c(momentum = max(abs(momentum_r - momentum_py), na.rm = TRUE), usage = max(abs(usage_r - usage_py), na.rm = TRUE),
                hiring = max(abs(hiring_r - hiring_py), na.rm = TRUE), learning = max(abs(learning_r - learning_py), na.rm = TRUE),
                interest = max(abs(interest_r - interest_py), na.rm = TRUE)))
cat("\nMax absolute difference vs Python:\n"); print(signif(d, 3))

# Backtest: log(want/used) in year t vs log(used_{t+2}/used_t), year fixed effects
P <- function(y, k) { v <- unlist(sv[sv$year == y & sv$metric == k, L]); v[v == 0] <- NA; v }
bt <- do.call(rbind, lapply(2017:2024, function(t) {
  u0 <- P(t, "u"); w0 <- P(t, "w"); u2 <- P(t + 2, "u")
  ok <- !is.na(u0) & !is.na(w0) & !is.na(u2)
  data.frame(year = t, language = L[ok], gap = log(w0 / u0)[ok], growth = log(u2 / u0)[ok]) }))
fit <- lm(growth ~ gap + factor(year), data = bt)
cat("\nBacktest slope (lm with year FE):", round(coef(fit)["gap"], 3), " n =", nrow(bt), "\n")
js <- paste(readLines("data/processed/summary.json", warn = FALSE), collapse = "")
cat("Python slope:", sub('.*"slope": ([0-9.]+).*', "\\1", js), "\n")
