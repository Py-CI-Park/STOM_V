
from utility.setting_base import ui_num
from utility.static import error_decorator


class DrawTremap:
    def __init__(self, ui):
        self.ui      = ui
        self.tm_ax1  = None
        self.tm_ax2  = None
        self.df_tm1  = None
        self.df_tm2  = None
        self.tm_cl1  = None
        self.tm_cl2  = None
        self.tm_dt   = False
        self.tm_mc1  = 0
        self.tm_mc2  = 0

    @error_decorator
    def draw_treemap(self, data):
        import squarify

        if not self.ui.dialog_tree.isVisible():
            self.ui.webcQ.put(('트리맵중단', ''))
            return

        gubun, df1, df2, cl1, cl2 = data
        if gubun == ui_num['트리맵'] and self.tm_dt:
            return

        def mouse_press(event):
            if event.inaxes == self.tm_ax1 and self.df_tm1 is not None:
                if event.button == 1 and event.button != self.tm_mc1:
                    self.tm_mc1 = 1
                    df_ = self.df_tm1[(self.df_tm1['x'] < event.xdata) & (event.xdata < self.df_tm1['x2']) &
                                      (self.df_tm1['y'] < event.ydata) & (event.ydata < self.df_tm1['y2'])]
                    if len(df_) == 1:
                        self.tm_dt = True
                        url = df_['url'].iloc[0]
                        self.ui.webcQ.put(('트리맵1', url))
                elif event.button == 3 and event.button != self.tm_mc1:
                    self.tm_mc1 = 3
                    self.tm_dt = False
                    self.tm_ax1.clear()
                    self.tm_ax1.axis('off')
                    squarify.plot(sizes=self.df_tm1['등락율'], label=self.df_tm1['업종명'], alpha=.9,
                                  value=self.df_tm1['등락율%'], color=self.tm_cl1, ax=self.tm_ax1,
                                  bar_kwargs=dict(linewidth=1, edgecolor='#000000'))
                    self.ui.canvas.figure.tight_layout()
                    self.ui.canvas.mpl_connect('button_press_event', mouse_press)
                    self.ui.canvas.draw()
            elif event.inaxes == self.tm_ax2 and self.df_tm2 is not None:
                if event.button == 1 and event.button != self.tm_mc2:
                    self.tm_mc2 = 1
                    df_ = self.df_tm2[(self.df_tm2['x'] < event.xdata) & (event.xdata < self.df_tm2['x2']) &
                                      (self.df_tm2['y'] < event.ydata) & (event.ydata < self.df_tm2['y2'])]
                    if len(df_) == 1:
                        self.tm_dt = True
                        url = df_['url'].iloc[0]
                        self.ui.webcQ.put(('트리맵2', url))
                elif event.button == 3 and event.button != self.tm_mc2:
                    self.tm_mc2 = 3
                    self.tm_dt = False
                    self.tm_ax2.clear()
                    self.tm_ax2.axis('off')
                    squarify.plot(sizes=self.df_tm2['등락율'], label=self.df_tm2['테마명'], alpha=.9,
                                  value=self.df_tm2['등락율%'], color=self.tm_cl2, ax=self.tm_ax2,
                                  bar_kwargs=dict(linewidth=1, edgecolor='#000000'))
                    self.ui.canvas.figure.tight_layout()
                    self.ui.canvas.mpl_connect('button_press_event', mouse_press)
                    self.ui.canvas.draw()

        if self.ui.canvas is None:
            from matplotlib import pyplot as plt, font_manager
            from PyQt5.QtWidgets import QVBoxLayout
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            plt.rcParams['figure.max_open_warning'] = 0
            plt.rcParams['font.family'] = font_manager.FontProperties(fname='C:/Windows/Fonts/malgun.ttf').get_name()
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['path.simplify'] = True
            plt.rcParams['path.snap'] = True
            plt.rcParams['figure.autolayout'] = True
            plt.rcParams['figure.constrained_layout.use'] = True
            fig = plt.figure('업종별 테마별 등락율', figsize=(15, 13.3))
            fig.set_facecolor('black')
            self.ui.canvas = FigureCanvas(fig)
            tree_layout = QVBoxLayout(self.ui.dialog_tree)
            tree_layout.setContentsMargins(0, 0, 0, 0)
            tree_layout.addWidget(self.ui.canvas)

        if gubun == ui_num['트리맵']:
            self.df_tm1 = df1
            self.df_tm2 = df2
            self.tm_cl1 = cl1
            self.tm_cl2 = cl2

            normed = squarify.normalize_sizes(self.df_tm1['등락율'], 100, 100)
            rects  = squarify.squarify(normed, 0, 0, 100, 100)
            self.df_tm1['x']  = [rect["x"] for rect in rects]
            self.df_tm1['y']  = [rect["y"] for rect in rects]
            self.df_tm1['dx'] = [rect["dx"] for rect in rects]
            self.df_tm1['dy'] = [rect["dy"] for rect in rects]
            self.df_tm1['x2'] = self.df_tm1['x'] + self.df_tm1['dx']
            self.df_tm1['y2'] = self.df_tm1['y'] + self.df_tm1['dy']

            normed = squarify.normalize_sizes(self.df_tm2['등락율'], 100, 100)
            rects  = squarify.squarify(normed, 0, 0, 100, 100)
            self.df_tm2['x']  = [rect["x"] for rect in rects]
            self.df_tm2['y']  = [rect["y"] for rect in rects]
            self.df_tm2['dx'] = [rect["dx"] for rect in rects]
            self.df_tm2['dy'] = [rect["dy"] for rect in rects]
            self.df_tm2['x2'] = self.df_tm2['x'] + self.df_tm2['dx']
            self.df_tm2['y2'] = self.df_tm2['y'] + self.df_tm2['dy']

            if self.tm_ax1 is None:
                self.tm_ax1 = self.ui.canvas.figure.add_subplot(211)
                self.tm_ax2 = self.ui.canvas.figure.add_subplot(212)
            else:
                self.tm_ax1.clear()
                self.tm_ax2.clear()
            self.tm_ax1.axis('off')
            self.tm_ax2.axis('off')
            squarify.plot(sizes=self.df_tm1['등락율'], label=self.df_tm1['업종명'], alpha=.9, value=self.df_tm1['등락율%'],
                          color=self.tm_cl1, ax=self.tm_ax1, bar_kwargs=dict(linewidth=1, edgecolor='#000000'))
            squarify.plot(sizes=self.df_tm2['등락율'], label=self.df_tm2['테마명'], alpha=.9, value=self.df_tm2['등락율%'],
                          color=self.tm_cl2, ax=self.tm_ax2, bar_kwargs=dict(linewidth=1, edgecolor='#000000'))
        elif gubun == ui_num['트리맵1']:
            self.tm_ax1.clear()
            self.tm_ax1.axis('off')
            squarify.plot(sizes=df1['등락율'], label=df1['종목명'], alpha=.9, value=df1['등락율%'],
                          color=cl1, ax=self.tm_ax1, bar_kwargs=dict(linewidth=1, edgecolor='#000000'))
        elif gubun == ui_num['트리맵2']:
            self.tm_ax2.clear()
            self.tm_ax2.axis('off')
            squarify.plot(sizes=df2['등락율'], label=df2['종목명'], alpha=.9, value=df2['등락율%'],
                          color=cl2, ax=self.tm_ax2, bar_kwargs=dict(linewidth=1, edgecolor='#000000'))

        self.ui.canvas.figure.tight_layout()
        self.ui.canvas.mpl_connect('button_press_event', mouse_press)
        self.ui.canvas.draw()
