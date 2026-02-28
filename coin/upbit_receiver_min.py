
import numpy as np
from utility.setting import ui_num
from utility.static import now, str_ymdhms_utc
from coin.upbit_receiver_tick import UpbitReceiverTick


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
            per   = np.round(data['signed_change_rate'] * 100, 2)
            tbids = data['acc_bid_volume']
            tasks = data['acc_ask_volume']
            dm    = data['acc_trade_price']
        except:
            return

        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.ctraderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        if code in self.dict_data:
            bids, asks, pretbids, pretasks = self.dict_data[code][7:11]
        else:
            bids, asks, pretbids, pretasks = 0, 0, tbids, tasks

        if bids == 0 and asks == 0:
            mo = mh = ml = c
        else:
            mo, mh, ml = self.dict_data[code][-3:]
            if mh < c: mh = c
            if ml > c: ml = c

        bids_ = np.round(tbids - pretbids, 8)
        asks_ = np.round(tasks - pretasks, 8)
        bids += bids_
        asks += asks_
        try:
            ch = np.round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.

        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]
        self.dict_daym[code] = dm

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.hogaQ.put((code, c, per, 0, -1, o, h, low))
                if asks > 0: self.hogaQ.put((-asks, ch))
                if bids > 0: self.hogaQ.put((bids, ch))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, data):
        try:
            dt = int(str_ymdhms_utc(data['timestamp']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code = data['code']
            hoga_tamount = (
                data['total_ask_size'], data['total_bid_size']
            )
            data = data['orderbook_units']
            hoga_seprice = (
                data[9]['ask_price'], data[8]['ask_price'], data[7]['ask_price'], data[6]['ask_price'],
                data[5]['ask_price'],
                data[4]['ask_price'], data[3]['ask_price'], data[2]['ask_price'], data[1]['ask_price'],
                data[0]['ask_price']
            )
            hoga_buprice = (
                data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'],
                data[4]['bid_price'],
                data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'], data[8]['bid_price'],
                data[9]['bid_price']
            )
            hoga_samount = (
                data[9]['ask_size'], data[8]['ask_size'], data[7]['ask_size'], data[6]['ask_size'], data[5]['ask_size'],
                data[4]['ask_size'], data[3]['ask_size'], data[2]['ask_size'], data[1]['ask_size'], data[0]['ask_size']
            )
            hoga_bamount = (
                data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'], data[4]['bid_size'],
                data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'], data[8]['bid_size'], data[9]['bid_size']
            )
            receivetime = now()
        except:
            return

        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data:
            if code in self.dict_dtdm:
                if dt_min > self.dict_dtdm[code][0]:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]

        if send or code == self.chart_code:
            c, _, h, low, _, dm = self.dict_data[code][:6]
            csp = cbp = c

            if hoga_seprice[-1] < csp:
                index = next((i for i, price in enumerate(hoga_seprice[::-1]) if price >= csp), None)
                if index is not None:
                    start_idx = (5 - index) if index < 5 else 0
                    end_idx   = 10 - index
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_seprice = (0.,) * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = (0.,) * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = (0.,) * 5
                    hoga_samount = (0.,) * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = next((i for i, price in enumerate(hoga_buprice) if price <= cbp), None)
                if index is not None:
                    start_idx = index
                    end_idx   = index + 5
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + (0.,) * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + (0.,) * add_cnt
                else:
                    hoga_buprice = (0.,) * 5
                    hoga_bamount = (0.,) * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            tm = dm - self.dict_dtdm[code][1]
            if tm == dm and 500 < int(str(dt)[8:]): tm = 0
            hlp  = np.round((c / ((h + low) / 2) - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            gsjm = 1 if code in self.list_gsjm else 0
            logt = now() if self.int_logt < dt_min else 0
            dt_  = self.dict_dtdm[code][0]
            data = (dt_,) + tuple(self.dict_data[code][:9]) + tuple(self.dict_data[code][11:]) + (tm, hlp) + \
                hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + \
                (hjt, gsjm, code, logt, send)

            self.cstgQ.put(data)
            if send:
                if code in self.tuple_order:
                    self.ctraderQ.put(('주문확인', (code, c)))

                self.dict_dtdm[code] = [dt_min, dm]
                self.dict_data[code][7:9] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.windowQ.put((ui_num['C단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt_min
        elif self.int_mtdt < dt_min:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_min

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.hogaQ.put((code,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5])
