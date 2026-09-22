"""Track the entries of the application list.

The entries themselves -- job applications and the other Eigenbemühungen --
live in entries.py; this module only stores them and lays them out as a
LaTeX summary. All files live in the output directory configured in config.py.
"""

import datetime
import json
import os

import config
import entries

APPLICATIONS_FILE = "applications.json"
APPLICATIONS_TABLE = "applications.tex"
DOC_HEADER = r"""\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage[margin=2cm]{geometry}
\usepackage{longtable}
\usepackage{xcolor}
\usepackage{hyperref}
\definecolor{linkgray}{gray}{0.35}
\hypersetup{colorlinks=true, allcolors=linkgray}
\renewcommand{\arraystretch}{1.5}
\setlength{\tabcolsep}{10pt}
\begin{document}
\section*{Übersicht der Eigenbemühungen}
Zeitraum: %s -- %s
"""
SECTION_HEADER = r"""\subsection*{%s}
\begin{longtable}{|c|p{0.55\textwidth}|p{0.33\textwidth}|}
\hline
\textbf{Nr.} & \textbf{%s} & \textbf{%s} \\
\hline
\endhead
"""
SECTION_FOOTER = "\\end{longtable}\n"
DOC_FOOTER = "\\end{document}\n"


def output_path(filename):
    """Return the path of a tracker file inside the output directory.

    The output directory is created if it does not exist.

    Args:
        filename: Name of the file inside the output directory.

    Returns:
        Filesystem path as a string.
    """
    output_dir = config.get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)


def load_applications():
    """Load the entries of the application list.

    Returns:
        List of Entry objects. Empty if nothing was saved yet.
    """
    path = output_path(APPLICATIONS_FILE)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [entries.from_dict(data) for data in json.load(f)]


def save_applications(applications):
    """Write the application list and its LaTeX table to the output directory.

    Args:
        applications: List of Entry objects to persist.
    """
    with open(output_path(APPLICATIONS_FILE), "w", encoding="utf-8") as f:
        json.dump([entry.to_dict() for entry in applications], f, indent=2,
                  ensure_ascii=False)
    write_latex_table(applications)


def format_period(start, end, oldest):
    """Return the ends of the period a summary covers, as printed dates.

    Which entries a summary holds is not otherwise visible in it -- a month
    with little to report looks like a year with little to report -- so the
    period it was generated for is stated under the title, always as a
    range between two dates. A bound left open is filled in with the date
    the summary reaches to anyway: its oldest entry at the near end, today
    at the far end. A range is never printed backwards, so a start date in
    the future closes the period on itself.

    Args:
        start: Optional ISO date (YYYY-MM-DD) of the lower bound.
        end: Optional ISO date (YYYY-MM-DD) of the upper bound.
        oldest: ISO date of the oldest entry the summary holds, or "" when
            it holds none and there is nothing to open the range on.

    Returns:
        The two ends of the period as a (start, end) pair of dates in the
        format the summary prints.
    """
    end = end or datetime.date.today().isoformat()
    start = start or oldest or end
    return (entries.format_date(start), entries.format_date(max(start, end)))


def write_latex_table(applications, start="", end=""):
    """Write the entries acted on as a LaTeX summary to the output directory.

    Only entries the effort was actually made on are included, and an entry
    belongs in a period whenever one of its steps falls inside it: an
    application sent in August and interviewed for in September is part of
    both months, each time with its whole timeline. What counts as a step is
    up to the kind, so the day of a job fair counts only once it has been
    gone to. Each kind gets its own section, numbered from one, so that the
    applications stay countable next to the other efforts. Within a section,
    each row shows what the entry was about next to its timeline, the
    entries ordered by the day the effort started. The period the bounds
    below stand for is named under the title, so that a summary says what it
    covers; the entries being sorted, the oldest of them is the one an open
    lower bound reaches back to.

    Args:
        applications: List of Entry objects.
        start: Optional ISO date (YYYY-MM-DD). When given, entries nothing
            happened on since then are left out; when empty, there is no
            lower bound.
        end: Optional ISO date (YYYY-MM-DD). When given, entries nothing
            happened on until then are left out; when empty, there is no
            upper bound. Both bounds are inclusive.
    """
    acted_on = sorted((a for a in applications
                       if a.reportable and a.changed_between(start, end)),
                      key=lambda a: a.effort_date)
    sections = []
    for entry_class in entries.KINDS:
        of_kind = [a for a in acted_on if a.kind == entry_class.kind]
        if not of_kind:
            continue
        header = SECTION_HEADER % (entry_class.section, *entry_class.columns)
        rows = [entry.latex_row(number)
                for number, entry in enumerate(of_kind, start=1)]
        sections.append(header + "".join(rows) + SECTION_FOOTER)
    preamble = DOC_HEADER % format_period(
        start, end, acted_on[0].effort_date if acted_on else "")
    document = preamble + "".join(sections) + DOC_FOOTER
    with open(output_path(APPLICATIONS_TABLE), "w", encoding="utf-8") as f:
        f.write(document)


def add_application(service, record, priority=None, applied="", kind="job",
                    contact="", saved="", attended=False, invited=""):
    """Add an entry to the application list with an empty timeline.

    Args:
        service: Where the entry came from: "manual" for entries added by
            hand, the name of a job board for those saved by the search of
            earlier versions.
        record: Dictionary with the entry's id, title, company, location,
            published date and url.
        priority: Optional priority level (one of entries.PRIORITIES). When
            given, it is stored on the entry; when omitted the entry has no
            chosen priority.
        applied: Optional ISO date (YYYY-MM-DD) of the first action. When
            given it marks the entry as already acted on; when omitted the
            timeline starts empty and the entry is left out of the summary.
        kind: Which kind of Eigenbemühung this is, a key of entries.REGISTRY.
            Defaults to a plain job application.
        contact: Optional contact person, e.g. of a recruiter.
        saved: Optional ISO date (YYYY-MM-DD) the entry was noted down on.
            Defaults to today.
        attended: Whether an event was already attended.
        invited: Optional ISO date (YYYY-MM-DD) of the second step of the
            timeline, e.g. the day an event was registered for.
    """
    applications = load_applications()
    entry_class = entries.REGISTRY.get(kind, entries.Entry)
    known = {key: value for key, value in record.items()
             if key in entries.RECORD_FIELDS}
    extra = {key: value for key, value in record.items()
             if key not in entries.RECORD_FIELDS}
    applications.append(entry_class(
        service=service, applied=applied, invited=invited, contact=contact,
        saved=saved, attended=attended,
        priority=priority if priority in entries.PRIORITIES else None,
        extra=extra, **known))
    save_applications(applications)


def update_status(index, status, date=""):
    """Set the status of a saved entry by updating its timeline.

    Args:
        index: Index of the entry in the saved list.
        status: New status, one of entries.STATUSES.
        date: Optional ISO date (YYYY-MM-DD) the status was reached on.
            Defaults to today.
    """
    applications = load_applications()
    applications[index].set_status(status, date)
    save_applications(applications)


def delete_application(index):
    """Remove a saved entry from the application list.

    Args:
        index: Index of the entry in the saved list.
    """
    applications = load_applications()
    applications.pop(index)
    save_applications(applications)


def update_priority(index, priority):
    """Set or clear the priority of a saved entry.

    Args:
        index: Index of the entry in the saved list.
        priority: New priority (one of entries.PRIORITIES), or None to clear.
    """
    applications = load_applications()
    applications[index].set_priority(priority)
    save_applications(applications)
