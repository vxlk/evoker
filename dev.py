#!/usr/bin/env python3
import sys
import subprocess
import os
import venv
from pathlib import Path
import argparse

def run_command(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        sys.exit(result.returncode)

def get_venv_python():
    py_path = Path(".venv/Scripts/python.exe") if os.name == "nt" else Path(".venv/bin/python")
    if not py_path.exists():
        print(f"[!] Virtual environment not found at {py_path}. Falling back to global Python.")
        return Path(sys.executable)
    return py_path

def cmd_install():
    print("Installing dependencies...")
    venv_dir = Path(".venv")
    if not venv_dir.exists():
        print("Creating virtual environment...")
        venv.create(".venv", with_pip=True)
    
    py_exec = get_venv_python()
    run_command([str(py_exec), "-m", "pip", "install", "-e", ".[dev]"])

def cmd_build():
    print("Building pyinstaller example...")
    py_exec = get_venv_python()
    run_command([str(py_exec), "-m", "PyInstaller", "--onefile", "examples/host.py"])

def cmd_docs():
    print("Building documentation...")
    run_command(["npm", "run", "build"], cwd="doc")

def cmd_test():
    print("Running tests...")
    py_exec = get_venv_python()
    run_command([str(py_exec), "-m", "pytest"])

def cmd_run_example():
    print("Running example...")
    py_exec = get_venv_python()
    # Unbuffered python output to ensure plugin prints stream correctly
    run_command([str(py_exec), "-u", "examples/host.py"])

def cmd_build_release():
    print("Building release bundle...")
    py_exec = get_venv_python()
    
    # Download pythons if missing
    pythons_script = Path("scripts/download_pythons.py")
    subprocess.run([str(py_exec), "-m", "pip", "install", "requests", "zstandard"], check=True)
    subprocess.run([str(py_exec), str(pythons_script), "3.13"], check=True)
    
    # Ensure pyinstaller is installed in venv
    subprocess.run([str(py_exec), "-m", "pip", "install", "pyinstaller"])
    run_command([str(py_exec), "-m", "PyInstaller", "host.spec", "--clean"])

def main():
    parser = argparse.ArgumentParser(description="Development utility script for Behemoth")
    parser.add_argument("command", choices=["install", "build", "docs", "test", "run-example", "build-release"])
    
    args = parser.parse_args()
    
    if args.command == "install":
        cmd_install()
    elif args.command == "build":
        cmd_build()
    elif args.command == "docs":
        cmd_docs()
    elif args.command == "test":
        cmd_test()
    elif args.command == "run-example":
        cmd_run_example()
    elif args.command == "build-release":
        cmd_build_release()

if __name__ == "__main__":
    main()
