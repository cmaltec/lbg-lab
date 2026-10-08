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
              "paper_count": len(pubs)}

    if _paths.BUILD.exists():
        shutil.rmtree(_paths.BUILD)
    shutil.copytree(_paths.STATIC, _paths.BUILD / "static")

    pages = {
        "index.html": {"team": team},  # bands use art_wide and theme descriptions
        "research.html": {"featured": featured, "rotation": rotation,
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
