
from PyQt5.QtCore import QTimer, QEvent, Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat
from PyQt5.QtWidgets import QTextEdit, QMainWindow, QApplication, QMessageBox

from ui.create_widget.set_style import color_bf_dk
from ui.create_widget.set_widget import PlainTextEdit
from ui.event_keypress.extend_window import extend_window
from ui.etcetera.etc import chart_screenshot, manual_save_and_exit
from ui.event_click.button_clicked_etc import hg_button_clicked_01, hg_button_clicked_02
from ui.event_click.button_clicked_zoom import sz_button_clicked_01, sz_button_clicked_02
from ui.event_click.button_clicked_shortcut import mnbutton_c_clicked_02, mnbutton_c_clicked_03, \
    mnbutton_c_clicked_04, trade_process_kill, mnbutton_c_clicked_01, mnbutton_c_clicked_05, \
    mnbutton_c_clicked_06
from ui.event_click.button_clicked_show_dialog import show_db, show_kimp, show_chart, show_hoga, show_giup, \
    show_treemap, show_qsize, show_backscheduler, show_order
from ui.event_click.button_clicked_stg_editer import stg_editer, opti_editer, opti_test_editer, rwf_test_editer, \
    opti_ga_editer, opti_cond_editer, opti_vars_editer, opti_gavars_editer, backtest_log, backtest_detail

syntax_highlighters = {}


def setup_syntax_highlighter(widget, widget_id):
    """구문 강조 하이라이터를 설정합니다."""
    syntax_highlighters[widget_id] = SyntaxHighlighter(widget)
    syntax_highlighters[widget_id].connect_signal()


def check_python_syntax(text):
    """파이썬 문법을 검사합니다."""
    try:
        compile(text, '<string>', 'exec')
        return None, None
    except SyntaxError as e:
        return str(e), e.lineno
    except Exception as e:
        return str(e), None


class SyntaxHighlighter:
    def __init__(self, widget):
        self.widget = widget
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_syntax)
        self.timer.setSingleShot(True)

    def connect_signal(self):
        self.widget.textChanged.connect(self.schedule_check)

    def schedule_check(self):
        self.timer.start(300)

    def check_syntax(self):
        text = self.widget.toPlainText()
        error_msg, error_line = check_python_syntax(text)
        self.widget.setExtraSelections([])
        if error_msg and error_line:
            lines = text.split('\n')
            if 1 <= error_line <= len(lines):
                cursor = QTextCursor(self.widget.document())
                cursor.setPosition(0)
                for i in range(error_line - 1):
                    cursor.movePosition(QTextCursor.NextBlock)
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                error_format = QTextCharFormat()
                error_format.setBackground(color_bf_dk)
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = error_format
                self.widget.setExtraSelections([selection])


def handle_auto_indent(widget):
    """자동 들여쓰기를 처리합니다."""
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.StartOfLine)
    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
    current_line = cursor.selectedText()

    indent = 0
    for char in current_line:
        if char == ' ':
            indent += 1
        elif char == '\t':
            indent += 4
        else:
            break

    stripped_line = current_line.strip()
    additional_indent = 0

    if stripped_line.endswith(':') or any(stripped_line.startswith(keyword) for keyword in ['if', 'elif']):
        additional_indent = 4
    elif any(stripped_line.endswith(keyword) for keyword in ['True', 'False']):
        additional_indent = -4

    total_indent = max(0, indent + additional_indent)
    widget.textCursor().insertText('\n')

    if total_indent > 0:
        widget.textCursor().insertText(' ' * total_indent)


def event_filter(ui, widget, event):
    """이벤트 필터를 처리합니다."""
    if event.type() != QEvent.KeyPress:
        return QMainWindow.eventFilter(ui, widget, event)

    if widget.__class__ == PlainTextEdit and not (QApplication.keyboardModifiers() & Qt.AltModifier) and \
            not (QApplication.keyboardModifiers() & Qt.ControlModifier):
        widget_id = id(widget)
        if widget_id not in syntax_highlighters:
            setup_syntax_highlighter(widget, widget_id)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            handle_auto_indent(widget)
            return True

        elif event.key() == Qt.Key_Tab:
            if hasattr(widget, 'textCursor') and widget.textCursor().hasSelection():
                cursor = widget.textCursor()
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                cursor.setPosition(start_pos)
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                actual_start = cursor.selectionStart()
                cursor.setPosition(end_pos)
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                actual_end = cursor.selectionEnd()
                cursor.setPosition(actual_start)
                cursor.setPosition(actual_end, QTextCursor.KeepAnchor)
                selected_text = cursor.selectedText()
                selected_text = selected_text.replace('\u2029', '\n')
                lines = selected_text.split('\n')
                indented_lines = ['    ' + line for line in lines]
                indented_text = '\n'.join(indented_lines)
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                cursor.insertText(indented_text)
                cursor.endEditBlock()
                cursor.setPosition(actual_start, QTextCursor.MoveAnchor)
                cursor.setPosition(actual_start + len(indented_text), QTextCursor.KeepAnchor)
                widget.setTextCursor(cursor)
            else:
                cursor = widget.textCursor()
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                line_text = cursor.selectedText()
                indented_line = '    ' + line_text
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                cursor.insertText(indented_line)
                cursor.endEditBlock()
                widget.setTextCursor(cursor)
            return True

        elif event.key() == Qt.Key_Backtab:
            if hasattr(widget, 'textCursor') and widget.textCursor().hasSelection():
                cursor = widget.textCursor()
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                cursor.setPosition(start_pos)
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                actual_start = cursor.selectionStart()
                cursor.setPosition(end_pos)
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                actual_end = cursor.selectionEnd()
                cursor.setPosition(actual_start)
                cursor.setPosition(actual_end, QTextCursor.KeepAnchor)
                selected_text = cursor.selectedText()
                selected_text = selected_text.replace('\u2029', '\n')
                lines = selected_text.split('\n')
                unindented_lines = [line[4:] if line.startswith('    ') else line for line in lines]
                unindented_text = '\n'.join(unindented_lines)
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                cursor.insertText(unindented_text)
                cursor.endEditBlock()
                cursor.setPosition(actual_start, QTextCursor.MoveAnchor)
                cursor.setPosition(actual_start + len(unindented_text), QTextCursor.KeepAnchor)
                widget.setTextCursor(cursor)
            else:
                cursor = widget.textCursor()
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                line_text = cursor.selectedText()
                if line_text.startswith('    '):
                    unindented_line = line_text[4:]
                    cursor.beginEditBlock()
                    cursor.removeSelectedText()
                    cursor.insertText(unindented_line)
                    cursor.endEditBlock()
                    widget.setTextCursor(cursor)
            return True

    if event.key() == Qt.Key_Escape and ui.main_btn == 2:
        if not ui.svc_pushButton_24.isVisible():
            if widget in (ui.ss_textEditttt_01, ui.ss_textEditttt_03):
                sz_button_clicked_01(ui)
            elif widget in (ui.ss_textEditttt_02, ui.ss_textEditttt_04):
                sz_button_clicked_02(ui)
        return True

    elif QApplication.keyboardModifiers() & Qt.AltModifier:
        if ui.main_btn == 2 and \
                event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                                Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
            if event.key() == Qt.Key_1:
                stg_editer(ui)
            elif event.key() == Qt.Key_2:
                opti_editer(ui)
            elif event.key() == Qt.Key_3:
                opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                opti_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                opti_gavars_editer(ui)
            elif event.key() == Qt.Key_9:
                backtest_log(ui)
            elif event.key() == Qt.Key_0:
                backtest_detail(ui)
            elif event.key() == Qt.Key_E:
                extend_window(ui)
            return True

        elif event.key() in (Qt.Key_T, Qt.Key_L, Qt.Key_D, Qt.Key_Z, Qt.Key_K, Qt.Key_C, Qt.Key_H, Qt.Key_G,
                             Qt.Key_U, Qt.Key_Q, Qt.Key_B, Qt.Key_X, Qt.Key_S, Qt.Key_V, Qt.Key_O, Qt.Key_E,
                             Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if event.key() == Qt.Key_T:
                mnbutton_c_clicked_02(ui)
            elif event.key() == Qt.Key_L:
                mnbutton_c_clicked_03(ui)
            elif event.key() == Qt.Key_D:
                show_db(ui)
            elif event.key() == Qt.Key_Z:
                mnbutton_c_clicked_04(ui)
            elif event.key() == Qt.Key_K:
                show_kimp(ui)
            elif event.key() == Qt.Key_C:
                show_chart(ui)
            elif event.key() == Qt.Key_H:
                show_hoga(ui)
            elif event.key() == Qt.Key_G:
                show_giup(ui)
            elif event.key() == Qt.Key_U:
                show_treemap(ui)
            elif event.key() == Qt.Key_Q:
                show_qsize(ui)
            elif event.key() == Qt.Key_B:
                show_backscheduler(ui)
            elif event.key() == Qt.Key_X:
                trade_process_kill(ui)
            elif event.key() == Qt.Key_S:
                chart_screenshot(ui)
            elif event.key() == Qt.Key_V:
                manual_save_and_exit(ui)
            elif event.key() == Qt.Key_O:
                show_order(ui)
            elif event.key() == Qt.Key_E:
                extend_window(ui)
            elif event.key() == Qt.Key_Left:
                hg_button_clicked_01(ui, '이전')
            elif event.key() == Qt.Key_Right:
                hg_button_clicked_01(ui, '다음')
            elif event.key() == Qt.Key_Up:
                hg_button_clicked_02(ui, '매수')
            elif event.key() == Qt.Key_Down:
                hg_button_clicked_02(ui, '매도')
            return True

    elif QApplication.keyboardModifiers() & Qt.ControlModifier:
        if event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_B, Qt.Key_A):
            if event.key() == Qt.Key_1:
                mnbutton_c_clicked_01(ui, 0)
            elif event.key() == Qt.Key_2:
                mnbutton_c_clicked_01(ui, 1)
            elif event.key() == Qt.Key_3:
                mnbutton_c_clicked_01(ui, 2)
            elif event.key() == Qt.Key_4:
                mnbutton_c_clicked_01(ui, 3)
            elif event.key() == Qt.Key_5:
                mnbutton_c_clicked_01(ui, 4)
            elif event.key() == Qt.Key_6:
                mnbutton_c_clicked_01(ui, 5)
            elif event.key() == Qt.Key_B:
                mnbutton_c_clicked_05(ui)
            elif event.key() == Qt.Key_A:
                mnbutton_c_clicked_06(ui)
            return True

    return QMainWindow.eventFilter(ui, widget, event)


def close_event(ui, a):
    """창 닫기 이벤트를 처리합니다."""
    buttonReply = QMessageBox.question(
        ui, "프로그램 종료", "프로그램을 종료합니다.",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        ui.process_kill()
        a.accept()
    else:
        a.ignore()
