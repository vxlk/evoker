import tempfile
from pathlib import Path
from plugin_host.client import PluginClient

def test_quick_start_snippets():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "my_app"
        plugins_dir = root / "plugins"
        plugin_dir = plugins_dir / "hello_plugin"
        plugin_dir.mkdir(parents=True)
        
        (plugin_dir / "manifest.json").write_text("""{
          "name": "hello_plugin",
          "version": "1.0.0",
          "description": "My first plugin"
        }""")
        
        (plugin_dir / "__init__.py").write_text("""def greet(name: str) -> str:
    return f"Hello, {name}!"
""")
        
        client = PluginClient(plugins_dir)
        client.start_worker()
        
        try:
            manifest = client.get_plugins()
            assert "hello_plugin" in manifest
            assert "greet" in manifest["hello_plugin"]
            
            result = client.run_action("hello_plugin", "greet", {"name": "World"})
            assert result == "Hello, World!"
        finally:
            client.stop_worker()
