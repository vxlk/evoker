import importlib.util
import inspect
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, Optional

from plugin_host.installer import install_plugin_deps, DependencyInstallError

logger = logging.getLogger(__name__)

@dataclass
class PluginAction:
    name: str
    func: Callable
    signature_info: Dict[str, Any]  # Serializable signature info
    is_keyword: bool

class PluginManager:
    def __init__(self):
        self.plugins = {}
        self.keyword_signatures = {
            "on_start": ["app_context"]
        }

    def load_plugin(self, plugin_dir: Path) -> Optional[Dict[str, PluginAction]]:
        manifest_path = plugin_dir / "manifest.json"
        init_path = plugin_dir / "__init__.py"
        
        if not manifest_path.exists():
            logger.warning(f"Skipping {plugin_dir}: Missing manifest.json")
            return None
            
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if not isinstance(manifest, dict):
                raise ValueError("Manifest must be a JSON object")
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Skipping {plugin_dir}: Invalid manifest.json")
            return None

        if not init_path.exists():
            logger.warning(f"Skipping {plugin_dir}: Missing __init__.py")
            return None

        # Auto-install dependencies
        try:
            install_plugin_deps(plugin_dir)
        except DependencyInstallError:
            logger.warning(f"Skipping {plugin_dir}: Dependency installation failed.")
            return None

        # Standard dynamic load
        spec = importlib.util.spec_from_file_location(plugin_dir.name, init_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Skipping {plugin_dir}: Failed to create module spec")
            return None

        module = importlib.util.module_from_spec(spec)
        
        # Inject to path for local imports within the plugin
        sys.path.insert(0, str(plugin_dir))
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_dir.name}: {e}")
            return None
        finally:
            sys.path.pop(0)

        actions = self._introspect_module(module)
        self.plugins[plugin_dir.name] = {
            "manifest": manifest,
            "actions": actions,
            "module": module
        }
        return actions

    def _introspect_module(self, module) -> Dict[str, PluginAction]:
        actions = {}
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue

            sig = inspect.signature(func)
            
            # Serialize signature info
            sig_info = {"parameters": {}}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                type_name = "str" # Default fallback
                if param.annotation != inspect.Parameter.empty:
                    type_name = getattr(param.annotation, "__name__", str(param.annotation))
                else:
                    logger.warning(f"Argument '{param_name}' in action '{name}' lacks type hint. Defaulting to str.")
                
                sig_info["parameters"][param_name] = {
                    "type": type_name,
                    "required": param.default == inspect.Parameter.empty
                }

            is_keyword = name in self.keyword_signatures
            
            if is_keyword:
                expected_args = self.keyword_signatures[name]
                actual_args = list(sig_info["parameters"].keys())
                if actual_args != expected_args:
                    logger.warning(f"Keyword action '{name}' signature mismatch. Expected {expected_args}, got {actual_args}. Ignoring.")
                    continue
                    
            actions[name] = PluginAction(name, func, sig_info, is_keyword)
            
        return actions
