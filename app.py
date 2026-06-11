"""Web interface for job search."""

from flask import Flask, redirect, render_template, request, url_for

import search
import tracker

app = Flask(__name__)

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
                           description=description, total=len(jobs))


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
    for entry in get_pending_jobs():
        if entry[0] == service and entry[1]["id"] == job_id:
            tracker.mark_seen(service, job_id)
            if action == "save":
                tracker.add_application(service, entry[1])
            pending_jobs.remove(entry)
            break
    return redirect(url_for("review"))


@app.route("/")
@app.route("/applications")
def applications():
    """List saved applications. Implemented in the next commit."""
    return "Coming soon."


if __name__ == "__main__":
    app.run(debug=True)
