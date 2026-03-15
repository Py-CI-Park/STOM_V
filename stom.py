
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.ui_splash_screen import StomSplashScreen
from ui.ui_import_hook import ImportProgressHook
from utility.database_check import database_check

if __name__ == '__main__':
    auto_run = 0
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stock':    auto_run = 1
        elif sys.argv[1] == 'coin':   auto_run = 2
        elif sys.argv[1] == 'future': auto_run = 3

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setStyle('fusion')

    splash = StomSplashScreen()
    splash.show()

    completed, error = database_check()
    if not completed:
        QMessageBox.critical(splash, '오류 알림', error)
        sys.exit()

    import_hook = ImportProgressHook(splash)
    import_hook.install()

    from ui.ui_mainwindow import MainWindow
    from ui.set_style import color_bg_bc, color_fg_bc, color_bg_dk, color_fg_bk, color_fg_hl, color_bg_bk

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

    import_hook.uninstall()

    mainwindow = MainWindow(auto_run, splash)
    app.exec_()
