import os
import sys
import numpy as np
from kiwoom_receiver_tick import KiwoomReceiverTick
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, roundfigure_upper5, GetSangHahanga


class KiwoomReceiverMin(KiwoomReceiverTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp):
        if self.operation == 1:
            self.operation = 3

        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('tickdata', (code, c, dt)))

        if code in self.tuple_jango and (code not in self.dict_jgdt.keys() or dt > self.dict_jgdt[code]):
            self.straderQ.put((code, c))
            self.dict_jgdt[code] = dt

        if code not in self.dict_vipr.keys():
            self.InsertViPrice(code, o)
        elif not self.dict_vipr[code][0] and now() > self.dict_vipr[code][1]:
            self.UpdateViPrice(code, c)

        if code in self.dict_data.keys():
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

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, dmp, jvp, vrp, jsvp, sgta, rf, bids, asks, self.dict_vipr[code][1], self.dict_vipr[code][2], self.dict_vipr[code][-1], mo, mh, ml]

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.kwzservQ.put(('hoga', (self.dict_name[code], c, per, sgta, self.dict_vipr[code][2], o, h, low)))
                if asks > 0: self.kwzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.kwzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, receivetime):
        mm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data.keys():
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt.keys():
                if dt_min > self.dict_tmdt[code][0] and hoga_bamount[4] != 0:
                    send = True
            else:
                self.dict_tmdt[code] = [dt_min, 0]
            mm = dm - self.dict_tmdt[code][1]
            if mm == dm and 100000 < int(str(dt)[8:]) < 152000: mm = 0

        if send or code == self.chart_code:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = 0
                for i, price in enumerate(hoga_seprice[::-1]):
                    if price >= csp:
                        index = i
                        break
                if index <= 5:
                    hoga_seprice = hoga_seprice[5 - index:10 - index]
                    hoga_samount = hoga_samount[5 - index:10 - index]
                else:
                    hoga_seprice = tuple(np.zeros(index - 5)) + hoga_seprice[:10 - index]
                    hoga_samount = tuple(np.zeros(index - 5)) + hoga_samount[:10 - index]
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = 0
                for i, price in enumerate(hoga_buprice):
                    if price <= cbp:
                        index = i
                        break
                hoga_buprice = hoga_buprice[index:index + 5]
                hoga_bamount = hoga_bamount[index:index + 5]
                if index > 5:
                    hoga_buprice = hoga_buprice + tuple(np.zeros(index - 5))
                    hoga_bamount = hoga_bamount + tuple(np.zeros(index - 5))
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            c     = self.dict_data[code][0]
            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            gsjm  = 1 if code in self.list_gsjm else 0
            dt_   = self.dict_tmdt[code][0]
            data  = (dt_,) + tuple(self.dict_data[code]) + (mm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + (hgjrt, gsjm, code, name, logt, send)

            self.sstgQs[self.dict_sgbn[code]].put(data)
            if send:
                if code in self.tuple_jango or code in self.tuple_order:
                    self.straderQ.put(('주문확인', code, c))

                if self.dict_set['리시버공유'] == 1:
                    self.recvservQ.put(('tickdata', data))

                self.dict_tmdt[code] = [dt_min, dm]
                self.dict_data[code][13:15] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt_min
        elif self.int_mtdt < dt_min and str(self.int_mtdt)[-4:] < '1520':
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_min

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            if code in self.dict_sghg.keys():
                shg, hhg = self.dict_sghg[code]
            else:
                shg, hhg = GetSangHahanga(code in self.tuple_kosd, self.kw.GetMasterLastPrice(code), self.int_hgtime)
                self.dict_sghg[code] = (shg, hhg)
            self.kwzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5] + (shg, hhg)))
