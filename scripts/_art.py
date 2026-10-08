#!/usr/bin/env python3
"""
_art.py

Decorative SVG illustrations for the site, one motif per research theme and
a banner for the home page. They are schematic, not data: no axes, numbers
or results. Colours come from CSS classes (art-*), so the drawings follow
the light and dark palettes. A fixed seed keeps them identical between
builds.

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-10-08
"""

import math
import random

from markupsafe import Markup

SEED = 2026


def _svg(w, h, body, label):
    return Markup(f'<svg class="art" viewBox="0 0 {w} {h}" role="img" aria-label="{label}" '
                  f'preserveAspectRatio="xMidYMid slice">{body}</svg>')


def haplotype_band(w=1200, h=180):
    """Rows of haplotype blocks: the hero panels."""
    rng = random.Random(SEED)
    rows, out = max(6, round(h / 22)), []
    rh = h / rows
    for r in range(rows):
        x = 0.0
        while x < w:
            seg = rng.uniform(30, 160)
            shade = rng.choice(["art-0", "art-1", "art-1", "art-2", "art-3"])
            out.append(f'<rect class="{shade}" x="{x:.1f}" y="{r * rh + 2:.1f}" '
                       f'width="{max(seg - 3, 2):.1f}" height="{rh - 4:.1f}" rx="2"/>')
            x += seg
    return _svg(w, h, "".join(out), "Schematic haplotype blocks")


def genotype_matrix(w=360, h=150):
    """Genomic selection: a genotype matrix with one highlighted marker column."""
    rng = random.Random(SEED + 1)
    rows, out = max(10, round(h / 14)), []    # ~14 px cells at any size
    cols = max(12, round(w / (h / rows)))
    cw, ch = w / cols, h / rows
    hot = round(cols * 0.63)
    for c in range(cols):
        for r in range(rows):
            g = rng.choice([0, 1, 1, 2])
            cls = ("art-hot" if c == hot and g == 2 else
                   "art-3" if g == 2 else "art-2" if g == 1 else "art-0")
            out.append(f'<rect class="{cls}" x="{c * cw + 1:.1f}" y="{r * ch + 1:.1f}" '
                       f'width="{cw - 2:.1f}" height="{ch - 2:.1f}" rx="1.5"/>')
    out.append(f'<rect class="art-frame" x="{hot * cw:.1f}" y="0" width="{cw:.1f}" height="{h}" rx="2"/>')
    return _svg(w, h, "".join(out), "Schematic genotype matrix with one marker highlighted")


def chromosomes_roh(w=360, h=150):
    """Inbreeding: chromosome pairs with runs of homozygosity marked."""
    rng = random.Random(SEED + 2)
    n, out = max(5, round(w / 52)), []      # one chromosome pair per ~52 px
    gap = w / n
    for i in range(n):
        length = h * rng.uniform(0.55, 0.95)
        y0 = (h - length) / 2
        for side in (-7, 7):
            x = i * gap + gap / 2 + side - 5
            out.append(f'<rect class="art-1" x="{x:.1f}" y="{y0:.1f}" width="10" '
                       f'height="{length:.1f}" rx="5"/>')
        # shared runs of homozygosity span both homologues
        for _ in range(rng.randint(1, 3)):
            seg = length * rng.uniform(0.08, 0.25)
            ys = y0 + rng.uniform(0, length - seg)
            x = i * gap + gap / 2 - 12
            out.append(f'<rect class="art-hot" x="{x:.1f}" y="{ys:.1f}" width="24" '
                       f'height="{seg:.1f}" rx="3" opacity=".85"/>')
        out.append(f'<circle class="art-3" cx="{i * gap + gap / 2:.1f}" '
                   f'cy="{y0 + length * 0.4:.1f}" r="3"/>')
    return _svg(w, h, "".join(out), "Schematic chromosomes with runs of homozygosity")


def host_microbe_network(w=360, h=150):
    """Microbiome: a host node linked to a cloud of microbial taxa."""
    rng = random.Random(SEED + 3)
    cx, cy, out, nodes = w / 2, h / 2, [], []
    spread = w / h                                   # wider canvas, wider cloud
    for i in range(int(18 + 8 * spread)):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(30, h / 2 - 8)
        nodes.append((cx + r * math.cos(a) * spread * 0.9, cy + r * math.sin(a), rng.uniform(3, 7)))
    for i, (x, y, _) in enumerate(nodes):
        if rng.random() < 0.55:
            out.append(f'<line class="art-edge" x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}"/>')
        j = rng.randrange(len(nodes))
        if j != i and rng.random() < 0.6:
            x2, y2, _ = nodes[j]
            out.append(f'<line class="art-edge" x1="{x:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for x, y, r in nodes:
        out.append(f'<circle class="{rng.choice(["art-2", "art-3", "art-hot"])}" '
                   f'cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>')
    out.append(f'<circle class="art-host" cx="{cx:.1f}" cy="{cy:.1f}" r="22"/>')
    return _svg(w, h, "".join(out), "Schematic host-microbe network")


THEME_ART = {"breeding": genotype_matrix, "diversity": chromosomes_roh,
             "microbiome": host_microbe_network}
