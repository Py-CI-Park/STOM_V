
import sys
import sqlite3
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from utility.static_method.static import qtest_qwait
from utility.settings.setting_base import DB_TRADELIST
from utility.settings.setting_base import ui_num, columns_cj, columns_jg, columns_td, columns_tdf, columns_jgf, \
    columns_jgcf
from utility.static_method.static import now, str_hms, str_ymd, dt_hms, timedelta_sec, get_inthms, get_str_ymdhms, \
    get_str_ymdhmsf


class MonitorTraderQ(QThread):
    """트레이더 큐를 모니터링하는 스레드 클래스입니다.
    트레이더 큐에서 데이터를 읽어와 시그널로 전송합니다."""
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(tuple)
    signal3 = pyqtSignal(tuple)
    signal4 = pyqtSignal(str)

    def __init__(self, traderQ, market_gubun):
        super().__init__()
        self.traderQ = traderQ
        self.market_gubun = market_gubun

    def run(self):
        """큐 모니터링 루프를 실행합니다."""
        while True:
            data = self.traderQ.get()
            if data.__class__ == tuple:
                if len(data) in (7, 8):
                    if self.market_gubun < 6:
                        self.signal1.emit(data)
                    else:
                        self.signal2.emit(data)
                else:
                    self.signal3.emit(data)
            elif data.__class__ == str:
                self.signal4.emit(data)


class BaseTrader:
    """주문 실행 및 관리를 담당하는 기본 클래스입니다.
    체결 목록, 잔고 목록, 거래 목록을 관리하며,
    주문 생성, 취소, 정정 기능을 제공합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        """
        self.windowQ      = qlist[0]
        self.soundQ       = qlist[1]
        self.queryQ       = qlist[2]
        self.teleQ        = qlist[3]
        self.receivQ      = qlist[8]
        self.traderQ      = qlist[9]
        self.stgQs        = qlist[10]
        self.stgQ         = qlist[10][0]
        self.liveQ        = qlist[11]
        self.dict_set     = dict_set
        self.market_gubun = market_infos[0]
        self.market_info  = market_infos[1]
        self.is_etfn      = self.market_gubun in (2, 3)

        self.dict_cj: dict[str, dict[str, int | float]] = {}  # 체결목록
        self.dict_jg: dict[str, dict[str, int | float]] = {}  # 잔고목록
        self.dict_td: dict[str, dict[str, int | float]] = {}  # 거래목록
        self.dict_signal: dict[str, list] = {}

        self.dict_tj       = {}  # 잔고평가
        self.dict_tt       = {}  # 평가손익
        self.dict_info     = {}
        self.dict_expc     = {}
        self.dict_curc     = {}
        self.dict_lvrg     = {}
        self.dict_pos      = {}
        self.dict_sgbn     = {}
        self.dict_intg = {
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
            '종목당투자금': 0
        }
        self.dict_bool = {
            '잔고청산': False
        }

        if self.market_gubun < 6:
            self.dict_order = {
                '매수': {},
                '매도': {}
            }
        else:
            self.dict_order = {
                'BUY_LONG': {},
                'SELL_LONG': {},
                'SELL_SHORT': {},
                'BUY_SHORT': {}
            }

        self.ls         = None
        self.token      = None
        self.upbit      = None
        self.binance    = None
        self.ws_thread  = None

        self.is_tick    = self.dict_set['타임프레임']
        acc_no          = self.dict_set['거래소'][-2:]
        self.access_key = self.dict_set[f"access_key{acc_no}"]
        self.secret_key = self.dict_set[f"secret_key{acc_no}"]

        self.str_today  = str_ymd()
        self.order_time = now()
        self.jgcs_time  = self.get_jgcs_time()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(500)
        self.qtimer1.timeout.connect(self._scheduler1)
        self.qtimer1.start()

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(1 * 1000)
        self.qtimer2.timeout.connect(self._scheduler2)
        self.qtimer2.start()

        self.updater = MonitorTraderQ(self.traderQ, self.market_gubun)
        self.updater.signal1.connect(self._check_order)
        self.updater.signal2.connect(self._check_order_future)
        self.updater.signal3.connect(self._update_tuple)
        self.updater.signal4.connect(self._update_string)
        self.updater.start()

        self._load_database()

    def _get_yesugm_for_paper_trading(self):
        """모의투스용 예수금을 반환합니다.
        Returns:
            예수금
        """
        from utility.settings.setting_base import DB_TRADELIST
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM {self.market_info['거래디비']}", con)
        con.close()
        tcg = df['수익금'].sum()
        yesugm = 100_000_000 + tcg
        if yesugm < 100_000_000:
            yesugm = 100_000_000
        return yesugm

    def _set_yesugm_and_noti(self, yesugm):
        """예수금을 설정하고 알림을 보냅니다.
        Args:
            yesugm: 예수금
        """
        총매입금액 = sum([v['매입금액'] for v in self.dict_jg.values()]) if self.dict_jg else 0
        self.dict_intg['예수금'] = int(yesugm - 총매입금액)
        self.dict_intg['추정예수금'] = int(yesugm - 총매입금액)
        self.dict_intg['추정예탁자산'] = yesugm

        if self.dict_td:
            self._update_totaltradelist()

        self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 예수금 조회 완료"))
        self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 트레이더 시작"))

    def get_jgcs_time(self):
        """잔고청산 시간을 반환합니다.
        Returns:
            int: 잔고청산 시간 (HHMMSS)
        """
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['전략종료시간'])))))

    def _load_database(self):
        """데이터베이스를 로드합니다."""
        con = sqlite3.connect(DB_TRADELIST)
        df_cj = pd.read_sql(f"SELECT * FROM {self.market_info['체결디비']} WHERE 체결시간 LIKE '{self.str_today}%'", con)
        df_td = pd.read_sql(f"SELECT * FROM {self.market_info['거래디비']} WHERE 체결시간 LIKE '{self.str_today}%'", con)
        df_jg = pd.read_sql(f"SELECT * FROM {self.market_info['잔고디비']}", con)
        df_cj.set_index('index', inplace=True)
        df_td.set_index('index', inplace=True)
        df_jg.set_index('index', inplace=True)
        if len(df_cj) > 0:
            self.dict_cj = df_cj.to_dict('index')
            self.windowQ.put((ui_num['체결목록'], df_cj[::-1]))
        if len(df_td) > 0:
            self.dict_td = df_td.to_dict('index')
            self.windowQ.put((ui_num['거래목록'], df_td[::-1]))
        if len(df_jg) > 0:
            self.dict_jg = df_jg.to_dict('index')
            self.receivQ.put(('잔고목록', tuple(self.dict_jg)))
        con.close()
        self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 데이터베이스 불러오기 완료"))

    def _scheduler1(self):
        """스케줄러1을 실행합니다."""
        data = ('잔고목록', self.dict_jg.copy())
        if self.market_gubun in (1, 4):
            for q in self.stgQs:
                q.put(data)
        else:
            self.stgQ.put(data)

    def _scheduler2(self):
        """스케줄러2를 실행합니다."""
        inthms = get_inthms(self.market_gubun)
        if self.is_tick and inthms < self.dict_set['전략종료시간']:
            self._order_time_control()

        if self.dict_set['잔고청산'] and not self.dict_bool['잔고청산'] and self.jgcs_time < inthms < self.jgcs_time + 10:
            self._jango_cheongsan('자동')

        self._update_totaljango()

    def _check_order(self, data):
        """주문을 확인합니다.
        Args:
            data: 데이터
        """
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg
        매수주문중 = 종목코드 in self.dict_order['매수']
        매도주문중 = 종목코드 in self.dict_order['매도']

        원주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 잔고청산:
            if 잔고없음 or 매도주문중:
                주문취소 = True
        elif self.dict_bool['잔고청산']:
            주문취소 = True
        elif 주문구분 == '매수':
            inthms = get_inthms(self.market_gubun)
            거래횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목명]))
            손절횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목명 and v['수익률'] < 0]))
            if self.dict_set['매수금지거래횟수'] and self.dict_set['매수금지거래횟수값'] <= 거래횟수:
                주문취소 = True
            elif self.dict_set['매수금지손절횟수'] and self.dict_set['매수금지손절횟수값'] <= 손절횟수:
                주문취소 = True
            elif 잔고없음 and inthms < self.dict_set['전략종료시간'] and len(self.dict_jg) >= self.dict_set['최대매수종목수']:
                주문취소 = True
            elif self.dict_set['매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.dict_jg[종목코드]['분할매수횟수'] >= self.dict_set['매수분할횟수']:
                주문취소 = True
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self._create_order('시드부족', 종목코드, 종목명, 주문가격, 주문수량, '', 시그널시간, 잔고청산, 0, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 매수주문중:
                주문취소 = True
        elif 주문구분 == '매도':
            if 잔고없음 or 매도주문중:
                주문취소 = True
            elif self.dict_set['매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
        elif '취소' in 주문구분:
            if 주문구분 == '매수취소' and not 매수주문중:
                주문취소 = True
            elif 주문구분 == '매도취소' and not 매도주문중:
                주문취소 = True

        if 주문취소:
            if '취소' not in 주문구분:
                self._put_order_complete(f'{주문구분}취소', 종목코드)
        else:
            if 주문수량 > 0:
                if 잔고청산:
                    self._put_order_complete(f'{주문구분}주문', 종목코드)
                self._create_order(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 0, 수동주문유형)
            else:
                if 주문구분 == '매수':
                    if self.dict_set['매도취소매수시그널'] and 매도주문중: self._cancel_order(종목코드, 주문구분)
                elif 주문구분 == '매도':
                    if self.dict_set['매수취소매도시그널'] and 매수주문중: self._cancel_order(종목코드, 주문구분)
                self._put_order_complete(f'{주문구분}취소', 종목코드)

    def _check_order_future(self, data):
        """선물 주문을 확인합니다.
        Args:
            data: 데이터
        """
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg
        롱매수주문중 = 종목코드 in self.dict_order['BUY_LONG']
        숏매수주문중 = 종목코드 in self.dict_order['SELL_SHORT']
        롱매도주문중 = 종목코드 in self.dict_order['SELL_LONG']
        숏매도주문중 = 종목코드 in self.dict_order['BUY_SHORT']
        jg_data = self.dict_jg.get(종목코드)
        포지션 = jg_data['포지션'] if jg_data else None

        원주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 잔고청산:
            if 잔고없음 or (주문구분 == 'SELL_LONG' and 롱매도주문중) or (주문구분 == 'BUY_SHORT' and 숏매도주문중):
                주문취소 = True
        elif self.dict_bool['잔고청산']:
            주문취소 = True
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            inthms = get_inthms(self.market_gubun)
            거래횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목코드]))
            손절횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목코드 and v['수익률'] < 0]))
            if self.dict_set['매수금지거래횟수'] and self.dict_set['매수금지거래횟수값'] <= 거래횟수:
                주문취소 = True
            elif self.dict_set['매수금지손절횟수'] and self.dict_set['매수금지손절횟수값'] <= 손절횟수:
                주문취소 = True
            elif 잔고없음 and inthms < self.dict_set['전략종료시간'] and len(self.dict_jg) >= self.dict_set['최대매수종목수']:
                주문취소 = True
            elif self.dict_set['매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.dict_jg[종목코드]['분할매수횟수'] >= self.dict_set['매수분할횟수']:
                주문취소 = True
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self._create_order('시드부족', 종목코드, 종목코드, 주문가격, 주문수량, '', 시그널시간, 잔고청산, 0, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 포지션 == 'LONG' and 'SHORT' in 주문구분: 주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'BUY_LONG' and 롱매수주문중:   주문취소 = True
            elif 주문구분 == 'SELL_SHORT' and 숏매수주문중: 주문취소 = True
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT'):
            if 포지션 == 'LONG' and 'SHORT' in 주문구분:   주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'SELL_LONG' and 롱매도주문중:  주문취소 = True
            elif 주문구분 == 'BUY_SHORT' and 숏매도주문중:  주문취소 = True
            elif self.dict_set['매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
        elif 'CANCEL' in 주문구분:
            if 주문구분 == 'BUY_LONG_CANCEL' and not 롱매수주문중:     주문취소 = True
            elif 주문구분 == 'SELL_SHORT_CANCEL' and not 숏매수주문중: 주문취소 = True
            elif 주문구분 == 'SELL_LONG_CANCEL' and not 롱매도주문중:  주문취소 = True
            elif 주문구분 == 'BUY_SHORT_CANCEL' and not 숏매도주문중:  주문취소 = True

        if 주문취소:
            if 'CANCEL' not in 주문구분:
                self._put_order_complete(f'{주문구분}_CANCEL', 종목코드)
        else:
            if 주문수량 > 0:
                if 잔고청산:
                    self._put_order_complete(f'{주문구분}_MANUAL', 종목코드)
                self._create_order(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 0, 수동주문유형)
            else:
                if 주문구분 == 'BUY_LONG':
                    if self.dict_set['매도취소매수시그널'] and 롱매도주문중: self._cancel_order(종목코드, 주문구분)
                elif 주문구분 == 'SELL_SHORT':
                    if self.dict_set['매도취소매수시그널'] and 숏매도주문중: self._cancel_order(종목코드, 주문구분)
                elif 주문구분 == 'SELL_LONG':
                    if self.dict_set['매수취소매도시그널'] and 롱매수주문중: self._cancel_order(종목코드, 주문구분)
                elif 주문구분 == 'BUY_SHORT':
                    if self.dict_set['매수취소매도시그널'] and 숏매수주문중: self._cancel_order(종목코드, 주문구분)
                self._put_order_complete(f'{주문구분}_CANCEL', 종목코드)

    def _put_order_complete(self, 주문구분, 종목코드):
        """주문 완료를 전송합니다.
        Args:
            주문구분: 주문 구분
            종목코드: 종목 코드
        """
        data = (주문구분, 종목코드)
        if self.market_gubun in (1, 4):
            self.stgQs[self.dict_sgbn[종목코드]].put(data)
        else:
            self.stgQ.put(data)

    def _create_order(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형):
        """주문을 생성합니다.
        Args:
            주문구분: 주문 구분
            종목코드: 종목 코드
            종목명: 종목명
            주문가격: 주문 가격
            주문수량: 주문 수량
            원주문번호: 원 주문 번호
            시그널시간: 시그널 시간
            잔고청산: 잔고 청산 여부
            정정횟수: 정정 횟수
            수동주문유형: 수동 주문 유형
        """
        if self.market_gubun < 6:
            if 주문구분 == '매수' and 정정횟수 == 0:
                if 수동주문유형 is None and '지정가' in self.dict_set['매수주문유형']:
                    주문가격 = self._get_order_buy_price(종목코드, 주문구분, 주문가격)
            elif 주문구분 == '매도' and 정정횟수 == 0:
                if 수동주문유형 is None and '지정가' in self.dict_set['매도주문유형']:
                    주문가격 = self._get_order_sell_price(종목코드, 주문구분, 주문가격)
        else:
            if 주문구분 in ('BUY_LONG', 'SELL_SHORT') and 정정횟수 == 0:
                if 수동주문유형 is None and '지정가' in self.dict_set['매수주문유형']:
                    주문가격 = self._get_order_buy_price(종목코드, 주문구분, 주문가격)

            elif 주문구분 in ('SELL_LONG', 'BUY_SHORT') and 정정횟수 == 0:
                if 수동주문유형 is None and '지정가' in self.dict_set['매도주문유형']:
                    주문가격 = self._get_order_sell_price(종목코드, 주문구분, 주문가격)

        if self.market_gubun == 5 and 주문수량 * 주문가격 < 5000:
            self.windowQ.put((ui_num['시스템로그'], f'오류 알림 - 주문금액이 5천원미만입니다.'))
            self._put_order_complete(f'{주문구분}취소', 종목코드)
            return

        if self.market_gubun == 9 and 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            주문수량 = round(주문수량 * self.dict_lvrg[종목코드], self.dict_info[종목코드]['수량소숫점자리수'])

        if self.market_gubun in (6, 7, 8):
            self.dict_signal[종목코드] = [주문구분, 주문가격, 주문수량, 0]

        if self.dict_set['모의투자'] or 주문구분 == '시드부족':
            self._push_chejan_data_for_paper_trade(주문구분, 종목코드, 주문수량, 주문가격, 시그널시간)
        else:
            data = (주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형)
            self._send_order(data)

    def _push_chejan_data_for_paper_trade(self, 주문구분, 종목코드, 주문수량, 주문가격, 시그널시간):
        """모의투스용 체결 데이터를 전송합니다.
        Args:
            주문구분: 주문 구분
            종목코드: 종목 코드
            주문수량: 주문 수량
            주문가격: 주문 가격
            시그널시간: 시그널 시간
        """
        self._order_time_log(시그널시간)
        체결시간 = get_str_ymdhms(self.market_gubun)
        if 주문구분 == '시드부족':
            체결가격, 체결수량, 미체결수량 = 0, 0, 주문수량
        else:
            체결가격, 체결수량, 미체결수량 = 주문가격, 주문수량, 0

        if self.market_gubun < 6:
            호가단위 = self._get_hogaunit(주문가격)
        else:
            호가단위 = self._get_hogaunit(종목코드)

        if 주문구분 != '시드부족':
            if self.market_gubun == 9:
                self.dict_order[주문구분][종목코드] = [
                    timedelta_sec(self.dict_set['매수취소시간초']), 0, 주문가격, 호가단위, self.dict_lvrg[종목코드]
                ]
            else:
                self.dict_order[주문구분][종목코드] = [
                    timedelta_sec(self.dict_set['매수취소시간초']), 0, 주문가격, 호가단위
                ]

        if self.market_gubun < 6:
            self._update_chejan_data(
                주문구분, '체결', 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 체결시간, '모의투자'
            )
        elif self.market_gubun < 9:
            self._update_chejan_data_future('체결', 종목코드, 주문수량, 주문가격, 체결시간, '모의투자')
        else:
            self._update_chejan_data_coin_future(
                주문구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 체결시간, '모의투자'
            )

    def _check_order_error(self, 주문번호, 응답메시지, 주문구분, 종목명, 주문가격, 주문수량):
        if 주문번호 == 0:
            if 'Traceback' in 응답메시지:
                self.windowQ.put((ui_num['시스템로그'], 응답메시지))
            else:
                주문구분기록 = f'{주문구분}실패' if self.market_gubun < 6 else f'{주문구분}_FAIL'
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분기록}] {종목명} | {주문가격} | {주문수량} | {응답메시지}'
                ))
            return False
        return True

    def _order_time_log(self, signal_time):
        """주문 시간 로그를 기록합니다.
        Args:
            signal_time: 시그널 시간
        """
        gap = (now() - signal_time).total_seconds()
        self.windowQ.put((ui_num['타임로그'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.'))

    def _update_tuple(self, data):
        """튜플을 업데이트합니다.
        Args:
            data: 데이터
        """
        gubun, data = data
        if gubun == '잔고갱신':
            self._update_jango(data)
        elif gubun == '주문확인':
            code, c = data
            self.dict_curc[code] = c
            self._order_time_control(code)
        elif gubun == '저가대비고가등락율':
            self._set_leverage(data)
        if gubun == '관심진입':
            if self.market_gubun < 6:
                if data in self.dict_order['매도']:
                    self._cancel_order(data, '매도')
            else:
                if data in self.dict_order['SELL_LONG']:
                    self._cancel_order(data, 'SELL_LONG')
                if data in self.dict_order['BUY_SHORT']:
                    self._cancel_order(data, 'BUY_SHORT')
        elif gubun == '관심이탈':
            if self.market_gubun < 6:
                if data in self.dict_order['매수']:
                    self._cancel_order(data, '매수')
            else:
                if data in self.dict_order['BUY_LONG']:
                    self._cancel_order(data, 'BUY_LONG')
                if data in self.dict_order['SELL_SHORT']:
                    self._cancel_order(data, 'SELL_SHORT')
        elif gubun == '설정변경':
            self.dict_set = data
            self.jgcs_time = self.get_jgcs_time()
        elif gubun == '종목정보':
            if self.market_gubun in (1, 4):
                self.dict_info, self.dict_sgbn = data
            elif self.market_gubun in (6, 7):
                self.dict_info, self.dict_expc = data
            else:
                self.dict_info = data
            self._update_dict_info()
            if self.market_gubun == 9:
                self._set_position()

    def _update_jango(self, data):
        """잔고를 업데이트합니다.
        Args:
            data: 데이터
        """
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            if 현재가 != self.dict_jg[종목코드]['현재가']:
                매입금액 = self.dict_jg[종목코드]['매입금액']
                보유수량 = self.dict_jg[종목코드]['보유수량']

                if self.market_gubun < 6 or self.market_gubun == 9:
                    보유금액 = 보유수량 * 현재가
                else:
                    매수가 = self.dict_jg[종목코드]['매수가']
                    보유금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량

                if self.market_gubun < 6:
                    평가금액, 평가손익, 수익률 = self._get_profit(매입금액, 보유금액)
                else:
                    포지션 = self.dict_jg[종목코드]['포지션']
                    if 포지션 == 'LONG':
                        평가금액, 평가손익, 수익률 = self._get_profit_long(매입금액, 보유금액)
                    else:
                        평가금액, 평가손익, 수익률 = self._get_profit_short(매입금액, 보유금액)

                self.dict_jg[종목코드].update({
                    '현재가': 현재가,
                    '수익률': 수익률,
                    '평가손익': 평가손익,
                    '평가금액': 평가금액
                })
        except Exception:
            pass

    def _update_dict_info(self):
        """정보 딕셔너리를 업데이트합니다."""
        dummy_time = timedelta_sec(-3600)
        for code in self.dict_info.copy():
            self.dict_info[code].update({
                '시드부족시간': dummy_time,
                '최종거래시간': dummy_time,
                '손절거래시간': dummy_time
            })

    # noinspection PyUnresolvedReferences
    def _order_time_control(self, code_=None):
        """주문시간 및 주문가격을 확인하여 취소 및 정정 주문을 생성합니다.
        Args:
            code_: 종목 코드
        """
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order:
            for code in self.dict_order[gubun]:
                if code_ is None or code == code_:
                    if self.market_gubun < 9:
                        주문취소시간, 정정횟수, 주문가격, 호가단위 = self.dict_order[gubun][code]
                    else:
                        주문취소시간, 정정횟수, 주문가격, 호가단위, _ = self.dict_order[gubun][code]

                    if self.market_gubun < 6:
                        매수매도구분 = gubun
                        범위이탈구분 = gubun == '매수'
                    else:
                        매수매도구분 = '매수' if gubun in ('BUY_LONG', 'SELL_SHORT') else '매도'
                        범위이탈구분 = 'BUY' in gubun

                    범위이탈 = False
                    호가차이 = 호가단위 * self.dict_set[f'{매수매도구분}정정호가차이']
                    현재가 = self.dict_curc.get(code)
                    if 현재가:
                        if 범위이탈구분:
                            범위이탈 = 현재가 >= 주문가격 + 호가차이
                        else:
                            범위이탈 = 현재가 <= 주문가격 - 호가차이

                    if self.dict_set[f'{매수매도구분}취소시간'] and now() > 주문취소시간:
                        cancel_list.append((code, gubun))

                    elif 정정횟수 < self.dict_set[f'{매수매도구분}정정횟수'] and 범위이탈:
                        정정호가 = self.dict_set[f'{매수매도구분}정정호가']
                        if 범위이탈구분:
                            정정가격 = self._get_modify_buy_price(현재가, 정정호가, code)
                        else:
                            정정가격 = self._get_modify_sell_price(현재가, 정정호가, code)
                        modify_list.append((code, gubun, 정정가격))

        if cancel_list:
            for code, gubun in cancel_list:
                self._cancel_order(code, gubun)
        if modify_list:
            for code, gubun, 정정가격 in modify_list:
                self._modify_order(code, gubun, 정정가격)

    def _cancel_order(self, 종목코드, 주문구분):
        """주문을 취소합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
        """
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self._get_chejan_last_value(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                원주문번호, 원주문가격 = last_value['주문번호'], last_value['주문가격']
                if self.market_gubun < 6:
                    self._create_order(
                        f'{주문구분}취소', 종목코드, 종목명, 원주문가격, 미체결수량, 원주문번호, now(), False, 0, None
                    )
                else:
                    self._create_order(
                        f'{주문구분}_CANCEL', 종목코드, 종목명, 원주문가격, 미체결수량, 원주문번호, now(), False, 0, None
                    )

    def _modify_order(self, 종목코드, 주문구분, 정정가격):
        """주문을 정정합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
            정정가격: 정정 가격
        """
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self._get_chejan_last_value(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                정정횟수 = self.dict_order[주문구분][종목코드][1] + 1
                원주문번호, 원주문가격 = last_value['주문번호'], last_value['주문가격']
                if self.market_gubun < 5:
                    self._create_order(
                        f'{주문구분}정정', 종목코드, 종목명, 정정가격, 미체결수량, 원주문번호, now(), False, 정정횟수, None
                    )
                elif self.market_gubun == 5:
                    self._create_order(
                        f'{주문구분}취소', 종목코드, 종목명, 원주문가격, 미체결수량, 원주문번호, now(), False, 0, None
                    )
                    self._create_order(
                        주문구분, 종목코드, 종목명, 정정가격, 미체결수량, '', now(), False, 정정횟수, None
                    )
                elif self.market_gubun < 9:
                    self._create_order(
                        f'{주문구분}_MODIFY', 종목코드, 종목명, 정정가격, 미체결수량, 원주문번호, now(), False, 정정횟수, None
                    )
                else:
                    self._create_order(
                        f'{주문구분}_CANCEL', 종목코드, 종목코드, 원주문가격, 미체결수량, 원주문번호, now(), False, 0, None
                    )
                    self._create_order(
                        주문구분, 종목코드, 종목코드, 정정가격, 미체결수량, '', now(), False, 정정횟수, None
                    )

    def _get_chejan_last_value(self, code, gubun):
        """체결 마지막 값을 반환합니다.
        Args:
            code: 종목 코드
            gubun: 구분
        Returns:
            체결 마지막 값
        """
        if self.market_gubun < 6:
            return [v for v in self.dict_cj.values() if v['종목명'] == code and
                    (v['주문구분'] == gubun or v['주문구분'] == f'{gubun} 접수')][-1]
        else:
            return [v for v in self.dict_cj.values() if v['종목명'] == code and
                    (v['주문구분'] == gubun or v['주문구분'] == f'{gubun}_REG')][-1]

    def _update_string(self, data):
        """문자열을 업데이트합니다.
        Args:
            data: 데이터
        """
        if data == '잔고청산':
            self._jango_cheongsan('수동')
        elif data == '프로세스종료':
            self._sys_exit()

    def _jango_cheongsan(self, gubun):
        """잔고 청산을 수행합니다.
        Args:
            gubun: 구분
        """
        for 주문구분 in self.dict_order:
            for 종목코드 in self.dict_order[주문구분]:
                self._cancel_order(종목코드, 주문구분)

        if self.dict_jg:
            if gubun == '수동':
                self.teleQ.put(f"{self.market_info['마켓이름']} 잔고청산 주문을 전송합니다.")
            for 종목코드 in self.dict_jg.copy():
                종목명 = self.dict_jg[종목코드]['종목명']
                현재가 = self.dict_jg[종목코드]['현재가']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                if self.market_gubun < 6:
                    주문구분 = '매도'
                else:
                    포지션 = self.dict_jg[종목코드]['포지션']
                    주문구분 = 'SELL_LONG' if 포지션 == 'LONG' else 'BUY_SHORT'
                if self.dict_set['모의투자']:
                    self._push_chejan_data_for_paper_trade(주문구분, 종목코드, 보유수량, 현재가, now())
                else:
                    self._check_order((주문구분, 종목코드, 종목명, 현재가, 보유수량, now(), True))
            if self.dict_set['알림소리']:
                self.soundQ.put(f"{self.market_info['마켓이름']} 잔고청산 주문을 전송하였습니다.")
            self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 잔고청산 주문 완료"))
        elif gubun == '수동':
            self.teleQ.put(f"현재는 {self.market_info['마켓이름']} 보유종목이 없습니다.")
        self.dict_bool['잔고청산'] = True

    def _sys_exit(self):
        """시스템을 종료합니다."""
        self._websocket_kill()
        self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 트레이더 종료"))
        qtest_qwait(1)
        sys.exit()

    def _websocket_kill(self):
        """웹소켓을 종료합니다."""
        if self.ws_thread:
            self.ws_thread.stop()
            self.ws_thread.terminate()
            self.ws_thread = None

    def _get_index(self):
        """체결목록용 인덱스를 반환합니다.
        Returns:
            인덱스
        """
        index = get_str_ymdhmsf(self.market_gubun)
        if index in self.dict_cj:
            while index in self.dict_cj:
                index = str(int(index) + 1)
        return index

    def _update_chejan_data(self, 주문구분, 체결구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 체결시간, 주문번호):
        """체결 데이터를 업데이트합니다.
        Args:
            주문구분: 주문 구분
            체결구분: 체결 구분
            종목코드: 종목 코드
            주문수량: 주문 수량
            체결수량: 체결 수량
            미체결수량: 미체결 수량
            체결가격: 체결 가격
            주문가격: 주문 가격
            체결시간: 체결 시간
            주문번호: 주문 번호
        """
        if 주문구분 != '시드부족' and 종목코드 not in self.dict_order[주문구분]:
            self.windowQ.put((ui_num['시스템로그'], '오류 알림 - 수동 주문은 기록하지 않습니다.'))
            return

        index = self._get_index()
        종목명 = self.dict_info[종목코드]['종목명']

        if 체결구분 == '체결' and 주문구분 != '시드부족':
            if 주문구분 == '매수':
                if 종목코드 in self.dict_jg:
                    보유수량 = self.dict_jg[종목코드]['보유수량'] + 체결수량
                    매입금액 = self.dict_jg[종목코드]['매입금액'] + 체결수량 * 체결가격
                    매수가 = int(매입금액 / 보유수량 + 0.5)
                    평가금액, 수익금, 수익률 = self._get_profit(매입금액, 보유수량 * 체결가격)

                    self.dict_jg[종목코드].update({
                        '매수가': 매수가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': 체결시간
                    })
                else:
                    보유수량 = 체결수량
                    매입금액 = 체결수량 * 체결가격
                    매수가 = 체결가격
                    평가금액, 수익금, 수익률 = self._get_profit(매입금액, 보유수량 * 체결가격)

                    self.dict_jg[종목코드] = {
                        '종목명': 종목명,
                        '매수가': 매수가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '분할매수횟수': 0,
                        '분할매도횟수': 0,
                        '매수시간': 체결시간
                    }

                if 미체결수량 == 0:
                    self.dict_jg[종목코드]['분할매수횟수'] += 1
                    del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.dict_jg:
                    return
                보유수량 = self.dict_jg[종목코드]['보유수량'] - 체결수량
                매수가 = self.dict_jg[종목코드]['매수가']
                if 보유수량 != 0:
                    매입금액 = 매수가 * 보유수량
                    평가금액, 수익금, 수익률 = self._get_profit(매입금액, 보유수량 * 체결가격)

                    self.dict_jg[종목코드].update({
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량
                    })
                else:
                    del self.dict_jg[종목코드]

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매도횟수'] += 1
                    del self.dict_order[주문구분][종목코드]

                매입금액 = 매수가 * 체결수량
                평가금액, 수익금, 수익률 = self._get_profit(매입금액, 체결수량 * 체결가격)

                if -100 < 수익률 < 100:
                    self._update_tradelist(index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 체결시간)

                if 수익률 < 0:
                    self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['매수금지손절간격초'])

            self.dict_jg = dict(sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True))

            if 미체결수량 == 0:
                self._put_order_complete(f'{주문구분}완료', 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            if 주문구분 == '매수':
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            if self.dict_set['알림소리']:
                self.soundQ.put(f'{종목명} {체결수량}주를 {주문구분[:2]}하였습니다')

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {체결가격} | {체결수량}'))

        elif 체결구분 in ('정정', '취소'):
            if 체결구분 == '정정':
                정정횟수 = self.dict_order[주문구분][종목코드][1] + 1
                취소시간 = timedelta_sec(self.dict_set['매수취소시간초' if 주문구분 == '매수' else '매도취소시간초'])
                self.dict_order[주문구분][종목코드] = [취소시간, 정정횟수, 주문가격, self._get_hogaunit(주문가격)]
            else:
                if 주문구분 == '매수':
                    self.dict_intg['추정예수금'] += 미체결수량 * 주문가격

                del self.dict_order[주문구분][종목코드]

                self._put_order_complete(주문구분, 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            if self.dict_set['알림소리']:
                self.soundQ.put(f'{종목명} {주문수량}주를 {주문구분}하였습니다')

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {주문가격} | {주문수량}'))

        elif 주문구분 == '시드부족':
            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

        self.receivQ.put(('잔고목록', tuple(self.dict_jg)))

    def _update_chejan_data_future(self, 체결구분, 종목코드, 체결수량, 체결가격, 체결시간, 주문번호):
        """선물 체결 데이터를 업데이트합니다.
        Args:
            체결구분: 체결 구분
            종목코드: 종목 코드
            체결수량: 체결 수량
            체결가격: 체결 가격
            체결시간: 체결 시간
            주문번호: 주문 번호
        """
        signal_data = self.dict_signal.get(종목코드)
        if signal_data is None:
            self.windowQ.put((ui_num['시스템로그'], '오류 알림 - 수동 주문은 기록하지 않습니다.'))
            return

        index = self._get_index()
        종목명 = self.dict_info[종목코드]['종목명']
        주문구분, 주문가격, 주문수량, 체결된수량 = signal_data

        if 체결구분 == '체결' and 주문구분 != '시드부족':
            if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                if 종목코드 in self.dict_jg:
                    직전매수가 = self.dict_jg[종목코드]['매수가']
                    직전보유수량 = self.dict_jg[종목코드]['보유수량']
                    직전매입금액 = self.dict_jg[종목코드]['매입금액']
                    보유수량 = 직전보유수량 + 체결수량
                    매입금액 = 직전매입금액 + self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    매수가 = round((직전매수가 * 직전보유수량 + 체결가격 * 체결수량) / 보유수량, self.dict_info[종목코드]['소숫점자리수'] + 1)
                    보유금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in 주문구분:
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액, 종목코드)

                    self.dict_jg[종목코드].update({
                        '매수가': 매수가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': index[:14]
                    })
                else:
                    보유수량 = 체결수량
                    매입금액 = 보유금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    if 'LONG' in 주문구분:
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액, 종목코드)
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액, 종목코드)

                    self.dict_jg[종목코드] = {
                        '종목명': 종목명,
                        '포지션': 포지션,
                        '매수가': 체결가격,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 체결수량,
                        '분할매수횟수': 0,
                        '분할매도횟수': 0,
                        '매수시간': index[:14]
                    }

                체결된수량 += 체결수량
                미체결수량 = 주문수량 - 체결된수량
                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매수횟수'] += 1
                    del self.dict_order[signal_data][종목코드]
                    del self.dict_signal[종목코드]
                else:
                    signal_data[-1] = 체결된수량

            else:
                if 종목코드 not in self.dict_jg:
                    return
                포지션 = self.dict_jg[종목코드]['포지션']
                매수가 = self.dict_jg[종목코드]['매수가']
                보유수량 = self.dict_jg[종목코드]['보유수량'] - 체결수량
                if 보유수량 != 0:
                    매입금액 = self.dict_info[종목코드]['위탁증거금'] * 보유수량
                    보유금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in 주문구분:
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액, 종목코드)

                    self.dict_jg[종목코드].update({
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량
                    })
                else:
                    del self.dict_jg[종목코드]

                체결된수량 += 체결수량
                미체결수량 = 주문수량 - 체결된수량
                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매도횟수'] += 1
                    del self.dict_order[signal_data][종목코드]
                    del self.dict_signal[종목코드]
                else:
                    signal_data[-1] = 체결된수량

                매입금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                보유금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 체결수량
                if 'LONG' in 주문구분:
                    평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액, 종목코드)
                else:
                    평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액, 종목코드)

                if -100 < 수익률 < 100:
                    self._update_tradelist(index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 체결시간, 포지션)

                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['매수금지손절간격초'])

            self.dict_jg = dict(sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True))

            if 미체결수량 == 0:
                self._put_order_complete(f'{주문구분}_COMPLETE', 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            위탁증거금 = 체결수량 * self.dict_info[종목코드]['위탁증거금']
            if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                self.dict_intg['예수금'] -= 위탁증거금
                if self.dict_set['모의투자']:
                    self.dict_intg['추정예수금'] -= 위탁증거금
            else:
                self.dict_intg['추정예탁자산'] += 수익금
                self.dict_intg['예수금'] += 위탁증거금 + 수익금
                self.dict_intg['추정예수금'] += 위탁증거금 + 수익금

            if self.dict_set['알림소리']:
                self.soundQ.put(f'{종목명} {체결수량}주를 {주문구분}하였습니다')

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {체결가격} | {체결수량}'))

        elif 체결구분 in ('정정', '취소'):
            if 체결구분 == '정정':
                정정횟수 = self.dict_order[주문구분][종목코드][1] + 1
                취소시간 = timedelta_sec(self.dict_set['매수취소시간초' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도취소시간초'])
                self.dict_order[주문구분][종목코드] = [취소시간, 정정횟수, 주문가격, self._get_hogaunit(종목코드)]
            else:
                if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                    self.dict_intg['추정예수금'] += 주문수량 * self.dict_info[종목코드]['위탁증거금']

                del self.dict_order[주문구분][종목코드]
                del self.dict_signal[종목코드]

                self._put_order_complete(주문구분, 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            if self.dict_set['알림소리']:
                self.soundQ.put(f'{종목명} {주문수량}주를 {주문구분}하였습니다')

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {주문가격} | {주문수량}'))

        elif 주문구분 == '시드부족':
            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

        self.receivQ.put(('잔고목록', tuple(self.dict_jg)))

    def _update_chejan_data_coin_future(self, 주문구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 체결시간, 주문번호):
        """코인 선물 체결 데이터를 업데이트합니다.
        Args:
            주문구분: 주문 구분
            종목코드: 종목 코드
            주문수량: 주문 수량
            체결수량: 체결 수량
            미체결수량: 미체결 수량
            체결가격: 체결 가격
            주문가격: 주문 가격
            체결시간: 체결 시간
            주문번호: 주문 번호
        """
        if 주문구분 != '시드부족' and 종목코드 not in self.dict_order[주문구분]:
            self.windowQ.put((ui_num['시스템로그'], '오류 알림 - 수동 주문은 기록하지 않습니다.'))
            return

        index = self._get_index()
        종목명 = self.dict_info[종목코드]['종목명']

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT', 'SELL_LONG', 'BUY_SHORT'):
            if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                if 종목코드 in self.dict_jg:
                    보유수량 = round(self.dict_jg[종목코드]['보유수량'] + 체결수량, self.dict_info[종목코드]['소숫점자리수'])
                    매입금액 = round(self.dict_jg[종목코드]['매입금액'] + 체결수량 * 체결가격, 4)
                    매수가 = round(매입금액 / 보유수량, 8)
                    보유금액 = round(체결가격 * 보유수량, 4)
                    if 주문구분 == 'BUY_LONG':
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액)
                    else:
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액)

                    self.dict_jg[종목코드].update({
                        '매수가': 매수가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': 체결시간
                    })
                else:
                    매입금액 = 보유금액 = round(체결가격 * 체결수량, 4)
                    if self.dict_set['바이낸스선물고정레버리지']:
                        레버리지 = self.dict_set['바이낸스선물고정레버리지값']
                    else:
                        레버리지 = self.dict_order[주문구분][종목코드][4]
                    if 주문구분 == 'BUY_LONG':
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액)
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액)

                    self.dict_jg[종목코드] = {
                        '종목명': 종목명,
                        '포지션': 포지션,
                        '매수가': 체결가격,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 체결수량,
                        '분할매수횟수': 0,
                        '분할매도횟수': 0,
                        '매수시간': 체결시간,
                        '레버리지': 레버리지
                    }

                if 미체결수량 == 0:
                    self.dict_jg[종목코드]['분할매수횟수'] += 1
                    del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.dict_jg:
                    return
                포지션 = self.dict_jg[종목코드]['포지션']
                매수가 = self.dict_jg[종목코드]['매수가']
                보유수량 = round(self.dict_jg[종목코드]['보유수량'] - 체결수량, self.dict_info[종목코드]['소숫점자리수'])
                if 보유수량 != 0:
                    매입금액 = round(매수가 * 보유수량, 4)
                    보유금액 = round(체결가격 * 보유수량, 4)
                    if 주문구분 == 'SELL_LONG':
                        평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액)
                    else:
                        평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액)
                    """['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량',
                        '분할매수횟수', '분할매도횟수', '매수시간', '레버리지']"""
                    self.dict_jg[종목코드].update({
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량
                    })
                else:
                    del self.dict_jg[종목코드]

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매도횟수'] += 1
                    del self.dict_order[주문구분][종목코드]

                매입금액 = round(매수가 * 체결수량, 4)
                보유금액 = round(체결가격 * 체결수량, 4)
                if 주문구분 == 'SELL_LONG':
                    평가금액, 수익금, 수익률 = self._get_profit_long(매입금액, 보유금액)
                else:
                    평가금액, 수익금, 수익률 = self._get_profit_short(매입금액, 보유금액)

                if -100 < 수익률 < 100:
                    self._update_tradelist(index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 체결시간, 포지션)

                if 수익률 < 0:
                    self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['매수금지손절간격초'])

            self.dict_jg = dict(sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True))

            if 미체결수량 == 0:
                self._put_order_complete(f'{주문구분}_COMPLETE', 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            if self.dict_set['모의투자']:
                if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                    self.dict_intg['예수금'] -= 체결수량 * 체결가격
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
                else:
                    self.dict_intg['예수금'] += 매입금액 + 수익금
                    self.dict_intg['추정예수금'] += 매입금액 + 수익금

            if self.dict_set['알림소리']:
                text = ''
                if 주문구분 == 'BUY_LONG':     text = '롱포지션을 진입'
                elif 주문구분 == 'SELL_SHORT': text = '숏포지션을 진입'
                elif 주문구분 == 'SELL_LONG':  text = '롱포지션을 청산'
                elif 주문구분 == 'BUY_SHORT':  text = '숏포지션을 청산'
                self.soundQ.put(f"{종목코드} {text}하였습니다.")

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {체결가격} | {체결수량}'))

        elif 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL', 'SELL_LONG_CANCEL', 'BUY_SHORT_CANCEL'):
            if 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL'):
                self.dict_intg['추정예수금'] += 주문수량 * 주문가격

            gubun = 주문구분.replace('_CANCEL', '')
            del self.dict_order[gubun][종목코드]

            self._put_order_complete(주문구분, 종목코드)

            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

            if self.dict_set['알림소리']:
                text = ''
                if 주문구분 == 'BUY_LONG_CANCEL':     text = '롱포지션 진입을 취소'
                elif 주문구분 == 'SELL_SHORT_CANCEL': text = '숏포지션 진입을 취소'
                elif 주문구분 == 'SELL_LONG_CANCEL':  text = '롱포지션 청산을 취소'
                elif 주문구분 == 'BUY_SHORT_CANCEL':  text = '숏포지션 청산을 취소'
                self.soundQ.put(f"{종목코드} {text}하였습니다.")

            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {주문가격} | {주문수량}'))

        elif 주문구분 == '시드부족':
            self._update_chegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호)

        self.receivQ.put(('잔고목록', tuple(self.dict_jg)))

    def _update_tradelist(self, index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간, 포지션=None):
        """거래 리스트를 업데이트합니다.
        Args:
            index: 인덱스
            종목명: 종목명
            매입금액: 매입 금액
            평가금액: 평가 금액
            체결수량: 체결 수량
            수익률: 수익률
            수익금: 수익금
            주문시간: 주문 시간
            포지션: 포지션
        """
        if 포지션 is None:
            self.dict_td[index] = {
                '종목명': 종목명,
                '매수금액': 매입금액,
                '매도금액': 평가금액,
                '주문수량': 체결수량,
                '수익률': 수익률,
                '수익금': 수익금,
                '체결시간': 주문시간
            }
        else:
            self.dict_td[index] = {
                '종목명': 종목명,
                '포지션': 포지션,
                '매수금액': 매입금액,
                '매도금액': 평가금액,
                '주문수량': 체결수량,
                '수익률': 수익률,
                '수익금': 수익금,
                '체결시간': 주문시간
            }

        df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
        self.windowQ.put((ui_num['거래목록'], df_td[::-1]))

        if 포지션 is None:
            data = [[종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]]
            columns = columns_td
        else:
            data = [[종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]]
            columns = columns_tdf
        df = pd.DataFrame(data, columns=columns, index=[index])
        self.queryQ.put(('거래디비', df, self.market_info['거래디비'], 'append'))

        self._update_totaltradelist()

    def _update_totaltradelist(self, first=False):
        """전체 거래 리스트를 업데이트합니다.
        Args:
            first: 첫 번째 여부
        """
        td_values = self.dict_td.values()
        거래횟수 = len(set([(v['종목명'], v['체결시간']) for v in td_values]))
        총매수금액 = sum([v['매수금액'] for v in td_values])
        총매도금액 = sum([v['매도금액'] for v in td_values])
        총수익금액 = sum([v['수익금'] for v in td_values if v['수익금'] >= 0])
        총손실금액 = sum([v['수익금'] for v in td_values if v['수익금'] < 0])
        수익금합계 = sum([v['수익금'] for v in td_values])
        수익률 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)

        self.dict_tt[self.str_today] = {
            '거래횟수': 거래횟수,
            '총매수금액': 총매수금액,
            '총매도금액': 총매도금액,
            '총수익금액': 총수익금액,
            '총손실금액': 총손실금액,
            '수익률': 수익률,
            '수익금합계': 수익금합계
        }

        df_tt = pd.DataFrame.from_dict(self.dict_tt, orient='index')
        delete_query = f"DELETE FROM {self.market_info['손익디비']} WHERE `index` = '{self.str_today}'"
        self.queryQ.put(('거래디비', delete_query))
        self.queryQ.put(('거래디비', df_tt, self.market_info['손익디비'], 'append'))
        self.windowQ.put((ui_num['실현손익'], df_tt))

        if not first:
            QTimer.singleShot(1 * 1000, lambda: self.windowQ.put('매도완료'))

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.liveQ.put((self.market_info['마켓구분'], data_list))

    def _update_chegeollist(self, index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        """체결 리스트를 업데이트합니다.
        Args:
            index: 인덱스
            종목코드: 종목 코드
            종목명: 종목명
            주문구분: 주문 구분
            주문수량: 주문 수량
            체결수량: 체결 수량
            미체결수량: 미체결 수량
            체결가격: 체결 가격
            체결시간: 체결 시간
            주문가격: 주문 가격
            주문번호: 주문 번호
        """
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['매수금지간격초'])
        self.dict_cj[index] = {
            '종목명': 종목명,
            '주문구분': 주문구분,
            '주문수량': 주문수량,
            '체결수량': 체결수량,
            '미체결수량': 미체결수량,
            '체결가': 체결가격,
            '체결시간': 체결시간,
            '주문가격': 주문가격,
            '주문번호': 주문번호
        }

        self.dict_cj = dict(sorted(self.dict_cj.items(), key=lambda x: x[0]))
        df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
        self.windowQ.put((ui_num['체결목록'], df_cj[::-1]))

        df = pd.DataFrame(
            [[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]],
            columns=columns_cj,
            index=[index]
        )
        self.queryQ.put(('거래디비', df, self.market_info['체결디비'], 'append'))

    def _update_totaljango(self):
        """잔고평가를 업데이트합니다."""
        if self.dict_jg:
            jg_values = self.dict_jg.values()
            총평가손익 = sum([v['평가손익'] for v in jg_values])
            총매입금액 = sum([v['매입금액'] for v in jg_values])
            총평가금액 = sum([v['평가금액'] for v in jg_values])
            총수익률 = round(총평가손익 / 총매입금액 * 100, 2)
            잔고수량 = len(self.dict_jg)
            추정예탁자산 = self.dict_intg['예수금'] + 총평가금액
        else:
            총평가손익, 총매입금액, 총평가금액, 총수익률, 잔고수량 = 0, 0, 0, 0., 0
            추정예탁자산 = self.dict_intg['예수금']

        self.dict_tj[self.str_today] = {
            '추정예탁자산': 추정예탁자산,
            '추정예수금': self.dict_intg['예수금'],
            '보유종목수': 잔고수량,
            '수익률': 총수익률,
            '총평가손익': 총평가손익,
            '총매입금액': 총매입금액,
            '총평가금액': 총평가금액
        }

        거래수익금합계 = sum([v['수익금'] for v in self.dict_td.values()])
        당일평가손익 = 총평가손익 + 거래수익금합계

        if self.dict_set['손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['손실중지수익률'] / 100
            if 기준손실금 < -당일평가손익:
                self._strategy_stop()

        if self.dict_set['수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['수익중지수익률'] / 100
            if 기준수익금 < 당일평가손익:
                self._strategy_stop()

        if self.dict_set['투자금고정']:
            종목당투자금 = int(self.dict_set['투자금'] * (1_000_000 if self.market_gubun in (1, 2, 3, 5) else 1))
        else:
            종목당투자금 = int(self.dict_intg['추정예탁자산'] * 0.98 / self.dict_set['최대매수종목수'])

        if self.dict_intg['종목당투자금'] != 종목당투자금:
            self.dict_intg['종목당투자금'] = 종목당투자금
            if self.market_gubun in (1, 4):
                for q in self.stgQs:
                    q.put(('종목당투자금', self.dict_intg['종목당투자금']))
            else:
                self.stgQ.put(('종목당투자금', self.dict_intg['종목당투자금']))

        if self.dict_jg:
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
        else:
            columns = columns_jg if self.market_gubun < 6 else columns_jgf if self.market_gubun < 8 else columns_jgcf
            df_jg = pd.DataFrame(columns=columns)
        df_tj = pd.DataFrame.from_dict(self.dict_tj, orient='index')
        self.windowQ.put((ui_num['잔고목록'], df_jg))
        self.windowQ.put((ui_num['잔고평가'], df_tj))
        self.queryQ.put(('거래디비', df_jg, self.market_info['잔고디비'], 'replace'))

    def _strategy_stop(self):
        """전략을 중지합니다."""
        if self.market_gubun in (1, 4):
            for q in self.stgQs:
                q.put('매수전략중지')
        else:
            self.stgQ.put('매수전략중지')
        self._jango_cheongsan('수동')

    def _get_order_code_list(self):
        """주문 종목 코드 리스트를 반환합니다.
        Returns:
            주문 종목 코드 리스트
        """
        if self.market_gubun < 6:
            return tuple(self.dict_order['매수']) + tuple(self.dict_order['매도'])
        else:
            return tuple(self.dict_order['BUY_LONG']) + tuple(self.dict_order['SELL_SHORT']) + \
                tuple(self.dict_order['SELL_LONG']) + tuple(self.dict_order['BUY_SHORT'])

    def _get_order_buy_price(self, 종목코드, 주문구분, 주문가격):
        """매수 주문 가격을 반환합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
            주문가격: 주문 가격
        Returns:
            매수 주문 가격
        """
        return 0

    def _get_order_sell_price(self, 종목코드, 주문구분, 주문가격):
        """매도 주문 가격을 반환합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
            주문가격: 주문 가격
        Returns:
            매도 주문 가격
        """
        return 0

    def _get_modify_buy_price(self, 현재가, 정정호가, 종목코드):
        """매수 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매수 정정 가격
        """
        return 0

    def _get_modify_sell_price(self, 현재가, 정정호가, 종목코드):
        """매도 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매도 정정 가격
        """
        return 0

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            수익
        """
        return 0, 0, 0

    def _get_profit_long(self, 매입금액, 보유금액, 종목코드=None):
        """롱 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            롱 수익
        """
        return 0, 0, 0

    def _get_profit_short(self, 매입금액, 보유금액, 종목코드=None):
        """숏 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            숏 수익
        """
        return 0, 0, 0

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return 0

    def _set_position(self):
        """포지션을 설정합니다.
        """
        pass

    def _set_leverage(self, data):
        """레버리지를 설정합니다.
        Args:
            data: 데이터
        """
        pass

    def _send_order(self, data):
        """주문을 전송합니다.
        Args:
            data: 데이터
        """
        pass

    def _convert_order_data(self, data):
        """주문 데이터를 변환합니다.
        Args:
            data: 데이터
        Returns:
            변환된 주문 데이터
        """
        pass
