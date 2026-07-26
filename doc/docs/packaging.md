---
sidebar_position: 5
---

# PyInstaller & Packaging

Bundling a Behemoth Host Application via PyInstaller requires specific handling due to the architecture's reliance on spawning sub-processes and isolated virtual environments. 

## 1. Use a "One-Dir" Build
**Never use a one-file (`-F`) build.** 

A one-file build embeds all your files inside the executable and extracts them to a temporary `_MEIxxxxx` folder on execution. When the app closes, that folder is deleted. If you use a one-file build:
- Behemoth will recreate the `.venv` and download dependencies every single time the app launches.
- Plugins become read-only and uneditable by users.
- Users cannot drop new plugins into the directories.

Instead, always use a **one-dir** build (`-D` or `COLLECT` in your `.spec` file), which generates a persistent folder containing your `.exe` alongside your `plugins/` directories.

## 2. Automatic PyInstaller Hooks
Behemoth ships with a native PyInstaller hook! When you run `pyinstaller host.py`, PyInstaller will automatically detect Behemoth and bundle the `plugin_host` (and its bundled standalone Python interpreters) into the executable's `_internal` directory. 

You **do not** need to manually add `plugin_host` to your `.spec` file's `datas=[]` array.

## 3. Bundling the Plugins Directory
If you want PyInstaller to automatically copy your default `plugins` folder into the compiled `dist/host` directory, add it to your `.spec` file's `datas`:

```python
    datas=[
        ('plugins', 'plugins'),
    ],
```

## 4. Resolving Paths in the Host
When your `host.py` application is compiled by PyInstaller, `__file__` behaves differently. If you use `Path(__file__).parent / "plugins"` inside a frozen PyInstaller app, it will look inside the hidden `_internal` directory, not the root of your application folder where the user expects to see the `plugins` folder!

To solve this, use Behemoth's built-in path utility to find the true application directory:

```python
from plugin_host.utils import get_app_dir

base_dir = get_app_dir(__file__)
plugins_client = PluginClient(base_dir / "plugins")
```
This utility gracefully falls back to `__file__` when running as a normal python script, but correctly points to the `.exe` location when running as a PyInstaller bundle.
