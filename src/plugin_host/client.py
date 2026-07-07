import subprocess
import time
import xmlrpc.client
import sys
from pathlib import Path

class PluginClient:
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.worker_process = None
        self.proxy = None
        
    def start_worker(self):
        worker_script = Path(__file__).parent / "worker.py"
        import os
        env = os.environ.copy()
        # Add src/ to PYTHONPATH
        env["PYTHONPATH"] = str(Path(__file__).parent.parent)
        
        # Determine which python executable to use.
        # Check if any plugin in plugins_dir has a .venv we can use, 
        # or check the common pythons directory.
        python_exe = Path(sys.executable)
        
        # 1. Check for a .venv in any of the plugins
        if self.plugins_dir.exists():
            for plugin_dir in self.plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    if os.name == "nt":
                        venv_exe = plugin_dir / ".venv" / "Scripts" / "python.exe"
                    else:
                        venv_exe = plugin_dir / ".venv" / "bin" / "python"
                        
                    if venv_exe.exists():
                        python_exe = venv_exe
                        break
        
        # 2. Check the pythons directory directly as a fallback
        if python_exe == Path(sys.executable):
            pythons_dir = Path(__file__).parent.parent.parent / "pythons"
            if pythons_dir.exists():
                for item in pythons_dir.iterdir():
                    if item.is_dir() and item.name.startswith("python-"):
                        if os.name == "nt":
                            standalone_exe = item / "python" / "python.exe"
                        else:
                            standalone_exe = item / "python" / "bin" / "python3"
                        if standalone_exe.exists():
                            python_exe = standalone_exe
                            break

        # Start the worker subprocess
        self.worker_process = subprocess.Popen(
            [str(python_exe), str(worker_script), str(self.plugins_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )
        
        # Scrape stdout for the assigned port
        port = None
        start_time = time.time()
        while time.time() - start_time < 5:
            line = self.worker_process.stdout.readline()
            if not line:
                break
            if line.startswith("RPC_PORT:"):
                port = int(line.strip().split(":")[1])
                break
                
        if port is None:
            self.stop_worker()
            raise RuntimeError("Failed to start worker or get port.")
            
        self.proxy = xmlrpc.client.ServerProxy(f"http://localhost:{port}")
        
    def stop_worker(self):
        if self.worker_process:
            self.worker_process.terminate()
            self.worker_process.wait(timeout=2)
            self.worker_process = None
            
    def get_plugins(self):
        return self.proxy.scan()
        
    def run_action(self, plugin_name: str, action_name: str, kwargs: dict):
        return self.proxy.invoke(plugin_name, action_name, kwargs)
