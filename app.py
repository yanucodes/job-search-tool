"""Web interface for the application tracker."""

import argparse
import datetime
import os
import subprocess
import uuid

from flask import Flask, redirect, render_template, request, send_file, \
    url_for

import config
import entries
import tracker

app = Flask(__name__)

APPLICATIONS_PDF = "applications.pdf"
DEMO_PORT = 5055
# How far back the applications page looks for a change of status until
# another period is chosen.
RECENT_WEEKS = 2
# Query arguments holding the period the applications page is filtered by.
FILTER_ARGS = ("start", "end")
# The kinds listed away from the applications page, by the path of their
# page. Taken from the registry, so a new kind brings its page with it.
KIND_PAGES = {entry_class.page: entry_class
              for entry_class in entries.KINDS[1:]}


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


def filter_args():
    """Return the filter the current request carries, to pass it on.

    The forms on a filtered page post to addresses of their own, so the
    filter travels along with them and the page comes back filtered the
    same way once the change is made.

    Returns:
        Dictionary of the filter's query arguments present in the request.
    """
    return {key: request.args[key] for key in FILTER_ARGS
            if key in request.args}


def activity_period():
    """Return the period the applications page is filtered by.

    Without a chosen period the page shows the last few weeks. An argument
    that is present but empty leaves the period open at that end, which is
    how everything is shown; one that is not a date is treated alike.

    Returns:
        The period as a (start, end) pair of ISO dates, either of which may
        be "" for an open end.
    """
    recent = datetime.date.today() - datetime.timedelta(weeks=RECENT_WEEKS)
    start = request.args.get("start", recent.isoformat()).strip()
    end = request.args.get("end", "").strip()
    return (start if entries.is_date(start) else "",
            end if entries.is_date(end) else "")


def entry_page(entry):
    """Return the address of the list page an entry is shown on.

    Args:
        entry: Entry a form was posted for, or the class of one, since the
            page belongs to the kind rather than to the entry.

    Returns:
        URL of that entry's page, to return to once the change is made,
        filtered as it was when the form was posted.
    """
    if entry.page in KIND_PAGES:
        return url_for("entry_list", page=entry.page)
    return url_for("applications", **filter_args())


@app.route("/")
def index():
    """Redirect the start page to the application list."""
    return redirect(url_for("applications"))


def render_entry_list(heading, groups, empty, period=None, counts=None):
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
        period: Optional (start, end) pair of ISO dates the page is filtered
            by. When given, the page offers the filter form; when omitted,
            the page is not filtered.
        counts: Optional (shown, total) pair, how many entries the filter
            let through out of how many there are.

    Returns:
        The rendered page.
    """
    return render_template("entry_list.html", heading=heading, groups=groups,
                           empty=empty, period=period, counts=counts,
                           recent_weeks=RECENT_WEEKS,
                           filter_args=filter_args(),
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

    The list keeps growing while the search goes on, so only the
    applications whose status changed within a period are shown: by
    default the last few weeks, otherwise the one the optional "start" and
    "end" query arguments give as ISO dates, as for the PDF summary.
    """
    saved = [e for e in enumerate(tracker.load_applications())
             if e[1].kind == entries.Entry.kind]
    period = activity_period()
    jobs = [e for e in saved if e[1].status_changed_between(*period)]
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
    if jobs:
        empty = ""
    elif saved:
        empty = "No application changed status in this period."
    else:
        empty = "No saved applications yet."
    return render_entry_list("My applications", groups, empty,
                             period=period, counts=(len(jobs), len(saved)))


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
            tracker.add_application(record, priority, applied,
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
    output_dir = config.get_output_dir()
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", tracker.APPLICATIONS_TABLE],
        cwd=output_dir, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        return (f"pdflatex failed:\n{result.stdout}", 500,
                {"Content-Type": "text/plain; charset=utf-8"})
    return send_file(os.path.abspath(os.path.join(output_dir,
                                                  APPLICATIONS_PDF)))


def run_demo():
    """Serve the demo entries on a port of their own.

    The demo runs against the obviously fake entries in demo/results,
    found next to this file rather than through the configuration, so it
    never reads or writes the real tracker files whatever is configured.
    Its own port keeps it beside an instance serving the real ones.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    config.OUTPUT_DIR = os.path.join(here, "demo", "results")
    app.run(port=DEMO_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true",
                        help="serve the demo entries on port {}".format(
                            DEMO_PORT))
    if parser.parse_args().demo:
        run_demo()
    else:
        app.run(debug=True)
