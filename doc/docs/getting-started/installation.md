---
title: Installation
sidebar_label: Installation
sidebar_position: 1
---

# Installation

This guide covers how to install Behemoth as a library in your application, configure development environments, and utilize the built-in development CLI tooling.

---

## Prerequisites

Before installing Behemoth, ensure your system satisfies the following prerequisites:

- **Python 3.10+**: Behemoth relies on modern type hints, process spawning primitives, and PyArrow integration.
- **pip**: Ensure `pip` is updated to a modern version (`pip install --upgrade pip`).
- **Node.js 18+** *(Optional)*: Required only if you intend to build or preview the local Docusaurus documentation site.

---

## Basic Installation

To install Behemoth into your current Python environment directly from the repository source:

```bash
pip install . --no-cache-dir
```

:::warning Pip Caching and Standalone Pythons
During the build phase (`setup.py`), Behemoth automatically downloads a standalone Python distribution via [`python-build-standalone`](https://github.com/astral-sh/python-build-standalone) and packages it into the distribution.

`pip` aggressively caches built wheels. If you modify build configurations or standalone Python versions in `setup.py`, running `pip install .` without flags may reuse a stale cached wheel rather than triggering a clean standalone download. **Always use `--no-cache-dir` when installing from local source.**
:::

---

## Development Installation

If you are developing Behemoth itself or writing custom extensions, install the project in **editable mode** along with all development extras:

```bash
pip install -e .[dev]
```

### Included Development Dependencies

The `dev` extra includes comprehensive testing, fuzzing, and bundling toolchains:

- **`pytest`** (`>= 7.4.0`): Unit and integration test runner.
- **`hypothesis`** (`>= 6.82.0`): Property-based testing and fuzzing for IPC mechanisms and strategy matching.
- **`pytest-xprocess`** (`>= 0.22.0`): Process management fixture for integration tests involving worker subprocesses.
- **`tox`** (`>= 4.6.4`): Test automation across multiple Python environments.
- **`requests`** (`>= 2.31.0`): HTTP library used during build-time downloads of standalone Python distributions.
- **`zstandard`** (`>= 0.21.0`): High-compression archive decompression for standalone Python bundles (`.tar.zst`).

---

## Using the `dev.py` CLI

Behemoth provides a root-level `dev.py` script to automate common developer workflows without needing to memorize virtual environment paths or command-line flags.

### Common CLI Commands

| Command | Description |
| :--- | :--- |
| `python dev.py install` | Creates a local `.venv` (if missing), activates it, and installs Behemoth in editable mode with all dev dependencies (`pip install -e .[dev]`). |
| `python dev.py test` | Runs the full test suite using `pytest` within the isolated development virtual environment. |
| `python dev.py run-example` | Runs the demonstration application in unbuffered mode (`examples/host.py`), showcasing strategy matching and PyArrow IPC. |
| `python dev.py build-release` | Downloads target standalone Python distributions, installs PyInstaller, and builds a release bundle using `host.spec`. |
| `python dev.py docs` | Runs the Docusaurus production build (`npm run build` in `doc/`) to compile static documentation. |

### Example Usage

```bash
# Set up development virtualenv and install dependencies
python dev.py install

# Run the test suite
python dev.py test

# Launch the Hello World demo
python dev.py run-example
```

---

## Next Steps

Now that you have Behemoth installed, proceed to the [Quick Start Tutorial](./quick-start.md) to build your first plugin and host application.
