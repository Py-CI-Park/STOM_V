"""백테스트 진행률 모니터링 — QueueDrainer 확장.

현재는 공식 `stom_backtest.py` 서브커맨드로 직접 노출하지 않는 library-only 모듈이다.
"""

import sys
import time
from threading import Thread, Event


def format_duration(seconds: float) -> str:
    """Format seconds to human readable string.

    Examples:
        45 -> "45s"
        125 -> "2m 5s"
        3700 -> "1h 1m 40s"
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s}s"
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h}h {m}m {s}s"


def create_progress_bar(current: int, total: int, width: int = 40) -> str:
    """ASCII progress bar.

    Example: "[████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 30.0%"
    """
    if total <= 0:
        percent = 0.0
    else:
        percent = min(current / total, 1.0)

    filled = int(width * percent)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percent * 100:.1f}%"


class ProgressMonitor(Thread):
    """Thread-based monitor that tracks progress from queue messages.

    Extends the QueueDrainer pattern but adds progress tracking:
    processed count, elapsed time, ETA.
    """

    def __init__(self, total_codes: int = 0, verbose: bool = True):
        super().__init__(daemon=True)
        self.total_codes = total_codes
        self.verbose = verbose
        self.stop_event = Event()
        self.last_message = None

        self._processed = 0
        self._start_time = None

    # ------------------------------------------------------------------
    # Thread interface
    # ------------------------------------------------------------------

    def run(self):
        # ProgressMonitor는 독립 모니터 스레드로도 쓸 수 있고,
        # 외부 큐 없이 update() 호출만으로도 동작한다.
        # 큐 기반 사용 시 서브클래스에서 run()을 오버라이드하면 된다.
        pass

    def stop(self):
        self.stop_event.set()

    # ------------------------------------------------------------------
    # Progress API
    # ------------------------------------------------------------------

    def update(self, msg) -> None:
        """Process a message from the queue.

        If the message is a tuple whose first element contains progress
        information, increment the processed counter.
        """
        if self._start_time is None:
            self._start_time = time.time()

        if isinstance(msg, tuple) and len(msg) >= 2:
            ui_id, message = msg[0], msg[1]
            self.last_message = message
            self._processed += 1
            if self.verbose:
                print(f"[STOM] {message}", file=sys.stderr)
        elif isinstance(msg, str):
            self.last_message = msg
            self._processed += 1
            if self.verbose:
                print(f"[STOM] {msg}", file=sys.stderr)

    def get_progress(self) -> dict:
        """Return progress snapshot.

        Returns:
            {
                'processed': int,
                'total': int,
                'percent': float,
                'elapsed_sec': float,
                'eta_sec': float | None,
            }
        """
        elapsed = (time.time() - self._start_time) if self._start_time else 0.0
        processed = self._processed
        total = self.total_codes

        if total > 0:
            percent = min(processed / total * 100.0, 100.0)
        else:
            percent = 0.0

        if processed > 0 and total > 0 and processed < total:
            rate = elapsed / processed  # sec per item
            eta = rate * (total - processed)
        else:
            eta = None

        return {
            "processed": processed,
            "total": total,
            "percent": percent,
            "elapsed_sec": elapsed,
            "eta_sec": eta,
        }

    def format_progress(self) -> str:
        """Format progress as a human-readable string.

        Example:
            "[Engine 2/4] 처리 중: 127/500 종목 (25.4%) | 경과: 3m 22s | 예상 잔여: 10m"
        """
        p = self.get_progress()
        processed = p["processed"]
        total = p["total"]
        percent = p["percent"]
        elapsed = p["elapsed_sec"]
        eta = p["eta_sec"]

        elapsed_str = format_duration(elapsed)
        eta_str = format_duration(eta) if eta is not None else "계산 중"

        return (
            f"처리 중: {processed}/{total} 종목 ({percent:.1f}%)"
            f" | 경과: {elapsed_str}"
            f" | 예상 잔여: {eta_str}"
        )

    def reset(self) -> None:
        """Reset counters for a new run."""
        self._processed = 0
        self._start_time = None
        self.last_message = None
