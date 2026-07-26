import sys
from pathlib import Path

def get_app_dir(file_path: str) -> Path:
    """
    Returns the persistent application directory, seamlessly resolving PyInstaller paths.
    
    In a frozen PyInstaller bundle, `__file__` often points to the hidden `_internal` 
    or `_MEIPASS` directory. This helper correctly resolves to the directory containing 
    the `.exe` when frozen, while gracefully falling back to `Path(file_path).parent` 
    during standard python execution.
    
    Usage:
        base_dir = get_app_dir(__file__)
        plugins_client = PluginClient(base_dir / "plugins")
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(file_path).parent
