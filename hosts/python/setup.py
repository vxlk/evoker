import os
from setuptools import setup, find_packages

version_file = os.path.join(os.path.dirname(__file__), '../../VERSION')
with open(version_file, 'r') as f:
    version = f.read().strip()

setup(
    name='evoker_client',
    version=version,
    description='Evoker Python Client',
    python_requires='>=3.10',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        f"evoker=={version}"
    ],
    entry_points={
        'pyinstaller40': [
            'hook-dirs = evoker_client._pyinstaller:get_hook_dirs',
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
    include_package_data=True
)
