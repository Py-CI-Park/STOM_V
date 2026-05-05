
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QSplashScreen, QApplication, QVBoxLayout, QLabel, QProgressBar, QWidget, QHBoxLayout, \
    QGraphicsDropShadowEffect


class StomSplashScreen(QSplashScreen):
    """STOM 스플래시 스크린 클래스입니다.
    애플리케이션 시작 시 로딩 화면을 표시합니다.
    """
    def __init__(self):
        """스플래시 스크린을 초기화합니다."""
        super().__init__()

        self.setFixedSize(500, 300)
        self.setStyleSheet("""
            QSplashScreen {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0a0a, stop:0.5 #1a1a2e, stop:1 #16213e);
                border: none;
                border-radius: 15px;
            }
        """)

        self.status_label   = None
        self.progress_bar   = None
        self.version_label  = None
        self.fade_out_timer = None
        self.loading_dots   = 0

        self.fade_in_timer = QTimer()
        self.fade_in_timer.timeout.connect(self.update_fade_in)

        self.setup_ui()

    def showEvent(self, event):
        """표시 이벤트를 처리합니다.
        Args:
            event: 이벤트
        """
        super().showEvent(event)
        self.center_on_screen()

        self.setWindowOpacity(0.0)
        self.fade_in_timer.start(30)

    def update_fade_in(self):
        """페이드인 애니메이션을 업데이트합니다."""
        current_opacity = self.windowOpacity()
        if current_opacity < 1.0:
            self.setWindowOpacity(min(current_opacity + 0.1, 1.0))
        else:
            self.fade_in_timer.stop()

    def center_on_screen(self):
        """스크린 중앙에 스플래시 스크린을 배치합니다."""
        # noinspection PyUnresolvedReferences
        screen = QApplication.desktop().screenGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def setup_ui(self):
        """UI를 설정합니다."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)

        logo_container = QHBoxLayout()
        logo_container.setSpacing(15)

        icon_label = QLabel()
        pixmap = QPixmap("ui/_icon/logo.png")
        icon_label.setPixmap(pixmap.scaled(60, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(60, 50)

        try:
            with open("_update.txt", "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                version = first_line.split("V")[1] if "V" in first_line else "2.00"
                version_int = version.split(".")[0] + '.0'
        except Exception:
            version     = "2.00"
            version_int = "2.0"

        title = QLabel(f"STOM {version_int}")
        title.setStyleSheet("""
            QLabel {
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:0.5 #64b5f6, stop:1 #4a90e2);
                font-size: 50px;
                font-weight: 900;
                font-family: 'Segoe UI', 'Malgun Gothic';
                text-transform: uppercase;
                letter-spacing: 2px;
            }
        """)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        logo_container.addStretch()
        logo_container.addWidget(icon_label)
        logo_container.addWidget(title)
        logo_container.addStretch()

        subtitle = QLabel("System Trade Operating Machine")
        subtitle.setStyleSheet("""
            QLabel {
                color: #b0bec5;
                font-size: 14px;
                font-family: 'Segoe UI', 'Malgun Gothic';
                letter-spacing: 3px;
                text-transform: uppercase;
                font-weight: 500;
            }
        """)
        subtitle.setAlignment(Qt.AlignCenter)

        self.version_label = QLabel(f"Version {version}")
        self.version_label.setStyleSheet("""
            QLabel {
                color: #607d8b;
                font-size: 12px;
                font-family: 'Consolas', 'Malgun Gothic';
                background: rgba(255, 255, 255, 0.05);
                padding: 5px 15px;
                border-radius: 12px;
                border: 1px solid rgba(74, 144, 226, 0.3);
            }
        """)
        self.version_label.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("System Initializing")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #eceff1;
                font-size: 16px;
                font-family: 'Segoe UI', 'Malgun Gothic';
                font-weight: 500;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 0.1);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:0.5 #64b5f6, stop:1 #4a90e2);
                border-radius: 5px;
            }
        """)

        main_layout.addStretch()
        main_layout.addLayout(logo_container)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(self.version_label)
        main_layout.addStretch()
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)

        widget = QWidget()
        widget.setLayout(main_layout)
        widget.setGraphicsEffect(shadow)

        final_layout = QVBoxLayout()
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.addWidget(widget)
        self.setLayout(final_layout)

    def show_progress(self, message, progress=None):
        """진행률을 표시합니다.
        Args:
            message: 상태 메시지
            progress: 진행률 값
        """
        self.status_label.setText(message)
        if progress is not None:
            current_value = self.progress_bar.value()
            if progress >= current_value:
                self.progress_bar.setValue(progress)

                if progress > 66 and self.progress_bar.value() > 66:
                    self.progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: none;
                            border-radius: 4px;
                            background-color: rgba(255, 255, 255, 0.1);
                        }
                        QProgressBar::chunk {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4caf50, stop:0.5 #66bb6a, stop:1 #4caf50);
                            border-radius: 4px;
                        }
                    """)
                elif progress > 33 and self.progress_bar.value() > 33:
                    self.progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: none;
                            border-radius: 4px;
                            background-color: rgba(255, 255, 255, 0.1);
                        }
                        QProgressBar::chunk {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #ff9800, stop:0.5 #ffb74d, stop:1 #ff9800);
                            border-radius: 4px;
                        }
                    """)
                elif progress <= 33:
                    self.progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: none;
                            border-radius: 4px;
                            background-color: rgba(255, 255, 255, 0.1);
                        }
                        QProgressBar::chunk {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4a90e2, stop:0.5 #64b5f6, stop:1 #4a90e2);
                            border-radius: 4px;
                        }
                    """)

        QApplication.processEvents()

    def finish_splash(self):
        """스플래시 스크린을 종료합니다."""
        self.fade_in_timer.stop()

        self.status_label.setText("System Ready ✓")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-size: 16px;
                font-family: 'Segoe UI', 'Malgun Gothic';
                font-weight: 600;
            }
        """)
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4caf50, stop:0.5 #66bb6a, stop:1 #4caf50);
                border-radius: 4px;
            }
        """)
        QApplication.processEvents()
        QTimer.singleShot(1000, self.start_fade_out)

    def start_fade_out(self):
        """페이드아웃 애니메이션을 시작합니다."""
        self.fade_out_timer = QTimer()
        self.fade_out_timer.timeout.connect(self.update_fade_out)
        self.fade_out_timer.start(30)

    def update_fade_out(self):
        """페이드아웃 애니메이션을 업데이트합니다."""
        current_opacity = self.windowOpacity()
        if current_opacity > 0.0:
            self.setWindowOpacity(max(current_opacity - 0.05, 0.0))
        else:
            self.fade_out_timer.stop()
            self.close()
