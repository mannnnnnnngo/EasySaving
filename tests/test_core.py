"""core / services 레이어 검증 (창을 띄우지 않는 테스트).

실행: python3 -m tests.test_core
"""

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easysaving.core import naming, splitter                      # noqa: E402
from easysaving.core.models import SAVE_SEPARATE, SAVE_TOGETHER, Settings  # noqa: E402
from easysaving.platform_layer import memory                      # noqa: E402
from easysaving.services import split_service                     # noqa: E402
from easysaving.services.config_service import ConfigService      # noqa: E402

PASS, FAIL = "  ✓", "  ✗"
failures = []


def check(label, condition, extra=""):
    print(f"{PASS if condition else FAIL} {label}{(' — ' + extra) if extra else ''}")
    if not condition:
        failures.append(label)


def make_pdf(path, pages):
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)   # A4
    with open(path, "wb") as fp:
        writer.write(fp)
    return path


def main():
    workdir = tempfile.mkdtemp(prefix="easysaving_test_")
    desktop = os.path.join(workdir, "Desktop")
    os.makedirs(desktop)
    print(f"작업 폴더: {workdir}\n")

    # --- 1. 이름 규칙 -------------------------------------------------------
    print("[1] 파일/폴더 이름 규칙")
    check("폴더 이름 '기안 저장'", naming.folder_name("기안") == "기안 저장")
    check("파일 이름 '기안 - 1.pdf'", naming.page_filename("기안", 1) == "기안 - 1.pdf")
    check("자릿수 맞춤 (12장 → 01)", naming.page_filename("기안", 1, 12, pad=True) == "기안 - 01.pdf")
    check("자릿수 맞춤 (124장 → 001)", naming.page_filename("기안", 1, 124, pad=True) == "기안 - 001.pdf")
    check("금지문자 제거", not any(c in naming.sanitize('보고/서:*?"<>|') for c in '/\\:*?"<>|'),
          naming.sanitize('보고/서:*?"<>|'))
    check("빈 이름은 기본값으로", naming.sanitize("   ") == "문서")
    check("윈도우 예약어 회피", naming.sanitize("CON") == "_CON")
    check("확장자 제거", naming.stem_of("/a/b/기안.pdf") == "기안")

    # --- 2. 124페이지 분할 --------------------------------------------------
    print("\n[2] 124페이지 PDF 를 1장씩 분할")
    src = make_pdf(os.path.join(workdir, "기안.pdf"), 124)
    settings = Settings()
    settings.output_root = desktop
    job = split_service.build_job([src], settings, SAVE_SEPARATE)

    service = split_service.SplitService()
    started = time.time()
    service.start(job)
    results, root = drain(service)
    elapsed = time.time() - started

    out_dir = os.path.join(desktop, "기안 저장")
    files = sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []
    check("'기안 저장' 폴더 생성", os.path.isdir(out_dir))
    check("124개 파일 저장", len(files) == 124, f"{len(files)}개")
    check("첫 파일 '기안 - 1.pdf'", os.path.exists(os.path.join(out_dir, "기안 - 1.pdf")))
    check("마지막 파일 '기안 - 124.pdf'", os.path.exists(os.path.join(out_dir, "기안 - 124.pdf")))
    check("각 파일이 정확히 1페이지",
          all(splitter.page_count(os.path.join(out_dir, f)) == 1 for f in files[:10]))
    print(f"    소요 시간 {elapsed:.2f}초, 메모리 {memory.rss_mb()}MB")

    # --- 3. 여러 파일 / 한 폴더에 모아 저장 ---------------------------------
    print("\n[3] 여러 파일 · 한 폴더에 모아 저장")
    a = make_pdf(os.path.join(workdir, "기안.pdf"), 2)
    b = make_pdf(os.path.join(workdir, "보고서.pdf"), 3)
    job = split_service.build_job([a, b], settings, SAVE_TOGETHER, "12월 문서")
    service = split_service.SplitService()
    service.start(job)
    results, root = drain(service)

    parent = os.path.join(desktop, "12월 문서")
    check("상위 폴더 '12월 문서' 생성", os.path.isdir(parent))
    check("그 안에 '기안 저장' 폴더", os.path.isdir(os.path.join(parent, "기안 저장")))
    check("그 안에 '보고서 저장' 폴더", os.path.isdir(os.path.join(parent, "보고서 저장")))
    check("보고서 3장", len(os.listdir(os.path.join(parent, "보고서 저장"))) == 3)

    # --- 4. 이름 충돌 -------------------------------------------------------
    print("\n[4] 같은 파일을 두 번 저장 (덮어쓰기 방지)")
    job = split_service.build_job([a], settings, SAVE_SEPARATE)
    service = split_service.SplitService()
    service.start(job)
    drain(service)
    check("'기안 저장 (2)' 폴더로 분리 저장", os.path.isdir(os.path.join(desktop, "기안 저장 (2)")))

    # --- 5. 잘못된 입력 -----------------------------------------------------
    print("\n[5] 잘못된 파일 처리")
    broken = os.path.join(workdir, "깨진.pdf")
    with open(broken, "w", encoding="utf-8") as fp:
        fp.write("이건 PDF 가 아닙니다")
    job = split_service.build_job([broken], settings, SAVE_SEPARATE)
    service = split_service.SplitService()
    service.start(job)
    results, _ = drain(service)
    check("오류를 잡아내고 앱이 죽지 않음", bool(results and results[0].error))
    check("빈 폴더를 남기지 않음", not os.path.isdir(os.path.join(desktop, "깨진 저장")))

    # --- 6. 설정 저장/복구 --------------------------------------------------
    print("\n[6] 설정 저장 · 복구")
    config_path = os.path.join(workdir, "config.json")
    config = ConfigService(config_path)
    config.load()
    config.settings.button_text = "1장씩 저장"
    config.settings.button_color = "#1F9D55"
    config.settings.pos_x, config.settings.pos_y = 120, 340
    check("저장 성공", config.save())
    reloaded = ConfigService(config_path).load()
    check("버튼 글자 유지", reloaded.button_text == "1장씩 저장")
    check("위치 유지", (reloaded.pos_x, reloaded.pos_y) == (120, 340))
    with open(config_path, "w", encoding="utf-8") as fp:
        fp.write("{망가진 json")
    check("망가진 설정도 기본값으로 복구", ConfigService(config_path).load().button_text == "저장하기")

    # --- 7. 조합키 ----------------------------------------------------------
    print("\n[7] 이동 조합키")
    from easysaving.core.models import MoveCombo
    from easysaving.services import combo

    alt_mask = 0x10 if sys.platform == "darwin" else (0x20000 if sys.platform.startswith("win") else 0x8)
    default = MoveCombo()
    check("Alt + 오른쪽 클릭 인식", combo.matches(default, alt_mask, default.button))
    check("Alt 없이 클릭하면 무시", not combo.matches(default, 0, default.button))
    check("Alt + Shift 는 다른 조합으로 취급", not combo.matches(default, alt_mask | 0x1, default.button))
    check("설명 문자열 생성", "클릭" in combo.describe(default), combo.describe(default))
    ok, _ = combo.is_valid(MoveCombo(modifiers=[], button=1))
    check("수식키 없는 좌클릭은 거부", not ok)

    # --- 마무리 -------------------------------------------------------------
    peak = memory.rss_mb()
    print(f"\n최대 메모리: {peak}MB (목표 100MB 이하)")
    check("메모리 100MB 이하", peak <= 100, f"{peak}MB")

    shutil.rmtree(workdir, ignore_errors=True)
    print("\n" + ("모든 테스트 통과 🎉" if not failures else f"실패 {len(failures)}건: {failures}"))
    return 1 if failures else 0


def drain(service, timeout=120):
    """워커가 끝날 때까지 이벤트를 모두 소비한다."""
    import queue as _queue

    deadline = time.time() + timeout
    results, root = [], None
    while time.time() < deadline:
        try:
            event = service.events.get(timeout=0.2)
        except _queue.Empty:
            continue
        if event[0] == split_service.EV_DONE:
            results, root = event[1], event[2]
            break
        if event[0] == split_service.EV_CANCELLED:
            results = event[1]
            break
    return results, root


if __name__ == "__main__":
    raise SystemExit(main())
