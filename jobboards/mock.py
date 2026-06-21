"""
Demo job board that serves obviously fake postings from a local JSON file.

This module exists to showcase the pluggable job-board interface — the same
search / normalize / description contract the real boards implement — without
calling any external API. Point a search configuration's "file" key at a JSON
file of mock postings and the rest of the app behaves exactly as it would with
a real board.
"""

import json


FIELDS = ("id", "title", "company", "location", "published", "url",
          "description")


def search(config):
    """Return the raw postings stored in the configured JSON file.

    Args:
        config: Search configuration. The "file" key holds the path to a JSON
            file containing a list of posting dictionaries.

    Returns:
        List of raw posting dictionaries, or None if the file is missing or
        cannot be parsed.
    """
    path = config.get("file")
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Mock board: could not read {path}: {error}")
        return None


def normalize(job):
    """Convert a raw mock posting to the standard record format.

    The description is kept on the record so description() can return it
    without a second lookup.

    Args:
        job: A posting dictionary from the mock JSON file.

    Returns:
        Dictionary with the standard record keys.
    """
    return {field: job.get(field, "") for field in FIELDS}


def description(record):
    """Return the stored description for a normalized mock record.

    Args:
        record: A record as returned by normalize().

    Returns:
        The posting description as an HTML string.
    """
    return record.get("description") or "<p>No description available.</p>"


def get_config(config=None):
    """Return a search configuration for the mock board.

    The mock board is configured non-interactively, so an existing config is
    returned unchanged and otherwise a default pointing at the demo file is
    used.

    Args:
        config: Optional existing configuration.

    Returns:
        Configuration dictionary.
    """
    return dict(config) if config else {"file": "demo/mock_jobs.json"}
