import logging
import subprocess
import sys
import os
from pathlib import Path

CORE_DEPS = []

logger = logging.getLogger(__name__)

class DependencyInstallError(Exception):
    """Raised when plugin dependencies fail to install."""
    pass

def _get_bundled_python() -> Path | None:
    """Finds the bundled python executable installed via setup.py."""
    pythons_dir = Path(__file__).parent / "pythons"
    if not pythons_dir.exists() or not pythons_dir.is_dir():
        return None
        
    for root, dirs, files in os.walk(pythons_dir):
        if "python.exe" in files:
            return Path(root) / "python.exe"
        if "python3" in files and "bin" in Path(root).parts:
            return Path(root) / "python3"
            
    return None

def install_plugin_deps(plugin_path: Path) -> bool:
    """
    Scans a plugin directory for requirements.txt.
    It will create a .venv using the bundled python interpreter (if available)
    or the host's python interpreter, and install dependencies into it.
    
    Returns True if successful (or nothing to do), raises DependencyInstallError on failure.
    """
    req_file = plugin_path / "requirements.txt"
    if not req_file.exists():
        return True
        
    bundled_python = _get_bundled_python()
    venv_dir = plugin_path / ".venv"
    
    if bundled_python:
        logger.info(f"Using bundled Python at {bundled_python} for {plugin_path.name}")
        base_python_exe = bundled_python
    else:
        logger.info(f"No bundled Python found. Falling back to host Python {sys.executable} for {plugin_path.name}")
        base_python_exe = Path(sys.executable)
        
    if not venv_dir.exists():
        subprocess.run([str(base_python_exe), "-m", "venv", str(venv_dir)], check=True)
        
    # Determine venv python path
    if os.name == "nt":
        pip_python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        pip_python_exe = venv_dir / "bin" / "python"
        
    wheels_dir = plugin_path / "wheels"
    cmd = [str(pip_python_exe), "-m", "pip", "install", *CORE_DEPS, "-r", str(req_file)]
    
    # Auto-build wheels if they are missing
    if not wheels_dir.exists() or not any(wheels_dir.iterdir()):
        logger.info(f"Wheels for plugin {plugin_path.name} do not exist. Building them now...")
        wheels_dir.mkdir(exist_ok=True)
        build_cmd = [str(pip_python_exe), "-m", "pip", "wheel", *CORE_DEPS, "-r", str(req_file), "-w", str(wheels_dir)]
        try:
            result = subprocess.run(build_cmd, check=True, capture_output=True, text=True)
            logger.debug(f"Pip wheel output for {plugin_path.name}: {result.stdout}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to build wheels for {plugin_path.name}. Exit code: {e.returncode}\n{e.stderr}"
            logger.error(error_msg)
            raise DependencyInstallError(error_msg)
    
    if wheels_dir.exists() and any(wheels_dir.iterdir()):
        logger.info(f"Plugin {plugin_path.name} contains offline wheels. Preferring local wheels.")
        cmd.extend(["--no-index", "--find-links", str(wheels_dir)])
        
    logger.info(f"Installing dependencies for plugin {plugin_path.name}...")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.debug(f"Pip install output for {plugin_path.name}: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to install dependencies for {plugin_path.name}. Exit code: {e.returncode}\n{e.stderr}"
        logger.error(error_msg)
        raise DependencyInstallError(error_msg)
