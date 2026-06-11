# job-search-tool

A command-line tool that searches job boards, shows each new posting with
its description, and lets you save it to an application list or discard it.
Jobs you have already reviewed are remembered by their job ID and are not
shown again. Currently supported job board: [arbeitsagentur.de](https://www.arbeitsagentur.de).

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```sh
python main.py
```

From the main menu you can:

1. **Search and review new jobs** — runs every saved search and shows each
   unseen job with its description. For each job choose `s` to save it to
   the application list, `d` to discard it, or `q` to stop reviewing
   (remaining jobs stay unseen and come up next time).
2. **Show application list** — lists the jobs you saved with their status,
   and lets you update a status (`to apply`, `applied`, `interview`,
   `offer`, `rejected`).
3. **Show search configurations** — add, update or remove saved searches.
4. **Set output directory** — choose where results are stored.

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
