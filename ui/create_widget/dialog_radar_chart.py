"""
시장미시구조 레이더 차트 다이얼로그 모듈입니다.
별도의 다이얼로그 창에서 레이더 차트를 표시합니다.
메인UI에서 직접 함수 호출로 데이터를 전달받습니다.
"""
from typing import List
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget
from ui.draw_chart.draw_radar_chart import DrawRadarChart


class MicrostructureRadarDialog(QDialog):
    """시장미시구조 레이더 차트 다이얼로그 클래스입니다.
    별도의 다이얼로그 창에서 레이더 차트를 표시합니다.
    Attributes:
        chart: MicrostructureRadarChart 인스턴스
    """
    def __init__(self, title: str, parent=None, size: int = 550):
        """초기화 메서드입니다.
        Args:
            title: 다이얼로그 제목
            parent: 부모 위젯
            size: 차트 크기 (픽셀)
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(False)  # 모달리스 다이얼로그
        self.resize(size + 5, size + 5)

        # UI 설정
        self._setup_ui(size)

    def _setup_ui(self, size: int):
        """UI를 설정합니다.
        Args:
            size: 차트 크기
        """
        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # 차트 위젯 컨테이너
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        # 차트 생성
        self.chart = DrawRadarChart(size, parent=chart_container)
        chart_layout.addWidget(self.chart.get_widget())

        layout.addWidget(chart_container)
        self.setLayout(layout)

    def update_radar(self, curr_values: List[float], avg_values: List[float], overall_risk: float):
        """차트 데이터를 업데이트합니다.
        Args:
            curr_values: 8개 현재값 리스트 (0~1 범위, 이미 정규화됨)
            avg_values: 8개 평균값 리스트 (0~1 범위)
            overall_risk: 전체 리스크 값 (0~1 범위, 이미 정규화됨)
        """
        if self.chart is None:
            return

        if not curr_values or len(curr_values) != 8 or len(avg_values) != 8:
            return

        self.chart.update_chart(curr_values, avg_values, overall_risk)
