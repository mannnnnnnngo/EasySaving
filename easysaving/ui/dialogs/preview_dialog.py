"""저장하기 직전 미리보기 — '이렇게 저장할까요?'

어떤 폴더가 생기고, 어떤 이름의 파일이 몇 개 만들어지는지 저장 전에 보여준다.
페이지 수를 세려면 PDF 를 열어야 해서 시간이 걸릴 수 있으므로,
세는 일은 워커 스레드에서 하고 UI 는 큐를 after() 로 확인해 한 줄씩 채운다.
"""

import os
import queue
import threading
import tkinter as tk

from .. import theme
from ..widgets import Modal, SoftButton, Toggle, scroll_area
from ...services import split_service

POLL_MS = 60
MAX_ROWS = 60        # 이보다 많이 고르면 앞의 것만 보여주고 나머지는 숫자로 요약


def confirm_split(master, job, settings=None):
    """미리보기 창을 띄운다. 저장하기를 누르면 True, 취소/닫기면 None."""
    return PreviewDialog(master, job, settings).show()


class PreviewDialog(Modal):
    def __init__(self, master, job, settings=None):
        super().__init__(master, "이렇게 저장할까요?", width=620)
        self.job = job
        self.settings = settings
        self.events = queue.Queue()
        self._cancel = threading.Event()
        self._pages_total = 0
        self._counted = 0
        self._errors = 0

        sources = list(job.sources)
        self.shown = sources[:MAX_ROWS]
        hidden = len(sources) - len(self.shown)

        self.summary = tk.Label(self.body, text=self._summary_text(len(sources)),
                                bg=theme.BG, fg=theme.MUTED, font=theme.font(12),
                                anchor="w", justify="left")
        self.summary.pack(fill="x")

        rows_height = min(300, 84 * len(self.shown) + 6)
        holder = tk.Frame(self.body, bg=theme.BG)
        holder.pack(fill="both", expand=True, pady=(12, 0))
        list_frame = scroll_area(holder, height=rows_height)

        self.rows = [_PreviewRow(list_frame, path) for path in self.shown]
        if hidden > 0:
            tk.Label(list_frame, text=f"… 그 밖에 {hidden}개", bg=theme.BG, fg=theme.MUTED,
                     font=theme.font(11), anchor="w").pack(fill="x", pady=(8, 0))

        if settings is not None:
            self.skip = Toggle(self.body, "다음부터는 이 창을 건너뛰기 (설정에서 다시 켤 수 있어요)",
                               value=False, font=theme.font(11))
            self.skip.pack(fill="x", pady=(12, 0))
        else:
            self.skip = None

        self.ok = SoftButton(self.footer, "저장하기", command=self._confirm)
        self.ok.pack(side="right")
        SoftButton(self.footer, "취소", kind="ghost",
                   command=self.close).pack(side="right", padx=(0, 8))

        self._height = 300 + rows_height + (30 if settings is not None else 0)
        self.bind("<Return>", lambda _e: self._confirm())
        self._start_counting()

    # --- 페이지 수 세기 ------------------------------------------------------

    def _start_counting(self):
        import dataclasses

        preview_job = dataclasses.replace(self.job, sources=self.shown)

        def work():
            split_service.preview_job(
                preview_job,
                on_item=lambda index, item: self.events.put((index, item)),
                is_cancelled=self._cancel.is_set,
            )
            self.events.put(None)

        threading.Thread(target=work, daemon=True).start()
        self.after(POLL_MS, self._poll)

    def _poll(self):
        finished = False
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event is None:
                finished = True
                break
            index, item = event
            self._apply(index, item)
        if not finished and self.winfo_exists():
            self.after(POLL_MS, self._poll)

    def _apply(self, index, item):
        if index < len(self.rows):
            self.rows[index].fill(item)
        self._counted += 1
        self._pages_total += item.pages
        if item.error:
            self._errors += 1
        self.summary.config(text=self._summary_text(len(self.job.sources)))

    def _summary_text(self, total_files):
        if self._counted == 0:
            return f"PDF {total_files}개를 살펴보는 중이에요…"
        head = f"PDF {total_files}개 · 총 {self._pages_total}쪽 → 파일 {self._pages_total}개가 만들어져요."
        if self._counted < len(self.shown):
            return head + "  (세는 중…)"
        if self._errors:
            return head + f"  ⚠️ {self._errors}개는 저장할 수 없어요 (건너뜁니다)."
        return head

    # --- 마무리 -------------------------------------------------------------

    def _confirm(self):
        if self.skip is not None and self.skip.get():
            self.settings.preview_before_save = False
        self._cancel.set()
        self.done(True)

    def close(self, result=None):
        self._cancel.set()
        super().close(result)


class _PreviewRow(tk.Frame):
    """원본 PDF 한 개 = 만들어질 폴더 이름 + 파일 이름 범위."""

    def __init__(self, parent, source):
        super().__init__(parent, bg=theme.BORDER)
        self.pack(fill="x", pady=(0, 6))
        inner = tk.Frame(self, bg=theme.CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(inner, text=f"📄 {os.path.basename(source)}", bg=theme.CARD, fg=theme.TEXT,
                 font=theme.font(12, "bold"), anchor="w").pack(fill="x", padx=14, pady=(11, 2))
        self.folder = tk.Label(inner, text="", bg=theme.CARD, fg=theme.MUTED,
                               font=theme.font(10), anchor="w", justify="left")
        self.folder.pack(fill="x", padx=14)
        self.detail = tk.Label(inner, text="쪽수를 세는 중…", bg=theme.CARD, fg=theme.MUTED,
                               font=theme.font(11), anchor="w", justify="left")
        self.detail.pack(fill="x", padx=14, pady=(2, 11))

    def fill(self, item):
        self.folder.config(text="📁 " + _short(item.folder))
        if item.error:
            self.detail.config(text=f"⚠️ {item.error}", fg=theme.DANGER)
        elif item.pages == 1:
            self.detail.config(text=f"{item.first_name}  (1개)", fg=theme.TEXT)
        elif item.pages == 2:
            self.detail.config(text=f"{item.first_name} · {item.last_name}  (2개)", fg=theme.TEXT)
        else:
            self.detail.config(text=f"{item.first_name} … {item.last_name}  ({item.pages}개)",
                               fg=theme.TEXT)


def _short(path, limit=64):
    path = path.replace(os.path.expanduser("~"), "~")
    return path if len(path) <= limit else "…" + path[-(limit - 1):]
