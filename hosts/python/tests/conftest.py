import pytest
from pathlib import Path
from evoker.manager import PluginManager

@pytest.fixture
def temp_plugins_dir(tmp_path):
    return tmp_path / "plugins"

@pytest.fixture
def manager():
    return PluginManager()
