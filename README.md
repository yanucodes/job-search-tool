# job-search-tool

A tool that searches job boards, shows each new posting with its
description, and lets you save it to an application list or discard it.
Jobs you have already reviewed are remembered by their job ID and are not
shown again. Searches are configured with a command-line interface;
reviewing jobs and managing applications happens in a small web interface.
Currently supported job board:
[arbeitsagentur.de](https://www.arbeitsagentur.de).

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```sh
python main.py
```

From the main menu you can:

1. **Show search configurations** — add, update or remove saved searches.
2. **Set output directory** — choose where results are stored.

## Web interface

```sh
python app.py
```

Then open <http://127.0.0.1:5000>. Search configurations are managed with
the command-line interface; the web interface uses the same saved searches
and output files.

- **Review new jobs** (`/review`) — searches all job boards once and shows
  one new job at a time with its description. *Add to my list* saves the
  job to the application list, *Mark as seen* discards it; either way the
  next job appears. *Search again* re-runs the search.
- **My applications** (`/applications`) — lists the saved jobs with their
  status. Click an entry to see its details and change the status.
- **Generate PDF** (`/applications/pdf`) — compiles the LaTeX table of
  applications with `pdflatex` (must be installed) and opens the PDF.

## Output directory

All results live in the configured output directory:

- `seen.json` — IDs of jobs you have already reviewed (for arbeitsagentur
  this is the posting's `refnr`).
- `applications.json` — the jobs you plan to apply for, with saved date and
  application status.
- `applications.tex` — the same list as a LaTeX table, regenerated on every
  change. Compile it with `pdflatex applications.tex` for a PDF overview.

## Adding another job board

Create a module in `jobboards/` that provides four functions:

- `get_config(config=None)` — interactively collect search parameters and
  return them as a dictionary (or `None` if the user cancels).
- `search(params)` — run the search and return a list of raw job
  dictionaries (or `None` on failure).
- `normalize(job)` — convert a raw job to the standard record: a dictionary
  with `id`, `title`, `company`, `location`, `published` and `url` keys.
  `id` must be stable, it is what the seen-job tracking is keyed on.
- `description(record)` — return the plain-text description for a
  normalized record (or `None` if unavailable). This is the only function
  allowed to be slow; it is called once per job shown to the user.

Then register the module in `SERVICES` in `search.py`. See
`jobboards/arbeitsagentur.py` for a reference implementation.

## Development and AI usage

I designed and wrote the initial structure of this project myself, and
later extended it with the help of AI tools. Every line of code is
reviewed, understood and maintained by me.
