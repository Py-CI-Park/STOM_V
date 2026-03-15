
def get_label_text(ui, real, gubun, code, is_min, xpoint, factor, hms):
    def fi(fname):
        if real:
            if is_min:
                if gubun == 'S':    return ui.dict_findex_stock_min[fname]
                else:               return ui.dict_findex_coin_min[fname]
            else:
                if gubun == 'S':    return ui.dict_findex_stock_tick[fname]
                else:               return ui.dict_findex_coin_tick[fname]
        else:
            if is_min:
                if gubun == 'S':    return ui.dict_findex_stock_min2[fname]
                elif 'KRW' in code: return ui.dict_findex_coin_min2[fname]
                else:               return ui.dict_findex_future_min2[fname]
            else:
                if gubun == 'S':    return ui.dict_findex_stock_tick2[fname]
                elif 'KRW' in code: return ui.dict_findex_coin_tick2[fname]
                else:               return ui.dict_findex_future_tick2[fname]

    if factor == '현재가':
        if gubun == 'S':
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {ui.ctpg_arry[xpoint, fi('이동평균5')]:,.3f}\n" \
                       f"이평010 {ui.ctpg_arry[xpoint, fi('이동평균10')]:,.3f}\n" \
                       f"이평020 {ui.ctpg_arry[xpoint, fi('이동평균20')]:,.3f}\n" \
                       f"이평060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.3f}\n" \
                       f"이평120 {ui.ctpg_arry[xpoint, fi('이동평균120')]:,.3f}\n" \
                       f"분봉시가 {ui.ctpg_arry[xpoint, fi('분봉시가')]:,.0f}\n" \
                       f"분봉고가 {ui.ctpg_arry[xpoint, fi('분봉고가')]:,.0f}\n" \
                       f"분봉저가 {ui.ctpg_arry[xpoint, fi('분봉저가')]:,.0f}\n" \
                       f"현재가 {ui.ctpg_arry[xpoint, fi('현재가')]:,.0f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.3f}\n" \
                       f"이평0150 {ui.ctpg_arry[xpoint, fi('이동평균150')]:,.3f}\n" \
                       f"이평0300 {ui.ctpg_arry[xpoint, fi('이동평균300')]:,.3f}\n" \
                       f"이평0600 {ui.ctpg_arry[xpoint, fi('이동평균600')]:,.3f}\n" \
                       f"이평1200 {ui.ctpg_arry[xpoint, fi('이동평균1200')]:,.3f}\n" \
                       f"현재가       {ui.ctpg_arry[xpoint, fi('현재가')]:,.0f}"
        elif gubun == 'F':
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {ui.ctpg_arry[xpoint, fi('이동평균5')]:,.5f}\n" \
                       f"이평010 {ui.ctpg_arry[xpoint, fi('이동평균10')]:,.5f}\n" \
                       f"이평020 {ui.ctpg_arry[xpoint, fi('이동평균20')]:,.5f}\n" \
                       f"이평060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.5f}\n" \
                       f"이평120 {ui.ctpg_arry[xpoint, fi('이동평균120')]:,.5f}\n" \
                       f"분봉시가 {ui.ctpg_arry[xpoint, fi('분봉시가')]:,.2f}\n" \
                       f"분봉고가 {ui.ctpg_arry[xpoint, fi('분봉고가')]:,.2f}\n" \
                       f"분봉저가 {ui.ctpg_arry[xpoint, fi('분봉저가')]:,.2f}\n" \
                       f"현재가    {ui.ctpg_arry[xpoint, fi('현재가')]:,.2f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.5f}\n" \
                       f"이평0150 {ui.ctpg_arry[xpoint, fi('이동평균150')]:,.5f}\n" \
                       f"이평0300 {ui.ctpg_arry[xpoint, fi('이동평균300')]:,.5f}\n" \
                       f"이평0600 {ui.ctpg_arry[xpoint, fi('이동평균600')]:,.5f}\n" \
                       f"이평1200 {ui.ctpg_arry[xpoint, fi('이동평균1200')]:,.5f}\n" \
                       f"현재가       {ui.ctpg_arry[xpoint, fi('현재가')]:,.2f}"
        else:
            if is_min:
                text = f"시간 {hms}\n" \
                       f"이평005 {ui.ctpg_arry[xpoint, fi('이동평균5')]:,.8f}\n" \
                       f"이평010 {ui.ctpg_arry[xpoint, fi('이동평균10')]:,.8f}\n" \
                       f"이평020 {ui.ctpg_arry[xpoint, fi('이동평균20')]:,.8f}\n" \
                       f"이평060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평120 {ui.ctpg_arry[xpoint, fi('이동평균120')]:,.8f}\n" \
                       f"분봉시가 {ui.ctpg_arry[xpoint, fi('분봉시가')]:,.4f}\n" \
                       f"분봉고가 {ui.ctpg_arry[xpoint, fi('분봉고가')]:,.4f}\n" \
                       f"분봉저가 {ui.ctpg_arry[xpoint, fi('분봉저가')]:,.4f}\n" \
                       f"현재가    {ui.ctpg_arry[xpoint, fi('현재가')]:,.4f}"
            else:
                text = f"시간 {hms}\n" \
                       f"이평0060 {ui.ctpg_arry[xpoint, fi('이동평균60')]:,.8f}\n" \
                       f"이평0150 {ui.ctpg_arry[xpoint, fi('이동평균150')]:,.8f}\n" \
                       f"이평0300 {ui.ctpg_arry[xpoint, fi('이동평균300')]:,.8f}\n" \
                       f"이평0600 {ui.ctpg_arry[xpoint, fi('이동평균600')]:,.8f}\n" \
                       f"이평1200 {ui.ctpg_arry[xpoint, fi('이동평균1200')]:,.8f}\n" \
                       f"현재가       {ui.ctpg_arry[xpoint, fi('현재가')]:,.4f}"
    elif factor == '초당거래대금':
        text =     f"시간 {hms}\n" \
                   f"초당거래대금        {ui.ctpg_arry[xpoint, fi('초당거래대금')]:,.0f}\n" \
                   f"초당거래대금평균 {ui.ctpg_arry[xpoint, fi('초당거래대금평균')]:,.0f}"
    elif factor == '초당매도수금액':
        text =     f"시간 {hms}\n" \
                   f"초당매수금액 {ui.ctpg_arry[xpoint, fi('초당매수금액')]:,.0f}\n" \
                   f"초당매도금액 {ui.ctpg_arry[xpoint, fi('초당매도금액')]:,.0f}"
    elif factor == '분당매도수금액':
        text =     f"시간 {hms}\n" \
                   f"분당매수금액 {ui.ctpg_arry[xpoint, fi('분당매수금액')]:,.0f}\n" \
                   f"분당매도금액 {ui.ctpg_arry[xpoint, fi('분당매도금액')]:,.0f}"
    elif factor == '당일매도수금액':
        text =     f"시간 {hms}\n" \
                   f"당일매수금액 {ui.ctpg_arry[xpoint, fi('당일매수금액')]:,.0f}\n" \
                   f"당일매도금액 {ui.ctpg_arry[xpoint, fi('당일매도금액')]:,.0f}"
    elif factor == '최고매도수금액':
        text =     f"시간 {hms}\n" \
                   f"최고매수금액 {ui.ctpg_arry[xpoint, fi('최고매수금액')]:,.0f}\n" \
                   f"최고매도금액 {ui.ctpg_arry[xpoint, fi('최고매도금액')]:,.0f}"
    elif factor == '최고매도수가격':
        if gubun == 'S':
            text = f"시간 {hms}\n" \
                   f"최고매수가격 {ui.ctpg_arry[xpoint, fi('최고매수가격')]:,.0f}\n" \
                   f"최고매도가격 {ui.ctpg_arry[xpoint, fi('최고매도가격')]:,.0f}"
        else:
            text = f"최고매수가격 {ui.ctpg_arry[xpoint, fi('최고매수가격')]:,.8f}\n" \
                   f"최고매도가격 {ui.ctpg_arry[xpoint, fi('최고매도가격')]:,.8f}"
    elif factor == '체결강도':
        text =     f"시간 {hms}\n" \
                   f"체결강도        {ui.ctpg_arry[xpoint, fi('체결강도')]:,.2f}\n" \
                   f"체결강도평균 {ui.ctpg_arry[xpoint, fi('체결강도평균')]:,.2f}\n" \
                   f"최고체결강도 {ui.ctpg_arry[xpoint, fi('최고체결강도')]:,.2f}\n" \
                   f"최저체결강도 {ui.ctpg_arry[xpoint, fi('최저체결강도')]:,.2f}"
    elif factor == '분당거래대금':
        text =     f"시간 {hms}\n" \
                   f"분당거래대금        {ui.ctpg_arry[xpoint, fi('분당거래대금')]:,.0f}\n" \
                   f"분당거래대금평균 {ui.ctpg_arry[xpoint, fi('분당거래대금평균')]:,.0f}"
    elif factor == '초당체결수량':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"초당매수수량 {ui.ctpg_arry[xpoint, fi('초당매수수량')]:,.0f}\n" \
                   f"초당매도수량 {ui.ctpg_arry[xpoint, fi('초당매도수량')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"초당매수수량 {ui.ctpg_arry[xpoint, fi('초당매수수량')]:,.8f}\n" \
                   f"초당매도수량 {ui.ctpg_arry[xpoint, fi('초당매도수량')]:,.8f}"
    elif factor == '분당체결수량':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"분당매수수량 {ui.ctpg_arry[xpoint, fi('분당매수수량')]:,.0f}\n" \
                   f"분당매도수량 {ui.ctpg_arry[xpoint, fi('분당매도수량')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"분당매수수량 {ui.ctpg_arry[xpoint, fi('분당매수수량')]:,.8f}\n" \
                   f"분당매도수량 {ui.ctpg_arry[xpoint, fi('분당매도수량')]:,.8f}"
    elif factor == '호가총잔량':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"매도총잔량 {ui.ctpg_arry[xpoint, fi('매도총잔량')]:,.0f}\n" \
                   f"매수총잔량 {ui.ctpg_arry[xpoint, fi('매수총잔량')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"매도총잔량 {ui.ctpg_arry[xpoint, fi('매도총잔량')]:,.8f}\n" \
                   f"매수총잔량 {ui.ctpg_arry[xpoint, fi('매수총잔량')]:,.8f}"
    elif factor == '매도수호가잔량1':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"매도1잔량 {ui.ctpg_arry[xpoint, fi('매도잔량1')]:,.0f}\n" \
                   f"매수1잔량 {ui.ctpg_arry[xpoint, fi('매수잔량1')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"매도1잔량 {ui.ctpg_arry[xpoint, fi('매도잔량1')]:,.8f}\n" \
                   f"매수1잔량 {ui.ctpg_arry[xpoint, fi('매수잔량1')]:,.8f}"
    elif factor == '매도수5호가잔량합':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"매도수5호가잔량합 {ui.ctpg_arry[xpoint, fi('매도수5호가잔량합')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"매도수5호가잔량합 {ui.ctpg_arry[xpoint, fi('매도수5호가잔량합')]:,.8f}"
    elif factor == '누적초당매도수수량':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"누적초당매수수량 {ui.ctpg_arry[xpoint, fi('누적초당매수수량')]:,.0f}\n" \
                   f"누적초당매도수량 {ui.ctpg_arry[xpoint, fi('누적초당매도수량')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"누적초당매수수량 {ui.ctpg_arry[xpoint, fi('누적초당매수수량')]:,.8f}\n" \
                   f"누적초당매도수량 {ui.ctpg_arry[xpoint, fi('누적초당매도수량')]:,.8f}"
    elif factor == '누적분당매도수수량':
        if gubun in ('S', 'F'):
            text = f"시간 {hms}\n" \
                   f"누적분당매수수량 {ui.ctpg_arry[xpoint, fi('누적분당매수수량')]:,.0f}\n" \
                   f"누적분당매도수량 {ui.ctpg_arry[xpoint, fi('누적분당매도수량')]:,.0f}"
        else:
            text = f"시간 {hms}\n" \
                   f"누적분당매수수량 {ui.ctpg_arry[xpoint, fi('누적분당매수수량')]:,.8f}\n" \
                   f"누적분당매도수량 {ui.ctpg_arry[xpoint, fi('누적분당매도수량')]:,.8f}"
    elif factor == 'AROON':
        text =     f"시간 {hms}\n" \
                   f"AROOND {ui.ctpg_arry[xpoint, fi('AROOND')]:,.2f}\n" \
                   f"AROONU {ui.ctpg_arry[xpoint, fi('AROONU')]:,.2f}"
    elif factor == 'BBAND':
        text =     f"시간 {hms}\n" \
                   f"BBU {ui.ctpg_arry[xpoint, fi('BBU')]:,.2f}\n" \
                   f"BBM {ui.ctpg_arry[xpoint, fi('BBM')]:,.2f}\n" \
                   f"BBL {ui.ctpg_arry[xpoint, fi('BBL')]:,.2f}"
    elif factor == 'MACD':
        text =     f"시간 {hms}\n" \
                   f"MACD   {ui.ctpg_arry[xpoint, fi('MACD')]:,.2f}\n" \
                   f"MACDS {ui.ctpg_arry[xpoint, fi('MACDS')]:,.2f}\n" \
                   f"MACDH {ui.ctpg_arry[xpoint, fi('MACDH')]:,.2f}"
    elif factor == 'DMI':
        text =     f"시간 {hms}\n" \
                   f"DIM {ui.ctpg_arry[xpoint, fi('DIM')]:,.2f}\n" \
                   f"DIP {ui.ctpg_arry[xpoint, fi('DIP')]:,.2f}"
    elif factor == 'STOCHS':
        text =     f"시간 {hms}\n" \
                   f"STOCHSK {ui.ctpg_arry[xpoint, fi('STOCHSK')]:,.2f}\n" \
                   f"STOCHSD {ui.ctpg_arry[xpoint, fi('STOCHSD')]:,.2f}"
    elif factor == 'STOCHF':
        text =     f"시간 {hms}\n" \
                   f"STOCHFK {ui.ctpg_arry[xpoint, fi('STOCHFK')]:,.2f}\n" \
                   f"STOCHFD {ui.ctpg_arry[xpoint, fi('STOCHFD')]:,.2f}"
    else:
        text =     f"시간 {hms}\n" \
                   f"{factor} {ui.ctpg_arry[xpoint, fi(factor)]:,.2f}"

    if ui.dict_fm is not None and factor in ui.dict_fm:
        for name, ftype, findex in ui.dict_fm[factor]:
            if ftype in ('선:일반', '선:조건'):
                if gubun == 'S':
                    text = f"{text}\n{name} {ui.ctpg_arry[xpoint, findex]:,.2f}"
                elif gubun == 'F':
                    text = f"{text}\n{name} {ui.ctpg_arry[xpoint, findex]:,.4f}"
                else:
                    text = f"{text}\n{name} {ui.ctpg_arry[xpoint, findex]:,.8f}"
            else:
                text = f"{text}\n{name} {'True' if ui.ctpg_arry[xpoint, findex] else 'False'}"

    return text
