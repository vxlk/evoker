---
name: create-evoker-plugin
description: >-
  Provides the standard template and instructions for creating a new Evoker plugin. 
  Use this skill when the user asks to create a new plugin, add a plugin, or define 
  plugin context menu actions.
---

# Creating an Evoker Plugin

Evoker plugins are stored as directories containing three core files: `manifest.json`, `requirements.txt`, and `__init__.py`.

## 1. Create the Directory Structure

```text
hosts/python/examples/plugins/my_new_plugin/
├── manifest.json
├── requirements.txt
└── __init__.py
```

## 2. Define `manifest.json`

The manifest registers the plugin with the host and defines how it should be activated.
It supports exact match triggers (`on_start`) or prefix match triggers (e.g. for context menus).

```json
{
  "name": "my_new_plugin",
  "version": "1.0.0",
  "strategies": [
    {
      "trigger": "on_start",
      "match_type": "exact",
      "action": "on_start"
    },
    {
      "trigger": "context_menu/",
      "match_type": "prefix",
      "action": "on_context_menu"
    }
  ]
}
```

## 3. Specify Dependencies in `requirements.txt`

List any external PyPI dependencies your plugin needs. Evoker will automatically download and bundle wheels for these when the host runs.

```text
pyarrow
# Add other dependencies here
```

## 4. Implement `__init__.py`

The init file must export functions corresponding to the `action` strings defined in the manifest.

```python
import pyarrow as pa
import host_api.arrow_ipc as arrow_ipc

def on_start(app_context):
    print(f"[Plugin] Hello from my_new_plugin! Context: {app_context}")

def on_context_menu(app_context, sub_action):
    print(f"[Plugin] Context menu triggered with {sub_action}")
    
    # Example: Receive a PyArrow table path from the host
    if "table_path" in app_context:
        table = arrow_ipc.read_table_from_mmap(app_context["table_path"])
        print(f"[Plugin] Received {table.num_rows} rows from host!")
```
