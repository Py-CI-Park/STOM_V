
def setting_load_01(ui):
    """기본 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.static_method.static import de_text

    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM main').set_index('index')
    ui.sj_main_comBox_01.setCurrentText(df['거래소'][0])
    ui.sj_main_cheBox_01.setChecked(True) if df['모의투자'][0] else ui.sj_main_cheBox_01.setChecked(False)
    ui.sj_main_cheBox_02.setChecked(True) if df['데이터저장'][0] else ui.sj_main_cheBox_02.setChecked(False)
    ui.sj_main_cheBox_03.setChecked(True) if df['알림소리'][0] else ui.sj_main_cheBox_04.setChecked(False)
    ui.sj_main_comBox_02.setCurrentText('1초스냅샷' if df['타임프레임'][0] else '1분봉')
    ui.sj_main_liEdit_01.setText(de_text(ui.dict_set['키'], df['프로그램비밀번호'][0]) if df['프로그램비밀번호'][0] else '')
    ui.sj_main_comBox_03.setCurrentText('격리' if df['바이낸스선물마진타입'][0] == 'ISOLATED' else '교차')
    ui.sj_main_comBox_04.setCurrentText('단방향' if df['바이낸스선물포지션'][0] == 'false' else '양방향')


def setting_load_02(ui):
    """계정 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import de_text

    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM account').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    access_key = df['access_key'][no]
    secret_key = df['secret_key'][no]

    if access_key and secret_key:
        ui.sj_accc_liEdit_01.setText(de_text(ui.dict_set['키'], access_key))
        ui.sj_accc_liEdit_02.setText(de_text(ui.dict_set['키'], secret_key))
    else:
        ui.sj_accc_liEdit_01.clear()
        ui.sj_accc_liEdit_02.clear()
        QMessageBox.critical(ui, '오류 알림', '계정 설정값이\n존재하지 않습니다.\n')


def setting_load_03(ui):
    """텔레그램 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import de_text

    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM telegram').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    bot_token = df['bot_token'][no]
    chatingid = df['chatingid'][no]

    if bot_token and chatingid:
        ui.sj_tele_liEdit_01.setText(de_text(ui.dict_set['키'], bot_token))
        ui.sj_tele_liEdit_02.setText(de_text(ui.dict_set['키'], chatingid))
    else:
        ui.sj_tele_liEdit_01.clear()
        ui.sj_tele_liEdit_02.clear()
        QMessageBox.critical(ui, '오류 알림', '텔레그램 봇토큰 및 사용자 아이디\n설정값이 존재하지 않습니다.\n')


def setting_load_04(ui):
    """전략 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox

    df   = ui.dbreader.read_sql('설정디비', 'SELECT * FROM strategy').set_index('index')
    dfb  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_buy").set_index('index')
    dfs  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_sell").set_index('index')
    dfob = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optibuy").set_index('index')
    dfos = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optisell").set_index('index')
    no   = int(ui.dict_set['거래소'][-2:])

    ui.sj_strgy_ckBox_01.setChecked(True) if df['잔고청산'][no] else ui.sj_strgy_ckBox_01.setChecked(False)
    ui.sj_strgy_ckBox_02.setChecked(True) if df['프로세스종료'][no] else ui.sj_strgy_ckBox_02.setChecked(False)
    ui.sj_strgy_ckBox_03.setChecked(True) if df['컴퓨터종료'][no] else ui.sj_strgy_ckBox_03.setChecked(False)
    ui.sj_strgy_ckBox_04.setChecked(True) if df['투자금고정'][no] else ui.sj_strgy_ckBox_04.setChecked(False)
    ui.sj_strgy_ckBox_05.setChecked(True) if df['손실중지'][no] else ui.sj_strgy_ckBox_05.setChecked(False)
    ui.sj_strgy_ckBox_06.setChecked(True) if df['수익중지'][no] else ui.sj_strgy_ckBox_06.setChecked(False)
    ui.sj_strgy_lEdit_01.setText(str(df['평균값계산틱수'][no]))
    ui.sj_strgy_lEdit_02.setText(str(df['최대매수종목수'][no]))
    ui.sj_strgy_lEdit_03.setText(str(df['전략종료시간'][no]))
    ui.sj_strgy_cbBox_01.clear()
    ui.sj_strgy_cbBox_02.clear()
    ui.sj_strgy_cbBox_01.addItem('사용안함')
    ui.sj_strgy_cbBox_02.addItem('사용안함')

    if len(dfb) > 0:
        stg_list = list(dfb.index)
        stg_list.sort()
        for stg in stg_list:
            ui.sj_strgy_cbBox_01.addItem(stg)

    if len(dfob) > 0:
        stg_list = list(dfob.index)
        stg_list.sort()
        for stg in stg_list:
            ui.sj_strgy_cbBox_01.addItem(stg)

    if df['매수전략'][no]:
        ui.sj_strgy_cbBox_01.setCurrentText(df['매수전략'][no])

    if len(dfs) > 0:
        stg_list = list(dfs.index)
        stg_list.sort()
        for stg in stg_list:
            ui.sj_strgy_cbBox_02.addItem(stg)

    if len(dfos) > 0:
        stg_list = list(dfos.index)
        stg_list.sort()
        for stg in stg_list:
            ui.sj_strgy_cbBox_02.addItem(stg)

    if df['매도전략'][no]:
        ui.sj_strgy_cbBox_02.setCurrentText(df['매도전략'][no])

    ui.sj_strgy_lEdit_04.setText(str(df['투자금'][no]))
    ui.sj_strgy_lEdit_05.setText(str(df['손실중지수익률'][no]))
    ui.sj_strgy_lEdit_06.setText(str(df['수익중지수익률'][no]))
    time_limit = ui.market_info['프로세스종료시간'] - 30
    if ui.market_gubun != 7 and df['전략종료시간'][no] > time_limit:
        QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 전략종료시간은 {time_limit}을 초과할 수 없습니다.\n")


def setting_load_05(ui):
    """백테스트 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import QDate

    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM back').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    ui.sj_back_cheBox_01.setChecked(True) if df['블랙리스트추가'][no] else ui.sj_back_cheBox_01.setChecked(False)
    ui.sj_back_cheBox_02.setChecked(True) if df['백테일괄로딩'][no] else ui.sj_back_cheBox_02.setChecked(False)
    ui.sj_back_cheBox_03.setChecked(True) if not df['백테일괄로딩'][no] else ui.sj_back_cheBox_03.setChecked(False)
    ui.sj_back_cheBox_04.setChecked(True) if df['디비자동관리'][no] else ui.sj_back_cheBox_04.setChecked(False)
    ui.sj_back_cheBox_05.setChecked(True) if df['백테주문관리적용'][no] else ui.sj_back_cheBox_05.setChecked(False)
    ui.sj_back_cheBox_06.setChecked(True) if df['교차검증가중치'][no] else ui.sj_back_cheBox_06.setChecked(False)
    ui.sj_back_cheBox_07.setChecked(True) if df['범위자동관리'][no] else ui.sj_back_cheBox_07.setChecked(False)
    ui.sj_back_cheBox_08.setChecked(True) if df['자동학습'][no] else ui.sj_back_cheBox_08.setChecked(False)
    ui.sj_back_cheBox_09.setChecked(True) if df['백테스트로그기록안함'][no] else ui.sj_back_cheBox_09.setChecked(False)
    ui.sj_back_cheBox_10.setChecked(True) if df['시장미시구조분석'][no] else ui.sj_back_cheBox_10.setChecked(False)
    ui.sj_back_cheBox_11.setChecked(True) if df['리스크분석'][no] else ui.sj_back_cheBox_11.setChecked(False)
    ui.sj_back_cheBox_12.setChecked(True) if df['패턴분석'][no] else ui.sj_back_cheBox_12.setChecked(False)
    ui.sj_back_cheBox_13.setChecked(True) if df['가격대분석'][no] else ui.sj_back_cheBox_13.setChecked(False)
    ui.sj_back_cheBox_14.setChecked(True) if df['백테매수시간기준'][no] else ui.sj_back_cheBox_14.setChecked(False)
    ui.sj_back_liEdit_01.setText(str(df['기준값최소상승률'][no]))
    ui.sj_back_cheBox_15.setChecked(True) if df['그래프저장하지않기'][no] else ui.sj_back_cheBox_15.setChecked(False)
    ui.sj_back_cheBox_16.setChecked(True) if df['그래프띄우지않기'][no] else ui.sj_back_cheBox_16.setChecked(False)
    ui.sj_back_cheBox_17.setChecked(True) if df['백테스케쥴실행'][no] else ui.sj_back_cheBox_17.setChecked(False)
    ui.sj_back_cheBox_18.setChecked(True) if not df['백테날짜고정'][no] else ui.sj_back_cheBox_18.setChecked(False)
    ui.sj_back_cheBox_19.setChecked(True) if df['백테날짜고정'][no] else ui.sj_back_cheBox_19.setChecked(False)
    ui.sj_back_comBox_02.clear()
    dfs = ui.dbreader.read_sql('전략디비', 'SELECT * FROM schedule').set_index('index')
    indexs = list(dfs.index)
    indexs.sort()

    for index in indexs:
        ui.sj_back_comBox_02.addItem(index)

    if df['백테스케쥴요일'][no] == 4:
        ui.sj_back_comBox_01.setCurrentText('금')
    elif df['백테스케쥴요일'][no] == 5:
        ui.sj_back_comBox_01.setCurrentText('토')
    elif df['백테스케쥴요일'][no] == 6:
        ui.sj_back_comBox_01.setCurrentText('일')

    ui.sj_back_liEdit_02.setText(str(df['백테스케쥴시간'][no]))
    ui.sj_back_comBox_02.setCurrentText(df['백테스케쥴명'][no])

    if df['백테날짜고정'][no]:
        ui.sj_back_daEdit_01.setDate(QDate.fromString(ui.dict_set['백테날짜'], 'yyyyMMdd'))
    else:
        ui.sj_back_liEdit_03.setText(df['백테날짜'][no])


def setting_load_06(ui):
    """기타 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.static_method.static import de_text

    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM etc').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    ui.sj_etc_comBoxx_01.setCurrentText(df['테마'][no])
    ui.sj_etc_checBox_02.setChecked(True) if df['저해상도'][no] else ui.sj_etc_checBox_02.setChecked(False)
    ui.sj_etc_checBox_03.setChecked(True) if df['스톰라이브'][no] else ui.sj_etc_checBox_03.setChecked(False)
    ui.sj_etc_checBox_04.setChecked(True) if df['휴무프로세스종료'][no] else ui.sj_etc_checBox_04.setChecked(False)
    ui.sj_etc_checBox_05.setChecked(True) if df['휴무컴퓨터종료'][no] else ui.sj_etc_checBox_05.setChecked(False)
    ui.sj_etc_checBox_06.setChecked(True) if df['웹대시보드'][no] else ui.sj_etc_checBox_06.setChecked(False)
    ui.sj_etc_checBox_07.setChecked(True) if df['창위치기억'][no] else ui.sj_etc_checBox_07.setChecked(False)
    ui.sj_etc_checBox_08.setChecked(True) if df['프로그램종료'][no] else ui.sj_etc_checBox_08.setChecked(False)
    ui.sj_etc_liEditt_02.setText(str(df['웹대시보드포트번호'][no]))

    if df['시리얼키'][no]:
        ui.sj_etc_liEditt_01.setText(de_text(ui.dict_set['키'], df['시리얼키'][no]))


def settings_save_completed(ui):
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.etcetera.etc import update_dictset
    from ui.create_widget.set_text import famous_saying

    _ = ui.testQ.get()
    update_dictset(ui, force=True)
    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def setting_save_01(ui):
    """기본 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import en_text, qtest_qwait

    이전거래소 = ui.dict_set['거래소']
    이전타임프레임 = ui.dict_set['타임프레임']

    거래소 = ui.sj_main_comBox_01.currentText()
    모의투자 = 1 if ui.sj_main_cheBox_01.isChecked() else 0
    데이터저장 = 1 if ui.sj_main_cheBox_02.isChecked() else 0
    타임프레임 = 1 if ui.sj_main_comBox_02.currentText() == '1초스냅샷' else 0

    if ui.trading and 이전거래소 != 거래소:
        QMessageBox.critical(ui, '오류 알림', '매매 중에는 거래소 설정을 변경할 수 없습니다.\n')
        return

    if ui.trading and 이전타임프레임 != 타임프레임:
        QMessageBox.critical(ui, '오류 알림', '매매 중에는 타임프레임 설정을 변경할 수 없습니다.\n')
        return

    프로그램비밀번호_ = ui.sj_main_liEdit_01.text()
    바이낸스선물마진타입 = 'ISOLATED' if ui.sj_main_comBox_03.currentText() == '격리' else 'CROSSED'
    바이낸스선물포지션 = 'false' if ui.sj_main_comBox_04.currentText() == '단방향' else 'true'

    pass_check = True
    if ui.dict_set['프로그램비밀번호'] != '' and ui.dict_set['프로그램비밀번호'] != 프로그램비밀번호_:
        ui.pa_lineEditttt_01.clear()
        ui.pa_labelllllll_01.setText('비밀번호가 변경되었습니다.\n이전 비밀번호를 입력하십시오.\n')
        ui.dialog_pass.show()
        while ui.dialog_pass.isVisible():
            qtest_qwait(0.1)
        if ui.pa_lineEditttt_01.text() != ui.dict_set['프로그램비밀번호']:
            pass_check = False

    if pass_check:
        if ui.proc_chqs.is_alive():
            프로그램비밀번호 = en_text(ui.dict_set['키'], 프로그램비밀번호_) if 프로그램비밀번호_ else ''
            columns = ['거래소', '모의투자', '데이터저장', '타임프레임', '프로그램비밀번호', '바이낸스선물마진타입', '바이낸스선물포지션']
            set_txt = ', '.join([f'{col} = ?' for col in columns])
            query = f'UPDATE main SET {set_txt}'
            localvs = locals()
            values = tuple(localvs[col] for col in columns)
            ui.queryQ.put(('설정디비', query, values))
            settings_save_completed(ui)

            from ui.etcetera.etc import strategy_setting_label_change
            strategy_setting_label_change(ui)
            setting_load_02(ui)
            setting_load_03(ui)
            setting_load_04(ui)
            setting_load_05(ui)
            setting_load_06(ui)
            setting_order_load_01(ui)
            setting_order_load_02(ui)

    else:
        QMessageBox.critical(ui, '오류 알림', '이전 비밀번호을 잘못입력하여\n기본설정을 변경할 수 없습니다.\n')

    ui.pa_labelllllll_01.setText('프로그램 비밀번호을 입력하십시오.\n미설정 시 입력없이 엔터!!\n')


def setting_save_02(ui):
    """계정 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import en_text

    access_key = ui.sj_accc_liEdit_01.text()
    secret_key = ui.sj_accc_liEdit_02.text()

    if '' in (access_key, secret_key):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        no = int(ui.sj_main_comBox_01.currentText()[-2:])
        en_access_key = en_text(ui.dict_set['키'], access_key)
        en_secret_key = en_text(ui.dict_set['키'], secret_key)
        query  = 'UPDATE account SET access_key = ?, secret_key = ? WHERE `index` = ?'
        values = (en_access_key, en_secret_key, no)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)


def setting_save_03(ui):
    """텔레그램 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import en_text

    bot_token = ui.sj_tele_liEdit_01.text()
    chatingid = ui.sj_tele_liEdit_02.text()

    if '' in (bot_token, chatingid):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        no = int(ui.sj_main_comBox_01.currentText()[-2:])
        en_bot_token = en_text(ui.dict_set['키'], bot_token)
        en_chatingid = en_text(ui.dict_set['키'], chatingid)
        query  = 'UPDATE telegram SET bot_token = ?, chatingid = ? WHERE `index` = ?'
        values = (en_bot_token, en_chatingid, no)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)


def setting_save_04(ui):
    """전략 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox

    잔고청산 = 1 if ui.sj_strgy_ckBox_01.isChecked() else 0
    프로세스종료 = 1 if ui.sj_strgy_ckBox_02.isChecked() else 0
    컴퓨터종료 = 1 if ui.sj_strgy_ckBox_03.isChecked() else 0
    투자금고정 = 1 if ui.sj_strgy_ckBox_04.isChecked() else 0
    손실중지 = 1 if ui.sj_strgy_ckBox_05.isChecked() else 0
    수익중지 = 1 if ui.sj_strgy_ckBox_06.isChecked() else 0
    매수전략 = ui.sj_strgy_cbBox_01.currentText()
    매도전략 = ui.sj_strgy_cbBox_02.currentText()
    평균값계산틱수 = ui.sj_strgy_lEdit_01.text()
    최대매수종목수 = ui.sj_strgy_lEdit_02.text()
    전략종료시간 = ui.sj_strgy_lEdit_03.text()
    투자금 = ui.sj_strgy_lEdit_04.text()
    손실중지수익률 = ui.sj_strgy_lEdit_05.text()
    수익중지수익률 = ui.sj_strgy_lEdit_06.text()

    if '' in (평균값계산틱수, 최대매수종목수, 전략종료시간, 투자금, 손실중지수익률, 수익중지수익률):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    평균값계산틱수, 최대매수종목수, 전략종료시간, 투자금, 손실중지수익률, 수익중지수익률 = \
        int(평균값계산틱수), int(최대매수종목수), int(전략종료시간), float(투자금), float(손실중지수익률), float(수익중지수익률)
    time_limit = ui.market_info['프로세스종료시간'] - 30

    if 전략종료시간 < 10000:
        QMessageBox.critical(ui, '오류 알림', '전략종료시간을 초단위 시간까지 입력하십시오.\n')
        return

    if ui.market_gubun != 7 and 전략종료시간 > ui.market_info['프로세스종료시간'] - 30:
        QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 전략종료시간은 {time_limit}을 초과할 수 없습니다.\n")
        return

    if 매수전략 == '사용안함': 매수전략 = ''
    if 매도전략 == '사용안함': 매도전략 = ''

    if ui.proc_chqs.is_alive():
        columns = ['잔고청산', '프로세스종료', '컴퓨터종료', '투자금고정', '손실중지', '수익중지', '매수전략', '매도전략',
                   '평균값계산틱수', '최대매수종목수', '전략종료시간', '투자금', '손실중지수익률', '수익중지수익률']
        no      = ui.sj_main_comBox_01.currentText()[-2:]
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE strategy SET {set_txt} WHERE `index` = ?'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns) + (no,)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)


def setting_save_05(ui):
    """백테스트 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from ui.event_click.button_clicked_backtest_start import backtest_engine_kill

    블랙리스트추가 = 1 if ui.sj_back_cheBox_01.isChecked() else 0
    백테일괄로딩 = 1 if ui.sj_back_cheBox_02.isChecked() else 0
    # 백테분할로딩 = 1 if ui.sj_back_cheBox_03.isChecked() else 0
    디비자동관리 = 1 if ui.sj_back_cheBox_04.isChecked() else 0
    백테주문관리적용 = 1 if ui.sj_back_cheBox_05.isChecked() else 0
    교차검증가중치 = 1 if ui.sj_back_cheBox_06.isChecked() else 0
    범위자동관리 = 1 if ui.sj_back_cheBox_07.isChecked() else 0
    자동학습 = 1 if ui.sj_back_cheBox_08.isChecked() else 0
    백테스트로그기록안함 = 1 if ui.sj_back_cheBox_09.isChecked() else 0
    기준값최소상승률 = ui.sj_back_liEdit_01.text()
    시장미시구조분석 = 1 if ui.sj_back_cheBox_10.isChecked() else 0
    리스크분석 = 1 if ui.sj_back_cheBox_11.isChecked() else 0
    패턴분석 = 1 if ui.sj_back_cheBox_12.isChecked() else 0
    가격대분석 = 1 if ui.sj_back_cheBox_13.isChecked() else 0
    백테매수시간기준 = 1 if ui.sj_back_cheBox_14.isChecked() else 0
    그래프저장하지않기 = 1 if ui.sj_back_cheBox_15.isChecked() else 0
    그래프띄우지않기 = 1 if ui.sj_back_cheBox_16.isChecked() else 0
    백테스케쥴실행 = 1 if ui.sj_back_cheBox_17.isChecked() else 0
    # 백테날짜일전 = 1 if ui.sj_back_cheBox_18.isChecked() else 0
    백테날짜고정 = 1 if ui.sj_back_cheBox_19.isChecked() else 0

    if ui.sj_back_comBox_01.currentText() == '금':
        백테스케쥴요일 = 4
    elif ui.sj_back_comBox_01.currentText() == '토':
        백테스케쥴요일 = 5
    else:
        백테스케쥴요일 = 6

    백테스케쥴시간 = ui.sj_back_liEdit_02.text()
    백테스케쥴명 = ui.sj_back_comBox_02.currentText()

    if 백테날짜고정:
        백테날짜 = ui.sj_back_daEdit_01.date().toString('yyyyMMdd')
    else:
        백테날짜 = ui.sj_back_liEdit_03.text()

    if '' in (백테날짜, 백테스케쥴시간):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        백테스케쥴시간 = int(백테스케쥴시간)
        pre_bbg = ui.dict_set['백테주문관리적용']
        columns = ['블랙리스트추가', '백테일괄로딩', '디비자동관리', '백테주문관리적용', '교차검증가중치', '범위자동관리', '자동학습',
                   '기준값최소상승률', '시장미시구조분석', '리스크분석', '패턴분석', '가격대분석', '백테매수시간기준',
                   '백테스트로그기록안함', '그래프저장하지않기', '그래프띄우지않기', '백테스케쥴실행', '백테스케쥴요일', '백테스케쥴시간',
                   '백테스케쥴명', '백테날짜고정', '백테날짜']
        no      = ui.sj_main_comBox_01.currentText()[-2:]
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE back SET {set_txt} WHERE `index` = ?'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns) + (no,)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)
        if pre_bbg != 백테주문관리적용:
            backtest_engine_kill(ui)


def setting_save_06(ui):
    """기타 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import en_text

    테마 = ui.sj_etc_comBoxx_01.currentText()
    저해상도 = 1 if ui.sj_etc_checBox_02.isChecked() else 0
    스톰라이브 = 1 if ui.sj_etc_checBox_03.isChecked() else 0
    휴무프로세스종료 = 1 if ui.sj_etc_checBox_04.isChecked() else 0
    휴무컴퓨터종료 = 1 if ui.sj_etc_checBox_05.isChecked() else 0
    웹대시보드 = 1 if ui.sj_etc_checBox_06.isChecked() else 0
    창위치기억 = 1 if ui.sj_etc_checBox_07.isChecked() else 0
    프로그램종료 = 1 if ui.sj_etc_checBox_08.isChecked() else 0
    시리얼키 = ui.sj_etc_liEditt_01.text()

    if 시리얼키 == '':
        QMessageBox.critical(ui, '오류 알림', '시리얼키가 입력되지 않았습니다.\n')
        return

    시리얼키 = en_text(ui.dict_set['키'], 시리얼키)
    웹대시보드포트번호 = int(ui.sj_etc_liEditt_02.text())

    if ui.proc_chqs.is_alive():
        columns = ['테마', '저해상도', '스톰라이브', '휴무프로세스종료', '휴무컴퓨터종료', '웹대시보드', '웹대시보드포트번호',
                   '창위치기억', '프로그램종료', '시리얼키']
        no      = ui.sj_main_comBox_01.currentText()[-2:]
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE etc SET {set_txt} WHERE `index` = ?'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns) + (no,)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)
        query   = f"UPDATE etc SET 시리얼키 = '{시리얼키}'"
        ui.queryQ.put(('설정디비', query))


def setting_acc_view(ui):
    """계정 텍스트 표시/숨김을 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_style import style_bc_bt

    if ui.sj_etc_pButton_01.text() == '계정 텍스트 보기':
        ui.pa_lineEditttt_01.clear()
        ui.dialog_pass.show() if not ui.dialog_pass.isVisible() else ui.dialog_pass.close()
    else:
        from PyQt5.QtWidgets import QLineEdit
        ui.sj_main_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_accc_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_accc_liEdit_02.setEchoMode(QLineEdit.Password)
        ui.sj_tele_liEdit_01.setEchoMode(QLineEdit.Password)
        ui.sj_tele_liEdit_02.setEchoMode(QLineEdit.Password)
        ui.sj_etc_liEditt_01.setEchoMode(QLineEdit.Password)
        ui.sj_etc_pButton_01.setText('계정 텍스트 보기')
        ui.sj_etc_pButton_01.setStyleSheet(style_bc_bt)


def setting_order_load_01(ui):
    """매수 주문 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM buyorder').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    ui.ss_buyy_checkBox_01.setChecked(True) if df['매수주문유형'][no] == '시장가' else ui.ss_buyy_checkBox_01.setChecked(False)
    ui.ss_buyy_checkBox_02.setChecked(True) if df['매수주문유형'][no] == '지정가' else ui.ss_buyy_checkBox_02.setChecked(False)
    ui.ss_buyy_checkBox_03.setChecked(True) if df['매수주문유형'][no] == '최유리지정가' else ui.ss_buyy_checkBox_03.setChecked(False)
    ui.ss_buyy_checkBox_04.setChecked(True) if df['매수주문유형'][no] == '지정가IOC' else ui.ss_buyy_checkBox_04.setChecked(False)
    ui.ss_buyy_checkBox_05.setChecked(True) if df['매수주문유형'][no] == '최유리IOC' else ui.ss_buyy_checkBox_05.setChecked(False)
    ui.ss_buyy_checkBox_06.setChecked(True) if df['매수주문유형'][no] == '지정가FOK' else ui.ss_buyy_checkBox_06.setChecked(False)
    ui.ss_buyy_checkBox_07.setChecked(True) if df['매수주문유형'][no] == '최유리FOK' else ui.ss_buyy_checkBox_07.setChecked(False)
    ui.ss_buyy_lineEdit_01.setText(str(df['매수분할횟수'][no]))
    ui.ss_buyy_checkBox_11.setChecked(True) if df['매수분할방법'][no] == 1 else ui.ss_buyy_checkBox_11.setChecked(False)
    ui.ss_buyy_checkBox_12.setChecked(True) if df['매수분할방법'][no] == 2 else ui.ss_buyy_checkBox_12.setChecked(False)
    ui.ss_buyy_checkBox_13.setChecked(True) if df['매수분할방법'][no] == 3 else ui.ss_buyy_checkBox_13.setChecked(False)
    ui.ss_buyy_checkBox_14.setChecked(True) if df['매수분할시그널'][no] else ui.ss_buyy_checkBox_14.setChecked(False)
    ui.ss_buyy_checkBox_15.setChecked(True) if df['매수분할하방'][no] else ui.ss_buyy_checkBox_15.setChecked(False)
    ui.ss_buyy_checkBox_16.setChecked(True) if df['매수분할상방'][no] else ui.ss_buyy_checkBox_16.setChecked(False)
    ui.ss_buyy_lineEdit_02.setText(str(df['매수분할하방수익률'][no]))
    ui.ss_buyy_lineEdit_03.setText(str(df['매수분할상방수익률'][no]))
    ui.ss_buyy_checkBox_17.setChecked(True) if df['매수분할고정수익률'][no] else ui.ss_buyy_checkBox_17.setChecked(False)
    ui.ss_buyy_comboBox_01.setCurrentText(str(df['매수지정가기준가격'][no]))
    ui.ss_buyy_comboBox_02.setCurrentText(str(df['매수지정가호가번호'][no]))
    ui.ss_buyy_comboBox_03.setCurrentText(str(df['매수시장가잔량범위'][no]))
    ui.ss_buyy_checkBox_18.setChecked(True) if df['매수취소관심이탈'][no] else ui.ss_buyy_checkBox_18.setChecked(False)
    ui.ss_buyy_checkBox_19.setChecked(True) if df['매수취소매도시그널'][no] else ui.ss_buyy_checkBox_19.setChecked(False)
    ui.ss_buyy_checkBox_20.setChecked(True) if df['매수취소시간'][no] else ui.ss_buyy_checkBox_20.setChecked(False)
    ui.ss_buyy_lineEdit_04.setText(str(df['매수취소시간초'][no]))
    ui.ss_buyy_checkBox_21.setChecked(True) if df['매수금지블랙리스트'][no] else ui.ss_buyy_checkBox_21.setChecked(False)
    ui.ss_buyy_checkBox_23.setChecked(True) if df['매수금지손절횟수'][no] else ui.ss_buyy_checkBox_23.setChecked(False)
    ui.ss_buyy_lineEdit_06.setText(str(df['매수금지손절횟수값'][no]))
    ui.ss_buyy_checkBox_24.setChecked(True) if df['매수금지거래횟수'][no] else ui.ss_buyy_checkBox_24.setChecked(False)
    ui.ss_buyy_lineEdit_07.setText(str(df['매수금지거래횟수값'][no]))
    ui.ss_buyy_checkBox_25.setChecked(True) if df['매수금지시간'][no] else ui.ss_buyy_checkBox_25.setChecked(False)
    ui.ss_buyy_lineEdit_08.setText(str(df['매수금지시작시간'][no]))
    ui.ss_buyy_lineEdit_09.setText(str(df['매수금지종료시간'][no]))
    ui.ss_buyy_checkBox_26.setChecked(True) if df['매수금지간격'][no] else ui.ss_buyy_checkBox_26.setChecked(False)
    ui.ss_buyy_lineEdit_10.setText(str(df['매수금지간격초'][no]))
    ui.ss_buyy_checkBox_27.setChecked(True) if df['매수금지손절간격'][no] else ui.ss_buyy_checkBox_27.setChecked(False)
    ui.ss_buyy_lineEdit_11.setText(str(df['매수금지손절간격초'][no]))
    ui.ss_buyy_lineEdit_12.setText(str(df['매수정정횟수'][no]))
    ui.ss_buyy_comboBox_04.setCurrentText(str(df['매수정정호가차이'][no]))
    ui.ss_buyy_comboBox_05.setCurrentText(str(df['매수정정호가'][no]))

    ui.ss_bj_checkBoxxx_01.setChecked(False)
    ui.ss_bj_checkBoxxx_02.setChecked(False)
    ui.ss_bj_checkBoxxx_03.setChecked(False)
    ui.ss_bj_checkBoxxx_04.setChecked(False)
    ui.ss_bj_checkBoxxx_05.setChecked(False)
    ui.ss_bj_checkBoxxx_06.setChecked(False)

    bjjj_list = df['비중조절'][no]
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


def setting_order_load_02(ui):
    """매도 주문 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM sellorder').set_index('index')
    no = int(ui.dict_set['거래소'][-2:])
    ui.ss_sell_checkBox_01.setChecked(True) if df['매도주문유형'][no] == '시장가' else ui.ss_sell_checkBox_01.setChecked(False)
    ui.ss_sell_checkBox_02.setChecked(True) if df['매도주문유형'][no] == '지정가' else ui.ss_sell_checkBox_02.setChecked(False)
    ui.ss_sell_checkBox_03.setChecked(True) if df['매도주문유형'][no] == '최유리지정가' else ui.ss_sell_checkBox_03.setChecked(False)
    ui.ss_sell_checkBox_04.setChecked(True) if df['매도주문유형'][no] == '지정가IOC' else ui.ss_sell_checkBox_04.setChecked(False)
    ui.ss_sell_checkBox_05.setChecked(True) if df['매도주문유형'][no] == '최유리IOC' else ui.ss_sell_checkBox_05.setChecked(False)
    ui.ss_sell_checkBox_06.setChecked(True) if df['매도주문유형'][no] == '지정가FOK' else ui.ss_sell_checkBox_06.setChecked(False)
    ui.ss_sell_checkBox_07.setChecked(True) if df['매도주문유형'][no] == '최유리FOK' else ui.ss_sell_checkBox_07.setChecked(False)
    ui.ss_sell_lineEdit_01.setText(str(df['매도분할횟수'][no]))
    ui.ss_sell_checkBox_11.setChecked(True) if df['매도분할방법'][no] == 1 else ui.ss_sell_checkBox_11.setChecked(False)
    ui.ss_sell_checkBox_12.setChecked(True) if df['매도분할방법'][no] == 2 else ui.ss_sell_checkBox_12.setChecked(False)
    ui.ss_sell_checkBox_13.setChecked(True) if df['매도분할방법'][no] == 3 else ui.ss_sell_checkBox_13.setChecked(False)
    ui.ss_sell_checkBox_14.setChecked(True) if df['매도분할시그널'][no] else ui.ss_sell_checkBox_14.setChecked(False)
    ui.ss_sell_checkBox_15.setChecked(True) if df['매도분할하방'][no] else ui.ss_sell_checkBox_15.setChecked(False)
    ui.ss_sell_checkBox_16.setChecked(True) if df['매도분할상방'][no] else ui.ss_sell_checkBox_16.setChecked(False)
    ui.ss_sell_lineEdit_02.setText(str(df['매도분할하방수익률'][no]))
    ui.ss_sell_lineEdit_03.setText(str(df['매도분할상방수익률'][no]))
    ui.ss_sell_comboBox_01.setCurrentText(str(df['매도지정가기준가격'][no]))
    ui.ss_sell_comboBox_02.setCurrentText(str(df['매도지정가호가번호'][no]))
    ui.ss_sell_comboBox_03.setCurrentText(str(df['매도시장가잔량범위'][no]))
    ui.ss_sell_checkBox_17.setChecked(True) if df['매도취소관심진입'][no] else ui.ss_sell_checkBox_17.setChecked(False)
    ui.ss_sell_checkBox_18.setChecked(True) if df['매도취소매수시그널'][no] else ui.ss_sell_checkBox_18.setChecked(False)
    ui.ss_sell_checkBox_19.setChecked(True) if df['매도취소시간'][no] else ui.ss_sell_checkBox_19.setChecked(False)
    ui.ss_sell_lineEdit_04.setText(str(df['매도취소시간초'][no]))
    ui.ss_sell_checkBox_20.setChecked(True) if df['매도금지매수횟수'][no] else ui.ss_sell_checkBox_20.setChecked(False)
    ui.ss_sell_lineEdit_05.setText(str(df['매도금지매수횟수값'][no]))
    ui.ss_sell_checkBox_22.setChecked(True) if df['매도금지시간'][no] else ui.ss_sell_checkBox_22.setChecked(False)
    ui.ss_sell_lineEdit_07.setText(str(df['매도금지시작시간'][no]))
    ui.ss_sell_lineEdit_08.setText(str(df['매도금지종료시간'][no]))
    ui.ss_sell_checkBox_23.setChecked(True) if df['매도금지간격'][no] else ui.ss_sell_checkBox_23.setChecked(False)
    ui.ss_sell_lineEdit_09.setText(str(df['매도금지간격초'][no]))
    ui.ss_sell_lineEdit_10.setText(str(df['매도정정횟수'][no]))
    ui.ss_sell_comboBox_04.setCurrentText(str(df['매도정정호가차이'][no]))
    ui.ss_sell_comboBox_05.setCurrentText(str(df['매도정정호가'][no]))
    ui.ss_sell_checkBox_24.setChecked(True) if df['매도익절수익률청산'][no] else ui.ss_sell_checkBox_26.setChecked(False)
    ui.ss_sell_lineEdit_11.setText(str(df['매도익절수익률'][no]))
    ui.ss_sell_checkBox_25.setChecked(True) if df['매도익절수익금청산'][no] else ui.ss_sell_checkBox_27.setChecked(False)
    ui.ss_sell_lineEdit_12.setText(str(df['매도익절수익금'][no]))
    ui.ss_sell_checkBox_26.setChecked(True) if df['매도손절수익률청산'][no] else ui.ss_sell_checkBox_26.setChecked(False)
    ui.ss_sell_lineEdit_13.setText(str(df['매도손절수익률'][no]))
    ui.ss_sell_checkBox_27.setChecked(True) if df['매도손절수익금청산'][no] else ui.ss_sell_checkBox_27.setChecked(False)
    ui.ss_sell_lineEdit_14.setText(str(df['매도손절수익금'][no]))


def setting_order_save_01(ui):
    """매수 주문 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox

    매수주문유형 = ''
    if ui.ss_buyy_checkBox_01.isChecked(): 매수주문유형 = '시장가'
    if ui.ss_buyy_checkBox_02.isChecked(): 매수주문유형 = '지정가'
    if ui.ss_buyy_checkBox_03.isChecked(): 매수주문유형 = '최유리지정가'
    if ui.ss_buyy_checkBox_04.isChecked(): 매수주문유형 = '지정가IOC'
    if ui.ss_buyy_checkBox_05.isChecked(): 매수주문유형 = '최유리IOC'
    if ui.ss_buyy_checkBox_06.isChecked(): 매수주문유형 = '지정가FOK'
    if ui.ss_buyy_checkBox_07.isChecked(): 매수주문유형 = '최유리FOK'
    매수분할횟수 = ui.ss_buyy_lineEdit_01.text()

    매수분할방법 = 0
    if ui.ss_buyy_checkBox_11.isChecked(): 매수분할방법 = 1
    if ui.ss_buyy_checkBox_12.isChecked(): 매수분할방법 = 2
    if ui.ss_buyy_checkBox_13.isChecked(): 매수분할방법 = 3

    매수분할시그널 = 1 if ui.ss_buyy_checkBox_14.isChecked() else 0
    매수분할하방 = 1 if ui.ss_buyy_checkBox_15.isChecked() else 0
    매수분할상방 = 1 if ui.ss_buyy_checkBox_16.isChecked() else 0
    매수분할하방수익률 = ui.ss_buyy_lineEdit_02.text()
    매수분할상방수익률 = ui.ss_buyy_lineEdit_03.text()
    매수지정가기준가격 = ui.ss_buyy_comboBox_01.currentText()
    매수지정가호가번호 = ui.ss_buyy_comboBox_02.currentText()
    매수시장가잔량범위 = ui.ss_buyy_comboBox_03.currentText()
    매수분할고정수익률 = 1 if ui.ss_buyy_checkBox_17.isChecked() else 0
    매수취소관심이탈 = 1 if ui.ss_buyy_checkBox_18.isChecked() else 0
    매수취소매도시그널 = 1 if ui.ss_buyy_checkBox_19.isChecked() else 0
    매수취소시간 = 1 if ui.ss_buyy_checkBox_20.isChecked() else 0
    매수취소시간초 = ui.ss_buyy_lineEdit_04.text()
    매수금지블랙리스트 = 1 if ui.ss_buyy_checkBox_21.isChecked() else 0
    매수금지손절횟수 = 1 if ui.ss_buyy_checkBox_23.isChecked() else 0
    매수금지손절횟수값 = ui.ss_buyy_lineEdit_06.text()
    매수금지거래횟수 = 1 if ui.ss_buyy_checkBox_24.isChecked() else 0
    매수금지거래횟수값 = ui.ss_buyy_lineEdit_07.text()
    매수금지시간 = 1 if ui.ss_buyy_checkBox_25.isChecked() else 0
    매수금지시작시간 = ui.ss_buyy_lineEdit_08.text()
    매수금지종료시간 = ui.ss_buyy_lineEdit_09.text()
    매수금지간격 = 1 if ui.ss_buyy_checkBox_26.isChecked() else 0
    매수금지간격초 = ui.ss_buyy_lineEdit_10.text()
    매수금지손절간격 = 1 if ui.ss_buyy_checkBox_27.isChecked() else 0
    매수금지손절간격초 = ui.ss_buyy_lineEdit_11.text()
    매수정정횟수 = ui.ss_buyy_lineEdit_12.text()
    매수정정호가차이 = ui.ss_buyy_comboBox_04.currentText()
    매수정정호가 = ui.ss_buyy_comboBox_05.currentText()

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
    비중조절 = ';'.join(bjjj_list)

    if '' in (매수주문유형, 매수분할횟수, 매수분할하방수익률, 매수분할상방수익률, 매수지정가호가번호, 매수시장가잔량범위, 매수취소시간초,
              매수금지손절횟수값, 매수금지거래횟수값, 매수금지시작시간, 매수금지종료시간, 매수금지간격초, 매수정정횟수):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 매수분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매수방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (매수분할시그널, 매수분할하방, 매수분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매수방법이 선택되지 않았습니다.\n')
        return

    매수분할횟수, 매수분할하방수익률, 매수분할상방수익률, 매수지정가호가번호, 매수시장가잔량범위, 매수취소시간초, 매수금지손절횟수값, 매수금지거래횟수값, \
        매수금지시작시간, 매수금지종료시간, 매수금지간격초, 매수금지손절간격초, 매수정정횟수, 매수정정호가차이, 매수정정호가 = \
        int(매수분할횟수), float(매수분할하방수익률), float(매수분할상방수익률), int(매수지정가호가번호), int(매수시장가잔량범위), \
        int(매수취소시간초), int(매수금지손절횟수값), int(매수금지거래횟수값), int(매수금지시작시간), int(매수금지종료시간), \
        int(매수금지간격초), int(매수금지손절간격초), int(매수정정횟수), int(매수정정호가차이), int(매수정정호가)

    if 매수분할횟수 < 0 or 매수분할하방수익률 < 0 or 매수분할상방수익률 < 0 or 매수시장가잔량범위 < 0 or 매수취소시간초 < 0 or \
            매수금지손절횟수값 < 0 or 매수금지거래횟수값 < 0 or 매수금지시작시간 < 0 or 매수금지종료시간 < 0 or 매수금지간격초 < 0 or \
            매수금지손절간격초 < 0 or 매수정정횟수 < 0 or 매수정정호가차이 < 0 or 매수정정호가 < 0:
        QMessageBox.critical(ui, '오류 알림', '지정가 호가 외 모든 입력값은 양수여야합니다.\n')
        return

    if 매수분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매수분할횟수는 10을 초과할 수 없습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['매수주문유형', '매수분할횟수', '매수분할방법', '매수분할시그널', '매수분할하방', '매수분할상방', '매수분할하방수익률',
                   '매수분할상방수익률', '매수분할고정수익률', '매수지정가기준가격', '매수지정가호가번호', '매수시장가잔량범위',
                   '매수취소관심이탈', '매수취소매도시그널', '매수취소시간', '매수취소시간초', '매수금지블랙리스트', '매수금지손절횟수',
                   '매수금지손절횟수값', '매수금지거래횟수', '매수금지거래횟수값', '매수금지시간', '매수금지시작시간', '매수금지종료시간',
                   '매수금지간격', '매수금지간격초', '매수금지손절간격', '매수금지손절간격초', '매수정정횟수', '매수정정호가차이',
                   '매수정정호가', '비중조절']
        no      = ui.sj_main_comBox_01.currentText()[-2:]
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE buyorder SET {set_txt} WHERE `index` = ?'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns) + (no,)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)


def setting_order_save_02(ui):
    """매도 주문 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox

    매도주문유형 = ''
    if ui.ss_sell_checkBox_01.isChecked(): 매도주문유형 = '시장가'
    if ui.ss_sell_checkBox_02.isChecked(): 매도주문유형 = '지정가'
    if ui.ss_sell_checkBox_03.isChecked(): 매도주문유형 = '최유리지정가'
    if ui.ss_sell_checkBox_04.isChecked(): 매도주문유형 = '지정가IOC'
    if ui.ss_sell_checkBox_05.isChecked(): 매도주문유형 = '최유리IOC'
    if ui.ss_sell_checkBox_06.isChecked(): 매도주문유형 = '지정가FOK'
    if ui.ss_sell_checkBox_07.isChecked(): 매도주문유형 = '최유리FOK'
    매도분할횟수 = ui.ss_sell_lineEdit_01.text()

    매도분할방법 = 0
    if ui.ss_sell_checkBox_11.isChecked(): 매도분할방법 = 1
    if ui.ss_sell_checkBox_12.isChecked(): 매도분할방법 = 2
    if ui.ss_sell_checkBox_13.isChecked(): 매도분할방법 = 3

    매도분할시그널 = 1 if ui.ss_sell_checkBox_14.isChecked() else 0
    매도분할하방 = 1 if ui.ss_sell_checkBox_15.isChecked() else 0
    매도분할상방 = 1 if ui.ss_sell_checkBox_16.isChecked() else 0
    매도분할하방수익률 = ui.ss_sell_lineEdit_02.text()
    매도분할상방수익률 = ui.ss_sell_lineEdit_03.text()
    매도지정가기준가격 = ui.ss_sell_comboBox_01.currentText()
    매도지정가호가번호 = ui.ss_sell_comboBox_02.currentText()
    매도시장가잔량범위 = ui.ss_sell_comboBox_03.currentText()
    매도취소관심진입 = 1 if ui.ss_sell_checkBox_17.isChecked() else 0
    매도취소매수시그널 = 1 if ui.ss_sell_checkBox_18.isChecked() else 0
    매도취소시간 = 1 if ui.ss_sell_checkBox_19.isChecked() else 0
    매도취소시간초 = ui.ss_sell_lineEdit_04.text()
    매도금지매수횟수 = 1 if ui.ss_sell_checkBox_20.isChecked() else 0
    매도금지매수횟수값 = ui.ss_sell_lineEdit_05.text()
    매도금지시간 = 1 if ui.ss_sell_checkBox_22.isChecked() else 0
    매도금지시작시간 = ui.ss_sell_lineEdit_07.text()
    매도금지종료시간 = ui.ss_sell_lineEdit_08.text()
    매도금지간격 = 1 if ui.ss_sell_checkBox_23.isChecked() else 0
    매도금지간격초 = ui.ss_sell_lineEdit_09.text()
    매도정정횟수 = ui.ss_sell_lineEdit_10.text()
    매도정정호가차이 = ui.ss_sell_comboBox_04.currentText()
    매도정정호가 = ui.ss_sell_comboBox_05.currentText()
    매도익절수익률청산 = 1 if ui.ss_sell_checkBox_24.isChecked() else 0
    매도익절수익률 = ui.ss_sell_lineEdit_11.text()
    매도익절수익금청산  = 1 if ui.ss_sell_checkBox_25.isChecked() else 0
    매도익절수익금 = ui.ss_sell_lineEdit_12.text()
    매도손절수익률청산 = 1 if ui.ss_sell_checkBox_26.isChecked() else 0
    매도손절수익률 = ui.ss_sell_lineEdit_13.text()
    매도손절수익금청산  = 1 if ui.ss_sell_checkBox_27.isChecked() else 0
    매도손절수익금 = ui.ss_sell_lineEdit_14.text()

    if '' in (매도주문유형, 매도분할횟수, 매도분할하방수익률, 매도분할상방수익률, 매도취소시간초, 매도금지매수횟수값, 매도금지시작시간,
              매도금지종료시간, 매도금지간격초, 매도정정횟수, 매도익절수익률, 매도익절수익금, 매도손절수익률, 매도손절수익금):
        QMessageBox.critical(ui, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        return

    if 매도분할방법 == 0:
        QMessageBox.critical(ui, '오류 알림', '분할매도방법이 선택되지 않았습니다.\n')
        return

    if 1 not in (매도분할시그널, 매도분할하방, 매도분할상방):
        QMessageBox.critical(ui, '오류 알림', '추가매도방법이 선택되지 않았습니다.\n')
        return

    매도분할횟수, 매도분할하방수익률, 매도분할상방수익률, 매도지정가호가번호, 매도시장가잔량범위, 매도취소시간초, 매도금지매수횟수값, 매도금지시작시간, \
        매도금지종료시간, 매도금지간격초, 매도정정횟수, 매도정정호가차이, 매도정정호가, 매도익절수익률, 매도익절수익금, 매도손절수익률, 매도손절수익금 = \
        int(매도분할횟수), float(매도분할하방수익률), float(매도분할상방수익률), int(매도지정가호가번호), int(매도시장가잔량범위), \
        int(매도취소시간초), int(매도금지매수횟수값), int(매도금지시작시간), int(매도금지종료시간), int(매도금지간격초), int(매도정정횟수), \
        int(매도정정호가차이), int(매도정정호가), float(매도익절수익률), int(매도익절수익금), float(매도손절수익률), int(매도손절수익금)

    if 매도분할횟수 < 0 or 매도분할하방수익률 < 0 or 매도분할상방수익률 < 0 or 매도취소시간초 < 0 or 매도금지매수횟수값 < 0 or \
            매도금지시작시간 < 0 or 매도금지종료시간 < 0 or 매도금지간격초 < 0 or 매도정정횟수 < 0 or 매도정정호가차이 < 0 or \
            매도정정호가 < 0 or 매도익절수익률 < 0 or 매도익절수익금 < 0 or 매도손절수익률 < 0 or 매도손절수익금 < 0:
        QMessageBox.critical(ui, '오류 알림', '모든 값은 양수로 입력하십시오.\n')
        return

    if 매도분할횟수 > 10:
        QMessageBox.critical(ui, '오류 알림', '매도분할횟수는 10을 초과할 수 없습니다.\n')
        return

    if 매도금지매수횟수값 > 9:
        QMessageBox.critical(ui, '오류 알림', '매도금지 매수횟수는 10미만으로 입력하십시오.\n')
        return

    if ui.proc_chqs.is_alive():
        columns = ['매도주문유형', '매도분할횟수', '매도분할방법', '매도분할시그널', '매도분할하방', '매도분할상방', '매도분할하방수익률',
                   '매도분할상방수익률', '매도지정가기준가격', '매도지정가호가번호', '매도시장가잔량범위', '매도취소관심진입',
                   '매도취소매수시그널', '매도취소시간', '매도취소시간초', '매도금지매수횟수', '매도금지매수횟수값', '매도금지시간',
                   '매도금지시작시간', '매도금지종료시간', '매도금지간격', '매도금지간격초', '매도정정횟수', '매도정정호가차이', '매도정정호가',
                   '매도익절수익률청산', '매도익절수익률', '매도익절수익금청산', '매도익절수익금', '매도손절수익률청산', '매도손절수익률',
                   '매도손절수익금청산', '매도손절수익금']
        no      = ui.sj_main_comBox_01.currentText()[-2:]
        set_txt = ', '.join([f'{col} = ?' for col in columns])
        query   = f'UPDATE sellorder SET {set_txt} WHERE `index` = ?'
        localvs = locals()
        values  = tuple(localvs[col] for col in columns) + (no,)
        ui.queryQ.put(('설정디비', query, values))
        settings_save_completed(ui)


def setting_all_load(ui):
    """모든 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    load_setting_file(ui)


def setting_all_app(ui):
    """모든 설정을 적용합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    import random
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import DB_PATH
    from ui.create_widget.set_text import famous_saying
    from utility.static_method.static import qtest_qwait

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
        setting_load_01(ui)
        setting_load_02(ui)
        setting_load_03(ui)
        setting_load_04(ui)
        setting_load_05(ui)
        setting_load_06(ui)
        setting_order_load_01(ui)
        setting_order_load_02(ui)
        setting_save_01(ui)
        setting_save_02(ui)
        setting_save_03(ui)
        setting_save_04(ui)
        setting_save_05(ui)
        setting_save_06(ui)
        setting_order_save_01(ui)
        setting_order_save_02(ui)
        QMessageBox.information(ui, '모든 설정 적용 완료', random.choice(famous_saying))


def setting_all_del(ui):
    """설정 파일을 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    import random
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import DB_PATH
    from ui.create_widget.set_text import famous_saying

    name = ui.sj_set_comBoxx_01.currentText()
    if name == '':
        QMessageBox.critical(ui, '오류 알림', '설정이름이 선택되지 않았습니다.\n')
        return

    remove_file = f'{DB_PATH}/setting_{name}.db'
    os.remove(remove_file)
    load_setting_file(ui)
    QMessageBox.information(ui, '삭제 완료', random.choice(famous_saying))


def setting_all_save(ui):
    """모든 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    import shutil
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import DB_PATH
    from ui.create_widget.set_text import famous_saying

    name = ui.sj_set_liEditt_01.text()
    if name == '':
        QMessageBox.critical(ui, '오류 알림', '설정이름이 입력되지 않았습니다.\n')
        return

    origin_file = f'{DB_PATH}/setting.db'
    copy_file = f'{DB_PATH}/setting_{name}.db'
    shutil.copy(origin_file, copy_file)
    load_setting_file(ui)
    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def setting_passticks(ui):
    """패스틱스 설정 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.dialog_setsj.show() if not ui.dialog_setsj.isVisible() else ui.dialog_setsj.close()


def load_setting_file(ui):
    """설정 파일 목록을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    from utility.settings.setting_base import DB_PATH

    ui.sj_set_comBoxx_01.clear()
    file_list = os.listdir(DB_PATH)
    file_list = [x for x in file_list if 'setting_' in x]

    for file_name in file_list:
        name = file_name.replace('setting_', '').replace('.db', '')
        ui.sj_set_comBoxx_01.addItem(name)
