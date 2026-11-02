"""메모리 사용량 측정 (100MB 제약 확인용). 외부 패키지 없이 OS API 만 쓴다."""

import sys

IS_WIN = sys.platform.startswith("win")


def rss_mb():
    """현재 프로세스가 실제로 쓰는 메모리(MB). 못 재면 0.0"""
    try:
        if IS_WIN:
            return _windows_rss()
        return _unix_rss()
    except Exception:
        return 0.0


def _unix_rss():
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS 는 byte, Linux 는 KB 단위로 준다.
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(usage / divisor, 1)


def _windows_rss():
    import ctypes
    import ctypes.wintypes as wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    return round(counters.WorkingSetSize / (1024 * 1024), 1)
