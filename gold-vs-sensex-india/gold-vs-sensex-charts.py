#!/usr/bin/env python3
"""Charts for 'Has gold beaten the Sensex for Indian investors?' (Truth with Data, Nov 2026).
Usage: python gold-vs-sensex-charts.py DATA_DIR CHART_DIR [LOGO_PNG]
Reads the CSVs written by gold-vs-sensex-analysis.py. House style matches the site's other charts:
Inter, #0f172a ink, #64748b secondary, #e2e8f0 grid; gold is amber #d97706, the Sensex blue #2563eb."""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

D, CH = sys.argv[1], sys.argv[2]
LOGO = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY, LIGHT, LBLUE = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8", "#fde68a", "#93c5fd"
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC = ("Sources: World Bank Pink Sheet (gold, US$/oz); US Federal Reserve via FRED (rupees per dollar); OECD Main Economic Indicators "
       "via FRED\n(India share prices, follows the BSE Sensex); MOSPI and OECD (CPI). Analysis: truthwithdata.com")
S = json.load(open(os.path.join(D, "gold-vs-sensex-summary.json")))
mo = pd.read_csv(os.path.join(D, "gold-vs-sensex-monthly-1990-2026.csv"))
mo = mo[mo.date >= S["from"]].reset_index(drop=True)
mo["d"] = pd.to_datetime(mo.date + "-01")
t = np.arange(len(mo))
div = S["div_assumption_pct"] / 100
mo["g100"] = 100 * mo.gold_inr_per_10g / mo.gold_inr_per_10g[0]
mo["s100"] = 100 * mo.sensex_price_index_2015_100 / mo.sensex_price_index_2015_100[0]
mo["sd100"] = mo.s100 * (1 + div) ** (t / 12)
roll = pd.read_csv(os.path.join(D, "gold-vs-sensex-rolling-returns-1993-2026.csv"))
trail = pd.read_csv(os.path.join(D, "gold-vs-sensex-trailing-returns-2026-10.csv"))
wins = pd.read_csv(os.path.join(D, "gold-vs-sensex-win-rates.csv"))
mixs = pd.read_csv(os.path.join(D, "gold-vs-sensex-mix-summary.csv"))
LASTLAB = f"{pd.Timestamp(S['to'] + '-01'):%b %Y}"


def frame(fig, title, subtitle, source=SRC, top=0.8, bottom=0.15, left=0.08, right=0.97):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    w, h = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / w, 1 - 29 / h, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / w, 1 - 50 / h, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / w, 10 / h, source, fontsize=8.2, color=MUTED, va="bottom", linespacing=1.35)


def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{alt}" ', 1)
    open(path, "w").write(s)


def style(ax, axis="y"):
    (ax.yaxis if axis == "y" else ax.xaxis).grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    if axis == "y":
        ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)


# 1. Growth of Rs 100 -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12.4, 6.4))
ax.plot(mo.d, mo.g100, color=AMBER, lw=2.2, label="Gold (rupee price)")
ax.plot(mo.d, mo.sd100, color=BLUE, lw=2.2, label=f"Sensex with an assumed {S['div_assumption_pct']:.2f}% dividend yield")
ax.plot(mo.d, mo.s100, color=LBLUE, lw=1.6, label="Sensex, price only")
ax.set_yscale("log")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
ax.set_yticks([50, 100, 200, 500, 1000, 2000, 5000])
for col, c, dy in [("g100", AMBER, 6), ("sd100", BLUE, 8), ("s100", LBLUE, -16)]:
    v = mo[col].iloc[-1]
    ax.annotate(f"₹{v:,.0f}", (mo.d.iloc[-1], v), xytext=(6, dy), textcoords="offset points", fontsize=10, color=c, fontweight=700)
ax.set_xlim(mo.d.iloc[0], mo.d.iloc[-1] + pd.Timedelta(days=700))
ax.xaxis.set_major_locator(mdates.YearLocator(4)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.legend(loc="upper left", frameon=False, fontsize=10, labelcolor=INK)
ax.set_ylabel("Value of ₹100 invested in April 1993 (log scale)")
style(ax)
frame(fig, f"Over 33 years, gold and the Sensex finished close together; dividends give the Sensex the edge",
      f"Value of ₹100 put into each in April 1993, monthly averages to {LASTLAB}. Gold at the international price in rupees (before import duty and GST).\n"
      f"Gold {S['full_gold_cagr']:.1f}% a year; Sensex {S['full_sensex_cagr']:.1f}% price only, about {S['full_sensexdiv_cagr']:.1f}% with dividends. No costs or taxes.")
save(fig, "gold-vs-sensex-growth-of-100-rupees-1993-2026.svg",
     f"Line chart on a log scale. Rs 100 invested in April 1993 grew to about Rs {mo.g100.iloc[-1]:,.0f} in gold, Rs {mo.s100.iloc[-1]:,.0f} in the Sensex "
     f"price index and about Rs {mo.sd100.iloc[-1]:,.0f} with an assumed 1.25% dividend yield by {LASTLAB}. Gold led in the 1990s slump and after 2008 and 2019; "
     "the Sensex led from 2003 to 2008 and from 2014 to 2024.")

# 2. Rolling 10-year returns ---------------------------------------------------------------------------
r = roll[roll.horizon_years == 10].copy()
r["d"] = pd.to_datetime(r.start + "-01")
fig, ax = plt.subplots(figsize=(12.4, 6.2))
ax.fill_between(r.d, r.gold_cagr_pct, r.sensex_with_dividends_cagr_pct, where=r.gold_cagr_pct > r.sensex_with_dividends_cagr_pct,
                color=LIGHT, alpha=0.7, lw=0, interpolate=True, label="Gold ahead")
ax.fill_between(r.d, r.gold_cagr_pct, r.sensex_with_dividends_cagr_pct, where=r.gold_cagr_pct <= r.sensex_with_dividends_cagr_pct,
                color="#dbeafe", alpha=0.8, lw=0, interpolate=True, label="Sensex ahead")
ax.plot(r.d, r.gold_cagr_pct, color=AMBER, lw=2.2, label="Gold")
ax.plot(r.d, r.sensex_with_dividends_cagr_pct, color=BLUE, lw=2.2, label="Sensex with dividends (assumed 1.25%)")
ax.plot(r.d, r.sensex_price_cagr_pct, color=LBLUE, lw=1.2, ls=(0, (3, 2)), label="Sensex, price only")
ax.axhline(0, color=GREY, lw=0.8)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.set_ylabel("Annual return over the next 10 years")
ax.set_xlabel("Month the 10 years started")
ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.legend(loc="upper right", frameon=False, fontsize=9.5, labelcolor=INK, ncol=2)
w10 = wins[wins.horizon_years == 10].iloc[0]
style(ax)
frame(fig, "Gold won when you started near a stock-market peak: 10-year spells from 1999-2000, 2006-08 and 2015 onwards",
      f"Annualised return over each 10-year window, by start month (April 1993 to {pd.Timestamp(r.start.iloc[-1] + '-01'):%b %Y}, {int(w10.windows)} overlapping windows).\n"
      f"Gold beat the Sensex in {w10.gold_won_price_only_pct:.0f}% of windows on price alone and in {w10.gold_won_vs_dividends_1_25_pct:.0f}% once an assumed 1.25% dividend yield is added.")
save(fig, "gold-vs-sensex-rolling-10-year-returns-1993-2026.svg",
     f"Line chart of 10-year annualised returns by start month. Gold returned between {w10.gold_min_cagr_pct:.0f}% and {w10.gold_max_cagr_pct:.0f}% a year, "
     f"the Sensex with dividends between {w10.sensex_div_min_cagr_pct:.0f}% and {w10.sensex_div_max_cagr_pct:.0f}%. Gold was ahead in "
     f"{w10.gold_won_vs_dividends_1_25_pct:.0f}% of windows once dividends are included, mostly for starts around 1999-2000, 2006-2008, 2010 and since 2015.")

# 3. Returns by period ending in the latest month ---------------------------------------------------------------
tt = trail.copy()
lab = [p if p != "since Apr 1993" else "Since Apr 1993" for p in tt.period]
fig, ax = plt.subplots(figsize=(12.4, 6.2))
x = np.arange(len(tt)); bw = 0.27
ax.bar(x - bw, tt.gold_cagr_pct, bw, color=AMBER, label="Gold")
ax.bar(x, tt.sensex_with_dividends_cagr_pct, bw, color=BLUE, label="Sensex with dividends (assumed 1.25%)")
ax.bar(x + bw, tt.sensex_price_cagr_pct, bw, color=LBLUE, label="Sensex, price only")
for xi, row in zip(x, tt.itertuples()):
    ax.text(xi - bw, row.gold_cagr_pct + (0.8 if row.gold_cagr_pct >= 0 else -2.2), f"{row.gold_cagr_pct:.1f}", ha="center", fontsize=8.5, color=AMBER, fontweight=700)
    v = row.sensex_with_dividends_cagr_pct
    ax.text(xi, v + (0.8 if v >= 0 else -2.2), f"{v:.1f}", ha="center", fontsize=8.5, color=BLUE, fontweight=700)
ax.axhline(0, color=GREY, lw=0.8)
ax.set_xticks(x, [f"{l}\n{pd.Timestamp(f + '-01'):%b %Y}" for l, f in zip(lab, tt["from"])])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.set_ylabel(f"Annualised return to {LASTLAB}")
ax.legend(loc="upper right", frameon=False, fontsize=9.5, labelcolor=INK)
style(ax)
frame(fig, "Pick 3, 5, 10 or 20 years and gold wins easily; pick 15, 25 or 30 and dividends tip it to the Sensex",
      f"Annualised returns for periods ending in {LASTLAB} (monthly averages). The last year was unusual: the Sensex index fell {abs(tt.sensex_price_cagr_pct[0]):.0f}% while\n"
      "gold rose. That one year moves every 'gold vs Sensex' headline written this autumn.")
save(fig, "gold-vs-sensex-returns-by-period-to-2026-10.svg",
     f"Grouped bar chart of annualised returns to {LASTLAB}. Gold: " + ", ".join(f"{p} {g:.1f}%" for p, g in zip(tt.period, tt.gold_cagr_pct)) +
     ". Sensex with dividends: " + ", ".join(f"{p} {g:.1f}%" for p, g in zip(tt.period, tt.sensex_with_dividends_cagr_pct)) + ".")

# 4. Drawdowns --------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12.4, 5.6))
for col, c, name in [("g100", AMBER, "Gold"), ("sd100", BLUE, "Sensex with dividends")]:
    v = mo[col]
    dd = 100 * (v / v.cummax() - 1)
    ax.fill_between(mo.d, dd, 0, color=c, alpha=0.18, lw=0)
    ax.plot(mo.d, dd, color=c, lw=1.6, label=name)
    j = int(dd.idxmin())
    ax.annotate(f"{name}: {dd[j]:.0f}%\n{mo.d[j]:%b %Y}", (mo.d[j], dd[j]), xytext=(12, -4) if name != "Gold" else (-70, -105),
                textcoords="offset points", fontsize=9, color=c, arrowprops=dict(arrowstyle="-", color=GREY))
ax.set_ylim(-62, 3)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.set_ylabel("Below previous peak")
ax.xaxis.set_major_locator(mdates.YearLocator(4)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.legend(loc="lower left", frameon=False, fontsize=9.5, labelcolor=INK)
style(ax)
rk = pd.read_csv(os.path.join(D, "gold-vs-sensex-risk-1993-2026.csv"))
frame(fig, "The Sensex falls twice as hard; gold's slumps are shallower but can last longer",
      f"Distance below the previous high, monthly averages (which smooth out the worst days). Annualised volatility: gold {rk.annualised_volatility_pct[0]:.1f}%, "
      f"Sensex {rk.annualised_volatility_pct[1]:.1f}%.\nLongest spell below a previous high: gold {int(rk.longest_below_previous_peak_months[0])} months, the Sensex "
      f"{int(rk.longest_below_previous_peak_months[1])} months. Monthly returns are uncorrelated ({S['corr_monthly']:.2f}).",
      top=0.76, bottom=0.16)
save(fig, "gold-vs-sensex-drawdowns-1993-2026.svg",
     f"Area chart of drawdowns. The Sensex's worst fall was {rk.max_drawdown_pct[2]:.0f}% to March 2009; gold's was {rk.max_drawdown_pct[0]:.0f}% to July 1999. "
     f"Gold's longest spell below a previous high was {int(rk.longest_below_previous_peak_months[0])} months, the Sensex's {int(rk.longest_below_previous_peak_months[1])}.")

# 5. Does a slice of gold help a 10-year SIP? -------------------------------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(12.4, 5.8))
for ax, h in zip(axs, (10, 15)):
    q = mixs[mixs.horizon_years == h]
    y = np.arange(len(q))
    ax.hlines(y, q.sip_worst_xirr_pct, q.sip_best_xirr_pct, color=GRID, lw=6)
    ax.scatter(q.sip_worst_xirr_pct, y, color=INK, s=40, zorder=3, label="Worst start month")
    ax.scatter(q.sip_p10_xirr_pct, y, color=GREY, s=40, zorder=3, label="1 in 10 starts did worse than")
    ax.scatter(q.sip_median_xirr_pct, y, color=BLUE, s=60, zorder=3, label="Median")
    for yi, row in zip(y, q.itertuples()):
        ax.text(row.sip_worst_xirr_pct, yi + 0.28, f"{row.sip_worst_xirr_pct:.1f}", ha="center", fontsize=8.8, color=INK)
        ax.text(row.sip_median_xirr_pct, yi + 0.28, f"{row.sip_median_xirr_pct:.1f}", ha="center", fontsize=8.8, color=BLUE)
    ax.set_yticks(y, [f"{s}% gold" if s not in (0, 100) else ("All Sensex" if s == 0 else "All gold") for s in q.gold_share_pct])
    ax.invert_yaxis()
    ax.axvline(0, color=GREY, lw=0.8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("SIP return a year (XIRR)")
    ax.set_xlim(-4, 30) if h == 10 else ax.set_xlim(0, 20)
    ax.set_xticks(range(0, 31, 5) if h == 10 else range(0, 21, 5))
    ax.set_title(f"{h}-year monthly SIPs ({int(q.windows.iloc[0])} start months)", loc="left", fontsize=11.5, color=INK, fontweight=600)
    style(ax, "x"); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
axs[0].legend(loc="lower right", frameon=False, fontsize=8.8, labelcolor=INK)
frame(fig, "Adding 10-30% gold to a Sensex SIP lifted the worst outcomes without lowering the typical one",
      "Monthly SIPs started in every month from April 1993, rebalanced to the target mix once a year. Sensex includes an assumed 1.25% dividend yield.\n"
      "One past period, overlapping windows, no costs or taxes: a description of what happened, not a promise.",
      top=0.76, bottom=0.17, left=0.1, right=0.98)
q10 = mixs[mixs.horizon_years == 10].set_index("gold_share_pct")
save(fig, "gold-share-sip-outcomes-10-and-15-years.svg",
     f"Dot chart of SIP returns by gold share. For 10-year SIPs the worst start month returned {q10.sip_worst_xirr_pct[0]:.1f}% a year with no gold, "
     f"{q10.sip_worst_xirr_pct[20]:.1f}% with 20% gold and {q10.sip_worst_xirr_pct[100]:.1f}% in gold only; the median was {q10.sip_median_xirr_pct[0]:.1f}%, "
     f"{q10.sip_median_xirr_pct[20]:.1f}% and {q10.sip_median_xirr_pct[100]:.1f}%.")

# 6. Open Graph image 1200x630 PNG ----------------------------------------------------------------------------------
fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor("white")
fig.text(0.05, 0.86, "Has gold beaten the Sensex?", fontsize=30, fontweight=800, color=INK)
fig.text(0.05, 0.775, f"33 years of rupee returns, April 1993 to {LASTLAB}, with a free SIP backtester", fontsize=14.5, color=MUTED)
fig.text(0.05, 0.56, f"{S['full_gold_cagr']:.1f}%", fontsize=46, fontweight=800, color=AMBER)
fig.text(0.05, 0.47, "a year for gold since 1993", fontsize=15, color=INK)
fig.text(0.05, 0.30, f"{S['full_sensex_cagr']:.1f}% / {S['full_sensexdiv_cagr']:.1f}%", fontsize=46, fontweight=800, color=BLUE)
fig.text(0.05, 0.21, "Sensex, price only / with an assumed 1.25% dividend yield", fontsize=15, color=INK)
fig.text(0.05, 0.07, "truthwithdata.com  ·  Gold vs Sensex SIP Backtester inside", fontsize=13, color=MUTED)
ax = fig.add_axes([0.58, 0.14, 0.38, 0.52])
ax.plot(mo.d, mo.g100, color=AMBER, lw=2.2)
ax.plot(mo.d, mo.sd100, color=BLUE, lw=2.2)
ax.set_yscale("log"); ax.set_yticks([100, 300, 1000, 3000]); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
ax.set_title("₹100 invested in April 1993", loc="left", fontsize=11, color=INK)
ax.xaxis.set_major_locator(mdates.YearLocator(8)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
style(ax)
if LOGO and os.path.exists(LOGO):
    img = plt.imread(LOGO)
    lx = fig.add_axes([0.855, 0.79, 0.12, 0.18]); lx.imshow(img); lx.axis("off")
fig.savefig(os.path.join(CH, "gold-vs-sensex-og-1200x630.png"), dpi=100, facecolor="white")
plt.close(fig)
print("charts written to", CH)
