import sys
import time
from pathlib import Path

# Ensure the Behemoth src is in the python path
behemoth_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(behemoth_src))

from plugin_host.client import PluginClient
import xmlrpc.client

def print_separator(title: str):
    print(f"\n{'='*50}")
    print(f"--- {title} ---")
    print(f"{'='*50}\n")

def main():
    print_separator("Welcome to the Behemoth Architecture Demo")
    print("This lightweight host application will orchestrate multiple plugins.")
    print("Each plugin runs in an isolated process via XML-RPC.\n")
    
    plugins_dir = Path(__file__).parent / "plugins"
    print(f"[*] Booting PluginClient pointing to: {plugins_dir}")
    
    # 1. Boot Client
    client = PluginClient(plugins_dir)
    print("[*] Spawning isolated PluginWorker process...")
    client.start_worker()
    time.sleep(1) # Give it a second to boot up
    
    try:
        # 2. Scan Plugins
        input("\n[Press Enter to scan the plugins directory...]")
        manifest = client.get_plugins()
        print(f"\n[+] Discovered {len(manifest)} plugins:")
        for plugin_name, actions in manifest.items():
            print(f"  -> {plugin_name}")
            for action_name in actions.keys():
                print(f"       * Action: {action_name}")
                
        # 3. Data Ingestion (PyArrow IPC Demo)
        input("\n[Press Enter to trigger Data Ingestion (Zero-copy PyArrow)...]")
        print_separator("Executing: data_ingestor_plugin")
        mmap_path = client.run_action("data_ingestor_plugin", "ingest_dataset", {"num_rows": 500000})
        print(f"\n[Host] Received lightweight handle to massive dataset: {mmap_path}")
        
        # 4. NLP Analysis
        input("\n[Press Enter to trigger NLP Analysis...]")
        print_separator("Executing: nlp_analyzer_plugin")
        print(f"[Host] Passing handle {mmap_path} over XML-RPC boundary...")
        results = client.run_action("nlp_analyzer_plugin", "analyze_sentiment", {"mmap_path": mmap_path})
        print(f"\n[Host] Received results: {results}")
        
        # 5. Telemetry
        input("\n[Press Enter to push results to Telemetry...]")
        print_separator("Executing: telemetry_exporter_plugin")
        client.run_action("telemetry_exporter_plugin", "export_metrics", {"metrics": results})
        print("\n[Host] Dashboard updated!")
        
        # 6. Fault Tolerance Demo
        input("\n[Press Enter to test Fault Tolerance with an unstable plugin...]")
        print_separator("Executing: vision_processor_plugin (UNSTABLE)")
        try:
            client.run_action("vision_processor_plugin", "process_images", {})
        except xmlrpc.client.Fault as e:
            print(f"\n[Host] CAUGHT FATAL EXCEPTION: {e.faultString}")
            print("[Host] The host application is completely fine! We isolated the segmentation fault.")
            
        # 7. Prove worker is still alive
        input("\n[Press Enter to verify the worker can still process data...]")
        print("[Host] Asking the worker to ingest a small dataset just to prove it's alive...")
        path2 = client.run_action("data_ingestor_plugin", "ingest_dataset", {"num_rows": 5})
        print(f"[Host] Success! Worker returned: {path2}")
        
    finally:
        print("\n[*] Shutting down PluginWorker...")
        client.stop_worker()
        print("[*] Behemoth Demo Complete.")

if __name__ == "__main__":
    main()
