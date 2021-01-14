# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

spec_path = os.path.realpath(SPECPATH)

from PyInstaller.utils.hooks import collect_all
astor_datas, _, astor_hidden_imports = collect_all("astor")


a = Analysis(['app.py'],
             pathex=[os.path.join(spec_path, '..')],
             binaries=[],
             datas=astor_datas + [('assets/icon.ico', '.')],
             hiddenimports=astor_hidden_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          # exclude_binaries=True,
          name='Image Tools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='assets/icon.ico')

# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name='Image Tools.app',
                icon='assets/icon.ico')
