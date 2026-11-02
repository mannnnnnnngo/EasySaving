"""파일/폴더 이름 규칙.

규칙 (요구사항):
  원본이 '기안.pdf' 이고 2페이지라면
    데스크탑/기안 저장/기안 - 1.pdf
    데스크탑/기안 저장/기안 - 2.pdf
"""

import os
import re

# 윈도우에서 파일명에 못 쓰는 문자 + 제어문자
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# 윈도우 예약어
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
MAX_STEM = 120  # 경로 길이 제한(특히 윈도우 260자)을 감안한 여유 있는 상한


def sanitize(name, fallback="문서"):
    """어떤 OS에서도 안전한 파일/폴더 이름으로 정리한다."""
    name = _INVALID.sub("_", (name or "").strip())
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        return fallback
    if name.upper().split(".")[0] in _RESERVED:
        name = "_" + name
    if len(name) > MAX_STEM:
        name = name[:MAX_STEM].strip()
    return name or fallback


def stem_of(path):
    """'/a/b/기안.pdf' -> '기안'"""
    return sanitize(os.path.splitext(os.path.basename(path))[0])


def folder_name(stem, suffix="저장"):
    """'기안' -> '기안 저장'"""
    suffix = (suffix or "").strip()
    return sanitize(f"{stem} {suffix}".strip() if suffix else stem)


def page_filename(stem, page_number, total_pages=0, pad=False):
    """'기안' + 1 -> '기안 - 1.pdf' (pad=True 면 '기안 - 01.pdf')"""
    if pad and total_pages > 9:
        width = len(str(total_pages))
        number = str(page_number).zfill(width)
    else:
        number = str(page_number)
    return f"{sanitize(stem)} - {number}.pdf"


def unique_path(path):
    """이미 존재하면 ' (2)', ' (3)' … 을 붙여 겹치지 않는 경로를 만든다."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"
