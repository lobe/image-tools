# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
spec_path = os.path.realpath(SPECPATH)

# fix for tensorflow >=1.15 from https://github.com/pyinstaller/pyinstaller/issues/4400
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all
tf_hidden_imports = collect_submodules('tensorflow_core')
tf_datas = collect_data_files('tensorflow_core', subdir=None, include_py_files=True)
astor_datas, _, astor_hidden_imports = collect_all("astor")


a = Analysis(['app.py'],
             pathex=[os.path.join(spec_path, '..')],
             binaries=[],
             datas=tf_datas + astor_datas + [('assets/', 'assets/')],
             hiddenimports=tf_hidden_imports + astor_hidden_imports,
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
          [],
          exclude_binaries=True,
          name='Image Tools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='assets/icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Image Tools')
