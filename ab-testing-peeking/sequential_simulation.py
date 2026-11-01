#!/usr/bin/env python3
"""A/B test peeking: how often it declares a false winner, and how a sequential
boundary fixes it (Truth with Data case study, Nov 2026).

Usage: python3 sequential_simulation.py OUT_DIR

Set-up (extends simulation.py):
  * 1,000 visitors per arm per day for 20 days, 5% baseline conversion.
  * Each look runs a two-sided two-proportion z-test on the cumulative data.
  * A/A tests (no real difference) measure false winners; A/B tests with a real
    +10% relative lift (5.0% -> 5.5%) measure power and how early a true winner is called.
  * Fix: a Pocock-style constant boundary for 20 daily looks, calibrated by simulation
    so the overall false-winner rate is 5%; and an O'Brien-Fleming-style boundary
    (critical z falls as data accumulates), calibrated the same way.
50,000 simulated tests per scenario.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261101)
SIMS, DAYS, N_DAY, P0, LIFT = 50_000, 20, 1_000, 0.05, 0.10


def zpath(p_a, p_b):
    a = rng.binomial(N_DAY, p_a, size=(SIMS, DAYS)).cumsum(axis=1)
    b = rng.binomial(N_DAY, p_b, size=(SIMS, DAYS)).cumsum(axis=1)
    n = N_DAY * np.arange(1, DAYS + 1)
    pooled = (a + b) / (2 * n)
    se = np.sqrt(pooled * (1 - pooled) * 2 / n)
    return (b / n - a / n) / se  # positive = B looks better


z_null = zpath(P0, P0)
z_alt = zpath(P0, P0 * (1 + LIFT))
days = np.arange(1, DAYS + 1)
t = days / DAYS  # information fraction


def first_cross(z, crit, looks):
    """Day of the first look where |z| crosses its critical value (inf if never)."""
    hit = np.abs(z[:, looks - 1]) >= crit[looks - 1]
    any_hit = hit.any(axis=1)
    first = np.where(any_hit, looks[np.argmax(hit, axis=1)], np.inf)
    return first


def calibrate(shape, looks, alpha=0.05):
    """Scale a boundary shape c * shape(t) so the A/A false-winner rate is alpha."""
    lo, hi = 1.5, 6.0
    for _ in range(60):
        c = (lo + hi) / 2
        rate = np.isfinite(first_cross(z_null, c * shape, looks)).mean()
        lo, hi = (lo, c) if rate < alpha else (c, hi)
    return (lo + hi) / 2


fixed = np.full(DAYS, norm.ppf(0.975))
daily = days
pocock_c = calibrate(np.ones(DAYS), daily)
obf_c = calibrate(1 / np.sqrt(t), daily)
pocock, obf = pocock_c * np.ones(DAYS), obf_c / np.sqrt(t)

plans = [
    ("Look once, at day 20 (as planned)", fixed, np.array([20])),
    ("Look weekly (days 7, 14, 20)", fixed, np.array([7, 14, 20])),
    ("Look every 2 days", fixed, np.arange(2, 21, 2)),
    ("Look daily, stop at first p < 0.05", fixed, daily),
    ("Look daily with a sequential boundary (O'Brien-Fleming style)", obf, daily),
    ("Look daily with a sequential boundary (Pocock style)", pocock, daily),
]
rows = []
for name, crit, looks in plans:
    fn = first_cross(z_null, crit, looks)
    fa = first_cross(z_alt, crit, looks)
    # a 'win' only counts if B is ahead when the test stops
    stop_idx = np.where(np.isfinite(fa), fa, DAYS).astype(int) - 1
    b_ahead = z_alt[np.arange(SIMS), stop_idx] > 0
    power = (np.isfinite(fa) & b_ahead).mean()
    rows.append({
        "plan": name, "looks": len(looks),
        "false_winner_rate": np.isfinite(fn).mean(),
        "power_10pct_lift": power,
        "mean_days_to_stop_true_lift": np.where(np.isfinite(fa), fa, DAYS).mean(),
        "share_true_winners_called_by_day_10": (fa <= 10).mean(),
        "nominal_p_threshold_last_look": 2 * (1 - norm.cdf(crit[looks[-1] - 1])),
        "critical_z_day_5": crit[4], "critical_z_day_20": crit[19],
    })
res = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(res.round(4).to_string())
res.to_csv(os.path.join(OUT, "ab-test-peeking-sequential-simulation.csv"), index=False)
json.dump({"sims": SIMS, "days": DAYS, "visitors_per_arm_per_day": N_DAY, "baseline": P0, "relative_lift": LIFT,
           "pocock_z": pocock_c, "pocock_nominal_p": 2 * (1 - norm.cdf(pocock_c)), "obf_c": obf_c,
           "results": res.to_dict("records")},
          open(os.path.join(OUT, "ab-test-peeking-summary.json"), "w"), indent=1)

# example A/A paths for the explainer chart: one that crosses 1.96 early then fades,
# and two ordinary ones; plus the boundaries
az = np.abs(z_null)
early = np.where((az[:, 3:9].max(axis=1) > 2.3) & (az[:, -1] < 0.6) & (az[:, 3:9].max(axis=1) < pocock_c - 0.1))[0]
calm = np.where(az.max(axis=1) < 1.5)[0]
pick = [early[0], calm[0], calm[1]]
paths = pd.DataFrame({"day": days, "fixed_z": fixed, "obf_z": obf, "pocock_z": pocock,
                      **{f"path_{k}": z_null[i] for k, i in enumerate(pick)}})
paths.to_csv(os.path.join(OUT, "ab-test-peeking-example-paths.csv"), index=False)
