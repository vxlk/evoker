import importlib.util
import importlib.metadata
import inspect
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List
from abc import ABC, abstractmethod

from evoker.installer import install_plugin_deps, DependencyInstallError

logger = logging.getLogger(__name__)

class PluginStrategy(ABC):
    @abstractmethod
    def match(self, name: str, sig_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

class ExactMatchStrategy(PluginStrategy):
    def __init__(self, exact_name: str, expected_args: List[str]):
        self.exact_name = exact_name
        self.expected_args = expected_args

    def match(self, name: str, sig_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if name == self.exact_name:
            actual_args = list(sig_info["parameters"].keys())
            if actual_args != self.expected_args:
                logger.warning(f"Keyword action '{name}' signature mismatch. Expected {self.expected_args}, got {actual_args}. Ignoring.")
                raise ValueError("Signature mismatch")
            return {}
        return None

class PrefixStrategy(PluginStrategy):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def match(self, name: str, sig_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if name.startswith(self.prefix):
            return {"menu_name": name[len(self.prefix):]}
        return None

@dataclass
class PluginAction:
    name: str
    func: Callable
    signature_info: Dict[str, Any]  # Serializable signature info
    is_keyword: bool
    strategy_metadata: Optional[Dict[str, Any]] = None

class PluginManager:
    def __init__(self, strategies: Optional[List[PluginStrategy]] = None):
        self.plugins = {}
        if "evoker_plugins" not in sys.modules:
            import types
            sys.modules["evoker_plugins"] = types.ModuleType("evoker_plugins")
        self.strategies: List[PluginStrategy]
        if strategies is None:
            self.strategies = [ExactMatchStrategy("on_start", ["app_context"])]
        else:
            self.strategies = strategies

    def load_plugin(self, plugin_dir: Path) -> Optional[Dict[str, PluginAction]]:
        manifest_path = plugin_dir / "manifest.json"
        init_path = plugin_dir / "__init__.py"

        if not manifest_path.exists():
            logger.warning(f"Skipping {plugin_dir}: Missing manifest.json")
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8-sig") as f:
                manifest = json.load(f)
            if not isinstance(manifest, dict):
                raise ValueError("Manifest must be a JSON object")
            if manifest.get("name") != plugin_dir.name:
                logger.warning(f"Skipping {plugin_dir}: Manifest name '{manifest.get('name')}' does not match directory name.")
                return None
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

        # Namespace the module to avoid collisions
        safe_name = plugin_dir.name.replace(".", "_")
        module_name = f"evoker_plugins.{safe_name}"
        spec = importlib.util.spec_from_file_location(module_name, init_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Skipping {plugin_dir}: Failed to create module spec")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        path_insertions = []
        # Inject to path for local imports within the plugin
        sys.path.insert(0, str(plugin_dir))
        path_insertions.append(str(plugin_dir))

        # Inject the newly created .venv site-packages into sys.path
        # so the plugin can import the dependencies just installed by installer.py.
        venv_dir = plugin_dir / ".venv"
        if venv_dir.exists():
            import os
            if os.name == "nt":
                site_packages = venv_dir / "Lib" / "site-packages"
            else:
                site_packages = None
                lib_dir = venv_dir / "lib"
                if lib_dir.exists():
                    for d in lib_dir.iterdir():
                        if d.is_dir() and d.name.startswith("python"):
                            site_packages = d / "site-packages"
                            break

            if site_packages and site_packages.exists():
                if str(site_packages) not in sys.path:
                    # Detect dependency collisions with previously loaded plugins
                    for item in site_packages.iterdir():
                        if item.name.startswith('.') or item.name.startswith('__') or item.name.endswith('.dist-info') or item.name.endswith('.egg-info'):
                            continue
                        pkg_name = item.stem if item.is_file() else item.name
                        if pkg_name in sys.modules:
                            mod = sys.modules[pkg_name]
                            if hasattr(mod, '__file__') and mod.__file__ and str(site_packages) not in mod.__file__:
                                loaded_version = None
                                try:
                                    loaded_version = importlib.metadata.version(pkg_name)
                                except Exception:
                                    pass
                                version_str = f" (version {loaded_version})" if loaded_version else ""
                                logger.error(f"Plugin {plugin_dir.name} dependency collision: '{pkg_name}'{version_str} already loaded from {mod.__file__}")
                                sys.modules.pop(module_name, None)
                                return None

                    sys.path.insert(1, str(site_packages))
                    path_insertions.append(str(site_packages))

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_dir.name}: {e}")
            sys.modules.pop(module_name, None)
            return None
        finally:
            for p in path_insertions:
                if p in sys.path:
                    sys.path.remove(p)

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
            if inspect.iscoroutinefunction(func):
                logger.warning(f"Action '{name}' in plugin '{module.__name__}' was skipped because async functions are not supported.")
                continue
            original_func = inspect.unwrap(func)
            if getattr(original_func, '__module__', None) != module.__name__:
                logger.debug(f"Action '{name}' in plugin '{module.__name__}' was filtered out because it belongs to module '{getattr(original_func, '__module__', None)}'")
                continue

            sig = inspect.signature(func)

            has_positional_only = False
            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    has_positional_only = True
                    break

            if has_positional_only:
                logger.warning(f"Action '{name}' in plugin '{module.__name__}' was skipped because positional-only parameters are not supported.")
                continue

            # Serialize signature info
            sig_info = {"parameters": {}}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                type_name = "unannotated"
                if param.annotation is not inspect.Parameter.empty:
                    type_name = getattr(param.annotation, "__name__", str(param.annotation))
                else:
                    logger.warning(f"Argument '{param_name}' in action '{name}' lacks type hint. Defaulting to unannotated.")

                sig_info["parameters"][param_name] = {
                    "type": type_name,
                    "required": param.default is inspect.Parameter.empty
                }

            is_keyword = False
            strategy_metadata = None
            ignore_action = False

            for strategy in self.strategies:
                try:
                    match_result = strategy.match(name, sig_info)
                    if match_result is not None:
                        is_keyword = True
                        strategy_metadata = match_result
                        break
                except ValueError:
                    ignore_action = True
                    break

            if ignore_action:
                continue

            actions[name] = PluginAction(name, func, sig_info, is_keyword, strategy_metadata)

        return actions
