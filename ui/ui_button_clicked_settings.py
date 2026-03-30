
import os
import random
import shutil
import subprocess
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox, QLineEdit
from ui.set_style import style_bc_bt
from ui.set_text import famous_saying
from utility.setting_base import DB_PATH, ui_num
from utility.static import de_text, en_text, qtest_qwait, error_decorator


@error_decorator
def setting_load_01(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM main').set_index('index')
    if len(df) > 0:
        ui.sj_main_comBox_01.setCurrentText(df['증권사'][0])
        ui.sj_main_cheBox_01.setChecked(True) if df['주식에이전트'][0] else ui.sj_main_cheBox_01.setChecked(False)
        ui.sj_main_cheBox_02.setChecked(True) if df['주식트레이더'][0] else ui.sj_main_cheBox_02.setChecked(False)
        ui.sj_main_cheBox_03.setChecked(True) if df['주식데이터저장'][0] else ui.sj_main_cheBox_03.setChecked(False)
        ui.sj_main_comBox_02.setCurrentText(df['거래소'][0])
        ui.sj_main_cheBox_04.setChecked(True) if df['코인리시버'][0] else ui.sj_main_cheBox_04.setChecked(False)
        ui.sj_main_cheBox_05.setChecked(True) if df['코인트레이더'][0] else ui.sj_main_cheBox_05.setChecked(False)
        ui.sj_main_cheBox_06.setChecked(True) if df['코인데이터저장'][0] else ui.sj_main_cheBox_06.setChecked(False)
        ui.sj_main_comBox_03.setCurrentText('격리' if df['바이낸스선물마진타입'][0] == 'ISOLATED' else '교차')
        ui.sj_main_comBox_04.setCurrentText('단방향' if df['바이낸스선물포지션'][0] == 'false' else '양방향')
    else:
        QMessageBox.critical(ui, '오류 알림', '기본 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_02(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM sacc').set_index('index')
    comob_name = ui.sj_main_comBox_01.currentText()
    id_num = int(comob_name[4:])
    if len(df) > 0:
        if df['아이디'][id_num]:
            ui.sj_sacc_liEdit_01.setText(de_text(ui.dict_set['키'], df['아이디'][id_num]))
            ui.sj_sacc_liEdit_02.setText(de_text(ui.dict_set['키'], df['비밀번호'][id_num]))
            ui.sj_sacc_liEdit_03.setText(de_text(ui.dict_set['키'], df['인증서비밀번호'][id_num]))
            ui.sj_sacc_liEdit_04.setText(de_text(ui.dict_set['키'], df['계좌비밀번호'][id_num]))
    else:
        QMessageBox.critical(ui, '오류 알림', '주식 계정 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_03(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM cacc').set_index('index')
    combo_name = ui.sj_main_comBox_02.currentText()
    if len(df) > 0:
        if combo_name == '업비트' and df['Access_key'][1] and df['Secret_key'][1]:
            ui.sj_cacc_liEdit_01.setText(de_text(ui.dict_set['키'], df['Access_key'][1]))
            ui.sj_cacc_liEdit_02.setText(de_text(ui.dict_set['키'], df['Secret_key'][1]))
        elif combo_name == '바이낸스선물' and df['Access_key'][2] and df['Secret_key'][2]:
            ui.sj_cacc_liEdit_01.setText(de_text(ui.dict_set['키'], df['Access_key'][2]))
            ui.sj_cacc_liEdit_02.setText(de_text(ui.dict_set['키'], df['Secret_key'][2]))
    else:
        QMessageBox.critical(ui, '오류 알림', '계정 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_04(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM telegram').set_index('index')
    gubun = int(ui.sj_main_comBox_01.currentText()[4:])
    if len(df) > 0 and df['str_bot'][gubun]:
        ui.sj_tele_liEdit_01.setText(de_text(ui.dict_set['키'], df['str_bot'][gubun]))
        ui.sj_tele_liEdit_02.setText(de_text(ui.dict_set['키'], df['int_id'][gubun]))
    else:
        QMessageBox.critical(ui, '오류 알림', '텔레그램 봇토큰 및 사용자 아이디\n설정값이 존재하지 않습니다.\n')


@error_decorator
def setting_load_05(ui):
    df   = ui.dbreader.read_sql('설정디비', 'SELECT * FROM stock').set_index('index')
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    dfb  = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}buy').set_index('index')
    dfs  = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}sell').set_index('index')
    dfob = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}optibuy').set_index('index')
    dfos = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}optisell').set_index('index')
    if len(df) > 0:
        ui.sj_stock_ckBox_01.setChecked(True) if df['주식모의투자'][0] else ui.sj_stock_ckBox_01.setChecked(False)
        ui.sj_stock_ckBox_02.setChecked(True) if df['주식알림소리'][0] else ui.sj_stock_ckBox_02.setChecked(False)
        ui.sj_stock_ckBox_03.setChecked(True) if df['주식잔고청산'][0] else ui.sj_stock_ckBox_03.setChecked(False)
        ui.sj_stock_ckBox_04.setChecked(True) if df['주식프로세스종료'][0] else ui.sj_stock_ckBox_04.setChecked(False)
        ui.sj_stock_ckBox_05.setChecked(True) if df['주식컴퓨터종료'][0] else ui.sj_stock_ckBox_05.setChecked(False)
        ui.sj_stock_ckBox_09.setChecked(True) if df['주식투자금고정'][0] else ui.sj_stock_ckBox_09.setChecked(False)
        ui.sj_stock_ckBox_10.setChecked(True) if df['주식손실중지'][0] else ui.sj_stock_ckBox_10.setChecked(False)
        ui.sj_stock_ckBox_11.setChecked(True) if df['주식수익중지'][0] else ui.sj_stock_ckBox_11.setChecked(False)
        ui.sj_stock_lEdit_01.setText(str(df['주식평균값계산틱수'][0]))
        ui.sj_stock_lEdit_02.setText(str(df['주식최대매수종목수'][0]))
        ui.sj_stock_lEdit_03.setText(str(df['주식전략종료시간'][0]))
        ui.sj_stock_cbBox_01.clear()
        ui.sj_stock_cbBox_02.clear()
        ui.sj_stock_cbBox_01.addItem('사용안함')
        ui.sj_stock_cbBox_02.addItem('사용안함')
        if len(dfb) > 0:
            stg_list = list(dfb.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_stock_cbBox_01.addItem(stg)
        if len(dfob) > 0:
            stg_list = list(dfob.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_stock_cbBox_01.addItem(stg)
        if df['주식매수전략'][0]:
            ui.sj_stock_cbBox_01.setCurrentText(df['주식매수전략'][0])
        if len(dfs) > 0:
            stg_list = list(dfs.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_stock_cbBox_02.addItem(stg)
        if len(dfos) > 0:
            stg_list = list(dfos.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_stock_cbBox_02.addItem(stg)
        if df['주식매도전략'][0]:
            ui.sj_stock_cbBox_02.setCurrentText(df['주식매도전략'][0])
        ui.sj_stock_cbBox_03.setCurrentText('1초스냅샷' if df['주식타임프레임'][0] else '1분봉')
        ui.sj_stock_lEdit_07.setText(str(df['주식투자금'][0]))
        ui.sj_stock_lEdit_09.setText(str(df['주식손실중지수익률'][0]))
        ui.sj_stock_lEdit_10.setText(str(df['주식수익중지수익률'][0]))
        if gubun == 'stock' and 153000 < df['주식전략종료시간'][0]:
            QMessageBox.critical(ui, '오류 알림', '주식전략의 종료시간을\n153001 이후 시간으로 설정할 수 없습니다.\n')
        elif gubun == 'future' and 160000 < df['주식전략종료시간'][0]:
            QMessageBox.critical(ui, '오류 알림', '해선전략의 종료시간을\n160001 이후 시간으로 설정할 수 없습니다.\n')
    else:
        QMessageBox.critical(ui, '오류 알림', '주식 전략 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_06(ui):
    df   = ui.dbreader.read_sql('설정디비', 'SELECT * FROM coin').set_index('index')
    dfb  = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinbuy').set_index('index')
    dfs  = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinsell').set_index('index')
    dfob = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptibuy').set_index('index')
    dfos = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptisell').set_index('index')
    if len(df) > 0:
        ui.sj_coin_cheBox_01.setChecked(True) if df['코인모의투자'][0] else ui.sj_coin_cheBox_01.setChecked(False)
        ui.sj_coin_cheBox_02.setChecked(True) if df['코인알림소리'][0] else ui.sj_coin_cheBox_02.setChecked(False)
        ui.sj_coin_cheBox_03.setChecked(True) if df['코인잔고청산'][0] else ui.sj_coin_cheBox_03.setChecked(False)
        ui.sj_coin_cheBox_04.setChecked(True) if df['코인프로세스종료'][0] else ui.sj_coin_cheBox_04.setChecked(False)
        ui.sj_coin_cheBox_05.setChecked(True) if df['코인컴퓨터종료'][0] else ui.sj_coin_cheBox_05.setChecked(False)
        ui.sj_coin_cheBox_09.setChecked(True) if df['코인투자금고정'][0] else ui.sj_coin_cheBox_09.setChecked(False)
        ui.sj_coin_cheBox_10.setChecked(True) if df['코인손실중지'][0] else ui.sj_coin_cheBox_10.setChecked(False)
        ui.sj_coin_cheBox_11.setChecked(True) if df['코인수익중지'][0] else ui.sj_coin_cheBox_11.setChecked(False)
        ui.sj_coin_liEdit_01.setText(str(df['코인평균값계산틱수'][0]))
        ui.sj_coin_liEdit_02.setText(str(df['코인최대매수종목수'][0]))
        ui.sj_coin_liEdit_03.setText(str(df['코인전략종료시간'][0]))
        ui.sj_coin_comBox_01.clear()
        ui.sj_coin_comBox_02.clear()
        ui.sj_coin_comBox_01.addItem('사용안함')
        ui.sj_coin_comBox_02.addItem('사용안함')
        if len(dfb) > 0:
            stg_list = list(dfb.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_coin_comBox_01.addItem(stg)
        if len(dfob) > 0:
            stg_list = list(dfob.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_coin_comBox_01.addItem(stg)
        if df['코인매수전략'][0]:
            ui.sj_coin_comBox_01.setCurrentText(df['코인매수전략'][0])
        if len(dfs) > 0:
            stg_list = list(dfs.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_coin_comBox_02.addItem(stg)
        if len(dfos) > 0:
            stg_list = list(dfos.index)
            stg_list.sort()
            for stg in stg_list:
                ui.sj_coin_comBox_02.addItem(stg)
        if df['코인매도전략'][0]:
            ui.sj_coin_comBox_02.setCurrentText(df['코인매도전략'][0])
        ui.sj_coin_comBox_03.setCurrentText('1초스냅샷' if df['코인타임프레임'][0] else '1분봉')
        ui.sj_coin_liEdit_07.setText(str(df['코인투자금'][0]))
        ui.sj_coin_liEdit_09.setText(str(df['코인손실중지수익률'][0]))
        ui.sj_coin_liEdit_10.setText(str(df['코인수익중지수익률'][0]))
        if df['코인전략종료시간'][0] > 235000:
            QMessageBox.critical(ui, '오류 알림', '코인 전략의 종료시간은\n235000이하로 설정하십시오.\n')
    else:
        QMessageBox.critical(ui, '오류 알림', '코인 전략 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_07(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM back').set_index('index')
    if len(df) > 0:
        ui.sj_back_cheBox_01.setChecked(True) if df['블랙리스트추가'][0] else ui.sj_back_cheBox_01.setChecked(False)
        ui.sj_back_cheBox_02.setChecked(True) if df['백테일괄로딩'][0] else ui.sj_back_cheBox_02.setChecked(False)
        ui.sj_back_cheBox_03.setChecked(True) if not df['백테일괄로딩'][0] else ui.sj_back_cheBox_03.setChecked(False)
        ui.sj_back_cheBox_04.setChecked(True) if df['디비자동관리'][0] else ui.sj_back_cheBox_04.setChecked(False)
        ui.sj_back_cheBox_05.setChecked(True) if df['백테주문관리적용'][0] else ui.sj_back_cheBox_05.setChecked(False)
        ui.sj_back_cheBox_06.setChecked(True) if df['교차검증가중치'][0] else ui.sj_back_cheBox_06.setChecked(False)
        ui.sj_back_cheBox_07.setChecked(True) if df['범위자동관리'][0] else ui.sj_back_cheBox_07.setChecked(False)
        ui.sj_back_cheBox_09.setChecked(True) if df['백테매수시간기준'][0] else ui.sj_back_cheBox_09.setChecked(False)
        ui.sj_back_liEdit_01.setText(str(df['기준값최소상승률'][0]))
        ui.sj_back_cheBox_10.setChecked(True) if df['그래프저장하지않기'][0] else ui.sj_back_cheBox_10.setChecked(False)
        ui.sj_back_cheBox_11.setChecked(True) if df['그래프띄우지않기'][0] else ui.sj_back_cheBox_11.setChecked(False)
        ui.sj_back_cheBox_12.setChecked(True) if df['백테스트로그기록안함'][0] else ui.sj_back_cheBox_12.setChecked(False)
        ui.sj_back_cheBox_13.setChecked(True) if df['백테스케쥴실행'][0] else ui.sj_back_cheBox_13.setChecked(False)
        ui.sj_back_cheBox_14.setChecked(True) if not df['백테날짜고정'][0] else ui.sj_back_cheBox_14.setChecked(False)
        ui.sj_back_cheBox_15.setChecked(True) if df['백테날짜고정'][0] else ui.sj_back_cheBox_15.setChecked(False)
        ui.sj_back_cheBox_16.setChecked(True) if df['시장미시구조분석'][0] else ui.sj_back_cheBox_16.setChecked(False)
        ui.sj_back_cheBox_17.setChecked(True) if df['시장리스크분석'][0] else ui.sj_back_cheBox_17.setChecked(False)
        ui.sj_back_comBox_03.clear()
        dfs = ui.dbreader.read_sql('전략디비', 'SELECT * FROM schedule').set_index('index')
        indexs = list(dfs.index)
        indexs.sort()
        for index in indexs:
            ui.sj_back_comBox_03.addItem(index)
        if df['백테스케쥴요일'][0] == 4:
            ui.sj_back_comBox_01.setCurrentText('금')
        elif df['백테스케쥴요일'][0] == 5:
            ui.sj_back_comBox_01.setCurrentText('토')
        elif df['백테스케쥴요일'][0] == 6:
            ui.sj_back_comBox_01.setCurrentText('일')

        ui.sj_back_liEdit_02.setText(str(df['백테스케쥴시간'][0]))
        ui.sj_back_comBox_02.setCurrentText(df['백테스케쥴구분'][0])
        ui.sj_back_comBox_03.setCurrentText(df['백테스케쥴명'][0])
        if df['백테날짜고정'][0]:
            ui.sj_back_daEdit_01.setDate(QDate.fromString(ui.dict_set['백테날짜'], 'yyyyMMdd'))
        else:
            ui.sj_back_liEdit_03.setText(df['백테날짜'][0])
    else:
        QMessageBox.critical(ui, '오류 알림', '백테 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_load_08(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM etc').set_index('index')
    if len(df) > 0:
        ui.sj_etc_checBox_02.setChecked(True) if df['저해상도'][0] else ui.sj_etc_checBox_02.setChecked(False)
        ui.sj_etc_checBox_04.setChecked(True) if df['휴무프로세스종료'][0] else ui.sj_etc_checBox_04.setChecked(False)
        ui.sj_etc_checBox_05.setChecked(True) if df['휴무컴퓨터종료'][0] else ui.sj_etc_checBox_05.setChecked(False)
        ui.sj_etc_checBox_03.setChecked(True) if df['창위치기억'][0] else ui.sj_etc_checBox_03.setChecked(False)
        ui.sj_etc_checBox_06.setChecked(True) if df['스톰라이브'][0] else ui.sj_etc_checBox_06.setChecked(False)
        ui.sj_etc_checBox_07.setChecked(True) if df['프로그램종료'][0] else ui.sj_etc_checBox_07.setChecked(False)
        if df['시리얼키'][0]:
            ui.sj_etc_liEditt_01.setText(de_text(ui.dict_set['키'], df['시리얼키'][0]))
        ui.sj_etc_comBoxx_01.setCurrentText(df['테마'][0])
    else:
        QMessageBox.critical(ui, '오류 알림', '기타 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_save_01(ui):
    증권사 = ui.sj_main_comBox_01.currentText()
    주식에이전트 = 1 if ui.sj_main_cheBox_01.isChecked() else 0
    주식트레이더 = 1 if ui.sj_main_cheBox_02.isChecked() else 0
    주식데이터저장 = 1 if ui.sj_main_cheBox_03.isChecked() else 0
    거래소 = ui.sj_main_comBox_02.currentText()
    코인리시버 = 1 if ui.sj_main_cheBox_04.isChecked() else 0
    코인트레이더 = 1 if ui.sj_main_cheBox_05.isChecked() else 0
    코인데이터저장 = 1 if ui.sj_main_cheBox_06.isChecked() else 0
    바이낸스선물마진타입 = 'ISOLATED' if ui.sj_main_comBox_03.currentText() == '격리' else 'CROSSED'
    바이낸스선물포지션 = 'false' if ui.sj_main_comBox_04.currentText() == '단방향' else 'true'

    if ui.proc_chqs.is_alive():
        columns = ['증권사', '주식에이전트', '주식트레이더', '주식데이터저장', '거래소', '코인리시버', '코인트레이더', '코인데이터저장',
                   '바이낸스선물마진타입', '바이낸스선물포지션']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query = f'UPDATE main SET {set_txt}'
        localvs = locals()
        values = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        prev_sg = ui.dict_set['증권사']
        prev_sr = ui.dict_set['주식에이전트']
        ui.dict_set['증권사'] = 증권사
        ui.dict_set['주식에이전트'] = 주식에이전트
        ui.dict_set['주식트레이더'] = 주식트레이더
        ui.dict_set['주식데이터저장'] = 주식데이터저장
        ui.dict_set['거래소'] = 거래소
        ui.dict_set['코인리시버'] = 코인리시버
        ui.dict_set['코인트레이더'] = 코인트레이더
        ui.dict_set['코인데이터저장'] = 코인데이터저장
        ui.dict_set['바이낸스선물마진타입'] = 바이낸스선물마진타입
        ui.dict_set['바이낸스선물포지션'] = 바이낸스선물포지션

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()

        if '키움증권' in ui.dict_set['증권사']:
            ui.sj_stock_label_03.setText(
                '종목당투자금                          백만원                                  전략중지 및 잔고청산   |')
        else:
            ui.sj_stock_label_03.setText(
                '종목당투자금                          계약수                                  전략중지 및 잔고청산   |')
        if ui.dict_set['거래소'] == '업비트':
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          백만원                                  전략중지 및 잔고청산   |')
        else:
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          USDT                                   전략중지 및 잔고청산   |')

        if (not prev_sr and 주식에이전트) or (prev_sr and prev_sg[:4] != 증권사[:4]):
            if ui.proc_manager is not None and ui.proc_manager.poll() is None:
                ui.wdzservQ.put(('manager', '프로세스종료'))
                qtest_qwait(3)
            if '키움증권' in 증권사:
                ui.proc_manager = subprocess.Popen(f'python32 ./trade/stock_korea/kiwoom_manager.py {ui.port_num}')
            else:
                ui.proc_manager = subprocess.Popen(f'python32 ./trade/future_oversea/future_manager.py {ui.port_num}')
            ui.windowQ.put((ui_num['시스템로그'], '설정이 변경되어 32비트 매니저 프로세스를 재구동하였습니다.'))

        if prev_sr and not 주식에이전트:
            if ui.proc_manager is not None and ui.proc_manager.poll() is None:
                ui.wdzservQ.put(('manager', '프로세스종료'))
                qtest_qwait(3)
                ui.windowQ.put((ui_num['시스템로그'], '설정이 변경되어 32비트 매니저 프로세스를 종료하였습니다.'))


@error_decorator
def setting_save_02(ui):
    아이디 = ui.sj_sacc_liEdit_01.text()
    비밀번호 = ui.sj_sacc_liEdit_02.text()
    인증서비밀번호 = ui.sj_sacc_liEdit_03.text()
    계좌비밀번호 = ui.sj_sacc_liEdit_04.text()
    comob_name = ui.sj_main_comBox_01.currentText()

    if '' in (아이디, 비밀번호, 인증서비밀번호, 계좌비밀번호):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        en_id1 = en_text(ui.dict_set['키'], 아이디)
        en_ps1 = en_text(ui.dict_set['키'], 비밀번호)
        en_cp1 = en_text(ui.dict_set['키'], 인증서비밀번호)
        en_ap1 = en_text(ui.dict_set['키'], 계좌비밀번호)
        id_num = int(comob_name[4:])

        if ui.proc_chqs.is_alive():
            columns = ['아이디', '비밀번호', '인증서비밀번호', '계좌비밀번호']
            set_txt = ', '.join([f'{col} = ?' for col in columns])
            query   = f'UPDATE sacc SET {set_txt} WHERE `index` = ?'
            values  = (en_id1, en_ps1, en_cp1, en_ap1, id_num)
            ui.queryQ.put(('설정디비', query, values))

            ui.dict_set[f'아이디{id_num}'] = 아이디
            ui.dict_set[f'비밀번호{id_num}'] = 비밀번호
            ui.dict_set[f'인증서비밀번호{id_num}'] = 인증서비밀번호
            ui.dict_set[f'계좌비밀번호{id_num}'] = 계좌비밀번호

            QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def setting_save_03(ui):
    access_key = ui.sj_cacc_liEdit_01.text()
    secret_key = ui.sj_cacc_liEdit_02.text()

    if '' in (access_key, secret_key):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        combo_name = ui.sj_main_comBox_02.currentText()
        if ui.proc_chqs.is_alive():
            en_access_key = en_text(ui.dict_set['키'], access_key)
            en_secret_key = en_text(ui.dict_set['키'], secret_key)
            index  = 1 if combo_name == '업비트' else 2
            query  = 'UPDATE cacc SET Access_key = ?, Secret_key = ? WHERE `index` = ?'
            values = (en_access_key, en_secret_key, index)
            ui.queryQ.put(('설정디비', query, values))

            if combo_name == '업비트':
                ui.dict_set['Access_key1'] = access_key
                ui.dict_set['Secret_key1'] = secret_key
            else:
                ui.dict_set['Access_key2'] = access_key
                ui.dict_set['Secret_key2'] = secret_key

            QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def setting_save_04(ui):
    str_bot = ui.sj_tele_liEdit_01.text()
    int_id = ui.sj_tele_liEdit_02.text()

    if '' in (str_bot, int_id):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        comob_name = ui.sj_main_comBox_01.currentText()
        gubun = comob_name[4:]
        if ui.proc_chqs.is_alive():
            en_str_bot = en_text(ui.dict_set['키'], str_bot)
            en_int_id = en_text(ui.dict_set['키'], int_id)
            query  = 'UPDATE telegram SET str_bot = ?, int_id = ? WHERE `index` = ?'
            values = (en_str_bot, en_int_id, gubun)
            ui.queryQ.put(('설정디비', query, values))

            ui.dict_set[f'텔레그램봇토큰{gubun}'] = str_bot
            ui.dict_set[f'텔레그램사용자아이디{gubun}'] = int(int_id)

            QMessageBox.information(ui, '저장 완료', '텔레그램봇 토큰 및 사용자 아이디 설정은 재구동해야 적용됩니다.')


@error_decorator
def setting_save_05(ui):
    주식모의투자 = 1 if ui.sj_stock_ckBox_01.isChecked() else 0
    주식알림소리 = 1 if ui.sj_stock_ckBox_02.isChecked() else 0
    주식잔고청산 = 1 if ui.sj_stock_ckBox_03.isChecked() else 0
    주식프로세스종료 = 1 if ui.sj_stock_ckBox_04.isChecked() else 0
    주식컴퓨터종료 = 1 if ui.sj_stock_ckBox_05.isChecked() else 0
    주식투자금고정 = 1 if ui.sj_stock_ckBox_09.isChecked() else 0
    주식손실중지 = 1 if ui.sj_stock_ckBox_10.isChecked() else 0
    주식수익중지 = 1 if ui.sj_stock_ckBox_11.isChecked() else 0
    주식매수전략 = ui.sj_stock_cbBox_01.currentText()
    주식매도전략 = ui.sj_stock_cbBox_02.currentText()
    주식타임프레임 = 1 if ui.sj_stock_cbBox_03.currentText() == '1초스냅샷' else 0
    주식평균값계산틱수 = ui.sj_stock_lEdit_01.text()
    주식최대매수종목수 = ui.sj_stock_lEdit_02.text()
    주식전략종료시간 = ui.sj_stock_lEdit_03.text()
    주식투자금 = ui.sj_stock_lEdit_07.text()
    주식손실중지수익률 = ui.sj_stock_lEdit_09.text()
    주식수익중지수익률 = ui.sj_stock_lEdit_10.text()

    if '' in (주식평균값계산틱수, 주식최대매수종목수, 주식전략종료시간, 주식투자금, 주식손실중지수익률, 주식수익중지수익률):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        if '해외선물' in ui.dict_set['증권사']:
            buttonReply = QMessageBox.question(
                ui, "경고", "해외선물의 전략 종료시간은 미국시카고 기준입니다.\n일반적으로 160000로 설정하시면 됩니다.\n",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
        else:
            buttonReply = QMessageBox.Yes

        if buttonReply == QMessageBox.Yes:
            주식평균값계산틱수, 주식최대매수종목수, 주식전략종료시간, 주식투자금, 주식손실중지수익률, 주식수익중지수익률 = \
                int(주식평균값계산틱수), int(주식최대매수종목수), int(주식전략종료시간), float(주식투자금), float(주식손실중지수익률), float(주식수익중지수익률)
            if 주식전략종료시간 < 10000:
                QMessageBox.critical(ui, '오류 알림', '주식 전략의 종료시간을\n초단위 시간까지 입력하십시오.\n')
                return
            elif '키움증권' in ui.dict_set['증권사'] and 152000 < 주식전략종료시간:
                QMessageBox.critical(ui, '오류 알림', '주식 전략의 종료시간을\n152001 이후 시간으로 설정할 수 없습니다.\n')
                return
            elif '해외선물' in ui.dict_set['증권사'] and 160000 < 주식전략종료시간:
                QMessageBox.critical(ui, '오류 알림', '해선 전략의 종료시간을\n160001 이후 시간으로 설정할 수 없습니다.\n')
                return

            if 주식매수전략 == '사용안함':
                주식매수전략 = ''
            if 주식매도전략 == '사용안함':
                주식매도전략 = ''

            if ui.proc_chqs.is_alive():
                columns = ['주식모의투자', '주식알림소리', '주식매수전략', '주식타임프레임', '주식매도전략', '주식평균값계산틱수',
                           '주식최대매수종목수', '주식전략종료시간', '주식잔고청산', '주식프로세스종료', '주식컴퓨터종료', '주식투자금고정',
                           '주식투자금', '주식손실중지', '주식손실중지수익률', '주식수익중지', '주식수익중지수익률']
                set_txt = ', '.join([f'{col} = ?' for col in columns])
                query   = f'UPDATE stock SET {set_txt}'
                localvs = locals()
                values  = tuple(localvs[col] for col in columns)
                ui.queryQ.put(('설정디비', query, values))

                ui.dict_set['주식모의투자'] = 주식모의투자
                ui.dict_set['주식알림소리'] = 주식알림소리
                ui.dict_set['주식매수전략'] = 주식매수전략
                ui.dict_set['주식매도전략'] = 주식매도전략
                ui.dict_set['주식타임프레임'] = 주식타임프레임
                ui.dict_set['주식평균값계산틱수'] = 주식평균값계산틱수
                ui.dict_set['주식최대매수종목수'] = 주식최대매수종목수
                ui.dict_set['주식전략종료시간'] = 주식전략종료시간
                ui.dict_set['주식잔고청산'] = 주식잔고청산
                ui.dict_set['주식프로세스종료'] = 주식프로세스종료
                ui.dict_set['주식컴퓨터종료'] = 주식컴퓨터종료
                ui.dict_set['주식투자금고정'] = 주식투자금고정
                ui.dict_set['주식투자금'] = 주식투자금
                ui.dict_set['주식손실중지'] = 주식손실중지
                ui.dict_set['주식손실중지수익률'] = 주식손실중지수익률
                ui.dict_set['주식수익중지'] = 주식수익중지
                ui.dict_set['주식수익중지수익률'] = 주식수익중지수익률

                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
                ui.UpdateDictSet()


@error_decorator
def setting_save_06(ui):
    코인모의투자 = 1 if ui.sj_coin_cheBox_01.isChecked() else 0
    코인알림소리 = 1 if ui.sj_coin_cheBox_02.isChecked() else 0
    코인잔고청산 = 1 if ui.sj_coin_cheBox_03.isChecked() else 0
    코인프로세스종료 = 1 if ui.sj_coin_cheBox_04.isChecked() else 0
    코인컴퓨터종료 = 1 if ui.sj_coin_cheBox_05.isChecked() else 0
    코인투자금고정 = 1 if ui.sj_coin_cheBox_09.isChecked() else 0
    코인손실중지 = 1 if ui.sj_coin_cheBox_10.isChecked() else 0
    코인수익중지 = 1 if ui.sj_coin_cheBox_11.isChecked() else 0
    코인매수전략 = ui.sj_coin_comBox_01.currentText()
    코인매도전략 = ui.sj_coin_comBox_02.currentText()
    코인타임프레임 = 1 if ui.sj_coin_comBox_03.currentText() == '1초스냅샷' else 0
    코인평균값계산틱수 = ui.sj_coin_liEdit_01.text()
    코인최대매수종목수 = ui.sj_coin_liEdit_02.text()
    코인전략종료시간 = ui.sj_coin_liEdit_03.text()
    코인투자금 = ui.sj_coin_liEdit_07.text()
    코인손실중지수익률 = ui.sj_coin_liEdit_09.text()
    코인수익중지수익률 = ui.sj_coin_liEdit_10.text()

    if '' in (코인평균값계산틱수, 코인최대매수종목수, 코인전략종료시간, 코인투자금, 코인손실중지수익률, 코인수익중지수익률):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        buttonReply = QMessageBox.question(
            ui, "경고", "코인의 전략 종료시간은 UTC 기준입니다.\n한국시간 -9시간으로 설정하였습니까?\n",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            코인평균값계산틱수, 코인최대매수종목수, 코인전략종료시간, 코인투자금, 코인손실중지수익률, 코인수익중지수익률 = \
                int(코인평균값계산틱수), int(코인최대매수종목수), int(코인전략종료시간), float(코인투자금), float(코인손실중지수익률), float(코인수익중지수익률)
            if 코인전략종료시간 < 10000:
                QMessageBox.critical(ui, '오류 알림', '코인 전략의 종료시간을\n초단위 시간까지 입력하십시오.\n')
                return
            elif 코인전략종료시간 > 235000:
                QMessageBox.critical(ui, '오류 알림', '코인 전략의 종료시간은\n235000이하로 설정하십시오.\n')
                return

            if 코인매수전략 == '사용안함':
                코인매수전략 = ''
            if 코인매도전략 == '사용안함':
                코인매도전략 = ''

            if ui.proc_chqs.is_alive():
                columns = ['코인모의투자', '코인알림소리', '코인매수전략', '코인타임프레임', '코인매도전략', '코인평균값계산틱수',
                           '코인최대매수종목수', '코인전략종료시간', '코인잔고청산', '코인프로세스종료', '코인컴퓨터종료', '코인투자금고정',
                           '코인투자금', '코인손실중지', '코인손실중지수익률', '코인수익중지', '코인수익중지수익률']
                set_txt = ', '.join([f'{col} = ?' for col in columns])
                query   = f'UPDATE coin SET {set_txt}'
                localvs = locals()
                values  = tuple(localvs[col] for col in columns)
                ui.queryQ.put(('설정디비', query, values))

                ui.dict_set['코인모의투자'] = 코인모의투자
                ui.dict_set['코인알림소리'] = 코인알림소리
                ui.dict_set['코인매수전략'] = 코인매수전략
                ui.dict_set['코인매도전략'] = 코인매도전략
                ui.dict_set['코인타임프레임'] = 코인타임프레임
                ui.dict_set['코인평균값계산틱수'] = 코인평균값계산틱수
                ui.dict_set['코인최대매수종목수'] = 코인최대매수종목수
                ui.dict_set['코인전략종료시간'] = 코인전략종료시간
                ui.dict_set['코인잔고청산'] = 코인잔고청산
                ui.dict_set['코인프로세스종료'] = 코인프로세스종료
                ui.dict_set['코인컴퓨터종료'] = 코인컴퓨터종료
                ui.dict_set['코인투자금고정'] = 코인투자금고정
                ui.dict_set['코인투자금'] = 코인투자금
                ui.dict_set['코인손실중지'] = 코인손실중지
                ui.dict_set['코인손실중지수익률'] = 코인손실중지수익률
                ui.dict_set['코인수익중지'] = 코인수익중지
                ui.dict_set['코인수익중지수익률'] = 코인수익중지수익률

                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
                ui.UpdateDictSet()


@error_decorator
def setting_save_07(ui):
    블랙리스트추가 = 1 if ui.sj_back_cheBox_01.isChecked() else 0
    백테일괄로딩 = 1 if ui.sj_back_cheBox_02.isChecked() else 0
    디비자동관리 = 1 if ui.sj_back_cheBox_04.isChecked() else 0
    백테주문관리적용 = 1 if ui.sj_back_cheBox_05.isChecked() else 0
    교차검증가중치 = 1 if ui.sj_back_cheBox_06.isChecked() else 0
    범위자동관리 = 1 if ui.sj_back_cheBox_07.isChecked() else 0
    백테매수시간기준 = 1 if ui.sj_back_cheBox_09.isChecked() else 0
    기준값최소상승률 = ui.sj_back_liEdit_01.text()
    그래프저장하지않기 = 1 if ui.sj_back_cheBox_10.isChecked() else 0
    그래프띄우지않기 = 1 if ui.sj_back_cheBox_11.isChecked() else 0
    백테스트로그기록안함 = 1 if ui.sj_back_cheBox_12.isChecked() else 0
    백테스케쥴실행 = 1 if ui.sj_back_cheBox_13.isChecked() else 0
    백테날짜고정 = 1 if ui.sj_back_cheBox_15.isChecked() else 0
    시장미시구조분석 = 1 if ui.sj_back_cheBox_16.isChecked() else 0
    시장리스크분석 = 1 if ui.sj_back_cheBox_17.isChecked() else 0

    if ui.sj_back_comBox_01.currentText() == '금':
        백테스케쥴요일 = 4
    elif ui.sj_back_comBox_01.currentText() == '토':
        백테스케쥴요일 = 5
    else:
        백테스케쥴요일 = 6

    백테스케쥴시간 = ui.sj_back_liEdit_02.text()
    백테스케쥴구분 = ui.sj_back_comBox_02.currentText()
    백테스케쥴명 = ui.sj_back_comBox_03.currentText()

    if 백테날짜고정:
        백테날짜 = ui.sj_back_daEdit_01.date().toString('yyyyMMdd')
    else:
        백테날짜 = ui.sj_back_liEdit_03.text()

    if '' in (백테날짜, 백테스케쥴시간):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
    else:
        백테스케쥴시간 = int(백테스케쥴시간)
        if ui.proc_chqs.is_alive():
            columns = ['블랙리스트추가', '백테주문관리적용', '백테매수시간기준', '백테일괄로딩', '그래프저장하지않기', '그래프띄우지않기',
                       '디비자동관리', '교차검증가중치', '기준값최소상승률', '백테스케쥴실행', '백테스케쥴요일', '백테스케쥴시간',
                       '백테스케쥴구분', '백테스케쥴명', '백테날짜고정', '백테날짜', '범위자동관리', '백테스트로그기록안함',
                       '시장미시구조분석', '시장리스크분석']
            set_txt = ', '.join([f'{col} = ?' for col in columns])
            query   = f'UPDATE back SET {set_txt}'
            localvs = locals()
            values  = tuple(localvs[col] for col in columns)
            ui.queryQ.put(('설정디비', query, values))

            pre_bbg = ui.dict_set['백테주문관리적용']
            ui.dict_set['블랙리스트추가'] = 블랙리스트추가
            ui.dict_set['백테주문관리적용'] = 백테주문관리적용
            ui.dict_set['백테매수시간기준'] = 백테매수시간기준
            ui.dict_set['백테일괄로딩'] = 백테일괄로딩
            ui.dict_set['그래프저장하지않기'] = 그래프저장하지않기
            ui.dict_set['그래프띄우지않기'] = 그래프띄우지않기
            ui.dict_set['디비자동관리'] = 디비자동관리
            ui.dict_set['교차검증가중치'] = 교차검증가중치
            ui.dict_set['기준값최소상승률'] = 기준값최소상승률
            ui.dict_set['백테스케쥴실행'] = 백테스케쥴실행
            ui.dict_set['백테스케쥴요일'] = 백테스케쥴요일
            ui.dict_set['백테스케쥴시간'] = 백테스케쥴시간
            ui.dict_set['백테스케쥴구분'] = 백테스케쥴구분
            ui.dict_set['백테스케쥴명'] = 백테스케쥴명
            ui.dict_set['백테날짜고정'] = 백테날짜고정
            ui.dict_set['백테날짜'] = 백테날짜
            ui.dict_set['범위자동관리'] = 범위자동관리
            ui.dict_set['백테스트로그기록안함'] = 백테스트로그기록안함
            ui.dict_set['시장미시구조분석'] = 시장미시구조분석
            ui.dict_set['시장리스크분석'] = 시장리스크분석

            QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
            ui.UpdateDictSet()

            if pre_bbg != 백테주문관리적용:
                ui.BacktestEngineKill()


@error_decorator
def setting_save_08(ui):
    테마 = ui.sj_etc_comBoxx_01.currentText()
    저해상도 = 1 if ui.sj_etc_checBox_02.isChecked() else 0
    창위치기억 = 1 if ui.sj_etc_checBox_03.isChecked() else 0
    휴무프로세스종료 = 1 if ui.sj_etc_checBox_04.isChecked() else 0
    휴무컴퓨터종료 = 1 if ui.sj_etc_checBox_05.isChecked() else 0
    스톰라이브 = 1 if ui.sj_etc_checBox_06.isChecked() else 0
    프로그램종료 = 1 if ui.sj_etc_checBox_07.isChecked() else 0
    시리얼키_ = ui.sj_etc_liEditt_01.text()
    시리얼키 = en_text(ui.dict_set['키'], 시리얼키_)

    if ui.proc_chqs.is_alive():
        columns = ['테마', '저해상도', '창위치기억', '휴무프로세스종료', '휴무컴퓨터종료', '스톰라이브', '프로그램종료', '시리얼키']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE etc SET {set_txt}'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        ui.dict_set['테마'] = 테마
        ui.dict_set['저해상도'] = 저해상도
        ui.dict_set['창위치기억'] = 창위치기억
        ui.dict_set['휴무프로세스종료'] = 휴무프로세스종료
        ui.dict_set['휴무컴퓨터종료'] = 휴무컴퓨터종료
        ui.dict_set['스톰라이브'] = 스톰라이브
        ui.dict_set['프로그램종료'] = 프로그램종료
        ui.dict_set['시리얼키'] = 시리얼키_

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()


@error_decorator
def setting_acc_view(ui):
    if ui.sj_etc_pButton_01.text() == '계정 텍스트 보기':
        ui.pa_lineEditttt_01.clear()
        ui.dialog_pass.show() if not ui.dialog_pass.isVisible() else ui.dialog_pass.close()
    else:
        ui.sj_sacc_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_sacc_liEdit_02.setEchoMode(QLineEdit.Password)
        ui.sj_sacc_liEdit_03.setEchoMode(QLineEdit.Password)
        ui.sj_sacc_liEdit_04.setEchoMode(QLineEdit.Password)
        ui.sj_cacc_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_cacc_liEdit_02.setEchoMode(QLineEdit.Password)
        ui.sj_tele_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_tele_liEdit_02.setEchoMode(QLineEdit.Password)
        ui.sj_etc_liEditt_01.setEchoMode(QLineEdit.Password)
        ui.sj_etc_pButton_01.setText('계정 텍스트 보기')
        ui.sj_etc_pButton_01.setStyleSheet(style_bc_bt)


@error_decorator
def setting_order_load_01(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM stockbuyorder').set_index('index')

    if len(df) > 0:
        ui.ss_buyy_checkBox_01.setChecked(True) if df['주식매수주문구분'][0] == '시장가' else ui.ss_buyy_checkBox_01.setChecked(False)
        ui.ss_buyy_checkBox_02.setChecked(True) if df['주식매수주문구분'][0] == '지정가' else ui.ss_buyy_checkBox_02.setChecked(False)
        ui.ss_buyy_checkBox_03.setChecked(True) if df['주식매수주문구분'][0] == '최유리지정가' else ui.ss_buyy_checkBox_03.setChecked(False)
        ui.ss_buyy_checkBox_04.setChecked(True) if df['주식매수주문구분'][0] == '최우선지정가' else ui.ss_buyy_checkBox_04.setChecked(False)
        ui.ss_buyy_checkBox_05.setChecked(True) if df['주식매수주문구분'][0] == '지정가IOC' else ui.ss_buyy_checkBox_05.setChecked(False)
        ui.ss_buyy_checkBox_06.setChecked(True) if df['주식매수주문구분'][0] == '시장가IOC' else ui.ss_buyy_checkBox_06.setChecked(False)
        ui.ss_buyy_checkBox_07.setChecked(True) if df['주식매수주문구분'][0] == '최유리IOC' else ui.ss_buyy_checkBox_07.setChecked(False)
        ui.ss_buyy_checkBox_08.setChecked(True) if df['주식매수주문구분'][0] == '지정가FOK' else ui.ss_buyy_checkBox_08.setChecked(False)
        ui.ss_buyy_checkBox_09.setChecked(True) if df['주식매수주문구분'][0] == '시장가FOK' else ui.ss_buyy_checkBox_09.setChecked(False)
        ui.ss_buyy_checkBox_10.setChecked(True) if df['주식매수주문구분'][0] == '최유리FOK' else ui.ss_buyy_checkBox_10.setChecked(False)
        ui.ss_buyy_lineEdit_01.setText(str(df['주식매수분할횟수'][0]))
        ui.ss_buyy_checkBox_11.setChecked(True) if df['주식매수분할방법'][0] == 1 else ui.ss_buyy_checkBox_11.setChecked(False)
        ui.ss_buyy_checkBox_12.setChecked(True) if df['주식매수분할방법'][0] == 2 else ui.ss_buyy_checkBox_12.setChecked(False)
        ui.ss_buyy_checkBox_13.setChecked(True) if df['주식매수분할방법'][0] == 3 else ui.ss_buyy_checkBox_13.setChecked(False)
        ui.ss_buyy_checkBox_14.setChecked(True) if df['주식매수분할시그널'][0] else ui.ss_buyy_checkBox_14.setChecked(False)
        ui.ss_buyy_checkBox_15.setChecked(True) if df['주식매수분할하방'][0] else ui.ss_buyy_checkBox_15.setChecked(False)
        ui.ss_buyy_checkBox_16.setChecked(True) if df['주식매수분할상방'][0] else ui.ss_buyy_checkBox_16.setChecked(False)
        ui.ss_buyy_lineEdit_02.setText(str(df['주식매수분할하방수익률'][0]))
        ui.ss_buyy_lineEdit_03.setText(str(df['주식매수분할상방수익률'][0]))
        ui.ss_buyy_checkBox_17.setChecked(True) if df['주식매수분할고정수익률'][0] else ui.ss_buyy_checkBox_17.setChecked(False)
        ui.ss_buyy_comboBox_01.setCurrentText(str(df['주식매수지정가기준가격'][0]))
        ui.ss_buyy_comboBox_02.setCurrentText(str(df['주식매수지정가호가번호'][0]))
        ui.ss_buyy_comboBox_03.setCurrentText(str(df['주식매수시장가잔량범위'][0]))
        ui.ss_buyy_checkBox_18.setChecked(True) if df['주식매수취소관심이탈'][0] else ui.ss_buyy_checkBox_18.setChecked(False)
        ui.ss_buyy_checkBox_19.setChecked(True) if df['주식매수취소매도시그널'][0] else ui.ss_buyy_checkBox_19.setChecked(False)
        ui.ss_buyy_checkBox_20.setChecked(True) if df['주식매수취소시간'][0] else ui.ss_buyy_checkBox_20.setChecked(False)
        ui.ss_buyy_lineEdit_04.setText(str(df['주식매수취소시간초'][0]))
        ui.ss_buyy_checkBox_21.setChecked(True) if df['주식매수금지블랙리스트'][0] else ui.ss_buyy_checkBox_21.setChecked(False)
        ui.ss_buyy_checkBox_22.setChecked(True) if df['주식매수금지라운드피겨'][0] else ui.ss_buyy_checkBox_22.setChecked(False)
        ui.ss_buyy_lineEdit_05.setText(str(df['주식매수금지라운드호가'][0]))
        ui.ss_buyy_checkBox_23.setChecked(True) if df['주식매수금지손절횟수'][0] else ui.ss_buyy_checkBox_23.setChecked(False)
        ui.ss_buyy_lineEdit_06.setText(str(df['주식매수금지손절횟수값'][0]))
        ui.ss_buyy_checkBox_24.setChecked(True) if df['주식매수금지거래횟수'][0] else ui.ss_buyy_checkBox_24.setChecked(False)
        ui.ss_buyy_lineEdit_07.setText(str(df['주식매수금지거래횟수값'][0]))
        ui.ss_buyy_checkBox_25.setChecked(True) if df['주식매수금지시간'][0] else ui.ss_buyy_checkBox_25.setChecked(False)
        ui.ss_buyy_lineEdit_08.setText(str(df['주식매수금지시작시간'][0]))
        ui.ss_buyy_lineEdit_09.setText(str(df['주식매수금지종료시간'][0]))
        ui.ss_buyy_checkBox_26.setChecked(True) if df['주식매수금지간격'][0] else ui.ss_buyy_checkBox_26.setChecked(False)
        ui.ss_buyy_lineEdit_10.setText(str(df['주식매수금지간격초'][0]))
        ui.ss_buyy_checkBox_27.setChecked(True) if df['주식매수금지손절간격'][0] else ui.ss_buyy_checkBox_27.setChecked(False)
        ui.ss_buyy_lineEdit_11.setText(str(df['주식매수금지손절간격초'][0]))
        ui.ss_buyy_lineEdit_12.setText(str(df['주식매수정정횟수'][0]))
        ui.ss_buyy_comboBox_04.setCurrentText(str(df['주식매수정정호가차이'][0]))
        ui.ss_buyy_comboBox_05.setCurrentText(str(df['주식매수정정호가'][0]))
        ui.ss_bj_checkBoxxx_01.setChecked(False)
        ui.ss_bj_checkBoxxx_02.setChecked(False)
        ui.ss_bj_checkBoxxx_03.setChecked(False)
        ui.ss_bj_checkBoxxx_04.setChecked(False)
        ui.ss_bj_checkBoxxx_05.setChecked(False)
        ui.ss_bj_checkBoxxx_06.setChecked(False)
        bjjj_list = df['주식비중조절'][0]
        bjjj_list = bjjj_list.split(';')
        if bjjj_list[0] == '0':   ui.ss_bj_checkBoxxx_01.setChecked(True)
        elif bjjj_list[0] == '1': ui.ss_bj_checkBoxxx_02.setChecked(True)
        elif bjjj_list[0] == '2': ui.ss_bj_checkBoxxx_03.setChecked(True)
        elif bjjj_list[0] == '3': ui.ss_bj_checkBoxxx_04.setChecked(True)
        elif bjjj_list[0] == '4': ui.ss_bj_checkBoxxx_05.setChecked(True)
        elif bjjj_list[0] == '5': ui.ss_bj_checkBoxxx_06.setChecked(True)
        ui.ss_bj_lineEdittt_01.setText(bjjj_list[1])
        ui.ss_bj_lineEdittt_02.setText(bjjj_list[2])
        ui.ss_bj_lineEdittt_03.setText(bjjj_list[3])
        ui.ss_bj_lineEdittt_04.setText(bjjj_list[4])
        ui.ss_bj_lineEdittt_05.setText(bjjj_list[5])
        ui.ss_bj_lineEdittt_06.setText(bjjj_list[6])
        ui.ss_bj_lineEdittt_07.setText(bjjj_list[7])
        ui.ss_bj_lineEdittt_08.setText(bjjj_list[8])
        ui.ss_bj_lineEdittt_09.setText(bjjj_list[9])
    else:
        QMessageBox.critical(ui, '오류 알림', '주문관리 주식매수 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_order_load_02(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM stocksellorder').set_index('index')

    if len(df) > 0:
        ui.ss_sell_checkBox_01.setChecked(True) if df['주식매도주문구분'][0] == '시장가' else ui.ss_sell_checkBox_01.setChecked(False)
        ui.ss_sell_checkBox_02.setChecked(True) if df['주식매도주문구분'][0] == '지정가' else ui.ss_sell_checkBox_02.setChecked(False)
        ui.ss_sell_checkBox_03.setChecked(True) if df['주식매도주문구분'][0] == '최유리지정가' else ui.ss_sell_checkBox_03.setChecked(False)
        ui.ss_sell_checkBox_04.setChecked(True) if df['주식매도주문구분'][0] == '최우선지정가' else ui.ss_sell_checkBox_04.setChecked(False)
        ui.ss_sell_checkBox_05.setChecked(True) if df['주식매도주문구분'][0] == '지정가IOC' else ui.ss_sell_checkBox_05.setChecked(False)
        ui.ss_sell_checkBox_06.setChecked(True) if df['주식매도주문구분'][0] == '시장가IOC' else ui.ss_sell_checkBox_06.setChecked(False)
        ui.ss_sell_checkBox_07.setChecked(True) if df['주식매도주문구분'][0] == '최유리IOC' else ui.ss_sell_checkBox_07.setChecked(False)
        ui.ss_sell_checkBox_08.setChecked(True) if df['주식매도주문구분'][0] == '지정가FOK' else ui.ss_sell_checkBox_08.setChecked(False)
        ui.ss_sell_checkBox_09.setChecked(True) if df['주식매도주문구분'][0] == '시장가FOK' else ui.ss_sell_checkBox_09.setChecked(False)
        ui.ss_sell_checkBox_10.setChecked(True) if df['주식매도주문구분'][0] == '최유리FOK' else ui.ss_sell_checkBox_10.setChecked(False)
        ui.ss_sell_lineEdit_01.setText(str(df['주식매도분할횟수'][0]))
        ui.ss_sell_checkBox_11.setChecked(True) if df['주식매도분할방법'][0] == 1 else ui.ss_sell_checkBox_11.setChecked(False)
        ui.ss_sell_checkBox_12.setChecked(True) if df['주식매도분할방법'][0] == 2 else ui.ss_sell_checkBox_12.setChecked(False)
        ui.ss_sell_checkBox_13.setChecked(True) if df['주식매도분할방법'][0] == 3 else ui.ss_sell_checkBox_13.setChecked(False)
        ui.ss_sell_checkBox_14.setChecked(True) if df['주식매도분할시그널'][0] else ui.ss_sell_checkBox_14.setChecked(False)
        ui.ss_sell_checkBox_15.setChecked(True) if df['주식매도분할하방'][0] else ui.ss_sell_checkBox_15.setChecked(False)
        ui.ss_sell_checkBox_16.setChecked(True) if df['주식매도분할상방'][0] else ui.ss_sell_checkBox_16.setChecked(False)
        ui.ss_sell_lineEdit_02.setText(str(df['주식매도분할하방수익률'][0]))
        ui.ss_sell_lineEdit_03.setText(str(df['주식매도분할상방수익률'][0]))
        ui.ss_sell_comboBox_01.setCurrentText(str(df['주식매도지정가기준가격'][0]))
        ui.ss_sell_comboBox_02.setCurrentText(str(df['주식매도지정가호가번호'][0]))
        ui.ss_sell_comboBox_03.setCurrentText(str(df['주식매도시장가잔량범위'][0]))
        ui.ss_sell_checkBox_17.setChecked(True) if df['주식매도취소관심진입'][0] else ui.ss_sell_checkBox_17.setChecked(False)
        ui.ss_sell_checkBox_18.setChecked(True) if df['주식매도취소매수시그널'][0] else ui.ss_sell_checkBox_18.setChecked(False)
        ui.ss_sell_checkBox_19.setChecked(True) if df['주식매도취소시간'][0] else ui.ss_sell_checkBox_19.setChecked(False)
        ui.ss_sell_lineEdit_04.setText(str(df['주식매도취소시간초'][0]))
        ui.ss_sell_checkBox_20.setChecked(True) if df['주식매도금지매수횟수'][0] else ui.ss_sell_checkBox_20.setChecked(False)
        ui.ss_sell_lineEdit_05.setText(str(df['주식매도금지매수횟수값'][0]))
        ui.ss_sell_checkBox_21.setChecked(True) if df['주식매도금지라운드피겨'][0] else ui.ss_sell_checkBox_21.setChecked(False)
        ui.ss_sell_lineEdit_06.setText(str(df['주식매도금지라운드호가'][0]))
        ui.ss_sell_checkBox_22.setChecked(True) if df['주식매도금지시간'][0] else ui.ss_sell_checkBox_22.setChecked(False)
        ui.ss_sell_lineEdit_07.setText(str(df['주식매도금지시작시간'][0]))
        ui.ss_sell_lineEdit_08.setText(str(df['주식매도금지종료시간'][0]))
        ui.ss_sell_checkBox_23.setChecked(True) if df['주식매도금지간격'][0] else ui.ss_sell_checkBox_23.setChecked(False)
        ui.ss_sell_lineEdit_09.setText(str(df['주식매도금지간격초'][0]))
        ui.ss_sell_lineEdit_10.setText(str(df['주식매도정정횟수'][0]))
        ui.ss_sell_comboBox_04.setCurrentText(str(df['주식매도정정호가차이'][0]))
        ui.ss_sell_comboBox_05.setCurrentText(str(df['주식매도정정호가'][0]))
        ui.ss_sell_checkBox_24.setChecked(True) if df['주식매도익절수익률청산'][0] else ui.ss_sell_checkBox_26.setChecked(False)
        ui.ss_sell_lineEdit_11.setText(str(df['주식매도익절수익률'][0]))
        ui.ss_sell_checkBox_25.setChecked(True) if df['주식매도익절수익금청산'][0] else ui.ss_sell_checkBox_27.setChecked(False)
        ui.ss_sell_lineEdit_12.setText(str(df['주식매도익절수익금'][0]))
        ui.ss_sell_checkBox_26.setChecked(True) if df['주식매도손절수익률청산'][0] else ui.ss_sell_checkBox_26.setChecked(False)
        ui.ss_sell_lineEdit_13.setText(str(df['주식매도손절수익률'][0]))
        ui.ss_sell_checkBox_27.setChecked(True) if df['주식매도손절수익금청산'][0] else ui.ss_sell_checkBox_27.setChecked(False)
        ui.ss_sell_lineEdit_14.setText(str(df['주식매도손절수익금'][0]))
    else:
        QMessageBox.critical(ui, '오류 알림', '주문관리 주식매도 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_order_load_03(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM coinbuyorder').set_index('index')

    if len(df) > 0:
        ui.sc_buyy_checkBox_01.setChecked(True) if df['코인매수주문구분'][0] == '시장가' else ui.sc_buyy_checkBox_01.setChecked(False)
        ui.sc_buyy_checkBox_02.setChecked(True) if df['코인매수주문구분'][0] == '지정가' else ui.sc_buyy_checkBox_02.setChecked(False)
        ui.sc_buyy_checkBox_03.setChecked(True) if df['코인매수주문구분'][0] == '지정가IOC' else ui.sc_buyy_checkBox_03.setChecked(False)
        ui.sc_buyy_checkBox_04.setChecked(True) if df['코인매수주문구분'][0] == '지정가FOK' else ui.sc_buyy_checkBox_04.setChecked(False)
        ui.sc_buyy_lineEdit_01.setText(str(df['코인매수분할횟수'][0]))
        ui.sc_buyy_checkBox_05.setChecked(True) if df['코인매수분할방법'][0] == 1 else ui.sc_buyy_checkBox_05.setChecked(False)
        ui.sc_buyy_checkBox_06.setChecked(True) if df['코인매수분할방법'][0] == 2 else ui.sc_buyy_checkBox_06.setChecked(False)
        ui.sc_buyy_checkBox_07.setChecked(True) if df['코인매수분할방법'][0] == 3 else ui.sc_buyy_checkBox_07.setChecked(False)
        ui.sc_buyy_checkBox_08.setChecked(True) if df['코인매수분할시그널'][0] else ui.sc_buyy_checkBox_08.setChecked(False)
        ui.sc_buyy_checkBox_09.setChecked(True) if df['코인매수분할하방'][0] else ui.sc_buyy_checkBox_09.setChecked(False)
        ui.sc_buyy_checkBox_10.setChecked(True) if df['코인매수분할상방'][0] else ui.sc_buyy_checkBox_10.setChecked(False)
        ui.sc_buyy_lineEdit_02.setText(str(df['코인매수분할하방수익률'][0]))
        ui.sc_buyy_lineEdit_03.setText(str(df['코인매수분할상방수익률'][0]))
        ui.sc_buyy_checkBox_11.setChecked(True) if df['코인매수분할고정수익률'][0] else ui.sc_buyy_checkBox_11.setChecked(False)
        ui.sc_buyy_comboBox_01.setCurrentText(str(df['코인매수지정가기준가격'][0]))
        ui.sc_buyy_comboBox_02.setCurrentText(str(df['코인매수지정가호가번호'][0]))
        ui.sc_buyy_comboBox_03.setCurrentText(str(df['코인매수시장가잔량범위'][0]))
        ui.sc_buyy_checkBox_12.setChecked(True) if df['코인매수취소관심이탈'][0] else ui.sc_buyy_checkBox_12.setChecked(False)
        ui.sc_buyy_checkBox_13.setChecked(True) if df['코인매수취소매도시그널'][0] else ui.sc_buyy_checkBox_13.setChecked(False)
        ui.sc_buyy_checkBox_14.setChecked(True) if df['코인매수취소시간'][0] else ui.sc_buyy_checkBox_14.setChecked(False)
        ui.sc_buyy_lineEdit_04.setText(str(df['코인매수취소시간초'][0]))
        ui.sc_buyy_checkBox_15.setChecked(True) if df['코인매수금지블랙리스트'][0] else ui.sc_buyy_checkBox_15.setChecked(False)
        ui.sc_buyy_checkBox_16.setChecked(True) if df['코인매수금지200원이하'][0] else ui.sc_buyy_checkBox_16.setChecked(False)
        ui.sc_buyy_checkBox_17.setChecked(True) if df['코인매수금지손절횟수'][0] else ui.sc_buyy_checkBox_17.setChecked(False)
        ui.sc_buyy_lineEdit_05.setText(str(df['코인매수금지손절횟수값'][0]))
        ui.sc_buyy_checkBox_18.setChecked(True) if df['코인매수금지거래횟수'][0] else ui.sc_buyy_checkBox_18.setChecked(False)
        ui.sc_buyy_lineEdit_06.setText(str(df['코인매수금지거래횟수값'][0]))
        ui.sc_buyy_checkBox_19.setChecked(True) if df['코인매수금지시간'][0] else ui.sc_buyy_checkBox_19.setChecked(False)
        ui.sc_buyy_lineEdit_07.setText(str(df['코인매수금지시작시간'][0]))
        ui.sc_buyy_lineEdit_08.setText(str(df['코인매수금지종료시간'][0]))
        ui.sc_buyy_checkBox_20.setChecked(True) if df['코인매수금지간격'][0] else ui.sc_buyy_checkBox_20.setChecked(False)
        ui.sc_buyy_lineEdit_09.setText(str(df['코인매수금지간격초'][0]))
        ui.sc_buyy_checkBox_21.setChecked(True) if df['코인매수금지손절간격'][0] else ui.sc_buyy_checkBox_21.setChecked(False)
        ui.sc_buyy_lineEdit_10.setText(str(df['코인매수금지손절간격초'][0]))
        ui.sc_buyy_lineEdit_11.setText(str(df['코인매수정정횟수'][0]))
        ui.sc_buyy_comboBox_04.setCurrentText(str(df['코인매수정정호가차이'][0]))
        ui.sc_buyy_comboBox_05.setCurrentText(str(df['코인매수정정호가'][0]))
        ui.sc_bj_checkBoxxx_01.setChecked(False)
        ui.sc_bj_checkBoxxx_02.setChecked(False)
        ui.sc_bj_checkBoxxx_03.setChecked(False)
        ui.sc_bj_checkBoxxx_04.setChecked(False)
        ui.sc_bj_checkBoxxx_05.setChecked(False)
        ui.sc_bj_checkBoxxx_06.setChecked(False)
        bjjj_list = df['코인비중조절'][0]
        bjjj_list = bjjj_list.split(';')
        if bjjj_list[0] == '0':   ui.sc_bj_checkBoxxx_01.setChecked(True)
        elif bjjj_list[0] == '1': ui.sc_bj_checkBoxxx_02.setChecked(True)
        elif bjjj_list[0] == '2': ui.sc_bj_checkBoxxx_03.setChecked(True)
        elif bjjj_list[0] == '3': ui.sc_bj_checkBoxxx_04.setChecked(True)
        elif bjjj_list[0] == '4': ui.sc_bj_checkBoxxx_05.setChecked(True)
        elif bjjj_list[0] == '5': ui.sc_bj_checkBoxxx_06.setChecked(True)
        ui.sc_bj_lineEdittt_01.setText(bjjj_list[1])
        ui.sc_bj_lineEdittt_02.setText(bjjj_list[2])
        ui.sc_bj_lineEdittt_03.setText(bjjj_list[3])
        ui.sc_bj_lineEdittt_04.setText(bjjj_list[4])
        ui.sc_bj_lineEdittt_05.setText(bjjj_list[5])
        ui.sc_bj_lineEdittt_06.setText(bjjj_list[6])
        ui.sc_bj_lineEdittt_07.setText(bjjj_list[7])
        ui.sc_bj_lineEdittt_08.setText(bjjj_list[8])
        ui.sc_bj_lineEdittt_09.setText(bjjj_list[9])
    else:
        QMessageBox.critical(ui, '오류 알림', '주문관리 코인매수 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_order_load_04(ui):
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM coinsellorder').set_index('index')

    if len(df) > 0:
        ui.sc_sell_checkBox_01.setChecked(True) if df['코인매도주문구분'][0] == '시장가' else ui.sc_sell_checkBox_01.setChecked(False)
        ui.sc_sell_checkBox_02.setChecked(True) if df['코인매도주문구분'][0] == '지정가' else ui.sc_sell_checkBox_02.setChecked(False)
        ui.sc_sell_checkBox_03.setChecked(True) if df['코인매도주문구분'][0] == '지정가IOC' else ui.sc_sell_checkBox_03.setChecked(False)
        ui.sc_sell_checkBox_04.setChecked(True) if df['코인매도주문구분'][0] == '지정가FOK' else ui.sc_sell_checkBox_04.setChecked(False)
        ui.sc_sell_lineEdit_01.setText(str(df['코인매도분할횟수'][0]))
        ui.sc_sell_checkBox_05.setChecked(True) if df['코인매도분할방법'][0] == 1 else ui.sc_sell_checkBox_04.setChecked(False)
        ui.sc_sell_checkBox_06.setChecked(True) if df['코인매도분할방법'][0] == 2 else ui.sc_sell_checkBox_06.setChecked(False)
        ui.sc_sell_checkBox_07.setChecked(True) if df['코인매도분할방법'][0] == 3 else ui.sc_sell_checkBox_07.setChecked(False)
        ui.sc_sell_checkBox_08.setChecked(True) if df['코인매도분할시그널'][0] else ui.sc_sell_checkBox_08.setChecked(False)
        ui.sc_sell_checkBox_09.setChecked(True) if df['코인매도분할하방'][0] else ui.sc_sell_checkBox_09.setChecked(False)
        ui.sc_sell_checkBox_10.setChecked(True) if df['코인매도분할상방'][0] else ui.sc_sell_checkBox_10.setChecked(False)
        ui.sc_sell_lineEdit_02.setText(str(df['코인매도분할하방수익률'][0]))
        ui.sc_sell_lineEdit_03.setText(str(df['코인매도분할상방수익률'][0]))
        ui.sc_sell_comboBox_01.setCurrentText(str(df['코인매도지정가기준가격'][0]))
        ui.sc_sell_comboBox_02.setCurrentText(str(df['코인매도지정가호가번호'][0]))
        ui.sc_sell_comboBox_03.setCurrentText(str(df['코인매도시장가잔량범위'][0]))
        ui.sc_sell_checkBox_11.setChecked(True) if df['코인매도취소관심진입'][0] else ui.sc_sell_checkBox_11.setChecked(False)
        ui.sc_sell_checkBox_12.setChecked(True) if df['코인매도취소매수시그널'][0] else ui.sc_sell_checkBox_12.setChecked(False)
        ui.sc_sell_checkBox_13.setChecked(True) if df['코인매도취소시간'][0] else ui.sc_sell_checkBox_13.setChecked(False)
        ui.sc_sell_lineEdit_04.setText(str(df['코인매도취소시간초'][0]))
        ui.sc_sell_checkBox_14.setChecked(True) if df['코인매도금지매수횟수'][0] else ui.sc_sell_checkBox_14.setChecked(False)
        ui.sc_sell_lineEdit_05.setText(str(df['코인매도금지매수횟수값'][0]))
        ui.sc_sell_checkBox_15.setChecked(True) if df['코인매도금지시간'][0] else ui.sc_sell_checkBox_15.setChecked(False)
        ui.sc_sell_lineEdit_06.setText(str(df['코인매도금지시작시간'][0]))
        ui.sc_sell_lineEdit_07.setText(str(df['코인매도금지종료시간'][0]))
        ui.sc_sell_checkBox_16.setChecked(True) if df['코인매도금지간격'][0] else ui.sc_sell_checkBox_16.setChecked(False)
        ui.sc_sell_lineEdit_08.setText(str(df['코인매도금지간격초'][0]))
        ui.sc_sell_lineEdit_09.setText(str(df['코인매도정정횟수'][0]))
        ui.sc_sell_comboBox_04.setCurrentText(str(df['코인매도정정호가차이'][0]))
        ui.sc_sell_comboBox_05.setCurrentText(str(df['코인매도정정호가'][0]))
        ui.sc_sell_checkBox_17.setChecked(True) if df['코인매도익절수익률청산'][0] else ui.sc_sell_checkBox_14.setChecked(False)
        ui.sc_sell_lineEdit_10.setText(str(df['코인매도익절수익률'][0]))
        ui.sc_sell_checkBox_18.setChecked(True) if df['코인매도익절수익금청산'][0] else ui.sc_sell_checkBox_15.setChecked(False)
        ui.sc_sell_lineEdit_11.setText(str(df['코인매도익절수익금'][0]))
        ui.sc_sell_checkBox_19.setChecked(True) if df['코인매도손절수익률청산'][0] else ui.sc_sell_checkBox_14.setChecked(False)
        ui.sc_sell_lineEdit_12.setText(str(df['코인매도손절수익률'][0]))
        ui.sc_sell_checkBox_20.setChecked(True) if df['코인매도손절수익금청산'][0] else ui.sc_sell_checkBox_15.setChecked(False)
        ui.sc_sell_lineEdit_13.setText(str(df['코인매도손절수익금'][0]))
    else:
        QMessageBox.critical(ui, '오류 알림', '주문관리 코인매도 설정값이\n존재하지 않습니다.\n')


@error_decorator
def setting_order_save_01(ui):
    주식매수주문구분 = ''
    if ui.ss_buyy_checkBox_01.isChecked(): 주식매수주문구분 = '시장가'
    if ui.ss_buyy_checkBox_02.isChecked(): 주식매수주문구분 = '지정가'
    if ui.ss_buyy_checkBox_03.isChecked(): 주식매수주문구분 = '최유리지정가'
    if ui.ss_buyy_checkBox_04.isChecked(): 주식매수주문구분 = '최우선지정가'
    if ui.ss_buyy_checkBox_05.isChecked(): 주식매수주문구분 = '지정가IOC'
    if ui.ss_buyy_checkBox_06.isChecked(): 주식매수주문구분 = '시장가IOC'
    if ui.ss_buyy_checkBox_07.isChecked(): 주식매수주문구분 = '최유리IOC'
    if ui.ss_buyy_checkBox_08.isChecked(): 주식매수주문구분 = '지정가FOK'
    if ui.ss_buyy_checkBox_09.isChecked(): 주식매수주문구분 = '시장가FOK'
    if ui.ss_buyy_checkBox_10.isChecked(): 주식매수주문구분 = '최유리FOK'
    주식매수분할횟수 = ui.ss_buyy_lineEdit_01.text()
    주식매수분할방법 = 0
    if ui.ss_buyy_checkBox_11.isChecked(): 주식매수분할방법 = 1
    if ui.ss_buyy_checkBox_12.isChecked(): 주식매수분할방법 = 2
    if ui.ss_buyy_checkBox_13.isChecked(): 주식매수분할방법 = 3
    주식매수분할시그널 = 1 if ui.ss_buyy_checkBox_14.isChecked() else 0
    주식매수분할하방 = 1 if ui.ss_buyy_checkBox_15.isChecked() else 0
    주식매수분할상방 = 1 if ui.ss_buyy_checkBox_16.isChecked() else 0
    주식매수분할하방수익률 = ui.ss_buyy_lineEdit_02.text()
    주식매수분할상방수익률 = ui.ss_buyy_lineEdit_03.text()
    주식매수지정가기준가격 = ui.ss_buyy_comboBox_01.currentText()
    주식매수지정가호가번호 = ui.ss_buyy_comboBox_02.currentText()
    주식매수시장가잔량범위 = ui.ss_buyy_comboBox_03.currentText()
    주식매수분할고정수익률 = 1 if ui.ss_buyy_checkBox_17.isChecked() else 0
    주식매수취소관심이탈 = 1 if ui.ss_buyy_checkBox_18.isChecked() else 0
    주식매수취소매도시그널 = 1 if ui.ss_buyy_checkBox_19.isChecked() else 0
    주식매수취소시간 = 1 if ui.ss_buyy_checkBox_20.isChecked() else 0
    주식매수취소시간초 = ui.ss_buyy_lineEdit_04.text()
    주식매수금지블랙리스트 = 1 if ui.ss_buyy_checkBox_21.isChecked() else 0
    주식매수금지라운드피겨 = 1 if ui.ss_buyy_checkBox_22.isChecked() else 0
    주식매수금지라운드호가 = ui.ss_buyy_lineEdit_05.text()
    주식매수금지손절횟수 = 1 if ui.ss_buyy_checkBox_23.isChecked() else 0
    주식매수금지손절횟수값 = ui.ss_buyy_lineEdit_06.text()
    주식매수금지거래횟수 = 1 if ui.ss_buyy_checkBox_24.isChecked() else 0
    주식매수금지거래횟수값 = ui.ss_buyy_lineEdit_07.text()
    주식매수금지시간 = 1 if ui.ss_buyy_checkBox_25.isChecked() else 0
    주식매수금지시작시간 = ui.ss_buyy_lineEdit_08.text()
    주식매수금지종료시간 = ui.ss_buyy_lineEdit_09.text()
    주식매수금지간격 = 1 if ui.ss_buyy_checkBox_26.isChecked() else 0
    주식매수금지간격초 = ui.ss_buyy_lineEdit_10.text()
    주식매수금지손절간격 = 1 if ui.ss_buyy_checkBox_27.isChecked() else 0
    주식매수금지손절간격초 = ui.ss_buyy_lineEdit_11.text()
    주식매수정정횟수 = ui.ss_buyy_lineEdit_12.text()
    주식매수정정호가차이 = ui.ss_buyy_comboBox_04.currentText()
    주식매수정정호가 = ui.ss_buyy_comboBox_05.currentText()

    bjjj_list = []
    if ui.ss_bj_checkBoxxx_01.isChecked():   bjjj_list.append('0')
    elif ui.ss_bj_checkBoxxx_02.isChecked(): bjjj_list.append('1')
    elif ui.ss_bj_checkBoxxx_03.isChecked(): bjjj_list.append('2')
    elif ui.ss_bj_checkBoxxx_04.isChecked(): bjjj_list.append('3')
    elif ui.ss_bj_checkBoxxx_05.isChecked(): bjjj_list.append('4')
    elif ui.ss_bj_checkBoxxx_06.isChecked(): bjjj_list.append('5')

    save = True
    if ui.ss_bj_lineEdittt_01.text() == '': save = False
    if ui.ss_bj_lineEdittt_02.text() == '': save = False
    if ui.ss_bj_lineEdittt_03.text() == '': save = False
    if ui.ss_bj_lineEdittt_04.text() == '': save = False
    if ui.ss_bj_lineEdittt_05.text() == '': save = False
    if ui.ss_bj_lineEdittt_06.text() == '': save = False
    if ui.ss_bj_lineEdittt_07.text() == '': save = False
    if ui.ss_bj_lineEdittt_08.text() == '': save = False
    if ui.ss_bj_lineEdittt_09.text() == '': save = False

    if not save:
        QMessageBox.critical(ui, '오류 알림', '비중조절 세부설정값이 입력되지 않았습니다.\n')
        return

    bjjj_list.append(ui.ss_bj_lineEdittt_01.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_02.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_03.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_04.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_05.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_06.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_07.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_08.text())
    bjjj_list.append(ui.ss_bj_lineEdittt_09.text())
    주식비중조절 = ';'.join(bjjj_list)
    주식비중조절_ = [float(x) for x in bjjj_list]

    if '' in (주식매수주문구분, 주식매수분할횟수, 주식매수분할하방수익률, 주식매수분할상방수익률, 주식매수지정가호가번호, 주식매수시장가잔량범위,
              주식매수취소시간초, 주식매수금지라운드호가, 주식매수금지손절횟수값, 주식매수금지거래횟수값, 주식매수금지시작시간, 주식매수금지종료시간,
              주식매수금지간격초, 주식매수정정횟수):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 주식매수분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매수방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (주식매수분할시그널, 주식매수분할하방, 주식매수분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매수방법이 선택되지 않았습니다.\n')
        return

    주식매수분할횟수, 주식매수분할하방수익률, 주식매수분할상방수익률, 주식매수지정가호가번호, 주식매수시장가잔량범위, 주식매수취소시간초, \
        주식매수금지라운드호가, 주식매수금지손절횟수값, 주식매수금지거래횟수값, 주식매수금지시작시간, 주식매수금지종료시간, 주식매수금지간격초, \
        주식매수금지손절간격초, 주식매수정정횟수, 주식매수정정호가차이, 주식매수정정호가 = \
        int(주식매수분할횟수), float(주식매수분할하방수익률), float(주식매수분할상방수익률), int(주식매수지정가호가번호), \
        int(주식매수시장가잔량범위), int(주식매수취소시간초), int(주식매수금지라운드호가), int(주식매수금지손절횟수값), \
        int(주식매수금지거래횟수값), int(주식매수금지시작시간), int(주식매수금지종료시간), int(주식매수금지간격초), int(주식매수금지손절간격초), \
        int(주식매수정정횟수), int(주식매수정정호가차이), int(주식매수정정호가)

    if 주식매수분할횟수 < 0 or 주식매수분할하방수익률 < 0 or 주식매수분할상방수익률 < 0 or 주식매수시장가잔량범위 < 0 or 주식매수취소시간초 < 0 or \
            주식매수금지라운드호가 < 0 or 주식매수금지손절횟수값 < 0 or 주식매수금지거래횟수값 < 0 or 주식매수금지시작시간 < 0 or \
            주식매수금지종료시간 < 0 or 주식매수금지간격초 < 0 or 주식매수금지손절간격초 < 0 or 주식매수정정횟수 < 0 or \
            주식매수정정호가차이 < 0 or 주식매수정정호가 < 0:
        QMessageBox.critical(ui, '오류 알림', '지정가 호가 외 모든 입력값은 양수여야합니다.\n')
        return

    if 주식매수분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매수분할횟수는 10을 초과할 수 없습니다.\n')
        return

    if '해외선물' in ui.dict_set['증권사'] and 주식매수주문구분 not in ('시장가', '지정가'):
        QMessageBox.critical(ui, '오류 알림', '해외선물의 주문유형은 시장가 또는 지정가만 지원합니다.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['주식매수주문구분', '주식매수분할횟수', '주식매수분할방법', '주식매수분할시그널', '주식매수분할하방', '주식매수분할상방',
                   '주식매수분할하방수익률', '주식매수분할상방수익률', '주식매수분할고정수익률', '주식매수지정가기준가격', '주식매수지정가호가번호',
                   '주식매수시장가잔량범위', '주식매수취소관심이탈', '주식매수취소매도시그널', '주식매수취소시간', '주식매수취소시간초',
                   '주식매수금지블랙리스트', '주식매수금지라운드피겨', '주식매수금지라운드호가', '주식매수금지손절횟수', '주식매수금지손절횟수값',
                   '주식매수금지거래횟수', '주식매수금지거래횟수값', '주식매수금지시간', '주식매수금지시작시간', '주식매수금지종료시간',
                   '주식매수금지간격', '주식매수금지간격초', '주식매수금지손절간격', '주식매수금지손절간격초', '주식매수정정횟수',
                   '주식매수정정호가차이', '주식매수정정호가', '주식비중조절']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE stockbuyorder SET {set_txt}'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        ui.dict_set['주식매수주문구분'] = 주식매수주문구분
        ui.dict_set['주식매수분할횟수'] = 주식매수분할횟수
        ui.dict_set['주식매수분할방법'] = 주식매수분할방법
        ui.dict_set['주식매수분할시그널'] = 주식매수분할시그널
        ui.dict_set['주식매수분할하방'] = 주식매수분할하방
        ui.dict_set['주식매수분할상방'] = 주식매수분할상방
        ui.dict_set['주식매수분할하방수익률'] = 주식매수분할하방수익률
        ui.dict_set['주식매수분할상방수익률'] = 주식매수분할상방수익률
        ui.dict_set['주식매수분할고정수익률'] = 주식매수분할고정수익률
        ui.dict_set['주식매수지정가기준가격'] = 주식매수지정가기준가격
        ui.dict_set['주식매수지정가호가번호'] = 주식매수지정가호가번호
        ui.dict_set['주식매수시장가잔량범위'] = 주식매수시장가잔량범위
        ui.dict_set['주식매수취소관심이탈'] = 주식매수취소관심이탈
        ui.dict_set['주식매수취소매도시그널'] = 주식매수취소매도시그널
        ui.dict_set['주식매수취소시간'] = 주식매수취소시간
        ui.dict_set['주식매수취소시간초'] = 주식매수취소시간초
        ui.dict_set['주식매수금지블랙리스트'] = 주식매수금지블랙리스트
        ui.dict_set['주식매수금지라운드피겨'] = 주식매수금지라운드피겨
        ui.dict_set['주식매수금지라운드호가'] = 주식매수금지라운드호가
        ui.dict_set['주식매수금지손절횟수'] = 주식매수금지손절횟수
        ui.dict_set['주식매수금지손절횟수값'] = 주식매수금지손절횟수값
        ui.dict_set['주식매수금지거래횟수'] = 주식매수금지거래횟수
        ui.dict_set['주식매수금지거래횟수값'] = 주식매수금지거래횟수값
        ui.dict_set['주식매수금지시간'] = 주식매수금지시간
        ui.dict_set['주식매수금지시작시간'] = 주식매수금지시작시간
        ui.dict_set['주식매수금지종료시간'] = 주식매수금지종료시간
        ui.dict_set['주식매수금지간격'] = 주식매수금지간격
        ui.dict_set['주식매수금지간격초'] = 주식매수금지간격초
        ui.dict_set['주식매수금지손절간격'] = 주식매수금지손절간격
        ui.dict_set['주식매수금지손절간격초'] = 주식매수금지손절간격초
        ui.dict_set['주식매수정정횟수'] = 주식매수정정횟수
        ui.dict_set['주식매수정정호가차이'] = 주식매수정정호가차이
        ui.dict_set['주식매수정정호가'] = 주식매수정정호가
        ui.dict_set['주식비중조절'] = 주식비중조절_

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()


@error_decorator
def setting_order_save_02(ui):
    주식매도주문구분 = ''
    if ui.ss_sell_checkBox_01.isChecked(): 주식매도주문구분 = '시장가'
    if ui.ss_sell_checkBox_02.isChecked(): 주식매도주문구분 = '지정가'
    if ui.ss_sell_checkBox_03.isChecked(): 주식매도주문구분 = '최유리지정가'
    if ui.ss_sell_checkBox_04.isChecked(): 주식매도주문구분 = '최우선지정가'
    if ui.ss_sell_checkBox_05.isChecked(): 주식매도주문구분 = '지정가IOC'
    if ui.ss_sell_checkBox_06.isChecked(): 주식매도주문구분 = '시장가IOC'
    if ui.ss_sell_checkBox_07.isChecked(): 주식매도주문구분 = '최유리IOC'
    if ui.ss_sell_checkBox_08.isChecked(): 주식매도주문구분 = '지정가FOK'
    if ui.ss_sell_checkBox_09.isChecked(): 주식매도주문구분 = '시장가FOK'
    if ui.ss_sell_checkBox_10.isChecked(): 주식매도주문구분 = '최유리FOK'
    주식매도분할횟수 = ui.ss_sell_lineEdit_01.text()
    주식매도분할방법 = 0
    if ui.ss_sell_checkBox_11.isChecked(): 주식매도분할방법 = 1
    if ui.ss_sell_checkBox_12.isChecked(): 주식매도분할방법 = 2
    if ui.ss_sell_checkBox_13.isChecked(): 주식매도분할방법 = 3
    주식매도분할시그널 = 1 if ui.ss_sell_checkBox_14.isChecked() else 0
    주식매도분할하방 = 1 if ui.ss_sell_checkBox_15.isChecked() else 0
    주식매도분할상방 = 1 if ui.ss_sell_checkBox_16.isChecked() else 0
    주식매도분할하방수익률 = ui.ss_sell_lineEdit_02.text()
    주식매도분할상방수익률 = ui.ss_sell_lineEdit_03.text()
    주식매도지정가기준가격 = ui.ss_sell_comboBox_01.currentText()
    주식매도지정가호가번호 = ui.ss_sell_comboBox_02.currentText()
    주식매도시장가잔량범위 = ui.ss_sell_comboBox_03.currentText()
    주식매도취소관심진입 = 1 if ui.ss_sell_checkBox_17.isChecked() else 0
    주식매도취소매수시그널 = 1 if ui.ss_sell_checkBox_18.isChecked() else 0
    주식매도취소시간 = 1 if ui.ss_sell_checkBox_19.isChecked() else 0
    주식매도취소시간초 = ui.ss_sell_lineEdit_04.text()
    주식매도금지매수횟수 = 1 if ui.ss_sell_checkBox_20.isChecked() else 0
    주식매도금지매수횟수값 = ui.ss_sell_lineEdit_05.text()
    주식매도금지라운드피겨 = 1 if ui.ss_sell_checkBox_21.isChecked() else 0
    주식매도금지라운드호가 = ui.ss_sell_lineEdit_06.text()
    주식매도금지시간 = 1 if ui.ss_sell_checkBox_22.isChecked() else 0
    주식매도금지시작시간 = ui.ss_sell_lineEdit_07.text()
    주식매도금지종료시간 = ui.ss_sell_lineEdit_08.text()
    주식매도금지간격 = 1 if ui.ss_sell_checkBox_23.isChecked() else 0
    주식매도금지간격초 = ui.ss_sell_lineEdit_09.text()
    주식매도정정횟수 = ui.ss_sell_lineEdit_10.text()
    주식매도정정호가차이 = ui.ss_sell_comboBox_04.currentText()
    주식매도정정호가 = ui.ss_sell_comboBox_05.currentText()
    주식매도익절수익률청산 = 1 if ui.ss_sell_checkBox_24.isChecked() else 0
    주식매도익절수익률 = ui.ss_sell_lineEdit_11.text()
    주식매도익절수익금청산  = 1 if ui.ss_sell_checkBox_25.isChecked() else 0
    주식매도익절수익금 = ui.ss_sell_lineEdit_12.text()
    주식매도손절수익률청산 = 1 if ui.ss_sell_checkBox_26.isChecked() else 0
    주식매도손절수익률 = ui.ss_sell_lineEdit_13.text()
    주식매도손절수익금청산  = 1 if ui.ss_sell_checkBox_27.isChecked() else 0
    주식매도손절수익금 = ui.ss_sell_lineEdit_14.text()

    if '' in (주식매도주문구분, 주식매도분할횟수, 주식매도분할하방수익률, 주식매도분할상방수익률, 주식매도취소시간초, 주식매도금지매수횟수값,
              주식매도금지라운드호가, 주식매도금지시작시간, 주식매도금지종료시간, 주식매도금지간격초, 주식매도정정횟수, 주식매도익절수익률,
              주식매도익절수익금, 주식매도손절수익률, 주식매도손절수익금):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 주식매도분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매도방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (주식매도분할시그널, 주식매도분할하방, 주식매도분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매도방법이 선택되지 않았습니다.\n')
        return

    주식매도분할횟수, 주식매도분할하방수익률, 주식매도분할상방수익률, 주식매도지정가호가번호, 주식매도시장가잔량범위, 주식매도취소시간초, \
        주식매도금지매수횟수값, 주식매도금지라운드호가, 주식매도금지시작시간, 주식매도금지종료시간, 주식매도금지간격초, 주식매도정정횟수, \
        주식매도정정호가차이, 주식매도정정호가, 주식매도익절수익률, 주식매도익절수익금, 주식매도손절수익률, 주식매도손절수익금 = \
        int(주식매도분할횟수), float(주식매도분할하방수익률), float(주식매도분할상방수익률), int(주식매도지정가호가번호), \
        int(주식매도시장가잔량범위), int(주식매도취소시간초), int(주식매도금지매수횟수값), int(주식매도금지라운드호가), \
        int(주식매도금지시작시간), int(주식매도금지종료시간), int(주식매도금지간격초), int(주식매도정정횟수), \
        int(주식매도정정호가차이), int(주식매도정정호가), float(주식매도익절수익률), int(주식매도익절수익금), \
        float(주식매도손절수익률), int(주식매도손절수익금)

    if 주식매도분할횟수 < 0 or 주식매도분할하방수익률 < 0 or 주식매도분할상방수익률 < 0 or 주식매도취소시간초 < 0 or \
            주식매도금지매수횟수값 < 0 or 주식매도금지라운드호가 < 0 or 주식매도금지시작시간 < 0 or 주식매도금지종료시간 < 0 or \
            주식매도금지간격초 < 0 or 주식매도정정횟수 < 0 or 주식매도정정호가차이 < 0 or 주식매도정정호가 < 0 or \
            주식매도익절수익률 < 0 or 주식매도익절수익금 < 0 or 주식매도손절수익률 < 0 or 주식매도손절수익금 < 0:
        QMessageBox.critical(ui, '오류 알림', '모든 값은 양수로 입력하십시오.\n')
        return

    if 주식매도분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매도분할횟수는 10을 초과할 수 없습니다.\n')
        return

    if 주식매도금지매수횟수값 > 9:
        QMessageBox.critical(ui, '오류 알림', '매도금지 매수횟수는 10미만으로 입력하십시오.\n')
        return

    if '해외선물' in ui.dict_set['증권사'] and 주식매도주문구분 not in ('시장가', '지정가'):
        QMessageBox.critical(ui, '오류 알림', '해외선물의 주문유형은 시장가 또는 지정가만 지원합니다.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['주식매도주문구분', '주식매도분할횟수', '주식매도분할방법', '주식매도분할시그널', '주식매도분할하방', '주식매도분할상방',
                   '주식매도분할하방수익률', '주식매도분할상방수익률', '주식매도지정가기준가격', '주식매도지정가호가번호',
                   '주식매도시장가잔량범위', '주식매도취소관심진입', '주식매도취소매수시그널', '주식매도취소시간', '주식매도취소시간초',
                   '주식매도금지매수횟수', '주식매도금지매수횟수값', '주식매도금지라운드피겨', '주식매도금지라운드호가', '주식매도금지시간',
                   '주식매도금지시작시간', '주식매도금지종료시간', '주식매도금지간격', '주식매도금지간격초', '주식매도정정횟수',
                   '주식매도정정호가차이', '주식매도정정호가', '주식매도익절수익률청산', '주식매도익절수익률', '주식매도익절수익금청산',
                   '주식매도익절수익금', '주식매도손절수익률청산', '주식매도손절수익률', '주식매도손절수익금청산', '주식매도손절수익금']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE stocksellorder SET {set_txt}'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        ui.dict_set['주식매도주문구분'] = 주식매도주문구분
        ui.dict_set['주식매도분할횟수'] = 주식매도분할횟수
        ui.dict_set['주식매도분할방법'] = 주식매도분할방법
        ui.dict_set['주식매도분할시그널'] = 주식매도분할시그널
        ui.dict_set['주식매도분할하방'] = 주식매도분할하방
        ui.dict_set['주식매도분할상방'] = 주식매도분할상방
        ui.dict_set['주식매도분할하방수익률'] = 주식매도분할하방수익률
        ui.dict_set['주식매도분할상방수익률'] = 주식매도분할상방수익률
        ui.dict_set['주식매도지정가기준가격'] = 주식매도지정가기준가격
        ui.dict_set['주식매도지정가호가번호'] = 주식매도지정가호가번호
        ui.dict_set['주식매도시장가잔량범위'] = 주식매도시장가잔량범위
        ui.dict_set['주식매도취소관심진입'] = 주식매도취소관심진입
        ui.dict_set['주식매도취소매수시그널'] = 주식매도취소매수시그널
        ui.dict_set['주식매도취소시간'] = 주식매도취소시간
        ui.dict_set['주식매도취소시간초'] = 주식매도취소시간초
        ui.dict_set['주식매도금지매수횟수'] = 주식매도금지매수횟수
        ui.dict_set['주식매도금지매수횟수값'] = 주식매도금지매수횟수값
        ui.dict_set['주식매도금지라운드피겨'] = 주식매도금지라운드피겨
        ui.dict_set['주식매도금지라운드호가'] = 주식매도금지라운드호가
        ui.dict_set['주식매도금지시간'] = 주식매도금지시간
        ui.dict_set['주식매도금지시작시간'] = 주식매도금지시작시간
        ui.dict_set['주식매도금지종료시간'] = 주식매도금지종료시간
        ui.dict_set['주식매도금지간격'] = 주식매도금지간격
        ui.dict_set['주식매도금지간격초'] = 주식매도금지간격초
        ui.dict_set['주식매도정정횟수'] = 주식매도정정횟수
        ui.dict_set['주식매도정정호가차이'] = 주식매도정정호가차이
        ui.dict_set['주식매도정정호가'] = 주식매도정정호가
        ui.dict_set['주식매도익절수익률청산'] = 주식매도익절수익률청산
        ui.dict_set['주식매도익절수익률'] = 주식매도익절수익률
        ui.dict_set['주식매도익절수익금청산'] = 주식매도익절수익금청산
        ui.dict_set['주식매도익절수익금'] = 주식매도익절수익금
        ui.dict_set['주식매도손절수익률청산'] = 주식매도손절수익률청산
        ui.dict_set['주식매도손절수익률'] = 주식매도손절수익률
        ui.dict_set['주식매도손절수익금청산'] = 주식매도손절수익금청산
        ui.dict_set['주식매도손절수익금'] = 주식매도손절수익금

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()


@error_decorator
def setting_order_save_03(ui):
    코인매수주문구분 = ''
    if ui.sc_buyy_checkBox_01.isChecked(): 코인매수주문구분 = '시장가'
    if ui.sc_buyy_checkBox_02.isChecked(): 코인매수주문구분 = '지정가'
    if ui.sc_buyy_checkBox_03.isChecked(): 코인매수주문구분 = '지정가IOC'
    if ui.sc_buyy_checkBox_04.isChecked(): 코인매수주문구분 = '지정가FOK'
    코인매수분할횟수 = ui.sc_buyy_lineEdit_01.text()
    코인매수분할방법 = 0
    if ui.sc_buyy_checkBox_05.isChecked(): 코인매수분할방법 = 1
    if ui.sc_buyy_checkBox_06.isChecked(): 코인매수분할방법 = 2
    if ui.sc_buyy_checkBox_07.isChecked(): 코인매수분할방법 = 3
    코인매수분할시그널 = 1 if ui.sc_buyy_checkBox_08.isChecked() else 0
    코인매수분할하방 = 1 if ui.sc_buyy_checkBox_09.isChecked() else 0
    코인매수분할상방 = 1 if ui.sc_buyy_checkBox_10.isChecked() else 0
    코인매수분할하방수익률 = ui.sc_buyy_lineEdit_02.text()
    코인매수분할상방수익률 = ui.sc_buyy_lineEdit_03.text()
    코인매수지정가기준가격 = ui.sc_buyy_comboBox_01.currentText()
    코인매수지정가호가번호 = ui.sc_buyy_comboBox_02.currentText()
    코인매수시장가잔량범위 = ui.sc_buyy_comboBox_03.currentText()
    코인매수분할고정수익률 = 1 if ui.sc_buyy_checkBox_11.isChecked() else 0
    코인매수취소관심이탈 = 1 if ui.sc_buyy_checkBox_12.isChecked() else 0
    코인매수취소매도시그널 = 1 if ui.sc_buyy_checkBox_13.isChecked() else 0
    코인매수취소시간 = 1 if ui.sc_buyy_checkBox_14.isChecked() else 0
    코인매수취소시간초 = ui.sc_buyy_lineEdit_04.text()
    코인매수금지블랙리스트 = 1 if ui.sc_buyy_checkBox_15.isChecked() else 0
    코인매수금지200원이하 = 1 if ui.sc_buyy_checkBox_16.isChecked() else 0
    코인매수금지손절횟수 = 1 if ui.sc_buyy_checkBox_17.isChecked() else 0
    코인매수금지손절횟수값 = ui.sc_buyy_lineEdit_05.text()
    코인매수금지거래횟수 = 1 if ui.sc_buyy_checkBox_18.isChecked() else 0
    코인매수금지거래횟수값 = ui.sc_buyy_lineEdit_06.text()
    코인매수금지시간 = 1 if ui.sc_buyy_checkBox_19.isChecked() else 0
    코인매수금지시작시간 = ui.sc_buyy_lineEdit_07.text()
    코인매수금지종료시간 = ui.sc_buyy_lineEdit_08.text()
    코인매수금지간격 = 1 if ui.sc_buyy_checkBox_20.isChecked() else 0
    코인매수금지간격초 = ui.sc_buyy_lineEdit_09.text()
    코인매수금지손절간격 = 1 if ui.sc_buyy_checkBox_21.isChecked() else 0
    코인매수금지손절간격초 = ui.sc_buyy_lineEdit_10.text()
    코인매수정정횟수 = ui.sc_buyy_lineEdit_11.text()
    코인매수정정호가차이 = ui.sc_buyy_comboBox_04.currentText()
    코인매수정정호가 = ui.sc_buyy_comboBox_05.currentText()

    bjjj_list = []
    if ui.sc_bj_checkBoxxx_01.isChecked():   bjjj_list.append('0')
    elif ui.sc_bj_checkBoxxx_02.isChecked(): bjjj_list.append('1')
    elif ui.sc_bj_checkBoxxx_03.isChecked(): bjjj_list.append('2')
    elif ui.sc_bj_checkBoxxx_04.isChecked(): bjjj_list.append('3')
    elif ui.sc_bj_checkBoxxx_05.isChecked(): bjjj_list.append('4')
    elif ui.sc_bj_checkBoxxx_06.isChecked(): bjjj_list.append('5')

    save = True
    if ui.sc_bj_lineEdittt_01.text() == '': save = False
    if ui.sc_bj_lineEdittt_02.text() == '': save = False
    if ui.sc_bj_lineEdittt_03.text() == '': save = False
    if ui.sc_bj_lineEdittt_04.text() == '': save = False
    if ui.sc_bj_lineEdittt_05.text() == '': save = False
    if ui.sc_bj_lineEdittt_06.text() == '': save = False
    if ui.sc_bj_lineEdittt_07.text() == '': save = False
    if ui.sc_bj_lineEdittt_08.text() == '': save = False
    if ui.sc_bj_lineEdittt_09.text() == '': save = False

    if not save:
        QMessageBox.critical(ui, '오류 알림', '비중조절 세부설정값이 입력되지 않았습니다.\n')
        return

    bjjj_list.append(ui.sc_bj_lineEdittt_01.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_02.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_03.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_04.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_05.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_06.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_07.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_08.text())
    bjjj_list.append(ui.sc_bj_lineEdittt_09.text())
    코인비중조절 = ';'.join(bjjj_list)
    코인비중조절_ = [float(x) for x in bjjj_list]

    if '' in (코인매수주문구분, 코인매수분할횟수, 코인매수분할하방수익률, 코인매수분할상방수익률, 코인매수지정가호가번호, 코인매수시장가잔량범위,
              코인매수취소시간초, 코인매수금지손절횟수값, 코인매수금지거래횟수값, 코인매수금지시작시간, 코인매수금지종료시간, 코인매수금지간격초,
              코인매수금지손절간격초, 코인매수정정횟수):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 코인매수분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매수방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (코인매수분할시그널, 코인매수분할하방, 코인매수분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매수방법이 선택되지 않았습니다.\n')
        return

    코인매수분할횟수, 코인매수분할하방수익률, 코인매수분할상방수익률, 코인매수지정가호가번호, 코인매수시장가잔량범위, 코인매수취소시간초, \
        코인매수금지손절횟수값, 코인매수금지거래횟수값, 코인매수금지시작시간, 코인매수금지종료시간, 코인매수금지간격초, 코인매수금지손절간격초, \
        코인매수정정횟수, 코인매수정정호가차이, 코인매수정정호가 = \
        int(코인매수분할횟수), float(코인매수분할하방수익률), float(코인매수분할상방수익률), int(코인매수지정가호가번호), \
        int(코인매수시장가잔량범위), int(코인매수취소시간초), int(코인매수금지손절횟수값), int(코인매수금지거래횟수값), \
        int(코인매수금지시작시간), int(코인매수금지종료시간), int(코인매수금지간격초), int(코인매수금지손절간격초), int(코인매수정정횟수), \
        int(코인매수정정호가차이), int(코인매수정정호가)

    if 코인매수분할횟수 < 0 or 코인매수분할하방수익률 < 0 or 코인매수분할상방수익률 < 0 or 코인매수시장가잔량범위 < 0 or \
            코인매수취소시간초 < 0 or 코인매수금지손절횟수값 < 0 or 코인매수금지거래횟수값 < 0 or 코인매수금지시작시간 < 0 or \
            코인매수금지종료시간 < 0 or 코인매수금지간격초 < 0 or 코인매수금지손절간격초 < 0:
        QMessageBox.critical(ui, '오류 알림', '지정가 호가 외 모든 입력값은 양수여야합니다.\n')
        return

    if 코인매수분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매수분할횟수는 10를 초과할 수 없습니다.\n')
        return

    if ui.dict_set['거래소'] == '업비트' and 코인매수주문구분 not in ('시장가', '지정가'):
        QMessageBox.critical(ui, '오류 알림', '업비트의 주문유형은 시장가 또는 지정가만 지원합니다.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['코인매수주문구분', '코인매수분할횟수', '코인매수분할방법', '코인매수분할시그널', '코인매수분할하방', '코인매수분할상방',
                   '코인매수분할하방수익률', '코인매수분할상방수익률', '코인매수분할고정수익률', '코인매수지정가기준가격', '코인매수지정가호가번호',
                   '코인매수시장가잔량범위', '코인매수취소관심이탈', '코인매수취소매도시그널', '코인매수취소시간', '코인매수취소시간초',
                   '코인매수금지블랙리스트', '코인매수금지200원이하', '코인매수금지손절횟수', '코인매수금지손절횟수값', '코인매수금지거래횟수',
                   '코인매수금지거래횟수값', '코인매수금지시간', '코인매수금지시작시간', '코인매수금지종료시간', '코인매수금지간격',
                   '코인매수금지간격초', '코인매수금지손절간격', '코인매수금지손절간격초', '코인매수정정횟수', '코인매수정정호가차이',
                   '코인매수정정호가', '코인비중조절']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE coinbuyorder SET {set_txt}'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        ui.dict_set['코인매수주문구분'] = 코인매수주문구분
        ui.dict_set['코인매수분할횟수'] = 코인매수분할횟수
        ui.dict_set['코인매수분할방법'] = 코인매수분할방법
        ui.dict_set['코인매수분할시그널'] = 코인매수분할시그널
        ui.dict_set['코인매수분할하방'] = 코인매수분할하방
        ui.dict_set['코인매수분할상방'] = 코인매수분할상방
        ui.dict_set['코인매수분할하방수익률'] = 코인매수분할하방수익률
        ui.dict_set['코인매수분할상방수익률'] = 코인매수분할상방수익률
        ui.dict_set['코인매수분할고정수익률'] = 코인매수분할고정수익률
        ui.dict_set['코인매수지정가기준가격'] = 코인매수지정가기준가격
        ui.dict_set['코인매수지정가호가번호'] = 코인매수지정가호가번호
        ui.dict_set['코인매수시장가잔량범위'] = 코인매수시장가잔량범위
        ui.dict_set['코인매수취소관심이탈'] = 코인매수취소관심이탈
        ui.dict_set['코인매수취소매도시그널'] = 코인매수취소매도시그널
        ui.dict_set['코인매수취소시간'] = 코인매수취소시간
        ui.dict_set['코인매수취소시간초'] = 코인매수취소시간초
        ui.dict_set['코인매수금지블랙리스트'] = 코인매수금지블랙리스트
        ui.dict_set['코인매수금지200원이하'] = 코인매수금지200원이하
        ui.dict_set['코인매수금지손절횟수'] = 코인매수금지손절횟수
        ui.dict_set['코인매수금지손절횟수값'] = 코인매수금지손절횟수값
        ui.dict_set['코인매수금지거래횟수'] = 코인매수금지거래횟수
        ui.dict_set['코인매수금지거래횟수값'] = 코인매수금지거래횟수값
        ui.dict_set['코인매수금지시간'] = 코인매수금지시간
        ui.dict_set['코인매수금지시작시간'] = 코인매수금지시작시간
        ui.dict_set['코인매수금지종료시간'] = 코인매수금지종료시간
        ui.dict_set['코인매수금지간격'] = 코인매수금지간격
        ui.dict_set['코인매수금지간격초'] = 코인매수금지간격초
        ui.dict_set['코인매수금지손절간격'] = 코인매수금지손절간격
        ui.dict_set['코인매수금지손절간격초'] = 코인매수금지손절간격초
        ui.dict_set['코인매수정정횟수'] = 코인매수정정횟수
        ui.dict_set['코인매수정정호가차이'] = 코인매수정정호가차이
        ui.dict_set['코인매수정정호가'] = 코인매수정정호가
        ui.dict_set['코인비중조절'] = 코인비중조절_

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()


@error_decorator
def setting_order_save_04(ui):
    코인매도주문구분 = ''
    if ui.sc_sell_checkBox_01.isChecked(): 코인매도주문구분 = '시장가'
    if ui.sc_sell_checkBox_02.isChecked(): 코인매도주문구분 = '지정가'
    if ui.sc_sell_checkBox_03.isChecked(): 코인매도주문구분 = '시장가IOC'
    if ui.sc_sell_checkBox_04.isChecked(): 코인매도주문구분 = '지정가FOK'
    코인매도분할횟수 = ui.sc_sell_lineEdit_01.text()
    코인매도분할방법 = 0
    if ui.sc_sell_checkBox_05.isChecked(): 코인매도분할방법 = 1
    if ui.sc_sell_checkBox_06.isChecked(): 코인매도분할방법 = 2
    if ui.sc_sell_checkBox_07.isChecked(): 코인매도분할방법 = 3
    코인매도분할시그널 = 1 if ui.sc_sell_checkBox_08.isChecked() else 0
    코인매도분할하방 = 1 if ui.sc_sell_checkBox_09.isChecked() else 0
    코인매도분할상방 = 1 if ui.sc_sell_checkBox_10.isChecked() else 0
    코인매도분할하방수익률 = ui.sc_sell_lineEdit_02.text()
    코인매도분할상방수익률 = ui.sc_sell_lineEdit_03.text()
    코인매도지정가기준가격 = ui.sc_sell_comboBox_01.currentText()
    코인매도지정가호가번호 = ui.sc_sell_comboBox_02.currentText()
    코인매도시장가잔량범위 = ui.sc_sell_comboBox_03.currentText()
    코인매도취소관심진입 = 1 if ui.sc_sell_checkBox_11.isChecked() else 0
    코인매도취소매수시그널 = 1 if ui.sc_sell_checkBox_12.isChecked() else 0
    코인매도취소시간 = 1 if ui.sc_sell_checkBox_13.isChecked() else 0
    코인매도취소시간초 = ui.sc_sell_lineEdit_04.text()
    코인매도금지매수횟수 = 1 if ui.sc_sell_checkBox_14.isChecked() else 0
    코인매도금지매수횟수값 = ui.sc_sell_lineEdit_05.text()
    코인매도금지시간 = 1 if ui.sc_sell_checkBox_15.isChecked() else 0
    코인매도금지시작시간 = ui.sc_sell_lineEdit_06.text()
    코인매도금지종료시간 = ui.sc_sell_lineEdit_07.text()
    코인매도금지간격 = 1 if ui.sc_sell_checkBox_16.isChecked() else 0
    코인매도금지간격초 = ui.sc_sell_lineEdit_08.text()
    코인매도정정횟수 = ui.sc_sell_lineEdit_09.text()
    코인매도정정호가차이 = ui.sc_sell_comboBox_04.currentText()
    코인매도정정호가 = ui.sc_sell_comboBox_05.currentText()
    코인매도익절수익률청산 = 1 if ui.sc_sell_checkBox_17.isChecked() else 0
    코인매도익절수익률 = ui.sc_sell_lineEdit_10.text()
    코인매도익절수익금청산 = 1 if ui.sc_sell_checkBox_18.isChecked() else 0
    코인매도익절수익금 = ui.sc_sell_lineEdit_11.text()
    코인매도손절수익률청산 = 1 if ui.sc_sell_checkBox_19.isChecked() else 0
    코인매도손절수익률 = ui.sc_sell_lineEdit_12.text()
    코인매도손절수익금청산 = 1 if ui.sc_sell_checkBox_20.isChecked() else 0
    코인매도손절수익금 = ui.sc_sell_lineEdit_13.text()

    if '' in (코인매도주문구분, 코인매도분할횟수, 코인매도분할하방수익률, 코인매도분할상방수익률, 코인매도취소시간초, 코인매도금지매수횟수값,
              코인매도금지시작시간, 코인매도금지종료시간, 코인매도금지간격초, 코인매도정정횟수, 코인매도익절수익률, 코인매도익절수익금,
              코인매도손절수익률, 코인매도손절수익금):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 코인매도분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매도방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (코인매도분할시그널, 코인매도분할하방, 코인매도분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매도방법이 선택되지 않았습니다.\n')
        return

    코인매도분할횟수, 코인매도분할하방수익률, 코인매도분할상방수익률, 코인매도지정가호가번호, 코인매도시장가잔량범위, 코인매도취소시간초, \
        코인매도금지매수횟수값, 코인매도금지시작시간, 코인매도금지종료시간, 코인매도금지간격초, 코인매도정정횟수, 코인매도정정호가차이, \
        코인매도정정호가, 코인매도익절수익률, 코인매도익절수익금, 코인매도손절수익률, 코인매도손절수익금 = \
        int(코인매도분할횟수), float(코인매도분할하방수익률), float(코인매도분할상방수익률), int(코인매도지정가호가번호), \
        int(코인매도시장가잔량범위), int(코인매도취소시간초), int(코인매도금지매수횟수값), int(코인매도금지시작시간), \
        int(코인매도금지종료시간), int(코인매도금지간격초), int(코인매도정정횟수), float(코인매도정정호가차이), \
        int(코인매도정정호가), float(코인매도익절수익률), int(코인매도익절수익금), float(코인매도손절수익률), int(코인매도손절수익금)

    if 코인매도분할횟수 < 0 or 코인매도분할하방수익률 < 0 or 코인매도분할상방수익률 < 0 or 코인매도취소시간초 < 0 or \
            코인매도금지매수횟수값 < 0 or 코인매도금지시작시간 < 0 or 코인매도금지종료시간 < 0 or 코인매도금지간격초 < 0 or \
            코인매도정정횟수 < 0 or 코인매도정정호가차이 < 0 or 코인매도정정호가 < 0 or 코인매도익절수익률 < 0 or \
            코인매도익절수익금 < 0 or 코인매도손절수익률 < 0 or 코인매도손절수익금 < 0:
        QMessageBox.critical(ui, '오류 알림', '모든 값은 양수로 입력하십시오.\n')
        return

    if 코인매도분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매도분할횟수는 10을 초과할 수 없습니다.\n')
        return

    if 코인매도금지매수횟수값 > 9:
        QMessageBox.critical(ui, '오류 알림', '매도금지 매수횟수는 10미만으로 입력하십시오.\n')
        return

    if ui.dict_set['거래소'] == '업비트' and 코인매도주문구분 not in ('시장가', '지정가'):
        QMessageBox.critical(ui, '오류 알림', '업비트의 주문유형은 시장가 또는 지정가만 지원합니다.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['코인매도주문구분', '코인매도분할횟수', '코인매도분할방법', '코인매도분할시그널', '코인매도분할하방', '코인매도분할상방',
                   '코인매도분할하방수익률', '코인매도분할상방수익률', '코인매도지정가기준가격', '코인매도지정가호가번호', '코인매도시장가잔량범위',
                   '코인매도취소관심진입', '코인매도취소매수시그널', '코인매도취소시간', '코인매도취소시간초', '코인매도금지매수횟수',
                   '코인매도금지매수횟수값', '코인매도금지시간', '코인매도금지시작시간', '코인매도금지종료시간', '코인매도금지간격',
                   '코인매도금지간격초', '코인매도정정횟수', '코인매도정정호가차이', '코인매도정정호가', '코인매도익절수익률청산',
                   '코인매도익절수익률', '코인매도익절수익금청산', '코인매도익절수익금', '코인매도손절수익률청산', '코인매도손절수익률',
                   '코인매도손절수익금청산', '코인매도손절수익금']
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE coinsellorder SET {set_txt}'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns)
        ui.queryQ.put(('설정디비', query, values))

        ui.dict_set['코인매도주문구분'] = 코인매도주문구분
        ui.dict_set['코인매도분할횟수'] = 코인매도분할횟수
        ui.dict_set['코인매도분할방법'] = 코인매도분할방법
        ui.dict_set['코인매도분할시그널'] = 코인매도분할시그널
        ui.dict_set['코인매도분할하방'] = 코인매도분할하방
        ui.dict_set['코인매도분할상방'] = 코인매도분할상방
        ui.dict_set['코인매도분할하방수익률'] = 코인매도분할하방수익률
        ui.dict_set['코인매도분할상방수익률'] = 코인매도분할상방수익률
        ui.dict_set['코인매도지정가기준가격'] = 코인매도지정가기준가격
        ui.dict_set['코인매도지정가호가번호'] = 코인매도지정가호가번호
        ui.dict_set['코인매도시장가잔량범위'] = 코인매도시장가잔량범위
        ui.dict_set['코인매도취소관심진입'] = 코인매도취소관심진입
        ui.dict_set['코인매도취소매수시그널'] = 코인매도취소매수시그널
        ui.dict_set['코인매도취소시간'] = 코인매도취소시간
        ui.dict_set['코인매도취소시간초'] = 코인매도취소시간초
        ui.dict_set['코인매도금지매수횟수'] = 코인매도금지매수횟수
        ui.dict_set['코인매도금지매수횟수값'] = 코인매도금지매수횟수값
        ui.dict_set['코인매도금지시간'] = 코인매도금지시간
        ui.dict_set['코인매도금지시작시간'] = 코인매도금지시작시간
        ui.dict_set['코인매도금지종료시간'] = 코인매도금지종료시간
        ui.dict_set['코인매도금지간격'] = 코인매도금지간격
        ui.dict_set['코인매도금지간격초'] = 코인매도금지간격초
        ui.dict_set['코인매도정정횟수'] = 코인매도정정횟수
        ui.dict_set['코인매도정정호가차이'] = 코인매도정정호가차이
        ui.dict_set['코인매도정정호가'] = 코인매도정정호가
        ui.dict_set['코인매도익절수익률청산'] = 코인매도익절수익률청산
        ui.dict_set['코인매도익절수익률'] = 코인매도익절수익률
        ui.dict_set['코인매도익절수익금청산'] = 코인매도익절수익금청산
        ui.dict_set['코인매도익절수익금'] = 코인매도익절수익금
        ui.dict_set['코인매도손절수익률청산'] = 코인매도손절수익률청산
        ui.dict_set['코인매도손절수익률'] = 코인매도손절수익률
        ui.dict_set['코인매도손절수익금청산'] = 코인매도손절수익금청산
        ui.dict_set['코인매도손절수익금'] = 코인매도손절수익금

        QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
        ui.UpdateDictSet()


def setting_all_load(ui):
    LoadSettings(ui)


@error_decorator
def setting_all_app(ui):
    name = ui.sj_set_comBoxx_01.currentText()
    if name == '':
        QMessageBox.critical(ui, '오류 알림', '설정이름이 선택되지 않았습니다.\n')
        return

    origin_file = f'{DB_PATH}/setting_{name}.db'
    copy_file = f'{DB_PATH}/setting.db'
    file_list = os.listdir(DB_PATH)
    if f'setting_{name}.db' not in file_list:
        QMessageBox.critical(ui, '오류 알림', '설정파일이 존재하지 않았습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        ui.queryQ.put(('설정파일변경', origin_file, copy_file))
        qtest_qwait(2)
        ui.SettingLoad_01()
        ui.SettingLoad_02()
        ui.SettingLoad_03()
        ui.SettingLoad_04()
        ui.SettingLoad_05()
        ui.SettingLoad_06()
        ui.SettingLoad_07()
        ui.SettingLoad_08()
        ui.SettingOrderLoad_01()
        ui.SettingOrderLoad_02()
        ui.SettingOrderLoad_03()
        ui.SettingOrderLoad_04()
        ui.SettingSave_01()
        ui.SettingSave_02()
        ui.SettingSave_03()
        ui.SettingSave_04()
        ui.SettingSave_05()
        ui.SettingSave_06()
        ui.SettingSave_07()
        ui.SettingSave_08()
        ui.SettingOrderSave_01()
        ui.SettingOrderSave_02()
        ui.SettingOrderSave_03()
        ui.SettingOrderSave_04()
        QMessageBox.information(ui, '모든 설정 적용 완료', random.choice(famous_saying))


@error_decorator
def setting_all_del(ui):
    name = ui.sj_set_comBoxx_01.currentText()
    if name == '':
        QMessageBox.critical(ui, '오류 알림', '설정이름이 선택되지 않았습니다.\n')
        return

    remove_file = f'{DB_PATH}/setting_{name}.db'
    os.remove(remove_file)
    LoadSettings(ui)
    QMessageBox.information(ui, '삭제 완료', random.choice(famous_saying))


@error_decorator
def setting_all_save(ui):
    name = ui.sj_set_liEditt_01.text()
    if name == '':
        QMessageBox.critical(ui, '오류 알림', '설정이름이 입력되지 않았습니다.\n')
        return

    origin_file = f'{DB_PATH}/setting.db'
    copy_file = f'{DB_PATH}/setting_{name}.db'
    shutil.copy(origin_file, copy_file)
    LoadSettings(ui)
    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def setting_stock_elapsed_tick_number(ui):
    ui.dialog_setsj.show() if not ui.dialog_setsj.isVisible() else ui.dialog_setsj.close()


@error_decorator
def setting_coin_elapsed_tick_number(ui):
    ui.dialog_cetsj.show() if not ui.dialog_cetsj.isVisible() else ui.dialog_cetsj.close()


@error_decorator
def LoadSettings(ui):
    ui.sj_set_comBoxx_01.clear()
    file_list = os.listdir(DB_PATH)
    file_list = [x for x in file_list if 'setting_' in x]
    for file_name in file_list:
        name = file_name.replace('setting_', '').replace('.db', '')
        ui.sj_set_comBoxx_01.addItem(name)
