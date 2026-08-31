import traceback
from evoker_client.client import PluginClient
import xmlrpc.client
import pathlib
temp = pathlib.Path('.venv/temp/rpc_plugin')
temp.mkdir(parents=True, exist_ok=True)
(temp / 'manifest.json').write_text('{"name": "rpc_plugin"}')
(temp / '__init__.py').write_text('def rpc_action(**kwargs): return kwargs')
try:
    with PluginClient(temp.parent) as client:
        client.start_worker()
        client.get_plugins()
        try:
            client.proxy.invoke('rpc_plugin', 'rpc_action', {'\x1f0': []})
        except Exception as e:
            traceback.print_exc()
except Exception as e:
    traceback.print_exc()

