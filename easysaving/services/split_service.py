"""분할 작업 오케스트레이션.

UI 가 멈추지 않도록 작업은 워커 스레드에서 돌리고,
진행 상황은 Queue 로 넘겨 UI 가 after() 로 꺼내 쓰게 한다.
"""

import gc
import os
import queue
import threading

from ..core import naming, splitter
from ..core.errors import CancelledError, EasySavingError
from ..core.models import SAVE_TOGETHER, PreviewItem, SplitJob, SplitResult
from ..platform_layer import paths

# 이벤트 종류
EV_FILE_START = "file_start"   # (index, total, 파일이름, 폴더경로)
EV_PAGE = "page"               # (page, pages, 저장된 파일이름)
EV_FILE_DONE = "file_done"     # (SplitResult,)
EV_ERROR = "error"             # (파일이름, 메시지, 상세)
EV_DONE = "done"               # (results, root_folder)
EV_CANCELLED = "cancelled"     # (results,)


class SplitService:
    def __init__(self):
        self.events = queue.Queue()
        self._cancel = threading.Event()
        self._thread = None

    @property
    def busy(self):
        return bool(self._thread and self._thread.is_alive())

    def cancel(self):
        self._cancel.set()

    def start(self, job: SplitJob):
        if self.busy:
            return False
        self._cancel.clear()
        while not self.events.empty():           # 이전 작업 찌꺼기 비우기
            try:
                self.events.get_nowait()
            except queue.Empty:
                break
        self._thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        self._thread.start()
        return True

    # --- 워커 스레드 ---------------------------------------------------------

    def _run(self, job: SplitJob):
        results = []
        root = _root_folder(job)

        total_files = len(job.sources)
        try:
            for index, src in enumerate(job.sources, start=1):
                if self._cancel.is_set():
                    raise CancelledError("취소됨")

                stem = naming.stem_of(src)
                out_dir = naming.unique_path(
                    os.path.join(root, naming.folder_name(stem, job.folder_suffix))
                )
                self.events.put((EV_FILE_START, index, total_files, os.path.basename(src), out_dir))

                try:
                    files = splitter.split_pdf(
                        src, out_dir, stem=stem, pad=job.pad_numbers,
                        on_page=lambda p, t, name: self.events.put((EV_PAGE, p, t, name)),
                        is_cancelled=self._cancel.is_set,
                    )
                except CancelledError:
                    _cleanup_empty(out_dir)
                    raise
                except EasySavingError as exc:
                    _cleanup_empty(out_dir)
                    self.events.put((EV_ERROR, os.path.basename(src), exc.message, exc.detail))
                    results.append(SplitResult(src, out_dir, 0, [], exc.message))
                    continue
                except Exception as exc:  # 예상 못 한 오류도 앱을 죽이지 않는다
                    _cleanup_empty(out_dir)
                    self.events.put((EV_ERROR, os.path.basename(src), "알 수 없는 오류가 났습니다.", str(exc)))
                    results.append(SplitResult(src, out_dir, 0, [], str(exc)))
                    continue

                result = SplitResult(src, out_dir, len(files), files)
                results.append(result)
                self.events.put((EV_FILE_DONE, result))

            self.events.put((EV_DONE, results, root))
        except CancelledError:
            self.events.put((EV_CANCELLED, results))
        except Exception as exc:
            self.events.put((EV_ERROR, "", "작업을 끝내지 못했습니다.", str(exc)))
            self.events.put((EV_DONE, results, root))


def _root_folder(job: SplitJob):
    """실제 저장이 시작될 루트 폴더. (SAVE_TOGETHER 면 상위 폴더 하나를 더 만든다)"""
    root = job.output_root or paths.desktop_dir()
    if job.mode == SAVE_TOGETHER:
        parent = naming.sanitize(job.parent_folder or "PDF 분할 저장", "PDF 분할 저장")
        root = naming.unique_path(os.path.join(root, parent))
    return root


def preview_job(job: SplitJob, on_item=None, is_cancelled=None):
    """저장하지 않고, 어떤 폴더에 어떤 이름으로 몇 개가 생길지만 계산한다.

    페이지 수를 세려면 PDF 를 열어야 해서 시간이 걸릴 수 있으므로
    UI 는 이 함수를 워커 스레드에서 돌리고 on_item(index, PreviewItem) 으로 한 줄씩 받는다.
    """
    root = _root_folder(job)
    items = []
    for index, src in enumerate(job.sources):
        if is_cancelled and is_cancelled():
            break
        stem = naming.stem_of(src)
        folder = naming.unique_path(os.path.join(root, naming.folder_name(stem, job.folder_suffix)))
        try:
            pages = splitter.page_count(src)
            item = PreviewItem(
                source=src, folder=folder, pages=pages,
                first_name=naming.page_filename(stem, 1, pages, job.pad_numbers),
                last_name=naming.page_filename(stem, pages, pages, job.pad_numbers),
            )
            if pages == 0:
                item.error = "페이지가 없는 PDF 입니다."
        except EasySavingError as exc:
            item = PreviewItem(source=src, folder=folder, error=exc.message)
        except Exception:
            item = PreviewItem(source=src, folder=folder, error="이 파일은 읽을 수 없어요.")
        items.append(item)
        if on_item:
            on_item(index, item)
    gc.collect()          # 쪽수만 세고 pypdf 가 남긴 캐시는 바로 버린다
    return items


def _cleanup_empty(path):
    """실패했을 때 빈 폴더를 남기지 않는다."""
    try:
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
    except Exception:
        pass


def build_job(sources, settings, mode, parent_folder=""):
    """설정 + 사용자 선택 -> SplitJob"""
    return SplitJob(
        sources=list(sources),
        mode=mode,
        parent_folder=parent_folder,
        output_root=settings.output_root or paths.desktop_dir(),
        folder_suffix=settings.folder_suffix,
        pad_numbers=settings.pad_numbers,
    )
