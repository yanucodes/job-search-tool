"""Read where the tool keeps its files.

The only setting is the output directory, stored under "output_dir" in
config.json. Without the file, or without the key, results go to the
default directory. The demo sets OUTPUT_DIR instead, so that it reads and
writes its own files whatever is configured.
"""

import json
import os

CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_DIR = "results"
OUTPUT_DIR = None  # takes precedence over the configured directory


def get_output_dir():
    """Return the directory where the tracker files are saved.

    Returns:
        Filesystem path as a string, with "~" expanded.
    """
    if OUTPUT_DIR:
        return OUTPUT_DIR
    path = DEFAULT_OUTPUT_DIR
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            path = json.load(f).get("output_dir", DEFAULT_OUTPUT_DIR)
    return os.path.expanduser(path)
