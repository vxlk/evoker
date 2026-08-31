import sys
import time
from pathlib import Path
import pyarrow as pa

is_frozen = getattr(sys, "frozen", False)
if is_frozen:
    base_dir = Path(sys._MEIPASS)
    host_api_dir = base_dir / "injected" / "host_api"
else:
    base_dir = Path(__file__).parent
    host_api_dir = base_dir / "host_api"

# Ensure the Evoker src is in the python path (only when not frozen)
if not is_frozen:
    evoker_src = base_dir.parent / "src"
    sys.path.insert(0, str(evoker_src))

# Add host_api to python path so host can use it natively
if str(host_api_dir.parent) not in sys.path:
    sys.path.insert(0, str(host_api_dir.parent))

from plugin_host.client import PluginClient
from host_api.arrow_ipc import write_table_to_mmap, read_table_from_mmap, cleanup_mmap

def print_separator(title: str):
    print(f"\n{'='*50}")
    print(f"--- {title} ---")
    print(f"{'='*50}\n")

def main():
    print_separator("Welcome to the Evoker Hello World Demo")
    
    # 1. Boot Client with Custom Strategies
    if is_frozen:
        plugins_dir = Path(sys.executable).parent / "plugins"
        if not plugins_dir.exists():
            import shutil
            shutil.copytree(base_dir / "plugins", plugins_dir)
    else:
        plugins_dir = base_dir / "plugins"
        
    print(f"[*] Booting PluginClient pointing to: {plugins_dir}")
    
    # 1. Boot Client with Custom Strategies
    client = PluginClient(
        plugins_dir,
        strategies=[
            {"type": "prefix", "value": "context_menu_"}
        ],
        injected_packages=[host_api_dir.parent]
    )
    print("[*] Spawning isolated PluginWorker process...")
    client.start_worker()
    time.sleep(1) # Give it a second to boot up
    
    try:
        manifest = client.get_plugins()
        plugin_name = "hello_world_plugin"
        
        if plugin_name not in manifest:
            print(f"[!] Could not find {plugin_name} in manifest!")
            return
            
        # Demo 1: Exact Match (on_start)
        print_separator("Demo 1: Exact Match Strategy (on_start)")
        client.run_action(plugin_name, "on_start", {"app_context": {}})
        
        # Demo 2: Prefix Match
        print_separator("Demo 2: Prefix Match Strategy")
        # In a real UI, we would read the manifest to find buttons. Let's do that!
        for action_name, action_details in manifest[plugin_name].items():
            metadata = action_details.get("strategy_metadata")
            if metadata and "menu_name" in metadata:
                menu_name = metadata["menu_name"]
                print(f"[Host] Found context menu action: '{menu_name}'. Invoking...")
                client.run_action(plugin_name, action_name, {})
        
        # Demo 3: Plugin -> Host (Arrow IPC)
        print_separator("Demo 3: Plugin -> Host (Arrow IPC)")
        print("[Host] Asking plugin to send us a PyArrow table...")
        mmap_path = client.run_action(plugin_name, "send_arrow_to_host", {})
        print(f"[Host] Received memory map handle: {mmap_path}")
        table = read_table_from_mmap(mmap_path)
        message = table.column("message")[0].as_py()
        print(f"[Host] Successfully read message from plugin: {message}")
        cleanup_mmap(mmap_path)
        
        # Demo 4: Host -> Plugin (Arrow IPC)
        print_separator("Demo 4: Host -> Plugin (Arrow IPC)")
        print("[Host] Creating PyArrow table to send to plugin...")
        table = pa.Table.from_arrays([pa.array(["Hello World from Host via Arrow!"])], names=["message"])
        mmap_path = write_table_to_mmap(table)
        print(f"[Host] Passing memory map handle {mmap_path} over XML-RPC...")
        client.run_action(plugin_name, "receive_arrow_from_host", {"mmap_path": mmap_path})
        
    finally:
        print("\n[*] Shutting down PluginWorker...")
        client.stop_worker()
        print("[*] Evoker Demo Complete.")

if __name__ == "__main__":
    main()
