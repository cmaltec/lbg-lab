#!/usr/bin/env python3
"""
01b_fetch_stories.py

Collects the plain-language accounts of the lab's papers for the "Latest
research" page. Every paper repository carries PLAIN_LANGUAGE.md at its root,
with the article DOI in a hidden line, <!-- doi: 10.xxxx/yyyy -->. A story is
published here once both are true:

  1. the repository is public on GitHub (it is made public on acceptance), and
  2. its DOI is in content/publications.json, that is, the paper is out and
     listed on ORCID (01_fetch_publications.py runs first).

The page text is converted to HTML and stored with its images under
content/stories/<repo>/; content/stories/index.json lists the stories. Stories
already collected are kept if GitHub cannot be reached. The weekly build runs
this script, so a paper appears within a week of publication; a push to this
repository, or a repository_dispatch event of type "story", publishes it at once.

Usage:
  python scripts/01b_fetch_stories.py              # all public repositories of the owners in site.json
  python scripts/01b_fetch_stories.py --local DIR  # add one local paper repository, for previews in a scratch copy of this repo

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-11-12
"""

import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import markdown

import _paths

STORIES = _paths.CONTENT / "stories"
FILE = "PLAIN_LANGUAGE.md"
DOI_LINE = re.compile(r"<!--\s*doi:\s*(10\.\S+?)\s*-->", re.I)
USER_AGENT = f"lbg-lab/1.0 (mailto:{_paths.MAILTO})"


def get(url, tries=3, api=False):
    headers = {"User-Agent": USER_AGENT}
    if api and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
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


def public_repos(owner):
    repos, page = [], 1
    while True:
        batch = json.loads(get(f"https://api.github.com/users/{owner}/repos?type=owner&per_page=100&page={page}", api=True))
        repos += [r for r in batch if not r["private"] and not r["fork"] and not r["archived"]]
        if len(batch) < 100:
            return repos
        page += 1


def render(text, slug, blob_base):
    """Markdown to HTML. The first heading becomes the title; images are served
    from stories/<slug>/; other relative links point to the file on GitHub."""
    title = re.search(r"^#\s+(.+)$", text, re.M).group(1).strip()
    text = re.sub(r"^#\s+.+\n", "", text, count=1, flags=re.M)
    text = DOI_LINE.sub("", text)
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text)
    images = [i for i in images if not re.match(r"[a-z]+://", i)]
    html = markdown.markdown(text, extensions=["tables"])
    html = re.sub(r'<img alt="([^"]*)" src="(?![a-z]+://)([^"]+)"', rf'<img alt="\1" src="stories/{slug}/\2" loading="lazy"', html)
    html = re.sub(r'<a href="(?![a-z]+://|#|mailto:)([^"]+)"', rf'<a href="{blob_base}/\1"', html)
    m = re.search(r"<h2>In short</h2>\s*<p>(.*?)</p>", html, re.S) or re.search(r"<p>(?!<em>|<img)(.*?)</p>", html, re.S)
    summary = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    return title, html, summary, images


def collect(text, slug, fetch_file, repo_url, branch, papers):
    m = DOI_LINE.search(text)
    if not m:
        print(f"  {slug}: no DOI line yet, skipped")
        return None
    doi = m.group(1).lower().rstrip(".")
    paper = papers.get(doi)
    if not paper:
        print(f"  {slug}: DOI {doi} not in the publication list yet, skipped")
        return None
    title, html, summary, images = render(text, slug, f"{repo_url}/blob/{branch}")
    out = Path(tempfile.mkdtemp()) / slug
    out.mkdir(parents=True)
    for rel in images:
        data = fetch_file(rel)
        if data is None:
            print(f"  {slug}: image {rel} not found")
            continue
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(data)
    (out / "body.html").write_text(html, encoding="utf-8")
    first_img = f"stories/{slug}/{images[0]}" if images else None
    print(f"  {slug}: published ({paper['venue']}, {paper.get('date') or paper['year']})")
    return out, {"slug": slug, "title": title, "summary": summary, "image": first_img, "doi": doi,
                 "repo": repo_url, "date": paper.get("date") or str(paper["year"])}


def main():
    papers = {p["doi"].lower(): p for p in json.load(open(_paths.PUBLICATIONS, encoding="utf-8"))["papers"]}
    index_file = STORIES / "index.json"
    old = json.load(open(index_file, encoding="utf-8"))["stories"] if index_file.exists() else []
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        d = Path(sys.argv[2])
        got = collect((d / FILE).read_text(encoding="utf-8"), d.name.lower(),
                      lambda rel: (d / rel).read_bytes() if (d / rel).exists() else None,
                      f"https://github.com/cmaltec/{d.name}", "main", papers)
        if got:
            shutil.rmtree(STORIES / got[1]["slug"], ignore_errors=True)
            shutil.copytree(got[0], STORIES / got[1]["slug"])
            stories = sorted([s for s in old if s["slug"] != got[1]["slug"]] + [got[1]], key=lambda s: s["date"], reverse=True)
            json.dump({"stories": stories}, open(index_file, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return 0

    site = json.load(open(_paths.CONTENT / "site.json", encoding="utf-8"))
    owners = site.get("story_owners", ["cmaltec"])
    try:
        repos = [r for o in owners for r in public_repos(o)]
    except Exception as e:  # noqa: BLE001
        print(f"GitHub not reachable ({e}); keeping {len(old)} stories")
        return 0

    stories, staged = [], []
    for r in repos:
        branch = r["default_branch"]
        raw = f"https://raw.githubusercontent.com/{r['full_name']}/{branch}/"
        text = get(raw + FILE)
        if text is None:
            continue
        got = collect(text.decode("utf-8"), r["name"].lower(), lambda rel, raw=raw: get(raw + rel),
                      r["html_url"], branch, papers)
        if got:
            staged.append(got[0])
            stories.append(got[1])

    if STORIES.exists():
        shutil.rmtree(STORIES)
    STORIES.mkdir(parents=True)
    for d in staged:
        shutil.copytree(d, STORIES / d.name)
    stories.sort(key=lambda s: s["date"], reverse=True)
    json.dump({"stories": stories}, open(index_file, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(stories)} stories from {len(repos)} public repositories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
