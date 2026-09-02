import subprocess
from pathlib import Path
import sys

def patch():
    with open(r'hosts\python\src\evoker_client\client.py', 'r', encoding='utf-8') as f:
        code = f.read()

    helper = '''def ensure_evoker_installed(python_exe: Path):
    try:
        import subprocess
        subprocess.check_call([str(python_exe), "-c", "import evoker.worker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        repo_path = Path(__file__).resolve()
        while repo_path.parent != repo_path:
            if (repo_path / "evoker" / "pyproject.toml").exists():
                break
            repo_path = repo_path.parent
        
        if (repo_path / "evoker" / "pyproject.toml").exists():
            evoker_pkg = repo_path / "evoker"
            try:
                subprocess.check_call([str(python_exe), "-m", "pip", "install", str(evoker_pkg)])
                subprocess.check_call([str(python_exe), "-c", "import evoker.worker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to install evoker runtime into python interpreter {python_exe}") from e
        else:
            raise RuntimeError(f"evoker is not installed in {python_exe} and evoker package directory not found for auto-installation.")

'''
    code = code.replace("class WorkerDiedError(Exception):", helper + "class WorkerDiedError(Exception):")
    
    target = '        cmd = [str(python_exe), "-u", str(worker_script), str(self.plugins_dir)]'
    replacement = '''        if python_exe != Path(sys.executable) and not is_frozen:
            ensure_evoker_installed(python_exe)

        cmd = [str(python_exe), "-u", str(worker_script), str(self.plugins_dir)]'''
        
    code = code.replace(target, replacement)
    
    with open(r'hosts\python\src\evoker_client\client.py', 'w', encoding='utf-8') as f:
        f.write(code)

patch()
