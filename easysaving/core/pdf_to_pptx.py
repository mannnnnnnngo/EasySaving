"""PDF → PowerPoint(.pptx) 변환 엔진 (core 레이어).

두 가지 방식:
  * editable (기본) : 페이지 속 하나하나를 따로 된 개체로 옮긴다.
                      - 사각형 → PowerPoint 사각형, 선 → 선, 그 밖의 도형(원·곡선·화살표 등) → 자유형 도형
                      - 사진·그림 → 그림 개체 (잘린 부분은 '자르기' 로)
                      - 글자 → 편집 가능한 텍스트 상자 (세로 글자는 회전된 상자)
                      배경 그림 한 장으로 깔지 않는다. 그라데이션처럼 도형으로 못 옮기는 것만
                      그 자리만 잘라 그림으로 넣는다. 도형이 너무 많은 페이지(MAX_SHAPES 초과)는
                      예전처럼 글자 뺀 페이지 그림 + 텍스트 상자로.
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
MAX_SHAPES = 2500          # 한 페이지 도형이 이보다 많으면 도형층을 그림 한 장으로

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

            if mode == "editable":
                _build_editable_slide(pymupdf, doc, page, slide, emu, off_x, off_y, scale, zoom)
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
    """글자 줄을 모은다. 세로/회전 글자는 방향(dir)을 같이 적어 회전된 상자로 만든다."""
    out = []
    data = page.get_text("dict", flags=0)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            dx, dy = line.get("dir", (1, 0))
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
            out.append({"bbox": line["bbox"], "spans": spans, "dir": (dx, dy)})
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
    dx, dy = line.get("dir", (1, 0))
    height = size * 1.25
    rotation = 0.0
    if abs(dy) <= 0.01 and dx > 0:
        # 글자 기준선(origin) 에서 위로 올라가 텍스트 상자 위치를 정한다
        left = x0
        top = first["origin"][1] - size * 1.0 if first.get("origin") else y0
        width = (x1 - x0) * 1.08 + size * 0.5
    else:
        # 세로·기울어진 글자: 가로 상자를 만든 뒤 줄 가운데를 축으로 돌린다
        import math
        rotation = math.degrees(math.atan2(dy, dx)) % 360
        length = abs(dx) * (x1 - x0) + abs(dy) * (y1 - y0) - size * min(abs(dx), abs(dy)) * 2
        length = max(length, size)
        width = length * 1.08 + size * 0.5
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        left, top = cx - width / 2, cy - height / 2

    box = slide.shapes.add_textbox(emu(left, off_x), emu(top, off_y),
                                   int(width * EMU_PER_PT * scale),
                                   int(height * EMU_PER_PT * scale))
    if rotation:
        box.rotation = rotation
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


# --- 편집 가능 슬라이드: 페이지 속 개체를 하나씩 옮기기 ---------------------------

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_NO_FILL = "<a:noFill/>"
_NO_LINE = "<a:ln><a:noFill/></a:ln>"


def _build_editable_slide(pymupdf, doc, page, slide, emu, off_x, off_y, scale, zoom):
    """도형·그림·글자를 PDF 에 그려진 순서대로, 각각 따로 된 개체로 슬라이드에 넣는다."""
    lines = _extract_lines(page)
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = None
    # 돌려 놓은 페이지: pymupdf 는 돌리기 전 좌표를 주므로 화면 좌표로 바꾼다
    m = page.rotation_matrix if page.rotation % 360 else None
    if m is not None:
        lines = [_rotate_line(ln, m) for ln in lines]
        if drawings is not None:
            drawings = [_rotate_drawing(pymupdf, d, m) for d in drawings]
    if drawings is None or len(drawings) > MAX_SHAPES:
        # 도형이 지나치게 많은 페이지 (지도·복잡한 도표 등): 글자 뺀 페이지 그림 + 텍스트 상자
        _erase_text(pymupdf, page, lines)
        _add_render(pymupdf, page, slide, page.rect, emu, off_x, off_y, scale, zoom)
        for line in lines:
            _add_line(slide, line, emu, off_x, off_y, scale)
        return

    try:
        log = page.get_bboxlog()
    except Exception:
        log = []
    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:
        infos = []
    if m is not None:
        log = [(t, tuple(pymupdf.Rect(r) * m)) for t, r in log]
        for info in infos:
            info["bbox"] = tuple(pymupdf.Rect(info["bbox"]) * m)
            info["transform"] = tuple(pymupdf.Matrix(info["transform"]) * m)

    # get_drawings 의 seqno 와 get_bboxlog 의 순번은 같은 '그리기 명령 번호' 다
    items = [(d.get("seqno", 0), "path", d) for d in drawings]
    image_slots = [(i, r) for i, (t, r) in enumerate(log) if t == "fill-image"]
    matched = len(image_slots) == len(infos)
    for n, (i, r) in enumerate(image_slots):
        items.append((i, "image", (infos[n] if matched else None, r)))
    for i, (t, r) in enumerate(log):
        if t in ("fill-shade", "fill-imagemask"):
            items.append((i, "render", (None, r)))
    items.sort(key=lambda it: it[0])

    page_rect = page.rect
    pending = []  # 그림으로 잘라 넣을 자리: (자리 표시 개체, 영역)
    for _seq, kind, data in items:
        ok = True
        if kind == "path":
            if _is_page_background(data, page_rect):
                continue
            try:
                _add_path(slide, data, emu, off_x, off_y, scale)
            except Exception:
                ok, area = False, data.get("rect")
        elif kind == "image":
            info, area = data
            try:
                ok = info is not None and _add_image(pymupdf, doc, slide, info, area, page_rect,
                                                     emu, off_x, off_y, scale)
            except Exception:
                ok = False
        else:
            ok, area = False, data[1]
        if not ok and area is not None:
            # 쌓는 순서를 지키려고 지금 자리에 빈 개체를 두고, 나중에 그림으로 바꾼다
            from pptx.util import Emu
            pending.append((slide.shapes.add_textbox(Emu(0), Emu(0), Emu(1), Emu(1)),
                            pymupdf.Rect(area)))

    if pending:
        _erase_text(pymupdf, page, lines)
        for holder, rect in pending:
            pic = _add_render(pymupdf, page, slide, rect & page_rect, emu, off_x, off_y, scale, zoom)
            if pic is not None:
                holder._element.addprevious(pic._element)
            holder._element.getparent().remove(holder._element)

    for line in lines:
        _add_line(slide, line, emu, off_x, off_y, scale)


def _rotate_line(line, m):
    """글자 줄 좌표를 화면 좌표로 (지울 때 쓰는 span bbox 는 원래 좌표 그대로)."""
    import pymupdf

    dx, dy = line.get("dir", (1, 0))
    v = pymupdf.Point(dx, dy) * pymupdf.Matrix(m.a, m.b, m.c, m.d, 0, 0)
    spans = []
    for sp in line["spans"]:
        sp = dict(sp)
        if sp.get("origin"):
            sp["origin"] = tuple(pymupdf.Point(sp["origin"]) * m)
        spans.append(sp)
    return {"bbox": tuple(pymupdf.Rect(line["bbox"]) * m), "spans": spans,
            "dir": (round(v.x, 6), round(v.y, 6))}


def _rotate_drawing(pymupdf, d, m):
    d = dict(d)
    items = []
    for it in d.get("items") or []:
        op = it[0]
        if op == "re":
            items.append((op, pymupdf.Rect(it[1]) * m) + tuple(it[2:]))
        elif op == "qu":
            items.append((op, pymupdf.Quad(it[1]) * m))
        else:
            items.append((op,) + tuple(pymupdf.Point(p) * m for p in it[1:]))
    d["items"] = items
    if d.get("rect") is not None:
        d["rect"] = pymupdf.Rect(d["rect"]) * m
    return d


def _add_render(pymupdf, page, slide, rect, emu, off_x, off_y, scale, zoom):
    """페이지의 rect 부분만 그림으로 렌더링해 넣는다."""
    if rect.is_empty or rect.width < 0.5 or rect.height < 0.5:
        return None
    png = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False).tobytes("png")
    pic = slide.shapes.add_picture(io.BytesIO(png), emu(rect.x0, off_x), emu(rect.y0, off_y),
                                   int(rect.width * EMU_PER_PT * scale),
                                   int(rect.height * EMU_PER_PT * scale))
    del png
    return pic


def _is_page_background(d, page_rect):
    """페이지 전체를 덮는 흰 사각형 (흔한 '종이' 배경) 은 건너뛴다."""
    if d.get("color") is not None or d.get("fill") is None:
        return False
    if len(d.get("items") or []) != 1 or d["items"][0][0] != "re":
        return False
    fill = _rgb(d["fill"])
    if fill is None or min(fill) < 250:
        return False
    r = d["rect"]
    return r.width * r.height >= page_rect.width * page_rect.height * 0.9


def _rgb(color):
    """pymupdf 색 (0~1 실수 1·3·4 개) → (r, g, b) 0~255."""
    if color is None:
        return None
    c = list(color)
    if len(c) == 1:
        c = c * 3
    elif len(c) == 4:  # CMYK
        k = c[3]
        c = [(1 - c[0]) * (1 - k), (1 - c[1]) * (1 - k), (1 - c[2]) * (1 - k)]
    elif len(c) != 3:
        return None
    return tuple(max(0, min(255, int(round(v * 255)))) for v in c)


def _color_xml(rgb, opacity):
    alpha = ""
    if opacity is not None and opacity < 0.999:
        alpha = f'<a:alpha val="{max(0, int(round(opacity * 100000)))}"/>'
    return f'<a:srgbClr val="{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}">{alpha}</a:srgbClr>'


def _line_xml(d, scale):
    rgb = _rgb(d.get("color"))
    if rgb is None or d.get("type") == "f":
        return _NO_LINE
    width = d.get("width") or 0
    width_pt = max(width * scale, 0.25)  # 폭 0 = 가장 가는 선
    cap = d.get("lineCap")
    cap = cap[0] if isinstance(cap, (tuple, list)) and cap else (cap or 0)
    cap_attr = {0: "flat", 1: "rnd", 2: "sq"}.get(int(cap), "flat")
    dash = ""
    nums = [float(x) for x in _NUM.findall((d.get("dashes") or "").split("]")[0])]
    nums = [x for x in nums if x > 0]
    if nums:
        if len(nums) % 2:
            nums = nums * 2
        w = max(width, 0.1)
        parts = "".join(f'<a:ds d="{int(nums[i] / w * 100000)}" sp="{int(nums[i + 1] / w * 100000)}"/>'
                        for i in range(0, len(nums), 2))
        dash = f"<a:custDash>{parts}</a:custDash>"
    join = int(d.get("lineJoin") or 0)
    join_xml = {1: "<a:round/>", 2: "<a:bevel/>"}.get(join, '<a:miter lim="800000"/>')
    return (f'<a:ln w="{int(width_pt * EMU_PER_PT)}" cap="{cap_attr}">'
            f'<a:solidFill>{_color_xml(rgb, d.get("stroke_opacity"))}</a:solidFill>'
            f'{dash}{join_xml}</a:ln>')


def _fill_xml(d):
    rgb = _rgb(d.get("fill"))
    if rgb is None or d.get("type") == "s":
        return _NO_FILL
    return f'<a:solidFill>{_color_xml(rgb, d.get("fill_opacity"))}</a:solidFill>'


def _restyle(shape, geom_xml, fill_xml, line_xml):
    """python-pptx 가 붙이는 테마 스타일(파란 채우기·그림자)을 떼고 모양·채우기·선을 직접 정한다."""
    from pptx.oxml import parse_xml

    el = shape._element
    for style in el.findall(f"{{{_P_NS}}}style"):
        el.remove(style)
    sp_pr = el.spPr
    for child in list(sp_pr):
        if not child.tag.endswith("}xfrm"):
            sp_pr.remove(child)
    for xml in (geom_xml, fill_xml, line_xml):
        if xml:
            sp_pr.append(parse_xml(f'<a:wrap xmlns:a="{_A_NS}">{xml}</a:wrap>')[0])


def _quad_is_rect(q):
    return (abs(q.ul.y - q.ur.y) < 0.01 and abs(q.ll.y - q.lr.y) < 0.01
            and abs(q.ul.x - q.ll.x) < 0.01 and abs(q.ur.x - q.lr.x) < 0.01)


def _add_path(slide, d, emu, off_x, off_y, scale):
    """PDF 경로 하나 → PowerPoint 도형 하나 (사각형 / 선 / 자유형)."""
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.util import Emu

    path_items = d.get("items") or []
    if not path_items:
        return
    fill_xml = _fill_xml(d)
    line_xml = _line_xml(d, scale)
    if fill_xml == _NO_FILL and line_xml == _NO_LINE:
        return  # 보이지 않는 경로

    def box(r):
        x0, y0 = emu(r.x0, off_x), emu(r.y0, off_y)
        return x0, y0, max(emu(r.x1, off_x) - x0, 1), max(emu(r.y1, off_y) - y0, 1)

    # 사각형 하나 → 진짜 사각형 개체
    if len(path_items) == 1 and path_items[0][0] in ("re", "qu"):
        op, geo = path_items[0][0], path_items[0][1]
        if op == "re" or _quad_is_rect(geo):
            x0, y0, w, h = box(geo if op == "re" else geo.rect)
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x0), Emu(y0), Emu(w), Emu(h))
            _restyle(shape, '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>', fill_xml, line_xml)
            shape.name = "Rectangle %d" % (shape.shape_id - 1)
            return

    # 직선 하나 (선만) → 선 개체
    if len(path_items) == 1 and path_items[0][0] == "l" and fill_xml == _NO_FILL:
        p1, p2 = path_items[0][1], path_items[0][2]
        conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                          Emu(emu(p1.x, off_x)), Emu(emu(p1.y, off_y)),
                                          Emu(emu(p2.x, off_x)), Emu(emu(p2.y, off_y)))
        _restyle(conn, '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>', None, line_xml)
        conn.name = "Line %d" % (conn.shape_id - 1)
        return

    # 나머지 (원·곡선·다각형·화살표 등) → 자유형 도형 하나, 곡선은 베지어 그대로
    x0, y0, w, h = box(d["rect"])

    def pt(p):
        return f'<a:pt x="{emu(p.x, off_x) - x0}" y="{emu(p.y, off_y) - y0}"/>'

    closing = bool(d.get("closePath")) or fill_xml != _NO_FILL
    cmds, cur = [], None
    for it in path_items:
        op = it[0]
        if op in ("re", "qu"):
            q = it[1].quad if op == "re" else it[1]
            if cur is not None and closing:
                cmds.append("<a:close/>")
            cmds.append(f"<a:moveTo>{pt(q.ul)}</a:moveTo>")
            cmds += [f"<a:lnTo>{pt(c)}</a:lnTo>" for c in (q.ur, q.lr, q.ll)]
            cmds.append("<a:close/>")
            cur = None
            continue
        start = it[1]
        if cur is None or abs(cur.x - start.x) > 0.01 or abs(cur.y - start.y) > 0.01:
            if cur is not None and closing:
                cmds.append("<a:close/>")
            cmds.append(f"<a:moveTo>{pt(start)}</a:moveTo>")
        if op == "l":
            cmds.append(f"<a:lnTo>{pt(it[2])}</a:lnTo>")
            cur = it[2]
        elif op == "c":
            cmds.append(f"<a:cubicBezTo>{pt(it[2])}{pt(it[3])}{pt(it[4])}</a:cubicBezTo>")
            cur = it[4]
    if cur is not None and closing:
        cmds.append("<a:close/>")
    if not cmds:
        return
    geom = ('<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>'
            '<a:rect l="0" t="0" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{w}" h="{h}">{"".join(cmds)}</a:path></a:pathLst></a:custGeom>')
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x0), Emu(y0), Emu(w), Emu(h))
    _restyle(shape, geom, fill_xml, line_xml)
    shape.name = "Freeform %d" % (shape.shape_id - 1)


def _image_bytes(pymupdf, doc, xref):
    """PDF 속 그림 원본 → PNG/JPEG 바이트 (투명 마스크·CMYK 처리). 못 하면 None."""
    info = doc.extract_image(xref)
    if not info:
        return None
    smask = info.get("smask") or 0
    if not smask and info.get("ext") in ("jpeg", "jpg", "png") and info.get("colorspace", 3) in (1, 3):
        return info["image"]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if smask:
        try:
            mask = pymupdf.Pixmap(doc, smask)
            if pix.alpha:
                pix = pymupdf.Pixmap(pix, 0)
            pix = pymupdf.Pixmap(pix, mask)
        except Exception:
            pass
    return pix.tobytes("png")


def _add_image(pymupdf, doc, slide, info, visible, page_rect, emu, off_x, off_y, scale):
    """그림 하나 → 그림 개체 하나. 돌아가거나 뒤집힌 그림은 False (그 자리만 렌더링)."""
    from pptx.util import Emu

    import math

    xref = info.get("xref") or 0
    a, b, c, d, e, f = info.get("transform", (1, 0, 0, 1, 0, 0))
    if not xref or a * d - b * c <= 0:  # 뒤집힌 그림
        return False
    data = _image_bytes(pymupdf, doc, xref)
    if not data:
        return False
    if abs(b) > 1e-3 or abs(c) > 1e-3 or a <= 0:
        # 돌아간 그림 → 원래 크기 그림을 가운데 기준으로 돌린다
        w, h = math.hypot(a, b), math.hypot(c, d)
        cx, cy = e + (a + c) / 2, f + (b + d) / 2
        x0, y0 = emu(cx - w / 2, off_x), emu(cy - h / 2, off_y)
        pic = slide.shapes.add_picture(io.BytesIO(data), Emu(x0), Emu(y0),
                                       Emu(max(emu(cx + w / 2, off_x) - x0, 1)),
                                       Emu(max(emu(cy + h / 2, off_y) - y0, 1)))
        pic.rotation = math.degrees(math.atan2(b, a)) % 360
        return True
    full = pymupdf.Rect(info["bbox"])
    if full.is_empty:
        return True
    shown = full & pymupdf.Rect(visible) & page_rect
    if shown.is_empty:
        return True
    x0, y0 = emu(full.x0, off_x), emu(full.y0, off_y)
    pic = slide.shapes.add_picture(io.BytesIO(data), Emu(x0), Emu(y0),
                                   Emu(max(emu(full.x1, off_x) - x0, 1)),
                                   Emu(max(emu(full.y1, off_y) - y0, 1)))
    # 보이는 부분만 남기도록 자르기 (PowerPoint 의 '자르기' 로 되돌릴 수 있음)
    cl = (shown.x0 - full.x0) / full.width
    cr = (full.x1 - shown.x1) / full.width
    ct = (shown.y0 - full.y0) / full.height
    cb = (full.y1 - shown.y1) / full.height
    if max(cl, cr, ct, cb) > 0.002:
        pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom = cl, cr, ct, cb
        left, top = emu(shown.x0, off_x), emu(shown.y0, off_y)
        pic.left, pic.top = Emu(left), Emu(top)
        pic.width = Emu(max(emu(shown.x1, off_x) - left, 1))
        pic.height = Emu(max(emu(shown.y1, off_y) - top, 1))
    return True
