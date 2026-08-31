import os
import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

# Set the desired standalone python version to download here
PYTHON_VERSION = "3.13"

setup(
    name='evoker',
    version='0.1.0',
    description='Evoker: Extending native applications with Python',
    python_requires='>=3.10',
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
    include_package_data=True,
    package_data={
        # Ensure the downloaded pythons are bundled with the package
        '': ['pythons/**/*'],
    }
)
