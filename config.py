"""Read where the tool keeps its files.

The only setting is the output directory, stored under "output_dir" in
config.json. Without the file, or without the key, results go to the
default directory.
"""

import json
import os

CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_DIR = "results"


def get_output_dir():
    """Return the directory where the tracker files are saved.

    Returns:
        Filesystem path as a string, with "~" expanded.
    """
    path = DEFAULT_OUTPUT_DIR
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            path = json.load(f).get("output_dir", DEFAULT_OUTPUT_DIR)
    return os.path.expanduser(path)
