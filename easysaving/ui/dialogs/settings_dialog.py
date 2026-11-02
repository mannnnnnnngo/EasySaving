"""설정 창 — 이동 조합키 / 버튼 모양 / 저장 규칙."""

import copy
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, filedialog

from .. import theme
from ..widgets import Modal, SoftButton, Toggle, divider, scroll_area, section_label
from ...core.models import MoveCombo
from ...platform_layer import memory, paths
from ...services import combo as combo_service

# 조합키 녹화 중 modifier 키를 눌렀을 때 오는 keysym
_MODIFIER_KEYSYMS = {
    "Shift_L": "shift", "Shift_R": "shift",
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Alt_L": "alt", "Alt_R": "alt", "Option_L": "alt", "Option_R": "alt",
    "Meta_L": "cmd" if theme.IS_MAC else "alt", "Meta_R": "cmd" if theme.IS_MAC else "alt",
    "Command_L": "cmd", "Command_R": "cmd",
    "Super_L": "cmd", "Super_R": "cmd", "Win_L": "cmd", "Win_R": "cmd",
}


def open_settings(master, settings, on_change):
    """설정 창을 연다. 값이 바뀔 때마다 on_change(settings) 로 즉시 미리보기 반영."""
    dialog = SettingsDialog(master, settings, on_change)
    return dialog.show()


class SettingsDialog(Modal):
    def __init__(self, master, settings, on_change):
        super().__init__(master, "설정", width=620)
        self.settings = settings
        self.original = copy.deepcopy(settings)
        self.on_change = on_change
        self.recording = False
        self.pending_modifiers = set()

        body = scroll_area(self.body, height=470)

        self._build_preview(body)
        self._build_move_combo(body)
        self._build_appearance(body)
        self._build_saving(body)
        self._build_about(body)

        SoftButton(self.footer, "닫기", command=self._finish).pack(side="right")
        SoftButton(self.footer, "기본값으로 되돌리기", kind="ghost",
                   command=self._reset).pack(side="left")

        self._height = 640
        self.bind("<Destroy>", self._on_destroy, add="+")

    # --- 미리보기 ------------------------------------------------------------

    def _build_preview(self, parent):
        section_label(parent, "미리보기", pady=(0, 6))
        holder = tk.Frame(parent, bg=theme.CARD, height=86)
        holder.pack(fill="x")
        holder.pack_propagate(False)
        self.preview = tk.Canvas(holder, bg=theme.CARD, highlightthickness=0, height=60)
        self.preview.pack(expand=True)
        self._draw_preview()

    def _draw_preview(self):
        canvas = self.preview
        canvas.delete("all")
        settings = self.settings
        font = (theme.family(), max(9, int(settings.font_size * settings.scale)), "bold")
        text = settings.button_text or "저장하기"
        text_width = tkfont.Font(family=font[0], size=font[1], weight=font[2]).measure(text)
        main_w = text_width + int(22 * settings.scale) * 2
        drop_w = int(38 * settings.scale)
        height = max(int(34 * settings.scale), int(settings.font_size * settings.scale) + int(22 * settings.scale))
        width = main_w + drop_w
        canvas.config(width=width + 4, height=height + 4)

        radius = min(settings.corner_radius, height // 2)
        base = settings.button_color
        theme.round_rect_corners(canvas, 2, 2, main_w, height, radius,
                                 (True, False, False, True), fill=base)
        theme.round_rect_corners(canvas, main_w, 2, width, height, radius,
                                 (False, True, True, False), fill=theme.darken(base, 0.08))
        canvas.create_text(main_w / 2 + 1, height / 2 + 1, text=text,
                           fill=settings.text_color, font=font)
        canvas.create_text(main_w + drop_w / 2, height / 2 + 2, text="▾",
                           fill=settings.text_color, font=(theme.family(), 12))

    def _changed(self):
        self.settings.clamped()
        self._draw_preview()
        if self.on_change:
            self.on_change(self.settings)

    # --- 이동 조합키 ---------------------------------------------------------

    def _build_move_combo(self, parent):
        section_label(parent, "버튼 옮기기 조합")
        box = tk.Frame(parent, bg=theme.CARD, highlightbackground=theme.BORDER,
                       highlightthickness=1)
        box.pack(fill="x")
        self.combo_box = box

        self.combo_label = tk.Label(box, text=combo_service.describe(self.settings.move_combo),
                                    bg=theme.CARD, fg=theme.TEXT, font=theme.font(14, "bold"),
                                    anchor="w")
        self.combo_label.pack(fill="x", padx=16, pady=(14, 2))
        self.combo_hint = tk.Label(
            box, text="여기를 눌러 바꿀 수 있어요. (수식키를 누른 채로 이 상자를 클릭 → 바깥을 클릭하면 저장)",
            bg=theme.CARD, fg=theme.MUTED, font=theme.font(10), anchor="w",
            justify="left", wraplength=520)
        self.combo_hint.pack(fill="x", padx=16, pady=(0, 14))

        for widget in (box, self.combo_label, self.combo_hint):
            widget.bind("<Button-1>", self._on_combo_click)
            widget.bind("<Button-2>", self._on_combo_click)
            widget.bind("<Button-3>", self._on_combo_click)
            widget.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

    def _on_combo_click(self, event):
        if not self.recording:
            self._start_recording()
            return "break"
        # 녹화 중 상자 안을 클릭 = 마우스 버튼 지정
        modifiers = sorted(self.pending_modifiers | set(combo_service.modifiers_from_state(event.state)))
        candidate = MoveCombo(modifiers=modifiers, button=event.num)
        valid, reason = combo_service.is_valid(candidate)
        if not valid:
            self.combo_hint.config(text=reason, fg=theme.DANGER)
            return "break"
        self.settings.move_combo = candidate
        self.combo_label.config(text=combo_service.describe(candidate))
        self.combo_hint.config(text="좋아요! 창 아무 곳이나 클릭하면 저장됩니다.", fg=theme.SUCCESS)
        return "break"

    def _start_recording(self):
        self.recording = True
        self.pending_modifiers = set()
        self.combo_box.config(highlightbackground=theme.ACCENT, highlightcolor=theme.ACCENT)
        self.combo_label.config(text="조합을 눌러 보세요…", fg=theme.ACCENT)
        self.combo_hint.config(
            text="Alt · Ctrl · Shift 같은 키를 누른 채로 이 상자를 마우스로 클릭하세요. "
                 "그 다음 상자 바깥을 클릭하면 저장됩니다.", fg=theme.MUTED)
        self.bind_all("<KeyPress>", self._on_key_press, add="+")
        self.bind_all("<KeyRelease>", self._on_key_release, add="+")
        self.bind("<Button-1>", self._maybe_stop_recording, add="+")
        self.focus_force()

    def _stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.pending_modifiers = set()
        try:
            self.unbind_all("<KeyPress>")
            self.unbind_all("<KeyRelease>")
        except Exception:
            pass
        self.combo_box.config(highlightbackground=theme.BORDER, highlightcolor=theme.BORDER)
        self.combo_label.config(text=combo_service.describe(self.settings.move_combo), fg=theme.TEXT)
        self.combo_hint.config(
            text="여기를 눌러 바꿀 수 있어요. (수식키를 누른 채로 이 상자를 클릭 → 바깥을 클릭하면 저장)",
            fg=theme.MUTED)
        self._changed()

    def _maybe_stop_recording(self, event):
        if not self.recording:
            return
        widget = event.widget
        while widget is not None:
            if widget is self.combo_box:
                return          # 상자 안 클릭은 버튼 지정용
            widget = getattr(widget, "master", None)
        self._stop_recording()

    def _on_key_press(self, event):
        if not self.recording:
            return
        name = _MODIFIER_KEYSYMS.get(event.keysym)
        if name:
            self.pending_modifiers.add(name)
        self.pending_modifiers |= set(combo_service.modifiers_from_state(event.state))
        preview = MoveCombo(modifiers=sorted(self.pending_modifiers),
                            button=self.settings.move_combo.button)
        self.combo_label.config(text=combo_service.describe(preview) + "  …")

    def _on_key_release(self, event):
        if not self.recording:
            return
        name = _MODIFIER_KEYSYMS.get(event.keysym)
        if name:
            self.pending_modifiers.discard(name)

    # --- 버튼 모양 -----------------------------------------------------------

    def _build_appearance(self, parent):
        section_label(parent, "버튼 모양")
        box = tk.Frame(parent, bg=theme.BG)
        box.pack(fill="x")

        # 버튼 글자
        row = _row(box, "버튼 글자")
        text_var = tk.StringVar(value=self.settings.button_text)
        entry = tk.Entry(row, textvariable=text_var, font=theme.font(12), width=16,
                         relief="flat", bg=theme.CARD, fg=theme.TEXT,
                         highlightthickness=1, highlightbackground=theme.BORDER,
                         highlightcolor=theme.ACCENT, insertbackground=theme.TEXT)
        entry.pack(side="right", ipady=5)

        def on_text(*_a):
            self.settings.button_text = text_var.get()[:20] or "저장하기"
            self._changed()

        text_var.trace_add("write", on_text)

        # 색
        self._color_row(box, "버튼 색", "button_color", theme.PRESET_COLORS)
        self._color_row(box, "글자 색", "text_color", theme.PRESET_TEXT_COLORS)

        # 크기
        self._slider_row(box, "글자 크기", "font_size", 10, 32, 1)
        self._slider_row(box, "버튼 크기", "scale", 0.7, 2.0, 0.05)
        self._slider_row(box, "모서리 둥글기", "corner_radius", 0, 30, 1)
        self._slider_row(box, "투명도", "opacity", 0.3, 1.0, 0.05)

        toggle = Toggle(box, "항상 다른 창 위에 띄우기", self.settings.always_on_top,
                        command=lambda value: self._set("always_on_top", value))
        toggle.pack(fill="x", pady=(10, 0))

    def _color_row(self, parent, label, field, presets):
        row = _row(parent, label)
        holder = tk.Frame(row, bg=theme.BG)
        holder.pack(side="right")

        swatch = tk.Frame(holder, bg=getattr(self.settings, field), width=26, height=26,
                          highlightbackground=theme.BORDER, highlightthickness=1)
        swatch.pack(side="right", padx=(8, 0))

        def choose():
            color = colorchooser.askcolor(color=getattr(self.settings, field),
                                          parent=self, title=label)[1]
            if color:
                apply_color(color.upper())

        def apply_color(color):
            setattr(self.settings, field, color)
            swatch.config(bg=color)
            self._changed()

        for preset in presets:
            dot = tk.Frame(holder, bg=preset, width=20, height=20,
                           highlightbackground=theme.BORDER, highlightthickness=1)
            dot.pack(side="right", padx=2)
            dot.bind("<Button-1>", lambda _e, c=preset: apply_color(c))
            dot.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

        picker = tk.Label(holder, text="직접 고르기", bg=theme.BG, fg=theme.ACCENT,
                          font=theme.font(11, "bold"))
        picker.pack(side="right", padx=(0, 10))
        picker.bind("<Button-1>", lambda _e: choose())
        picker.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

    def _slider_row(self, parent, label, field, minimum, maximum, step):
        row = _row(parent, label)
        value_label = tk.Label(row, text="", bg=theme.BG, fg=theme.MUTED,
                               font=theme.font(11), width=5, anchor="e")
        value_label.pack(side="right")

        is_float = isinstance(step, float)
        var = tk.DoubleVar(value=float(getattr(self.settings, field)))

        def on_move(_value=None):
            value = round(var.get(), 2)
            setattr(self.settings, field, value if is_float else int(round(value)))
            value_label.config(text=f"{value:.2f}" if is_float else str(int(round(value))))
            self._changed()

        scale = tk.Scale(row, from_=minimum, to=maximum, resolution=step, variable=var,
                         orient="horizontal", showvalue=False, length=210,
                         bg=theme.BG, highlightthickness=0, troughcolor=theme.CARD,
                         activebackground=theme.ACCENT, sliderrelief="flat", bd=0,
                         command=on_move)
        scale.pack(side="right", padx=(0, 10))
        on_move()

    def _set(self, field, value):
        setattr(self.settings, field, value)
        self._changed()

    # --- 저장 규칙 -----------------------------------------------------------

    def _build_saving(self, parent):
        section_label(parent, "저장 규칙")
        box = tk.Frame(parent, bg=theme.BG)
        box.pack(fill="x")

        row = _row(box, "저장 위치")
        self.path_label = tk.Label(row, text=self._path_text(), bg=theme.BG, fg=theme.MUTED,
                                   font=theme.font(11), anchor="e")
        self.path_label.pack(side="right", padx=(8, 0))
        change = tk.Label(row, text="변경", bg=theme.BG, fg=theme.ACCENT,
                          font=theme.font(11, "bold"))
        change.pack(side="right")
        change.bind("<Button-1>", lambda _e: self._pick_folder())
        change.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

        row = _row(box, "폴더 이름 뒤에 붙일 말")
        suffix_var = tk.StringVar(value=self.settings.folder_suffix)
        entry = tk.Entry(row, textvariable=suffix_var, font=theme.font(12), width=12,
                         relief="flat", bg=theme.CARD, fg=theme.TEXT,
                         highlightthickness=1, highlightbackground=theme.BORDER,
                         highlightcolor=theme.ACCENT, insertbackground=theme.TEXT)
        entry.pack(side="right", ipady=5)

        example = tk.Label(box, text="", bg=theme.BG, fg=theme.MUTED, font=theme.font(10),
                           anchor="w")
        example.pack(fill="x", pady=(2, 0))

        def on_suffix(*_a):
            self.settings.folder_suffix = suffix_var.get()[:20]
            self._update_example(example)
            self._changed()

        suffix_var.trace_add("write", on_suffix)

        pad_toggle = Toggle(box, "번호 자릿수 맞추기 (1, 2 → 01, 02)", self.settings.pad_numbers,
                            command=lambda value: (self._set("pad_numbers", value),
                                                   self._update_example(example)))
        pad_toggle.pack(fill="x", pady=(10, 0))

        preview_toggle = Toggle(box, "저장하기 전에 미리보기 보여주기", self.settings.preview_before_save,
                                command=lambda value: self._set("preview_before_save", value))
        preview_toggle.pack(fill="x", pady=(6, 0))

        open_toggle = Toggle(box, "저장이 끝나면 폴더 열기", self.settings.open_folder_when_done,
                             command=lambda value: self._set("open_folder_when_done", value))
        open_toggle.pack(fill="x", pady=(6, 0))
        self._update_example(example)

        section_label(parent, "PowerPoint 로 바꾸기")
        Toggle(parent, "글자를 편집할 수 있게 바꾸기 (끄면 페이지를 그림 그대로)",
               self.settings.pptx_editable,
               command=lambda value: self._set("pptx_editable", value)).pack(fill="x")

        section_label(parent, "업데이트")
        Toggle(parent, "켤 때 새 버전 자동 확인 (하루 한 번)", self.settings.auto_update_check,
               command=lambda value: self._set("auto_update_check", value)).pack(fill="x")

    def _update_example(self, label):
        from ...core import naming

        folder = naming.folder_name("기안", self.settings.folder_suffix)
        first = naming.page_filename("기안", 1, 12, self.settings.pad_numbers)
        label.config(text=f"예) {folder} / {first}")

    def _path_text(self):
        path = self.settings.output_root or paths.desktop_dir()
        path = path.replace(os.path.expanduser("~"), "~")
        label = "데스크탑" if not self.settings.output_root else path
        return label if len(label) <= 34 else "…" + label[-33:]

    def _pick_folder(self):
        folder = filedialog.askdirectory(parent=self, title="저장할 폴더 선택",
                                         initialdir=self.settings.output_root or paths.desktop_dir())
        if folder:
            desktop = paths.desktop_dir()
            self.settings.output_root = "" if os.path.normpath(folder) == os.path.normpath(desktop) else folder
            self.path_label.config(text=self._path_text())
            self._changed()

    # --- 정보 ---------------------------------------------------------------

    def _build_about(self, parent):
        from ... import APP_NAME, APP_VERSION

        divider(parent, pady=14)
        used = memory.rss_mb()
        tk.Label(parent,
                 text=f"{APP_NAME} {APP_VERSION}   ·   메모리 사용량 {used}MB / 100MB 목표",
                 bg=theme.BG, fg=theme.MUTED, font=theme.font(10), anchor="w").pack(fill="x")
        tk.Label(parent, text=f"설정 파일: {paths.config_path().replace(os.path.expanduser('~'), '~')}",
                 bg=theme.BG, fg=theme.MUTED, font=theme.font(10), anchor="w").pack(fill="x")

    # --- 마무리 -------------------------------------------------------------

    def _reset(self):
        from ...core.models import Settings

        keep_x, keep_y = self.settings.pos_x, self.settings.pos_y
        fresh = Settings()
        fresh.pos_x, fresh.pos_y = keep_x, keep_y
        fresh.tutorial_done = self.settings.tutorial_done
        fresh.permissions_ack = self.settings.permissions_ack
        for field, value in fresh.to_dict().items():
            if field == "move_combo":
                self.settings.move_combo = MoveCombo()
            else:
                setattr(self.settings, field, value)
        self.combo_label.config(text=combo_service.describe(self.settings.move_combo))
        self._changed()
        self.done("reset")

    def _finish(self):
        self._stop_recording()
        self.done(True)

    def _on_destroy(self, _event=None):
        if self.recording:
            self.recording = False


def _row(parent, label):
    row = tk.Frame(parent, bg=theme.BG)
    row.pack(fill="x", pady=5)
    tk.Label(row, text=label, bg=theme.BG, fg=theme.TEXT, font=theme.font(12),
             anchor="w").pack(side="left")
    return row
