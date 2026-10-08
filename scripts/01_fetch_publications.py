#!/usr/bin/env python3
"""
01_fetch_publications.py

Builds content/publications.json from the lab's ORCID record, with titles,
authors, venues, open-access links and abstracts from OpenAlex.

ORCID is the curated list of works; OpenAlex is looked up by DOI in batches.
Only peer-reviewed output is kept (journal articles, reviews, books,
chapters and encyclopedia entries); chapters of a book that is listed whole
are folded into the book. Conference abstracts, preprints, datasets and journal supplements
are left out, and content/exclude.json can drop individual DOIs by hand.
Each paper is tagged with the research themes whose keywords appear in its
title, abstract or keywords (content/themes.json).

Usage:
  python scripts/01_fetch_publications.py

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-10-08
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

import _paths

KEEP_TYPES = {"article", "review", "book-chapter", "book", "reference-entry"}
SUPPLEMENT = re.compile(r"suppl|abstract|meeting|proceedings of the", re.I)
USER_AGENT = f"qglab-site/1.0 (mailto:{_paths.MAILTO})"


def get_json(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def orcid_dois(orcid):
    data = get_json(f"https://pub.orcid.org/v3.0/{orcid}/works")
    dois = set()
    for group in data.get("group", []):
        for ext in (group.get("external-ids") or {}).get("external-id", []):
            if ext.get("external-id-type") == "doi":
                dois.add(ext["external-id-value"].lower().strip())
    return sorted(dois)


def openalex_by_doi(dois):
    fields = ("id,doi,title,publication_year,publication_date,type,authorships,"
              "primary_location,open_access,biblio,is_paratext,keywords,"
              "abstract_inverted_index")
    works = []
    for i in range(0, len(dois), 50):
        batch = "|".join("https://doi.org/" + d for d in dois[i:i + 50])
        url = ("https://api.openalex.org/works?per-page=50&select=" + fields
               + "&filter=doi:" + urllib.parse.quote(batch, safe="|:/")
               + "&mailto=" + _paths.MAILTO)
        works += get_json(url).get("results", [])
        time.sleep(0.2)
    return works


def abstract_text(inverted):
    if not inverted:
        return ""
    slots = {}
    for word, positions in inverted.items():
        for p in positions:
            slots[p] = word
    return " ".join(slots[k] for k in sorted(slots))


def is_peer_reviewed(w):
    if w.get("type") not in KEEP_TYPES or w.get("is_paratext"):
        return False
    source = ((w.get("primary_location") or {}).get("source") or {})
    venue = source.get("display_name") or ""
    issue = str((w.get("biblio") or {}).get("issue") or "")
    if SUPPLEMENT.search(venue) or SUPPLEMENT.search(issue):
        return False
    if source.get("type") == "repository":
        return False
    return True


def tag_themes(text, themes):
    text = text.lower()
    return [t["id"] for t in themes
            if any(k in text for k in t["keywords"])]


def main():
    themes = json.load(open(_paths.THEMES, encoding="utf-8"))["themes"]
    excluded = set()
    exclude_file = _paths.CONTENT / "exclude.json"
    if exclude_file.exists():
        excluded = {d.lower() for d in json.load(open(exclude_file))["dois"]}

    dois = orcid_dois(_paths.ORCID)
    print(f"ORCID: {len(dois)} works with a DOI")
    works = openalex_by_doi(dois)
    print(f"OpenAlex: {len(works)} matched")

    papers = []
    for w in works:
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        if doi in excluded or not is_peer_reviewed(w):
            continue
        source = ((w.get("primary_location") or {}).get("source") or {})
        abstract = abstract_text(w.get("abstract_inverted_index"))
        keywords = " ".join(k.get("display_name", "") for k in w.get("keywords") or [])
        papers.append({
            "title": w.get("title") or "",
            "authors": [a["author"]["display_name"] for a in w.get("authorships", [])],
            "year": w.get("publication_year"),
            "date": w.get("publication_date"),
            "venue": source.get("display_name") or "",
            "type": w.get("type"),
            "doi": doi,
            "oa_url": (w.get("open_access") or {}).get("oa_url"),
            "themes": tag_themes(" ".join([w.get("title") or "", abstract, keywords]), themes),
        })

    # A book listed whole stands for its chapters (Springer: <book DOI>_<n>).
    book_dois = {p["doi"] for p in papers if p["type"] == "book"}
    papers = [p for p in papers
              if not any(p["doi"].startswith(b + "_") for b in book_dois)]

    # The same paper can carry two DOIs (e.g. a symposium paper registered
    # twice); keep one per title.
    seen, unique = set(), []
    for p in sorted(papers, key=lambda p: p["doi"]):
        key = re.sub(r"[^a-z0-9]", "", p["title"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    papers = unique

    papers.sort(key=lambda p: (p["date"] or "", p["title"]), reverse=True)
    json.dump({"orcid": _paths.ORCID, "count": len(papers), "papers": papers},
              open(_paths.PUBLICATIONS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    untagged = sum(1 for p in papers if not p["themes"])
    print(f"Wrote {len(papers)} papers to {_paths.PUBLICATIONS.relative_to(_paths.ROOT)}"
          f" ({untagged} without a theme)")


if __name__ == "__main__":
    sys.exit(main())
