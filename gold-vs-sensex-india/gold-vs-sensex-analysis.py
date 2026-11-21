#!/usr/bin/env python3
"""Has gold beaten the Sensex for Indian investors? (Truth with Data, November 2026)

Usage: python gold-vs-sensex-analysis.py DATA_DIR [JS_OUT]
  DATA_DIR  folder holding india-gold-sensex-monthly-panel-1990-2026.csv (built by
            gold-vs-sensex-build-panel.py); all outputs are written there too.
  JS_OUT    optional path for the backtester's data file (js/gold-vs-sensex-data.js).

Method
  * Gold in rupees = World Bank monthly average gold price (US$/troy oz) x Fed monthly average
    rupees per dollar x 10 / 31.1034768, i.e. rupees per 10 grams at the international price.
    It excludes India's import duty and GST (see Limitations in the article).
  * Sensex = OECD MEI monthly average share-price index for India (2015 = 100), which follows
    the BSE Sensex. It is a price index: dividends are not included.
  * "Sensex with dividends" adds an assumed dividend yield of DIV a year, compounded monthly.
    BSE does not publish a long free total-return series, so this is an assumption, not data;
    we also report 0% and 1.5%.
  * CPI: OECD MEI consumer prices for India up to December 2013, chained to MOSPI's CPI
    (Combined, base 2012) from January 2014. Ends December 2025.
  * Main window: April 1993 (after the rupee became market-determined in March 1993) to
    October 2026. Every start month is used for the rolling windows, so windows overlap.
  * No costs or taxes for either asset.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

D = sys.argv[1]
JS = sys.argv[2] if len(sys.argv) > 2 else None
OZ = 31.1034768
DIV = 0.0125            # central dividend-yield assumption for the Sensex (a year)
START = "1993-04"
HORIZONS = [5, 10, 15, 20]
SHARES = [0, 10, 20, 30, 50, 100]   # gold share of a mixed portfolio, %

p = pd.read_csv(os.path.join(D, "india-gold-sensex-monthly-panel-1990-2026.csv"))
p["gold_inr_per_10g"] = p.gold_usd_per_oz * p.usd_inr * 10 / OZ
p["sensex_index"] = p.oecd_india_share_price_2015_100
k = p.index[p.date == "2014-01"][0]
ratio = p.mospi_cpi_combined_2012_100[k] / p.oecd_cpi_2015_100[k]
p["cpi"] = np.where(p.date >= "2014-01", p.mospi_cpi_combined_2012_100, p.oecd_cpi_2015_100 * ratio)

m = p[p.date >= START].reset_index(drop=True)
N = len(m)
t = np.arange(N)
G = m.gold_inr_per_10g.to_numpy()
S = m.sensex_index.to_numpy()


def tr(div):
    return S * (1 + div) ** (t / 12)


SD = tr(DIV)
CPI = m.cpi.to_numpy()
LAST = m.date.iloc[-1]
last_cpi = int(np.where(~np.isnan(CPI))[0].max())


def cagr(a, i, j):
    return (a[j] / a[i]) ** (12 / (j - i)) - 1


# 1. Panel with derived columns ---------------------------------------------------------------
out = p[["date", "usd_inr", "gold_usd_per_oz", "gold_inr_per_10g", "sensex_index", "cpi"]].copy()
out = out.rename(columns={"sensex_index": "sensex_price_index_2015_100", "cpi": "cpi_chained_2012_100"})
out.to_csv(os.path.join(D, "gold-vs-sensex-monthly-1990-2026.csv"), index=False, float_format="%.6g")

# 2. Trailing returns to the latest month -------------------------------------------------------
rows = []
for h in [1, 3, 5, 10, 15, 20, 25, 30, "since Apr 1993"]:
    n = N - 1 if isinstance(h, str) else 12 * h
    i, j = N - 1 - n, N - 1
    rows.append({"period": h if isinstance(h, str) else f"{h} year{'s' if h > 1 else ''}", "from": m.date[i], "to": m.date[j],
                 "gold_cagr_pct": 100 * cagr(G, i, j), "sensex_price_cagr_pct": 100 * cagr(S, i, j),
                 "sensex_with_dividends_cagr_pct": 100 * cagr(SD, i, j),
                 "winner_price_only": "Gold" if G[j] / G[i] > S[j] / S[i] else "Sensex",
                 "winner_with_dividends": "Gold" if G[j] / G[i] > SD[j] / SD[i] else "Sensex"})
trail = pd.DataFrame(rows)
trail.to_csv(os.path.join(D, "gold-vs-sensex-trailing-returns-2026-10.csv"), index=False, float_format="%.2f")

# 3. Rolling windows, every start month -----------------------------------------------------------
rows = []
for h in HORIZONS:
    n = 12 * h
    for i in range(N - n):
        j = i + n
        r = {"horizon_years": h, "start": m.date[i], "end": m.date[j],
             "gold_cagr_pct": 100 * cagr(G, i, j), "sensex_price_cagr_pct": 100 * cagr(S, i, j),
             "sensex_with_dividends_cagr_pct": 100 * cagr(SD, i, j)}
        if j <= last_cpi:
            infl = cagr(CPI, i, j)
            r["inflation_pct"] = 100 * infl
            r["gold_real_cagr_pct"] = 100 * ((1 + r["gold_cagr_pct"] / 100) / (1 + infl) - 1)
            r["sensex_with_dividends_real_cagr_pct"] = 100 * ((1 + r["sensex_with_dividends_cagr_pct"] / 100) / (1 + infl) - 1)
        rows.append(r)
roll = pd.DataFrame(rows)
roll.to_csv(os.path.join(D, "gold-vs-sensex-rolling-returns-1993-2026.csv"), index=False, float_format="%.3f")

rows = []
for h in HORIZONS:
    w = roll[roll.horizon_years == h]
    gap = w.gold_cagr_pct - w.sensex_with_dividends_cagr_pct
    alt = {}
    for d in (0.0, 0.015):
        sd = tr(d)
        alt[d] = np.mean([G[i + 12 * h] / G[i] > sd[i + 12 * h] / sd[i] for i in range(N - 12 * h)])
    rows.append({"horizon_years": h, "windows": len(w), "first_start": w.start.iloc[0], "last_start": w.start.iloc[-1],
                 "non_overlapping_windows": int((N - 1) // (12 * h)),
                 "gold_won_price_only_pct": 100 * alt[0.0],
                 "gold_won_vs_dividends_1_25_pct": 100 * (gap > 0).mean(),
                 "gold_won_vs_dividends_1_5_pct": 100 * alt[0.015],
                 "gold_median_cagr_pct": w.gold_cagr_pct.median(), "sensex_div_median_cagr_pct": w.sensex_with_dividends_cagr_pct.median(),
                 "gold_min_cagr_pct": w.gold_cagr_pct.min(), "gold_max_cagr_pct": w.gold_cagr_pct.max(),
                 "sensex_div_min_cagr_pct": w.sensex_with_dividends_cagr_pct.min(), "sensex_div_max_cagr_pct": w.sensex_with_dividends_cagr_pct.max(),
                 "median_gap_gold_minus_sensex_div_pts": gap.median(),
                 "gold_lost_to_inflation_pct": 100 * (w.gold_real_cagr_pct.dropna() < 0).mean(),
                 "sensex_div_lost_to_inflation_pct": 100 * (w.sensex_with_dividends_real_cagr_pct.dropna() < 0).mean()})
wins = pd.DataFrame(rows)
wins.to_csv(os.path.join(D, "gold-vs-sensex-win-rates.csv"), index=False, float_format="%.1f")

# Start-year view: which asset won the 10-year window starting in each April
dec = roll[(roll.horizon_years == 10) & (roll.start.str.endswith("-04"))][["start", "end", "gold_cagr_pct", "sensex_price_cagr_pct", "sensex_with_dividends_cagr_pct"]]

# 4. Risk -----------------------------------------------------------------------------------------
def risk(a, name):
    lr = np.diff(np.log(a))
    peak = np.maximum.accumulate(a)
    dd = a / peak - 1
    jt = int(dd.argmin())
    jp = int(np.argmax(a[:jt + 1]))
    rec = np.where(a[jt:] >= a[jp])[0]
    under, longest = 0, 0
    for x in dd:
        under = under + 1 if x < 0 else 0
        longest = max(longest, under)
    r12 = a[12:] / a[:-12] - 1
    return {"asset": name, "annualised_volatility_pct": 100 * lr.std(ddof=1) * np.sqrt(12),
            "max_drawdown_pct": 100 * dd.min(), "drawdown_peak": m.date[jp], "drawdown_trough": m.date[jt],
            "recovered": m.date[jt + rec[0]] if len(rec) else "not yet",
            "longest_below_previous_peak_months": longest, "worst_12m_return_pct": 100 * r12.min(),
            "share_of_12m_periods_negative_pct": 100 * (r12 < 0).mean()}


riskdf = pd.DataFrame([risk(G, "Gold (rupees)"), risk(S, "Sensex (price)"), risk(SD, "Sensex with 1.25% dividends")])
lg, ls_ = np.diff(np.log(G)), np.diff(np.log(S))
corr = float(np.corrcoef(lg, ls_)[0, 1])
c12 = float(np.corrcoef(np.log(G[12:] / G[:-12]), np.log(S[12:] / S[:-12]))[0, 1])
riskdf.to_csv(os.path.join(D, "gold-vs-sensex-risk-1993-2026.csv"), index=False, float_format="%.1f")

# 5. Mixed portfolios: lump sum with annual rebalancing, and monthly SIPs ------------------------------
def mix_index(w, i, j):
    """Value of 1 rupee put in at month i in a gold/Sensex(with dividends) mix, rebalanced every 12 months."""
    v = np.empty(j - i + 1)
    v[0] = 1.0
    hg, hs = w / G[i], (1 - w) / SD[i]
    for k in range(i + 1, j + 1):
        val = hg * G[k] + hs * SD[k]
        v[k - i] = val
        if (k - i) % 12 == 0:
            hg, hs = w * val / G[k], (1 - w) * val / SD[k]
    return v


def xirr_monthly(flows):
    """Annualised IRR of monthly cash flows (negative = paid in), by bisection."""
    def npv(r):
        mr = (1 + r) ** (1 / 12) - 1
        return sum(f / (1 + mr) ** k for k, f in enumerate(flows))
    lo, hi = -0.99, 2.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sip(w, i, n, amount=1.0):
    """Monthly SIP of `amount` for n months starting at month i, valued at month i+n. Rebalanced every 12 months."""
    hg = hs = 0.0
    for k in range(i, i + n):
        if k > i and (k - i) % 12 == 0:
            val = hg * G[k] + hs * SD[k]
            hg, hs = w * val / G[k], (1 - w) * val / SD[k]
        hg += w * amount / G[k]
        hs += (1 - w) * amount / SD[k]
    end = i + n
    val = hg * G[end] + hs * SD[end]
    flows = [-amount] * n + [val]
    return val, xirr_monthly(flows)


rows = []
for h in (10, 15):
    n = 12 * h
    for i in range(N - n):
        for s in SHARES:
            v = mix_index(s / 100, i, i + n)
            dd = (v / np.maximum.accumulate(v) - 1).min()
            val, irr = sip(s / 100, i, n)
            rows.append({"horizon_years": h, "start": m.date[i], "gold_share_pct": s,
                         "lump_sum_cagr_pct": 100 * (v[-1] ** (1 / h) - 1), "lump_sum_max_drawdown_pct": 100 * dd,
                         "sip_value_per_rupee_a_month": val, "sip_xirr_pct": 100 * irr})
mix = pd.DataFrame(rows)
mix.to_csv(os.path.join(D, "gold-vs-sensex-mix-and-sip-backtest.csv"), index=False, float_format="%.3f")

rows = []
for (h, s), w in mix.groupby(["horizon_years", "gold_share_pct"]):
    rows.append({"horizon_years": h, "gold_share_pct": s, "windows": len(w),
                 "lump_median_cagr_pct": w.lump_sum_cagr_pct.median(), "lump_worst_cagr_pct": w.lump_sum_cagr_pct.min(),
                 "lump_p10_cagr_pct": w.lump_sum_cagr_pct.quantile(0.1), "lump_median_max_drawdown_pct": w.lump_sum_max_drawdown_pct.median(),
                 "lump_worst_max_drawdown_pct": w.lump_sum_max_drawdown_pct.min(),
                 "sip_median_xirr_pct": w.sip_xirr_pct.median(), "sip_worst_xirr_pct": w.sip_xirr_pct.min(),
                 "sip_p10_xirr_pct": w.sip_xirr_pct.quantile(0.1), "sip_best_xirr_pct": w.sip_xirr_pct.max(),
                 "sip_worst_start": w.loc[w.sip_xirr_pct.idxmin(), "start"]})
mixsum = pd.DataFrame(rows)
mixsum.to_csv(os.path.join(D, "gold-vs-sensex-mix-summary.csv"), index=False, float_format="%.2f")

# 6. Real returns over the whole period (to the last CPI month) --------------------------------------
i0, j0 = 0, last_cpi
infl = cagr(CPI, i0, j0)
real = {"from": m.date[i0], "to": m.date[j0], "inflation_pct": 100 * infl,
        "gold_real_pct": 100 * ((1 + cagr(G, i0, j0)) / (1 + infl) - 1),
        "sensex_price_real_pct": 100 * ((1 + cagr(S, i0, j0)) / (1 + infl) - 1),
        "sensex_div_real_pct": 100 * ((1 + cagr(SD, i0, j0)) / (1 + infl) - 1)}

# 7. Summary --------------------------------------------------------------------------------------------
full = trail.iloc[-1]
summ = {"from": START, "to": LAST, "months": N, "div_assumption_pct": 100 * DIV,
        "gold_10g_start": G[0], "gold_10g_end": G[-1], "gold_multiple": G[-1] / G[0], "sensex_multiple": S[-1] / S[0],
        "sensexdiv_multiple": SD[-1] / SD[0],
        "full_gold_cagr": full.gold_cagr_pct, "full_sensex_cagr": full.sensex_price_cagr_pct, "full_sensexdiv_cagr": full.sensex_with_dividends_cagr_pct,
        "corr_monthly": corr, "corr_12m": c12, "real": real,
        "trailing": trail.to_dict("records"), "wins": wins.to_dict("records"),
        "risk": riskdf.to_dict("records"), "mix": mixsum.to_dict("records"), "decades": dec.to_dict("records")}
json.dump(summ, open(os.path.join(D, "gold-vs-sensex-summary.json"), "w"), indent=1, default=float)

# 8. Data for the in-browser backtester -------------------------------------------------------------------
if JS:
    js = {"asOf": f"{pd.Timestamp(LAST + '-01'):%B %Y}", "start": START,
          "gold": [round(float(x), 1) for x in G], "sensex": [round(float(x), 4) for x in S],
          "usdinr": [round(float(x), 4) for x in m.usd_inr],
          "cpi": [None if np.isnan(x) else round(float(x), 3) for x in CPI]}
    with open(JS, "w") as f:
        f.write("/* Gold vs Sensex SIP Backtester data, generated by data/gold-vs-sensex-analysis.py (Truth with Data, Nov 2026).\n"
                "   Monthly averages from April 1993. gold = rupees per 10 g at the international price (World Bank x Fed rupee rate);\n"
                "   sensex = OECD MEI share-price index for India (follows the BSE Sensex), 2015 = 100, price only;\n"
                "   cpi = OECD CPI to Dec 2013 chained to MOSPI CPI (Combined, 2012 = 100), null after the last release. */\n")
        f.write("var GVS_DATA = " + json.dumps(js, separators=(",", ":")) + ";\n")

# Console summary ----------------------------------------------------------------------------------------
pd.set_option("display.width", 200)
print(f"Panel {START} to {LAST}: {N} months")
print(f"Gold Rs/10g {G[0]:,.0f} -> {G[-1]:,.0f} (x{G[-1] / G[0]:.1f}); Sensex index x{S[-1] / S[0]:.1f}")
print(trail.round(2).to_string(index=False))
print(wins.round(1).to_string(index=False))
print(riskdf.round(1).to_string(index=False))
print(f"Correlation of monthly returns {corr:.2f}; of 12-month returns {c12:.2f}")
print(mixsum.round(2).to_string(index=False))
print("Real returns:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in real.items()})
print(dec.round(1).to_string(index=False))
