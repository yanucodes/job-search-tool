"""Companies worth applying to, kept as a list of their own.

A company you would like to work for is not an Eigenbemühung: nothing has
been done about it yet, and it may never have a posting to apply to. So it
is kept apart from the application list, in a file of its own, and never
reaches the PDF summary. Each company records where its openings are listed
and why it is on the list, with the same priority levels as a job.
"""

import datetime
import json
import os
import uuid

import entries
import tracker

COMPANIES_FILE = "companies.json"
FIELDS = ["name", "location", "url", "notes"]
REQUIRED_FIELDS = ["name"]
FIELD_LABELS = {"name": "Company", "location": "Location",
                "url": "Careers page", "notes": "Notes"}
FIELD_TYPES = {"name": "text", "location": "text", "url": "url",
               "notes": "textarea"}
FIELD_HINTS = {"url": "where the company lists its openings",
               "notes": "why it is on the list, what to watch out for"}


class Company:
    """A company you are interested in applying to."""

    def __init__(self, id="", name="", location="", url="", notes="",
                 priority=None, added="", extra=None):
        """Create a company.

        Args:
            id: Identifier of the company.
            name: Name of the company.
            location: Where it is, or "remote".
            url: Link to the page listing its openings.
            notes: Optional free text with your own remarks.
            priority: Optional priority level, one of entries.PRIORITIES.
            added: ISO date the company was put on the list. Defaults to
                today.
            extra: Optional dictionary of further keys to keep, for values
                in the file that this class does not know about.
        """
        self.id = id
        self.name = name
        self.location = location
        self.url = url
        self.notes = notes
        self.priority = priority if priority in entries.PRIORITIES else None
        self.added = added or datetime.date.today().isoformat()
        self.extra = extra or {}

    @property
    def sort_key(self):
        """Order of the list: highest priority first, then by name.

        Returns:
            Tuple to sort companies by, unprioritised ones last.
        """
        return (self.priority or 99, self.name.casefold())

    def update(self, fields, priority):
        """Replace the recorded details.

        Args:
            fields: Dictionary of new values by field name, for the keys of
                FIELDS. A field left out is kept as it is.
            priority: New priority (one of entries.PRIORITIES), or None to
                clear it.
        """
        for field in FIELDS:
            if field in fields:
                setattr(self, field, fields[field])
        self.priority = priority if priority in entries.PRIORITIES else None

    def to_dict(self):
        """Convert the company to a dictionary for the companies file.

        Optional values that are unset are left out, as for entries.

        Returns:
            Dictionary of the company, ready to be serialized as JSON.
        """
        data = {"id": self.id, "name": self.name, "location": self.location,
                "url": self.url, "added": self.added}
        if self.notes:
            data["notes"] = self.notes
        if self.priority in entries.PRIORITIES:
            data["priority"] = self.priority
        data.update(self.extra)
        return data


def from_dict(data):
    """Build the company a companies-file dictionary describes.

    Args:
        data: Dictionary as stored in the companies file.

    Returns:
        A Company.
    """
    known = {"id", "name", "location", "url", "notes", "priority", "added"}
    fields = {key: value for key, value in data.items() if key in known}
    extra = {key: value for key, value in data.items() if key not in known}
    return Company(extra=extra, **fields)


def load_companies():
    """Load the list of companies.

    Returns:
        List of Company objects. Empty if nothing was saved yet.
    """
    path = tracker.output_path(COMPANIES_FILE)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [from_dict(data) for data in json.load(f)]


def save_companies(companies):
    """Write the list of companies to the output directory.

    Args:
        companies: List of Company objects to persist.
    """
    with open(tracker.output_path(COMPANIES_FILE), "w",
              encoding="utf-8") as f:
        json.dump([company.to_dict() for company in companies], f, indent=2,
                  ensure_ascii=False)


def add_company(fields, priority=None):
    """Add a company to the list.

    Args:
        fields: Dictionary of values by field name, for the keys of FIELDS.
        priority: Optional priority level (one of entries.PRIORITIES).
    """
    companies = load_companies()
    companies.append(Company(id=uuid.uuid4().hex, priority=priority,
                             **{field: fields.get(field, "")
                                for field in FIELDS}))
    save_companies(companies)


def update_company(index, fields, priority):
    """Replace the details of a saved company.

    Args:
        index: Index of the company in the saved list.
        fields: Dictionary of new values by field name.
        priority: New priority, or None to clear it.
    """
    companies = load_companies()
    companies[index].update(fields, priority)
    save_companies(companies)


def delete_company(index):
    """Remove a company from the list.

    Args:
        index: Index of the company in the saved list.
    """
    companies = load_companies()
    companies.pop(index)
    save_companies(companies)
