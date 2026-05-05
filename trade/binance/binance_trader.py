
import sys
import binance
from PyQt5.QtCore import QTimer
from traceback import format_exc
from PyQt5.QtWidgets import QApplication
from trade.base_trader import BaseTrader
from utility.settings.setting_base import ui_num
from utility.static_method.static import now, timedelta_sec, get_profit_coin_future_short, get_profit_coin_future_long, \
    get_str_ymdhms


class BinanceTrader(BaseTrader):
    """바이낸스 트레이더 클래스입니다.
    BaseTrader를 상속받아 바이낸스 시장 주문을 실행합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        app = QApplication(sys.argv)

        super().__init__(qlist, dict_set, market_infos)

        self.binance = binance.Client(self.access_key, self.secret_key)

        self._get_balances()

        if not self.dict_set['모의투자']:
            from trade.restapi_binance import BinanceWebSocketTrader
            self.ws_thread = BinanceWebSocketTrader(self.access_key, self.secret_key, self.windowQ)
            self.ws_thread.signal.connect(self._convert_order_data)
            self.ws_thread.start()

        app.exec_()

    def _get_balances(self):
        """잔고를 조회합니다."""
        if self.dict_set['모의투자']:
            yesugm = self._get_yesugm_for_paper_trading()
        else:
            datas = self.binance.futures_account_balance()
            yesugm = [float(data['balance']) for data in datas if data['asset'] == 'USDT'][0]
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
        매도수구분, 포지션 = 주문구분.split('_')[:2]
        self._order_time_log(시그널시간)
        if 'CANCEL' not in 주문구분:
            ret = None
            if 수동주문유형 == '시장가' or (수동주문유형 is None and self.dict_set['매수주문유형'] == '시장가') or 잔고청산:
                ret = self.binance.futures_create_order(
                    symbol=종목코드, side=매도수구분, type='MARKET', quantity=주문수량
                )
            elif 수동주문유형 == '지정가' or (수동주문유형 is None and self.dict_set['매수주문유형'] == '지정가'):
                ret = self.binance.futures_create_order(
                    symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='GTC', quantity=주문수량
                )
            elif 수동주문유형 == '지정가IOC' or (수동주문유형 is None and self.dict_set['매수주문유형'] == '지정가IOC'):
                ret = self.binance.futures_create_order(
                    symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='IOC', quantity=주문수량
                )
            elif 수동주문유형 == '지정가FOK' or (수동주문유형 is None and self.dict_set['매수주문유형'] == '지정가FOK'):
                ret = self.binance.futures_create_order(
                    symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='FOK', quantity=주문수량
                )

            if ret is not None:
                if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                    self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                    add_time = self.dict_set['매수취소시간초']
                else:
                    add_time = self.dict_set['매도취소시간초']

                self.dict_order[주문구분][종목코드] = [
                    timedelta_sec(add_time), 정정횟수, 주문가격, self.dict_info[종목코드]['호가단위'], self.dict_lvrg[종목코드]
                ]

                self.dict_pos[종목코드] = 포지션

                # noinspection PyUnresolvedReferences
                orderId = int(ret['orderId'])
                index = self._get_index()
                self._update_chegeollist(index, 종목코드, 종목명, f'{주문구분}_REG', 주문수량, 0, 주문수량, 0, index[:14], 주문가격, orderId)
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}_REG] {종목코드} | {주문가격} | {주문수량}'
                ))
            else:
                self._put_order_complete(f'{주문구분}_CANCEL', 종목코드)
                self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}_FAIL] {종목명} | {주문가격} | {주문수량}'))
        else:
            ret = self.binance.futures_cancel_order(symbol=종목코드, orderId=원주문번호)
            if ret is not None:
                self.dict_pos[종목코드] = 포지션
            else:
                self.windowQ.put((
                    ui_num['기본로그'],
                    f'{format_exc()}\n주문 관리 시스템 알림 - [{주문구분}_FAIL] {종목명} | {주문가격} | {주문수량}'
                ))

        self.order_time = timedelta_sec(0.2)
        self.receivQ.put(('주문목록', self._get_order_code_list()))

    def _set_position(self):
        """포지션을 설정합니다."""
        if self.dict_set['바이낸스선물고정레버리지']:
            self.dict_lvrg = {x: self.dict_set['바이낸스선물고정레버리지값'] for x in self.dict_info}
        else:
            self.dict_lvrg = {x: 1 for x in self.dict_info}

        if not self.dict_set['모의투자']:
            for code in self.dict_info:
                try:
                    if self.dict_set['바이낸스선물고정레버리지']:
                        self.binance.futures_change_leverage(symbol=code, leverage=self.dict_set['바이낸스선물고정레버리지값'])
                    else:
                        self.binance.futures_change_leverage(symbol=code, leverage=1)
                    self.binance.futures_change_margin_type(symbol=code, marginType=self.dict_set['바이낸스선물마진타입'])
                except Exception:
                    pass
            try:
                self.binance.futures_change_position_mode(dualSidePosition=self.dict_set['바이낸스선물포지션'])
            except Exception:
                pass

        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 마진타입 및 레버리지 설정 완료'))

    def _set_leverage(self, dict_dlhp):
        """레버리지를 설정합니다.
        Args:
            dict_dlhp: 레버리지 설정 딕셔너리
        """
        for code in self.dict_info:
            lhp = dict_dlhp.get(code)
            if lhp:
                try:
                    leverage = self._get_leverage(lhp[1])
                    self.dict_lvrg[code] = leverage
                    if not self.dict_set['모의투자']:
                        self.binance.futures_change_leverage(symbol=code, leverage=leverage)
                except Exception:
                    pass

    def _get_leverage(self, lhp):
        """레버리지를 반환합니다.
        Args:
            lhp: 레버리지 설정
        Returns:
            레버리지
        """
        leverage = 1
        for min_area, max_area, lvrg in self.dict_set['바이낸스선물변동레버리지값']:
            if min_area <= lhp < max_area:
                leverage = lvrg
                break
        return leverage

    def _convert_order_data(self, data):
        """주문 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        try:
            if data['e'] == 'ACCOUNT_UPDATE':
                bal_list = data['a']['B']
                for bal_dict in bal_list:
                    if bal_dict['a'] == 'USDT':
                        self.dict_intg['추정예탁자산'] = float(bal_dict['wb'])
                        self.dict_intg['예수금'] = float(bal_dict['cw'])
                        break

            elif data['e'] == 'ORDER_TRADE_UPDATE':
                data = data['o']
                code = data['s']
                p = f"{data['S']}_{self.dict_pos[code]}"
                if data['X'] == 'CANCELED':
                    p = f'{p}_CANCEL'
                oc = float(data['q'])
                cc = float(data['l'])
                mc = round(oc - float(data['z']), self.dict_info[code]['소숫점자리수'])
                cp = float(data['L'])
                op = float(data['p'])
                on = int(data['i'])
                if cc > 0 or 'CANCEL' in p:
                    ct = get_str_ymdhms(self.market_gubun)
                    self._update_chejan_data_coin_future(p, code, oc, cc, mc, cp, op, ct, on)

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
        소숫점자리수 = self.dict_info[종목코드]['가격소숫점자리수']
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
        소숫점자리수 = self.dict_info[종목코드]['가격소숫점자리수']
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
        return round(현재가 - 정정호가, self.dict_info[종목코드]['가격소숫점자리수'])

    def _get_modify_sell_price(self, 현재가, 정정호가, 종목코드):
        """매도 정정 가격을 반환합니다.
        Args:
            현재가: 현재가
            정정호가: 정정 호가
            종목코드: 종목 코드
        Returns:
            매도 정정 가격
        """
        return round(현재가 + 정정호가, self.dict_info[종목코드]['가격소숫점자리수'])

    def _get_profit_long(self, 매입금액, 보유금액, 종목코드=None):
        """롱 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            롱 수익
        """
        return get_profit_coin_future_long(
            매입금액, 보유금액, '시장가' in self.dict_set['매수주문유형'], '시장가' in self.dict_set['매도주문유형']
        )

    def _get_profit_short(self, 매입금액, 보유금액, 종목코드=None):
        """숏 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            숏 수익
        """
        return get_profit_coin_future_short(
            매입금액, 보유금액, '시장가' in self.dict_set['매수주문유형'], '시장가' in self.dict_set['매도주문유형']
        )

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return self.dict_info[주문가격또는종목코드]['호가단위']

    def _get_order_code_list(self):
        """주문 종목 코드 리스트를 반환합니다.
        Returns:
            주문 종목 코드 리스트
        """
        return tuple(self.dict_order['BUY_LONG']) + tuple(self.dict_order['SELL_SHORT']) + \
            tuple(self.dict_order['SELL_LONG']) + tuple(self.dict_order['BUY_SHORT'])
