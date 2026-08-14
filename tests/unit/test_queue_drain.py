"""cli/queue_drain.py 단위 테스트.

QueueDrainer(Thread) 클래스의 동작을 검증한다.
- tuple 메시지 수신
- string 메시지 수신
- stop() 종료
- verbose=False 시 stderr 미출력
- None 메시지 → 루프 종료
- 빈 큐 → 크래시 없이 대기
"""
import sys
import os
import time
from multiprocessing import Queue
from io import StringIO

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.queue_drain import QueueDrainer


# ============================================================
# 헬퍼
# ============================================================

def _start_drainer(queue, verbose=True):
    """QueueDrainer를 시작하고 인스턴스를 반환한다."""
    drainer = QueueDrainer(queue, verbose=verbose)
    drainer.start()
    return drainer


def _stop_and_join(drainer, timeout=2.0):
    """drainer를 중단하고 종료를 기다린다."""
    drainer.stop()
    drainer.join(timeout=timeout)


def test_protocol_stream_emits_bounded_jsonl_when_enabled(monkeypatch, capsys):
    monkeypatch.setenv("STOM_CLI_BACKTEST_PROTOCOL_STREAM", "1")
    drainer = QueueDrainer(Queue(), verbose=False)
    message = '[CLI_DIAG] {"source":"BackTest","checkpoint":"waiting"}'
    drainer._record_protocol_diagnostic(message)
    assert capsys.readouterr().err.strip() == message
    assert drainer.protocol_diagnostics == [
        {"source": "BackTest", "checkpoint": "waiting"}
    ]


# ============================================================
# tuple 메시지 수신
# ============================================================

class TestTupleMessages:
    """QueueDrainer가 (ui_id, message) tuple을 올바르게 처리하는지 검증."""

    def test_tuple_message_sets_last_message(self):
        """tuple 메시지를 받으면 last_message에 두 번째 요소(message)가 저장된다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '백테스트 시작'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '백테스트 시작'

    def test_tuple_message_last_message_is_most_recent(self):
        """여러 tuple 메시지를 받으면 last_message는 마지막 메시지여야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '첫 번째 메시지'))
        q.put(('ui_001', '두 번째 메시지'))
        q.put(('ui_001', '세 번째 메시지'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '세 번째 메시지'

    def test_tuple_with_extra_elements_is_handled(self):
        """3개 이상 요소를 가진 tuple도 두 번째 요소를 message로 처리한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '확장 메시지', 'extra_data'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '확장 메시지'


# ============================================================
# string 메시지 수신
# ============================================================

class TestStringMessages:
    """QueueDrainer가 str 타입 메시지를 올바르게 처리하는지 검증."""

    def test_string_message_sets_last_message(self):
        """str 메시지를 받으면 last_message에 해당 문자열이 저장된다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put('단순 문자열 메시지')
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '단순 문자열 메시지'

    def test_multiple_string_messages_last_wins(self):
        """여러 str 메시지를 받으면 last_message는 마지막 메시지여야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put('첫 번째')
        q.put('두 번째')
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '두 번째'

    def test_empty_string_message_is_stored(self):
        """빈 문자열 메시지도 last_message에 저장된다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put('')
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == ''


# ============================================================
# stop() 종료
# ============================================================

class TestStop:
    """QueueDrainer.stop()이 2초 이내에 스레드를 종료하는지 검증."""

    def test_stop_exits_within_two_seconds(self):
        """stop() 호출 후 join(timeout=2)이 완료되어야 한다 (is_alive() == False)."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        drainer.stop()
        drainer.join(timeout=2.0)

        assert not drainer.is_alive(), 'stop() 호출 후 2초 이내에 스레드가 종료되어야 한다'

    def test_stop_is_idempotent(self):
        """stop()을 두 번 호출해도 예외가 발생하지 않아야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        drainer.stop()
        drainer.stop()  # 두 번째 호출 — 예외 없어야 함
        drainer.join(timeout=2.0)

        assert not drainer.is_alive()

    def test_stop_while_processing_messages(self):
        """메시지를 처리 중에 stop()을 호출해도 2초 이내에 종료된다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        for i in range(20):
            q.put(f'메시지 {i}')

        drainer.stop()
        drainer.join(timeout=2.0)

        assert not drainer.is_alive()


# ============================================================
# verbose=False — stderr 미출력
# ============================================================

class TestVerboseFalse:
    """verbose=False 일 때 stderr에 출력하지 않지만 last_message는 설정되는지 검증."""

    def test_verbose_false_does_not_write_to_stderr(self, capsys):
        """verbose=False → stderr에 아무것도 출력하지 않아야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '조용한 메시지'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        captured = capsys.readouterr()
        assert captured.err == '', \
            f'verbose=False 일 때 stderr에 출력이 없어야 하지만 "{captured.err}"가 출력됨'

    def test_verbose_false_still_sets_last_message(self, capsys):
        """verbose=False여도 last_message는 정상적으로 설정되어야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '저장은 해야 함'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '저장은 해야 함'

    def test_verbose_false_string_message_no_stderr(self, capsys):
        """verbose=False + str 메시지 → stderr 미출력, last_message 설정."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put('문자열 메시지도 조용해야 함')
        time.sleep(0.3)
        _stop_and_join(drainer)

        captured = capsys.readouterr()
        assert captured.err == ''
        assert drainer.last_message == '문자열 메시지도 조용해야 함'

    def test_verbose_true_writes_to_stderr(self, capsys):
        """verbose=True(기본값) → stderr에 '[STOM] ...' 형식으로 출력해야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=True)

        q.put(('ui_001', '출력 테스트'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        captured = capsys.readouterr()
        assert '[STOM]' in captured.err
        assert '출력 테스트' in captured.err


# ============================================================
# None 메시지 → 루프 종료
# ============================================================

class TestNoneMessage:
    """None 메시지를 받으면 run() 루프가 종료되는지 검증."""

    def test_none_message_stops_loop(self):
        """None을 큐에 넣으면 스레드 루프가 break되어 자연 종료된다."""
        q = Queue()
        drainer = QueueDrainer(q, verbose=False)
        drainer.start()

        q.put(None)
        drainer.join(timeout=2.0)

        assert not drainer.is_alive(), \
            'None 메시지 수신 후 스레드가 자연 종료되어야 한다'

    def test_none_message_after_real_messages(self):
        """실제 메시지 뒤에 None을 넣으면 last_message는 마지막 실제 메시지여야 한다."""
        q = Queue()
        drainer = QueueDrainer(q, verbose=False)
        drainer.start()

        q.put(('ui_001', '실제 메시지'))
        q.put(None)
        drainer.join(timeout=2.0)

        assert drainer.last_message == '실제 메시지'
        assert not drainer.is_alive()

    def test_none_does_not_update_last_message(self):
        """None 메시지는 last_message를 None으로 덮어쓰지 않아야 한다."""
        q = Queue()
        drainer = QueueDrainer(q, verbose=False)
        drainer.start()

        q.put(('ui_001', '보존되어야 할 메시지'))
        q.put(None)
        drainer.join(timeout=2.0)

        # last_message가 None으로 바뀌지 않아야 함
        assert drainer.last_message is not None
        assert drainer.last_message == '보존되어야 할 메시지'


# ============================================================
# 빈 큐 — 크래시 없이 대기
# ============================================================

class TestEmptyQueue:
    """빈 큐에서 QueueDrainer가 크래시 없이 대기 루프를 유지하는지 검증."""

    def test_empty_queue_does_not_crash(self):
        """빈 큐로 시작해도 드레이너가 예외를 발생시키지 않아야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        # 0.6초 동안 빈 큐 상태 유지 — 최소 1회 timeout 만료 경험
        time.sleep(0.6)

        assert drainer.is_alive(), '빈 큐에서도 스레드는 살아있어야 한다'
        _stop_and_join(drainer)

    def test_empty_queue_last_message_is_none(self):
        """메시지 없이 시작하면 last_message 초기값이 None이어야 한다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message is None

    def test_message_after_idle_period_is_received(self):
        """잠시 빈 큐 대기 후 메시지를 넣어도 정상 수신된다."""
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        time.sleep(0.6)  # 빈 큐 대기
        q.put(('ui_001', '지연 메시지'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '지연 메시지'


# ============================================================
# 초기 상태 검증
# ============================================================

class TestInitialState:
    """QueueDrainer 인스턴스 생성 직후 상태를 검증한다."""

    def test_initial_last_message_is_none(self):
        """start() 전 last_message 초기값이 None이어야 한다."""
        q = Queue()
        drainer = QueueDrainer(q, verbose=False)
        assert drainer.last_message is None

    def test_is_daemon_thread(self):
        """QueueDrainer는 daemon 스레드여야 한다 (메인 프로세스 종료 시 함께 종료)."""
        q = Queue()
        drainer = QueueDrainer(q, verbose=False)
        assert drainer.daemon is True

    def test_default_verbose_is_true(self):
        """verbose 기본값은 True여야 한다."""
        q = Queue()
        drainer = QueueDrainer(q)
        assert drainer.verbose is True


class TestProtocolDiagnostics:
    """CLI protocol diagnostics are captured without changing normal log behavior."""

    def test_cli_diag_message_is_recorded(self):
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put((
            'ui_001',
            '[CLI_DIAG] {"source":"BackTest","checkpoint":"backtest_child_started","detail":{"pid":123}}',
        ))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message.startswith('[CLI_DIAG]')
        assert drainer.protocol_diagnostics == [
            {
                'source': 'BackTest',
                'checkpoint': 'backtest_child_started',
                'detail': {'pid': 123},
            }
        ]

    def test_malformed_cli_diag_message_is_ignored(self):
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '[CLI_DIAG] not-json'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '[CLI_DIAG] not-json'
        assert drainer.protocol_diagnostics == []
