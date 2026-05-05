
def receiver_process_alive(ui):
    """수신기 프로세스 상태를 확인합니다.
    Args:
        ui: UI 객체
    Returns:
        프로세스存活 여부
    """
    return ui.proc_receiver is not None and ui.proc_receiver.is_alive()


def trader_process_alive(ui):
    """트레이더 프로세活 상태를 확인합니다.
    Args:
        ui: UI 객체
    Returns:
        프로세스存活 여부
    """
    return ui.proc_trader is not None and ui.proc_trader.is_alive()


def strategy_process_alive(ui):
    """전략 프로세스 상태를 확인합니다.
    Args:
        ui: UI 객체
    Returns:
        프로세스存活 여부
    """
    return ui.proc_strategys and ui.proc_strategys[0].is_alive()


def coinkimp_process_alive(ui):
    """코인 김치 프리미엄 프로세스 상태를 확인합니다.
    Args:
        ui: UI 객체
    Returns:
        프로세스存活 여부
    """
    return ui.proc_coin_kimp is not None and ui.proc_coin_kimp.is_alive()


def backtest_process_alive(ui):
    """백테스트 프로세스 상태를 확인합니다.
    Args:
        ui: UI 객체
    Returns:
        프로세스存活 여부
    """
    return (ui.proc_backtester_bs is not None and ui.proc_backtester_bs.is_alive()) or \
        (ui.proc_backtester_bf is not None and ui.proc_backtester_bf.is_alive()) or \
        (ui.proc_backtester_o is not None and ui.proc_backtester_o.is_alive()) or \
        (ui.proc_backtester_ov is not None and ui.proc_backtester_ov.is_alive()) or \
        (ui.proc_backtester_ovc is not None and ui.proc_backtester_ovc.is_alive()) or \
        (ui.proc_backtester_ot is not None and ui.proc_backtester_ot.is_alive()) or \
        (ui.proc_backtester_ovt is not None and ui.proc_backtester_ovt.is_alive()) or \
        (ui.proc_backtester_ovct is not None and ui.proc_backtester_ovct.is_alive()) or \
        (ui.proc_backtester_oc is not None and ui.proc_backtester_oc.is_alive()) or \
        (ui.proc_backtester_ocv is not None and ui.proc_backtester_ocv.is_alive()) or \
        (ui.proc_backtester_ocvc is not None and ui.proc_backtester_ocvc.is_alive()) or \
        (ui.proc_backtester_og is not None and ui.proc_backtester_og.is_alive()) or \
        (ui.proc_backtester_ogv is not None and ui.proc_backtester_ogv.is_alive()) or \
        (ui.proc_backtester_ogvc is not None and ui.proc_backtester_ogvc.is_alive()) or \
        (ui.proc_backtester_or is not None and ui.proc_backtester_or.is_alive()) or \
        (ui.proc_backtester_orv is not None and ui.proc_backtester_orv.is_alive()) or \
        (ui.proc_backtester_orvc is not None and ui.proc_backtester_orvc.is_alive()) or \
        (ui.proc_backtester_b is not None and ui.proc_backtester_b.is_alive()) or \
        (ui.proc_backtester_bv is not None and ui.proc_backtester_bv.is_alive()) or \
        (ui.proc_backtester_bvc is not None and ui.proc_backtester_bvc.is_alive()) or \
        (ui.proc_backtester_bt is not None and ui.proc_backtester_bt.is_alive()) or \
        (ui.proc_backtester_bvt is not None and ui.proc_backtester_bvt.is_alive()) or \
        (ui.proc_backtester_bvct is not None and ui.proc_backtester_bvct.is_alive()) or \
        (ui.proc_backtester_br is not None and ui.proc_backtester_br.is_alive()) or \
        (ui.proc_backtester_brv is not None and ui.proc_backtester_brv.is_alive()) or \
        (ui.proc_backtester_brvc is not None and ui.proc_backtester_brvc.is_alive())
