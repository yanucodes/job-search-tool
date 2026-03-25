import json
import os

import arbeitsagentur

CONFIG_FILE = "config.json"
SEARCH_SERVICES = {
    "arbeitsagentur": arbeitsagentur
}


def load_config():
    """Load search configurations from JSON file.

    If the file does not exist, create it with an empty list.

    Returns:
        List of dictionaries with search configurations.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
    return []


def add_config(search_service):
    """Add a new search configuration for a given service. Updated list is
    saved in a JSON file. Does nothing if the service is not found or the
    user adds an existing configuration or exits before configuration is added.

    Args:
        search_service: Name of the search service to configure.
    """
    if search_service not in SEARCH_SERVICES:
        print(f"Service '{search_service}' is not available.")
    else:
        new_config = SEARCH_SERVICES[search_service].get_config()
        if new_config is not None:
            new_entry = {"service": search_service, "config": new_config}
            configs = load_config()
            if new_entry in configs:
                print("This configuration already exists.")
            else:
                configs.append(new_entry)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(configs, f)
