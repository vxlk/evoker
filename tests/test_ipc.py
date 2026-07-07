import pytest
from plugin_host.client import PluginClient
import xmlrpc.client

def test_worker_ipc(temp_plugins_dir):
    # Create a simple valid plugin
    plugin_dir = temp_plugins_dir / "math_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text('{"name": "math"}', encoding="utf-8")
    
    init_content = """
def add_numbers(a: int, b: int) -> int:
    return a + b
    
def get_message() -> str:
    return "Hello from worker!"
    
def crash_me():
    raise RuntimeError("Intentional crash")
"""
    (plugin_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    
    host = PluginClient(temp_plugins_dir)
    try:
        host.start_worker()
        
        # Test 1: Scan
        manifest = host.get_plugins()
        assert "math_plugin" in manifest
        assert "add_numbers" in manifest["math_plugin"]
        assert "get_message" in manifest["math_plugin"]
        
        # Test 2: Invoke with args
        result = host.run_action("math_plugin", "add_numbers", {"a": 5, "b": 10})
        assert result == 15
        
        # Test 3: Invoke without args
        msg = host.run_action("math_plugin", "get_message", {})
        assert msg == "Hello from worker!"
        
        # Test 4: Exception boundary
        with pytest.raises(xmlrpc.client.Fault) as exc_info:
            host.run_action("math_plugin", "crash_me", {})
            
        assert "Intentional crash" in exc_info.value.faultString
        
        # Verify the worker is STILL ALIVE after an exception!
        result2 = host.run_action("math_plugin", "add_numbers", {"a": 1, "b": 1})
        assert result2 == 2
        
    finally:
        host.stop_worker()
