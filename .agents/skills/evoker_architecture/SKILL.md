---
name: evoker-architecture
description: >-
  Provides context and architectural details for the Evoker project. Use this skill when 
  the user asks questions about Evoker's design, how plugins are loaded, how the XML-RPC 
  communication works, or how to develop plugins or host integrations for Evoker.
---

# Evoker Architecture and Context

Evoker is a plugin framework that allows a host application (written in C++ or Python) to execute and communicate with Python plugins in a secure, isolated manner. 

## High-Level Architecture

1. **Host Process**: The main application running the user interface or core logic. It embeds `PluginClient` (if written in Python) or a C++ equivalent to talk to the worker.
2. **Worker Process (`worker.py`)**: A completely separate standalone Python interpreter process spawned by the Host. It runs `evoker.worker` and exposes an XML-RPC server.
3. **Communication**:
   - **RPC**: XML-RPC over a TCP socket is used for control flow, discovery, and small messages.
   - **Data Transfer**: Apache Arrow (PyArrow) memory-mapped files via Arrow IPC are used for zero-copy, high-bandwidth data transfers between the host and plugins.

## Key Components

### 1. The Worker (`evoker/worker.py`)
- Starts an XML-RPC server that the host connects to.
- Uses `evoker.manager.PluginManager` to load plugins and route requests to them.
- Uses a standalone Freethreaded (`cp313t`) Python build distributed with Evoker to avoid GIL restrictions.

### 2. Plugin Loading (`evoker/manager.py` & `evoker/installer.py`)
- Plugins are stored in a `plugins/` directory. Each plugin has a `manifest.json`, `__init__.py`, and `requirements.txt`.
- When the worker boots, `installer.py` reads `requirements.txt` and automatically builds `.whl` files (offline caching) and installs them into a plugin-specific `.venv`.
- `manager.py` then dynamically loads the `__init__.py` using `importlib`, injecting the plugin's `.venv/Lib/site-packages` into `sys.path` so it can find its dependencies.

### 3. The Client (`hosts/python/src/evoker_client/client.py`)
- Python reference implementation of the host-side client.
- Spawns the worker subprocess, locates the standalone Python interpreter, and establishes the XML-RPC connection.
- During PyInstaller bundling, it ensures the `evoker` package is isolated in `_MEIPASS/evoker_pkg` to prevent DLL collisions (e.g., C-extensions compiled for the host Python crashing the worker Python).

### 4. Arrow IPC (`hosts/python/examples/host_api/arrow_ipc.py`)
- Exposes `read_table_from_mmap` and `write_table_to_mmap` functions.
- PyArrow Tables are written to temporary memory-mapped `.arrow` files, and the file path is passed over XML-RPC. The receiving end memory-maps the file, achieving zero-copy data transfer.

## Plugin Structure Example
```text
plugins/my_plugin/
├── manifest.json       # Metadata and context menu strategies
├── __init__.py         # Entry point (must define `on_start` or custom actions)
└── requirements.txt    # Standard pip requirements
```
