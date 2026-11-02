# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 설정 — EasySaving.exe 하나로 묶는다.

빌드:  pyinstaller --clean build/EasySaving.spec
결과:  dist/EasySaving.exe
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files

ROOT = os.path.abspath(os.path.join(os.getcwd()))
ICON = os.path.join(ROOT, "assets", "easysaving.ico")
# .ico 는 윈도우 전용. (맥에서 빌드를 시험해 볼 때 오류가 나지 않도록)
USE_ICON = sys.platform.startswith("win") and os.path.exists(ICON)

# 실행 파일 속성(자세히) 에 회사·제품·버전 정보를 넣는다.
# 정보가 비어 있는 서명 없는 exe 는 백신이 더 의심하는 경향이 있다.
sys.path.insert(0, ROOT)
from easysaving import APP_NAME, APP_VERSION  # noqa: E402

_ver = tuple(int(x) for x in APP_VERSION.split(".")) + (0,)
VERSION_FILE = os.path.join(ROOT, "build", "version_info.txt")
with open(VERSION_FILE, "w", encoding="utf-8") as _fp:
    _fp.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={_ver}, prodvers={_ver}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041204B0', [
      StringStruct('CompanyName', 'Mango'),
      StringStruct('FileDescription', '{APP_NAME} - PDF 페이지 분할 저장 / PowerPoint 변환'),
      StringStruct('FileVersion', '{APP_VERSION}'),
      StringStruct('InternalName', 'EasySaving'),
      StringStruct('LegalCopyright', 'Copyright (c) Mango'),
      StringStruct('OriginalFilename', 'EasySaving.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])
  ]
)
""")

# 쓰지 않는 큰 모듈을 빼서 실행 파일 크기와 메모리 사용량을 줄인다.
EXCLUDES = [
    "numpy", "pandas", "matplotlib", "scipy", "cv2",   # PIL 은 python-pptx 가 쓴다
    "IPython", "jupyter", "notebook", "pytest", "setuptools", "pip",
    "lib2to3", "pydoc_data", "sqlite3", "curses", "distutils",
    "tkinter.test", "test", "multiprocessing.dummy",
]

a = Analysis(
    ["../run.py"],
    pathex=[ROOT],
    binaries=[],
    datas=collect_data_files("pptx"),     # python-pptx 기본 템플릿
    hiddenimports=["pypdf", "pymupdf", "pptx"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
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
    name="EasySaving",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,              # 검은 콘솔 창 없이 실행
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if USE_ICON else None,
    version=VERSION_FILE if sys.platform.startswith("win") else None,
)
