# install.packages(c("sandwich", "lmtest"))
library(sandwich); library(lmtest)

df <- read.csv("ai-exposure-employment-change-by-occupation.csv", colClasses = c(major_group = "character"))
df <- df[!is.na(df$aei_observed_exposure) & !is.na(df$median_annual_wage_2019), ]   # 722 occupations

df$y <- df$annualised_log_change_2019_2025 * 100          # pp per year
x <- df$aei_observed_exposure
df$exposure_sd <- (x - mean(x)) / sqrt(mean((x - mean(x))^2))   # population SD, as in Python
df$log_wage <- log(df$median_annual_wage_2019)
df$tele <- ifelse(is.na(df$dingel_neiman_teleworkable), mean(df$dingel_neiman_teleworkable, na.rm = TRUE), df$dingel_neiman_teleworkable)

cor.test(x, df$y)                                          # r = +0.01, p = 0.79
cor.test(x, df$y, method = "spearman", exact = FALSE)      # rho = +0.11, p = 0.004

report <- function(m, name) {
  ct <- coeftest(m, vcov = vcovHC(m, type = "HC3")); ci <- coefci(m, vcov = vcovHC(m, type = "HC3"))
  cat(sprintf("%s: %+.2f pp/yr per SD  [%+.2f, %+.2f]  p = %.3f\n", name,
              ct["exposure_sd", 1], ci["exposure_sd", 1], ci["exposure_sd", 2], ct["exposure_sd", 4]))
}
report(lm(y ~ exposure_sd, df, weights = employment_may2019), "bivariate, weighted")
report(lm(y ~ exposure_sd + log_wage + tele + factor(major_group), df, weights = employment_may2019), "full model")
# bivariate: -0.23 [-0.61, +0.16] p = 0.252 ; full model: -0.16 [-0.50, +0.18] p = 0.360
