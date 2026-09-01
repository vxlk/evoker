"""
Plugin Host package.
"""
import sys

import os

# PyInstaller frozen bundle worker interception logic
# When a PyInstaller frozen bundle launches a worker subprocess, it passes the
# `--evoker-worker` flag. Because sys.executable points to the user's host app,
# we must intercept this execution as early as possible (during import) to
# run the worker script instead of the user's main application logic.

# Prevent unbounded recursion in frozen bundles
if getattr(sys, "frozen", False):
    depth = int(os.environ.get("EVOKER_FROZEN_DEPTH", "0"))
    if depth > 2:
        print("Evoker fatal error: Unbounded subprocess recursion detected in frozen bundle.", file=sys.stderr)
        sys.exit(1)
    os.environ["EVOKER_FROZEN_DEPTH"] = str(depth + 1)

if len(sys.argv) >= 3 and sys.argv[1] == '--evoker-worker':
    import runpy

    # Remove --evoker-worker so the worker script doesn't see it
    # We drop the first 3 args: host.exe, --evoker-worker, worker_script_path
    sys.argv = ["evoker.worker"] + sys.argv[3:]

    # Execute the worker module directly from the PyInstaller embedded PYZ archive
    runpy.run_module("evoker.worker", run_name="__main__")

    # Exit after the worker finishes to prevent host.py from running its logic
    sys.exit(0)

