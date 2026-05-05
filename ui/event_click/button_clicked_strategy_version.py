
from utility.static_method.strategy_version_manager import StrategyVersionManager


SVM = StrategyVersionManager('stock', 'basic', 'buy', 'dummy')


def visible_false(ui):
    """모든 텍스트 에디터를 숨깁니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)
    ui.ss_textEditttt_07.setVisible(False)
    ui.ss_textEditttt_08.setVisible(False)
    ui.szoo_pushButon_01.setVisible(False)
    ui.szoo_pushButon_02.setVisible(False)


def comboBox_reload(comboBox1, comboBox2):
    """콤보박스를 다시 로드합니다.
    Args:
        comboBox1: 첫 번째 콤보박스
        comboBox2: 두 번째 콤보박스
    """
    global SVM
    version_list = SVM.get_versions()
    comboBox1.clear()
    comboBox2.clear()
    for i, item in enumerate(version_list):
        comboBox1.addItem(item)
        if i != 0:
            comboBox2.addItem(item)


def get_widget(ui, gubun1, gubun2):
    """위젯을 가져옵니다.
    Args:
        ui: UI 클래스 인스턴스
        gubun1: 첫 번째 구분 (basic, opti, cond)
        gubun2: 두 번째 구분 (buy, sell, vars, gavars)
    Returns:
        텍스트에디터1, 텍스트에디터2, 콤보박스1, 콤보박스2
    """
    if gubun1 == 'basic':
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, 'ss_textEditttt_01')
        else:
            textEdit1 = getattr(ui, 'ss_textEditttt_02')
    elif gubun1 == 'opti':
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, 'ss_textEditttt_03')
        elif gubun2 == 'sell':
            textEdit1 = getattr(ui, 'ss_textEditttt_04')
        elif gubun2 == 'vars':
            textEdit1 = getattr(ui, 'ss_textEditttt_05')
        else:
            textEdit1 = getattr(ui, 'ss_textEditttt_06')
    else:
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, 'ss_textEditttt_07')
        else:
            textEdit1 = getattr(ui, 'ss_textEditttt_08')
    textEdit2 = getattr(ui, 'ss_textEditttt_10')
    comboBox1 = getattr(ui, 'ss_comboBoxxxx_41')
    comboBox2 = getattr(ui, 'ss_comboBoxxxx_42')
    return textEdit1, textEdit2, comboBox1, comboBox2


def strategy_version(ui, gubun1, gubun2, strategy_name):
    """전략 버전 관리를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        gubun1: 첫 번째 구분 (basic, opti, cond)
        gubun2: 두 번째 구분 (buy, sell, vars, gavars)
        strategy_name: 전략 이름
    """
    from PyQt5.QtWidgets import QMessageBox
    from ui.event_click.button_clicked_stg_editer import change_pre_button_edit, change_version_button_color

    not_visible_widjet1 = getattr(ui, 'svc_pushButton_21')
    not_visible_widjet2 = getattr(ui, 'svc_pushButton_24')
    not_visible_widjet3 = getattr(ui, 'ss_pushButtonn_08')
    not_visible_widjet4 = getattr(ui, 'ss_pushButtonn_07')

    if not_visible_widjet1.isVisible():
        QMessageBox.critical(ui, '오류 알림', '변수편집기 상태에서는 사용할 수 없습니다.\n')
        return
    elif not_visible_widjet2.isVisible():
        QMessageBox.critical(ui, '오류 알림', '범위편집기 상태에서는 사용할 수 없습니다.\n')
        return
    elif not_visible_widjet3.isVisible():
        QMessageBox.critical(ui, '오류 알림', '백테스트로그 상태에서는 사용할 수 없습니다.\n')
        return
    elif not_visible_widjet4.isVisible():
        QMessageBox.critical(ui, '오류 알림', '상세기록 상태에서는 사용할 수 없습니다.\n')
        return

    global SVM
    SVM = StrategyVersionManager(ui.market_info['전략구분'], gubun1, gubun2, strategy_name)

    visible_false(ui)
    version_widget_list = getattr(ui, 'version_list')
    version_delete_btn  = getattr(ui, 'ss_pushButtonn_41')

    textEdit1, textEdit2, comboBox1, comboBox2 = get_widget(ui, gubun1, gubun2)
    textEdit1.setGeometry(7, 40, 497, 1307 if ui.extend_window else 700)
    textEdit2.setGeometry(509, 40, 497, 1307 if ui.extend_window else 700)
    textEdit1.setVisible(True)
    textEdit2.setVisible(True)

    textEdit1.verticalScrollBar().valueChanged.connect(lambda value: sync_scroll(version_delete_btn, textEdit2, value))
    textEdit2.verticalScrollBar().valueChanged.connect(lambda value: sync_scroll(version_delete_btn, textEdit1, value))

    for widget in version_widget_list:
        widget.setVisible(True)

    change_pre_button_edit(ui)
    change_version_button_color(ui)

    comboBox_reload(comboBox1, comboBox2)


def sync_scroll(version_delete_btn, target_edit, value):
    """target_edit의 스크롤을 value로 동기화"""
    if version_delete_btn.isVisible():
        target_edit.verticalScrollBar().setValue(value)


def strategy_version_delete(ui):
    """버전 삭제 버튼 호출"""
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying
    from utility.static_method.static import qtest_qwait

    global SVM
    comboBox1 = getattr(ui, 'ss_comboBoxxxx_41')
    comboBox2 = getattr(ui, 'ss_comboBoxxxx_42')
    version = comboBox2.currentText()
    if version:
        SVM.delete_version(version)
        qtest_qwait(0.1)
        comboBox_reload(comboBox1, comboBox2)
        QMessageBox.information(ui, '삭제 완료', random.choice(famous_saying))


def dactivated_04(ui):
    """버전 콤보박스 변경 시 호출 diff 표시"""
    from difflib import SequenceMatcher
    from ui.create_widget.set_style import color_bf_dk

    global SVM
    textEdit1, textEdit2, comboBox1, comboBox2 = get_widget(ui, SVM.gubun1, SVM.gubun2)
    version1   = comboBox1.currentText()
    version2   = comboBox2.currentText()
    stg_text1  = SVM.load_version(version1)
    stg_text2  = SVM.load_version(version2)
    back_color = color_bf_dk.name()

    textEdit1.clear()
    textEdit2.clear()

    if stg_text1 and stg_text2:
        lines1 = stg_text1.splitlines()
        lines2 = stg_text2.splitlines()

        matcher = SequenceMatcher(None, lines1, lines2)
        left_html = [f'<div style="font-size:14px; white-space:pre;">']
        right_html = [f'<div style="font-size:14px; white-space:pre;">']

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for line in lines1[i1:i2]:
                    escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    left_html.append(escaped)
                    right_html.append(escaped)
            elif tag == 'delete':
                for line in lines1[i1:i2]:
                    escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    left_html.append(f'<span style="background-color:{back_color};">{escaped}</span>')
                    right_html.append('')
            elif tag == 'insert':
                for line in lines2[j1:j2]:
                    escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    left_html.append('')
                    right_html.append(f'<span style="background-color:{back_color};">{escaped}</span>')
            elif tag == 'replace':
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    if k < (i2 - i1):
                        line = lines1[i1 + k]
                        escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        left_html.append(f'<span style="background-color:{back_color};">{escaped}</span>')
                    else:
                        left_html.append('')
                    if k < (j2 - j1):
                        line = lines2[j1 + k]
                        escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        right_html.append(f'<span style="background-color:{back_color};">{escaped}</span>')
                    else:
                        right_html.append('')

        left_html.append('</div>')
        right_html.append('</div>')
        textEdit1.setHtml('\n'.join(left_html))
        textEdit2.setHtml('\n'.join(right_html))
    else:
        textEdit1.append(stg_text1 if stg_text1 else "")
        textEdit2.append(stg_text2 if stg_text2 else "")
