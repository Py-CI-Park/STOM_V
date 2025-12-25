import os
import sys
from future_agent_tick import FutureAgentTick
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now


class FutureAgentMin(FutureAgentTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, v, csp, cbp):
        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.straderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        if code not in self.dict_data:
            dm, bids, asks, tbids, tasks = 0, 0, 0, 0, 0
        else:
            dm, _, bids, asks, tbids, tasks = self.dict_data[code][5:11]

        if bids == 0 and asks == 0:
            mo = mh = ml = c
        else:
            mo, mh, ml = self.dict_data[code][-3:]
            if mh < c: mh = c
            if ml > c: ml = c

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

        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.

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

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount,
                       code, name, receivetime):

        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data:
            if code in self.dict_dtdm:
                if dt_min > self.dict_dtdm[code][0]:
                    send = True
            else:
                self.dict_dtdm[code] = [dt_min, 0]

        if send or code == self.chart_code:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = next((i for i, price in enumerate(hoga_seprice[::-1]) if price >= csp), None)
                if index is not None:
                    hoga_seprice = (0.,) * index + hoga_seprice[:-index]
                    hoga_samount = (0,) * index + hoga_samount[:-index]
                else:
                    hoga_seprice = (0.,) * 5
                    hoga_samount = (0,) * 5

            if hoga_buprice[0] > cbp:
                index = next((i for i, price in enumerate(hoga_buprice) if price <= cbp), None)
                if index is not None:
                    hoga_buprice = hoga_buprice[index:] + (0.,) * index
                    hoga_bamount = hoga_bamount[index:] + (0,) * index
                else:
                    hoga_buprice = (0.,) * 5
                    hoga_bamount = (0,) * 5

            c, _, h, low, _, dm = self.dict_data[code][:6]
            tm = dm - self.dict_dtdm[code][1]
            if tm == dm and 93500 < int(str(dt)[8:]): tm = 0
            hlp  = round((c / ((h + low) / 2) - 1) * 100, 2)
            hjt  = sum(hoga_samount + hoga_bamount)
            logt = now() if self.int_logt < dt_min else 0
            dt_  = self.dict_dtdm[code][0]
            data = (dt_,) + tuple(self.dict_data[code][:9]) + tuple(self.dict_data[code][11:]) + (tm, hlp) + \
                hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + \
                (hjt, 1, code, name, logt, send)

            self.sstgQ.put(data)
            if send:
                if code in self.tuple_order:
                    self.straderQ.put(('주문확인', (code, c)))

                self.dict_dtdm[code] = [dt_min, dm]
                self.dict_data[code][7:9] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'에젼트 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt_min
        elif self.int_mtdt < dt_min:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_min
            self.list_gsjm = []

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.mgzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5]))
