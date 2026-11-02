"""색/글꼴 등 UI 공통 값."""

import sys
import tkinter.font as tkfont

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# 기본 팔레트 (밝은 테마)
BG = "#FFFFFF"
CARD = "#F4F6F9"
CARD_HOVER = "#E9EDF3"
TEXT = "#16181D"
MUTED = "#6B7280"
BORDER = "#DFE3EA"
ACCENT = "#2F6FED"
ACCENT_DARK = "#1E56C8"
DANGER = "#D94141"
SUCCESS = "#1F9D55"
WARN = "#B7791F"

# 버튼 기본 색 프리셋 (설정 창에서 고를 수 있게)
PRESET_COLORS = [
    "#2F6FED", "#1F9D55", "#D94141", "#7C3AED",
    "#F59E0B", "#0EA5E9", "#EC4899", "#111827",
]
PRESET_TEXT_COLORS = ["#FFFFFF", "#111827", "#FFF7E6", "#0B1B33"]

_family_cache = None


def family():
    """한글이 예쁘게 나오는 글꼴을 고른다."""
    global _family_cache
    if _family_cache:
        return _family_cache
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()
    for name in ("Apple SD Gothic Neo", "맑은 고딕", "Malgun Gothic", "AppleGothic",
                 "Noto Sans KR", "Segoe UI", "Helvetica"):
        if name in available:
            _family_cache = name
            return name
    _family_cache = "TkDefaultFont"
    return _family_cache


def font(size=13, weight="normal"):
    return (family(), size, weight)


def title_font(size=19):
    return (family(), size, "bold")


def mix(color_a, color_b, ratio=0.5):
    """두 색을 섞는다 (hover 색 자동 생성 등)."""
    try:
        a = _rgb(color_a)
        b = _rgb(color_b)
    except Exception:
        return color_a
    out = tuple(int(round(a[i] * (1 - ratio) + b[i] * ratio)) for i in range(3))
    return "#%02X%02X%02X" % out


def darken(color, ratio=0.18):
    return mix(color, "#000000", ratio)


def lighten(color, ratio=0.18):
    return mix(color, "#FFFFFF", ratio)


def readable_text_on(color):
    """배경색 위에서 잘 보이는 글자색(검정/흰색)을 고른다."""
    try:
        r, g, b = _rgb(color)
    except Exception:
        return "#FFFFFF"
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#111827" if luminance > 0.62 else "#FFFFFF"


def _rgb(color):
    color = color.strip()
    if not color.startswith("#") or len(color) != 7:
        raise ValueError(color)
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """캔버스에 둥근 사각형을 그린다 (알약 모양 버튼용)."""
    return round_rect_corners(canvas, x1, y1, x2, y2, radius,
                              (True, True, True, True), **kwargs)


def round_rect_corners(canvas, x1, y1, x2, y2, radius, corners, **kwargs):
    """모서리별로 둥글기를 다르게 준 사각형 (corners = 좌상, 우상, 우하, 좌하)."""
    radius = max(0, min(int(radius), int((x2 - x1) / 2), int((y2 - y1) / 2)))
    if radius == 0:
        return canvas.create_rectangle(x1, y1, x2, y2, width=0, **kwargs)
    tl, tr, br, bl = corners
    points = []

    def corner(x, y, rounded, before, after):
        # smooth=True 에서 같은 점을 반복하면 그 모서리는 각지게 남는다
        if rounded:
            points.extend(before + [x, y] + after)
        else:
            points.extend([x, y, x, y, x, y])

    corner(x1, y1, tl, [x1, y1 + radius], [x1 + radius, y1])
    corner(x2, y1, tr, [x2 - radius, y1], [x2, y1 + radius])
    corner(x2, y2, br, [x2, y2 - radius], [x2 - radius, y2])
    corner(x1, y2, bl, [x1 + radius, y2], [x1, y2 - radius])
    return canvas.create_polygon(points, smooth=True, splinesteps=24, width=0, **kwargs)
