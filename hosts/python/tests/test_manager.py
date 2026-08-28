import json
import logging
from pathlib import Path
import pytest
from plugin_host.manager import PluginManager, PrefixStrategy

def create_plugin(base_dir, name, manifest_content=None, init_content=None):
    plugin_dir = base_dir / name
    plugin_dir.mkdir(parents=True)
    if manifest_content is not None:
        (plugin_dir / "manifest.json").write_text(manifest_content)
    if init_content is not None:
        (plugin_dir / "__init__.py").write_text(init_content)
    return plugin_dir

def test_missing_manifest(temp_plugins_dir, manager, caplog):
    plugin_dir = create_plugin(temp_plugins_dir, "no_manifest", init_content="def hello(): pass")
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
    assert "Missing manifest.json" in caplog.text

def test_invalid_manifest(temp_plugins_dir, manager, caplog):
    plugin_dir = create_plugin(temp_plugins_dir, "bad_manifest", manifest_content="{bad json", init_content="def hello(): pass")
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
    assert "Invalid manifest.json" in caplog.text

def test_missing_init(temp_plugins_dir, manager, caplog):
    plugin_dir = create_plugin(temp_plugins_dir, "no_init", manifest_content='{"name": "test"}')
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
    assert "Missing __init__.py" in caplog.text

def test_syntax_error(temp_plugins_dir, manager, caplog):
    plugin_dir = create_plugin(temp_plugins_dir, "syntax_err", manifest_content='{"name": "test"}', init_content="def hello() pass") # Missing colon
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
    assert "Error executing plugin syntax_err" in caplog.text

def test_valid_plugin(temp_plugins_dir, manager):
    init_content = """
def extension_action(name: str, count: int = 5):
    pass

def _private_action():
    pass
    
def on_start(app_context):
    pass
"""
    plugin_dir = create_plugin(temp_plugins_dir, "valid_plugin", manifest_content='{"name": "test"}', init_content=init_content)
    actions = manager.load_plugin(plugin_dir)
    
    assert actions is not None
    assert "extension_action" in actions
    assert "on_start" in actions
    assert "_private_action" not in actions # Should be filtered out
    
    # Check signature serialization
    ext_action = actions["extension_action"]
    assert ext_action.signature_info["parameters"]["name"]["type"] == "str"
    assert ext_action.signature_info["parameters"]["name"]["required"] is True
    assert ext_action.signature_info["parameters"]["count"]["type"] == "int"
    assert ext_action.signature_info["parameters"]["count"]["required"] is False
    assert ext_action.is_keyword is False
    
    # Check keyword action
    on_start_action = actions["on_start"]
    assert on_start_action.is_keyword is True

def test_keyword_signature_mismatch(temp_plugins_dir, manager, caplog):
    init_content = """
def on_start(wrong_arg: str): # Should be app_context
    pass
"""
    plugin_dir = create_plugin(temp_plugins_dir, "bad_keyword", manifest_content='{"name": "test"}', init_content=init_content)
    actions = manager.load_plugin(plugin_dir)
    
    assert actions is not None
    assert "on_start" not in actions # Should be ignored due to signature mismatch
    assert "Keyword action 'on_start' signature mismatch" in caplog.text

def test_untyped_argument_warning(temp_plugins_dir, manager, caplog):
    init_content = """
def untyped_action(some_arg):
    pass
"""
    plugin_dir = create_plugin(temp_plugins_dir, "untyped_plugin", manifest_content='{"name": "test"}', init_content=init_content)
    with caplog.at_level(logging.WARNING):
        actions = manager.load_plugin(plugin_dir)
        
    assert actions is not None
    assert "untyped_action" in actions
    assert "lacks type hint. Defaulting to str." in caplog.text
    assert actions["untyped_action"].signature_info["parameters"]["some_arg"]["type"] == "str"

def test_prefix_strategy_matching(temp_plugins_dir):
    manager = PluginManager(strategies=[PrefixStrategy("context_menu_action_")])
    init_content = """
def context_menu_action_hello(text: str):
    pass
    
def context_menu_action_world():
    pass
    
def normal_action():
    pass
"""
    plugin_dir = create_plugin(temp_plugins_dir, "strategy_plugin", manifest_content='{"name": "test"}', init_content=init_content)
    actions = manager.load_plugin(plugin_dir)
    
    assert actions is not None
    assert "context_menu_action_hello" in actions
    hello_action = actions["context_menu_action_hello"]
    assert hello_action.is_keyword is True
    assert hello_action.strategy_metadata["menu_name"] == "hello"
    
    assert "context_menu_action_world" in actions
    world_action = actions["context_menu_action_world"]
    assert world_action.is_keyword is True
    assert world_action.strategy_metadata["menu_name"] == "world"
    
    assert "normal_action" in actions
    normal = actions["normal_action"]
    assert normal.is_keyword is False
    assert normal.strategy_metadata is None
