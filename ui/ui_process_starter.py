
from utility.static import now, summer_time, now_utc, now_cme, str_ymdhms_ios, str_hms, error_decorator


@error_decorator
def process_starter(ui):
    inthms = int(str_hms())

    if not ui.backtest_engine and ui.dict_set['스톰라이브'] and ui.live_recv.isRunning():
        if ui.dict_set['주식트레이더'] and '키움증권' in ui.dict_set['증권사'] and \
           ((ui.int_time < 93100 <= inthms) or (ui.int_time < 152000 <= inthms)):
            ui.StomliveScreenshot('주식')
        elif ui.dict_set['주식트레이더'] and '해외선물' in ui.dict_set['증권사'] and \
                ((ui.int_time < 50000 <= inthms and summer_time != 0) or (ui.int_time < 60000 <= inthms)):
            ui.StomliveScreenshot('해선')
        elif ui.dict_set['코인트레이더'] and ui.int_time < 235000 <= inthms:
            ui.StomliveScreenshot('코인')

    if ui.dict_set['백테스케쥴실행'] and not ui.backtest_engine and now().weekday() == ui.dict_set['백테스케쥴요일']:
        if ui.int_time < ui.dict_set['백테스케쥴시간'] <= inthms:
            ui.AutoBackSchedule(1)

    if ui.auto_run > 0:
        login_num = ui.auto_run
        ui.auto_run = 0
        ui.mnButtonClicked_03(login=login_num)

    UpdateWindowTitle(ui)
    ui.int_time = inthms


@error_decorator
def UpdateWindowTitle(ui):
    text = 'STOM'
    if ui.dict_set['주식트레이더']:
        data_type = '1초스냅샷' if ui.dict_set['주식타임프레임'] else '1분봉'
        if '키움증권' in ui.dict_set['증권사']:
            text = f'{text} | 키움증권 | {data_type}'
        else:
            text = f'{text} | 해외선물 | {data_type}'
    elif ui.dict_set['코인트레이더']:
        data_type = '1초스냅샷' if ui.dict_set['코인타임프레임'] else '1분봉'
        if ui.dict_set['거래소'] == '바이낸스선물':
            text = f'{text} | 바이낸스선물 | {data_type}'
        else:
            text = f'{text} | 업비트 | {data_type}'
    if ui.showQsize:
        beqsize = sum((stq.qsize() for stq in ui.back_eques)) if ui.back_eques else 0
        bstqsize = sum((ctq.qsize() for ctq in ui.back_sques)) if ui.back_sques else 0
        text = f'{text} | sagentQ[{ui.saqsize}] | straderQ[{ui.stqsize}] | sstrateyQ[{ui.ssqsize}] | ' \
               f'creceivQ[{ui.creceivQ.qsize()}] | ctraderQ[{ui.ctraderQ.qsize()}] | cstrateyQ[{ui.cstgQ.qsize()}] | ' \
               f'windowQ[{ui.windowQ.qsize()}] | queryQ[{ui.queryQ.qsize()}] | chartQ[{ui.chartQ.qsize()}] | ' \
               f'hogaQ[{ui.hogaQ.qsize()}] | soundQ[{ui.soundQ.qsize()}] | backegQ[{beqsize}] | backstQ[{bstqsize}] | ' \
               f'backttQ[{ui.totalQ.qsize()}]'
    else:
        if ui.dict_set['주식트레이더']:
            text = f'{text} | 모의' if ui.dict_set['주식모의투자'] else f'{text} | 실전'
            text = f'{text} | {ui.dict_set["주식매수전략"] if ui.dict_set["주식매수전략"] != "" else "전략사용안함"}'
        elif ui.dict_set['코인트레이더']:
            text = f'{text} | 모의' if ui.dict_set['코인모의투자'] else f'{text} | 실전'
            text = f'{text} | {ui.dict_set["코인매수전략"] if ui.dict_set["코인매수전략"] != "" else "전략사용안함"}'
        if ui.dict_set['거래소'] == '바이낸스선물' and ui.dict_set['코인트레이더']:
            text = f"{text} | {str_ymdhms_ios(now_utc())}"
        elif '해외선물' in ui.dict_set['증권사'] and ui.dict_set['주식트레이더']:
            text = f"{text} | {str_ymdhms_ios(now_cme())}"
        else:
            text = f"{text} | {str_ymdhms_ios()}"
    ui.setWindowTitle(text)
