"""
GUI Queue를 CLI 로깅으로 변환하는 어댑터

STOM의 windowQ, soundQ 등을 CLI 환경에서 사용할 수 있게 합니다.
"""

import sys
import logging
from queue import Queue, Empty
from typing import Any, Optional, Tuple
from datetime import datetime

# UI 번호 매핑 (utility/setting.py에서 복사)
UI_NUM = {
    '설정로그': 1, '종목명데이터': 1.2, '백테엔진': 1.4,
    'S단순텍스트': 2, 'S로그텍스트': 3, 'C단순텍스트': 4, 'C로그텍스트': 5,
    'S백테스트': 6, 'SF백테스트': 6.5, 'C백테스트': 7, 'CF백테스트': 7.5,
    'S백테바': 8, 'SF백테바': 8.5, 'C백테바': 9, 'CF백테바': 9.5, 'DB관리': 10,
    'S실현손익': 11, 'S거래목록': 12, 'S잔고평가': 13, 'S잔고목록': 14, 'S체결목록': 15,
    'S당일합계': 16, 'S당일상세': 17, 'S누적합계': 18, 'S누적상세': 19, 'S관심종목': 20,
    'C실현손익': 21, 'C거래목록': 22, 'C잔고평가': 23, 'C잔고목록': 24, 'C체결목록': 25,
    'C당일합계': 26, 'C당일상세': 27, 'C누적합계': 28, 'C누적상세': 29, 'C관심종목': 30,
    'S호가종목': 31, 'S호가체결': 32, 'S호가잔량': 33, 'C호가종목': 34, 'C호가체결': 35, 'C호가잔량': 36,
    'S상세기록': 46, 'C상세기록': 47,
}

# 진행률 표시용 UI 번호
PROGRESS_UI_NUMS = {8, 8.5, 9, 9.5}  # S백테바, SF백테바, C백테바, CF백테바

# 로그 표시용 UI 번호
LOG_UI_NUMS = {3, 5, 6, 6.5, 7, 7.5}  # S로그텍스트, C로그텍스트, S/C백테스트


class LoggingQueue(Queue):
    """로깅으로 리다이렉트하는 Queue"""

    def __init__(self, logger: logging.Logger, name: str = "queue"):
        super().__init__()
        self.logger = logger
        self.name = name

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """Queue에 넣는 대신 로깅"""
        if isinstance(item, tuple) and len(item) >= 2:
            ui_num = item[0]
            data = item[1] if len(item) == 2 else item[1:]

            # 진행률 메시지
            if ui_num in PROGRESS_UI_NUMS:
                pass  # 진행률은 별도 처리
            # 로그 메시지
            elif ui_num in LOG_UI_NUMS:
                if isinstance(data, str):
                    self.logger.info(data)
                elif isinstance(data, tuple) and data:
                    self.logger.info(str(data[0]))
            else:
                self.logger.debug(f"[{self.name}] UI {ui_num}: {data}")
        else:
            self.logger.debug(f"[{self.name}] {item}")

        # 실제 Queue에도 저장 (결과 수집용)
        super().put(item, block, timeout)


class NullQueue(Queue):
    """아무것도 하지 않는 Queue (soundQ 등에 사용)"""

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """무시"""
        pass

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """항상 Empty 발생"""
        raise Empty()


class ProgressQueue(Queue):
    """진행률을 표시하는 Queue"""

    def __init__(self, show_progress: bool = True):
        super().__init__()
        self.show_progress = show_progress
        self.last_progress = -1
        self.start_time = None

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """진행률 표시"""
        if self.show_progress and isinstance(item, tuple) and len(item) >= 3:
            ui_num, current, total = item[0], item[1], item[2]
            if ui_num in PROGRESS_UI_NUMS and total > 0:
                if self.start_time is None:
                    self.start_time = datetime.now()

                progress = int((current / total) * 100)
                if progress != self.last_progress:
                    self.last_progress = progress
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if current > 0:
                        eta = (elapsed / current) * (total - current)
                        sys.stdout.write(f"\rProgress: {progress}% ({current}/{total}) ETA: {eta:.1f}s")
                    else:
                        sys.stdout.write(f"\rProgress: {progress}% ({current}/{total})")
                    sys.stdout.flush()

                    if progress >= 100:
                        sys.stdout.write("\n")
                        sys.stdout.flush()

        super().put(item, block, timeout)


class CLIQueueAdapter:
    """GUI Queue를 CLI 출력으로 변환하는 어댑터"""

    def __init__(self, verbose: bool = True, show_progress: bool = True):
        """
        Args:
            verbose: 상세 로그 출력 여부
            show_progress: 진행률 표시 여부
        """
        self.verbose = verbose
        self.show_progress = show_progress
        self.logger = self._setup_logger()

        # 결과 저장용
        self.results = []
        self.completion_detected = False

    def _setup_logger(self) -> logging.Logger:
        """CLI용 로거 설정"""
        logger = logging.getLogger('stom-cli')
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO if self.verbose else logging.WARNING)
        return logger

    def create_window_queue(self) -> LoggingQueue:
        """windowQ 대체 - 로깅으로 리다이렉트"""
        return LoggingQueue(self.logger, 'window')

    def create_sound_queue(self) -> NullQueue:
        """soundQ 대체 - 무시"""
        return NullQueue()

    def create_progress_queue(self) -> ProgressQueue:
        """진행률 표시용 Queue"""
        return ProgressQueue(self.show_progress)

    def create_total_queue(self) -> Queue:
        """totalQ - 일반 Queue"""
        return Queue()

    def create_back_queue(self) -> Queue:
        """backQ - 일반 Queue"""
        return Queue()

    def create_tele_queue(self) -> NullQueue:
        """teleQ 대체 - 무시"""
        return NullQueue()

    def create_live_queue(self) -> NullQueue:
        """liveQ 대체 - 무시"""
        return NullQueue()

    def process_queue_message(self, msg: Any) -> bool:
        """
        Queue 메시지 처리

        Args:
            msg: Queue에서 가져온 메시지

        Returns:
            완료 메시지인지 여부
        """
        if isinstance(msg, tuple) and len(msg) >= 2:
            ui_num = msg[0]
            data = msg[1] if len(msg) == 2 else msg[1:]

            # 진행률 메시지
            if ui_num in PROGRESS_UI_NUMS:
                if len(msg) >= 4:
                    current, total, start = msg[1], msg[2], msg[3]
                    self._show_progress(current, total)

            # 백테스트 결과 메시지
            elif ui_num in {6, 6.5, 7, 7.5}:  # S/C백테스트
                if isinstance(data, str):
                    self.logger.info(data)
                    if 'COMPLETE' in data or '완료' in data:
                        self.completion_detected = True
                        return True
                    if 'STOP' in data or '중지' in data:
                        self.completion_detected = True
                        return True

            # 상세 기록
            elif ui_num in {46, 47}:  # S/C상세기록
                self.results.append(data)

            # 로그 메시지
            elif ui_num in LOG_UI_NUMS:
                if isinstance(data, str):
                    self.logger.info(data)

        elif isinstance(msg, str):
            self.logger.info(msg)
            if '완료' in msg or 'COMPLETE' in msg:
                self.completion_detected = True
                return True

        return False

    def _show_progress(self, current: int, total: int) -> None:
        """진행률 표시"""
        if self.show_progress and total > 0:
            progress = int((current / total) * 100)
            bar_length = 40
            filled = int(bar_length * current / total)
            bar = '=' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f"\r[{bar}] {progress}% ({current}/{total})")
            sys.stdout.flush()
            if current >= total:
                sys.stdout.write("\n")
                sys.stdout.flush()

    def is_completion_message(self, msg: Any) -> bool:
        """완료 메시지인지 확인"""
        if isinstance(msg, str):
            return '완료' in msg or 'COMPLETE' in msg or 'STOP' in msg
        if isinstance(msg, tuple) and len(msg) >= 2:
            data = msg[1]
            if isinstance(data, str):
                return '완료' in data or 'COMPLETE' in data or 'STOP' in data
        return False
