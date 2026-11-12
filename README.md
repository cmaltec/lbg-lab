# Livestock Breeding and Genomics Lab website

Static website for the Livestock Breeding and Genomics Lab, Department of Animal Science, NC State University. Publications update themselves weekly; people and text come from small content files.

## Content

| What | Where | Updated by |
|---|---|---|
| Publications | `content/publications.json` | `01_fetch_publications.py`, weekly on GitHub (ORCID + OpenAlex) |
| Research themes and the keywords that assign papers to them | `content/themes.json` | Hand-edited |
| Team, alumni, visiting scholars | `content/people/team.json` | `00_sync_people.py`, from the CV data folder |
| Lab name, mission line, contact | `content/site.json` | Hand-edited |
| Plain-language stories of published papers ("Latest research" page) | `content/stories/` | `01b_fetch_stories.py`, weekly on GitHub, from each paper repository's `PLAIN_LANGUAGE.md` |
| Papers to leave out | `content/exclude.json` (`{"dois": [...]}`) | Hand-edited, optional |

The CV data folder is not in this repository. `00_sync_people.py` reads it from the `CV_DATA_DIR` environment variable.

## Scripts, in run order

| # | Script | Produces |
|---|---|---|
| 00 | `scripts/00_sync_people.py` | `content/people/team.json` (local only; needs `CV_DATA_DIR`) |
| 01 | `scripts/01_fetch_publications.py` | `content/publications.json` |
| 01b | `scripts/01b_fetch_stories.py` | `content/stories/` (stories of published papers) |
| 02 | `scripts/02_build_site.py` | `_site/` (the website) |

```
CV_DATA_DIR=/path/to/CV_Rmd/data python scripts/00_sync_people.py
python scripts/01_fetch_publications.py
python scripts/01b_fetch_stories.py
python scripts/02_build_site.py
open _site/index.html
```

`.github/workflows/site.yml` runs 01 and 02 every Monday and on each push, and deploys `_site/` to GitHub Pages once the repository is public.

## Latest research

Each paper repository carries `PLAIN_LANGUAGE.md` at its root, with the article DOI in a hidden first line after the title, `<!-- doi: 10.xxxx/yyyy -->`. A story goes on the site when the repository is public and the DOI is in the publication list, that is, when the paper is out. The weekly build picks it up; to publish at once, run the workflow by hand or send a `story` event:

```
gh api repos/cmaltec/lbg-lab/dispatches -f event_type=story
```

The "Latest research" menu link appears with the first story. To preview a story before publication, copy this repository to a scratch folder, add the paper to `content/publications.json` there, and run `01b_fetch_stories.py --local <paper repo>` then `02_build_site.py`.

## NC State brand

The site follows brand.ncsu.edu: the NC State utility bar (loaded from cdn.ncsu.edu) is the first element of every page, Wolfpack Red predominates with black and white, each research theme uses one expanded-palette colour (Bio-Indigo, Genomic Green, Carmichael Aqua), and type is Roboto, Roboto Condensed and Roboto Slab from Google Fonts. All text colours pass WCAG AA on white.

## Requirements

Python 3.10 or newer, Jinja2, and Markdown (`pip install -r requirements.txt`). No commercial dependencies. The fetch uses the public ORCID and OpenAlex APIs and needs no keys.

## License and contact

MIT (see `LICENSE`). Christian Maltecca, cmaltec@ncsu.edu.
