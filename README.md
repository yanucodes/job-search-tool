# job-search-tool

A tool for documenting a job search: what you applied to, who you talked
to, where you went, how far each of them got, and a PDF summary of all of
it (in German, so it can be used as Nachweis der Eigenbemühungen for the
Arbeitsagentur). Entries are added and worked through in a small web
interface.

> **Versions.** Up to [`v1.0.0`](../../releases/tag/v1.0.0) the tool also
> searched job boards and offered each new posting for review. The
> Arbeitsagentur API that search depended on has changed, and most job
> boards offer no public API to build on, so from v2 the tool concentrates
> on tracking. The last version with search stays available under that tag.

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

The one setting is where the tool keeps its files. Without a
`config.json` next to `app.py` everything lands in `results/`; to keep it
elsewhere, put the directory in that file:

```json
{
  "output_dir": "~/job-search-dir"
}
```

## Web interface

```sh
python app.py
```

Then open <http://127.0.0.1:5000>. Starting the app with `flask run`
instead reads a local `.flaskenv` file, so a line like `FLASK_RUN_PORT=5002`
there serves the app on that port. Every page carries the same two bars:
the navigation between the pages below, and a toolbar with *Add manually*
and *Generate PDF*, so both are always one click away.

- **My applications** (`/applications`) — lists the saved job applications
  with their status and priority, grouped by how far they got: still to
  apply for, already applied to, and turned down. Each entry shows its
  status, its priority and the date it stands on at a glance — the day it is
  about, which is the day you applied, first made contact, or the day an
  event takes place, and the day you noted it down while nothing has
  happened yet. Click an entry to see its details and change
  the status (`to apply`, `applied`, `invited`, `interview`, `offer`,
  `rejected`): pick the new status, pick the date it was reached on — the
  field starts on today, but any past date will do — and press *Change
  status*. That builds a timeline of the application process. An
  application can go to `interview` more than once: each date is kept
  alongside the earlier ones, so a second and third round are all recorded.
  Falling back to an earlier status clears them again, together with the
  rest of the later timeline. You can also set or clear
  the priority here, or remove the entry from the list with *Delete*.
  Jobs still to apply for are ordered by priority
  (highest first, unprioritised last); jobs already applied to by the date
  you applied (oldest first), turned-down jobs by the date of the decision.
  As the list grows, the page keeps to what is current: it shows only the
  applications whose status changed in the last two weeks — any date on
  their timeline, or the day they were noted down while the timeline is
  still empty. The filter above the list picks another period, with the
  same *from* and *to* fields as the PDF summary, each optional; *Last 2
  weeks* goes back to the default and *Show all* lifts the filter. The line
  next to it says how many applications are shown out of how many are
  saved.
- **Recruiter contacts** (`/recruiters`), **Job fairs** (`/fairs`) and
  **Networking** (`/networking`) — one page per other kind of entry (see
  below), reached from the same navigation bar. Those efforts are recorded
  rather than worked through, so each page is a single list, newest first,
  with the count in its heading. The entries open, change status and delete
  exactly like the applications do.
- **Add manually** (`/new`) — adds an entry to the list. The *Kind of
  entry* dropdown at the top chooses what sort of effort is being recorded (see
  below) and reloads the form with the fields and names of that kind, so a
  recruiter contact asks for the agency and who wrote to you rather than for
  a job title and a posting. Four fields are always required, whatever they
  are called, because the PDF summary is built from them; the rest are
  optional. Filling in the date field records an effort already made, so a
  job application starts in the *Applied* group instead of *To apply*.
  Saving returns you to the page of the kind you added.
- **Generate PDF** (`/pdf`) — compiles a PDF summary of the
  entries you acted on and how each went, using `pdflatex` (must be
  installed). Each kind of entry gets its own section, numbered from one
  and ordered by date, so applications stay countable next to the other
  efforts. The two date fields next to the button limit the summary to a
  period: with a start date only entries acted on on or after it are
  included, with an end date only those on or before it. Both are optional
  — leaving them empty summarizes everything you acted on. The period is
  printed under the title as `Zeitraum`, so the summary says what it
  covers, and always as a range between two dates: a bound you left open is
  filled in with the date the summary reaches to anyway — the oldest entry
  in it at the start, today at the end. Generating without either date
  therefore reads `Zeitraum: 04.03.2026 -- 31.08.2026`. That line is the
  whole header; the day the file was generated on is not part of what is
  reported.

## Kinds of entry

Not every documented job-search effort is an application to a posting.
Contacting a private recruiter or visiting a job fair counts too, and has to
be reported with its own wording rather than as "Beworben". Each kind is a
class in `entries.py` carrying the German labels it prints with:

| Kind | Class | Page | PDF section |
|---|---|---|---|
| Job application | `Entry` | `/applications` | Bewerbungen |
| Recruiter contact | `RecruiterContact` | `/recruiters` | Vermittlerkontakte |
| Job fair | `FairVisit` | `/fairs` | Jobmessen |
| Networking | `NetworkEffort` | `/networking` | Sonstige Eigenbemühungen |

Every kind shares the same timeline — a first action, a follow-up, a
conversation and an outcome — and only relabels it, so the status dropdown
and the date tracking work the same everywhere. A recruiter contact set to
*invited* therefore reads "Unterlagen übermittelt" where an application
reads "Einladung erhalten". Several conversations are numbered in the
summary — "Vorstellungsgespräch 1", "Vorstellungsgespräch 2" — while a
single one stays unnumbered. A kind may also change the statuses it can be
in: a job fair goes *planned* → *registered* → *attended*, the stages of an
application not applying to it.

What a kind does not share is whether its stages follow one another. An
application is a ladder — an invitation comes before an interview — so
setting it back to an earlier status clears the later dates, which is how a
status set by mistake is taken back. A recruiter contact is not: documents
go out before or after a first call, and recording one leaves the others
where they are. There, the status shown is the stage acted on last rather
than the furthest one reached, and the way to undo a mistake is *not
contacted yet*, which clears the whole timeline.

Only entries the effort was actually made on reach the PDF summary, and each
kind decides what that means, as well as which day it counts as made on.
That makes the list usable for planning as well as for reporting: a job fair
you merely intend to visit shows up under *Job fairs* to keep track of but
stays out of the summary until you do something about it.

Going to a fair is two documented steps, and the summary reports both:
`Angemeldet am` when you signed up and `Besucht am` the day you were there.
Set the status to *registered* with the date you signed up on, and to
*attended* with the day of the fair, which is what that second date is.
Signing up is an effort in itself, so a fair enters the summary from the day
you registered, counted on that day and listing the day it takes place as
`Findet statt am` until you have been. A fair that took no registration is
reported once visited, and has the one line.

A fair whose day has not come yet cannot have been visited, so ticking
*Attended* ahead of time claims nothing: the entry reads as registered and
turns into a visit on the day itself.

The web interface is in English and the PDF summary in German, because the
summary is what the Arbeitsagentur is handed. The timeline in an entry's
details is shown in German too, so what you see there is what will be
reported. Both list it in date order, so it reads as the course of events
even where the stages did not follow one another.

To add a kind, subclass `Entry`, override its class attributes — the labels,
the path of its page, which fields the form offers and what they are called
— and list it in `entries.KINDS`. The page and its navigation link follow
from that; nothing in `app.py` needs to know about it.

## Demo

```sh
python app.py --demo
```

Runs the web interface on <http://127.0.0.1:5055> against the obviously
fake entries in `demo/results`, so you can click through the pages and
generate the summary without recording anything of your own first. The
entries are found next to `app.py` rather than through the configuration,
so your own files stay out of reach whatever is configured, and the demo's
own port leaves an instance on the real ones running.
`demo/results/applications.pdf` is the summary those entries produce, for
a look at the output without running anything.

## Output directory

Everything the tool saves lives in the configured output directory:

- `applications.json` — the entries you saved, with saved date and the
  timeline of the process: the dates of the first action, the invitation,
  the conversation and the final decision, and what the decision was. The
  `kind` key says which sort of effort the entry records. An entry with a
  chosen priority also has a `priority` key (`1` high, `2` moderate, `3`
  low), and one with a contact person a `contact` key; both are absent when
  unset. Entries are loaded as the objects defined in `entries.py` and
  written back with their `to_dict()`.
- `applications.tex` — a LaTeX summary of the entries you acted on and their
  outcomes, one section per kind. It is rewritten whenever the list changes,
  and again whenever *Generate PDF* runs — then holding only the entries of
  the chosen date range. Compile it with `pdflatex applications.tex` for a
  PDF overview.
- `applications.pdf` — the compiled overview, next to the `.aux`, `.log`
  and `.out` files `pdflatex` leaves behind.

## Development and AI usage

I designed and wrote the initial structure of this project myself, and
later extended it with the help of AI tools. Every line of code is
reviewed, understood and maintained by me.

## License

BSD 3-Clause — see [LICENSE](LICENSE).
