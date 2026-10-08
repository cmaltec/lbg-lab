#!/usr/bin/env python3
"""
_paths.py

Paths used by every script, resolved from the repository root so nothing
depends on where the repo is checked out.

Author: Christian Maltecca
E-mail: cmaltec@ncsu.edu
Date: 2026-10-08
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTENT = ROOT / "content"          # hand-edited and synced site content
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
BUILD = ROOT / "_site"              # generated site, not tracked
CACHE = ROOT / ".cache"             # API responses, not tracked

PUBLICATIONS = CONTENT / "publications.json"
THEMES = CONTENT / "themes.json"
PEOPLE = CONTENT / "people"

ORCID = "0000-0002-9996-4680"
MAILTO = "cmaltec@ncsu.edu"

# The CV data folder (for 00_sync_people.py) lives outside the repo. It is
# taken from CV_DATA_DIR if set, otherwise found next to the Scholar tracker,
# whose location the tracker records in ~/.config/scholar-tracker/root.
def _cv_data_dir():
    if os.environ.get("CV_DATA_DIR"):
        return Path(os.environ["CV_DATA_DIR"])
    pointer = Path.home() / ".config" / "scholar-tracker" / "root"
    if pointer.exists():
        candidate = Path(pointer.read_text().splitlines()[0]).parent / "CV" / "CV_Rmd" / "data"
        if candidate.is_dir():
            return candidate
    return None


CV_DATA_DIR = _cv_data_dir()
