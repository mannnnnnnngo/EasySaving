"""PDF → PowerPoint 변환 작업 오케스트레이션.

split_service 와 같은 방식: 워커 스레드에서 변환하고 진행 상황은 Queue 로 넘긴다.
"""

import gc
import os
import queue
import threading
from dataclasses import dataclass

from ..core import naming
from ..core.errors import CancelledError, EasySavingError
from ..platform_layer import paths

EV_FILE_START = "file_start"   # (index, total, 파일이름, 저장될 .pptx 경로)
EV_PAGE = "page"               # (page, pages)
EV_ERROR = "error"             # (파일이름, 메시지, 상세)
EV_DONE = "done"               # (results, 저장 폴더)
EV_CANCELLED = "cancelled"     # (results,)

MODE_EDITABLE = "editable"
MODE_IMAGE = "image"


@dataclass
class ConvertResult:
    source: str
    output: str
    pages: int = 0
    error: str = ""


class ConvertService:
    def __init__(self):
        self.events = queue.Queue()
        self._cancel = threading.Event()
        self._thread = None

    @property
    def busy(self):
        return bool(self._thread and self._thread.is_alive())

    def cancel(self):
        self._cancel.set()

    def start(self, sources, out_dir, mode=MODE_EDITABLE):
        if self.busy:
            return False
        self._cancel.clear()
        while not self.events.empty():
            try:
                self.events.get_nowait()
            except queue.Empty:
                break
        self._thread = threading.Thread(target=self._run, args=(list(sources), out_dir, mode),
                                        daemon=True)
        self._thread.start()
        return True

    def _run(self, sources, out_dir, mode):
        from ..core import pdf_to_pptx

        results = []
        total = len(sources)
        try:
            for index, src in enumerate(sources, start=1):
                if self._cancel.is_set():
                    raise CancelledError("취소됨")
                out_path = output_path_for(src, out_dir)
                self.events.put((EV_FILE_START, index, total, os.path.basename(src), out_path))
                pages = [0]

                def on_page(p, t):
                    pages[0] = t
                    self.events.put((EV_PAGE, p, t))

                try:
                    pdf_to_pptx.convert_pdf_to_pptx(
                        src, out_path, mode=mode, on_page=on_page,
                        is_cancelled=self._cancel.is_set,
                    )
                except CancelledError:
                    raise
                except EasySavingError as exc:
                    self.events.put((EV_ERROR, os.path.basename(src), exc.message, exc.detail))
                    results.append(ConvertResult(src, out_path, 0, exc.message))
                    continue
                except Exception as exc:  # 예상 못 한 오류도 앱을 죽이지 않는다
                    self.events.put((EV_ERROR, os.path.basename(src),
                                     "PowerPoint 로 바꾸지 못했습니다.", str(exc)))
                    results.append(ConvertResult(src, out_path, 0, str(exc)))
                    continue
                results.append(ConvertResult(src, out_path, pages[0]))
                gc.collect()
            self.events.put((EV_DONE, results, out_dir))
        except CancelledError:
            self.events.put((EV_CANCELLED, results))
        except Exception as exc:
            self.events.put((EV_ERROR, "", "작업을 끝내지 못했습니다.", str(exc)))
            self.events.put((EV_DONE, results, out_dir))


def output_path_for(src, out_dir):
    """'기안.pdf' → out_dir/'기안.pptx' (이미 있으면 '기안 (2).pptx')."""
    stem = naming.stem_of(src)
    return naming.unique_path(os.path.join(out_dir or paths.desktop_dir(), stem + ".pptx"))
