"""설정 모델과 작업 모델 (순수 데이터)."""

import sys
from dataclasses import dataclass, field, asdict, fields
from typing import List, Optional

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")


def _default_modifiers():
    # macOS 의 Alt 키는 Option 키다.
    return ["alt"]


def _default_button():
    # macOS Tk 는 오른쪽 버튼을 Button-2 로 보고하는 경우가 있어 매칭 단계에서 2/3 을 모두 허용한다.
    return 2 if IS_MAC else 3


@dataclass
class MoveCombo:
    """버튼을 옮길 때 쓰는 조합. 기본값: Alt + 마우스 오른쪽 클릭."""

    modifiers: List[str] = field(default_factory=_default_modifiers)
    button: int = field(default_factory=_default_button)

    def to_dict(self):
        return {"modifiers": list(self.modifiers), "button": int(self.button)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        mods = [str(m).lower() for m in data.get("modifiers", []) if str(m).lower() in MODIFIER_LABELS]
        try:
            button = int(data.get("button", _default_button()))
        except (TypeError, ValueError):
            button = _default_button()
        return cls(modifiers=mods or _default_modifiers(), button=button if button in (1, 2, 3) else _default_button())


# 화면에 보여줄 modifier 이름 (macOS 는 기호 표기)
MODIFIER_LABELS = {
    "shift": "Shift" if not IS_MAC else "⇧ Shift",
    "ctrl": "Ctrl" if not IS_MAC else "⌃ Control",
    "alt": "Alt" if not IS_MAC else "⌥ Option(Alt)",
    "cmd": "Win" if not IS_MAC else "⌘ Command",
}

BUTTON_LABELS = {1: "마우스 왼쪽 클릭", 2: "마우스 오른쪽 클릭" if IS_MAC else "마우스 가운데 클릭", 3: "마우스 오른쪽 클릭"}


@dataclass
class Settings:
    """앱 전체 설정. JSON 한 파일로 저장된다."""

    # --- 버튼 모양 ---
    button_text: str = "저장하기"
    button_color: str = "#2F6FED"
    text_color: str = "#FFFFFF"
    hover_color: str = "#1E56C8"
    font_size: int = 15
    scale: float = 1.0          # 전체 크기 배율 (0.7 ~ 2.0)
    corner_radius: int = 16
    opacity: float = 1.0        # 0.3 ~ 1.0
    always_on_top: bool = True

    # --- 위치 ---
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None

    # --- 이동 조합키 ---
    move_combo: MoveCombo = field(default_factory=MoveCombo)

    # --- 저장 규칙 ---
    output_root: str = ""        # 빈 값이면 데스크탑
    folder_suffix: str = "저장"   # '기안' -> '기안 저장'
    pad_numbers: bool = False    # True 면 01, 02 …
    open_folder_when_done: bool = True
    preview_before_save: bool = True   # 저장 전에 '이렇게 저장할까요?' 창을 보여줄지

    # --- PowerPoint 변환 ---
    pptx_editable: bool = True   # True: 글자 편집 가능 / False: 페이지를 그림 그대로

    # --- 업데이트 ---
    auto_update_check: bool = True   # 켤 때 하루 한 번 새 버전 확인
    last_update_check: float = 0.0

    # --- 상태 ---
    tutorial_done: bool = False      # 튜토리얼을 끝까지 보고 '다시 보지 않기' 를 눌렀는지
    permissions_ack: bool = False    # 권한 안내를 확인했는지

    def to_dict(self):
        data = asdict(self)
        data["move_combo"] = self.move_combo.to_dict()
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known and k != "move_combo"}
        obj = cls(**kwargs)
        obj.move_combo = MoveCombo.from_dict(data.get("move_combo"))
        return obj.clamped()

    def clamped(self):
        """말도 안 되는 값이 들어와도 UI 가 깨지지 않도록 범위를 강제한다."""
        self.font_size = max(9, min(48, int(self.font_size or 15)))
        self.scale = max(0.7, min(2.0, float(self.scale or 1.0)))
        self.corner_radius = max(0, min(40, int(self.corner_radius or 0)))
        self.opacity = max(0.3, min(1.0, float(self.opacity or 1.0)))
        self.button_text = (self.button_text or "저장하기")[:20]
        self.folder_suffix = (self.folder_suffix or "")[:20]
        for attr, fallback in (
            ("button_color", "#2F6FED"),
            ("text_color", "#FFFFFF"),
            ("hover_color", "#1E56C8"),
        ):
            value = str(getattr(self, attr) or "")
            if not (len(value) == 7 and value.startswith("#")):
                setattr(self, attr, fallback)
        return self


# --- 작업(Job) 모델 ---

SAVE_SEPARATE = "separate"   # 파일마다 폴더 하나
SAVE_TOGETHER = "together"   # 상위 폴더 하나에 모아서


@dataclass
class SplitJob:
    """분할 작업 하나 = PDF 여러 개 + 저장 방식."""

    sources: List[str]
    mode: str = SAVE_SEPARATE
    parent_folder: str = ""      # SAVE_TOGETHER 일 때 상위 폴더 이름
    output_root: str = ""        # 실제 저장 루트 (보통 데스크탑)
    folder_suffix: str = "저장"
    pad_numbers: bool = False


@dataclass
class SplitResult:
    source: str
    folder: str
    pages: int
    files: List[str] = field(default_factory=list)
    error: str = ""


@dataclass
class PreviewItem:
    """저장하기 전 미리보기 한 줄 = 원본 PDF 하나. 파일은 아직 만들지 않는다."""

    source: str
    folder: str                  # 만들어질 폴더의 전체 경로
    pages: int = 0
    first_name: str = ""         # '기안 - 1.pdf'
    last_name: str = ""          # '기안 - 12.pdf'
    error: str = ""              # 미리 읽어 보다 발견한 문제 (비밀번호·손상 등)
