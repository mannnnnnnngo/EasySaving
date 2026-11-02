"""앱 시작점 (PyInstaller 진입점이기도 함).

  개발 중 실행:  python run.py
  창 없이 실행:  EasySaving.pyw 더블클릭 (pythonw 로 열림)
  빌드:          build\\build_windows.bat
"""

import os
import sys


def _relaunch_without_console():
    """윈도우에서 python.exe 로 켜져 콘솔 창(검은/파란 터미널)이 따라 떴으면,
    창 없는 pythonw.exe 로 다시 켜고 지금 프로세스는 바로 끝낸다 → 콘솔 창이 사라진다.

    run.py 를 더블클릭하거나 .bat 으로 켰을 때 생기는 문제다. 콘솔을 이 앱만 쓰고 있을 때만
    (venv 의 python.exe 런처 포함 2개 이하) 동작하고, 개발자가 터미널에서 직접 실행한
    경우(셸까지 3개 이상)는 그대로 둔다.
    """
    if os.name != "nt" or getattr(sys, "frozen", False) or os.environ.get("EASYSAVING_CONSOLE"):
        return
    try:
        import ctypes
        import subprocess

        kernel32 = ctypes.windll.kernel32
        if not kernel32.GetConsoleWindow():
            return                                   # 이미 창 없이 실행 중 (pythonw)
        pids = (ctypes.c_uint * 8)()
        if kernel32.GetConsoleProcessList(pids, 8) > 2:
            return                                   # 터미널에서 직접 실행함
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            return
        script = os.path.abspath(__file__)
        subprocess.Popen([pythonw, script] + sys.argv[1:], cwd=os.path.dirname(script),
                         creationflags=0x00000008 | 0x00000200,   # DETACHED | NEW_PROCESS_GROUP
                         close_fds=True)
    except Exception:
        return
    os._exit(0)


if __name__ == "__main__":
    _relaunch_without_console()

# PyInstaller 로 묶였을 때도 패키지를 찾을 수 있게
if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from easysaving.main import main  # noqa: E402

if __name__ == "__main__":
    main()
