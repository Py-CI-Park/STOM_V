
import pyqtgraph as pg
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QPicture, QPainter
from ui.set_style import color_bg_ct, color_pluss, color_minus


class AreaItem(pg.GraphicsObject):
    def __init__(self, ar, ymin, ymax, xticks, gubun=0):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.draw(ar, ymin, ymax, xticks, gubun)

    def draw(self, ar, ymin, ymax, xticks, gubun):
        def draw_area():
            height = ymax - ymin
            if len(ar[ar > 0]) == 0:
                p.drawRect(QRectF(xticks[-2], ymin, xticks[-2] - xticks[-1], 0))
            else:
                start = 0
                last = len(ar) - 1
                for i, mt in enumerate(ar):
                    if i != last:
                        if mt:
                            if start == 0:
                                start = xticks[i]
                        else:
                            if start != 0:
                                p.drawRect(QRectF(start, ymin, xticks[i] - start, height))
                                start = 0
                    else:
                        if start != 0:
                            p.drawRect(QRectF(start, ymin, xticks[i] - start, height))

        p = QPainter(self.picture)
        p.setBrush(pg.mkBrush(color_bg_ct))
        p.setPen(pg.mkPen(color_bg_ct))

        if gubun == 0:
            draw_area()
        elif gubun == 1:
            ar = ar[:-2]
            draw_area()
        else:
            if ar[-1] == 1:
                p.drawRect(QRectF(xticks[-2], ymin, xticks[-2] - xticks[-1], ymax - ymin))
            else:
                p.drawRect(QRectF(xticks[-2], ymin, xticks[-2] - xticks[-1], 0))

        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, ar, idxs, xticks, gubun=0):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.draw(ar, idxs, xticks, gubun)

    def draw(self, ar, idxs, xticks, gubun):
        def draw_candle(x, c, o, h, low):
            color = color_minus
            if c > o:
                color = color_pluss
            elif c == o and i != 0:
                prec = ar[i - 1, idxs[0]]
                if c > prec:
                    color = color_pluss
            p.setPen(pg.mkPen(color))
            p.setBrush(pg.mkBrush(color))
            if h != low:
                p.drawLine(QPointF(x, h), QPointF(x, low))
                p.drawRect(QRectF(x - w, o, w * 2, c - o))
            else:
                p.drawLine(QPointF(x - w, c), QPointF(x + w * 2, c))

        p = QPainter(self.picture)
        w = min((xticks[1] - xticks[0]) / 3, (xticks[2] - xticks[1]) / 3)
        count = len(ar)
        if gubun == 0:
            for i in range(count):
                draw_candle(xticks[i], ar[i, idxs[0]], ar[i, idxs[1]], ar[i, idxs[2]], ar[i, idxs[3]])
        elif gubun == 1:
            for i in range(count-2):
                draw_candle(xticks[i], ar[i, idxs[0]], ar[i, idxs[1]], ar[i, idxs[2]], ar[i, idxs[3]])
        else:
            for i in (-2, -1):
                draw_candle(xticks[i], ar[i, idxs[0]], ar[i, idxs[1]], ar[i, idxs[2]], ar[i, idxs[3]])
        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class VolumeBarItem(pg.GraphicsObject):
    def __init__(self, ar, idxs, xticks, gubun=0):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.draw(ar, idxs, xticks, gubun)

    def draw(self, ar, idxs, xticks, gubun):
        def draw_bar(x, c, o, m):
            color = color_minus
            if c > o:
                color = color_pluss
            elif c == o and i != 0:
                prec = ar[i - 1, idxs[0]]
                if c > prec:
                    color = color_pluss
            p.setPen(pg.mkPen(color))
            p.setBrush(pg.mkBrush(color))
            p.drawRect(QRectF(x - w, 0, w * 2, m))

        p = QPainter(self.picture)
        w = min((xticks[1] - xticks[0]) / 3, (xticks[2] - xticks[1]) / 3)
        count = len(ar)
        if gubun == 0:
            for i in range(count):
                draw_bar(xticks[i], ar[i, idxs[0]], ar[i, idxs[1]], ar[i, idxs[2]])
        elif gubun == 1:
            for i in range(count-1):
                draw_bar(xticks[i], ar[i, idxs[0]], ar[i, idxs[1]], ar[i, idxs[2]])
        else:
            i = count-1
            draw_bar(xticks[-1], ar[-1, idxs[0]], ar[-1, idxs[1]], ar[-1, idxs[2]])
        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())
