"""
Headless Backtest Runner
========================

PyQt5 없이 백테스트 엔진을 실행하는 헤드리스 러너.
실제 BackTest 아키텍처와 동일한 큐 구조 및 프로세스 구조를 사용합니다.
"""

import sys
import time
import sqlite3
import pandas as pd
from typing import Optional, Dict, Any, List
from multiprocessing import Process, Queue, Value, Lock
from traceback import print_exc

from cli.adapters.settings_adapter import load_settings_without_qt, get_database_paths
from cli.adapters.output_adapter import OutputAdapter

# 로깅 - utility.static에서 레지스트리 접근 문제가 있을 수 있으므로 직접 설정
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HeadlessBacktestRunner')

def now():
    """현재 시간 반환 (utility.static.now 대체)"""
    import time
    return time.time()

# 데이터베이스 경로 상수 (utility.setting 대신 직접 정의)
DB_STOCK_BACK_TICK = './_database/stock_tick_back.db'
DB_STOCK_BACK_MIN = './_database/stock_min_back.db'
DB_COIN_BACK_TICK = './_database/coin_tick_back.db'
DB_COIN_BACK_MIN = './_database/coin_min_back.db'
DB_FUTURE_BACK_TICK = './_database/future_tick_back.db'
DB_FUTURE_BACK_MIN = './_database/future_min_back.db'
DB_STRATEGY = './_database/strategy.db'

# ui_num 매핑 (utility.setting 대신 직접 정의)
ui_num = {
    'S백테바': 8, 'C백테바': 9,
    'S백테스트': 6, 'C백테스트': 7,
    'S상세기록': 10, 'C상세기록': 11,
    '백테엔진': 12,
}

# 백테스트 모듈 지연 로딩을 위한 전역 변수
_backtest_modules_loaded = False
BackTest = None
BackSubTotal = None
GetMoneytopQuery = None
BackEngineKiwoomTick = None
BackEngineKiwoomTick2 = None
BackEngineKiwoomMin = None
BackEngineKiwoomMin2 = None
BackEngineFutureTick = None
BackEngineFutureTick2 = None
BackEngineFutureMin = None
BackEngineFutureMin2 = None
BackEngineUpbitTick = None
BackEngineUpbitTick2 = None
BackEngineUpbitMin = None
BackEngineUpbitMin2 = None
BackEngineBinanceTick = None
BackEngineBinanceTick2 = None
BackEngineBinanceMin = None
BackEngineBinanceMin2 = None


def _load_backtest_modules():
    """
    백테스트 모듈 지연 로딩

    utility.setting이 레지스트리에 접근하므로, 실제 백테스트 실행 시에만 로드합니다.
    """
    global _backtest_modules_loaded
    global BackTest, BackSubTotal, GetMoneytopQuery
    global BackEngineKiwoomTick, BackEngineKiwoomTick2, BackEngineKiwoomMin, BackEngineKiwoomMin2
    global BackEngineFutureTick, BackEngineFutureTick2, BackEngineFutureMin, BackEngineFutureMin2
    global BackEngineUpbitTick, BackEngineUpbitTick2, BackEngineUpbitMin, BackEngineUpbitMin2
    global BackEngineBinanceTick, BackEngineBinanceTick2, BackEngineBinanceMin, BackEngineBinanceMin2

    if _backtest_modules_loaded:
        return

    logger.info("Loading backtest modules...")

    from backtester.backtest import BackTest as _BackTest
    from backtester.back_subtotal import BackSubTotal as _BackSubTotal
    from backtester.back_static import GetMoneytopQuery as _GetMoneytopQuery
    from backtester.backengine_kiwoom_tick import BackEngineKiwoomTick as _BackEngineKiwoomTick
    from backtester.backengine_kiwoom_tick2 import BackEngineKiwoomTick2 as _BackEngineKiwoomTick2
    from backtester.backengine_kiwoom_min import BackEngineKiwoomMin as _BackEngineKiwoomMin
    from backtester.backengine_kiwoom_min2 import BackEngineKiwoomMin2 as _BackEngineKiwoomMin2
    from backtester.backengine_future_tick import BackEngineFutureTick as _BackEngineFutureTick
    from backtester.backengine_future_tick2 import BackEngineFutureTick2 as _BackEngineFutureTick2
    from backtester.backengine_future_min import BackEngineFutureMin as _BackEngineFutureMin
    from backtester.backengine_future_min2 import BackEngineFutureMin2 as _BackEngineFutureMin2
    from backtester.backengine_upbit_tick import BackEngineUpbitTick as _BackEngineUpbitTick
    from backtester.backengine_upbit_tick2 import BackEngineUpbitTick2 as _BackEngineUpbitTick2
    from backtester.backengine_upbit_min import BackEngineUpbitMin as _BackEngineUpbitMin
    from backtester.backengine_upbit_min2 import BackEngineUpbitMin2 as _BackEngineUpbitMin2
    from backtester.backengine_binance_tick import BackEngineBinanceTick as _BackEngineBinanceTick
    from backtester.backengine_binance_tick2 import BackEngineBinanceTick2 as _BackEngineBinanceTick2
    from backtester.backengine_binance_min import BackEngineBinanceMin as _BackEngineBinanceMin
    from backtester.backengine_binance_min2 import BackEngineBinanceMin2 as _BackEngineBinanceMin2

    BackTest = _BackTest
    BackSubTotal = _BackSubTotal
    GetMoneytopQuery = _GetMoneytopQuery
    BackEngineKiwoomTick = _BackEngineKiwoomTick
    BackEngineKiwoomTick2 = _BackEngineKiwoomTick2
    BackEngineKiwoomMin = _BackEngineKiwoomMin
    BackEngineKiwoomMin2 = _BackEngineKiwoomMin2
    BackEngineFutureTick = _BackEngineFutureTick
    BackEngineFutureTick2 = _BackEngineFutureTick2
    BackEngineFutureMin = _BackEngineFutureMin
    BackEngineFutureMin2 = _BackEngineFutureMin2
    BackEngineUpbitTick = _BackEngineUpbitTick
    BackEngineUpbitTick2 = _BackEngineUpbitTick2
    BackEngineUpbitMin = _BackEngineUpbitMin
    BackEngineUpbitMin2 = _BackEngineUpbitMin2
    BackEngineBinanceTick = _BackEngineBinanceTick
    BackEngineBinanceTick2 = _BackEngineBinanceTick2
    BackEngineBinanceMin = _BackEngineBinanceMin
    BackEngineBinanceMin2 = _BackEngineBinanceMin2

    _backtest_modules_loaded = True
    logger.info("Backtest modules loaded successfully")


class HeadlessBacktestRunner:
    """
    PyQt5 없이 백테스트 엔진을 실행하는 클래스

    실제 ui_backtest_engine.py와 동일한 아키텍처를 사용합니다:
    - windowQ, soundQ, totalQ, backQ, liveQ, teleQ
    - back_eques (N개의 BackEngine 큐)
    - back_sques (20개의 BackSubTotal 큐)
    - shared_cnt, shared_lock
    """

    def __init__(self):
        """초기화"""
        self.dict_set: Optional[Dict[str, Any]] = None
        self.output_adapter = OutputAdapter()

        # 큐들
        self.windowQ: Optional[Queue] = None
        self.soundQ: Optional[Queue] = None
        self.totalQ: Optional[Queue] = None
        self.backQ: Optional[Queue] = None
        self.liveQ: Optional[Queue] = None
        self.teleQ: Optional[Queue] = None

        # 엔진 큐 및 프로세스
        self.back_eques: List[Queue] = []
        self.back_sques: List[Queue] = []
        self.back_eprocs: List[Process] = []
        self.back_sprocs: List[Process] = []

        # 공유 변수
        self.shared_cnt: Optional[Value] = None
        self.shared_lock: Optional[Lock] = None

        # 백테스트 상태
        self.back_count: int = 0
        self.shared_info: List[Dict] = []
        self.dict_cn: Optional[Dict] = None
        self.multi: int = 1
        self.divid_mode: str = '종목코드별 분류'

        # 백테스트 프로세스
        self.backtest_process: Optional[Process] = None

    def load_settings(self) -> bool:
        """설정 로드"""
        try:
            logger.info("Loading settings without Qt...")
            self.dict_set = load_settings_without_qt()
            logger.info("Settings loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            print_exc()
            return False

    def _create_queues(self):
        """모든 필요한 큐 생성"""
        self.windowQ = Queue()
        self.soundQ = Queue()
        self.totalQ = Queue()
        self.backQ = Queue()
        self.liveQ = Queue()
        self.teleQ = Queue()
        self.back_eques = []
        self.back_sques = []
        logger.info("Queues created")

    def _start_subtotal_processes(self):
        """BackSubTotal 프로세스 20개 시작"""
        for i in range(20):
            bctq = Queue()
            self.back_sques.append(bctq)

        for i in range(20):
            proc = Process(
                target=BackSubTotal,
                args=(i, self.totalQ, self.back_sques, self.dict_set['백테매수시간기준']),
                daemon=True
            )
            proc.start()
            self.back_sprocs.append(proc)
            logger.info(f'BackSubTotal process {i + 1}/20 started')

    def _start_engine_processes(self, gubun: str, multi: int):
        """BackEngine 프로세스 N개 시작"""
        self.shared_cnt = Value('i', 0)
        self.shared_lock = Lock()

        for i in range(multi):
            beq = Queue()
            self.back_eques.append(beq)

        for i in range(multi):
            # 엔진 타입 선택
            if gubun == '주식':
                if not self.dict_set['백테주문관리적용']:
                    target = BackEngineKiwoomTick if self.dict_set['주식타임프레임'] else BackEngineKiwoomMin
                else:
                    target = BackEngineKiwoomTick2 if self.dict_set['주식타임프레임'] else BackEngineKiwoomMin2
            elif gubun == '해선':
                if not self.dict_set['백테주문관리적용']:
                    target = BackEngineFutureTick if self.dict_set['주식타임프레임'] else BackEngineFutureMin
                else:
                    target = BackEngineFutureTick2 if self.dict_set['주식타임프레임'] else BackEngineFutureMin2
            else:  # 코인
                if self.dict_set['거래소'] == '업비트':
                    if not self.dict_set['백테주문관리적용']:
                        target = BackEngineUpbitTick if self.dict_set['코인타임프레임'] else BackEngineUpbitMin
                    else:
                        target = BackEngineUpbitTick2 if self.dict_set['코인타임프레임'] else BackEngineUpbitMin2
                else:
                    if not self.dict_set['백테주문관리적용']:
                        target = BackEngineBinanceTick if self.dict_set['코인타임프레임'] else BackEngineBinanceMin
                    else:
                        target = BackEngineBinanceTick2 if self.dict_set['코인타임프레임'] else BackEngineBinanceMin2

            # 프로파일링은 CLI에서 비활성화
            proc = Process(
                target=target,
                args=(i, self.shared_cnt, self.shared_lock, self.windowQ, self.totalQ,
                      self.backQ, self.back_eques, self.back_sques),
                daemon=True
            )
            proc.start()
            self.back_eprocs.append(proc)
            logger.info(f'BackEngine process {i + 1}/{multi} started')

    def _load_data_into_engines(self, gubun: str, startday: int, endday: int,
                                starttime: int, endtime: int, avg_list: List[int],
                                divid_mode: str, one_code: Optional[str] = None):
        """엔진에 데이터 로딩 (ui_backtest_engine.py의 로직과 동일)"""
        try:
            # 데이터베이스 선택
            if gubun == '주식':
                db = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
            elif gubun == '해선':
                db = DB_FUTURE_BACK_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_BACK_MIN
            else:
                db = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN

            con = sqlite3.connect(db)

            # 종목명 로드
            dict_info = {}
            if gubun == '주식':
                try:
                    df_cn = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
                except:
                    df_cn = pd.read_sql('SELECT * FROM codename', con).set_index('index')
                self.dict_cn = df_cn['종목명'].to_dict()
            elif gubun == '해선':
                df_cn = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
                dict_info = df_cn.to_dict('index')
                self.dict_cn = df_cn['종목명'].to_dict()

            # 거래대금순위 데이터 로드
            gubun_ = 'S' if gubun == '주식' else 'X'
            query = GetMoneytopQuery(gubun_, startday, endday, starttime, endtime)
            df_mt = pd.read_sql(query, con)
            df_mt['일자'] = df_mt['index'].apply(lambda x: int(str(x)[:8]))
            df_mt.set_index('index', inplace=True)
            con.close()

            if df_mt.empty:
                logger.error("No data found for the specified date range")
                return False

            day_set = set(df_mt['일자'].to_list())

            # 종목코드 추출
            code_set = set()
            for mt_text in df_mt['거래대금순위'].values:
                code_set.update(mt_text.split(';'))

            # 일자별 종목 매핑
            day_codes = {}
            for day in day_set:
                df_mt_ = df_mt[df_mt['일자'] == day]
                codes = set()
                for mt_text in df_mt_['거래대금순위'].values:
                    codes.update(mt_text.split(';'))
                day_codes[day] = codes

            # 종목별 일자 매핑
            code_days = {}
            for code in code_set:
                code_days[code] = {day for day, codes in day_codes.items() if code in codes}

            # 분류 모드 검증
            if divid_mode == '종목코드별 분류' and len(code_set) < self.multi:
                logger.error(f"Not enough codes ({len(code_set)}) for multi={self.multi}")
                return False

            if divid_mode == '일자별 분류' and len(day_set) < self.multi:
                logger.error(f"Not enough days ({len(day_set)}) for multi={self.multi}")
                return False

            if divid_mode == '한종목 로딩' and one_code and one_code not in code_days:
                logger.error(f"Code {one_code} not found in date range")
                return False

            if divid_mode == '한종목 로딩' and one_code and len(code_days[one_code]) < self.multi:
                logger.error(f"Not enough days for code {one_code}")
                return False

            # 종목명 전송 (주식/해선만)
            if gubun in ('주식', '해선'):
                for i in range(self.multi):
                    if gubun == '주식':
                        self.back_eques[i].put(('종목명', self.dict_cn))
                    else:
                        self.back_eques[i].put(('종목명', dict_info))

            logger.info("Code names and money top data extracted")

            # 데이터 로딩
            log_gubun = divid_mode.split()[0]
            if log_gubun == '한종목':
                log_gubun = f'{log_gubun} 일자별'

            logger.info(f"Loading {log_gubun} data...")
            data_list = code_set if log_gubun == '종목코드별' else day_set if log_gubun == '일자별' else code_days[one_code]
            data_lists = []
            for i in range(self.multi):
                data_lists.append([data for j, data in enumerate(data_list) if j % self.multi == i])

            for i, datas in enumerate(data_lists):
                self.back_eques[i].put(('데이터로딩', startday, endday, starttime, endtime,
                                       datas, avg_list, code_days, day_codes, one_code, divid_mode))

            # 데이터 로딩 완료 대기
            self.shared_info = []
            for i in range(self.multi):
                shared_info_ = self.backQ.get()
                self.shared_info += shared_info_
                logger.info(f"{log_gubun} data loading... [{i+1}/{self.multi}]")

            self.shared_info = sorted(self.shared_info, key=lambda x: x['len'], reverse=True)
            logger.info(f"{log_gubun} data loading completed")

            # 공유 데이터 전송
            self.back_count = len(self.shared_info)
            for q in self.back_eques:
                q.put(('공유데이터', self.back_count, self.shared_info))

            logger.info(f"Backtest engine ready (back_count={self.back_count})")
            return True

        except Exception as e:
            logger.error(f"Failed to load data into engines: {e}")
            print_exc()
            return False

    def start_backtest(self,
                      backtest_type: str,
                      buy_strategy: str,
                      sell_strategy: str,
                      start_date: str,
                      end_date: str,
                      start_time: str = None,
                      end_time: str = None,
                      betting: float = 1.0,
                      avgtime: int = 20,
                      multi: int = 1,
                      divid_mode: str = '종목코드별 분류',
                      blacklist: bool = False,
                      **kwargs) -> bool:
        """
        백테스트 시작

        Args:
            backtest_type: 백테스트 타입 ('stock', 'coin', 'future')
            buy_strategy: 매수 전략명
            sell_strategy: 매도 전략명
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            start_time: 시작시간 (HHMMSS 또는 HHMM)
            end_time: 종료시간 (HHMMSS 또는 HHMM)
            betting: 배팅금액 (백만원 단위 또는 계약/USDT)
            avgtime: 평균값계산틱수
            multi: 멀티 프로세스 수
            divid_mode: 분류방법 ('종목코드별 분류', '일자별 분류', '한종목 로딩')
            blacklist: 블랙리스트 추가 여부
            **kwargs: 추가 파라미터

        Returns:
            성공 여부
        """
        if not self.dict_set:
            if not self.load_settings():
                return False

        # 백테스트 모듈 지연 로딩
        _load_backtest_modules()

        try:
            # gubun 매핑
            gubun_map = {
                'stock': '주식',
                'coin': '코인',
                'future': '해선'
            }
            gubun = gubun_map.get(backtest_type)
            if not gubun:
                logger.error(f"Unknown backtest type: {backtest_type}")
                return False

            # ui_gubun 매핑
            ui_gubun_map = {
                '주식': 'S',
                '코인': 'C',
                '해선': 'SF'
            }
            ui_gubun = ui_gubun_map[gubun]

            # 기본값 설정
            if start_time is None:
                if gubun == '주식':
                    start_time = '90000' if self.dict_set['주식타임프레임'] else '900'
                else:
                    start_time = '0' if gubun == '코인' else '93000'

            if end_time is None:
                if gubun == '주식':
                    end_time = '153000' if self.dict_set['주식타임프레임'] else '1520'
                else:
                    end_time = '235000' if gubun == '코인' and self.dict_set['코인타임프레임'] else '2350'

            self.multi = multi
            self.divid_mode = divid_mode

            # 날짜/시간 파싱
            startday = int(start_date)
            endday = int(end_date)
            starttime = int(start_time)
            endtime = int(end_time)
            avg_list = [avgtime]

            logger.info(f"Starting {gubun} backtest: {buy_strategy} / {sell_strategy}")
            logger.info(f"Period: {start_date}~{end_date}, Time: {start_time}~{end_time}")
            logger.info(f"Betting: {betting}, Multi: {multi}, Mode: {divid_mode}")

            # 큐 생성
            self._create_queues()

            # BackSubTotal 프로세스 시작
            self._start_subtotal_processes()

            # BackEngine 프로세스 시작
            self._start_engine_processes(gubun, multi)

            # 데이터 로딩
            if not self._load_data_into_engines(gubun, startday, endday, starttime, endtime,
                                                avg_list, divid_mode, kwargs.get('one_code')):
                self.kill_processes()
                return False

            # 백테스트 파라미터 준비
            backname = f"{gubun}백테스트"
            schedul = False
            back_club = False

            # backQ에 전달할 13-튜플 생성
            back_params = (
                betting,
                avgtime,
                startday,
                endday,
                starttime,
                endtime,
                buy_strategy,
                sell_strategy,
                self.dict_cn,
                self.back_count,
                blacklist,
                schedul,
                back_club
            )

            # BackTest 프로세스 시작
            self.backtest_process = Process(
                target=BackTest,
                args=(self.shared_cnt, self.windowQ, self.backQ, self.soundQ,
                      self.totalQ, self.liveQ, self.teleQ, self.back_eques,
                      self.back_sques, backname, ui_gubun),
                daemon=True
            )
            self.backtest_process.start()
            logger.info("BackTest process started")

            # backQ에 파라미터 전송
            self.backQ.put(back_params)

            # windowQ 모니터링 (결과 출력)
            self._monitor_results()

            # 프로세스 종료 대기
            self.backtest_process.join(timeout=3600)

            logger.info("Backtest completed")
            self.kill_processes()

            return True

        except Exception as e:
            logger.error(f"Failed to start backtest: {e}")
            print_exc()
            self.kill_processes()
            return False

    def _monitor_results(self):
        """windowQ에서 결과 수신 및 출력"""
        while True:
            try:
                if not self.windowQ.empty():
                    data = self.windowQ.get(timeout=0.1)

                    # 데이터 형식 처리
                    if isinstance(data, tuple):
                        if len(data) >= 2:
                            msg_type = data[0]
                            msg_content = data[1] if len(data) == 2 else data[1:]

                            # 진행률 바 메시지
                            if len(data) == 4 and isinstance(data[1], int):
                                current, total, elapsed = data[1], data[2], data[3]
                                percent = (current / total * 100) if total > 0 else 0
                                print(f"Progress: {current}/{total} ({percent:.1f}%) - Elapsed: {elapsed}s")
                            else:
                                print(f"[{msg_type}] {msg_content}")
                        else:
                            print(data)
                    else:
                        print(data)

                # soundQ 확인 (완료 신호)
                if not self.soundQ.empty():
                    sound_msg = self.soundQ.get(timeout=0.1)
                    print(f"[SOUND] {sound_msg}")
                    if '완료' in str(sound_msg):
                        break

                # 프로세스 종료 확인
                if self.backtest_process and not self.backtest_process.is_alive():
                    logger.info("BackTest process terminated")
                    time.sleep(1)  # 잔여 메시지 수신 대기
                    break

                time.sleep(0.1)

            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")
                break

    def kill_processes(self):
        """모든 프로세스 종료"""
        logger.info("Killing all processes...")

        # 엔진 프로세스 종료
        for proc in self.back_eprocs:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=1)
                if proc.is_alive():
                    proc.kill()

        # 서브토탈 프로세스 종료
        for proc in self.back_sprocs:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=1)
                if proc.is_alive():
                    proc.kill()

        # 백테스트 프로세스 종료
        if self.backtest_process and self.backtest_process.is_alive():
            self.backtest_process.terminate()
            self.backtest_process.join(timeout=1)
            if self.backtest_process.is_alive():
                self.backtest_process.kill()

        logger.info("All processes terminated")

    def stop(self):
        """백테스트 중지"""
        logger.info("Stopping backtest...")

        # 중지 신호 전송
        for q in self.back_eques:
            q.put('백테중지')
        if self.totalQ:
            self.totalQ.put('백테중지')

        # 프로세스 종료
        self.kill_processes()
        logger.info("Backtest stopped")
