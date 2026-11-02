"""OS 권한 확인 + 설정 화면 열기.

튜토리얼 마지막 단계에서 이 목록을 그대로 보여 준다.
'required=True' 인 권한이 모두 granted 여야 튜토리얼을 매번 띄우지 않는다.
"""

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List

from . import paths

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

GRANTED = "granted"
DENIED = "denied"
UNKNOWN = "unknown"


@dataclass
class Permission:
    key: str
    name: str
    why: str                     # 왜 필요한지
    how: str                     # 어떻게 켜는지
    status: str = UNKNOWN
    required: bool = True
    settings_url: str = ""       # 설정 화면 바로 열기용
    optional_note: str = ""

    @property
    def ok(self):
        return self.status == GRANTED

    @property
    def badge(self):
        return {GRANTED: "허용됨", DENIED: "필요함", UNKNOWN: "확인 필요"}[self.status]


def check_all() -> List[Permission]:
    """현재 OS 에서 필요한 권한 목록과 상태를 돌려준다."""
    if IS_MAC:
        return _check_mac()
    if IS_WIN:
        return _check_windows()
    return _check_linux()


def all_required_granted(perms=None):
    perms = perms if perms is not None else check_all()
    return all(p.ok for p in perms if p.required)


def open_settings(perm: Permission):
    """OS 설정 화면을 연다."""
    if not perm.settings_url:
        return False
    try:
        if IS_MAC:
            subprocess.Popen(["open", perm.settings_url])
        elif IS_WIN:
            os.startfile(perm.settings_url)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", perm.settings_url])
        return True
    except Exception:
        return False


# --- macOS -------------------------------------------------------------------


def _check_mac():
    desktop = paths.desktop_dir()
    return [
        Permission(
            key="desktop",
            name="데스크탑 폴더 접근",
            why="분할한 PDF 를 데스크탑에 '[제목] 저장' 폴더로 만들어 저장합니다.",
            how="처음 저장할 때 뜨는 '데스크탑 폴더에 접근하려고 합니다' 창에서 [허용] 을 누르세요. "
                "이미 거부했다면 시스템 설정 > 개인정보 보호 및 보안 > 파일 및 폴더 에서 켤 수 있습니다.",
            status=GRANTED if paths.can_write(desktop) else DENIED,
            required=True,
            settings_url="x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders",
        ),
    ]


# --- Windows -----------------------------------------------------------------


def _check_windows():
    desktop = paths.desktop_dir()
    return [
        Permission(
            key="desktop",
            name="바탕 화면 폴더 쓰기",
            why="분할한 PDF 를 바탕 화면에 '[제목] 저장' 폴더로 만들어 저장합니다.",
            how="보통 그냥 됩니다. 회사 PC 처럼 정책이 걸려 있으면 설정 창에서 저장 위치를 다른 폴더로 바꾸세요.",
            status=GRANTED if paths.can_write(desktop) else DENIED,
            required=True,
            settings_url="",
        ),
        Permission(
            key="smartscreen",
            name="설치 허용 (SmartScreen)",
            why="서명되지 않은 설치 파일이라 처음 실행할 때 파란 경고창이 뜰 수 있습니다.",
            how="경고창에서 [추가 정보] > [실행] 을 누르면 됩니다. 설치 후에는 다시 뜨지 않습니다.",
            status=GRANTED,
            required=False,
        ),
    ]


def _check_linux():
    desktop = paths.desktop_dir()
    return [
        Permission(
            key="desktop",
            name="데스크탑 폴더 쓰기",
            why="분할한 PDF 를 저장합니다.",
            how="폴더 쓰기 권한을 확인해 주세요.",
            status=GRANTED if paths.can_write(desktop) else DENIED,
            required=True,
        )
    ]
