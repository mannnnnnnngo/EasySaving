"""여러 파일을 고른 뒤 -- 따로 저장할지, 한 폴더에 모을지 고르는 창."""

import os
import tkinter as tk

from .. import theme
from ..widgets import Modal, OptionCard, SoftButton
from ...core import naming
from ...core.models import SAVE_SEPARATE, SAVE_TOGETHER


def choose_save_mode(master, sources, desktop_name="데스크탑"):
    """(mode, parent_folder) 를 돌려준다. 취소하면 None."""
    dialog = Modal(master, "어떻게 저장할까요?", width=560)
    count = len(sources)
    example = naming.stem_of(sources[0]) if sources else "기안"

    tk.Label(dialog.body, text=f"PDF {count}개를 나눠 저장합니다.",
             bg=theme.BG, fg=theme.MUTED, font=theme.font(12), anchor="w").pack(fill="x")

    body = dialog.body

    OptionCard(
        body, "파일마다 따로 저장",
        f"{desktop_name}에 '{example} 저장' 같은 폴더를 파일 수만큼 만듭니다.",
        lambda: dialog.done((SAVE_SEPARATE, "")), emoji="🗂",
    ).pack(fill="x", pady=(14, 8))

    together_holder = tk.Frame(body, bg=theme.BG)
    together_holder.pack(fill="x")

    card = OptionCard(
        together_holder, "한 폴더에 모아서 저장",
        f"{desktop_name}에 폴더 하나를 만들고, 그 안에 파일별 폴더를 넣습니다.",
        lambda: show_name_input(), emoji="📦",
    )
    card.pack(fill="x")

    name_box = tk.Frame(body, bg=theme.CARD)
    entry_var = tk.StringVar(value=_default_parent_name(sources))

    def show_name_input():
        card.pack_forget()
        name_box.pack(fill="x", pady=(0, 4))
        entry.focus_set()
        entry.select_range(0, "end")
        dialog.center_on()

    tk.Label(name_box, text="모아 둘 폴더 이름", bg=theme.CARD, fg=theme.TEXT,
             font=theme.font(12, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 6))
    entry = tk.Entry(name_box, textvariable=entry_var, font=theme.font(13),
                     relief="flat", bg=theme.BG, fg=theme.TEXT,
                     highlightthickness=1, highlightbackground=theme.BORDER,
                     highlightcolor=theme.ACCENT, insertbackground=theme.TEXT)
    entry.pack(fill="x", padx=16, ipady=7)
    preview = tk.Label(name_box, text="", bg=theme.CARD, fg=theme.MUTED,
                       font=theme.font(10), anchor="w", justify="left")
    preview.pack(fill="x", padx=16, pady=(6, 14))

    def update_preview(*_args):
        parent = naming.sanitize(entry_var.get() or "PDF 분할 저장", "PDF 분할 저장")
        preview.config(
            text=f"{desktop_name}/{parent}/{naming.folder_name(example)}/{example} - 1.pdf"
        )

    entry_var.trace_add("write", update_preview)
    update_preview()

    def confirm():
        dialog.done((SAVE_TOGETHER, entry_var.get().strip()))

    entry.bind("<Return>", lambda _e: confirm())

    def on_ok():
        if name_box.winfo_ismapped():
            confirm()
        else:
            dialog.done((SAVE_SEPARATE, ""))

    SoftButton(dialog.footer, "저장하기", command=on_ok).pack(side="right")
    SoftButton(dialog.footer, "취소", kind="ghost",
               command=dialog.close).pack(side="right", padx=(0, 8))
    return dialog.show()


def _default_parent_name(sources):
    if not sources:
        return "PDF 분할 저장"
    folder = os.path.basename(os.path.dirname(sources[0])) or "PDF"
    return naming.sanitize(f"{folder} 분할 저장", "PDF 분할 저장")
