"""안내 / 오류 / 완료 창."""

import os
import tkinter as tk

from .. import theme
from ..widgets import Modal, SoftButton


def info(master, title, message, detail="", ok="확인"):
    dialog = Modal(master, title, width=460)
    _body(dialog, message, detail)
    SoftButton(dialog.footer, ok, command=lambda: dialog.done(True)).pack(side="right")
    return dialog.show()


def error(master, title, message, detail=""):
    dialog = Modal(master, title, width=480)
    _body(dialog, message, detail, color=theme.DANGER)
    SoftButton(dialog.footer, "닫기", command=lambda: dialog.done(True)).pack(side="right")
    return dialog.show()


def confirm(master, title, message, detail="", ok="확인", cancel="취소"):
    dialog = Modal(master, title, width=460)
    _body(dialog, message, detail)
    SoftButton(dialog.footer, ok, command=lambda: dialog.done(True)).pack(side="right")
    SoftButton(dialog.footer, cancel, kind="ghost",
               command=lambda: dialog.done(False)).pack(side="right", padx=(0, 8))
    return bool(dialog.show())


def _body(dialog, message, detail, color=theme.TEXT):
    tk.Label(dialog.body, text=message, bg=theme.BG, fg=color, font=theme.font(13),
             anchor="w", justify="left", wraplength=400).pack(fill="x")
    if detail:
        tk.Label(dialog.body, text=detail, bg=theme.BG, fg=theme.MUTED, font=theme.font(11),
                 anchor="w", justify="left", wraplength=400).pack(fill="x", pady=(8, 0))


def completed(master, results, root_folder):
    """분할 완료 안내. 폴더는 저장이 끝나면 자동으로 열린다."""
    ok = [r for r in results if not r.error]
    failed = [r for r in results if r.error]
    pages = sum(r.pages for r in ok)

    dialog = Modal(master, "저장을 끝냈어요", width=520)
    headline = f"PDF {len(ok)}개 · 총 {pages}장을 나눠 저장했습니다."
    tk.Label(dialog.body, text=headline, bg=theme.BG, fg=theme.TEXT,
             font=theme.font(13, "bold"), anchor="w").pack(fill="x")

    box = tk.Frame(dialog.body, bg=theme.CARD)
    box.pack(fill="x", pady=(12, 0))
    for result in ok[:6]:
        row = tk.Frame(box, bg=theme.CARD)
        row.pack(fill="x", padx=12, pady=6)
        tk.Label(row, text=f"📁 {os.path.basename(result.folder)}", bg=theme.CARD,
                 fg=theme.TEXT, font=theme.font(11, "bold"), anchor="w").pack(side="left")
        tk.Label(row, text=f"{result.pages}장", bg=theme.CARD, fg=theme.MUTED,
                 font=theme.font(11)).pack(side="right")
    if len(ok) > 6:
        tk.Label(box, text=f"… 외 {len(ok) - 6}개", bg=theme.CARD, fg=theme.MUTED,
                 font=theme.font(11)).pack(anchor="w", padx=12, pady=(0, 8))

    tk.Label(dialog.body, text=f"저장 위치: {_short(root_folder)}", bg=theme.BG,
             fg=theme.MUTED, font=theme.font(11), anchor="w").pack(fill="x", pady=(10, 0))

    if failed:
        tk.Label(dialog.body, text=f"⚠️ {len(failed)}개 파일은 실패했어요", bg=theme.BG,
                 fg=theme.DANGER, font=theme.font(11, "bold"), anchor="w").pack(fill="x", pady=(10, 0))
        for result in failed[:3]:
            tk.Label(dialog.body, text=f"· {os.path.basename(result.source)} — {result.error}",
                     bg=theme.BG, fg=theme.MUTED, font=theme.font(10), anchor="w",
                     wraplength=460, justify="left").pack(fill="x")

    SoftButton(dialog.footer, "확인",
               command=lambda: dialog.done(True)).pack(side="right")
    return dialog.show()


def _short(path, limit=60):
    path = path.replace(os.path.expanduser("~"), "~")
    return path if len(path) <= limit else "…" + path[-(limit - 1):]
