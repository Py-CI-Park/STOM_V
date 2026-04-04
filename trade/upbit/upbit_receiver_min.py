
from traceback import format_exc
from utility.setting_base import ui_num
from utility.static import now, str_ymdhms_utc
from trade.upbit.upbit_receiver_tick import UpbitReceiverTick


class UpbitReceiverMin(UpbitReceiverTick):
    def UpdateTickData(self, data):
        try:
            dt = int(str_ymdhms_utc(data['timestamp']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code  = data['code']
            c     = data['trade_price']
            o     = data['opening_price']
            h     = data['high_price']
            low   = data['low_price']
            per   = round(data['signed_change_rate'] * 100, 2)
            tbids = data['acc_bid_volume']
            tasks = data['acc_ask_volume']
            dm    = data['acc_trade_price']
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - UpdateTickData'))
            return

        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.ctraderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        code_data = self.dict_data.get(code)
        if code_data:
            bids, asks, pretbids, pretasks = code_data[7:11]
            if bids == 0 and asks == 0:
                mo = mh = ml = c
            else:
                mo, mh, ml = code_data[-3:]
                if mh < c: mh = c
                if ml > c: ml = c
        else:
            bids, asks, pretbids, pretasks = 0, 0, tbids, tasks
            mo = mh = ml = c

        bids_ = round(tbids - pretbids, 8)
        asks_ = round(tasks - pretasks, 8)
        bids += bids_
        asks += asks_
        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500

        self.dict_daym[code] = dm
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        self.UpdateMoneyFactor(code, c, int(c * bids_), int(c * asks_))
        self.UpdateHogaWindowTick(code, dt, bids_, asks_, c, per, o, h, low, ch)

    def UpdateHogaData(self, data):
        try:
            dt = int(str_ymdhms_utc(data['timestamp']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code = data['code']
            hoga_tamount = [
                data['total_ask_size'], data['total_bid_size']
            ]
            data = data['orderbook_units']
            hoga_seprice = [
                data[9]['ask_price'], data[8]['ask_price'], data[7]['ask_price'], data[6]['ask_price'], data[5]['ask_price'],
                data[4]['ask_price'], data[3]['ask_price'], data[2]['ask_price'], data[1]['ask_price'], data[0]['ask_price']
            ]
            hoga_buprice = [
                data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'], data[4]['bid_price'],
                data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'], data[8]['bid_price'], data[9]['bid_price']
            ]
            hoga_samount = [
                data[9]['ask_size'], data[8]['ask_size'], data[7]['ask_size'], data[6]['ask_size'], data[5]['ask_size'],
                data[4]['ask_size'], data[3]['ask_size'], data[2]['ask_size'], data[1]['ask_size'], data[0]['ask_size']
            ]
            hoga_bamount = [
                data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'], data[4]['bid_size'],
                data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'], data[8]['bid_size'], data[9]['bid_size']
            ]
            receivetime = now()
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - UpdateHogaData'))
            return

        send   = False
        dt_min = int(str(dt)[:12])

        code_data = self.dict_data.get(code)
        money_arr = self.dict_money.get(code)
        if code_data and money_arr:
            code_dtdm = self.dict_dtdm.get(code)
            if code_dtdm:
                if dt_min > code_dtdm[0]:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]
                code_dtdm = self.dict_dtdm[code]

            if send or code == self.chart_code or code in self.list_gsjm:
                csp = cbp = code_data[0]
                hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount = \
                    self.CorrectionHogaData(csp, cbp, hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount)

                data, c, dm, logt = self.GetSendData(False, code, code_data, code_dtdm, money_arr,
                                                     hoga_samount, hoga_bamount, hoga_seprice, hoga_buprice,
                                                     hoga_tamount, dt, dt_min)

                data.append(send)
                self.cstgQ.put(data)
                if send:
                    if code in self.tuple_order:
                        self.ctraderQ.put(('주문확인', (code, c)))

                    code_dtdm[0] = dt_min
                    code_dtdm[1] = dm
                    code_data[7] = 0
                    code_data[8] = 0
                    money_arr[0] = 0
                    money_arr[1] = 0

                self.SendLog(logt, dt_min, receivetime)

        self.UpdateMoneyTop(dt_min)
        self.UpdateHogaWindowRem(code, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount)
