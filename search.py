import json
import os

from jobboards import arbeitsagentur
from jobboards import mock

CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_DIR = "results"
SERVICES = {
    "arbeitsagentur": arbeitsagentur,
    "mock": mock,
}


def default_config():
    """Return a fresh configuration structure.

    Returns:
        Dictionary with an output directory and an empty list of searches.
    """
    return {"output_dir": DEFAULT_OUTPUT_DIR, "searches": []}


def load_config():
    """Load the configuration from the JSON file.

    Creates the file with default contents if it does not exist. Configuration
    files written in the older list-only format are migrated to the current
    structure and saved back.

    Returns:
        Dictionary with "output_dir" and "searches" keys.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):  # migrate legacy list-only format
            data = {"output_dir": DEFAULT_OUTPUT_DIR, "searches": data}
            save_config(data)
        return data
    config = default_config()
    save_config(config)
    return config


def save_config(config):
    """Write the configuration to the JSON file.

    Args:
        config: Configuration dictionary to persist.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_searches():
    """Return the list of saved search configurations.

    Returns:
        List of dictionaries with "service" and "config" keys.
    """
    return load_config()["searches"]


def get_output_dir():
    """Return the directory where search results are saved.

    Returns:
        Filesystem path as a string.
    """
    return load_config()["output_dir"]


def set_output_dir(path):
    """Set the directory where search results are saved.

    The path is expanded (so "~" works) and the directory is created if it
    does not exist.

    Args:
        path: Filesystem path to store results in.

    Returns:
        The expanded path that was saved.
    """
    expanded = os.path.expanduser(path)
    os.makedirs(expanded, exist_ok=True)
    config = load_config()
    config["output_dir"] = expanded
    save_config(config)
    return expanded


def find_new_jobs(seen):
    """Run all saved searches and return jobs the user has not seen yet.

    Results are normalized by their job board module and de-duplicated
    across searches.

    Args:
        seen: Set of (service, job_id) tuples the user has already seen.

    Returns:
        List of (service, record) tuples for unseen jobs, where record is
        a normalized job record.
    """
    new_jobs = []
    found = set(seen)
    for entry in get_searches():
        service = entry["service"]
        results = SERVICES[service].search(entry["config"])
        if results is None:
            continue
        for job in results:
            record = SERVICES[service].normalize(job)
            if (service, record["id"]) not in found:
                found.add((service, record["id"]))
                new_jobs.append((service, record))
    return new_jobs


def add_config(search_service):
    """Add a new search configuration for a given service and save it.

    Does nothing if the service is not found, the user exits before a
    configuration is provided, or an identical configuration already exists.

    Args:
        search_service: Name of the search service to configure.
    """
    if search_service not in SERVICES:
        print(f"Service '{search_service}' is not available.")
        return
    new_config = SERVICES[search_service].get_config()
    if new_config is None:
        return
    new_entry = {"service": search_service, "config": new_config}
    config = load_config()
    if new_entry in config["searches"]:
        print("This configuration already exists.")
        return
    config["searches"].append(new_entry)
    save_config(config)


def update_config(index):
    """Update an existing search configuration at a given index.

    Uses the service's get_config to collect new parameters and saves the
    updated configuration. Does nothing if the index is invalid or the user
    exits before a valid configuration is provided.

    Args:
        index: Index of the configuration to update.
    """
    config = load_config()
    searches = config["searches"]
    if index < 0 or index >= len(searches):
        print("Invalid configuration index.")
        return
    entry = searches[index]
    service = entry["service"]
    new_config = SERVICES[service].get_config(config=entry["config"])
    if new_config is not None:
        searches[index]["config"] = new_config
        save_config(config)


def remove_config(index):
    """Remove a search configuration at a given index and save the result.

    Args:
        index: Index of the configuration to remove.
    """
    config = load_config()
    searches = config["searches"]
    if index < 0 or index >= len(searches):
        print("Invalid configuration index.")
        return
    searches.pop(index)
    save_config(config)
