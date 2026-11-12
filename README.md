# Livestock Breeding and Genomics Lab website

Static website for the Livestock Breeding and Genomics Lab, Department of Animal Science, NC State University. Publications update themselves weekly; people and text come from small content files.

## Content

| What | Where | Updated by |
|---|---|---|
| Publications | `content/publications.json` | `01_fetch_publications.py`, weekly on GitHub (ORCID + OpenAlex) |
| Research themes and the keywords that assign papers to them | `content/themes.json` | Hand-edited |
| Team, alumni, visiting scholars | `content/people/team.json` | `00_sync_people.py`, from the CV data folder |
| Lab name, mission line, contact | `content/site.json` | Hand-edited |
| Plain-language stories of published papers ("Latest research" page) | `content/stories/` | `03_add_story.py`, run by hand at publication, from the paper repository's `PLAIN_LANGUAGE.md` |
| Papers to leave out | `content/exclude.json` (`{"dois": [...]}`) | Hand-edited, optional |

The CV data folder is not in this repository. `00_sync_people.py` reads it from the `CV_DATA_DIR` environment variable.

## Scripts, in run order

| # | Script | Produces |
|---|---|---|
| 00 | `scripts/00_sync_people.py` | `content/people/team.json` (local only; needs `CV_DATA_DIR`) |
| 01 | `scripts/01_fetch_publications.py` | `content/publications.json` |
| 02 | `scripts/02_build_site.py` | `_site/` (the website) |
| 03 | `scripts/03_add_story.py` | One story in `content/stories/`; by hand, when a paper is published |

```
CV_DATA_DIR=/path/to/CV_Rmd/data python scripts/00_sync_people.py
python scripts/01_fetch_publications.py
python scripts/02_build_site.py
open _site/index.html
```

`.github/workflows/site.yml` runs 01 and 02 every Monday and on each push, and deploys `_site/` to GitHub Pages once the repository is public.

## Latest research

Stories go on the site only when Christian adds them, at publication. Each paper repository carries `PLAIN_LANGUAGE.md` at its root, with the article DOI in a hidden line, `<!-- doi: 10.xxxx/yyyy -->`. When the paper is out:

```
python scripts/03_add_story.py /path/to/paper-repo     # or owner/repo if public
python scripts/02_build_site.py && open _site/latest.html
git add content/stories && git commit -m "Story: <paper>" && git push
```

The script refuses a DOI that Crossref does not know, so a story cannot go up before the article, and it shows the reference the DOI points to and waits for a yes before adding anything. Text marked `<!-- repo-only -->` in the paper repository is left out, and the story page gives the full citation. `--remove SLUG` takes a story down.

The "Latest research" page shows the six newest stories; the archive lists all of them by year, and each paper with a story links to it from the publication list. The menu link appears with the first story.

## NC State brand

The site follows brand.ncsu.edu: the NC State utility bar (loaded from cdn.ncsu.edu) is the first element of every page, Wolfpack Red predominates with black and white, each research theme uses one expanded-palette colour (Bio-Indigo, Genomic Green, Carmichael Aqua), and type is Roboto, Roboto Condensed and Roboto Slab from Google Fonts. All text colours pass WCAG AA on white.

## Requirements

Python 3.10 or newer, Jinja2, and Markdown (`pip install -r requirements.txt`). No commercial dependencies. The fetch uses the public ORCID and OpenAlex APIs and needs no keys.

## License and contact

MIT (see `LICENSE`). Christian Maltecca, cmaltec@ncsu.edu.
