
from ui.etcetera.etc import auto_back_schedule
from ui.event_click.button_clicked_shortcut import mnbutton_c_clicked_03
from utility.static_method.static import now, now_utc, now_cme, str_ymdhms_ios, str_hms


def process_starter(ui):
    """프로세스 스타터를 실행합니다.
    자동 백테스트 스케줄러, 자동 실행 등을 처리합니다.
    Args:
        ui: UI 객체
    """
    inthms = int(str_hms())

    if ui.dict_set['백테스케쥴실행'] and not ui.backtest_engine and now().weekday() == ui.dict_set['백테스케쥴요일']:
        if ui.int_time < ui.dict_set['백테스케쥴시간'] <= inthms:
            auto_back_schedule(ui, 1)

    if ui.auto_run > 0:
        ui.auto_run = 0
        mnbutton_c_clicked_03(ui, True)

    _update_window_title(ui)
    ui.int_time = inthms


def _update_window_title(ui):
    """윈도우 제목을 업데이트합니다.
    Args:
        ui: UI 객체
    """
    market_text = ui.dict_set['거래소']
    data_type = '1초스냅샷' if ui.dict_set['타임프레임'] else '1분봉'
    trade_type = '모의' if ui.dict_set['모의투자'] else '실전'
    text = f'STOM | {market_text} | {data_type} | {trade_type}'

    if ui.showQsize:
        beqsize = sum((q.qsize() for q in ui.back_eques)) if ui.back_eques else 0
        bstqsize = sum((q.qsize() for q in ui.back_sques)) if ui.back_sques else 0
        stgqsize = sum((q.qsize() for q in ui.stgQs))
        text = f'{text} | receivQ[{ui.receivQ.qsize()}] | traderQ[{ui.traderQ.qsize()}] | strateyQ[{stgqsize}] | ' \
               f'windowQ[{ui.windowQ.qsize()}] | queryQ[{ui.queryQ.qsize()}] | chartQ[{ui.chartQ.qsize()}] | ' \
               f'hogaQ[{ui.hogaQ.qsize()}] | soundQ[{ui.soundQ.qsize()}] | backegQ[{beqsize}] | backstQ[{bstqsize}] | ' \
               f'backttQ[{ui.totalQ.qsize()}]'
    else:
        text = f"{text} | {ui.dict_set['매수전략'] if ui.dict_set['매수전략'] != '' else '전략사용안함'}"
        if ui.market_gubun in (5, 9):
            text = f"{text} | {str_ymdhms_ios(now_utc())}"
        elif ui.market_gubun in (4, 8):
            text = f"{text} | {str_ymdhms_ios(now_cme())}"
        else:
            text = f"{text} | {str_ymdhms_ios()}"

    ui.setWindowTitle(text)
