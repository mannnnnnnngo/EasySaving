"""공통 위젯.

macOS(Aqua) 의 tk.Button 은 배경색이 무시되기 때문에,
색을 자유롭게 쓰기 위해 Frame + Label 로 직접 만든 버튼을 쓴다.
"""

import tkinter as tk

from . import theme


class SoftButton(tk.Frame):
    """어느 OS 에서나 같은 색으로 보이는 버튼."""

    KINDS = {
        "primary": (theme.ACCENT, "#FFFFFF"),
        "ghost": (theme.CARD, theme.TEXT),
        "outline": (theme.BG, theme.TEXT),
        "danger": (theme.DANGER, "#FFFFFF"),
    }

    def __init__(self, parent, text, command=None, kind="primary", width=None,
                 padx=18, pady=10, font=None, **kwargs):
        bg, fg = self.KINDS.get(kind, self.KINDS["primary"])
        border = theme.BORDER if kind in ("outline", "ghost") else bg
        super().__init__(parent, bg=border, highlightthickness=0, bd=0, **kwargs)
        self.command = command
        self._bg = bg
        self._hover = theme.darken(bg, 0.12) if kind != "ghost" else theme.CARD_HOVER
        self._enabled = True

        self.inner = tk.Frame(self, bg=bg, bd=0, highlightthickness=0)
        self.inner.pack(padx=1, pady=1, fill="both", expand=True)
        self.label = tk.Label(
            self.inner, text=text, bg=bg, fg=fg,
            font=font or theme.font(13, "bold"), padx=padx, pady=pady,
        )
        self.label.pack(fill="both", expand=True)
        if width:
            self.label.config(width=width)

        for widget in (self, self.inner, self.label):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

    def _on_click(self, _event=None):
        if self._enabled and self.command:
            self.command()

    def _on_enter(self, _event=None):
        if self._enabled:
            self.inner.config(bg=self._hover)
            self.label.config(bg=self._hover)

    def _on_leave(self, _event=None):
        if self._enabled:
            self.inner.config(bg=self._bg)
            self.label.config(bg=self._bg)

    def set_text(self, text):
        self.label.config(text=text)

    def set_enabled(self, enabled):
        self._enabled = enabled
        color = self._bg if enabled else theme.mix(self._bg, "#FFFFFF", 0.55)
        self.inner.config(bg=color)
        self.label.config(bg=color)


class Toggle(tk.Frame):
    """체크박스 (☑/☐). OS 기본 위젯 대신 직접 그려 색을 통일한다."""

    def __init__(self, parent, text, value=False, command=None, bg=theme.BG,
                 font=None, wraplength=0):
        super().__init__(parent, bg=bg)
        self.var = tk.BooleanVar(value=bool(value))
        self.command = command
        self.box = tk.Label(self, text=self._glyph(), bg=bg, fg=theme.ACCENT,
                            font=theme.font(15))
        self.box.pack(side="left")
        self.text = tk.Label(self, text=text, bg=bg, fg=theme.TEXT, anchor="w",
                             font=font or theme.font(12), justify="left")
        if wraplength:
            self.text.config(wraplength=wraplength)
        self.text.pack(side="left", padx=(6, 0))
        for widget in (self, self.box, self.text):
            widget.bind("<Button-1>", self.toggle)

    def _glyph(self):
        return "☑" if self.var.get() else "☐"

    def toggle(self, _event=None):
        self.var.set(not self.var.get())
        self.box.config(text=self._glyph(), fg=theme.ACCENT if self.var.get() else theme.MUTED)
        if self.command:
            self.command(self.var.get())

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(bool(value))
        self.box.config(text=self._glyph(), fg=theme.ACCENT if value else theme.MUTED)


class Modal(tk.Toplevel):
    """앱 공통 다이얼로그 기본형. show() 가 결과를 돌려준다."""

    def __init__(self, master, title, width=560, height=None, closable=True):
        super().__init__(master)
        self.result = None
        self._closable = closable
        self.title(title)
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self.header = tk.Frame(self, bg=theme.BG)
        self.header.pack(fill="x", padx=24, pady=(22, 0))
        tk.Label(self.header, text=title, bg=theme.BG, fg=theme.TEXT,
                 font=theme.title_font(18), anchor="w").pack(side="left")

        self.body = tk.Frame(self, bg=theme.BG)
        self.body.pack(fill="both", expand=True, padx=24, pady=(10, 0))

        self.footer = tk.Frame(self, bg=theme.BG)
        self.footer.pack(fill="x", padx=24, pady=(14, 20))

        self._width = width
        self._height = height
        self.protocol("WM_DELETE_WINDOW", self.close)
        if closable:
            self.bind("<Escape>", lambda _e: self.close())

    def subtitle(self, text):
        tk.Label(self.header.master, text=text, bg=theme.BG, fg=theme.MUTED,
                 font=theme.font(12), anchor="w", justify="left",
                 wraplength=self._width - 48).pack(fill="x", padx=24, pady=(6, 0),
                                                   after=self.header)

    def center_on(self, widget=None):
        self.update_idletasks()
        width = self._width
        height = self._height or self.winfo_reqheight()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = int((screen_w - width) / 2)
        y = int((screen_h - height) / 2.4)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def show(self):
        self.center_on()
        self.transient(self.master)
        self.deiconify()
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass
        self.wait_window(self)
        return self.result

    def close(self, result=None):
        if result is not None:
            self.result = result
        if not self._closable and self.result is None:
            return
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def done(self, result):
        self.result = result
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class OptionCard(tk.Frame):
    """큰 선택지 카드 (제목 + 설명 + 클릭)."""

    def __init__(self, parent, title, description, command, emoji="", bg=theme.CARD):
        super().__init__(parent, bg=theme.BORDER, bd=0, highlightthickness=0)
        self.command = command
        self._bg = bg
        inner = tk.Frame(self, bg=bg)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.inner = inner

        row = tk.Frame(inner, bg=bg)
        row.pack(fill="x", padx=16, pady=14)
        self.widgets = [self, inner, row]

        if emoji:
            icon = tk.Label(row, text=emoji, bg=bg, font=theme.font(20))
            icon.pack(side="left", padx=(0, 12))
            self.widgets.append(icon)

        text_col = tk.Frame(row, bg=bg)
        text_col.pack(side="left", fill="x", expand=True)
        title_label = tk.Label(text_col, text=title, bg=bg, fg=theme.TEXT,
                               font=theme.font(14, "bold"), anchor="w")
        title_label.pack(fill="x")
        desc_label = tk.Label(text_col, text=description, bg=bg, fg=theme.MUTED,
                              font=theme.font(11), anchor="w", justify="left",
                              wraplength=420)
        desc_label.pack(fill="x", pady=(3, 0))
        arrow = tk.Label(row, text="›", bg=bg, fg=theme.MUTED, font=theme.font(20))
        arrow.pack(side="right")
        self.widgets += [text_col, title_label, desc_label, arrow]

        for widget in self.widgets:
            widget.bind("<Button-1>", lambda _e: self.command())
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)
            widget.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

    def _paint(self, color):
        for widget in self.widgets:
            try:
                widget.configure(bg=color)
            except tk.TclError:
                pass

    def _enter(self, _event=None):
        self._paint(theme.CARD_HOVER)

    def _leave(self, _event=None):
        self._paint(self._bg)


def section_label(parent, text, bg=theme.BG, pady=(16, 6)):
    label = tk.Label(parent, text=text, bg=bg, fg=theme.MUTED,
                     font=theme.font(11, "bold"), anchor="w")
    label.pack(fill="x", pady=pady)
    return label


def scroll_area(parent, height=460, bg=theme.BG):
    """세로 스크롤 되는 영역을 만들어 안쪽 Frame 을 돌려준다."""
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, height=height)
    scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=bg)

    window = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def on_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(window, width=canvas.winfo_width())

    inner.bind("<Configure>", on_configure)
    canvas.bind("<Configure>", on_configure)

    def on_wheel(event):
        delta = event.delta
        if theme.IS_MAC:
            canvas.yview_scroll(-1 * int(delta), "units")
        else:
            canvas.yview_scroll(int(-delta / 120), "units")

    canvas.bind_all("<MouseWheel>", on_wheel)
    inner.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))
    return inner


def divider(parent, bg=theme.BG, pady=8):
    line = tk.Frame(parent, bg=theme.BORDER, height=1)
    line.pack(fill="x", pady=pady)
    return line
