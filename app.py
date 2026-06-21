"""Web interface for job search."""

import os
import subprocess

from flask import Flask, redirect, render_template, request, send_file, \
    url_for

import search
import tracker

app = Flask(__name__)

APPLICATIONS_PDF = "applications.pdf"

pending_jobs = None  # jobs found by the last search, None before the first


def get_pending_jobs(refresh=False):
    """Return new jobs to review, searching the job boards when needed.

    The result is cached in memory, so reloading the review page does not
    query the job boards again.

    Args:
        refresh: If True, run the search again even if results are cached.

    Returns:
        List of (service, record) tuples for unseen jobs.
    """
    global pending_jobs
    if pending_jobs is None or refresh:
        pending_jobs = search.find_new_jobs(tracker.load_seen())
    return pending_jobs


@app.route("/review")
def review():
    """Show the next new job with its description for review."""
    jobs = get_pending_jobs()
    if not jobs:
        return render_template("review.html", job=None)
    service, record = jobs[0]
    description = search.SERVICES[service].description(record)
    return render_template("review.html", service=service, job=record,
                           description=description, total=len(jobs),
                           priorities=tracker.PRIORITIES,
                           priority_labels=tracker.PRIORITY_LABELS)


@app.route("/review/search", methods=["POST"])
def refresh_jobs():
    """Search the job boards again and show the review page."""
    get_pending_jobs(refresh=True)
    return redirect(url_for("review"))


@app.route("/review/<any(save, seen):action>", methods=["POST"])
def resolve_job(action):
    """Mark the submitted job as seen and optionally save it.

    With the "save" action the job is also added to the application list.
    The job is removed from the pending jobs, so the review page moves on
    to the next one.

    Args:
        action: Either "save" or "seen".
    """
    service = request.form["service"]
    job_id = request.form["job_id"]
    raw = request.form.get("priority", "")
    priority = int(raw) if raw.isdigit() and int(raw) in tracker.PRIORITIES \
        else None
    for entry in get_pending_jobs():
        if entry[0] == service and entry[1]["id"] == job_id:
            tracker.mark_seen(service, job_id)
            if action == "save":
                tracker.add_application(service, entry[1], priority)
            pending_jobs.remove(entry)
            break
    return redirect(url_for("review"))


@app.route("/")
def index():
    """Redirect the start page to the application list."""
    return redirect(url_for("applications"))


@app.route("/applications")
def applications():
    """Show the jobs the user plans to apply for, grouped by progress.

    The page has one section for jobs still to apply for and one for jobs
    the application process has started on. Each application is paired
    with its index in the saved list, which the status form posts back.
    """
    applications = tracker.load_applications()
    for application in applications:
        application["status"] = tracker.get_status(application)
    entries = list(enumerate(applications))
    to_apply = sorted((e for e in entries if e[1]["status"] == "to apply"),
                      key=lambda e: e[1].get("priority", 99))
    applied = sorted((e for e in entries if e[1]["status"] != "to apply"),
                     key=lambda e: e[1].get("applied", ""))
    groups = [
        ("To apply", to_apply),
        ("Applied", applied),
    ]
    return render_template("applications.html", groups=groups,
                           empty=not applications,
                           statuses=tracker.STATUSES,
                           priorities=tracker.PRIORITIES,
                           priority_labels=tracker.PRIORITY_LABELS,
                           timeline_fields=tracker.TIMELINE_FIELDS,
                           expand=request.args.get("open") == "1")


@app.route("/applications/<int:index>/status", methods=["POST"])
def update_status(index):
    """Set the application status of a saved job.

    The timeline date of the chosen status is stamped automatically.

    Args:
        index: Index of the application in the saved list.
    """
    status = request.form["status"]
    if (0 <= index < len(tracker.load_applications())
            and status in tracker.STATUSES):
        tracker.update_status(index, status)
    return redirect(url_for("applications"))


@app.route("/applications/<int:index>/priority", methods=["POST"])
def update_priority(index):
    """Set or clear the priority of a saved job.

    Args:
        index: Index of the application in the saved list.
    """
    raw = request.form.get("priority", "")
    priority = int(raw) if raw.isdigit() and int(raw) in tracker.PRIORITIES \
        else None
    if 0 <= index < len(tracker.load_applications()):
        tracker.update_priority(index, priority)
    return redirect(url_for("applications"))


@app.route("/applications/<int:index>/delete", methods=["POST"])
def delete_application(index):
    """Remove a saved job from the application list.

    The job stays in the seen list, so it will not reappear in future
    searches.

    Args:
        index: Index of the application in the saved list.
    """
    if 0 <= index < len(tracker.load_applications()):
        tracker.delete_application(index)
    return redirect(url_for("applications"))


@app.route("/applications/pdf")
def applications_pdf():
    """Generate a PDF summary of the application list and return it."""
    tracker.write_latex_table(tracker.load_applications())
    output_dir = search.get_output_dir()
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", tracker.APPLICATIONS_TABLE],
        cwd=output_dir, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        return (f"pdflatex failed:\n{result.stdout}", 500,
                {"Content-Type": "text/plain; charset=utf-8"})
    return send_file(os.path.abspath(os.path.join(output_dir,
                                                  APPLICATIONS_PDF)))


if __name__ == "__main__":
    app.run(debug=True)
