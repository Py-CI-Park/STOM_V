
from io import BytesIO
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QBuffer, QRect, QIODevice
from utility.static_method.static import qtest_qwait
from ui.event_click.button_clicked_shortcut import mnbutton_c_clicked_01


class UpdateTelegramMsg:
    """텔레그램 업데이트 클래스입니다.
    텔레그램 버튼 메시지를 수신하여 버튼명에 맞는 스크린샷 보내기를 수행합니다."""
    def __init__(self, ui):
        self.ui = ui

    def send_screenshot(self, msg):
        """텔레그램으로 수신한 명령을 구분하여 스크린샷을 찍고 텔레그램큐로 전송합니다.
        QBuffer를 사용하여 QPixmap을 바이트 배열로 변환 후 BytesIO로 감싸서 전송"""
        rect = None
        prev_main_btn = None

        if msg == '라이브':
            prev_main_btn = self.ui.main_btn
            mnbutton_c_clicked_01(self.ui, 3)
            qtest_qwait(1)
            if self.ui.market_gubun in (1, 2, 3):
                self.ui.slv_tapWidgett_01.setCurrentIndex(self.ui.slv_index1)
            elif self.ui.market_gubun in (5, 9):
                self.ui.slv_tapWidgett_01.setCurrentIndex(self.ui.slv_index2)
            else:
                self.ui.slv_tapWidgett_01.setCurrentIndex(self.ui.slv_index3)
            qtest_qwait(1)
            widget = QApplication.primaryScreen()
        elif msg == '매도완료':
            widget = self.ui
            rect = QRect(45, 5, 683, 377)
        elif msg == '실현손익':
            widget = self.ui.tj_tableWidgettt
        elif msg == '거래목록':
            widget = self.ui.td_tableWidgettt
        elif msg == '잔고평가':
            widget = self.ui.tj_tableWidgettt
        elif msg == '잔고목록':
            widget = self.ui.jg_tableWidgettt
        elif msg == '관심종목':
            widget = self.ui.gj_tableWidgettt
        else:
            widget = self.ui.cj_tableWidgettt

        if prev_main_btn is not None:
            # noinspection PyUnresolvedReferences
            pixmap = widget.grabWindow(self.ui.winId())
        elif rect is not None:
            # noinspection PyUnresolvedReferences
            pixmap = widget.grab(rect)
        else:
            # noinspection PyUnresolvedReferences
            pixmap = widget.grab()

        qbuffer = QBuffer()
        # noinspection PyUnresolvedReferences
        qbuffer.open(QIODevice.WriteOnly)
        pixmap.save(qbuffer, 'PNG')
        byte_array = qbuffer.data().data()
        qbuffer.close()

        buffer = BytesIO(byte_array)
        buffer.seek(0)
        self.ui.teleQ.put(buffer)

        if prev_main_btn is not None:
            mnbutton_c_clicked_01(self.ui, prev_main_btn)
