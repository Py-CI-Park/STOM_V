
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

        code_data = self.dict_data.get(code)
        if code_data:
            bids, asks, pretbids, pretasks = code_data[7:11]
            mo, mh, ml = code_data[-3:]
            if mh < c: mh = c
            if ml > c: ml = c
        else:
            bids, asks, pretbids, pretasks = 0, 0, tbids, tasks
            mo = mh = ml = c

        bids_ = np.round(tbids - pretbids, 8)
        asks_ = np.round(tasks - pretasks, 8)
        bids += bids_
        asks += asks_
        # noinspection PyTypeChecker
        ch = min(500, np.round(tbids / tasks * 100, 2)) if tasks > 0 else 500

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
            hoga_tamount = [
                data['total_ask_size'], data['total_bid_size']
            ]
            data = data['orderbook_units']
            hoga_seprice = [
                data[9]['ask_price'], data[8]['ask_price'], data[7]['ask_price'], data[6]['ask_price'],
                data[5]['ask_price'],
                data[4]['ask_price'], data[3]['ask_price'], data[2]['ask_price'], data[1]['ask_price'],
                data[0]['ask_price']
            ]
            hoga_buprice = [
                data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'],
                data[4]['bid_price'],
                data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'], data[8]['bid_price'],
                data[9]['bid_price']
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
            return

        send   = False
        dt_min = int(str(dt)[:12])

        code_dtdm = self.dict_dtdm.get(code)
        if code in self.dict_data:
            if code_dtdm:
                if dt_min > code_dtdm[0]:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]
                code_dtdm = self.dict_dtdm[code]

        if send or code == self.chart_code:
            code_data = self.dict_data[code]
            c, _, h, low, _, dm, _, bids, asks = code_data[:9]
            csp = cbp = c

            if hoga_seprice[-1] < csp:
                valid_indices = np.where(np.array(hoga_seprice) >= csp)[0]
                index = valid_indices[-1] + 1 if len(valid_indices) > 0 else None
                if index is not None:
                    start_idx = max(index - 5, 0)
                    end_idx   = index
                    add_cnt   = max(5 - index, 0)
                    hoga_seprice = [0.] * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = [0.] * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = [0.] * 5
                    hoga_samount = [0.] * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                valid_indices = np.where(np.array(hoga_buprice) >= cbp)[0]
                index = valid_indices[0] if len(valid_indices) > 0 else None
                if index is not None:
                    start_idx = index
                    end_idx   = min(index + 5, 10)
                    add_cnt   = max(index - 5, 0)
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + [0.] * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + [0.] * add_cnt
                else:
                    hoga_buprice = [0.] * 5
                    hoga_bamount = [0.] * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            buy_money = int(c * bids)
            sell_money = int(c * asks)

            if code not in self.dict_money:
                self.dict_money[code] = [buy_money, buy_money, c, sell_money, sell_money, c]
                self.dict_index[code] = {c: 0}
                self.dict_bmbyp[code] = np.zeros(1000, dtype=np.int64)
                self.dict_smbyp[code] = np.zeros(1000, dtype=np.int64)
                self.dict_bmbyp[code][0] = buy_money
                self.dict_smbyp[code][0] = sell_money
                self.dict_index[code]['count'] = 1
                money_arr = self.dict_money[code]
            else:
                money_arr = self.dict_money[code]
                price_idx = self.dict_index[code]
                buy_arr   = self.dict_bmbyp[code]
                sell_arr  = self.dict_smbyp[code]

                money_arr[0] += buy_money
                if c in price_idx:
                    idx = price_idx[c]
                    buy_arr[idx] += buy_money
                else:
                    idx = price_idx['count']
                    if idx >= len(buy_arr):
                        self.dict_bmbyp[code] = np.resize(buy_arr, len(buy_arr) * 2)
                        buy_arr  = self.dict_bmbyp[code]
                    price_idx[c] = idx
                    buy_arr[idx] = buy_money
                    price_idx['count'] += 1
                if buy_arr[idx] >= money_arr[1]:
                    money_arr[1] = buy_arr[idx]
                    money_arr[2] = c

                money_arr[3] += sell_money
                if c in price_idx:
                    idx = price_idx[c]
                    sell_arr[idx] += sell_money
                else:
                    idx = price_idx['count']
                    if idx >= len(sell_arr):
                        self.dict_smbyp[code] = np.resize(sell_arr, len(sell_arr) * 2)
                        sell_arr = self.dict_smbyp[code]
                    price_idx[c] = idx
                    sell_arr[idx] = sell_money
                    price_idx['count'] += 1
                if sell_arr[idx] >= money_arr[4]:
                    money_arr[4] = sell_arr[idx]
                    money_arr[5] = c

            tm = dm - code_dtdm[1]
            if tm == dm and 500 < int(str(dt)[8:]): tm = 0
            hlp  = np.round((c / ((h + low) / 2) - 1) * 100, 2)
            lhp  = np.round((h / low - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            gsjm = 1 if code in self.list_gsjm else 0
            logt = now() if self.int_logt < dt_min else 0
            dt_  = code_dtdm[0]

            data = [dt_] + code_data[:9] + code_data[11:] + [tm, hlp, lhp, buy_money, sell_money] + money_arr + \
                hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + hoga_tamount + \
                [hjt, gsjm, code, logt, send]

            self.cstgQ.put(data)
            if send:
                if code in self.tuple_order:
                    self.ctraderQ.put(('주문확인', (code, c)))

                code_dtdm[0] = dt_min
                code_dtdm[1] = dm
                code_data[7] = 0
                code_data[8] = 0

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
            self.hogaQ.put([code] + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5])
