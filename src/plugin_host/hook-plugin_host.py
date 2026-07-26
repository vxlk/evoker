import os
from PyInstaller.utils.hooks import collect_data_files, get_package_paths

# This hook tells PyInstaller to automatically bundle all data files within `plugin_host`
# Whenever a Pyinstaller build is triggered on an app that imports `plugin_host`, 
# this hook runs and ensures the bundled standalone python environments (and installers)
# are perfectly packaged into the `_internal` directory without the user needing to 
# configure `datas` in their .spec file!
datas = collect_data_files('plugin_host')

# Automatically deploy Behemoth HTML documentation to the host's plugins folder
pkg_base, pkg_dir = get_package_paths('plugin_host')
docs_html_path = os.path.join(pkg_dir, 'docs_html')

if os.path.exists(docs_html_path):
    # Appending (source, dest) to datas tells PyInstaller to copy the HTML files
    # directly to `dist/host/plugins/docs` rather than burying them in `_internal`!
    datas.append((docs_html_path, 'plugins/docs'))

# The worker script is spawned dynamically via subprocess, so Pyinstaller's analysis 
# doesn't see it statically. We must explicitly include it in the hidden imports so 
# it gets packaged into the PYZ archive and can be executed via runpy in the frozen bundle.
hiddenimports = ['plugin_host.worker']

# PyInstaller compiles all .py files into a PYZ archive by default.
# However, if a plugin runs in an EXTERNAL `.venv`, that external Python interpreter
# cannot read from the PYZ archive. It needs the raw `.py` source code of `plugin_host`.
# By adding the package directory to `datas`, PyInstaller will copy the raw source code
# to `_internal/plugin_host_src`, allowing the external Python to import it via PYTHONPATH.
datas.append((pkg_dir, 'plugin_host_src/plugin_host'))




