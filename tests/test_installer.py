import pytest
from pathlib import Path
from plugin_host.installer import install_plugin_deps, DependencyInstallError
from plugin_host.manager import PluginManager
import sys

def test_no_requirements(temp_plugins_dir):
    plugin_dir = temp_plugins_dir / "no_deps"
    plugin_dir.mkdir(parents=True)
    # Should return True immediately
    assert install_plugin_deps(plugin_dir) is True

def test_online_install_success(temp_plugins_dir):
    plugin_dir = temp_plugins_dir / "online_deps"
    plugin_dir.mkdir(parents=True)
    
    # We will install a tiny known package just to prove pip runs
    # 'six' is usually extremely fast and harmless
    (plugin_dir / "requirements.txt").write_text("six", encoding="utf-8")
    
    assert install_plugin_deps(plugin_dir) is True

def test_install_failure(temp_plugins_dir):
    plugin_dir = temp_plugins_dir / "bad_deps"
    plugin_dir.mkdir(parents=True)
    
    (plugin_dir / "requirements.txt").write_text("this_package_does_not_exist_12345", encoding="utf-8")
    
    with pytest.raises(DependencyInstallError):
        install_plugin_deps(plugin_dir)

def test_offline_install_attempt(temp_plugins_dir, monkeypatch):
    plugin_dir = temp_plugins_dir / "offline_deps"
    plugin_dir.mkdir(parents=True)
    
    (plugin_dir / "requirements.txt").write_text("six", encoding="utf-8")
    (plugin_dir / "wheels").mkdir() # create the offline dir
    
    # We'll mock subprocess.run to verify the command contains --no-index
    import subprocess
    original_run = subprocess.run
    
    cmd_called = []
    def mock_run(cmd, **kwargs):
        cmd_called.append(cmd)
        # return a mock completed process
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="mock")
        
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    assert install_plugin_deps(plugin_dir) is True
    
    assert len(cmd_called) == 1
    assert "--no-index" in cmd_called[0]
    assert "--find-links" in cmd_called[0]

def test_manager_skips_on_install_failure(temp_plugins_dir, caplog):
    manager = PluginManager()
    plugin_dir = temp_plugins_dir / "bad_deps_plugin"
    plugin_dir.mkdir(parents=True)
    
    (plugin_dir / "manifest.json").write_text('{"name": "test"}', encoding="utf-8")
    (plugin_dir / "__init__.py").write_text("def hello(): pass", encoding="utf-8")
    (plugin_dir / "requirements.txt").write_text("this_package_does_not_exist_12345", encoding="utf-8")
    
    actions = manager.load_plugin(plugin_dir)
    assert actions is None
    assert "Dependency installation failed" in caplog.text
