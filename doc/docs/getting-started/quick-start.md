---
title: Quick Start
sidebar_label: Quick Start
sidebar_position: 2
---

# Quick Start

In this tutorial, you will create a minimal Evoker application in 3 simple steps:
1. Define a plugin directory with a manifest and entry point.
2. Initialize and invoke the plugin using `PluginClient` in a host script.
3. Run the application and observe process-isolated execution.

---

## Step 1: Create a Plugin

Create a project directory structure containing a host script and a `plugins/` directory:

```text
my_app/
  plugins/
    hello_plugin/
      manifest.json
      __init__.py
  host.py
```

### 1. Plugin Manifest (`manifest.json`)

Inside `plugins/hello_plugin/manifest.json`, define basic metadata describing your plugin. 
**Note:** The `name` field must exactly match the name of the plugin's directory.

```json
{
  "name": "hello_plugin",
  "version": "1.0.0",
  "description": "My first plugin"
}
```

### 2. Plugin Code (`__init__.py`)

Inside `plugins/hello_plugin/__init__.py`, write the function you want to expose. Functions can use standard Python type annotations:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

---

## Step 2: Create the Host Application

In `host.py`, import `PluginClient`, point it to your `plugins` directory, start the worker subprocess, and invoke the action:

```python
from pathlib import Path
from plugin_host.client import PluginClient

# Point the client to your plugins directory
client = PluginClient(Path("plugins"))

# Spawn the isolated worker process
client.start_worker()

try:
    # Discover available plugins and their introspected actions
    manifest = client.get_plugins()
    print("Discovered Plugins:", manifest)

    # Invoke the greet function inside the isolated plugin worker
    result = client.run_action("hello_plugin", "greet", {"name": "World"})
    print("Result:", result)  # "Hello, World!"
finally:
    # Ensure the worker subprocess is cleanly terminated
    client.stop_worker()
```

---

## Step 3: Run the Application

Run `host.py` using Python:

```bash
python host.py
```

### Output

```text
Discovered Plugins: {'hello_plugin': {'greet': {'name': 'greet', 'signature': {'parameters': {'name': {'type': 'str', 'required': True}}}, 'is_keyword': False, 'strategy_metadata': None}}}
Result: Hello, World!
```

---

## Why Process Isolation Matters

When `client.run_action("hello_plugin", "greet", ...)` is executed:
- The function does **not** run in the memory space of `host.py`.
- It executes inside a dedicated Python worker subprocess managed by `PluginClient`.
- Communication is routed over an XML-RPC control channel.
- If `hello_plugin` raises an unhandled exception, runs out of memory, or crashes due to a C-extension segmentation fault, the host process remains completely unaffected and can safely recover or restart the worker.

---

## What's Next?

Now that you have seen the basics in action, explore the architecture and advanced capabilities of Evoker:

- [Architecture Overview](../architecture/overview.md) — Learn how workers, discovery, and XML-RPC communication layers interact.
- [Writing Plugins](../guides/writing-plugins.md) — Dive deeper into plugin manifests, action decorators, and custom dependencies.
- [API Injection](../guides/api-injection.md) — Inject custom host APIs and pre-compiled libraries directly into worker processes.
- [Strategy Patterns](../guides/strategies.md) — Use declarative strategy matchers to bind plugin functions to UI actions.
