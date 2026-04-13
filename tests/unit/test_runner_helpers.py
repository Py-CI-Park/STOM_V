"""runner.py 헬퍼 함수 단위 테스트.

TDD RED 단계: 아직 구현되지 않은 기능의 테스트를 먼저 작성.
- US-102: _sync_dict_set() DICT_SET 동기화
- US-103: BacktestConfig.timeout + join timeout
- US-104: _drain_queues() 큐 drain
- US-105: _child_procs.clear(), signal 위치, DB try/finally 등
"""
import sys
import os
import signal
from multiprocessing import Queue, Process
from unittest.mock import patch
import time

import types
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# utility.setting 모듈이 sys.exit()을 호출하지 않도록 가짜 모듈을 미리 등록
# _sync_dict_set()이 'from utility.setting import DICT_SET'를 할 때
# 이 가짜 모듈의 DICT_SET을 사용하게 됨
_mock_dict_set = {}
if 'utility.setting' not in sys.modules:
    _fake_setting = types.ModuleType('utility.setting')
    _fake_setting.DICT_SET = _mock_dict_set
    sys.modules['utility.setting'] = _fake_setting


# ============================================================
# US-102: DICT_SET 동기화 테스트
# ============================================================

class TestSyncDictSet:
    """C-1: _sync_dict_set()가 config 값을 DICT_SET에 동기화하는지 검증."""

    def test_sync_timeframe_tick(self, sample_config):
        """is_tick=True → DICT_SET['주식타임프레임'] = True."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.is_tick = True
        _sync_dict_set(sample_config)
        assert _mock_dict_set['주식타임프레임'] is True

    def test_sync_timeframe_min(self, sample_config):
        """is_tick=False → DICT_SET['주식타임프레임'] = False."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.is_tick = False
        _sync_dict_set(sample_config)
        assert _mock_dict_set['주식타임프레임'] is False

    def test_sync_dict_set_returns_synchronized_dict(self, sample_config):
        """_sync_dict_set() returns the synchronized DICT_SET object."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _mock_dict_set['백테매수시간기준'] = '체결시간'
        sample_config.is_tick = False

        synced = _sync_dict_set(sample_config)

        assert synced is _mock_dict_set
        assert synced['주식타임프레임'] is False
        assert synced['백테매수시간기준'] == _mock_dict_set['백테매수시간기준']

    def test_sync_broker(self, sample_config):
        """증권사가 '키움증권'으로 설정되어야 함."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _sync_dict_set(sample_config)
        assert '키움' in _mock_dict_set.get('증권사', '')

    def test_sync_oms(self, sample_config):
        """config.oms → DICT_SET['백테주문관리적용'] (정확한 한국어 키)."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.oms = True
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('백테주문관리적용') is True

    def test_sync_blacklist(self, sample_config):
        """config.blacklist → DICT_SET['블랙리스트추가'] (정확한 한국어 키)."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.blacklist = True
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('블랙리스트추가') is True


# ============================================================
# US-201: DICT_SET 완전 동기화 테스트
# ============================================================

class TestSyncDictSetComplete:
    """US-201: _sync_dict_set()가 CLI headless 모드에 필요한 모든 키를 동기화."""

    def test_graph_save_disabled(self, sample_config):
        """CLI에서 그래프 저장 비활성화: DICT_SET['그래프저장하지않기'] = True."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('그래프저장하지않기') is True

    def test_graph_display_disabled(self, sample_config):
        """CLI에서 그래프 표시 비활성화: DICT_SET['그래프띄우지않기'] = True."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('그래프띄우지않기') is True

    def test_stom_live_disabled(self, sample_config):
        """CLI에서 스톰라이브 비활성화: DICT_SET['스톰라이브'] = False."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('스톰라이브') is False

    def test_no_wrong_english_keys(self, sample_config):
        """잘못된 영어 키(backtest_oms_apply, blacklist_add)가 사용되지 않아야 함."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        _sync_dict_set(sample_config)
        assert 'backtest_oms_apply' not in _mock_dict_set, \
            'backtest_oms_apply는 잘못된 키. 백테주문관리적용 사용해야 함'
        assert 'blacklist_add' not in _mock_dict_set, \
            'blacklist_add는 잘못된 키. 블랙리스트추가 사용해야 함'

    def test_oms_false_sync(self, sample_config):
        """config.oms=False → DICT_SET['백테주문관리적용'] = False."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.oms = False
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('백테주문관리적용') is False

    def test_blacklist_false_sync(self, sample_config):
        """config.blacklist=False → DICT_SET['블랙리스트추가'] = False."""
        from cli.runner import _sync_dict_set
        _mock_dict_set.clear()
        sample_config.blacklist = False
        _sync_dict_set(sample_config)
        assert _mock_dict_set.get('블랙리스트추가') is False


# ============================================================
# US-103: join() 타임아웃 테스트
# ============================================================

class TestJoinTimeout:
    """C-2: BacktestConfig.timeout 필드 및 join timeout 동작."""

    def test_config_has_timeout_field(self):
        """BacktestConfig에 timeout 필드가 존재해야 함."""
        from cli.config import BacktestConfig
        config = BacktestConfig()
        assert hasattr(config, 'timeout')
        assert config.timeout == 3600  # 기본값 1시간

    def test_parse_args_timeout(self):
        """--timeout 인자가 파싱되어야 함."""
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B',
                             '--start', '20250101', '--end', '20250131',
                             '--timeout', '60'])
        assert config.timeout == 60

    def test_config_timeout_in_argparser(self):
        """--timeout이 argparse에 등록되어 있어야 함."""
        from cli.config import parse_args
        # --timeout 없이 호출해도 기본값이 설정되어야 함
        config = parse_args(['--buy', 'A', '--sell', 'B',
                             '--start', '20250101', '--end', '20250131'])
        assert config.timeout == 3600

    def test_runner_uses_config_verbose_for_queue_drainer(self):
        """run_backtest()는 QueueDrainer에 config.verbose를 전달해야 한다."""
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'cli', 'runner.py'
        )
        with open(runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "QueueDrainer(windowQ, verbose=getattr(config, 'verbose', True))" in content


class TestCliDictSetProcessArgs:
    """CLI process construction passes explicit DICT_SET snapshots to constructors."""

    def _runner_source_without_space(self):
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'cli', 'runner.py'
        )
        with open(runner_path, 'r', encoding='utf-8') as f:
            return ''.join(f.read().split())

    def test_engine_process_passes_dict_set_and_profiling_to_constructor(self):
        content = self._runner_source_without_space()

        assert (
            'args=(target,dict(dict_set),'
            'i,shared_cnt,shared_lock,windowQ,totalQ,backQ,back_eques,back_sques,'
            'dict(dict_set),profiling)'
        ) in content

    def test_engine_process_defines_cli_profiling_flag(self):
        content = self._runner_source_without_space()

        assert "profiling=i==0anddict_set['백테엔진프로파일링']" in content

    def test_backtest_process_passes_dict_set_to_constructor(self):
        content = self._runner_source_without_space()

        assert (
            "args=(BackTest,dict(dict_set),"
            "shared_cnt,windowQ,backQ,soundQ,totalQ,liveQ,teleQ,"
            "back_eques,back_sques,'백테스트','S',dict(dict_set))"
        ) in content


# ============================================================
# US-104: 큐 drain 테스트
# ============================================================

class TestDrainQueues:
    """C-3: _drain_queues()가 모든 큐를 비우는지 검증."""

    def test_drain_single_queue(self):
        """단일 큐에 있는 메시지를 모두 drain."""
        from cli.runner import _drain_queues

        q = Queue()
        q.put('msg1')
        q.put('msg2')
        q.put('msg3')
        _drain_queues([q])
        assert q.empty()

    def test_drain_multiple_queues(self):
        """여러 큐를 동시에 drain."""
        from cli.runner import _drain_queues

        q1 = Queue()
        q2 = Queue()
        q1.put('a')
        q2.put('b')
        q2.put('c')
        _drain_queues([q1, q2])
        assert q1.empty()
        assert q2.empty()

    def test_drain_empty_queue(self):
        """빈 큐에 drain 호출해도 에러 없음."""
        from cli.runner import _drain_queues

        q = Queue()
        _drain_queues([q])  # should not raise
        assert q.empty()


# ============================================================
# US-105: H-5 + M-1 데드코드 제거 + _child_procs 초기화
# ============================================================

class TestDeadCodeRemoval:
    """H-5: output.py에서 BacktestResult 제거, runner.py에서 numpy 제거."""

    def test_no_backtest_result_dataclass(self):
        """output.py에 BacktestResult dataclass가 없어야 함."""
        import cli.output as output_mod
        assert not hasattr(output_mod, 'BacktestResult'), \
            'BacktestResult dataclass는 데드코드이므로 제거되어야 함'

    def test_no_numpy_import_in_runner(self):
        """runner.py에 'import numpy' 가 없어야 함."""
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'cli', 'runner.py'
        )
        with open(runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'import numpy' not in content, \
            'runner.py에서 미사용 numpy import를 제거해야 함'


class TestChildProcsInit:
    """M-1: run_backtest() 시작 시 _child_procs.clear() 호출."""

    def test_child_procs_cleared_on_start(self):
        """run_backtest() 호출 시 _child_procs가 초기화되어야 함."""
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'cli', 'runner.py'
        )
        with open(runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # run_backtest 함수 내부에 _child_procs.clear()가 있어야 함
        assert '_child_procs.clear()' in content, \
            'run_backtest() 시작부에 _child_procs.clear()가 있어야 함'


class TestSignalRegistration:
    """M-2 + H-4: signal 등록이 모듈 레벨이 아닌 함수 내부에 있어야 함."""

    def test_no_module_level_signal(self):
        """runner.py 모듈 레벨에서 signal.signal() 호출이 없어야 함."""
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'cli', 'runner.py'
        )
        with open(runner_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 함수/클래스 바깥 (들여쓰기 없는) signal.signal 호출이 없어야 함
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.startswith('signal.signal('):
                pytest.fail(
                    f'runner.py:{i+1}에 모듈 레벨 signal 등록이 있음. '
                    f'함수 내부로 이동해야 함: {stripped}'
                )


class TestCleanupProcs:
    """중단 시그널 처리 시 foreign process AssertionError를 삼켜야 한다."""

    def test_cleanup_procs_skips_foreign_process_assertion(self):
        from cli import runner

        class ForeignProc:
            def is_alive(self):
                raise AssertionError('can only test a child process')

            def kill(self):
                raise AssertionError('kill should not be called')

        class AliveProc:
            def __init__(self):
                self.killed = False

            def is_alive(self):
                return True

            def kill(self):
                self.killed = True

        alive = AliveProc()
        original = list(runner._child_procs)
        runner._child_procs[:] = [ForeignProc(), alive]
        try:
            runner._cleanup_procs()
            assert alive.killed is True
        finally:
            runner._child_procs[:] = original


class TestCliSharedMemoryCleanup:
    """CLI parent process cleans up shared memory segments after a one-shot run."""

    def test_cleanup_shared_memory_unlinks_unique_shm_names(self, monkeypatch):
        from cli import runner

        calls = []

        class FakeSharedMemory:
            def __init__(self, name):
                calls.append(("open", name))
                self.name = name

            def close(self):
                calls.append(("close", self.name))

            def unlink(self):
                calls.append(("unlink", self.name))

        monkeypatch.setattr(runner.shared_memory, "SharedMemory", FakeSharedMemory)

        runner._cleanup_shared_memory([
            {"shm_name": "backdata_1"},
            {"shm_name": "backdata_1"},
            {"shm_name": "backdata_2"},
            {"file_name": "back_0"},
        ])

        assert calls == [
            ("open", "backdata_1"),
            ("close", "backdata_1"),
            ("unlink", "backdata_1"),
            ("open", "backdata_2"),
            ("close", "backdata_2"),
            ("unlink", "backdata_2"),
        ]

    def test_cleanup_shared_memory_ignores_missing_segments(self, monkeypatch):
        from cli import runner

        class MissingSharedMemory:
            def __init__(self, name):
                raise FileNotFoundError(name)

        monkeypatch.setattr(runner.shared_memory, "SharedMemory", MissingSharedMemory)

        runner._cleanup_shared_memory([{"shm_name": "missing"}])
