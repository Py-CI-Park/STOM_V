
"""웜풀(warm-pool) 백테스트 세션.

`cli/runner.py:run_backtest`는 매 호출마다 32개 엔진 + 20개 BackSubTotal을
순차 spawn(~130초)하고 데이터를 로딩(~80초)한 뒤 실제 연산(~28초)을 수행하고
전부 죽인다(총 ~273초). AI 루프는 세대마다 이 비용을 반복 지불한다.

`WarmBacktestSession`은 그 흐름을 prepare/run/close로 분리한다:

- prepare(): 엔진/서브토탈을 ThreadPoolExecutor로 **병렬** spawn하고
  데이터를 1번만 로딩한다(run_backtest Step1~5와 동일).
- run(): 엔진을 **살려둔 채** 전략만 바꿔 BackTest 1개만 띄워 반복 백테한다
  (run_backtest Step6~7과 동일). 세대당 비용을 ~30-60초로 낮춘다.
- close(): 엔진/서브토탈/공유메모리를 정리한다(멱등).

엔진(`backengine_base.py:MainLoop`)은 `while True`로 명령을 반복 수신하므로
이미 반복 백테를 지원한다. 엔진/BackTest는 수정하지 않는다.

GUI 참고 프로토콜:
- 병렬 spawn: `ui/ui_backtest_engine.py:130-156`
- 웜 재실행: `ui/ui_button_clicked_editer_stock.py:1266-1326`
- 큐 drain: `ui/ui_backtest_engine.py:361-368`(`clear_backtestQ`)
"""

import os
import time
import sqlite3
import pandas as pd
from multiprocessing import Process, Queue, Value, Lock
from concurrent.futures import ThreadPoolExecutor

from cli.paths import DB_STOCK_BACK_TICK, DB_STOCK_BACK_MIN
from cli.backtest_checkpoints import BacktestCheckpointRecorder
from cli.queue_drain import QueueDrainer
from backtest.back_static import GetMoneytopQuery
from backtest.back_subtotal import BackSubTotal
from backtest.backtest import BackTest
from backtest.backengine_kiwoom_tick import BackEngineKiwoomTick
from backtest.backengine_kiwoom_tick2 import BackEngineKiwoomTick2
from backtest.backengine_kiwoom_min import BackEngineKiwoomMin
from backtest.backengine_kiwoom_min2 import BackEngineKiwoomMin2

# runner.py의 검증된 헬퍼들을 재사용한다(중복 구현 금지).
from cli.runner import (
    _register_signals,
    _ensure_cli_db_env,
    _sync_dict_set,
    _engine_with_dict_set,
    _collect_engine_shared_info,
    _collect_backtest_child_diagnostics,
    _get_backtest_last_rowid,
    _extract_metrics,
    _find_latest_csv,
    _cleanup_shared_memory,
    _drain_queues,
    _normalize_avg_list,
)

# BackSubTotal 프로세스 개수(GUI/runner와 동일하게 20 고정).
_SUBTOTAL_COUNT = 20


def _select_engine_target(is_tick, oms):
    """is_tick / oms 조합으로 엔진 클래스를 선택한다(runner.py:397-400과 동일)."""
    if not oms:
        return BackEngineKiwoomTick if is_tick else BackEngineKiwoomMin
    return BackEngineKiwoomTick2 if is_tick else BackEngineKiwoomMin2


def _empty_queue(queue):
    """큐 한 개의 잔여 메시지를 비운다(clear_backtestQ 방식, 연속 2회 빈 큐면 종료)."""
    empty_count = 0
    while True:
        try:
            queue.get(timeout=0.05)
            empty_count = 0
        except Exception:
            empty_count += 1
            if empty_count >= 2:
                break


class WarmBacktestSession:
    """엔진/데이터를 재사용하는 웜풀 백테스트 세션.

    prepare()로 1회 워밍업 후 run()을 여러 번 호출해 전략만 바꿔 반복 백테한다.
    close()로 자원을 정리하며, 컨텍스트 매니저로도 사용할 수 있다.

    주의: Windows multiprocessing spawn 환경이며 엔진은 daemon Process이므로,
    이 세션을 만든 부모 프로세스가 살아있어야 엔진이 유지된다.
    """

    def __init__(self, config):
        self.config = config
        self._prepared = False

        # 멀티프로세싱 공유 객체 / 큐
        self.windowQ = None
        self.backQ = None
        self.totalQ = None
        self.soundQ = None
        self.liveQ = None
        self.teleQ = None
        self.shared_cnt = None
        self.shared_lock = None
        self.back_sques = []
        self.back_eques = []

        # 워밍업 결과 상태
        self.dict_cn = None
        self.dict_set = None
        self.shared_info = []
        self.back_count = 0
        # _load_market_data() 결과를 보관한다(엔진 리셋 후 DB 재쿼리 없이 데이터 재로딩용).
        self._market_data = None

        # 정리 대상(엔진 + 서브토탈만 보관; BackTest 프로세스는 run마다 따로 reap)
        self._procs = []
        self.drainer = None
        self._warm_timeout_count = 0
        self._warm_recovery_attempts = 0
        self._warm_recovery_success_count = 0
        self._warm_recovery_failure_count = 0
        self._warm_nuclear_fallback_count = 0


    # ------------------------------------------------------------------
    def _elapsed(self, started_at):
        """monotonic 기준 경과초를 음수 없이 반환한다(관측 메타데이터 전용)."""
        return max(0.0, time.perf_counter() - started_at)

    def _timing_common(self, status):
        return {
            'engine_count': int(getattr(self.config, 'engine_count', 0) or 0),
            'back_count': int(self.back_count or 0),
            'status': status,
        }

    def _prepare_timing(self, status, started_at, stage_elapsed):
        timing = self._timing_common(status)
        timing.update({
            'prepare_elapsed': self._elapsed(started_at),
            'spawn_subtotals_elapsed': max(0.0, stage_elapsed.get('spawn_subtotals', 0.0)),
            'spawn_engines_elapsed': max(0.0, stage_elapsed.get('spawn_engines', 0.0)),
            'market_data_load_elapsed': max(0.0, stage_elapsed.get('market_data_load', 0.0)),
            'engine_data_send_elapsed': max(0.0, stage_elapsed.get('engine_data_send', 0.0)),
        })
        return timing

    def _run_timing(self, status, started_at, timeout_hit=False):
        timing = self._timing_common(status)
        timing.update({
            'run_elapsed': self._elapsed(started_at),
            'timeout': bool(timeout_hit),
            'timeout_count': int(self._warm_timeout_count),
            'recovery_attempts': int(self._warm_recovery_attempts),
            'recovery_success_count': int(self._warm_recovery_success_count),
            'recovery_failure_count': int(self._warm_recovery_failure_count),
            'nuclear_fallback_count': int(self._warm_nuclear_fallback_count),
        })
        return timing

    @staticmethod
    def _with_timing(result, timing):
        result = dict(result)
        result['timing'] = timing
        return result

    # prepare: 워밍업 (runner.py Step1~5)
    # ------------------------------------------------------------------
    def prepare(self):
        """엔진/서브토탈을 병렬 spawn하고 데이터를 1회 로딩한다.

        반환: 성공 시 {'status':'ok','back_count':N},
              실패 시 {'status':'error','message':...}.
        """
        started_at = time.perf_counter()
        stage_elapsed = {}
        if self._prepared:
            result = {'status': 'ok', 'back_count': self.back_count}
            return self._with_timing(result, self._prepare_timing('ok', started_at, stage_elapsed))

        _register_signals()
        _ensure_cli_db_env()
        self.dict_set = _sync_dict_set(self.config)

        self._create_queues()
        self.drainer = QueueDrainer(self.windowQ, verbose=getattr(self.config, 'verbose', True))
        self.drainer.start()

        try:
            stage_t0 = time.perf_counter()
            self._spawn_subtotals()
            stage_elapsed['spawn_subtotals'] = self._elapsed(stage_t0)

            stage_t0 = time.perf_counter()
            self._spawn_engines()
            stage_elapsed['spawn_engines'] = self._elapsed(stage_t0)

            stage_t0 = time.perf_counter()
            data = self._load_market_data()
            stage_elapsed['market_data_load'] = self._elapsed(stage_t0)
            if data.get('status') != 'ok':
                self.close()
                return self._with_timing(
                    data, self._prepare_timing(data.get('status', 'error'), started_at, stage_elapsed)
                )
            # 엔진 리셋 후 재로딩 시 DB를 다시 쿼리하지 않도록 보관한다.
            self._market_data = data

            stage_t0 = time.perf_counter()
            send_result = self._send_engine_data(data)
            stage_elapsed['engine_data_send'] = self._elapsed(stage_t0)
            if send_result.get('status') != 'ok':
                self.close()
                return self._with_timing(
                    send_result,
                    self._prepare_timing(send_result.get('status', 'error'), started_at, stage_elapsed),
                )
        except Exception as e:
            self.close()
            result = {'status': 'error', 'message': f'prepare 실패: {e}'}
            return self._with_timing(result, self._prepare_timing('error', started_at, stage_elapsed))

        self._prepared = True
        result = {'status': 'ok', 'back_count': self.back_count}
        return self._with_timing(result, self._prepare_timing('ok', started_at, stage_elapsed))

    def _create_queues(self):
        """큐 및 공유 객체 생성(runner.py Step1)."""
        self.windowQ = Queue()
        self.backQ = Queue()
        self.totalQ = Queue()
        self.soundQ = Queue()
        self.liveQ = Queue()
        self.teleQ = Queue()
        self.shared_cnt = Value('i', 0)
        self.shared_lock = Lock()
        self.back_sques = [Queue() for _ in range(_SUBTOTAL_COUNT)]
        self.back_eques = [Queue() for _ in range(self.config.engine_count)]

    def _spawn_subtotals(self):
        """BackSubTotal 20개를 ThreadPoolExecutor로 병렬 start(ui_backtest_engine.py:152-153)."""
        time_basis = self.dict_set['백테매수시간기준']

        def _start(idx):
            proc = Process(
                target=BackSubTotal,
                args=(idx, self.windowQ, self.totalQ, self.back_sques, time_basis),
                daemon=True,
            )
            proc.start()
            self._procs.append(proc)
            self.windowQ.put((1.4, f'중간집계 프로세스{idx + 1} 생성 완료'))

        with ThreadPoolExecutor(max_workers=_SUBTOTAL_COUNT) as executor:
            list(executor.map(_start, range(_SUBTOTAL_COUNT)))

    def _spawn_engines(self):
        """엔진 engine_count개를 _engine_with_dict_set 래퍼로 병렬 start(ui_backtest_engine.py:155-156)."""
        target = _select_engine_target(self.config.is_tick, self.config.oms)
        dict_set = self.dict_set

        def _start(idx):
            profiling = idx == 0 and dict_set['백테엔진프로파일링']
            proc = Process(
                target=_engine_with_dict_set,
                args=(target, dict(dict_set),
                      idx, self.shared_cnt, self.shared_lock, self.windowQ, self.totalQ,
                      self.backQ, self.back_eques, self.back_sques, dict(dict_set), profiling),
                daemon=True,
            )
            proc.start()
            self._procs.append(proc)
            self.windowQ.put((1.4, f'엔진 프로세스{idx + 1} 생성 완료'))

        with ThreadPoolExecutor(max_workers=self.config.engine_count) as executor:
            list(executor.map(_start, range(self.config.engine_count)))

    def _load_market_data(self):
        """DB에서 종목정보/거래대금순위를 읽고 분류 검증까지 수행(runner.py Step4)."""
        config = self.config
        db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN

        con = sqlite3.connect(db)
        try:
            try:
                df_info = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
            except Exception:
                df_info = pd.read_sql('SELECT * FROM codename', con).set_index('index')
            dict_info = df_info['코스닥'].to_dict()
            self.dict_cn = df_info['종목명'].to_dict()

            query = GetMoneytopQuery(config.is_tick, 'S', config.start_date, config.end_date,
                                     config.start_time, config.end_time)
            df_mt = pd.read_sql(query, con)
        finally:
            con.close()

        if df_mt is None or df_mt.empty:
            return {'status': 'error',
                    'message': '시작 또는 종료일자가 잘못 선택되었거나 해당 일자에 데이터가 존재하지 않습니다.'}

        sets = self._build_code_day_sets(df_mt)
        validation = self._validate_division(sets)
        if validation is not None:
            return validation

        sets['dict_info'] = dict_info
        sets['status'] = 'ok'
        return sets

    def _build_code_day_sets(self, df_mt):
        """거래대금순위에서 code_set/day_list/day_codes/code_days를 추출(runner.py:447-467)."""
        df_mt = df_mt.copy()
        df_mt['일자'] = df_mt['index'].apply(lambda x: int(str(x)[:8]))
        df_mt.set_index('index', inplace=True)

        day_list = df_mt['일자'].unique()

        code_set = set()
        for mt_text in df_mt['거래대금순위'].values:
            code_set.update(mt_text.split(';'))

        day_codes = {}
        for day in day_list:
            codes = set()
            for mt_text in df_mt[df_mt['일자'] == day]['거래대금순위'].values:
                codes.update(mt_text.split(';'))
            day_codes[day] = codes

        code_days = {}
        for code in code_set:
            code_days[code] = {day for day, codes in day_codes.items() if code in codes}

        self.windowQ.put((1.4, '거래대금순위 및 종목코드 추출 완료'))
        return {'code_set': code_set, 'day_list': day_list,
                'day_codes': day_codes, 'code_days': code_days}

    def _validate_division(self, sets):
        """divid_mode별 데이터 충분성 검증(runner.py:474-496). 정상이면 None."""
        config = self.config
        multi = config.engine_count
        divid_mode = config.divid_mode
        one_code = config.one_code
        code_set = sets['code_set']
        day_list = sets['day_list']
        code_days = sets['code_days']

        if divid_mode == '종목코드별 분류' and len(code_set) < multi:
            return {'status': 'error', 'message': '선택한 일자의 종목의 개수가 멀티수보다 작습니다. 일자를 늘리십시오.'}
        if divid_mode == '일자별 분류' and len(day_list) < multi:
            return {'status': 'error', 'message': '선택한 일자의 수가 멀티수보다 작습니다. 일자를 늘리십시오.'}
        if divid_mode == '한종목 로딩' and one_code not in code_days:
            return {'status': 'error', 'message': f'{one_code} 종목은 선택한 일자에 데이터가 존재하지 않습니다.'}
        if divid_mode == '한종목 로딩' and len(code_days.get(one_code, set())) < multi:
            return {'status': 'error', 'message': f'{one_code} 종목의 일자 수가 엔진 수보다 적습니다.'}
        return None

    def _send_engine_data(self, data):
        """엔진에 종목명/데이터로딩 메시지를 보내고 shared_info를 수집(runner.py Step5).

        반환: 성공 시 {'status':'ok'}, 실패 시 {'status':'error','message':...}.
        """
        config = self.config
        multi = config.engine_count
        divid_mode = config.divid_mode
        one_code = config.one_code

        # 메시지 1: 종목명 (주식: 3-tuple)
        for i in range(multi):
            self.back_eques[i].put(('종목명', self.dict_cn, data['dict_info']))

        log_gubun = divid_mode.split()[0]
        if log_gubun == '한종목':
            log_gubun = f'{log_gubun} 일자별'

        data_list = (data['code_set'] if log_gubun == '종목코드별'
                     else data['day_list'] if log_gubun == '일자별'
                     else data['code_days'].get(one_code, set()))
        data_lists = [[d for j, d in enumerate(data_list) if j % multi == i] for i in range(multi)]

        self.windowQ.put((1.4, f'{log_gubun} 데이터 로딩 시작'))

        # 메시지 2: 데이터로딩 (11-tuple)
        avg_list = _normalize_avg_list(config.avg_time)
        for i, datas in enumerate(data_lists):
            self.back_eques[i].put(('데이터로딩', config.start_date, config.end_date,
                                    config.start_time, config.end_time, datas,
                                    avg_list, data['code_days'], data['day_codes'],
                                    one_code if divid_mode == '한종목 로딩' else '',
                                    divid_mode))

        # 응답 대기: shared_info 수집(runner의 검증된 헬퍼 재사용).
        timeout = getattr(config, 'timeout', 3600) or 3600
        checkpoint = BacktestCheckpointRecorder()
        probe = {}
        self.shared_info = []
        collected = _collect_engine_shared_info(
            self.backQ, multi, timeout, checkpoint, probe, self.windowQ, log_gubun,
            self.shared_info,
        )
        if collected is None:
            return {'status': 'error',
                    'message': probe.get('message', 'engine data loading timed out')}

        self.shared_info[:] = sorted(self.shared_info, key=lambda x: x['shape'][0], reverse=True)
        self.back_count = len(self.shared_info)
        self.windowQ.put((1.4, f'{log_gubun} 데이터 로딩 완료'))

        # 메시지 3: 공유데이터
        for q in self.back_eques:
            q.put(('공유데이터', self.back_count, self.shared_info))
        self.windowQ.put((1.4, '백테엔진 준비 완료'))
        return {'status': 'ok'}

    # ------------------------------------------------------------------
    # run: 웜 재실행 (runner.py Step6~7)
    # ------------------------------------------------------------------
    def run(self, buy_strategy, sell_strategy, betting=None, back_club=False, timeout=None, recover_on_timeout=True):
        """살아있는 엔진에 전략만 바꿔 백테 1회를 실행한다.

        반환: run_backtest와 동일한 result dict 구조
              (status/metrics/csv_path/config/message).
        """
        timing_started_at = time.perf_counter()
        if not self._prepared:
            result = {'status': 'error', 'message': 'prepare()가 먼저 호출되어야 합니다.'}
            return self._with_timing(result, self._run_timing('error', timing_started_at))

        config = self.config
        if betting is None:
            betting = config.betting
        if timeout is None:
            # 호출자가 명시하지 않으면 기본 150초로 over-firing 전략을 빨리 컷한다.
            # (검증된 좋은 전략은 ~60초면 충분. config.timeout이 명시돼 있으면 그걸 존중.)
            timeout = getattr(config, 'timeout', None) or 150

        run_start_time = time.time()
        watermark = _get_backtest_last_rowid()

        self._clear_run_queues()
        for q in self.back_eques:
            q.put(('백테유형', '백테스트'))

        proc = self._spawn_backtest(buy_strategy, sell_strategy, betting, back_club)
        proc.join(timeout=timeout)

        if proc.is_alive():
            # timeout: 하드 kill 전에 협조적 취소를 먼저 시도해 BackTest/엔진을 정상 종료시킨다.
            self._warm_timeout_count += 1
            if not recover_on_timeout:
                result = self._abort_timeout_without_recovery(
                    proc,
                    error_message=f'백테스트 시간 초과 ({timeout}초)',
                )
            else:
                result = self._recover_after_failure(
                    proc, timeout_hit=True,
                    error_message=f'백테스트 시간 초과 ({timeout}초)')
            return self._with_timing(
                result, self._run_timing(result.get('status', 'error'), timing_started_at, timeout_hit=True)
            )

        if proc.exitcode not in (0, None):
            # 비정상 종료: 엔진이 오염됐을 수 있으므로 동일하게 협조적 취소 + 재로딩으로 복구한다.
            result = self._recover_after_failure(
                proc, timeout_hit=False,
                error_message=f'백테스트 child process exited with code {proc.exitcode}')
            return self._with_timing(
                result, self._run_timing(result.get('status', 'error'), timing_started_at)
            )

        result = self._collect_run_result(proc, buy_strategy, sell_strategy, watermark, run_start_time)
        return self._with_timing(result, self._run_timing(result.get('status', 'error'), timing_started_at))

    def _clear_run_queues(self):
        """run 직전 backQ/totalQ를 drain(clear_backtestQ 방식)한다.

        backQ에는 직전 run의 child diagnostics 잔여가 남을 수 있으므로 안전하게 비운다.
        """
        _empty_queue(self.backQ)
        _empty_queue(self.totalQ)

    # ------------------------------------------------------------------
    # 복구: 협조적 취소(reset) + 데이터 재로딩(reload) + nuclear fallback
    # ------------------------------------------------------------------
    def _reset_engines(self, timeout=120):
        """GUI backtest_process_kill을 모사한 협조적 취소로 엔진을 정상 리셋한다.

        - 모든 엔진 큐와 totalQ에 '백테중지'를 넣는다.
          엔진은 MainLoop에서 '백테중지'를 받아 BackStop(2) → shared_list unlink +
          backQ에 '백테중지완료'를 넣는다. 실행 중이던 BackTest는 totalQ의 '백테중지'를
          받아 SysExit(True)로 스스로 종료한다(하드 kill 불필요).
        - backQ를 drain하며 '백테중지완료'를 engine_count개 받을 때까지 대기한다.
          그 외 메시지(child diagnostics 등)는 폐기한다.

        반환: engine_count개를 모두 수신하면 True, 상한(timeout초) 초과면 False.
              (리셋 후 엔진들은 shared_list가 비어 데이터 재로딩이 필요하다.)
        """
        engine_count = self.config.engine_count
        try:
            for q in self.back_eques:
                q.put('백테중지')
            self.totalQ.put('백테중지')
        except Exception:
            return False

        received = 0
        deadline = time.time() + timeout
        while received < engine_count:
            remaining = deadline - time.time()
            if remaining <= 0:
                return False
            try:
                msg = self.backQ.get(timeout=min(remaining, 5))
            except Exception:
                # 큐가 잠시 비었을 뿐일 수 있으므로 상한 안에서 계속 폴링한다.
                continue
            if msg == '백테중지완료':
                received += 1
            # '백테중지완료' 외 잔여 메시지는 무시(폐기)한다.
        return True

    def _reload_data(self):
        """살아있는 엔진에 보관해둔 market_data를 다시 보내 공유데이터를 재구성한다.

        엔진 재spawn 없이 _send_engine_data(self._market_data)를 재호출해 종목명/
        데이터로딩/공유데이터를 재전송하고 shared_info/back_count를 갱신한다.

        반환: 성공 True, 실패 False(예외/누락/타임아웃 모두 흡수해 bool만 반환).
        """
        if not self._market_data:
            return False
        try:
            # 직전 shared_info는 리셋 시 엔진이 unlink했으므로 참조를 비운다(이중 unlink 방지).
            self.shared_info = []
            send_result = self._send_engine_data(self._market_data)
            return send_result.get('status') == 'ok'
        except Exception:
            return False

    def _recover_after_failure(self, proc, timeout_hit, error_message):
        """run() 실패/timeout 경로의 복구 흐름. 절대 예외를 던지지 않는다.

        1) 협조적 취소(_reset_engines)로 엔진/BackTest를 정상 종료시킨다.
           - timeout 경로면 그 후 proc.join(grace) → 그래도 살아있으면 kill+join.
           - 실패(exitcode) 경로면 proc는 이미 종료됐으므로 join만 마무리한다.
        2) 데이터 재로딩(_reload_data)으로 엔진을 다시 웜 상태로 만든다.
        3) reset이 실패하거나 reload가 실패하면 nuclear fallback:
           close() → prepare()로 full 재구동. 그것도 실패하면 세션을 unhealthy로
           표시(_prepared=False)하고 error 결과를 반환한다.

        반환: 항상 result dict({'status':'error', ...}).
        """
        reset_ok = False
        self._warm_recovery_attempts += 1
        try:
            reset_ok = self._reset_engines()
        except Exception:
            reset_ok = False

        # BackTest 프로세스 마무리(협조적 취소가 성공하면 이미 스스로 종료 중).
        self._finalize_backtest_proc(proc, timeout_hit, reset_ok)

        if reset_ok:
            reload_ok = False
            try:
                reload_ok = self._reload_data()
            except Exception:
                reload_ok = False
            if reload_ok:
                self._warm_recovery_success_count += 1
                # 협조적 취소 + 재로딩 성공 → 엔진 웜 유지. error 결과만 반환.
                return {'status': 'error', 'message': error_message, 'metrics': None}

        # 여기까지 오면 reset 실패 또는 reload 실패 → nuclear fallback(full 재구동).
        self._warm_recovery_failure_count += 1
        return self._nuclear_fallback(error_message)

    def _abort_timeout_without_recovery(self, proc, error_message):
        """Fail-fast timeout path for terminal batch probes.

        Some research preflights intentionally stop on the first timeout instead of
        paying the full warm-session reset/reload cost. Kill the current BackTest,
        close the warm pool, and return a recordable error row to the caller.
        """
        try:
            self._finalize_backtest_proc(proc, timeout_hit=True, reset_ok=False)
        except Exception:
            pass
        try:
            self.close()
        except Exception:
            pass
        self._prepared = False
        return {'status': 'error',
                'message': f'{error_message} (엔진 복구 생략: fail-fast timeout)',
                'metrics': None}

    def _finalize_backtest_proc(self, proc, timeout_hit, reset_ok):
        """BackTest 프로세스를 정상 종료시킨다(필요 시에만 hard-kill).

        협조적 취소가 성공했으면 BackTest는 totalQ의 '백테중지'로 스스로 종료하므로
        join만으로 충분하다. grace 후에도 살아있으면 그때만 kill한다.
        BackTest는 자식 프로세스를 spawn하지 않으므로(BackSubTotal은 세션 소유)
        kill해도 고아 Total은 생기지 않는다.
        """
        try:
            if proc.is_alive():
                # 협조적 취소가 BackTest를 종료시킬 시간을 준다(grace 10초).
                proc.join(timeout=10)
            if proc.is_alive():
                # 그래도 살아있으면 최후의 수단으로 hard-kill.
                proc.kill()
                proc.join(timeout=5)
        except Exception:
            pass

    def _nuclear_fallback(self, error_message):
        """close() → prepare()로 세션을 full 재구동한다. 예외를 흡수한다.

        재구동 성공이면 엔진은 다시 웜 상태가 되고 error 결과를 반환한다.
        재구동 실패면 세션을 unhealthy(_prepared=False)로 두고 error 결과를 반환해
        상위 루프가 cold 폴백/중단을 판단하게 한다.
        """
        self._warm_nuclear_fallback_count += 1
        try:
            self.close()
        except Exception:
            pass
        try:
            prepared = self.prepare()
        except Exception:
            prepared = {'status': 'error'}

        if isinstance(prepared, dict) and prepared.get('status') == 'ok':
            return {'status': 'error',
                    'message': f'{error_message} (엔진 full 재구동으로 복구)',
                    'metrics': None}

        # full 재구동도 실패 → 세션 unhealthy.
        self._prepared = False
        return {'status': 'error',
                'message': f'{error_message} (엔진 복구 실패: 세션 unhealthy)',
                'metrics': None}

    def _spawn_backtest(self, buy_strategy, sell_strategy, betting, back_club):
        """BackTest 프로세스 1개를 spawn한다(runner.py:569-578과 동일 인자 계약).

        BackTest 프로세스는 이번 run 전용이므로 self._procs에 넣지 않고 별도로 reap한다.
        """
        config = self.config
        proc = Process(
            target=_engine_with_dict_set,
            args=(BackTest, dict(self.dict_set),
                  self.shared_cnt, self.windowQ, self.soundQ, self.totalQ, self.liveQ, self.teleQ,
                  self.back_eques, self.back_sques, '백테스트', 'S', dict(self.dict_set),
                  betting, str(config.avg_time), str(config.start_date), str(config.end_date),
                  str(config.start_time), str(config.end_time), buy_strategy, sell_strategy,
                  self.dict_cn, self.back_count, config.blacklist, False, back_club, self.backQ),
        )
        proc.start()
        return proc

    def _collect_run_result(self, proc, buy_strategy, sell_strategy, watermark, run_start_time):
        """BackTest 완료 후 진단/메트릭/CSV를 수집해 result dict로 구성(runner.py Step7)."""
        result = {'status': 'error', 'message': '', 'metrics': None}

        child_diagnostic = _collect_backtest_child_diagnostics(self.backQ)
        if child_diagnostic is not None:
            result['backtest_child_diagnostics'] = child_diagnostic

        if proc.exitcode not in (0, None):
            result['message'] = f'Backtest child process exited with code {proc.exitcode}'
            return result

        if child_diagnostic is not None and child_diagnostic.get('moneytop_query_status') == 'error':
            result['message'] = 'Backtest child moneytop query failed'
            moneytop_error = child_diagnostic.get('moneytop_error')
            if moneytop_error:
                result['message'] = f"{result['message']}: {moneytop_error}"
            return result

        metrics = _extract_metrics(self.config, min_rowid=watermark)
        csv_path = _find_latest_csv(buy_strategy, run_start_time)
        if metrics:
            result['status'] = 'success'
            result['message'] = '백테스트 완료'
            result['metrics'] = metrics
            result['csv_path'] = csv_path
            result['config'] = {
                'buy_strategy': buy_strategy,
                'sell_strategy': sell_strategy,
                'start_date': str(self.config.start_date),
                'end_date': str(self.config.end_date),
            }
        else:
            result['message'] = 'backtest completed without metrics'
            result['csv_path'] = csv_path
        return result

    # ------------------------------------------------------------------
    # close: 자원 정리 (멱등)
    # ------------------------------------------------------------------
    def close(self):
        """엔진/서브토탈/공유메모리를 정리한다. 여러 번 호출해도 안전(멱등)."""
        self._drain_all_queues()

        if self.drainer is not None:
            try:
                self.drainer.stop()
                self.drainer.join(timeout=2)
            except Exception:
                pass
            self.drainer = None

        for proc in self._procs:
            self._kill_proc(proc)
        self._procs = []

        if self.shared_info:
            _cleanup_shared_memory(self.shared_info)
            self.shared_info = []

        self._prepared = False

    def _drain_all_queues(self):
        """모든 큐(공용 + back_sques + back_eques)를 drain한다."""
        queues = [q for q in (self.windowQ, self.backQ, self.totalQ,
                              self.soundQ, self.liveQ, self.teleQ) if q is not None]
        queues += list(self.back_sques) + list(self.back_eques)
        if queues:
            _drain_queues(queues)

    @staticmethod
    def _kill_proc(proc):
        """단일 프로세스를 kill + join한다(예외 무시)."""
        try:
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 컨텍스트 매니저
    # ------------------------------------------------------------------
    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
