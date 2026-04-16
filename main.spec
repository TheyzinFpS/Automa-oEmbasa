# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


project_root = Path.cwd()

datas = [(str(project_root / "interface"), "interface")]
datas += collect_data_files("webview", subdir="js")
datas += collect_data_files("webview", subdir="lib")
datas += collect_data_files("pythonnet")
datas += collect_data_files("clr_loader")

binaries = []
binaries += collect_dynamic_libs("webview")
binaries += collect_dynamic_libs("pythonnet")
binaries += collect_dynamic_libs("clr_loader")

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["clr", "pythonnet", "clr_loader", "webview.platforms.edgechromium"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EMBASA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EMBASA",
)
