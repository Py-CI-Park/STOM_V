
import pyqtgraph as pg
from PyQt5.QtGui import QFont, QPen, QColor
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect
from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QHBoxLayout
from ui.set_style import color_fg_bc, color_bg_ct, style_ht_gb, style_ht_pb
from ui.set_widget import error_decorator

qfont16 = QFont()
qfont16.setFamily('나눔고딕')
qfont16.setPixelSize(16)
qfont16.setBold(True)

qfont12 = QFont()
qfont12.setFamily('나눔고딕')
qfont12.setPixelSize(12)


class ClickableGroupBox(QGroupBox):
    def __init__(self, title, parent, ui):
        super().__init__(title, parent)
        self.ui = ui
        self.move_gbox = None
        self.animation = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.geometry().width() != 667:
                self._resetAllGroupBoxes()
                current_geometry = (self.geometry().x(), self.geometry().y(), self.geometry().width(), self.geometry().height())

                if self in self.ui.home_gbox_center_list:
                    self.move_gbox = self
                elif self in self.ui.home_gbox_left_up_list:
                    self.move_gbox = self.ui.home_gbox_left_up_list[-1]
                    self.move_gbox.animateGeometry(*current_geometry)
                elif self in self.ui.home_gbox_right_up_list:
                    self.move_gbox = self.ui.home_gbox_right_up_list[-1]
                    self.move_gbox.animateGeometry(*current_geometry)
                elif self in self.ui.home_gbox_left_down_list:
                    self.move_gbox = self.ui.home_gbox_left_down_list[-1]
                    self.move_gbox.animateGeometry(*current_geometry)
                elif self in self.ui.home_gbox_right_down_list:
                    self.move_gbox = self.ui.home_gbox_right_down_list[-1]
                    self.move_gbox.animateGeometry(*current_geometry)

                self.animateGeometry(343, 196, 667, 368, self.onAnimationFinished)

        elif event.button() == Qt.RightButton:
            self._resetAllGroupBoxes()

        super().mousePressEvent(event)

    def onAnimationFinished(self):
        if self in self.ui.home_gbox_center_list:
            self._setVisibleGroupBoxes()
        elif self in self.ui.home_gbox_left_up_list:
            self._setVisibleGroupBoxes()
        elif self in self.ui.home_gbox_right_up_list:
            self._setVisibleGroupBoxes()
        elif self in self.ui.home_gbox_left_down_list:
            self._setVisibleGroupBoxes()
        elif self in self.ui.home_gbox_right_down_list:
            self._setVisibleGroupBoxes()

    def animateGeometry(self, x, y, width, height, callback=None):
        """부드러운 애니메이션으로 위치와 크기 변경"""
        if self.animation: self.animation.stop()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(QRect(x, y, width, height))
        if callback: self.animation.finished.connect(callback)
        self.animation.start()
    
    def _setVisibleGroupBoxes(self):
        """GroupBox 표시 상태 설정"""
        for gbox in self.ui.home_gbox_center_list:
            gbox.setVisible(gbox == self.move_gbox)

    def _resetAllGroupBoxes(self):
        """모든 GroupBox를 원래 위치로 리셋"""
        positions = {
            'kospi_boxxxxxx': (7, 10, 331, 181),
            'kosdaq_boxxxxx': (343, 10, 331, 181),
            'kospi100_boxxx': (7, 196, 331, 181),
            'kospi200_boxxx': (343, 196, 331, 181),
            'future_boxxxxx': (679, 10, 331, 182),
            'usdkrw_boxxxxx': (1015, 10, 331, 182),
            'oilgsl_boxxxxx': (679, 196, 331, 182),
            'gold_boxxxxxxx': (1015, 196, 331, 182),
            'btcusdt_boxxxx': (7, 383, 331, 181),
            'ethusdt_boxxxx': (343, 383, 331, 181),
            'bnbusdt_boxxxx': (7, 569, 331, 181),
            'xrpusdt_boxxxx': (343, 569, 331, 181),
            'solusdt_boxxxx': (679, 383, 331, 182),
            'dogeusdt_boxxx': (1015, 383, 331, 182),
            'adausdt_boxxxx': (679, 569, 331, 182),
            'linkusdt_boxxx': (1015, 569, 331, 182)
        }

        for gbox in self.ui.home_gbox_all_list:
            gbox.setVisible(True)
            gbox_name = next((name for name, pos in positions.items() if getattr(self.ui, name, None) == gbox), None)
            if gbox_name:
                gbox.animateGeometry(*positions[gbox_name])


class SetHomeTap:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def setLabel(self, name, font, left=True):
        label = QLabel(name)
        label.setFont(font)
        if left:
            label.setAlignment(Qt.AlignLeft)
        else:
            label.setAlignment(Qt.AlignRight)
        return label

    def setaddPlot(self):
        subplot = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        subplot.setBackground(color_bg_ct)
        transparent_pen = QPen(QColor(0, 0, 0, 0))

        x_axis = subplot.getAxis('bottom')
        x_axis.setStyle(tickLength=0, tickTextWidth=0, tickTextOffset=1)
        x_axis.setPen(transparent_pen)
        x_axis.setTextPen(color_fg_bc)
        x_axis.setTickFont(qfont12)

        y_axis = subplot.getAxis('right')
        y_axis.setStyle(tickLength=0, tickTextWidth=0, tickTextOffset=1)
        y_axis.setPen(transparent_pen)
        y_axis.setTextPen(color_fg_bc)
        y_axis.setTickFont(qfont12)

        subplot.showAxis('left', False)
        subplot.showAxis('right', False)
        subplot.showAxis('bottom', False)
        subplot.enableMouse(False)
        subplot.getViewBox().setMenuEnabled(False)
        subplot.getViewBox().setMouseEnabled(x=False, y=False)
        return subplot

    @error_decorator
    def set(self):
        self.ui.kospi_boxxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.kosdaq_boxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.kospi100_boxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.kospi200_boxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.future_boxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.usdkrw_boxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.oilgsl_boxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.gold_boxxxxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)

        self.ui.btcusdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.ethusdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.bnbusdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.xrpusdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.solusdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.dogeusdt_boxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.adausdt_boxxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)
        self.ui.linkusdt_boxxx = ClickableGroupBox('', self.ui.hm_tab, self.ui)

        self.ui.home_gbox_all_list = [
            self.ui.kospi_boxxxxxx, self.ui.kosdaq_boxxxxx, self.ui.kospi100_boxxx, self.ui.kospi200_boxxx,
            self.ui.future_boxxxxx, self.ui.usdkrw_boxxxxx, self.ui.gold_boxxxxxxx, self.ui.oilgsl_boxxxxx,
            self.ui.btcusdt_boxxxx, self.ui.bnbusdt_boxxxx, self.ui.xrpusdt_boxxxx, self.ui.ethusdt_boxxxx,
            self.ui.solusdt_boxxxx, self.ui.dogeusdt_boxxx, self.ui.adausdt_boxxxx, self.ui.linkusdt_boxxx
        ]

        self.ui.home_gbox_left_up_list = [
            self.ui.kospi_boxxxxxx, self.ui.kosdaq_boxxxxx, self.ui.kospi100_boxxx, self.ui.kospi200_boxxx
        ]

        self.ui.home_gbox_right_up_list = [
            self.ui.future_boxxxxx, self.ui.usdkrw_boxxxxx, self.ui.gold_boxxxxxxx, self.ui.oilgsl_boxxxxx
        ]

        self.ui.home_gbox_left_down_list = [
            self.ui.btcusdt_boxxxx, self.ui.bnbusdt_boxxxx, self.ui.xrpusdt_boxxxx, self.ui.ethusdt_boxxxx
        ]

        self.ui.home_gbox_right_down_list = [
            self.ui.dogeusdt_boxxx, self.ui.adausdt_boxxxx, self.ui.linkusdt_boxxx, self.ui.solusdt_boxxxx
        ]

        self.ui.home_gbox_center_list = [
            self.ui.kospi200_boxxx, self.ui.oilgsl_boxxxxx, self.ui.ethusdt_boxxxx, self.ui.solusdt_boxxxx
        ]

        self.ui.kospi_boxxxxxx.setStyleSheet(style_ht_gb)
        self.ui.kosdaq_boxxxxx.setStyleSheet(style_ht_gb)
        self.ui.kospi100_boxxx.setStyleSheet(style_ht_gb)
        self.ui.kospi200_boxxx.setStyleSheet(style_ht_gb)
        self.ui.future_boxxxxx.setStyleSheet(style_ht_gb)
        self.ui.usdkrw_boxxxxx.setStyleSheet(style_ht_gb)
        self.ui.oilgsl_boxxxxx.setStyleSheet(style_ht_gb)
        self.ui.gold_boxxxxxxx.setStyleSheet(style_ht_gb)

        self.ui.btcusdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.ethusdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.bnbusdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.xrpusdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.solusdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.dogeusdt_boxxx.setStyleSheet(style_ht_gb)
        self.ui.adausdt_boxxxx.setStyleSheet(style_ht_gb)
        self.ui.linkusdt_boxxx.setStyleSheet(style_ht_gb)

        self.ui.kospi_boxxxxxx.setGeometry(7, 10, 331, 181)
        self.ui.kosdaq_boxxxxx.setGeometry(343, 10, 331, 181)
        self.ui.kospi100_boxxx.setGeometry(7, 196, 331, 181)
        self.ui.kospi200_boxxx.setGeometry(343, 196, 331, 181)
        self.ui.future_boxxxxx.setGeometry(679, 10, 331, 182)
        self.ui.usdkrw_boxxxxx.setGeometry(1015, 10, 331, 182)
        self.ui.oilgsl_boxxxxx.setGeometry(679, 196, 331, 182)
        self.ui.gold_boxxxxxxx.setGeometry(1015, 196, 331, 182)

        self.ui.btcusdt_boxxxx.setGeometry(7, 383, 331, 181)
        self.ui.ethusdt_boxxxx.setGeometry(343, 383, 331, 181)
        self.ui.bnbusdt_boxxxx.setGeometry(7, 569, 331, 181)
        self.ui.xrpusdt_boxxxx.setGeometry(343, 569, 331, 181)
        self.ui.solusdt_boxxxx.setGeometry(679, 383, 331, 182)
        self.ui.dogeusdt_boxxx.setGeometry(1015, 383, 331, 182)
        self.ui.adausdt_boxxxx.setGeometry(679, 569, 331, 182)
        self.ui.linkusdt_boxxx.setGeometry(1015, 569, 331, 182)

        kospi_vlayout    = QVBoxLayout(self.ui.kospi_boxxxxxx)
        kosdaq_vlayout   = QVBoxLayout(self.ui.kosdaq_boxxxxx)
        kospi100_vlayout = QVBoxLayout(self.ui.kospi100_boxxx)
        kospi200_vlayout = QVBoxLayout(self.ui.kospi200_boxxx)
        future_vlayout   = QVBoxLayout(self.ui.future_boxxxxx)
        usdkrw_vlayout   = QVBoxLayout(self.ui.usdkrw_boxxxxx)
        oilgsl_vlayout   = QVBoxLayout(self.ui.oilgsl_boxxxxx)
        gold_vlayout     = QVBoxLayout(self.ui.gold_boxxxxxxx)

        btcusdt_vlayout  = QVBoxLayout(self.ui.btcusdt_boxxxx)
        ethusdt_vlayout  = QVBoxLayout(self.ui.ethusdt_boxxxx)
        bnbusdt_vlayout  = QVBoxLayout(self.ui.bnbusdt_boxxxx)
        xrpusdt_vlayout  = QVBoxLayout(self.ui.xrpusdt_boxxxx)
        solusdt_vlayout  = QVBoxLayout(self.ui.solusdt_boxxxx)
        dogeusdt_vlayout = QVBoxLayout(self.ui.dogeusdt_boxxx)
        adausdt_vlayout  = QVBoxLayout(self.ui.adausdt_boxxxx)
        linkusdt_vlayout = QVBoxLayout(self.ui.linkusdt_boxxx)

        kospi_h1layout    = QHBoxLayout()
        kosdaq_h1layout   = QHBoxLayout()
        kospi100_h1layout = QHBoxLayout()
        kospi200_h1layout = QHBoxLayout()
        future_h1layout   = QHBoxLayout()
        usdkrw_h1layout   = QHBoxLayout()
        oilgsl_h1layout   = QHBoxLayout()
        gold_h1layout     = QHBoxLayout()

        btcusdt_h1layout  = QHBoxLayout()
        ethusdt_h1layout  = QHBoxLayout()
        bnbusdt_h1layout  = QHBoxLayout()
        xrpusdt_h1layout  = QHBoxLayout()
        solusdt_h1layout  = QHBoxLayout()
        dogeusdt_h1layout = QHBoxLayout()
        adausdt_h1layout  = QHBoxLayout()
        linkusdt_h1layout = QHBoxLayout()

        kospi_h2layout    = QHBoxLayout()
        kosdaq_h2layout   = QHBoxLayout()
        kospi100_h2layout = QHBoxLayout()
        kospi200_h2layout = QHBoxLayout()
        future_h2layout   = QHBoxLayout()
        usdkrw_h2layout   = QHBoxLayout()
        oilgsl_h2layout   = QHBoxLayout()
        gold_h2layout     = QHBoxLayout()

        btcusdt_h2layout  = QHBoxLayout()
        ethusdt_h2layout  = QHBoxLayout()
        bnbusdt_h2layout  = QHBoxLayout()
        xrpusdt_h2layout  = QHBoxLayout()
        solusdt_h2layout  = QHBoxLayout()
        dogeusdt_h2layout = QHBoxLayout()
        adausdt_h2layout  = QHBoxLayout()
        linkusdt_h2layout = QHBoxLayout()

        self.ui.kospi_pbtnnnnn = self.wc.setPushbutton('', icon=self.ui.icon_korea, color=6)
        self.ui.kosdaq_pbtnnnn = self.wc.setPushbutton('', icon=self.ui.icon_korea, color=6)
        self.ui.kospi100_pbtnn = self.wc.setPushbutton('', icon=self.ui.icon_korea, color=6)
        self.ui.kospi200_pbtnn = self.wc.setPushbutton('', icon=self.ui.icon_korea, color=6)
        self.ui.future_pbtnnnn = self.wc.setPushbutton('', icon=self.ui.icon_korea, color=6)
        self.ui.usdkrw_pbtnnnn = self.wc.setPushbutton('', icon=self.ui.icon_usdkrw, color=6)
        self.ui.oilgsl_pbtnnnn = self.wc.setPushbutton('', icon=self.ui.icon_oilgsl, color=6)
        self.ui.gold_pbtnnnnnn = self.wc.setPushbutton('', icon=self.ui.icon_gold, color=6)

        self.ui.kospi_pbtnnnnn.setStyleSheet(style_ht_pb)
        self.ui.kosdaq_pbtnnnn.setStyleSheet(style_ht_pb)
        self.ui.kospi100_pbtnn.setStyleSheet(style_ht_pb)
        self.ui.kospi200_pbtnn.setStyleSheet(style_ht_pb)
        self.ui.future_pbtnnnn.setStyleSheet(style_ht_pb)
        self.ui.usdkrw_pbtnnnn.setStyleSheet(style_ht_pb)
        self.ui.oilgsl_pbtnnnn.setStyleSheet(style_ht_pb)
        self.ui.gold_pbtnnnnnn.setStyleSheet(style_ht_pb)

        self.ui.kospi_labellll = self.setLabel('코스피', qfont16)
        self.ui.kosdaq_labelll = self.setLabel('코스닥', qfont16)
        self.ui.kospi100_label = self.setLabel('코스피100', qfont16)
        self.ui.kospi200_label = self.setLabel('코스피200', qfont16)
        self.ui.future_labelll = self.setLabel('코스피200선물', qfont16)
        self.ui.usdkrw_labelll = self.setLabel('환율', qfont16)
        self.ui.oilgsl_labelll = self.setLabel('휘발유', qfont16)
        self.ui.gold_labelllll = self.setLabel('국제금', qfont16)

        self.ui.btcusdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_btc, color=6)
        self.ui.ethusdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_eth, color=6)
        self.ui.bnbusdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_bnb, color=6)
        self.ui.xrpusdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_xrp, color=6)
        self.ui.solusdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_sol, color=6)
        self.ui.dogeusdt_pbtnn = self.wc.setPushbutton('', icon=self.ui.icon_doge, color=6)
        self.ui.adausdt_pbtnnn = self.wc.setPushbutton('', icon=self.ui.icon_ada, color=6)
        self.ui.linkusdt_pbtnn = self.wc.setPushbutton('', icon=self.ui.icon_link, color=6)

        self.ui.btcusdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.ethusdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.bnbusdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.xrpusdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.solusdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.dogeusdt_pbtnn.setStyleSheet(style_ht_pb)
        self.ui.adausdt_pbtnnn.setStyleSheet(style_ht_pb)
        self.ui.linkusdt_pbtnn.setStyleSheet(style_ht_pb)

        self.ui.btcusdt_labell = self.setLabel('BTC/USDT', qfont16)
        self.ui.ethusdt_labell = self.setLabel('ETH/USDT', qfont16)
        self.ui.bnbusdt_labell = self.setLabel('BNB/USDT', qfont16)
        self.ui.xrpusdt_labell = self.setLabel('XRP/USDT', qfont16)
        self.ui.solusdt_labell = self.setLabel('SOL/USDT', qfont16)
        self.ui.dogeusdt_label = self.setLabel('DOGE/USDT', qfont16)
        self.ui.adausdt_labell = self.setLabel('ADA/USDT', qfont16)
        self.ui.linkusdt_label = self.setLabel('LINK/USDT', qfont16)

        kospi_h1layout.addWidget(self.ui.kospi_pbtnnnnn, stretch=1)
        kospi_h1layout.addWidget(self.ui.kospi_labellll, stretch=30)
        kosdaq_h1layout.addWidget(self.ui.kosdaq_pbtnnnn, stretch=1)
        kosdaq_h1layout.addWidget(self.ui.kosdaq_labelll, stretch=30)
        kospi100_h1layout.addWidget(self.ui.kospi100_pbtnn, stretch=1)
        kospi100_h1layout.addWidget(self.ui.kospi100_label, stretch=30)
        kospi200_h1layout.addWidget(self.ui.kospi200_pbtnn, stretch=1)
        kospi200_h1layout.addWidget(self.ui.kospi200_label, stretch=30)
        future_h1layout.addWidget(self.ui.future_pbtnnnn, stretch=1)
        future_h1layout.addWidget(self.ui.future_labelll, stretch=30)
        usdkrw_h1layout.addWidget(self.ui.usdkrw_pbtnnnn, stretch=1)
        usdkrw_h1layout.addWidget(self.ui.usdkrw_labelll, stretch=30)
        oilgsl_h1layout.addWidget(self.ui.oilgsl_pbtnnnn, stretch=1)
        oilgsl_h1layout.addWidget(self.ui.oilgsl_labelll, stretch=30)
        gold_h1layout.addWidget(self.ui.gold_pbtnnnnnn, stretch=1)
        gold_h1layout.addWidget(self.ui.gold_labelllll, stretch=30)

        btcusdt_h1layout.addWidget(self.ui.btcusdt_pbtnnn, stretch=1)
        btcusdt_h1layout.addWidget(self.ui.btcusdt_labell, stretch=30)
        ethusdt_h1layout.addWidget(self.ui.ethusdt_pbtnnn, stretch=1)
        ethusdt_h1layout.addWidget(self.ui.ethusdt_labell, stretch=30)
        bnbusdt_h1layout.addWidget(self.ui.bnbusdt_pbtnnn, stretch=1)
        bnbusdt_h1layout.addWidget(self.ui.bnbusdt_labell, stretch=30)
        xrpusdt_h1layout.addWidget(self.ui.xrpusdt_pbtnnn, stretch=1)
        xrpusdt_h1layout.addWidget(self.ui.xrpusdt_labell, stretch=30)
        solusdt_h1layout.addWidget(self.ui.solusdt_pbtnnn, stretch=1)
        solusdt_h1layout.addWidget(self.ui.solusdt_labell, stretch=30)
        dogeusdt_h1layout.addWidget(self.ui.dogeusdt_pbtnn, stretch=1)
        dogeusdt_h1layout.addWidget(self.ui.dogeusdt_label, stretch=30)
        adausdt_h1layout.addWidget(self.ui.adausdt_pbtnnn, stretch=1)
        adausdt_h1layout.addWidget(self.ui.adausdt_labell, stretch=30)
        linkusdt_h1layout.addWidget(self.ui.linkusdt_pbtnn, stretch=1)
        linkusdt_h1layout.addWidget(self.ui.linkusdt_label, stretch=30)

        self.ui.home_label_001 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_002 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_003 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_004 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_005 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_006 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_007 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_008 = self.setLabel('데이터 검색 중 ...', qfont16)

        self.ui.home_label_009 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_010 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_011 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_012 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_013 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_014 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_015 = self.setLabel('데이터 검색 중 ...', qfont16)
        self.ui.home_label_016 = self.setLabel('데이터 검색 중 ...', qfont16)

        self.ui.home_label_017 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_018 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_019 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_020 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_021 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_022 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_023 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_024 = self.setLabel('', qfont16, left=False)

        self.ui.home_label_025 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_026 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_027 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_028 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_029 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_030 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_031 = self.setLabel('', qfont16, left=False)
        self.ui.home_label_032 = self.setLabel('', qfont16, left=False)

        kospi_h2layout.addWidget(self.ui.home_label_001, stretch=1)
        kospi_h2layout.addWidget(self.ui.home_label_017, stretch=1)
        kosdaq_h2layout.addWidget(self.ui.home_label_002, stretch=1)
        kosdaq_h2layout.addWidget(self.ui.home_label_018, stretch=1)
        kospi100_h2layout.addWidget(self.ui.home_label_003, stretch=1)
        kospi100_h2layout.addWidget(self.ui.home_label_019, stretch=1)
        kospi200_h2layout.addWidget(self.ui.home_label_004, stretch=1)
        kospi200_h2layout.addWidget(self.ui.home_label_020, stretch=1)
        future_h2layout.addWidget(self.ui.home_label_005, stretch=1)
        future_h2layout.addWidget(self.ui.home_label_021, stretch=1)
        usdkrw_h2layout.addWidget(self.ui.home_label_006, stretch=1)
        usdkrw_h2layout.addWidget(self.ui.home_label_022, stretch=1)
        oilgsl_h2layout.addWidget(self.ui.home_label_007, stretch=1)
        oilgsl_h2layout.addWidget(self.ui.home_label_023, stretch=1)
        gold_h2layout.addWidget(self.ui.home_label_008, stretch=1)
        gold_h2layout.addWidget(self.ui.home_label_024, stretch=1)

        btcusdt_h2layout.addWidget(self.ui.home_label_009, stretch=1)
        btcusdt_h2layout.addWidget(self.ui.home_label_025, stretch=1)
        ethusdt_h2layout.addWidget(self.ui.home_label_010, stretch=1)
        ethusdt_h2layout.addWidget(self.ui.home_label_026, stretch=1)
        bnbusdt_h2layout.addWidget(self.ui.home_label_011, stretch=1)
        bnbusdt_h2layout.addWidget(self.ui.home_label_027, stretch=1)
        xrpusdt_h2layout.addWidget(self.ui.home_label_012, stretch=1)
        xrpusdt_h2layout.addWidget(self.ui.home_label_028, stretch=1)
        solusdt_h2layout.addWidget(self.ui.home_label_013, stretch=1)
        solusdt_h2layout.addWidget(self.ui.home_label_029, stretch=1)
        dogeusdt_h2layout.addWidget(self.ui.home_label_014, stretch=1)
        dogeusdt_h2layout.addWidget(self.ui.home_label_030, stretch=1)
        adausdt_h2layout.addWidget(self.ui.home_label_015, stretch=1)
        adausdt_h2layout.addWidget(self.ui.home_label_031, stretch=1)
        linkusdt_h2layout.addWidget(self.ui.home_label_016, stretch=1)
        linkusdt_h2layout.addWidget(self.ui.home_label_032, stretch=1)

        self.ui.homepg   = {}

        kospi_plot    = self.setaddPlot()
        kosdaq_plot   = self.setaddPlot()
        kospi100_plot = self.setaddPlot()
        kospi200_plot = self.setaddPlot()
        future_plot   = self.setaddPlot()
        usdkrw_plot   = self.setaddPlot()
        oilgsl_plot   = self.setaddPlot()
        gold_plot     = self.setaddPlot()
        btcusdt_plot  = self.setaddPlot()
        ethusdt_plot  = self.setaddPlot()
        bnbusdt_plot  = self.setaddPlot()
        xrpusdt_plot  = self.setaddPlot()
        solusdt_plot  = self.setaddPlot()
        dogeusdt_plot = self.setaddPlot()
        adausdt_plot  = self.setaddPlot()
        linkusdt_plot = self.setaddPlot()

        self.ui.homepg[0]  = kospi_plot
        self.ui.homepg[1]  = kosdaq_plot
        self.ui.homepg[2]  = kospi100_plot
        self.ui.homepg[3]  = kospi200_plot
        self.ui.homepg[4]  = future_plot
        self.ui.homepg[5]  = usdkrw_plot
        self.ui.homepg[6]  = oilgsl_plot
        self.ui.homepg[7]  = gold_plot
        self.ui.homepg[8]  = btcusdt_plot
        self.ui.homepg[9]  = ethusdt_plot
        self.ui.homepg[10] = bnbusdt_plot
        self.ui.homepg[11] = xrpusdt_plot
        self.ui.homepg[12] = solusdt_plot
        self.ui.homepg[13] = dogeusdt_plot
        self.ui.homepg[14] = adausdt_plot
        self.ui.homepg[15] = linkusdt_plot

        kospi_vlayout.addLayout(kospi_h1layout, stretch=1)
        kospi_vlayout.addLayout(kospi_h2layout, stretch=1)
        kospi_vlayout.addWidget(kospi_plot, stretch=30)

        kosdaq_vlayout.addLayout(kosdaq_h1layout, stretch=1)
        kosdaq_vlayout.addLayout(kosdaq_h2layout, stretch=1)
        kosdaq_vlayout.addWidget(kosdaq_plot, stretch=30)

        kospi100_vlayout.addLayout(kospi100_h1layout, stretch=1)
        kospi100_vlayout.addLayout(kospi100_h2layout, stretch=1)
        kospi100_vlayout.addWidget(kospi100_plot, stretch=30)

        kospi200_vlayout.addLayout(kospi200_h1layout, stretch=1)
        kospi200_vlayout.addLayout(kospi200_h2layout, stretch=1)
        kospi200_vlayout.addWidget(kospi200_plot, stretch=30)

        future_vlayout.addLayout(future_h1layout, stretch=1)
        future_vlayout.addLayout(future_h2layout, stretch=1)
        future_vlayout.addWidget(future_plot, stretch=30)

        usdkrw_vlayout.addLayout(usdkrw_h1layout, stretch=1)
        usdkrw_vlayout.addLayout(usdkrw_h2layout, stretch=1)
        usdkrw_vlayout.addWidget(usdkrw_plot, stretch=30)

        oilgsl_vlayout.addLayout(oilgsl_h1layout, stretch=1)
        oilgsl_vlayout.addLayout(oilgsl_h2layout, stretch=1)
        oilgsl_vlayout.addWidget(oilgsl_plot, stretch=30)

        gold_vlayout.addLayout(gold_h1layout, stretch=1)
        gold_vlayout.addLayout(gold_h2layout, stretch=1)
        gold_vlayout.addWidget(gold_plot, stretch=30)

        btcusdt_vlayout.addLayout(btcusdt_h1layout, stretch=1)
        btcusdt_vlayout.addLayout(btcusdt_h2layout, stretch=1)
        btcusdt_vlayout.addWidget(btcusdt_plot, stretch=30)

        ethusdt_vlayout.addLayout(ethusdt_h1layout, stretch=1)
        ethusdt_vlayout.addLayout(ethusdt_h2layout, stretch=1)
        ethusdt_vlayout.addWidget(ethusdt_plot, stretch=30)

        bnbusdt_vlayout.addLayout(bnbusdt_h1layout, stretch=1)
        bnbusdt_vlayout.addLayout(bnbusdt_h2layout, stretch=1)
        bnbusdt_vlayout.addWidget(bnbusdt_plot, stretch=30)

        xrpusdt_vlayout.addLayout(xrpusdt_h1layout, stretch=1)
        xrpusdt_vlayout.addLayout(xrpusdt_h2layout, stretch=1)
        xrpusdt_vlayout.addWidget(xrpusdt_plot, stretch=30)

        solusdt_vlayout.addLayout(solusdt_h1layout, stretch=1)
        solusdt_vlayout.addLayout(solusdt_h2layout, stretch=1)
        solusdt_vlayout.addWidget(solusdt_plot, stretch=30)

        dogeusdt_vlayout.addLayout(dogeusdt_h1layout, stretch=1)
        dogeusdt_vlayout.addLayout(dogeusdt_h2layout, stretch=1)
        dogeusdt_vlayout.addWidget(dogeusdt_plot, stretch=30)

        adausdt_vlayout.addLayout(adausdt_h1layout, stretch=1)
        adausdt_vlayout.addLayout(adausdt_h2layout, stretch=1)
        adausdt_vlayout.addWidget(adausdt_plot, stretch=30)

        linkusdt_vlayout.addLayout(linkusdt_h1layout, stretch=1)
        linkusdt_vlayout.addLayout(linkusdt_h2layout, stretch=1)
        linkusdt_vlayout.addWidget(linkusdt_plot, stretch=30)
