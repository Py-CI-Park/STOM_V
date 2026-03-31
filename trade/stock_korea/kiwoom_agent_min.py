
import os
import sys
from kiwoom_agent_tick import KiwoomAgentTick
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.static import roundfigure_upper5


class KiwoomAgentMin(KiwoomAgentTick):
    def UpdateTickData(self, code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp):
        if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
            self.straderQ.put(('잔고갱신', (code, c)))
            self.dict_jgdt[code] = dt

        self.CheckVI(code, c, o)

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

        self.UpdateMoneyFactor(code, c, c * bids_, c * asks_)
        self.UpdateHogaWindowTick(code, dt, bids_, asks_, c, per, sgta, uvi, o, h, low, ch)

    def UpdateHogaData(self, dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                       code, name, receivetime, lastprice):

        send   = False
        dt_min = int(str(dt)[:12])

        code_data = self.dict_data.get(code)
        money_arr = self.dict_money.get(code)
        if code_data and money_arr:
            code_dtdm = self.dict_dtdm.get(code)
            if code_dtdm:
                if dt_min > code_dtdm[0] and hoga_bamount[4] != 0:
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
                self.sstgQs[self.dict_sgbn[code]].put(data)
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
        self.UpdateHogaWindowRem(code, name, dt, lastprice, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount)
