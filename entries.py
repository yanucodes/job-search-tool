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
DECISIONS = ["offer", "rejected"]
STATUSES = ["to apply", "applied", "invited", "interview"] + DECISIONS
PRIORITIES = [1, 2, 3]
PRIORITY_LABELS = {1: "high", 2: "moderate", 3: "low"}
RECORD_FIELDS = ["id", "title", "company", "location", "published", "url"]
KNOWN_FIELDS = ({"service", "saved", "contact", "decision", "priority"}
                | set(TIMELINE_FIELDS) | set(RECORD_FIELDS))
REQUIRED_FIELDS = ["title", "company", "location", "url"]
FIELD_TYPES = {"title": "text", "company": "text", "location": "text",
               "url": "url", "contact": "text", "published": "date",
               "applied": "date"}
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
        group: Heading of the section this kind gets in the web interface.
        form_fields: Which fields the manual form offers, in order.
        field_labels: Label per form field, saying what to record in it.
        field_hints: Optional help text per form field.
        section: Heading of the section this kind gets in the PDF summary.
        columns: Headings of the two table columns, as a (left, right) pair.
        timeline_labels: German label per timeline field.
        decision_labels: German label per decision.
    """

    kind = "job"
    label = "Job application"
    group = "Applications"
    form_fields = ["title", "company", "location", "url", "contact",
                   "published", "applied"]
    field_labels = {"title": "Job title", "company": "Company",
                    "location": "Location", "url": "Link to the posting",
                    "contact": "Contact person", "published": "Published",
                    "applied": "Applied"}
    field_hints = {"applied": "leave empty if not applied yet; may be a past"
                              " date"}
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
                 invited="", interview="", decided="", decision="",
                 priority=None, extra=None):
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
            interview: ISO date of the conversation.
            decided: ISO date of the outcome.
            decision: What the outcome was, one of DECISIONS.
            priority: Optional priority level, one of PRIORITIES.
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
        self.interview = interview
        self.decided = decided
        self.decision = decision
        self.priority = priority
        self.extra = extra or {}

    @property
    def status(self):
        """Status of the entry, derived from its timeline.

        The status is the latest timeline event: the decision if one was
        made, otherwise "interview", "invited", "applied" or "to apply".

        Returns:
            Status as a string, one of STATUSES.
        """
        if self.decision:
            return self.decision
        if self.interview:
            return "interview"
        if self.invited:
            return "invited"
        if self.applied:
            return "applied"
        return "to apply"

    def set_status(self, status):
        """Set the status by updating the timeline.

        The timeline date of the new status is set to today, later dates and
        the decision are cleared, and earlier dates are kept. The status
        "to apply" clears the whole timeline.

        Args:
            status: New status, one of STATUSES.
        """
        field = "decided" if status in DECISIONS else status
        position = TIMELINE_FIELDS.index(field) \
            if field in TIMELINE_FIELDS else -1
        if position >= 0:
            setattr(self, field, datetime.date.today().isoformat())
        for later_field in TIMELINE_FIELDS[position + 1:]:
            setattr(self, later_field, "")
        self.decision = status if status in DECISIONS else ""

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

    def latex_timeline_cell(self):
        """Build the table cell with the timeline of the entry.

        Returns:
            LaTeX for the cell: one line per recorded timeline date, each
            labelled in the wording of this kind of entry.
        """
        lines = []
        for field in TIMELINE_FIELDS:
            date = getattr(self, field)
            if not date:
                continue
            label = self.timeline_labels[field]
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
    """Contact with a private recruiter (Einschaltung eines Vermittlers)."""

    kind = "recruiter"
    label = "Recruiter contact"
    group = "Recruiter contacts"
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
    """Visit to a job fair or career event."""

    kind = "fair"
    label = "Job fair"
    group = "Job fairs"
    form_fields = ["title", "company", "location", "url", "contact",
                   "applied"]
    field_labels = {"title": "Event", "company": "Organiser",
                    "location": "Venue", "url": "Event website",
                    "contact": "Who you spoke to", "applied": "Date visited"}
    field_hints = {"title": "e.g. heise Jobs IT-Tag Stuttgart",
                   "contact": "optional, the people or companies you talked"
                              " to at the stands"}
    section = "Jobmessen"
    columns = ("Veranstaltung", "Verlauf")
    timeline_labels = {
        "applied": "Besuch",
        "invited": "Kontakte geknüpft",
        "interview": "Folgegespräch",
        "decided": "Abschluss",
    }
    decision_labels = {"offer": "Zusage", "rejected": "Absage"}


class NetworkEffort(Entry):
    """Any other documented effort, e.g. a speculative enquiry."""

    kind = "network"
    label = "Networking"
    group = "Networking"
    form_fields = ["title", "company", "contact", "location", "url",
                   "applied"]
    field_labels = {"title": "What you did",
                    "company": "Organisation or person",
                    "contact": "Contact person", "location": "Place",
                    "url": "Link", "applied": "Date"}
    field_hints = {"title": "e.g. Initiativanfrage, Meetup, Empfehlung über"
                            " Kontakt",
                   "location": "or \"remote\" if it was not in person"}
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
