#!/usr/bin/env python3
"""
03_add_story.py

Adds the plain-language account of one published paper to the "Latest
research" page. Run by hand, once, when the paper is out; nothing on the site
adds stories by itself. The weekly build only renders the stories already in
content/stories/.

The paper repository carries PLAIN_LANGUAGE.md at its root, with the article
DOI in a hidden line, <!-- doi: 10.xxxx/yyyy -->. The script refuses the story
unless that DOI is registered with Crossref, that is, the article is published.
Text between <!-- repo-only --> and <!-- /repo-only --> (scripts, notes about
the repository) is left out; the story page gives the full citation instead.
The page is converted to HTML and stored with its images under
content/stories/<slug>/, and content/stories/index.json records the story and
the article's reference.

Nothing is pushed. Check the build, then commit and push to publish.

Usage:
  python scripts/03_add_story.py PAPER_REPO_DIR        # local checkout of the paper repository
  python scripts/03_add_story.py owner/repo            # public repository on GitHub
  python scripts/03_add_story.py --remove SLUG         # take a story off the site

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-11-12
"""

import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import markdown

import _paths

STORIES = _paths.CONTENT / "stories"
INDEX = STORIES / "index.json"
FILE = "PLAIN_LANGUAGE.md"
DOI_LINE = re.compile(r"<!--\s*doi:\s*(10\.\S+?)\s*-->", re.I)
REPO_ONLY = re.compile(r"<!--\s*repo-only\s*-->.*?<!--\s*/repo-only\s*-->", re.S | re.I)
USER_AGENT = f"lbg-lab/1.0 (mailto:{_paths.MAILTO})"


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == tries - 1:
                raise
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
        time.sleep(2 ** attempt)


def reference(doi):
    """The article's reference: from the site's publication list if it is
    there already, otherwise from Crossref. None if the DOI is not registered."""
    for p in json.load(open(_paths.PUBLICATIONS, encoding="utf-8"))["papers"]:
        if p["doi"].lower() == doi:
            return {k: p.get(k) for k in ("title", "authors", "year", "date", "venue", "volume", "issue", "pages", "doi", "oa_url")}
    raw = get("https://api.crossref.org/works/" + urllib.parse.quote(doi) + "?mailto=" + _paths.MAILTO)
    if raw is None:
        return None
    w = json.loads(raw)["message"]
    parts = (w.get("published") or w.get("issued") or {}).get("date-parts", [[None]])[0]
    return {"title": re.sub(r"<[^>]+>", "", (w.get("title") or [""])[0]).strip(),
            "authors": [f'{a.get("given", "")} {a.get("family", "")}'.strip() or a.get("name", "") for a in w.get("author", [])],
            "year": parts[0], "date": "-".join(f"{x:02d}" for x in parts) if len(parts) == 3 else None,
            "venue": (w.get("container-title") or [""])[0], "volume": w.get("volume"), "issue": w.get("issue"),
            "pages": (w.get("page") or "").replace("-", "–") or w.get("article-number"), "doi": doi, "oa_url": None}


def render(text, slug, blob_base):
    """Markdown to HTML. The first heading becomes the title; images are served
    from stories/<slug>/; any other relative link points to the file on GitHub."""
    title = re.search(r"^#\s+(.+)$", text, re.M).group(1).strip()
    text = re.sub(r"^#\s+.+\n", "", text, count=1, flags=re.M)
    text = REPO_ONLY.sub("", DOI_LINE.sub("", text))
    images = [i for i in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text) if not re.match(r"[a-z]+://", i)]
    html = markdown.markdown(text, extensions=["tables"])
    html = re.sub(r'<img alt="([^"]*)" src="(?![a-z]+://)([^"]+)"', rf'<img alt="\1" src="stories/{slug}/\2" loading="lazy"', html)
    html = re.sub(r'<a href="(?![a-z]+://|#|mailto:)([^"]+)"', rf'<a href="{blob_base}/\1"', html)
    m = re.search(r"<h2>In short</h2>\s*<p>(.*?)</p>", html, re.S) or re.search(r"<p>(?!<em>|<img)(.*?)</p>", html, re.S)
    summary = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    return title, html, summary, images


def load_index():
    return json.load(open(INDEX, encoding="utf-8"))["stories"] if INDEX.exists() else []


def save_index(stories):
    STORIES.mkdir(parents=True, exist_ok=True)
    stories.sort(key=lambda s: s["paper"].get("date") or str(s["paper"]["year"]), reverse=True)
    json.dump({"stories": stories}, open(INDEX, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--remove":
        slug = sys.argv[2]
        save_index([s for s in load_index() if s["slug"] != slug])
        shutil.rmtree(STORIES / slug, ignore_errors=True)
        print(f"removed {slug}; rebuild, commit, and push to take it off the site")
        return 0
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    src = sys.argv[1]
    if Path(src).is_dir():
        d = Path(src)
        slug = d.name.lower()
        read = lambda rel: (d / rel).read_bytes() if (d / rel).exists() else None
        blob_base = f"https://github.com/cmaltec/{d.name}/blob/main"
    else:
        meta = json.loads(get(f"https://api.github.com/repos/{src}") or b"{}")
        if not meta or meta.get("private"):
            print(f"{src}: not a public GitHub repository; use a local checkout instead")
            return 1
        raw = f"https://raw.githubusercontent.com/{src}/{meta['default_branch']}/"
        slug = meta["name"].lower()
        read = lambda rel: get(raw + rel)
        blob_base = f"{meta['html_url']}/blob/{meta['default_branch']}"

    text = read(FILE)
    if text is None:
        print(f"{src}: no {FILE}")
        return 1
    text = text.decode("utf-8")
    m = DOI_LINE.search(text)
    if not m:
        print(f"{FILE} has no DOI line (<!-- doi: 10.xxxx/yyyy -->); add the article DOI first")
        return 1
    doi = m.group(1).lower().rstrip(".")
    paper = reference(doi)
    if not paper:
        print(f"DOI {doi} is not registered with Crossref; the story waits until the article is published")
        return 1

    title, html, summary, images = render(text, slug, blob_base)
    out = STORIES / slug
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for rel in images:
        data = read(rel)
        if data is None:
            print(f"warning: image {rel} not found")
            continue
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(data)
    (out / "body.html").write_text(html, encoding="utf-8")

    stories = [s for s in load_index() if s["slug"] != slug]
    stories.append({"slug": slug, "title": title, "summary": summary, "image": f"stories/{slug}/{images[0]}" if images else None,
                    "doi": doi, "added": date.today().isoformat(), "paper": paper})
    save_index(stories)
    print(f"added {slug}: {paper['venue']}, {paper.get('date') or paper['year']}")
    print("next: python scripts/02_build_site.py, check _site/latest.html, then commit and push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
