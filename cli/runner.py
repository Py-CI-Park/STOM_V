
import os
import sys
import json
import glob
import time
import signal
import sqlite3
import atexit
import pandas as pd
from pathlib import Path
from multiprocessing import Process, Queue, Value, Lock, shared_memory
from queue import Empty

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli.paths import DB_SETTING, DB_STRATEGY, DB_STOCK_BACK_TICK, DB_STOCK_BACK_MIN, DB_BACKTEST
from cli.backtest_checkpoints import BacktestCheckpointRecorder
from backtest.back_static import GetMoneytopQuery
from backtest.back_subtotal import BackSubTotal
from backtest.backtest import BackTest
from cli.queue_drain import QueueDrainer
from utility.sqlite_readonly import connect_existing_db_readonly


# 엔진 import (backengine_base.py의 PyQt5 의존성은 Phase 0에서 격리됨)
from backtest.backengine_kiwoom_tick import BackEngineKiwoomTick
from backtest.backengine_kiwoom_tick2 import BackEngineKiwoomTick2
from backtest.backengine_kiwoom_min import BackEngineKiwoomMin
from backtest.backengine_kiwoom_min2 import BackEngineKiwoomMin2


_child_procs = []
_BACKTEST_CSV_DIR_ENV = 'STOM_CLI_BACKTEST_CSV_DIR'
_DEFAULT_BACKTEST_CSV_DIR = 'backtest/csv'


def _normalize_avg_list(avg_time):
    """avg_time 값을 엔진이 기대하는 flat list[int] 형태로 정규화한다."""
    if avg_time is None:
        return []
    if isinstance(avg_time, (list, tuple)):
        return [int(x) for x in avg_time]
    return [int(avg_time)]


def _ensure_cli_db_env():
    defaults = {
        'STOM_CLI_DB_SETTING': DB_SETTING,
        'STOM_CLI_DB_STRATEGY': DB_STRATEGY,
        'STOM_CLI_DB_BACKTEST': DB_BACKTEST,
        'STOM_CLI_DB_STOCK_BACK_TICK': DB_STOCK_BACK_TICK,
        'STOM_CLI_DB_STOCK_BACK_MIN': DB_STOCK_BACK_MIN,
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, str(value))


def _configured_csv_dir(csv_dir=_DEFAULT_BACKTEST_CSV_DIR):
    if csv_dir is not None and str(csv_dir) != _DEFAULT_BACKTEST_CSV_DIR:
        return str(csv_dir)
    return os.environ.get(_BACKTEST_CSV_DIR_ENV) or _DEFAULT_BACKTEST_CSV_DIR


def _get_backtest_last_rowid(table_name='stock_bt'):
    """현재 backtest 결과 테이블의 마지막 rowid를 반환한다."""
    con = None
    try:
        con = sqlite3.connect(DB_BACKTEST)
        row = con.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM '{table_name}'").fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0
    finally:
        if con is not None:
            con.close()


def _cleanup_procs():
    for p in _child_procs:
        try:
            is_alive = p.is_alive()
        except AssertionError:
            continue
        except Exception:
            continue
        if is_alive:
            try:
                p.kill()
            except Exception:
                continue


atexit.register(_cleanup_procs)


def _signal_handler(signum, frame):
    print('\n[STOM] 백테스트 중단 요청 (Ctrl+C)', file=sys.stderr)
    _cleanup_procs()
    sys.exit(1)


def _register_signals():
    """시그널 핸들러를 등록한다. 모듈 import 부작용을 방지하기 위해 함수로 분리."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    if sys.platform == 'win32':
        try:
            signal.signal(signal.SIGBREAK, _signal_handler)
        except (AttributeError, OSError):
            pass


def _sync_dict_set(config):
    """CLI config 값을 DICT_SET 전역 설정에 동기화한다.

    BackTest.Start(), BackEngineBase, Total 등 하위 프로세스가
    DICT_SET를 참조하므로, CLI 인자와 일치시켜야 한다.

    키 이름은 utility/setting.py DICT_SET 정의 및
    backengine_base.py self.dict_set[] 접근 패턴과 일치해야 한다.
    """
    from utility.setting import DICT_SET
    # --- CLI 인자 → DICT_SET 동기화 (정확한 한국어 키 사용) ---
    DICT_SET['주식타임프레임'] = config.is_tick
    DICT_SET['증권사'] = '키움증권'
    DICT_SET['백테주문관리적용'] = config.oms           # backengine_base.py:107
    DICT_SET['블랙리스트추가'] = config.blacklist       # setting.py:200

    # --- CLI headless 모드 필수 오버라이드 ---
    DICT_SET['그래프저장하지않기'] = True                # CLI에서 그래프 파일 저장 불필요
    DICT_SET['그래프띄우지않기'] = True                  # CLI에서 그래프 표시 불가
    DICT_SET['스톰라이브'] = False                      # CLI에서 라이브 연결 불필요
    DICT_SET['시장미시구조분석'] = False                 # tick engine Strategy() 기본 키 보장
    DICT_SET['시장리스크분석'] = False                   # tick engine Strategy() 기본 키 보장

    # 환경 변수로 오버라이드 전파 — Windows spawn 손자 프로세스(Total 등) 대응
    # BackTest가 내부에서 Total을 Process로 생성하므로, _engine_with_dict_set 래퍼로는
    # 도달할 수 없다. 환경 변수는 모든 자손 프로세스에 자동 상속된다.
    os.environ['_STOM_CLI_DICT_SET'] = json.dumps({
        '주식타임프레임': config.is_tick,
        '증권사': '키움증권',
        '백테주문관리적용': config.oms,
        '블랙리스트추가': config.blacklist,
        '그래프저장하지않기': True,
        '그래프띄우지않기': True,
        '스톰라이브': False,
        '시장미시구조분석': False,
        '시장리스크분석': False,
    })
    return DICT_SET


def _drain_queues(queues):
    """큐 목록의 모든 미소비 메시지를 drain한다.

    Windows에서 프로세스 kill 전 큐를 비우지 않으면
    파이프 버퍼 데드락이 발생할 수 있다.
    """
    for q in queues:
        empty_count = 0
        while True:
            try:
                q.get(timeout=0.05)
                empty_count = 0
            except Exception:
                empty_count += 1
                if empty_count >= 2:
                    break


def _cleanup_shared_memory(shared_info):
    seen = set()
    for info in shared_info or []:
        name = info.get('shm_name')
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            shm = shared_memory.SharedMemory(name=name)
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass


def _snapshot_engine_liveness(engine_procs):
    """엔진 자식 프로세스의 생존/종료코드 스냅샷을 반환한다.

    멀티엔진 데이터 응답 교착(issue #35)의 진단 핵심: '응답 0건' 증상이
    (a) 엔진이 살아서 계산 중인지, (b) 엔진이 조용히 죽었는지를 구분하지
    못하면 블록 지점을 확정할 수 없다. 타임아웃 시점에 각 엔진의 is_alive/
    exitcode/pid 를 수집해 결과에 첨부하면, 한 엔진이라도 alive=False +
    exitcode!=0 이면 DataLoad 단계의 침묵 예외(self.bq.put 미도달)를,
    전원 alive=True 면 계산 지연(전략 비용/대용량 데이터)을 가리킨다.
    """
    snapshot = []
    for idx, proc in enumerate(engine_procs or []):
        try:
            entry = {
                'engine_index': idx,
                'pid': proc.pid,
                'alive': bool(proc.is_alive()),
                'exitcode': proc.exitcode,
            }
        except Exception as exc:  # noqa: BLE001 - 진단 수집 실패가 타임아웃 처리를 막지 않는다.
            entry = {'engine_index': idx, 'error': str(exc)}
        snapshot.append(entry)
    return snapshot


def _record_engine_data_loading_timeout(
    checkpoint,
    result,
    multi,
    received_count,
    timeout,
    received_lengths,
    engine_procs=None,
):
    engine_liveness = _snapshot_engine_liveness(engine_procs)
    detail = {
        'expected_count': multi,
        'received_count': received_count,
        'missing_count': multi - received_count,
        'timeout_seconds': timeout,
        'received_lengths': received_lengths,
        'engine_liveness': engine_liveness,
    }
    checkpoint.mark('engine_data_response_timeout', detail=detail)
    result['status'] = 'error'
    result['message'] = 'engine data loading timed out'
    result['engine_data_loading'] = dict(detail)
    result.update(checkpoint.to_result_fields(status='error'))


def _collect_engine_shared_info(
    backQ,
    multi,
    timeout,
    checkpoint,
    result,
    windowQ,
    log_gubun,
    shared_info=None,
    load_stats=None,
    engine_procs=None,
):
    data_load_deadline = time.monotonic() + timeout
    received_count = 0
    received_lengths = []
    if load_stats is not None:
        load_stats['received_count'] = received_count
        load_stats['received_lengths'] = received_lengths
    checkpoint.mark('engine_data_response_wait_started', detail={
        'expected_count': multi,
        'timeout_seconds': timeout,
    })

    collected = shared_info if shared_info is not None else []
    collected.clear()
    for i in range(multi):
        remaining = data_load_deadline - time.monotonic()
        if remaining <= 0:
            _record_engine_data_loading_timeout(
                checkpoint, result, multi, received_count, timeout, received_lengths,
                engine_procs,
            )
            return None

        try:
            shared_info_ = backQ.get(timeout=remaining)
        except Empty:
            _record_engine_data_loading_timeout(
                checkpoint, result, multi, received_count, timeout, received_lengths,
                engine_procs,
            )
            return None

        received_count += 1
        received_lengths.append(len(shared_info_))
        if load_stats is not None:
            load_stats['received_count'] = received_count
        checkpoint.mark('engine_data_response_received', detail={
            'expected_count': multi,
            'received_count': received_count,
            'response_index': i,
            'chunk_count': len(shared_info_),
        })
        collected += shared_info_
        windowQ.put((1.4, f'{log_gubun} 데이터 로딩 중 ... [{i+1}/{multi}]'))

    return collected


def _collect_backtest_child_diagnostics(back_queue):
    diagnostic = None
    empty_count = 0
    while True:
        try:
            data = back_queue.get(timeout=0.05)
            empty_count = 0
        except Exception:
            empty_count += 1
            if empty_count >= 2:
                break
            continue

        if isinstance(data, tuple) and len(data) == 2 and data[0] == 'backtest_child_diagnostics':
            diagnostic = data[1]
    return diagnostic


def _summarize_protocol_diagnostics(events):
    events = list(events or [])
    last_by_source = {}
    last_detail_by_source = {}
    for event in events:
        source = event.get('source')
        checkpoint = event.get('checkpoint')
        if source and checkpoint:
            last_by_source[source] = checkpoint
            detail = event.get('detail')
            if isinstance(detail, dict):
                last_detail_by_source[source] = detail
    return {
        'event_count': len(events),
        'last_checkpoint': events[-1].get('checkpoint') if events else None,
        'last_by_source': last_by_source,
        'last_detail_by_source': last_detail_by_source,
        'events': events,
    }


def _engine_with_dict_set(engine_cls, dict_set_override, *args):
    """자식 프로세스 시작 시 DICT_SET을 CLI 값으로 패치한 후 엔진을 생성한다.

    Windows spawn 방식은 자식 프로세스에서 모든 모듈을 재import하므로,
    부모 프로세스의 _sync_dict_set()이 수정한 DICT_SET 값이 자식에게 전달되지 않는다.
    이 래퍼가 엔진 생성자 호출 전에 올바른 DICT_SET 값을 주입한다.

    각 자식 프로세스는 Windows spawn으로 생성된 독립 메모리 공간이므로
    DICT_SET.update()는 해당 프로세스에만 영향을 미치며,
    부모 프로세스나 다른 자식 프로세스에는 전파되지 않는다.

    See: docs/research/2026-03-08_dict_set_propagation_fix.md
    """
    from utility.setting import DICT_SET
    DICT_SET.update(dict_set_override)
    engine_cls(*args)


def _find_latest_csv(strategy_name, after_timestamp, csv_dir=_DEFAULT_BACKTEST_CSV_DIR):
    """설정된 CSV 디렉터리에서 strategy_name 포함 + after_timestamp 이후 최신 CSV를 반환한다."""
    csv_dir = _configured_csv_dir(csv_dir)
    if not os.path.isdir(csv_dir):
        return None
    pattern = os.path.join(csv_dir, f'*{strategy_name}*.csv') if strategy_name else os.path.join(csv_dir, '*.csv')
    candidates = [
        f for f in glob.glob(pattern)
        if os.path.getmtime(f) >= after_timestamp
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _strategy_names(config):
    if config is None:
        return None
    buy_name = getattr(config, 'buy_strategy', None)
    sell_name = getattr(config, 'sell_strategy', None)
    if not buy_name or not sell_name:
        return None
    return buy_name, sell_name


def _read_strategy_source(con, table_name, strategy_name):
    row = con.execute(
        f'SELECT "전략코드" FROM {table_name} WHERE "index" = ? LIMIT 1',
        (strategy_name,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


def _current_strategy_source_filter(config):
    names = _strategy_names(config)
    if names is None:
        return None, False
    buy_name, sell_name = names
    con = None
    try:
        con = sqlite3.connect(f"file:{Path(DB_STRATEGY).resolve().as_posix()}?mode=ro", uri=True)
        buy_source = _read_strategy_source(con, 'stockbuy', buy_name)
        sell_source = _read_strategy_source(con, 'stocksell', sell_name)
    except Exception:
        return None, True
    finally:
        if con is not None:
            con.close()
    if buy_source is None or sell_source is None:
        return None, True
    return (buy_source, sell_source), True


def run_backtest(config):
    """CLI 백테스트 실행. backengine_start() (ui_backtest_engine.py:77-266) 프로토콜 재구현."""

    _child_procs.clear()
    _register_signals()
    _ensure_cli_db_env()
    dict_set = _sync_dict_set(config)
    _run_start_time = time.time()
    previous_protocol_diag = os.environ.get('STOM_CLI_BACKTEST_PROTOCOL_DIAG')
    os.environ['STOM_CLI_BACKTEST_PROTOCOL_DIAG'] = '1'
    checkpoint = BacktestCheckpointRecorder()
    checkpoint.mark('preflight_started', detail={
        'buy_strategy': config.buy_strategy,
        'sell_strategy': config.sell_strategy,
        'start_date': config.start_date,
        'end_date': config.end_date,
        'is_tick': config.is_tick,
        'engine_count': config.engine_count,
    })
    checkpoint.mark('dict_set_synced')

    result = {
        'status': 'error',
        'message': '',
        'metrics': None,
    }

    # === Step 1: 큐 및 공유 객체 생성 ===
    windowQ    = Queue()
    backQ      = Queue()
    totalQ     = Queue()
    soundQ     = Queue()    # dummy
    liveQ      = Queue()    # dummy
    teleQ      = Queue()    # dummy
    shared_cnt  = Value('i', 0)
    shared_lock = Lock()

    all_queues = [windowQ, backQ, totalQ, soundQ, liveQ, teleQ]
    back_sques = []
    back_eques = []

    # QueueDrainer 시작 (windowQ → stderr)
    drainer = QueueDrainer(windowQ, verbose=getattr(config, 'verbose', True))
    drainer.start()
    shared_info = []

    try:
        backtest_rowid_watermark = _get_backtest_last_rowid()
        checkpoint.mark('backtest_watermark_ready', detail={
            'backtest_rowid_watermark': backtest_rowid_watermark,
        })

        # === Step 2: BackSubTotal 프로세스 생성 (20개) ===
        for i in range(20):
            bctq = Queue()
            back_sques.append(bctq)

        for i in range(20):
            proc = Process(
                target=BackSubTotal,
                args=(i, windowQ, totalQ, back_sques, dict_set['백테매수시간기준']),
                daemon=True
            )
            proc.start()
            _child_procs.append(proc)
            windowQ.put((1.4, f'중간집계 프로세스{i + 1} 생성 완료'))

        # === Step 3: 엔진 클래스 선택 + 프로세스 생성 ===
        for i in range(config.engine_count):
            beq = Queue()
            back_eques.append(beq)

        if not config.oms:
            target = BackEngineKiwoomTick if config.is_tick else BackEngineKiwoomMin
        else:
            target = BackEngineKiwoomTick2 if config.is_tick else BackEngineKiwoomMin2

        engine_procs = []
        for i in range(config.engine_count):
            profiling = i == 0 and dict_set['백테엔진프로파일링']
            proc = Process(
                target=_engine_with_dict_set,
                args=(target, dict(dict_set),
                      i, shared_cnt, shared_lock, windowQ, totalQ, backQ, back_eques, back_sques,
                      dict(dict_set), profiling),
                daemon=True
            )
            proc.start()
            _child_procs.append(proc)
            engine_procs.append(proc)
            windowQ.put((1.4, f'엔진 프로세스{i + 1} 생성 완료'))

        # === Step 4: 데이터 로딩 (DB 연결 + moneytop 파싱) ===
        checkpoint.mark('engine_processes_started', detail={
            'engine_count': config.engine_count,
        })

        db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN
        checkpoint.mark('stock_back_db_selected', detail={'db_path': db})

        con = connect_existing_db_readonly(db)
        try:
            try:
                df_info = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
            except Exception:
                df_info = pd.read_sql('SELECT * FROM codename', con).set_index('index')
            dict_info = df_info['코스닥'].to_dict()
            dict_cn   = df_info['종목명'].to_dict()

            query = GetMoneytopQuery(config.is_tick, 'S', config.start_date, config.end_date,
                                     config.start_time, config.end_time)
            df_mt = pd.read_sql(query, con)
        finally:
            con.close()
        checkpoint.mark('moneytop_loaded', detail={
            'rows': 0 if df_mt is None else len(df_mt),
        })

        if df_mt is None or df_mt.empty:
            result['message'] = '시작 또는 종료일자가 잘못 선택되었거나 해당 일자에 데이터가 존재하지 않습니다.'
            windowQ.put((1.4, result['message']))
            result.update(checkpoint.to_result_fields(status='error'))
            return result

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

        windowQ.put((1.4, '거래대금순위 및 종목코드 추출 완료'))

        # 데이터 검증 (ui_backtest_engine.py:209-227)
        multi = config.engine_count
        divid_mode = config.divid_mode
        one_code = config.one_code

        if divid_mode == '종목코드별 분류' and len(code_set) < multi:
            result['message'] = '선택한 일자의 종목의 개수가 멀티수보다 작습니다. 일자를 늘리십시오.'
            windowQ.put((1.4, result['message']))
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        if divid_mode == '일자별 분류' and len(day_list) < multi:
            result['message'] = '선택한 일자의 수가 멀티수보다 작습니다. 일자를 늘리십시오.'
            windowQ.put((1.4, result['message']))
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        if divid_mode == '한종목 로딩' and one_code not in code_days:
            result['message'] = f'{one_code} 종목은 선택한 일자에 데이터가 존재하지 않습니다.'
            windowQ.put((1.4, result['message']))
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        if divid_mode == '한종목 로딩' and len(code_days.get(one_code, set())) < multi:
            result['message'] = f'{one_code} 종목의 일자 수가 엔진 수보다 적습니다.'
            windowQ.put((1.4, result['message']))
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        # === Step 5: 엔진 큐 메시지 시퀀스 ===

        # 메시지 1: 종목명 (주식: 3-tuple)
        for i in range(config.engine_count):
            back_eques[i].put(('종목명', dict_cn, dict_info))

        # 데이터 분류
        log_gubun = divid_mode.split()[0]
        if log_gubun == '한종목':
            log_gubun = f'{log_gubun} 일자별'

        data_list = code_set if log_gubun == '종목코드별' else day_list if log_gubun == '일자별' else code_days.get(one_code, set())
        data_lists = []
        for i in range(multi):
            data_lists.append([data for j, data in enumerate(data_list) if j % multi == i])

        windowQ.put((1.4, f'{log_gubun} 데이터 로딩 시작'))

        # 메시지 2: 데이터로딩 (11-tuple)
        avg_list = _normalize_avg_list(config.avg_time)
        checkpoint.mark('engine_data_load_requested', detail={
            'expected_count': multi,
            'data_list_count': len(data_list),
            'avg_list': avg_list,
        })
        for i, datas in enumerate(data_lists):
            back_eques[i].put(('데이터로딩', config.start_date, config.end_date,
                               config.start_time, config.end_time, datas,
                               avg_list, code_days, day_codes,
                               one_code if divid_mode == '한종목 로딩' else '',
                               divid_mode))

        # 응답 대기: shared_info 수집
        timeout = getattr(config, 'timeout', 3600) or 3600
        data_load_stats = {}
        shared_info.clear()
        collected_shared_info = _collect_engine_shared_info(
            backQ, multi, timeout, checkpoint, result, windowQ, log_gubun,
            shared_info, data_load_stats, engine_procs
        )
        if collected_shared_info is None:
            return result

        received_count = data_load_stats['received_count']
        received_lengths = data_load_stats['received_lengths']
        shared_info[:] = sorted(shared_info, key=lambda x: x['shape'][0], reverse=True)
        checkpoint.mark('shared_data_loaded', detail={'back_count': len(shared_info)})
        checkpoint.mark('engine_data_load_completed', detail={
            'back_count': len(shared_info),
            'expected_count': multi,
            'received_count': received_count,
            'received_lengths': received_lengths,
        })
        windowQ.put((1.4, f'{log_gubun} 데이터 로딩 완료'))

        # 메시지 3: 공유데이터
        back_count = len(shared_info)
        checkpoint.mark('back_count_ready', detail={'back_count': back_count})
        for q in back_eques:
            q.put(('공유데이터', back_count, shared_info))

        windowQ.put((1.4, '백테엔진 준비 완료'))

        # === Step 6: 백테스트 실행 ===

        # 메시지 4: 백테유형
        for q in back_eques:
            q.put(('백테유형', '백테스트'))

        # BackTest 프로세스 시작: UI와 동일한 소형 생성자 계약을 사용하고
        # 실행 설정은 backQ의 단일 초기 메시지로 전달한다.
        backQ.put((
            config.betting, str(config.avg_time), str(config.start_date), str(config.end_date),
            str(config.start_time), str(config.end_time), config.buy_strategy, config.sell_strategy,
            dict_cn, back_count, config.blacklist, False, config.back_club,
        ))
        proc_backtest = Process(
            target=_engine_with_dict_set,
            args=(BackTest, dict(dict_set),
                  shared_cnt, windowQ, backQ, soundQ, totalQ, liveQ, teleQ,
                  back_eques, back_sques, '백테스트', 'S', dict(dict_set))
        )
        proc_backtest.start()
        checkpoint.mark('backtest_process_started', detail={'pid': proc_backtest.pid})
        _child_procs.append(proc_backtest)

        # === Step 7: 완료 대기 + 결과 수집 ===
        timeout = getattr(config, 'timeout', 3600) or 3600
        proc_backtest.join(timeout=timeout)

        if proc_backtest.is_alive():
            proc_backtest.kill()
            proc_backtest.join(timeout=5)
            result['status'] = 'error'
            result['message'] = f'백테스트 시간 초과 ({timeout}초)'
            result.update(checkpoint.to_result_fields(status='timeout', cleanup_status='process_killed'))
            return result
        checkpoint.mark('backtest_process_finished', detail={'exitcode': proc_backtest.exitcode})
        child_diagnostic = _collect_backtest_child_diagnostics(backQ)
        if child_diagnostic is not None:
            result['backtest_child_diagnostics'] = child_diagnostic
            checkpoint.mark('backtest_child_diagnostics', detail=child_diagnostic)
        if proc_backtest.exitcode not in (0, None):
            checkpoint.mark('backtest_process_exitcode', detail={'exitcode': proc_backtest.exitcode})
            result['status'] = 'error'
            result['message'] = f'Backtest child process exited with code {proc_backtest.exitcode}'
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        # backtest.db에서 최신 결과 읽기
        child_moneytop_error = result.get('backtest_child_diagnostics', {}).get('moneytop_error')
        if result.get('backtest_child_diagnostics', {}).get('moneytop_query_status') == 'error':
            result['status'] = 'error'
            result['message'] = 'Backtest child moneytop query failed'
            if child_moneytop_error:
                result['message'] = f"{result['message']}: {child_moneytop_error}"
            result.update(checkpoint.to_result_fields(status='error'))
            return result

        metrics = _extract_metrics(config, min_rowid=backtest_rowid_watermark)
        csv_path = _find_latest_csv(config.buy_strategy, _run_start_time)
        checkpoint.mark('csv_detected', detail={'csv_path': csv_path})
        if metrics:
            result['status'] = 'success'
            result['message'] = '백테스트 완료'
            result['metrics'] = metrics
            result['csv_path'] = csv_path
            result['config'] = {
                'buy_strategy': config.buy_strategy,
                'sell_strategy': config.sell_strategy,
                'start_date': str(config.start_date),
                'end_date': str(config.end_date),
            }
            result.update(checkpoint.to_result_fields(status='success'))
        else:
            result['status'] = 'error'
            result['message'] = 'backtest completed without metrics'
            result['csv_path'] = csv_path
            result.update(checkpoint.to_result_fields(status='error'))

    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
        result.update(checkpoint.to_result_fields(status='error'))
        windowQ.put((1.4, f'오류 발생: {e}'))

    finally:
        checkpoint.mark('shared_memory_cleanup_started', detail={
            'shared_info_count': len(shared_info or []),
        })
        _cleanup_shared_memory(shared_info)
        checkpoint.mark('shared_memory_cleanup_completed')
        _drain_queues(all_queues + back_sques + back_eques)
        drainer.stop()
        drainer.join(timeout=2)
        if result.get('status') != 'success' or drainer.protocol_diagnostics:
            result['backtest_process_diagnostics'] = _summarize_protocol_diagnostics(drainer.protocol_diagnostics)
        _cleanup_procs()
        if previous_protocol_diag is None:
            os.environ.pop('STOM_CLI_BACKTEST_PROTOCOL_DIAG', None)
        else:
            os.environ['STOM_CLI_BACKTEST_PROTOCOL_DIAG'] = previous_protocol_diag

    return result


def _extract_metrics(config, min_rowid=0):
    """backtest.db의 현재 전략 source와 일치하는 post-watermark 결과 행을 metrics로 변환."""
    table_name = 'stock_bt'
    source_filter, source_filter_required = _current_strategy_source_filter(config)
    if source_filter_required and source_filter is None:
        return None
    watermark = int(min_rowid or 0)
    con = None
    try:
        con = sqlite3.connect(DB_BACKTEST)
        params = [watermark]
        where = "WHERE rowid > ?"
        if source_filter is not None:
            where += ' AND "매수전략" = ? AND "매도전략" = ?'
            params.extend(source_filter)
        query = f"SELECT rowid, * FROM '{table_name}' {where} ORDER BY rowid DESC LIMIT 1"
        df = pd.read_sql(query, con, params=params)
    except Exception:
        return None
    finally:
        if con is not None:
            con.close()

    if df.empty:
        return None

    row = df.iloc[0]
    trade_count = int(row.get('거래횟수', 0))
    # 일평균거래횟수 = 거래횟수 / 거래일수 (stock_bt 컬럼에 직접 존재; 예 0.4).
    #   일일 시스템 트레이딩 빈도 게이트의 주 기준이다(절대 거래수가 아니라 일평균).
    daily_avg_trades = float(row.get('일평균거래횟수', 0.0))
    # 거래일수(day_count): stock_bt에 직접 없으므로 일평균에서 역산한다.
    #   거래일수 = 거래횟수 / 일평균(반올림). 일평균이 0이면 역산 불가 → 0.
    if daily_avg_trades > 0.0:
        day_count = int(round(trade_count / daily_avg_trades))
    else:
        day_count = 0
    return {
        'trade_count': trade_count,
        'daily_avg_trades': daily_avg_trades,
        'win_rate': float(row.get('승률', 0.0)),
        'avg_profit_pct': float(row.get('평균수익률', 0.0)),
        'total_profit_pct': float(row.get('수익률합계', 0.0)),
        'total_profit_krw': int(row.get('수익금합계', 0)),
        'cagr': float(row.get('연간예상수익률', 0.0)),
        'mdd_pct': float(row.get('최대낙폭률', 0.0)),
        'mdd_amount': 0.0,
        'tpi': float(row.get('매매성능지수', 0.0)),
        'seed_capital': float(row.get('필요자금', 0.0)),
        'max_hold_count': int(row.get('최대보유종목수', 0)),
        'avg_hold_time': float(row.get('평균보유기간', 0.0)),
        'day_count': day_count,
        'bootstrap_avg': 0.0,
        'bootstrap_min': 0.0,
        'bootstrap_max': 0.0,
    }
