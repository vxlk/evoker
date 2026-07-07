import pytest
import types
from hypothesis import given, settings, HealthCheck, strategies as st
from plugin_host.manager import PluginManager

def make_dummy_module(code: str):
    mod = types.ModuleType("dummy_plugin")
    exec(code, mod.__dict__)
    return mod

@st.composite
def generate_valid_signature(draw):
    """Generates a valid python function signature string."""
    num_positional = draw(st.integers(min_value=0, max_value=5))
    num_defaults = draw(st.integers(min_value=0, max_value=5))
    has_varargs = draw(st.booleans())
    has_kwargs = draw(st.booleans())
    has_type_hints = draw(st.booleans())
    
    params = []
    for i in range(num_positional):
        hint = ": int" if has_type_hints and draw(st.booleans()) else ""
        params.append(f"p{i}{hint}")
        
    for i in range(num_defaults):
        hint = ": str" if has_type_hints and draw(st.booleans()) else ""
        params.append(f"d{i}{hint} = 'default'")
        
    if has_varargs:
        params.append("*args")
        
    if has_kwargs:
        params.append("**kwargs")
        
    return ", ".join(params)

@given(generate_valid_signature())
def test_fuzz_introspection_signatures(sig):
    """
    Strategy 3B: Fuzzing Argument Injection.
    Ensures that _introspect_module never crashes when encountering
    bizarre (but syntactically valid) Python signatures.
    """
    code = f"def test_func({sig}): pass"
    mod = make_dummy_module(code)
    
    manager = PluginManager()
    actions = manager._introspect_module(mod)
    
    assert "test_func" in actions
    action = actions["test_func"]
    
    assert action.name == "test_func"
    assert isinstance(action.signature_info, dict)
    assert "parameters" in action.signature_info

@given(st.text())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fuzz_manifest_parsing(temp_plugins_dir, manager, bad_json):
    """
    Ensures bad JSON in manifest files never crashes the manager.
    """
    plugin_dir = temp_plugins_dir / "bad_plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    (plugin_dir / "manifest.json").write_text(bad_json, encoding="utf-8")
    (plugin_dir / "__init__.py").write_text("def x(): pass", encoding="utf-8")
    
    # Should safely return None (fail to load) but NEVER crash
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
