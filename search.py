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
