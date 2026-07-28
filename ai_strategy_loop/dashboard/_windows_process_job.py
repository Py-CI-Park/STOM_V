from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100

# v5.13.2(결함 E) — kill-on-close: 잡 핸들이 닫히면(보유 프로세스 종료 포함) 잡 안의 모든
#   프로세스를 커널이 종료한다. 배치 러너가 자신을 이 플래그로 부착하면, 러너가 어떤
#   방식으로 죽든(Stop-Process 포함) 엔진 자식 수십 개가 고아로 남지 않는다
#   (2026-07-28 실측: 강제 종료 2회로 고아 105개·RAM 33GB 누적).
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


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
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
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


def attach_process_job(pid: int, kill_on_close: bool = False) -> WindowsProcessJob | None:
    """pid 를 새 잡에 배정한다.

    kill_on_close=True 면 잡 핸들이 사라지는 순간(보유 프로세스의 어떤 형태의 종료 포함)
    잡 안의 모든 프로세스가 커널에 의해 종료된다 — 배치 러너 자기부착용(고아 엔진 방지).
    기존 호출자(대시보드 잡 매니저, 명시적 terminate 경로)는 기본값 False 로 동작 불변.
    """
    if os.name != "nt":
        return None
    kernel32 = _kernel32()
    job_handle = kernel32.CreateJobObjectW(None, None)
    if not job_handle:
        return None
    if kill_on_close:
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            wintypes.HANDLE(job_handle),
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(wintypes.HANDLE(job_handle))
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
