from pathlib import Path


def test_mainwindow_runs_webcrawling_as_qthread_not_process():
    text = Path('ui/ui_mainwindow.py').read_text(encoding='utf-8')

    assert 'Process(target=WebCrawling' not in text, 'QThread로 바뀐 WebCrawling을 여전히 Process로 실행하면 홈탭 데이터가 전달되지 않습니다.'
    assert 'self.webc.signal.connect(self.windowQ.put)' in text, 'WebCrawling signal이 windowQ로 연결되어야 홈탭 데이터가 UI로 전달됩니다.'


def test_process_kill_does_not_reference_removed_qtimer0():
    text = Path('ui/ui_process_kill.py').read_text(encoding='utf-8')

    assert 'qtimer0' not in text, 'MainWindow에 없는 qtimer0 참조가 종료 예외를 일으키고 있습니다.'


def test_webcrawling_stop_contract_is_bounded_and_cancels_timer():
    text = Path('utility/webcrawling.py').read_text(encoding='utf-8')

    assert 'self.treemap_timer = None' in text, 'treemap 재스케줄 timer 참조를 보관해야 stop()에서 취소할 수 있습니다.'
    assert 'self.treemap_timer.cancel()' in text, 'stop()에서 기존 treemap timer를 취소해야 종료 지연 위험이 줄어듭니다.'
    assert 'self.wait(2000)' in text, 'stop()은 무기한 wait() 대신 bounded wait를 사용해야 합니다.'


def test_webcrawling_network_calls_use_timeouts():
    text = Path('utility/webcrawling.py').read_text(encoding='utf-8')

    assert 'self.request_timeout = 10' in text, '네트워크 요청 timeout 기본값이 필요합니다.'
    assert text.count('timeout=self.request_timeout') >= 10, '크롤링 HTTP 요청에는 공통 timeout을 적용해야 합니다.'
