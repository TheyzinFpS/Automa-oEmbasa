# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# O pythonnet carrega componentes .NET em runtime. Hidden imports sozinhos nao
# bastam: o onedir precisa levar a DLL e o .deps.json de Python.Runtime.
pythonnet_datas = collect_data_files("pythonnet", subdir="runtime")
pythonnet_binaries = collect_dynamic_libs("pythonnet")
clr_loader_binaries = collect_dynamic_libs("clr_loader")

hiddenimports = [
    "clr",
    "pythonnet",
    "pythonnet.runtime",
    "clr_loader",
    "clr_loader.ffi",
    "pythoncom",
    "tkinter",
    "win32com",
    "win32com.client",
    "webview",
    "webview.platforms.edgechromium",
]

hiddenimports += collect_submodules("pythonnet")
hiddenimports += collect_submodules("clr_loader")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pythonnet_binaries + clr_loader_binaries,
    datas=[
        ("interface", "interface"),
    ] + pythonnet_datas,
    hiddenimports=hiddenimports,
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
    name="EmbasaPedidosSAP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icons/embasa_automation_icon_A.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EmbasaPedidosSAP",
)
