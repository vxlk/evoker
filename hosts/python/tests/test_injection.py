import pytest
import shutil
from evoker_client.client import PluginClient

def test_custom_api_injection(temp_plugins_dir, tmp_path):
    # 1. Create a fake "host_api" directory that the host wants to inject
    host_api_dir = tmp_path / "my_custom_host_api"
    host_api_dir.mkdir()
    
    # Create the python module inside it
    api_module_dir = host_api_dir / "secret_api"
    api_module_dir.mkdir()
    (api_module_dir / "__init__.py").write_text("def get_secret():\n    return 'the_eagle_has_landed'\n")

    # 2. Create a plugin that depends on this injected API
    plugin_dir = temp_plugins_dir / "api_consumer_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text('{"name": "api_consumer_plugin"}', encoding="utf-8")
    
    init_content = """
from secret_api import get_secret

def run_consumer() -> str:
    # Use the API that the host injected!
    return get_secret()
"""
    (plugin_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # 3. Create the PluginClient with the injected package path
    host = PluginClient(temp_plugins_dir, injected_packages=[host_api_dir])
    
    try:
        host.start_worker()
        
        # 4. Verify it scanned successfully (it wouldn't scan if the import failed)
        manifest = host.get_plugins()
        assert "api_consumer_plugin" in manifest
        
        # 5. Invoke the action and verify the secret was returned
        result = host.run_action("api_consumer_plugin", "run_consumer", {})
        assert result == 'the_eagle_has_landed'
        
    finally:
        host.stop_worker()

def test_multiple_injected_packages(temp_plugins_dir, tmp_path):
    # 1. Create two separate fake host packages
    host_api_1 = tmp_path / "host_api_1"
    host_api_1.mkdir()
    (host_api_1 / "mod_a.py").write_text("def val_a(): return 'A'")

    host_api_2 = tmp_path / "host_api_2"
    host_api_2.mkdir()
    (host_api_2 / "mod_b.py").write_text("def val_b(): return 'B'")

    # 2. Create a plugin that imports both
    plugin_dir = temp_plugins_dir / "multi_consumer_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text('{"name": "multi_consumer_plugin"}', encoding="utf-8")
    
    init_content = """
import mod_a
import mod_b

def run_both() -> str:
    return mod_a.val_a() + mod_b.val_b()
"""
    (plugin_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # 3. Inject both!
    host = PluginClient(temp_plugins_dir, injected_packages=[host_api_1, host_api_2])
    
    try:
        host.start_worker()
        host.get_plugins()
        result = host.run_action("multi_consumer_plugin", "run_both", {})
        assert result == 'AB'
    finally:
        host.stop_worker()
