import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl


class BactPlot3D:
    def __init__(self, arry):
        app = pg.mkQApp()
        self.arry = arry
        self.Start()
        app.exec()

    def Start(self):
        dsize = len(self.arry[0, :])
        tsize = len(self.arry)

        w = gl.GLViewWidget()
        w.setWindowTitle('최적화 3D 그래프')
        w.setCameraPosition(distance=250)
        w.show()

        gx = gl.GLGridItem()
        gx.setSize(tsize, dsize, dsize)
        gx.rotate(90, 1, 0, 0)
        gx.translate(0, -int(dsize / 2), 0)
        w.addItem(gx)

        gy = gl.GLGridItem()
        gy.setSize(tsize, dsize, dsize)
        gy.translate(0, 0, -int(dsize / 2))
        w.addItem(gy)

        gz = gl.GLGridItem()
        gz.rotate(90, 0, 1, 0)
        gz.setSize(dsize, dsize, dsize)
        gz.translate(-int(tsize / 2), 0, 0)
        w.addItem(gz)

        y = []
        x = []
        z = []
        coeff = self.arry.max() / dsize
        for i in range(tsize):
            x.append(np.array(list(range(0, dsize, 1))) - int(dsize / 2))
            y.append(self.arry[i, :] / coeff - int(dsize / 2))
            z.append(np.zeros(dsize) + i - int(tsize / 2))

        for i in range(tsize):
            pts = np.column_stack([z[i], x[i], y[i]])
            plt = gl.GLLinePlotItem(pos=pts, color=pg.mkColor((i, 1000)), width=2, antialias=True)
            w.addItem(plt)


if __name__ == '__main__':
    ar = np.r_[[np.sort(np.random.rand(130))], [np.sort(np.random.rand(130))]]
    for _ in range(600):
        ar = np.r_[ar, [np.sort(np.random.rand(130))]]
    BactPlot3D(ar)
