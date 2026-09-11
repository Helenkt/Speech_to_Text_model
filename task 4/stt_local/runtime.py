from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
import sys


@dataclass(frozen=True)
class RuntimeProfile:
    model: str
    device: str
    compute_type: str
    cpu_threads: int
    logical_cpus: int
    memory_gb: float
    cuda_ready: bool


def _memory_gb() -> float:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.total_physical / (1024**3)

    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return pages * page_size / (1024**3)
        except (ValueError, OSError):
            pass

    return 0.0


def _cuda_ready() -> bool:
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() < 1:
            return False
        if sys.platform == "win32":
            for library in ("cublas64_12.dll", "cudnn64_9.dll"):
                ctypes.WinDLL(library)
        return True
    except (ImportError, OSError, RuntimeError):
        return False


def select_runtime(
    logical_cpus: int, memory_gb: float, cuda_ready: bool
) -> RuntimeProfile:
    logical_cpus = max(1, logical_cpus)
    if cuda_ready:
        model = "small"
        device = "cuda"
        compute_type = "float16"
    elif logical_cpus >= 8 and memory_gb >= 8:
        model = "small"
        device = "cpu"
        compute_type = "int8"
    elif logical_cpus >= 4 and memory_gb >= 4:
        model = "base"
        device = "cpu"
        compute_type = "int8"
    else:
        model = "tiny"
        device = "cpu"
        compute_type = "int8"

    return RuntimeProfile(
        model=model,
        device=device,
        compute_type=compute_type,
        cpu_threads=min(logical_cpus, 8),
        logical_cpus=logical_cpus,
        memory_gb=round(memory_gb, 1),
        cuda_ready=cuda_ready,
    )


def recommend_runtime() -> RuntimeProfile:
    return select_runtime(
        logical_cpus=max(1, os.cpu_count() or 1),
        memory_gb=_memory_gb(),
        cuda_ready=_cuda_ready(),
    )
