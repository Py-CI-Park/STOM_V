
import os
import sys
import signal
import sqlite3
import atexit
import numpy as np
import pandas as pd
from multiprocessing import Process, Queue, Value, Lock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utility.setting import DICT_SET, DB_STOCK_BACK_TICK, DB_STOCK_BACK_MIN, DB_BACKTEST
from backtest.back_static import GetMoneytopQuery
from backtest.back_subtotal import BackSubTotal
from backtest.backtest import BackTest
from cli.queue_drain import QueueDrainer


# 엔진 import (lazy하지 않고 top-level에서 import — backengine_base.py의 PyQt5 의존성은 Phase 0에서 격리됨)
from backtest.backengine_kiwoom_tick import BackEngineKiwoomTick
from backtest.backengine_kiwoom_tick2 import BackEngineKiwoomTick2
from backtest.backengine_kiwoom_min import BackEngineKiwoomMin
from backtest.backengine_kiwoom_min2 import BackEngineKiwoomMin2


_child_procs = []


def _cleanup_procs():
    for p in _child_procs:
        if p.is_alive():
            p.kill()


atexit.register(_cleanup_procs)


def _signal_handler(signum, frame):
    print('\n[STOM] 백테스트 중단 요청 (Ctrl+C)', file=sys.stderr)
    _cleanup_procs()
    sys.exit(1)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def run_backtest(config):
    """CLI 백테스트 실행. backengine_start() (ui_backtest_engine.py:77-266) 프로토콜 재구현."""

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

    # QueueDrainer 시작 (windowQ → stderr)
    drainer = QueueDrainer(windowQ, verbose=True)
    drainer.start()

    try:
        # === Step 2: BackSubTotal 프로세스 생성 (20개) ===
        back_sques = []
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
        back_eques = []
        for i in range(config.engine_count):
            beq = Queue()
            back_eques.append(beq)

        if not config.oms:
            target = BackEngineKiwoomTick if config.is_tick else BackEngineKiwoomMin
        else:
            target = BackEngineKiwoomTick2 if config.is_tick else BackEngineKiwoomMin2

        for i in range(config.engine_count):
            proc = Process(
                target=target,
                args=(i, shared_cnt, shared_lock, windowQ, totalQ, backQ, back_eques, back_sques),
                daemon=True
            )
            proc.start()
            _child_procs.append(proc)
            windowQ.put((1.4, f'엔진 프로세스{i + 1} 생성 완료'))

        # === Step 4: 데이터 로딩 (DB 연결 + moneytop 파싱) ===
        db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN

        con = sqlite3.connect(db)
        try:
            df_info = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
        except Exception:
            df_info = pd.read_sql('SELECT * FROM codename', con).set_index('index')
        dict_info = df_info['코스닥'].to_dict()
        dict_cn   = df_info['종목명'].to_dict()

        # gubun_ = 'S' (주식 전용. 해선/코인 확장 시 'X'로 변경)
        query = GetMoneytopQuery(config.is_tick, 'S', config.start_date, config.end_date,
                                 config.start_time, config.end_time)
        df_mt = pd.read_sql(query, con)
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
        one_code = ''

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
        for i, datas in enumerate(data_lists):
            back_eques[i].put(('데이터로딩', config.start_date, config.end_date,
                               config.start_time, config.end_time, datas,
                               [config.avg_time], code_days, day_codes,
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
            target=BackTest,
            args=(shared_cnt, windowQ, backQ, soundQ, totalQ, liveQ, teleQ,
                  back_eques, back_sques, '백테스트', 'S')
        )
        proc_backtest.start()
        _child_procs.append(proc_backtest)

        # === Step 7: 완료 대기 + 결과 수집 ===
        proc_backtest.join()

        # backtest.db에서 최신 결과 읽기
        # BackTest.Report()가 columns_vj 컬럼으로 '백테스트' 테이블에 저장
        # columns_vj = ['배팅금액', '필요자금', '거래횟수', '일평균거래횟수', '최대보유종목수',
        #               '평균보유기간', '익절', '손절', '승률', '평균수익률', '수익률합계',
        #               '최대낙폭률', '수익금합계', '매매성능지수', '연간예상수익률', '매수전략', '매도전략']
        metrics = _extract_metrics(config)
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
        drainer.stop()
        drainer.join(timeout=2)
        _cleanup_procs()

    return result


def _extract_metrics(config):
    """backtest.db의 '백테스트' 테이블에서 최신 결과 행을 읽어 metrics dict로 변환."""
    try:
        con = sqlite3.connect(DB_BACKTEST)
        df = pd.read_sql("SELECT * FROM '백테스트' ORDER BY rowid DESC LIMIT 1", con)
        con.close()
    except Exception:
        return None

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
