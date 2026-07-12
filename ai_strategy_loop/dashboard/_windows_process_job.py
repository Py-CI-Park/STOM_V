from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


def _kernel32() -> ctypes.CDLL:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


class WindowsProcessJob:
    def __init__(self, handle: int) -> None:
        self._handle: int | None = handle
        self._lock = threading.Lock()

    def terminate(self) -> bool:
        with self._lock:
            handle = self._handle
            if handle is None or os.name != "nt":
                return False
            return bool(
                _kernel32().TerminateJobObject(wintypes.HANDLE(handle), 1)
            )

    def close(self) -> None:
        with self._lock:
            handle = self._handle
            self._handle = None
        if handle is not None and os.name == "nt":
            _kernel32().CloseHandle(wintypes.HANDLE(handle))


def attach_process_job(pid: int) -> WindowsProcessJob | None:
    if os.name != "nt":
        return None
    kernel32 = _kernel32()
    job_handle = kernel32.CreateJobObjectW(None, None)
    if not job_handle:
        return None
    process_handle = kernel32.OpenProcess(
        _PROCESS_TERMINATE | _PROCESS_SET_QUOTA,
        False,
        pid,
    )
    if not process_handle:
        kernel32.CloseHandle(job_handle)
        return None
    try:
        if not kernel32.AssignProcessToJobObject(job_handle, process_handle):
            kernel32.CloseHandle(job_handle)
            return None
        return WindowsProcessJob(int(job_handle))
    finally:
        kernel32.CloseHandle(process_handle)
