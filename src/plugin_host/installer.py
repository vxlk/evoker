import logging
import subprocess
import sys
import os
from pathlib import Path

from plugin_host.downloader import download_and_extract_python

logger = logging.getLogger(__name__)

class DependencyInstallError(Exception):
    """Raised when plugin dependencies fail to install."""
    pass

def install_plugin_deps(plugin_path: Path) -> bool:
    """
    Scans a plugin directory for requirements.txt.
    If a python version is specified (e.g. python==3.11), it will download
    that python version as an AOT step, create a .venv, and install dependencies into it.
    
    Returns True if successful (or nothing to do), raises DependencyInstallError on failure.
    """
    req_file = plugin_path / "requirements.txt"
    if not req_file.exists():
        return True
        
    python_version = None
    filtered_reqs = []
    
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("python=="):
                python_version = stripped.split("==")[1].strip()
            else:
                filtered_reqs.append(line)
                
    # If a specific python is requested, download it and create a .venv
    if python_version:
        logger.info(f"Plugin {plugin_path.name} requested Python {python_version}. Preparing isolated environment...")
        base_python_exe = download_and_extract_python(python_version)
        
        venv_dir = plugin_path / ".venv"
        if not venv_dir.exists():
            subprocess.run([str(base_python_exe), "-m", "venv", str(venv_dir)], check=True)
            
        # Determine venv python path
        if os.name == "nt":
            pip_python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            pip_python_exe = venv_dir / "bin" / "python"
    else:
        # Fallback to host's environment if no python version specified
        pip_python_exe = Path(sys.executable)
        
    filtered_req_file = plugin_path / ".requirements_filtered.txt"
    with open(filtered_req_file, "w", encoding="utf-8") as f:
        f.writelines(filtered_reqs)
        
    wheels_dir = plugin_path / "wheels"
    cmd = [str(pip_python_exe), "-m", "pip", "install", "-r", str(filtered_req_file)]
    
    if wheels_dir.exists() and wheels_dir.is_dir():
        logger.info(f"Plugin {plugin_path.name} contains offline wheels. Using offline installation.")
        cmd.extend(["--no-index", "--find-links", str(wheels_dir)])
        
    logger.info(f"Installing dependencies for plugin {plugin_path.name}...")
    
    try:
        # We capture output to avoid polluting host app stdout unless there's an error
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.debug(f"Pip install output for {plugin_path.name}: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to install dependencies for {plugin_path.name}. Exit code: {e.returncode}\n{e.stderr}"
        logger.error(error_msg)
        raise DependencyInstallError(error_msg)
    finally:
        if filtered_req_file.exists():
            filtered_req_file.unlink()
