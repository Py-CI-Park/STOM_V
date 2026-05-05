
from traceback import format_exc
from utility.settings.setting_base import ui_num
from ui.create_widget.set_text import buy_signal, sell_signal, buy_signal_future, sell_signal_future


def get_fix_strategy(ui, strategy, gubun):
    """전략에 시그널을 추가합니다.
    Args:
        ui: UI 클래스 인스턴스
        strategy: 전략 코드
        gubun: 구분 (매수, 매도)
    Returns:
        수정된 전략 코드
    """
    if gubun == '매수':
        if ui.market_gubun < 6:
            if '\nif 매수:' in strategy:
                strategy = strategy.split('\nif 매수:')[0] + buy_signal
            elif 'self.tickdata' not in strategy and buy_signal not in strategy:
                strategy += '\n' + buy_signal
        else:
            if '\nif BUY_LONG or SELL_SHORT:' in strategy:
                strategy = strategy.split('\nif BUY_LONG or SELL_SHORT:')[0] + buy_signal_future
            elif 'self.tickdata' not in strategy and buy_signal_future not in strategy:
                strategy += '\n' + buy_signal_future
    else:
        if ui.market_gubun < 6:
            if '\nif 매도:' in strategy:
                strategy = strategy.split('\nif 매도:')[0] + sell_signal
            elif 'self.tickdata' not in strategy and sell_signal not in strategy:
                strategy += '\n' + sell_signal
        else:
            if "\nif (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):" in strategy:
                strategy = strategy.split("\nif (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):")[0] + sell_signal_future
            elif 'self.tickdata' not in strategy and sell_signal_future not in strategy:
                strategy += '\n' + sell_signal_future
    return strategy


def get_optivars_to_gavars(ui, opti_vars_text):
    """최적화 변수를 GA 변수로 변환합니다.
    Args:
        ui: UI 클래스 인스턴스
        opti_vars_text: 최적화 변수 텍스트
    Returns:
        GA 변수 텍스트
    """
    ga_vars_text = ''
    try:
        vars_ = {}
        opti_vars_text = opti_vars_text.replace('self.vars', 'vars_')
        exec(compile(opti_vars_text, '<string>', 'exec'))
        for i in range(len(vars_)):
            ga_vars_text = f'{ga_vars_text}self.vars[{i}] = [['
            vars_start, vars_last, vars_gap = vars_[i][0]
            vars_high = vars_[i][1]
            vars_curr = vars_start
            if vars_start == vars_last:
                ga_vars_text = f'{ga_vars_text}{vars_curr}], {vars_curr}]\n'
            elif vars_start < vars_last:
                while vars_curr <= vars_last:
                    ga_vars_text = f'{ga_vars_text}{vars_curr}, '
                    vars_curr += vars_gap
                    if vars_gap < 0:
                        vars_curr = round(vars_curr, 2)
                ga_vars_text = f'{ga_vars_text[:-2]}], {vars_high}]\n'
            else:
                while vars_curr >= vars_last:
                    ga_vars_text = f'{ga_vars_text}{vars_curr}, '
                    vars_curr += vars_gap
                    if vars_gap < 0:
                        vars_curr = round(vars_curr, 2)
                ga_vars_text = f'{ga_vars_text[:-2]}], {vars_high}]\n'
    except Exception:
        ui.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_optivars_to_gavars'))

    ga_vars_text = ga_vars_text.replace('vars_', 'self.vars')
    return ga_vars_text[:-1]


def get_gavars_to_optivars(ui, ga_vars_text):
    """GA 변수를 최적화 변수로 변환합니다.
    Args:
        ui: UI 클래스 인스턴스
        ga_vars_text: GA 변수 텍스트
    Returns:
        최적화 변수 텍스트
    """
    opti_vars_text = ''
    try:
        vars_ = {}
        ga_vars_text = ga_vars_text.replace('self.vars', 'vars_')
        exec(compile(ga_vars_text, '<string>', 'exec'))
        for i in range(len(vars_)):
            if len(vars_[i][0]) == 1:
                vars_high = vars_[i][1]
                vars_gap = 0
                vars_start = vars_high
                vars_end = vars_high
            else:
                vars_high, vars_gap = vars_[i][1], vars_[i][0][1] - vars_[i][0][0]
                if vars_gap.__class__ == float: vars_gap = round(vars_gap, 2)
                vars_start = vars_[i][0][0]
                vars_end = vars_[i][0][-1]
            opti_vars_text = f'{opti_vars_text}vars_[{i}] = [[{vars_start}, {vars_end}, {vars_gap}], {vars_high}]\n'
    except Exception:
        ui.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_gavars_to_optivars'))

    opti_vars_text = opti_vars_text.replace('vars_', 'self.vars')
    return opti_vars_text[:-1]


def convert_varstext(cnt, stg_text):
    """변수 텍스트를 변환합니다.
    Args:
        cnt: 카운트
        stg_text: 전략 텍스트
    Returns:
        카운트, 변환된 텍스트
    """
    convert_text = ''
    for text in stg_text:
        convert_text += text
        if convert_text[-2:] == '변수':
            convert_text = f'{convert_text[:-2]}self.vars[{cnt}]'
            cnt += 1
    return cnt, convert_text


def get_stgtxt_to_varstxt(ui, buystg, sellstg):
    """전략 텍스트를 변수 텍스트로 변환합니다.
    Args:
        ui: UI 클래스 인스턴스
        buystg: 매수 전략
        sellstg: 매도 전략
    Returns:
        매수 전략, 매도 전략
    """
    cnt = 1
    if ui.focusWidget() == ui.svc_pushButton_24:
        if buystg and '변수' in buystg:
            cnt, buystg = convert_varstext(cnt, buystg)
        if sellstg and '변수' in sellstg:
            _, sellstg = convert_varstext(cnt, sellstg)
    else:
        if sellstg and '변수' in sellstg:
            cnt, sellstg = convert_varstext(cnt, sellstg)
        if buystg and '변수' in buystg:
            _, buystg = convert_varstext(cnt, buystg)
    return buystg, sellstg


def sort_varstext(cnt, stg_text):
    """변수 텍스트를 정렬합니다.
    Args:
        cnt: 카운트
        stg_text: 전략 텍스트
    Returns:
        카운트, 정렬된 텍스트
    """
    sort_text = ''
    for line in stg_text.split('\n'):
        if 'self.vars' in line and line[0] != '#':
            str_pass = False
            for text in line:
                if str_pass:
                    if text == ']':
                        str_pass = False
                    else:
                        continue
                else:
                    sort_text += text

                if sort_text[-5:] == 'vars[':
                    sort_text += f'{cnt}]'
                    str_pass = True
                    cnt += 1
            sort_text += '\n'
        else:
            sort_text += line + '\n'
    return cnt, sort_text[:-1]


def get_stgtxt_sort(buystg, sellstg):
    """전략 텍스트를 정렬합니다.
    Args:
        buystg: 매수 전략
        sellstg: 매도 전략
    Returns:
        매수 전략, 매도 전략
    """
    if buystg and sellstg and 'self.vars' in buystg and 'self.vars' in sellstg:
        buy_num = int(buystg.split('self.vars[')[1].split(']')[0])
        sell_num = int(sellstg.split('self.vars[')[1].split(']')[0])
        cnt = 1
        if buy_num < sell_num:
            cnt, buystg = sort_varstext(cnt, buystg)
            _, sellstg = sort_varstext(cnt, sellstg)
        else:
            cnt, sellstg = sort_varstext(cnt, sellstg)
            _, buystg = sort_varstext(cnt, buystg)
    return buystg, sellstg


def get_stgtxt_sort2(optivars, gavars):
    """최적화 변수를 정렬합니다.
    Args:
        optivars: 최적화 변수
        gavars: GA 변수
    Returns:
        최적화 변수, GA 변수
    """
    if optivars and 'self.vars' in optivars:
        _, optivars = sort_varstext(0, optivars)
    if gavars and 'self.vars' in gavars:
        _, gavars = sort_varstext(0, gavars)
    return optivars, gavars
