#!/usr/bin/env python3
"""Charts for 'Is crime really going up in the UK?' (Truth with Data, Nov 2026).
Usage: python uk-crime-charts.py DATA_DIR CHART_DIR [LOGO_PNG]
Reads the CSVs and summary JSON written by uk-crime-analysis.py. Writes the 'two clocks' poster as hand-built SVG
(wide and tall layouts) and four supporting charts with matplotlib. PNG exports are made separately
(see the README: Playwright renders the SVGs at 1200x630 and 1080x1350).
House style: Inter, #0f172a ink, #64748b secondary, #e2e8f0 grid; survey (CSEW) blue #2563eb, police amber #d97706;
rising #c2410c, falling #008a72 (always with an arrow and a number, never colour alone)."""
import base64
import io
import json
import os
import sys
from html import escape

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

D, CH = sys.argv[1], sys.argv[2]
LOGO = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, LBLUE, UP, DOWN, NEUTRAL = ("#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#93c5fd",
                                                           "#c2410c", "#008a72", "#94a3b8")
S = json.load(open(os.path.join(D, "uk-crime-summary.json")))
P = S["phases"]
clocks = pd.read_csv(os.path.join(D, "uk-crime-two-measures-1981-2026.csv"))
panel = pd.read_csv(os.path.join(D, "uk-crime-which-crimes-are-rising-2017-2026.csv"))
SRC = ("Source: ONS, Crime in England and Wales, year ending June 2026 (Crime Survey for England and Wales; police recorded "
       "crime); Home Office recorded crime 1898–2001/02. Analysis: truthwithdata.com")

# ------------------------------------------------------------------------------------------------------------
# Series for the poster: one point a year (March years, then the latest June year)
DROP = {"YE Jun 2025", "YE Mar 2026"}
cs = clocks[(clocks.measure.str.startswith("CSEW incidents, excl")) & ~clocks.period.isin(DROP)].sort_values("year")
cf = clocks[(clocks.measure.str.startswith("CSEW incidents, incl")) & ~clocks.period.isin(DROP)].sort_values("year")
po = clocks[clocks.measure.str.startswith("Police") & ~clocks.period.isin(DROP)].sort_values("year")
seg_police = [po[po.series == "Home Office, old counting rules"], po[po.series.str.contains("new counting")],
              po[po.series.str.startswith("ONS")]]
seg_csew = [cs[cs.year < 2021], cs[cs.year > 2021]]

SHORT = {"Theft from outside homes and other household theft": "Theft from outside homes",
         "Theft from the person (pickpocketing, snatches)": "Theft from the person",
         "Domestic / residential burglary": "Burglary of homes", "Computer misuse (hacking, viruses)": "Computer misuse"}


def cell(change, sigf, available=True):
    """(arrow, text, colour) for one survey/police cell."""
    if not available or pd.isna(change):
        return ("", "not measured", NEUTRAL)
    if sigf is False:
        return ("≈", f"{change:+.0f}%  no clear change", MUTED)
    return ("▲" if change > 0 else "▼", f"{change:+.0f}%", UP if change > 0 else DOWN)


rows = []
for _, r in panel.iterrows():
    sv = cell(r.csew_change_pct, bool(r.csew_significant) if pd.notna(r.csew_change_pct) else None)
    pv = cell(r.police_change_pct, None)
    rows.append((SHORT.get(r.offence, r.offence), sv, pv, r.police_base_period if pd.notna(r.police_base_period) else None))


def logo_href(width_px):
    if not (LOGO and os.path.exists(LOGO)):
        return None
    from PIL import Image
    im = Image.open(LOGO).convert("RGBA")
    h = int(im.height * width_px / im.width)
    im = im.resize((width_px, h), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), h


def poster(W, H, L, name):
    """L: layout dict (font sizes and boxes) so one function draws the wide and the tall poster."""
    o = []
    a = o.append
    title = "Two clocks, two stories: is crime rising in England and Wales?"
    desc = (f"Line chart, 1981 to 2026. The Crime Survey for England and Wales estimated {P['csew_1981']/1e3:.1f} million incidents "
            f"in 1981, peaked at {P['csew_peak_1995']/1e3:.1f} million in 1995 and fell to {P['csew_latest']/1e3:.2f} million in the "
            f"year to June 2026 ({P['csew_fall_1995_latest_pct']:.0f}%), excluding fraud and computer misuse. Police recorded crime "
            f"(excluding fraud) rose from {P['prc_1981']/1e6:.2f} million in 1981, fell to {P['prc_low']/1e6:.2f} million in 2013/14 "
            f"and rose to {P['prc_latest']/1e6:.2f} million ({P['prc_rise_2014_latest_pct']:+.0f}%) after recording was tightened. "
            "Below, a table of offences shows that fraud and theft from outside homes rose in the survey, while violence, robbery, "
            "burglary, vehicle and bicycle theft, criminal damage and computer misuse fell; police records of violence, robbery, "
            "shoplifting and theft from the person rose.")
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
      f'aria-labelledby="t-{name} d-{name}" font-family="Inter, \'Segoe UI\', Arial, sans-serif">')
    a(f'<title id="t-{name}">{escape(title)}</title><desc id="d-{name}">{escape(desc)}</desc>')
    a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    a(f'<rect width="{W}" height="{L["bar"]}" fill="{INK}"/>')
    a(f'<text x="{L["pad"]}" y="{L["bar"] * 0.68:.0f}" fill="#ffffff" font-size="{L["kicker"]}" font-weight="700" '
      f'letter-spacing="2">CRIME IN ENGLAND AND WALES · 1981–2026</text>')
    y = L["bar"] + L["h1"] * 1.25
    for line in L["headline"]:
        a(f'<text x="{L["pad"]}" y="{y:.0f}" fill="{INK}" font-size="{L["h1"]}" font-weight="800">{escape(line)}</text>')
        y += L["h1"] * 1.12
    y += L["sub"] * 0.2
    for line in L["subline"]:
        a(f'<text x="{L["pad"]}" y="{y:.0f}" fill="{MUTED}" font-size="{L["sub"]}">{line}</text>')
        y += L["sub"] * 1.3

    # --- main chart ---
    x0, x1, y0, y1 = L["chart"]  # left, right, top, bottom of plot area
    X = lambda yr: x0 + (yr - 1981) / (2026.6 - 1981) * (x1 - x0)  # noqa: E731
    YMAX = 21
    Y = lambda m: y1 - m / YMAX * (y1 - y0)  # noqa: E731
    fs = L["axis"]
    for m in range(0, 21, 5):
        a(f'<line x1="{x0}" x2="{x1}" y1="{Y(m):.1f}" y2="{Y(m):.1f}" stroke="{GRID}" stroke-width="1.5"/>')
        a(f'<text x="{x0 - 10}" y="{Y(m) + fs * 0.35:.1f}" fill="{MUTED}" font-size="{fs}" text-anchor="end">{m}m</text>')
    for yr in (1981, 1990, 2000, 2010, 2020, 2026):
        a(f'<text x="{X(yr + 0.5):.1f}" y="{y1 + fs * 1.4:.1f}" fill="{MUTED}" font-size="{fs}" text-anchor="middle">{yr}</text>')
    # pandemic gap and turning points
    a(f'<rect x="{X(2020.2):.1f}" y="{y0}" width="{X(2022.6) - X(2020.2):.1f}" height="{y1 - y0}" fill="#f1f5f9"/>')
    a(f'<text x="{X(2021.4):.1f}" y="{y0 + fs * 1.1:.1f}" fill="{MUTED}" font-size="{fs * 0.8:.0f}" text-anchor="middle">no</text>'
      f'<text x="{X(2021.4):.1f}" y="{y0 + fs * 2:.1f}" fill="{MUTED}" font-size="{fs * 0.8:.0f}" text-anchor="middle">survey</text>')
    for yr, lab, ly, anc in L["events"]:
        top = Y(ly) - L["ann"] * 0.9
        a(f'<line x1="{X(yr):.1f}" x2="{X(yr):.1f}" y1="{top:.1f}" y2="{y1}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="4 4"/>')
        dx = 6 if anc == "start" else -6
        for k, t in enumerate(lab):
            a(f'<text x="{X(yr) + dx:.1f}" y="{Y(ly) + k * L["ann"] * 1.15:.1f}" fill="{INK}" font-size="{L["ann"]}" '
              f'text-anchor="{anc}">{escape(t)}</text>')

    def path(df):
        return "M" + " L".join(f"{X(r.year):.1f},{Y(r.millions):.1f}" for r in df.itertuples())
    # survey area + lines
    for sg in seg_csew:
        pts = " L".join(f"{X(r.year):.1f},{Y(r.millions):.1f}" for r in sg.itertuples())
        a(f'<path d="M{X(sg.year.iloc[0]):.1f},{y1} L{pts} L{X(sg.year.iloc[-1]):.1f},{y1} Z" fill="{BLUE}" fill-opacity="0.10"/>')
        a(f'<path d="{path(sg)}" fill="none" stroke="{BLUE}" stroke-width="{L["lw"]}" stroke-linejoin="round" stroke-linecap="round"/>')
    a(f'<path d="{path(cf)}" fill="none" stroke="{BLUE}" stroke-width="{L["lw"] * 0.6:.1f}" stroke-dasharray="7 6" stroke-linecap="round"/>')
    for sg in seg_police:
        a(f'<path d="{path(sg)}" fill="none" stroke="{AMBER}" stroke-width="{L["lw"]}" stroke-linejoin="round" stroke-linecap="round"/>')
    # key points
    pk = cs[cs.period == "YE Dec 1995"].iloc[0]
    a(f'<circle cx="{X(pk.year):.1f}" cy="{Y(pk.millions):.1f}" r="{L["dot"]}" fill="{BLUE}" stroke="#fff" stroke-width="3"/>')
    a(f'<text x="{X(pk.year) + 14:.1f}" y="{Y(pk.millions) - 4:.1f}" fill="{INK}" font-size="{L["ann"]}" font-weight="700">'
      f'Survey peak, 1995: {pk.millions:.1f}m</text>')
    lo = po[po.period == P["prc_low_period"]].iloc[0]
    a(f'<circle cx="{X(lo.year):.1f}" cy="{Y(lo.millions):.1f}" r="{L["dot"]}" fill="{AMBER}" stroke="#fff" stroke-width="3"/>')
    for k, t in enumerate(L["low_label"]):
        a(f'<text x="{X(lo.year):.1f}" y="{Y(lo.millions) + L["ann"] * (1.6 + 1.15 * k):.1f}" fill="{INK}" font-size="{L["ann"]}" '
          f'text-anchor="middle" font-weight="{700 if k == 0 else 400}">{t.format(v=lo.millions)}</text>')
    # end labels
    le, lp, lf = cs.iloc[-1], po.iloc[-1], cf.iloc[-1]
    ex = X(2026) + 14
    a(f'<circle cx="{X(lp.year):.1f}" cy="{Y(lp.millions):.1f}" r="{L["dot"]}" fill="{AMBER}" stroke="#fff" stroke-width="3"/>')
    a(f'<circle cx="{X(le.year):.1f}" cy="{Y(le.millions):.1f}" r="{L["dot"]}" fill="{BLUE}" stroke="#fff" stroke-width="3"/>')
    if L.get("fraud_label", True):
        a(f'<text x="{ex:.1f}" y="{Y(lf.millions) + 8:.1f}" fill="{BLUE}" font-size="{L["end"] * 0.8:.0f}" font-weight="700">{lf.millions:.1f}m</text>')
        a(f'<text x="{ex:.1f}" y="{Y(lf.millions) + 8 + L["end"] * 0.85:.1f}" fill="{MUTED}" font-size="{L["ann"] * 0.85:.0f}">incl. fraud</text>')
    a(f'<text x="{ex:.1f}" y="{Y(lp.millions) - 6:.1f}" fill="{AMBER}" font-size="{L["end"]}" font-weight="800">{lp.millions:.2f}m</text>')
    a(f'<text x="{ex:.1f}" y="{Y(lp.millions) - 6 + L["end"] * 0.9:.1f}" fill="{INK}" font-size="{L["ann"] * 0.85:.0f}">police</text>')
    a(f'<text x="{ex:.1f}" y="{Y(le.millions) + 16 + L["end"] * 0.5:.1f}" fill="{BLUE}" font-size="{L["end"]}" font-weight="800">{le.millions:.2f}m</text>')
    a(f'<text x="{ex:.1f}" y="{Y(le.millions) + 16 + L["end"] * 1.4:.1f}" fill="{INK}" font-size="{L["ann"] * 0.85:.0f}">survey</text>')
    # legend
    lx, ly = L["legend"]
    for k, (c, t, dash) in enumerate([(BLUE, "Crime Survey (CSEW): incidents people say they experienced", ""),
                                       (AMBER, "Police recorded crime (breaks = new counting rules)", ""),
                                       (BLUE, "Survey incl. fraud and computer misuse (from 2016/17)", "7 6")]):
        yy = ly + k * L["leg"] * 1.45
        a(f'<line x1="{lx}" x2="{lx + 40}" y1="{yy - L["leg"] * 0.35:.1f}" y2="{yy - L["leg"] * 0.35:.1f}" stroke="{c}" '
          f'stroke-width="{L["lw"] * (0.6 if dash else 1):.1f}" stroke-dasharray="{dash}" stroke-linecap="round"/>')
        a(f'<text x="{lx + 52}" y="{yy:.1f}" fill="{INK}" font-size="{L["leg"]}">{escape(t)}</text>')
    for k, t in enumerate(L["notes"]):
        a(f'<text x="{L["pad"]}" y="{y1 + fs * 2.9 + k * L["note"] * 1.3:.1f}" fill="{MUTED}" font-size="{L["note"]}">{escape(t)}</text>')

    # --- offence table ---
    tx, ty = L["table_xy"]
    a(f'<text x="{tx}" y="{ty:.0f}" fill="{INK}" font-size="{L["h2"]}" font-weight="800">Which crimes are really rising?</text>')
    for k, t in enumerate(L["tsubs"]):
        a(f'<text x="{tx}" y="{ty + L["h2"] * 1.0 + k * L["tsub"] * 1.3:.0f}" fill="{MUTED}" font-size="{L["tsub"]}">{escape(t)}</text>')
    cols = L["cols"]
    per = int(np.ceil(len(rows) / cols))
    cw = (W - 2 * L["pad"]) / cols
    hy = ty + L["h2"] * 1.0 + (len(L["tsubs"]) - 1) * L["tsub"] * 1.3 + L["row"] * 1.15
    for c in range(cols):
        cx = tx + c * cw
        a(f'<text x="{cx + L["c1"]:.0f}" y="{hy:.0f}" fill="{BLUE}" font-size="{L["th"]}" font-weight="700">Survey</text>')
        a(f'<text x="{cx + L["c2"]:.0f}" y="{hy:.0f}" fill="{AMBER}" font-size="{L["th"]}" font-weight="700">Police</text>')
    for i, (nm, sv, pv, pb) in enumerate(rows):
        c, rr = divmod(i, per)
        cx, ry = tx + c * cw, hy + (rr + 1) * L["row"]
        if rr % 2 == 0:
            a(f'<rect x="{cx - 8:.0f}" y="{ry - L["row"] * 0.72:.0f}" width="{cw - 16:.0f}" height="{L["row"]:.0f}" fill="#f8fafc"/>')
        a(f'<text x="{cx:.0f}" y="{ry:.0f}" fill="{INK}" font-size="{L["td"]}" font-weight="600">{escape(nm)}</text>')
        for (arrow, txt, colr), off in ((sv, L["c1"]), (pv, L["c2"])):
            short = txt.replace("  no clear change", " ≈") if arrow == "≈" else txt
            label = f'{arrow} {short}' if arrow and arrow != "≈" else (f'≈ {txt.split()[0]}' if arrow == "≈" else "—")
            a(f'<text x="{cx + off:.0f}" y="{ry:.0f}" fill="{colr}" font-size="{L["td"]}" font-weight="{700 if arrow in "▲▼" and arrow else 500}">'
              f'{escape(label)}</text>')
    ky = hy + (per + 1) * L["row"] + 4
    for k, t in enumerate(L["keys"]):
        a(f'<text x="{tx}" y="{ky + k * L["note"] * 1.3:.0f}" fill="{MUTED}" font-size="{L["note"]}">{escape(t)}</text>')

    # --- footer ---
    fy = H - L["foot"]
    a(f'<line x1="{L["pad"]}" x2="{W - L["pad"]}" y1="{fy:.0f}" y2="{fy:.0f}" stroke="{GRID}" stroke-width="2"/>')
    for k, t in enumerate(L["source"]):
        a(f'<text x="{L["pad"]}" y="{fy + L["src"] * (1.5 + 1.25 * k):.0f}" fill="{MUTED}" font-size="{L["src"]}">{escape(t)}</text>')
    lg = logo_href(L["logo"])
    if lg:
        href, lh = lg
        a(f'<image href="{href}" x="{W - L["pad"] - L["logo"]}" y="{fy + 6:.0f}" width="{L["logo"]}" height="{lh}"/>')
    else:
        a(f'<text x="{W - L["pad"]}" y="{fy + L["src"] * 2:.0f}" fill="{INK}" font-size="{L["src"]}" font-weight="800" text-anchor="end">TRUTH WITH DATA</text>')
    a("</svg>")
    open(os.path.join(CH, name), "w").write("\n".join(o))


NOTE_W = ["Police and survey count different crimes (police figures include crimes against shops, drug and public-order offences;",
          "the survey includes crimes never reported). Compare the trends, not the levels. 1981-2001 police data: Home Office."]
KEYS_W = ["▲ rise   ▼ fall   ≈ change not statistically significant   — not measured (the survey does not cover shops;",
          "police fraud and computer misuse figures come from reporting centres and are not comparable over time)"]
WIDE = dict(bar=46, pad=48, kicker=17, h1=46, sub=21, headline=["Crime survey: down 78% since 1995.", "Police records: up 50% since 2014."],
            subline=["Two official measures of crime in England and Wales, millions of offences a year. Both can be true at once."],
            chart=(110, 1040, 345, 715), axis=18, ann=17, lw=5, dot=8, end=28,
            events=[(1998.3, ["1998: wider counting", f"rules (+{P['counting_rules_1998_effect_pct']:.0f}%)"], 9.2, "end"),
                    (2002.3, ["2002: national", "recording standard"], 8.6, "start"),
                    (2014.9, ["2014: inspectors find", "1 in 5 crimes unrecorded;", "recording tightened"], 17.5, "start")],
            low_label=["2013/14: {v:.2f}m", "police low"], legend=(48, 250), leg=18, note=15, notes=NOTE_W,
            h2=30, tsub=17, tsubs=["Change from 2016/17 to the year to June 2026 (police burglary from 2017/18). Survey: ONS significance test, 5% level."],
            table_xy=(48, 840), cols=2, c1=300, c2=420, row=40, th=18, td=19, keys=KEYS_W,
            foot=66, src=14, logo=80,
            source=["Source: ONS, Crime in England and Wales, year ending June 2026 (Crime Survey for England and Wales; police",
                    "recorded crime); Home Office recorded crime 1898-2001/02. Analysis: truthwithdata.com"])
TALL = dict(bar=50, pad=40, kicker=19, h1=47, sub=25, headline=["Survey: crime down 78% since 1995.", "Police records: up 50% since 2014."],
            subline=["Millions of crimes a year, England and Wales"],
            chart=(100, 905, 372, 712), axis=22, ann=21, lw=6, dot=9, end=30,
            events=[(1998.3, ["1998: new", "counting rules"], 9.6, "end"), (2002.3, ["2002: national", "standard"], 8.6, "start"),
                    (2014.9, ["2014: 1 in 5", "crimes found", "unrecorded"], 18.6, "end")],
            low_label=["{v:.2f}m"], legend=(40, 262), leg=21, note=19,
            notes=["They count different crimes: compare the trends, not the levels."],
            h2=36, tsub=19, tsubs=["2016/17 to year to June 2026. Survey changes tested by ONS (5% level)."],
            table_xy=(40, 812), cols=1, c1=560, c2=800, row=32, th=23, td=25,
            keys=["▲ rise   ▼ fall   ≈ not significant   — not measured"],
            foot=50, src=15, logo=64, source=["Source: ONS Crime in England and Wales, YE June 2026; Home Office 1981-2002.",
                                               "Analysis: truthwithdata.com"])
poster(1200, 1300, WIDE, "uk-crime-two-clocks-poster-wide.svg")
poster(1080, 1350, TALL, "uk-crime-two-clocks-poster-1080x1350.svg")

# OG / share card (1200x630): headline and the two lines only
OG = dict(WIDE, headline=["Is crime rising? Survey: down 78% since 1995.", "Police records: up 50% since 2014."], h1=40,
          subline=["England and Wales, millions of crimes a year"], sub=22, chart=(100, 1040, 312, 548), legend=(48, 232),
          events=[], foot=0, notes=[], leg=16, fraud_label=False)


def og():
    import re
    poster(1200, 630, dict(OG, table_xy=(-2000, -2000), key_y=-50), "_og_tmp.svg")
    s = open(os.path.join(CH, "_og_tmp.svg")).read()
    s = re.sub(r'<line x1="48" x2="1152" y1="630".*', "", s, flags=re.S)  # drop footer block
    s = s.rstrip() + "\n" + (f'<text x="48" y="606" fill="{MUTED}" font-size="15">Source: ONS, Crime in England and Wales, YE June 2026; '
                             'Home Office. Analysis: truthwithdata.com</text>\n</svg>')
    open(os.path.join(CH, "uk-crime-og-1200x630.svg"), "w").write(s)
    os.remove(os.path.join(CH, "_og_tmp.svg"))


og()

# ------------------------------------------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC2 = SRC.replace("; Home Office recorded crime 1898–2001/02", "")


def frame(fig, title, subtitle, source=SRC2, top=0.8, bottom=0.15, left=0.08, right=0.97):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    w, h = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / w, 1 - 29 / h, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / w, 1 - 50 / h, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / w, 10 / h, source, fontsize=8.2, color=MUTED, va="bottom", linespacing=1.35)


def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{escape(alt)}" ', 1)
    open(path, "w").write(s)


# 1. Where the police-recorded rise came from ----------------------------------------------------------------
dec = pd.read_csv(os.path.join(D, "uk-crime-police-rise-decomposition-2014-2026.csv")).sort_values("change")
fig, ax = plt.subplots(figsize=(12.4, 6.0))
cols = [UP if v > 0 else DOWN for v in dec.change]
ax.barh(dec.group, dec.change / 1000, color=cols, height=0.62)
for i, r in enumerate(dec.itertuples()):
    lab = f"{r.change / 1000:+,.0f}k ({r.change_pct:+.0f}%)"
    ax.text(r.change / 1000 + (12 if r.change > 0 else -12), i, lab, va="center", ha="left" if r.change > 0 else "right",
            fontsize=10, color=INK)
ax.axvline(0, color=INK, lw=1)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+,.0f}k" if v else "0"))
ax.set_xlim(-520, 1750)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(axis="y", length=0)
ax.spines["left"].set_visible(False)
tot = dec.change.sum()
frame(fig, "Violence, sexual and public order offences account for all of the rise in police records",
      f"Change in police recorded offences, year ending March 2014 to year ending June 2026 (net {tot / 1e6:+.2f} million, excluding fraud).\n"
      "These are the offence types where ONS says better recording, not more crime, drove most of the increase.", left=0.3, bottom=0.12)
save(fig, "uk-crime-police-recorded-rise-by-offence-2014-2026.svg",
     f"Horizontal bar chart. Between 2013/14 and the year to June 2026, police recorded violence rose by "
     f"{dec.set_index('group').change['Violence against the person'] / 1000:,.0f} thousand, public order offences by "
     f"{dec.set_index('group').change['Public order offences'] / 1000:,.0f} thousand and sexual offences by "
     f"{dec.set_index('group').change['Sexual offences'] / 1000:,.0f} thousand, while theft offences fell by "
     f"{-dec.set_index('group').change['Theft offences (incl. burglary, vehicle, shoplifting)'] / 1000:,.0f} thousand.")

# 2. Survey vs police change by offence (dumbbell-style dot chart) ------------------------------------------------
pp = panel.copy()
pp["name"] = [SHORT.get(o, o) for o in pp.offence]
pp = pp.iloc[::-1].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(12.4, 6.6))
for i, r in pp.iterrows():
    if pd.notna(r.csew_change_pct) and pd.notna(r.police_change_pct):
        ax.plot([r.csew_change_pct, r.police_change_pct], [i, i], color=GRID, lw=3, zorder=1)
    if pd.notna(r.csew_change_pct):
        filled = bool(r.csew_significant)
        ax.scatter(r.csew_change_pct, i, s=95, color=BLUE if filled else "white", edgecolor=BLUE, lw=2, zorder=3)
        ax.text(r.csew_change_pct, i + 0.32, f"{r.csew_change_pct:+.0f}%", ha="center", fontsize=9, color=INK)
    if pd.notna(r.police_change_pct):
        ax.scatter(r.police_change_pct, i, s=95, marker="D", color=AMBER, edgecolor="white", lw=1.5, zorder=3)
        close = pd.notna(r.csew_change_pct) and abs(r.police_change_pct - r.csew_change_pct) < 3
        ax.text(r.police_change_pct, i - 0.5 if close else i + 0.32, f"{r.police_change_pct:+.0f}%", ha="center", fontsize=9, color=INK)
ax.set_yticks(range(len(pp))); ax.set_yticklabels(pp.name); ax.tick_params(axis="y", length=0)
ax.axvline(0, color=INK, lw=1)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}%" if v else "0"))
ax.set_xlim(-70, 85); ax.set_ylim(-0.6, len(pp) - 0.3)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.spines["left"].set_visible(False)
ax.scatter([], [], s=95, color=BLUE, label="Crime Survey: significant change")
ax.scatter([], [], s=95, color="white", edgecolor=BLUE, lw=2, label="Crime Survey: not significant")
ax.scatter([], [], s=95, marker="D", color=AMBER, label="Police recorded")
ax.legend(loc="lower right", frameon=False, fontsize=10)
frame(fig, "The survey and police records disagree most on violence and robbery",
      "Change from 2016/17 to the year to June 2026 (police residential burglary from 2017/18, when it was redefined).\n"
      "Survey significance as tested by ONS at the 5% level. Shoplifting is police-only: the survey does not cover crimes against shops.",
      left=0.2, bottom=0.12)
save(fig, "uk-crime-survey-vs-police-change-by-offence-2017-2026.svg",
     "Dot chart of percentage change by offence, 2016/17 to 2026. Survey: fraud +34% and theft from outside homes +42% "
     "(significant); violence -35%, robbery -58%, burglary -43%, vehicle theft -23%, computer misuse -54%. Police: violence +70%, "
     "robbery +49%, shoplifting +40%, theft from the person +31%, residential burglary -51%, vehicle offences -23%.")

# 3. Perception gap -------------------------------------------------------------------------------------------------
pc = pd.read_csv(os.path.join(D, "uk-crime-perceptions-2017-2024.csv"))
fig, ax = plt.subplots(figsize=(12.4, 5.6))
for seg in (pc[pc.year < 2021], pc[pc.year > 2021]):
    ax.plot(seg.year, seg.national_pct_said_crime_rose, color=AMBER, lw=2.4, marker="o", ms=5)
    ax.plot(seg.year, seg.local_pct_said_crime_rose, color=BLUE, lw=2.4, marker="o", ms=5)
l = pc.iloc[-1]
ax.text(l.year + 0.1, l.national_pct_said_crime_rose, f"Across the country: {l.national_pct_said_crime_rose:.0f}%", va="center", color=INK, fontsize=10.5, fontweight=600)
ax.text(l.year + 0.1, l.local_pct_said_crime_rose, f"In their local area: {l.local_pct_said_crime_rose:.0f}%", va="center", color=INK, fontsize=10.5, fontweight=600)
ax.axvspan(2020.0, 2022.0, color="#f1f5f9", lw=0)
ax.text(2021.0, 36, "not asked\n(pandemic)", ha="center", color=MUTED, fontsize=9)
ax.set_ylim(30, 90); ax.set_xlim(2017.2, 2025.1)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
frame(fig, "Most people think crime is rising nationally; far fewer say so about where they live",
      "Share of adults saying crime has gone up 'a little' or 'a lot' in the past few years, Crime Survey for England and Wales,\n"
      f"rolling years to {l.period[3:]} ({int(l.unweighted_base):,} respondents in the latest year). Latest ONS table on this question.", top=0.76)
save(fig, "uk-crime-perception-gap-national-vs-local-2017-2024.svg",
     f"Line chart. In the year to March 2024, {l.national_pct_said_crime_rose:.0f}% of adults in England and Wales said crime had "
     f"risen across the country, against {l.local_pct_said_crime_rose:.0f}% for their local area. In 2017 the figures were "
     f"{pc.national_pct_said_crime_rose.iloc[0]:.0f}% and {pc.local_pct_said_crime_rose.iloc[0]:.0f}%.")

# 4. Police force rates, YE June 2026 vs England and Wales ------------------------------------------------------------
ff = pd.read_csv(os.path.join(D, "uk-crime-force-summary-2026.csv")).dropna(subset=["total_2026"]).sort_values("total_2026")
ewv = S["local"]["ew_total_2026"]
fig, ax = plt.subplots(figsize=(12.4, 10.5))
ax.barh(ff.area_name, ff.total_2026, color=[AMBER if v > ewv else "#fcd9a8" for v in ff.total_2026], height=0.7)
for i, r in enumerate(ff.itertuples()):
    ax.text(r.total_2026 + 1, i, f"{r.total_2026:.0f}", va="center", fontsize=8.5, color=INK)
ax.axvline(ewv, color=INK, lw=1.2, ls="--")
ax.text(ewv + 1, len(ff) - 0.2, f"England and Wales: {ewv:.1f}", fontsize=10, color=INK, va="bottom")
ax.set_ylim(-0.7, len(ff) + 0.6)
ax.tick_params(axis="y", length=0, labelsize=9); ax.spines["left"].set_visible(False)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
frame(fig, "Recorded crime per 1,000 residents, by police force",
      "Year ending June 2026, excluding fraud. Darker bars: above the England and Wales rate. City of London is not shown (tiny\n"
      "resident population). Forces record differently, so small gaps between forces mean little. Look up any area with our free tool.",
      top=0.87, bottom=0.07, left=0.2)
save(fig, "uk-crime-recorded-crime-rate-by-police-force-2026.svg",
     f"Bar chart of police recorded crime per 1,000 residents for 42 forces in the year to June 2026. Highest "
     f"{S['local']['highest_force'][0]} {S['local']['highest_force'][1]:.0f}, lowest {S['local']['lowest_force'][0]} "
     f"{S['local']['lowest_force'][1]:.0f}; England and Wales {ewv:.1f}.")
print("charts written to", CH)
