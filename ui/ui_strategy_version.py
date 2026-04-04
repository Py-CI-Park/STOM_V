
import random
from difflib import SequenceMatcher
from ui.set_text import famous_saying
from utility.static import qtest_qwait
from PyQt5.QtWidgets import QMessageBox
from utility.strategy_version_manager import StrategyVersionManager


SVM = StrategyVersionManager('stock', 'basic', 'buy', 'dummy')


def stock_visible_false(ui):
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


def coin_visible_false(ui):
    ui.sc_textEditttt_01.setVisible(False)
    ui.sc_textEditttt_02.setVisible(False)
    ui.sc_textEditttt_03.setVisible(False)
    ui.sc_textEditttt_04.setVisible(False)
    ui.sc_textEditttt_05.setVisible(False)
    ui.sc_textEditttt_06.setVisible(False)
    ui.sc_textEditttt_07.setVisible(False)
    ui.sc_textEditttt_08.setVisible(False)
    ui.czoo_pushButon_01.setVisible(False)
    ui.czoo_pushButon_02.setVisible(False)


def comboBox_reload(comboBox1, comboBox2):
    global SVM
    version_list = SVM.get_versions()
    comboBox1.clear()
    comboBox2.clear()
    for i, item in enumerate(version_list):
        comboBox1.addItem(item)
        if i != 0:
            comboBox2.addItem(item)


def get_widget(ui, sorc, gubun1, gubun2):
    if gubun1 == 'basic':
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_01')
        else:
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_02')
    elif gubun1 == 'opti':
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_03')
        elif gubun2 == 'sell':
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_04')
        elif gubun2 == 'vars':
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_05')
        else:
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_06')
    else:
        if gubun2 == 'buy':
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_07')
        else:
            textEdit1 = getattr(ui, f'{sorc}s_textEditttt_08')
    textEdit2 = getattr(ui, f'{sorc}s_textEditttt_10')
    comboBox1 = getattr(ui, f'{sorc}s_comboBoxxxx_41')
    comboBox2 = getattr(ui, f'{sorc}s_comboBoxxxx_42')
    return textEdit1, textEdit2, comboBox1, comboBox2


def strategy_version(ui, market, gubun1, gubun2, strategy_name):
    if market in ('stock', 'future'):
        not_visible_widjet1 = getattr(ui, 'svc_pushButton_21')
        not_visible_widjet2 = getattr(ui, 'svc_pushButton_24')
        not_visible_widjet3 = getattr(ui, 'ss_pushButtonn_08')
        not_visible_widjet4 = getattr(ui, 'ss_pushButtonn_07')
    else:
        not_visible_widjet1 = getattr(ui, 'cvc_pushButton_21')
        not_visible_widjet2 = getattr(ui, 'cvc_pushButton_24')
        not_visible_widjet3 = getattr(ui, 'cs_pushButtonn_08')
        not_visible_widjet4 = getattr(ui, 'cs_pushButtonn_07')

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
    SVM = StrategyVersionManager(market, gubun1, gubun2, strategy_name)

    if market in ('stock', 'future'):
        stock_visible_false(ui)
        version_widget_list = getattr(ui, 'stock_version_list')
    else:
        coin_visible_false(ui)
        version_widget_list = getattr(ui, 'coin_version_list')

    textEdit1, textEdit2, comboBox1, comboBox2 = get_widget(ui, SVM.sorc, gubun1, gubun2)
    textEdit1.setGeometry(7, 40, 497, 1307 if ui.extend_window else 700)
    textEdit2.setGeometry(509, 40, 497, 1307 if ui.extend_window else 700)
    textEdit1.setVisible(True)
    textEdit2.setVisible(True)

    textEdit1.verticalScrollBar().valueChanged.connect(lambda value: sync_scroll(textEdit2, value))
    textEdit2.verticalScrollBar().valueChanged.connect(lambda value: sync_scroll(textEdit1, value))

    for widget in version_widget_list:
        widget.setVisible(True)

    if SVM.sorc == 's':
        from ui.ui_button_clicked_editer_stock import change_pre_button_edit, change_version_button_color
        change_pre_button_edit(ui)
        change_version_button_color(ui)
    else:
        from ui.ui_button_clicked_editer_coin import change_pre_button_edit, change_version_button_color
        change_pre_button_edit(ui)
        change_version_button_color(ui)

    comboBox_reload(comboBox1, comboBox2)


def sync_scroll(target_edit, value):
    """target_edit의 스크롤을 value로 동기화"""
    target_edit.verticalScrollBar().setValue(value)


def ssbutton_clicked_07(ui):
    global SVM
    comboBox1 = getattr(ui, f'{SVM.sorc}s_comboBoxxxx_41')
    comboBox2 = getattr(ui, f'{SVM.sorc}s_comboBoxxxx_42')
    version = comboBox2.currentText()
    SVM.delete_version(version)
    qtest_qwait(0.1)
    comboBox_reload(comboBox1, comboBox2)
    QMessageBox.information(ui, '삭제 완료', random.choice(famous_saying))


def dactivated_04(ui):
    """
    버전 콤보박스 변경 시 호출
    - comboBox1: 현재 버전 (textEdit1에 표시)
    - comboBox2: 비교 버전 (textEdit2에 diff 표시)
    """
    global SVM
    textEdit1, textEdit2, comboBox1, comboBox2 = get_widget(ui, SVM.sorc, SVM.gubun1, SVM.gubun2)

    if ui.focusWidget() == comboBox1:
        version = comboBox1.currentText()
        stg_text = SVM.load_version(version)
        textEdit1.clear()
        textEdit1.append(stg_text)

    elif ui.focusWidget() == comboBox2:
        version = comboBox2.currentText()
        stg_text = SVM.load_version(version)
        textEdit2.clear()
        textEdit2.append(stg_text)

    else:
        version1 = comboBox1.currentText()
        version2 = comboBox2.currentText()
        stg_text1 = SVM.load_version(version1)
        stg_text2 = SVM.load_version(version2)
        textEdit1.clear()
        textEdit1.append(stg_text1)
        textEdit2.clear()
        textEdit2.append(stg_text2)

    show_diff(textEdit1, textEdit2)


def show_diff(textEdit1, textEdit2):
    """textEdit1(현재 에디터 01~08)와 textEdit2(비교 대상 10)의 내용 비교"""
    global SVM
    text1 = textEdit1.toPlainText()
    text2 = textEdit2.toPlainText()
    if text1 and text2:
        diff_html = compare_and_format(text1, text2)
        textEdit2.setHtml(diff_html)


def compare_and_format(current_text: str, previous_text: str) -> str:
    """
    두 텍스트를 비교하여 HTML 형식의 diff 반환
    """
    diff_list = get_line_diff(previous_text, current_text)
    return format_diff_html(diff_list)


def get_line_diff(text1: str, text2: str) -> list[tuple[str, str]]:
    """
    두 텍스트를 라인별로 비교하여 차이점 반환
    Returns: [(action, line), ...]
    action: 'equal', 'insert', 'delete'
    """
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    matcher = SequenceMatcher(None, lines1, lines2)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                result.append(('equal', line))
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                result.append(('delete', line))
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                result.append(('insert', line))
        elif tag == 'replace':
            for line in lines1[i1:i2]:
                result.append(('delete', line))
            for line in lines2[j1:j2]:
                result.append(('insert', line))

    return result


def format_diff_html(diff_list: list[tuple[str, str]]) -> str:
    """
    diff 결과를 HTML 문자열로 변환
    - insert: + 접두사
    - delete: - 접두사
    - equal: 공백 접두사
    """

    html_lines = [f'<div style="font-size:14px; white-space:pre;">']
    for action, line in diff_list:
        escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        prefix = '+' if action == 'insert' else '-' if action == 'delete' else ''
        html_lines.append(f'{prefix}{escaped_line}')

    html_lines.append('</div>')
    return '\n'.join(html_lines)
