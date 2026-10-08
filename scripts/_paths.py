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

# The CV data folder (for 00_sync_people.py) lives outside the repo; give its
# location in the environment rather than in code.
CV_DATA_DIR = Path(os.environ["CV_DATA_DIR"]) if os.environ.get("CV_DATA_DIR") else None
