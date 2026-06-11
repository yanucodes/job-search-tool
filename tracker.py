"""Track which jobs the user has already seen.

All files live in the output directory configured in search.py.
"""

import json
import os

import search

SEEN_FILE = "seen.json"


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
