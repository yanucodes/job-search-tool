"""Track seen jobs and the entries of the application list.

The entries themselves -- job applications and the other Eigenbemühungen --
live in entries.py; this module only stores them and lays them out as a
LaTeX summary. All files live in the output directory configured in search.py.
"""

import datetime
import json
import os

import entries
import search

SEEN_FILE = "seen.json"
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
Stand: %s
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
    output_dir = search.get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)


def load_seen():
    """Load the set of jobs the user has already seen.

    Returns:
        Set of (service, job_id) tuples. Empty if nothing was seen yet.
    """
    path = output_path(SEEN_FILE)
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {(service, job_id) for service, job_id in json.load(f)}


def mark_seen(service, job_id):
    """Record that the user has seen a job.

    Args:
        service: Name of the job board the job came from.
        job_id: Identifier of the job on that board.
    """
    seen = load_seen()
    seen.add((service, job_id))
    with open(output_path(SEEN_FILE), "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2, ensure_ascii=False)


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


def write_latex_table(applications, start="", end=""):
    """Write the entries acted on as a LaTeX summary to the output directory.

    Only entries with a first action recorded are included. Each kind of
    Eigenbemühung gets its own section, numbered from one, so that the
    applications stay countable next to the other efforts. Within a section,
    each row shows what the entry was about next to its timeline.

    Args:
        applications: List of Entry objects.
        start: Optional ISO date (YYYY-MM-DD). When given, entries acted on
            before it are left out; when empty, there is no lower bound.
        end: Optional ISO date (YYYY-MM-DD). When given, entries acted on
            after it are left out; when empty, there is no upper bound. Both
            bounds are inclusive.
    """
    acted_on = sorted((a for a in applications if a.applied
                       and (not start or a.applied >= start)
                       and (not end or a.applied <= end)),
                      key=lambda a: a.applied)
    sections = []
    for entry_class in entries.KINDS:
        of_kind = [a for a in acted_on if a.kind == entry_class.kind]
        if not of_kind:
            continue
        header = SECTION_HEADER % (entry_class.section, *entry_class.columns)
        rows = [entry.latex_row(number)
                for number, entry in enumerate(of_kind, start=1)]
        sections.append(header + "".join(rows) + SECTION_FOOTER)
    document = (DOC_HEADER % entries.format_date(
        datetime.date.today().isoformat()) + "".join(sections) + DOC_FOOTER)
    with open(output_path(APPLICATIONS_TABLE), "w", encoding="utf-8") as f:
        f.write(document)


def add_application(service, record, priority=None, applied="", kind="job",
                    contact="", saved=""):
    """Add an entry to the application list with an empty timeline.

    Args:
        service: Name of the job board the job came from, or "manual".
        record: Normalized job record as returned by the board's normalize().
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
    """
    applications = load_applications()
    entry_class = entries.REGISTRY.get(kind, entries.Entry)
    known = {key: value for key, value in record.items()
             if key in entries.RECORD_FIELDS}
    extra = {key: value for key, value in record.items()
             if key not in entries.RECORD_FIELDS}
    applications.append(entry_class(
        service=service, applied=applied, contact=contact, saved=saved,
        priority=priority if priority in entries.PRIORITIES else None,
        extra=extra, **known))
    save_applications(applications)


def update_status(index, status):
    """Set the status of a saved entry by updating its timeline.

    Args:
        index: Index of the entry in the saved list.
        status: New status, one of entries.STATUSES.
    """
    applications = load_applications()
    applications[index].set_status(status)
    save_applications(applications)


def delete_application(index):
    """Remove a saved entry from the application list.

    The job is kept in the seen list (re-asserted here in case the entry
    predates seen tracking or the seen file was cleared), so it will not
    reappear in future searches.

    Args:
        index: Index of the entry in the saved list.
    """
    applications = load_applications()
    entry = applications[index]
    mark_seen(entry.service, entry.id)
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
