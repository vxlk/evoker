import pytest
import subprocess
from pathlib import Path
import sys

@pytest.mark.slow
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
    build_result = subprocess.run(["python", "dev.py", "build-release"], cwd=python_host_dir, capture_output=True, text=True, timeout=600)
    assert build_result.returncode == 0, f"Build failed:\n{build_result.stdout}\n{build_result.stderr}"
    
    # 3. Verify the executable exists
    exe_path = python_host_dir / "dist" / "host.exe"
    assert exe_path.exists(), "host.exe was not created in dist/"
        
    # 4. Run the executable and verify it works
    print("Running compiled host.exe...")
    
    # Run the host executable, which could fork bomb if EV-88 isn't fixed.
    # On Windows, we can use CREATE_NEW_PROCESS_GROUP and send CTRL_BREAK_EVENT on timeout
    # Or ideally a Job Object, but CREATE_NEW_PROCESS_GROUP with taskkill is simpler in pure Python stdlib.
    # We will use subprocess.Popen and taskkill to kill the tree.
    p = subprocess.Popen([str(exe_path)], cwd=python_host_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = p.communicate(timeout=120)
        returncode = p.returncode
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        stdout, stderr = p.communicate()
        returncode = -1
        assert False, f"Host execution timed out:\n{stdout}\n{stderr}"
    
    assert returncode == 0, f"Host execution failed:\n{stdout}\n{stderr}"
    
    # Verify the host output contains the success messages
    output = stdout + "\n" + stderr
    print(f"--- HOST EXECUTION OUTPUT ---\n{output}\n-----------------------------")
    
    assert "Building them now..." in output, "Expected to see auto-wheel building log."
    assert "Hello World from Plugin via Arrow!" in output, "Missing Arrow IPC (Plugin -> Host) success."
    assert "Hello World from Host via Arrow!" in output, "Missing Arrow IPC (Host -> Plugin) success."
