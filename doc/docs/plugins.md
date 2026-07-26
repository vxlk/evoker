---
sidebar_position: 3
---

# Creating Plugins

Plugins in Behemoth are just Python directories with an `__init__.py` that exposes functions.

## Structure

```
my_plugin/
├── __init__.py
├── requirements.txt
└── manifest.json (optional)
```

## Introspection

Behemoth's `PluginManager` uses Python's `inspect` module to dynamically read the type hints and default values of your functions. This means you do not need to register your functions manually; if they are public functions in `__init__.py`, they become available to the Host.

## Dependency Management

If your plugin requires third-party packages, simply list them in `requirements.txt`. Behemoth will automatically `pip install` these into the isolated worker environment before loading the plugin.

### Default Dependencies (PyArrow)
You **do not** need to include `pyarrow` in your `requirements.txt` to use Behemoth's zero-copy memory-mapped IPC. The Behemoth installer forcefully injects core dependencies like `pyarrow` into the isolated environment automatically during initialization.

### Offline Wheels Caching
When Behemoth installs dependencies, it automatically runs `pip wheel` behind the scenes to cache the `.whl` files into a local `wheels/` directory inside your plugin folder. On subsequent runs, Behemoth instructs `pip` to prefer these local files. 
If you are distributing your plugins to an air-gapped machine without internet access, you can manually drop `.whl` files into the `wheels/` directory and Behemoth will install them seamlessly!

## Worker Lifecycle & Shutdown

When your Host application spawns a `PluginClient`, it creates a headless Python worker process in the background.

```python
client = PluginClient(plugins_dir)
client.start_worker()
```

**CRITICAL**: You must manually shut down the worker when your host application closes. If you fail to do this (e.g. not catching `KeyboardInterrupt` or unexpected crashes), the headless Python process will zombie out and continue running in the background of the operating system indefinitely.

```python
try:
    # Run host logic
finally:
    client.stop_worker()
```

## Lifecycle Overrides (Keyword Signatures)

The `PluginManager` reserves certain function names as "keyword signatures". By defining a function with this name and the exact expected arguments, your plugin can hook into the host's lifecycle events.

Currently supported lifecycle hooks:

- `on_start(app_context)`: Called when the plugin worker successfully boots.

If you define a reserved function but your argument signature does not perfectly match (for instance, `def on_start(my_custom_arg):`), Behemoth will log a warning and ignore it, preventing runtime crashes.

## Custom Keyword Strategies

Host applications can inject their own declarative matching strategies into the plugin system. This is extremely useful for building dynamic UIs based on plugin functions.

Because the `PluginManager` runs in an isolated Python process, strategies must be serializable configuration dictionaries passed to the `PluginClient`.

### Example: Prefix Strategy

A common use case is collecting functions that begin with a specific prefix to populate a UI context menu.

**1. The Host Application Configuration**
```python
from plugin_host.client import PluginClient

# Tell the isolated worker to flag any function starting with "context_menu_"
client = PluginClient(
    plugins_dir,
    strategies=[
        {"type": "prefix", "value": "context_menu_"}
    ]
)
client.start_worker()
```

**2. The Plugin Implementation**
```python
# Inside your plugin's __init__.py
def context_menu_say_hello(name: str):
    print(f"Hello, {name}!")
```

**3. The UI Manifest**
When the Host Application calls `client.get_plugins()`, the resulting manifest will automatically contain the `strategy_metadata` (extracting the menu name) AND the `signature` object detailing the required arguments.

```json
{
  "context_menu_say_hello": {
    "is_keyword": true,
    "strategy_metadata": {
      "menu_name": "say_hello"
    },
    "signature": {
      "parameters": {
        "name": {"type": "str", "required": true}
      }
    }
  }
}
```
The Host UI can now iterate over this manifest, generate a "say_hello" button, and dynamically render a text input for the required `name` string!
