import pytest
import types
from hypothesis import given, settings, HealthCheck, strategies as st
from evoker.manager import PluginManager, PrefixStrategy

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
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
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

@given(st.text(), st.text())
def test_fuzz_prefix_strategy_matching(prefix, random_suffix):
    """
    Property test for PrefixStrategy to ensure robust matching and metadata extraction.
    """
    strategy = PrefixStrategy(prefix)
    sig_info = {"parameters": {}}
    
    # 1. Valid Extraction
    # If the function name is perfectly constructed from prefix + suffix
    valid_name = prefix + random_suffix
    # Note: if prefix is empty, startswith("") is always True.
    match = strategy.match(valid_name, sig_info)
    assert match is not None
    assert match["menu_name"] == random_suffix
    
    # 2. Rejection
    # If we prepend a character that differs from the first character of the prefix,
    # it should fail to match
    if prefix:
        prepended_char = "Y" if prefix[0] == "X" else "X"
        invalid_name = prepended_char + prefix + random_suffix
        assert strategy.match(invalid_name, sig_info) is None

@given(st.text(), st.text())
def test_fuzz_prefix_strategy_no_crash(prefix, random_name):
    """
    Ensures PrefixStrategy never crashes on any text input.
    """
    strategy = PrefixStrategy(prefix)
    sig_info = {"parameters": {}}
    # 3. No Exceptions
    try:
        strategy.match(random_name, sig_info)
    except Exception as e:
        pytest.fail(f"PrefixStrategy crashed with exception: {e}")

@settings(deadline=None)
@given(st.text())
def test_fuzz_injected_packages_env(env_val):
    """
    Ensures arbitrary env inputs don't crash injected packages logic.
    """
    from evoker.worker import parse_injected_packages
    try:
        parse_injected_packages(env_val)
    except Exception as e:
        pytest.fail(f"parse_injected_packages crashed with: {e}")

@given(st.text())
def test_fuzz_strategies_env(env_val):
    """
    Ensures arbitrary env inputs don't crash strategy parsing logic.
    """
    from evoker.worker import parse_strategies
    try:
        parse_strategies(env_val)
    except Exception as e:
        pytest.fail(f"parse_strategies crashed with: {e}")

@given(st.dictionaries(st.text(), st.text()))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fuzz_rpc_serialization(temp_plugins_dir, kwargs_payload):
    """
    Ensure the RPC client gracefully raises xmlrpc Faults on arbitrary kwargs,
    rather than causing hangs or hard crashes.
    """
    from evoker_client.client import PluginClient
    import xmlrpc.client
    
    plugin_dir = temp_plugins_dir / "rpc_plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text('{"name": "test"}', encoding="utf-8")
    (plugin_dir / "__init__.py").write_text("def rpc_action(**kwargs): return kwargs", encoding="utf-8")
    
    client = PluginClient(temp_plugins_dir)
    try:
        client.start_worker()
        client.get_plugins()
        try:
            client.run_action("rpc_plugin", "rpc_action", kwargs_payload)
        except xmlrpc.client.Fault:
            pass
        except ValueError:
            pass
    finally:
        client.stop_worker()

