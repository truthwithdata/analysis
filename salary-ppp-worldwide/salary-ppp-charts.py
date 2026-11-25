#!/usr/bin/env python3
"""Charts for 'How far does your salary really go in another country?' (Truth with Data, Nov 2026).
Usage: python salary-ppp-charts.py DATA_DIR CHART_DIR [LOGO_PNG]   (the site uses TWD_Logo_white.png: poster and share image are dark)
Reads the CSVs written by salary-ppp-analysis.py. The signature bubble chart, the ranking poster and the
share image are drawn as plain SVG (PNG versions need cairosvg); the supporting charts use matplotlib in the
site's house style: Inter, #0f172a ink, #64748b secondary, #e2e8f0 grid, blue #2563eb, amber #d97706."""
import base64
import html
import json
import math
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

D, CH = sys.argv[1], sys.argv[2]
LOGO = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY, LBLUE = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8", "#93c5fd"
# Sequential blues for the price level (dark = a dollar goes furthest)
RAMP = [(0.20, "#172554"), (0.30, "#1e40af"), (0.40, "#2563eb"), (0.55, "#3b82f6"), (0.70, "#60a5fa"),
        (0.85, "#93c5fd"), (1.00, "#bfdbfe"), (9.99, "#dbeafe")]
RAMP_LABELS = ["under 0.20", "0.20–0.30", "0.30–0.40", "0.40–0.55", "0.55–0.70", "0.70–0.85", "0.85–1.00", "above 1.00"]
plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC = ("Sources: World Bank, World Development Indicators (PPP conversion factor for private consumption, official exchange "
       "rate; updated 11 Nov 2026);\nILOSTAT (median monthly earnings of employees). Analysis: truthwithdata.com")
SRC_WDI = ("Source: World Bank, World Development Indicators: PPP conversion factor for private consumption and official exchange rate, "
           "2025\n(2024 for 7 countries), updated 11 Nov 2026. Analysis: truthwithdata.com")
c = pd.read_csv(os.path.join(D, "salary-ppp-price-levels-by-country.csv"))
S = json.load(open(os.path.join(D, "salary-ppp-summary.json")))
cases = pd.read_csv(os.path.join(D, "salary-ppp-india-case-studies.csv"))
occ = pd.read_csv(os.path.join(D, "salary-ppp-occupation-earnings-ppp.csv"))
SHORT = {"Egypt, Arab Rep.": "Egypt", "Gambia, The": "Gambia", "Bahamas, The": "Bahamas", "Lao PDR": "Laos",
         "Viet Nam": "Vietnam", "Korea, Rep.": "South Korea", "Russian Federation": "Russia", "Turkiye": "Türkiye",
         "Slovak Republic": "Slovakia", "Kyrgyz Republic": "Kyrgyzstan", "Hong Kong SAR, China": "Hong Kong",
         "Macao SAR, China": "Macao", "Congo, Rep.": "Congo", "Iran, Islamic Rep.": "Iran",
         "United Arab Emirates": "UAE", "United Kingdom": "UK", "United States": "US", "Bosnia and Herzegovina": "Bosnia",
         "Central African Republic": "CAR", "Sao Tome and Principe": "São Tomé", "Trinidad and Tobago": "Trinidad & Tobago",
         "St. Vincent and the Grenadines": "St Vincent", "Dominican Republic": "Dominican Rep.", "Cote d'Ivoire": "Côte d'Ivoire",
         "North Macedonia": "N. Macedonia", "Papua New Guinea": "Papua New Guinea", "Brunei Darussalam": "Brunei",
         "Micronesia, Fed. Sts.": "Micronesia", "Yemen, Rep.": "Yemen", "Antigua and Barbuda": "Antigua & Barbuda",
         "St. Kitts and Nevis": "St Kitts & Nevis", "St. Lucia": "St Lucia", "Solomon Islands": "Solomon Is."}
c["short"] = c.country.map(lambda s: SHORT.get(s, s))
FOCUS = {"IND", "GBR", "USA", "ARE", "DEU"}
esc = html.escape


def colour(pl):
    for hi, col in RAMP:
        if pl < hi:
            return col
    return RAMP[-1][1]


def ink_on(pl):
    return "#ffffff" if pl < 0.55 else INK


def money(v):
    return f"${v:,.0f}"


# ---------------------------------------------------------------------------------------------------------------
# Circle packing: largest first, each circle placed at the free spot nearest the centre (scaled by `aspect`)
def pack(radii, aspect=1.0, gap=2.0):
    placed = []
    for r in radii:
        if not placed:
            placed.append((0.0, 0.0, r))
            continue
        best = None
        for (x0, y0, r0) in placed:          # candidate spots touching each placed circle
            for k in range(36):
                a = 2 * math.pi * k / 36
                x, y = x0 + (r0 + r + gap) * math.cos(a), y0 + (r0 + r + gap) * math.sin(a)
                if any((x - x1) ** 2 + (y - y1) ** 2 < (r + r1 + gap - 0.01) ** 2 for (x1, y1, r1) in placed):
                    continue
                d = (x / aspect) ** 2 + y ** 2
                if best is None or d < best[0]:
                    best = (d, x, y)
        placed.append((best[1], best[2], r))
    return placed


def bubbles_svg(width, rmax, aspect, label_min, title_size, sub_lines, legend_cols, mobile=False):
    d = c.sort_values("value_of_1000_usd", ascending=False).reset_index(drop=True)
    vmax = d.value_of_1000_usd.max()
    radii = [rmax * math.sqrt(v / vmax) for v in d.value_of_1000_usd]
    pos = pack(radii, aspect=aspect)
    xs = [p[0] for p in pos]; ys = [p[1] for p in pos]
    minx = min(x - r for x, _, r in pos); maxx = max(x + r for x, _, r in pos)
    miny = min(y - r for _, y, r in pos); maxy = max(y + r for _, y, r in pos)
    pad = 16
    scale = min(1.0, (width - 2 * pad) / (maxx - minx))
    top = 30 + title_size + 22 * len(sub_lines) + 18
    ph = (maxy - miny) * scale
    leg_h = (2 * rmax * scale + 46) + (90 if mobile else 0) + 26
    height = int(top + ph + 24 + leg_h + 46)
    ox = (width - (maxx - minx) * scale) / 2 - minx * scale
    oy = top - miny * scale
    alt = (f"Bubble chart of {len(d)} countries. Each circle is sized by what $1,000 changed at the market exchange rate "
           f"buys locally, in US prices. It buys the most in {d.short[0]} (${d.value_of_1000_usd[0]:,.0f}), "
           f"{d.short[1]} and {d.short[2]}, and the least in {d.short.iloc[-1]} (${d.value_of_1000_usd.iloc[-1]:,.0f}) "
           f"and {d.short.iloc[-2]}. In the median country it buys ${S['median_value_of_1000']:,.0f}.")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
         f'role="img" aria-labelledby="spp-t{"m" if mobile else ""} spp-d{"m" if mobile else ""}" '
         f'font-family="Inter, Segoe UI, Arial, sans-serif">',
         f'<title id="spp-t{"m" if mobile else ""}">What $1,000 a month is really worth in {len(d)} countries</title>',
         f'<desc id="spp-d{"m" if mobile else ""}">{esc(alt)}</desc>',
         f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
         f'<text x="{pad}" y="{30 + title_size * 0.8:.0f}" font-size="{title_size}" font-weight="800" fill="{INK}">'
         f'What $1,000 a month is really worth</text>']
    for i, line in enumerate(sub_lines):
        o.append(f'<text x="{pad}" y="{30 + title_size + 18 + 22 * i:.0f}" font-size="{15 if not mobile else 13.5}" fill="{MUTED}">{esc(line)}</text>')
    for i, r in d.iterrows():
        x, y, rad = ox + pos[i][0] * scale, oy + pos[i][1] * scale, pos[i][2] * scale
        foc = r.iso3 in FOCUS
        stroke = f' stroke="{AMBER}" stroke-width="3"' if foc else ' stroke="#ffffff" stroke-width="1"'
        tip = f"{r.country}: $1,000 buys what ${r.value_of_1000_usd:,.0f} buys in the US (price level {r.price_level:.2f}, {int(r.wdi_year)})"
        o.append(f'<g><title>{esc(tip)}</title><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{colour(r.price_level)}"{stroke}/>')
        col = ink_on(r.price_level)
        if rad >= label_min * 1.9 and len(r.short) <= 11:
            fs = min(14, rad / 3.2) if not mobile else min(11.5, rad / 3.0)
            o.append(f'<text x="{x:.1f}" y="{y - fs * 0.15:.1f}" font-size="{fs:.1f}" font-weight="700" fill="{col}" text-anchor="middle">{esc(r.short)}</text>')
            o.append(f'<text x="{x:.1f}" y="{y + fs * 1.05:.1f}" font-size="{fs * 0.92:.1f}" fill="{col}" text-anchor="middle">{money(r.value_of_1000_usd)}</text>')
        elif rad >= label_min or foc:
            fs = max(9.0, min(11.5, rad / 1.8)) if mobile else max(9.0, min(12.0, rad / 1.9))
            o.append(f'<text x="{x:.1f}" y="{y + fs * 0.35:.1f}" font-size="{fs:.1f}" font-weight="600" fill="{col}" text-anchor="middle">{r.iso3}</text>')
        o.append('</g>')
    # Legend: size and colour
    ly = top + ph + 28
    o.append(f'<text x="{pad}" y="{ly + 4}" font-size="12.5" font-weight="700" fill="{INK}">Circle size: what $1,000 buys, in US prices</text>')
    lx = pad
    for v in [1000, 2000, 4000, 6000]:
        rr = rmax * scale * math.sqrt(v / vmax)
        base = ly + 14 + 2 * rmax * scale
        o.append(f'<circle cx="{lx + rr:.1f}" cy="{base - rr:.1f}" r="{rr:.1f}" fill="none" stroke="{GREY}" stroke-width="1.2"/>')
        o.append(f'<text x="{lx + rr:.1f}" y="{base + 15:.1f}" font-size="11" fill="{MUTED}" text-anchor="middle">{money(v)}</text>')
        lx += 2 * rr + (14 if mobile else 22)
    if mobile:
        cx0, cy0 = pad, ly + 2 * rmax * scale + 48
    else:
        cx0, cy0 = max(lx + 30, width * 0.45), ly
    o.append(f'<text x="{cx0}" y="{cy0 + 4}" font-size="12.5" font-weight="700" fill="{INK}">Colour: price level (US = 1.00)</text>')
    sw = (width - cx0 - pad) / len(RAMP) if not mobile else (width - 2 * pad) / 4
    for k, (hi, col) in enumerate(RAMP):
        row, colk = (k // 4, k % 4) if mobile else (0, k)
        x = cx0 + colk * sw
        y = cy0 + 14 + row * 34
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{sw - 4:.1f}" height="12" rx="3" fill="{col}"/>')
        o.append(f'<text x="{x:.1f}" y="{y + 26:.1f}" font-size="{10.5 if not mobile else 10}" fill="{MUTED}">{RAMP_LABELS[k]}</text>')
    fy = height - 30
    o.append(f'<circle cx="{pad + 7}" cy="{fy - 30}" r="6" fill="none" stroke="{AMBER}" stroke-width="3"/>'
             f'<text x="{pad + 20}" y="{fy - 26}" font-size="11.5" fill="{MUTED}">India, UK, US, UAE and Germany (case studies)</text>')
    src = ("Source: World Bank WDI, PPP conversion factor for private consumption and official exchange rate, 2025 (2024 for 7 countries).",
           "Price level = PPP factor ÷ exchange rate. Truth with Data · truthwithdata.com")
    if mobile:
        src = ("Source: World Bank WDI, PPP factor for private consumption", "and exchange rate, 2025 (2024 for 7 countries).",
               "Truth with Data · truthwithdata.com")
        fy -= 12
    for i, s in enumerate(src):
        o.append(f'<text x="{pad}" y="{fy + 14 * i}" font-size="10.5" fill="{MUTED}">{esc(s)}</text>')
    o.append('</svg>')
    return "\n".join(o), alt


desk, alt = bubbles_svg(1000, 46, 1.55, 15, 30,
                        [f"Change $1,000 at the market rate and spend it locally. In {S['countries']} countries, this is what it buys",
                         "at US prices. Bigger, darker circles: the dollar goes further."], 8)
open(os.path.join(CH, "salary-ppp-what-1000-dollars-is-worth-2025.svg"), "w").write(desk)
mob, _ = bubbles_svg(420, 30, 0.62, 12.5, 21,
                     ["$1,000 changed at the market rate and spent", f"locally, valued at US prices ({S['countries']} countries)."], 4, mobile=True)
open(os.path.join(CH, "salary-ppp-what-1000-dollars-is-worth-2025-mobile.svg"), "w").write(mob)


# ---------------------------------------------------------------------------------------------------------------
# Poster 1080x1350: the 20 countries where a dollar goes furthest and least far
def logo_tag(x, y, h):
    if not (LOGO and os.path.exists(LOGO)):
        return f'<text x="{x}" y="{y + h * 0.7:.0f}" font-size="{h * 0.6:.0f}" font-weight="800" fill="#ffffff">Truth with Data</text>'
    b64 = base64.b64encode(open(LOGO, "rb").read()).decode()
    return f'<image x="{x}" y="{y}" height="{h}" width="{h * 1.574:.0f}" href="data:image/png;base64,{b64}"/>'


def poster():
    W, H = 1080, 1350
    top = c.nsmallest(20, "price_level").reset_index(drop=True)
    bot = c.nlargest(20, "price_level").sort_values("price_level").reset_index(drop=True)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-labelledby="pt pd" font-family="Inter, Segoe UI, Arial, sans-serif">',
         '<title id="pt">Where $1,000 goes furthest, and least far</title>',
         f'<desc id="pd">Ranking of the 20 countries where $1,000 changed at the market rate buys the most at US prices, led by '
         f'{top.short[0]} (${top.value_of_1000_usd[0]:,.0f}), and the 20 where it buys the least, ending with {bot.short.iloc[-1]} '
         f'(${bot.value_of_1000_usd.iloc[-1]:,.0f}).</desc>',
         f'<rect width="{W}" height="{H}" fill="#0f172a"/>',
         f'<rect x="0" y="0" width="{W}" height="300" fill="#1e3a8a"/>',
         '<text x="60" y="96" font-size="25" font-weight="700" fill="#93c5fd" letter-spacing="3">PURCHASING POWER, 2025</text>',
         '<text x="60" y="160" font-size="56" font-weight="800" fill="#ffffff">What $1,000 a month</text>',
         '<text x="60" y="224" font-size="56" font-weight="800" fill="#ffffff">is really worth</text>',
         f'<text x="60" y="270" font-size="22" fill="#dbeafe">Changed at the market rate and spent locally, valued at US prices</text>']
    colw = 460
    for side, (df, head, x0, col) in enumerate([(top, "Goes furthest", 60, "#60a5fa"), (bot, "Goes least far", 560, "#fbbf24")]):
        o.append(f'<text x="{x0}" y="352" font-size="28" font-weight="800" fill="#ffffff">{head}</text>')
        vmax = 6500
        for i, r in df.iterrows():
            y = 384 + i * 41
            bw = (colw - 190 - 78) * r.value_of_1000_usd / vmax
            o.append(f'<text x="{x0}" y="{y + 21}" font-size="16" fill="#94a3b8" font-variant-numeric="tabular-nums">{i + 1 if side == 0 else len(c) - 19 + i}</text>')
            o.append(f'<text x="{x0 + 40}" y="{y + 21}" font-size="18" font-weight="600" fill="#f8fafc">{esc(r.short)}</text>')
            o.append(f'<rect x="{x0 + 190}" y="{y + 6}" width="{bw:.1f}" height="20" rx="4" fill="{col}"/>')
            o.append(f'<text x="{x0 + 196 + bw:.1f}" y="{y + 22}" font-size="17" font-weight="700" fill="#ffffff">{money(r.value_of_1000_usd)}</text>')
    o.append(f'<line x1="60" x2="{W - 60}" y1="1222" y2="1222" stroke="#334155"/>')
    o.append(f'<text x="60" y="1254" font-size="17" fill="#cbd5e1">Median of {S["countries"]} countries: ${S["median_value_of_1000"]:,.0f}. US = $1,000 by definition. '
             f'Ranks of {S["countries"]}.</text>')
    o.append('<text x="60" y="1284" font-size="14.5" fill="#94a3b8">Source: World Bank WDI, PPP conversion factor for private consumption and official exchange rate,</text>')
    o.append('<text x="60" y="1304" font-size="14.5" fill="#94a3b8">2025 (2024 for 7 countries). National averages: big-city rents, taxes and imported goods differ.</text>')
    o.append(logo_tag(W - 60 - 118, 1250, 75))
    o.append('</svg>')
    return "\n".join(o)


open(os.path.join(CH, "salary-ppp-where-1000-dollars-goes-furthest-poster.svg"), "w").write(poster())


# Share image 1200x630
def og():
    W, H = 1200, 630
    f = c.set_index("iso3")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, Segoe UI, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#0f172a"/>',
         '<text x="56" y="92" font-size="22" font-weight="700" fill="#93c5fd" letter-spacing="3">SALARY vs PRICES · 164 COUNTRIES</text>',
         '<text x="56" y="160" font-size="52" font-weight="800" fill="#ffffff">How far does your salary</text>',
         '<text x="56" y="222" font-size="52" font-weight="800" fill="#ffffff">really go abroad?</text>',
         '<text x="56" y="270" font-size="22" fill="#cbd5e1">What $1,000 changed at the market rate buys, at US prices (2025)</text>']
    items = [("IND", "India"), ("ARE", "UAE"), ("DEU", "Germany"), ("GBR", "UK"), ("CHE", "Switzerland")]
    vmax = f.value_of_1000_usd.max()
    x = 70
    for iso, name in items:
        v = f.loc[iso, "value_of_1000_usd"]
        r = 92 * math.sqrt(v / f.loc["IND", "value_of_1000_usd"])
        cx = x + 100
        o.append(f'<circle cx="{cx}" cy="{420 + 92 - r:.0f}" r="{r:.0f}" fill="{colour(f.loc[iso, "price_level"])}" stroke="#334155"/>')
        o.append(f'<text x="{cx}" y="{420 + 92 + 34}" font-size="22" font-weight="700" fill="#ffffff" text-anchor="middle">{name}</text>')
        o.append(f'<text x="{cx}" y="{420 + 92 + 62}" font-size="24" font-weight="800" fill="#fbbf24" text-anchor="middle">{money(v)}</text>')
        x += 215
    o.append(logo_tag(W - 56 - 140, 40, 89))
    o.append(f'<text x="{W - 56}" y="612" font-size="14" fill="#94a3b8" text-anchor="end">Data: World Bank WDI · truthwithdata.com</text>')
    o.append('</svg>')
    return "\n".join(o)


open(os.path.join(CH, "salary-ppp-og.svg"), "w").write(og())
try:
    import cairosvg
    cairosvg.svg2png(url=os.path.join(CH, "salary-ppp-og.svg"), write_to=os.path.join(CH, "salary-ppp-og-1200x630.png"),
                     output_width=1200, output_height=630)
    cairosvg.svg2png(url=os.path.join(CH, "salary-ppp-where-1000-dollars-goes-furthest-poster.svg"),
                     write_to=os.path.join(CH, "salary-ppp-where-1000-dollars-goes-furthest-poster-1080x1350.png"),
                     output_width=1080, output_height=1350)
    os.remove(os.path.join(CH, "salary-ppp-og.svg"))
except ImportError:
    print("cairosvg not installed: PNG versions skipped")


# ---------------------------------------------------------------------------------------------------------------
# Supporting charts (matplotlib)
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
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{esc(alt)}" ', 1)
    open(path, "w").write(s)


# A. Price level by region: one dot per country
reg_order = (c.groupby("region").price_level.median().sort_values().index.tolist())
fig, ax = plt.subplots(figsize=(12.4, 6.2))
rng = np.random.default_rng(7)
for k, rg in enumerate(reg_order):
    sub = c[c.region == rg]
    yj = k + rng.uniform(-0.22, 0.22, len(sub))
    ax.scatter(sub.price_level, yj, s=36, color=[colour(p) for p in sub.price_level], edgecolor="#64748b", linewidth=0.5, zorder=3)
    med = sub.price_level.median()
    ax.plot([med, med], [k - 0.34, k + 0.34], color=INK, lw=2, zorder=4)
    for _, r in sub[sub.iso3.isin(FOCUS | {"CHE", "EGY", "PAK", "CHN", "BRA", "NGA"})].iterrows():
        ax.annotate(r.short, (r.price_level, yj[list(sub.index).index(_)]), xytext=(0, 8), textcoords="offset points",
                    fontsize=8.6, color=INK, ha="center", fontweight=600)
ax.axvline(1, color=GREY, lw=1, ls=(0, (3, 3)))
ax.text(1.01, len(reg_order) - 0.55, "US prices = 1.00", fontsize=9, color=MUTED)
ax.set_yticks(range(len(reg_order)))
ax.set_yticklabels([f"{r.replace(', Afghanistan & Pakistan', ' (incl. Pakistan)')} ({(c.region == r).sum()})" for r in reg_order])
ax.set_xlim(0, 1.4)
ax.set_xlabel("Price level of household consumption (PPP factor ÷ exchange rate; US = 1.00)")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0)
frame(fig, "Prices for the same basket are lowest in South Asia and Africa",
      "Each dot is a country; the black line is the regional median. A price level of 0.25 means the average basket costs a quarter\n"
      "of what $1,000 changed at the market rate would suggest.", source=SRC_WDI, left=0.30, top=0.77, bottom=0.17)
save(fig, "salary-ppp-price-level-by-region-2025.svg",
     "Dot plot of price levels by region. Medians: " + ", ".join(
         f"{r} {c[c.region == r].price_level.median():.2f}" for r in reg_order) + ".")

# B. Median monthly earnings at market rates and in PPP dollars
pick = ["CHE", "LUX", "DNK", "USA", "DEU", "NLD", "GBR", "AUS", "CAN", "FRA", "ESP", "POL", "TUR", "CHN", "BRA", "MEX",
        "ZAF", "THA", "VNM", "IND", "PAK", "EGY", "NGA"]
e = c[c.iso3.isin(pick) & c.median_monthly_intl_usd_ppp.notna()].sort_values("median_monthly_intl_usd_ppp")
fig, ax = plt.subplots(figsize=(12.4, 7.4))
yy = np.arange(len(e))
for y, (_, r) in zip(yy, e.iterrows()):
    ax.plot([r.median_monthly_usd_market, r.median_monthly_intl_usd_ppp], [y, y], color=GRID, lw=3, zorder=1)
ax.scatter(e.median_monthly_usd_market, yy, s=60, color=GREY, zorder=3, label="At market exchange rates (US$)")
ax.scatter(e.median_monthly_intl_usd_ppp, yy, s=60, color=BLUE, zorder=3, label="Adjusted for local prices (PPP $)")
for y, (_, r) in zip(yy, e.iterrows()):
    ax.text(r.median_monthly_intl_usd_ppp + 90 if r.median_monthly_intl_usd_ppp >= r.median_monthly_usd_market else r.median_monthly_usd_market + 90,
            y, f"{money(r.median_monthly_intl_usd_ppp)} PPP", va="center", fontsize=8.8, color=INK)
ax.set_yticks(yy)
ax.set_yticklabels([f"{r.short} ({int(r.earnings_year)})" for _, r in e.iterrows()])
ax.tick_params(axis="y", length=0)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_xlim(0, 9000)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("Median monthly earnings of employees, before tax (survey year in brackets, uprated to 2025 prices)")
ax.legend(loc="lower right", frameon=False, fontsize=9.5)
frame(fig, "Adjusting for prices narrows pay gaps, but doesn't close them",
      "Median monthly earnings of all employees. Grey: changed into dollars at market rates. Blue: what that buys at US prices.",
      left=0.17, top=0.86, bottom=0.155)
save(fig, "salary-ppp-median-earnings-market-vs-ppp-2025.svg",
     "Dumbbell chart of median monthly earnings. " + "; ".join(
         f"{r.short}: ${r.median_monthly_usd_market:,.0f} at market rates, ${r.median_monthly_intl_usd_ppp:,.0f} PPP" for _, r in e.iloc[::-1].iterrows()) + ".")

# C. India case study: Rs 1 lakh a month
k = cases[cases.salary_inr_month == 100000].set_index("iso3")
fx = c.set_index("iso3").fx
names = {"GBR": "United Kingdom", "USA": "United States", "ARE": "UAE", "DEU": "Germany"}
fig, ax = plt.subplots(figsize=(12.4, 5.6))
grp = ["GBR", "USA", "DEU", "ARE"]
bw = 0.26
vals = {g: [k.loc[g, "market_rate_equivalent"] / fx[g], k.loc[g, "ppp_equivalent"] / fx[g],
            k.loc[g, "same_rank_salary_lcu"] / fx[g] if pd.notna(k.loc[g, "same_rank_salary_lcu"]) else np.nan] for g in grp}
cols = [GREY, BLUE, AMBER]
labs = ["Changed at the market rate", "Same average basket (PPP)", "Same place in the pay ladder (6.7× the median)"]
for j in range(3):
    xs = [i + (j - 1) * bw for i in range(len(grp))]
    hs = [vals[g][j] for g in grp]
    ax.bar(xs, hs, width=bw - 0.03, color=cols[j], label=labs[j], zorder=3)
    for x_, h_, g in zip(xs, hs, grp):
        if np.isfinite(h_):
            ax.text(x_, h_ + 400, f"${h_ / 1000:,.1f}k" if h_ >= 10000 else f"${h_:,.0f}", ha="center", fontsize=9, color=INK)
        else:
            ax.text(x_, 600, "no ILOSTAT\nmedian", ha="center", fontsize=8.2, color=MUTED)
ax.set_xticks(range(len(grp)))
ax.set_xticklabels([names[g] for g in grp], fontsize=11)
ax.tick_params(axis="x", length=0)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_ylabel("A month, in US dollars at market rates")
ax.set_ylim(0, 35000)
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
frame(fig, "₹1 lakh a month in India: what you'd need abroad depends on the question",
      "Monthly pay needed in each country, before tax. ₹1 lakh is 6.7 times India's median for employees (₹15,000 in the 2025 labour force survey).",
      top=0.80, bottom=0.14, left=0.08)
save(fig, "salary-ppp-india-1-lakh-equivalents-2025.svg",
     "Bar chart. For Rs 1 lakh a month in India: " + "; ".join(
         f"{names[g]} ${vals[g][0]:,.0f} at market rates, ${vals[g][1]:,.0f} for the same basket" +
         (f", ${vals[g][2]:,.0f} for the same place in the pay ladder" if np.isfinite(vals[g][2]) else "") for g in grp) + ".")

# D. Professionals' median earnings (ILO's PPP dollars)
pickp = ["LUX", "DEU", "CHE", "USA", "ESP", "IRL", "GBR", "POL", "FRA", "TUR", "THA", "BRA", "MEX", "VNM", "IND", "EGY", "PAK", "NGA"]
p = occ[occ.iso3.isin(pickp)].merge(c[["iso3", "short"]], on="iso3").sort_values("professionals")
fig, ax = plt.subplots(figsize=(12.4, 6.8))
yy = np.arange(len(p))
ax.barh(yy, p.professionals, height=0.62, color=[AMBER if i in ("IND", "GBR", "USA", "DEU") else BLUE for i in p.iso3], zorder=3)
ax.scatter(p.all_employees, yy, marker="|", s=220, color=INK, zorder=4, label="All employees")
for y, (_, r) in zip(yy, p.iterrows()):
    ax.text(r.professionals + 80, y, f"{money(r.professionals)}  ({r.professionals_vs_all:.1f}× all employees)", va="center", fontsize=8.8, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([f"{r.short} ({int(r.year)})" for _, r in p.iterrows()]); ax.tick_params(axis="y", length=0)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_xlim(0, 13500)
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("Median monthly earnings of professionals (ISCO-08 group 2), PPP dollars as published by ILOSTAT, not uprated")
ax.legend(loc="lower right", frameon=False, fontsize=9.5)
frame(fig, "Professionals' pay premium is biggest in middle-income countries",
      "Bars: median monthly earnings of professionals (engineers, teachers, doctors, IT and finance specialists...). Black tick: all employees.",
      source="Source: ILOSTAT, median monthly earnings of employees by occupation, PPP $ (latest year 2022 or later). Analysis: truthwithdata.com",
      left=0.15, top=0.86, bottom=0.14)
save(fig, "salary-ppp-professionals-earnings-ppp.svg",
     "Bar chart of professionals' median monthly earnings in PPP dollars: " + "; ".join(
         f"{r.short} ${r.professionals:,.0f}" for _, r in p.iloc[::-1].iterrows()) + ".")
print("charts written to", CH)
