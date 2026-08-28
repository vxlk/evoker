---
sidebar_position: 6
---

# Native Language Bindings

Evoker was built from the ground up to empower native desktop applications to seamlessly leverage Python's massive Data Science and AI ecosystem without sacrificing the stability and memory safety of compiled languages.

We provide official, fully-featured host clients with 1:1 API parity across:
* **Python**
* **Rust**
* **C++**
* **C**

## Transparent Runtime Bootstrapping

A major pain point for integrating Python into native applications is the burden of requiring end-users to have a global Python installation.

Evoker's **Rust**, **C++**, and **C** clients solve this natively. By passing an empty string `""` or `None` as the Python executable path when starting the worker, the Evoker client will seamlessly:
1. Detect the host OS and CPU architecture.
2. Download a portable, statically compiled version of Python (from `astral-sh/python-build-standalone`).
3. Extract it locally into `~/.evoker/python`.
4. Install the Evoker plugin dependencies directly into the standalone interpreter.
5. Boot the worker using the sandboxed environment.

Your users never need to know Python is powering the plugins under the hood!

---

## 🦀 Rust

The Rust client provides an idiomatic interface leveraging the `xmlrpc` crate.

### Installation

Add `evoker-host` to your `Cargo.toml`:

```toml
[dependencies]
evoker-host = "0.1.0"
xmlrpc = "0.15.0"
```

### Example Usage

```rust
use evoker_host::PluginClient;
use std::collections::BTreeMap;
use xmlrpc::Value;

fn main() {
    let plugins_dir = "plugins/";
    
    // Create the client
    let mut client = PluginClient::new(plugins_dir, None, None);
    
    // Boot the python worker. Passing `None` triggers Automatic Bootstrapping!
    client.start_worker(None, "plugin_host.worker").expect("Failed to start worker");
    
    // Scan for available plugins
    let manifest = client.scan().expect("Scan failed");
    println!("Available plugins: {:?}", manifest);
    
    // Invoke a specific plugin action
    let mut kwargs = BTreeMap::new();
    kwargs.insert("name".to_string(), Value::String("Rustacean".to_string()));
    
    let result = client.invoke("my_plugin", "hello_world", kwargs).expect("Invoke failed");
    println!("Plugin Returned: {:?}", result);
}
```

---

## 🚀 C++

The C++ client uses standard C++17 types and seamlessly converts XML-RPC responses into modern `nlohmann::json` objects.

### Installation
Evoker uses CMake. Simply use `FetchContent` or `add_subdirectory()` to link `evoker_host` into your target.

### Example Usage

```cpp
#include <iostream>
#include "evoker_client.hpp"

int main() {
    evoker::PluginClient client("plugins/");
    
    // Boot the worker. Passing "" triggers Automatic Bootstrapping!
    if (!client.start_worker("", "plugin_host.worker")) {
        std::cerr << "Failed to boot plugin worker!" << std::endl;
        return 1;
    }
    
    // Scan for available plugins
    nlohmann::json manifest = client.scan();
    std::cout << "Available plugins: " << manifest.dump(4) << std::endl;
    
    // Invoke a plugin action
    nlohmann::json kwargs = {{"name", "C++ Developer"}};
    nlohmann::json result = client.invoke("my_plugin", "hello_world", kwargs);
    
    std::cout << "Plugin Returned: " << result.get<std::string>() << std::endl;
    
    return 0;
}
```

---

## ⚙️ C 

For legacy applications or FFI interfaces into other languages (like Go or C#), we provide a pure C ABI wrapper.

### Installation
Link against the `evoker_client_c` CMake target.

### Example Usage

```c
#include <stdio.h>
#include <stdlib.h>
#include "evoker_client_c.h"

int main() {
    // Create the client
    evoker_client_t* client = evoker_client_create("plugins/", NULL, NULL);
    if (!client) return 1;
    
    // Boot the worker. Passing "" triggers Automatic Bootstrapping!
    if (!evoker_client_start_worker(client, "", "plugin_host.worker")) {
        printf("Failed to boot plugin worker!\n");
        return 1;
    }
    
    // Scan for plugins. The client handles memory allocation.
    char* manifest_json = evoker_client_scan(client);
    printf("Plugins: %s\n", manifest_json);
    evoker_client_free_string(manifest_json);
    
    // Invoke a plugin action by passing JSON strings
    char* result_json = evoker_client_invoke(client, "my_plugin", "hello_world", "{\"name\": \"C Programmer\"}");
    printf("Result: %s\n", result_json);
    evoker_client_free_string(result_json);
    
    // Cleanup
    evoker_client_destroy(client);
    return 0;
}
```
