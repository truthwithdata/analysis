#!/usr/bin/env python3
"""Charts for the AI-written review detector case study (Truth with Data, Nov 2026).
Usage: python3 charts.py OUT_DIR CHART_DIR
Reads the CSVs written by analysis.py. Site house style."""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT, CH = sys.argv[1], sys.argv[2]
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8"
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC = ("Data: Salminen et al. (2022) Amazon and GPT-2 reviews; CRSD (Infinitode, 2026) chat-model reviews. "
       "Analysis: truthwithdata.com")


def frame(fig, title, subtitle, top=0.8, bottom=0.12, left=0.2, right=0.96):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    W, H = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / W, 1 - 29 / H, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / W, 1 - 50 / H, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / W, 12 / H, SRC, fontsize=8.5, color=MUTED)


def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    alt = alt.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{alt}" ', 1)
    open(path, "w").write(s)


# 1. A detector trained on 2019 fakes vs today's chat models ------------------------------
c = pd.read_csv(os.path.join(OUT, "ai-written-review-detector-legacy-vs-modern.csv"))
fig, ax = plt.subplots(figsize=(11, 5.6))
groups = ["trained on GPT-2 (2019)", "trained on modern chat models"]
labels = ["Detector trained on\n2019 GPT-2 fakes", "Detector trained on\nmodern chat models"]
w = 0.34
for gi, g in enumerate(groups):
    for ti, (test, col) in enumerate((("GPT-2 reviews", GREY), ("modern chat-model reviews", BLUE))):
        v = c[(c.trained == g) & (c.tested == test)].caught_at_1pct_fpr.iloc[0] * 100
        x = gi + (ti - 0.5) * w
        ax.bar(x, v, w * 0.92, color=col, zorder=2)
        ax.text(x, v + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=12, fontweight=700, color=INK)
ax.set_xticks([0, 1], labels, fontsize=11)
ax.set_ylim(0, 100)
ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_ylabel("AI reviews caught")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(axis="x", length=0)
ax.legend(handles=[Line2D([], [], marker="s", ls="", color=GREY, markersize=11, label="Tested on GPT-2 fakes"),
                   Line2D([], [], marker="s", ls="", color=BLUE, markersize=11, label="Tested on modern chat-model fakes")],
          loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=10, labelcolor=INK)
frame(fig, "A detector built for 2019's fake reviews catches almost none of today's",
      "Share of AI-written reviews flagged when the detector may wrongly flag only 1% of genuine reviews. Each detector is tested\n"
      "on reviews and generators it never saw in training, against the same unseen human reviews.", top=0.76, bottom=0.2, left=0.09)
v_old = c[(c.trained == groups[0]) & (c.tested == "modern chat-model reviews")].caught_at_1pct_fpr.iloc[0] * 100
v_new = c[(c.trained == groups[1]) & (c.tested == "modern chat-model reviews")].caught_at_1pct_fpr.iloc[0] * 100
save(fig, "ai-review-detector-2019-vs-modern-fakes.svg",
     f"Bar chart: a detector trained on 2019 GPT-2 fake reviews catches {v_old:.0f}% of modern chat-model reviews, "
     f"while one trained on modern chat models catches {v_new:.0f}%.")

# 2. Unseen generators -------------------------------------------------------------------
g = pd.read_csv(os.path.join(OUT, "ai-written-review-detector-by-generator.csv")).sort_values("logo_caught_at_1pct_fpr")
NAMES = {"Grok-4.1-Fast-Non-Reasoning": "Grok 4.1 Fast", "Llama-3-8b-T": "Llama 3 8B", "Mixtral-8x7b": "Mixtral 8x7B",
         "Gemini-2.0-Flash-Lite": "Gemini 2.0 Flash-Lite", "Gemini-1.5-Flash": "Gemini 1.5 Flash", "Gemini-3-Flash": "Gemini 3 Flash",
         "GPT-5.2-Instant": "GPT-5.2 Instant", "GPT-5-mini": "GPT-5 mini", "GPT-4o-Mini": "GPT-4o mini"}
fig, ax = plt.subplots(figsize=(11, 6.4))
y = np.arange(len(g))
seen, unseen = g.cv_caught_at_1pct_fpr * 100, g.logo_caught_at_1pct_fpr * 100
for yi, (a, b) in enumerate(zip(unseen, seen)):
    ax.plot([a, b], [yi, yi], color=GRID, lw=3, zorder=1)
ax.errorbar(unseen, y, xerr=[unseen - g.logo_caught_ci_low * 100, g.logo_caught_ci_high * 100 - unseen],
            fmt="none", ecolor=AMBER, elinewidth=1.2, capsize=3, zorder=2, alpha=0.7)
ax.scatter(seen, y, s=80, color=BLUE, zorder=3, edgecolor="white", linewidth=1.5, label="Model was in the training data")
ax.scatter(unseen, y, s=80, color=AMBER, marker="D", zorder=3, edgecolor="white", linewidth=1.5,
           label="Model was held out (a brand-new model to the detector), with 95% interval")
for yi, (a, b, n, lo) in enumerate(zip(unseen, seen, g.n_ai, g.logo_caught_ci_low * 100)):
    ax.text(min(lo, b) - 1.8, yi, f"{a:.0f}%", ha="right", va="center", fontsize=9.5, color=AMBER, fontweight=700)
    ax.text(max(a, b) + 2.5, yi, f"{b:.0f}%  (n={n:,})", ha="left", va="center", fontsize=9, color=MUTED)
ax.set_yticks(y, [NAMES.get(s, s) for s in g.generator])
ax.set_xlim(0, 118)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("AI reviews caught at a 1% false-flag rate")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.1), ncol=2, frameon=False, fontsize=9.5, labelcolor=INK)
frame(fig, "The newest chat models are the hardest to catch when the detector hasn't met them",
      "Share of each model's reviews flagged. Blue: the model's reviews were in training (5-fold cross-validation).\n"
      "Amber: trained on the other eight models only, so this one is new to the detector.", top=0.82, bottom=0.2, left=0.17)
save(fig, "ai-review-detector-unseen-models.svg",
     "Dot plot by chat model of AI reviews caught at a 1% false-flag rate: "
     + "; ".join(f"{NAMES.get(r.generator, r.generator)} {r.logo_caught_at_1pct_fpr*100:.0f}% when unseen, {r.cv_caught_at_1pct_fpr*100:.0f}% when seen"
                 for r in g.itertuples()))

# 3. The tells ---------------------------------------------------------------------------
t = pd.read_csv(os.path.join(OUT, "ai-written-review-detector-tells.csv"))
t["gap"] = t.pct_ai - t.pct_human
t = t.sort_values("gap")
fig, ax = plt.subplots(figsize=(11, 6.2))
y = np.arange(len(t))
for yi, (a, h) in enumerate(zip(t.pct_ai, t.pct_human)):
    ax.plot([a, h], [yi, yi], color=GRID, lw=3, zorder=1)
ax.scatter(t.pct_human, y, s=85, color=GREY, zorder=3, edgecolor="white", linewidth=1.5, label="Human reviews")
ax.scatter(t.pct_ai, y, s=85, color=BLUE, zorder=3, edgecolor="white", linewidth=1.5, label="AI-written reviews")
for yi, (a, h) in enumerate(zip(t.pct_ai, t.pct_human)):
    lo, hi = (a, h) if a < h else (h, a)
    ax.text(lo - 1.6, yi, f"{lo:.0f}%", ha="right", va="center", fontsize=9.5, color=BLUE if lo == a else MUTED, fontweight=700)
    ax.text(hi + 1.6, yi, f"{hi:.0f}%", ha="left", va="center", fontsize=9.5, color=BLUE if hi == a else MUTED, fontweight=700)
ax.set_yticks(y, t.tell)
ax.set_xlim(-6, 92)
ax.set_xticks([0, 20, 40, 60, 80], ["0%", "20%", "40%", "60%", "80%"])
ax.set_xlabel("Share of reviews")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.3, -0.1), ncol=2, frameon=False, fontsize=10, labelcolor=INK)
frame(fig, "AI writes tidy, complete sentences. People are messier",
      "Share of reviews showing each feature. Human and AI reviews matched on length and sentiment (4,018 of each).",
      top=0.85, bottom=0.2, left=0.4)
save(fig, "ai-review-detector-telltale-signs.svg",
     "Dot plot of telltale signs: " + "; ".join(f"{r.tell}: AI {r.pct_ai:.0f}%, human {r.pct_human:.0f}%" for r in t.itertuples()))
print("charts written to", CH)
