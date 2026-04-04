
from future_agent_tick import FutureAgentTick


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

        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500

        if code not in self.list_gsjm:
            self.list_gsjm.append(code)

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        self.UpdateMoneyFactor(code, c, int(wtm * bids_), int(wtm * asks_))
        self.UpdateHogaWindowTick(code, dt, bids_, asks_, c, per, o, h, low, ch)

    def UpdateHogaData(self, dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                       code, name, receivetime):

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
                csp, cbp = self.dict_hgbs[code]
                hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount = \
                    self.CorrectionHogaData(csp, cbp, hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount)

                data, c, dm, logt = self.GetSendData(False, code, name, code_data, code_dtdm, money_arr,
                                                     hoga_samount, hoga_bamount, hoga_seprice, hoga_buprice,
                                                     hoga_tamount, dt, dt_min)

                data.append(send)
                self.sstgQ.put(data)
                if send:
                    if code in self.tuple_order:
                        self.straderQ.put(('주문확인', (code, c)))

                    code_dtdm[0] = dt_min
                    code_dtdm[1] = dm
                    code_data[7] = 0
                    code_data[8] = 0
                    money_arr[0] = 0
                    money_arr[1] = 0

                self.SendLog(logt, dt_min, receivetime)

        self.UpdateMoneyTop(dt_min)
        self.UpdateHogaWindowRem(code, name, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount)
