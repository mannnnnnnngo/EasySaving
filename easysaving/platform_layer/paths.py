"""OS 별 경로: 데스크탑, 설정 폴더, 폴더 열기."""

import os
import subprocess
import sys

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")


def desktop_dir():
    """사용자의 데스크탑 경로. (윈도우에서 OneDrive 로 옮겨진 경우도 처리)"""
    home = os.path.expanduser("~")
    if IS_WIN:
        path = _windows_desktop()
        if path:
            return path
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "바탕 화면"),
        os.path.join(home, "바탕화면"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "바탕 화면"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return home


def _windows_desktop():
    """레지스트리에 등록된 실제 데스크탑 경로를 읽는다 (OneDrive 리다이렉트 대응)."""
    try:
        import ctypes
        import ctypes.wintypes as wintypes

        CSIDL_DESKTOPDIRECTORY = 0x0010
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        result = ctypes.windll.shell32.SHGetFolderPathW(
            None, CSIDL_DESKTOPDIRECTORY, None, SHGFP_TYPE_CURRENT, buf
        )
        if result == 0 and buf.value and os.path.isdir(buf.value):
            return buf.value
    except Exception:
        pass
    return None


def config_dir():
    """설정 파일을 둘 폴더. 없으면 만든다."""
    from .. import APP_ID

    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_ID)
    elif IS_MAC:
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_ID)
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        path = os.path.join(base, APP_ID)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.expanduser("~")
    return path


def config_path():
    return os.path.join(config_dir(), "config.json")


def reveal(path):
    """탐색기/파인더로 해당 폴더를 연다."""
    try:
        if IS_WIN:
            os.startfile(path)  # noqa: S606  (윈도우 전용 API)
        elif IS_MAC:
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def can_write(path):
    """해당 폴더에 실제로 쓸 수 있는지 시험해 본다 (권한 확인용)."""
    probe = os.path.join(path, ".easysaving_write_test")
    try:
        os.makedirs(path, exist_ok=True)
        with open(probe, "w") as fp:
            fp.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False
