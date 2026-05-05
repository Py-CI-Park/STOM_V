
class SetLogTap:
    """로그 탭 설정 클래스입니다.
    로그 탭을 설정합니다.
    """
    def __init__(self, ui_class, wc):
        """로그 탭 설정을 초기화합니다.
        Args:
            ui_class: UI 클래스
            wc: 위젯 생성자
        """
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """로그 탭을 설정합니다."""
        self.ui.log_trade_basic_textedit = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)
        self.ui.log_trade_error_textedit = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)
        self.ui.log_system_textedit      = self.wc.setTextEdit(self.ui.lg_tab, vscroll=True)

        self.ui.log_trade_basic_textedit.setGeometry(7, 10, 668, 367)
        self.ui.log_trade_error_textedit.setGeometry(680, 10, 668, 367)
        self.ui.log_system_textedit.setGeometry(7, 382, 1340, 367)
