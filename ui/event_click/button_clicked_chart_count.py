
import pyqtgraph as pg
from ui.etcetera.etc import chart_clear
from ui.create_widget.set_style import style_bc_bt, color_bg_bk


def chart_count_change(ui):
    """차트 개수를 변경합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    chart_clear(ui)
    ui.ctpg = {}
    ui.ctpg_cvb = {}
    if ui.ct_pushButtonnn_05.text() == 'CHART I':
        ui.ctpg_vboxLayout.removeWidget(ui.ctpg_layout)
        ui.dialog_chart.setFixedWidth(2088)
        ui.ct_groupBoxxxxx_02.setFixedWidth(2078)
        ui.ct_dateEdittttt_02.setGeometry(2088, 15, 120, 30)
        ui.ct_tableWidgett_01.setGeometry(2088, 55, 120, 1310 if not ui.dict_set['저해상도'] else 950)
        ui.ct_pushButtonnn_05.setText('CHART II')
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)
        pg.setConfigOption('background', color_bg_bk)
        ui.ctpg_layout = pg.GraphicsLayoutWidget()
        if not ui.dict_set['타임프레임']:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=3)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0, colspan=3)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
            ui.ctpg[6], ui.ctpg_cvb[6] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 2)
            ui.ctpg[7], ui.ctpg_cvb[7] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 2)
        else:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=3)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[6], ui.ctpg_cvb[6] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
            ui.ctpg[7], ui.ctpg_cvb[7] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 2)
            ui.ctpg[8], ui.ctpg_cvb[8] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 2)
            ui.ctpg[9], ui.ctpg_cvb[9] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 2)
        ui.ctpg_vboxLayout.addWidget(ui.ctpg_layout)
    elif ui.ct_pushButtonnn_05.text() == 'CHART II':
        ui.ctpg_vboxLayout.removeWidget(ui.ctpg_layout)
        ui.dialog_chart.setFixedWidth(2773)
        ui.ct_groupBoxxxxx_02.setFixedWidth(2763)
        ui.ct_dateEdittttt_02.setGeometry(2773, 15, 120, 30)
        ui.ct_tableWidgett_01.setGeometry(2773, 55, 120, 1310 if not ui.dict_set['저해상도'] else 950)
        ui.ct_pushButtonnn_05.setText('CHART III')
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)
        pg.setConfigOption('background', color_bg_bk)
        ui.ctpg_layout = pg.GraphicsLayoutWidget()
        if not ui.dict_set['타임프레임']:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=4)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0, colspan=4)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
            ui.ctpg[6], ui.ctpg_cvb[6] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 2)
            ui.ctpg[7], ui.ctpg_cvb[7] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 2)
            ui.ctpg[8], ui.ctpg_cvb[8] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 3)
            ui.ctpg[9], ui.ctpg_cvb[9] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 3)
        else:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=4)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[6], ui.ctpg_cvb[6] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
            ui.ctpg[7], ui.ctpg_cvb[7] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 2)
            ui.ctpg[8], ui.ctpg_cvb[8] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 2)
            ui.ctpg[9], ui.ctpg_cvb[9] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 2)
            ui.ctpg[10], ui.ctpg_cvb[10] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 3)
            ui.ctpg[11], ui.ctpg_cvb[11] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 3)
            ui.ctpg[12], ui.ctpg_cvb[12] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 3)
        ui.ctpg_vboxLayout.addWidget(ui.ctpg_layout)
    elif ui.ct_pushButtonnn_05.text() == 'CHART III':
        ui.ctpg_vboxLayout.removeWidget(ui.ctpg_layout)
        ui.dialog_chart.setFixedWidth(1403)
        ui.ct_groupBoxxxxx_02.setFixedWidth(1393)
        ui.ct_dateEdittttt_02.setGeometry(1403, 15, 120, 30)
        ui.ct_tableWidgett_01.setGeometry(1403, 55, 120, 1310 if not ui.dict_set['저해상도'] else 950)
        ui.ct_pushButtonnn_05.setText('CHART I')
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)
        pg.setConfigOption('background', color_bg_bk)
        ui.ctpg_layout = pg.GraphicsLayoutWidget()
        if not ui.dict_set['타임프레임']:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=2)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0, colspan=2)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
        else:
            ui.ctpg[0], ui.ctpg_cvb[0] = ui.wc.setaddPlot(ui.ctpg_layout, 0, 0, colspan=2)
            ui.ctpg[1], ui.ctpg_cvb[1] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 0)
            ui.ctpg[2], ui.ctpg_cvb[2] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 0)
            ui.ctpg[3], ui.ctpg_cvb[3] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 0)
            ui.ctpg[4], ui.ctpg_cvb[4] = ui.wc.setaddPlot(ui.ctpg_layout, 1, 1)
            ui.ctpg[5], ui.ctpg_cvb[5] = ui.wc.setaddPlot(ui.ctpg_layout, 2, 1)
            ui.ctpg[6], ui.ctpg_cvb[6] = ui.wc.setaddPlot(ui.ctpg_layout, 3, 1)
        ui.ctpg_vboxLayout.addWidget(ui.ctpg_layout)

    qGraphicsGridLayout = ui.ctpg_layout.ci.layout
    qGraphicsGridLayout.setRowStretchFactor(0, 3)
    qGraphicsGridLayout.setRowStretchFactor(1, 2)
    qGraphicsGridLayout.setRowStretchFactor(2, 2)
    qGraphicsGridLayout.setRowStretchFactor(3, 2)
