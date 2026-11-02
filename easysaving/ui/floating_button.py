"""화면에 떠 있는 '저장하기' 버튼.

  ┌──────────────────┬────┐
  │     저장하기      │ ▾ │
  └──────────────────┴────┘
     ↑ 클릭 = 저장       ↑ 클릭 = 메뉴

  이동 : Alt + 마우스 오른쪽 클릭 드래그 (설정에서 변경 가능)
"""

import os
import tkinter as tk
import tkinter.font as tkfont

from . import theme
from ..services import combo as combo_service

ZONE_MAIN = "main"
ZONE_DROP = "drop"
DRAG_THRESHOLD = 3  # 이 픽셀 이상 움직여야 '드래그' 로 본다


class FloatingButton(tk.Toplevel):
    """숨겨진 루트 창의 자식으로 만든다.

    루트 자체를 overrideredirect 로 쓰면 macOS 에서 일반 다이얼로그가 뜨지 않으므로,
    루트는 withdraw() 해 두고 이 버튼만 화면에 띄운다.
    """

    def __init__(self, master, settings, on_save, on_menu):
        super().__init__(master)
        self.settings = settings
        self.on_save = on_save
        self.on_menu = on_menu

        self._hover_zone = None
        self._press_zone = None
        self._dragging = False
        self._drag_origin = (0, 0)
        self._drag_start_pointer = (0, 0)
        self._busy_text = None
        self._on_moved = None

        self.overrideredirect(True)
        try:
            self.attributes("-topmost", bool(settings.always_on_top))
        except Exception:
            pass

        self._transparent = self._setup_transparency()
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                                bg=self._canvas_bg())
        self.canvas.pack(fill="both", expand=True)

        self._bind_events()
        self.redraw()
        self._place_window(first=True)

    # --- 외부 API ------------------------------------------------------------

    def apply_settings(self, settings):
        """설정 창에서 바꾼 값을 즉시 반영."""
        self.settings = settings
        try:
            self.attributes("-topmost", bool(settings.always_on_top))
            self.attributes("-alpha", float(settings.opacity))
        except Exception:
            pass
        self.canvas.config(bg=self._canvas_bg())
        self.redraw()
        self._place_window()

    def set_busy(self, text=None):
        """작업 중이면 버튼 글씨를 바꾸고 클릭을 막는다."""
        self._busy_text = text
        self.redraw()

    @property
    def busy(self):
        return self._busy_text is not None

    def set_move_callback(self, callback):
        self._on_moved = callback

    def flash(self, text, milliseconds=1400):
        """짧은 안내 문구를 버튼에 잠깐 띄운다."""
        previous = self._busy_text
        self._busy_text = text
        self.redraw()

        def restore():
            self._busy_text = previous
            self.redraw()

        self.after(milliseconds, restore)

    # --- 그리기 --------------------------------------------------------------

    def _font(self):
        size = max(9, int(self.settings.font_size * self.settings.scale))
        return tkfont.Font(family=theme.family(), size=size, weight="bold")

    def _metrics(self):
        scale = self.settings.scale
        font = self._font()
        text = self._busy_text or self.settings.button_text or "저장하기"
        pad_x = int(22 * scale)
        height = max(int(34 * scale), font.metrics("linespace") + int(20 * scale))
        main_w = font.measure(text) + pad_x * 2
        drop_w = int(38 * scale)
        return font, text, main_w, drop_w, main_w + drop_w, height

    def redraw(self):
        font, text, main_w, drop_w, width, height = self._metrics()
        canvas = self.canvas
        canvas.delete("all")
        canvas.config(width=width, height=height)
        self.geometry(f"{width}x{height}")

        base = self.settings.button_color
        fg = self.settings.text_color
        radius = min(self.settings.corner_radius, height // 2)

        main_bg = theme.darken(base, 0.14) if self._hover_zone == ZONE_MAIN else base
        drop_bg = theme.darken(base, 0.22) if self._hover_zone == ZONE_DROP else theme.darken(base, 0.08)
        if self.busy:
            main_bg = drop_bg = theme.mix(base, "#FFFFFF", 0.25)

        # 왼쪽(저장하기) / 오른쪽(▾) 을 따로 그려 각각 hover 효과를 준다
        _rounded(canvas, 0, 0, main_w, height, radius, (True, False, False, True), fill=main_bg)
        _rounded(canvas, main_w, 0, width, height, radius, (False, True, True, False), fill=drop_bg)

        canvas.create_text(main_w / 2, height / 2, text=text, fill=fg, font=font)
        canvas.create_line(main_w, height * 0.25, main_w, height * 0.75,
                           fill=theme.mix(fg, base, 0.65))
        canvas.create_text(main_w + drop_w / 2, height / 2 + 1, text="▾", fill=fg,
                           font=(theme.family(), max(10, int(font.cget("size") * 0.95))))

    def _canvas_bg(self):
        if self._transparent == "mac":
            return "systemTransparent"
        if self._transparent == "win":
            return TRANSPARENT_KEY
        return self.settings.button_color

    def _setup_transparency(self):
        """모서리 바깥을 투명하게. 안 되면 그냥 버튼색으로 채운다."""
        # macOS Tk 는 -transparent 창에서 update() 가 멈추는 문제가 있어,
        # 자동 테스트에서는 이 환경변수로 투명 처리를 끈다.
        if os.environ.get("EASYSAVING_NO_TRANSPARENT"):
            return None
        if theme.IS_WIN:
            try:
                self.config(bg=TRANSPARENT_KEY)
                self.attributes("-transparentcolor", TRANSPARENT_KEY)
                return "win"
            except Exception:
                return None
        if theme.IS_MAC:
            try:
                self.wm_attributes("-transparent", True)
                self.config(bg="systemTransparent")
                return "mac"
            except Exception:
                return None
        return None

    # --- 위치 ----------------------------------------------------------------

    def _place_window(self, first=False):
        _, _, _, _, width, height = self._metrics()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = self.settings.pos_x
        y = self.settings.pos_y
        if x is None or y is None:
            x = screen_w - width - 40
            y = int(screen_h * 0.72)
        x = max(0, min(int(x), screen_w - width))
        y = max(0, min(int(y), screen_h - height))
        self.settings.pos_x, self.settings.pos_y = x, y
        self.geometry(f"{width}x{height}+{x}+{y}")
        if first:
            try:
                self.attributes("-alpha", float(self.settings.opacity))
            except Exception:
                pass

    # --- 이벤트 --------------------------------------------------------------

    def _bind_events(self):
        for button in (1, 2, 3):
            self.canvas.bind(f"<ButtonPress-{button}>", self._on_press)
            self.canvas.bind(f"<ButtonRelease-{button}>", self._on_release)
            self.canvas.bind(f"<B{button}-Motion>", self._on_motion)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)

    def _zone_at(self, x):
        _, _, main_w, _, _, _ = self._metrics()
        return ZONE_MAIN if x < main_w else ZONE_DROP

    def _on_hover(self, event):
        zone = self._zone_at(event.x)
        if zone != self._hover_zone:
            self._hover_zone = zone
            self.redraw()

    def _on_leave(self, _event=None):
        if self._hover_zone is not None:
            self._hover_zone = None
            self.redraw()

    def _on_press(self, event):
        if combo_service.matches(self.settings.move_combo, event.state, event.num):
            self._dragging = True
            self._drag_start_pointer = (event.x_root, event.y_root)
            self._drag_origin = (self.winfo_x(), self.winfo_y())
            self.canvas.config(cursor="fleur")
            return
        if event.num == 1 and not self.busy:
            self._press_zone = self._zone_at(event.x)

    def _on_motion(self, event):
        if not self._dragging:
            return
        dx = event.x_root - self._drag_start_pointer[0]
        dy = event.y_root - self._drag_start_pointer[1]
        x = self._drag_origin[0] + dx
        y = self._drag_origin[1] + dy
        _, _, _, _, width, height = self._metrics()
        x = max(0, min(x, self.winfo_screenwidth() - width))
        y = max(0, min(y, self.winfo_screenheight() - height))
        self.geometry(f"+{int(x)}+{int(y)}")

    def _on_release(self, event):
        if self._dragging:
            self._dragging = False
            self.canvas.config(cursor="")
            moved = (abs(event.x_root - self._drag_start_pointer[0]) > DRAG_THRESHOLD or
                     abs(event.y_root - self._drag_start_pointer[1]) > DRAG_THRESHOLD)
            if moved:
                self.settings.pos_x, self.settings.pos_y = self.winfo_x(), self.winfo_y()
                if self._on_moved:
                    self._on_moved()
            return

        zone = self._press_zone
        self._press_zone = None
        if zone is None or self.busy or event.num != 1:
            return
        if self._zone_at(event.x) != zone:   # 눌렀다가 다른 곳에서 뗀 경우는 무시
            return
        if zone == ZONE_MAIN:
            self.on_save()
        else:
            self.on_menu()


TRANSPARENT_KEY = "#FF00FE"  # 윈도우에서 투명 처리용으로만 쓰는 색

_rounded = theme.round_rect_corners
