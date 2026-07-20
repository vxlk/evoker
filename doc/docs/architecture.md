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
