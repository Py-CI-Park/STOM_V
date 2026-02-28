
import os
import sys
import numpy as np
from kiwoom_agent_tick import KiwoomAgentTick
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, roundfigure_upper5, GetSangHahanga


class KiwoomAgentMin(KiwoomAgentTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp):
        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.straderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        if code not in self.dict_vipr:
            self.InsertViPrice(code, o)
        elif not self.dict_vipr[code][0] and now() > self.dict_vipr[code][1]:
            self.UpdateViPrice(code, c)

        if code in self.dict_data:
            bids, asks = self.dict_data[code][13:15]
        else:
            bids, asks = 0, 0

        if bids == 0 and asks == 0:
            mo = mh = ml = c
        else:
            mo, mh, ml = self.dict_data[code][-3:]
            if mh < c: mh = c
            if ml > c: ml = c

        rf = roundfigure_upper5(c, dt)
        bids_, asks_ = 0, 0
        if '+' in v: bids_ = abs(int(v))
        if '-' in v: asks_ = abs(int(v))
        bids += bids_
        asks += asks_

        _, vi_dt, uvi, _, vi_hgunit = self.dict_vipr[code]

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, dmp, jvp, vrp, jsvp, sgta, rf, bids, asks,
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

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount,
                       code, name, receivetime, lastprice):

        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data:
            if code in self.dict_dtdm:
                if dt_min > self.dict_dtdm[code][0] and hoga_bamount[4] != 0:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]

        if send or code == self.chart_code:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = next((i for i, price in enumerate(hoga_seprice[::-1]) if price >= csp), None)
                if index is not None:
                    start_idx = (5 - index) if index < 5 else 0
                    end_idx   = 10 - index
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_seprice = (0,) * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = (0,) * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = (0,) * 5
                    hoga_samount = (0,) * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = next((i for i, price in enumerate(hoga_buprice) if price <= cbp), None)
                if index is not None:
                    start_idx = index
                    end_idx   = index + 5
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + (0,) * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + (0,) * add_cnt
                else:
                    hoga_buprice = (0,) * 5
                    hoga_bamount = (0,) * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            c, _, h, low, _, dm = self.dict_data[code][:6]
            tm = dm - self.dict_dtdm[code][1]
            if tm == dm and 90500 < int(str(dt)[8:]): tm = 0
            hlp  = np.round((c / ((h + low) / 2) - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            gsjm = 1 if code in self.list_gsjm else 0
            logt = now() if self.int_logt < dt_min else 0
            dt_  = self.dict_dtdm[code][0]
            data = (dt_,) + tuple(self.dict_data[code]) + (tm, hlp) + \
                hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + \
                (hjt, gsjm, code, name, logt, send)

            self.sstgQs[self.dict_sgbn[code]].put(data)
            if send:
                if code in self.tuple_order:
                    self.straderQ.put(('주문확인', (code, c)))

                self.dict_dtdm[code] = [dt_min, dm]
                self.dict_data[code][13:15] = [0, 0]

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
            if code in self.dict_sghg:
                shg, hhg = self.dict_sghg[code]
            else:
                shg, hhg = GetSangHahanga(code in self.tuple_kosd, lastprice, self.int_hgtime)
                self.dict_sghg[code] = (shg, hhg)
            self.mgzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5] + (shg, hhg)))
