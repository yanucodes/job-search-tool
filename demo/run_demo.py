"""Run the web interface against the obviously-fake demo data.

This points the app at demo/config.json (mock job board + demo results dir),
so it never touches the real config.json, the real results, or any external
API. Used to produce screenshots of the tool.

    python demo/run_demo.py    # from the job-search-tool directory
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import search  # noqa: E402

# Redirect the app to the demo configuration before anything reads it.
search.CONFIG_FILE = os.path.join(HERE, "config.json")

import app  # noqa: E402

if __name__ == "__main__":
    app.app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)
