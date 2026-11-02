"""PDF → PowerPoint(.pptx) 변환 엔진 (core 레이어).

두 가지 방식:
  * editable (기본) : 페이지에서 글자만 지운 배경 이미지 + 그 위에 원래 자리에
                      편집 가능한 텍스트 상자. 그림·도형·표 선은 배경에 그대로 남는다.
  * image           : 페이지를 통째로 한 장의 그림으로 (모양은 100% 같지만 편집 불가).
                      페이지 글자는 발표자 노트에 넣어 검색·복사할 수 있게 한다.

메모리 제약 때문에 pymupdf / python-pptx 는 변환할 때만 import 하고,
페이지 이미지는 1장씩 만들어 바로 슬라이드에 넣는다.
"""

import gc
import io
import os
import re

from .errors import CancelledError, NotAPdfError, OutputError, PdfEncryptedError, PdfReadError

EMU_PER_PT = 12700
DEFAULT_DPI = 200
GC_EVERY = 10

_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_STYLE_SUFFIX = re.compile(
    r"[-,](Bold|Italic|Oblique|BoldItalic|BoldOblique|Regular|Roman|Light|Medium|"
    r"Semibold|SemiBold|Black|Heavy|Condensed|Narrow|MT|PS|PSMT)+$",
    re.IGNORECASE,
)
_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])")
# XML 에 넣을 수 없는 제어 문자
_BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

# PDF 내장 폰트 이름 → 윈도우/맥에 있는 폰트 이름
_FONT_ALIASES = {
    "ArialMT": "Arial",
    "Arial": "Arial",
    "Helvetica": "Arial",
    "TimesNewRomanPSMT": "Times New Roman",
    "TimesNewRoman": "Times New Roman",
    "Times": "Times New Roman",
    "CourierNewPSMT": "Courier New",
    "Courier": "Courier New",
    "SymbolMT": "Symbol",
    "Wingdings": "Wingdings",
    "ArialNarrow": "Arial Narrow",
    "SegoeUISymbol": "Segoe UI Symbol",
    "SegoeUI": "Segoe UI",
    "CambriaMath": "Cambria Math",
}

# 윈도우·맥·오피스에 기본으로 들어 있는 폰트 (설치 확인 없이 그대로 써도 되는 것)
_COMMON_FONTS = {
    "arial", "arial narrow", "arial black", "calibri", "calibri light", "cambria",
    "cambria math", "candara", "consolas", "constantia", "corbel", "courier new",
    "georgia", "segoe ui", "segoe ui symbol", "tahoma", "times new roman",
    "trebuchet ms", "verdana", "symbol", "wingdings", "wingdings 2", "wingdings 3",
    "garamond", "century gothic", "book antiqua", "palatino linotype", "helvetica",
    "helvetica neue", "malgun gothic", "맑은 고딕", "batang", "gulim", "dotum",
    "apple sd gothic neo", "menlo", "monaco",
}
_SERIF_HINT = re.compile(r"roman|serif(?!.*sans)|times|georgia|garamond|minion|caslon|"
                         r"baskerville|bodoni|didot|palatino|antiqua|batang|myeongjo|book",
                         re.IGNORECASE)
_installed_cache = None


def page_count(path):
    doc = _open(path)
    try:
        return doc.page_count
    finally:
        doc.close()


def default_output_path(src_path, out_dir=None):
    stem = os.path.splitext(os.path.basename(src_path))[0]
    out_dir = out_dir or os.path.dirname(os.path.abspath(src_path))
    return os.path.join(out_dir, stem + ".pptx")


def convert_pdf_to_pptx(src_path, out_path, mode="editable", dpi=DEFAULT_DPI,
                        on_page=None, is_cancelled=None):
    """PDF 를 .pptx 로 바꿔 out_path 에 저장하고 그 경로를 돌려준다.

    on_page(page_number, total_pages) : 진행 상황 콜백
    is_cancelled() -> bool            : True 면 중단
    """
    import pymupdf  # 지연 임포트
    from pptx import Presentation

    if mode not in ("editable", "image"):
        raise ValueError("mode 는 'editable' 또는 'image' 여야 합니다.")

    doc = _open(src_path)
    try:
        total = doc.page_count
        if total == 0:
            raise PdfReadError("페이지가 없는 PDF 입니다.", src_path)

        prs = Presentation()
        first = doc[0].rect
        prs.slide_width = int(first.width * EMU_PER_PT)
        prs.slide_height = int(first.height * EMU_PER_PT)
        blank = prs.slide_layouts[6]
        zoom = dpi / 72.0

        for index in range(total):
            if is_cancelled and is_cancelled():
                raise CancelledError("사용자가 작업을 취소했습니다.")
            page = doc[index]
            slide = prs.slides.add_slide(blank)
            # 페이지 크기가 첫 장과 다르면 슬라이드 안에 비율 맞춰 넣는다
            scale = min(prs.slide_width / (page.rect.width * EMU_PER_PT),
                        prs.slide_height / (page.rect.height * EMU_PER_PT))
            off_x = (prs.slide_width - page.rect.width * EMU_PER_PT * scale) / 2
            off_y = (prs.slide_height - page.rect.height * EMU_PER_PT * scale) / 2

            def emu(v, off):
                return int(off + v * EMU_PER_PT * scale)

            lines = []
            if mode == "editable":
                lines = _extract_lines(page)
                _erase_text(pymupdf, page, lines)
            else:
                text = _BAD_XML.sub("", page.get_text()).strip()
                if text:
                    slide.notes_slide.notes_text_frame.text = text

            png = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).tobytes("png")
            slide.shapes.add_picture(
                io.BytesIO(png), emu(0, off_x), emu(0, off_y),
                int(page.rect.width * EMU_PER_PT * scale),
                int(page.rect.height * EMU_PER_PT * scale),
            )
            del png

            for line in lines:
                _add_line(slide, line, emu, off_x, off_y, scale)

            if on_page:
                on_page(index + 1, total)
            if (index + 1) % GC_EVERY == 0:
                gc.collect()

        out_dir = os.path.dirname(os.path.abspath(out_path))
        try:
            os.makedirs(out_dir, exist_ok=True)
            prs.save(out_path)
        except OSError as exc:
            raise OutputError("PowerPoint 파일을 저장하지 못했습니다.", str(exc))
        return out_path
    finally:
        doc.close()
        gc.collect()


# --- 내부 도우미 -------------------------------------------------------------


def _open(path):
    import pymupdf

    if not os.path.isfile(path):
        raise NotAPdfError("파일을 찾을 수 없습니다.", path)
    if os.path.splitext(path)[1].lower() != ".pdf":
        raise NotAPdfError("PDF 파일이 아닙니다.", path)
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise PdfReadError("PDF 를 읽을 수 없습니다. 파일이 손상됐을 수 있습니다.", str(exc))
    if doc.needs_pass and not doc.authenticate(""):
        doc.close()
        raise PdfEncryptedError("비밀번호가 걸린 PDF 라 변환할 수 없습니다.",
                                os.path.basename(path))
    return doc


def _extract_lines(page):
    """가로로 쓰인 글자 줄만 모은다. 세로/회전 글자는 배경 그림에 남겨 둔다."""
    out = []
    data = page.get_text("dict", flags=0)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            dx, dy = line.get("dir", (1, 0))
            if abs(dy) > 0.01 or dx < 0:
                continue
            spans = []
            for s in line.get("spans", []):
                text = _BAD_XML.sub("", s.get("text", ""))
                if not text:
                    continue
                spans.append({
                    "text": text,
                    "size": s.get("size", 10),
                    "font": s.get("font", ""),
                    "flags": s.get("flags", 0),
                    "color": s.get("color", 0),
                    "bbox": s.get("bbox"),
                    "origin": s.get("origin"),
                    "ascender": s.get("ascender", 0.9),
                })
            if not spans or not "".join(sp["text"] for sp in spans).strip():
                continue
            out.append({"bbox": line["bbox"], "spans": spans})
    return out


def _erase_text(pymupdf, page, lines):
    """옮겨 적을 글자만 페이지에서 지운다 (그림·선은 그대로)."""
    if not lines:
        return
    for line in lines:
        for sp in line["spans"]:
            r = pymupdf.Rect(sp["bbox"])
            if r.is_empty:
                continue
            # 이웃 글자를 같이 지우지 않도록 위아래를 살짝 줄인다
            h = r.height * 0.15
            page.add_redact_annot(pymupdf.Rect(r.x0, r.y0 + h, r.x1, r.y1 - h), fill=False)
    kwargs = {"images": pymupdf.PDF_REDACT_IMAGE_NONE}
    if hasattr(pymupdf, "PDF_REDACT_LINE_ART_NONE"):
        kwargs["graphics"] = pymupdf.PDF_REDACT_LINE_ART_NONE
    page.apply_redactions(**kwargs)


def _font_name(raw):
    """PDF 폰트 이름을 PowerPoint 에서 쓸 이름으로. 없는 폰트면 비슷한 기본 폰트로."""
    name = _SUBSET_PREFIX.sub("", raw or "")
    if name in _FONT_ALIASES:
        return _FONT_ALIASES[name]
    base = _STYLE_SUFFIX.sub("", name)
    if base in _FONT_ALIASES:
        return _FONT_ALIASES[base]
    base = base.split(",")[0].strip()
    nice = _CAMEL_SPLIT.sub(" ", base)
    key = nice.lower()
    if key in _COMMON_FONTS or _squash(key) in _installed_fonts():
        return nice
    if not re.search("[A-Za-z]", nice):  # '2,Bold' 처럼 이름이 깨진 폰트
        return "Arial"
    return "Georgia" if _SERIF_HINT.search(name) else "Arial"


def _squash(text):
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def _installed_fonts():
    """이 컴퓨터에 깔린 폰트 이름 (공백·기호 뺀 소문자). 못 읽으면 빈 집합."""
    global _installed_cache
    if _installed_cache is not None:
        return _installed_cache
    found = set()
    try:
        if os.name == "nt":
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, key_path) as k:
                        i = 0
                        while True:
                            try:
                                label = winreg.EnumValue(k, i)[0]
                            except OSError:
                                break
                            i += 1
                            for part in re.sub(r"\(.*?\)", "", label).split("&"):
                                part = _STYLE_SUFFIX.sub("", part.strip().replace(" ", ""))
                                found.add(_squash(part))
                except OSError:
                    pass
        else:
            dirs = ["/System/Library/Fonts", "/Library/Fonts",
                    os.path.expanduser("~/Library/Fonts"), "/usr/share/fonts",
                    os.path.expanduser("~/.fonts")]
            for d in dirs:
                for _root, _subs, files in os.walk(d):
                    for f in files:
                        stem = os.path.splitext(f)[0]
                        found.add(_squash(_STYLE_SUFFIX.sub("", stem)))
    except Exception:
        pass
    found.discard("")
    _installed_cache = found
    return found


def _add_line(slide, line, emu, off_x, off_y, scale):
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
    from pptx.util import Pt

    x0, y0, x1, y1 = line["bbox"]
    first = line["spans"][0]
    size = max(first["size"], 1)
    # 글자 기준선(origin) 에서 위로 올라가 텍스트 상자 위치를 정한다
    top = first["origin"][1] - size * 1.0 if first.get("origin") else y0
    width = (x1 - x0) * 1.08 + size * 0.5
    height = size * 1.25

    box = slide.shapes.add_textbox(emu(x0, off_x), emu(top, off_y),
                                   int(width * EMU_PER_PT * scale),
                                   int(height * EMU_PER_PT * scale))
    tf = box.text_frame
    tf.word_wrap = False
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.line_spacing = 1.0

    main_size = max(sp["size"] for sp in line["spans"])
    for sp in line["spans"]:
        run = p.add_run()
        run.text = sp["text"]
        f = run.font
        size = sp["size"]
        if sp["flags"] & 1 and size < main_size * 0.9:
            # 위첨자: PowerPoint 가 글자를 2/3 로 줄여 올려 준다
            run._r.get_or_add_rPr().set("baseline", "30000")
            size = min(size * 1.5, main_size)
        f.size = Pt(round(size * scale * 2) / 2 or 1)
        f.name = _font_name(sp["font"])
        raw = (sp["font"] or "").lower()
        f.bold = bool(sp["flags"] & 16) or "bold" in raw or "black" in raw or "heavy" in raw
        f.italic = bool(sp["flags"] & 2) or "italic" in raw or "oblique" in raw
        c = sp["color"] or 0
        f.color.rgb = RGBColor((c >> 16) & 255, (c >> 8) & 255, c & 255)
