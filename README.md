# Behemoth

![Behemoth Mascot](assets/mascot.jpg)

**Behemoth** is a hyper-modular, multi-headed plugin architecture designed for infinite scale. Built for host applications that require processing massive datasets or orchestrating complex AI workflows, Behemoth isolates plugins in separate processes while maintaining zero-copy data transfer speeds.

## Core Features
*   **Multi-Headed Isolation**: Plugins run in their own dedicated Python environments (via XML-RPC). If a plugin crashes, your Host Application stays alive.
*   **Custom API & Dependency Injection**: Host applications can inject their own Python packages, APIs, and pre-compiled dependencies (like `pyarrow` or `numpy`) directly into the `sys.path` of the plugin worker processes using the `injected_packages` parameter.
*   **Auto-Installing Dependencies**: Drop a `requirements.txt` or an offline `wheels/` folder into a plugin, and Behemoth handles the `pip install` transparently upon loading into an isolated virtual environment.
*   **Deep Introspection**: The `PluginManager` dynamically reads type hints and signature defaults, ensuring your Host knows exactly how to invoke the plugin.

---

## Installation

Behemoth downloads and bundles a standalone Python interpreter during its installation phase. This ensures that plugins can run in fully isolated environments without relying on the end-user's system Python.

To install Behemoth:

```bash
pip install .
```

> [!WARNING]
> **Pip Caching Behavior**
> `pip` aggressively caches built wheels. If you change the `PYTHON_VERSION` in `setup.py`, running `pip install .` again might simply install the cached wheel without re-running the python downloader script. 
> 
> To force a clean build and ensure the latest python version is downloaded, use:
> ```bash
> pip install . --no-cache-dir
> ```

## Usage

For a comprehensive, full-system overview of how to build a Behemoth application, intercept data streams with PyArrow, and package the entire architecture into a standalone PyInstaller binary, check out our official example repository:

👉 **[Behemoth Example Host Repository](https://github.com/vxlk/behemoth-example)**

You can also see the local [examples/](file:///c:/Users/small/Desktop/projects/Behemoth/examples/README.md) directory for a simpler "Hello World" demonstration of how to boot a `PluginClient`.

## Documentation

📖 **[Read the full documentation →](https://vxlk.github.io/Behemoth/)**

To run the documentation site locally:
1. Ensure you have Node.js (>= 18.0) installed.
2. Navigate to the `doc` directory:
   ```bash
   cd doc
   ```
3. Install dependencies and start the development server:
   ```bash
   npm install
   npm start
   ```

## Development

Behemoth includes a `dev.py` utility script for streamlining local development tasks.

* `python dev.py install`: Creates a `.venv` (if missing), activates it, and installs development dependencies via `pip install -e .[dev]`.
* `python dev.py build`: Builds the standard PyInstaller example.
* `python dev.py docs`: Builds the static Docusaurus site in the `doc/` directory.
* `python dev.py test`: Activates the virtual environment and runs the test suite using `pytest`.
* `python dev.py run-example`: Activates the virtual environment and runs the `examples/host.py` script.
* `python dev.py build-release`: Bundles all plugin dependencies dynamically and builds the PyInstaller release bundle via `host.spec`.

## PyInstaller Packaging

Behemoth is natively designed to be compiled into a standalone binary using PyInstaller. 
When distributing your host application via a `One-Dir` build (e.g., `dist/host/`), PyInstaller will automatically place its bundled modules inside an `_internal` directory to keep the root directory clean.

Because plugins are designed to be user-facing, you should **not** bundle your default `plugins` or `tools` directories within PyInstaller's `datas` array, as this would hide them inside the `_internal` folder. Instead, the `host.py` script expects these folders to be placed directly alongside the `.exe` at the root of the distribution directory.

**Best Practice for Distribution:**
After running your PyInstaller compilation, implement a post-build step in your build scripts to copy your default plugins alongside the executable.
An example PowerShell build script `build.ps1` is provided in the root of this repository:
```powershell
# 1. Build the executable
.\venv\Scripts\python.exe -m PyInstaller build.spec -y

# 2. Deploy user-facing plugin folders alongside the binary
Copy-Item -Recurse -Force "plugins" "dist\host\plugins"
Copy-Item -Recurse -Force "tools" "dist\host\tools"
```
This ensures end-users can seamlessly add their own `.venv` or `.zip` plugins right next to your binary without navigating through Pyinstaller's internal DLL structure!
