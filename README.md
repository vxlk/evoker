# Evoker

<p align="center">
  <img src="assets/evoker_mascot.jpg" width="250" alt="Evoker Mascot">
</p>

<p align="center">
  <a href="https://github.com/vxlk/evoker/actions"><img src="https://img.shields.io/github/actions/workflow/status/vxlk/evoker/ci.yml?branch=main" alt="Build Status"></a>
  <a href="https://pypi.org/project/evoker-plugin-host/"><img src="https://img.shields.io/pypi/v/evoker-plugin-host" alt="PyPI Version"></a>
  <a href="https://vxlk.github.io/Evoker/"><img src="https://img.shields.io/badge/docs-latest-blue.svg" alt="Documentation"></a>
  <a href="https://github.com/vxlk/evoker/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vxlk/evoker" alt="License"></a>
  <a href="https://codecov.io/gh/vxlk/evoker"><img src="https://img.shields.io/codecov/c/github/vxlk/evoker" alt="Codecov"></a>
</p>

<p align="center">
  📖 <b><a href="https://vxlk.github.io/Evoker/">Read the full documentation here</a></b>
</p>

**Evoker** is a dead-simple, process-isolated plugin system for Python desktop applications. Ship your app with fully decoupled plugins that run in isolated subprocesses — users extend your application by dropping a folder in. No internet required, no install wizards, no shared state bugs.

## Core Philosophy

Evoker occupies a highly strategic, underserved niche: **Extending native applications with Python's data/AI ecosystem without compromising application stability.**

To achieve this, the framework is driven by three strict architectural principles:
1. **Stateless Invocation**: Evoker is built around a host-driven, request-response model. By enforcing this paradigm, Evoker forces plugin developers to write clean, modular extensions (microservices) rather than deeply entangled, state-corrupting scripts.
2. **No Synchronized State**: Many modern microservice and plugin architectures collapse under their own weight because they attempt to synchronize complex state and maintain chatty, two-way communication across boundaries. Evoker avoids this by explicitly restricting communication to simple invocations.
3. **True Process Isolation**: If a plugin crashes, segfaults, or OOMs, the host application must survive. Plugins are treated as untrusted worker nodes.

## Native Language Bindings

Evoker isn't just for Python host applications! We provide official, fully-featured host clients in **Python**, **Rust**, **C++**, and **C**. 

These native bindings include **Transparent Runtime Bootstrapping**. This means your native C++ or Rust application does **not** require the end-user to have Python installed on their system. The Evoker client will automatically download, extract, and provision an isolated `python-build-standalone` runtime behind the scenes!

## Core Features
*   **Multi-Headed Isolation**: Plugins run in their own dedicated Python environments (via XML-RPC). If a plugin crashes, your Host Application stays alive.
*   **Custom API & Dependency Injection**: Host applications can inject their own Python packages and APIs directly into the `sys.path` of the plugin worker processes using the `injected_packages` parameter. Plugins consume host-provided libraries without needing their own installations.
*   **Auto-Installing Dependencies**: Drop a `requirements.txt` or an offline `wheels/` folder into a plugin, and Evoker handles the `pip install` transparently upon loading into an isolated virtual environment.
*   **Deep Introspection**: The `PluginManager` dynamically reads type hints and signature defaults, ensuring your Host knows exactly how to invoke the plugin.

---

## Installation

Evoker downloads and bundles a standalone Python interpreter during its installation phase. This ensures that plugins can run in fully isolated environments without relying on the end-user's system Python.

To install Evoker:

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

For a comprehensive, full-system overview of how to build a Evoker application with custom API injection and package the entire architecture into a standalone PyInstaller binary, check out our official example repository:

👉 **[Evoker Example Host Repository](https://github.com/vxlk/evoker-example)**

You can also see the local [examples/README.md](examples/README.md) directory for a simpler "Hello World" demonstration of how to boot a `PluginClient`.

## Documentation

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

Evoker includes a `dev.py` utility script for streamlining local development tasks.

* `python hosts/python/dev.py install`: Creates a `.venv` (if missing), activates it, and installs development dependencies via `pip install -e .[dev]`.
* `python hosts/python/dev.py build`: Builds the standard PyInstaller example.
* `python hosts/python/dev.py docs`: Builds the static Docusaurus site in the `doc/` directory.
* `python hosts/python/dev.py test`: Activates the virtual environment and runs the test suite using `pytest`.
* `python hosts/python/dev.py run-example`: Activates the virtual environment and runs the `examples/host.py` script.

## PyInstaller Packaging

Evoker is natively designed to be compiled into a standalone binary using PyInstaller. 
When distributing your host application via a `One-Dir` build (e.g., `dist/host/`), PyInstaller will automatically place its bundled modules inside an `_internal` directory to keep the root directory clean.

Because plugins are designed to be user-facing, you should **not** bundle your default `plugins` or `tools` directories within PyInstaller's `datas` array, as this would hide them inside the `_internal` folder. Instead, the `host.py` script expects these folders to be placed directly alongside the `.exe` at the root of the distribution directory.

**Best Practice for Distribution:**
After running your PyInstaller compilation, implement a post-build step in your build scripts to copy your default plugins alongside the executable.
Here is an example `build.ps1` script you can use:
```powershell
# 1. Build the executable
.\venv\Scripts\python.exe -m PyInstaller build.spec -y

# 2. Deploy user-facing plugin folders alongside the binary
Copy-Item -Recurse -Force "plugins" "dist\host\plugins"
Copy-Item -Recurse -Force "tools" "dist\host\tools"
```
This ensures end-users can seamlessly add their own `.venv` or `.zip` plugins right next to your binary without navigating through Pyinstaller's internal DLL structure!
