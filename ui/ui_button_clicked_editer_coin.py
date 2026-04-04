
from multiprocessing import Process
from backtest.optimiz import Optimize
from backtest.backtest import BackTest
from backtest.backfinder import BackFinder
from PyQt5.QtWidgets import QMessageBox, QApplication
from backtest.optimiz_conditions import OptimizeConditions
from backtest.rolling_walk_forward_test import RollingWalkForwardTest
from backtest.optimiz_genetic_algorithm import OptimizeGeneticAlgorithm
from ui.set_style import style_bc_by, style_bc_dk, style_bc_bs, style_bc_bd, style_bc_st
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect
from ui.set_text import testtext, rwfttext, gaoptext, vedittxt, optitext, condtext, cedittxt, example_finder, \
    example_finder_future
from utility.static import error_decorator


def group_animation_01(ui):
    """coin_opti_test_editer, coin_rwf_test_editer, coin_opti_editer용 그룹 애니메이션"""
    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.cs_textEditttt_03.geometry()
    current_geo_tedt2 = ui.cs_textEditttt_04.geometry()
    current_geo_tedt3 = ui.cs_textEditttt_05.geometry()
    current_geo_comb1 = ui.cvc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.cvc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.cvc_pushButton_03.geometry()
    current_geo_btn02 = ui.cvc_pushButton_04.geometry()
    current_geo_zoo01 = ui.czoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.czoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 647, 740 if ui.extend_window else 463)
    target_geo_tedt2 = QRect(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    target_geo_tedt3 = QRect(659, 10, 347, 1347 if ui.extend_window else 740)
    target_geo_comb1 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn01 = QRect(1012, 150, 165, 30)
    target_geo_btn02 = QRect(1182, 150, 165, 30)
    target_geo_zoo01 = QRect(584, 15, 50, 20)
    target_geo_zoo02 = QRect(584, 761 if ui.extend_window else 483, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.cs_textEditttt_03, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.cs_textEditttt_04, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.cs_textEditttt_05, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_comb1 = QPropertyAnimation(ui.cvc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.cvc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.cvc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.cvc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_zoo01 = QPropertyAnimation(ui.czoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.czoo_pushButon_02, b'geometry')
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
    """coin_opti_ga_editer용 그룹 애니메이션"""
    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.cs_textEditttt_03.geometry()
    current_geo_tedt2 = ui.cs_textEditttt_04.geometry()
    current_geo_tedt3 = ui.cs_textEditttt_06.geometry()
    current_geo_comb1 = ui.cvc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.cvc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.cvc_pushButton_03.geometry()
    current_geo_btn02 = ui.cvc_pushButton_04.geometry()
    current_geo_comb2 = ui.cva_comboBoxxx_01.geometry()
    current_geo_line2 = ui.cva_lineEdittt_01.geometry()
    current_geo_btn03 = ui.cva_pushButton_04.geometry()
    current_geo_btn04 = ui.cva_pushButton_05.geometry()
    current_geo_zoo01 = ui.czoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.czoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 647, 740 if ui.extend_window else 463)
    target_geo_tedt2 = QRect(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    target_geo_tedt3 = QRect(659, 10, 347, 1347 if ui.extend_window else 740)
    target_geo_comb1 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn01 = QRect(1012, 150, 165, 30)
    target_geo_btn02 = QRect(1182, 150, 165, 30)
    target_geo_comb2 = QRect(1012, 115, 165, 30)
    target_geo_line2 = QRect(1182, 115, 165, 30)
    target_geo_btn03 = QRect(1012, 150, 165, 30)
    target_geo_btn04 = QRect(1182, 150, 165, 30)
    target_geo_zoo01 = QRect(584, 15, 50, 20)
    target_geo_zoo02 = QRect(584, 761 if ui.extend_window else 483, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.cs_textEditttt_03, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.cs_textEditttt_04, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.cs_textEditttt_06, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_comb1 = QPropertyAnimation(ui.cvc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.cvc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.cvc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.cvc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb2 = QPropertyAnimation(ui.cva_comboBoxxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_line2 = QPropertyAnimation(ui.cva_lineEdittt_01, b'geometry')
    anim_line2.setDuration(300)
    anim_line2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line2.setStartValue(current_geo_line2)
    anim_line2.setEndValue(target_geo_line2)

    anim_btn03 = QPropertyAnimation(ui.cva_pushButton_04, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.cva_pushButton_05, b'geometry')
    anim_btn04.setDuration(300)
    anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn04.setStartValue(current_geo_btn04)
    anim_btn04.setEndValue(target_geo_btn04)

    anim_zoo01 = QPropertyAnimation(ui.czoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.czoo_pushButon_02, b'geometry')
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
    """coin_opti_vars_editer용 그룹 애니메이션"""
    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.cs_textEditttt_05.geometry()
    current_geo_tedt2 = ui.cs_textEditttt_06.geometry()
    current_geo_comb1 = ui.cvc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.cvc_lineEdittt_02.geometry()
    current_geo_btn01 = ui.cvc_pushButton_03.geometry()
    current_geo_btn02 = ui.cvc_pushButton_04.geometry()
    current_geo_comb2 = ui.cva_comboBoxxx_01.geometry()
    current_geo_line2 = ui.cva_lineEdittt_01.geometry()
    current_geo_btn03 = ui.cva_pushButton_04.geometry()
    current_geo_btn04 = ui.cva_pushButton_05.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 497, 1347 if ui.extend_window else 740)
    target_geo_tedt2 = QRect(509, 10, 497, 1347 if ui.extend_window else 740)
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
    anim_tedt1 = QPropertyAnimation(ui.cs_textEditttt_05, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.cs_textEditttt_06, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_comb1 = QPropertyAnimation(ui.cvc_comboBoxxx_02, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_line1 = QPropertyAnimation(ui.cvc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn01 = QPropertyAnimation(ui.cvc_pushButton_03, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_btn02 = QPropertyAnimation(ui.cvc_pushButton_04, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb2 = QPropertyAnimation(ui.cva_comboBoxxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_line2 = QPropertyAnimation(ui.cva_lineEdittt_01, b'geometry')
    anim_line2.setDuration(300)
    anim_line2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line2.setStartValue(current_geo_line2)
    anim_line2.setEndValue(target_geo_line2)

    anim_btn03 = QPropertyAnimation(ui.cva_pushButton_04, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.cva_pushButton_05, b'geometry')
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
    """coin_vars_editer용 그룹 애니메이션"""
    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.cs_textEditttt_01.geometry()
    current_geo_tedt2 = ui.cs_textEditttt_02.geometry()
    current_geo_tedt3 = ui.cs_textEditttt_03.geometry()
    current_geo_tedt4 = ui.cs_textEditttt_04.geometry()
    current_geo_comb1 = ui.cvjb_comboBoxx_01.geometry()
    current_geo_btn01 = ui.cvjb_pushButon_01.geometry()
    current_geo_comb2 = ui.cvjs_comboBoxx_01.geometry()
    current_geo_btn02 = ui.cvjs_pushButon_01.geometry()
    current_geo_comb3 = ui.cvc_comboBoxxx_02.geometry()
    current_geo_line1 = ui.cvc_lineEdittt_02.geometry()
    current_geo_btn03 = ui.cvc_pushButton_03.geometry()
    current_geo_btn04 = ui.cvc_pushButton_04.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 497, 740 if ui.extend_window else 463)
    target_geo_tedt2 = QRect(7, 756 if ui.extend_window else 478, 497, 602 if ui.extend_window else 272)
    target_geo_tedt3 = QRect(509, 10, 497, 740 if ui.extend_window else 463)
    target_geo_tedt4 = QRect(509, 756 if ui.extend_window else 478, 497, 602 if ui.extend_window else 272)
    target_geo_comb1 = QRect(1012, 10, 165, 30)
    target_geo_btn01 = QRect(1182, 10, 165, 30)
    target_geo_comb2 = QRect(1012, 478, 165, 30)
    target_geo_btn02 = QRect(1182, 478, 165, 30)
    target_geo_comb3 = QRect(1012, 115, 165, 30)
    target_geo_line1 = QRect(1182, 115, 165, 30)
    target_geo_btn03 = QRect(1012, 150, 165, 30)
    target_geo_btn04 = QRect(1182, 150, 165, 30)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.cs_textEditttt_01, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.cs_textEditttt_02, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_tedt3 = QPropertyAnimation(ui.cs_textEditttt_03, b'geometry')
    anim_tedt3.setDuration(300)
    anim_tedt3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt3.setStartValue(current_geo_tedt3)
    anim_tedt3.setEndValue(target_geo_tedt3)

    anim_tedt4 = QPropertyAnimation(ui.cs_textEditttt_04, b'geometry')
    anim_tedt4.setDuration(300)
    anim_tedt4.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt4.setStartValue(current_geo_tedt4)
    anim_tedt4.setEndValue(target_geo_tedt4)

    anim_comb1 = QPropertyAnimation(ui.cvjb_comboBoxx_01, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_btn01 = QPropertyAnimation(ui.cvjb_pushButon_01, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_comb2 = QPropertyAnimation(ui.cvjs_comboBoxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_btn02 = QPropertyAnimation(ui.cvjs_pushButon_01, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_comb3 = QPropertyAnimation(ui.cvc_comboBoxxx_02, b'geometry')
    anim_comb3.setDuration(300)
    anim_comb3.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb3.setStartValue(current_geo_comb3)
    anim_comb3.setEndValue(target_geo_comb3)

    anim_line1 = QPropertyAnimation(ui.cvc_lineEdittt_02, b'geometry')
    anim_line1.setDuration(300)
    anim_line1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_line1.setStartValue(current_geo_line1)
    anim_line1.setEndValue(target_geo_line1)

    anim_btn03 = QPropertyAnimation(ui.cvc_pushButton_03, b'geometry')
    anim_btn03.setDuration(300)
    anim_btn03.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn03.setStartValue(current_geo_btn03)
    anim_btn03.setEndValue(target_geo_btn03)

    anim_btn04 = QPropertyAnimation(ui.cvc_pushButton_04, b'geometry')
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
    """coin_stg_editer용 그룹 애니메이션"""
    # 위젯들의 현재 지오메트리 저장
    current_geo_tedt1 = ui.cs_textEditttt_01.geometry()
    current_geo_tedt2 = ui.cs_textEditttt_02.geometry()
    current_geo_comb1 = ui.cvjb_comboBoxx_01.geometry()
    current_geo_btn01 = ui.cvjb_pushButon_01.geometry()
    current_geo_comb2 = ui.cvjs_comboBoxx_01.geometry()
    current_geo_btn02 = ui.cvjs_pushButon_01.geometry()
    current_geo_zoo01 = ui.czoo_pushButon_01.geometry()
    current_geo_zoo02 = ui.czoo_pushButon_02.geometry()

    # 목표 지오메트리 설정
    target_geo_tedt1 = QRect(7, 10, 1000, 740 if ui.extend_window else 463)
    target_geo_tedt2 = QRect(7, 756 if ui.extend_window else 478, 1000, 602 if ui.extend_window else 272)
    target_geo_comb1 = QRect(1012, 10, 165, 25)
    target_geo_btn01 = QRect(1012, 40, 165, 30)
    target_geo_comb2 = QRect(1012, 478, 165, 25)
    target_geo_btn02 = QRect(1012, 508, 165, 30)
    target_geo_zoo01 = QRect(937, 15, 50, 20)
    target_geo_zoo02 = QRect(937, 761 if ui.extend_window else 483, 50, 20)

    # 애니메이션 그룹 생성
    ui.animation_group = QParallelAnimationGroup()

    # 각 위젯의 지오메트리 애니메이션 생성
    anim_tedt1 = QPropertyAnimation(ui.cs_textEditttt_01, b'geometry')
    anim_tedt1.setDuration(300)
    anim_tedt1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt1.setStartValue(current_geo_tedt1)
    anim_tedt1.setEndValue(target_geo_tedt1)

    anim_tedt2 = QPropertyAnimation(ui.cs_textEditttt_02, b'geometry')
    anim_tedt2.setDuration(300)
    anim_tedt2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_tedt2.setStartValue(current_geo_tedt2)
    anim_tedt2.setEndValue(target_geo_tedt2)

    anim_comb1 = QPropertyAnimation(ui.cvjb_comboBoxx_01, b'geometry')
    anim_comb1.setDuration(300)
    anim_comb1.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb1.setStartValue(current_geo_comb1)
    anim_comb1.setEndValue(target_geo_comb1)

    anim_btn01 = QPropertyAnimation(ui.cvjb_pushButon_01, b'geometry')
    anim_btn01.setDuration(300)
    anim_btn01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn01.setStartValue(current_geo_btn01)
    anim_btn01.setEndValue(target_geo_btn01)

    anim_comb2 = QPropertyAnimation(ui.cvjs_comboBoxx_01, b'geometry')
    anim_comb2.setDuration(300)
    anim_comb2.setEasingCurve(QEasingCurve.InOutCirc)
    anim_comb2.setStartValue(current_geo_comb2)
    anim_comb2.setEndValue(target_geo_comb2)

    anim_btn02 = QPropertyAnimation(ui.cvjs_pushButon_01, b'geometry')
    anim_btn02.setDuration(300)
    anim_btn02.setEasingCurve(QEasingCurve.InOutCirc)
    anim_btn02.setStartValue(current_geo_btn02)
    anim_btn02.setEndValue(target_geo_btn02)

    anim_zoo01 = QPropertyAnimation(ui.czoo_pushButon_01, b'geometry')
    anim_zoo01.setDuration(300)
    anim_zoo01.setEasingCurve(QEasingCurve.InOutCirc)
    anim_zoo01.setStartValue(current_geo_zoo01)
    anim_zoo01.setEndValue(target_geo_zoo01)

    anim_zoo02 = QPropertyAnimation(ui.czoo_pushButon_02, b'geometry')
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


def group_animation_06(ui, pushButton1, pushButton2, pushButton3, pushButton4=None):
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
        # noinspection PyUnboundLocalVariable
        anim_btn04.setStartValue(current_geo_btn04)
        # noinspection PyUnboundLocalVariable
        anim_btn04.setEndValue(target_geo_btn04)

    # 그룹에 모든 애니메이션 추가
    ui.animation_group2.addAnimation(anim_btn01)
    ui.animation_group2.addAnimation(anim_btn02)
    ui.animation_group2.addAnimation(anim_btn03)
    if pushButton4 is not None:
        # noinspection PyUnboundLocalVariable
        ui.animation_group2.addAnimation(anim_btn04)

    # 애니메이션 시작
    ui.animation_group2.start()


def group_animation_07(ui, pushButton1, pushButton2, pushButton3, pushButton4, pushButton5, pushButton6):
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


@error_decorator
def coin_opti_test_editer(ui):
    group_animation_01(ui)
    group_animation_07(ui, ui.cvc_pushButton_15, ui.cvc_pushButton_16, ui.cvc_pushButton_17, ui.cvc_pushButton_30, ui.cvc_pushButton_31, ui.cvc_pushButton_32)

    ui.czoo_pushButon_01.setText('확대(esc)')
    ui.czoo_pushButon_02.setText('확대(esc)')

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(True)
    ui.cs_textEditttt_04.setVisible(True)
    ui.cs_textEditttt_05.setVisible(True)
    ui.cs_textEditttt_06.setVisible(False)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(True)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)
    for item in ui.coin_optest_list:
        item.setVisible(True)

    ui.cvc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.cvc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_04.setText(testtext)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_07.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_rwf_test_editer(ui):
    group_animation_01(ui)
    group_animation_07(ui, ui.cvc_pushButton_18, ui.cvc_pushButton_19, ui.cvc_pushButton_20, ui.cvc_pushButton_33, ui.cvc_pushButton_34, ui.cvc_pushButton_35)

    ui.czoo_pushButon_01.setText('확대(esc)')
    ui.czoo_pushButon_02.setText('확대(esc)')

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(True)
    ui.cs_textEditttt_04.setVisible(True)
    ui.cs_textEditttt_05.setVisible(True)
    ui.cs_textEditttt_06.setVisible(False)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(True)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)
    for item in ui.coin_rwftvd_list:
        item.setVisible(True)

    ui.cvc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.cvc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_01.setVisible(False)
    ui.cvc_labellllll_04.setText(rwfttext)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_06.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_opti_ga_editer(ui):
    group_animation_02(ui)
    group_animation_06(ui, ui.cva_pushButton_01, ui.cva_pushButton_02, ui.cva_pushButton_03)

    ui.czoo_pushButon_01.setText('확대(esc)')
    ui.czoo_pushButon_02.setText('확대(esc)')

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(True)
    ui.cs_textEditttt_04.setVisible(True)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(True)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(True)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)
    for item in ui.coin_gaopti_list:
        item.setVisible(True)

    ui.cva_pushButton_04.setText('GA 변수범위 로딩(F9)')
    ui.cva_pushButton_05.setText('GA 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_04.setText(gaoptext)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_10.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_opti_vars_editer(ui):
    group_animation_03(ui)
    group_animation_06(ui, ui.cvc_pushButton_21, ui.cvc_pushButton_22, ui.cvc_pushButton_23)

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(False)
    ui.cs_textEditttt_04.setVisible(False)
    ui.cs_textEditttt_05.setVisible(True)
    ui.cs_textEditttt_06.setVisible(True)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(False)
    for item in ui.coin_optimz_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)
    for item in ui.coin_gaopti_list:
        item.setVisible(True)

    ui.cva_pushButton_04.setText('GA 변수범위 로딩')
    ui.cva_pushButton_05.setText('GA 변수범위 저장')
    ui.cvc_pushButton_03.setText('최적화 변수범위 로딩')
    ui.cvc_pushButton_04.setText('최적화 변수범위 저장')

    ui.cvc_pushButton_06.setVisible(False)
    ui.cvc_pushButton_07.setVisible(False)
    ui.cvc_pushButton_08.setVisible(False)
    ui.cvc_pushButton_27.setVisible(False)
    ui.cvc_pushButton_28.setVisible(False)
    ui.cvc_pushButton_29.setVisible(False)

    ui.cva_pushButton_01.setVisible(False)
    ui.cva_pushButton_02.setVisible(False)
    ui.cva_pushButton_03.setVisible(False)

    ui.cvc_comboBoxxx_02.setVisible(True)
    ui.cvc_lineEdittt_02.setVisible(True)
    ui.cvc_pushButton_03.setVisible(True)
    ui.cvc_pushButton_04.setVisible(True)

    ui.cvc_pushButton_11.setVisible(True)

    ui.image_label1.setVisible(True)
    ui.cvc_labellllll_04.setText(gaoptext)
    ui.cvc_labellllll_05.setText(vedittxt)
    ui.cvc_labellllll_05.setVisible(True)

    ui.cvj_pushButton_12.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_opti_editer(ui):
    group_animation_01(ui)
    group_animation_07(ui, ui.cvc_pushButton_06, ui.cvc_pushButton_07, ui.cvc_pushButton_08, ui.cvc_pushButton_27, ui.cvc_pushButton_28, ui.cvc_pushButton_29)

    ui.czoo_pushButon_01.setText('확대(esc)')
    ui.czoo_pushButon_02.setText('확대(esc)')

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(True)
    ui.cs_textEditttt_04.setVisible(True)
    ui.cs_textEditttt_05.setVisible(True)
    ui.cs_textEditttt_06.setVisible(False)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(True)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)

    ui.cvc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.cvc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_04.setText(optitext)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_08.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_vars_editer(ui):
    group_animation_04(ui)
    group_animation_06(ui, ui.cvc_pushButton_24, ui.cvc_pushButton_25, ui.cvc_pushButton_26)

    ui.cs_textEditttt_01.setVisible(True)
    ui.cs_textEditttt_02.setVisible(True)
    ui.cs_textEditttt_03.setVisible(True)
    ui.cs_textEditttt_04.setVisible(True)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(False)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(True)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)

    ui.cvjb_pushButon_01.setText('매수전략 로딩')
    ui.cvjs_pushButon_01.setText('매도전략 로딩')

    ui.cvjb_comboBoxx_01.setVisible(True)
    ui.cvjb_pushButon_01.setVisible(True)
    ui.cvjs_comboBoxx_01.setVisible(True)
    ui.cvjs_pushButon_01.setVisible(True)

    ui.cvc_lineEdittt_04.setVisible(False)
    ui.cvc_pushButton_13.setVisible(False)
    ui.cvc_lineEdittt_05.setVisible(False)
    ui.cvc_pushButton_14.setVisible(False)

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_04.setText(optitext)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_13.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def change_pre_button_edit(ui):
    if ui.cvj_pushButton_01.isVisible():
        ui.cvj_pushButton_09.setStyleSheet(style_bc_bd)
    elif ui.cvc_pushButton_32.isVisible():
        ui.cvj_pushButton_07.setStyleSheet(style_bc_bd)
    elif ui.cvc_pushButton_35.isVisible():
        ui.cvj_pushButton_06.setStyleSheet(style_bc_bd)
    elif ui.cva_pushButton_03.isVisible():
        ui.cvj_pushButton_10.setStyleSheet(style_bc_bd)
    elif ui.cvo_pushButton_08.isVisible():
        ui.cvj_pushButton_11.setStyleSheet(style_bc_bd)
    elif ui.cvc_pushButton_23.isVisible():
        ui.cvj_pushButton_12.setStyleSheet(style_bc_bd)
    elif ui.cvc_pushButton_26.isVisible():
        ui.cvj_pushButton_13.setStyleSheet(style_bc_bd)
    elif ui.cvc_pushButton_29.isVisible():
        ui.cvj_pushButton_08.setStyleSheet(style_bc_bd)


@error_decorator
def coin_backtest_log(ui):
    change_pre_button_edit(ui)

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(False)
    ui.cs_textEditttt_04.setVisible(False)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(False)
    ui.cs_textEditttt_07.setVisible(False)
    ui.cs_textEditttt_08.setVisible(False)

    ui.cs_textEditttt_09.setGeometry(7, 10, 1000, 1313 if ui.extend_window else 703)
    ui.cs_progressBar_01.setGeometry(7, 1328 if ui.extend_window else 718, 830, 30)
    ui.cs_pushButtonn_08.setGeometry(842, 1328 if ui.extend_window else 718, 165, 30)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(True)

    ui.cs_pushButtonn_08.setStyleSheet(style_bc_by)
    ui.cvj_pushButton_14.setFocus()
    ui.cvj_pushButton_14.setStyleSheet(style_bc_dk)
    ui.cvj_pushButton_15.setStyleSheet(style_bc_bs)
    change_version_button_color(ui)


@error_decorator
def coin_backtest_detail(ui):
    change_pre_button_edit(ui)

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(False)
    ui.cs_textEditttt_04.setVisible(False)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(False)
    ui.cs_textEditttt_07.setVisible(False)
    ui.cs_textEditttt_08.setVisible(False)

    ui.cs_tableWidget_01.setGeometry(7, 40, 1000, 1318 if ui.extend_window else 713)
    if (ui.extend_window and ui.cs_tableWidget_01.rowCount() < 60) or \
            (not ui.extend_window and ui.cs_tableWidget_01.rowCount() < 32):
        ui.cs_tableWidget_01.setRowCount(60 if ui.extend_window else 32)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(True)

    ui.cvj_pushButton_15.setFocus()
    ui.cvj_pushButton_15.setStyleSheet(style_bc_dk)
    ui.cvj_pushButton_14.setStyleSheet(style_bc_bs)
    change_version_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_stg_editer(ui):
    group_animation_05(ui)
    group_animation_06(ui, ui.cvj_pushButton_01, ui.cvj_pushButton_02, ui.cvj_pushButton_03, ui.cvj_pushButton_04)

    ui.czoo_pushButon_01.setText('확대(esc)')
    ui.czoo_pushButon_02.setText('확대(esc)')

    ui.cs_textEditttt_01.setVisible(True)
    ui.cs_textEditttt_02.setVisible(True)
    ui.cs_textEditttt_03.setVisible(False)
    ui.cs_textEditttt_04.setVisible(False)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(False)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_optimz_list:
        item.setVisible(False)
    for item in ui.coin_period_list:
        item.setVisible(False)
    for item in ui.coin_opcond_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(True)
    for item in ui.coin_esczom_list:
        item.setVisible(True)
    for item in ui.coin_backte_list:
        item.setVisible(True)

    ui.cvjb_pushButon_01.setText('매수전략 로딩(F1)')
    ui.cvjs_pushButon_01.setText('매도전략 로딩(F5)')

    ui.image_label1.setVisible(False)
    ui.cvc_labellllll_05.setVisible(False)

    ui.cvj_pushButton_09.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_cond_editer(ui):
    group_animation_06(ui, ui.cvo_pushButton_05, ui.cvo_pushButton_06, ui.cvo_pushButton_07)

    ui.cs_textEditttt_01.setVisible(False)
    ui.cs_textEditttt_02.setVisible(False)
    ui.cs_textEditttt_03.setVisible(False)
    ui.cs_textEditttt_04.setVisible(False)
    ui.cs_textEditttt_05.setVisible(False)
    ui.cs_textEditttt_06.setVisible(False)

    ui.cs_textEditttt_07.setGeometry(7, 10, 497, 1347 if ui.extend_window else 740)
    ui.cs_textEditttt_08.setGeometry(509, 10, 497, 1347 if ui.extend_window else 740)

    for item in ui.coin_version_list:
        item.setVisible(False)
    for item in ui.coin_esczom_list:
        item.setVisible(False)
    for item in ui.coin_backte_list:
        item.setVisible(False)
    for item in ui.coin_detail_list:
        item.setVisible(False)
    for item in ui.coin_baklog_list:
        item.setVisible(False)
    for item in ui.coin_gaopti_list:
        item.setVisible(False)
    for item in ui.coin_optest_list:
        item.setVisible(False)
    for item in ui.coin_rwftvd_list:
        item.setVisible(False)
    for item in ui.coin_datedt_list:
        item.setVisible(False)
    for item in ui.coin_varsedit_list:
        item.setVisible(False)
    for item in ui.coin_areaedit_list:
        item.setVisible(False)
    for item in ui.coin_optimz_list:
        item.setVisible(True)
    for item in ui.coin_period_list:
        item.setVisible(True)
    for item in ui.coin_opcond_list:
        item.setVisible(True)

    ui.cvc_lineEdittt_04.setVisible(False)
    ui.cvc_lineEdittt_05.setVisible(False)
    ui.cvc_pushButton_13.setVisible(False)
    ui.cvc_pushButton_14.setVisible(False)

    ui.cvc_comboBoxxx_08.setVisible(False)
    ui.cvc_lineEdittt_03.setVisible(False)
    ui.cvc_pushButton_09.setVisible(False)
    ui.cvc_pushButton_10.setVisible(False)

    ui.cvc_comboBoxxx_02.setVisible(False)
    ui.cvc_lineEdittt_02.setVisible(False)
    ui.cvc_pushButton_03.setVisible(False)
    ui.cvc_pushButton_04.setVisible(False)

    ui.image_label1.setVisible(True)
    ui.cvc_labellllll_01.setVisible(False)
    ui.cvc_labellllll_04.setText(condtext)
    ui.cvc_labellllll_05.setText(cedittxt)
    ui.cvc_labellllll_05.setVisible(True)

    ui.cvj_pushButton_11.setFocus()
    change_svj_button_color(ui)
    change_version_button_color(ui)


@error_decorator
def coin_backtest_start(ui):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        back_club = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                QApplication.keyboardModifiers() & Qt.AltModifier) else False
        if back_club and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진을 먼저 실행하십시오.\n')
            return
        if not back_club and (not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier)):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday  = ui.cvjb_dateEditt_01.date().toString('yyyyMMdd')
        endday    = ui.cvjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.cvjb_lineEditt_02.text()
        endtime   = ui.cvjb_lineEditt_03.text()
        betting   = ui.cvjb_lineEditt_04.text()
        avgtime   = ui.cvjb_lineEditt_05.text()
        buystg    = ui.cvjb_comboBoxx_01.currentText()
        sellstg   = ui.cvjs_comboBoxx_01.currentText()
        bl = True if ui.dict_set['블랙리스트추가'] else False

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (startday, endday, starttime, endtime, betting, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '백테스트'))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        ui.proc_backtester_bs = Process(
            target=BackTest,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                  ui.back_sques, '백테스트', gubun, ui.dict_set, betting, avgtime, startday, endday, starttime,
                  endtime, buystg, sellstg, None, ui.back_count, bl, False, back_club)
        )
        ui.proc_backtester_bs.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_backfinder_start(ui):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday  = ui.cvjb_dateEditt_01.date().toString('yyyyMMdd')
        endday    = ui.cvjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.cvjb_lineEditt_02.text()
        endtime   = ui.cvjb_lineEditt_03.text()
        avgtime   = ui.cvjb_lineEditt_05.text()
        buystg    = ui.cvjb_comboBoxx_01.currentText()

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (startday, endday, starttime, endtime, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if buystg == '':
            QMessageBox.critical(ui, '오류 알림', '매수전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if 'self.tickcols' not in ui.cs_textEditttt_01.toPlainText():
            QMessageBox.critical(ui, '오류 알림', '현재 매수전략이 백파인더용이 아닙니다.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '백파인더'))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        ui.proc_backtester_bf = Process(
            target=BackFinder,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, gubun,
                  ui.dict_set, avgtime, startday, endday, starttime, endtime, buystg, ui.back_count)
        )
        ui.proc_backtester_bf.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_backfinder_sample(ui):
    if ui.cs_textEditttt_01.isVisible():
        ui.cs_textEditttt_01.clear()
        ui.cs_textEditttt_02.clear()
        ui.cs_textEditttt_01.append(example_finder if ui.dict_set['거래소'] == '업비트' else example_finder_future)


@error_decorator
def coin_opti_start(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (not (QApplication.keyboardModifiers() & Qt.ShiftModifier) and
                                      not (QApplication.keyboardModifiers() & Qt.AltModifier) and
                                      (QApplication.keyboardModifiers() & Qt.ControlModifier)):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        randomopti  = True if not (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                        QApplication.keyboardModifiers() & Qt.AltModifier) else False
        onlybuy     = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                        QApplication.keyboardModifiers() & Qt.ShiftModifier) else False
        onlysell    = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                        QApplication.keyboardModifiers() & Qt.AltModifier) else False
        starttime   = ui.cvjb_lineEditt_02.text()
        endtime     = ui.cvjb_lineEditt_03.text()
        betting     = ui.cvjb_lineEditt_04.text()
        buystg      = ui.cvc_comboBoxxx_01.currentText()
        sellstg     = ui.cvc_comboBoxxx_08.currentText()
        optivars    = ui.cvc_comboBoxxx_02.currentText()
        ccount      = ui.cvc_comboBoxxx_06.currentText()
        optistd     = ui.cvc_comboBoxxx_07.currentText()
        weeks_train = ui.cvc_comboBoxxx_03.currentText()
        weeks_valid = ui.cvc_comboBoxxx_04.currentText()
        weeks_test  = ui.cvc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
        optunasampl = ui.op_comboBoxxxx_01.currentText()
        optunafixv  = ui.op_lineEditttt_01.text()
        optunacount = ui.op_lineEditttt_02.text()
        optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, None, ccount, ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, False, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday, optunasampl,
            optunafixv, optunacount, optunaautos, randomopti, onlybuy, onlysell
        ))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        if back_name == '최적화O':
            ui.proc_backtester_o = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_o.start()
        elif back_name == '최적화OV':
            ui.proc_backtester_ov = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ov.start()
        elif back_name == '최적화OVC':
            ui.proc_backtester_ovc = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ovc.start()
        elif back_name == '최적화B':
            ui.proc_backtester_b = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_b.start()
        elif back_name == '최적화BV':
            ui.proc_backtester_bv = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_bv.start()
        elif back_name == '최적화BVC':
            ui.proc_backtester_bvc = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_bvc.start()
        elif back_name == '최적화OT':
            ui.proc_backtester_ot = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ot.start()
        elif back_name == '최적화OVT':
            ui.proc_backtester_ovt = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ovt.start()
        elif back_name == '최적화OVCT':
            ui.proc_backtester_ovct = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ovct.start()
        elif back_name == '최적화BT':
            ui.proc_backtester_bt = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_bt.start()
        elif back_name == '최적화BVT':
            ui.proc_backtester_bvt = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_bvt.start()
        else:
            ui.proc_backtester_bvct = Process(
                target=Optimize,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_bvct.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_opti_rwft_start(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        randomopti  = True if (QApplication.keyboardModifiers() & Qt.AltModifier) and 'B' not in back_name else False
        startday    = ui.cvjb_dateEditt_01.date().toString('yyyyMMdd')
        endday      = ui.cvjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime   = ui.cvjb_lineEditt_02.text()
        endtime     = ui.cvjb_lineEditt_03.text()
        betting     = ui.cvjb_lineEditt_04.text()
        buystg      = ui.cvc_comboBoxxx_01.currentText()
        sellstg     = ui.cvc_comboBoxxx_08.currentText()
        optivars    = ui.cvc_comboBoxxx_02.currentText()
        ccount      = ui.cvc_comboBoxxx_06.currentText()
        optistd     = ui.cvc_comboBoxxx_07.currentText()
        weeks_train = ui.cvc_comboBoxxx_03.currentText()
        weeks_valid = ui.cvc_comboBoxxx_04.currentText()
        weeks_test  = ui.cvc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if weeks_train == 'ALL':
            QMessageBox.critical(ui, '오류 알림', '전진분석 학습기간은 전체를 선택할 수 없습니다.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '전진분석'))

        ui.backQ.put((
            betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, None, ccount,
            ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, False, None, None, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday,
            randomopti
        ))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        if back_name == '전진분석OR':
            ui.proc_backtester_or = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_or.start()
        elif back_name == '전진분석ORV':
            ui.proc_backtester_orv = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_orv.start()
        elif back_name == '전진분석ORVC':
            ui.proc_backtester_orvc = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_orvc.start()
        elif back_name == '전진분석BR':
            ui.proc_backtester_br = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_br.start()
        elif back_name == '전진분석BRV':
            ui.proc_backtester_brv = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_brv.start()
        else:
            ui.proc_backtester_brvc = Process(
                target=RollingWalkForwardTest,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_brvc.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_opti_ga_start(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime   = ui.cvjb_lineEditt_02.text()
        endtime     = ui.cvjb_lineEditt_03.text()
        betting     = ui.cvjb_lineEditt_04.text()
        buystg      = ui.cvc_comboBoxxx_01.currentText()
        sellstg     = ui.cvc_comboBoxxx_08.currentText()
        optivars    = ui.cva_comboBoxxx_01.currentText()
        optistd     = ui.cvc_comboBoxxx_07.currentText()
        weeks_train = ui.cvc_comboBoxxx_03.currentText()
        weeks_valid = ui.cvc_comboBoxxx_04.currentText()
        weeks_test  = ui.cvc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', 'GA최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, None, ui.dict_set['최적화기준값제한'], optistd,
            ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        if back_name == '최적화OG':
            ui.proc_backtester_og = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_og.start()
        elif back_name == '최적화OGV':
            ui.proc_backtester_ogv = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ogv.start()
        else:
            ui.proc_backtester_ogvc = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                      ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ogvc.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_opti_cond_start(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('코인')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime   = ui.cvjb_lineEditt_02.text()
        endtime     = ui.cvjb_lineEditt_03.text()
        betting     = ui.cvjb_lineEditt_04.text()
        avgtime     = ui.cvjb_lineEditt_05.text()
        buystg      = ui.cvo_comboBoxxx_01.currentText()
        sellstg     = ui.cvo_comboBoxxx_02.currentText()
        bcount      = ui.cvo_lineEdittt_03.text()
        scount      = ui.cvo_lineEdittt_04.text()
        rcount      = ui.cvo_lineEdittt_05.text()
        optistd     = ui.cvc_comboBoxxx_07.currentText()
        weeks_train = ui.cvc_comboBoxxx_03.currentText()
        weeks_valid = ui.cvc_comboBoxxx_04.currentText()
        weeks_test  = ui.cvc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

        if weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (starttime, endtime, betting, avgtime, bcount, scount, rcount):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '조건을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '조건최적화'))

        ui.backQ.put((
            betting, avgtime, starttime, endtime, buystg, sellstg, ui.dict_set['최적화기준값제한'], optistd, bcount,
            scount, rcount, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        gubun = 'C' if ui.dict_set['거래소'] == '업비트' else 'CF'
        if back_name == '최적화OC':
            ui.proc_backtester_oc = Process(
                target=OptimizeConditions,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                      ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_oc.start()
        elif back_name == '최적화OCV':
            ui.proc_backtester_ocv = Process(
                target=OptimizeConditions,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                      ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ocv.start()
        else:
            ui.proc_backtester_ocvc = Process(
                target=OptimizeConditions,
                args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                      ui.multi, back_name, gubun, ui.dict_set)
            )
            ui.proc_backtester_ocvc.start()
        ui.CoinBacktestLog()
        ui.cs_progressBar_01.setValue(0)
        ui.csicon_alert = True


@error_decorator
def coin_optivars_to_gavars(ui):
    opti_vars_text = ui.cs_textEditttt_05.toPlainText()
    if opti_vars_text:
        ga_vars_text = ui.GetOptivarsToGavars(opti_vars_text)
        ui.cs_textEditttt_06.clear()
        ui.cs_textEditttt_06.append(ga_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 최적화 범위 코드가 공백 상태입니다.\n최적화 범위 코드를 작성하거나 로딩하십시오.\n')


@error_decorator
def coin_gavars_to_optivars(ui):
    ga_vars_text = ui.cs_textEditttt_06.toPlainText()
    if ga_vars_text:
        opti_vars_text = ui.GetGavarsToOptivars(ga_vars_text)
        ui.cs_textEditttt_05.clear()
        ui.cs_textEditttt_05.append(opti_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 GA 범위 코드가 공백 상태입니다.\nGA 범위 코드를 작성하거나 로딩하십시오.\n')


@error_decorator
def coin_stg_vars_change(ui):
    buystg  = ui.cs_textEditttt_01.toPlainText()
    sellstg = ui.cs_textEditttt_02.toPlainText()
    buystg_str, sellstg_str = ui.GetStgtxtToVarstxt(buystg, sellstg)
    ui.cs_textEditttt_03.clear()
    ui.cs_textEditttt_04.clear()
    ui.cs_textEditttt_03.append(buystg_str)
    ui.cs_textEditttt_04.append(sellstg_str)


@error_decorator
def coin_stgvars_key_sort(ui):
    optivars = ui.cs_textEditttt_05.toPlainText()
    gavars   = ui.cs_textEditttt_06.toPlainText()
    optivars_str, gavars_str = ui.GetStgtxtSort2(optivars, gavars)
    ui.cs_textEditttt_05.clear()
    ui.cs_textEditttt_06.clear()
    ui.cs_textEditttt_05.append(optivars_str)
    ui.cs_textEditttt_06.append(gavars_str)


@error_decorator
def coin_optivars_key_sort(ui):
    buystg  = ui.cs_textEditttt_03.toPlainText()
    sellstg = ui.cs_textEditttt_04.toPlainText()
    buystg_str, sellstg_str = ui.GetStgtxtSort(buystg, sellstg)
    ui.cs_textEditttt_03.clear()
    ui.cs_textEditttt_04.clear()
    ui.cs_textEditttt_03.append(buystg_str)
    ui.cs_textEditttt_04.append(sellstg_str)


@error_decorator
def change_svj_button_color(ui):
    for button in ui.coin_editer_list:
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_bs)


@error_decorator
def change_version_button_color(ui):
    for button in ui.coin_load_list:
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_st)
