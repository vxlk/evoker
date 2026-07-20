import pyarrow as pa
from plugin_host.arrow_ipc import write_table_to_mmap, read_table_from_mmap, cleanup_mmap

# 1. Exact Match Strategy
def on_start(app_context):
    print("[Plugin] Hello World from on_start! (Exact Match)")

# 2. Prefix Match Strategy
def context_menu_say_hello():
    print("[Plugin] Hello World from a Context Menu! (Prefix Match)")

# 3. Arrow IPC (Plugin -> Host)
def send_arrow_to_host() -> str:
    print("[Plugin] Generating PyArrow Table with 'Hello World'...")
    table = pa.Table.from_arrays([pa.array(["Hello World from Plugin via Arrow!"])], names=["message"])
    path = write_table_to_mmap(table)
    print(f"[Plugin] Sent table to memory map: {path}")
    return path

# 4. Arrow IPC (Host -> Plugin)
def receive_arrow_from_host(mmap_path: str):
    print(f"[Plugin] Reading PyArrow Table from memory map: {mmap_path}...")
    table = read_table_from_mmap(mmap_path)
    message = table.column("message")[0].as_py()
    print(f"[Plugin] Received message from host: {message}")
    cleanup_mmap(mmap_path)
