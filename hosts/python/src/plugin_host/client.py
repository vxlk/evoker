import subprocess
import time
import xmlrpc.client
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

class PluginClient:
    def __init__(self, plugins_dir: Path, strategies: Optional[List[Dict[str, Any]]] = None, injected_packages: Optional[List[Path]] = None):
        self.plugins_dir = plugins_dir
        self.strategies = strategies
        self.injected_packages = injected_packages
        self.worker_process = None
        self.proxy = None
        
    def start_worker(self):
        worker_script = Path(__file__).parent / "worker.py"
        import os
        env = os.environ.copy()
        
        # Strip PyInstaller environment modifications so standalone python doesn't crash
        for var in ["PYTHONPATH", "PYTHONHOME", "PATH"]:
            orig_var = f"ORIG_{var}"
            if orig_var in env:
                env[var] = env[orig_var]
            elif var in env:
                # We shouldn't delete PATH, but PYTHONPATH/PYTHONHOME are fine
                if var != "PATH":
                    del env[var]
                
        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            base_dir = Path(sys._MEIPASS)
            # Add the extracted raw source code directory to PYTHONPATH
            # so external venv Python interpreters can import plugin_host!
            plugin_host_src = base_dir / "plugin_host_src"
            env["PYTHONPATH"] = str(plugin_host_src)
            plugin_host_dir = plugin_host_src / "plugin_host"
            worker_script = plugin_host_dir / "worker.py"
        else:
            plugin_host_dir = Path(__file__).parent
            env["PYTHONPATH"] = str(plugin_host_dir.parent)
            worker_script = plugin_host_dir / "worker.py"

        if self.strategies is not None:
            env["EVOKER_STRATEGIES"] = json.dumps(self.strategies)
            
        if self.injected_packages is not None:
            env["EVOKER_INJECTED_PACKAGES"] = json.dumps([str(p.resolve()) for p in self.injected_packages])
        
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
        
        # 2. Check the common pythons directory
        if python_exe == Path(sys.executable):
            pythons_dir = plugin_host_dir / "pythons"
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

        if getattr(sys, "frozen", False) and python_exe == Path(sys.executable):
            # In a frozen bundle (PyInstaller), if we are using the bundled host.exe as the interpreter
            # We must pass this flag so our runtime hook intercepts it and launches the worker script
            # instead of running the main host app again (which would cause an infinite hang).
            cmd = [str(python_exe), "--evoker-worker", str(worker_script), str(self.plugins_dir)]
        else:
            # When using an external Python interpreter (.venv), it natively supports running modules
            cmd = [str(python_exe), "-u", "-m", "plugin_host.worker", str(self.plugins_dir)]

        self.worker_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )
        
        # Scrape stdout for the assigned port
        port = None
        start_time = time.time()
        output_lines = []
        while time.time() - start_time < 5:
            line = self.worker_process.stdout.readline()
            if not line:
                break
            output_lines.append(line)
            if line.startswith("RPC_PORT:"):
                port = int(line.strip().split(":")[1])
                break
                
        if port is None:
            self.stop_worker()
            raise RuntimeError(f"Failed to start worker or get port.\npython_exe: {python_exe} (exists: {Path(python_exe).exists()})\nworker_script: {worker_script} (exists: {Path(worker_script).exists()})\nWorker output:\n{''.join(output_lines)}")
            
        import threading
        def forward_stdout():
            if self.worker_process and self.worker_process.stdout:
                for line in iter(self.worker_process.stdout.readline, ''):
                    sys.stdout.write(line)
        threading.Thread(target=forward_stdout, daemon=True).start()
            
        self.proxy = xmlrpc.client.ServerProxy(f"http://localhost:{port}")
        
    def stop_worker(self):
        if self.worker_process:
            self.worker_process.terminate()
            self.worker_process.wait(timeout=2)
            self.worker_process = None
            
    def get_plugins(self):
        return self.proxy.scan()
        
    def run_action(self, plugin_name: str, action_name: str, kwargs: dict):
        try:
            return self.proxy.invoke(plugin_name, action_name, kwargs)
        except xmlrpc.client.Fault:
            raise
        except Exception as e:
            raise ValueError(f"RPC Serialization or Connection Error: {e}")
