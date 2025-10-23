# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Log Collector
# Build mode: --onedir (패키지 파일들을 압축하지 않음)
# Console: --noconsole (콘솔 창 표시 안 함)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'paramiko',
        'cryptography',
        'bcrypt',
        'pynacl',
        'wx',
        'wx.lib.agw',
        'wx._core',
        'wx._html',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'scipy',
        'numpy.distutils',
        'tk',
        'tcl',
        '_tkinter',
        'tkinter',
        'Tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # --onedir 모드: 바이너리를 별도 파일로 분리
    name='LogCollector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # --noconsole: 콘솔창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일 경로 (선택사항)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LogCollector',
)
