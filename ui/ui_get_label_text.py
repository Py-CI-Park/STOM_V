
from utility.setting import list_stock_tick_c, list_stock_min_c, list_coin_min_c, list_coin_min_cf, list_coin_tick_c, \
    list_coin_tick_cf, list_stock_min, list_coin_min, list_stock_tick, list_coin_tick


def get_label_text(real, gubun, code, is_min, arry, xpoint, factor, hms):
    def fi(fname):
        if real:
            if is_min:
                if gubun == 'S':    return list_stock_min.index(fname)
                else:               return list_coin_min.index(fname)
            else:
                if gubun == 'S':    return list_stock_tick.index(fname)
                else:               return list_coin_tick.index(fname)
        else:
            if is_min:
                if gubun == 'S':    return list_stock_min_c.index(fname)
                elif 'KRW' in code: return list_coin_min_c.index(fname)
                else:               return list_coin_min_cf.index(fname)
            else:
                if gubun == 'S':    return list_stock_tick_c.index(fname)
                elif 'KRW' in code: return list_coin_tick_c.index(fname)
                else:               return list_coin_tick_cf.index(fname)

    if factor == '현재가':
        if gubun == 'S':
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {arry[xpoint, fi('이동평균5')]:,.3f}\n" \
                       f"이평010 {arry[xpoint, fi('이동평균10')]:,.3f}\n" \
                       f"이평020 {arry[xpoint, fi('이동평균20')]:,.3f}\n" \
                       f"이평060 {arry[xpoint, fi('이동평균60')]:,.3f}\n" \
                       f"이평120 {arry[xpoint, fi('이동평균120')]:,.3f}\n" \
                       f"분봉시가 {arry[xpoint, fi('분봉시가')]:,.0f}\n" \
                       f"분봉고가 {arry[xpoint, fi('분봉고가')]:,.0f}\n" \
                       f"분봉저가 {arry[xpoint, fi('분봉저가')]:,.0f}\n" \
                       f"현재가    {arry[xpoint, fi('현재가')]:,.0f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {arry[xpoint, fi('이동평균60')]:,.3f}\n" \
                       f"이평0150 {arry[xpoint, fi('이동평균150')]:,.3f}\n" \
                       f"이평0300 {arry[xpoint, fi('이동평균300')]:,.3f}\n" \
                       f"이평0600 {arry[xpoint, fi('이동평균600')]:,.3f}\n" \
                       f"이평1200 {arry[xpoint, fi('이동평균1200')]:,.3f}\n" \
                       f"현재가       {arry[xpoint, fi('현재가')]:,.0f}"
        elif gubun == 'F':
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {arry[xpoint, fi('이동평균5')]:,.8f}\n" \
                       f"이평010 {arry[xpoint, fi('이동평균10')]:,.8f}\n" \
                       f"이평020 {arry[xpoint, fi('이동평균20')]:,.8f}\n" \
                       f"이평060 {arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평120 {arry[xpoint, fi('이동평균120')]:,.8f}\n" \
                       f"분봉시가 {arry[xpoint, fi('분봉시가')]:,.8f}\n" \
                       f"분봉고가 {arry[xpoint, fi('분봉고가')]:,.8f}\n" \
                       f"분봉저가 {arry[xpoint, fi('분봉저가')]:,.8f}\n" \
                       f"현재가    {arry[xpoint, fi('현재가')]:,.8f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평0150 {arry[xpoint, fi('이동평균150')]:,.8f}\n" \
                       f"이평0300 {arry[xpoint, fi('이동평균300')]:,.8f}\n" \
                       f"이평0600 {arry[xpoint, fi('이동평균600')]:,.8f}\n" \
                       f"이평1200 {arry[xpoint, fi('이동평균1200')]:,.8f}\n" \
                       f"현재가       {arry[xpoint, fi('현재가')]:,.8f}"
        else:
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {arry[xpoint, fi('이동평균5')]:,.8f}\n" \
                       f"이평010 {arry[xpoint, fi('이동평균10')]:,.8f}\n" \
                       f"이평020 {arry[xpoint, fi('이동평균20')]:,.8f}\n" \
                       f"이평060 {arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평120 {arry[xpoint, fi('이동평균120')]:,.8f}\n" \
                       f"분봉시가 {arry[xpoint, fi('분봉시가')]:,.4f}\n" \
                       f"분봉고가 {arry[xpoint, fi('분봉고가')]:,.4f}\n" \
                       f"분봉저가 {arry[xpoint, fi('분봉저가')]:,.4f}\n" \
                       f"현재가    {arry[xpoint, fi('현재가')]:,.4f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평0150 {arry[xpoint, fi('이동평균150')]:,.8f}\n" \
                       f"이평0300 {arry[xpoint, fi('이동평균300')]:,.8f}\n" \
                       f"이평0600 {arry[xpoint, fi('이동평균600')]:,.8f}\n" \
                       f"이평1200 {arry[xpoint, fi('이동평균1200')]:,.8f}\n" \
                       f"현재가       {arry[xpoint, fi('현재가')]:,.4f}"
    elif factor == '체결강도':
        text =     f"체결강도        {arry[xpoint, fi('체결강도')]:,.2f}\n" \
                   f"체결강도평균 {arry[xpoint, fi('체결강도평균')]:,.2f}\n" \
                   f"최고체결강도 {arry[xpoint, fi('최고체결강도')]:,.2f}\n" \
                   f"최저체결강도 {arry[xpoint, fi('최저체결강도')]:,.2f}"
    elif factor == '초당거래대금':
        text =     f"초당거래대금        {arry[xpoint, fi('초당거래대금')]:,.0f}\n" \
                   f"초당거래대금평균 {arry[xpoint, fi('초당거래대금평균')]:,.0f}"
    elif factor == '분당거래대금':
        text =     f"분당거래대금        {arry[xpoint, fi('분당거래대금')]:,.0f}\n" \
                   f"분당거래대금평균 {arry[xpoint, fi('분당거래대금평균')]:,.0f}"
    elif factor == '초당체결수량':
        if gubun in ('S', 'F'):
            text = f"초당매수수량 {arry[xpoint, fi('초당매수수량')]:,.0f}\n" \
                   f"초당매도수량 {arry[xpoint, fi('초당매도수량')]:,.0f}"
        else:
            text = f"초당매수수량 {arry[xpoint, fi('초당매수수량')]:,.8f}\n" \
                   f"초당매도수량 {arry[xpoint, fi('초당매도수량')]:,.8f}"
    elif factor == '분당체결수량':
        if gubun in ('S', 'F'):
            text = f"분당매수수량 {arry[xpoint, fi('분당매수수량')]:,.0f}\n" \
                   f"분당매도수량 {arry[xpoint, fi('분당매도수량')]:,.0f}"
        else:
            text = f"분당매수수량 {arry[xpoint, fi('분당매수수량')]:,.8f}\n" \
                   f"분당매도수량 {arry[xpoint, fi('분당매도수량')]:,.8f}"
    elif factor == '호가총잔량':
        if gubun in ('S', 'F'):
            text = f"매도총잔량 {arry[xpoint, fi('매도총잔량')]:,.0f}\n" \
                   f"매수총잔량 {arry[xpoint, fi('매수총잔량')]:,.0f}"
        else:
            text = f"매도총잔량 {arry[xpoint, fi('매도총잔량')]:,.8f}\n" \
                   f"매수총잔량 {arry[xpoint, fi('매수총잔량')]:,.8f}"
    elif factor == '매도수호가잔량1':
        if gubun in ('S', 'F'):
            text = f"매도1잔량 {arry[xpoint, fi('매도잔량1')]:,.0f}\n" \
                   f"매수1잔량 {arry[xpoint, fi('매수잔량1')]:,.0f}"
        else:
            text = f"매도1잔량 {arry[xpoint, fi('매도잔량1')]:,.8f}\n" \
                   f"매수1잔량 {arry[xpoint, fi('매수잔량1')]:,.8f}"
    elif factor == '매도수5호가잔량합':
        if gubun in ('S', 'F'):
            text = f"매도수5호가잔량합 {arry[xpoint, fi('매도수5호가잔량합')]:,.0f}"
        else:
            text = f"매도수5호가잔량합 {arry[xpoint, fi('매도수5호가잔량합')]:,.8f}"
    elif factor == '누적초당매도수수량':
        if gubun in ('S', 'F'):
            text = f"누적초당매수수량 {arry[xpoint, fi('누적초당매수수량')]:,.0f}\n" \
                   f"누적초당매도수량 {arry[xpoint, fi('누적초당매도수량')]:,.0f}"
        else:
            text = f"누적초당매수수량 {arry[xpoint, fi('누적초당매수수량')]:,.8f}\n" \
                   f"누적초당매도수량 {arry[xpoint, fi('누적초당매도수량')]:,.8f}"
    elif factor == '누적분당매도수수량':
        if gubun in ('S', 'F'):
            text = f"누적분당매수수량 {arry[xpoint, fi('누적분당매수수량')]:,.0f}\n" \
                   f"누적분당매도수량 {arry[xpoint, fi('누적분당매도수량')]:,.0f}"
        else:
            text = f"누적분당매수수량 {arry[xpoint, fi('누적분당매수수량')]:,.8f}\n" \
                   f"누적분당매도수량 {arry[xpoint, fi('누적분당매도수량')]:,.8f}"
    elif factor == 'AROON':
        text =     f"AROOND {arry[xpoint, fi('AROOND')]:,.2f}\n" \
                   f"AROONU {arry[xpoint, fi('AROONU')]:,.2f}"
    elif factor == 'BBAND':
        text =     f"BBU {arry[xpoint, fi('BBU')]:,.2f}\n" \
                   f"BBM {arry[xpoint, fi('BBM')]:,.2f}\n" \
                   f"BBL {arry[xpoint, fi('BBL')]:,.2f}"
    elif factor == 'MACD':
        text =     f"MACD   {arry[xpoint, fi('MACD')]:,.2f}\n" \
                   f"MACDS {arry[xpoint, fi('MACDS')]:,.2f}\n" \
                   f"MACDH {arry[xpoint, fi('MACDH')]:,.2f}"
    elif factor == 'DMI':
        text =     f"DIM {arry[xpoint, fi('DIM')]:,.2f}\n" \
                   f"DIP {arry[xpoint, fi('DIP')]:,.2f}"
    elif factor == 'STOCHS':
        text =     f"STOCHSK {arry[xpoint, fi('STOCHSK')]:,.2f}\n" \
                   f"STOCHSD {arry[xpoint, fi('STOCHSD')]:,.2f}"
    elif factor == 'STOCHF':
        text =     f"STOCHFK {arry[xpoint, fi('STOCHFK')]:,.2f}\n" \
                   f"STOCHFD {arry[xpoint, fi('STOCHFD')]:,.2f}"
    else:
        text =     f"{factor} {arry[xpoint, fi(factor)]:,.2f}"

    return text
