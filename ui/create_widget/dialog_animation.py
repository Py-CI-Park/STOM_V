
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve


class AnimatedDialog(QDialog):
    """페이드인/페이드아웃 애니메이션이 적용된 다이얼로그 클래스"""

    def __init__(self, parent=None):
        """애니메이션 다이얼로그를 초기화합니다.
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.fade_animation = None
        self.animation_duration = 300
        self.is_fading = False
        self._animation_setup_done = False

    def showEvent(self, event):
        """다이얼로그 표시 시 페이드인 애니메이션 실행"""
        super().showEvent(event)
        if not self._animation_setup_done:
            self.fade_in()
            self._animation_setup_done = True

    def fade_in(self):
        """페이드인 애니메이션"""
        if self.is_fading:
            return

        self.is_fading = True
        self.setWindowOpacity(0.0)

        if self.fade_animation:
            self.fade_animation.stop()
            del self.fade_animation

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(self.animation_duration)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_animation.finished.connect(self._on_fade_in_finished)
        self.fade_animation.start()

    def fade_out(self, callback=None):
        """페이드아웃 애니메이션"""
        if self.is_fading:
            return

        self.is_fading = True

        if self.fade_animation:
            self.fade_animation.stop()
            del self.fade_animation

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(self.animation_duration)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InCubic)

        if callback:
            self.fade_animation.finished.connect(callback)
        else:
            self.fade_animation.finished.connect(self._on_fade_out_finished)

        self.fade_animation.start()

    def _on_fade_out_finished(self):
        """페이드아웃 완료 처리"""
        self.is_fading = False
        if self.fade_animation:
            del self.fade_animation
            self.fade_animation = None
        self.hide()
        self._animation_setup_done = False

    def _on_fade_in_finished(self):
        """페이드인 완료 처리"""
        self.is_fading = False
        if self.fade_animation:
            del self.fade_animation
            self.fade_animation = None

    def close(self):
        """닫기 시 페이드아웃 애니메이션 후 실제 닫기"""
        if not self.is_fading:
            self.fade_out(super().close)
        else:
            super().close()


class DialogAnimator:
    """다이얼로그 애니메이션 관리 클래스"""
    _animated_dialogs = set()

    @staticmethod
    def setup_dialog_animation(dialog, duration=200):
        """다이얼로그에 애니메이션 설정"""
        if id(dialog) in DialogAnimator._animated_dialogs:
            dialog._animation_setup_done = False
            dialog.is_fading = False
            if hasattr(dialog, 'fade_animation'):
                dialog.fade_animation = None

        def animated_show_event(event):
            dialog.original_show_event(event)
            if not dialog._animation_setup_done:
                DialogAnimator._fade_in(dialog)
                dialog._animation_setup_done = True

        def animated_close():
            if not dialog.is_fading:
                DialogAnimator._fade_out(dialog, dialog.original_close)
            else:
                dialog.original_close()

        def animated_hide():
            dialog._animation_setup_done = False
            if hasattr(dialog, 'original_hide'):
                dialog.original_hide()
            else:
                dialog.hide()

        DialogAnimator._animated_dialogs.add(id(dialog))

        if not isinstance(dialog, AnimatedDialog):
            dialog.fade_animation = None
            dialog.animation_duration = duration
            dialog.is_fading = False
            dialog._animation_setup_done = False

            dialog.fade_in = lambda: DialogAnimator._fade_in(dialog)
            dialog.fade_out = lambda callback=None: DialogAnimator._fade_out(dialog, callback)

            if not hasattr(dialog, 'original_show_event'):
                dialog.original_show_event = dialog.showEvent
                dialog.showEvent = animated_show_event

            if hasattr(dialog, 'hide') and not hasattr(dialog, 'original_hide'):
                dialog.original_hide = dialog.hide
                dialog.hide = animated_hide

            if not hasattr(dialog, 'original_close'):
                dialog.original_close = dialog.close
                dialog.close = animated_close

    @staticmethod
    def _fade_in(dialog):
        """페이드인 애니메이션 실행"""
        if dialog.is_fading:
            return

        dialog.is_fading = True
        dialog.setWindowOpacity(0.0)

        if hasattr(dialog, 'fade_animation') and dialog.fade_animation:
            dialog.fade_animation.stop()
            del dialog.fade_animation

        dialog.fade_animation = QPropertyAnimation(dialog, b"windowOpacity")
        dialog.fade_animation.setDuration(dialog.animation_duration)
        dialog.fade_animation.setStartValue(0.0)
        dialog.fade_animation.setEndValue(1.0)
        dialog.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        dialog.fade_animation.finished.connect(lambda: DialogAnimator._cleanup_animation(dialog))
        dialog.fade_animation.start()

    @staticmethod
    def _fade_out(dialog, callback=None):
        """페이드아웃 애니메이션 실행"""
        if dialog.is_fading:
            return

        dialog.is_fading = True

        if hasattr(dialog, 'fade_animation') and dialog.fade_animation:
            dialog.fade_animation.stop()
            del dialog.fade_animation

        dialog.fade_animation = QPropertyAnimation(dialog, b"windowOpacity")
        dialog.fade_animation.setDuration(dialog.animation_duration)
        dialog.fade_animation.setStartValue(1.0)
        dialog.fade_animation.setEndValue(0.0)
        dialog.fade_animation.setEasingCurve(QEasingCurve.InCubic)

        if callback:
            dialog.fade_animation.finished.connect(lambda: DialogAnimator._execute_callback(dialog, callback))
        else:
            dialog.fade_animation.finished.connect(lambda: DialogAnimator._on_fade_out_finished(dialog))

        dialog.fade_animation.start()

    @staticmethod
    def _on_fade_out_finished(dialog):
        """페이드아웃 완료 처리"""
        DialogAnimator._cleanup_animation(dialog)
        dialog.hide()
        dialog._animation_setup_done = False
        if id(dialog) in DialogAnimator._animated_dialogs:
            DialogAnimator._animated_dialogs.remove(id(dialog))

    @staticmethod
    def _cleanup_animation(dialog):
        """애니메이션 정리"""
        dialog.is_fading = False
        if hasattr(dialog, 'fade_animation') and dialog.fade_animation:
            del dialog.fade_animation
            dialog.fade_animation = None

    @staticmethod
    def _execute_callback(dialog, callback):
        """콜백 실행 및 정리"""
        DialogAnimator._cleanup_animation(dialog)
        if callback:
            callback()
