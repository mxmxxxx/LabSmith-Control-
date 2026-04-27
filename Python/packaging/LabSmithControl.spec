# -*- mode: python ; coding: utf-8 -*-
# Build (from repo):  cd Python
#   pip install pyinstaller
#   pyinstaller packaging/LabSmithControl.spec
# Output: Python/dist/LabSmithControl.exe
#
# Optional: place icon.ico next to this spec, then uncomment icon= below.

import os

block_cipher = None

try:
    _spec = os.path.abspath(SPECPATH)
except NameError:
    _spec = os.path.abspath(SPEC)
_spec_dir = os.path.dirname(_spec)
# Spec may live in Python/ or Python/packaging/
if os.path.isfile(os.path.join(_spec_dir, "labsmith_gui.py")):
    ROOT = _spec_dir
else:
    ROOT = os.path.dirname(_spec_dir)

datas = []
binaries = []
hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "numpy",
    "serial",
    "serial.tools",
    "serial.tools.list_ports",
    "uProcess_x64",
    "uProcess_x64.uProcess_x64",
]

up = os.path.join(ROOT, "uProcess_x64")
if os.path.isdir(up):
    datas.append((up, "uProcess_x64"))

a = Analysis(
    [os.path.join(ROOT, "labsmith_gui.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LabSmithControl",
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
    # icon=os.path.join(os.path.dirname(_spec), "icon.ico"),
)
