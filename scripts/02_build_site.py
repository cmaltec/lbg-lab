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

import _paths



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
    years = sorted({p["year"] for p in pubs if p["year"]}, reverse=True)

    env = Environment(loader=FileSystemLoader(_paths.TEMPLATES),
                      autoescape=select_autoescape(["html"]))
    env.filters["authors"] = authors
    common = {"site": site, "themes": themes, "updated": date.today().strftime("%B %-d, %Y"),
              "paper_count": len(pubs)}

    if _paths.BUILD.exists():
        shutil.rmtree(_paths.BUILD)
    shutil.copytree(_paths.STATIC, _paths.BUILD / "static")

    pages = {
        "index.html": {"team": team},
        "research.html": {"featured": featured,
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
