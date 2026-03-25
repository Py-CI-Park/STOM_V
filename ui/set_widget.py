
import sys
import pyqtgraph as pg
from traceback import format_exc
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QRect, QEasingCurve, QTimer
from PyQt5.QtWidgets import QPushButton, QFrame, QTextEdit, QComboBox, QCheckBox, QLineEdit, QDateEdit, QProgressBar, \
    QDialog, QTableWidget, QAbstractItemView, QGroupBox, QMessageBox
from utility import syntax
from utility.setting_base import columns_nt, columns_td, columns_jg, columns_cj, columns_hj, columns_hc, columns_ns, \
    columns_gc, columns_hg, columns_jm1, columns_jm2, columns_nd, columns_stg1, columns_stg2, columns_sb, \
    columns_kp, columns_sd, columns_hc2, columns_bt
from ui.set_style import qfont12, style_bc_bt, style_bc_st, style_bc_sl, style_bc_bs, style_bc_by, style_fc_dk, \
    style_bc_bb, style_bc_dk, style_st_cf, style_st_sf, style_st_mf, style_st_sp, style_st_ct, style_st_ks, style_st_ss, \
    style_st_su


def error_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            self_obj = args[0]
            QMessageBox.critical(self_obj.ui.splash, '오류 알림', format_exc())
            sys.exit()
    return wrapper


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
        self.setMouseEnabled(x=False, y=False)
        self.ui   = None
        self.xmin = 0
        self.xmax = 0
        self.ymin = 0
        self.ymax = 0
        self.linked_views = []

        self.zoom_in              = False
        self.right_drag_start_pos = None
        self.is_right_dragging    = False
        self.original_x_range     = None
        self.original_y_range     = None

    def set_uiclass(self, ui_class):
        self.ui = ui_class

    def set_range(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    def is_zoomin(self):
        return self.zoom_in

    def linkX(self, other_view):
        if other_view not in self.linked_views:
            self.linked_views.append(other_view)
            other_view.linked_views.append(self)
            self.sigXRangeChanged.connect(self._update_linked_views)
            other_view.sigXRangeChanged.connect(self._update_linked_views)

    def _update_linked_views(self, _, x_range):
        x_min, x_max = x_range
        for view in self.linked_views:
            if view != self:
                view.setXRange(x_min, x_max, padding=0)

    def mouseClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            try:
                if self.ui.database_chart and self.ui.dialog_hoga.isVisible():
                    if self.ui.dialog_hoga.width() != 852:
                        self.ui.dialog_hoga.setFixedSize(852, 390)
                        self.ui.hj_tableWidgett_01.setGeometry(5, 5, 843, 42)
                        self.ui.hj_tableWidgett_01.setColumnWidth(0, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(1, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(2, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(3, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(4, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(5, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(6, 105)
                        self.ui.hj_tableWidgett_01.setColumnWidth(7, 106)
                        self.ui.hc_tableWidgett_01.setHorizontalHeaderLabels(columns_hc2)
                        self.ui.hc_tableWidgett_02.setVisible(True)
                        self.ui.hg_tableWidgett_01.setGeometry(565, 52, 282, 297)
                    code = self.ui.ct_lineEdittttt_04.text()
                    name = self.ui.ct_lineEdittttt_05.text()
                    ymd  = self.ui.ct_dateEdittttt_01.date().toString('yyyyMMdd')
                    hms  = self.ui.ctpg_labels[0].toPlainText()
                    hms  = hms.split('시간')[1].split('이평')[0].strip().replace(':', '')
                    self.ui.hogaQ.put(('차트용호가정보요청', code, name, ymd + hms))
            except:
                pass
        else:
            super().mouseClickEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.is_right_dragging = True
            self.right_drag_start_pos = ev.pos()
            self.original_x_range = self.viewRange()[0]
            self.original_y_range = self.viewRange()[1]
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self.is_right_dragging and self.right_drag_start_pos is not None:
            current_pos   = ev.pos()
            delta_x       = current_pos.x() - self.right_drag_start_pos.x()
            delta_y       = current_pos.y() - self.right_drag_start_pos.y()
            view_range    = self.viewRange()
            x_range       = view_range[0]
            y_range       = view_range[1]
            current_width = x_range[1] - x_range[0]
            current_height = y_range[1] - y_range[0]

            move_ratio_x  = -delta_x / self.width()
            x_move        = current_width * move_ratio_x
            new_x_min     = self.original_x_range[0] + x_move
            new_x_max     = self.original_x_range[1] + x_move

            move_ratio_y  = delta_y / self.height()
            y_move        = current_height * move_ratio_y
            new_y_min     = self.original_y_range[0] + y_move
            new_y_max     = self.original_y_range[1] + y_move

            if self.xmax > 0:
                if new_x_min < self.xmin:
                    new_x_min = self.xmin
                    new_x_max = new_x_min + current_width
                elif new_x_max > self.xmax:
                    new_x_max = self.xmax
                    new_x_min = new_x_max - current_width

            if self.ymax > 0:
                if new_y_min < self.ymin:
                    new_y_min = self.ymin
                    new_y_max = new_y_min + current_height
                elif new_y_max > self.ymax:
                    new_y_max = self.ymax
                    new_y_min = new_y_max - current_height

            self.setXRange(new_x_min, new_x_max, padding=0)
            self.setYRange(new_y_min, new_y_max, padding=0)
            ev.accept()
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.RightButton:
            was_dragging = False
            if self.is_right_dragging and self.right_drag_start_pos is not None:
                current_pos   = ev.pos()
                move_distance_x = abs(current_pos.x() - self.right_drag_start_pos.x())
                move_distance_y = abs(current_pos.y() - self.right_drag_start_pos.y())
                was_dragging  = move_distance_x > 3 or move_distance_y > 3

            self.is_right_dragging    = False
            self.right_drag_start_pos = None
            self.original_x_range     = None
            self.original_y_range     = None

            if not was_dragging:
                if self.xmax > 0:
                    self.setXRange(self.xmin, self.xmax, padding=0.01)
                    self.setYRange(self.ymin, self.ymax, padding=0.03)
                    self.zoom_in = False
        else:
            super().mouseReleaseEvent(ev)

    def mouseDragEvent(self, ev, axis=None):
        if not self.is_right_dragging:
            super().mouseDragEvent(ev)
            if ev.isFinish():
                self.zoom_in = True


class AnimatedPushButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.hover_animation = None
        self.original_geometry = None
        self.is_hovering = False
        self.animation_timer = None
        self.setup_animations()
    
    def setup_animations(self):
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.animation_timer = QTimer()
        self.animation_timer.setSingleShot(True)
        self.animation_timer.timeout.connect(self._delayed_leave)
    
    def enterEvent(self, event):
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        
        self.is_hovering = True
        self.animation_timer.stop()
        
        # 약간 확장된 크기로 애니메이션
        expanded_rect = QRect(
            self.original_geometry.x() - 2,
            self.original_geometry.y() - 2,
            self.original_geometry.width() + 4,
            self.original_geometry.height() + 4
        )
        
        self.hover_animation.setStartValue(self.geometry())
        self.hover_animation.setEndValue(expanded_rect)
        self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.is_hovering = False
        # 약간의 딜레이 후 애니메이션 실행 (빠른 이동 시 깜빡임 방지)
        self.animation_timer.start(50)
        super().leaveEvent(event)
    
    def _delayed_leave(self):
        if not self.is_hovering and self.original_geometry is not None:
            self.hover_animation.setStartValue(self.geometry())
            self.hover_animation.setEndValue(self.original_geometry)
            self.hover_animation.start()


class WidgetCreater:
    def __init__(self, ui_class):
        self.ui = ui_class

    def setQGroupBox(self, gname, tab):
        groupbox = QGroupBox(gname, tab)
        return groupbox

    def setPushbutton(self, pname, color=0, box=None, cmd=None, icon=None, tip=None, shortcut=None, visible=True, click=None, animated=False):
        if animated:
            if box is not None:
                pushbutton = AnimatedPushButton(pname, box)
            else:
                pushbutton = AnimatedPushButton(pname, self.ui)
        else:
            if box is not None:
                pushbutton = QPushButton(pname, box)
            else:
                pushbutton = QPushButton(pname, self.ui)
        if color == 1:
            pushbutton.setStyleSheet(style_bc_st)
        elif color == 2:
            pushbutton.setStyleSheet(style_bc_by)
        elif color == 3:
            pushbutton.setStyleSheet(style_bc_sl)
        elif color == 4:
            pushbutton.setStyleSheet(style_bc_bs)
        elif color == 5:
            pushbutton.setStyleSheet(style_bc_dk)
        elif color == 6:
            pushbutton.setStyleSheet(style_bc_bb)
        elif color == 7:
            pushbutton.setStyleSheet(style_st_cf)
        elif color == 8:
            pushbutton.setStyleSheet(style_st_sf)
        elif color == 9:
            pushbutton.setStyleSheet(style_st_mf)
        elif color == 10:
            pushbutton.setStyleSheet(style_st_sp)
        elif color == 11:
            pushbutton.setStyleSheet(style_st_ct)
        elif color == 12:
            pushbutton.setStyleSheet(style_st_ks)
        elif color == 13:
            pushbutton.setStyleSheet(style_st_ss)
        elif color == 14:
            pushbutton.setStyleSheet(style_st_su)
        else:
            pushbutton.setStyleSheet(style_bc_bt)
        pushbutton.setFont(qfont12)
        if icon is not None:
            pushbutton.setIcon(icon)
        if tip is not None:
            pushbutton.setToolTip(tip)
        if shortcut is not None:
            pushbutton.setShortcut(shortcut)
        if not visible:
            pushbutton.setVisible(False)
        if click is not None:
            if cmd is not None:
                pushbutton.clicked.connect(lambda: click(cmd))
            else:
                pushbutton.clicked.connect(click)
        return pushbutton

    @staticmethod
    def setLine(tab, width):
        line = QFrame(tab)
        line.setLineWidth(width)
        line.setStyleSheet(style_fc_dk)
        line.setFrameShape(QFrame.HLine)
        return line

    def setTextEdit(self, tab, visible=True, font=None, vscroll=False, filter_=False):
        textedit = QTextEdit(tab)
        textedit.setStyleSheet(style_bc_dk)
        if filter_:
            textedit.installEventFilter(self.ui)
            syntax.PythonHighlighter(textedit)
        else:
            textedit.setReadOnly(True)
        if not vscroll:
            textedit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        textedit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if font is not None:
            textedit.setFont(font)
        if not visible:
            textedit.setVisible(visible)
        return textedit

    @staticmethod
    def setCombobox(tab, font=None, items=None, tip=None, visible=True, activated=None):
        combobox = QComboBox(tab)
        combobox.setStyleSheet(style_fc_dk)
        if font is not None:
            combobox.setFont(font)
        if items is not None:
            for item in items:
                combobox.addItem(item)
        if tip is not None:
            combobox.setToolTip(tip)
        if not visible:
            combobox.setVisible(visible)
        if activated is not None:
            combobox.currentTextChanged.connect(activated)
        return combobox

    @staticmethod
    def setCheckBox(cname, groupbox, checked=False, tip=None, style=None, changed=None):
        checkbox = QCheckBox(cname, groupbox)
        if checked:
            checkbox.setChecked(checked)
        if tip is not None:
            checkbox.setToolTip(tip)
        if style is not None:
            checkbox.setFont(qfont12)
            checkbox.setStyleSheet(style)
        if changed is not None:
            checkbox.stateChanged.connect(changed)
        return checkbox

    @staticmethod
    def setLineedit(groupbox, enter=None, passhide=False, ltext=None, style=None, tip=None, font=None, aleft=False, acenter=False, visible=True, change=None):
        lineedit = QLineEdit(groupbox)
        lineedit.setVisible(visible)
        if aleft:
            lineedit.setAlignment(Qt.AlignLeft)
        else:
            lineedit.setAlignment(Qt.AlignRight)
        if acenter:
            lineedit.setAlignment(Qt.AlignCenter)
        if font is not None:
            lineedit.setFont(font)
        else:
            lineedit.setFont(qfont12)
        if passhide:
            lineedit.setEchoMode(QLineEdit.Password)
        if ltext is not None:
            lineedit.setText(ltext)
        if style is not None:
            lineedit.setStyleSheet(style)
        if tip is not None:
            lineedit.setToolTip(tip)
        if enter:
            lineedit.returnPressed.connect(enter)
        if change:
            lineedit.textChanged.connect(change)
        return lineedit

    @staticmethod
    def setDateEdit(tab, qday=None, addday=None, changed=None):
        dateEdit = QDateEdit(tab)
        if qday is not None:
            qdate = qday
        elif addday is not None:
            qdate = QDate.currentDate().addDays(addday)
            qweek = qdate.dayOfWeek()
            if qweek < 5:
                qdate = qdate.addDays(-6 - qweek)
            else:
                qdate = qdate.addDays(1 - qweek)
        else:
            qdate = QDate.currentDate()
            qweek = qdate.dayOfWeek()
            if qweek < 5:
                qdate = qdate.addDays(-2 - qweek)
            elif qweek > 5:
                qdate = qdate.addDays(5 - qweek)
        dateEdit.setDate(qdate)
        dateEdit.setCalendarPopup(True)
        if changed is not None:
            dateEdit.dateChanged.connect(changed)
        return dateEdit

    @staticmethod
    def setProgressBar(tab, vertical=False, style=None, visible=True):
        progressBar = QProgressBar(tab)
        progressBar.setAlignment(Qt.AlignCenter)
        if vertical:
            progressBar.setOrientation(Qt.Vertical)
        progressBar.setRange(0, 100)
        if style is not None:
            progressBar.setStyleSheet(style)
        if not visible:
            progressBar.setVisible(False)
        return progressBar

    def setaddPlot(self, layout, row, col, colspan=1, dateaxis=True, title=None):
        cb = CustomViewBox()
        cb.set_uiclass(self.ui)
        if not dateaxis:
            subplot = layout.addPlot(row=row, col=col, colspan=colspan, viewBox=cb)
        elif title is not None:
            subplot = layout.addPlot(title=title, row=row, col=col, colspan=colspan, axisItems={'bottom': pg.DateAxisItem()})
        else:
            subplot = layout.addPlot(title=title, row=row, col=col, colspan=colspan, viewBox=cb, axisItems={'bottom': pg.DateAxisItem()})
        subplot.showAxis('left', False)
        subplot.showAxis('right', True)
        subplot.getAxis('right').setStyle(tickTextWidth=45, autoExpandTextSpace=False)
        subplot.getAxis('right').setTickFont(qfont12)
        subplot.getAxis('bottom').setTickFont(qfont12)
        subplot.enableAutoRange(False, False)
        return subplot, cb

    def setDialog(self, name, tab=None):
        if tab is None:
            dialog = QDialog()
        else:
            dialog = QDialog(tab)
        dialog.setWindowTitle(name)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowIcon(self.ui.icon_main)
        dialog.setFont(qfont12)
        return dialog

    def setTablewidget(self, tab, columns, rowcount, vscroll=False, visible=True, clicked=None, valuechanged=None, sortchanged=None):
        tableWidget = QTableWidget(tab)
        tableWidget.verticalHeader().setDefaultSectionSize(23)
        tableWidget.verticalHeader().setVisible(False)
        tableWidget.setAlternatingRowColors(True)
        tableWidget.setSelectionMode(QAbstractItemView.NoSelection)
        tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        if not vscroll:
            tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tableWidget.setColumnCount(len(columns))
        tableWidget.setRowCount(rowcount)
        tableWidget.setHorizontalHeaderLabels(columns)
        if valuechanged is not None:
            tableWidget.verticalScrollBar().valueChanged.connect(valuechanged)
        if sortchanged is not None:
            tableWidget.horizontalHeader().sortIndicatorChanged.connect(valuechanged)
        if not visible:
            tableWidget.setVisible(False)
        if clicked is not None:
            tableWidget.cellClicked.connect(clicked)
        if columns[-1] == 'chh':
            if tab == self.ui.st_tab:
                tableWidget.setColumnWidth(0, 122)
                tableWidget.setColumnWidth(1, 68)
                tableWidget.setColumnWidth(2, 68)
                tableWidget.setColumnWidth(3, 68)
                tableWidget.setColumnWidth(4, 68)
                tableWidget.setColumnWidth(5, 68)
                tableWidget.setColumnWidth(6, 68)
                tableWidget.setColumnWidth(7, 68)
                tableWidget.setColumnWidth(8, 68)
                tableWidget.setColumnWidth(9, 68)
                tableWidget.setColumnWidth(10, 68)
                tableWidget.setColumnWidth(11, 68)
                tableWidget.setColumnWidth(12, 68)
                tableWidget.setColumnWidth(13, 68)
                tableWidget.setColumnWidth(14, 68)
            else:
                tableWidget.setColumnWidth(0, 85)
                tableWidget.setColumnWidth(1, 55)
                tableWidget.setColumnWidth(2, 55)
                tableWidget.setColumnWidth(3, 90)
                tableWidget.setColumnWidth(4, 90)
                tableWidget.setColumnWidth(5, 126)
                tableWidget.setColumnWidth(6, 55)
                tableWidget.setColumnWidth(7, 55)
                tableWidget.setColumnWidth(8, 55)
                tableWidget.setColumnWidth(9, 55)
                tableWidget.setColumnWidth(10, 55)
                tableWidget.setColumnWidth(11, 55)
                tableWidget.setColumnWidth(12, 55)
                tableWidget.setColumnWidth(13, 55)
                tableWidget.setColumnWidth(14, 55)
        elif columns in (columns_nt, columns_nd):
            if tab in (self.ui.slv_tab, self.ui.clv_tab, self.ui.flv_tab):
                tableWidget.setColumnWidth(0, 94)
            else:
                tableWidget.setColumnWidth(0, 100)
            tableWidget.setColumnWidth(1, 100)
            tableWidget.setColumnWidth(2, 100)
            tableWidget.setColumnWidth(3, 100)
            tableWidget.setColumnWidth(4, 100)
            tableWidget.setColumnWidth(5, 66)
            tableWidget.setColumnWidth(6, 100)
        elif columns == columns_sb:
            tableWidget.setColumnWidth(0, 68)
            tableWidget.setColumnWidth(1, 70)
            tableWidget.setColumnWidth(2, 70)
            tableWidget.setColumnWidth(3, 70)
            tableWidget.setColumnWidth(4, 70)
            tableWidget.setColumnWidth(5, 70)
            tableWidget.setColumnWidth(6, 70)
            tableWidget.setColumnWidth(7, 70)
            tableWidget.setColumnWidth(8, 70)
            tableWidget.setColumnWidth(9, 70)
            tableWidget.setColumnWidth(10, 70)
            tableWidget.setColumnWidth(11, 70)
            tableWidget.setColumnWidth(12, 70)
            tableWidget.setColumnWidth(13, 70)
            tableWidget.setColumnWidth(14, 70)
            tableWidget.setColumnWidth(15, 70)
            tableWidget.setColumnWidth(16, 70)
            tableWidget.setColumnWidth(17, 70)
            tableWidget.setColumnWidth(18, 68)
        elif columns == columns_sd:
            tableWidget.setColumnWidth(0, 159)
            tableWidget.setColumnWidth(1, 159)
            tableWidget.setColumnWidth(2, 54)
            tableWidget.setColumnWidth(3, 54)
            tableWidget.setColumnWidth(4, 97)
            tableWidget.setColumnWidth(5, 97)
            tableWidget.setColumnWidth(6, 54)
            tableWidget.setColumnWidth(7, 54)
            tableWidget.setColumnWidth(8, 54)
            tableWidget.setColumnWidth(9, 54)
            tableWidget.setColumnWidth(10, 54)
            tableWidget.setColumnWidth(11, 54)
            tableWidget.setColumnWidth(12, 54)
            tableWidget.setColumnWidth(13, 54)
            tableWidget.setColumnWidth(14, 54)
            tableWidget.setColumnWidth(15, 54)
            tableWidget.setColumnWidth(16, 97)
            tableWidget.setColumnWidth(17, 55)
        elif columns == columns_td and tab == self.ui.ct_tab:
            tableWidget.setColumnWidth(0, 96)
            tableWidget.setColumnWidth(1, 90)
            tableWidget.setColumnWidth(2, 90)
            tableWidget.setColumnWidth(3, 140)
            tableWidget.setColumnWidth(4, 70)
            tableWidget.setColumnWidth(5, 90)
            tableWidget.setColumnWidth(6, 90)
        elif columns == columns_jg:
            if tab == self.ui.ct_tab:
                tableWidget.setColumnWidth(0, 96)
                tableWidget.setColumnWidth(1, 115)
                tableWidget.setColumnWidth(2, 115)
                tableWidget.setColumnWidth(3, 80)
                tableWidget.setColumnWidth(4, 80)
                tableWidget.setColumnWidth(5, 90)
                tableWidget.setColumnWidth(6, 90)
                tableWidget.setColumnWidth(7, 90)
                tableWidget.setColumnWidth(8, 90)
            else:
                tableWidget.setColumnWidth(0, 126)
                tableWidget.setColumnWidth(1, 90)
                tableWidget.setColumnWidth(2, 90)
                tableWidget.setColumnWidth(3, 90)
                tableWidget.setColumnWidth(4, 90)
                tableWidget.setColumnWidth(5, 90)
                tableWidget.setColumnWidth(6, 90)
                tableWidget.setColumnWidth(7, 90)
                tableWidget.setColumnWidth(8, 90)
            tableWidget.setColumnWidth(9, 90)
            tableWidget.setColumnWidth(10, 90)
            tableWidget.setColumnWidth(11, 90)
            tableWidget.setColumnWidth(12, 90)
        elif columns == columns_kp:
            tableWidget.setColumnWidth(0, 90)
            tableWidget.setColumnWidth(1, 120)
            tableWidget.setColumnWidth(2, 120)
            tableWidget.setColumnWidth(3, 90)
            tableWidget.setColumnWidth(4, 90)
        elif columns == columns_cj:
            if tab == self.ui.ct_tab:
                tableWidget.setColumnWidth(0, 96)
                tableWidget.setColumnWidth(1, 90)
                tableWidget.setColumnWidth(2, 125)
                tableWidget.setColumnWidth(3, 125)
                tableWidget.setColumnWidth(4, 55)
                tableWidget.setColumnWidth(5, 105)
                tableWidget.setColumnWidth(6, 70)
                tableWidget.setColumnWidth(7, 90)
                tableWidget.setColumnWidth(8, 90)
            else:
                tableWidget.setColumnWidth(0, 126)
                tableWidget.setColumnWidth(1, 90)
                tableWidget.setColumnWidth(2, 90)
                tableWidget.setColumnWidth(3, 90)
                tableWidget.setColumnWidth(4, 90)
                tableWidget.setColumnWidth(5, 90)
                tableWidget.setColumnWidth(6, 90)
                tableWidget.setColumnWidth(7, 90)
                tableWidget.setColumnWidth(8, 90)
        elif columns == columns_hj:
            tableWidget.setColumnWidth(0, 140)
            tableWidget.setColumnWidth(1, 140)
            tableWidget.setColumnWidth(2, 140)
            tableWidget.setColumnWidth(3, 140)
            tableWidget.setColumnWidth(4, 140)
            tableWidget.setColumnWidth(5, 140)
            tableWidget.setColumnWidth(6, 140)
            tableWidget.setColumnWidth(7, 140)
        elif columns in (columns_hc, columns_hc2, columns_hg):
            tableWidget.setColumnWidth(0, 140)
            tableWidget.setColumnWidth(1, 140)
        elif columns == columns_ns:
            tableWidget.setColumnWidth(0, 140)
            tableWidget.setColumnWidth(1, 140)
            tableWidget.setColumnWidth(2, 410)
            tableWidget.setColumnWidth(3, 410)
        elif columns == columns_gc:
            tableWidget.setColumnWidth(0, 140)
            tableWidget.setColumnWidth(1, 140)
            tableWidget.setColumnWidth(2, 410)
            tableWidget.setColumnWidth(3, 410)
        elif columns == columns_jm1:
            tableWidget.setColumnWidth(0, 70)
            tableWidget.setColumnWidth(1, 62)
            tableWidget.setColumnWidth(2, 62)
            tableWidget.setColumnWidth(3, 62)
            tableWidget.setColumnWidth(4, 62)
        elif columns == columns_jm2:
            tableWidget.setColumnWidth(0, 62)
            tableWidget.setColumnWidth(1, 62)
            tableWidget.setColumnWidth(2, 62)
            tableWidget.setColumnWidth(3, 62)
            tableWidget.setColumnWidth(4, 62)
            tableWidget.setColumnWidth(5, 62)
        elif columns == columns_bt:
            tableWidget.setColumnWidth(0, 87)
            tableWidget.setColumnWidth(1, 60)
            tableWidget.setColumnWidth(2, 130)
            tableWidget.setColumnWidth(3, 130)
            tableWidget.setColumnWidth(4, 60)
            tableWidget.setColumnWidth(5, 60)
            tableWidget.setColumnWidth(6, 60)
            tableWidget.setColumnWidth(7, 80)
            tableWidget.setColumnWidth(8, 80)
            tableWidget.setColumnWidth(9, 60)
            tableWidget.setColumnWidth(10, 90)
            tableWidget.setColumnWidth(11, 90)
            tableWidget.setColumnWidth(12, 600)
            tableWidget.setColumnWidth(13, 750)
        elif columns in (columns_stg1, columns_stg2):
            tableWidget.setColumnWidth(0, 125)
            tableWidget.setColumnWidth(1, 125)
            tableWidget.setColumnWidth(2, 125)
            tableWidget.setColumnWidth(3, 124)
        elif columns == ['종목명']:
            tableWidget.setColumnWidth(0, 120)
        elif columns == ['백테스트 스케쥴']:
            tableWidget.setColumnWidth(0, 500)
        elif columns == ['백테스트 상세기록']:
            tableWidget.setColumnWidth(0, 333)
        else:
            if tab in (self.ui.slv_tab, self.ui.clv_tab, self.ui.flv_tab):
                tableWidget.setColumnWidth(0, 121)
            elif tab == self.ui.ct_tab:
                tableWidget.setColumnWidth(0, 96)
            else:
                tableWidget.setColumnWidth(0, 126)
            if tab == self.ui.ct_tab:
                tableWidget.setColumnWidth(1, 105)
                tableWidget.setColumnWidth(2, 105)
            else:
                tableWidget.setColumnWidth(1, 90)
                tableWidget.setColumnWidth(2, 90)
            tableWidget.setColumnWidth(3, 90)
            tableWidget.setColumnWidth(4, 90)
            tableWidget.setColumnWidth(5, 90)
            tableWidget.setColumnWidth(6, 90)
        return tableWidget
