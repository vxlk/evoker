import subprocess
import time
import xmlrpc.client
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading
import queue

_orig_escape = xmlrpc.client.escape
def _evoker_escape(s):
    for c in s:
        code = ord(c)
        if code < 0x20 and code not in (0x09, 0x0a, 0x0d):
            raise ValueError("Control characters are not allowed in XML-RPC strings")
    return _orig_escape(s).replace('\r', '&#13;')
xmlrpc.client.escape = _evoker_escape

class WorkerDiedError(Exception):
    pass


class PluginClient:
    def __init__(self, plugins_dir: Path, strategies: Optional[List[Dict[str, Any]]] = None, injected_packages: Optional[List[Path]] = None):
        self.plugins_dir = plugins_dir
        self.strategies = strategies
        self.injected_packages = injected_packages
        self.worker_process = None
        self.proxy = None
        self.lock = threading.Lock()
        self.auth_token = None
        
    def start_worker(self):
        import os
        env = os.environ.copy()
        
        # Scrub PyInstaller environment variables so they don't break the standalone python
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        
        # PyInstaller modifies PATH to prepend sys._MEIPASS. We must remove it
        # or else C extensions (like numpy) will load conflicting DLLs from the host bundle.
        if hasattr(sys, "_MEIPASS"):
            path_env = env.get("PATH", "")
            # Filter out the MEIPASS directory
            clean_paths = [p for p in path_env.split(os.pathsep) if p != sys._MEIPASS and p != sys._MEIPASS + "\\"]
            env["PATH"] = os.pathsep.join(clean_paths)
        
        # Strip PyInstaller environment modifications so standalone python doesn't crash
        for var in ["PYTHONPATH", "PYTHONHOME", "PATH"]:
            orig_var = f"ORIG_{var}"
            if orig_var in env:
                env[var] = env[orig_var]
            elif var in env:
                # We shouldn't delete PATH, but PYTHONPATH/PYTHONHOME are fine
                if var != "PATH":
                    del env[var]
                
        import importlib.util
        spec = importlib.util.find_spec("evoker.worker")
        if not spec or not spec.origin:
            raise RuntimeError("Cannot find evoker.worker. Is evoker installed?")
            
        worker_script = Path(spec.origin)
        evoker_pkg_dir = worker_script.parent
        
        # Set PYTHONPATH so the standalone python can import it
        env["PYTHONPATH"] = str(evoker_pkg_dir.parent)
        
        # Also, pythons directory might be in evoker_client
        client_dir = Path(__file__).parent
        
        if self.strategies is not None:
            env["EVOKER_STRATEGIES"] = json.dumps(self.strategies)
            
        if self.injected_packages is not None:
            env["EVOKER_INJECTED_PACKAGES"] = json.dumps([str(p.resolve()) for p in self.injected_packages])
            
        import os
        self.auth_token = os.urandom(16).hex()
        env["EVOKER_AUTH_TOKEN"] = self.auth_token

        
        # Determine which python executable to use.
        # Check if any plugin in plugins_dir has a .venv we can use, 
        # or check the common pythons directory.
        python_exe = Path(sys.executable)
        
        # 1. Check for a .venv in any of the plugins
        if self.plugins_dir.exists():
            for plugin_dir in sorted(self.plugins_dir.iterdir()):
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
            pythons_dir = client_dir / "pythons"
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
            # When using an external Python interpreter (.venv), run the script directly by path
            cmd = [str(python_exe), "-u", str(worker_script), str(self.plugins_dir)]

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
        
        q = queue.Queue()
        def read_port():
            for line in iter(self.worker_process.stdout.readline, ''):
                q.put(line)
        t = threading.Thread(target=read_port, daemon=True)
        t.start()
        
        while time.time() - start_time < 5:
            try:
                line = q.get(timeout=0.5)
                output_lines.append(line)
                if line.startswith("RPC_PORT:"):
                    port = int(line.strip().split(":")[1])
                    break
            except queue.Empty:
                if self.worker_process.poll() is not None:
                    break
                
        if port is None:
            self.stop_worker()
            raise RuntimeError(f"Failed to start worker or get port.\npython_exe: {python_exe} (exists: {Path(python_exe).exists()})\nworker_script: {worker_script} (exists: {Path(worker_script).exists()})\nWorker output:\n{''.join(output_lines)}")
            
        def forward_stdout():
            while True:
                try:
                    line = q.get(timeout=1.0)
                    sys.stdout.write(line)
                except queue.Empty:
                    if self.worker_process and self.worker_process.poll() is not None:
                        break
                        
        threading.Thread(target=forward_stdout, daemon=True).start()
            
        self.proxy = xmlrpc.client.ServerProxy(
            f"http://127.0.0.1:{port}", 
            headers=(("X-Evoker-Auth", self.auth_token),),
            allow_none=True,
            use_builtin_types=True
        )
        
    def stop_worker(self):
        if self.worker_process:
            self.worker_process.terminate()
            try:
                self.worker_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.worker_process.kill()
                self.worker_process.wait()
            self.worker_process = None
            
    def restart_worker(self):
        self.stop_worker()
        self.start_worker()
            
    def _check_worker(self):
        if self.worker_process and self.worker_process.poll() is not None:
            rc = self.worker_process.returncode
            self.worker_process = None
            raise WorkerDiedError(f"Worker process died unexpectedly (exit code {rc})")

    def get_plugins(self):
        """Scans for plugins. Note: PluginClient serialises calls, blocking the calling thread."""
        with self.lock:
            self._check_worker()
            return self.proxy.scan()
        
    def run_action(self, plugin_name: str, action_name: str, kwargs: dict) -> any:
        """
        Executes a plugin action.
        
        Note: You must call `get_plugins` (scan) before calling this method,
        otherwise the host will reject the invocation with "Plugin not found or not loaded".
        
        Note: This is a synchronous blocking call over XML-RPC.
        It will serialize calls across the worker, meaning that
        a slow plugin action will block the caller and any other
        clients sharing the worker.
        """
        with self.lock:
            self._check_worker()
            try:
                return self.proxy.invoke(plugin_name, action_name, kwargs)
            except xmlrpc.client.Fault:
                raise
            except Exception as e:
                raise ValueError(f"RPC Serialization or Connection Error: {e}")
