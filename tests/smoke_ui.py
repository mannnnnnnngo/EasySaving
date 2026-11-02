"""UI 스모크 테스트 — 실제 창을 띄워 모든 화면을 한 번씩 열고 닫는다.

실행: python3 -m tests.smoke_ui  (창이 잠깐씩 떴다 사라집니다)
"""

import os
import sys
import tempfile
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# macOS 시스템 Tk 8.5 버그 회피용 (투명 창 + update()). 윈도우/Tk 8.6 에는 영향 없음.
os.environ["EASYSAVING_NO_TRANSPARENT"] = "1"

from easysaving.main import App                                   # noqa: E402
from easysaving.platform_layer import memory                      # noqa: E402
from easysaving.services.config_service import ConfigService      # noqa: E402
from easysaving.ui.dialogs import message, save_mode_dialog, tutorial  # noqa: E402
from easysaving.ui.dialogs.preview_dialog import PreviewDialog    # noqa: E402
from easysaving.ui.dialogs.progress_dialog import ProgressDialog  # noqa: E402
from easysaving.ui.dialogs.settings_dialog import SettingsDialog  # noqa: E402
from easysaving.ui.menu import DropdownMenu                       # noqa: E402

errors = []
log = []


def step(label):
    def wrapper(fn):
        def run():
            print(f"  … {label}", flush=True)
            try:
                fn()
                log.append(f"  ✓ {label}")
                print(f"  ✓ {label}", flush=True)
            except Exception as exc:  # noqa: BLE001
                errors.append((label, exc))
                log.append(f"  ✗ {label} — {type(exc).__name__}: {exc}")
                print(f"  ✗ {label} — {type(exc).__name__}: {exc}", flush=True)
        run.__name__ = fn.__name__
        return run
    return wrapper


def watchdog(seconds=90):
    """어떤 창이 멈춰도 테스트가 영원히 붙잡히지 않게 한다."""
    import threading

    def kill():
        print(f"\n[watchdog] {seconds}초 안에 끝나지 않아 강제 종료합니다.", flush=True)
        os._exit(2)

    timer = threading.Timer(seconds, kill)
    timer.daemon = True
    timer.start()


def _make_pdf(path, pages):
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)   # A4
    with open(path, "wb") as fp:
        writer.write(fp)
    return path


def close_tops(root, keep=None):
    """열려 있는 Toplevel 을 닫는다 (플로팅 버튼은 남긴다)."""
    for child in list(root.winfo_children()):
        if isinstance(child, tk.Toplevel) and child is not keep:
            try:
                child.grab_release()
            except Exception:
                pass
            try:
                child.destroy()
            except Exception:
                pass


def main():
    watchdog(90)
    print("UI 스모크 테스트 시작", flush=True)

    # 실제 설정 파일을 건드리지 않도록 임시 경로 사용 + 자동 튜토리얼은 끄고 시작
    tmp = tempfile.mkdtemp(prefix="easysaving_ui_")
    config_path = os.path.join(tmp, "config.json")
    seed = ConfigService(config_path)
    seed.load()
    seed.settings.tutorial_done = True
    seed.settings.permissions_ack = True
    seed.save()
    ConfigService.__init__.__defaults__ = (config_path,)

    app = App()
    root = app.root          # 숨겨진 루트 (다이얼로그의 부모)
    btn = app.window        # 화면에 보이는 플로팅 버튼
    root.update_idletasks()

    plan = []

    @step("플로팅 버튼 그리기")
    def draw():
        root.update_idletasks()
        width = btn.winfo_width()
        assert width > 80, f"버튼 폭이 이상합니다: {width}"

    @step("버튼 hover / 클릭 영역 계산")
    def zones():
        from easysaving.ui.floating_button import ZONE_DROP, ZONE_MAIN
        assert btn._zone_at(5) == ZONE_MAIN
        assert btn._zone_at(btn.winfo_width() - 5) == ZONE_DROP

    @step("설정 변경 즉시 반영")
    def restyle():
        app.settings.button_color = "#1F9D55"
        app.settings.button_text = "1장씩 저장"
        app.settings.scale = 1.3
        btn.apply_settings(app.settings)
        root.update_idletasks()
        app.settings.button_color = "#2F6FED"
        app.settings.button_text = "저장하기"
        app.settings.scale = 1.0
        btn.apply_settings(app.settings)
        root.update_idletasks()

    @step("드롭다운 메뉴")
    def dropdown():
        menu = DropdownMenu(root, [("🗂", "여러 파일 저장하기", "설명", lambda: None), None,
                                   ("⚙️", "설정", "", lambda: None)], anchor_widget=btn)
        root.update_idletasks()
        menu.close()

    @step("튜토리얼 8단계 전체 이동")
    def tutorial_steps():
        dialog = tutorial.TutorialDialog(root, app.settings)
        dialog.update_idletasks()
        for _ in range(len(dialog.steps) - 1):
            dialog.next()
            dialog.update_idletasks()
        for _ in range(len(dialog.steps) - 1):
            dialog.back()
            dialog.update_idletasks()
        dialog.destroy()

    @step("설정 창 (조합키 녹화 포함)")
    def settings_dialog():
        dialog = SettingsDialog(root, app.settings, on_change=lambda s: None)
        dialog.update_idletasks()
        dialog._start_recording()
        dialog.update_idletasks()
        fake = type("E", (), {"state": 0x10 if sys.platform == "darwin" else 0x20000,
                              "num": 3, "widget": dialog.combo_box})()
        dialog._on_combo_click(fake)
        dialog.update_idletasks()
        dialog._stop_recording()
        dialog.update_idletasks()
        dialog._draw_preview()
        dialog.destroy()

    @step("여러 파일 저장 방식 창")
    def save_mode():
        root.after(150, lambda: close_tops(root, keep=btn))
        save_mode_dialog.choose_save_mode(root, ["/tmp/기안.pdf", "/tmp/보고서.pdf"])

    @step("저장 전 미리보기 창")
    def preview():
        from easysaving.services import split_service

        made = _make_pdf(os.path.join(tmp, "기안.pdf"), pages=3)
        job = split_service.build_job([made, os.path.join(tmp, "없는파일.pdf")],
                                      app.settings, "separate", "")
        dialog = PreviewDialog(root, job, app.settings)
        for _ in range(40):                      # 워커가 다 셀 때까지 폴링
            dialog.update_idletasks()
            dialog._poll()
            if dialog._counted >= 2:
                break
            time.sleep(0.03)
        assert dialog._counted == 2, f"미리보기가 다 세지 못했습니다: {dialog._counted}"
        assert dialog._pages_total == 3, f"쪽수가 이상합니다: {dialog._pages_total}"
        assert dialog._errors == 1, "없는 파일을 오류로 잡지 못했습니다"
        assert dialog.rows[0].detail.cget("text").startswith("기안 - 1.pdf")
        dialog.update_idletasks()
        dialog.close()

    @step("진행 창")
    def progress():
        dialog = ProgressDialog(root, on_cancel=lambda: None)
        dialog.set_file(1, 2, "기안.pdf", "/tmp/기안 저장")
        for page in (1, 60, 124):
            dialog.set_page(page, 124)
            dialog.update_idletasks()
        dialog.finish()

    @step("완료 / 오류 안내 창")
    def messages():
        from easysaving.core.models import SplitResult
        results = [SplitResult("/tmp/기안.pdf", "/tmp/기안 저장", 124, [])]
        root.after(150, lambda: close_tops(root, keep=btn))
        message.completed(root, results, "/tmp/기안 저장")
        root.after(150, lambda: close_tops(root, keep=btn))
        message.error(root, "저장하지 못했어요", "비밀번호가 걸린 PDF 입니다.", "기안.pdf")

    plan = [draw, zones, restyle, dropdown, tutorial_steps, settings_dialog,
            save_mode, preview, progress, messages]

    def run_all():
        for action in plan:
            action()
            close_tops(root, keep=btn)
            root.update_idletasks()
        import gc
        gc.collect()
        print("\n".join(log))
        # 이 프로세스는 12개 화면을 연달아 띄우고 pypdf 까지 올린 '최악의 경우' 값이다.
        # 실제 사용 흐름(시작 → 미리보기 → 분할)은 90MB 안팎.
        print(f"\n메모리 사용량: {memory.rss_mb()}MB (모든 화면 + pypdf 를 한 프로세스에서 연 값)")
        root.destroy()

    root.after(300, run_all)
    root.mainloop()

    if errors:
        print(f"\n실패 {len(errors)}건")
        return 1
    print("\nUI 스모크 테스트 통과 🎉")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
