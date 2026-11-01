# How often does "peeking" at an A/B test find a winner that isn't there?

Case study: https://truthwithdata.com/case-studies/ab-testing-peeking-simulation.html · Guide: https://truthwithdata.com/blog/statistical-significance-ab-testing.html · Sample size calculator: https://truthwithdata.com/tools/sample-size-calculator.html

```bash
pip install numpy scipy pandas matplotlib
python simulation.py                      # the original 10,000-test version
python sequential_simulation.py out       # 100,000 tests, six stopping plans, sequential boundaries (~3 s)
python charts.py out charts               # the two charts in the case study
```

## The original simulation (`simulation.py`)

10,000 A/A tests: both versions convert at 5%, with 1,000 visitors per arm per day for 20 days. At each "peek" it runs a two-sided two-proportion z-test on the data so far, and counts a false winner if any peek has p < 0.05.

Result (seed 20261029):

| How often you check | False "winner" rate |
| --- | --- |
| Once, at day 20 as planned | 5.1% |
| Weekly (days 7, 14, 20) | 10.9% |
| Every 2 days | 19.3% |
| Daily, stopping at the first p < 0.05 | 24.9% |

## The fix (`sequential_simulation.py`)

Same set-up with 50,000 A/A tests (no real difference) and 50,000 A/B tests with a real 10% relative lift (5.0% to 5.5%), each read under six stopping plans. The Pocock (constant) and O'Brien-Fleming (c/√t) boundaries for 20 daily looks are calibrated by simulation so exactly 5% of A/A tests ever cross them.

Result (seed 20261101):

| Plan | False winners | Power (10% lift) | Average days to stop (10% lift) |
| --- | --- | --- | --- |
| Look once at day 20 | 4.9% | 61% | 20.0 |
| Look weekly | 10.4% | 66% | 15.2 |
| Look every 2 days | 19.2% | 72% | 12.2 |
| Look daily, stop at p < 0.05 | 24.6% | 74% | 11.0 |
| Daily with O'Brien-Fleming boundary | 5.0% | 59% | 16.8 |
| Daily with Pocock boundary (z = 2.66, p = 0.0077) | 5.0% | 46% | 15.8 |

`data/ab-test-peeking-sequential-simulation.csv` has these plus the critical values; `data/ab-test-peeking-example-paths.csv` has the boundaries and three example A/A paths used in the explainer chart.
