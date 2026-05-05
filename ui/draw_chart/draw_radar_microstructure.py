"""
시장미시구조 레이더 차트 시각화 모듈입니다.
PyQtGraph를 사용하여 8개 지표를 레이더 차트 형태로 표시합니다.
이중 다각형 방식으로 외곽은 평균값, 내곽은 현재 값을 표시합니다.
"""
import numpy as np
import pyqtgraph as pg
from typing import List, Tuple
from ui.create_widget.set_style import color_bg_bk


class MicrostructureRadarChart:
    """시장미시구조 레이더 차트 클래스입니다.
    8개 지표(depth_ratio, weighted_depth_ratio, imbalance, pressure_level,
    layering, pump_dump, iceberg, stop_hunt)를 레이더 차트로 시각화합니다.
    Attributes:
        plot_widget: PyQtGraph PlotWidget 인스턴스
        n_axes: 축 개수 (8개)
        axis_names: 각 축의 지표명 리스트
        axis_labels: 각 축의 표시명 리스트 (한글)
        angles: 각 축의 각도 (라디안)
    """

    def __init__(self, size: int, parent=None):
        """초기화 메서드입니다.
        Args:
            parent: 부모 위젯 (None 가능)
            size: 차트 크기 (픽셀)
        """
        self.n_axes       = 8
        self.avg_plot     = None
        self.current_plot = None

        self.axis_names = [
            'depth_ratio', 'weighted_depth_ratio', 'imbalance', 'pressure_level',
            'layering', 'pump_dump', 'iceberg', 'stop_hunt'
        ]
        self.axis_labels = [
            '깊이비율', '가중깊이', '불균형', '상승압력',
            '레이어링', '펌프앤덤프', '아이스버그', '스탑헌트'
        ]

        # 각 축 각도 (0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°)
        self.angles = np.linspace(0, 2 * np.pi, self.n_axes, endpoint=False)

        # UI 설정
        self._setup_ui(parent, size)

    def _setup_ui(self, parent, size: int):
        """UI를 설정합니다.
        Args:
            parent: 부모 위젯
            size: 차트 크기
        """
        # PlotWidget 생성
        pg.setConfigOption('background', color_bg_bk)
        self.plot_widget = pg.PlotWidget(parent=parent)
        self.plot_widget.setFixedSize(size, size)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.showGrid(x=False, y=False)
        self.plot_widget.getAxis('bottom').hide()
        self.plot_widget.getAxis('left').hide()
        self.plot_widget.setXRange(-1.15, 1.15)
        self.plot_widget.setYRange(-1.15, 1.15)

        self._draw_grid_circles()
        self._draw_axes()
        self._draw_crosshair()
        self._draw_avg_data()
        self._draw_curr_data()

    def _draw_grid_circles(self):
        """원형 그리드 라인을 그립니다. (어두운 배경용)"""
        theta = np.linspace(0, 2 * np.pi, 100)

        for radius in [0.2, 0.4, 0.6, 0.8, 1.0]:
            x = radius * np.cos(theta)
            y = radius * np.sin(theta)

            circle_plot = pg.PlotDataItem(
                x=x, y=y,
                pen=pg.mkPen(color=(100, 100, 100), width=0.5)
            )
            self.plot_widget.addItem(circle_plot)

    def _draw_axes(self):
        """8개 축 라인과 레이블을 그립니다. (어두운 배경용)"""
        for i, (angle, label) in enumerate(zip(self.angles, self.axis_labels)):
            # 축 라인 (중심에서 바깥으로)
            x_line = [0, 1.1 * np.cos(angle)]
            y_line = [0, 1.1 * np.sin(angle)]

            axis_plot = pg.PlotDataItem(
                x=x_line, y=y_line,
                pen=pg.mkPen(color=(120, 120, 120), width=1)
            )
            self.plot_widget.addItem(axis_plot)

            # 레이블 텍스트 (어두운 배경용 밝은 색상)
            label_x = 1.2 * np.cos(angle)
            label_y = 1.2 * np.sin(angle)

            text_item = pg.TextItem(
                text=label,
                color=(220, 220, 220),
                anchor=(0.5, 0.5)
            )
            text_item.setPos(label_x, label_y)
            self.plot_widget.addItem(text_item)

    def _draw_crosshair(self):
        self.center_point = pg.ScatterPlotItem(
            x=[0], y=[0],
            brush=pg.mkBrush(color=(200, 200, 200)),
            size=5
        )
        self.plot_widget.addItem(self.center_point)

    def _draw_avg_data(self):
        self.avg_plot = pg.PlotDataItem(
            pen=pg.mkPen(color=(120, 120, 120), width=1),
            brush=pg.mkBrush(color=(150, 150, 150, 60)),
            fillLevel=0
        )
        self.plot_widget.addItem(self.avg_plot)

    def _draw_curr_data(self):
        self.current_plot = pg.PlotDataItem(
            pen=pg.mkPen(color=(0, 200, 0), width=2),
            brush=pg.mkBrush(color=(0, 200, 0, 50)),
            fillLevel=0
        )
        self.plot_widget.addItem(self.current_plot)

    def update_chart(self, current_values: List[float], avg_values: List[float], overall_risk: float = 0.0):
        """차트를 업데이트합니다.
        Args:
            current_values: 현재 8개 지표값 리스트 (0~1 범위)
            avg_values: 평균 8개 지표값 리스트 (0~1 범위)
            overall_risk: 전체 리스크 값 (색상 결정용)
        """
        # 좌표 변환
        avg_x, avg_y = self._polar_to_cartesian(avg_values)
        current_x, current_y = self._polar_to_cartesian(current_values)

        # 평균 다각형 업데이트
        self.avg_plot.setData(x=avg_x, y=avg_y)

        # 현재값 다각형 업데이트
        color = self._get_risk_color(overall_risk)
        self.current_plot.setData(
            x=current_x, y=current_y, pen=pg.mkPen(color=color, width=2),
            brush=pg.mkBrush(color=(color[0], color[1], color[2], 50))
        )

    def _polar_to_cartesian(self, values: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """극좌표를 직교좌표로 변환합니다.
        Args:
            values: 8개 축의 값 리스트 (0~1)
        Returns:
            (x좌표 배열, y좌표 배열) 튜플
        """
        # 닫힌 다각형을 위해 첫 값을 끝에 추가
        values = [max(v, 0.00000001) for v in values]
        values_closed = values + [values[0]]
        angles_closed = np.concatenate([self.angles, [self.angles[0]]])

        x = np.array(values_closed) * np.cos(angles_closed)
        y = np.array(values_closed) * np.sin(angles_closed)

        return x, y

    def _get_risk_color(self, overall_risk: float) -> Tuple[int, int, int]:
        """리스크 값에 따른 색상을 반환합니다.
        Args:
            overall_risk: 전체 리스크 값 (0~1)
        Returns:
            (R, G, B) 색상 튜플
        """
        if overall_risk < 0.3:
            return 0, 200, 0  # 녹색 (안전)
        elif overall_risk < 0.6:
            return 255, 200, 0  # 노란색 (주의)
        else:
            return 255, 50, 50  # 빨간색 (위험)

    def get_widget(self):
        """차트 위젯을 반환합니다.
        Returns:
            PyQtGraph PlotWidget
        """
        return self.plot_widget
