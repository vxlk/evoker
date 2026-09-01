# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['examples/host.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/evoker_client', 'evoker_client'),
        ('../../evoker/src/evoker', 'evoker_pkg/evoker'),
        ('examples/plugins', 'plugins'),
        ('examples/host_api', 'injected/host_api')
    ],
    hiddenimports=['xmlrpc.client', 'xmlrpc.server', 'xmlrpc'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'pandas', 'matplotlib', 'PIL', 'PyQt5', 'PySide2', 'tkinter', 'IPython', 'notebook', 'jupyter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='host',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
