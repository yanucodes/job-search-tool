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
# The kinds listed away from the applications page, by the path of their
# page. Taken from the registry, so a new kind brings its page with it.
KIND_PAGES = {entry_class.page: entry_class
              for entry_class in entries.KINDS[1:]}

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
    """Supply what the navigation and toolbar of every page need.

    Each kind of entry has a list page of its own, and adding an entry and
    generating the summary are reachable from anywhere in the tool, so both
    bars sit in the base template rather than on one page. Offering the
    summary is only worth it once something is saved to summarize.

    Returns:
        Dictionary of variables added to the context of every template.
    """
    pages = [(entries.Entry.group, url_for("applications"))]
    pages += [(entry_class.group, url_for("entry_list", page=page))
              for page, entry_class in KIND_PAGES.items()]
    return {"nav_pages": pages,
            "has_entries": bool(tracker.load_applications())}


def entry_page(entry):
    """Return the address of the list page an entry is shown on.

    Args:
        entry: Entry a form was posted for, or the class of one, since the
            page belongs to the kind rather than to the entry.

    Returns:
        URL of that entry's page, to return to once the change is made.
    """
    if entry.page in KIND_PAGES:
        return url_for("entry_list", page=entry.page)
    return url_for("applications")


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


def render_entry_list(heading, groups, empty):
    """Render a page listing saved entries.

    Each entry is paired with its index in the saved list, which the status
    form posts back. The status form's date field starts on today, the day a
    status is most often changed on.

    Args:
        heading: Heading of the page.
        groups: List of (heading, entries) pairs, where each entry is an
            (index, Entry) pair. A group heading may be empty, for a page
            that is one list rather than several.
        empty: What to say when the page has nothing to list, or "" when it
            has something.

    Returns:
        The rendered page.
    """
    return render_template("entry_list.html", heading=heading, groups=groups,
                           empty=empty,
                           priorities=entries.PRIORITIES,
                           priority_labels=entries.PRIORITY_LABELS,
                           default_kind=entries.Entry.kind,
                           today=datetime.date.today().isoformat(),
                           expand=request.args.get("open") == "1")


@app.route("/applications")
def applications():
    """Show the job applications, grouped by how far they got.

    One section holds those still to apply for, one those the process is
    running on, and one those that were turned down. Applications still to
    make are ordered by priority (highest first, unprioritised last), those
    made by the date applied, and turned-down ones by the date of the
    decision.
    """
    jobs = [e for e in enumerate(tracker.load_applications())
            if e[1].kind == entries.Entry.kind]
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
    return render_entry_list("My applications", groups,
                             "" if jobs else "No saved applications yet.")


@app.route("/<any({}):page>".format(",".join(KIND_PAGES)))
def entry_list(page):
    """Show the entries of one kind of Eigenbemühung, newest first.

    These kinds are recorded rather than worked through, so their page is
    one list ordered by date rather than sections by progress.

    Args:
        page: Path of the kind, a key of KIND_PAGES.
    """
    entry_class = KIND_PAGES[page]
    of_kind = sorted((e for e in enumerate(tracker.load_applications())
                      if e[1].kind == entry_class.kind),
                     key=lambda e: e[1].entry_date, reverse=True)
    return render_entry_list(
        "{} ({})".format(entry_class.group, len(of_kind)),
        [("", of_kind)],
        "" if of_kind else "No {} saved yet.".format(entry_class.group.lower()))


@app.route("/new", methods=["GET", "POST"])
def new_application():
    """Add a job to the application list by hand.

    Which fields the form offers, and what they are called, depends on the
    kind of Eigenbemühung being recorded: the "kind" query argument chooses
    it on GET, a hidden field carries it on POST. POST validates that the
    fields the PDF summary needs (title, company, location, url) are filled,
    then saves the entry. An optional past date in a timeline field records
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
        invited = request.form.get("invited", "").strip()
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
                                    attended, invited)
            return redirect(entry_page(entry_class))
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


@app.route("/entries/<int:index>/status", methods=["POST"])
def update_status(index):
    """Set the status of a saved entry.

    The posted date is stamped as the timeline date of the chosen status;
    today is used when it is missing or not a date.

    Which statuses are on offer depends on the kind of entry, so the posted
    one is checked against the entry's own.

    Args:
        index: Index of the entry in the saved list.
    """
    status = request.form["status"]
    date = request.form.get("date", "").strip()
    applications = tracker.load_applications()
    if not 0 <= index < len(applications):
        return redirect(url_for("applications"))
    entry = applications[index]
    if status in entry.statuses:
        tracker.update_status(index, status,
                              date if entries.is_date(date) else "")
    return redirect(entry_page(entry))


@app.route("/entries/<int:index>/priority", methods=["POST"])
def update_priority(index):
    """Set or clear the priority of a saved job.

    Args:
        index: Index of the entry in the saved list.
    """
    raw = request.form.get("priority", "")
    priority = int(raw) if raw.isdigit() and int(raw) in entries.PRIORITIES \
        else None
    applications = tracker.load_applications()
    if not 0 <= index < len(applications):
        return redirect(url_for("applications"))
    tracker.update_priority(index, priority)
    return redirect(entry_page(applications[index]))


@app.route("/entries/<int:index>/delete", methods=["POST"])
def delete_application(index):
    """Remove a saved entry from the list.

    A job stays in the seen list, so it will not reappear in future
    searches.

    Args:
        index: Index of the entry in the saved list.
    """
    applications = tracker.load_applications()
    if not 0 <= index < len(applications):
        return redirect(url_for("applications"))
    page = entry_page(applications[index])
    tracker.delete_application(index)
    return redirect(page)


@app.route("/pdf")
def applications_pdf():
    """Generate a PDF summary of the application list and return it.

    The optional "start" and "end" query arguments hold ISO dates limiting
    the summary to the entries something happened on within that range --
    an application sent earlier counts too when it was answered or talked
    about in it. Each bound is inclusive; a bound that is left empty is not
    applied.
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
