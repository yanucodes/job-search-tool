"""Web interface for job search."""

import datetime
import os
import subprocess
import uuid

from flask import Flask, redirect, render_template, request, send_file, \
    url_for

import entries
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


@app.context_processor
def toolbar():
    """Supply what the toolbar carried by every page needs.

    Adding an entry and generating the summary are reachable from anywhere
    in the tool, so that toolbar sits in the base template rather than on
    one page. Offering the summary is only worth it once something is
    saved to summarize.

    Returns:
        Dictionary of variables added to the context of every template.
    """
    return {"has_entries": bool(tracker.load_applications())}


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
                           priorities=entries.PRIORITIES,
                           priority_labels=entries.PRIORITY_LABELS)


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
    priority = int(raw) if raw.isdigit() and int(raw) in entries.PRIORITIES \
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

    Job applications are split by how far they got: one section for those
    still to apply for, one for those the process is running on, and one for
    those that were turned down. Every other kind of Eigenbemühung gets a
    section of its own, newest first, since those are recorded rather than
    worked through. Each entry is paired with its index in the saved list,
    which the status form posts back. The status form's date field starts on
    today, the day a status is most often changed on.
    """
    applications = tracker.load_applications()
    numbered = list(enumerate(applications))
    jobs = [e for e in numbered if e[1].kind == entries.Entry.kind]
    to_apply = sorted((e for e in jobs if e[1].status == "to apply"),
                      key=lambda e: e[1].priority or 99)
    applied = sorted((e for e in jobs
                      if e[1].status not in ("to apply", "rejected")),
                     key=lambda e: e[1].applied)
    rejected = sorted((e for e in jobs if e[1].status == "rejected"),
                      key=lambda e: e[1].decided)
    groups = [
        ("To apply", to_apply),
        ("Applied ({})".format(len(applied)), applied),
        ("Rejected ({})".format(len(rejected)), rejected),
    ]
    for entry_class in entries.KINDS[1:]:
        of_kind = sorted((e for e in numbered
                          if e[1].kind == entry_class.kind),
                         key=lambda e: e[1].applied or e[1].saved,
                         reverse=True)
        groups.append(("{} ({})".format(entry_class.group, len(of_kind)),
                       of_kind))
    return render_template("applications.html", groups=groups,
                           empty=not applications,
                           statuses=entries.STATUSES,
                           priorities=entries.PRIORITIES,
                           priority_labels=entries.PRIORITY_LABELS,
                           default_kind=entries.Entry.kind,
                           today=datetime.date.today().isoformat(),
                           expand=request.args.get("open") == "1")


@app.route("/new", methods=["GET", "POST"])
def new_application():
    """Add a job to the application list by hand.

    Which fields the form offers, and what they are called, depends on the
    kind of Eigenbemühung being recorded: the "kind" query argument chooses
    it on GET, a hidden field carries it on POST. POST validates that the
    fields the PDF summary needs (title, company, location, url) are filled,
    then saves the entry. An optional past date in the timeline field records
    an effort already made; when omitted a job application starts in the
    "to apply" group.
    """
    if request.method == "POST":
        kind = request.form.get("kind", "")
        entry_class = entries.REGISTRY.get(kind, entries.Entry)
        fields = {key: request.form.get(key, "").strip()
                  for key in entries.REQUIRED_FIELDS}
        published = request.form.get("published", "").strip()
        applied = request.form.get("applied", "").strip()
        contact = request.form.get("contact", "").strip()
        saved = request.form.get("saved", "").strip()
        attended = bool(request.form.get("attended"))
        raw = request.form.get("priority", "")
        priority = int(raw) if raw.isdigit() and int(raw) in entries.PRIORITIES \
            else None
        if all(fields.values()):
            record = {"id": uuid.uuid4().hex, "published": published, **fields}
            tracker.add_application("manual", record, priority, applied,
                                    entry_class.kind, contact, saved,
                                    attended)
            return redirect(url_for("applications"))
        missing = ", ".join(entry_class.field_labels[key]
                            for key in entries.REQUIRED_FIELDS
                            if not fields[key])
        return render_template(
            "add_application.html", form=request.form,
            error=f"Still needed: {missing}.", entry_class=entry_class,
            field_types=entries.FIELD_TYPES,
            required=entries.REQUIRED_FIELDS,
            priorities=entries.PRIORITIES,
            priority_labels=entries.PRIORITY_LABELS, kinds=entries.KINDS)
    entry_class = entries.REGISTRY.get(request.args.get("kind", ""),
                                       entries.Entry)
    return render_template("add_application.html", form={}, error=None,
                           entry_class=entry_class,
                           field_types=entries.FIELD_TYPES,
                           required=entries.REQUIRED_FIELDS,
                           priorities=entries.PRIORITIES,
                           priority_labels=entries.PRIORITY_LABELS,
                           kinds=entries.KINDS)


@app.route("/applications/<int:index>/status", methods=["POST"])
def update_status(index):
    """Set the application status of a saved job.

    The posted date is stamped as the timeline date of the chosen status;
    today is used when it is missing or not a date.

    Which statuses are on offer depends on the kind of entry, so the posted
    one is checked against the entry's own.

    Args:
        index: Index of the application in the saved list.
    """
    status = request.form["status"]
    date = request.form.get("date", "").strip()
    applications = tracker.load_applications()
    if 0 <= index < len(applications) \
            and status in applications[index].statuses:
        tracker.update_status(index, status,
                              date if entries.is_date(date) else "")
    return redirect(url_for("applications"))


@app.route("/applications/<int:index>/priority", methods=["POST"])
def update_priority(index):
    """Set or clear the priority of a saved job.

    Args:
        index: Index of the application in the saved list.
    """
    raw = request.form.get("priority", "")
    priority = int(raw) if raw.isdigit() and int(raw) in entries.PRIORITIES \
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


@app.route("/pdf")
def applications_pdf():
    """Generate a PDF summary of the application list and return it.

    The optional "start" and "end" query arguments hold ISO dates limiting
    the summary to the jobs applied to within that range. Each bound is
    inclusive; a bound that is left empty is not applied.
    """
    start = request.args.get("start", "").strip()
    end = request.args.get("end", "").strip()
    tracker.write_latex_table(tracker.load_applications(), start, end)
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
