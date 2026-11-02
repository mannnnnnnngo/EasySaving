"""처음 실행 튜토리얼.

권한 설정을 마치고 '다시 보지 않기' 를 체크하기 전까지는 앱을 켤 때마다 뜬다.
"""

import tkinter as tk

from .. import theme
from ..widgets import Modal, SoftButton, Toggle
from ...platform_layer import paths, permissions
from ...services import combo as combo_service

BODY_HEIGHT = 372
WIDTH = 640


def should_show(settings):
    """권한이 다 갖춰지고 사용자가 확인했을 때만 건너뛴다."""
    if not settings.tutorial_done:
        return True
    return not permissions.all_required_granted()


def run_tutorial(master, settings, on_settings_saved=None):
    dialog = TutorialDialog(master, settings, on_settings_saved)
    return dialog.show()


class TutorialDialog(Modal):
    def __init__(self, master, settings, on_settings_saved=None):
        super().__init__(master, "Easy Saving 사용법", width=WIDTH, closable=True)
        self.settings = settings
        self.on_settings_saved = on_settings_saved
        self.index = 0
        self.permission_rows = []

        self.dots = tk.Frame(self.header, bg=theme.BG)
        self.dots.pack(side="right")

        self.stage = tk.Frame(self.body, bg=theme.BG, height=BODY_HEIGHT)
        self.stage.pack(fill="both", expand=True)
        self.stage.pack_propagate(False)

        self.steps = [
            self._step_welcome,
            self._step_button,
            self._step_save,
            self._step_multi,
            self._step_move,
            self._step_settings,
            self._step_permissions,
            self._step_finish,
        ]

        self.back_button = SoftButton(self.footer, "이전", kind="ghost", command=self.back)
        self.back_button.pack(side="left")
        self.next_button = SoftButton(self.footer, "다음", command=self.next)
        self.next_button.pack(side="right")
        self.skip_button = SoftButton(self.footer, "건너뛰기", kind="ghost", command=self._skip)
        self.skip_button.pack(side="right", padx=(0, 8))

        self._height = 620
        self._render()

    # --- 이동 ---------------------------------------------------------------

    def _render(self):
        for child in self.stage.winfo_children():
            child.destroy()
        self.steps[self.index]()
        self._render_dots()
        self.back_button.set_enabled(self.index > 0)
        last = self.index == len(self.steps) - 1
        self.next_button.set_text("시작하기" if last else "다음")
        if last:
            self.skip_button.pack_forget()
        elif not self.skip_button.winfo_ismapped():
            self.skip_button.pack(side="right", padx=(0, 8), before=self.next_button)

    def _render_dots(self):
        for child in self.dots.winfo_children():
            child.destroy()
        for i in range(len(self.steps)):
            color = theme.ACCENT if i == self.index else theme.BORDER
            dot = tk.Frame(self.dots, bg=color, width=8, height=8)
            dot.pack(side="left", padx=2)

    def next(self):
        if self.index >= len(self.steps) - 1:
            self._finish()
            return
        self.index += 1
        self._render()

    def back(self):
        if self.index > 0:
            self.index -= 1
            self._render()

    def _skip(self):
        self.done("skipped")

    def _finish(self):
        if permissions.all_required_granted():
            self.settings.permissions_ack = True
        if self.settings.permissions_ack:
            self.settings.tutorial_done = True
        if self.on_settings_saved:
            self.on_settings_saved()
        self.done("done")

    # --- 화면 조각 ----------------------------------------------------------

    def _title(self, text, subtitle=""):
        tk.Label(self.stage, text=text, bg=theme.BG, fg=theme.TEXT,
                 font=theme.title_font(20), anchor="w", justify="left",
                 wraplength=WIDTH - 60).pack(fill="x", pady=(4, 0))
        if subtitle:
            tk.Label(self.stage, text=subtitle, bg=theme.BG, fg=theme.MUTED,
                     font=theme.font(12), anchor="w", justify="left",
                     wraplength=WIDTH - 60).pack(fill="x", pady=(8, 0))

    def _card(self, lines, title="", mono=False):
        box = tk.Frame(self.stage, bg=theme.CARD)
        box.pack(fill="x", pady=(14, 0))
        if title:
            tk.Label(box, text=title, bg=theme.CARD, fg=theme.TEXT,
                     font=theme.font(12, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 4))
        font = ("Menlo" if theme.IS_MAC else "Consolas", 11) if mono else theme.font(12)
        tk.Label(box, text="\n".join(lines), bg=theme.CARD, fg=theme.TEXT if mono else theme.MUTED,
                 font=font, anchor="w", justify="left",
                 wraplength=WIDTH - 90).pack(fill="x", padx=16, pady=(0 if title else 14, 14))
        return box

    def _bullets(self, items):
        holder = tk.Frame(self.stage, bg=theme.BG)
        holder.pack(fill="x", pady=(12, 0))
        for icon, text in items:
            row = tk.Frame(holder, bg=theme.BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=icon, bg=theme.BG, font=theme.font(13), width=2).pack(side="left")
            tk.Label(row, text=text, bg=theme.BG, fg=theme.TEXT, font=theme.font(12),
                     anchor="w", justify="left", wraplength=WIDTH - 110).pack(side="left", fill="x")
        return holder

    def _button_preview(self, parent=None, label=None):
        parent = parent or self.stage
        holder = tk.Frame(parent, bg=theme.CARD, height=90)
        holder.pack(fill="x", pady=(14, 0))
        holder.pack_propagate(False)
        canvas = tk.Canvas(holder, bg=theme.CARD, highlightthickness=0, width=260, height=64)
        canvas.pack(expand=True)
        base = self.settings.button_color
        text = label or self.settings.button_text or "저장하기"
        theme.round_rect_corners(canvas, 10, 14, 160, 58, 16, (True, False, False, True), fill=base)
        theme.round_rect_corners(canvas, 160, 14, 205, 58, 16, (False, True, True, False),
                                 fill=theme.darken(base, 0.1))
        canvas.create_text(85, 36, text=text, fill=self.settings.text_color,
                           font=theme.font(14, "bold"))
        canvas.create_text(182, 37, text="▾", fill=self.settings.text_color, font=theme.font(13))
        return canvas

    # --- 각 단계 ------------------------------------------------------------

    def _step_welcome(self):
        self._title("PDF 를 1장씩 잘라서 저장해 드려요",
                    "인쇄 창을 띄워 한 장씩 저장하던 작업을, 버튼 한 번으로 끝냅니다.")
        self._card([
            "'기안.pdf' (2페이지) 를 고르면",
            "",
            f"{_desktop_label()}/",
            "└── 기안 저장/",
            "     ├── 기안 - 1.pdf     ← 1페이지",
            "     └── 기안 - 2.pdf     ← 2페이지",
        ], title="이렇게 저장됩니다", mono=True)
        self._bullets([
            ("⚡", "124페이지짜리 문서도 몇 초면 끝납니다."),
            ("📁", "폴더는 자동으로 만들어지고, 이름이 겹치면 (2) 를 붙여 안전하게 저장합니다."),
            ("🔒", "파일은 이 컴퓨터 안에서만 처리됩니다. 인터넷으로 보내지 않습니다."),
        ])

    def _step_button(self):
        self._title("화면에 이 버튼이 떠 있습니다",
                    "다른 창 위에 항상 떠 있어서, 어떤 프로그램을 쓰든 바로 누를 수 있어요.")
        self._button_preview()
        self._bullets([
            ("①", "왼쪽 '저장하기' 를 누르면 → 나눌 PDF 를 고르는 파일 창이 바로 뜹니다."),
            ("②", "오른쪽 '▾' 를 누르면 → 여러 파일 저장하기 · 설정 · 튜토리얼 다시 보기 · 종료 메뉴가 열립니다."),
            ("③", "버튼이 방해되면 조합키로 옮기거나, 메뉴 > 종료 로 끌 수 있습니다."),
        ])

    def _step_save(self):
        self._title("'저장하기' 를 누르면",
                    "바로 파일 창이 열립니다.")
        self._bullets([
            ("📂", "윈도우(맥) 기본 파일 창이 열립니다. 늘 쓰던 그 창이에요."),
            ("📄", "나눌 PDF 를 하나 고르면 곧바로 저장이 시작됩니다."),
        ])
        self._card([
            "1. 저장하기 클릭",
            "2. PDF 선택",
            f"3. {_desktop_label()} 에 '[파일이름] 저장' 폴더가 생기고",
            "4. 그 안에 '[파일이름] - 1.pdf', '- 2.pdf' … 순서대로 저장",
            "5. 끝나면 폴더가 자동으로 열립니다. (설정에서 끌 수 있어요)",
        ], title="저장되는 순서", mono=False)

    def _step_multi(self):
        self._title("여러 파일을 한 번에 나누기",
                    "▾ 메뉴 > '여러 파일 저장하기' 를 고른 뒤, 파일 창에서 여러 개를 선택하세요. "
                    "(Ctrl 또는 ⌘ 를 누른 채 클릭하면 여러 개가 선택됩니다.)")
        self._card([
            "따로 저장",
            f"  {_desktop_label()}/기안 저장/기안 - 1.pdf",
            f"  {_desktop_label()}/보고서 저장/보고서 - 1.pdf",
            "",
            "한 폴더에 모아서 저장  (폴더 이름을 직접 정합니다)",
            f"  {_desktop_label()}/12월 문서/기안 저장/기안 - 1.pdf",
            f"  {_desktop_label()}/12월 문서/보고서 저장/보고서 - 1.pdf",
        ], title="저장 방식 두 가지", mono=True)

    def _step_move(self):
        self._title("버튼 위치 옮기기",
                    "버튼이 가리는 곳에 있으면 언제든 옮길 수 있어요.")
        combo_text = combo_service.describe(self.settings.move_combo)
        box = tk.Frame(self.stage, bg=theme.CARD)
        box.pack(fill="x", pady=(16, 0))
        tk.Label(box, text=combo_text, bg=theme.CARD, fg=theme.ACCENT,
                 font=theme.font(17, "bold")).pack(padx=16, pady=(18, 4))
        tk.Label(box, text="을 누른 채로 버튼을 끌면 됩니다.", bg=theme.CARD, fg=theme.MUTED,
                 font=theme.font(12)).pack(padx=16, pady=(0, 18))
        self._bullets([
            ("🖱", "누른 채 드래그 → 원하는 자리에서 손을 떼면 그 위치가 저장됩니다."),
            ("⚙️", "이 조합이 불편하면 설정에서 다른 키로 바꿀 수 있어요."),
            ("📌", "다음에 앱을 켜도 마지막 위치 그대로 나타납니다."),
        ])

    def _step_settings(self):
        self._title("설정에서 바꿀 수 있는 것", "▾ 메뉴 > 설정 에서 언제든 바꿀 수 있어요.")
        self._bullets([
            ("⌨️", "버튼 옮기기 조합 — 상자를 클릭하고, 원하는 키를 누른 채 상자를 클릭한 뒤, 바깥을 클릭하면 저장됩니다."),
            ("🎨", "버튼 색 / 글자 색 — 미리 준비된 색을 고르거나 직접 고를 수 있습니다."),
            ("🔠", "버튼 글자 — '저장하기' 대신 원하는 말로 바꿀 수 있어요."),
            ("📏", "크기 · 모서리 둥글기 · 투명도 — 슬라이더로 조절합니다."),
            ("📁", "저장 위치 · 폴더 이름 · 번호 자릿수(01, 02) · 끝나면 폴더 열기."),
        ])

    def _step_permissions(self):
        self._title("필요한 권한", "이 앱이 정상적으로 동작하려면 아래 권한이 필요합니다.")
        holder = tk.Frame(self.stage, bg=theme.BG)
        holder.pack(fill="both", expand=True, pady=(12, 0))
        self.permission_holder = holder
        self._render_permissions()

    def _render_permissions(self):
        holder = self.permission_holder
        for child in holder.winfo_children():
            child.destroy()

        perms = permissions.check_all()
        for perm in perms:
            row = tk.Frame(holder, bg=theme.CARD)
            row.pack(fill="x", pady=3)
            head = tk.Frame(row, bg=theme.CARD)
            head.pack(fill="x", padx=14, pady=(10, 0))
            tk.Label(head, text=perm.name, bg=theme.CARD, fg=theme.TEXT,
                     font=theme.font(12, "bold"), anchor="w").pack(side="left")
            color = theme.SUCCESS if perm.ok else (theme.WARN if not perm.required else theme.DANGER)
            tk.Label(head, text=("필수 · " if perm.required else "선택 · ") + perm.badge,
                     bg=theme.CARD, fg=color, font=theme.font(11, "bold")).pack(side="right")
            tk.Label(row, text=perm.why + " " + perm.how, bg=theme.CARD, fg=theme.MUTED,
                     font=theme.font(10), anchor="w", justify="left",
                     wraplength=WIDTH - 90).pack(fill="x", padx=14, pady=(2, 10))
            if perm.settings_url and not perm.ok:
                link = tk.Label(row, text="설정 화면 열기 ›", bg=theme.CARD, fg=theme.ACCENT,
                                font=theme.font(11, "bold"), anchor="w")
                link.pack(fill="x", padx=14, pady=(0, 10))
                link.bind("<Button-1>", lambda _e, p=perm: permissions.open_settings(p))
                link.configure(cursor="hand2" if not theme.IS_MAC else "pointinghand")

        actions = tk.Frame(holder, bg=theme.BG)
        actions.pack(fill="x", pady=(10, 0))
        SoftButton(actions, "권한 다시 확인", kind="outline",
                   command=self._render_permissions).pack(side="left")
        self.ack_toggle = Toggle(
            holder, "권한을 확인했어요. 다음부터 이 튜토리얼을 띄우지 마세요.",
            value=self.settings.permissions_ack,
            command=self._set_ack, wraplength=WIDTH - 80)
        self.ack_toggle.pack(fill="x", pady=(12, 0))

    def _set_ack(self, value):
        self.settings.permissions_ack = bool(value)
        if self.on_settings_saved:
            self.on_settings_saved()

    def _step_finish(self):
        self._title("준비 끝났습니다!", "이제 버튼을 눌러 바로 써 보세요.")
        self._button_preview()
        self._card([
            "· 저장하기 → PDF 고르기 → 끝",
            f"· 결과는 {_desktop_label()} 의 '[파일이름] 저장' 폴더에 들어 있습니다.",
            f"· 버튼 옮기기: {combo_service.describe_short(self.settings.move_combo)}",
            "· 이 안내는 ▾ 메뉴 > '튜토리얼 다시 보기' 에서 언제든 다시 볼 수 있어요.",
        ], title="한눈에 정리")


def _desktop_label():
    return "바탕 화면" if theme.IS_WIN else "데스크탑"
