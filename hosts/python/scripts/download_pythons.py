import logging
import os
import platform
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Optional

import requests
try:
    import zstandard as zstd
except ImportError:
    zstd = None

logger = logging.getLogger(__name__)

def get_target_triple() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        arch = "x86_64" if machine in ["amd64", "x86_64"] else machine
        return f"{arch}-pc-windows-msvc"
    elif system == "darwin":
        arch = "aarch64" if machine in ["arm64", "aarch64"] else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "linux":
        arch = "aarch64" if machine in ["arm64", "aarch64"] else "x86_64"
        # Often standalone builds use musl or gnu, we'll prefer gnu as default
        return f"{arch}-unknown-linux-gnu"
    
    raise ValueError(f"Unsupported platform: {system} {machine}")

def get_pythons_dir() -> Path:
    """Return the common location for python environments inside the package."""
    return Path(__file__).resolve().parent.parent.parent.parent / "evoker" / "src" / "evoker" / "pythons"

def extract_zst(archive_path: Path, dest_dir: Path):
    if zstd is None:
        raise ImportError("zstandard module is required to extract .tar.zst files")
        
    dctx = zstd.ZstdDecompressor()
    with open(archive_path, 'rb') as ifh:
        with dctx.stream_reader(ifh) as reader:
            with tarfile.open(fileobj=reader, mode='r|') as tar:
                tar.extractall(path=dest_dir)

def extract_gz(archive_path: Path, dest_dir: Path):
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=dest_dir)

def find_latest_release_asset(version: str, triple: str) -> Optional[dict]:
    """Finds the appropriate asset from python-build-standalone."""
    url = "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
    logger.info(f"Querying {url} for Python {version} and {triple}")
    
    resp = requests.get(url)
    resp.raise_for_status()
    release = resp.json()
    
    # We want an asset that matches: cpython-{version}.*-{triple}-install_only
    # If install_only is not available, just standard
    
    best_asset = None
    for asset in release.get("assets", []):
        name = asset["name"]
        
        # Must be cpython
        if not name.startswith("cpython-"):
            continue
            
        # Must match version (e.g. 3.11)
        # the name is like cpython-3.11.8+20240224-x86_64-pc-windows-msvc-install_only.tar.zst
        version_part = name.split("-")[1]
        if not version_part.startswith(version):
            continue
            
        # Must match architecture
        if triple not in name:
            continue
            
        if name.endswith(".tar.zst") or name.endswith(".tar.gz"):
            # Prefer install_only as it's much smaller
            if "install_only" in name:
                return asset
            best_asset = asset
            
    return best_asset

def download_and_extract_python(version: str) -> Path:
    """
    Downloads and extracts the requested Python version.
    Returns the path to the python executable.
    """
    pythons_dir = get_pythons_dir()
    pythons_dir.mkdir(parents=True, exist_ok=True)
    
    triple = get_target_triple()
    short_version = "".join(version.split(".")[:2]) # e.g. 3.13 -> 313
    target_dir = pythons_dir / f"py{short_version}"
    
    if platform.system().lower() == "windows":
        exe_path = target_dir / "python" / "python.exe"
    else:
        exe_path = target_dir / "python" / "bin" / "python3"
        
    if exe_path.exists():
        logger.info(f"Python {version} already exists at {exe_path}")
        return exe_path
        
    asset = find_latest_release_asset(version, triple)
    if not asset:
        raise RuntimeError(f"Could not find a standalone python build for {version} on {triple}")
        
    download_url = asset["browser_download_url"]
    filename = asset["name"]
    
    archive_path = pythons_dir / filename
    
    logger.info(f"Downloading {filename} from {download_url}...")
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(archive_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
    logger.info(f"Extracting {filename} to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if filename.endswith(".tar.zst"):
            extract_zst(archive_path, target_dir)
        elif filename.endswith(".tar.gz"):
            extract_gz(archive_path, target_dir)
        else:
            raise RuntimeError(f"Unknown archive format: {filename}")
    finally:
        # Cleanup archive
        if archive_path.exists():
            archive_path.unlink()
            
    if not exe_path.exists():
        raise RuntimeError(f"Extraction completed but {exe_path} not found.")
        
    return exe_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        download_and_extract_python(sys.argv[1])
    else:
        print("Usage: python download_pythons.py <version>")
        sys.exit(1)
