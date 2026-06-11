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
STATUSES = ["to apply", "applied", "interview", "offer", "rejected"]
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
TABLE_HEADER = r"""\documentclass{article}
\usepackage[margin=2cm]{geometry}
\usepackage{longtable}
\usepackage{hyperref}
\begin{document}
\section*{Job applications}
\begin{longtable}{rlllll}
\# & Saved & Title & Company & Location & Status \\
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


def write_latex_table(applications):
    """Write the application list as a LaTeX table to the output directory.

    Each row shows when the job was saved, its title (linked to the
    posting), company, location and the current application status.

    Args:
        applications: List of application dictionaries.
    """
    rows = []
    for i, application in enumerate(applications):
        title = (f"\\href{{{application['url']}}}"
                 f"{{{escape_latex(application['title'])}}}")
        cells = [str(i + 1), application["saved"], title,
                 escape_latex(application["company"]),
                 escape_latex(application["location"]),
                 escape_latex(application["status"])]
        rows.append(" & ".join(cells) + " \\\\\n")
    with open(output_path(APPLICATIONS_TABLE), "w", encoding="utf-8") as f:
        f.write(TABLE_HEADER + "".join(rows) + TABLE_FOOTER)


def add_application(service, record):
    """Add a job to the application list with the initial status.

    Args:
        service: Name of the job board the job came from.
        record: Normalized job record as returned by the board's normalize().
    """
    applications = load_applications()
    applications.append({
        "service": service,
        "saved": datetime.date.today().isoformat(),
        "status": STATUSES[0],
        **record,
    })
    save_applications(applications)


def update_status(index, status):
    """Set the application status of a saved job.

    Args:
        index: Index of the application in the saved list.
        status: New status, one of STATUSES.
    """
    applications = load_applications()
    applications[index]["status"] = status
    save_applications(applications)
