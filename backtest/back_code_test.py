
import re
from traceback import format_exc
from PyQt5.QtCore import QThread
from strategy.analyzer_microstructure import AnalyzerMicrostructure
from utility.settings.setting_base import DICT_INDICATOR, UI_NUM
# noinspection PyUnresolvedReferences
from utility.static_method.static import timedelta_sec, qtest_qwait, now


# noinspection PyUnusedLocal,PyUnresolvedReferences
class BackCodeTest(QThread):
    """백테스트 코드 테스트 스레드 클래스입니다.
    전략 코드의 문법을 검증합니다.
    """
    def __init__(self, testQ, windowQ, stg, fm_list=None, var=None, ga=False):
        super().__init__()
        self.testQ       = testQ
        self.windowQ     = windowQ
        self.stg         = stg
        self.fm_list     = fm_list
        self.vars        = None
        self.var         = var
        self.ga          = ga
        self.ms_analyzer = AnalyzerMicrostructure('stock', [])
        self.indicator   = DICT_INDICATOR

    def run(self):
        """테스트를 실행합니다.
        전략 코드의 문법을 검증합니다.
        """
        if self.stg is None:
            self.vars = {i: [[1, 2, 1], 1] for i in range(300)}

            error = False
            try:
                exec(compile(self.var, '<string>', 'exec'))
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
                error = True

            for i, var in enumerate(self.vars.values()):
                if len(var) != 2:
                    self.windowQ.put((UI_NUM['시스템로그'], f'오류 알림 - self.vars[{i}]의 범위 설정 방법 오류'))
                    error = True
                if not self.ga:
                    if len(var[0]) != 3:
                        self.windowQ.put((UI_NUM['시스템로그'], f'오류 알림 - self.vars[{i}]의 범위 설정 방법 오류'))
                        error = True
                    if var[0][2] != 0 and (var[0][1] - var[0][0]) / var[0][2] + 1 > 20:
                        self.windowQ.put((UI_NUM['시스템로그'], f'오류 알림 - self.vars[{i}]의 범위 설정 갯수 20개 초과'))
                        error = True
                    if (var[0][0] < var[0][1] and var[0][2] < 0) or (var[0][0] > var[0][1] and var[0][2] > 0):
                        self.windowQ.put((UI_NUM['시스템로그'], f'오류 알림 - self.vars[{i}]의 범위 간격 부호 오류'))
                        error = True

            if error:
                self._error_end()
            else:
                self._no_error_end()

        else:
            self.vars = {i: 1 for i in range(300)}

            error = False
            if not self._check_factor():
                error = True

            try:
                self.stg = compile(self.stg, '<string>', 'exec')
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
                error = True

            if error:
                self._error_end()
            else:
                self._test()

    def _check_factor(self):
        error = False
        gugan_factors = [
            '이동평균', '최고현재가', '최저현재가', '체결강도평균', '최고체결강도', '최저체결강도', '등락율각도', '경과틱수',
            '초당거래대금평균', '누적초당매수수량', '누적초당매도수량', '최고초당매수수량', '최고초당매도수량', '당일거래대금각도',
            '분당거래대금평균', '누적분당매수수량', '누적분당매도수량', '최고분당매수수량', '최고분당매도수량', '최고분봉고가', '최저분봉저가',
            '이평지지', '이평돌파', '이평이탈', '시가지지', '시가돌파', '시가이탈', '변동성', '변동성급증', '변동성급감',
            '구간저가대비현재가등락율', '구간고가대비현재가등락율', '거래대금평균대비비율', '체결강도평균대비비율', '구간호가총잔량비율',
            '매수수량변동성', '매도수량변동성', '고가미갱신지속틱수', '저가미갱신지속틱수', '횡보감지', '연속상승', '가격급등', '거래대금급증',
            '매수수량급증', '매도수량급증', '연속하락', '가격급락', '거래대금급감', '매수수량급감', '매도수량급감', '이평지지후이평돌파',
            '체결강도급등', '호가상승압력', '횡보후가격급등', '횡보후연속상승', '이평지지후이평이탈', '체결강도급락', '호가하락압력',
            '횡보후가격급락', '횡보후연속하락', '연속상승및가격급등', '거래대금급증및구간최고가갱신', '거래대금급증및가격급등',
            '거래대금급증및연속상승', '호가상승압력및매수수량급증', '연속하락및가격급락', '거래대금급감후구간최저가갱신', '거래대금급감및가격급락',
            '거래대금급감및연속하락', '호가하락압력및매도수량급증', '체결강도급등및호가상승압력', '매수수량급증및가격급등', '시가근접황보후시가돌파',
            '저가갱신후가격급등', '변동성급증및구간최고가갱신', '체결강도급락및호가하락압력', '매도수량급증후가격급락', '시가근접황보후시가이탈',
            '고가갱신후가격급락', '변동성급감및구간최저가갱신', '호가갭발생', '횡보상태장기보유', '변동성급증_역추세매도',
            '장기보유종목_동적익절청산', '거래대금비율기반_동적청산', '호가압력기반_동적청산', '이평기반_동적청산', '변동성기반_동적청산',
            '변동성급증기반_동적청산', '고점저점기준등락율각도'
        ]

        stg = self.stg
        factors = sorted(gugan_factors, key=len, reverse=True)

        for i, raw_line in enumerate(stg.split('\n')):
            line = raw_line.split('#', 1)[0]
            for factor in factors:
                pattern = rf'(?<![0-9A-Za-z_가-힣]){re.escape(factor)}(?![0-9A-Za-z_가-힣])'
                for m in re.finditer(pattern, line):
                    if not re.match(r'\s*\(', line[m.end():]):
                        self.windowQ.put((UI_NUM['시스템로그'], f'오류 알림 - 줄번호[{i + 1}] : {factor}(30), {factor}(30, 1) 형태로 사용하십시오.'))
                        error = True
        if error:
            return False
        else:
            return True

    def _error_end(self):
        self.testQ.put('전략테스트오류')

    def _no_error_end(self):
        self.testQ.put('전략테스트완료')

    def Buy(*args):
        pass

    def Sell(*args):
        pass

    def _test(self):
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

        def 시가총액N(pre):
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

        if self.fm_list is not None:
            locals().update(self.fm_list)

        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 시가총액, VI해제시간, VI가격, VI호가단위, \
            당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = [
                20220721090001, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, now(), 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, '005930', '삼성전자', now()
            ]
        분당매수수량, 분당매도수량, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, 분당매수금액, 분당매도금액 = 1, 1, 1, 1, 1, 1, 1, 1
        시분초, 데이터길이, 호가단위, 포지션 = int(str(체결시간)[8:]), 1800, 1, 'LONG'
        AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, \
            PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = \
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        수익률, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 보유시간, 최고수익률, 최저수익률, 리스크점수 = 1, 1, 1, 1, 1, 1, 1, 1, 1
        패턴점수, 패턴신뢰도, 가격대점수, 가격대신뢰도 = 0, 0, 0, 0
        매수, 매도, BUY_LONG, SELL_LONG, SELL_SHORT, BUY_SHORT, 강제청산 = False, False, False, False, False, False, False

        try:
            exec(self.stg)
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            self._error_end()
        else:
            self._no_error_end()
