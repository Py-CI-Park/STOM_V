
def group_animation_01(ui):
    """stock_opti_test_editer, stock_rwf_test_editer, stock_opti_editer용 그룹 애니메이션"""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.ss_textEditttt_03.geometry()
    current_geo_tedt2 = ui.ss_textEditttt_04.geometry()
    current_geo_tedt3 = ui.ss_textEditttt_05.geometry()
    current_geo_comb1 = ui.svc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.svc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.svc_pushButton_03.geometry()
    current_geo_btn02 = ui.svc_pushButton_04.geometry()
    current_geo_zoo01 = ui.szoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.szoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 647, 740 if ui.extend_window else 460)
    target_geo_tedt2 = QRect(7, 755 if ui.extend_window else 475, 647, 600 if ui.extend_window else 275)
    target_geo_tedt3 = QRect(659, 10, 347, 1345 if ui.extend_window else 740)
    target_geo_comb1 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn01 = QRect(1012, 150, 165, 30)
    target_geo_btn02 = QRect(1182, 150, 165, 30)
    target_geo_zoo01 = QRect(584, 15, 50, 20)
    target_geo_zoo02 = QRect(584, 760 if ui.extend_window else 480, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.ss_textEditttt_03, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.ss_textEditttt_04, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.ss_textEditttt_05, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_comb1 = QPropertyAnimation(ui.svc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.svc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.svc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.svc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_zoo01 = QPropertyAnimation(ui.szoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.szoo_pushButon_02, b'geometry')
    anim_zoo02.setDuration(300)
    anim_zoo02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo02.setStartValue(current_geo_zoo02)
    anim_zoo02.setEndValue(target_geo_zoo02)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group.addAnimation(anim_tedt1)
    ui.animation_group.addAnimation(anim_tedt2)
    ui.animation_group.addAnimation(anim_tedt3)
    ui.animation_group.addAnimation(anim_comb1)
    ui.animation_group.addAnimation(anim_line1)
    ui.animation_group.addAnimation(anim_btn01)
    ui.animation_group.addAnimation(anim_btn02)
    ui.animation_group.addAnimation(anim_zoo01)
    ui.animation_group.addAnimation(anim_zoo02)

    # 애니메이션 시작
    ui.animation_group.start()


def group_animation_02(ui):
    """stock_opti_ga_editer용 그룹 애니메이션"""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.ss_textEditttt_03.geometry()
    current_geo_tedt2 = ui.ss_textEditttt_04.geometry()
    current_geo_tedt3 = ui.ss_textEditttt_06.geometry()
    current_geo_comb1 = ui.svc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.svc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.svc_pushButton_03.geometry()
    current_geo_btn02 = ui.svc_pushButton_04.geometry()
    current_geo_comb2 = ui.sva_comboBoxxx_01.geometry()
    current_geo_line2 = ui.sva_lineEdittt_01.geometry()
    current_geo_btn03 = ui.sva_pushButton_04.geometry()
    current_geo_btn04 = ui.sva_pushButton_05.geometry()
    current_geo_zoo01 = ui.szoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.szoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 647, 740 if ui.extend_window else 460)
    target_geo_tedt2 = QRect(7, 755 if ui.extend_window else 475, 647, 600 if ui.extend_window else 275)
    target_geo_tedt3 = QRect(659, 10, 347, 1345 if ui.extend_window else 740)
    target_geo_comb1 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn01 = QRect(1012, 150, 165, 30)
    target_geo_btn02 = QRect(1182, 150, 165, 30)
    target_geo_comb2 = QRect(1012, 115, 165, 30)
    target_geo_line2 = QRect(1182, 115, 165, 30)
    target_geo_btn03 = QRect(1012, 150, 165, 30)
    target_geo_btn04 = QRect(1182, 150, 165, 30)
    target_geo_zoo01 = QRect(584, 15, 50, 20)
    target_geo_zoo02 = QRect(584, 760 if ui.extend_window else 480, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.ss_textEditttt_03, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.ss_textEditttt_04, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.ss_textEditttt_06, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_comb1 = QPropertyAnimation(ui.svc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.svc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.svc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.svc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb2 = QPropertyAnimation(ui.sva_comboBoxxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_line2 = QPropertyAnimation(ui.sva_lineEdittt_01, b'geometry')
    anim_line2.setDuration(300)
    anim_line2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line2.setStartValue(current_geo_line2)
    anim_line2.setEndValue(target_geo_line2)

    anim_btn03 = QPropertyAnimation(ui.sva_pushButton_04, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.sva_pushButton_05, b'geometry')
    anim_btn04.setDuration(300)
    anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn04.setStartValue(current_geo_btn04)
    anim_btn04.setEndValue(target_geo_btn04)

    anim_zoo01 = QPropertyAnimation(ui.szoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.szoo_pushButon_02, b'geometry')
    anim_zoo02.setDuration(300)
    anim_zoo02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo02.setStartValue(current_geo_zoo02)
    anim_zoo02.setEndValue(target_geo_zoo02)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group.addAnimation(anim_tedt1)
    ui.animation_group.addAnimation(anim_tedt2)
    ui.animation_group.addAnimation(anim_tedt3)
    ui.animation_group.addAnimation(anim_comb1)
    ui.animation_group.addAnimation(anim_line1)
    ui.animation_group.addAnimation(anim_btn01)
    ui.animation_group.addAnimation(anim_btn02)
    ui.animation_group.addAnimation(anim_comb2)
    ui.animation_group.addAnimation(anim_line2)
    ui.animation_group.addAnimation(anim_btn03)
    ui.animation_group.addAnimation(anim_btn04)
    ui.animation_group.addAnimation(anim_zoo01)
    ui.animation_group.addAnimation(anim_zoo02)

    # 애니메이션 시작
    ui.animation_group.start()


def group_animation_03(ui):
    """stock_opti_vars_editer용 그룹 애니메이션"""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.ss_textEditttt_05.geometry()
    current_geo_tedt2 = ui.ss_textEditttt_06.geometry()
    current_geo_comb1 = ui.svc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.svc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.svc_pushButton_03.geometry()
    current_geo_btn02 = ui.svc_pushButton_04.geometry()
    current_geo_comb2 = ui.sva_comboBoxxx_01.geometry()
    current_geo_line2 = ui.sva_lineEdittt_01.geometry()
    current_geo_btn03 = ui.sva_pushButton_04.geometry()
    current_geo_btn04 = ui.sva_pushButton_05.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 497, 1345 if ui.extend_window else 740)
    target_geo_tedt2 = QRect(509, 10, 497, 1345 if ui.extend_window else 740)
    target_geo_comb1 = QRect(1012, 10, 165, 30)
    target_geo_line1 = QRect(1182, 10, 165, 30)
    target_geo_btn01 = QRect(1012, 45, 165, 30)
    target_geo_btn02 = QRect(1182, 45, 165, 30)
    target_geo_comb2 = QRect(1012, 80, 165, 30)
    target_geo_line2 = QRect(1182, 80, 165, 30)
    target_geo_btn03 = QRect(1012, 115, 165, 30)
    target_geo_btn04 = QRect(1182, 115, 165, 30)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.ss_textEditttt_05, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.ss_textEditttt_06, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_comb1 = QPropertyAnimation(ui.svc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.svc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.svc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.svc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb2 = QPropertyAnimation(ui.sva_comboBoxxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_line2 = QPropertyAnimation(ui.sva_lineEdittt_01, b'geometry')
    anim_line2.setDuration(300)
    anim_line2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line2.setStartValue(current_geo_line2)
    anim_line2.setEndValue(target_geo_line2)

    anim_btn03 = QPropertyAnimation(ui.sva_pushButton_04, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.sva_pushButton_05, b'geometry')
    anim_btn04.setDuration(300)
    anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn04.setStartValue(current_geo_btn04)
    anim_btn04.setEndValue(target_geo_btn04)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group.addAnimation(anim_tedt1)
    ui.animation_group.addAnimation(anim_tedt2)
    ui.animation_group.addAnimation(anim_comb1)
    ui.animation_group.addAnimation(anim_line1)
    ui.animation_group.addAnimation(anim_btn01)
    ui.animation_group.addAnimation(anim_btn02)
    ui.animation_group.addAnimation(anim_comb2)
    ui.animation_group.addAnimation(anim_line2)
    ui.animation_group.addAnimation(anim_btn03)
    ui.animation_group.addAnimation(anim_btn04)

    # 애니메이션 시작
    ui.animation_group.start()


def group_animation_04(ui):
    """stock_vars_editer용 그룹 애니메이션"""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.ss_textEditttt_01.geometry()
    current_geo_tedt2 = ui.ss_textEditttt_02.geometry()
    current_geo_tedt3 = ui.ss_textEditttt_03.geometry()
    current_geo_tedt4 = ui.ss_textEditttt_04.geometry()
    current_geo_comb1 = ui.svjb_comboBoxx_01.geometry()
    current_geo_btn01 = ui.svjb_pushButon_01.geometry()
    current_geo_comb2 = ui.svjs_comboBoxx_01.geometry()
    current_geo_btn02 = ui.svjs_pushButon_01.geometry()
    current_geo_comb3 = ui.svc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.svc_lineEdittt_02.geometry()
    current_geo_btn03 = ui.svc_pushButton_03.geometry()
    current_geo_btn04 = ui.svc_pushButton_04.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 497, 740 if ui.extend_window else 460)
    target_geo_tedt2 = QRect(7, 755 if ui.extend_window else 475, 497, 600 if ui.extend_window else 275)
    target_geo_tedt3 = QRect(509, 10, 497, 740 if ui.extend_window else 460)
    target_geo_tedt4 = QRect(509, 755 if ui.extend_window else 475, 497, 600 if ui.extend_window else 275)
    target_geo_comb1 = QRect(1012, 10, 165, 30)
    target_geo_btn01 = QRect(1182, 10, 165, 30)
    target_geo_comb2 = QRect(1012, 475, 165, 30)
    target_geo_btn02 = QRect(1182, 475, 165, 30)
    target_geo_comb3 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn03 = QRect(1012, 150, 165, 30)
    target_geo_btn04 = QRect(1182, 150, 165, 30)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.ss_textEditttt_01, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.ss_textEditttt_02, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.ss_textEditttt_03, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_tedt4 = QPropertyAnimation(ui.ss_textEditttt_04, b'geometry')
    anim_tedt4.setDuration(300)
    anim_tedt4.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt4.setStartValue(current_geo_tedt4)
    anim_tedt4.setEndValue(target_geo_tedt4)

    anim_comb1 = QPropertyAnimation(ui.svjb_comboBoxx_01, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_btn01 = QPropertyAnimation(ui.svjb_pushButon_01, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_comb2 = QPropertyAnimation(ui.svjs_comboBoxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_btn02 = QPropertyAnimation(ui.svjs_pushButon_01, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb3 = QPropertyAnimation(ui.svc_comboBoxxx_02, b'geometry')
    anim_comb3.setDuration(300)
    anim_comb3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb3.setStartValue(current_geo_comb3)
    anim_comb3.setEndValue(target_geo_comb3)

    anim_line1 = QPropertyAnimation(ui.svc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn03 = QPropertyAnimation(ui.svc_pushButton_03, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.svc_pushButton_04, b'geometry')
    anim_btn04.setDuration(300)
    anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn04.setStartValue(current_geo_btn04)
    anim_btn04.setEndValue(target_geo_btn04)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group.addAnimation(anim_tedt1)
    ui.animation_group.addAnimation(anim_tedt2)
    ui.animation_group.addAnimation(anim_tedt3)
    ui.animation_group.addAnimation(anim_tedt4)
    ui.animation_group.addAnimation(anim_comb1)
    ui.animation_group.addAnimation(anim_btn01)
    ui.animation_group.addAnimation(anim_comb2)
    ui.animation_group.addAnimation(anim_btn02)
    ui.animation_group.addAnimation(anim_comb3)
    ui.animation_group.addAnimation(anim_line1)
    ui.animation_group.addAnimation(anim_btn03)
    ui.animation_group.addAnimation(anim_btn04)

    # 애니메이션 시작
    ui.animation_group.start()


def group_animation_05(ui):
    """stock_stg_editer용 그룹 애니메이션"""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.ss_textEditttt_01.geometry()
    current_geo_tedt2 = ui.ss_textEditttt_02.geometry()
    current_geo_comb1 = ui.svjb_comboBoxx_01.geometry()
    current_geo_btn01 = ui.svjb_pushButon_01.geometry()
    current_geo_comb2 = ui.svjs_comboBoxx_01.geometry()
    current_geo_btn02 = ui.svjs_pushButon_01.geometry()
    current_geo_zoo01 = ui.szoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.szoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 1000, 740 if ui.extend_window else 460)
    target_geo_tedt2 = QRect(7, 755 if ui.extend_window else 475, 1000, 600 if ui.extend_window else 275)
    target_geo_comb1 = QRect(1012, 10, 165, 25)
    target_geo_btn01 = QRect(1012, 40, 165, 30)
    target_geo_comb2 = QRect(1012, 475, 165, 30)
    target_geo_btn02 = QRect(1012, 510, 165, 30)
    target_geo_zoo01 = QRect(937, 15, 50, 20)
    target_geo_zoo02 = QRect(937, 760 if ui.extend_window else 480, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.ss_textEditttt_01, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.ss_textEditttt_02, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_comb1 = QPropertyAnimation(ui.svjb_comboBoxx_01, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_btn01 = QPropertyAnimation(ui.svjb_pushButon_01, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_comb2 = QPropertyAnimation(ui.svjs_comboBoxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_btn02 = QPropertyAnimation(ui.svjs_pushButon_01, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_zoo01 = QPropertyAnimation(ui.szoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.szoo_pushButon_02, b'geometry')
    anim_zoo02.setDuration(300)
    anim_zoo02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo02.setStartValue(current_geo_zoo02)
    anim_zoo02.setEndValue(target_geo_zoo02)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group.addAnimation(anim_tedt1)
    ui.animation_group.addAnimation(anim_tedt2)
    ui.animation_group.addAnimation(anim_comb1)
    ui.animation_group.addAnimation(anim_btn01)
    ui.animation_group.addAnimation(anim_comb2)
    ui.animation_group.addAnimation(anim_btn02)
    ui.animation_group.addAnimation(anim_zoo01)
    ui.animation_group.addAnimation(anim_zoo02)

    # 애니메이션 시작
    ui.animation_group.start()


# noinspection PyUnboundLocalVariable
def group_animation_06(ui, pushButton1, pushButton2, pushButton3, pushButton4=None):
    """버튼 그룹 애니메이션 06을 실행합니다."""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 좌측 상단으로 지오메트리 저장
    current_geo_btn01 = QRect(1350, 0, 0, 0)
    current_geo_btn02 = QRect(1350, 0, 0, 0)
    current_geo_btn03 = QRect(1350, 0, 0, 0)
    current_geo_btn04 = QRect(1350, 0, 0, 0)

    # 목표 지오메트리 설정
    target_geo_btn01 = QRect(1012, 335, 165, 30)
    target_geo_btn02 = QRect(1012, 370, 165, 30)

    if pushButton4 is None:
        target_geo_btn03  = QRect(1012, 405, 165, 30)
    else:
        target_geo_btn03  = QRect(1012, 405, 80, 30)
        target_geo_btn04  = QRect(1097, 405, 80, 30)

    # 애니메이션 그룹 생성
    ui.animation_group2 = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_btn01 = QPropertyAnimation(pushButton1, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(pushButton2, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_btn03 = QPropertyAnimation(pushButton3, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    if pushButton4 is not None:
        anim_btn04 = QPropertyAnimation(pushButton4, b'geometry')
        anim_btn04.setDuration(300)
        anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
        anim_btn04.setStartValue(current_geo_btn04)
        anim_btn04.setEndValue(target_geo_btn04)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group2.addAnimation(anim_btn01)
    ui.animation_group2.addAnimation(anim_btn02)
    ui.animation_group2.addAnimation(anim_btn03)
    if pushButton4 is not None:
        ui.animation_group2.addAnimation(anim_btn04)

    # 애니메이션 시작
    ui.animation_group2.start()


def group_animation_07(ui, pushButton1, pushButton2, pushButton3, pushButton4, pushButton5, pushButton6):
    """버튼 그룹 애니메이션 07을 실행합니다."""
    from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect

    # 위젯들의 좌측 상단으로 지오메트리 저장
    current_geo_btn01 = QRect(1350, 0, 0, 0)
    current_geo_btn02 = QRect(1350, 0, 0, 0)
    current_geo_btn03 = QRect(1350, 0, 0, 0)
    current_geo_btn04 = QRect(1350, 0, 0, 0)
    current_geo_btn05 = QRect(1350, 0, 0, 0)
    current_geo_btn06 = QRect(1350, 0, 0, 0)

    # 목표 지오메트리 설정
    target_geo_btn01 = QRect(1012, 335, 80, 30)
    target_geo_btn02 = QRect(1012, 370, 80, 30)
    target_geo_btn03 = QRect(1012, 405, 80, 30)
    target_geo_btn04 = QRect(1097, 335, 80, 30)
    target_geo_btn05 = QRect(1097, 370, 80, 30)
    target_geo_btn06 = QRect(1097, 405, 80, 30)

    # 애니메이션 그룹 생성
    ui.animation_group2 = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_btn01 = QPropertyAnimation(pushButton1, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(pushButton2, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_btn03 = QPropertyAnimation(pushButton3, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(pushButton4, b'geometry')
    anim_btn04.setDuration(300)
    anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn04.setStartValue(current_geo_btn04)
    anim_btn04.setEndValue(target_geo_btn04)

    anim_btn05 = QPropertyAnimation(pushButton5, b'geometry')
    anim_btn05.setDuration(300)
    anim_btn05.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn05.setStartValue(current_geo_btn05)
    anim_btn05.setEndValue(target_geo_btn05)

    anim_btn06 = QPropertyAnimation(pushButton6, b'geometry')
    anim_btn06.setDuration(300)
    anim_btn06.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn06.setStartValue(current_geo_btn06)
    anim_btn06.setEndValue(target_geo_btn06)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group2.addAnimation(anim_btn01)
    ui.animation_group2.addAnimation(anim_btn02)
    ui.animation_group2.addAnimation(anim_btn03)
    ui.animation_group2.addAnimation(anim_btn04)
    ui.animation_group2.addAnimation(anim_btn05)
    ui.animation_group2.addAnimation(anim_btn06)

    # 애니메이션 시작
    ui.animation_group2.start()


def opti_test_editer(ui):
    """최적화 테스트 에디터를 표시합니다."""
    from ui.create_widget.set_text import testtext

    group_animation_01(ui)
    group_animation_07(ui, ui.svc_pushButton_15, ui.svc_pushButton_16, ui.svc_pushButton_17, ui.svc_pushButton_30, ui.svc_pushButton_31, ui.svc_pushButton_32)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(True)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)
    for item in ui.optest_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(testtext)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_07.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def rwf_test_editer(ui):
    """전진분석 테스트 에디터를 표시합니다."""
    from ui.create_widget.set_text import rwfttext

    group_animation_01(ui)
    group_animation_07(ui, ui.svc_pushButton_18, ui.svc_pushButton_19, ui.svc_pushButton_20, ui.svc_pushButton_33, ui.svc_pushButton_34, ui.svc_pushButton_35)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(True)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)
    for item in ui.rwftvd_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_01.setVisible(False)
    ui.svc_labellllll_04.setText(rwfttext)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_06.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def opti_ga_editer(ui):
    """유전알고리즘 최적화 에디터를 표시합니다."""
    from ui.create_widget.set_text import gaoptext

    group_animation_02(ui)
    group_animation_06(ui, ui.sva_pushButton_01, ui.sva_pushButton_02, ui.sva_pushButton_03)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(True)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(True)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)
    for item in ui.gaopti_list:
        item.setVisible(True)

    ui.sva_pushButton_04.setText('GA 변수범위 로딩(F9)')
    ui.sva_pushButton_05.setText('GA 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(gaoptext)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_10.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def opti_vars_editer(ui):
    """최적화 변수 에디터를 표시합니다."""
    from ui.create_widget.set_text import gaoptext, vedittxt

    group_animation_03(ui)
    group_animation_06(ui, ui.svc_pushButton_21, ui.svc_pushButton_22, ui.svc_pushButton_23)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(True)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(False)
    for item in ui.optimz_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)
    for item in ui.gaopti_list:
        item.setVisible(True)

    ui.sva_pushButton_04.setText('GA 변수범위 로딩')
    ui.sva_pushButton_05.setText('GA 변수범위 저장')
    ui.svc_pushButton_03.setText('최적화 변수범위 로딩')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장')

    ui.svc_pushButton_06.setVisible(False)
    ui.svc_pushButton_07.setVisible(False)
    ui.svc_pushButton_08.setVisible(False)
    ui.svc_pushButton_27.setVisible(False)
    ui.svc_pushButton_28.setVisible(False)
    ui.svc_pushButton_29.setVisible(False)

    ui.sva_pushButton_01.setVisible(False)
    ui.sva_pushButton_02.setVisible(False)
    ui.sva_pushButton_03.setVisible(False)

    ui.svc_comboBoxxx_02.setVisible(True)
    ui.svc_lineEdittt_02.setVisible(True)
    ui.svc_pushButton_03.setVisible(True)
    ui.svc_pushButton_04.setVisible(True)

    ui.svc_pushButton_11.setVisible(True)

    ui.image_label1.setVisible(True)
    ui.svc_labellllll_04.setText(gaoptext)
    ui.svc_labellllll_05.setText(vedittxt)
    ui.svc_labellllll_05.setVisible(True)

    ui.svj_pushButton_12.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def opti_editer(ui):
    """최적화 에디터를 표시합니다."""
    from ui.create_widget.set_text import optitext

    group_animation_01(ui)
    group_animation_07(ui, ui.svc_pushButton_06, ui.svc_pushButton_07, ui.svc_pushButton_08, ui.svc_pushButton_27, ui.svc_pushButton_28, ui.svc_pushButton_29)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(True)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(optitext)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_08.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def opti_gavars_editer(ui):
    """최적화 GA 변수 에디터를 표시합니다."""
    from ui.create_widget.set_text import optitext

    group_animation_04(ui)
    group_animation_06(ui, ui.svc_pushButton_24, ui.svc_pushButton_25, ui.svc_pushButton_26)

    ui.ss_textEditttt_01.setVisible(True)
    ui.ss_textEditttt_02.setVisible(True)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(True)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)

    ui.svjb_pushButon_01.setText('매수전략 로딩')
    ui.svjs_pushButon_01.setText('매도전략 로딩')

    ui.svjb_comboBoxx_01.setVisible(True)
    ui.svjb_pushButon_01.setVisible(True)
    ui.svjs_comboBoxx_01.setVisible(True)
    ui.svjs_pushButon_01.setVisible(True)

    ui.svc_lineEdittt_04.setVisible(False)
    ui.svc_pushButton_13.setVisible(False)
    ui.svc_lineEdittt_05.setVisible(False)
    ui.svc_pushButton_14.setVisible(False)

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(optitext)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_13.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def change_pre_button_edit(ui):
    """이전 버튼의 색상을 변경합니다."""
    from ui.create_widget.set_style import style_bc_bd
    if ui.svj_pushButton_01.isVisible():
        ui.svj_pushButton_09.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_32.isVisible():
        ui.svj_pushButton_07.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_35.isVisible():
        ui.svj_pushButton_06.setStyleSheet(style_bc_bd)
    elif ui.sva_pushButton_03.isVisible():
        ui.svj_pushButton_10.setStyleSheet(style_bc_bd)
    elif ui.svo_pushButton_08.isVisible():
        ui.svj_pushButton_11.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_23.isVisible():
        ui.svj_pushButton_12.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_26.isVisible():
        ui.svj_pushButton_13.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_29.isVisible():
        ui.svj_pushButton_08.setStyleSheet(style_bc_bd)


def backtest_log(ui):
    """백테스트 로그를 표시합니다."""
    from ui.create_widget.set_style import style_bc_by, style_bc_dk, style_bc_bs

    change_pre_button_edit(ui)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)
    ui.ss_textEditttt_07.setVisible(False)
    ui.ss_textEditttt_08.setVisible(False)

    ui.ss_textEditttt_09.setGeometry(7, 10, 1000, 1310 if ui.extend_window else 705)
    ui.ss_progressBar_01.setGeometry(7, 1325 if ui.extend_window else 720, 830, 30)
    ui.ss_pushButtonn_08.setGeometry(842, 1325 if ui.extend_window else 720, 165, 30)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(True)

    ui.ss_pushButtonn_08.setStyleSheet(style_bc_by)
    ui.svj_pushButton_14.setFocus()
    ui.svj_pushButton_14.setStyleSheet(style_bc_dk)
    ui.svj_pushButton_15.setStyleSheet(style_bc_bs)
    change_version_button_color(ui)


def backtest_detail(ui):
    """백테스트 상세 정보를 표시합니다."""
    from ui.create_widget.set_style import style_bc_dk, style_bc_bs

    change_pre_button_edit(ui)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)
    ui.ss_textEditttt_07.setVisible(False)
    ui.ss_textEditttt_08.setVisible(False)

    ui.ss_tableWidget_01.setGeometry(7, 40, 1000, 1315 if ui.extend_window else 710)
    if (ui.extend_window and ui.ss_tableWidget_01.rowCount() < 60) or \
            (not ui.extend_window and ui.ss_tableWidget_01.rowCount() < 32):
        ui.ss_tableWidget_01.setRowCount(60 if ui.extend_window else 32)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(True)

    ui.svj_pushButton_15.setFocus()
    ui.svj_pushButton_15.setStyleSheet(style_bc_dk)
    ui.svj_pushButton_14.setStyleSheet(style_bc_bs)
    change_version_button_color(ui)


def stg_editer(ui):
    """전략 에디터를 표시합니다."""
    group_animation_05(ui)
    group_animation_06(ui, ui.svj_pushButton_01, ui.svj_pushButton_02, ui.svj_pushButton_03, ui.svj_pushButton_04)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(True)
    ui.ss_textEditttt_02.setVisible(True)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.optimz_list:
        item.setVisible(False)
    for item in ui.period_list:
        item.setVisible(False)
    for item in ui.opcond_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(True)
    for item in ui.esczom_list:
        item.setVisible(True)
    for item in ui.backte_list:
        item.setVisible(True)

    ui.svjb_pushButon_01.setText('매수전략 로딩(F1)')
    ui.svjs_pushButon_01.setText('매도전략 로딩(F5)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_05.setVisible(False)

    ui.svj_pushButton_09.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def opti_cond_editer(ui):
    """조건 최적화 에디터를 표시합니다."""
    from ui.create_widget.set_text import condtext, cedittxt

    group_animation_06(ui, ui.svo_pushButton_05, ui.svo_pushButton_06, ui.svo_pushButton_07)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    ui.ss_textEditttt_07.setGeometry(7, 10, 497, 1345 if ui.extend_window else 740)
    ui.ss_textEditttt_08.setGeometry(509, 10, 497, 1345 if ui.extend_window else 740)

    for item in ui.version_list:
        item.setVisible(False)
    for item in ui.esczom_list:
        item.setVisible(False)
    for item in ui.backte_list:
        item.setVisible(False)
    for item in ui.detail_list:
        item.setVisible(False)
    for item in ui.baklog_list:
        item.setVisible(False)
    for item in ui.gaopti_list:
        item.setVisible(False)
    for item in ui.optest_list:
        item.setVisible(False)
    for item in ui.rwftvd_list:
        item.setVisible(False)
    for item in ui.datedt_list:
        item.setVisible(False)
    for item in ui.varsedit_list:
        item.setVisible(False)
    for item in ui.areaedit_list:
        item.setVisible(False)
    for item in ui.optimz_list:
        item.setVisible(True)
    for item in ui.period_list:
        item.setVisible(True)
    for item in ui.opcond_list:
        item.setVisible(True)

    ui.svc_lineEdittt_04.setVisible(False)
    ui.svc_lineEdittt_05.setVisible(False)
    ui.svc_pushButton_13.setVisible(False)
    ui.svc_pushButton_14.setVisible(False)

    ui.svc_comboBoxxx_08.setVisible(False)
    ui.svc_lineEdittt_03.setVisible(False)
    ui.svc_pushButton_09.setVisible(False)
    ui.svc_pushButton_10.setVisible(False)

    ui.svc_comboBoxxx_02.setVisible(False)
    ui.svc_lineEdittt_02.setVisible(False)
    ui.svc_pushButton_03.setVisible(False)
    ui.svc_pushButton_04.setVisible(False)

    ui.image_label1.setVisible(True)
    ui.svc_labellllll_01.setVisible(False)
    ui.svc_labellllll_04.setText(condtext)
    ui.svc_labellllll_05.setText(cedittxt)
    ui.svc_labellllll_05.setVisible(True)

    ui.svj_pushButton_11.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


def backfinder_sample(ui):
    """백파인더 샘플을 로드합니다."""
    from ui.create_widget.set_text import example_backfinder
    if ui.ss_textEditttt_01.isVisible():
        ui.ss_textEditttt_01.clear()
        ui.ss_textEditttt_02.clear()
        ui.ss_textEditttt_01.append(example_backfinder)


def optivars_to_gavars(ui):
    """최적화 변수를 GA 변수로 변환합니다."""
    from PyQt5.QtWidgets import QMessageBox
    from ui.event_click.button_clicked_varstext_change import get_optivars_to_gavars

    opti_vars_text = ui.ss_textEditttt_05.toPlainText()
    if opti_vars_text:
        ga_vars_text = get_optivars_to_gavars(ui, opti_vars_text)
        ui.ss_textEditttt_06.clear()
        ui.ss_textEditttt_06.append(ga_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 최적화 범위 코드가 공백 상태입니다.\n최적화 범위 코드를 작성하거나 로딩하십시오.\n')


def gavars_to_optivars(ui):
    """GA 변수를 최적화 변수로 변환합니다."""
    from PyQt5.QtWidgets import QMessageBox
    from ui.event_click.button_clicked_varstext_change import get_gavars_to_optivars

    ga_vars_text = ui.ss_textEditttt_06.toPlainText()
    if ga_vars_text:
        opti_vars_text = get_gavars_to_optivars(ui, ga_vars_text)
        ui.ss_textEditttt_05.clear()
        ui.ss_textEditttt_05.append(opti_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 GA 범위 코드가 공백 상태입니다.\nGA 범위 코드를 작성하거나 로딩하십시오.\n')


def stg_vars_change(ui):
    """전략 변수를 변경합니다."""
    from ui.event_click.button_clicked_varstext_change import get_stgtxt_to_varstxt

    buystg = ui.ss_textEditttt_01.toPlainText()
    sellstg = ui.ss_textEditttt_02.toPlainText()
    buystg_str, sellstg_str = get_stgtxt_to_varstxt(ui, buystg, sellstg)
    ui.ss_textEditttt_03.clear()
    ui.ss_textEditttt_04.clear()
    ui.ss_textEditttt_03.append(buystg_str)
    ui.ss_textEditttt_04.append(sellstg_str)


def stgvars_key_sort(ui):
    """전략 변수 키를 정렬합니다."""
    from ui.event_click.button_clicked_varstext_change import get_stgtxt_sort2

    optivars = ui.ss_textEditttt_05.toPlainText()
    gavars = ui.ss_textEditttt_06.toPlainText()
    optivars_str, gavars_str = get_stgtxt_sort2(optivars, gavars)
    ui.ss_textEditttt_05.clear()
    ui.ss_textEditttt_06.clear()
    ui.ss_textEditttt_05.append(optivars_str)
    ui.ss_textEditttt_06.append(gavars_str)


def optivars_key_sort(ui):
    """최적화 변수 키를 정렬합니다."""
    from ui.event_click.button_clicked_varstext_change import get_stgtxt_sort

    buystg = ui.ss_textEditttt_03.toPlainText()
    sellstg = ui.ss_textEditttt_04.toPlainText()
    buystg_str, sellstg_str = get_stgtxt_sort(buystg, sellstg)
    ui.ss_textEditttt_03.clear()
    ui.ss_textEditttt_04.clear()
    ui.ss_textEditttt_03.append(buystg_str)
    ui.ss_textEditttt_04.append(sellstg_str)


def change_svj_button_color(ui):
    """버튼 색상을 변경합니다."""
    from ui.create_widget.set_style import style_bc_dk, style_bc_bs

    for button in ui.editer_list:
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_bs)


def change_version_button_color(ui):
    """버전 버튼 색상을 변경합니다."""
    from ui.create_widget.set_style import style_bc_dk, style_bc_st

    for button in ui.load_list:
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_st)
