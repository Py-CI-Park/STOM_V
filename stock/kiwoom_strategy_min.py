import os
import sys
import math
import numpy as np
from talib import stream
from traceback import print_exc
from kiwoom_strategy_tick import KiwoomStrategyTick
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, strf_time, strp_time, GetUvilower5, GetKiwoomPgSgSp, GetHogaunit


# noinspection PyUnusedLocal
class KiwoomStrategyMin(KiwoomStrategyTick):
    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, \
            라운드피겨위5호가이내, 분당매수수량, 분당매도수량, VI해제시간, VI가격, VI호가단위, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, \
            고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, \
            매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, \
            매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data

        def Parameter_Previous(aindex, pre):
            if pre < 데이터길이:
                pindex = (self.indexn - pre) if pre != -1 else self.indexb
                return self.dict_arry[종목코드][pindex, aindex]
            return 0

        def 현재가N(pre):
            return Parameter_Previous(1, pre)

        def 시가N(pre):
            return Parameter_Previous(2, pre)

        def 고가N(pre):
            return Parameter_Previous(3, pre)

        def 저가N(pre):
            return Parameter_Previous(4, pre)

        def 등락율N(pre):
            return Parameter_Previous(5, pre)

        def 당일거래대금N(pre):
            return Parameter_Previous(6, pre)

        def 체결강도N(pre):
            return Parameter_Previous(7, pre)

        def 거래대금증감N(pre):
            return Parameter_Previous(8, pre)

        def 전일비N(pre):
            return Parameter_Previous(9, pre)

        def 회전율N(pre):
            return Parameter_Previous(10, pre)

        def 전일동시간비N(pre):
            return Parameter_Previous(11, pre)

        def 시가총액N(pre):
            return Parameter_Previous(12, pre)

        def 라운드피겨위5호가이내N(pre):
            return Parameter_Previous(13, pre)

        def 분당매수수량N(pre):
            return Parameter_Previous(14, pre)

        def 분당매도수량N(pre):
            return Parameter_Previous(15, pre)

        def 분봉시가N(pre):
            return Parameter_Previous(19, pre)

        def 분봉고가N(pre):
            return Parameter_Previous(20, pre)

        def 분봉저가N(pre):
            return Parameter_Previous(21, pre)

        def 분당거래대금N(pre):
            return Parameter_Previous(22, pre)

        def 고저평균대비등락율N(pre):
            return Parameter_Previous(23, pre)

        def 매도총잔량N(pre):
            return Parameter_Previous(24, pre)

        def 매수총잔량N(pre):
            return Parameter_Previous(25, pre)

        def 매도호가5N(pre):
            return Parameter_Previous(26, pre)

        def 매도호가4N(pre):
            return Parameter_Previous(27, pre)

        def 매도호가3N(pre):
            return Parameter_Previous(28, pre)

        def 매도호가2N(pre):
            return Parameter_Previous(29, pre)

        def 매도호가1N(pre):
            return Parameter_Previous(30, pre)

        def 매수호가1N(pre):
            return Parameter_Previous(31, pre)

        def 매수호가2N(pre):
            return Parameter_Previous(32, pre)

        def 매수호가3N(pre):
            return Parameter_Previous(33, pre)

        def 매수호가4N(pre):
            return Parameter_Previous(34, pre)

        def 매수호가5N(pre):
            return Parameter_Previous(35, pre)

        def 매도잔량5N(pre):
            return Parameter_Previous(36, pre)

        def 매도잔량4N(pre):
            return Parameter_Previous(37, pre)

        def 매도잔량3N(pre):
            return Parameter_Previous(38, pre)

        def 매도잔량2N(pre):
            return Parameter_Previous(39, pre)

        def 매도잔량1N(pre):
            return Parameter_Previous(40, pre)

        def 매수잔량1N(pre):
            return Parameter_Previous(41, pre)

        def 매수잔량2N(pre):
            return Parameter_Previous(42, pre)

        def 매수잔량3N(pre):
            return Parameter_Previous(43, pre)

        def 매수잔량4N(pre):
            return Parameter_Previous(44, pre)

        def 매수잔량5N(pre):
            return Parameter_Previous(45, pre)

        def 매도수5호가잔량합N(pre):
            return Parameter_Previous(46, pre)

        def 관심종목N(pre):
            return Parameter_Previous(47, pre)

        def 이동평균(tick, pre=0):
            if tick == 5:
                return Parameter_Previous(48, pre)
            elif tick == 10:
                return Parameter_Previous(49, pre)
            elif tick == 20:
                return Parameter_Previous(50, pre)
            elif tick == 60:
                return Parameter_Previous(51, pre)
            elif tick == 120:
                return Parameter_Previous(52, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    return round(self.dict_arry[종목코드][sindex:eindex, 1].mean(), 3)
                return 0

        def Parameter_Area(aindex, vindex, tick, pre, gubun_):
            if tick == 평균값계산틱수:
                return Parameter_Previous(aindex, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    if gubun_ == 'max':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].max()
                    elif gubun_ == 'min':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].min()
                    elif gubun_ == 'sum':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].sum()
                    else:
                        return self.dict_arry[종목코드][sindex:eindex, vindex].mean()
                return 0

        def 최고현재가(tick, pre=0):
            return Parameter_Area(53, 1, tick, pre, 'max')

        def 최저현재가(tick, pre=0):
            return Parameter_Area(54, 1, tick, pre, 'min')

        def 최고분봉고가(tick, pre=0):
            return Parameter_Area(55, 20, tick, pre, 'max')

        def 최저분봉저가(tick, pre=0):
            return Parameter_Area(56, 21, tick, pre, 'min')

        def 체결강도평균(tick, pre=0):
            return round(Parameter_Area(57, 7, tick, pre, 'mean'), 3)

        def 최고체결강도(tick, pre=0):
            return Parameter_Area(58, 7, tick, pre, 'max')

        def 최저체결강도(tick, pre=0):
            return Parameter_Area(59, 7, tick, pre, 'min')

        def 최고분당매수수량(tick, pre=0):
            return Parameter_Area(60, 14, tick, pre, 'max')

        def 최고분당매도수량(tick, pre=0):
            return Parameter_Area(61, 15, tick, pre, 'max')

        def 누적분당매수수량(tick, pre=0):
            return Parameter_Area(62, 14, tick, pre, 'sum')

        def 누적분당매도수량(tick, pre=0):
            return Parameter_Area(63, 15, tick, pre, 'sum')

        def 분당거래대금평균(tick, pre=0):
            return int(Parameter_Area(64, 22, tick, pre, 'mean'))

        def Parameter_Dgree(aindex, vindex, tick, pre, cf):
            if tick == 평균값계산틱수:
                return Parameter_Previous(aindex, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn - pre - tick + 1) if pre != -1  else self.indexb - tick + 1
                    eindex = (self.indexn - pre) if pre != -1  else self.indexb
                    dmp_gap = self.dict_arry[종목코드][eindex, vindex] - self.dict_arry[종목코드][sindex, vindex]
                    return round(math.atan2(dmp_gap * cf, tick) / (2 * math.pi) * 360, 2)
                return 0

        def 등락율각도(tick, pre=0):
            return Parameter_Dgree(65, 5, tick, pre, 5)

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(66, 6, tick, pre, 0.01)

        def 전일비각도(tick, pre=0):
            return Parameter_Dgree(67, 9, tick, pre, 1)

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn.keys() and \
                    조건명 in self.dict_cond_indexn[종목코드].keys() and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        def AD_N(pre):
            return Parameter_Previous(68, pre)

        def ADOSC_N(pre):
            return Parameter_Previous(69, pre)

        def ADXR_N(pre):
            return Parameter_Previous(70, pre)

        def APO_N(pre):
            return Parameter_Previous(71, pre)

        def AROOND_N(pre):
            return Parameter_Previous(72, pre)

        def AROONU_N(pre):
            return Parameter_Previous(73, pre)

        def ATR_N(pre):
            return Parameter_Previous(74, pre)

        def BBU_N(pre):
            return Parameter_Previous(75, pre)

        def BBM_N(pre):
            return Parameter_Previous(76, pre)

        def BBL_N(pre):
            return Parameter_Previous(77, pre)

        def CCI_N(pre):
            return Parameter_Previous(78, pre)

        def DIM_N(pre):
            return Parameter_Previous(79, pre)

        def DIP_N(pre):
            return Parameter_Previous(80, pre)

        def MACD_N(pre):
            return Parameter_Previous(81, pre)

        def MACDS_N(pre):
            return Parameter_Previous(82, pre)

        def MACDH_N(pre):
            return Parameter_Previous(83, pre)

        def MFI_N(pre):
            return Parameter_Previous(84, pre)

        def MOM_N(pre):
            return Parameter_Previous(85, pre)

        def OBV_N(pre):
            return Parameter_Previous(86, pre)

        def PPO_N(pre):
            return Parameter_Previous(87, pre)

        def ROC_N(pre):
            return Parameter_Previous(88, pre)

        def RSI_N(pre):
            return Parameter_Previous(89, pre)

        def SAR_N(pre):
            return Parameter_Previous(90, pre)

        def STOCHSK_N(pre):
            return Parameter_Previous(91, pre)

        def STOCHSD_N(pre):
            return Parameter_Previous(92, pre)

        def STOCHFK_N(pre):
            return Parameter_Previous(93, pre)

        def STOCHFD_N(pre):
            return Parameter_Previous(94, pre)

        def WILLR_N(pre):
            return Parameter_Previous(95, pre)

        시분초 = int(str(체결시간)[8:] + '00')
        호가단위 = GetHogaunit(종목코드 in self.tuple_kosd, 현재가, 체결시간)
        VI아래5호가 = GetUvilower5(VI가격, VI호가단위, 체결시간)
        VI해제시간_ = int(strf_time('%Y%m%d%H%M%S', VI해제시간))
        평균값계산틱수 = self.dict_set['주식평균값계산틱수']
        이동평균005, 이동평균010, 이동평균020, 이동평균060, 이동평균120, 최고현재가_, 최저현재가_, 최고분봉고가_, 최저분봉저가_ = 0., 0., 0., 0., 0., 0, 0, 0, 0
        체결강도평균_, 최고체결강도_, 최저체결강도_, 최고분당매수수량_, 최고분당매도수량_ = 0., 0., 0., 0, 0
        누적분당매수수량_, 누적분당매도수량_, 분당거래대금평균_, 등락율각도_, 당일거래대금각도_, 전일비각도_ = 0, 0, 0., 0., 0., 0.
        AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, \
            PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = \
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.dict_set['주식매수시장가잔량범위']]
        self.shogainfo = shogainfo[:self.dict_set['주식매도시장가잔량범위']]

        if 종목코드 in self.dict_arry.keys():
            len_array = len(self.dict_arry[종목코드])
            if len_array >=   4: 이동평균005 = round((self.dict_arry[종목코드][-4:,   1].sum() + 현재가) / 5, 3)
            if len_array >=   9: 이동평균010 = round((self.dict_arry[종목코드][-9:,   1].sum() + 현재가) / 10, 3)
            if len_array >=  19: 이동평균020 = round((self.dict_arry[종목코드][-19:,  1].sum() + 현재가) / 20, 3)
            if len_array >=  59: 이동평균060 = round((self.dict_arry[종목코드][-59:,  1].sum() + 현재가) / 60, 3)
            if len_array >= 119: 이동평균120 = round((self.dict_arry[종목코드][-119:, 1].sum() + 현재가) / 120, 3)
            if len_array >= 평균값계산틱수 - 1:
                최고현재가_      = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 1].max(), 현재가)
                최저현재가_      = min(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 1].min(), 현재가)
                체결강도평균_    = round((self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].sum() + 체결강도) / 평균값계산틱수, 3)
                최고체결강도_    = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].max(), 체결강도)
                최저체결강도_    = min(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].min(), 체결강도)
                최고분당매수수량_ = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 14].max(), 분당매수수량)
                최고분당매도수량_ = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 15].max(), 분당매도수량)
                누적분당매수수량_ = self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 14].sum() + 분당매수수량
                누적분당매도수량_ = self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 15].sum() + 분당매도수량
                최고분봉고가_    = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 20].max(), 분봉고가)
                최저분봉저가_    = min(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 21].min(), 분봉저가)
                분당거래대금평균_ = int((self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 22].sum() + 분당거래대금) / 평균값계산틱수)
                등락율각도_      = round(math.atan2((등락율 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 5]) * 5, 평균값계산틱수) / (2 * math.pi) * 360, 2)
                당일거래대금각도_ = round(math.atan2((당일거래대금 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 6]) / 100, 평균값계산틱수) / (2 * math.pi) * 360, 2)
                전일비각도_      = round(math.atan2(전일비 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 9], 평균값계산틱수) / (2 * math.pi) * 360, 2)

            """
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액,
               0      1     2    3    4     5         6         7         8        9      10       11        12
            라운드피겨위5호가이내, 분당매수수량, 분당매도수량, VI해제시간, VI가격, VI호가단위, 분봉시가, 분봉고가, 분봉저가, 분당거래대금,
                    13             14         15         16       17       18       19       20       21       22
            고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2,
                   23          24        25        26        27       28       29        30       31       32
            매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3,
               33       34        35       36       37       38        39       40        41       42        43
            매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목, 이동평균005, 이동평균010, 이동평균020, 이동평균060, 이동평균120,
               44       45          46           47        48         49          50         51         52
            최고현재가_, 최저현재가_, 최고분봉고가_, 최저분봉저가_, 체결강도평균_, 최고체결강도_, 최저체결강도, 최고분당매수수량_,
               53         54          55          56           57           58          59            60
            최고분당매도수량_, 누적분당매수수량_, 누적분당매도수량_, 분당거래대금평균_, 등락율각도_, 당일거래대금각도_, 전일비각도_,
                  61             62              63              64           65           66            67
            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI,
            68   69     70    71    72      73     74   75   76   77   78   79   80   81    82     83     84
            MOM, OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR
            85   86   87   88   89   90      91      92       93       94      95
            """

            k  = list(self.indicator.values())
            mc = np.r_[self.dict_arry[종목코드][:,  1], np.array([현재가])]
            mh = np.r_[self.dict_arry[종목코드][:, 20], np.array([분봉고가])]
            ml = np.r_[self.dict_arry[종목코드][:, 21], np.array([분봉저가])]
            mv = np.r_[self.dict_arry[종목코드][:, 22], np.array([분당거래대금])]
            try:    AD                     = stream.AD(      mh, ml, mc, mv)
            except: AD                     = 0
            if k[0] != 0:
                try:    ADOSC              = stream.ADOSC(   mh, ml, mc, mv, fastperiod=k[0], slowperiod=k[1])
                except: ADOSC              = 0
            if k[2] != 0:
                try:    ADXR               = stream.ADXR(    mh, ml, mc,     timeperiod=k[2])
                except: ADXR               = 0
            if k[3] != 0:
                try:    APO                = stream.APO(     mc,             fastperiod=k[3], slowperiod=k[4], matype=k[5])
                except: APO                = 0
            if k[6] != 0:
                try:    AROOND, AROONU     = stream.AROON(   mh, ml,         timeperiod=k[6])
                except: AROOND, AROONU     = 0, 0
            if k[7] != 0:
                try:    ATR                = stream.ATR(     mh, ml, mc,     timeperiod=k[7])
                except: ATR                = 0
            if k[8] != 0:
                try:    BBU, BBM, BBL      = stream.BBANDS(  mc,             timeperiod=k[8], nbdevup=k[9], nbdevdn=k[10], matype=k[11])
                except: BBU, BBM, BBL      = 0, 0, 0
            if k[12] != 0:
                try:    CCI                = stream.CCI(     mh, ml, mc,     timeperiod=k[12])
                except: CCI                = 0
            if k[13] != 0:
                try:    DIM, DIP           = stream.MINUS_DI(mh, ml, mc,     timeperiod=k[13]), stream.PLUS_DI( mh, ml, mc, timeperiod=k[13])
                except: DIM, DIP           = 0, 0
            if k[14] != 0:
                try:    MACD, MACDS, MACDH = stream.MACD(    mc,             fastperiod=k[14], slowperiod=k[15], signalperiod=k[16])
                except: MACD, MACDS, MACDH = 0, 0, 0
            if k[17] != 0:
                try:    MFI                = stream.MFI(     mh, ml, mc, mv, timeperiod=k[17])
                except: MFI                = 0
            if k[18] != 0:
                try:    MOM                = stream.MOM(     mc,             timeperiod=k[18])
                except: MOM                = 0
            try:    OBV                    = stream.OBV(     mc, mv)
            except: OBV                    = 0
            if k[19] != 0:
                try:    PPO                = stream.PPO(     mc,             fastperiod=k[19], slowperiod=k[20], matype=k[21])
                except: PPO                = 0
            if k[22] != 0:
                try:    ROC                = stream.ROC(     mc,             timeperiod=k[22])
                except: ROC                = 0
            if k[23] != 0:
                try:    RSI                = stream.RSI(     mc,             timeperiod=k[23])
                except: RSI                = 0
            if k[24] != 0:
                try:    SAR                = stream.SAR(     mh, ml,         acceleration=k[24], maximum=k[25])
                except: SAR                = 0
            if k[26] != 0:
                try:    STOCHSK, STOCHSD   = stream.STOCH(   mh, ml, mc,     fastk_period=k[26], slowk_period=k[27], slowk_matype=k[28], slowd_period=k[29], slowd_matype=k[30])
                except: STOCHSK, STOCHSD   = 0, 0
            if k[31] != 0:
                try:    STOCHFK, STOCHFD   = stream.STOCHF(  mh, ml, mc,     fastk_period=k[31], fastd_period=k[32], fastd_matype=k[33])
                except: STOCHFK, STOCHFD   = 0, 0
            if k[34] != 0:
                try:    WILLR              = stream.WILLR(   mh, ml, mc,     timeperiod=k[34])
                except: WILLR              = 0

        new_data_tick = [
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내,
            분당매수수량, 분당매도수량, VI해제시간_, VI가격, VI호가단위, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량,
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5,
            매도수5호가잔량합, 관심종목, 이동평균005, 이동평균010, 이동평균020, 이동평균060, 이동평균120,
            최고현재가_, 최저현재가_, 최고분봉고가_, 최저분봉저가_, 체결강도평균_, 최고체결강도_, 최저체결강도_, 최고분당매수수량_,
            최고분당매도수량_, 누적분당매수수량_, 누적분당매도수량_, 분당거래대금평균_, 등락율각도_, 당일거래대금각도_, 전일비각도_,
            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI,
            MOM, OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR
        ]

        if 종목코드 not in self.dict_arry.keys():
            self.dict_arry[종목코드] = np.array([new_data_tick])
        else:
            if 체결시간 != self.dict_arry[종목코드][-1, 0]:
                self.dict_arry[종목코드] = np.r_[self.dict_arry[종목코드], np.array([new_data_tick])]
            else:
                self.dict_arry[종목코드][-1, :] = np.array([new_data_tick])

        데이터길이 = len(self.dict_arry[종목코드])
        self.indexn = 데이터길이 - 1

        if self.dict_condition and 전략연산:
            if 종목코드 not in self.dict_cond_indexn.keys():
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                try:
                    exec(v)
                except:
                    print_exc()
                    self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - 경과틱수 연산오류')))

        if 체결강도평균_ != 0 and not (매수잔량5 == 0 and 매도잔량5 == 0) and 전략연산:
            if 종목코드 in self.df_jg.index:
                if 종목코드 not in self.dict_buy_num.keys():
                    self.dict_buy_num[종목코드] = len(self.dict_arry[종목코드]) - 1
                매수틱번호 = self.dict_buy_num[종목코드]
                매입가 = self.df_jg['매입가'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                매입금액 = self.df_jg['매입금액'][종목코드]
                분할매수횟수 = int(self.df_jg['분할매수횟수'][종목코드])
                분할매도횟수 = int(self.df_jg['분할매도횟수'][종목코드])
                _, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 현재가)
                매수시간 = strp_time('%Y%m%d%H%M%S', self.df_jg['매수시간'][종목코드])
                보유시간 = (now() - 매수시간).total_seconds()
                if 종목코드 not in self.dict_hilo.keys():
                    self.dict_hilo[종목코드] = [수익률, 수익률]
                else:
                    if 수익률 > self.dict_hilo[종목코드][0]:
                        self.dict_hilo[종목코드][0] = 수익률
                    elif 수익률 < self.dict_hilo[종목코드][1]:
                        self.dict_hilo[종목코드][1] = 수익률
                최고수익률, 최저수익률 = self.dict_hilo[종목코드]
            else:
                매수틱번호, 수익금, 수익률, 매입가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = 0, 0, 0, 0, 0, 0, 0, now(), 0, 0, 0
            self.indexb = 매수틱번호

            BBT = not self.dict_set['주식매수금지시간'] or not (self.dict_set['주식매수금지시작시간'] < 시분초 < self.dict_set['주식매수금지종료시간'])
            BLK = not self.dict_set['주식매수금지블랙리스트'] or 종목코드 not in self.dict_set['주식블랙리스트']
            NIB = 종목코드 not in self.list_buy
            NIS = 종목코드 not in self.list_sell

            A = 관심종목 and NIB and 매입가 == 0
            B = self.dict_set['주식매수분할시그널']
            C = NIB and 매입가 != 0 and 분할매수횟수 < self.dict_set['주식매수분할횟수']
            D = NIB and self.dict_set['주식매도취소매수시그널'] and not NIS

            if BBT and BLK and (A or (B and C) or C or D):
                매수수량 = 0

                if A or (B and C) or C:
                    매수수량 = self.SetBuyCount(분할매수횟수, 매입가, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)

                if A or (B and C) or D:
                    매수 = True
                    if self.buystrategy is not None:
                        try:
                            exec(self.buystrategy)
                        except:
                            print_exc()
                            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - BuyStrategy')))
                elif C:
                    매수 = False
                    분할매수기준수익률 = round((현재가 / 현재가N(-1) - 1) * 100, 2) if self.dict_set['주식매수분할고정수익률'] else 수익률
                    if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                        매수 = True
                    elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                        매수 = True

                    if 매수:
                        self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)

            SBT = not self.dict_set['주식매도금지시간'] or not (self.dict_set['주식매도금지시작시간'] < 시분초 < self.dict_set['주식매도금지종료시간'])
            SCC = self.dict_set['주식매수분할횟수'] == 1 or not self.dict_set['주식매도금지매수횟수'] or 분할매수횟수 > self.dict_set['주식매도금지매수횟수값']
            NIB = 종목코드 not in self.list_buy

            A = NIB and NIS and SCC and 매입가 != 0 and self.dict_set['주식매도분할횟수'] == 1
            B = self.dict_set['주식매도분할시그널']
            C = NIB and NIS and SCC and 매입가 != 0 and 분할매도횟수 < self.dict_set['주식매도분할횟수']
            D = NIS and self.dict_set['주식매수취소매도시그널'] and not NIB
            E = NIB and NIS and 매입가 != 0 and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
            F = NIB and NIS and 매입가 != 0 and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']

            if SBT and (A or (B and C) or C or D or E or F):
                매도 = False
                매도수량 = 0
                강제청산 = E or F

                if A or E or F:
                    매도수량 = 보유수량
                elif (B and C) or C:
                    매도수량 = self.SetSellCount(분할매도횟수, 보유수량, 매입가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)

                if A or (B and C) or D:
                    if self.sellstrategy is not None:
                        try:
                            exec(self.sellstrategy)
                        except:
                            print_exc()
                            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - SellStrategy')))
                elif C or E or F:
                    if 강제청산:
                        매도 = True
                    elif C:
                        if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                            매도 = True
                        elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                            매도 = True

                    if 매도:
                        self.Sell(종목코드, 종목명, 매도수량, 현재가, 매도호가1, 매수호가1, 강제청산)

        if 관심종목 and 전략연산:
            self.df_gj.loc[종목코드] = 종목명, 등락율, 고저평균대비등락율, 분당거래대금, 분당거래대금평균_, 당일거래대금, 체결강도, 체결강도평균_, 최고체결강도_

        if len(self.dict_arry[종목코드]) >= 평균값계산틱수 and self.chart_code == 종목코드:
            self.kwzservQ.put(('window', (ui_num['실시간차트'], 종목명, self.dict_arry[종목코드])))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
