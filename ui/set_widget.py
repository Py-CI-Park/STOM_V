
import sys
import pyqtgraph as pg
from traceback import format_exc
from PyQt5.QtGui import QPen
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QRect, QEasingCurve, QTimer, QEvent
from PyQt5.QtWidgets import QPushButton, QFrame, QTextEdit, QComboBox, QCheckBox, QLineEdit, QDateEdit, QProgressBar, \
    QDialog, QTableWidget, QAbstractItemView, QGroupBox, QMessageBox, QTableWidgetItem
from utility import syntax
from utility.setting_base import columns_nt, columns_td, columns_jg, columns_cj, columns_hj, columns_hc, columns_ns, \
    columns_gc, columns_hg, columns_jm1, columns_jm2, columns_nd, columns_stg1, columns_stg2, columns_sb, \
    columns_kp, columns_sd, columns_hc2, columns_bt
from ui.set_style import qfont12, style_bc_bt, style_bc_st, style_bc_sl, style_bc_bs, style_bc_by, style_fc_dk, \
    style_bc_bb, style_bc_dk, style_st_cf, style_st_sf, style_st_mf, style_st_sp, style_st_ct, style_st_ks, style_st_ss, \
    style_st_su, color_gb_nm, color_gb_hv, color_bf_dk


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
    """커스텀 뷰박스: 마우스 우클릭 호가창정보표시, 좌드레그 확대, 우클릭 확대복귀, 우드레그 X축 이동"""
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
        self.animation_timer.start(50)
        super().leaveEvent(event)

    def _delayed_leave(self):
        if not self.is_hovering and self.original_geometry is not None:
            self.hover_animation.setStartValue(self.geometry())
            self.hover_animation.setEndValue(self.original_geometry)
            self.hover_animation.start()


class BounceButton(QPushButton):
    """클릭 시 버튼이 커졌다가 원래대로 돌아가는 바운스 애니메이션 버튼"""
    def __init__(self, text, parent=None, scale=1.20, duration=300):
        super().__init__(text, parent)
        self.scale_factor = scale
        self.anim_duration = duration
        self.original_geometry = None
        self.click_animation = None

    def mousePressEvent(self, event):
        """클릭 시 바운스 애니메이션 실행"""
        if event.button() == Qt.LeftButton:
            self._play_bounce_animation()
        super().mousePressEvent(event)

    def _play_bounce_animation(self):
        """버튼 커졌다가 원래대로 돌아가는 애니메이션"""
        self.original_geometry = self.geometry()
        center_x = self.original_geometry.x() + self.original_geometry.width() / 2
        center_y = self.original_geometry.y() + self.original_geometry.height() / 2
        new_width = int(self.original_geometry.width() * self.scale_factor)
        new_height = int(self.original_geometry.height() * self.scale_factor)
        new_x = int(center_x - new_width / 2)
        new_y = int(center_y - new_height / 2)
        expanded_rect = QRect(new_x, new_y, new_width, new_height)
        self.click_animation = QPropertyAnimation(self, b"geometry")
        self.click_animation.setDuration(self.anim_duration)
        self.click_animation.setEasingCurve(QEasingCurve.OutBack)
        self.click_animation.setKeyValueAt(0.0, self.original_geometry)
        self.click_animation.setKeyValueAt(0.4, expanded_rect)
        self.click_animation.setKeyValueAt(1.0, self.original_geometry)
        self.click_animation.start()


class HoverComboBox(QComboBox):
    """마우스 오버 시 드롭다운을 자동으로 열고 닫는 콤보박스"""
    def __init__(self, parent=None, delay_ms=100):
        super().__init__(parent)
        self._is_open = False
        self._is_mouse_over = False
        self._delay_ms = delay_ms
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._try_close)
        self.view().viewport().installEventFilter(self)

    def enterEvent(self, event):
        """마우스가 콤보박스 위로 들어오면 드롭다운 열기"""
        self._is_mouse_over = True
        self._close_timer.stop()
        if not self._is_open:
            self.showPopup()
            self._is_open = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스가 콤보박스 영역을 벗어나면 닫기 타이머 시작"""
        self._is_mouse_over = False
        self._close_timer.start(self._delay_ms)
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        """드롭다운 리스트의 마우스 이벤트 감지"""
        if obj == self.view().viewport():
            if event.type() == QEvent.Enter:
                self._is_mouse_over = True
                self._close_timer.stop()
            elif event.type() == QEvent.Leave:
                self._is_mouse_over = False
                self._close_timer.start(self._delay_ms)
        return super().eventFilter(obj, event)

    def _try_close(self):
        """마우스가 영역 밖에 있으면 드롭다운 닫기"""
        if not self._is_mouse_over:
            self.hidePopup()
            self._is_open = False

    def hidePopup(self):
        """드롭다운이 닫히면 상태 초기화"""
        super().hidePopup()
        self._is_open = False


class HoverGroupBox(QGroupBox):
    """마우스 오버 시 배경색이 변경되는 그룹박스"""
    def __init__(self, title, parent=None, duration=100):
        super().__init__(title, parent)
        self._normal_color = f'rgb({color_gb_nm.red()}, {color_gb_nm.green()}, {color_gb_nm.blue()})'
        self._hover_color = f'rgb({color_gb_hv.red()}, {color_gb_hv.green()}, {color_gb_hv.blue()})'
        self._duration = duration
        self.setStyleSheet(self._build_style(self._normal_color))

    def _build_style(self, bg_color):
        return f"""
            QGroupBox {{
                background-color: {bg_color};
                font-family: "나눔고딕", "Malgun Gothic";
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                font-family: "나눔고딕", "Malgun Gothic";
            }}
            QLabel, QCheckBox, QPushButton, QDateEdit, HoverComboBox {{
                font-family: "나눔고딕", "Malgun Gothic";
            }}
        """

    def enterEvent(self, event):
        """마우스가 들어오면 배경색 변경"""
        self.setStyleSheet(self._build_style(self._hover_color))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스가 나가면 원래 배경색 복원"""
        self.setStyleSheet(self._build_style(self._normal_color))
        super().leaveEvent(event)


class PlainTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        self.insertPlainText(source.text())


class FixedColumnTableWidget(QTableWidget):
    """첫번째 칼럼과 동일한 별도의 자식테이블을 만들어서 부모테이블과 동기화"""
    def __init__(self, parent=None, clicked=None):
        super().__init__(parent)
        self._first_column_table = None
        self._first_column_width = 0
        self._is_fixed = False
        self._clicked = clicked
        self._setup_fixed_column()

    def _setup_fixed_column(self):
        self._first_column_table = QTableWidget(self)
        self._first_column_table.verticalHeader().setDefaultSectionSize(23)
        self._first_column_table.verticalHeader().setVisible(False)
        self._first_column_table.horizontalHeader().setVisible(True)
        self._first_column_table.setAlternatingRowColors(True)
        self._first_column_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._first_column_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._first_column_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._first_column_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._first_column_table.setColumnCount(1)
        self._first_column_table.setFrameStyle(QFrame.NoFrame)
        self._first_column_table.viewport().setAutoFillBackground(True)
        self._first_column_table.hide()
        self._first_column_table.verticalScrollBar().valueChanged.connect(self._sync_child_to_parent_scroll)
        if self._clicked is not None:
            self._first_column_table.cellClicked.connect(self._clicked)
        self.verticalScrollBar().valueChanged.connect(self._sync_parent_to_child_scroll)
        self.horizontalScrollBar().valueChanged.connect(self._update_fixed_column_position)
        self.horizontalHeader().sectionResized.connect(self._on_column_resized)
        self.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)

    def _sync_child_to_parent_scroll(self, value):
        if self._is_fixed:
            self.verticalScrollBar().setValue(value)

    def _sync_parent_to_child_scroll(self, value):
        if self._is_fixed and self._first_column_table:
            self._first_column_table.verticalScrollBar().setValue(value)

    # noinspection PyUnusedLocal
    def _on_column_resized(self, logical_index, old_size, new_size):
        if self._is_fixed and logical_index == 0:
            self._first_column_width = new_size
            self._first_column_table.setColumnWidth(0, new_size)
            self._update_fixed_column_position()

    # noinspection PyUnusedLocal
    def _on_sort_changed(self, logical_index, order):
        if not self._is_fixed or not self._first_column_table:
            return
        QTimer.singleShot(50, self._sync_all_data_to_child)

    def _sync_all_data_to_child(self):
        if not self._is_fixed or not self._first_column_table:
            return

        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                child_item = self._first_column_table.item(row, 0)
                if child_item is None:
                    child_item = QTableWidgetItem(item.text())
                    child_item.setForeground(item.foreground())
                    child_item.setBackground(item.background())
                    child_item.setFont(item.font())
                    child_item.setTextAlignment(item.textAlignment())
                    self._first_column_table.setItem(row, 0, child_item)
                else:
                    child_item.setText(item.text())
                    child_item.setForeground(item.foreground())
                    child_item.setBackground(item.background())
                    child_item.setFont(item.font())
                    child_item.setTextAlignment(item.textAlignment())

    def setFirstColumnFixed(self, fixed=True):
        self._is_fixed = fixed
        if fixed and self.columnCount() > 0:
            self._first_column_width = self.columnWidth(0)
            self._first_column_table.setColumnCount(1)
            self._first_column_table.setRowCount(self.rowCount())
            self._first_column_table.setColumnWidth(0, self._first_column_width)
            self._first_column_table.setHorizontalHeaderLabels([self.horizontalHeaderItem(0).text() if self.horizontalHeaderItem(0) else ''])

            for row in range(self.rowCount()):
                item = self.item(row, 0)
                if item:
                    child_item = QTableWidgetItem(item.text())
                    child_item.setForeground(item.foreground())
                    child_item.setBackground(item.background())
                    child_item.setFont(item.font())
                    child_item.setTextAlignment(item.textAlignment())
                    self._first_column_table.setItem(row, 0, child_item)

            self._first_column_table.show()
            self._update_fixed_column_position()
        else:
            self._first_column_table.hide()

    def _update_fixed_column_position(self):
        if not self._is_fixed or not self._first_column_table:
            return

        header_height = self.horizontalHeader().height()
        viewport_x = self.viewport().x()
        viewport_y = self.viewport().y()
        scroll_x = max(0, -self.horizontalScrollBar().value())
        actual_x = viewport_x + scroll_x

        self._first_column_table.setGeometry(actual_x, viewport_y - header_height,
                                             self._first_column_width, self.viewport().height() + header_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_fixed_column_position()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._update_fixed_column_position()

    def setColumnCount(self, count):
        super().setColumnCount(count)
        if self._is_fixed and count > 0:
            self._first_column_table.setColumnCount(1)

    def setRowCount(self, count):
        super().setRowCount(count)
        if self._is_fixed and self._first_column_table:
            self._first_column_table.setRowCount(count)

    def clearContents(self):
        super().clearContents()
        if self._is_fixed and self._first_column_table:
            self._first_column_table.clearContents()

    def setHorizontalHeaderLabels(self, labels):
        super().setHorizontalHeaderLabels(labels)
        if self._is_fixed and len(labels) > 0:
            self._first_column_table.setHorizontalHeaderLabels([labels[0]])

    def setColumnWidth(self, column, width):
        super().setColumnWidth(column, width)
        if column == 0 and self._is_fixed:
            self._first_column_width = width
            self._first_column_table.setColumnWidth(0, width)
            self._update_fixed_column_position()
        elif column == 0 and not self._is_fixed:
            self._first_column_width = width

    def setItem(self, row, column, item):
        super().setItem(row, column, item)
        if column == 0 and self._is_fixed and item:
            child_item = QTableWidgetItem(item.text())
            child_item.setForeground(item.foreground())
            child_item.setBackground(item.background())
            child_item.setFont(item.font())
            child_item.setTextAlignment(item.textAlignment())
            self._first_column_table.setItem(row, 0, child_item)

    def setCellWidget(self, row, column, widget):
        super().setCellWidget(row, column, widget)
        if column == 0 and self._is_fixed and widget:
            widget_clone = type(widget)()
            if hasattr(widget, 'text'):
                widget_clone.setText(widget.text())
            self._first_column_table.setCellWidget(row, 0, widget_clone)


class WidgetCreater:
    def __init__(self, ui_class):
        self.ui = ui_class

    def setQGroupBox(self, gname, parent, hover=False):
        if hover:
            groupbox = HoverGroupBox(gname, parent)
        else:
            groupbox = QGroupBox(gname, parent)
        return groupbox

    def setPushbutton(self, pname, color=0, parent=None, cmd=None, icon=None, tip=None, shortcut=None, visible=True,
                      click=None, animated=False, bounced=False):
        if animated:
            if parent is not None:
                pushbutton = AnimatedPushButton(pname, parent)
            else:
                pushbutton = AnimatedPushButton(pname, self.ui)
        elif bounced:
            if parent is not None:
                pushbutton = BounceButton(pname, parent)
            else:
                pushbutton = BounceButton(pname, self.ui)
        else:
            if parent is not None:
                pushbutton = QPushButton(pname, parent)
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
    def setLine(parent, width):
        line = QFrame(parent)
        line.setLineWidth(width)
        line.setStyleSheet(style_fc_dk)
        line.setFrameShape(QFrame.HLine)
        return line

    def setTextEdit(self, parent, visible=True, font=None, vscroll=False, filter_=False, event_filter=True):
        if filter_:
            textedit = PlainTextEdit(parent)
        else:
            textedit = QTextEdit(parent)
        textedit.setStyleSheet(style_bc_dk)
        if filter_:
            if event_filter:
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
    def setCombobox(parent, font=None, items=None, tip=None, visible=True, activated=None, hover=True):
        if hover:
            combobox = HoverComboBox(parent)
        else:
            combobox = QComboBox(parent)
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
    def setCheckBox(cname, parent, checked=False, tip=None, style=None, changed=None):
        checkbox = QCheckBox(cname, parent)
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
    def setLineedit(parent, enter=None, passhide=False, ltext=None, style=None, tip=None, font=None, aleft=False, acenter=False, visible=True, change=None):
        lineedit = QLineEdit(parent)
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
    def setDateEdit(parent, qday=None, addday=None, changed=None, popup=True):
        dateEdit = QDateEdit(parent)
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
        if popup:
            dateEdit.setCalendarPopup(True)
        else:
            dateEdit.setReadOnly(True)
        if changed is not None:
            dateEdit.dateChanged.connect(changed)
        return dateEdit

    @staticmethod
    def setProgressBar(parent, vertical=False, style=None, visible=True):
        progressBar = QProgressBar(parent)
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
        transparent_pen = QPen(color_bf_dk)
        subplot.getAxis('right').setPen(transparent_pen)
        subplot.getAxis('bottom').setPen(transparent_pen)
        subplot.getAxis('right').setTickFont(qfont12)
        subplot.getAxis('bottom').setTickFont(qfont12)
        subplot.enableAutoRange(False, False)
        return subplot, cb

    def setDialog(self, name, parent=None):
        if parent is None:
            dialog = QDialog()
        else:
            dialog = QDialog(parent)
        dialog.setWindowTitle(name)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowIcon(self.ui.icon_main)
        dialog.setFont(qfont12)
        return dialog

    def setTablewidget(self, parent, columns, rowcount, vscroll=False, visible=True, clicked=None, valuechanged=None,
                       sortchanged=None, fixed=False):
        if fixed:
            if clicked is not None:
                tableWidget = FixedColumnTableWidget(parent, clicked=clicked)
            else:
                tableWidget = FixedColumnTableWidget(parent)
        else:
            tableWidget = QTableWidget(parent)
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
            if parent == self.ui.st_tab:
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
            if parent in (self.ui.slv_tab, self.ui.clv_tab, self.ui.flv_tab):
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
        elif columns == columns_td and parent == self.ui.ct_tab:
            tableWidget.setColumnWidth(0, 96)
            tableWidget.setColumnWidth(1, 90)
            tableWidget.setColumnWidth(2, 90)
            tableWidget.setColumnWidth(3, 140)
            tableWidget.setColumnWidth(4, 70)
            tableWidget.setColumnWidth(5, 90)
            tableWidget.setColumnWidth(6, 90)
        elif columns == columns_jg:
            if parent == self.ui.ct_tab:
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
            if parent == self.ui.ct_tab:
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
            if parent in (self.ui.slv_tab, self.ui.clv_tab, self.ui.flv_tab):
                tableWidget.setColumnWidth(0, 121)
            elif parent == self.ui.ct_tab:
                tableWidget.setColumnWidth(0, 96)
            else:
                tableWidget.setColumnWidth(0, 126)
            if parent == self.ui.ct_tab:
                tableWidget.setColumnWidth(1, 105)
                tableWidget.setColumnWidth(2, 105)
            else:
                tableWidget.setColumnWidth(1, 90)
                tableWidget.setColumnWidth(2, 90)
            tableWidget.setColumnWidth(3, 90)
            tableWidget.setColumnWidth(4, 90)
            tableWidget.setColumnWidth(5, 90)
            tableWidget.setColumnWidth(6, 90)
        if fixed:
            tableWidget.setFirstColumnFixed(True)
        return tableWidget
