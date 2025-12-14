# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['src'],  # src 디렉토리를 모듈 검색 경로에 추가
    binaries=[],
    datas=[
        ('src/study_with/resources', 'resources'),
    ],
    hiddenimports=[
        'study_with',
        'study_with.app',
        'study_with.ui',
        'study_with.session_manager',
        'study_with.rank_themes',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageQt',
        'PIL._webp',
        'flask',
        'flask_cors',
        'psutil',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
    ],
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
    name='StudyWith',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있다면 여기에 경로 지정
)
