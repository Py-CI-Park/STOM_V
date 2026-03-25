
import os
import sys
import numpy as np
from future_agent_tick import FutureAgentTick
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.static import now
from utility.setting_base import ui_num


class FutureAgentMin(FutureAgentTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, v, csp, cbp):
        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.straderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        code_data = self.dict_data.get(code)
        if code_data:
            dm, _, bids, asks, tbids, tasks = code_data[5:11]
            if bids == 0 and asks == 0:
                mo = mh = ml = c
            else:
                mo, mh, ml = code_data[-3:]
                if mh < c: mh = c
                if ml > c: ml = c
        else:
            dm, bids, asks, tbids, tasks = 0, 0, 0, 0, 0
            mo = mh = ml = c

        bids_, asks_ = 0, 0
        wtm = self.dict_info[code]['위탁증거금']
        if '+' in v:
            bids_ = abs(int(v))
            dm   += int(bids_ * wtm)
        if '-' in v:
            asks_ = abs(int(v))
            dm   += int(asks_ * wtm)
        bids += bids_
        asks += asks_
        tbids += bids_
        tasks += asks_

        # noinspection PyTypeChecker
        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        if code not in self.list_gsjm:
            self.list_gsjm.append(code)

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.mgzservQ.put(('hoga', (self.dict_info[code]['종목명'], c, per, 0, -1, o, h, low)))
                if asks > 0: self.mgzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.mgzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                       code, name, receivetime):

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
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                valid_indices = [i for i, price in enumerate(hoga_seprice) if price >= csp]
                end_index = valid_indices[-1] + 1 if valid_indices else None
                if end_index is not None:
                    add_cnt = 5 - end_index
                    hoga_seprice = [0.] * add_cnt + hoga_seprice[:end_index]
                    hoga_samount = [0] * add_cnt + hoga_samount[:end_index]
                else:
                    hoga_seprice = [0.] * 5
                    hoga_samount = [0] * 5

            if hoga_buprice[0] > cbp:
                valid_indices = [i for i, price in enumerate(hoga_buprice) if price <= cbp]
                start_index = valid_indices[0] if valid_indices else None
                if start_index is not None:
                    hoga_buprice = hoga_buprice[start_index:] + [0.] * start_index
                    hoga_bamount = hoga_bamount[start_index:] + [0] * start_index
                else:
                    hoga_buprice = [0.] * 5
                    hoga_bamount = [0] * 5

            code_data = self.dict_data[code]
            c, _, h, low, _, dm, _, bids, asks = code_data[:9]
            wtm = self.dict_info[code]['위탁증거금']
            buy_money = int(wtm * bids)
            sell_money = int(wtm * asks)

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
                money_arr[3] += sell_money

                idx = price_idx.get(c)
                if idx is not None:
                    buy_arr[idx]  += buy_money
                    sell_arr[idx] += sell_money
                else:
                    idx = price_idx['count']
                    if idx >= len(buy_arr):
                        self.dict_bmbyp[code] = np.resize(buy_arr, len(buy_arr) * 2)
                        self.dict_smbyp[code] = np.resize(sell_arr, len(sell_arr) * 2)
                        buy_arr  = self.dict_bmbyp[code]
                        sell_arr = self.dict_smbyp[code]
 
                    price_idx[c] = idx
                    buy_arr[idx] = buy_money
                    sell_arr[idx] = sell_money
                    price_idx['count'] += 1
     
                if buy_arr[idx] >= money_arr[1]:
                    money_arr[1] = buy_arr[idx]
                    money_arr[2] = c

                if sell_arr[idx] >= money_arr[4]:
                    money_arr[4] = sell_arr[idx]
                    money_arr[5] = c

            tm = dm - code_dtdm[1]
            if tm == dm and 93500 < int(str(dt)[8:]): tm = 0
            hlp  = round((c / ((h + low) / 2) - 1) * 100, 2)
            lhp  = round((h / low - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            logt = now() if self.int_logt < dt_min else 0
            dt_  = code_dtdm[0]

            data = [dt_] + code_data[:9] + code_data[11:] + [tm, hlp, lhp, buy_money, sell_money] + money_arr + \
                hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + hoga_tamount + \
                [hjt, 1, code, name, logt, send]

            self.sstgQ.put(data)
            if send:
                if code in self.tuple_order:
                    self.straderQ.put(('주문확인', (code, c)))

                code_dtdm[0] = dt_min
                code_dtdm[1] = dm
                code_data[7] = 0
                code_data[8] = 0

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.mgzservQ.put(('window', (ui_num['타임로그'], f'에젼트 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt_min
        elif self.int_mtdt < dt_min:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_min
            self.list_gsjm = []

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.mgzservQ.put(('hoga', [name] + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5]))
