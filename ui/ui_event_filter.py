
from ui.set_style import color_bf_dk
from ui.set_widget import PlainTextEdit
from PyQt5.QtCore import QEvent, QTimer
from ui.ui_button_clicked_zoom import *
from ui.ui_button_clicked_editer_coin import *
from ui.ui_button_clicked_editer_stock import *
from ui.ui_extend_window import extend_window
from PyQt5.QtGui import QTextCursor, QTextCharFormat
from PyQt5.QtWidgets import QMainWindow, QTextEdit

syntax_highlighters = {}


def setup_syntax_highlighter(widget, widget_id):
    syntax_highlighters[widget_id] = SyntaxHighlighter(widget)
    syntax_highlighters[widget_id].connect_signal()


def check_python_syntax(text):
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

    @error_decorator
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


@error_decorator
def event_filter(ui, widget, event):
    if event.type() != QEvent.KeyPress:
        return QMainWindow.eventFilter(ui, widget, event)

    if widget.__class__ == PlainTextEdit and not (QApplication.keyboardModifiers() & Qt.AltModifier):
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

    if event.key() == Qt.Key_Escape:
        if not ui.svc_pushButton_24.isVisible():
            if widget in (ui.ss_textEditttt_01, ui.ss_textEditttt_03):
                sz_button_clicked_01(ui)
            elif widget in (ui.ss_textEditttt_02, ui.ss_textEditttt_04):
                sz_button_clicked_02(ui)
        if not ui.cvc_pushButton_24.isVisible():
            if widget in (ui.cs_textEditttt_01, ui.cs_textEditttt_03):
                cz_button_clicked_01(ui)
            elif widget in (ui.cs_textEditttt_02, ui.cs_textEditttt_04):
                cz_button_clicked_02(ui)
        return True

    elif event.key() == Qt.Key_E and (QApplication.keyboardModifiers() & Qt.ShiftModifier):
        extend_window(ui)
        return True

    elif (QApplication.keyboardModifiers() & Qt.AltModifier) and \
            event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                            Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
        if ui.main_btn == 3:
            if event.key() == Qt.Key_1:
                stock_stg_editer(ui)
            elif event.key() == Qt.Key_2:
                stock_opti_editer(ui)
            elif event.key() == Qt.Key_3:
                stock_opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                stock_rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                stock_opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                stock_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                stock_opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                stock_vars_editer(ui)
            elif event.key() == Qt.Key_9:
                stock_backtest_log(ui)
            elif event.key() == Qt.Key_0:
                stock_backtest_detail(ui)
        elif ui.main_btn == 4:
            if event.key() == Qt.Key_1:
                coin_stg_editer(ui)
            elif event.key() == Qt.Key_2:
                coin_opti_editer(ui)
            elif event.key() == Qt.Key_3:
                coin_opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                coin_rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                coin_opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                coin_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                coin_opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                coin_vars_editer(ui)
            elif event.key() == Qt.Key_9:
                coin_backtest_log(ui)
            elif event.key() == Qt.Key_0:
                coin_backtest_detail(ui)
        return True

    return QMainWindow.eventFilter(ui, widget, event)


def close_event(ui, a):
    buttonReply = QMessageBox.question(
        ui, "프로그램 종료", "프로그램을 종료합니다.",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        ui.ProcessKill()
        a.accept()
    else:
        a.ignore()
