"""A/A test simulation: how often does 'peeking' declare a winner when nothing changed?

Both arms convert at 5%. 1,000 visitors per arm per day for 20 days.
Each 'peek' runs a two-sided two-proportion z-test on the cumulative data.
A test 'finds a winner' if any peek has p < 0.05. 10,000 simulated tests.
Run: python3 simulation.py
"""
import numpy as np
from scipy.stats import norm

rng = np.random.default_rng(20261029)
SIMS, DAYS, N_DAY, P = 10_000, 20, 1_000, 0.05

a = rng.binomial(N_DAY, P, size=(SIMS, DAYS)).cumsum(axis=1)
b = rng.binomial(N_DAY, P, size=(SIMS, DAYS)).cumsum(axis=1)
n = N_DAY * np.arange(1, DAYS + 1)
pooled = (a + b) / (2 * n)
se = np.sqrt(pooled * (1 - pooled) * 2 / n)
z = np.abs(a / n - b / n) / se
p = 2 * (1 - norm.cdf(z))
sig = p < 0.05

def rate(peek_days):
    idx = np.array(peek_days) - 1
    return sig[:, idx].any(axis=1).mean()

schedules = {
    "Once, at day 20 (as planned)": [20],
    "Weekly (days 7, 14, 20)": [7, 14, 20],
    "Every 2 days": list(range(2, 21, 2)),
    "Daily (20 peeks)": list(range(1, 21)),
}
for name, days in schedules.items():
    print(f"{name:32s} false 'winner' rate: {rate(days):.1%}")
