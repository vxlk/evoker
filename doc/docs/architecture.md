---
sidebar_position: 2
---

# Architecture

Behemoth utilizes a process-isolated client/worker architecture. 

## Process Isolation

When a host application initializes a `PluginClient`, it points to a directory of plugins. Behemoth spawns an isolated `PluginWorker` process for that directory. This ensures that:
- Heavy computations do not block the host application's event loop.
- Crashes (like segmentation faults in C-extensions) inside a plugin kill the worker, but leave the host entirely unscathed.

## Zero-Copy IPC with PyArrow

Transferring gigabytes of data over standard RPC protocols like JSON/HTTP or XML-RPC is too slow. 
Behemoth solves this by using **PyArrow Memory-Mapped Files**. 
1. The sender serializes data to a memory-mapped file on the OS.
2. The sender passes the *filepath* over XML-RPC.
3. The receiver deserializes the memory-mapped file instantly, achieving zero-copy reads.

## Zero-Install Framework Injection (PYTHONPATH)

You might wonder: *If plugins run in completely isolated Python `.venv` environments, how can they `import plugin_host` without installing the Behemoth framework inside their `.venv`?*

When the `PluginClient` launches the worker process, it dynamically calculates the absolute path to the Behemoth `src` directory (or the extracted `sys._MEIPASS` directory if running from a frozen PyInstaller bundle) and forcefully overrides the `PYTHONPATH` environment variable for the worker subprocess. 

This effectively tricks the isolated Python interpreter into finding the `plugin_host` module directly from the host application's disk location. Plugins can natively import base classes and IPC utilities without redundant installations or version conflicts!
