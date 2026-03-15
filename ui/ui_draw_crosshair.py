
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from utility.static import from_timestamp
from ui.ui_draw_label_text import get_label_text
from ui.set_style import color_cs_hr, color_fg_bt, color_bg_bt, color_bg_ld, qfont12


_np = None


def get_np():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


class CrossHair:
    def __init__(self, ui):
        self.ui = ui

    def crosshair(self, real, gubun, is_min, main_pg1, sub_pg1, sub_pg2, sub_pg3, sub_pg4, sub_pg5, sub_pg6=None, sub_pg7=None,
                  sub_pg8=None, sub_pg9=None, sub_pg10=None, sub_pg11=None, sub_pg12=None):
        def setInfiniteLine(angle=None):
            if angle is None:
                vhline = pg.InfiniteLine()
            else:
                vhline = pg.InfiniteLine(angle=angle)
            vhline.setPen(pg.mkPen(color_cs_hr, width=0.5, style=Qt.DashLine))
            return vhline

        hLine1  = setInfiniteLine(angle=0)
        hLine2  = setInfiniteLine(angle=0)
        hLine3  = setInfiniteLine(angle=0)
        hLine4  = setInfiniteLine(angle=0)
        hLine5  = setInfiniteLine(angle=0)
        hLine6  = setInfiniteLine(angle=0)
        hLine7  = setInfiniteLine(angle=0)
        hLine8  = setInfiniteLine(angle=0)
        hLine9  = setInfiniteLine(angle=0)
        hLine10 = setInfiniteLine(angle=0)
        hLine11 = setInfiniteLine(angle=0)
        hLine12 = setInfiniteLine(angle=0)
        hLine13 = setInfiniteLine(angle=0)

        vLine1  = setInfiniteLine()
        vLine2  = setInfiniteLine()
        vLine3  = setInfiniteLine()
        vLine4  = setInfiniteLine()
        vLine5  = setInfiniteLine()
        vLine6  = setInfiniteLine()
        vLine7  = setInfiniteLine()
        vLine8  = setInfiniteLine()
        vLine9  = setInfiniteLine()
        vLine10 = setInfiniteLine()
        vLine11 = setInfiniteLine()
        vLine12 = setInfiniteLine()
        vLine13 = setInfiniteLine()

        pg_list = [main_pg1, sub_pg1, sub_pg2, sub_pg3, sub_pg4, sub_pg5]
        hLines  = [hLine1, hLine2, hLine3, hLine4, hLine5, hLine6]
        vLines  = [vLine1, vLine2, vLine3, vLine4, vLine5, vLine6]
        count_  = 6
        if sub_pg6 is not None:
            pg_list += [sub_pg6]
            hLines  += [hLine7]
            vLines  += [vLine7]
            count_  += 1
        if sub_pg7 is not None:
            pg_list += [sub_pg7]
            hLines  += [hLine8]
            vLines  += [vLine8]
            count_  += 1
        if sub_pg9 is not None:
            pg_list += [sub_pg8, sub_pg9]
            hLines  += [hLine9, hLine10]
            vLines  += [vLine9, vLine10]
            count_  += 2
        if sub_pg12 is not None:
            pg_list += [sub_pg10, sub_pg11, sub_pg12]
            hLines  += [hLine11, hLine12, hLine13]
            vLines  += [vLine11, vLine12, vLine13]
            count_  += 3

        self.ui.ctpg_labels = []

        for k in range(count_):
            kxmin = self.ui.ctpg_cvb[k].state['viewRange'][0][0]
            kymin = self.ui.ctpg_cvb[k].state['viewRange'][1][0]
            label = pg.TextItem(anchor=(0, 1), color=color_fg_bt, border=color_bg_bt, fill=color_bg_ld)
            label.setFont(qfont12)
            label.setPos(kxmin, kymin)
            self.ui.ctpg_labels.append(label)
            if k == len(self.ui.ctpg_factors) - 1:
                break

        try:
            main_pg1.addItem(vLine1, ignoreBounds=True)
            main_pg1.addItem(hLine1, ignoreBounds=True)
            main_pg1.addItem(self.ui.ctpg_labels[0])
            sub_pg1.addItem(vLine2, ignoreBounds=True)
            sub_pg1.addItem(hLine2, ignoreBounds=True)
            sub_pg1.addItem(self.ui.ctpg_labels[1])
            sub_pg2.addItem(vLine3, ignoreBounds=True)
            sub_pg2.addItem(hLine3, ignoreBounds=True)
            sub_pg2.addItem(self.ui.ctpg_labels[2])
            sub_pg3.addItem(vLine4, ignoreBounds=True)
            sub_pg3.addItem(hLine4, ignoreBounds=True)
            sub_pg3.addItem(self.ui.ctpg_labels[3])
            sub_pg4.addItem(vLine5, ignoreBounds=True)
            sub_pg4.addItem(hLine5, ignoreBounds=True)
            sub_pg4.addItem(self.ui.ctpg_labels[4])
            sub_pg5.addItem(vLine6, ignoreBounds=True)
            sub_pg5.addItem(hLine6, ignoreBounds=True)
            sub_pg5.addItem(self.ui.ctpg_labels[5])
            if sub_pg6 is not None:
                sub_pg6.addItem(vLine7, ignoreBounds=True)
                sub_pg6.addItem(hLine7, ignoreBounds=True)
                sub_pg6.addItem(self.ui.ctpg_labels[6])
            if sub_pg7 is not None:
                sub_pg7.addItem(vLine8, ignoreBounds=True)
                sub_pg7.addItem(hLine8, ignoreBounds=True)
                sub_pg7.addItem(self.ui.ctpg_labels[7])
            if sub_pg9 is not None:
                sub_pg8.addItem(vLine9, ignoreBounds=True)
                sub_pg8.addItem(hLine9, ignoreBounds=True)
                sub_pg8.addItem(self.ui.ctpg_labels[8])
                sub_pg9.addItem(vLine10, ignoreBounds=True)
                sub_pg9.addItem(hLine10, ignoreBounds=True)
                sub_pg9.addItem(self.ui.ctpg_labels[9])
            if sub_pg12 is not None:
                sub_pg10.addItem(vLine11, ignoreBounds=True)
                sub_pg10.addItem(hLine11, ignoreBounds=True)
                sub_pg10.addItem(self.ui.ctpg_labels[10])
                sub_pg11.addItem(vLine12, ignoreBounds=True)
                sub_pg11.addItem(hLine12, ignoreBounds=True)
                sub_pg11.addItem(self.ui.ctpg_labels[11])
                sub_pg12.addItem(vLine13, ignoreBounds=True)
                sub_pg12.addItem(hLine13, ignoreBounds=True)
                sub_pg12.addItem(self.ui.ctpg_labels[12])
        except:
            pass

        def mouseMoved(evt):
            pos = evt[0]
            index = -1
            if main_pg1.sceneBoundingRect().contains(pos):       index =  0
            elif sub_pg1.sceneBoundingRect().contains(pos):      index =  1
            elif sub_pg2.sceneBoundingRect().contains(pos):      index =  2
            elif sub_pg3.sceneBoundingRect().contains(pos):      index =  3
            elif sub_pg4.sceneBoundingRect().contains(pos):      index =  4
            elif sub_pg5.sceneBoundingRect().contains(pos):      index =  5
            if sub_pg6 is not None:
                if sub_pg6.sceneBoundingRect().contains(pos):    index =  6
            if sub_pg7 is not None:
                if sub_pg7.sceneBoundingRect().contains(pos):    index =  7
            if sub_pg9 is not None:
                if sub_pg8.sceneBoundingRect().contains(pos):    index =  8
                elif sub_pg9.sceneBoundingRect().contains(pos):  index =  9
            if sub_pg12 is not None:
                if sub_pg10.sceneBoundingRect().contains(pos):   index = 10
                elif sub_pg11.sceneBoundingRect().contains(pos): index = 11
                elif sub_pg12.sceneBoundingRect().contains(pos): index = 12

            if index != -1:
                try:
                    mousePoint = pg_list[index].getViewBox().mapSceneToView(pos)
                    int_mpx = int(mousePoint.x())
                    if is_min:
                        rest = int_mpx % 60
                        int_mpx -= rest
                        if rest > 30:
                            int_mpx += 60
                    xpoint = self.ui.ctpg_xticks.index(int_mpx)
                    hms_   = from_timestamp(int_mpx).strftime('%H:%M' if is_min else '%H:%M:%S')
                    code   = self.ui.ctpg_name
                    for n, labell in enumerate(self.ui.ctpg_labels):
                        foctor = self.ui.ctpg_factors[n]
                        if index == n:
                            text = f'Y축 {get_np().round(mousePoint.y(), 2):,}\n{get_label_text(self.ui, real, gubun, code, is_min, xpoint, foctor, hms_)}'
                        else:
                            text = get_label_text(self.ui, real, gubun, code, is_min, xpoint, foctor, hms_)
                        labell.setText(text)
                        lxmin, lxmax = self.ui.ctpg_cvb[n].state['viewRange'][0]
                        lymin, lymax = self.ui.ctpg_cvb[n].state['viewRange'][1]
                        if not real:
                            if mousePoint.x() < lxmin + (lxmax - lxmin) * 0.33:
                                if self.ui.ct_checkBoxxxxx_01.isChecked():
                                    labell.setAnchor((1, 1))
                                    labell.setPos(lxmax, lymin)
                                if self.ui.ct_checkBoxxxxx_02.isChecked():
                                    self.ui.ctpg_legend[n].setAnchor((1, 0))
                                    self.ui.ctpg_legend[n].setPos(lxmax, lymax)
                            else:
                                if self.ui.ct_checkBoxxxxx_01.isChecked():
                                    labell.setAnchor((0, 1))
                                    labell.setPos(lxmin, lymin)
                                if self.ui.ct_checkBoxxxxx_02.isChecked():
                                    self.ui.ctpg_legend[n].setAnchor((0, 0))
                                    self.ui.ctpg_legend[n].setPos(lxmin, lymax)
                        if n == len(self.ui.ctpg_factors) - 1:
                            break
                    hLines[index].setPos(mousePoint.y())
                    for vLine in vLines:
                        vLine.setPos(mousePoint.x())
                except:
                    pass

        main_pg1.proxy = pg.SignalProxy(main_pg1.scene().sigMouseMoved, rateLimit=20, slot=mouseMoved)
