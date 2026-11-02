"""composition root — 레이어들을 실제로 이어 붙이는 곳."""

import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog

from . import APP_NAME, APP_VERSION
from .core.models import SAVE_SEPARATE
from .platform_layer import paths
from .services import convert_service, split_service, update_service
from .services.convert_service import ConvertService
from .services.config_service import ConfigService
from .services.split_service import SplitService
from .ui import theme
from .ui.floating_button import FloatingButton
from .ui.menu import DropdownMenu
from .ui.dialogs import message, preview_dialog, save_mode_dialog, tutorial
from .ui.dialogs.progress_dialog import ProgressDialog
from .ui.dialogs.settings_dialog import open_settings

POLL_MS = 70            # 진행 상황 큐를 확인하는 주기
PDF_TYPES = [("PDF 파일", "*.pdf"), ("모든 파일", "*.*")]


class App:
    def __init__(self):
        self.config = ConfigService()
        self.settings = self.config.load()
        self.splitter = SplitService()
        self.converter = ConvertService()
        self.progress = None
        self._last_root_folder = None
        self._busy = False
        self._pending_errors = []

        # 루트는 숨겨 두고, 화면에 보이는 버튼은 자식 창으로 만든다.
        # (루트를 overrideredirect 로 쓰면 macOS 에서 다이얼로그가 뜨지 않는다)
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        _hide_root(self.root)

        self.window = FloatingButton(self.root, self.settings,
                                     on_save=self.on_save, on_menu=self.on_menu)
        self.window.set_move_callback(self.config.save)

        threading.Thread(target=update_service.cleanup_old_exe, daemon=True).start()
        if tutorial.should_show(self.settings):
            self.root.after(350, self.show_tutorial)
        elif update_service.due_for_auto_check(self.settings):
            self.root.after(4000, self._auto_update_check)

    def run(self):
        self.root.mainloop()

    # --- 메뉴 ---------------------------------------------------------------

    def on_menu(self):
        DropdownMenu(self.root, [
            ("🗂", "여러 파일 저장하기", "PDF 여러 개를 한 번에", self.on_save_multiple),
            ("📊", "PowerPoint 로 바꾸기", "PDF → .pptx (여러 개 가능)", self.on_convert_pptx),
            None,
            ("⚙️", "설정", "색 · 크기 · 조합키 · 저장 위치", self.open_settings),
            ("📘", "튜토리얼 다시 보기", "사용법과 권한 안내", self.show_tutorial),
            ("🔄", "업데이트 확인", f"지금 버전 {APP_VERSION}", self.check_updates),
            None,
            ("✕", "종료", "", self.quit),
        ], anchor_widget=self.window)

    def show_tutorial(self):
        tutorial.run_tutorial(self.root, self.settings, on_settings_saved=self.config.save)
        self.config.save()

    def open_settings(self):
        def live_apply(settings):
            self.window.apply_settings(settings)

        open_settings(self.root, self.settings, on_change=live_apply)
        self.window.apply_settings(self.settings)
        self.config.save()

    def quit(self):
        self.config.save()
        try:
            self.root.destroy()
        except Exception:
            pass

    # --- 저장 흐름 -----------------------------------------------------------

    def on_save(self):
        if self._guard_busy():
            return
        path = self._ask_single_file()
        if not path:
            return
        self._start([path], SAVE_SEPARATE, "")

    def on_save_multiple(self):
        if self._guard_busy():
            return
        paths_picked = filedialog.askopenfilenames(
            parent=self.root, title="나눌 PDF 를 여러 개 고르세요 (Ctrl/⌘ + 클릭)",
            filetypes=PDF_TYPES, initialdir=self._initial_dir(),
        )
        sources = [p for p in (paths_picked or []) if p]
        if not sources:
            return
        if len(sources) == 1:
            self._start(sources, SAVE_SEPARATE, "")
            return
        choice = save_mode_dialog.choose_save_mode(
            self.root, sources, desktop_name=_desktop_label())
        if not choice:
            return
        mode, parent_folder = choice
        self._start(sources, mode, parent_folder)

    def _ask_single_file(self):
        return filedialog.askopenfilename(
            parent=self.root, title="나눌 PDF 를 고르세요",
            filetypes=PDF_TYPES, initialdir=self._initial_dir(),
        )

    def _initial_dir(self):
        return self.settings.output_root or paths.desktop_dir()

    def _guard_busy(self):
        if self._busy or self.splitter.busy or self.converter.busy:
            self.window.flash("작업 중이에요")
            return True
        return False

    # --- 작업 실행 -----------------------------------------------------------

    def _start(self, sources, mode, parent_folder):
        root = self.settings.output_root or paths.desktop_dir()
        if not paths.can_write(root):
            message.error(
                self.root, "저장할 수 없어요",
                f"{root} 에 폴더를 만들 권한이 없습니다.",
                "설정 > 저장 위치 에서 다른 폴더를 고르거나, OS 권한 설정에서 폴더 접근을 허용해 주세요.",
            )
            return

        job = split_service.build_job(sources, self.settings, mode, parent_folder)

        if self.settings.preview_before_save:
            if not preview_dialog.confirm_split(self.root, job, self.settings):
                return
            self.config.save()      # '다음부터 건너뛰기' 를 눌렀을 수 있다

        self._busy = True
        self.window.set_busy("저장 중…")
        self.progress = ProgressDialog(self.root, on_cancel=self.splitter.cancel)
        self.splitter.start(job)
        self.root.after(POLL_MS, lambda: self._poll(self.splitter.events, self._handle_event))

    def _poll(self, events, handler):
        finished = False
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                break
            finished = handler(event) or finished
        if not finished:
            self.root.after(POLL_MS, lambda: self._poll(events, handler))

    def _handle_event(self, event):
        kind = event[0]
        if kind == split_service.EV_FILE_START:
            _, index, total, filename, folder = event
            if self.progress:
                self.progress.set_file(index, total, filename, folder)
        elif kind == split_service.EV_PAGE:
            _, page, pages, _name = event
            if self.progress:
                self.progress.set_page(page, pages)
        elif kind == split_service.EV_ERROR:
            _, filename, msg, detail = event
            self._pending_errors.append((filename, msg, detail))
        elif kind == split_service.EV_DONE:
            _, results, root_folder = event
            self._finish(results, root_folder, cancelled=False)
            return True
        elif kind == split_service.EV_CANCELLED:
            _, results = event
            self._finish(results, None, cancelled=True)
            return True
        return False

    def _finish(self, results, root_folder, cancelled):
        self._busy = False
        self.window.set_busy(None)
        if self.progress:
            self.progress.finish()
            self.progress = None

        errors = list(self._pending_errors)
        self._pending_errors = []

        if cancelled:
            self.window.flash("취소했어요")
            return

        succeeded = [r for r in results if not r.error]
        if not succeeded:
            first = errors[0] if errors else ("", "저장하지 못했습니다.", "")
            message.error(self.root, "저장하지 못했어요", first[1], first[2])
            return

        folder_to_open = (succeeded[0].folder if len(succeeded) == 1 else root_folder)
        self._last_root_folder = folder_to_open

        if self.settings.open_folder_when_done:
            paths.reveal(folder_to_open)
        message.completed(self.root, results, folder_to_open)


    # --- PowerPoint 변환 -----------------------------------------------------

    def on_convert_pptx(self):
        if self._guard_busy():
            return
        picked = filedialog.askopenfilenames(
            parent=self.root, title="PowerPoint 로 바꿀 PDF 를 고르세요 (여러 개 가능)",
            filetypes=PDF_TYPES, initialdir=self._initial_dir(),
        )
        sources = [p for p in (picked or []) if p]
        if not sources:
            return
        out_dir = self.settings.output_root or paths.desktop_dir()
        if not paths.can_write(out_dir):
            message.error(self.root, "저장할 수 없어요", f"{out_dir} 에 저장할 권한이 없습니다.",
                          "설정 > 저장 위치 에서 다른 폴더를 골라 주세요.")
            return
        mode = (convert_service.MODE_EDITABLE if self.settings.pptx_editable
                else convert_service.MODE_IMAGE)
        self._busy = True
        self.window.set_busy("변환 중…")
        self.progress = ProgressDialog(self.root, on_cancel=self.converter.cancel,
                                       title="PowerPoint 로 바꾸는 중…")
        self.converter.start(sources, out_dir, mode)
        self.root.after(POLL_MS, lambda: self._poll(self.converter.events, self._handle_convert))

    def _handle_convert(self, event):
        kind = event[0]
        if kind == convert_service.EV_FILE_START:
            _, index, total, filename, out_path = event
            if self.progress:
                self.progress.set_file(index, total, filename, out_path)
                self.progress.folder_label.config(text=f"만들 파일: {os.path.basename(out_path)}")
        elif kind == convert_service.EV_PAGE:
            _, page, pages = event
            if self.progress:
                self.progress.set_page(page, pages, verb="변환")
        elif kind == convert_service.EV_ERROR:
            _, filename, msg, detail = event
            self._pending_errors.append((filename, msg, detail))
        elif kind in (convert_service.EV_DONE, convert_service.EV_CANCELLED):
            self._finish_convert(event[1], cancelled=kind == convert_service.EV_CANCELLED)
            return True
        return False

    def _finish_convert(self, results, cancelled):
        self._busy = False
        self.window.set_busy(None)
        if self.progress:
            self.progress.finish()
            self.progress = None
        errors, self._pending_errors = self._pending_errors, []
        if cancelled:
            self.window.flash("취소했어요")
            return
        ok = [r for r in results if not r.error]
        if not ok:
            first = errors[0] if errors else ("", "변환하지 못했습니다.", "")
            message.error(self.root, "PowerPoint 로 바꾸지 못했어요", first[1], first[2])
            return
        if self.settings.open_folder_when_done:
            paths.reveal(os.path.dirname(ok[0].output))
        names = "\n".join(f"📊 {os.path.basename(r.output)}  ({r.pages}장)" for r in ok[:6])
        if len(ok) > 6:
            names += f"\n… 외 {len(ok) - 6}개"
        detail = f"저장 위치: {os.path.dirname(ok[0].output)}"
        failed = [r for r in results if r.error]
        if failed:
            detail += f"\n⚠️ {len(failed)}개 실패: " + ", ".join(
                f"{os.path.basename(r.source)} ({r.error})" for r in failed[:3])
        message.info(self.root, "PowerPoint 로 바꿨어요", names, detail)

    # --- 업데이트 -----------------------------------------------------------

    def _auto_update_check(self):
        if self._busy:
            return
        self.settings.last_update_check = time.time()
        self.config.save()
        self._check_in_background(silent=True)

    def check_updates(self):
        self.window.flash("새 버전 확인 중…")
        self._check_in_background(silent=False)

    def _run_in_background(self, work, on_done, on_tick=None):
        """work() 를 스레드에서 돌리고, 끝나면 UI 스레드에서 on_done(결과, 오류) 를 부른다."""
        box = {}

        def runner():
            try:
                box["result"] = work()
            except update_service.UpdateError as exc:
                box["error"] = str(exc)
            except Exception as exc:
                box["error"] = f"문제가 생겼습니다. ({exc})"

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

        def wait():
            if on_tick:
                on_tick()
            if thread.is_alive():
                self.root.after(150, wait)
            else:
                on_done(box.get("result"), box.get("error"))

        self.root.after(150, wait)

    def _check_in_background(self, silent):
        def done(release, error):
            if error:
                if not silent:
                    message.error(self.root, "업데이트 확인 실패", error,
                                  "인터넷 연결을 확인하고 다시 시도해 주세요.")
            elif release:
                self._offer_update(release)
            elif not silent:
                message.info(self.root, "최신 버전이에요", f"지금 쓰는 {APP_VERSION} 이 최신입니다.")

        self._run_in_background(update_service.check, done)

    def _offer_update(self, release):
        notes = release.notes[:500] if release.notes else ""
        if not message.confirm(self.root, "새 버전이 나왔어요",
                               f"{APP_VERSION} → {release.version} 로 업데이트할까요?",
                               notes, ok="지금 업데이트", cancel="나중에"):
            return
        if self._guard_busy():
            return
        self._busy = True
        self.window.set_busy("업데이트 중…")
        status = queue.Queue()

        def tick():
            last = None
            while True:
                try:
                    last = status.get_nowait()
                except queue.Empty:
                    break
            if last:
                self.window.set_busy(last[:16])

        def done(restart, error):
            self._busy = False
            self.window.set_busy(None)
            if error:
                message.error(self.root, "업데이트하지 못했어요", error)
                return
            message.info(self.root, "업데이트 완료",
                         f"{release.version} 을(를) 설치했어요. 확인을 누르면 다시 켜집니다.")
            self.quit()
            restart()

        self._run_in_background(lambda: update_service.apply(release, on_status=status.put),
                                done, on_tick=tick)


def _hide_root(root):
    """루트 창은 화면에 절대 보이지 않게 한다.

    withdraw() 만으로는 macOS 에서 작은 빈 창이 왼쪽 위 구석에 남는 경우가 있어,
    크기를 1x1 로 줄이고 화면 밖으로 보낸 뒤 투명하게까지 만들어 둔다.
    (자식 창인 다이얼로그·플로팅 버튼에는 영향이 없다)
    """
    root.withdraw()
    try:
        root.geometry("1x1+-10000+-10000")
    except tk.TclError:
        pass
    try:
        root.attributes("-alpha", 0.0)
    except tk.TclError:
        pass


def _desktop_label():
    return "바탕 화면" if theme.IS_WIN else "데스크탑"


def _cli_to_pptx(args):
    """명령줄 변환:  EasySaving.exe --to-pptx 입력.pdf [출력.pptx] [--image]"""
    from .core import pdf_to_pptx
    from .core.errors import EasySavingError

    mode = "image" if "--image" in args else "editable"
    files = [a for a in args if not a.startswith("--")]
    if not files:
        print("사용법: --to-pptx 입력.pdf [출력.pptx] [--image]")
        return 2
    src = files[0]
    out = files[1] if len(files) > 1 else pdf_to_pptx.default_output_path(src)
    try:
        pdf_to_pptx.convert_pdf_to_pptx(src, out, mode=mode)
    except EasySavingError as exc:
        print(f"오류: {exc.message} {exc.detail}")
        return 1
    print(out)
    return 0


def main():
    if "--to-pptx" in sys.argv[1:]:
        raise SystemExit(_cli_to_pptx([a for a in sys.argv[1:] if a != "--to-pptx"]))
    try:
        App().run()
    except KeyboardInterrupt:
        pass
    except tk.TclError as exc:
        # 화면(디스플레이)이 없는 환경 등
        print(f"[{APP_NAME}] 창을 열 수 없습니다: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
