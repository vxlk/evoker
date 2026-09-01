import sys
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)
import logging
import os
import json
import socketserver
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from pathlib import Path
from typing import Any, List
from evoker.manager import PluginManager, PrefixStrategy, ExactMatchStrategy, PluginStrategy

_AUTH_TOKEN = os.environ.pop("EVOKER_AUTH_TOKEN", None)

class AuthXMLRPCRequestHandler(SimpleXMLRPCRequestHandler):
    def parse_request(self):
        if super().parse_request():
            if not _AUTH_TOKEN:
                self.send_error(500, "Worker improperly configured (missing auth token)")
                return False
            auth_token = self.headers.get("X-Evoker-Auth")
            if auth_token != _AUTH_TOKEN:
                self.send_error(401, "Unauthorized")
                return False
            return True
        return False

class ThreadingXMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    pass

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
    strategies: List[PluginStrategy] = None
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
        self.plugins_mtimes = {}

    def _get_plugin_mtime(self, plugin_dir: Path) -> float:
        mtime = plugin_dir.stat().st_mtime
        for root, dirs, files in os.walk(plugin_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('wheels', '__pycache__')]
            for f in files:
                if f.endswith('.py'):
                    mtime = max(mtime, (Path(root) / f).stat().st_mtime)
        manifest = plugin_dir / "manifest.json"
        if manifest.exists():
            mtime = max(mtime, manifest.stat().st_mtime)
        return mtime

    def reload_plugin(self, plugin_name: str) -> bool:
        plugin_dir = self.plugins_dir / plugin_name
        if plugin_dir.exists() and plugin_dir.is_dir():
            actions = self.manager.load_plugin(plugin_dir)
            if actions is not None:
                self.plugins_mtimes[plugin_name] = self._get_plugin_mtime(plugin_dir)
                return True
        return False

    def scan(self) -> dict:
        """Scans the plugin directory and returns a manifest of available actions."""
        if not self.plugins_dir.exists():
            return {}

        manifest = {}
        for item in self.plugins_dir.iterdir():
            if not item.is_dir():
                continue

            mtime = self._get_plugin_mtime(item)
            if item.name in self.manager.plugins and self.plugins_mtimes.get(item.name) == mtime:
                actions = self.manager.plugins[item.name]["actions"]
            else:
                actions = self.manager.load_plugin(item)
                self.plugins_mtimes[item.name] = mtime

            if actions is not None:
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

    def invoke(self, plugin_name: str, action_name: str, kwargs: dict) -> Any:
        """Invokes a specific action on a specific plugin."""
        if plugin_name not in self.manager.plugins:
            raise ValueError(f"Plugin {plugin_name} not found or not loaded.")

        plugin = self.manager.plugins[plugin_name]
        if action_name not in plugin["actions"]:
            raise ValueError(f"Action {action_name} not found in plugin {plugin_name}.")

        action = plugin["actions"][action_name]

        # Coerce kwargs based on signature_info
        for k, param_info in action.signature_info["parameters"].items():
            if k in kwargs:
                t = param_info["type"]
                v = kwargs[k]
                try:
                    if t == "int" and not isinstance(v, int):
                        kwargs[k] = int(v)
                    elif t == "float" and not isinstance(v, float):
                        kwargs[k] = float(v)
                    elif t == "str" and not isinstance(v, str):
                        kwargs[k] = str(v)
                    elif t == "bool" and not isinstance(v, bool):
                        if isinstance(v, str):
                            kwargs[k] = v.lower() in ("true", "1", "yes")
                        else:
                            kwargs[k] = bool(v)
                except (ValueError, TypeError):
                    raise ValueError(f"Failed to coerce argument '{k}' to type '{t}': {v}")

        try:
            return action.func(**kwargs)
        except Exception as e:
            # We must catch this so the RPC server doesn't crash from a bad plugin
            logger.error(f"Plugin {plugin_name} threw an exception during {action_name}: {e}")
            raise

def start_worker(plugins_dir: str, port: int = 0):
    server = ThreadingXMLRPCServer(("127.0.0.1", port), requestHandler=AuthXMLRPCRequestHandler, allow_none=True)
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
