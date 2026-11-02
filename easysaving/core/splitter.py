"""PDF 페이지 분할 엔진 (core 레이어).

메모리 100MB 제약 때문에 다음을 지킨다.
  * pypdf 는 실제로 분할할 때만 import 한다 (지연 임포트, 앱 시작 시 약 20MB 절약).
  * 페이지를 통째로 메모리에 모으지 않고 1페이지씩 만들고 즉시 파일로 흘려보낸다.
  * 일정 페이지마다 gc 를 돌려 pypdf 내부 캐시가 쌓이는 것을 끊는다.
"""

import gc
import os

from .errors import (
    CancelledError,
    NotAPdfError,
    OutputError,
    PdfEncryptedError,
    PdfReadError,
)
from . import naming

GC_EVERY = 25  # N 페이지마다 가비지 컬렉션


def page_count(path):
    """분할 없이 페이지 수만 센다 (미리보기/안내용)."""
    reader, stream = _open_reader(path)
    try:
        return len(reader.pages)
    finally:
        _close(reader, stream)


def split_pdf(src_path, out_dir, stem=None, pad=False, on_page=None, is_cancelled=None):
    """PDF 를 페이지별로 잘라 out_dir 에 저장하고, 저장된 파일 경로 목록을 돌려준다.

    on_page(page_number, total_pages, filename) : 진행 상황 콜백
    is_cancelled() -> bool                      : True 를 돌려주면 중단
    """
    from pypdf import PdfWriter  # 지연 임포트

    stem = stem or naming.stem_of(src_path)
    reader, stream = _open_reader(src_path)
    written = []
    try:
        total = len(reader.pages)
        if total == 0:
            raise PdfReadError("페이지가 없는 PDF 입니다.", src_path)

        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as exc:
            raise OutputError("저장 폴더를 만들 수 없습니다.", str(exc))

        for index in range(total):
            if is_cancelled and is_cancelled():
                raise CancelledError("사용자가 작업을 취소했습니다.")

            page_number = index + 1
            filename = naming.page_filename(stem, page_number, total, pad)
            out_path = naming.unique_path(os.path.join(out_dir, filename))

            writer = PdfWriter()
            writer.add_page(reader.pages[index])
            try:
                with open(out_path, "wb") as fp:
                    writer.write(fp)
            except OSError as exc:
                raise OutputError(f"'{filename}' 을(를) 저장하지 못했습니다.", str(exc))
            finally:
                del writer

            written.append(out_path)
            if on_page:
                on_page(page_number, total, os.path.basename(out_path))
            if page_number % GC_EVERY == 0:
                gc.collect()

        return written
    finally:
        _close(reader, stream)
        gc.collect()


# --- 내부 도우미 -------------------------------------------------------------


def _open_reader(path):
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError as PypdfReadError

    if not os.path.isfile(path):
        raise NotAPdfError("파일을 찾을 수 없습니다.", path)
    if os.path.splitext(path)[1].lower() != ".pdf":
        raise NotAPdfError("PDF 파일이 아닙니다.", path)

    stream = open(path, "rb")
    try:
        reader = PdfReader(stream)
        if reader.is_encrypted:
            # 빈 비밀번호로 열리는 '보기 제한' PDF 는 그대로 진행할 수 있다.
            try:
                opened = reader.decrypt("")
            except Exception:
                opened = 0
            if not opened:
                raise PdfEncryptedError(
                    "비밀번호가 걸린 PDF 라 분할할 수 없습니다.",
                    os.path.basename(path),
                )
        len(reader.pages)  # 여기서 구조 오류를 미리 드러낸다
        return reader, stream
    except (PdfEncryptedError, NotAPdfError):
        stream.close()
        raise
    except PypdfReadError as exc:
        stream.close()
        raise PdfReadError("PDF 를 읽을 수 없습니다. 파일이 손상됐을 수 있습니다.", str(exc))
    except Exception as exc:
        stream.close()
        raise PdfReadError("PDF 를 여는 중 문제가 생겼습니다.", str(exc))


def _close(reader, stream):
    try:
        del reader
    except Exception:
        pass
    try:
        stream.close()
    except Exception:
        pass
