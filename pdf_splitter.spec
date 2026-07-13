# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

from PyInstaller.utils.hooks import collect_data_files


project_root = Path(os.getcwd()).resolve()


a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=collect_data_files('tkinterdnd2') + [
        (str(project_root / 'templates' / 'templates.json'), 'templates'),
        (str(project_root / 'templates' / 'LS Dotted S A4.template'), 'templates'),
    ],
    hiddenimports=['tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pdf_splitter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
