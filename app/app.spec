# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

spec_path = os.path.realpath(SPECPATH)


a = Analysis(['app.py'],
             pathex=[os.path.join(spec_path, '..')],
             binaries=[],
             datas=[('assets/icon.ico', '.')],
             hiddenimports=['cmath'],
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
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='assets/icon.ico')

# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name='Image Tools.app',
                icon='assets/icon.ico')
