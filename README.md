# Behemoth

![Behemoth Mascot](assets/mascot.jpg)

**Behemoth** is a hyper-modular, multi-headed plugin architecture designed for infinite scale. Built for host applications that require processing massive datasets or orchestrating complex AI workflows, Behemoth isolates plugins in separate processes while maintaining zero-copy data transfer speeds.

## Core Features
*   **Multi-Headed Isolation**: Plugins run in their own dedicated Python environments (via XML-RPC). If a plugin crashes, your Host Application stays alive.
*   **Zero-Copy PyArrow IPC**: Share colossal DataFrames and Tensors across the process boundary instantly. Behemoth serializes to memory-mapped OS files, meaning gigabytes of data never touch Python's memory buffer until read.
*   **Auto-Installing Dependencies**: Drop a `requirements.txt` or an offline `wheels/` folder into a plugin, and Behemoth handles the `pip install` transparently upon loading.
*   **Deep Introspection**: The `PluginManager` dynamically reads type hints and signature defaults, ensuring your Host knows exactly how to invoke the plugin.

---

## Example Host Integration: AI Data Orchestrator

To demonstrate Behemoth's infinite scalability, imagine an AI Data Orchestrator host. This host coordinates a pipeline of massive datasets, moving them through various stages of analysis. Here are examples of plugins that easily snap into the Behemoth architecture:

### 1. `data_ingestor_plugin`
*   **Role**: Reads terabytes of unstructured CSV/Parquet files from cloud storage and converts them into PyArrow Tables.
*   **Behemoth Advantage**: The massive PyArrow Tables are written to a memory-mapped file, and only the lightweight *file handle* is passed back to the Host via XML-RPC.

### 2. `nlp_analyzer_plugin`
*   **Role**: Receives the memory-mapped PyArrow data and runs local HuggingFace sentiment analysis across millions of rows.
*   **Behemoth Advantage**: Ships with an offline `wheels/` folder containing the massive PyTorch/Transformers dependencies. Behemoth auto-installs them without requiring an internet connection or polluting the Host's environment.

### 3. `vision_processor_plugin`
*   **Role**: A highly experimental, unstable plugin that processes image batches using a bleeding-edge C++ wrapper.
*   **Behemoth Advantage**: If a segmentation fault occurs in the C++ library, only the isolated `PluginWorkerRPC` process dies. The Host seamlessly catches the exception over XML-RPC, logs the error, and spins up a fresh worker without downtime.

### 4. `telemetry_exporter_plugin`
*   **Role**: Aggregates the analyzed data and pushes metrics to a Grafana/Prometheus dashboard.
*   **Behemoth Advantage**: Utilizes a highly-specific API client that has conflicting version requirements with the `nlp_analyzer`. Behemoth's process isolation means "Dependency Hell" is entirely bypassed.
