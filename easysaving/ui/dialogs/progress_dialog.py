"""분할 진행 창."""

import os
import tkinter as tk
from tkinter import ttk

from .. import theme
from ..widgets import Modal, SoftButton


class ProgressDialog(Modal):
    def __init__(self, master, on_cancel, title="저장하는 중…"):
        super().__init__(master, title, width=470, closable=False)
        self.on_cancel = on_cancel

        self.file_label = tk.Label(self.body, text="준비하는 중…", bg=theme.BG, fg=theme.TEXT,
                                   font=theme.font(13, "bold"), anchor="w")
        self.file_label.pack(fill="x")
        self.page_label = tk.Label(self.body, text="", bg=theme.BG, fg=theme.MUTED,
                                   font=theme.font(11), anchor="w")
        self.page_label.pack(fill="x", pady=(4, 10))

        self.bar = ttk.Progressbar(self.body, mode="determinate", maximum=100, length=420)
        self.bar.pack(fill="x")

        self.folder_label = tk.Label(self.body, text="", bg=theme.BG, fg=theme.MUTED,
                                     font=theme.font(10), anchor="w")
        self.folder_label.pack(fill="x", pady=(10, 0))

        self.cancel_button = SoftButton(self.footer, "취소", kind="ghost", command=self._cancel)
        self.cancel_button.pack(side="right")

        self.center_on()
        self.transient(master)
        self.lift()
        try:
            self.grab_set()
        except Exception:
            pass

    def _cancel(self):
        self.cancel_button.set_text("취소하는 중…")
        self.cancel_button.set_enabled(False)
        self.on_cancel()

    def set_file(self, index, total, filename, folder):
        prefix = f"[{index}/{total}] " if total > 1 else ""
        self.file_label.config(text=f"{prefix}{filename}")
        self.folder_label.config(text=f"저장 폴더: {os.path.basename(folder)}")
        self.bar.config(value=0)

    def set_page(self, page, pages, verb="저장"):
        self.page_label.config(text=f"{page} / {pages} 장 {verb} 완료")
        self.bar.config(value=(page / pages) * 100 if pages else 0)

    def finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
