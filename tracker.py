"""Track seen jobs and the list of jobs the user plans to apply for.

All files live in the output directory configured in search.py.
"""

import datetime
import json
import os

import search

SEEN_FILE = "seen.json"
APPLICATIONS_FILE = "applications.json"
APPLICATIONS_TABLE = "applications.tex"
TIMELINE_FIELDS = ["applied", "invited", "interview", "decided"]
DECISIONS = ["offer", "rejected"]
STATUSES = ["to apply", "applied", "invited", "interview"] + DECISIONS
LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
TIMELINE_LABELS = {
    "applied": "Beworben",
    "invited": "Einladung erhalten",
    "interview": "Vorstellungsgespräch",
    "decided": "Entscheidung",
}
DECISION_LABELS = {"offer": "Zusage", "rejected": "Absage"}
TABLE_HEADER = r"""\documentclass{article}
\usepackage[margin=2cm]{geometry}
\usepackage{longtable}
\usepackage{hyperref}
\begin{document}
\section*{Bewerbungsübersicht}
Stand: %s
\begin{longtable}{|p{0.55\textwidth}|p{0.33\textwidth}|}
\hline
\textbf{Stellenangebot} & \textbf{Bewerbungsverlauf} \\
\hline
\endhead
"""
TABLE_FOOTER = r"""\end{longtable}
\end{document}
"""


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
    """Load the list of jobs the user plans to apply for.

    Returns:
        List of application dictionaries. Empty if nothing was saved yet.
    """
    path = output_path(APPLICATIONS_FILE)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_applications(applications):
    """Write the application list and its LaTeX table to the output directory.

    Args:
        applications: List of application dictionaries to persist.
    """
    with open(output_path(APPLICATIONS_FILE), "w", encoding="utf-8") as f:
        json.dump(applications, f, indent=2, ensure_ascii=False)
    write_latex_table(applications)


def escape_latex(text):
    """Escape characters that have a special meaning in LaTeX.

    Args:
        text: Plain text to escape.

    Returns:
        Text safe to place in a LaTeX document.
    """
    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in text)


def format_date(date):
    """Format an ISO date for the LaTeX table.

    Args:
        date: Date as an ISO string (YYYY-MM-DD).

    Returns:
        The date as DD.MM.YYYY.
    """
    return datetime.date.fromisoformat(date).strftime("%d.%m.%Y")


def latex_job_cell(application):
    """Build the table cell describing the job of an application.

    Args:
        application: Application dictionary.

    Returns:
        LaTeX for the cell: title, company, place and link to the posting.
    """
    return " \\newline ".join([
        f"\\textbf{{{escape_latex(application['title'])}}}",
        escape_latex(f"{application['company']}, {application['location']}"),
        f"\\url{{{application['url']}}}",
    ])


def latex_timeline_cell(application):
    """Build the table cell with the timeline of an application.

    Args:
        application: Application dictionary.

    Returns:
        LaTeX for the cell: one line per recorded timeline date.
    """
    lines = []
    for field in TIMELINE_FIELDS:
        if not application.get(field):
            continue
        label = TIMELINE_LABELS[field]
        if field == "decided" and application.get("decision"):
            label = DECISION_LABELS[application["decision"]]
        lines.append(f"{label}: {format_date(application[field])}")
    return " \\newline ".join(lines)


def write_latex_table(applications):
    """Write the applied-for jobs as a LaTeX table to the output directory.

    Only jobs the user has applied to are included. Each row shows the job
    (title, company, place and link to the posting) next to the timeline
    of the application process.

    Args:
        applications: List of application dictionaries.
    """
    rows = []
    for application in applications:
        if not application.get("applied"):
            continue
        rows.append(f"{latex_job_cell(application)} & "
                    f"{latex_timeline_cell(application)} \\\\\n\\hline\n")
    header = TABLE_HEADER % format_date(datetime.date.today().isoformat())
    with open(output_path(APPLICATIONS_TABLE), "w", encoding="utf-8") as f:
        f.write(header + "".join(rows) + TABLE_FOOTER)


def add_application(service, record):
    """Add a job to the application list with an empty timeline.

    Args:
        service: Name of the job board the job came from.
        record: Normalized job record as returned by the board's normalize().
    """
    applications = load_applications()
    applications.append({
        "service": service,
        "saved": datetime.date.today().isoformat(),
        **{field: "" for field in TIMELINE_FIELDS},
        "decision": "",
        **record,
    })
    save_applications(applications)


def get_status(application):
    """Derive the displayed status of an application from its timeline.

    The status is the latest timeline event: the decision if one was made,
    otherwise "interview", "invited", "applied" or "to apply".

    Args:
        application: Application dictionary.

    Returns:
        Status as a string.
    """
    if application.get("decision"):
        return application["decision"]
    if application.get("interview"):
        return "interview"
    if application.get("invited"):
        return "invited"
    if application.get("applied"):
        return "applied"
    return "to apply"


def update_status(index, status):
    """Set the status of a saved job by updating its timeline.

    The timeline date of the new status is set to today, later dates and
    the decision are cleared, and earlier dates are kept. The status
    "to apply" clears the whole timeline.

    Args:
        index: Index of the application in the saved list.
        status: New status, one of STATUSES.
    """
    applications = load_applications()
    application = applications[index]
    field = "decided" if status in DECISIONS else status
    position = TIMELINE_FIELDS.index(field) if field in TIMELINE_FIELDS else -1
    if position >= 0:
        application[field] = datetime.date.today().isoformat()
    for later_field in TIMELINE_FIELDS[position + 1:]:
        application[later_field] = ""
    application["decision"] = status if status in DECISIONS else ""
    save_applications(applications)
