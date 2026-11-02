"""자동 업데이트 — GitHub Releases 에서 새 버전을 받아 설치한다.

설치 방식별 동작:
  * EasySaving.exe (PyInstaller)  : 릴리스의 EasySaving.exe 를 받아 앱이 꺼진 뒤 바꿔 끼우고 다시 켠다.
  * git 으로 받은 소스 폴더      : git pull 후 다시 켠다.
  * 그 밖의 소스 설치(파이썬 방식) : 릴리스 소스 zip 을 받아 프로그램 파일만 덮어쓰고,
                                    requirements.txt 의 라이브러리를 설치한 뒤 다시 켠다.
설정 파일은 사용자 폴더에 따로 있어서 업데이트해도 그대로 남는다.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field

from .. import APP_ID, APP_VERSION

GITHUB_REPO = "mannnnnnnngo/EasySaving"
API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_ASSET = "EasySaving.exe"
CHECK_INTERVAL_SEC = 24 * 3600
TIMEOUT = 15

# 소스 설치에서 업데이트할 때 덮어쓰는 것들 (사용자 파일·가상환경은 건드리지 않는다)
SOURCE_ITEMS = ("easysaving", "run.py", "requirements.txt", "assets", "build", "README.md")


@dataclass
class Release:
    version: str
    tag: str
    notes: str = ""
    exe_url: str = ""
    zip_url: str = ""
    page_url: str = ""
    assets: dict = field(default_factory=dict)


class UpdateError(Exception):
    pass


def parse_version(text):
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) + (0,) * (3 - len(nums[:3]))


def is_newer(remote, local=APP_VERSION):
    return parse_version(remote) > parse_version(local)


def fetch_latest(timeout=TIMEOUT):
    """가장 최근 릴리스 정보를 돌려준다. 실패하면 UpdateError."""
    req = urllib.request.Request(API_LATEST, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_ID}/{APP_VERSION}",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise UpdateError(f"업데이트 정보를 가져오지 못했습니다. ({exc})")
    tag = data.get("tag_name") or ""
    assets = {a.get("name"): a.get("browser_download_url") for a in data.get("assets", [])}
    return Release(
        version=tag.lstrip("vV"), tag=tag, notes=(data.get("body") or "").strip(),
        exe_url=assets.get(EXE_ASSET, ""), zip_url=data.get("zipball_url") or "",
        page_url=data.get("html_url") or "", assets=assets,
    )


def check(timeout=TIMEOUT):
    """새 버전이 있으면 Release, 없으면 None."""
    release = fetch_latest(timeout)
    return release if release.version and is_newer(release.version) else None


def due_for_auto_check(settings):
    return settings.auto_update_check and (
        time.time() - float(settings.last_update_check or 0) >= CHECK_INTERVAL_SEC)


# --- 설치 ---------------------------------------------------------------------


def install_kind():
    if getattr(sys, "frozen", False):
        return "exe"
    if os.path.isdir(os.path.join(app_root(), ".git")):
        return "git"
    return "source"


def app_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def apply(release, on_status=None):
    """업데이트를 내려받아 설치 준비까지 한다.

    돌려주는 값: 앱을 끈 직후 실행할 재시작 함수. 호출하는 쪽은 이 함수를 부르고 앱을 종료한다.
    """
    say = on_status or (lambda _msg: None)
    kind = install_kind()
    if kind == "exe":
        return _apply_exe(release, say)
    if kind == "git":
        return _apply_git(say)
    return _apply_source(release, say)


def _download(url, dest, say, label):
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_ID}/{APP_VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                fp.write(chunk)
                done += len(chunk)
                if total:
                    say(f"{label} 받는 중… {done * 100 // total}%")
    except Exception as exc:
        raise UpdateError(f"{label}을(를) 내려받지 못했습니다. ({exc})")


def _apply_exe(release, say):
    if not release.exe_url:
        raise UpdateError("이 릴리스에는 EasySaving.exe 가 없습니다.")
    exe = sys.executable
    new_exe = exe + ".new"
    _download(release.exe_url, new_exe, say, "새 버전")
    if os.path.getsize(new_exe) < 1_000_000:
        os.remove(new_exe)
        raise UpdateError("받은 파일이 올바르지 않습니다.")

    # 배치 파일 없이 교체한다 (숨은 cmd 로 exe 를 바꿔 끼우는 방식은 백신이 의심한다).
    # 윈도우는 실행 중인 exe 의 '이름 바꾸기' 는 허용하므로:
    #   지금 exe → EasySaving.exe.old,  받은 파일 → EasySaving.exe,  새 exe 실행 후 종료.
    # 남은 .old 파일은 새 버전이 켜질 때 cleanup_old_exe() 가 지운다.
    old_exe = exe + ".old"
    try:
        if os.path.exists(old_exe):
            os.remove(old_exe)
        os.replace(exe, old_exe)
        os.replace(new_exe, exe)
    except OSError as exc:
        try:
            if not os.path.exists(exe) and os.path.exists(old_exe):
                os.replace(old_exe, exe)      # 되돌리기
        except OSError:
            pass
        raise UpdateError(f"프로그램 파일을 바꾸지 못했습니다. ({exc})")

    def restart():
        subprocess.Popen([exe], cwd=os.path.dirname(exe), close_fds=True)
    return restart


def cleanup_old_exe():
    """업데이트 뒤 남은 EasySaving.exe.old 를 지운다 (앱 시작 시 호출)."""
    if not getattr(sys, "frozen", False):
        return
    old_exe = sys.executable + ".old"
    for _ in range(10):                    # 이전 프로세스가 막 꺼지는 중일 수 있다
        try:
            if os.path.exists(old_exe):
                os.remove(old_exe)
            return
        except OSError:
            time.sleep(0.5)


def _apply_git(say):
    say("git pull 하는 중…")
    root = app_root()
    try:
        out = subprocess.run(["git", "-C", root, "pull", "--ff-only"], capture_output=True,
                             text=True, timeout=120, **_no_window())
    except Exception as exc:
        raise UpdateError(f"git 을 실행하지 못했습니다. ({exc})")
    if out.returncode != 0:
        raise UpdateError("git pull 에 실패했습니다.\n" + (out.stderr or out.stdout).strip()[-400:])
    _install_requirements(root, say)
    return _restart_python(root)


def _apply_source(release, say):
    if not release.zip_url:
        raise UpdateError("이 릴리스에는 소스 파일이 없습니다.")
    root = app_root()
    tmp = tempfile.mkdtemp(prefix="easysaving_update_")
    try:
        archive = os.path.join(tmp, "src.zip")
        _download(release.zip_url, archive, say, "새 버전")
        say("압축 푸는 중…")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(os.path.join(tmp, "x"))
        tops = os.listdir(os.path.join(tmp, "x"))
        src_root = os.path.join(tmp, "x", tops[0]) if len(tops) == 1 else os.path.join(tmp, "x")
        if not os.path.isfile(os.path.join(src_root, "easysaving", "__init__.py")):
            raise UpdateError("받은 파일에 프로그램이 들어 있지 않습니다.")
        say("파일 바꾸는 중…")
        for item in SOURCE_ITEMS:
            src = os.path.join(src_root, item)
            dst = os.path.join(root, item)
            if not os.path.exists(src):
                continue
            if os.path.isdir(src):
                if item == "easysaving" and os.path.isdir(dst):
                    shutil.rmtree(dst, ignore_errors=True)   # 지워진 파일이 남지 않게
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _install_requirements(root, say)
    return _restart_python(root)


def _python_console():
    """pythonw.exe 로 실행 중이어도 pip 은 python.exe 로 돌린다."""
    exe = sys.executable
    if os.name == "nt" and os.path.basename(exe).lower() == "pythonw.exe":
        candidate = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(candidate):
            return candidate
    return exe


def _install_requirements(root, say):
    req = os.path.join(root, "requirements.txt")
    if not os.path.isfile(req):
        return
    say("필요한 라이브러리 설치 중…")
    try:
        out = subprocess.run([_python_console(), "-m", "pip", "install", "--quiet", "-r", req],
                             capture_output=True, text=True, timeout=600, **_no_window())
    except Exception as exc:
        raise UpdateError(f"라이브러리를 설치하지 못했습니다. ({exc})")
    if out.returncode != 0:
        raise UpdateError("라이브러리를 설치하지 못했습니다.\n" + (out.stderr or "").strip()[-400:])


def _restart_python(root):
    def restart():
        subprocess.Popen([sys.executable, os.path.join(root, "run.py")], cwd=root,
                         close_fds=True, **_no_window())
    return restart


def _no_window():
    if os.name == "nt":
        return {"creationflags": 0x08000000}
    return {}
