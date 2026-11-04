#!/usr/bin/env python3
"""Charts for 'Which programming language is genuinely growing?' (Truth with Data, Nov 2026).
Usage: python3 charts.py CHART_DIR [LOGO_PNG]
Reads data/inputs and data/processed (run analysis.py first). House style matches the site:
Inter, #0f172a ink, #64748b secondary, #e2e8f0 grid."""
import json
import os
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D

HERE = Path(__file__).parent
RAW, OUT = HERE / "data/inputs", HERE / "data/processed"
CH = Path(sys.argv[1] if len(sys.argv) > 1 else "charts")
LOGO = sys.argv[2] if len(sys.argv) > 2 else None
CH.mkdir(parents=True, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY, GREEN, RED = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8", "#059669", "#dc2626"
VCOL = {"Genuinely growing": GREEN, "Quiet workhorse": BLUE, "Hype": AMBER, "Fading": GREY}
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC = ("Sources: GitHub Innovation Graph; Stack Overflow Developer Survey; Hacker News 'Who is hiring?'; "
       "Google Trends. Analysis: truthwithdata.com")
summ = json.loads((OUT / "summary.json").read_text())
sig = pd.read_csv(OUT / "momentum-by-language-and-country.csv")
W = sig[sig.geo == "WORLD"].set_index("language")
pct = lambda v: 100 * (np.exp(v) - 1)


def frame(fig, title, subtitle, source=SRC, top=0.83, bottom=0.11, left=0.08, right=0.97):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    W_, H_ = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / W_, 1 - 29 / H_, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / W_, 1 - 50 / H_, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / W_, 12 / H_, source, fontsize=8.5, color=MUTED)


def save(fig, name, alt):
    path = CH / name
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    s = path.read_text().replace("<svg ", f'<svg role="img" aria-label="{alt}" ', 1)
    path.write_text(s)


# 1. Hype vs hiring quadrant ---------------------------------------------------------
d = W[W.verdict != "Not enough data"].copy()
d["x"], d["y"] = pct(d.attention), pct(d.demand)
fig, ax = plt.subplots(figsize=(12.4, 8.2))
xmax = np.ceil(max(abs(d.x).max(), 10) / 10) * 10 + 12
ymax = np.ceil(max(abs(d.y).max(), 10) / 10) * 10 + 8
ax.set_xlim(-xmax, xmax); ax.set_ylim(-ymax, ymax)
for (x0, x1, y0, y1, c) in [(0, xmax, 0, ymax, GREEN), (-xmax, 0, 0, ymax, BLUE), (0, xmax, -ymax, 0, AMBER), (-xmax, 0, -ymax, 0, GREY)]:
    ax.fill_between([x0, x1], y0, y1, color=c, alpha=0.06, lw=0)
ax.axhline(0, color=GREY, lw=1); ax.axvline(0, color=GREY, lw=1)
qlab = [("GENUINELY GROWING", "more use, more hiring, more interest", xmax - 1, 2, "right", "bottom", GREEN),
        ("QUIET WORKHORSE", "more use and hiring, less buzz", -xmax + 1, ymax - 2, "left", "top", BLUE),
        ("HYPE", "more buzz, less use and hiring", xmax - 1, -2, "right", "top", AMBER),
        ("FADING", "losing ground on both counts", -xmax + 1, -ymax + 2, "left", "bottom", "#475569")]
for t, s_, x, y, ha, va, c in qlab:
    ax.text(x, y, t + "\n" + s_, ha=ha, va=va, fontsize=9.5, color=c, fontweight=600, linespacing=1.35)
size = lambda p: 60 + 2400 * np.sqrt(p / 4.81e6)
SIDE = {"JavaScript": "l", "Python": "r", "TypeScript": "r", "SQL": "r", "C++": "r", "Go": "t", "Swift": "r", "Kotlin": "b",
        "Java": "r", "C#": "l", "Dart": "b", "Scala": "l", "Ruby": "b", "R": "r", "PHP": "r", "Rust": "l"}
for L, r in d.iterrows():
    c = VCOL[r.verdict]
    if np.isfinite(r.pushers_after):
        sz = size(r.pushers_after)
        ax.scatter(r.x, r.y, s=sz, color=c, alpha=0.55, edgecolor=c, linewidth=1.5, zorder=3)
    else:
        sz = 160
        ax.scatter(r.x, r.y, s=sz, facecolor="white", edgecolor=c, linewidth=2, zorder=3)
    rad = np.sqrt(sz / np.pi) + 4
    side = SIDE.get(L, "r")
    dx, dy, ha, va = {"r": (rad, 0, "left", "center"), "l": (-rad, 0, "right", "center"),
                      "t": (0, rad, "center", "bottom"), "b": (0, -rad, "center", "top")}[side]
    ax.annotate(L, (r.x, r.y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                fontsize=10.5, fontweight=700, color=INK, zorder=4)
ax.set_xlabel("Attention: change in share of 'want to learn' votes and Google searches  (%)")
ax.set_ylabel("Real demand: change in share of GitHub developers and job posts  (%)")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%" if v else "0")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%" if v else "0")
frame(fig, "Rust, TypeScript and Python are gaining real ground. Most of the rest are not",
      "Change in each language's share of four signals, the 12 months to Oct 2022 vs the 12 months to Oct 2026 (GitHub: mid-2022 vs mid-2026).\n"
      "Shares, not counts: above zero means pulling ahead of the other 15. Bubble size = developers on GitHub; hollow = no GitHub measure.", top=0.86, bottom=0.12, left=0.09)
grow = ", ".join(d[d.verdict == "Genuinely growing"].index)
save(fig, "programming-languages-hype-vs-hiring-quadrant-2026.svg",
     f"Bubble chart of 16 programming languages by change in attention (x axis) and change in real demand (y axis), 2022 to 2026. "
     f"Genuinely growing: {grow}. TypeScript is a quiet workhorse: much more use and hiring, slightly less buzz. "
     f"C++ and PHP sit in the hype quadrant. Java, C#, Ruby, Scala, Go, Kotlin, Dart, R, Swift and JavaScript are losing ground.")

# 2. Signal heatmap ------------------------------------------------------------------
d = W[W.verdict != "Not enough data"].sort_values("momentum", ascending=False)
cols = [("usage", "Developers\npushing code\n(GitHub)"), ("hiring", "Job posts\nmentioning it\n(HN hiring)"),
        ("learning", "Want to\nlearn it\n(SO survey)"), ("interest", "Google\nsearches\n(Trends)")]
M = np.array([[pct(d.loc[L, c]) if np.isfinite(d.loc[L, c]) else np.nan for c, _ in cols] for L in d.index])
cmap = LinearSegmentedColormap.from_list("gr", ["#b91c1c", "#fca5a5", "#f8fafc", "#6ee7b7", "#047857"])
norm = TwoSlopeNorm(vmin=-75, vcenter=0, vmax=110)
fig, ax = plt.subplots(figsize=(10.4, 9.6))
ax.imshow(np.where(np.isnan(M), 0, M), cmap=cmap, norm=norm, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M[i, j]
        if np.isnan(v):
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="#f1f5f9", edgecolor="white", lw=2))
            ax.text(j, i, "n/a", ha="center", va="center", fontsize=9, color=GREY)
        else:
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="white", lw=2))
            ax.text(j, i, f"{v:+.0f}%", ha="center", va="center", fontsize=10.5, fontweight=600,
                    color="white" if abs(v) > 55 else INK)
for i, L in enumerate(d.index):
    v = d.loc[L, "verdict"]
    ax.text(3.65, i, v, ha="left", va="center", fontsize=10, fontweight=600, color=VCOL[v])
ax.set_xticks(range(4), [c[1] for c in cols], fontsize=9.5, color=INK)
ax.xaxis.tick_top(); ax.tick_params(length=0)
ax.set_yticks(range(len(d)), [f"{int(d.loc[L, 'rank'])}. {L}" for L in d.index], fontsize=10.5)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_xlim(-0.5, 5.1)
ax.text(3.65, -0.95, "Verdict", ha="left", va="bottom", fontsize=9.5, color=INK)
frame(fig, "Four signals, one scoreboard",
      "Change in each language's share of each signal, 2022 to 2026. Ranked by momentum score (average of the four, standardised).\n"
      "n/a: too few searches to measure reliably (Google Trends), or no GitHub measure (SQL).",
      top=0.80, bottom=0.05, left=0.17, right=0.99)
save(fig, "programming-languages-four-signals-heatmap-2026.svg",
     "Heatmap of 16 programming languages by four signals, 2022 to 2026. Rust is up on every measured signal, "
     f"GitHub share +{pct(W.loc['Rust','usage']):.0f}%, job-post share +{pct(W.loc['Rust','hiring']):.0f}%. "
     f"TypeScript GitHub share +{pct(W.loc['TypeScript','usage']):.0f}%. Java GitHub share {pct(W.loc['Java','usage']):.0f}% "
     f"and job-post share {pct(W.loc['Java','hiring']):.0f}%.")

# 3. Stack Overflow collapse ---------------------------------------------------------
q = pd.read_csv(RAW / "stackoverflow-questions-quarterly.csv")
fig, ax = plt.subplots(figsize=(12.4, 6.6))
x = np.arange(len(q))
ax.fill_between(x, q.questions / 1000, color=BLUE, alpha=0.12, lw=0)
ax.plot(x, q.questions / 1000, color=BLUE, lw=2.6)
ci = q.index[q.quarter == "2022Q4"][0]
ax.axvline(ci, color=AMBER, lw=1.4, ls=(0, (3, 3)))
ax.text(ci + 0.3, 520, "ChatGPT launches\n30 Nov 2022", color=AMBER, fontsize=9.5, fontweight=600, va="top")
for k in ["2019Q1", "2022Q3", "2024Q3", "2026Q3"]:
    i = q.index[q.quarter == k][0]; v = q.questions[i]
    ax.scatter([i], [v / 1000], s=40, color=BLUE, zorder=3)
    ax.text(i, v / 1000 + 22, f"{v / 1000:,.0f}k" if v >= 10000 else f"{v:,}", ha="center", fontsize=9.5, fontweight=700, color=INK)
ax.set_xticks(x[::4], [s[:4] for s in q.quarter[::4]])
ax.set_ylim(0, 600); ax.set_xlim(-0.5, len(q) - 0.3)
ax.set_ylabel("New questions per quarter (thousands)")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
so = summ["so_questions_jan_oct"]
frame(fig, f"Stack Overflow questions are down {summ['so_questions_fall_2019_2026_pct']:.0f}%. Rankings built on them are broken",
      f"New questions asked on Stack Overflow each quarter. January-October 2026: {so['y2026']:,} questions, against {so['y2019']:,} in the same months of 2019.\n"
      "Developers now ask AI assistants instead, so a language's share of Stack Overflow traffic no longer tracks how much it is used.",
      source="Source: Stack Exchange API (questions created per quarter, to Sep 2026). Analysis: truthwithdata.com", top=0.80)
save(fig, "stack-overflow-questions-collapse-2019-2026.svg",
     f"Line chart of new Stack Overflow questions per quarter: about {q.questions[0]/1000:.0f} thousand in early 2019, "
     f"falling from late 2022 to {q.questions.iloc[-1]:,} in the third quarter of 2026, a {summ['so_questions_fall_2019_2026_pct']:.0f}% fall comparing January to October.")

# 4. GitHub rank bump chart -----------------------------------------------------------
g = pd.read_csv(OUT / "github-share-quarterly.csv")
g = g[(g.geo == "WORLD") & (g.quarter == 2)].pivot(index="year", columns="language", values="share")
show = ["JavaScript", "Python", "TypeScript", "Shell", "Java", "C++", "C", "PHP", "C#", "Kotlin", "Ruby", "Swift", "Go", "Rust", "Dart"]
rk = g[show].rank(axis=1, ascending=False)
fig, ax = plt.subplots(figsize=(12.4, 8.0))
hi = {"TypeScript": GREEN, "Python": GREEN, "Rust": GREEN, "Java": RED, "Ruby": RED}
yrs = rk.index.values
for L in show:
    c = hi.get(L, "#cbd5e1"); lw = 3.4 if L in hi else 2
    ax.plot(yrs, rk[L], color=c, lw=lw, zorder=3 if L in hi else 2, solid_capstyle="round")
    ax.scatter(yrs, rk[L], s=46 if L in hi else 26, color=c, zorder=4, edgecolor="white", linewidth=1.2)
    ax.text(yrs[0] - 0.15, rk[L].iloc[0], f"{L}  {int(rk[L].iloc[0])}", ha="right", va="center", fontsize=10,
            color=INK if L in hi else MUTED, fontweight=700 if L in hi else 400)
    ax.text(yrs[-1] + 0.15, rk[L].iloc[-1], f"{int(rk[L].iloc[-1])}  {L}   {100 * g[L].iloc[-1]:.1f}%", ha="left", va="center",
            fontsize=10, color=INK if L in hi else MUTED, fontweight=700 if L in hi else 400)
ax.invert_yaxis(); ax.set_yticks([])
ax.set_xticks(yrs, [str(y) for y in yrs]); ax.set_xlim(yrs[0] - 1.25, yrs[-1] + 1.6)
for s in ["left", "bottom"]:
    ax.spines[s].set_visible(False)
ax.tick_params(axis="x", length=0)
ax.text(yrs[-1] + 1.0, 0.1, "share of\ndevelopers", ha="center", va="bottom", fontsize=8.5, color=MUTED)
frame(fig, "TypeScript climbed from 9th to 3rd on GitHub; Java slid from 4th to 5th",
      "Rank of each language by the number of developers pushing code in it on GitHub, worldwide, April-June each year.\n"
      "Right: share of all developer-language pairs in Q2 2026. Every language gained developers; ranks show who gained fastest.",
      source="Source: GitHub Innovation Graph (unique pushers per economy and language, CC0). Analysis: truthwithdata.com",
      top=0.85, bottom=0.07, left=0.03, right=0.99)
save(fig, "github-language-rank-bump-chart-2020-2026.svg",
     "Bump chart of GitHub language ranks 2020 to 2026. JavaScript stays first and Python second. TypeScript rises from 9th to 3rd. "
     "Rust rises from 15th to 14th of the 15 shown. Java falls from 4th to 5th, Ruby from 5th to 12th.")

# 5. Hiring: HN job-post share ---------------------------------------------------------
h = pd.read_csv(OUT / "hn-share-by-year.csv", index_col=0).loc[2015:2026]
fig, ax = plt.subplots(figsize=(12.4, 6.8))
lines = {"Python": GREEN, "TypeScript": BLUE, "JavaScript": "#7c3aed", "SQL": GREY, "Rust": AMBER, "Go": "#0891b2", "Ruby": RED, "Java": "#be123c"}
ends = []
for L, c in lines.items():
    ax.plot(h.index, h[L], color=c, lw=2.6 if L in ("Python", "TypeScript", "Rust", "Java") else 1.8)
    ends.append([L, h[L].iloc[-1], c])
ends.sort(key=lambda e: -e[1])
ypos = []
for L, v, c in ends:            # nudge labels apart
    y = v
    while any(abs(y - p) < 1.15 for p in ypos):
        y -= 1.15
    ypos.append(y)
    ax.text(2026.25, y, f"{L} {v:.0f}%", va="center", fontsize=10, fontweight=700, color=c)
ax.axvspan(2022.9, 2026.05, color=AMBER, alpha=0.06, lw=0)
ax.text(2023.0, 39, "after ChatGPT", color=AMBER, fontsize=9, fontweight=600)
ax.set_xlim(2015, 2027.6); ax.set_ylim(0, 41)
ax.set_xticks(range(2015, 2027, 1), [str(y) if y % 2 == 0 else "" for y in range(2015, 2027)])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_ylabel("Share of job posts mentioning the language")
frame(fig, "In job posts, TypeScript overtook JavaScript in 2023 and Python leads again",
      f"Share of Hacker News 'Who is hiring?' posts naming each language, by year ({int(h.posts.sum()):,} posts, Jan 2015-Nov 2026; 2026 = Jan-Nov).\n"
      "A startup- and US-heavy sample of employers, but the only free hiring record that goes back a decade.",
      source="Source: Hacker News 'Who is hiring?' threads via the Algolia HN API; counts of posts by keyword. Analysis: truthwithdata.com",
      top=0.84, right=0.98)
save(fig, "hn-hiring-posts-by-language-2015-2026.svg",
     f"Line chart of the share of Hacker News hiring posts naming each language, 2015 to 2026. TypeScript rose from under 1% to {h.TypeScript.iloc[-1]:.0f}%, "
     f"passing JavaScript ({h.JavaScript.iloc[-1]:.0f}%) in 2023. Python {h.Python.iloc[-1]:.0f}%. Rust rose to {h.Rust.iloc[-1]:.0f}%. "
     f"Ruby fell from {h.Ruby.iloc[0]:.0f}% to {h.Ruby.iloc[-1]:.0f}% and Java from {h.Java.iloc[0]:.0f}% to {h.Java.iloc[-1]:.1f}%.")

# 6. UK vs US vs India: GitHub share before/after ------------------------------------
langs6 = ["Python", "TypeScript", "JavaScript", "Java", "C#", "C++", "Go", "Rust", "Kotlin", "Swift", "PHP", "Ruby"]
geos = [("GB", "UK"), ("US", "US"), ("IN", "India")]
fig, axes = plt.subplots(1, 3, figsize=(12.4, 7.6), sharey=True)
for ax, (gc, gn) in zip(axes, geos):
    s = sig[sig.geo == gc].set_index("language").loc[langs6]
    y = np.arange(len(langs6))[::-1]
    for yi, L in zip(y, langs6):
        a, b = 100 * s.loc[L, "share_before"], 100 * s.loc[L, "share_after"]
        c = GREEN if b > a else RED
        ax.plot([a, b], [yi, yi], color=c, lw=2.4, alpha=0.8)
        ax.scatter([a], [yi], s=34, color=GREY, zorder=3)
        ax.scatter([b], [yi], s=58, color=c, zorder=3, edgecolor="white", linewidth=1)
        ax.text(max(a, b) + 0.6, yi, f"{100 * (b / a - 1):+.0f}%", va="center", fontsize=9, color=c, fontweight=600)
    ax.set_title(gn, fontsize=13, fontweight=700, color=INK, loc="left")
    ax.set_xlim(0, 29); ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
axes[0].set_yticks(np.arange(len(langs6))[::-1], langs6)
axes[1].set_xlabel("Share of developer-language pairs on GitHub (grey: mid-2022, coloured: mid-2026)")
frame(fig, "TypeScript's surge is biggest in India; Java is losing share everywhere",
      "Each language's share of developers pushing code on GitHub, Q3 2021-Q2 2022 vs Q3 2025-Q2 2026, by country of the developer.",
      source="Source: GitHub Innovation Graph (CC0). Analysis: truthwithdata.com", top=0.84, bottom=0.12, left=0.09)
fig.subplots_adjust(wspace=0.12)
s_in, s_gb, s_us = (sig[sig.geo == g].set_index("language") for g in ["IN", "GB", "US"])
save(fig, "github-language-share-uk-us-india-2022-2026.svg",
     f"Dumbbell charts of GitHub language share in the UK, US and India, mid-2022 vs mid-2026. TypeScript's share rose "
     f"{100*(s_gb.loc['TypeScript','share_after']/s_gb.loc['TypeScript','share_before']-1):.0f}% in the UK, "
     f"{100*(s_us.loc['TypeScript','share_after']/s_us.loc['TypeScript','share_before']-1):.0f}% in the US and "
     f"{100*(s_in.loc['TypeScript','share_after']/s_in.loc['TypeScript','share_before']-1):.0f}% in India. "
     f"Java's share fell in all three.")

# 7. Forecast 2028 ---------------------------------------------------------------------
fc = pd.read_csv(OUT / "forecast-2028-relative-usage.csv")
fc = fc[fc.used_2026 >= 4].sort_values("rel_growth_pct")
bt = summ["backtest"]
fig, ax = plt.subplots(figsize=(12.4, 7.6))
y = np.arange(len(fc))
for yi, (_, r) in zip(y, fc.iterrows()):
    c = GREEN if r.p_gain >= 0.7 else (RED if r.p_gain <= 0.3 else GREY)
    ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=7, alpha=0.22, solid_capstyle="round")
    ax.scatter([r.rel_growth_pct], [yi], s=80, color=c, zorder=3, edgecolor="white", linewidth=1.4)
    ax.text(r.hi + 2, yi, f"{r.rel_growth_pct:+.0f}%   ({100 * r.p_gain:.0f}% chance of gaining)", va="center", fontsize=9.5, color=c if c != GREY else MUTED,
            fontweight=600)
ax.axvline(0, color=INK, lw=1)
ax.set_yticks(y, fc.language)
ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%" if v else "0")
ax.set_xlim(-45, 100)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("Forecast change in share of developers using it, 2026 to 2028, relative to the average language (80% interval)")
frame(fig, "Where the next two years point: Rust and Go up, JavaScript, Java and PHP down",
      f"Forecast from the 2026 survey's gap between 'want to use' and 'use now'. Back-tested on 2017-2024: the gap called the direction\n"
      f"of the next two years correctly {100 * bt['oos_mean_hit_rate']:.0f}% of the time out of sample, and ranked languages better than chance in all {bt['oos_years']} years. Languages used by 4%+ of developers.",
      source="Source: Stack Overflow Developer Survey 2017-2026 (ODbL). Model and analysis: truthwithdata.com",
      top=0.84, bottom=0.12, left=0.1)
top2 = fc.sort_values("rel_growth_pct", ascending=False).head(2)
save(fig, "programming-language-forecast-2028.svg",
     "Forecast chart: change in share of developers using each language from 2026 to 2028, relative to the average language. "
     + "; ".join(f"{r.language} {r.rel_growth_pct:+.0f}%" for _, r in fc.sort_values('rel_growth_pct', ascending=False).iterrows()) + ".")

# 8. Skills in job posts: 2022 vs 2026 -----------------------------------------------
sk = pd.read_csv(RAW / "hn-whos-hiring-skill-mentions-by-year.csv").set_index("year")
skills = [c for c in sk.columns if c not in ("posts", "Remote")]
sh = sk[skills].div(sk.posts, axis=0) * 100
d = pd.DataFrame({"y2022": sh.loc[2022], "y2026": sh.loc[2026]}).sort_values("y2026")
fig, ax = plt.subplots(figsize=(12.4, 7.2))
y = np.arange(len(d))
for yi, (k, r) in zip(y, d.iterrows()):
    ch = r.y2026 - r.y2022
    c = GREEN if (ch >= 0.5 and r.y2026 > r.y2022 * 1.1) else (RED if (ch <= -0.5 and r.y2026 < r.y2022 * 0.9) else GREY)
    ax.plot([r.y2022, r.y2026], [yi, yi], color=c, lw=2.6, alpha=0.8)
    ax.scatter([r.y2022], [yi], s=40, color=GREY, zorder=3)
    ax.scatter([r.y2026], [yi], s=70, color=c, zorder=3, edgecolor="white", linewidth=1.2)
    ax.text(max(r.y2022, r.y2026) + 0.6, yi, f"{r.y2022:.1f}% \u2192 {r.y2026:.1f}%", va="center", fontsize=9.5,
            color=c if c != GREY else MUTED, fontweight=600)
ax.set_yticks(y, d.index); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%"); ax.set_xlim(0, 33)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("Share of Hacker News 'Who is hiring?' posts mentioning the skill (grey: 2022, coloured: 2026, Jan-Nov)")
frame(fig, "The fastest-rising skill in job posts isn't a language: it's building with AI",
      f"Posts mentioning LLMs or generative AI went from {sh.loc[2022, 'LLM / generative AI']:.1f}% in 2022 to {sh.loc[2026, 'LLM / generative AI']:.1f}% in 2026; 'agents' from {sh.loc[2022, 'AI agents']:.1f}% to {sh.loc[2026, 'AI agents']:.1f}%.\n"
      "Keyword counts in each post; 'agents' can occasionally mean something else (e.g. support agents).",
      source="Source: Hacker News 'Who is hiring?' threads via the Algolia HN API (7,582 posts in 2022, 3,110 in 2026). Analysis: truthwithdata.com",
      top=0.84, bottom=0.12, left=0.17)
save(fig, "hn-hiring-skills-ai-cloud-2022-2026.svg",
     "Dumbbell chart of skills mentioned in Hacker News hiring posts, 2022 vs 2026. " +
     "; ".join(f"{k} {r.y2022:.1f}% to {r.y2026:.1f}%" for k, r in d.sort_values("y2026", ascending=False).iterrows()) + ".")

# 8. Open Graph image 1200x630 PNG ----------------------------------------------------
fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor("white")
fig.text(0.05, 0.80, "Which programming language\nis genuinely growing?", fontsize=30, fontweight=800, color=INK, linespacing=1.15)
fig.text(0.05, 0.70, "We tested GitHub, job posts, a 10-year developer survey and Google searches", fontsize=14, color=MUTED)
fig.text(0.05, 0.50, "Rust · TypeScript · Python", fontsize=27, fontweight=800, color=GREEN)
fig.text(0.05, 0.43, "gaining real ground since 2022", fontsize=14, color=INK)
fig.text(0.05, 0.25, f"−{summ['so_questions_fall_2019_2026_pct']:.0f}%", fontsize=44, fontweight=800, color=AMBER)
fig.text(0.05, 0.18, "Stack Overflow questions since 2019", fontsize=14, color=INK)
fig.text(0.05, 0.06, "truthwithdata.com  ·  Language Momentum Checker inside", fontsize=13, color=MUTED)
d = W[W.verdict != "Not enough data"].sort_values("momentum").tail(10)
ax = fig.add_axes([0.66, 0.12, 0.30, 0.52])
ax.barh(range(len(d)), d.momentum, color=[VCOL[v] for v in d.verdict], height=0.65)
ax.set_yticks(range(len(d)), d.index, fontsize=10.5)
ax.axvline(0, color=GREY, lw=1)
ax.set_xlabel("Momentum score (top 10)", fontsize=10)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
if LOGO and os.path.exists(LOGO):
    img = plt.imread(LOGO)
    lx = fig.add_axes([0.855, 0.79, 0.12, 0.18]); lx.imshow(img); lx.axis("off")
fig.savefig(CH / "programming-languages-og-1200x630.png", dpi=100, facecolor="white")
plt.close(fig)
print("charts written to", CH)
