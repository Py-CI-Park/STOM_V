import sys
import ctypes
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication
from utility.timesync import timesync
from ui.ui_mainwindow import MainWindow
from ui.set_style import color_bg_bc, color_fg_bc, color_bg_dk, color_fg_bk, color_fg_hl, color_bg_bk

if __name__ == '__main__':
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 128)
    auto_run = 0
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stock':  auto_run = 1
        elif sys.argv[1] == 'coin': auto_run = 2
    timesync()
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, color_bg_bc)
    palette.setColor(QPalette.Background, color_bg_bc)
    palette.setColor(QPalette.WindowText, color_fg_bc)
    palette.setColor(QPalette.Base, color_bg_bc)
    palette.setColor(QPalette.AlternateBase, color_bg_dk)
    palette.setColor(QPalette.Text, color_fg_bc)
    palette.setColor(QPalette.Button, color_bg_bc)
    palette.setColor(QPalette.ButtonText, color_fg_bc)
    palette.setColor(QPalette.Link, color_fg_bk)
    palette.setColor(QPalette.Highlight, color_fg_hl)
    palette.setColor(QPalette.HighlightedText, color_bg_bk)
    app.setPalette(palette)
    mainwindow = MainWindow(auto_run)
    mainwindow.show()
    app.exec_()
