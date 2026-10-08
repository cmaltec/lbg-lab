#!/usr/bin/env python3
"""
02_build_site.py

Renders the static site into _site/ from content/ (themes, publications,
team, site text) and templates/. No network access; run
01_fetch_publications.py first to refresh the publication list.

Lab members (current and alumni) are set in bold in author lists. People who
held more than one role are merged into one alumni entry, and anyone in the
current team is not repeated among the alumni.

Usage:
  python scripts/02_build_site.py

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-10-08
"""

import json
import math
import re
import shutil
import sys
import unicodedata
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

import _art
import _paths

ROTATION_POOL = 12      # papers per theme the research page rotates through
ROTATION_YEARS = 10     # only papers from the last ten years join the pool



def load(path):
    return json.load(open(path, encoding="utf-8"))


def name_key(name):
    """Surname plus first initial, accent-free, to match author strings."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    parts = [p for p in re.split(r"[\s.\-]+", name) if p]  # "Lozada-Soto" == "Lozada Soto"
    return (parts[-1], parts[0][0]) if len(parts) >= 2 else (name, "")


def merge_alumni(team):
    current = {name_key(p["name"]) for p in team["current"]} | {name_key(team["pi"]["name"])}
    merged = {}
    for a in team["alumni"]:
        k = name_key(a["name"])
        if k in current:
            continue
        label = {"Postdoctoral researcher": "Postdoc"}.get(a["role"], a["role"])
        m = merged.setdefault(k, {"name": a["name"], "roles": [], "topics": [], "sort": ""})
        m["roles"].append(f'{label} {a.get("years", "")}'.strip())
        if a.get("topic"):
            m["topics"].append(a["topic"])
        m["sort"] = max(m["sort"], str(a.get("years", "")))
    return sorted(merged.values(), key=lambda m: m["sort"], reverse=True)


def theme_trend(pubs, themes, first=2005, eras=3):
    """Share of the lab's themed papers on each theme in three equal eras
    ending this year, as one donut per era. A paper on two themes counts half to
    each, so the shares in every window add to 100%."""
    this_year = date.today().year
    total = this_year - first + 1
    starts = [first + round(k * total / eras) for k in range(eras)]
    ids = [t["id"] for t in themes]
    rows = []
    for k, s0 in enumerate(starts):
        span = (starts[k + 1] if k + 1 < len(starts) else this_year + 1) - s0
        w = {i: 0.0 for i in ids}
        n = 0
        for p in pubs:
            th = [i for i in p["themes"] if i in w]
            if th and p["year"] and s0 <= p["year"] < s0 + span:
                n += 1
                for i in th:
                    w[i] += 1 / len(th)
        tot = sum(w.values()) or 1
        end = s0 + span - 1
        rows.append({"label": f"{s0}–{str(end)[2:]}" if end > s0 else str(s0),
                     "window": (f"{s0}–{end}" if end > s0 else str(s0)) + (" (to date)" if end == this_year else ""),
                     "n": n, **{i: 100 * w[i] / tot for i in ids}})
    # One donut per window, segments clockwise from twelve o'clock in theme order.
    R, r_in, gap = 70, 44, 0.025
    cells = []
    for row in rows:
        segs, a0 = [], -math.pi / 2
        for t in themes:
            frac = row[t["id"]] / 100
            if frac <= 0:
                continue
            a1 = a0 + 2 * math.pi * frac
            s0, s1 = a0 + gap / 2, max(a1 - gap / 2, a0 + gap / 2 + 1e-3)
            big = 1 if s1 - s0 > math.pi else 0
            pt = lambda rad, ang: (90 + rad * math.cos(ang), 90 + rad * math.sin(ang))
            (x0, y0), (x1, y1) = pt(R, s0), pt(R, s1)
            (x2, y2), (x3, y3) = pt(r_in, s1), pt(r_in, s0)
            d = (f"M{x0:.2f},{y0:.2f} A{R},{R} 0 {big} 1 {x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f} "
                 f"A{r_in},{r_in} 0 {big} 0 {x3:.2f},{y3:.2f} Z")
            tip = f'{row["window"]}: {t["name"]}, {row[t["id"]]:.0f}%'
            segs.append(f'<path class="tr-seg t-{t["id"]}" d="{d}"><title>{tip}</title></path>')
            if frac >= 0.08:
                mx, my = pt((R + r_in) / 2, (a0 + a1) / 2)
                segs.append(f'<text class="tr-in" x="{mx:.1f}" y="{my + 4:.1f}">{row[t["id"]]:.0f}%</text>')
            a0 = a1
        segs.append(f'<text class="tr-c" x="90" y="95">{row["label"]}</text>')
        cells.append(Markup(f'<svg class="donut" viewBox="0 0 180 180" role="img" aria-label="Share of '
                            f'themed papers on each theme, {row["window"]}">{"".join(segs)}</svg>'))
    svg = cells
    table = [{"window": r["window"], **{i: f"{r[i]:.0f}%" for i in ids}} for r in rows]
    return svg, table

def share_donut(pct, label):
    """A single-value donut: the share filled in red, the rest in grey,
    the percentage in the centre."""
    R, r_in, cx = 54, 36, 60
    a1 = -math.pi / 2 + 2 * math.pi * pct / 100
    big = 1 if pct > 50 else 0
    pt = lambda rad, ang: (cx + rad * math.cos(ang), cx + rad * math.sin(ang))
    (x0, y0), (x1, y1) = pt(R, -math.pi / 2), pt(R, a1)
    (x2, y2), (x3, y3) = pt(r_in, a1), pt(r_in, -math.pi / 2)
    seg = (f'<path class="sd-on" d="M{x0:.2f},{y0:.2f} A{R},{R} 0 {big} 1 {x1:.2f},{y1:.2f} '
           f'L{x2:.2f},{y2:.2f} A{r_in},{r_in} 0 {big} 0 {x3:.2f},{y3:.2f} Z"/>')
    return Markup(f'<svg class="share-donut" viewBox="0 0 120 120" role="img" aria-label="{label}: about {pct}%">'
                  f'<circle class="sd-off" cx="{cx}" cy="{cx}" r="{(R + r_in) / 2}" stroke-width="{R - r_in}"/>'
                  f'{seg}<text x="{cx}" y="{cx + 7}">{pct}%</text></svg>')


def lab_shares(pubs):
    """Share of papers with an open-access copy, rounded to 5% to avoid
    false precision, for the publications page."""
    oa = sum(1 for p in pubs if p.get("oa_url"))
    op = 5 * round(20 * oa / (len(pubs) or 1))
    return {"open": op, "open_donut": share_donut(op, "Papers free to read")}

def main():
    site = load(_paths.CONTENT / "site.json")
    themes = load(_paths.THEMES)["themes"]
    pubs = load(_paths.PUBLICATIONS)["papers"]
    team = load(_paths.PEOPLE / "team.json")

    # Openings past their closing date drop off at the next build.
    today = date.today().isoformat()
    openings_file = _paths.CONTENT / "openings.json"
    openings = [o for o in (load(openings_file)["openings"] if openings_file.exists() else [])
                if not o.get("closes") or o["closes"] >= today]

    members = {name_key(team["pi"]["name"])}
    members |= {name_key(p["name"]) for p in team["current"]}
    members |= {name_key(p["name"]) for p in team["alumni"]}

    def authors(names):
        out = []
        for n in names:
            out.append(Markup("<b>%s</b>") % n if name_key(n) in members else escape(n))
        if len(out) > 12:
            out = out[:10] + [Markup("&hellip;")] + out[-1:]
        return Markup(", ").join(out)

    by_theme = {t["id"]: [p for p in pubs if t["id"] in p["themes"]] for t in themes}
    by_doi = {p["doi"]: p for p in pubs}
    featured = {t["id"]: [by_doi[d] for d in t.get("featured", []) if d in by_doi] for t in themes}

    # Rotation pool per theme: the hand-picked papers first, then recent papers
    # on the theme with a lab member as first or last author. The research page
    # shows three at random on each visit; without JavaScript, the first three.
    # Each paper joins one pool only, its most specific theme (themes.json
    # lists the broadest first), and work led by a listed collaborator stays out.
    recent_year = date.today().year - ROTATION_YEARS
    excluded_seniors = {name_key(n) for n in site.get("rotation_exclude_last_authors", [])}
    order = [t["id"] for t in themes][::-1]

    def primary_theme(p):
        return next((tid for tid in order if tid in p["themes"]), None)

    def lab_led(p):
        a = p["authors"]
        if not a or name_key(a[-1]) in excluded_seniors:
            return False
        return name_key(a[0]) in members or name_key(a[-1]) in members

    rotation = {}
    for t in themes:
        pool = list(featured[t["id"]])
        for p in by_theme[t["id"]]:
            if len(pool) >= ROTATION_POOL:
                break
            if (p not in pool and (p["year"] or 0) >= recent_year and lab_led(p)
                    and primary_theme(p) == t["id"]):
                pool.append(p)
        rotation[t["id"]] = pool
    years = sorted({p["year"] for p in pubs if p["year"]}, reverse=True)

    env = Environment(loader=FileSystemLoader(_paths.TEMPLATES),
                      autoescape=select_autoescape(["html"]))
    env.filters["authors"] = authors
    env.filters["longdate"] = lambda iso: date.fromisoformat(iso).strftime("%B %-d, %Y") if iso else ""
    art = {k: f() for k, f in _art.THEME_ART.items()}
    art_wide = {k: f(w=900, h=150) for k, f in _art.THEME_ART.items()}
    art_band = {k: f(w=620, h=420) for k, f in _art.THEME_ART.items()}
    common = {"site": site, "themes": themes, "openings": openings, "art": art, "art_wide": art_wide, "art_band": art_band,
              "banner": _art.dna_banner(w=1030, h=270),
              "banner_short": _art.dna_banner(w=1030, h=170), "updated": date.today().strftime("%B %-d, %Y"),
              "paper_count": len(pubs), "shares": lab_shares(pubs)}

    if _paths.BUILD.exists():
        shutil.rmtree(_paths.BUILD)
    shutil.copytree(_paths.STATIC, _paths.BUILD / "static")

    pages = {
        "index.html": {"team": team},  # bands use art_wide and theme descriptions
        "research.html": {"featured": featured, "rotation": rotation, "trend": theme_trend(pubs, themes),
                          "counts": {k: len(v) for k, v in by_theme.items()}},
        "publications.html": {"pubs": pubs, "years": years,
                              "pubs_json": Markup(json.dumps(
                                  [{"t": p["title"], "y": p["year"], "th": p["themes"],
                                    "a": " ".join(p["authors"]), "v": p["venue"]} for p in pubs],
                                  ensure_ascii=False).replace("</", "<\\/"))},
        "people.html": {"team": team, "alumni": merge_alumni(team)},
    }
    for name, ctx in pages.items():
        html = env.get_template(name).render(page=name, **common, **ctx)
        (_paths.BUILD / name).write_text(html, encoding="utf-8")
    (_paths.BUILD / ".nojekyll").write_text("")
    print(f"Built {len(pages)} pages into {_paths.BUILD.relative_to(_paths.ROOT)}/ "
          f"({len(pubs)} papers, {len(team['current'])} current members)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
