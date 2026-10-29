# pip install pandas numpy scipy statsmodels
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

df = pd.read_csv("ai-exposure-employment-change-by-occupation.csv", dtype={"major_group": str})
df = df.dropna(subset=["aei_observed_exposure", "median_annual_wage_2019"]).copy()   # 722 occupations

# Outcome: annualised change in log employment, in percentage points per year
df["y"] = df["annualised_log_change_2019_2025"] * 100
# Exposure standardised to 1 SD (population SD), plus controls
x = df["aei_observed_exposure"]
df["exposure_sd"] = (x - x.mean()) / x.std(ddof=0)
df["log_wage"] = np.log(df["median_annual_wage_2019"])
df["tele"] = df["dingel_neiman_teleworkable"].fillna(df["dingel_neiman_teleworkable"].mean())

print("Pearson r:",  stats.pearsonr(x, df["y"]))        # r = +0.01, p = 0.79
print("Spearman:",   stats.spearmanr(x, df["y"]))       # rho = +0.11, p = 0.004

w = df["employment_may2019"]
m1 = smf.wls("y ~ exposure_sd", df, weights=w).fit(cov_type="HC3")
m4 = smf.wls("y ~ exposure_sd + log_wage + tele + C(major_group)", df, weights=w).fit(cov_type="HC3")
for name, m in [("bivariate, weighted", m1), ("full model", m4)]:
    lo, hi = m.conf_int().loc["exposure_sd"]
    print(f"{name}: {m.params['exposure_sd']:+.2f} pp/yr per SD  [{lo:+.2f}, {hi:+.2f}]  p = {m.pvalues['exposure_sd']:.3f}")
# bivariate: -0.23 [-0.61, +0.16] p = 0.251 ; full model: -0.16 [-0.50, +0.18] p = 0.360
