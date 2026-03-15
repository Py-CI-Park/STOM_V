
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QTextEdit
from utility.static import error_decorator


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
                error_format.setBackground(QColor(100, 100, 120))
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

    if widget.__class__ == QTextEdit:
        widget_id = id(widget)
        if widget_id not in syntax_highlighters:
            setup_syntax_highlighter(widget, widget_id)

        if event.key() == Qt.Key_Return:
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
        else:
            return QMainWindow.eventFilter(ui, widget, event)
    elif event.key() == Qt.Key_Escape:
        if not ui.svc_pushButton_24.isVisible():
            if widget in (ui.ss_textEditttt_01, ui.ss_textEditttt_03):
                ui.szButtonClicked_01()
            elif widget in (ui.ss_textEditttt_02, ui.ss_textEditttt_04):
                ui.szButtonClicked_02()
        if not ui.cvc_pushButton_24.isVisible():
            if widget in (ui.cs_textEditttt_01, ui.cs_textEditttt_03):
                ui.czButtonClicked_01()
            elif widget in (ui.cs_textEditttt_02, ui.cs_textEditttt_04):
                ui.czButtonClicked_02()
        return True
    elif event.key() == Qt.Key_F1:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.ss_textEditttt_01.setFocus()
                ui.StockBuyStgLoad()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_03.setFocus()
                ui.StockOptiBuyLoad()
            elif ui.svo_pushButton_05.isVisible():
                ui.ss_textEditttt_07.setFocus()
                ui.StockCondbuyLoad()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cs_textEditttt_01.setFocus()
                ui.CoinBuyStgLoad()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_04.setFocus()
                ui.CoinOptiBuyLoad()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cs_textEditttt_08.setFocus()
                ui.CoinCondbuyLoad()
        return True
    elif event.key() == Qt.Key_F2:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.ss_textEditttt_01.setFocus()
                ui.svjb_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_03.setFocus()
                ui.svc_comboBoxxx_01.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.ss_textEditttt_07.setFocus()
                ui.svo_comboBoxxx_01.showPopup()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cs_textEditttt_01.setFocus()
                ui.cvjb_comboBoxx_01.showPopup()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_04.setFocus()
                ui.cvc_comboBoxxx_01.showPopup()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cs_textEditttt_08.setFocus()
                ui.cvo_comboBoxxx_01.showPopup()
        return True
    elif event.key() == Qt.Key_F3:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.svjb_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_01.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_01.setFocus()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjb_lineEditt_01.setFocus()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_lineEdittt_01.setFocus()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_lineEdittt_01.setFocus()
        return True
    elif event.key() == Qt.Key_F5:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.ss_textEditttt_02.setFocus()
                ui.StockSellStgLoad()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_04.setFocus()
                ui.StockOptiSellLoad()
            elif ui.svo_pushButton_05.isVisible():
                ui.ss_textEditttt_05.setFocus()
                ui.StockCondsellLoad()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cs_textEditttt_02.setFocus()
                ui.CoinSellStgLoad()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_05.setFocus()
                ui.CoinOptiSample()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cs_textEditttt_06.setFocus()
                ui.CoinCondsellLoad()
        return True
    elif event.key() == Qt.Key_F6:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.ss_textEditttt_02.setFocus()
                ui.svjs_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_03.setFocus()
                ui.svc_comboBoxxx_08.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.ss_textEditttt_04.setFocus()
                ui.svo_comboBoxxx_02.showPopup()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cs_textEditttt_02.setFocus()
                ui.cvjs_comboBoxx_01.showPopup()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_04.setFocus()
                ui.cvc_comboBoxxx_08.showPopup()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cs_textEditttt_05.setFocus()
                ui.cvo_comboBoxxx_02.showPopup()
        return True
    elif event.key() == Qt.Key_F7:
        if ui.main_btn == 2:
            if ui.svj_pushButton_01.isVisible():
                ui.svjs_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_03.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_02.setFocus()
        elif ui.main_btn == 3:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjs_lineEditt_01.setFocus()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_lineEdittt_03.setFocus()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_lineEdittt_02.setFocus()
        return True
    elif event.key() == Qt.Key_F9:
        if ui.main_btn == 2:
            if ui.svc_pushButton_06.isVisible():
                ui.ss_textEditttt_05.setFocus()
                ui.StockOptiVarsLoad()
            elif ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_06.setFocus()
                ui.StockGavarsLoad()
        elif ui.main_btn == 3:
            if ui.cvc_pushButton_06.isVisible():
                ui.cs_textEditttt_06.setFocus()
                ui.CoinOptiVarsLoad()
            elif ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_07.setFocus()
                ui.CoinGavarsSave()
        return True
    elif event.key() == Qt.Key_F10:
        if ui.main_btn == 2:
            if ui.svc_pushButton_06.isVisible():
                ui.ss_textEditttt_05.setFocus()
                ui.svc_comboBoxxx_02.showPopup()
            elif ui.sva_pushButton_03.isVisible():
                ui.ss_textEditttt_06.setFocus()
                ui.sva_comboBoxxx_01.showPopup()
        elif ui.main_btn == 3:
            if ui.cvc_pushButton_06.isVisible():
                ui.cs_textEditttt_06.setFocus()
                ui.cvc_comboBoxxx_02.showPopup()
            elif ui.cva_pushButton_01.isVisible():
                ui.cs_textEditttt_07.setFocus()
                ui.cva_comboBoxxx_01.showPopup()
        return True
    elif event.key() == Qt.Key_F11:
        if ui.main_btn == 2:
            if ui.svc_pushButton_06.isVisible():
                ui.svc_lineEdittt_02.setFocus()
            elif ui.sva_pushButton_03.isVisible():
                ui.sva_lineEdittt_01.setFocus()
        elif ui.main_btn == 3:
            if ui.cvc_pushButton_06.isVisible():
                ui.cvc_lineEdittt_02.setFocus()
            elif ui.cva_pushButton_01.isVisible():
                ui.cva_lineEdittt_01.setFocus()
        return True
    else:
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
