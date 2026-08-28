# Evoker Hello World Demo

This directory contains a foundational "Hello World" application that demonstrates the four core capabilities of the Evoker plugin architecture.

## Running the Demo

From the root of the project, execute:
```bash
python dev.py run-example
```

## What it Demonstrates

The `host.py` script boots up a `PluginClient` and scans the `plugins/hello_world_plugin`. It then orchestrates four demos:

1. **Exact Match Strategy**: Demonstrates invoking a lifecycle hook (`on_start`) based on an exact function name match.
2. **Prefix Match Strategy**: Demonstrates injecting a custom matching strategy (`context_menu_`) to dynamically discover functions and extract metadata from their names.
3. **Arrow IPC (Plugin -> Host)**: Demonstrates the plugin serializing a PyArrow string array into a zero-copy memory-mapped file, and the host reading it instantly.
4. **Arrow IPC (Host -> Plugin)**: Demonstrates the host generating a PyArrow string array and sending the memory-map handle over the XML-RPC boundary to the plugin for deserialization.
