"""플로팅 버튼의 ▾ 드롭다운 메뉴."""

import tkinter as tk

from . import theme

ITEM_HEIGHT = 38
MENU_WIDTH = 232


class DropdownMenu(tk.Toplevel):
    def __init__(self, master, items, anchor_widget):
        """items = [(아이콘, 라벨, 설명, 콜백), ...]  구분선은 None"""
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=theme.BORDER)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        frame = tk.Frame(self, bg=theme.BG)
        frame.pack(padx=1, pady=1, fill="both", expand=True)

        for item in items:
            if item is None:
                tk.Frame(frame, bg=theme.BORDER, height=1).pack(fill="x", pady=4)
                continue
            self._add_item(frame, *item)

        self._place(anchor_widget)
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<FocusOut>", lambda _e: self.close())
        self.after(10, self._grab)

    def _grab(self):
        try:
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def _add_item(self, parent, icon, label, description, command):
        row = tk.Frame(parent, bg=theme.BG)
        row.pack(fill="x")
        icon_label = tk.Label(row, text=icon, bg=theme.BG, font=theme.font(14), width=2)
        icon_label.pack(side="left", padx=(12, 4), pady=8)
        text_col = tk.Frame(row, bg=theme.BG)
        text_col.pack(side="left", fill="x", expand=True, pady=(6, 7))
        title = tk.Label(text_col, text=label, bg=theme.BG, fg=theme.TEXT,
                         font=theme.font(12, "bold"), anchor="w")
        title.pack(fill="x")
        widgets = [row, icon_label, text_col, title]
        if description:
            desc = tk.Label(text_col, text=description, bg=theme.BG, fg=theme.MUTED,
                            font=theme.font(10), anchor="w")
            desc.pack(fill="x")
            widgets.append(desc)

        def paint(color):
            for widget in widgets:
                try:
                    widget.configure(bg=color)
                except tk.TclError:
                    pass

        def run(_event=None):
            self.close()
            command()

        for widget in widgets:
            widget.bind("<Button-1>", run)
            widget.bind("<Enter>", lambda _e: paint(theme.CARD))
            widget.bind("<Leave>", lambda _e: paint(theme.BG))
            widget.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

    def _place(self, anchor):
        self.update_idletasks()
        width = max(MENU_WIDTH, self.winfo_reqwidth())
        height = self.winfo_reqheight()
        ax, ay = anchor.winfo_x(), anchor.winfo_y()
        aw, ah = anchor.winfo_width(), anchor.winfo_height()
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()

        x = ax + aw - width
        y = ay + ah + 6
        if y + height > screen_h:      # 아래 공간이 없으면 위로
            y = ay - height - 6
        x = max(6, min(x, screen_w - width - 6))
        y = max(6, y)
        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    def close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
