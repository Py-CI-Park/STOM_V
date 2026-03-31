
from PyQt5.QtWidgets import QLabel
from ui.set_widget import error_decorator
from ui.set_style import qfont14, style_bc_dk


class SetDialogStrategy:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.dialog_strategy = self.wc.setDialog('STOM STRATEGY')
        self.ui.dialog_strategy.geometry().center()

        self.ui.stg_pushButton_001 = self.wc.setPushbutton('종목코드', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=1)
        self.ui.stg_pushButton_002 = self.wc.setPushbutton('현재가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=2)
        self.ui.stg_pushButton_003 = self.wc.setPushbutton('일봉시가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=3)
        self.ui.stg_pushButton_004 = self.wc.setPushbutton('일봉고가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=4)
        self.ui.stg_pushButton_005 = self.wc.setPushbutton('일봉저가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=5)

        self.ui.stg_pushButton_006 = self.wc.setPushbutton('당일거래대금', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=6)
        self.ui.stg_pushButton_007 = self.wc.setPushbutton('등락율', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=7)
        self.ui.stg_pushButton_008 = self.wc.setPushbutton('고저평균대비등락율', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=8)
        self.ui.stg_pushButton_009 = self.wc.setPushbutton('저가대비고가등락율', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=9)
        self.ui.stg_pushButton_010 = self.wc.setPushbutton('순매수금액', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=10)

        self.ui.stg_pushButton_011 = self.wc.setPushbutton('당일매수금액', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=11)
        self.ui.stg_pushButton_012 = self.wc.setPushbutton('최고매수금액', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=12)
        self.ui.stg_pushButton_013 = self.wc.setPushbutton('최고매수가격', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=13)
        self.ui.stg_pushButton_014 = self.wc.setPushbutton('최고현재가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=14)
        self.ui.stg_pushButton_015 = self.wc.setPushbutton('매도총잔량', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=15)

        self.ui.stg_pushButton_016 = self.wc.setPushbutton('당일매도금액', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=16)
        self.ui.stg_pushButton_017 = self.wc.setPushbutton('최고매도금액', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=17)
        self.ui.stg_pushButton_018 = self.wc.setPushbutton('최고매도가격', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=18)
        self.ui.stg_pushButton_019 = self.wc.setPushbutton('최저현재가', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=19)
        self.ui.stg_pushButton_020 = self.wc.setPushbutton('매수총잔량', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=20)

        self.ui.stg_pushButton_021 = self.wc.setPushbutton('매도수5호가잔량합', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=21)
        self.ui.stg_pushButton_022 = self.wc.setPushbutton('등락율각도', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=22)
        self.ui.stg_pushButton_023 = self.wc.setPushbutton('당일거래대금각도', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=23)
        self.ui.stg_pushButton_024 = self.wc.setPushbutton('체결강도', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=24)
        self.ui.stg_pushButton_025 = self.wc.setPushbutton('체결강도평균', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=25)

        self.ui.stg_pushButton_026 = self.wc.setPushbutton('최고체결강도', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=26)
        self.ui.stg_pushButton_027 = self.wc.setPushbutton('최저체결강도', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=27)
        self.ui.stg_pushButton_028 = self.wc.setPushbutton('시분초', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=28)
        self.ui.stg_pushButton_029 = self.wc.setPushbutton('호가단위', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=29)
        self.ui.stg_pushButton_030 = self.wc.setPushbutton('경과틱수', parent=self.ui.dialog_strategy, color=7, animated=True, click=self.ui.StrategyButtonClicked, cmd=30)

        self.ui.stg_pushButton_031 = self.wc.setPushbutton('이동평균60', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=31)
        self.ui.stg_pushButton_032 = self.wc.setPushbutton('이동평균150', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=32)
        self.ui.stg_pushButton_033 = self.wc.setPushbutton('이동평균300', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=33)
        self.ui.stg_pushButton_034 = self.wc.setPushbutton('이동평균600', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=34)
        self.ui.stg_pushButton_035 = self.wc.setPushbutton('이동평균1200', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=35)

        self.ui.stg_pushButton_036 = self.wc.setPushbutton('초당매수수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=36)
        self.ui.stg_pushButton_037 = self.wc.setPushbutton('초당매도수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=37)
        self.ui.stg_pushButton_038 = self.wc.setPushbutton('최고초당매수수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=38)
        self.ui.stg_pushButton_039 = self.wc.setPushbutton('최고초당매도수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=39)
        self.ui.stg_pushButton_040 = self.wc.setPushbutton('누적초당매수수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=40)

        self.ui.stg_pushButton_041 = self.wc.setPushbutton('누적초당매도수량', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=41)
        self.ui.stg_pushButton_042 = self.wc.setPushbutton('초당거래대금', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=42)
        self.ui.stg_pushButton_043 = self.wc.setPushbutton('초당거래대금평균', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=43)
        self.ui.stg_pushButton_044 = self.wc.setPushbutton('초당매수금액', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=44)
        self.ui.stg_pushButton_045 = self.wc.setPushbutton('초당매도금액', parent=self.ui.dialog_strategy, color=8, animated=True, click=self.ui.StrategyButtonClicked, cmd=45)

        self.ui.stg_pushButton_046 = self.wc.setPushbutton('이동평균5', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=46)
        self.ui.stg_pushButton_047 = self.wc.setPushbutton('이동평균10', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=47)
        self.ui.stg_pushButton_048 = self.wc.setPushbutton('이동평균20', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=48)
        self.ui.stg_pushButton_049 = self.wc.setPushbutton('이동평균60', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=49)
        self.ui.stg_pushButton_050 = self.wc.setPushbutton('이동평균120', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=50)

        self.ui.stg_pushButton_051 = self.wc.setPushbutton('분봉시가', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=51)
        self.ui.stg_pushButton_052 = self.wc.setPushbutton('분봉고가', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=52)
        self.ui.stg_pushButton_053 = self.wc.setPushbutton('분봉저가', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=53)
        self.ui.stg_pushButton_054 = self.wc.setPushbutton('최고분봉고가', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=54)
        self.ui.stg_pushButton_055 = self.wc.setPushbutton('최저분봉저가', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=55)

        self.ui.stg_pushButton_056 = self.wc.setPushbutton('분당매수수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=56)
        self.ui.stg_pushButton_057 = self.wc.setPushbutton('분당매도수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=57)
        self.ui.stg_pushButton_058 = self.wc.setPushbutton('최고분당매수수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=58)
        self.ui.stg_pushButton_059 = self.wc.setPushbutton('최고분당매도수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=59)
        self.ui.stg_pushButton_060 = self.wc.setPushbutton('누적분당매수수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=60)

        self.ui.stg_pushButton_061 = self.wc.setPushbutton('누적분당매도수량', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=61)
        self.ui.stg_pushButton_062 = self.wc.setPushbutton('분당거래대금', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=62)
        self.ui.stg_pushButton_063 = self.wc.setPushbutton('분당거래대금평균', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=63)
        self.ui.stg_pushButton_064 = self.wc.setPushbutton('분당매수금액', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=64)
        self.ui.stg_pushButton_065 = self.wc.setPushbutton('분당매도금액', parent=self.ui.dialog_strategy, color=9, animated=True, click=self.ui.StrategyButtonClicked, cmd=65)

        self.ui.stg_pushButton_066 = self.wc.setPushbutton('국내주식 팩터', parent=self.ui.dialog_strategy, color=2, animated=True, click=self.ui.StrategyButtonClicked, cmd=66)
        self.ui.stg_pushButton_067 = self.wc.setPushbutton('VI가격', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=67)
        self.ui.stg_pushButton_068 = self.wc.setPushbutton('VI호가단위', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=68)
        self.ui.stg_pushButton_069 = self.wc.setPushbutton('거래대금증감', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=69)
        self.ui.stg_pushButton_070 = self.wc.setPushbutton('전일비', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=70)

        self.ui.stg_pushButton_071 = self.wc.setPushbutton('전일비각도', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=71)
        self.ui.stg_pushButton_072 = self.wc.setPushbutton('회전율', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=72)
        self.ui.stg_pushButton_073 = self.wc.setPushbutton('전일동시간비', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=73)
        self.ui.stg_pushButton_074 = self.wc.setPushbutton('라운드피겨위5호가이내', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=74)
        self.ui.stg_pushButton_075 = self.wc.setPushbutton('시가총액', parent=self.ui.dialog_strategy, color=10, animated=True, click=self.ui.StrategyButtonClicked, cmd=75)

        self.ui.stg_pushButton_076 = self.wc.setPushbutton('매도 전용 팩터', parent=self.ui.dialog_strategy, color=2, animated=True, click=self.ui.StrategyButtonClicked, cmd=76)
        self.ui.stg_pushButton_077 = self.wc.setPushbutton('수익금', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=77)
        self.ui.stg_pushButton_078 = self.wc.setPushbutton('수익률', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=78)
        self.ui.stg_pushButton_079 = self.wc.setPushbutton('매수가', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=79)
        self.ui.stg_pushButton_080 = self.wc.setPushbutton('보유수량', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=80)

        self.ui.stg_pushButton_081 = self.wc.setPushbutton('분할매수횟수', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=81)
        self.ui.stg_pushButton_082 = self.wc.setPushbutton('분할매도횟수', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=82)
        self.ui.stg_pushButton_083 = self.wc.setPushbutton('보유시간', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=83)
        self.ui.stg_pushButton_084 = self.wc.setPushbutton('최고수익률', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=84)
        self.ui.stg_pushButton_085 = self.wc.setPushbutton('최저수익률', parent=self.ui.dialog_strategy, color=11, animated=True, click=self.ui.StrategyButtonClicked, cmd=85)

        self.ui.stg_pushButton_086 = self.wc.setPushbutton('1분봉 보조지표', parent=self.ui.dialog_strategy, color=2, animated=True, click=self.ui.StrategyButtonClicked, cmd=86)
        self.ui.stg_pushButton_087 = self.wc.setPushbutton('AD', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=87)
        self.ui.stg_pushButton_088 = self.wc.setPushbutton('ADOSC', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=88)
        self.ui.stg_pushButton_089 = self.wc.setPushbutton('ADXR', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=89)
        self.ui.stg_pushButton_090 = self.wc.setPushbutton('APO', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=90)

        self.ui.stg_pushButton_091 = self.wc.setPushbutton('AROOND', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=91)
        self.ui.stg_pushButton_092 = self.wc.setPushbutton('AROONU', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=92)
        self.ui.stg_pushButton_093 = self.wc.setPushbutton('ATR', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=93)
        self.ui.stg_pushButton_094 = self.wc.setPushbutton('BBU', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=94)
        self.ui.stg_pushButton_095 = self.wc.setPushbutton('BBM', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=95)

        self.ui.stg_pushButton_096 = self.wc.setPushbutton('BBL', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=96)
        self.ui.stg_pushButton_097 = self.wc.setPushbutton('CCI', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=97)
        self.ui.stg_pushButton_098 = self.wc.setPushbutton('DIM', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=98)
        self.ui.stg_pushButton_099 = self.wc.setPushbutton('DIP', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=99)
        self.ui.stg_pushButton_100 = self.wc.setPushbutton('MACD', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=100)

        self.ui.stg_pushButton_101 = self.wc.setPushbutton('MACDS', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=101)
        self.ui.stg_pushButton_102 = self.wc.setPushbutton('MACDH', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=102)
        self.ui.stg_pushButton_103 = self.wc.setPushbutton('MFI', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=103)
        self.ui.stg_pushButton_104 = self.wc.setPushbutton('MOM', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=104)
        self.ui.stg_pushButton_105 = self.wc.setPushbutton('OBV', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=105)

        self.ui.stg_pushButton_106 = self.wc.setPushbutton('PPO', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=106)
        self.ui.stg_pushButton_107 = self.wc.setPushbutton('ROC', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=107)
        self.ui.stg_pushButton_108 = self.wc.setPushbutton('RSI', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=108)
        self.ui.stg_pushButton_109 = self.wc.setPushbutton('SAR', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=109)
        self.ui.stg_pushButton_110 = self.wc.setPushbutton('STOCHSK', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=110)

        self.ui.stg_pushButton_111 = self.wc.setPushbutton('STOCHSD', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=111)
        self.ui.stg_pushButton_112 = self.wc.setPushbutton('STOCHFK', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=112)
        self.ui.stg_pushButton_113 = self.wc.setPushbutton('STOCHFD', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=113)
        self.ui.stg_pushButton_114 = self.wc.setPushbutton('WILLR', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=114)
        self.ui.stg_pushButton_115 = self.wc.setPushbutton('None', parent=self.ui.dialog_strategy, color=12, animated=True, click=self.ui.StrategyButtonClicked, cmd=115)

        self.ui.stg_pushButton_116 = self.wc.setPushbutton('매수, 매도 공용 팩터', parent=self.ui.dialog_strategy, color=2, animated=True, click=self.ui.StrategyButtonClicked, cmd=116)
        self.ui.stg_pushButton_117 = self.wc.setPushbutton('이평지지', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=117)
        self.ui.stg_pushButton_118 = self.wc.setPushbutton('이평돌파', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=118)
        self.ui.stg_pushButton_119 = self.wc.setPushbutton('이평이탈', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=119)
        self.ui.stg_pushButton_120 = self.wc.setPushbutton('시가지지', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=120)

        self.ui.stg_pushButton_121 = self.wc.setPushbutton('시가돌파', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=121)
        self.ui.stg_pushButton_122 = self.wc.setPushbutton('시가이탈', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=122)
        self.ui.stg_pushButton_123 = self.wc.setPushbutton('변동성', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=123)
        self.ui.stg_pushButton_124 = self.wc.setPushbutton('변동성급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=124)
        self.ui.stg_pushButton_125 = self.wc.setPushbutton('변동성급감', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=125)

        self.ui.stg_pushButton_126 = self.wc.setPushbutton('구간저가대비현재가등락율', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=126)
        self.ui.stg_pushButton_127 = self.wc.setPushbutton('구간고가대비현재가등락율', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=127)
        self.ui.stg_pushButton_128 = self.wc.setPushbutton('거래대금평균대비비율', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=128)
        self.ui.stg_pushButton_129 = self.wc.setPushbutton('체결강도평균대비비율', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=129)
        self.ui.stg_pushButton_130 = self.wc.setPushbutton('구간호가총잔량비율', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=130)

        self.ui.stg_pushButton_131 = self.wc.setPushbutton('매수수량변동성', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=131)
        self.ui.stg_pushButton_132 = self.wc.setPushbutton('매도수량변동성', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=132)
        self.ui.stg_pushButton_133 = self.wc.setPushbutton('고가미갱신지속틱수', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=133)
        self.ui.stg_pushButton_134 = self.wc.setPushbutton('저가미갱신지속틱수', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=134)
        self.ui.stg_pushButton_135 = self.wc.setPushbutton('횡보감지', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=135)

        self.ui.stg_pushButton_136 = self.wc.setPushbutton('연속상승', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=136)
        self.ui.stg_pushButton_137 = self.wc.setPushbutton('가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=137)
        self.ui.stg_pushButton_138 = self.wc.setPushbutton('거래대금급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=138)
        self.ui.stg_pushButton_139 = self.wc.setPushbutton('매수수량급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=139)
        self.ui.stg_pushButton_140 = self.wc.setPushbutton('매도수량급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=140)

        self.ui.stg_pushButton_141 = self.wc.setPushbutton('연속하락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=141)
        self.ui.stg_pushButton_142 = self.wc.setPushbutton('가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=142)
        self.ui.stg_pushButton_143 = self.wc.setPushbutton('거래대금급감', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=143)
        self.ui.stg_pushButton_144 = self.wc.setPushbutton('매수수량급감', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=144)
        self.ui.stg_pushButton_145 = self.wc.setPushbutton('매도수량급감', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=145)

        self.ui.stg_pushButton_146 = self.wc.setPushbutton('이평지지후이평돌파', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=146)
        self.ui.stg_pushButton_147 = self.wc.setPushbutton('체결강도급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=147)
        self.ui.stg_pushButton_148 = self.wc.setPushbutton('호가상승압력', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=148)
        self.ui.stg_pushButton_149 = self.wc.setPushbutton('횡보후가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=149)
        self.ui.stg_pushButton_150 = self.wc.setPushbutton('횡보후연속상승', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=150)

        self.ui.stg_pushButton_151 = self.wc.setPushbutton('이평지지후이평이탈', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=151)
        self.ui.stg_pushButton_152 = self.wc.setPushbutton('체결강도급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=152)
        self.ui.stg_pushButton_153 = self.wc.setPushbutton('호가하락압력', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=153)
        self.ui.stg_pushButton_154 = self.wc.setPushbutton('횡보후가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=154)
        self.ui.stg_pushButton_155 = self.wc.setPushbutton('횡보후연속하락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=155)

        self.ui.stg_pushButton_156 = self.wc.setPushbutton('연속상승및가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=156)
        self.ui.stg_pushButton_157 = self.wc.setPushbutton('거래대금급증및구간최고가갱신', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=157)
        self.ui.stg_pushButton_158 = self.wc.setPushbutton('거래대금급증및가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=158)
        self.ui.stg_pushButton_159 = self.wc.setPushbutton('거래대금급증및연속상승', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=159)
        self.ui.stg_pushButton_160 = self.wc.setPushbutton('호가상승압력및매수수량급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=160)

        self.ui.stg_pushButton_161 = self.wc.setPushbutton('연속하락및가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=161)
        self.ui.stg_pushButton_162 = self.wc.setPushbutton('거래대금급감후구간최저가갱신', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=162)
        self.ui.stg_pushButton_163 = self.wc.setPushbutton('거래대금급감및가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=163)
        self.ui.stg_pushButton_164 = self.wc.setPushbutton('거래대금급감및연속하락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=164)
        self.ui.stg_pushButton_165 = self.wc.setPushbutton('호가하락압력및매도수량급증', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=165)

        self.ui.stg_pushButton_166 = self.wc.setPushbutton('체결강도급등및호가상승압력', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=166)
        self.ui.stg_pushButton_167 = self.wc.setPushbutton('매수수량급증및가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=167)
        self.ui.stg_pushButton_168 = self.wc.setPushbutton('시가근접황보후시가돌파', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=168)
        self.ui.stg_pushButton_169 = self.wc.setPushbutton('저가갱신후가격급등', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=169)
        self.ui.stg_pushButton_170 = self.wc.setPushbutton('변동성급증및구간최고가갱신', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=170)

        self.ui.stg_pushButton_171 = self.wc.setPushbutton('체결강도급락및호가하락압력', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=171)
        self.ui.stg_pushButton_172 = self.wc.setPushbutton('매도수량급증후가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=172)
        self.ui.stg_pushButton_173 = self.wc.setPushbutton('시가근접황보후시가이탈', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=173)
        self.ui.stg_pushButton_174 = self.wc.setPushbutton('고가갱신후가격급락', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=174)
        self.ui.stg_pushButton_175 = self.wc.setPushbutton('변동성급감및구간최저가갱신', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=175)

        self.ui.stg_pushButton_176 = self.wc.setPushbutton('호가갭발생', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=176)
        self.ui.stg_pushButton_177 = self.wc.setPushbutton('횡보상태장기보유', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=177)
        self.ui.stg_pushButton_178 = self.wc.setPushbutton('변동성급증_역추세매도', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=178)
        self.ui.stg_pushButton_179 = self.wc.setPushbutton('장기보유종목_동적익절청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=179)
        self.ui.stg_pushButton_180 = self.wc.setPushbutton('거래대금비율기반_동적청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=180)

        self.ui.stg_pushButton_181 = self.wc.setPushbutton('호가압력기반_동적청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=181)
        self.ui.stg_pushButton_182 = self.wc.setPushbutton('이평기반_동적청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=182)
        self.ui.stg_pushButton_183 = self.wc.setPushbutton('변동성기반_동적청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=183)
        self.ui.stg_pushButton_184 = self.wc.setPushbutton('변동성급증기반_동적청산', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=184)
        self.ui.stg_pushButton_185 = self.wc.setPushbutton('고점저점기준등락율각도', parent=self.ui.dialog_strategy, color=13, animated=True, click=self.ui.StrategyButtonClicked, cmd=185)

        self.ui.stg_pushButton_186 = self.wc.setPushbutton('시장미시구조분석', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=186)
        self.ui.stg_pushButton_187 = self.wc.setPushbutton('시장리스크분석', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=187)
        self.ui.stg_pushButton_188 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=188)
        self.ui.stg_pushButton_189 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=189)
        self.ui.stg_pushButton_190 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=190)

        self.ui.stg_pushButton_191 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=191)
        self.ui.stg_pushButton_192 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=192)
        self.ui.stg_pushButton_193 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=193)
        self.ui.stg_pushButton_194 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=194)
        self.ui.stg_pushButton_195 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=195)

        self.ui.stg_pushButton_196 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=196)
        self.ui.stg_pushButton_197 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=197)
        self.ui.stg_pushButton_198 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=198)
        self.ui.stg_pushButton_199 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=199)
        self.ui.stg_pushButton_200 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=200)

        self.ui.stg_pushButton_201 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=201)
        self.ui.stg_pushButton_202 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=202)
        self.ui.stg_pushButton_203 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=203)
        self.ui.stg_pushButton_204 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=204)
        self.ui.stg_pushButton_205 = self.wc.setPushbutton('사용자버튼설정', parent=self.ui.dialog_strategy, color=14, animated=True, click=self.ui.StrategyButtonClicked, cmd=205)

        self.ui.dialog_strategy.resize(1050, 1365)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_strategy.move(self.ui.dict_set['창위치'][20], self.ui.dict_set['창위치'][21])
            except:
                pass
        self.ui.dialog_strategy.resizeEvent = self.resize_dialog_strategy
        self.ui.button_index_list = [x for x in range(116, 206)]
        self.ui.button_index_list = self.ui.button_index_list + [x for x in range(1, 116)]
        for i, button_num in enumerate(self.ui.button_index_list):
            button_name = f'stg_pushButton_{button_num:03d}'
            button = getattr(self.ui, button_name)
            row = i // 5
            col = i % 5
            x = 5 + col * 209
            y = 5 + row * 33
            button.setGeometry(x, y, 204, 28)

        self.ui.dialog_stg_input1 = self.wc.setDialog('사용자 버튼 설정', self.ui.dialog_strategy)
        self.ui.dialog_stg_input1.geometry().center()

        self.ui.stginput_labelllll1 = QLabel(' ▣ 버튼의 이름과 전략조건을 입력하십시오.                            삭제하기 버튼을 누르면 아래의 원래 버튼으로 복구됩니다.', self.ui.dialog_stg_input1)
        self.ui.stginput_lineeditt1 = self.wc.setLineedit(self.ui.dialog_stg_input1, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_lineeditt2 = self.wc.setLineedit(self.ui.dialog_stg_input1, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_textEditt1 = self.wc.setTextEdit(self.ui.dialog_stg_input1, filter_=True, font=qfont14)
        self.ui.stginput_pushBtn011 = self.wc.setPushbutton('삭제하기', parent=self.ui.dialog_stg_input1, animated=True, click=self.ui.StrategyCustomBottunDel)
        self.ui.stginput_pushBtn012 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_stg_input1, animated=True, click=self.ui.StrategyCustomBottunSave)

        self.ui.dialog_stg_input2 = self.wc.setDialog('사용자 버튼 설정', self.ui)
        self.ui.dialog_stg_input2.geometry().center()

        self.ui.stginput_labelllll2 = QLabel(' ▣ 버튼의 이름과 전략조건을 입력하십시오.                            삭제하기 버튼을 누르면 아래의 원래 버튼으로 복구됩니다.', self.ui.dialog_stg_input2)
        self.ui.stginput_lineeditt3 = self.wc.setLineedit(self.ui.dialog_stg_input2, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_lineeditt4 = self.wc.setLineedit(self.ui.dialog_stg_input2, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_textEditt2 = self.wc.setTextEdit(self.ui.dialog_stg_input2, filter_=True, font=qfont14)
        self.ui.stginput_pushBtn021 = self.wc.setPushbutton('삭제하기', parent=self.ui.dialog_stg_input2, animated=True, click=self.ui.StrategyCustomBottunDel)
        self.ui.stginput_pushBtn022 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_stg_input2, animated=True, click=self.ui.StrategyCustomBottunSave)

        self.ui.dialog_stg_input1.setFixedSize(600, 218)
        self.ui.stginput_labelllll1.setGeometry(5, 7, 590, 30)
        self.ui.stginput_lineeditt1.setGeometry(5, 40, 292, 30)
        self.ui.stginput_lineeditt2.setGeometry(302, 40, 293, 30)
        self.ui.stginput_textEditt1.setGeometry(5, 75, 590, 100)
        self.ui.stginput_pushBtn011.setGeometry(5, 180, 292, 30)
        self.ui.stginput_pushBtn012.setGeometry(302, 180, 293, 30)

        self.ui.dialog_stg_input2.setFixedSize(600, 218)
        self.ui.stginput_labelllll2.setGeometry(5, 7, 590, 30)
        self.ui.stginput_lineeditt3.setGeometry(5, 40, 292, 30)
        self.ui.stginput_lineeditt4.setGeometry(302, 40, 293, 30)
        self.ui.stginput_textEditt2.setGeometry(5, 75, 590, 100)
        self.ui.stginput_pushBtn021.setGeometry(5, 180, 292, 30)
        self.ui.stginput_pushBtn022.setGeometry(302, 180, 293, 30)

    # noinspection PyUnusedLocal
    def resize_dialog_strategy(self, event):
        dialog_width = self.ui.dialog_strategy.width()
        dialog_height = self.ui.dialog_strategy.height()
        margin_x = 5
        margin_y = 5
        min_button_width = 100
        max_button_width = 1000
        min_button_height = 10
        max_button_height = 100
        available_width = dialog_width - (margin_x * 2) + 5
        available_height = dialog_height - (margin_y * 2) + 5
        button_width = max(min_button_width, min(max_button_width, available_width // 5) - 5)
        button_height = max(min_button_height, min(max_button_height, available_height // 40) - 5)
        for i, button_num in enumerate(self.ui.button_index_list):
            button_name = f'stg_pushButton_{button_num:03d}'
            button = getattr(self.ui, button_name)
            row = i // 5
            col = i % 5
            x = margin_x + col * (button_width + 5)
            y = margin_y + row * (button_height + 5)
            button.setGeometry(x, y, button_width, button_height)
