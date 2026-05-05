
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from utility.settings.setting_base import ui_num
from trade.base_trader import BaseTrader, MonitorTraderQ
from trade.restapi_upbit import UpbitRestAPI, UpbitWebSocketTrader
from utility.static_method.static import now, timedelta_sec, get_hogaunit_coin, get_profit_coin, str_ymdhms_utc


class UpbitTrader(BaseTrader):
    """업비트 트레이더 클래스입니다.
    BaseTrader를 상속받아 업비트 시장 주문을 실행합니다.
    """
    def __init__(self, qlist, dict_set, market_infos):
        """트레이더를 초기화합니다.
        Args:
            qlist (list): 큐 리스트
            dict_set (dict): 설정 딕셔너리
            market_infos (list): 마켓 정보 리스트
        """
        super().__init__(qlist, dict_set, market_infos)

        app = QApplication(sys.argv)

        self.업비트체결코드 = {
            'BID': '매수',
            'ASK': '매도',
            'trade': '체결',
            'cancel': '취소'
        }

        self.upbit = UpbitRestAPI(self.access_key, self.secret_key, self.windowQ)

        self._get_balances()

        if not self.dict_set['모의투자']:
            self.ws_thread = UpbitWebSocketTrader(self.windowQ)
            self.ws_thread.signal.connect(self._convert_order_data)
            self.ws_thread.start()

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

        app.exec_()

    def _get_balances(self):
        """잔고를 조회합니다."""
        if self.dict_set['모의투자']:
            yesugm = self._get_yesugm_for_paper_trading()
        else:
            yesugm = self.upbit.get_balances()
        self._set_yesugm_and_noti(yesugm)

    def _check_error(self, ret):
        """에러를 확인합니다.
        Args:
            ret: 응답
        """
        if ret.__class__ == dict and list(ret)[0] == 'error':
            self.windowQ.put((ui_num['시스템로그'], f"오류 알림 - {ret['error']['name']} : {ret['error']['message']}"))
            return False
        return True

    def _send_order(self, data):
        """주문을 전송합니다.
        Args:
            data: 데이터
        """
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self._send_order(data))
            return

        주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형 = data
        self._order_time_log(시그널시간)

        if 주문구분 in ('매수', '매도'):
            if 잔고청산:
                주문유형 = '시장가'
            else:
                주문유형 = self.dict_set[f'{주문구분}주문유형'] if 수동주문유형 is None else 수동주문유형
            주문금액 = int(주문가격 * 주문수량)

            """def order_coin(self, 종목코드='', 주문구분코드='', 주문유형='', 주문금액=0, 주문수량=0):"""
            ret = self.upbit.order_coin(종목코드=종목코드, 주문구분=주문구분, 주문유형=주문유형, 주문금액=주문금액, 주문수량=주문수량)
            if ret is not None:
                if self._check_error(ret):
                    index = self._get_index()
                    if 주문구분 == '매수':
                        self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                        add_time = self.dict_set['매수취소시간초']
                    else:
                        add_time = self.dict_set['매도취소시간초']

                    # noinspection PyUnresolvedReferences
                    self.dict_order[주문구분][종목코드] = [
                        timedelta_sec(add_time), 정정횟수, 주문가격, get_hogaunit_coin(주문가격)
                    ]

                    # noinspection PyUnresolvedReferences
                    self._update_chegeollist(
                        index, 종목코드, 종목명, f'{주문구분}접수', 주문수량, 0, 주문수량, 0, index[:14], 주문가격, ret['uuid']
                    )

                    self.windowQ.put((
                        ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목명} | {주문가격} | {주문수량}'
                    ))
            else:
                self._put_order_complete(f'{주문구분}취소', 종목코드)
                self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}실패] {종목명} | {주문가격} | {주문수량}'))

        elif 주문구분 in ('매수취소', '매도취소'):
            """def order_cancel(self, od_no):"""
            ret = self.upbit.order_cancel(원주문번호)
            if ret is None:
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}실패] {종목명} | {주문가격} | {주문수량}'
                ))

        self.order_time = timedelta_sec(0.2)
        self.receivQ.put(('주문목록', self._get_order_code_list()))

    def _convert_order_data(self, data):
        """주문 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        if data['type'] == 'myOrder':
            체결유형 = data['state']
            if 체결유형 in ('trade', 'cancel'):
                매매구분 = data['ask_bid']
                주문구분 = self.업비트체결코드[매매구분]
                체결구분 = self.업비트체결코드[체결유형]
                종목코드 = data['code']
                체결수량 = float(data['volume'])
                미체결수량 = float(data['remaining_volume'])
                체결된수량 = float(data['executed_volume'])
                주문수량 = round(미체결수량 + 체결된수량, 8)
                체결가격 = 주문가격 = float(data['price'])
                체결시간 = str_ymdhms_utc(data['timestamp'])
                주문번호 = data['uuid']
                self._update_chejan_data(주문구분, 체결구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 체결시간, 주문번호)

    def _get_order_buy_price(self, 종목코드, 주문구분, 주문가격):
        """매수 주문 가격을 반환합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
            주문가격: 주문 가격
        Returns:
            매수 주문 가격
        """
        매수지정가호가번호 = self.dict_set['매수지정가호가번호']
        return round(주문가격 + get_hogaunit_coin(주문가격) * 매수지정가호가번호, 8)

    def _get_order_sell_price(self, 종목코드, 주문구분, 주문가격):
        """매도 주문 가격을 반환합니다.
        Args:
            종목코드: 종목 코드
            주문구분: 주문 구분
            주문가격: 주문 가격
        Returns:
            매도 주문 가격
        """
        매도지정가호가번호 = self.dict_set['매도지정가호가번호']
        return round(주문가격 + get_hogaunit_coin(주문가격) * 매도지정가호가번호, 8)

    def _get_modify_buy_price(self, 현재가, 정정호가, 종목코드):
        """매수 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매수 정정 가격
        """
        return round(현재가 - 정정호가, 8)

    def _get_modify_sell_price(self, 현재가, 정정호가, 종목코드):
        """매도 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매도 정정 가격
        """
        return round(현재가 + 정정호가, 8)

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            수익
        """
        return get_profit_coin(매입금액, 보유금액)

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return get_hogaunit_coin(주문가격또는종목코드)
