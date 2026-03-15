
from traceback import print_exc
from PyQt5.QtCore import QThread
from utility.setting_base import indicator
# noinspection PyUnresolvedReferences
from utility.static import timedelta_sec, qtest_qwait, get_logger


# noinspection PyUnusedLocal
class BackCodeTest(QThread):
    def __init__(self, testQ, stg, var=None, ga=False):
        super().__init__()
        self.testQ = testQ
        self.stg   = stg
        self.vars  = None
        self.var   = var
        self.ga    = ga
        self.indicator = indicator
        self.logger    = get_logger(self.__class__.__name__)

    def run(self):
        if self.stg is None:
            self.vars = {i: [[1, 2, 1], 1] for i in range(300)}

            error = False
            try:
                exec(compile(self.var, '<string>', 'exec'))
            except:
                print_exc()
                error = True

            for i, var in enumerate(self.vars.values()):
                if len(var) != 2:
                    self.logger.error(f'self.vars[{i}]의 범위 설정 방법 오류')
                    error = True
                if not self.ga:
                    if len(var[0]) != 3:
                        self.logger.error(f'self.vars[{i}]의 범위 설정 방법 오류')
                        error = True
                    if var[0][2] != 0 and (var[0][1] - var[0][0]) / var[0][2] + 1 > 20:
                        self.logger.error(f'self.vars[{i}]의 범위 설정 갯수 20개 초과')
                        error = True
                    if (var[0][0] < var[0][1] and var[0][2] < 0) or (var[0][0] > var[0][1] and var[0][2] > 0):
                        self.logger.error(f'self.vars[{i}]의 범위 간격 부호 오류')
                        error = True

            if error:
                self.ErrorEnd()
            else:
                self.noErrorEnd()

        else:
            self.vars = {i: 1 for i in range(300)}

            error = False
            if not self.CheckFactor():
                error = True

            try:
                self.stg = compile(self.stg, '<string>', 'exec')
            except:
                print_exc()
                error = True

            if error:
                self.ErrorEnd()
            else:
                self.Test()

    def CheckFactor(self):
        error = False
        gugan_factors = [
            '이동평균', '최고현재가', '최저현재가', '체결강도평균', '최고체결강도', '최저체결강도', '등락율각도', '경과틱수',
            '초당거래대금평균', '누적초당매수수량', '누적초당매도수량', '최고초당매수수량', '최고초당매도수량', '당일거래대금각도', '전일비각도',
            '분당거래대금평균', '누적분당매수수량', '누적분당매도수량', '최고분당매수수량', '최고분당매도수량', '최고분봉고가', '최저분봉저가',
            'N'
        ]
        for factor in gugan_factors:
            if factor in self.stg:
                _stg = self.stg.replace(factor, f'{factor};')
                _stg_list = _stg.split(';')
                for i, txt in enumerate(_stg_list):
                    if factor in txt and _stg_list[i+1][0] != '(':
                        self.logger.error(f'{factor}(30), {factor}(30, 1) 형태로 사용하십시오.')
                        error = True
        if error:
            return False
        else:
            return True

    def ErrorEnd(self):
        self.testQ.put('전략테스트오류')

    def noErrorEnd(self):
        self.testQ.put('전략테스트완료')

    def Buy(*args):
        pass

    def Sell(*args):
        pass

    def Test(self):
        def now():
            return 1

        def 현재가N(pre):
            return 1

        def 시가N(pre):
            return 1

        def 고가N(pre):
            return 1

        def 저가N(pre):
            return 1

        def 등락율N(pre):
            return 1

        def 당일거래대금N(pre):
            return 1

        def 체결강도N(pre):
            return 1

        def 거래대금증감N(pre):
            return 1

        def 전일비N(pre):
            return 1

        def 회전율N(pre):
            return 1

        def 전일동시간비N(pre):
            return 1

        def 시가총액N(pre):
            return 1

        def 라운드피겨위5호가이내N(pre):
            return 1

        def 초당매수수량N(pre):
            return 1

        def 초당매도수량N(pre):
            return 1

        def 초당거래대금N(pre):
            return 1

        def 고저평균대비등락율N(pre):
            return 1

        def 매도총잔량N(pre):
            return 1

        def 매수총잔량N(pre):
            return 1

        def 매도호가5N(pre):
            return 1

        def 매도호가4N(pre):
            return 1

        def 매도호가3N(pre):
            return 1

        def 매도호가2N(pre):
            return 1

        def 매도호가1N(pre):
            return 1

        def 매수호가1N(pre):
            return 1

        def 매수호가2N(pre):
            return 1

        def 매수호가3N(pre):
            return 1

        def 매수호가4N(pre):
            return 1

        def 매수호가5N(pre):
            return 1

        def 매도잔량5N(pre):
            return 1

        def 매도잔량4N(pre):
            return 1

        def 매도잔량3N(pre):
            return 1

        def 매도잔량2N(pre):
            return 1

        def 매도잔량1N(pre):
            return 1

        def 매수잔량1N(pre):
            return 1

        def 매수잔량2N(pre):
            return 1

        def 매수잔량3N(pre):
            return 1

        def 매수잔량4N(pre):
            return 1

        def 매수잔량5N(pre):
            return 1

        def 매도수5호가잔량합N(pre):
            return 1

        def 관심종목N(pre):
            return 1

        def 이동평균(tick, pre=0):
            return 1

        def 등락율각도(tick, pre=0):
            return 1

        def 당일거래대금각도(tick, pre=0):
            return 1

        def 전일비각도(tick, pre=0):
            return 1

        def 최고현재가(tick, pre=0):
            return 1

        def 최저현재가(tick, pre=0):
            return 1

        def 체결강도평균(tick, pre=0):
            return 1

        def 최고체결강도(tick, pre=0):
            return 1

        def 최저체결강도(tick, pre=0):
            return 1

        def 최고초당매수수량(tick, pre=0):
            return 1

        def 최고초당매도수량(tick, pre=0):
            return 1

        def 누적초당매수수량(tick, pre=0):
            return 1

        def 누적초당매도수량(tick, pre=0):
            return 1

        def 초당거래대금평균(tick, pre=0):
            return 1

        def 초당매수금액N(pre):
            return 1
    
        def 초당매도금액N(pre):
            return 1
    
        def 당일매수금액N(pre):
            return 1
    
        def 최고매수금액N(pre):
            return 1
    
        def 최고매수가격N(pre):
            return 1
    
        def 당일매도금액N(pre):
            return 1
    
        def 최고매도금액N(pre):
            return 1
    
        def 최고매도가격N(pre):
            return 1

        def 분당매수수량N(pre):
            return 1

        def 분당매도수량N(pre):
            return 1

        def 분봉시가N(pre):
            return 1

        def 분봉고가N(pre):
            return 1

        def 분봉저가N(pre):
            return 1

        def 분당거래대금N(pre):
            return 1

        def 최고분봉고가(tick, pre=0):
            return 1

        def 최저분봉저가(tick, pre=0):
            return 1

        def 최고분당매수수량(tick, pre=0):
            return 1

        def 최고분당매도수량(tick, pre=0):
            return 1

        def 누적분당매수수량(tick, pre=0):
            return 1

        def 누적분당매도수량(tick, pre=0):
            return 1

        def 분당거래대금평균(tick, pre=0):
            return 1

        def 경과틱수(tick):
            return 1

        def AD_N(pre):
            return 1

        def ADOSC_N(pre):
            return 1

        def ADXR_N(pre):
            return 1

        def APO_N(pre):
            return 1

        def AROOND_N(pre):
            return 1

        def AROONU_N(pre):
            return 1

        def ATR_N(pre):
            return 1

        def BBU_N(pre):
            return 1

        def BBM_N(pre):
            return 1

        def BBL_N(pre):
            return 1

        def CCI_N(pre):
            return 1

        def DIM_N(pre):
            return 1

        def DIP_N(pre):
            return 1

        def MACD_N(pre):
            return 1

        def MACDS_N(pre):
            return 1

        def MACDH_N(pre):
            return 1

        def MFI_N(pre):
            return 1

        def MOM_N(pre):
            return 1

        def OBV_N(pre):
            return 1

        def PPO_N(pre):
            return 1

        def ROC_N(pre):
            return 1

        def RSI_N(pre):
            return 1

        def SAR_N(pre):
            return 1

        def STOCHSK_N(pre):
            return 1

        def STOCHSD_N(pre):
            return 1

        def STOCHFK_N(pre):
            return 1

        def STOCHFD_N(pre):
            return 1

        def WILLR_N(pre):
            return 1

        def 이평지지(window=60, tick=30, per=0.5, cnt=0):
            return 0

        def 시가지지(tick, per=0.5):
            return 0

        def 변동성(tick, pre=0):
            return 0

        def 구간저가대비현재가등락율(tick):
            return 0

        def 구간고가대비현재가등락율(tick):
            return 0

        def 거래대금평균대비비율(tick, pre=0):
            return 0

        def 체결강도평균대비비율(tick, pre=0):
            return 0

        def 구간호가총잔량비율(tick, pre=0):
            return 0

        def 매수수량변동성(tick, pre=0):
            return 0

        def 매도수량변동성(tick, pre=0):
            return 0

        def 횡보감지(tick, per=0.5, pre=0):
            return 0

        def 고가미갱신지속틱수():
            return 1

        def 저가미갱신지속틱수():
            return 1

        def 고점기준등락율각도(cf):
            return 0

        def 저점기준등락율각도(cf):
            return 0

        def 연속상승(tick):
            return False

        def 연속하락(tick):
            return False

        def 호가갭발생(hogagap, pre=0):
            return False

        def 변동성급증(tick, ratio=2):
            return False

        def 변동성급감(tick, ratio=2):
            return False

        def 가격급등(tick, per=0.7):
            return False

        def 가격급락(tick, per=0.7):
            return False

        def 거래대금급증(tick, ratio=3):
            return False

        def 거래대금급감(tick, ratio=0.7):
            return False

        def 체결강도급등(tick, ratio=1.1):
            return False

        def 체결강도급락(tick, ratio=0.9):
            return False

        def 호가상승압력(tick, ratio=0.7):
            return False

        def 호가하락압력(tick, ratio=0.3):
            return False

        def 매수수량급증(tick, ratio=3):
            return False

        def 매수수량급감(tick, ratio=0.3):
            return False

        def 매도수량급증(tick, ratio=3):
            return False

        def 매도수량급감(tick, ratio=0.3):
            return False

        def 이평돌파(tick, per=1.0):
            return False

        def 이평이탈(tick, per=1.0):
            return False

        def 시가돌파(tick, per=1.0):
            return False

        def 시가이탈(tick, per=1.0):
            return False

        def 이평지지후이평돌파(tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
            return False

        def 이평지지후이평이탈(tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
            return False

        def 횡보후가격급등(tick1, per1=0.5, tick2=2, per2=0.5):
            return False

        def 횡보후가격급락(tick1, per1=0.5, tick2=2, per2=0.5):
            return False

        def 횡보후연속상승(tick1, per1=0.5, tick2=3):
            return False

        def 횡보후연속하락(tick1, per1=0.5, tick2=3):
            return False

        def 연속상승및가격급등(tick1, tick2=2, per=0.5):
            return False

        def 연속하락및가격급락(tick1, tick2=2, per=0.5):
            return False

        def 거래대금급증및연속상승(tick1, ratio=2, tick2=5):
            return False

        def 호가상승압력및매수수량급증(tick, ratio1=0.7, ratio2=3):
            return False

        def 호가하락압력및매도수량급증(tick, ratio=0.3, ratio2=3):
            return False

        def 매수수량급증및가격급등(tick, ratio=3, tick2=5, per=0.7):
            return False

        def 매도수량급증후가격급락(tick, ratio=3, tick2=5, per=0.7):
            return False

        def 변동성급증및구간최고가갱신(tick, ratio=2):
            return False

        def 변동성급감및구간최저가갱신(tick, ratio=2):
            return False

        def 거래대금급증및구간최고가갱신(tick, ratio=2):
            return False

        def 거래대금급감후구간최저가갱신(tick, ratio=0.5):
            return False

        def 거래대금급증및가격급등(tick1, ratio=2, tick2=5, per=0.7):
            return False

        def 거래대금급감및가격급락(tick1, ratio=0.5, tick2=5, per=0.7):
            return False

        def 체결강도급등및호가상승압력(tick1, ratio1=1.1, tick2=10, ratio2=0.7):
            return False

        def 체결강도급락및호가하락압력(tick1, ratio1=0.9, tick2=10, ratio2=0.3):
            return False

        def 시가근접황보후시가돌파(tick, per1=0.5, cnt=7, per2=1.0):
            return False

        def 시가근접황보후시가이탈(tick, per1=0.5, cnt=7, per2=1.0):
            return False

        def 저가갱신후가격급등(tick, per=2):
            return False

        def 고가갱신후가격급락(tick, per=2):
            return False

        def 횡보상태장기보유(tick, per=0.5, time_=600):
            return False

        def 변동성급증_역추세매도(vol_tick, ratio=2.5, reversal_per=1.0):
            return False

        def 장기보유종목_동적익절청산(tick, time_=600, minper=0.3, multi=1):
            return False

        def 거래대금비율기반_동적청산(tick, ratio1=0.3, ratio2=3):
            return False

        def 호가압력기반_동적청산(tick, buy_pressure=0.8, sell_pressure=0.2):
            return False

        def 이평기반_동적청산(short, long=60, deviation1=0.5, deviation2=0.5):
            return False

        def 변동성기반_동적청산(tick, ratio1=3, ratio2=1.5):
            return False

        def 변동성급증기반_동적청산(tick, multi=2, ratio1=3, ratio2=1.5):
            return False

        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, \
            라운드피겨위5호가이내, 초당매수수량, 초당매도수량, VI해제시간, VI가격, VI호가단위, 초당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도수5호가잔량합, 관심종목, 종목코드, 틱수신시간, 종목명 = [
                20220721090001, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, now(), 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, '005930', now(), '삼성전자'
            ]

        초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, 분당매수수량, \
            분당매도수량, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, 분당매수금액, 분당매도금액 = \
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1

        시분초, 데이터길이, 호가단위, 포지션, 평균값계산틱수 = int(str(체결시간)[8:]), 1800, 1, 'LONG', 30

        AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, \
            PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = \
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

        shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        수익률, 매수가, 보유수량, 매도수량, 분할매수횟수, 분할매도횟수, 보유시간, 최고수익률, 최저수익률 = 1, 1, 1, 1, 1, 0, 0, 1, 0
        매수, 매도, BUY_LONG, SELL_LONG, SELL_SHORT, BUY_SHORT, 강제청산 = False, False, False, False, False, False, False

        try:
            exec(self.stg)
        except:
            print_exc()
            self.ErrorEnd()
        else:
            self.noErrorEnd()
