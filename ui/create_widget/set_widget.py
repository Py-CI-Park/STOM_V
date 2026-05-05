
import sys
import pyqtgraph as pg
from PyQt5.QtGui import QPen
from traceback import format_exc
from utility.static_method import syntax
from ui.create_widget.set_style import *
from utility.settings.setting_base import *
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QRect, QEasingCurve, QTimer, QEvent
from PyQt5.QtWidgets import QPushButton, QFrame, QTextEdit, QComboBox, QCheckBox, QLineEdit, QDateEdit, QProgressBar, \
    QDialog, QTableWidget, QAbstractItemView, QGroupBox, QMessageBox, QTableWidgetItem, QSizePolicy


def error_decorator(func):
    """에러 처리 데코레이터입니다.
    함수 실행 중 오류 발생 시 메시지 박스를 표시하고 시스템을 종료합니다.
    Args:
        func: 데코레이터를 적용할 함수
    Returns:
        래퍼 함수
    """
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            self_obj = args[0]
            QMessageBox.critical(self_obj.ui.splash, '오류 알림', format_exc())
            sys.exit()
    return wrapper


class CustomViewBox(pg.ViewBox):
    """커스텀 뷰박스 클래스입니다.
    마우스 우클릭 호가창정보표시, 좌드레그 확대, 우클릭 확대복귀, 우드레그 X축 이동 기능을 제공합니다.
    """
    def __init__(self, *args, **kwds):
        """커스텀 뷰박스를 초기화합니다.
        Args:
            *args: 가변 인자
            **kwds: 키워드 인자
        """
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
        """UI 클래스를 설정합니다.
        Args:
            ui_class: UI 클래스 인스턴스
        """
        self.ui = ui_class

    def set_range(self, xmin, xmax, ymin, ymax):
        """뷰 범위를 설정합니다.
        Args:
            xmin: 최소 x 좌표
            xmax: 최대 x 좌표
            ymin: 최소 y 좌표
            ymax: 최대 y 좌표
        """
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    def is_zoomin(self):
        """확대 상태를 반환합니다.
        Returns:
            확대 상태
        """
        return self.zoom_in

    def linkX(self, other_view):
        """다른 뷰와 X축을 연결합니다.
        Args:
            other_view: 연결할 다른 뷰
        """
        if other_view not in self.linked_views:
            self.linked_views.append(other_view)
            other_view.linked_views.append(self)
            self.sigXRangeChanged.connect(self._update_linked_views)
            other_view.sigXRangeChanged.connect(self._update_linked_views)

    def _update_linked_views(self, _, x_range):
        """연결된 뷰를 업데이트합니다.
        Args:
            _: 사용하지 않음
            x_range: X축 범위
        """
        x_min, x_max = x_range
        for view in self.linked_views:
            if view != self:
                view.setXRange(x_min, x_max, padding=0)

    def mouseClickEvent(self, ev):
        """마우스 클릭 이벤트를 처리합니다.
        좌클릭 시 호가창 정보를 요청합니다.
        Args:
            ev: 마우스 이벤트
        """
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
            except Exception:
                pass
        else:
            super().mouseClickEvent(ev)

    def mousePressEvent(self, ev):
        """마우스 누름 이벤트를 처리합니다.
        우클릭 시 드래그 모드를 시작합니다.
        Args:
            ev: 마우스 이벤트
        """
        if ev.button() == Qt.RightButton:
            self.is_right_dragging = True
            self.right_drag_start_pos = ev.pos()
            self.original_x_range = self.viewRange()[0]
            self.original_y_range = self.viewRange()[1]
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        """마우스 이동 이벤트를 처리합니다.
        우클릭 드래그 시 뷰를 이동합니다.
        Args:
            ev: 마우스 이벤트
        """
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
        """마우스 릴리즈 이벤트를 처리합니다.
        우클릭 시 드래그가 아니면 원래 뷰로 복귀합니다.
        Args:
            ev: 마우스 이벤트
        """
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
        """마우스 드래그 이벤트를 처리합니다.
        좌클릭 드래그 시 확대 모드를 설정합니다.
        Args:
            ev: 마우스 이벤트
            axis: 축
        """
        if not self.is_right_dragging:
            super().mouseDragEvent(ev)
            if ev.isFinish():
                self.zoom_in = True


class AnimatedPushButton(QPushButton):
    """호버 애니메이션 푸시버튼 클래스입니다.
    마우스 오버 시 확대 애니메이션을 제공합니다.
    """
    def __init__(self, text, parent=None):
        """애니메이션 푸시버튼을 초기화합니다.
        Args:
            text: 버튼 텍스트
            parent: 부모 위젯
        """
        super().__init__(text, parent)
        self.hover_animation = None
        self.original_geometry = None
        self.is_hovering = False
        self.animation_timer = None
        self.setup_animations()

    def setup_animations(self):
        """애니메이션을 설정합니다."""
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation_timer = QTimer()
        self.animation_timer.setSingleShot(True)
        self.animation_timer.timeout.connect(self._delayed_leave)

    def enterEvent(self, event):
        """마우스 진입 이벤트를 처리합니다.
        버튼을 확대하는 애니메이션을 시작합니다.
        Args:
            event: 이벤트
        """
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
        """마우스 이탈 이벤트를 처리합니다.
        지연 후 버튼을 원래 크기로 복원합니다.
        Args:
            event: 이벤트
        """
        self.is_hovering = False
        self.animation_timer.start(50)
        super().leaveEvent(event)

    def _delayed_leave(self):
        """지연 후 버튼을 원래 크기로 복원합니다."""
        if not self.is_hovering and self.original_geometry is not None:
            self.hover_animation.setStartValue(self.geometry())
            self.hover_animation.setEndValue(self.original_geometry)
            self.hover_animation.start()


class BounceButton(QPushButton):
    """바운스 애니메이션 버튼 클래스입니다.
    클릭 시 버튼이 커졌다가 원래대로 돌아가는 애니메이션을 제공합니다.
    """
    def __init__(self, text, parent=None, scale=1.20, duration=300):
        """바운스 버튼을 초기화합니다.
        Args:
            text: 버튼 텍스트
            parent: 부모 위젯
            scale: 확대 비율
            duration: 애니메이션 지속 시간
        """
        super().__init__(text, parent)
        self.scale_factor = scale
        self.anim_duration = duration
        self.original_geometry = None
        self.click_animation = None

    def mousePressEvent(self, event):
        """마우스 누름 이벤트를 처리합니다.
        좌클릭 시 바운스 애니메이션을 실행합니다.
        Args:
            event: 마우스 이벤트
        """
        if event.button() == Qt.LeftButton:
            self._play_bounce_animation()
        super().mousePressEvent(event)

    def _play_bounce_animation(self):
        """바운스 애니메이션을 실행합니다.
        버튼이 커졌다가 원래대로 돌아가는 애니메이션을 재생합니다.
        """
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
    """호버 콤보박스 클래스입니다.
    마우스 오버 시 드롭다운을 자동으로 열고 닫습니다.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, parent=None, delay_ms=100):
        """호버 콤보박스를 초기화합니다.
        Args:
            parent: 부모 위젯
            delay_ms: 닫기 지연 시간
        """
        super().__init__(parent)
        self._is_open = False
        self._is_mouse_over = False
        self._delay_ms = delay_ms
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._try_close)
        self.view().viewport().installEventFilter(self)

    def enterEvent(self, event):
        """마우스 진입 이벤트를 처리합니다.
        마우스가 콤보박스 위로 들어오면 드롭다운을 엽니다.
        Args:
            event: 이벤트
        """
        self._is_mouse_over = True
        self._close_timer.stop()
        if not self._is_open:
            self.showPopup()
            self._is_open = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스 이탈 이벤트를 처리합니다.
        마우스가 콤보박스 영역을 벗어나면 닫기 타이머를 시작합니다.
        Args:
            event: 이벤트
        """
        self._is_mouse_over = False
        self._close_timer.start(self._delay_ms)
        super().leaveEvent(event)

    # noinspection PyUnresolvedReferences
    def eventFilter(self, obj, event):
        """이벤트 필터를 처리합니다.
        드롭다운 리스트의 마우스 이벤트를 감지합니다.
        Args:
            obj: 객체
            event: 이벤트
        Returns:
            이벤트 필터 결과
        """
        if obj == self.view().viewport():
            if event.type() == QEvent.Enter:
                self._is_mouse_over = True
                self._close_timer.stop()
            elif event.type() == QEvent.Leave:
                self._is_mouse_over = False
                self._close_timer.start(self._delay_ms)
        return super().eventFilter(obj, event)

    def _try_close(self):
        """드롭다운 닫기를 시도합니다.
        마우스가 영역 밖에 있으면 드롭다운을 닫습니다.
        """
        if not self._is_mouse_over:
            self.hidePopup()
            self._is_open = False

    def hidePopup(self):
        """드롭다운을 닫습니다.
        드롭다운이 닫히면 상태를 초기화합니다.
        """
        super().hidePopup()
        self._is_open = False


class HoverGroupBox(QGroupBox):
    """호버 그룹박스 클래스입니다.
    마우스 오버 시 배경색이 변경됩니다.
    """
    def __init__(self, title, parent=None, duration=100):
        """호버 그룹박스를 초기화합니다.
        Args:
            title: 그룹박스 제목
            parent: 부모 위젯
            duration: 애니메이션 지속 시간
        """
        super().__init__(title, parent)
        self._normal_color = f'rgb({color_gb_nm.red()}, {color_gb_nm.green()}, {color_gb_nm.blue()})'
        self._hover_color = f'rgb({color_gb_hv.red()}, {color_gb_hv.green()}, {color_gb_hv.blue()})'
        self._duration = duration
        self.setStyleSheet(self._build_style(self._normal_color))

    def _build_style(self, bg_color):
        """스타일시트를 빌드합니다.
        Args:
            bg_color: 배경색
        Returns:
            스타일시트 문자열
        """
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
        """마우스 진입 이벤트를 처리합니다.
        마우스가 들어오면 배경색을 변경합니다.
        Args:
            event: 이벤트
        """
        self.setStyleSheet(self._build_style(self._hover_color))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스 이탈 이벤트를 처리합니다.
        마우스가 나가면 원래 배경색을 복원합니다.
        Args:
            event: 이벤트
        """
        self.setStyleSheet(self._build_style(self._normal_color))
        super().leaveEvent(event)


class PlainTextEdit(QTextEdit):
    """일반 텍스트 편집 클래스입니다.
    서식 없는 텍스트 붙여넣기만 허용합니다.
    """
    # noinspection PyUnresolvedReferences
    def insertFromMimeData(self, source):
        """마임 데이터를 삽입합니다.
        텍스트만 삽입하여 서식을 제거합니다.
        Args:
            source: 마임 데이터 소스
        """
        self.insertPlainText(source.text())


class FixedColumnTableWidget(QTableWidget):
    """고정 칼럼 테이블 위젯 클래스입니다.
    첫번째 칼럼과 동일한 별도의 자식테이블을 만들어서 부모테이블과 동기화합니다.
    """
    def __init__(self, parent=None, clicked=None):
        """고정 칼럼 테이블 위젯을 초기화합니다.
        Args:
            parent: 부모 위젯
            clicked: 클릭 콜백 함수
        """
        super().__init__(parent)
        self._first_column_table = None
        self._first_column_width = 0
        self._is_fixed = False
        self._clicked = clicked
        self._setup_fixed_column()

    # noinspection PyUnresolvedReferences
    def _setup_fixed_column(self):
        """고정 칼럼을 설정합니다."""
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

    # noinspection PyUnresolvedReferences
    def _sync_child_to_parent_scroll(self, value):
        """자식 테이블 스크롤을 부모 테이블에 동기화합니다.
        Args:
            value: 스크롤 값
        """
        if self._is_fixed:
            self.verticalScrollBar().setValue(value)

    def _sync_parent_to_child_scroll(self, value):
        """부모 테이블 스크롤을 자식 테이블에 동기화합니다.
        Args:
            value: 스크롤 값
        """
        if self._is_fixed and self._first_column_table:
            self._first_column_table.verticalScrollBar().setValue(value)

    # noinspection PyUnusedLocal
    def _on_column_resized(self, logical_index, old_size, new_size):
        """칼럼 리사이즈 이벤트를 처리합니다.
        Args:
            logical_index: 논리적 인덱스
            old_size: 이전 크기
            new_size: 새 크기
        """
        if self._is_fixed and logical_index == 0:
            self._first_column_width = new_size
            self._first_column_table.setColumnWidth(0, new_size)
            self._update_fixed_column_position()

    # noinspection PyUnusedLocal
    def _on_sort_changed(self, logical_index, order):
        """정렬 변경 이벤트를 처리합니다.
        Args:
            logical_index: 논리적 인덱스
            order: 정렬 순서
        """
        if not self._is_fixed or not self._first_column_table:
            return
        QTimer.singleShot(50, self._sync_all_data_to_child)

    def _sync_all_data_to_child(self):
        """모든 데이터를 자식 테이블에 동기화합니다."""
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

    # noinspection PyUnresolvedReferences
    def setFirstColumnFixed(self, fixed=True):
        """첫번째 칼럼 고정을 설정합니다.
        Args:
            fixed: 고정 여부
        """
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

    # noinspection PyUnresolvedReferences
    def _update_fixed_column_position(self):
        """고정 칼럼 위치를 업데이트합니다."""
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
        """리사이즈 이벤트를 처리합니다.
        Args:
            event: 이벤트
        """
        super().resizeEvent(event)
        self._update_fixed_column_position()

    def scrollContentsBy(self, dx, dy):
        """스크롤 이벤트를 처리합니다.
        Args:
            dx: X축 델타
            dy: Y축 델타
        """
        super().scrollContentsBy(dx, dy)
        self._update_fixed_column_position()

    def setColumnCount(self, count):
        """칼럼 수를 설정합니다.
        Args:
            count: 칼럼 수
        """
        super().setColumnCount(count)
        if self._is_fixed and count > 0:
            self._first_column_table.setColumnCount(1)

    def setRowCount(self, count):
        """행 수를 설정합니다.
        Args:
            count: 행 수
        """
        super().setRowCount(count)
        if self._is_fixed and self._first_column_table:
            self._first_column_table.setRowCount(count)

    def clearContents(self):
        """내용을 삭제합니다."""
        super().clearContents()
        if self._is_fixed and self._first_column_table:
            self._first_column_table.clearContents()

    # noinspection PyUnresolvedReferences
    def setHorizontalHeaderLabels(self, labels):
        """수평 헤더 라벨을 설정합니다.
        Args:
            labels: 라벨 리스트
        """
        super().setHorizontalHeaderLabels(labels)
        if self._is_fixed and len(labels) > 0:
            self._first_column_table.setHorizontalHeaderLabels([labels[0]])

    def setColumnWidth(self, column, width):
        """칼럼 너비를 설정합니다.
        Args:
            column: 칼럼 인덱스
            width: 너비
        """
        super().setColumnWidth(column, width)
        if column == 0 and self._is_fixed:
            self._first_column_width = width
            self._first_column_table.setColumnWidth(0, width)
            self._update_fixed_column_position()
        elif column == 0 and not self._is_fixed:
            self._first_column_width = width

    def setItem(self, row, column, item):
        """테이블 아이템을 설정합니다.
        Args:
            row: 행 인덱스
            column: 칼럼 인덱스
            item: 테이블 아이템
        """
        super().setItem(row, column, item)
        if column == 0 and self._is_fixed and item:
            child_item = QTableWidgetItem(item.text())
            child_item.setForeground(item.foreground())
            child_item.setBackground(item.background())
            child_item.setFont(item.font())
            child_item.setTextAlignment(item.textAlignment())
            self._first_column_table.setItem(row, 0, child_item)

    def setCellWidget(self, row, column, widget):
        """셀 위젯을 설정합니다.
        Args:
            row: 행 인덱스
            column: 칼럼 인덱스
            widget: 위젯
        """
        super().setCellWidget(row, column, widget)
        if column == 0 and self._is_fixed and widget:
            widget_clone = type(widget)()
            if hasattr(widget, 'text'):
                widget_clone.setText(widget.text())
            self._first_column_table.setCellWidget(row, 0, widget_clone)


class WidgetCreater:
    """위젯 생성자 클래스입니다.
    다양한 UI 위젯을 생성하고 설정합니다.
    """
    def __init__(self, ui_class):
        """위젯 생성자를 초기화합니다.
        Args:
            ui_class: UI 클래스 인스턴스
        """
        self.ui = ui_class

    def setQGroupBox(self, gname, parent, hover=False):
        """그룹박스를 생성합니다.
        Args:
            gname: 그룹박스 이름
            parent: 부모 위젯
            hover: 호버 효과 사용 여부
        Returns:
            그룹박스 위젯
        """
        if hover:
            groupbox = HoverGroupBox(gname, parent)
        else:
            groupbox = QGroupBox(gname, parent)
        return groupbox

    def setPushbutton(self, pname, color=0, parent=None, cmd=None, icon=None, tip=None, shortcut=None, visible=True,
                      click=None, animated=False, bounced=False):
        """푸시버튼을 생성합니다.
        Args:
            pname: 버튼 이름
            color: 색상 코드
            parent: 부모 위젯
            cmd: 명령어
            icon: 아이콘
            tip: 툴팁
            shortcut: 단축키
            visible: 표시 여부
            click: 클릭 콜백
            animated: 애니메이션 효과
            bounced: 바운스 효과
        Returns:
            푸시버튼 위젯
        """
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
        pushbutton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        """라인을 생성합니다.
        Args:
            parent: 부모 위젯
            width: 라인 너비
        Returns:
            프레임 위젯
        """
        line = QFrame(parent)
        line.setLineWidth(width)
        line.setStyleSheet(style_fc_dk)
        line.setFrameShape(QFrame.HLine)
        return line

    def setTextEdit(self, parent, visible=True, font=None, vscroll=False, filter_=False, event_filter=True):
        """텍스트 에디터를 생성합니다.
        Args:
            parent: 부모 위젯
            visible: 표시 여부
            font: 폰트
            vscroll: 수직 스크롤바 표시 여부
            filter_: 필터 사용 여부
            event_filter: 이벤트 필터 사용 여부
        Returns:
            텍스트 에디터 위젯
        """
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
        """콤보박스를 생성합니다.
        Args:
            parent: 부모 위젯
            font: 폰트
            items: 아이템 리스트
            tip: 툴팁
            visible: 표시 여부
            activated: 활성화 콜백
            hover: 호버 효과 사용 여부
        Returns:
            콤보박스 위젯
        """
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
        """체크박스를 생성합니다.
        Args:
            cname: 체크박스 이름
            parent: 부모 위젯
            checked: 체크 상태
            tip: 툴팁
            style: 스타일
            changed: 변경 콜백
        Returns:
            체크박스 위젯
        """
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
        """라인 에디트를 생성합니다.
        Args:
            parent: 부모 위젯
            enter: 엔터키 콜백
            passhide: 비밀번호 숨김 여부
            ltext: 초기 텍스트
            style: 스타일
            tip: 툴팁
            font: 폰트
            aleft: 좌측 정렬
            acenter: 중앙 정렬
            visible: 표시 여부
            change: 변경 콜백
        Returns:
            라인 에디트 위젯
        """
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
        """날짜 에디트를 생성합니다.
        Args:
            parent: 부모 위젯
            qday: 특정 날짜
            addday: 추가 일수
            changed: 변경 콜백
            popup: 팝업 사용 여부
        Returns:
            날짜 에디트 위젯
        """
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
        """프로그레스바를 생성합니다.
        Args:
            parent: 부모 위젯
            vertical: 수직 방향 여부
            style: 스타일
            visible: 표시 여부
        Returns:
            프로그레스바 위젯
        """
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
        """플롯을 추가합니다.
        Args:
            layout: 레이아웃
            row: 행 위치
            col: 칼럼 위치
            colspan: 칼럼 스팬
            dateaxis: 날짜 축 사용 여부
            title: 제목
        Returns:
            서브플롯과 커스텀 뷰박스
        """
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
        """다이얼로그를 생성합니다.
        Args:
            name: 다이얼로그 이름
            parent: 부모 위젯
        Returns:
            다이얼로그 위젯
        """
        if parent is None:
            dialog = QDialog()
        else:
            dialog = QDialog(parent)
        dialog.setWindowTitle(name)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowIcon(self.ui.icon_main)
        dialog.setFont(qfont12)
        return dialog

    # noinspection PyUnresolvedReferences
    def setTablewidget(self, parent, columns, rowcount, vscroll=False, visible=True, clicked=None, valuechanged=None,
                       sortchanged=None, fixed=False):
        """테이블 위젯을 생성합니다.
        Args:
            parent: 부모 위젯
            columns: 칼럼 리스트
            rowcount: 행 수
            vscroll: 수직 스크롤바 표시 여부
            visible: 표시 여부
            clicked: 클릭 콜백
            valuechanged: 값 변경 콜백
            sortchanged: 정렬 변경 콜백
            fixed: 고정 칼럼 사용 여부
        Returns:
            테이블 위젯
        """
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
            if parent == self.ui.td_tab:
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
        elif columns == columns_jg:
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
            else:
                tableWidget.setColumnWidth(0, 126)
            tableWidget.setColumnWidth(1, 90)
            tableWidget.setColumnWidth(2, 90)
            tableWidget.setColumnWidth(3, 90)
            tableWidget.setColumnWidth(4, 90)
            tableWidget.setColumnWidth(5, 90)
            tableWidget.setColumnWidth(6, 90)
        if fixed:
            tableWidget.setFirstColumnFixed(True)
        return tableWidget
