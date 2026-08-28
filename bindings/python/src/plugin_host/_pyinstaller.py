import os

def get_hook_dirs():
    """
    Returns the list of directories containing PyInstaller hooks for Evoker.
    Registered via the pyinstaller40 entry point.
    """
    return [os.path.dirname(__file__)]
