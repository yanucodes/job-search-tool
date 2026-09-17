"""The entries of the tracker: job applications and other Eigenbemühungen.

Not every documented job-search effort is an application to a posting.
Contacting a private recruiter or visiting a job fair counts too, and has to
be reported with its own wording rather than as "Beworben". Each kind of
effort is a class here: it carries the German labels it prints with and knows
how to render itself as a row of the LaTeX table.

Entries are stored as plain dictionaries in the tracker file, so from_dict()
and to_dict() convert between the two. Entries written before this module
existed have no "kind" key and load as plain job applications.
"""

import datetime

TIMELINE_FIELDS = ["applied", "invited", "interview", "decided"]
MULTI_FIELDS = ["interview"]
DECISIONS = ["offer", "rejected"]
STATUSES = ["to apply", "applied", "invited", "interview"] + DECISIONS
PRIORITIES = [1, 2, 3]
PRIORITY_LABELS = {1: "high", 2: "moderate", 3: "low"}
RECORD_FIELDS = ["id", "title", "company", "location", "published", "url"]
KNOWN_FIELDS = ({"service", "saved", "contact", "decision", "priority",
                 "attended"} | set(TIMELINE_FIELDS) | set(RECORD_FIELDS))
REQUIRED_FIELDS = ["title", "company", "location", "url"]
FIELD_TYPES = {"title": "text", "company": "text", "location": "text",
               "url": "url", "contact": "text", "published": "date",
               "saved": "date", "applied": "date", "invited": "date",
               "attended": "checkbox"}
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


def escape_latex(text):
    """Escape characters that have a special meaning in LaTeX.

    Args:
        text: Plain text to escape.

    Returns:
        Text safe to place in a LaTeX document.
    """
    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in text)


def date_list(dates):
    """Normalize a timeline field that may hold several dates.

    Entries saved before a field could hold more than one date store a
    single string there, which is that field's whole timeline.

    Args:
        dates: List of ISO dates, or a single one as a string.

    Returns:
        Sorted list of ISO dates. Empty for an empty string or list.
    """
    if isinstance(dates, str):
        return [dates] if dates else []
    return sorted(dates)


def is_date(text):
    """Check whether a string is a date the tracker can store.

    Args:
        text: String to check.

    Returns:
        True if it is a valid ISO date (YYYY-MM-DD).
    """
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def format_date(date):
    """Format an ISO date for the LaTeX table.

    Args:
        date: Date as an ISO string (YYYY-MM-DD).

    Returns:
        The date as DD.MM.YYYY.
    """
    return datetime.date.fromisoformat(date).strftime("%d.%m.%Y")


class Entry:
    """One documented Eigenbemühung: by default, a job application.

    Subclasses stand for the other kinds of effort and override the class
    attributes below with the German wording of their kind. Everything else
    -- the timeline, the status, the LaTeX rendering -- is shared, because
    every effort has the same shape: a first action, a follow-up, a
    conversation and an outcome.

    The web interface is in English and the PDF summary in German, because
    the summary is what the Arbeitsagentur is handed; the two sets of labels
    below are kept apart for that reason.

    Attributes:
        kind: Value stored in the "kind" key, and the key into REGISTRY.
        label: Name of one such entry, for the web interface.
        group: Heading of the page this kind gets in the web interface.
        page: Path of that page, and what the navigation links to.
        form_fields: Which fields the manual form offers, in order.
        field_labels: Label per form field, saying what to record in it.
        field_hints: Optional help text per form field.
        statuses: Which statuses this kind can be in.
        status_labels: What a status is called for this kind, where the
            wording of a job application does not fit.
        status_dated: Whether a status change records a date of its own, and
            so whether the status form asks for one.
        timeline_ordered: Whether the stages of the timeline follow one
            another, so that reaching one means the later ones have not
            happened. False where they may happen in any order.
        section: Heading of the section this kind gets in the PDF summary.
        columns: Headings of the two table columns, as a (left, right) pair.
        timeline_labels: German label per timeline field.
        decision_labels: German label per decision.
    """

    kind = "job"
    label = "Job application"
    group = "Applications"
    page = "applications"
    form_fields = ["title", "company", "location", "url", "contact",
                   "published", "applied"]
    field_labels = {"title": "Job title", "company": "Company",
                    "location": "Location", "url": "Link to the posting",
                    "contact": "Contact person", "published": "Published",
                    "applied": "Applied"}
    field_hints = {"applied": "leave empty if not applied yet; may be a past"
                              " date"}
    statuses = STATUSES
    status_labels = {}
    status_dated = True
    timeline_ordered = True
    section = "Bewerbungen"
    columns = ("Stellenangebot", "Bewerbungsverlauf")
    timeline_labels = {
        "applied": "Beworben",
        "invited": "Einladung erhalten",
        "interview": "Vorstellungsgespräch",
        "decided": "Entscheidung",
    }
    decision_labels = {"offer": "Zusage", "rejected": "Absage"}

    def __init__(self, service, id="", title="", company="", location="",
                 published="", url="", saved="", contact="", applied="",
                 invited="", interview=(), decided="", decision="",
                 priority=None, attended=False, extra=None):
        """Create an entry.

        Args:
            service: Name of the job board the entry came from, or "manual"
                for entries added by hand.
            id: Identifier of the job on that board. Must be stable, it is
                what the seen-job tracking is keyed on.
            title: Job title, or what the effort was for other kinds.
            company: Employer, or the agency or organiser for other kinds.
            location: Place of the job, agency or event.
            url: Link to the posting, agency or event.
            published: Optional ISO date the posting appeared on.
            saved: ISO date the entry was saved. Defaults to today.
            contact: Optional contact person, e.g. of a recruiter.
            applied: ISO date of the first action (applying, contacting).
            invited: ISO date of the follow-up.
            interview: ISO dates of the conversations, as a list. A single
                date as a string is accepted, as older entries store one.
            decided: ISO date of the outcome.
            decision: What the outcome was, one of DECISIONS.
            priority: Optional priority level, one of PRIORITIES.
            attended: Whether an event was actually attended. Only kinds
                that stand for an event use it.
            extra: Optional dictionary of further keys to keep, for values a
                job board records that this class does not know about.
        """
        self.service = service
        self.id = id
        self.title = title
        self.company = company
        self.location = location
        self.published = published
        self.url = url
        self.saved = saved or datetime.date.today().isoformat()
        self.contact = contact
        self.applied = applied
        self.invited = invited
        self.interview = date_list(interview)
        self.decided = decided
        self.decision = decision
        self.priority = priority
        self.attended = attended
        self.extra = extra or {}

    @property
    def reportable(self):
        """Whether the entry belongs in the PDF summary.

        An effort is only reported once it was actually made, which for a
        plain entry means its first timeline date is filled in.

        Returns:
            True if the entry should appear in the summary.
        """
        return bool(self.applied)

    @property
    def entry_date(self):
        """The date the entry stands on, for reading it at a glance.

        That is the day it is about -- applied, first contacted, or the day
        an event takes place -- and, while nothing has happened yet, the
        day the entry was noted down, so that a card always carries a date.

        Returns:
            ISO date (YYYY-MM-DD).
        """
        return self.applied or self.saved

    @property
    def effort_date(self):
        """The day the effort counts as made on.

        It is what the summary sorts by and what its period is measured
        against, so it is the day the entry earned its place there.

        Returns:
            ISO date (YYYY-MM-DD), or "" for an entry not reportable at all.
        """
        return self.applied

    @property
    def report_dates(self):
        """The days something happened on this entry.

        Every recorded stage is a documented step of its own, not only the
        first one: an application sent in one month may be answered and
        talked about in the next.

        Returns:
            List of ISO dates in date order, one per recorded timeline
            date. Empty while nothing is recorded.
        """
        return [date for _, _, date in self.timeline_lines()]

    def changed_between(self, start, end):
        """Whether anything happened on this entry within a period.

        A summary reports a period of the job search rather than a set of
        entries, so an entry belongs in it whenever one of its steps falls
        inside it -- the entry then appears with its whole timeline, which
        is what places that step in its course.

        Args:
            start: Optional ISO date (YYYY-MM-DD) of the lower bound. An
                empty string leaves the period open at that end.
            end: Optional ISO date (YYYY-MM-DD) of the upper bound, again
                open when empty. Both bounds are inclusive.

        Returns:
            True if at least one recorded date lies within the period.
        """
        return any((not start or date >= start) and (not end or date <= end)
                   for date in self.report_dates)

    def last_stage(self):
        """Return the timeline field that was acted on most recently.

        A field holding several dates is judged by its latest one. Stages
        sharing a date are ranked by their place in the timeline, the later
        one winning.

        Returns:
            Name of that field, or "" when nothing is recorded yet.
        """
        dated = []
        for position, field in enumerate(TIMELINE_FIELDS):
            value = getattr(self, field)
            dates = [date for date in
                     (value if field in MULTI_FIELDS else [value]) if date]
            if dates:
                dated.append((max(dates), position, field))
        return max(dated)[2] if dated else ""

    @property
    def status(self):
        """Status of the entry, derived from its timeline.

        The decision, once made, is the status: it is what became of the
        effort. Before that, a timeline whose stages follow one another
        reports the furthest stage reached, while one whose stages do not
        reports the stage acted on last, a later stage there saying nothing
        about the ones before it.

        Returns:
            Status as a string, one of STATUSES.
        """
        if self.decision:
            return self.decision
        if not self.timeline_ordered:
            stage = self.last_stage()
            return stage if stage in STATUSES else "to apply"
        if self.interview:
            return "interview"
        if self.invited:
            return "invited"
        if self.applied:
            return "applied"
        return "to apply"

    @property
    def status_label(self):
        """What the current status is called for this kind of entry.

        Returns:
            The status in the wording of this kind, e.g. "planned" rather
            than "to apply" for a job fair.
        """
        return self.status_labels.get(self.status, self.status)

    def set_status(self, status, date=""):
        """Set the status by updating the timeline.

        The timeline date of the new status is set to the given day and
        earlier dates are kept. Where the stages follow one another, the
        later ones are cleared along with the decision, since reaching a
        stage means what came after it has not happened yet; where they do
        not, nothing is cleared, as the stages say nothing about each
        other. Either way the status before anything happened clears the
        whole timeline, which is how a mistake is taken back.

        A field that holds several dates keeps the ones it has and takes the
        new one alongside them, so setting the status to "interview" again
        with another date records a second conversation rather than moving
        the first.

        Args:
            status: New status, one of STATUSES.
            date: ISO date (YYYY-MM-DD) the status was reached on. Defaults
                to today.
        """
        field = "decided" if status in DECISIONS else status
        if field not in TIMELINE_FIELDS:
            self.clear_timeline()
            return
        date = date or datetime.date.today().isoformat()
        if field in MULTI_FIELDS:
            date = sorted(set(getattr(self, field)) | {date})
        setattr(self, field, date)
        if status in DECISIONS:
            self.decision = status
        elif self.timeline_ordered:
            self.decision = ""
            for later_field in TIMELINE_FIELDS[
                    TIMELINE_FIELDS.index(field) + 1:]:
                setattr(self, later_field,
                        [] if later_field in MULTI_FIELDS else "")

    def clear_timeline(self):
        """Forget every date and the decision, leaving nothing recorded."""
        for field in TIMELINE_FIELDS:
            setattr(self, field, [] if field in MULTI_FIELDS else "")
        self.decision = ""

    def set_priority(self, priority):
        """Set or clear the priority.

        Args:
            priority: New priority (one of PRIORITIES), or None to clear it.
        """
        self.priority = priority if priority in PRIORITIES else None

    def to_dict(self):
        """Convert the entry to a dictionary for the tracker file.

        Optional values that are unset are left out, so entries stay as
        short as what they actually record.

        Returns:
            Dictionary of the entry, ready to be serialized as JSON.
        """
        data = {"kind": self.kind, "service": self.service,
                "saved": self.saved}
        data.update({field: getattr(self, field)
                     for field in TIMELINE_FIELDS})
        data["decision"] = self.decision
        data.update({field: getattr(self, field)
                     for field in RECORD_FIELDS})
        if self.contact:
            data["contact"] = self.contact
        if self.priority in PRIORITIES:
            data["priority"] = self.priority
        if self.attended:
            data["attended"] = True
        data.update(self.extra)
        return data

    def latex_entry_cell(self):
        """Build the table cell describing what the entry is about.

        Returns:
            LaTeX for the cell: title, company, place and link.
        """
        return " \\newline ".join(self.latex_entry_lines())

    def latex_entry_lines(self):
        """Build the lines of the cell describing what the entry is about.

        Returns:
            List of LaTeX lines, so subclasses can add their own.
        """
        return [
            f"\\textbf{{{escape_latex(self.title)}}}",
            escape_latex(f"{self.company}, {self.location}"),
            f"\\url{{{self.url}}}",
        ]

    def timeline_lines(self):
        """Build the recorded timeline as labelled dates.

        A field holding several dates contributes one line per date. Those
        lines are numbered, so that a second conversation is told apart from
        the first; a lone date is not numbered, as there is nothing to tell
        it apart from. The numbers go by date, as does the order of the
        lines: a timeline is read as the course of events, which the order
        of the fields only matches where the stages follow one another.

        Returns:
            List of (field, label, date) triples in date order, leaving out
            the fields no date was recorded in. Stages sharing a date keep
            the order of the timeline.
        """
        lines = []
        for field in TIMELINE_FIELDS:
            label = self.timeline_labels[field]
            if field not in MULTI_FIELDS:
                if getattr(self, field):
                    lines.append((field, label, getattr(self, field)))
                continue
            dates = getattr(self, field)
            lines.extend(
                (field, f"{label} {number}" if len(dates) > 1 else label, date)
                for number, date in enumerate(dates, start=1))
        return sorted(lines, key=lambda line: line[2])

    def latex_timeline_cell(self):
        """Build the table cell with the timeline of the entry.

        Returns:
            LaTeX for the cell: one line per recorded timeline date, each
            labelled in the wording of this kind of entry.
        """
        lines = []
        for field, label, date in self.timeline_lines():
            if field == "decided" and self.decision:
                label = self.decision_labels[self.decision]
            lines.append(f"{label}: {format_date(date)}")
        return " \\newline ".join(lines)

    def latex_row(self, number):
        """Build the whole table row of the entry.

        Args:
            number: Number of the row within its section.

        Returns:
            LaTeX for the row, including the rule closing it.
        """
        return (f"{number} & {self.latex_entry_cell()} & "
                f"{self.latex_timeline_cell()} \\\\\n\\hline\n")


class RecruiterContact(Entry):
    """Contact with a private recruiter (Einschaltung eines Vermittlers).

    Its stages are not a ladder the way an application's are: documents go
    out before or after a first call, and either may be repeated, so
    recording one must not take the others away.
    """

    kind = "recruiter"
    label = "Recruiter contact"
    group = "Recruiter contacts"
    page = "recruiters"
    form_fields = ["title", "company", "contact", "location", "url",
                   "applied"]
    field_labels = {"title": "What the contact was about",
                    "company": "Agency", "contact": "Contact person",
                    "location": "Agency address",
                    "url": "Agency website", "applied": "First contact"}
    field_hints = {"title": "e.g. Kontakt mit privatem Personalvermittler",
                   "company": "the agency, with its legal name if it differs"
                              " from the brand",
                   "contact": "who wrote to you, with their role",
                   "applied": "when they first got in touch, or you did"}
    status_labels = {"to apply": "not contacted yet", "applied": "in contact",
                     "invited": "documents sent", "interview": "call held"}
    timeline_ordered = False
    section = "Vermittlerkontakte"
    columns = ("Vermittler / Kontakt", "Verlauf")
    timeline_labels = {
        "applied": "Erstkontakt",
        "invited": "Unterlagen übermittelt",
        "interview": "Orientierungsgespräch",
        "decided": "Abschluss",
    }
    decision_labels = {"offer": "Vermittlung erfolgreich",
                       "rejected": "keine Vermittlung"}

    def latex_entry_lines(self):
        """Add the contact person under the agency, when one is recorded."""
        lines = super().latex_entry_lines()
        if self.contact:
            lines.insert(2, escape_latex(f"Ansprechpartner: {self.contact}"))
        return lines


class FairVisit(Entry):
    """A job fair or career event, planned and then possibly attended.

    Attending a fair is two documented steps, each with its own date:
    signing up for it, and being there on the day. The day it takes place
    is known long before either, so an entry can be kept for a fair that is
    still ahead; only a fair actually attended is an Eigenbemühung that
    belongs in the summary.

    Attributes:
        planned_label: What the day of the fair is called while the visit
            is still ahead, in place of its timeline label.
    """

    kind = "fair"
    label = "Job fair"
    group = "Job fairs"
    page = "fairs"
    form_fields = ["title", "company", "location", "url", "applied",
                   "invited", "contact", "attended"]
    field_labels = {"title": "Event", "company": "Organiser",
                    "location": "Venue", "url": "Event website",
                    "applied": "Date of the fair",
                    "invited": "Registered on",
                    "contact": "Who you spoke to", "attended": "Attended"}
    field_hints = {"title": "e.g. heise jobs IT-Tag Stuttgart",
                   "invited": "when you signed up; leave empty for a fair"
                              " that took no registration",
                   "contact": "the people or companies you talked to at the"
                              " stands; fill in after the visit",
                   "attended": "tick only once you have actually been there"
                               " -- a fair enters the PDF summary at that"
                               " point, not before"}
    statuses = ["planned", "registered", "attended"]
    section = "Jobmessen"
    columns = ("Veranstaltung", "Verlauf")
    timeline_labels = {
        "applied": "Besucht am",
        "invited": "Angemeldet am",
        "interview": "Folgegespräch",
        "decided": "Abschluss",
    }
    planned_label = "Findet statt am"  # what that date is until it is gone to
    decision_labels = {"offer": "Zusage", "rejected": "Absage"}

    @property
    def visited(self):
        """Whether the fair has been to, rather than merely marked so.

        A fair whose day has not come yet cannot have been visited,
        whatever the entry says, so a box ticked too early corrects itself
        when the day arrives instead of claiming a visit that never
        happened.

        Returns:
            True if the fair was attended and its day has come.
        """
        return bool(self.applied) and self.attended \
            and self.applied <= datetime.date.today().isoformat()

    @property
    def status(self):
        """How far the fair got: planned, registered for, or attended."""
        if self.visited:
            return "attended"
        return "registered" if self.invited else "planned"

    @property
    def reportable(self):
        """Whether the fair belongs in the summary.

        Signing up for one is a documented effort of its own, so a fair is
        reported from the day it was registered on, with the visit added to
        it once it has taken place. A fair that took no registration is
        reported once visited, as before.

        Returns:
            True if the fair should appear in the summary.
        """
        return bool(self.invited) or self.visited

    @property
    def effort_date(self):
        """The day the fair counts as an effort on.

        That is the day it was visited, or, while the visit is still ahead,
        the day it was signed up for -- a fair still to come must not be
        counted in a period that has not reached it.

        Returns:
            ISO date (YYYY-MM-DD).
        """
        return self.applied if self.visited else self.invited

    @property
    def report_dates(self):
        """The days this fair counts as documented on.

        The day it takes place is known before the visit, but it is a step
        taken only once the fair has been gone to: a fair still ahead must
        not be counted in a period that has not reached it.

        Returns:
            List of ISO dates in date order, leaving out the day of the
            fair while the visit is still ahead.
        """
        return [date for field, _, date in self.timeline_lines()
                if field != "applied" or self.visited]

    def timeline_lines(self):
        """Call the day of the fair what it is until the fair was attended.

        The date the entry carries is the day the fair takes place, which
        is known while the visit is still ahead; it is a day visited on
        only once the fair has been to. A fair signed up for is reported
        before that, and reports the day it takes place as one still to
        come.

        Returns:
            List of (field, label, date) triples, as for any entry.
        """
        lines = []
        for field, label, date in super().timeline_lines():
            if field == "applied" and not self.visited:
                label = self.planned_label
            lines.append((field, label, date))
        return lines

    def set_status(self, status, date=""):
        """Record how far the fair got.

        Registering is dated on its own. Attending is dated by the day the
        fair took place, which is the date the entry already carries, so
        confirming attendance sets that date rather than a second one.
        Falling back to a step not yet taken forgets the ones after it, the
        day of the fair excepted: that one stands whether it is gone to or
        not.

        Args:
            status: One of the statuses of this kind.
            date: ISO date (YYYY-MM-DD) of the step. Defaults to today.
        """
        date = date or datetime.date.today().isoformat()
        self.attended = status == "attended"
        if status == "attended":
            self.applied = date
        elif status == "registered":
            self.invited = date
        else:
            self.invited = ""


class NetworkEffort(Entry):
    """Any other documented effort, e.g. a speculative enquiry."""

    kind = "network"
    label = "Networking"
    group = "Networking"
    page = "networking"
    form_fields = ["title", "company", "contact", "location", "url",
                   "applied"]
    field_labels = {"title": "What you did",
                    "company": "Organisation or person",
                    "contact": "Contact person", "location": "Place",
                    "url": "Link", "applied": "Date"}
    field_hints = {"title": "e.g. Initiativanfrage, Meetup, Empfehlung über"
                            " Kontakt",
                   "location": "or \"remote\" if it was not in person"}
    status_labels = {"to apply": "planned", "applied": "done",
                     "invited": "answered", "interview": "spoke"}
    section = "Sonstige Eigenbemühungen"
    columns = ("Eigenbemühung", "Verlauf")
    timeline_labels = {
        "applied": "Kontaktaufnahme",
        "invited": "Rückmeldung",
        "interview": "Gespräch",
        "decided": "Abschluss",
    }
    decision_labels = {"offer": "Zusage", "rejected": "Absage"}


KINDS = [Entry, RecruiterContact, FairVisit, NetworkEffort]
REGISTRY = {kind.kind: kind for kind in KINDS}


def from_dict(data):
    """Build the entry a tracker-file dictionary describes.

    The "kind" key chooses the class. Entries saved before the other kinds
    existed have no such key and are job applications.

    Args:
        data: Dictionary as stored in the tracker file.

    Returns:
        An instance of the Entry subclass for that kind.
    """
    fields = dict(data)
    entry_class = REGISTRY.get(fields.pop("kind", ""), Entry)
    extra = {key: fields.pop(key)
             for key in list(fields) if key not in KNOWN_FIELDS}
    fields.setdefault("service", "manual")
    return entry_class(extra=extra, **fields)
