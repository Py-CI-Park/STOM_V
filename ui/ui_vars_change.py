
from traceback import format_exc
from utility.setting_base import ui_num
from utility.static import error_decorator
from ui.set_text import buy_signal, sell_signal, future_buy_signal, future_sell_signal


@error_decorator
def get_fix_strategy(ui, strategy, gubun):
    if gubun == '매수':
        if '키움증권' in ui.dict_set['증권사'] or ui.dict_set['거래소'] == '업비트':
            if '\nif 매수:' in strategy:
                strategy = strategy.split('\nif 매수:')[0] + buy_signal
            elif 'self.tickdata' not in strategy and buy_signal not in strategy:
                strategy += '\n' + buy_signal
        else:
            if '\nif BUY_LONG or SELL_SHORT:' in strategy:
                strategy = strategy.split('\nif BUY_LONG or SELL_SHORT:')[0] + future_buy_signal
            elif 'self.tickdata' not in strategy and future_buy_signal not in strategy:
                strategy += '\n' + future_buy_signal
    else:
        if '키움증권' in ui.dict_set['증권사'] or ui.dict_set['거래소'] == '업비트':
            if '\nif 매도:' in strategy:
                strategy = strategy.split('\nif 매도:')[0] + sell_signal
            elif 'self.tickdata' not in strategy and sell_signal not in strategy:
                strategy += '\n' + sell_signal
        else:
            if "\nif (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):" in strategy:
                strategy = strategy.split("\nif (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):")[0] + future_sell_signal
            elif 'self.tickdata' not in strategy and future_sell_signal not in strategy:
                strategy += '\n' + future_sell_signal
    return strategy


@error_decorator
def get_optivars_to_gavars(ui, opti_vars_text):
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
    except:
        ui.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_optivars_to_gavars'))

    ga_vars_text = ga_vars_text.replace('vars_', 'self.vars')
    return ga_vars_text[:-1]


@error_decorator
def get_gavars_to_optivars(ui, ga_vars_text):
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
    except:
        ui.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_gavars_to_optivars'))

    opti_vars_text = opti_vars_text.replace('vars_', 'self.vars')
    return opti_vars_text[:-1]


@error_decorator
def get_stgtxt_to_varstxt(ui, buystg, sellstg):
    cnt = 1
    sellstg_str, buystg_str = '', ''
    if ui.focusWidget() == ui.svc_pushButton_24:
        if buystg and '변수' in buystg:
            for text in buystg:
                buystg_str += text
                if buystg_str[-2:] == '변수':
                    buystg_str = f'{buystg_str[:-2]}self.vars[{cnt}]'
                    cnt += 1
        if sellstg and '변수' in sellstg:
            for text in sellstg:
                sellstg_str += text
                if sellstg_str[-2:] == '변수':
                    sellstg_str = f'{sellstg_str[:-2]}self.vars[{cnt}]'
                    cnt += 1
    else:
        if sellstg and '변수' in sellstg:
            for text in sellstg:
                sellstg_str += text
                if sellstg_str[-2:] == '변수':
                    sellstg_str = f'{sellstg_str[:-2]}self.vars[{cnt}]'
                    cnt += 1
        if buystg and '변수' in buystg:
            for text in buystg:
                buystg_str += text
                if buystg_str[-2:] == '변수':
                    buystg_str = f'{buystg_str[:-2]}self.vars[{cnt}]'
                    cnt += 1

    return buystg_str, sellstg_str


# noinspection PyUnusedLocal
@error_decorator
def get_stgtxt_sort(ui, buystg, sellstg):
    buystg_str, sellstg_str = '', ''
    if buystg and sellstg and 'self.vars' in buystg and 'self.vars' in sellstg:
        buy_num = int(buystg.split('self.vars[')[1].split(']')[0])
        sell_num = int(sellstg.split('self.vars[')[1].split(']')[0])
        cnt = 1
        buystg = buystg.split('\n')
        sellstg = sellstg.split('\n')
        if buy_num < sell_num:
            for line in buystg:
                if 'self.vars' in line and line[0] != '#':
                    str_pass = False
                    for text in line:
                        if str_pass:
                            if text == ']':
                                str_pass = False
                            else:
                                continue
                        else:
                            buystg_str += text

                        if buystg_str[-5:] == 'vars[':
                            buystg_str += f'{cnt}]'
                            str_pass = True
                            cnt += 1
                    buystg_str += '\n'
                else:
                    buystg_str += line + '\n'
            for line in sellstg:
                if 'self.vars' in line and line[0] != '#':
                    str_pass = False
                    for text in line:
                        if str_pass:
                            if text == ']':
                                str_pass = False
                            else:
                                continue
                        else:
                            sellstg_str += text

                        if sellstg_str[-5:] == 'vars[':
                            sellstg_str += f'{cnt}]'
                            str_pass = True
                            cnt += 1
                    sellstg_str += '\n'
                else:
                    sellstg_str += line + '\n'
        else:
            for line in sellstg:
                if 'self.vars' in line and line[0] != '#':
                    str_pass = False
                    for text in line:
                        if str_pass:
                            if text == ']':
                                str_pass = False
                            else:
                                continue
                        else:
                            sellstg_str += text

                        if sellstg_str[-5:] == 'vars[':
                            sellstg_str += f'{cnt}]'
                            str_pass = True
                            cnt += 1
                    sellstg_str += '\n'
                else:
                    sellstg_str += line + '\n'
            for line in buystg:
                if 'self.vars' in line and line[0] != '#':
                    str_pass = False
                    for text in line:
                        if str_pass:
                            if text == ']':
                                str_pass = False
                            else:
                                continue
                        else:
                            buystg_str += text

                        if buystg_str[-5:] == 'vars[':
                            buystg_str += f'{cnt}]'
                            str_pass = True
                            cnt += 1
                    buystg_str += '\n'
                else:
                    buystg_str += line + '\n'

    return buystg_str[:-1], sellstg_str[:-1]


# noinspection PyUnusedLocal
@error_decorator
def get_stgtxt_sort2(ui, optivars, gavars):
    optivars_str, gavars_str = '', ''
    if optivars and 'self.vars' in optivars:
        cnt = 0
        optivars = optivars.split('\n')
        for line in optivars:
            if 'self.vars' in line and line[0] != '#':
                str_pass = False
                for text in line:
                    if str_pass:
                        if text == ']':
                            str_pass = False
                        else:
                            continue
                    else:
                        optivars_str += text

                    if optivars_str[-5:] == 'vars[':
                        optivars_str += f'{cnt}]'
                        str_pass = True
                        cnt += 1
                optivars_str += '\n'
            else:
                optivars_str += line + '\n'
    if gavars and 'self.vars' in gavars:
        cnt = 0
        gavars = gavars.split('\n')
        for line in gavars:
            if 'self.vars' in line and line[0] != '#':
                str_pass = False
                for text in line:
                    if str_pass:
                        if text == ']':
                            str_pass = False
                        else:
                            continue
                    else:
                        gavars_str += text

                    if gavars_str[-5:] == 'vars[':
                        gavars_str += f'{cnt}]'
                        str_pass = True
                        cnt += 1
                gavars_str += '\n'
            else:
                gavars_str += line + '\n'

    return optivars_str[:-1], gavars_str[:-1]
