# How often does "peeking" at an A/B test find a winner that isn't there?

Related guide: https://truthwithdata.com/blog/statistical-significance-ab-testing.html · Sample size calculator: https://truthwithdata.com/tools/sample-size-calculator.html

`simulation.py` runs 10,000 A/A tests: both versions convert at 5%, with 1,000 visitors per arm per day for 20 days. At each "peek" it runs a two-sided two-proportion z-test on the data so far, and counts a false winner if any peek has p < 0.05.

```bash
pip install numpy scipy
python simulation.py
```

Result (seed 20261029):

| How often you check | False "winner" rate |
| --- | --- |
| Once, at day 20 as planned | 5.1% |
| Weekly (days 7, 14, 20) | 10.9% |
| Every 2 days | 19.3% |
| Daily, stopping at the first p < 0.05 | 24.9% |
