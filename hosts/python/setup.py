import os
import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

# Set the desired standalone python version to download here
PYTHON_VERSION = "3.13"

class CustomBuildPy(build_py):
    def run(self):
        print(f"Downloading Python {PYTHON_VERSION} as AOT step...")
        
        # Ensure requests and zstandard are installed in the current build environment
        # so our downloader script can use them.
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests>=2.31.0", "zstandard>=0.21.0"],
            check=True
        )
        
        # Run our custom downloader script
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "download_pythons.py")
        subprocess.run([sys.executable, script_path, PYTHON_VERSION], check=True)
        
        # Build docs
        print("Building documentation...")
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "doc")
        if os.path.exists(docs_dir):
            # Using shell=True for Windows npm command resolution
            subprocess.run(["npm", "install"], cwd=docs_dir, shell=True, check=True)
            subprocess.run(["npm", "run", "build"], cwd=docs_dir, shell=True, check=True)
            
            # Copy built docs to src/plugin_host/docs_html
            import shutil
            docs_build_dir = os.path.join(docs_dir, "build")
            docs_html_dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "plugin_host", "docs_html")
            if os.path.exists(docs_build_dir):
                if os.path.exists(docs_html_dest):
                    shutil.rmtree(docs_html_dest)
                shutil.copytree(docs_build_dir, docs_html_dest)
        
        # Continue with standard build
        build_py.run(self)

setup(
    name='evoker_plugin_host',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
    ],
    entry_points={
        'pyinstaller40': [
            'hook-dirs = plugin_host._pyinstaller:get_hook_dirs',
        ]
    },
    extras_require={
        'dev': [
            'pyarrow>=12.0.0',
            'pytest>=7.4.0',
            'hypothesis>=6.82.0',
            'pytest-xprocess>=0.22.0',
            'tox>=4.6.4',
            'requests>=2.31.0',
            'zstandard>=0.21.0',
        ]
    },
    cmdclass={
        'build_py': CustomBuildPy,
    },
    include_package_data=True,
    package_data={
        # Ensure the downloaded pythons and built docs are bundled with the package
        '': ['pythons/**/*', 'docs_html/**/*'],
    }
)
