---
name: build-evoker-release
description: >-
  Provides instructions for building and testing the Evoker PyInstaller release. 
  Use this skill when the user wants to compile Evoker, build the host.exe, 
  or run the integration tests for the Python host.
---

# Building and Testing Evoker Releases

The Evoker project includes a Python reference host implementation that bundles the `evoker` package and the standalone Python interpreter using PyInstaller.

## 1. Running the Integration Test (Recommended)

The most robust way to build and verify the release is by running the `test_build.py` integration test. It handles cleaning old artifacts, running the PyInstaller build, executing the resulting `host.exe`, and verifying XML-RPC/Arrow IPC communication.

```powershell
cd hosts/python
pytest -m "slow" tests/test_build.py -s
```

*Note: This process takes approximately 3-4 minutes as it involves downloading PyArrow wheels and bundling a full Python interpreter.*

## 2. Building Manually without Testing

If you only want to produce the `dist/host.exe` binary without running the test suite:

```powershell
cd hosts/python
python dev.py build-release
```

## 3. Investigating Build Failures

If the PyInstaller built executable (`dist/host.exe`) hangs or fails:
1. **DLL Collisions**: Ensure `evoker` is correctly isolated inside `_MEIPASS/evoker_pkg` in `host.spec`. Standalone freethreaded (`cp313t`) python workers will crash if they import `.pyd` files compiled for the `cp313` host Python.
2. **Missing Plugins**: Check the worker output to see if a plugin failed to load (e.g. `ImportError`).
3. **Ghost Processes**: If tests are forcefully stopped, lingering `python.exe` worker processes can hold a lock on `build/host/host.pkg`, breaking subsequent PyInstaller builds with `WinError 32`. Fix this by running:
   ```powershell
   taskkill /F /IM python.exe /T
   ```
