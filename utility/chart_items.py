import pyqtgraph as pg
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QPicture, QPainter
from ui.set_style import color_bg_dk, color_pluss, color_minus


class ChuseItem(pg.GraphicsObject):
    def __init__(self, ar, ymin, ymax, xticks):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.Chuse(ar, ymin, ymax, xticks)

    def Chuse(self, ar, ymin, ymax, xticks):
        p = QPainter(self.picture)
        height = ymax - ymin
        start = 0
        p.setBrush(pg.mkBrush(color_bg_dk))
        p.setPen(pg.mkPen(color_bg_dk))
        last = len(ar) - 1
        for i, mt in enumerate(ar):
            if i != last:
                if mt == 1 and start == 0:
                    start = xticks[i]
                elif mt == 0 and start != 0:
                    p.drawRect(QRectF(start, ymin, xticks[i] - start, height))
                    start = 0
            elif start != 0:
                p.drawRect(QRectF(start, ymin, xticks[-1] - start, height))
        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, ar, num, xticks, gubun=0):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.CandleSticks(ar, num, xticks, gubun)

    def CandleSticks(self, ar, num, xticks, gubun):
        p = QPainter(self.picture)
        w = (xticks[1] - xticks[0]) / 3
        count = len(ar)
        if gubun == 0:
            for i in range(count):
                c   = ar[i, num[0]]
                o   = ar[i, num[1]]
                h   = ar[i, num[2]]
                low = ar[i, num[3]]
                x   = xticks[i]
                color = color_minus
                if c > o:
                    color = color_pluss
                elif c == o and i != 0:
                    prec = ar[i-1, num[0]]
                    if c > prec:
                        color = color_pluss
                p.setPen(pg.mkPen(color))
                p.setBrush(pg.mkBrush(color))
                if h != low:
                    p.drawLine(QPointF(x, h), QPointF(x, low))
                    p.drawRect(QRectF(x - w, o, w * 2, c - o))
                else:
                    p.drawLine(QPointF(x - w, c), QPointF(x + w * 2, c))
        elif gubun == 1:
            for i in range(count):
                if i < count - 2:
                    c   = ar[i, num[0]]
                    o   = ar[i, num[1]]
                    h   = ar[i, num[2]]
                    low = ar[i, num[3]]
                    x   = xticks[i]
                    color = color_minus
                    if c > o:
                        color = color_pluss
                    elif c == o and i != 0:
                        prec = ar[i-1, num[0]]
                        if c > prec:
                            color = color_pluss
                    p.setPen(pg.mkPen(color))
                    p.setBrush(pg.mkBrush(color))
                    if h != low:
                        p.drawLine(QPointF(x, h), QPointF(x, low))
                        p.drawRect(QRectF(x - w, o, w * 2, c - o))
                    else:
                        p.drawLine(QPointF(x - w, c), QPointF(x + w * 2, c))
        else:
            for i in (-2, -1):
                c   = ar[i, num[0]]
                o   = ar[i, num[1]]
                h   = ar[i, num[2]]
                low = ar[i, num[3]]
                x   = xticks[i]
                color = color_minus
                if c > o:
                    color = color_pluss
                elif c == o:
                    prec = ar[i-1, num[0]]
                    if c > prec:
                        color = color_pluss
                p.setPen(pg.mkPen(color))
                p.setBrush(pg.mkBrush(color))
                if h != low:
                    p.drawLine(QPointF(x, h), QPointF(x, low))
                    p.drawRect(QRectF(x - w, o, w * 2, c - o))
                else:
                    p.drawLine(QPointF(x - w, c), QPointF(x + w * 2, c))
        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class VolumeBarsItem(pg.GraphicsObject):
    def __init__(self, ar, num, xticks, gubun=0):
        pg.GraphicsObject.__init__(self)
        self.picture = QPicture()
        self.MoneyBars(ar, num, xticks, gubun)

    def MoneyBars(self, ar, num, xticks, gubun):
        p = QPainter(self.picture)
        w = (xticks[1] - xticks[0]) / 3
        count = len(ar)
        if gubun == 0:
            for i in range(count):
                c = ar[i, num[0]]
                o = ar[i, num[1]]
                m = ar[i, num[2]]
                x = xticks[i]
                color = color_minus
                if c > o:
                    color = color_pluss
                elif c == o and i != 0:
                    prec = ar[i-1, num[0]]
                    if c > prec:
                        color = color_pluss
                p.setPen(pg.mkPen(color))
                p.setBrush(pg.mkBrush(color))
                p.drawRect(QRectF(x - w, 0, w * 2, m))
        elif gubun == 1:
            for i in range(count):
                if i < count - 1:
                    c = ar[i, num[0]]
                    o = ar[i, num[1]]
                    m = ar[i, num[2]]
                    x = xticks[i]
                    color = color_minus
                    if c > o:
                        color = color_pluss
                    elif c == o and i != 0:
                        prec = ar[i-1, num[0]]
                        if c > prec:
                            color = color_pluss
                    p.setPen(pg.mkPen(color))
                    p.setBrush(pg.mkBrush(color))
                    p.drawRect(QRectF(x - w, 0, w * 2, m))
        else:
            c = ar[-1, num[0]]
            o = ar[-1, num[1]]
            m = ar[-1, num[2]]
            x = xticks[-1]
            color = color_minus
            if c > o:
                color = color_pluss
            elif c == o:
                prec = ar[-2, num[0]]
                if c > prec:
                    color = color_pluss
            p.setPen(pg.mkPen(color))
            p.setBrush(pg.mkBrush(color))
            p.drawRect(QRectF(x - w, 0, w * 2, m))
        p.end()

    def paint(self, p, *args):
        if args is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())
