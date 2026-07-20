---
sidebar_position: 4
---

# Development Scripts

Behemoth provides a unified `dev.py` script to handle common development tasks.

To use it, run `python dev.py <command>`.

- `python dev.py install`: Checks for and creates a `.venv`, activates it, and installs local dependencies.
- `python dev.py build`: Standard PyInstaller build for the example host.
- `python dev.py docs`: Builds this documentation site!
- `python dev.py test`: Runs the pytest test suite.
- `python dev.py run-example`: Runs the primary test example in `examples/host.py`.
- `python dev.py build-release`: Bundles the plugins and their dependencies for a production release using PyInstaller.
