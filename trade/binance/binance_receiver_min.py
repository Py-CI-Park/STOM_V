
from traceback import format_exc
from utility.setting_base import ui_num
from utility.static import now, str_ymdhms_utc
from trade.binance.binance_receiver_tick import BinanceReceiverTick


class BinanceReceiverMin(BinanceReceiverTick):
    def UpdateTickData(self, data):
        try:
            data = data['data']
            dt   = int(str_ymdhms_utc(data['T']))
            code = data['s']
            c    = float(data['p'])
            v    = float(data['q'])
            m    = data['m']
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - UpdateTickData'))
            return

        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.ctraderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        code_data = self.dict_data[code]
        ymd = str(dt)[:8]
        if ymd != self.dict_prec[code][0]:
            self.dict_prec[code] = [ymd, code_data[0]]
            bids, asks, pretbids, pretasks = 0, 0, 0, 0
            o, h, low = c, c, c
            dm = round(v * c, 2)
            mo = mh = ml = c
        else:
            dm, _, bids, asks, pretbids, pretasks = code_data[5:11]
            o, h, low = code_data[1:4]
            if c > h: h = c
            if c < low: low = c
            dm = round(dm + v * c, 2)

            if bids == 0 and asks == 0:
                mo = mh = ml = c
            else:
                mo, mh, ml = code_data[-3:]
                if mh < c: mh = c
                if ml > c: ml = c

        bids_ = v if not m else 0
        asks_ = 0 if not m else v
        bids += bids_
        asks += asks_
        tbids = round(pretbids + bids_, 8)
        tasks = round(pretasks + asks_, 8)
        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500
        per = round((c / self.dict_prec[code][1] - 1) * 100, 2)

        self.dict_daym[code] = dm
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        self.UpdateMoneyFactor(code, c, int(c * bids_), int(c * asks_))
        self.UpdateHogaWindowTick(code, dt, bids_, asks_, c, per, o, h, low, ch)

        dt_ = int(str(dt)[:13])
        data_dlhp = self.dict_dlhp.get(code)
        if data_dlhp:
            if dt_ != data_dlhp[0]:
                data_dlhp[0] = dt_
                data_dlhp[1] = round((h / low - 1) * 100, 2)
        else:
            self.dict_dlhp[code] = [dt_, round((h / low - 1) * 100, 2)]

    def UpdateHogaData(self, data):
        try:
            data = data['data']
            dt   = int(str_ymdhms_utc(data['T']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code = data['s']
            hoga_seprice = [
                float(data['a'][9][0]), float(data['a'][8][0]), float(data['a'][7][0]), float(data['a'][6][0]), float(data['a'][5][0]),
                float(data['a'][4][0]), float(data['a'][3][0]), float(data['a'][2][0]), float(data['a'][1][0]), float(data['a'][0][0])
            ]
            hoga_buprice = [
                float(data['b'][0][0]), float(data['b'][1][0]), float(data['b'][2][0]), float(data['b'][3][0]), float(data['b'][4][0]),
                float(data['b'][5][0]), float(data['b'][6][0]), float(data['b'][7][0]), float(data['b'][8][0]), float(data['b'][9][0])
            ]
            hoga_samount = [
                float(data['a'][9][1]), float(data['a'][8][1]), float(data['a'][7][1]), float(data['a'][6][1]), float(data['a'][5][1]),
                float(data['a'][4][1]), float(data['a'][3][1]), float(data['a'][2][1]), float(data['a'][1][1]), float(data['a'][0][1])
            ]
            hoga_bamount = [
                float(data['b'][0][1]), float(data['b'][1][1]), float(data['b'][2][1]), float(data['b'][3][1]), float(data['b'][4][1]),
                float(data['b'][5][1]), float(data['b'][6][1]), float(data['b'][7][1]), float(data['b'][8][1]), float(data['b'][9][1])
            ]
            hoga_tamount = [
                round(sum(hoga_samount), 8), round(sum(hoga_bamount), 8)
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

                data, c, dm, lhp, logt = self.GetSendData(False, code, code_data, code_dtdm, money_arr,
                                                          hoga_samount, hoga_bamount, hoga_seprice, hoga_buprice,
                                                          hoga_tamount, dt, dt_min)

                data.append(send)
                self.cstgQ.put(data)
                if send:
                    if code in self.tuple_jango:
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
