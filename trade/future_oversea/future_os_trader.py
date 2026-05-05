
import sys
from PyQt5.QtCore import QTimer
from traceback import format_exc
from trade.restapi_ls import LsRestAPI
from PyQt5.QtWidgets import QApplication
from trade.base_trader import BaseTrader
from trade.restapi_lsdata import LsRestData
from utility.settings.setting_base import ui_num
from utility.static_method.static import now, timedelta_sec, get_profit_future_os_long, get_profit_future_os_short


class FutureOsTrader(BaseTrader):
    """해외 선물 트레이더 클래스입니다.
    BaseTrader를 상속받아 해외 선물 시장 주문을 실행합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        app = QApplication(sys.argv)

        super().__init__(qlist, dict_set, market_infos)

        self.ls = LsRestAPI(self.windowQ, self.access_key, self.secret_key)
        self.token = self.ls.create_token()

        self._get_balances()

        if not self.dict_set['모의투자']:
            from trade.restapi_ls import LsWebSocketTrader
            self.ws_thread = LsWebSocketTrader(self.market_info['마켓이름'], self.token, self.windowQ)
            self.ws_thread.signal.connect(self._convert_order_data)
            self.ws_thread.start()

        app.exec_()

    def _get_balances(self):
        """잔고를 조회합니다."""
        if self.dict_set['모의투자']:
            yesugm = self._get_yesugm_for_paper_trading()
        else:
            yesugm = self.ls.get_balance_future_oversea()
        self._set_yesugm_and_noti(yesugm)

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

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT', 'SELL_LONG', 'BUY_SHORT'):
            if 잔고청산:
                주문유형 = '시장가'
            else:
                if 수동주문유형 is None:
                    주문유형 = self.dict_set['매수주문유형' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도주문유형']
                else:
                    주문유형 = 수동주문유형

            """def order_future_oversea(self, 종목코드, 주문구분, 주문가격, 주문수량, 주문유형):"""
            주문번호, 응답메시지 = self.ls.order_future_oversea(종목코드, 주문구분, 주문가격, 주문수량, 주문유형)
            if self._check_order_error(주문번호, 응답메시지, 주문구분, 종목명, 주문가격, 주문수량):
                index = self._get_index()
                if 주문구분 == '매수':
                    self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                    add_time = self.dict_set['매수취소시간초']
                else:
                    add_time = self.dict_set['매도취소시간초']

                self.dict_order[주문구분][종목코드] = [
                    timedelta_sec(add_time), 정정횟수, 주문가격, 0.01
                ]

                self._update_chegeollist(
                    index, 종목코드, 종목명, f'{주문구분}접수', 주문수량, 0, 주문수량, 0, index[:14], 주문가격, 주문번호
                )

                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목명} | {주문가격} | {주문수량}'
                ))

        elif 'MODIFY' in 주문구분:
            """def order_modify_future_oversea(self, 종목코드, 원주문번호, 주문구분, 주문가격, 주문수량, 주문유형):"""
            주문유형 = self.dict_set['매수주문유형' if 주문구분 in ('BUY_LONG_MODIFY', 'SELL_SHORT_MODIFY') else '매도주문유형']
            주문번호, 응답메시지 = self.ls.order_modify_future_oversea(종목코드, 원주문번호, 주문구분, 주문가격, 주문수량, 주문유형)
            self._check_order_error(주문번호, 응답메시지, 주문구분, 종목명, 주문가격, 주문수량)

        elif 'CANCEL' in 주문구분:
            """def order_cancel_future_oversea(self, 종목코드, 원주문번호):"""
            주문번호, 응답메시지 = self.ls.order_cancel_future_oversea(종목코드, 원주문번호)
            self._check_order_error(주문번호, 응답메시지, 주문구분, 종목명, 주문가격, 주문수량)

        self.order_time = timedelta_sec(0.2)
        self.receivQ.put(('주문목록', self._get_order_code_list()))

    def _convert_order_data(self, data):
        """주문 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        body = data['body']
        if body is None:
            return

        try:
            체결유형 = body['ordr_ccd']
            if 체결유형 in ('1', '2', '3'):
                체결구분 = LsRestData.선물주문체결코드[체결유형]
                종목코드 = body['is_cd']
                체결수량 = int(body['ccls_q'])
                체결가격 = float(body['ccls_prc'])
                체결시간 = f"{self.str_today}{int(int(body['ccls_tm']) / 1000)}"
                주문번호 = body['ordr_no']
                self._update_chejan_data_future(체결구분, 종목코드, 체결수량, 체결가격, 체결시간, 주문번호)
        except Exception:
            self.windowQ.put((ui_num['시스템로그'], format_exc()))

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
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매수지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'BUY_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

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
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매도지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'SELL_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

    def _get_modify_buy_price(self, 현재가, 정정호가, 종목코드):
        """매수 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매수 정정 가격
        """
        return round(현재가 - 정정호가, self.dict_info[종목코드]['소숫점자리수'])

    def _get_modify_sell_price(self, 현재가, 정정호가, 종목코드):
        """매도 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매도 정정 가격
        """
        return round(현재가 + 정정호가, self.dict_info[종목코드]['소숫점자리수'])

    def _get_profit_long(self, 매입금액, 보유금액, 종목코드=None):
        """롱 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            롱 수익
        """
        mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
        return get_profit_future_os_long(mini, 매입금액, 보유금액)

    def _get_profit_short(self, 매입금액, 보유금액, 종목코드=None):
        """숏 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            숏 수익
        """
        mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
        return get_profit_future_os_short(mini, 매입금액, 보유금액)

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return self.dict_info[주문가격또는종목코드]['호가단위']
