---
description: >-
  Rules and context for the Evoker project.
trigger: always_on
---

# Evoker Project Rules

Welcome to the Evoker repository! 
Evoker is a secure plugin framework that connects a host application to a standalone 
freethreaded Python worker using XML-RPC and Arrow IPC.

## Key Directives
- **Zero-Copy First**: When passing large data between the host and plugins, always use PyArrow memory-mapped files (`arrow_ipc.py`) rather than serializing over XML-RPC.
- **Isolated Worker Environment**: The standalone Python worker (`worker.py`) must never import `.pyd` C-extensions compiled for the host application to avoid fatal DLL collisions.
- **Agent Skills**: If you are asked to debug or build Evoker, or to create a new plugin, remember to use your available skills:
  - `evoker-architecture`: For context on how the host, client, and worker interact.
  - `build-evoker-release`: For instructions on how to package and run integration tests.
  - `create-evoker-plugin`: For the standard layout of `manifest.json` and `main.py`.
