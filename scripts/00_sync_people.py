#!/usr/bin/env python3
"""
00_sync_people.py

Writes content/people/team.json from the CV data files (postdocs, current and
completed PhD students, MSc students, visiting scholars), so the team page
and the CV come from one source. Runs on the machine that holds the CV
folder; the GitHub build uses the committed team.json.

Current members are postdocs whose end year has not passed and students in
progress. Everyone else is listed as alumni. Chair/co-chair markers and
titles are stripped; co-advised students are noted as such.

Usage:
  python scripts/00_sync_people.py          # CV folder found via the tracker
  CV_DATA_DIR=/path/to/CV_Rmd/data python scripts/00_sync_people.py

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-10-08
"""

import csv
import json
import re
import sys
from datetime import date

import _paths


def rows(name):
    path = _paths.CV_DATA_DIR / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def clean(name):
    """Name without 'Dr.', chair markers (*, **) or award marks (!)."""
    name = re.sub(r"^Dr\.?\s+", "", name)
    return re.sub(r"[\s,]*[*!]+\s*$", "", name).strip()


def co_advised(name):
    return "**" in name


def main():
    if _paths.CV_DATA_DIR is None or not _paths.CV_DATA_DIR.is_dir():
        print("CV data folder not found; set CV_DATA_DIR.", file=sys.stderr)
        return 1
    year = date.today().year

    team = {"pi": {"name": "Christian Maltecca", "role": "Principal investigator"},
            "current": [], "alumni": [], "visitors": []}

    for r in rows("postdocs.csv"):
        entry = {"name": clean(r["who"]), "role": "Postdoctoral researcher",
                 "topic": r.get("area", ""),
                 "years": f'{r["start_date"]}–{r["end_date"]}' if r["start_date"] != r["end_date"]
                 else r["start_date"]}
        if r["end_date"] and int(r["end_date"]) >= year:
            team["current"].append(entry)
        else:
            team["alumni"].append(entry)

    for r in rows("curphd.csv"):
        team["current"].append({"name": clean(r["who"]), "role": "PhD student",
                                "topic": "", "co_advised": co_advised(r["who"])})

    for r in rows("phd.csv"):
        team["alumni"].append({"name": clean(r["who"]), "role": "PhD", "years": r["end_date"],
                               "topic": r.get("what", "").rstrip("."),
                               "co_advised": co_advised(r["who"])})
    for r in rows("msc.csv"):
        team["alumni"].append({"name": clean(r["who"]), "role": "MSc", "years": r["end_date"],
                               "topic": r.get("what", "").rstrip("."),
                               "co_advised": co_advised(r["who"])})

    for r in rows("internationals.csv"):
        team["visitors"].append({"name": clean(r["who"]), "from": r.get("where", ""),
                                 "years": r.get("when", "")})

    team["alumni"].sort(key=lambda e: str(e.get("years", "")), reverse=True)
    _paths.PEOPLE.mkdir(parents=True, exist_ok=True)
    out = _paths.PEOPLE / "team.json"
    json.dump(team, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Wrote {out.relative_to(_paths.ROOT)}: {len(team['current'])} current, "
          f"{len(team['alumni'])} alumni, {len(team['visitors'])} visitors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
