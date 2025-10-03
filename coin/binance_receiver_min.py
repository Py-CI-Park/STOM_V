import numpy as np
from coin.binance_receiver_tick import BinanceReceiverTick
from utility.setting import ui_num
from utility.static import now


class BinanceReceiverMin(BinanceReceiverTick):
    def UpdateTradeData(self, code, c, v, m, dt):
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('tickdata', (code, c, dt)))

        if code in self.tuple_jango and (code not in self.dict_jgdt.keys() or dt > self.dict_jgdt[code]):
            self.ctraderQ.put((code, c))
            self.dict_jgdt[code] = dt

        ymd = str(dt)[:8]
        if ymd != self.dict_tddt[code][0]:
            self.dict_tddt[code] = [ymd, self.dict_data[code][0]]
            bids, asks, pretbids, pretasks = 0, 0, 0, 0
            o, h, low = c, c, c
            dm = round(v * c, 2)
        else:
            bids, asks, pretbids, pretasks = self.dict_data[code][7:11]
            o, h, low = self.dict_data[code][1:4]
            if c > h: h = c
            if c < low: low = c
            dm = round(self.dict_data[code][5] + v * c, 2)

        if bids == 0 and asks == 0:
            mo = mh = ml = c
        else:
            mo, mh, ml = self.dict_data[code][-3:]
            if mh < c: mh = c
            if ml > c: ml = c

        bids_ = v if not m else 0
        asks_ = 0 if not m else v
        bids += bids_
        asks += asks_
        tbids = round(pretbids + bids_, 8)
        tasks = round(pretasks + asks_, 8)
        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.
        per = round((c / self.dict_tddt[code][1] - 1) * 100, 2)

        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]
        self.dict_daym[code] = dm

        dt_ = int(str(dt)[:13])
        if code not in self.dict_dlhp.keys() or dt_ != self.dict_dlhp[code][0]:
            self.dict_dlhp[code] = [dt_, round((h / low - 1) * 100, 2)]

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.hogaQ.put((code, c, per, 0, 0, o, h, low))
                if asks > 0: self.hogaQ.put((-asks, ch))
                if bids > 0: self.hogaQ.put((bids, ch))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, receivetime):
        mm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data.keys():
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt.keys():
                if dt_min > self.dict_tmdt[code][0]:
                    send = True
            else:
                self.dict_tmdt[code] = [dt_min, 0]
            mm = dm - self.dict_tmdt[code][1]
            if mm == dm and 10000 < int(str(dt)[8:]) < 235000: mm = 0

        if send or code == self.chart_code:
            c = self.dict_data[code][0]

            if hoga_seprice[-1] < c:
                index = 0
                for i, price in enumerate(hoga_seprice[::-1]):
                    if price >= c:
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

            if hoga_buprice[0] > c:
                index = 0
                for i, price in enumerate(hoga_buprice):
                    if price <= c:
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

            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            gsjm  = 1 if code in self.list_gsjm else 0
            dt_   = self.dict_tmdt[code][0]
            data  = (dt_,) + tuple(self.dict_data[code][:9]) + tuple(self.dict_data[code][11:]) + (mm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + (hgjrt, gsjm, code, logt, send)

            self.cstgQ.put(data)
            if send:
                if code in self.tuple_order or code in self.tuple_jango:
                    self.ctraderQ.put(('주문확인', code, c))

                if self.dict_set['리시버공유'] == 1:
                    self.recvservQ.put(('tickdata', data))

                self.dict_tmdt[code] = [dt_min, dm]
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
