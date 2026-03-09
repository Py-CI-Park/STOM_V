
import os
import sys
import json
import signal
import sqlite3
import atexit
import pandas as pd
from multiprocessing import Process, Queue, Value, Lock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utility.setting import DICT_SET, DB_STOCK_BACK_TICK, DB_STOCK_BACK_MIN, DB_BACKTEST
from backtest.back_static import GetMoneytopQuery
from backtest.back_subtotal import BackSubTotal
from backtest.backtest import BackTest
from cli.queue_drain import QueueDrainer


# 엔진 import (backengine_base.py의 PyQt5 의존성은 Phase 0에서 격리됨)
from backtest.backengine_kiwoom_tick import BackEngineKiwoomTick
from backtest.backengine_kiwoom_tick2 import BackEngineKiwoomTick2
from backtest.backengine_kiwoom_min import BackEngineKiwoomMin
from backtest.backengine_kiwoom_min2 import BackEngineKiwoomMin2


_child_procs = []


def _normalize_avg_list(avg_time):
    """avg_time 값을 엔진이 기대하는 flat list[int] 형태로 정규화한다."""
    if avg_time is None:
        return []
    if isinstance(avg_time, (list, tuple)):
        return [int(x) for x in avg_time]
    return [int(avg_time)]


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
        if p.is_alive():
            p.kill()


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
    # --- CLI 인자 → DICT_SET 동기화 (정확한 한국어 키 사용) ---
    DICT_SET['주식타임프레임'] = config.is_tick
    DICT_SET['증권사'] = '키움증권'
    DICT_SET['백테주문관리적용'] = config.oms           # backengine_base.py:107
    DICT_SET['블랙리스트추가'] = config.blacklist       # setting.py:200

    # --- CLI headless 모드 필수 오버라이드 ---
    DICT_SET['그래프저장하지않기'] = True                # CLI에서 그래프 파일 저장 불필요
    DICT_SET['그래프띄우지않기'] = True                  # CLI에서 그래프 표시 불가
    DICT_SET['스톰라이브'] = False                      # CLI에서 라이브 연결 불필요

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
    })


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


def run_backtest(config):
    """CLI 백테스트 실행. backengine_start() (ui_backtest_engine.py:77-266) 프로토콜 재구현."""

    _child_procs.clear()
    _register_signals()
    _sync_dict_set(config)

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

    try:
        backtest_rowid_watermark = _get_backtest_last_rowid()

        # === Step 2: BackSubTotal 프로세스 생성 (20개) ===
        for i in range(20):
            bctq = Queue()
            back_sques.append(bctq)

        for i in range(20):
            proc = Process(
                target=BackSubTotal,
                args=(i, totalQ, back_sques, DICT_SET['백테매수시간기준']),
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

        for i in range(config.engine_count):
            proc = Process(
                target=_engine_with_dict_set,
                args=(target, dict(DICT_SET),
                      i, shared_cnt, shared_lock, windowQ, totalQ, backQ, back_eques, back_sques),
                daemon=True
            )
            proc.start()
            _child_procs.append(proc)
            windowQ.put((1.4, f'엔진 프로세스{i + 1} 생성 완료'))

        # === Step 4: 데이터 로딩 (DB 연결 + moneytop 파싱) ===
        db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN

        con = sqlite3.connect(db)
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

        if df_mt is None or df_mt.empty:
            result['message'] = '시작 또는 종료일자가 잘못 선택되었거나 해당 일자에 데이터가 존재하지 않습니다.'
            windowQ.put((1.4, result['message']))
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
            return result

        if divid_mode == '일자별 분류' and len(day_list) < multi:
            result['message'] = '선택한 일자의 수가 멀티수보다 작습니다. 일자를 늘리십시오.'
            windowQ.put((1.4, result['message']))
            return result

        if divid_mode == '한종목 로딩' and one_code not in code_days:
            result['message'] = f'{one_code} 종목은 선택한 일자에 데이터가 존재하지 않습니다.'
            windowQ.put((1.4, result['message']))
            return result

        if divid_mode == '한종목 로딩' and len(code_days.get(one_code, set())) < multi:
            result['message'] = f'{one_code} 종목의 일자 수가 엔진 수보다 적습니다.'
            windowQ.put((1.4, result['message']))
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
        for i, datas in enumerate(data_lists):
            back_eques[i].put(('데이터로딩', config.start_date, config.end_date,
                               config.start_time, config.end_time, datas,
                               avg_list, code_days, day_codes,
                               one_code if divid_mode == '한종목 로딩' else '',
                               divid_mode))

        # 응답 대기: shared_info 수집
        shared_info = []
        for i in range(multi):
            shared_info_ = backQ.get()
            shared_info += shared_info_
            windowQ.put((1.4, f'{log_gubun} 데이터 로딩 중 ... [{i+1}/{multi}]'))
        shared_info = sorted(shared_info, key=lambda x: x['len'], reverse=True)
        windowQ.put((1.4, f'{log_gubun} 데이터 로딩 완료'))

        # 메시지 3: 공유데이터
        back_count = len(shared_info)
        for q in back_eques:
            q.put(('공유데이터', back_count, shared_info))

        windowQ.put((1.4, '백테엔진 준비 완료'))

        # === Step 6: 백테스트 실행 ===

        # 메시지 4: 백테유형
        for q in back_eques:
            q.put(('백테유형', '백테스트'))

        # backQ에 13-tuple 전달
        backQ.put((
            config.betting,
            str(config.avg_time),
            str(config.start_date),
            str(config.end_date),
            str(config.start_time),
            str(config.end_time),
            config.buy_strategy,
            config.sell_strategy,
            dict_cn,
            back_count,
            config.blacklist,
            False,              # schedul (CLI에서 항상 False)
            config.back_club,
        ))

        # BackTest 프로세스 시작 (11개 인자)
        proc_backtest = Process(
            target=_engine_with_dict_set,
            args=(BackTest, dict(DICT_SET),
                  shared_cnt, windowQ, backQ, soundQ, totalQ, liveQ, teleQ,
                  back_eques, back_sques, '백테스트', 'S')
        )
        proc_backtest.start()
        _child_procs.append(proc_backtest)

        # === Step 7: 완료 대기 + 결과 수집 ===
        timeout = getattr(config, 'timeout', 3600) or 3600
        proc_backtest.join(timeout=timeout)

        if proc_backtest.is_alive():
            proc_backtest.kill()
            proc_backtest.join(timeout=5)
            result['status'] = 'error'
            result['message'] = f'백테스트 시간 초과 ({timeout}초)'
            return result

        # backtest.db에서 최신 결과 읽기
        metrics = _extract_metrics(config, min_rowid=backtest_rowid_watermark)
        if metrics:
            result['status'] = 'success'
            result['message'] = '백테스트 완료'
            result['metrics'] = metrics
            result['config'] = {
                'buy_strategy': config.buy_strategy,
                'sell_strategy': config.sell_strategy,
                'start_date': str(config.start_date),
                'end_date': str(config.end_date),
            }
        else:
            result['status'] = 'success'
            result['message'] = '백테스트 완료 (결과 테이블이 비어있습니다)'

    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
        windowQ.put((1.4, f'오류 발생: {e}'))

    finally:
        _drain_queues(all_queues + back_sques + back_eques)
        drainer.stop()
        drainer.join(timeout=2)
        _cleanup_procs()

    return result


def _extract_metrics(config, min_rowid=0):
    """backtest.db의 결과 테이블에서 최신 결과 행을 읽어 metrics dict로 변환."""
    table_name = 'stock_bt'
    con = None
    try:
        con = sqlite3.connect(DB_BACKTEST)
        if min_rowid and min_rowid > 0:
            query = f"SELECT rowid, * FROM '{table_name}' WHERE rowid > ? ORDER BY rowid DESC LIMIT 1"
            df = pd.read_sql(query, con, params=[min_rowid])
        else:
            df = pd.read_sql(f"SELECT rowid, * FROM '{table_name}' ORDER BY rowid DESC LIMIT 1", con)
    except Exception:
        return None
    finally:
        if con is not None:
            con.close()

    if df.empty:
        return None

    row = df.iloc[0]
    return {
        'trade_count': int(row.get('거래횟수', 0)),
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
        'day_count': 0,
        'bootstrap_avg': 0.0,
        'bootstrap_min': 0.0,
        'bootstrap_max': 0.0,
    }
