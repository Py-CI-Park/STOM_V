
def group_animation(ui, pushButton, textEdit, pushButton_qrect, textEdit_qrect):
    """그룹 애니메이션을 실행합니다.
    Args:
        ui: UI 클래스 인스턴스
        pushButton: 푸시 버튼
        textEdit: 텍스트 에디터
        pushButton_qrect: 푸시 버튼 지오메트리
        textEdit_qrect: 텍스트 에디터 지오메트리
    """
    from PyQt5.QtCore import QParallelAnimationGroup, QPropertyAnimation, QEasingCurve

    current_geo_btn01 = pushButton.geometry()
    current_geo_tedt1 = textEdit.geometry()

    ui.animation_group3 = QParallelAnimationGroup()

    anim_btn01 = QPropertyAnimation(textEdit, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_tedt1)
    anim_btn01.setEndValue(textEdit_qrect)

    anim_tedt1 = QPropertyAnimation(pushButton, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_btn01)
    anim_tedt1.setEndValue(pushButton_qrect)

    ui.animation_group3.addAnimation(anim_btn01)
    ui.animation_group3.addAnimation(anim_tedt1)

    ui.animation_group3.start()


def sz_button_clicked_01(ui):
    """첫 번째 줌 버튼을 클릭합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import QRect

    if ui.svj_pushButton_01.isVisible():
        if ui.szoo_pushButon_01.text() == '확대(esc)':
            visible = False
            ui.szoo_pushButon_01.setText('축소(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_01,
                ui.ss_textEditttt_01,
                QRect(937, 15, 50, 20),
                QRect(7, 10, 1000, 1347 if ui.extend_window else 740)
            )
        else:
            visible = True
            ui.szoo_pushButon_01.setText('확대(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_01,
                ui.ss_textEditttt_01,
                QRect(937, 15, 50, 20),
                QRect(7, 10, 1000, 740 if ui.extend_window else 463)
            )
        ui.ss_textEditttt_02.setVisible(visible)
        ui.szoo_pushButon_02.setVisible(visible)
    else:
        if ui.szoo_pushButon_01.text() == '확대(esc)':
            visible = False
            ui.szoo_pushButon_01.setText('축소(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_01,
                ui.ss_textEditttt_03,
                QRect(937, 15, 50, 20),
                QRect(7, 10, 1000, 1347 if ui.extend_window else 740)
            )
        else:
            visible = True
            ui.szoo_pushButon_01.setText('확대(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_01,
                ui.ss_textEditttt_03,
                QRect(584, 15, 50, 20),
                QRect(7, 10, 647, 740 if ui.extend_window else 463)
            )
        ui.ss_textEditttt_04.setVisible(visible)
        if ui.sva_pushButton_01.isVisible():
            ui.ss_textEditttt_06.setVisible(visible)
        else:
            ui.ss_textEditttt_05.setVisible(visible)
        ui.szoo_pushButon_02.setVisible(visible)


def sz_button_clicked_02(ui):
    """두 번째 줌 버튼을 클릭합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import QRect

    if ui.svj_pushButton_01.isVisible():
        if ui.szoo_pushButon_02.text() == '확대(esc)':
            visible = False
            ui.szoo_pushButon_02.setText('축소(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_02,
                ui.ss_textEditttt_02,
                QRect(937, 15, 50, 20),
                QRect(7, 10, 1000, 1347 if ui.extend_window else 740)
            )
        else:
            visible = True
            ui.szoo_pushButon_02.setText('확대(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_02,
                ui.ss_textEditttt_02,
                QRect(937, 761 if ui.extend_window else 483, 50, 20),
                QRect(7, 756 if ui.extend_window else 480, 1000, 602 if ui.extend_window else 272)
            )
        ui.ss_textEditttt_01.setVisible(visible)
        ui.szoo_pushButon_01.setVisible(visible)
    else:
        if ui.szoo_pushButon_02.text() == '확대(esc)':
            visible = False
            ui.szoo_pushButon_02.setText('축소(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_02,
                ui.ss_textEditttt_04,
                QRect(937, 15, 50, 20),
                QRect(7, 10, 1000, 1347 if ui.extend_window else 740)
            )
        else:
            visible = True
            ui.szoo_pushButon_02.setText('확대(esc)')
            group_animation(
                ui,
                ui.szoo_pushButon_02,
                ui.ss_textEditttt_04,
                QRect(584, 761 if ui.extend_window else 483, 50, 20),
                QRect(7, 756 if ui.extend_window else 480, 647, 602 if ui.extend_window else 272)
            )
        ui.ss_textEditttt_03.setVisible(visible)
        if ui.sva_pushButton_01.isVisible():
            ui.ss_textEditttt_06.setVisible(visible)
        else:
            ui.ss_textEditttt_05.setVisible(visible)
        ui.szoo_pushButon_01.setVisible(visible)
