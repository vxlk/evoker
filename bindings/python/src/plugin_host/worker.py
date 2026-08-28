import sys
import logging
import os
import json
from xmlrpc.server import SimpleXMLRPCServer
from pathlib import Path
from plugin_host.manager import PluginManager, PrefixStrategy, ExactMatchStrategy

logger = logging.getLogger(__name__)

def parse_injected_packages(env_val: str):
    try:
        injected = json.loads(env_val)
        if isinstance(injected, list):
            for p in reversed(injected):
                if p not in sys.path:
                    sys.path.insert(0, p)
    except Exception as e:
        logger.error(f"Failed to parse EVOKER_INJECTED_PACKAGES: {e}")

if "EVOKER_INJECTED_PACKAGES" in os.environ:
    parse_injected_packages(os.environ["EVOKER_INJECTED_PACKAGES"])

def parse_strategies(env_val: str):
    strategies = None
    try:
        strategies_config = json.loads(env_val)
        if isinstance(strategies_config, list):
            strategies = []
            for config in strategies_config:
                if isinstance(config, dict):
                    if config.get("type") == "prefix":
                        strategies.append(PrefixStrategy(config["value"]))
                    elif config.get("type") == "exact":
                        strategies.append(ExactMatchStrategy(config["value"], config.get("args", [])))
    except Exception as e:
        logger.error(f"Failed to parse EVOKER_STRATEGIES: {e}")
    return strategies

class PluginWorkerRPC:
    def __init__(self, plugins_dir: Path):
        strategies = None
        if "EVOKER_STRATEGIES" in os.environ:
            strategies = parse_strategies(os.environ["EVOKER_STRATEGIES"])

        self.manager = PluginManager(strategies=strategies)
        self.plugins_dir = plugins_dir
        self.actions_manifest = {}

    def scan(self) -> dict:
        """Scans the plugin directory and returns a manifest of available actions."""
        if not self.plugins_dir.exists():
            return {}
            
        manifest = {}
        for item in self.plugins_dir.iterdir():
            if not item.is_dir():
                continue
                
            actions = self.manager.load_plugin(item)
            if actions:
                # Serialize to basic types for XML-RPC
                manifest[item.name] = {
                    name: {
                        "name": action.name,
                        "signature": action.signature_info,
                        "is_keyword": action.is_keyword,
                        "strategy_metadata": action.strategy_metadata
                    }
                    for name, action in actions.items()
                }
        
        self.actions_manifest = manifest
        return manifest

    def invoke(self, plugin_name: str, action_name: str, kwargs: dict) -> any:
        """Invokes a specific action on a specific plugin."""
        if plugin_name not in self.manager.plugins:
            raise ValueError(f"Plugin {plugin_name} not found or not loaded.")
            
        plugin = self.manager.plugins[plugin_name]
        if action_name not in plugin["actions"]:
            raise ValueError(f"Action {action_name} not found in plugin {plugin_name}.")
            
        action = plugin["actions"][action_name]
        
        try:
            return action.func(**kwargs)
        except Exception as e:
            # We must catch this so the RPC server doesn't crash from a bad plugin
            logger.error(f"Plugin {plugin_name} threw an exception during {action_name}: {e}")
            raise

def start_worker(plugins_dir: str, port: int = 0):
    server = SimpleXMLRPCServer(("localhost", port), allow_none=True)
    actual_port = server.server_address[1]
    
    # Print exactly this string so the parent process can scrape the port
    print(f"RPC_PORT:{actual_port}", flush=True)
    
    rpc_instance = PluginWorkerRPC(Path(plugins_dir))
    server.register_instance(rpc_instance)
    
    logger.info(f"Starting Plugin Worker on port {actual_port} for directory {plugins_dir}")
    server.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python worker.py <plugins_directory>")
        sys.exit(1)
    
    logging.basicConfig(level=logging.INFO)
    start_worker(sys.argv[1])
