
import os
import sys
import numpy as np
from kiwoom_agent_tick import KiwoomAgentTick
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.setting_base import ui_num
from utility.static import now, roundfigure_upper5, GetSangHahanga


class KiwoomAgentMin(KiwoomAgentTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp):
        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.straderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        vipr = self.dict_vipr.get(code)
        if vipr is None:
            self.InsertViPrice(code, o)
        elif not vipr[0] and now() > vipr[1]:
            self.UpdateViPrice(code, c)

        code_data = self.dict_data.get(code)
        if code_data:
            bids, asks = code_data[7:9]
            if bids == 0 and asks == 0:
                mo = mh = ml = c
            else:
                mo, mh, ml = code_data[-3:]
                if mh < c: mh = c
                if ml > c: ml = c
        else:
            bids, asks = 0, 0
            mo = mh = ml = c

        rf = roundfigure_upper5(c, dt)
        bids_ = abs(int(v)) if '+' in v else 0
        asks_ = abs(int(v)) if '-' in v else 0
        bids += bids_
        asks += asks_

        _, vi_dt, uvi, _, vi_hgunit = self.dict_vipr[code]

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, dmp, jvp, vrp, jsvp, sgta, rf,
                                vi_dt, uvi, vi_hgunit, mo, mh, ml]

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.mgzservQ.put(('hoga', (self.dict_name[code], c, per, sgta, uvi, o, h, low)))
                if asks > 0: self.mgzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.mgzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                       code, name, receivetime, lastprice):

        send   = False
        dt_min = int(str(dt)[:12])

        code_dtdm = self.dict_dtdm.get(code)
        if code in self.dict_data:
            if code_dtdm:
                if dt_min > code_dtdm[0] and hoga_bamount[4] != 0:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]
                code_dtdm = self.dict_dtdm[code]

        if send or code == self.chart_code:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                valid_indices = [i for i, price in enumerate(hoga_seprice) if price >= csp]
                end_idx = valid_indices[-1] + 1 if valid_indices else None
                if end_idx is not None:
                    start_idx = max(end_idx - 5, 0)
                    add_cnt   = max(5 - end_idx, 0)
                    hoga_seprice = [0] * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = [0] * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = [0] * 5
                    hoga_samount = [0] * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                valid_indices = [i for i, price in enumerate(hoga_buprice) if price <= cbp]
                start_idx = valid_indices[0] if valid_indices else None
                if start_idx is not None:
                    end_idx   = min(start_idx + 5, 10)
                    add_cnt   = max(start_idx - 5, 0)
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + [0] * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + [0] * add_cnt
                else:
                    hoga_buprice = [0] * 5
                    hoga_bamount = [0] * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            code_data = self.dict_data[code]
            c, _, h, low, _, dm, _, bids, asks = code_data[:9]
            buy_money = c * bids
            sell_money = c * asks

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
            if tm == dm and 90500 < int(str(dt)[8:]): tm = 0
            hlp  = np.round((c / ((h + low) / 2) - 1) * 100, 2)
            lhp  = np.round((h / low - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            gsjm = 1 if code in self.list_gsjm else 0
            logt = now() if self.int_logt < dt_min else 0
            dt_  = code_dtdm[0]

            data = [dt_] + code_data + [tm, hlp, lhp, buy_money, sell_money] + money_arr + \
                hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + hoga_tamount + \
                [hjt, gsjm, code, name, logt, send]

            self.sstgQs[self.dict_sgbn[code]].put(data)
            if send:
                if code in self.tuple_order:
                    self.straderQ.put(('주문확인', (code, c)))

                code_dtdm[0] = dt_min
                code_dtdm[1] = dm
                code_data[7] = 0
                code_data[8] = 0

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'에젼트 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt_min
        elif self.int_mtdt < dt_min:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_min

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            data = self.dict_sghg.get(code)
            if data:
                shg, hhg = data
            else:
                shg, hhg = GetSangHahanga(code in self.tuple_kosd, lastprice, self.int_hgtime)
                self.dict_sghg[code] = (shg, hhg)
            self.mgzservQ.put(('hoga', [name] + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5] + [shg, hhg]))
