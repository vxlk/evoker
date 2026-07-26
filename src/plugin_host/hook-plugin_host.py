from PyInstaller.utils.hooks import collect_data_files

# This hook tells PyInstaller to automatically bundle all data files within `plugin_host`
# Whenever a Pyinstaller build is triggered on an app that imports `plugin_host`, 
# this hook runs and ensures the bundled standalone python environments (and installers)
# are perfectly packaged into the `_internal` directory without the user needing to 
# configure `datas` in their .spec file!
datas = collect_data_files('plugin_host')
