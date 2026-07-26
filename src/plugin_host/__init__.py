"""
Plugin Host package.
"""
import sys

# PyInstaller frozen bundle worker interception logic
# When a PyInstaller frozen bundle launches a worker subprocess, it passes the 
# `--behemoth-worker` flag. Because sys.executable points to the user's host app,
# we must intercept this execution as early as possible (during import) to 
# run the worker script instead of the user's main application logic.
if len(sys.argv) >= 3 and sys.argv[1] == '--behemoth-worker':
    import runpy
    
    # Remove --behemoth-worker so the worker script doesn't see it
    # We drop the first 3 args: host.exe, --behemoth-worker, worker_script_path
    sys.argv = ["plugin_host.worker"] + sys.argv[3:]
    
    # Execute the worker module directly from the PyInstaller embedded PYZ archive
    runpy.run_module("plugin_host.worker", run_name="__main__")
    
    # Exit after the worker finishes to prevent host.py from running its logic
    sys.exit(0)

