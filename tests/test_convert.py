"""PDF → PowerPoint 변환 + 업데이트 로직 검증 (창을 띄우지 않는 테스트).

실행: python -m tests.test_convert
"""

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easysaving.core import pdf_to_pptx                       # noqa: E402
from easysaving.core.errors import NotAPdfError, CancelledError  # noqa: E402
from easysaving.services import convert_service, update_service  # noqa: E402
from easysaving.platform_layer import memory                  # noqa: E402

failures = []


def check(label, condition, extra=""):
    print(f"{'  ✓' if condition else '  ✗'} {label}{(' — ' + extra) if extra else ''}")
    if not condition:
        failures.append(label)


def make_pdf(path, pages=3):
    import pymupdf

    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=960, height=540)
        page.draw_rect(pymupdf.Rect(40, 300, 400, 500), color=(0, 0, 1), fill=(0.8, 0.9, 1))
        page.insert_text((60, 80), f"Slide title {i + 1}", fontsize=36, color=(0.1, 0.1, 0.4))
        page.insert_text((60, 140), "Body text with a number 42", fontsize=16)
    doc.save(path)
    doc.close()
    return path


def slide_texts(path):
    from pptx import Presentation

    prs = Presentation(path)
    out = []
    for slide in prs.slides:
        texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        out.append((texts, notes, [sh.shape_type for sh in slide.shapes]))
    return prs, out


def main():
    tmp = tempfile.mkdtemp(prefix="es_convert_")
    try:
        src = make_pdf(os.path.join(tmp, "기안 문서.pdf"), pages=3)

        print("\n[편집 가능 모드]")
        out = os.path.join(tmp, "editable.pptx")
        seen = []
        t0 = time.time()
        pdf_to_pptx.convert_pdf_to_pptx(src, out, on_page=lambda p, t: seen.append((p, t)))
        prs, slides = slide_texts(out)
        check("슬라이드 3장", len(slides) == 3)
        check("16:9 크기 (960x540pt)", prs.slide_width == 960 * 12700 and prs.slide_height == 540 * 12700)
        check("제목이 편집 가능한 글자로", any("Slide title 2" in t for t in slides[1][0]))
        check("본문 글자", any("Body text with a number 42" in t for t in slides[0][0]))
        check("배경 그림 1장씩", all(13 in kinds for _t, _n, kinds in slides))
        check("진행 콜백", seen == [(1, 3), (2, 3), (3, 3)], str(seen))
        print(f"    ({time.time() - t0:.2f}초)")

        print("\n[그림 그대로 모드]")
        out2 = os.path.join(tmp, "image.pptx")
        pdf_to_pptx.convert_pdf_to_pptx(src, out2, mode="image")
        _prs, slides2 = slide_texts(out2)
        check("텍스트 상자 없음", all(not t for t, _n, _k in slides2))
        check("글자는 발표자 노트에", "Slide title 1" in slides2[0][1])

        print("\n[오류 처리]")
        try:
            pdf_to_pptx.convert_pdf_to_pptx(os.path.join(tmp, "없음.pdf"), out)
            check("없는 파일 → NotAPdfError", False)
        except NotAPdfError:
            check("없는 파일 → NotAPdfError", True)
        bad = os.path.join(tmp, "깨짐.pdf")
        with open(bad, "wb") as fp:
            fp.write(b"not a pdf at all")
        try:
            pdf_to_pptx.convert_pdf_to_pptx(bad, out)
            check("손상된 PDF → 오류", False)
        except Exception as exc:
            check("손상된 PDF → 오류", hasattr(exc, "message"), type(exc).__name__)
        try:
            pdf_to_pptx.convert_pdf_to_pptx(src, out, is_cancelled=lambda: True)
            check("취소", False)
        except CancelledError:
            check("취소", True)

        print("\n[변환 서비스 (스레드)]")
        svc = convert_service.ConvertService()
        open(os.path.join(tmp, "기안 문서.pptx"), "wb").close()     # 이름 충돌 만들기
        svc.start([src, bad], tmp)
        events = []
        deadline = time.time() + 60
        while time.time() < deadline:
            ev = svc.events.get(timeout=60)
            events.append(ev)
            if ev[0] in (convert_service.EV_DONE, convert_service.EV_CANCELLED):
                break
        results = events[-1][1]
        check("완료 이벤트", events[-1][0] == convert_service.EV_DONE)
        check("이름 충돌 → '기안 문서 (2).pptx'",
              results[0].output.endswith("기안 문서 (2).pptx") and os.path.exists(results[0].output))
        check("실패한 파일은 오류로 보고", bool(results[1].error)
              and any(e[0] == convert_service.EV_ERROR for e in events))

        print("\n[폰트 이름]")
        check("ArialMT → Arial", pdf_to_pptx._font_name("ABCDEF+ArialMT") == "Arial")
        check("Calibri-Bold → Calibri", pdf_to_pptx._font_name("Calibri-Bold") == "Calibri")
        check("없는 세리프 → Georgia", pdf_to_pptx._font_name("FKRomanStandard-Light") == "Georgia")
        check("없는 산세리프 → Arial", pdf_to_pptx._font_name("Saans-Regular") == "Arial")
        check("깨진 이름 → Arial", pdf_to_pptx._font_name("2,Bold") == "Arial")

        print("\n[업데이트 버전 비교]")
        check("1.1.0 > 1.0.9", update_service.is_newer("1.1.0", "1.0.9"))
        check("v1.10.0 > 1.9.0", update_service.is_newer("v1.10.0", "1.9.0"))
        check("같으면 아님", not update_service.is_newer("1.1.0", "1.1.0"))
        check("옛 버전 아님", not update_service.is_newer("1.0.0", "1.1.0"))
        check("설치 방식 판별", update_service.install_kind() in ("git", "source"))

        rss = memory.rss_mb()
        check("메모리 100MB 이하", rss is None or rss <= 100, f"{rss}MB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + ("모두 통과" if not failures else f"실패 {len(failures)}개: {failures}"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
