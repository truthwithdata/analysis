#!/usr/bin/env python3
"""Does "Sell in May and go away" beat buy-and-hold? (Truth with Data, November 2026)

Usage: python sell-in-may-analysis.py DATA_DIR [JS_OUT]
  DATA_DIR  folder holding us-stocks-cash-monthly-panel-1871-2026.csv (built by
            sell-in-may-build-panel.py); all outputs are written there too.
  JS_OUT    optional path for the backtester's data file (js/sell-in-may-data.js).

Method
  * Stocks = Shiller's S&P Composite (S&P 500 from 1957), monthly average prices. The total
    return credited to month t is (P[t] + D[t]/12) / P[t-1] - 1, where D is the 12-month
    dividend. Because P is an average of daily closes, "May" runs roughly from mid-April to
    mid-May. We check every result with the opposite convention (each month shifted one later).
  * Cash = 3-month Treasury bill (FRED TB3MS) from 1934; NBER New York commercial paper rate
    before 1934. Month t earns rate[t-1] / 12.
  * Real = deflated by CPI (Shiller's CPI, extended with CPI-U NSA from FRED).
  * Summer of year y = May to October of y. Winter of year y = November of y-1 to April of y.
  * Strategy "Sell in May": stocks November to April, cash May to October. Costs are charged on
    each switch (two a year). Optional tax: the switcher pays tax on each May sale's net gain
    (losses carried forward) and on cash interest; buy-and-hold pays tax once, on its gain at
    the end. Dividends are untaxed in both (they are the same for both strategies while invested).
  * Bootstrap confidence intervals resample whole years (10,000 draws, seed 2026, the same draws
    for every statistic).
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

D = sys.argv[1]
JS = sys.argv[2] if len(sys.argv) > 2 else None
B = 10_000
rng = np.random.default_rng(2026)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

p = pd.read_csv(os.path.join(D, "us-stocks-cash-monthly-panel-1871-2026.csv"))
P, Dv, C, R = p.sp_composite_price.to_numpy(), p.dividend_12m.to_numpy(), p.cpi.to_numpy(), p.cash_rate_pct.to_numpy()

# 1. Monthly returns (row k describes the month p.date[k], k >= 1) -------------------------------
m = pd.DataFrame({"date": p.date[1:].to_numpy()})
m["year"] = m.date.str[:4].astype(int)
m["month"] = m.date.str[5:7].astype(int)
m["stock_tr"] = (P[1:] + Dv[1:] / 12) / P[:-1] - 1
m["price_only"] = P[1:] / P[:-1] - 1
m["cash"] = R[:-1] / 1200
m["inflation"] = C[1:] / C[:-1] - 1
m["stock_real"] = (1 + m.stock_tr) / (1 + m.inflation) - 1
m["cash_real"] = (1 + m.cash) / (1 + m.inflation) - 1
m.to_csv(os.path.join(D, "sell-in-may-monthly-returns-1871-2026.csv"), index=False, float_format="%.6f")
FIRST, LAST = m.date.iloc[0], m.date.iloc[-1]
NM = len(m)


def boot_mean_ci(x, stat=np.mean):
    x = np.asarray(x)
    idx = np.random.default_rng(2026).integers(0, len(x), size=(B, len(x)))   # same draws every call
    s = stat(x[idx], axis=1)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def tstat_p(x):
    x = np.asarray(x)
    t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
    return float(t), float(math.erfc(abs(t) / math.sqrt(2)))   # two-sided, normal approximation


# 2. Half years -------------------------------------------------------------------------------------
def compound(sel, col):
    return float(np.prod(1 + m.loc[sel, col].to_numpy()) - 1)


def halves(shift=0):
    """Summer = May..Oct of y (months shifted by `shift`), winter = Nov y-1 .. Apr y."""
    rows = []
    key = m.year * 12 + (m.month - 1)
    for y in range(m.year.min(), m.year.max() + 1):
        s0 = y * 12 + 4 + shift                    # May (+shift) of y
        w0 = (y - 1) * 12 + 10 + shift              # Nov (+shift) of y-1
        ss, ws = key.between(s0, s0 + 5), key.between(w0, w0 + 5)
        r = {"year": y}
        if ss.sum() == 6:
            r.update(summer_stock_real=compound(ss, "stock_real"), summer_cash_real=compound(ss, "cash_real"),
                     summer_stock_nominal=compound(ss, "stock_tr"), summer_cash_nominal=compound(ss, "cash"))
        if ws.sum() == 6:
            r.update(winter_stock_real=compound(ws, "stock_real"), winter_cash_real=compound(ws, "cash_real"),
                     winter_stock_nominal=compound(ws, "stock_tr"))
        rows.append(r)
    return pd.DataFrame(rows)


h = halves()
h["summer_excess_over_cash"] = (1 + h.summer_stock_nominal) / (1 + h.summer_cash_nominal) - 1
h.to_csv(os.path.join(D, "sell-in-may-half-years-1871-2026.csv"), index=False, float_format="%.6f")


def half_stats(h, lo=None, hi=None, label="all"):
    """Seasonal statistics using summers lo..hi and the winters that follow them (Nov y .. Apr y+1)."""
    hs = h.dropna(subset=["summer_stock_real"])
    if lo is not None:
        hs = hs[(hs.year >= lo) & (hs.year <= hi)]
    hw = h.dropna(subset=["winter_stock_real"])
    hw = hw[hw.year.isin(hs.year + 1)]
    pair = hs[["year", "summer_stock_real"]].merge(hw[["year", "winter_stock_real"]].assign(year=hw.year - 1), on="year")
    gap = pair.winter_stock_real - pair.summer_stock_real
    ex = hs.summer_excess_over_cash
    t, pv = tstat_p(gap)
    return {"period": label, "summers": int(len(hs)), "first_summer": int(hs.year.min()), "last_summer": int(hs.year.max()),
            "winters": int(len(hw)),
            "summer_mean_pct": 100 * hs.summer_stock_real.mean(), "summer_median_pct": 100 * hs.summer_stock_real.median(),
            "summer_mean_ci_lo": 100 * boot_mean_ci(hs.summer_stock_real)[0], "summer_mean_ci_hi": 100 * boot_mean_ci(hs.summer_stock_real)[1],
            "winter_mean_pct": 100 * hw.winter_stock_real.mean(), "winter_median_pct": 100 * hw.winter_stock_real.median(),
            "winter_mean_ci_lo": 100 * boot_mean_ci(hw.winter_stock_real)[0], "winter_mean_ci_hi": 100 * boot_mean_ci(hw.winter_stock_real)[1],
            "gap_mean_pts": 100 * gap.mean(), "gap_ci_lo": 100 * boot_mean_ci(gap)[0], "gap_ci_hi": 100 * boot_mean_ci(gap)[1],
            "gap_median_pts": 100 * gap.median(), "gap_t": t, "gap_p": pv,
            "winter_beat_summer_pct": 100 * (gap > 0).mean(), "pairs": int(len(gap)),
            "summer_stocks_lost_real_pct": 100 * (hs.summer_stock_real < 0).mean(),
            "summer_stocks_beat_cash_pct": 100 * (ex > 0).mean(),
            "summer_excess_mean_pct": 100 * ex.mean(), "summer_excess_ci_lo": 100 * boot_mean_ci(ex)[0],
            "summer_excess_ci_hi": 100 * boot_mean_ci(ex)[1], "summer_excess_median_pct": 100 * ex.median()}


# 3. Strategy simulation ----------------------------------------------------------------------------
def simulate(i0, i1, in_months, cost=0.0, tax=0.0):
    """Months i0..i1 of m (inclusive). in_months: set of calendar months (1-12) invested in stocks.
    Returns dict with nominal pre-tax path for the switcher and buy-and-hold, after-tax finals."""
    rs, rc, mo = m.stock_tr.to_numpy(), m.cash.to_numpy(), m.month.to_numpy()
    v, basis, carry, taxpaid = 1.0, 1.0, 0.0, 0.0
    inv = mo[i0] in in_months
    bh = 1.0
    path_s, path_b, switches = [], [], 0
    for k in range(i0, i1 + 1):
        want = mo[k] in in_months
        if want != inv:
            switches += 1
            if inv:      # sell stocks at the start of month k
                g = v - basis + carry
                if g > 0:
                    v -= tax * g
                    carry = 0.0
                else:
                    carry = g
                v *= 1 - cost
            else:        # buy back
                v *= 1 - cost
                basis = v
            inv = want
        if inv:
            v *= 1 + rs[k]
        else:
            v *= 1 + rc[k] * (1 - tax)
        bh *= 1 + rs[k]
        path_s.append(v)
        path_b.append(bh)
    v_after = v - tax * max(0.0, v - basis + carry) if inv else v
    bh_after = bh - tax * max(0.0, bh - 1.0)
    return {"s": np.array(path_s), "b": np.array(path_b), "s_final": v_after, "b_final": bh_after, "switches": switches}


def summarise(i0, i1, in_months, cost, tax):
    r = simulate(i0, i1, in_months, cost, tax)
    n = i1 - i0 + 1
    infl = np.prod(1 + m.inflation.to_numpy()[i0:i1 + 1])
    defl = np.cumprod(1 + m.inflation.to_numpy()[i0:i1 + 1])

    def mdd(path):
        real = np.concatenate([[1.0], path / defl])
        return float((real / np.maximum.accumulate(real) - 1).min())

    # year-by-year: calendar years fully inside the range
    yrs = m.year.to_numpy()[i0:i1 + 1]
    won, tot = 0, 0
    s_full, b_full = np.concatenate([[1.0], r["s"]]), np.concatenate([[1.0], r["b"]])
    for y in np.unique(yrs):
        ks = np.where(yrs == y)[0]
        if len(ks) < 12:
            continue
        a, b_ = ks[0], ks[-1] + 1
        tot += 1
        won += (s_full[b_] / s_full[a]) > (b_full[b_] / b_full[a])
    yrs_n = n / 12
    # 50/50 benchmark: half stocks, half cash, rebalanced monthly (same average exposure as switching)
    bl = np.cumprod(1 + 0.5 * m.stock_tr.to_numpy()[i0:i1 + 1] + 0.5 * m.cash.to_numpy()[i0:i1 + 1])
    bl_final = bl[-1] - tax * max(0.0, bl[-1] - 1.0)   # tax at the end only (a simplification)

    def vol(path):
        full = np.concatenate([[1.0], path / defl])
        return float(np.std(np.diff(np.log(full)), ddof=1) * math.sqrt(12))
    return {"halfhalf_real_cagr_pct": 100 * ((bl_final / infl) ** (1 / yrs_n) - 1), "halfhalf_max_drawdown_pct": 100 * mdd(bl),
            "strategy_real_vol_pct": 100 * vol(r["s"]), "buyhold_real_vol_pct": 100 * vol(r["b"]), "halfhalf_real_vol_pct": 100 * vol(bl),
            "strategy_real_final": r["s_final"] / infl, "buyhold_real_final": r["b_final"] / infl,
            "strategy_real_cagr_pct": 100 * ((r["s_final"] / infl) ** (1 / yrs_n) - 1),
            "buyhold_real_cagr_pct": 100 * ((r["b_final"] / infl) ** (1 / yrs_n) - 1),
            "strategy_nominal_cagr_pct": 100 * (r["s_final"] ** (1 / yrs_n) - 1),
            "buyhold_nominal_cagr_pct": 100 * (r["b_final"] ** (1 / yrs_n) - 1),
            "strategy_max_drawdown_pct": 100 * mdd(r["s"]), "buyhold_max_drawdown_pct": 100 * mdd(r["b"]),
            "strategy_months_in_stocks_pct": 100 * np.mean([mo in in_months for mo in m.month.to_numpy()[i0:i1 + 1]]),
            "years_compared": tot, "strategy_won_years_pct": 100 * won / tot if tot else float("nan"), "switches": r["switches"]}


def idx(date):
    return int(np.where(m.date == date)[0][0])


HALLOWEEN = {11, 12, 1, 2, 3, 4}
i_all0, i_all1 = 0, NM - 1
scen = []
for cost in [0.0, 0.001, 0.0025, 0.005]:
    for tax in [0.0, 0.2]:
        r = summarise(i_all0, i_all1, HALLOWEEN, cost, tax)
        scen.append({"from": FIRST, "to": LAST, "cost_per_switch_pct": 100 * cost, "tax_rate_pct": 100 * tax, **r})
scen = pd.DataFrame(scen)
scen.to_csv(os.path.join(D, "sell-in-may-backtest-scenarios.csv"), index=False, float_format="%.4f")

# Break-even cost: largest cost per switch at which the switcher still matches buy-and-hold (no tax)
lo_c, hi_c = 0.0, 0.05
base = summarise(i_all0, i_all1, HALLOWEEN, 0.0, 0.0)
if base["strategy_real_final"] < base["buyhold_real_final"]:
    breakeven_cost = 0.0
else:
    for _ in range(60):
        mid = (lo_c + hi_c) / 2
        s = summarise(i_all0, i_all1, HALLOWEEN, mid, 0.0)
        lo_c, hi_c = (mid, hi_c) if s["strategy_real_final"] > s["buyhold_real_final"] else (lo_c, mid)
    breakeven_cost = lo_c
lo_c, hi_c = 0.0, 0.05
for _ in range(60):
    mid = (lo_c + hi_c) / 2
    s_ = summarise(i_all0, i_all1, HALLOWEEN, mid, 0.0)
    lo_c, hi_c = (mid, hi_c) if s_["strategy_real_cagr_pct"] > s_["halfhalf_real_cagr_pct"] else (lo_c, mid)
breakeven_vs_halfhalf = lo_c

# 4. Periods: eras and decades (by summer year; each Halloween year = May y .. Apr y+1) ----------------
def hy_range(y0, y1):
    a = idx(f"{y0}-05")
    end = f"{y1 + 1}-04"
    b = idx(end) if end <= LAST else NM - 1
    return a, b


eras = [("1871-1950", 1871, 1950), ("1951-2001", 1951, 2001), ("2002-2025", 2002, 2025),
        ("1871-2001 (before the paper)", 1871, 2001), ("All 1871-2025", 1871, 2025)]
rows = []
for lab, y0, y1 in eras:
    st = half_stats(h, y0, y1, lab)
    a, b = hy_range(y0, y1)
    bt0 = summarise(a, b, HALLOWEEN, 0.0, 0.0)
    bt1 = summarise(a, b, HALLOWEEN, 0.0025, 0.0)
    st.update({"kind": "era", "bt_from": m.date[a], "bt_to": m.date[b],
               "strategy_minus_buyhold_real_cagr_pts_no_cost": bt0["strategy_real_cagr_pct"] - bt0["buyhold_real_cagr_pct"],
               "strategy_minus_buyhold_real_cagr_pts_cost_0_25": bt1["strategy_real_cagr_pct"] - bt1["buyhold_real_cagr_pct"],
               "buyhold_real_cagr_pct": bt0["buyhold_real_cagr_pct"], "strategy_real_cagr_pct_no_cost": bt0["strategy_real_cagr_pct"]})
    rows.append(st)
for d0 in range(1870, 2030, 10):
    y0, y1 = max(d0, 1871), min(d0 + 9, 2025)
    st = half_stats(h, y0, y1, f"{d0}s")
    a, b = hy_range(y0, y1)
    bt0 = summarise(a, b, HALLOWEEN, 0.0, 0.0)
    bt1 = summarise(a, b, HALLOWEEN, 0.0025, 0.0)
    st.update({"kind": "decade", "bt_from": m.date[a], "bt_to": m.date[b],
               "strategy_minus_buyhold_real_cagr_pts_no_cost": bt0["strategy_real_cagr_pct"] - bt0["buyhold_real_cagr_pct"],
               "strategy_minus_buyhold_real_cagr_pts_cost_0_25": bt1["strategy_real_cagr_pct"] - bt1["buyhold_real_cagr_pct"],
               "buyhold_real_cagr_pct": bt0["buyhold_real_cagr_pct"], "strategy_real_cagr_pct_no_cost": bt0["strategy_real_cagr_pct"]})
    rows.append(st)
per = pd.DataFrame(rows)
cols = ["kind", "period"] + [c for c in per.columns if c not in ("kind", "period")]
per[cols].to_csv(os.path.join(D, "sell-in-may-by-period.csv"), index=False, float_format="%.3f")

# Robustness: months shifted one later (Jun-Nov vs Dec-May), nominal, price-only
h_shift = halves(shift=1)
h_shift["summer_excess_over_cash"] = (1 + h_shift.summer_stock_nominal) / (1 + h_shift.summer_cash_nominal) - 1
rob = {"shifted_one_month": half_stats(h_shift, 1871, 2025, "shifted"),
       "shifted_backtest": summarise(0, NM - 1, {12, 1, 2, 3, 4, 5}, 0.0, 0.0)}
hn = h.copy()
hn["summer_stock_real"], hn["winter_stock_real"] = hn.summer_stock_nominal, hn.winter_stock_nominal
rob["nominal"] = half_stats(hn, 1871, 2025, "nominal")

# 5. Every 6-month "out" window (exit month E, out for 6 months) --------------------------------------
win6 = []
for e in range(1, 13):
    out = {((e - 1 + k) % 12) + 1 for k in range(6)}
    inm = set(range(1, 13)) - out
    s0 = summarise(0, NM - 1, inm, 0.0, 0.0)
    win6.append({"exit_month": MON[e - 1], "reenter_month": MON[(e + 5) % 12],
                 "strategy_real_cagr_pct": s0["strategy_real_cagr_pct"], "buyhold_real_cagr_pct": s0["buyhold_real_cagr_pct"],
                 "strategy_won_years_pct": s0["strategy_won_years_pct"]})
win6 = pd.DataFrame(win6)

# 6. Calendar months -------------------------------------------------------------------------------
mrows = []
full = m[(m.year >= 1871)]
for k in range(1, 13):
    x = full[full.month == k].stock_real.to_numpy()
    xn = full[full.month == k].stock_tr.to_numpy()
    lo, hi = boot_mean_ci(x)
    mrows.append({"month": MON[k - 1], "n": len(x), "mean_real_pct": 100 * x.mean(), "ci_lo": 100 * lo, "ci_hi": 100 * hi,
                  "median_real_pct": 100 * np.median(x), "share_positive_pct": 100 * (x > 0).mean(),
                  "mean_nominal_pct": 100 * xn.mean(),
                  "mean_real_pct_1871_2001": 100 * full[(full.month == k) & (full.year <= 2001)].stock_real.mean(),
                  "mean_real_pct_2002_2026": 100 * full[(full.month == k) & (full.year >= 2002)].stock_real.mean()})
mav = pd.DataFrame(mrows)
mav.to_csv(os.path.join(D, "sell-in-may-month-averages.csv"), index=False, float_format="%.3f")
# Is September different from the other 11 months? Permutation-free check: bootstrap of the difference
sep = full[full.month == 9].stock_real.to_numpy()
oth = full[full.month != 9].stock_real.to_numpy()
sep_diff = 100 * (sep.mean() - oth.mean())
db = [100 * (rng.choice(sep, len(sep)).mean() - rng.choice(oth, len(oth)).mean()) for _ in range(B)]
jan = full[full.month == 1].stock_real.to_numpy()
oth_j = full[full.month != 1].stock_real.to_numpy()
jb = [100 * (rng.choice(jan, len(jan)).mean() - rng.choice(oth_j, len(oth_j)).mean()) for _ in range(B)]

# 7. Summary ------------------------------------------------------------------------------------------
allst = half_stats(h, 1871, 2025, "all")
pre = per[per.period == "1871-2001 (before the paper)"].iloc[0].to_dict()
post = per[per.period == "2002-2025"].iloc[0].to_dict()
summary = {
    "data_from": FIRST, "data_to": LAST, "months": NM,
    "halves": allst,
    "pre_2002": pre, "post_2002": post,
    "scenarios": scen.to_dict(orient="records"),
    "breakeven_cost_per_switch_pct": 100 * breakeven_cost,
    "breakeven_cost_vs_halfhalf_pct": 100 * breakeven_vs_halfhalf,
    "robustness": rob,
    "six_month_windows": win6.to_dict(orient="records"),
    "september_minus_other_months_pts": sep_diff, "september_diff_ci": [float(np.percentile(db, 2.5)), float(np.percentile(db, 97.5))],
    "january_minus_other_months_pts": 100 * (jan.mean() - oth_j.mean()), "january_diff_ci": [float(np.percentile(jb, 2.5)), float(np.percentile(jb, 97.5))],
    "worst_month_by_mean": mav.sort_values("mean_real_pct").month.iloc[0],
    "best_month_by_mean": mav.sort_values("mean_real_pct").month.iloc[-1],
    "cash_vs_summer_stocks": {"mean_real_cash_summer_pct": 100 * h.summer_cash_real.mean()},
}
with open(os.path.join(D, "sell-in-may-summary.json"), "w") as f:
    json.dump(summary, f, indent=1, default=float)

# 8. Console report ------------------------------------------------------------------------------------
a = allst
print(f"Monthly returns {FIRST} to {LAST}: {NM} months")
print(f"Summers {a['first_summer']}-{a['last_summer']} (n={a['summers']}): mean real {a['summer_mean_pct']:.2f}% "
      f"[{a['summer_mean_ci_lo']:.2f}, {a['summer_mean_ci_hi']:.2f}], median {a['summer_median_pct']:.2f}%")
print(f"Winters (n={a['winters']}): mean real {a['winter_mean_pct']:.2f}% [{a['winter_mean_ci_lo']:.2f}, {a['winter_mean_ci_hi']:.2f}], "
      f"median {a['winter_median_pct']:.2f}%")
print(f"Gap winter - summer: {a['gap_mean_pts']:.2f} pts [{a['gap_ci_lo']:.2f}, {a['gap_ci_hi']:.2f}], median {a['gap_median_pts']:.2f}, "
      f"t={a['gap_t']:.2f}, p={a['gap_p']:.4f}; winter beat summer in {a['winter_beat_summer_pct']:.1f}% of {a['pairs']} years")
print(f"Summer stocks beat cash in {a['summer_stocks_beat_cash_pct']:.1f}% of summers; mean excess {a['summer_excess_mean_pct']:.2f}% "
      f"[{a['summer_excess_ci_lo']:.2f}, {a['summer_excess_ci_hi']:.2f}]; summer stocks lost money (real) in {a['summer_stocks_lost_real_pct']:.1f}%")
for _, r in scen.iterrows():
    print(f"cost {r.cost_per_switch_pct:.2f}% tax {r.tax_rate_pct:.0f}%: $1 -> switch {r.strategy_real_final:,.0f} vs hold {r.buyhold_real_final:,.0f} real; "
          f"CAGR {r.strategy_real_cagr_pct:.2f}% vs {r.buyhold_real_cagr_pct:.2f}%; maxDD {r.strategy_max_drawdown_pct:.1f}% vs {r.buyhold_max_drawdown_pct:.1f}%; "
          f"won {r.strategy_won_years_pct:.1f}% of {r.years_compared} yrs; 50/50 {r.halfhalf_real_cagr_pct:.2f}%")
print(f"Break-even cost per switch (no tax): {100 * breakeven_cost:.3f}%; vs 50/50 blend {100 * breakeven_vs_halfhalf:.3f}%")
r0 = scen.iloc[0]
print(f"50/50 blend: real CAGR {r0.halfhalf_real_cagr_pct:.2f}%, maxDD {r0.halfhalf_max_drawdown_pct:.1f}%; real vol switch {r0.strategy_real_vol_pct:.1f}% "
      f"hold {r0.buyhold_real_vol_pct:.1f}% 50/50 {r0.halfhalf_real_vol_pct:.1f}%")
for _, r in per[per.kind == "era"].iterrows():
    print(f"{r.period}: summer {r.summer_mean_pct:.2f}% winter {r.winter_mean_pct:.2f}% gap {r.gap_mean_pts:.2f} [{r.gap_ci_lo:.2f}, {r.gap_ci_hi:.2f}] "
          f"winter won {r.winter_beat_summer_pct:.0f}%; summer stocks beat cash {r.summer_stocks_beat_cash_pct:.0f}%; "
          f"strategy - hold {r.strategy_minus_buyhold_real_cagr_pts_no_cost:+.2f} pts (no cost), {r.strategy_minus_buyhold_real_cagr_pts_cost_0_25:+.2f} (0.25%)")
for _, r in per[per.kind == "decade"].iterrows():
    print(f"  {r.period}: gap {r.gap_mean_pts:6.2f}  strat-hold {r.strategy_minus_buyhold_real_cagr_pts_no_cost:+.2f}")
s = rob["shifted_one_month"]
print(f"Shifted one month: gap {s['gap_mean_pts']:.2f} [{s['gap_ci_lo']:.2f}, {s['gap_ci_hi']:.2f}]; backtest "
      f"{rob['shifted_backtest']['strategy_real_cagr_pct']:.2f}% vs {rob['shifted_backtest']['buyhold_real_cagr_pct']:.2f}%")
print(f"Nominal: gap {rob['nominal']['gap_mean_pts']:.2f}")
print(win6.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
print(mav[["month", "mean_real_pct", "ci_lo", "ci_hi", "median_real_pct", "share_positive_pct", "mean_real_pct_1871_2001", "mean_real_pct_2002_2026"]]
      .to_string(index=False, float_format=lambda v: f"{v:.2f}"))
print(f"September minus other months: {sep_diff:.2f} pts {summary['september_diff_ci']}; January: {summary['january_minus_other_months_pts']:.2f} {summary['january_diff_ci']}")

# 9. Tool data ------------------------------------------------------------------------------------------
if JS:
    enc = lambda a, s: ",".join(str(int(round(v * s))) for v in a)
    js = ("/* Sell in May backtester data, generated by data/sell-in-may-analysis.py (Truth with Data, Nov 2026).\n"
          "   Monthly from " + FIRST + " to " + LAST + ". s = S&P Composite total return (Shiller, monthly averages) x 1e5;\n"
          "   c = cash return (NBER commercial paper before 1934, 3-month T-bill after) x 1e6; i = CPI inflation x 1e6. */\n"
          "var SIM_DATA = {\"start\":\"" + FIRST + "\",\"end\":\"" + LAST + "\",\n"
          "\"s\":[" + enc(m.stock_tr, 1e5) + "],\n\"c\":[" + enc(m.cash, 1e6) + "],\n\"i\":[" + enc(m.inflation, 1e6) + "]};\n")
    with open(JS, "w") as f:
        f.write(js)
    print("wrote", JS, len(js), "bytes")
