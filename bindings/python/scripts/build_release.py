import os
import subprocess
import sys
from pathlib import Path

def prepare_plugin_datas():
    base_dir = Path(__file__).parent.parent.absolute()
    plugins_dir = base_dir / "examples" / "plugins"
    build_deps_dir = base_dir / "build" / "bundled_plugin_deps"
    
    # Create build dir if needed
    build_deps_dir.mkdir(parents=True, exist_ok=True)

    datas = []

    if plugins_dir.exists():
        for plugin_path in plugins_dir.iterdir():
            if plugin_path.is_dir():
                req_file = plugin_path / "requirements.txt"
                if req_file.exists():
                    plugin_name = plugin_path.name
                    target_dir = build_deps_dir / plugin_name
                    print(f"Installing dependencies for {plugin_name} into {target_dir}...")
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install",
                        "-r", str(req_file),
                        "-t", str(target_dir)
                    ])
                    # Add to PyInstaller datas: (source, destination)
                    datas.append((str(target_dir), f"bundled_plugin_deps/{plugin_name}"))

    # Also bundle pythons
    pythons_dir = base_dir / "src" / "pythons"
    if pythons_dir.exists():
        datas.append((str(pythons_dir), "src/pythons"))

    return datas

if __name__ == "__main__":
    print("PyInstaller datas to bundle:")
    for data in prepare_plugin_datas():
        print(data)
