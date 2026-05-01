
from ui.set_widget import error_decorator


class SetLogTap:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.log_trade_basic_textedit = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)
        self.ui.log_trade_error_textedit = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)
        self.ui.log_system_textedit      = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)

        self.ui.log_trade_basic_textedit.setGeometry(7, 10, 668, 367)
        self.ui.log_trade_error_textedit.setGeometry(680, 10, 668, 367)
        self.ui.log_system_textedit.setGeometry(7, 382, 1340, 367)
