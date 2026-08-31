import pytest
import subprocess
from pathlib import Path
import sys

@pytest.mark.skipif(sys.platform != "win32", reason="Integration test currently targets Windows host.exe")
def test_pyinstaller_build_and_run(tmp_path):
    """
    Integration test that proves:
    1. PyInstaller can successfully bundle Evoker (including the pythons dir).
    2. The resulting executable can successfully run, extract the bundled python,
       and automatically build wheels for the hello_world plugin.
    3. The host can communicate with the worker via XML-RPC and Arrow IPC.
    """
    # 1. Clean any existing wheels or .venv in the examples to ensure it auto-builds them
    python_host_dir = Path(__file__).parent.parent
    hw_plugin_dir = python_host_dir / "examples" / "plugins" / "hello_world_plugin"
    wheels_dir = hw_plugin_dir / "wheels"
    venv_dir = hw_plugin_dir / ".venv"
    import shutil
    if wheels_dir.exists():
        shutil.rmtree(wheels_dir)
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    # 2. Run the build (using python dev.py build-release)
    print("Building PyInstaller release bundle...")
    build_result = subprocess.run(["python", "dev.py", "build-release"], cwd=python_host_dir, capture_output=True, text=True)
    assert build_result.returncode == 0, f"Build failed:\n{build_result.stdout}\n{build_result.stderr}"
    
    # 3. Verify the executable exists
    exe_path = python_host_dir / "dist" / "host.exe"
    assert exe_path.exists(), "host.exe was not created in dist/"
        
    # 4. Run the executable and verify it works
    print("Running compiled host.exe...")
    run_result = subprocess.run([str(exe_path)], cwd=python_host_dir, capture_output=True, text=True)
    
    assert run_result.returncode == 0, f"Host execution failed:\n{run_result.stdout}\n{run_result.stderr}"
    
    # Verify the host output contains the success messages
    output = run_result.stdout + "\n" + run_result.stderr
    assert "Building them now..." in output, "Expected to see auto-wheel building log."
    assert "Hello World from Plugin via Arrow!" in output, "Missing Arrow IPC (Plugin -> Host) success."
    assert "Hello World from Host via Arrow!" in output, "Missing Arrow IPC (Host -> Plugin) success."
