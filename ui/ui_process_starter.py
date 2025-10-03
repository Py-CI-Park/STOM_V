from utility.static import int_hms, now, strf_time


def process_starter(ui):
    inthms = int_hms()

    if not ui.backtest_engine and ui.dict_set['스톰라이브'] and ui.StomLiveProcessAlive():
        if (ui.int_time < 93100 <= inthms) or (ui.int_time < 152000 <= inthms):
            if ui.dict_set['주식트레이더']:   ui.StomliveScreenshot('S스톰라이브')
            elif ui.dict_set['코인트레이더']: ui.StomliveScreenshot('C스톰라이브')

    if ui.dict_set['백테스케쥴실행'] and not ui.backtest_engine and now().weekday() == ui.dict_set['백테스케쥴요일']:
        if ui.int_time < ui.dict_set['백테스케쥴시간'] <= inthms:
            ui.AutoBackSchedule(1)

    if ui.auto_run == 1:
        ui.mnButtonClicked_03(login=1)
        ui.auto_run = 0

    if ui.auto_run == 2:
        ui.mnButtonClicked_03(login=2)
        ui.auto_run = 0

    UpdateWindowTitle(ui)
    ui.int_time = inthms


def UpdateWindowTitle(ui):
    text = 'STOM'
    if ui.dict_set['리시버공유'] == 1:
        text = f'{text} Server'
    elif ui.dict_set['리시버공유'] == 2:
        text = f'{text} Client'
    if ui.dict_set['거래소'] == '바이낸스선물' and ui.dict_set['코인트레이더']:
        text = f'{text} | 바이낸스선물'
    elif ui.dict_set['거래소'] == '업비트' and ui.dict_set['코인트레이더']:
        text = f'{text} | 업비트'
    elif ui.dict_set['증권사'] == '키움증권해외선물' and ui.dict_set['주식트레이더']:
        text = f'{text} | 키움증권해외선물'
    elif ui.dict_set['주식트레이더']:
        text = f'{text} | 키움증권'
    if ui.showQsize:
        beqsize = sum((stq.qsize() for stq in ui.back_eques)) if ui.back_eques else 0
        bstqsize = sum((ctq.qsize() for ctq in ui.back_sques)) if ui.back_sques else 0
        text = f'{text} | sreceivQ[{ui.srqsize}] | straderQ[{ui.stqsize}] | sstrateyQ[{ui.ssqsize}] | ' \
               f'creceivQ[{ui.creceivQ.qsize()}] | ctraderQ[{ui.ctraderQ.qsize()}] | cstrateyQ[{ui.cstgQ.qsize()}] | ' \
               f'windowQ[{ui.windowQ.qsize()}] | queryQ[{ui.queryQ.qsize()}] | chartQ[{ui.chartQ.qsize()}] | ' \
               f'hogaQ[{ui.hogaQ.qsize()}] | soundQ[{ui.soundQ.qsize()}] | backegQ[{beqsize}] | backstQ[{bstqsize}] | ' \
               f'backttQ[{ui.totalQ.qsize()}]'
    else:
        if ui.dict_set['코인트레이더']:
            text = f'{text} | 모의' if ui.dict_set['코인모의투자'] else f'{text} | 실전'
            text = f'{text} | {ui.dict_set["코인매수전략"] if ui.dict_set["코인매수전략"] != "" else "전략사용안함"}'
        elif ui.dict_set['주식트레이더']:
            text = f'{text} | 모의' if ui.dict_set['주식모의투자'] else f'{text} | 실전'
            text = f'{text} | {ui.dict_set["주식매수전략"] if ui.dict_set["주식매수전략"] != "" else "전략사용안함"}'
        text = f"{text} | {strf_time('%Y-%m-%d %H:%M:%S')}"
    ui.setWindowTitle(text)
