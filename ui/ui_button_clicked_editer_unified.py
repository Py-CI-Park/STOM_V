
from ui.ui_vars_change import *
from multiprocessing import Process
from backtest.optimiz import Optimize
from backtest.backtest import BackTest
from backtest.backfinder import BackFinder
from utility.static import error_decorator
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.ui_process_alive import backtest_process_alive
from backtest.optimiz_conditions import OptimizeConditions
from backtest.rolling_walk_forward_test import RollingWalkForwardTest
from backtest.optimiz_genetic_algorithm import OptimizeGeneticAlgorithm
from ui.set_style import style_bc_by, style_bc_dk, style_bc_bs, style_bc_bd, style_bc_st
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect
from ui.set_text import testtext, rwfttext, gaoptext, vedittxt, optitext, condtext, cedittxt, example_finder, \
    example_finder_future


# =============================================================================
# UI 타입별 설정 매핑 (코인/주식 공통)
# =============================================================================
UI_EDITER_CONFIG = {
    'coin': {
        'prefix': 'c',
        'widgets': {
            'text_01': 'cs_textEditttt_01', 'text_02': 'cs_textEditttt_02',
            'text_03': 'cs_textEditttt_03', 'text_04': 'cs_textEditttt_04',
            'text_05': 'cs_textEditttt_05', 'text_06': 'cs_textEditttt_06',
            'text_07': 'cs_textEditttt_07', 'text_08': 'cs_textEditttt_08',
            'text_09': 'cs_textEditttt_09', 'progress': 'cs_progressBar_01',
            'table': 'cs_tableWidget_01', 'push_08': 'cs_pushButtonn_08',
            'combo_buy': 'cvjb_comboBoxx_01', 'line_buy': 'cvjb_lineEditt_01',
            'push_buy': 'cvjb_pushButon_01', 'combo_sell': 'cvjs_comboBoxx_01',
            'line_sell': 'cvjs_lineEditt_01', 'push_sell': 'cvjs_pushButon_01',
            'combo_opti': 'cvc_comboBoxxx_01', 'combo_vars': 'cvc_comboBoxxx_02',
            'line_vars_02': 'cvc_lineEdittt_02', 'line_vars_04': 'cvc_lineEdittt_03',
            'line_vars_05': 'cvc_lineEdittt_04', 'push_03': 'cvc_pushButton_03',
            'push_04': 'cvc_pushButton_04', 'push_05': 'cvc_pushButton_05',
            'push_06': 'cvc_pushButton_06', 'push_07': 'cvc_pushButton_07',
            'push_08_v': 'cvc_pushButton_08', 'push_09': 'cvc_pushButton_09',
            'push_10': 'cvc_pushButton_10', 'push_11': 'cvc_pushButton_11',
            'push_12': 'cvc_pushButton_12', 'push_13': 'cvc_pushButton_13',
            'push_14': 'cvc_pushButton_14', 'push_15': 'cvc_pushButton_15',
            'push_16': 'cvc_pushButton_16', 'push_17': 'cvc_pushButton_17',
            'push_18': 'cvc_pushButton_18', 'push_19': 'cvc_pushButton_19',
            'push_20': 'cvc_pushButton_20', 'push_21': 'cvc_pushButton_21',
            'push_22': 'cvc_pushButton_22', 'push_23': 'cvc_pushButton_23',
            'push_24': 'cvc_pushButton_24', 'push_25': 'cvc_pushButton_25',
            'push_26': 'cvc_pushButton_26', 'push_27': 'cvc_pushButton_27',
            'push_28': 'cvc_pushButton_28', 'push_29': 'cvc_pushButton_29',
            'push_30': 'cvc_pushButton_30', 'push_31': 'cvc_pushButton_31',
            'push_32': 'cvc_pushButton_32', 'push_33': 'cvc_pushButton_33',
            'push_34': 'cvc_pushButton_34', 'push_35': 'cvc_pushButton_35',
            'combo_ga': 'cva_comboBoxxx_01', 'line_ga': 'cva_lineEdittt_01',
            'push_ga_01': 'cva_pushButton_01', 'push_ga_02': 'cva_pushButton_02',
            'push_ga_03': 'cva_pushButton_03', 'push_ga_04': 'cva_pushButton_04',
            'push_ga_05': 'cva_pushButton_05', 'combo_cond_buy': 'cvo_comboBoxxx_01',
            'line_cond_buy': 'cvo_lineEditt_01', 'combo_cond_sell': 'cvo_comboBoxxx_02',
            'line_cond_sell': 'cvo_lineEditt_02', 'push_cond_05': 'cvo_pushButton_05',
            'push_cond_06': 'cvo_pushButton_06', 'push_cond_07': 'cvo_pushButton_07',
            'push_cond_08': 'cvo_pushButton_08', 'zoo_01': 'czoo_pushButon_01',
            'zoo_02': 'czoo_pushButon_02', 'label_01': 'cvc_labellllll_01',
            'label_04': 'cvc_labellllll_04', 'label_05': 'cvc_labellllll_05',
            'combo_std': 'cvc_comboBoxxx_07', 'combo_week_train': 'cvc_comboBoxxx_03',
            'combo_week_valid': 'cvc_comboBoxxx_04', 'combo_week_test': 'cvc_comboBoxxx_05',
            'combo_sellstg': 'cvc_comboBoxxx_08', 'line_sellstg': 'cvc_lineEdittt_03',
            'date_start': 'cvjb_dateEditt_01', 'date_end': 'cvjb_dateEditt_02',
            'line_start': 'cvjb_lineEditt_02', 'line_end': 'cvjb_lineEditt_03',
            'line_betting': 'cvjb_lineEditt_04', 'line_avg': 'cvjb_lineEditt_05',
            'combo_ccount': 'cvc_comboBoxxx_06', 'sj_push_01': 'cvj_pushButton_01',
            'sj_push_02': 'cvj_pushButton_02', 'sj_push_03': 'cvj_pushButton_03',
            'sj_push_04': 'cvj_pushButton_04', 'sj_push_06': 'cvj_pushButton_06',
            'sj_push_07': 'cvj_pushButton_07', 'sj_push_08': 'cvj_pushButton_08',
            'sj_push_09': 'cvj_pushButton_09', 'sj_push_10': 'cvj_pushButton_10',
            'sj_push_11': 'cvj_pushButton_11', 'sj_push_12': 'cvj_pushButton_12',
            'sj_push_13': 'cvj_pushButton_13', 'sj_push_14': 'cvj_pushButton_14',
            'sj_push_15': 'cvj_pushButton_15', 'line_cond_03': 'cvo_lineEditt_03',
            'line_cond_04': 'cvo_lineEditt_04', 'line_cond_05': 'cvo_lineEditt_05',
        },
        'lists': {
            'version': 'coin_version_list', 'detail': 'coin_detail_list',
            'baklog': 'coin_baklog_list', 'datedt': 'coin_datedt_list',
            'backte': 'coin_backte_list', 'opcond': 'coin_opcond_list',
            'gaopti': 'coin_gaopti_list', 'optest': 'coin_optest_list',
            'rwftvd': 'coin_rwftvd_list', 'varsedit': 'coin_varsedit_list',
            'areaedit': 'coin_areaedit_list', 'esczom': 'coin_esczom_list',
            'optimz': 'coin_optimz_list', 'period': 'coin_period_list',
            'editer': 'coin_editer_list', 'load': 'coin_load_list',
        },
        'gubun_fn': lambda ui: 'C' if '업비트' in ui.dict_set['거래소'] else 'CF',
        'market_type': '코인',
        'exchange_key': '거래소',
        'icon_alert': 'csicon_alert',
        'dict_cn': None,
    },
    'stock': {
        'prefix': 's',
        'widgets': {
            'text_01': 'ss_textEditttt_01', 'text_02': 'ss_textEditttt_02',
            'text_03': 'ss_textEditttt_03', 'text_04': 'ss_textEditttt_04',
            'text_05': 'ss_textEditttt_05', 'text_06': 'ss_textEditttt_06',
            'text_07': 'ss_textEditttt_07', 'text_08': 'ss_textEditttt_08',
            'text_09': 'ss_textEditttt_09', 'progress': 'ss_progressBar_01',
            'table': 'ss_tableWidget_01', 'push_08': 'ss_pushButtonn_08',
            'combo_buy': 'svjb_comboBoxx_01', 'line_buy': 'svjb_lineEditt_01',
            'push_buy': 'svjb_pushButon_01', 'combo_sell': 'svjs_comboBoxx_01',
            'line_sell': 'svjs_lineEditt_01', 'push_sell': 'svjs_pushButon_01',
            'combo_opti': 'svc_comboBoxxx_01', 'combo_vars': 'svc_comboBoxxx_02',
            'line_vars_02': 'svc_lineEdittt_02', 'line_vars_04': 'svc_lineEdittt_04',
            'line_vars_05': 'svc_lineEdittt_05', 'push_03': 'svc_pushButton_03',
            'push_04': 'svc_pushButton_04', 'push_05': 'svc_pushButton_05',
            'push_06': 'svc_pushButton_06', 'push_07': 'svc_pushButton_07',
            'push_08_v': 'svc_pushButton_08', 'push_09': 'svc_pushButton_09',
            'push_10': 'svc_pushButton_10', 'push_11': 'svc_pushButton_11',
            'push_12': 'svc_pushButton_12', 'push_13': 'svc_pushButton_13',
            'push_14': 'svc_pushButton_14', 'push_15': 'svc_pushButton_15',
            'push_16': 'svc_pushButton_16', 'push_17': 'svc_pushButton_17',
            'push_18': 'svc_pushButton_18', 'push_19': 'svc_pushButton_19',
            'push_20': 'svc_pushButton_20', 'push_21': 'svc_pushButton_21',
            'push_22': 'svc_pushButton_22', 'push_23': 'svc_pushButton_23',
            'push_24': 'svc_pushButton_24', 'push_25': 'svc_pushButton_25',
            'push_26': 'svc_pushButton_26', 'push_27': 'svc_pushButton_27',
            'push_28': 'svc_pushButton_28', 'push_29': 'svc_pushButton_29',
            'push_30': 'svc_pushButton_30', 'push_31': 'svc_pushButton_31',
            'push_32': 'svc_pushButton_32', 'push_33': 'svc_pushButton_33',
            'push_34': 'svc_pushButton_34', 'push_35': 'svc_pushButton_35',
            'combo_ga': 'sva_comboBoxxx_01', 'line_ga': 'sva_lineEdittt_01',
            'push_ga_01': 'sva_pushButton_01', 'push_ga_02': 'sva_pushButton_02',
            'push_ga_03': 'sva_pushButton_03', 'push_ga_04': 'sva_pushButton_04',
            'push_ga_05': 'sva_pushButton_05', 'combo_cond_buy': 'svo_comboBoxxx_01',
            'line_cond_buy': 'svo_lineEditt_01', 'combo_cond_sell': 'svo_comboBoxxx_02',
            'line_cond_sell': 'svo_lineEditt_02', 'push_cond_05': 'svo_pushButton_05',
            'push_cond_06': 'svo_pushButton_06', 'push_cond_07': 'svo_pushButton_07',
            'push_cond_08': 'svo_pushButton_08', 'zoo_01': 'szoo_pushButon_01',
            'zoo_02': 'szoo_pushButon_02', 'label_01': 'svc_labellllll_01',
            'label_04': 'svc_labellllll_04', 'label_05': 'svc_labellllll_05',
            'combo_std': 'svc_comboBoxxx_07', 'combo_week_train': 'svc_comboBoxxx_03',
            'combo_week_valid': 'svc_comboBoxxx_04', 'combo_week_test': 'svc_comboBoxxx_05',
            'combo_sellstg': 'svc_comboBoxxx_08', 'line_sellstg': 'svc_lineEdittt_03',
            'date_start': 'svjb_dateEditt_01', 'date_end': 'svjb_dateEditt_02',
            'line_start': 'svjb_lineEditt_02', 'line_end': 'svjb_lineEditt_03',
            'line_betting': 'svjb_lineEditt_04', 'line_avg': 'svjb_lineEditt_05',
            'combo_ccount': 'svc_comboBoxxx_06', 'sj_push_01': 'svj_pushButton_01',
            'sj_push_02': 'svj_pushButton_02', 'sj_push_03': 'svj_pushButton_03',
            'sj_push_04': 'svj_pushButton_04', 'sj_push_06': 'svj_pushButton_06',
            'sj_push_07': 'svj_pushButton_07', 'sj_push_08': 'svj_pushButton_08',
            'sj_push_09': 'svj_pushButton_09', 'sj_push_10': 'svj_pushButton_10',
            'sj_push_11': 'svj_pushButton_11', 'sj_push_12': 'svj_pushButton_12',
            'sj_push_13': 'svj_pushButton_13', 'sj_push_14': 'svj_pushButton_14',
            'sj_push_15': 'svj_pushButton_15', 'line_cond_03': 'svo_lineEditt_03',
            'line_cond_04': 'svo_lineEditt_04', 'line_cond_05': 'svo_lineEditt_05',
        },
        'lists': {
            'version': 'stock_version_list', 'detail': 'stock_detail_list',
            'baklog': 'stock_baklog_list', 'datedt': 'stock_datedt_list',
            'backte': 'stock_backte_list', 'opcond': 'stock_opcond_list',
            'gaopti': 'stock_gaopti_list', 'optest': 'stock_optest_list',
            'rwftvd': 'stock_rwftvd_list', 'varsedit': 'stock_varsedit_list',
            'areaedit': 'stock_areaedit_list', 'esczom': 'stock_esczom_list',
            'optimz': 'stock_optimz_list', 'period': 'stock_period_list',
            'editer': 'stock_editer_list', 'load': 'stock_load_list',
        },
        'gubun_fn': lambda ui: 'S' if '키움증권' in ui.dict_set['증권사'] else 'SF',
        'market_type': '주식',
        'exchange_key': '증권사',
        'icon_alert': 'ssicon_alert',
        'dict_cn': 'dict_cn',
    }
}


# =============================================================================
# 헬퍼 함수
# =============================================================================
def _get_widget(ui, ui_type, widget_key):
    """설정에서 위젯 객체를 가져옴"""
    # noinspection PyUnresolvedReferences
    widget_name = UI_EDITER_CONFIG[ui_type]['widgets'][widget_key]
    return getattr(ui, widget_name)


def _get_list(ui, ui_type, list_key):
    """설정에서 리스트 객체를 가져옴"""
    # noinspection PyUnresolvedReferences
    list_name = UI_EDITER_CONFIG[ui_type]['lists'][list_key]
    return getattr(ui, list_name)


def _set_text_edits_visible(ui, ui_type, visibility_map):
    """text_edit들의 visible 상태를 일괄 설정"""
    for key, visible in visibility_map.items():
        widget = _get_widget(ui, ui_type, f'text_{key}')
        widget.setVisible(visible)


def _set_lists_visible(ui, ui_type, hidden_lists, visible_lists):
    """리스트들의 visible 상태를 일괄 설정"""
    for list_key in hidden_lists:
        for item in _get_list(ui, ui_type, list_key):
            item.setVisible(False)
    for list_key in visible_lists:
        for item in _get_list(ui, ui_type, list_key):
            item.setVisible(True)


def _set_widget_text(ui, ui_type, widget_key, text):
    """위젯 텍스트 설정"""
    widget = _get_widget(ui, ui_type, widget_key)
    widget.setText(text)


def _set_widget_visible(ui, ui_type, widget_key, visible):
    """위젯 visible 설정"""
    widget = _get_widget(ui, ui_type, widget_key)
    widget.setVisible(visible)


def _set_focus(ui, ui_type, widget_key):
    """위젯에 포커스 설정"""
    widget = _get_widget(ui, ui_type, widget_key)
    widget.setFocus()


def _set_geometry(ui, ui_type, widget_key, x, y, w, h):
    """위젯 geometry 설정"""
    widget = _get_widget(ui, ui_type, widget_key)
    widget.setGeometry(x, y, w, h)


def _get_config(ui_type):
    """UI 타입별 설정 반환"""
    return UI_EDITER_CONFIG[ui_type]


def _get_gubun(ui, ui_type):
    """구분값 반환"""
    return UI_EDITER_CONFIG[ui_type]['gubun_fn'](ui)


# =============================================================================
# 그룹 애니메이션 함수들 (설정 기반 공통)
# =============================================================================
def group_animation_01(ui, ui_type):
    """opti_test_editer, rwf_test_editer, opti_editer용 그룹 애니메이션 (공통)"""
    # 위젯들의 현재 지오메트리 저장
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    text_05 = _get_widget(ui, ui_type, 'text_05')
    combo_vars = _get_widget(ui, ui_type, 'combo_vars')
    line_vars = _get_widget(ui, ui_type, 'line_vars_02')
    push_03 = _get_widget(ui, ui_type, 'push_03')
    push_04 = _get_widget(ui, ui_type, 'push_04')
    zoo_01 = _get_widget(ui, ui_type, 'zoo_01')
    zoo_02 = _get_widget(ui, ui_type, 'zoo_02')

    current_geo_tedt1 = text_03.geometry()
    current_geo_tedt2 = text_04.geometry()
    current_geo_tedt3 = text_05.geometry()
    current_geo_comb1 = combo_vars.geometry()
    current_geo_line1 = line_vars.geometry()
    current_geo_btn01 = push_03.geometry()
    current_geo_btn02 = push_04.geometry()
    current_geo_zoo01 = zoo_01.geometry()
    current_geo_zoo02 = zoo_02.geometry()

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
    for widget, start, end in [
        (text_03, current_geo_tedt1, target_geo_tedt1),
        (text_04, current_geo_tedt2, target_geo_tedt2),
        (text_05, current_geo_tedt3, target_geo_tedt3),
        (combo_vars, current_geo_comb1, target_geo_comb1),
        (line_vars, current_geo_line1, target_geo_line1),
        (push_03, current_geo_btn01, target_geo_btn01),
        (push_04, current_geo_btn02, target_geo_btn02),
        (zoo_01, current_geo_zoo01, target_geo_zoo01),
        (zoo_02, current_geo_zoo02, target_geo_zoo02),
    ]:
        anim = QPropertyAnimation(widget, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group.addAnimation(anim)

    # 애니메이션 시작
    ui.animation_group.start()


def group_animation_02(ui, ui_type):
    """opti_ga_editer용 그룹 애니메이션 (공통)"""
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    text_06 = _get_widget(ui, ui_type, 'text_06')
    combo_vars = _get_widget(ui, ui_type, 'combo_vars')
    line_vars = _get_widget(ui, ui_type, 'line_vars_02')
    push_03 = _get_widget(ui, ui_type, 'push_03')
    push_04 = _get_widget(ui, ui_type, 'push_04')
    combo_ga = _get_widget(ui, ui_type, 'combo_ga')
    line_ga = _get_widget(ui, ui_type, 'line_ga')
    push_ga_04 = _get_widget(ui, ui_type, 'push_ga_04')
    push_ga_05 = _get_widget(ui, ui_type, 'push_ga_05')
    zoo_01 = _get_widget(ui, ui_type, 'zoo_01')
    zoo_02 = _get_widget(ui, ui_type, 'zoo_02')

    current_geo_tedt1 = text_03.geometry()
    current_geo_tedt2 = text_04.geometry()
    current_geo_tedt3 = text_06.geometry()
    current_geo_comb1 = combo_vars.geometry()
    current_geo_line1 = line_vars.geometry()
    current_geo_btn01 = push_03.geometry()
    current_geo_btn02 = push_04.geometry()
    current_geo_comb2 = combo_ga.geometry()
    current_geo_line2 = line_ga.geometry()
    current_geo_btn03 = push_ga_04.geometry()
    current_geo_btn04 = push_ga_05.geometry()
    current_geo_zoo01 = zoo_01.geometry()
    current_geo_zoo02 = zoo_02.geometry()

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

    ui.animation_group = QParallelAnimationGroup()

    for widget, start, end in [
        (text_03, current_geo_tedt1, target_geo_tedt1),
        (text_04, current_geo_tedt2, target_geo_tedt2),
        (text_06, current_geo_tedt3, target_geo_tedt3),
        (combo_vars, current_geo_comb1, target_geo_comb1),
        (line_vars, current_geo_line1, target_geo_line1),
        (push_03, current_geo_btn01, target_geo_btn01),
        (push_04, current_geo_btn02, target_geo_btn02),
        (combo_ga, current_geo_comb2, target_geo_comb2),
        (line_ga, current_geo_line2, target_geo_line2),
        (push_ga_04, current_geo_btn03, target_geo_btn03),
        (push_ga_05, current_geo_btn04, target_geo_btn04),
        (zoo_01, current_geo_zoo01, target_geo_zoo01),
        (zoo_02, current_geo_zoo02, target_geo_zoo02),
    ]:
        anim = QPropertyAnimation(widget, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group.addAnimation(anim)

    ui.animation_group.start()


def group_animation_03(ui, ui_type):
    """opti_vars_editer용 그룹 애니메이션 (공통)"""
    text_05 = _get_widget(ui, ui_type, 'text_05')
    text_06 = _get_widget(ui, ui_type, 'text_06')
    combo_vars = _get_widget(ui, ui_type, 'combo_vars')
    line_vars = _get_widget(ui, ui_type, 'line_vars_02')
    push_03 = _get_widget(ui, ui_type, 'push_03')
    push_04 = _get_widget(ui, ui_type, 'push_04')
    combo_ga = _get_widget(ui, ui_type, 'combo_ga')
    line_ga = _get_widget(ui, ui_type, 'line_ga')
    push_ga_04 = _get_widget(ui, ui_type, 'push_ga_04')
    push_ga_05 = _get_widget(ui, ui_type, 'push_ga_05')

    current_geo_tedt1 = text_05.geometry()
    current_geo_tedt2 = text_06.geometry()
    current_geo_comb1 = combo_vars.geometry()
    current_geo_line1 = line_vars.geometry()
    current_geo_btn01 = push_03.geometry()
    current_geo_btn02 = push_04.geometry()
    current_geo_comb2 = combo_ga.geometry()
    current_geo_line2 = line_ga.geometry()
    current_geo_btn03 = push_ga_04.geometry()
    current_geo_btn04 = push_ga_05.geometry()

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

    ui.animation_group = QParallelAnimationGroup()

    for widget, start, end in [
        (text_05, current_geo_tedt1, target_geo_tedt1),
        (text_06, current_geo_tedt2, target_geo_tedt2),
        (combo_vars, current_geo_comb1, target_geo_comb1),
        (line_vars, current_geo_line1, target_geo_line1),
        (push_03, current_geo_btn01, target_geo_btn01),
        (push_04, current_geo_btn02, target_geo_btn02),
        (combo_ga, current_geo_comb2, target_geo_comb2),
        (line_ga, current_geo_line2, target_geo_line2),
        (push_ga_04, current_geo_btn03, target_geo_btn03),
        (push_ga_05, current_geo_btn04, target_geo_btn04),
    ]:
        anim = QPropertyAnimation(widget, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group.addAnimation(anim)

    ui.animation_group.start()


def group_animation_04(ui, ui_type):
    """vars_editer용 그룹 애니메이션 (공통)"""
    text_01 = _get_widget(ui, ui_type, 'text_01')
    text_02 = _get_widget(ui, ui_type, 'text_02')
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    combo_buy = _get_widget(ui, ui_type, 'combo_buy')
    push_buy = _get_widget(ui, ui_type, 'push_buy')
    combo_sell = _get_widget(ui, ui_type, 'combo_sell')
    push_sell = _get_widget(ui, ui_type, 'push_sell')
    combo_vars = _get_widget(ui, ui_type, 'combo_vars')
    line_vars = _get_widget(ui, ui_type, 'line_vars_02')
    push_03 = _get_widget(ui, ui_type, 'push_03')
    push_04 = _get_widget(ui, ui_type, 'push_04')

    current_geo_tedt1 = text_01.geometry()
    current_geo_tedt2 = text_02.geometry()
    current_geo_tedt3 = text_03.geometry()
    current_geo_tedt4 = text_04.geometry()
    current_geo_comb1 = combo_buy.geometry()
    current_geo_btn01 = push_buy.geometry()
    current_geo_comb2 = combo_sell.geometry()
    current_geo_btn02 = push_sell.geometry()
    current_geo_comb3 = combo_vars.geometry()
    current_geo_line1 = line_vars.geometry()
    current_geo_btn03 = push_03.geometry()
    current_geo_btn04 = push_04.geometry()

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

    ui.animation_group = QParallelAnimationGroup()

    for widget, start, end in [
        (text_01, current_geo_tedt1, target_geo_tedt1),
        (text_02, current_geo_tedt2, target_geo_tedt2),
        (text_03, current_geo_tedt3, target_geo_tedt3),
        (text_04, current_geo_tedt4, target_geo_tedt4),
        (combo_buy, current_geo_comb1, target_geo_comb1),
        (push_buy, current_geo_btn01, target_geo_btn01),
        (combo_sell, current_geo_comb2, target_geo_comb2),
        (push_sell, current_geo_btn02, target_geo_btn02),
        (combo_vars, current_geo_comb3, target_geo_comb3),
        (line_vars, current_geo_line1, target_geo_line1),
        (push_03, current_geo_btn03, target_geo_btn03),
        (push_04, current_geo_btn04, target_geo_btn04),
    ]:
        anim = QPropertyAnimation(widget, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group.addAnimation(anim)

    ui.animation_group.start()


def group_animation_05(ui, ui_type):
    """stg_editer용 그룹 애니메이션 (공통)"""
    text_01 = _get_widget(ui, ui_type, 'text_01')
    text_02 = _get_widget(ui, ui_type, 'text_02')
    combo_buy = _get_widget(ui, ui_type, 'combo_buy')
    push_buy = _get_widget(ui, ui_type, 'push_buy')
    combo_sell = _get_widget(ui, ui_type, 'combo_sell')
    push_sell = _get_widget(ui, ui_type, 'push_sell')
    zoo_01 = _get_widget(ui, ui_type, 'zoo_01')
    zoo_02 = _get_widget(ui, ui_type, 'zoo_02')

    current_geo_tedt1 = text_01.geometry()
    current_geo_tedt2 = text_02.geometry()
    current_geo_comb1 = combo_buy.geometry()
    current_geo_btn01 = push_buy.geometry()
    current_geo_comb2 = combo_sell.geometry()
    current_geo_btn02 = push_sell.geometry()
    current_geo_zoo01 = zoo_01.geometry()
    current_geo_zoo02 = zoo_02.geometry()

    target_geo_tedt1 = QRect(7, 10, 1000, 740 if ui.extend_window else 463)
    target_geo_tedt2 = QRect(7, 756 if ui.extend_window else 478, 1000, 602 if ui.extend_window else 272)
    target_geo_comb1 = QRect(1012, 10, 165, 25)
    target_geo_btn01 = QRect(1012, 40, 165, 30)
    target_geo_comb2 = QRect(1012, 478, 165, 25)
    target_geo_btn02 = QRect(1012, 508, 165, 30)
    target_geo_zoo01 = QRect(937, 15, 50, 20)
    target_geo_zoo02 = QRect(937, 761 if ui.extend_window else 483, 50, 20)

    ui.animation_group = QParallelAnimationGroup()

    for widget, start, end in [
        (text_01, current_geo_tedt1, target_geo_tedt1),
        (text_02, current_geo_tedt2, target_geo_tedt2),
        (combo_buy, current_geo_comb1, target_geo_comb1),
        (push_buy, current_geo_btn01, target_geo_btn01),
        (combo_sell, current_geo_comb2, target_geo_comb2),
        (push_sell, current_geo_btn02, target_geo_btn02),
        (zoo_01, current_geo_zoo01, target_geo_zoo01),
        (zoo_02, current_geo_zoo02, target_geo_zoo02),
    ]:
        anim = QPropertyAnimation(widget, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group.addAnimation(anim)

    ui.animation_group.start()


# noinspection PyUnboundLocalVariable
def group_animation_06(ui, pushButton1, pushButton2, pushButton3, pushButton4=None):
    """버튼 그룹 애니메이션 (공통)"""
    current_geo_btn01 = QRect(1350, 0, 0, 0)
    current_geo_btn02 = QRect(1350, 0, 0, 0)
    current_geo_btn03 = QRect(1350, 0, 0, 0)
    current_geo_btn04 = QRect(1350, 0, 0, 0)

    target_geo_btn01 = QRect(1012, 335, 165, 30)
    target_geo_btn02 = QRect(1012, 370, 165, 30)

    if pushButton4 is None:
        target_geo_btn03 = QRect(1012, 405, 165, 30)
    else:
        target_geo_btn03 = QRect(1012, 405, 80, 30)
        target_geo_btn04 = QRect(1097, 405, 80, 30)

    ui.animation_group2 = QParallelAnimationGroup()

    for btn, start, end in [
        (pushButton1, current_geo_btn01, target_geo_btn01),
        (pushButton2, current_geo_btn02, target_geo_btn02),
        (pushButton3, current_geo_btn03, target_geo_btn03),
    ]:
        anim = QPropertyAnimation(btn, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group2.addAnimation(anim)

    if pushButton4 is not None:
        anim_btn04 = QPropertyAnimation(pushButton4, b'geometry')
        anim_btn04.setDuration(300)
        anim_btn04.setEasingCurve(QEasingCurve.InOutCirc)
        anim_btn04.setStartValue(current_geo_btn04)
        anim_btn04.setEndValue(target_geo_btn04)
        ui.animation_group2.addAnimation(anim_btn04)

    ui.animation_group2.start()


def group_animation_07(ui, pushButton1, pushButton2, pushButton3, pushButton4, pushButton5, pushButton6):
    """6버튼 그룹 애니메이션 (공통)"""
    current_geo_btn01 = QRect(1350, 0, 0, 0)
    current_geo_btn02 = QRect(1350, 0, 0, 0)
    current_geo_btn03 = QRect(1350, 0, 0, 0)
    current_geo_btn04 = QRect(1350, 0, 0, 0)
    current_geo_btn05 = QRect(1350, 0, 0, 0)
    current_geo_btn06 = QRect(1350, 0, 0, 0)

    target_geo_btn01 = QRect(1012, 335, 80, 30)
    target_geo_btn02 = QRect(1012, 370, 80, 30)
    target_geo_btn03 = QRect(1012, 405, 80, 30)
    target_geo_btn04 = QRect(1097, 335, 80, 30)
    target_geo_btn05 = QRect(1097, 370, 80, 30)
    target_geo_btn06 = QRect(1097, 405, 80, 30)

    ui.animation_group2 = QParallelAnimationGroup()

    for btn, start, end in [
        (pushButton1, current_geo_btn01, target_geo_btn01),
        (pushButton2, current_geo_btn02, target_geo_btn02),
        (pushButton3, current_geo_btn03, target_geo_btn03),
        (pushButton4, current_geo_btn04, target_geo_btn04),
        (pushButton5, current_geo_btn05, target_geo_btn05),
        (pushButton6, current_geo_btn06, target_geo_btn06),
    ]:
        anim = QPropertyAnimation(btn, b'geometry')
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutCirc)
        anim.setStartValue(start)
        anim.setEndValue(end)
        ui.animation_group2.addAnimation(anim)

    ui.animation_group2.start()


# =============================================================================
# 에디터 함수들 (설정 기반 공통)
# =============================================================================
@error_decorator
def opti_test_editer(ui, ui_type):
    """최적화 테스트 에디터 (코인/주식 공통)"""
    group_animation_01(ui, ui_type)
    group_animation_07(
        ui,
        _get_widget(ui, ui_type, 'push_15'),
        _get_widget(ui, ui_type, 'push_16'),
        _get_widget(ui, ui_type, 'push_17'),
        _get_widget(ui, ui_type, 'push_30'),
        _get_widget(ui, ui_type, 'push_31'),
        _get_widget(ui, ui_type, 'push_32')
    )

    _set_widget_text(ui, ui_type, 'zoo_01', '확대(esc)')
    _set_widget_text(ui, ui_type, 'zoo_02', '확대(esc)')

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': True, '04': True, '05': True, '06': False
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'detail', 'baklog', 'datedt', 'backte', 'opcond', 'gaopti', 'rwftvd', 'varsedit', 'areaedit'],
        ['esczom', 'optimz', 'period', 'optest']
    )

    _set_widget_text(ui, ui_type, 'push_03', '최적화 변수범위 로딩(F9)')
    _set_widget_text(ui, ui_type, 'push_04', '최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    _get_widget(ui, ui_type, 'label_04').setText(testtext)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_07')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def rwf_test_editer(ui, ui_type):
    """전진분석 테스트 에디터 (코인/주식 공통)"""
    group_animation_01(ui, ui_type)
    group_animation_07(
        ui,
        _get_widget(ui, ui_type, 'push_18'),
        _get_widget(ui, ui_type, 'push_19'),
        _get_widget(ui, ui_type, 'push_20'),
        _get_widget(ui, ui_type, 'push_33'),
        _get_widget(ui, ui_type, 'push_34'),
        _get_widget(ui, ui_type, 'push_35')
    )

    _set_widget_text(ui, ui_type, 'zoo_01', '확대(esc)')
    _set_widget_text(ui, ui_type, 'zoo_02', '확대(esc)')

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': True, '04': True, '05': True, '06': False
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'detail', 'baklog', 'datedt', 'backte', 'opcond', 'gaopti', 'optest', 'varsedit', 'areaedit'],
        ['esczom', 'optimz', 'period', 'rwftvd']
    )

    _set_widget_text(ui, ui_type, 'push_03', '최적화 변수범위 로딩(F9)')
    _set_widget_text(ui, ui_type, 'push_04', '최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    _set_widget_visible(ui, ui_type, 'label_01', False)
    _get_widget(ui, ui_type, 'label_04').setText(rwfttext)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_06')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def opti_ga_editer(ui, ui_type):
    """GA 최적화 에디터 (코인/주식 공통)"""
    group_animation_02(ui, ui_type)
    group_animation_06(
        ui,
        _get_widget(ui, ui_type, 'push_ga_01'),
        _get_widget(ui, ui_type, 'push_ga_02'),
        _get_widget(ui, ui_type, 'push_ga_03')
    )

    _set_widget_text(ui, ui_type, 'zoo_01', '확대(esc)')
    _set_widget_text(ui, ui_type, 'zoo_02', '확대(esc)')

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': True, '04': True, '05': False, '06': True
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'detail', 'baklog', 'datedt', 'backte', 'opcond', 'optest', 'rwftvd', 'varsedit', 'areaedit'],
        ['esczom', 'optimz', 'period', 'gaopti']
    )

    _set_widget_text(ui, ui_type, 'push_ga_04', 'GA 변수범위 로딩(F9)')
    _set_widget_text(ui, ui_type, 'push_ga_05', 'GA 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    _get_widget(ui, ui_type, 'label_04').setText(gaoptext)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_10')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def opti_vars_editer(ui, ui_type):
    """최적화 변수 에디터 (코인/주식 공통)"""
    group_animation_03(ui, ui_type)
    group_animation_06(
        ui,
        _get_widget(ui, ui_type, 'push_21'),
        _get_widget(ui, ui_type, 'push_22'),
        _get_widget(ui, ui_type, 'push_23')
    )

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': False, '04': False, '05': True, '06': True
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'datedt', 'backte', 'opcond', 'detail', 'baklog', 'optest', 'rwftvd', 'esczom', 'optimz', 'varsedit'],
        ['areaedit', 'period', 'gaopti']
    )

    _set_widget_text(ui, ui_type, 'push_ga_04', 'GA 변수범위 로딩')
    _set_widget_text(ui, ui_type, 'push_ga_05', 'GA 변수범위 저장')
    _set_widget_text(ui, ui_type, 'push_03', '최적화 변수범위 로딩')
    _set_widget_text(ui, ui_type, 'push_04', '최적화 변수범위 저장')

    for key in ['push_06', 'push_07', 'push_08_v', 'push_27', 'push_28', 'push_29']:
        _set_widget_visible(ui, ui_type, key, False)
    for key in ['push_ga_01', 'push_ga_02', 'push_ga_03']:
        _set_widget_visible(ui, ui_type, key, False)
    for key in ['combo_vars', 'line_vars_02', 'push_03', 'push_04', 'push_11']:
        _set_widget_visible(ui, ui_type, key, True)

    ui.image_label1.setVisible(True)
    _get_widget(ui, ui_type, 'label_04').setText(gaoptext)
    _get_widget(ui, ui_type, 'label_05').setText(vedittxt)
    _set_widget_visible(ui, ui_type, 'label_05', True)

    _set_focus(ui, ui_type, 'sj_push_12')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def opti_editer(ui, ui_type):
    """최적화 에디터 (코인/주식 공통)"""
    group_animation_01(ui, ui_type)
    group_animation_07(
        ui,
        _get_widget(ui, ui_type, 'push_06'),
        _get_widget(ui, ui_type, 'push_07'),
        _get_widget(ui, ui_type, 'push_08_v'),
        _get_widget(ui, ui_type, 'push_27'),
        _get_widget(ui, ui_type, 'push_28'),
        _get_widget(ui, ui_type, 'push_29')
    )

    _set_widget_text(ui, ui_type, 'zoo_01', '확대(esc)')
    _set_widget_text(ui, ui_type, 'zoo_02', '확대(esc)')

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': True, '04': True, '05': True, '06': False
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'datedt', 'backte', 'opcond', 'detail', 'baklog', 'optest', 'gaopti', 'rwftvd', 'varsedit', 'areaedit'],
        ['esczom', 'optimz', 'period']
    )

    _set_widget_text(ui, ui_type, 'push_03', '최적화 변수범위 로딩(F9)')
    _set_widget_text(ui, ui_type, 'push_04', '최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    _get_widget(ui, ui_type, 'label_04').setText(optitext)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_08')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def vars_editer(ui, ui_type):
    """변수 에디터 (코인/주식 공통)"""
    group_animation_04(ui, ui_type)
    group_animation_06(
        ui,
        _get_widget(ui, ui_type, 'push_24'),
        _get_widget(ui, ui_type, 'push_25'),
        _get_widget(ui, ui_type, 'push_26')
    )

    _set_text_edits_visible(ui, ui_type, {
        '01': True, '02': True, '03': True, '04': True, '05': False, '06': False
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'datedt', 'backte', 'opcond', 'detail', 'baklog', 'gaopti', 'optest', 'rwftvd', 'esczom', 'areaedit'],
        ['varsedit', 'optimz', 'period']
    )

    _set_widget_text(ui, ui_type, 'push_buy', '매수전략 로딩')
    _set_widget_text(ui, ui_type, 'push_sell', '매도전략 로딩')

    for key in ['line_vars_04', 'line_vars_05', 'push_13', 'push_14']:
        _set_widget_visible(ui, ui_type, key, False)
    for key in ['combo_buy', 'push_buy', 'combo_sell', 'push_sell']:
        _set_widget_visible(ui, ui_type, key, True)

    ui.image_label1.setVisible(False)
    _get_widget(ui, ui_type, 'label_04').setText(optitext)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_13')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def stg_editer(ui, ui_type):
    """전략 에디터 (코인/주식 공통)"""
    group_animation_05(ui, ui_type)
    group_animation_06(
        ui,
        _get_widget(ui, ui_type, 'sj_push_01'),
        _get_widget(ui, ui_type, 'sj_push_02'),
        _get_widget(ui, ui_type, 'sj_push_03'),
        _get_widget(ui, ui_type, 'sj_push_04')
    )

    _set_widget_text(ui, ui_type, 'zoo_01', '확대(esc)')
    _set_widget_text(ui, ui_type, 'zoo_02', '확대(esc)')

    _set_text_edits_visible(ui, ui_type, {
        '01': True, '02': True, '03': False, '04': False, '05': False, '06': False
    })

    _set_lists_visible(
        ui, ui_type,
        ['version', 'optimz', 'period', 'opcond', 'detail', 'baklog', 'gaopti', 'optest', 'rwftvd', 'varsedit', 'areaedit'],
        ['datedt', 'esczom', 'backte']
    )

    _set_widget_text(ui, ui_type, 'push_buy', '매수전략 로딩(F1)')
    _set_widget_text(ui, ui_type, 'push_sell', '매도전략 로딩(F5)')

    ui.image_label1.setVisible(False)
    _set_widget_visible(ui, ui_type, 'label_05', False)

    _set_focus(ui, ui_type, 'sj_push_09')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


@error_decorator
def cond_editer(ui, ui_type):
    """조건 에디터 (코인/주식 공통)"""
    group_animation_06(
        ui,
        _get_widget(ui, ui_type, 'push_cond_05'),
        _get_widget(ui, ui_type, 'push_cond_06'),
        _get_widget(ui, ui_type, 'push_cond_07')
    )

    _set_text_edits_visible(ui, ui_type, {
        '01': False, '02': False, '03': False, '04': False, '05': False, '06': False
    })

    text_07 = _get_widget(ui, ui_type, 'text_07')
    text_08 = _get_widget(ui, ui_type, 'text_08')
    text_07.setGeometry(7, 10, 497, 1347 if ui.extend_window else 740)
    text_08.setGeometry(509, 10, 497, 1347 if ui.extend_window else 740)

    _set_lists_visible(
        ui, ui_type,
        ['version', 'esczom', 'backte', 'detail', 'baklog', 'gaopti', 'optest', 'rwftvd', 'datedt', 'varsedit', 'areaedit'],
        ['optimz', 'period', 'opcond']
    )

    for key in ['line_vars_04', 'line_vars_05', 'push_13', 'push_14']:
        _set_widget_visible(ui, ui_type, key, False)
    for key in ['combo_sellstg', 'line_sellstg', 'push_09', 'push_10']:
        _set_widget_visible(ui, ui_type, key, False)
    for key in ['combo_vars', 'line_vars_02', 'push_03', 'push_04']:
        _set_widget_visible(ui, ui_type, key, False)

    ui.image_label1.setVisible(True)
    _set_widget_visible(ui, ui_type, 'label_01', False)
    _get_widget(ui, ui_type, 'label_04').setText(condtext)
    _get_widget(ui, ui_type, 'label_05').setText(cedittxt)
    _set_widget_visible(ui, ui_type, 'label_05', True)

    _set_focus(ui, ui_type, 'sj_push_11')
    change_svj_button_color(ui, ui_type)
    change_version_button_color(ui, ui_type)


# =============================================================================
# 백테스트 관련 함수들 (설정 기반 공통)
# =============================================================================
@error_decorator
def change_pre_button_edit(ui, ui_type):
    """이전 버튼 스타일 변경 (공통)"""
    sj_push_09 = _get_widget(ui, ui_type, 'sj_push_09')
    sj_push_07 = _get_widget(ui, ui_type, 'sj_push_07')
    sj_push_06 = _get_widget(ui, ui_type, 'sj_push_06')
    sj_push_10 = _get_widget(ui, ui_type, 'sj_push_10')
    sj_push_11 = _get_widget(ui, ui_type, 'sj_push_11')
    sj_push_12 = _get_widget(ui, ui_type, 'sj_push_12')
    sj_push_13 = _get_widget(ui, ui_type, 'sj_push_13')
    sj_push_08 = _get_widget(ui, ui_type, 'sj_push_08')

    if _get_widget(ui, ui_type, 'sj_push_01').isVisible():
        sj_push_09.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_32').isVisible():
        sj_push_07.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_35').isVisible():
        sj_push_06.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_ga_03').isVisible():
        sj_push_10.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_cond_08').isVisible():
        sj_push_11.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_23').isVisible():
        sj_push_12.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_26').isVisible():
        sj_push_13.setStyleSheet(style_bc_bd)
    elif _get_widget(ui, ui_type, 'push_29').isVisible():
        sj_push_08.setStyleSheet(style_bc_bd)


@error_decorator
def backtest_log(ui, ui_type):
    """백테스트 로그 화면 (공통)"""
    change_pre_button_edit(ui, ui_type)

    for i in range(1, 9):
        _set_widget_visible(ui, ui_type, f'text_0{i}', False)

    text_09 = _get_widget(ui, ui_type, 'text_09')
    progress = _get_widget(ui, ui_type, 'progress')
    push_08 = _get_widget(ui, ui_type, 'push_08')

    text_09.setGeometry(7, 10, 1000, 1313 if ui.extend_window else 703)
    progress.setGeometry(7, 1328 if ui.extend_window else 718, 830, 30)
    push_08.setGeometry(842, 1328 if ui.extend_window else 718, 165, 30)

    _set_lists_visible(
        ui, ui_type,
        ['version', 'esczom', 'detail'],
        ['baklog']
    )

    push_08.setStyleSheet(style_bc_by)
    sj_push_14 = _get_widget(ui, ui_type, 'sj_push_14')
    sj_push_15 = _get_widget(ui, ui_type, 'sj_push_15')
    sj_push_14.setFocus()
    sj_push_14.setStyleSheet(style_bc_dk)
    sj_push_15.setStyleSheet(style_bc_bs)
    change_version_button_color(ui, ui_type)


@error_decorator
def backtest_detail(ui, ui_type):
    """백테스트 상세 화면 (공통)"""
    change_pre_button_edit(ui, ui_type)

    for i in range(1, 9):
        _set_widget_visible(ui, ui_type, f'text_0{i}', False)

    table = _get_widget(ui, ui_type, 'table')
    table.setGeometry(7, 40, 1000, 1318 if ui.extend_window else 713)
    if (ui.extend_window and table.rowCount() < 60) or \
            (not ui.extend_window and table.rowCount() < 32):
        table.setRowCount(60 if ui.extend_window else 32)

    _set_lists_visible(
        ui, ui_type,
        ['version', 'esczom', 'baklog'],
        ['detail']
    )

    sj_push_15 = _get_widget(ui, ui_type, 'sj_push_15')
    sj_push_14 = _get_widget(ui, ui_type, 'sj_push_14')
    sj_push_15.setFocus()
    sj_push_15.setStyleSheet(style_bc_dk)
    sj_push_14.setStyleSheet(style_bc_bs)
    change_version_button_color(ui, ui_type)


# =============================================================================
# 버튼 색상 변경 함수들 (설정 기반 공통)
# =============================================================================
@error_decorator
def change_svj_button_color(ui, ui_type):
    """SVJ 버튼 색상 변경 (공통)"""
    for button in _get_list(ui, ui_type, 'editer'):
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_bs)


@error_decorator
def change_version_button_color(ui, ui_type):
    """버전 버튼 색상 변경 (공통)"""
    for button in _get_list(ui, ui_type, 'load'):
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_st)


# =============================================================================
# 백테스트 시작 함수들 (설정 기반 공통)
# =============================================================================
@error_decorator
def backtest_start(ui, ui_type):
    """백테스트 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ, backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
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
            QMessageBox.critical(ui, '오류 알림', '백테엔진을 먼저 구동하십시오.\n')
            return
        if not back_club and (not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier)):
            backengine_show(ui, config['market_type'])
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday = _get_widget(ui, ui_type, 'date_start').date().toString('yyyyMMdd')
        endday = _get_widget(ui, ui_type, 'date_end').date().toString('yyyyMMdd')
        starttime = _get_widget(ui, ui_type, 'line_start').text()
        endtime = _get_widget(ui, ui_type, 'line_end').text()
        betting = _get_widget(ui, ui_type, 'line_betting').text()
        avgtime = _get_widget(ui, ui_type, 'line_avg').text()
        buystg = _get_widget(ui, ui_type, 'combo_buy').currentText()
        sellstg = _get_widget(ui, ui_type, 'combo_sell').currentText()
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '백테스트'))

        gubun = config['gubun_fn'](ui)
        dict_cn = getattr(ui, config['dict_cn']) if config['dict_cn'] else None

        proc_name = f'proc_backtester_bs'
        setattr(ui, proc_name, Process(
            target=BackTest,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                  ui.back_sques, '백테스트', gubun, ui.dict_set, betting, avgtime, startday, endday, starttime,
                  endtime, buystg, sellstg, dict_cn, ui.back_count, bl, False, back_club)
        ))
        getattr(ui, proc_name).start()
        backtest_log(ui, ui_type)
        _get_widget(ui, ui_type, 'progress').setValue(0)
        setattr(ui, config['icon_alert'], True)


@error_decorator
def backfinder_start(ui, ui_type):
    """백파인더 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ, backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            backengine_show(ui, config['market_type'])
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday = _get_widget(ui, ui_type, 'date_start').date().toString('yyyyMMdd')
        endday = _get_widget(ui, ui_type, 'date_end').date().toString('yyyyMMdd')
        starttime = _get_widget(ui, ui_type, 'line_start').text()
        endtime = _get_widget(ui, ui_type, 'line_end').text()
        avgtime = _get_widget(ui, ui_type, 'line_avg').text()
        buystg = _get_widget(ui, ui_type, 'combo_buy').currentText()

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (startday, endday, starttime, endtime, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if buystg == '':
            QMessageBox.critical(ui, '오류 알림', '매수전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        text_01 = _get_widget(ui, ui_type, 'text_01')
        if 'self.tickcols' not in text_01.toPlainText():
            QMessageBox.critical(ui, '오류 알림', '현재 매수전략이 백파인더용이 아닙니다.\n')
            return

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '백파인더'))

        gubun = config['gubun_fn'](ui)

        proc_name = f'proc_backtester_bf'
        setattr(ui, proc_name, Process(
            target=BackFinder,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, gubun,
                  ui.dict_set, avgtime, startday, endday, starttime, endtime, buystg, ui.back_count)
        ))
        getattr(ui, proc_name).start()
        backtest_log(ui, ui_type)
        _get_widget(ui, ui_type, 'progress').setValue(0)
        setattr(ui, config['icon_alert'], True)


@error_decorator
def backfinder_sample(ui, ui_type):
    """백파인더 샘플 로드 (코인/주식 공통)"""
    text_01 = _get_widget(ui, ui_type, 'text_01')
    if text_01.isVisible():
        text_01.clear()
        _get_widget(ui, ui_type, 'text_02').clear()
        if ui_type == 'coin':
            text_01.append(example_finder if ui.dict_set['거래소'] == '업비트' else example_finder_future)
        else:
            text_01.append(example_finder)


# =============================================================================
# 최적화 시작 함수들 (설정 기반 공통)
# =============================================================================
def _opti_common_check(ui, ui_type):
    """최적화 공통 검증 (내부 함수)"""
    from ui.ui_backtest_engine import backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
        return None
    if ui.back_engining:
        QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
        return None
    if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
        QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
        return None
    if not ui.backtest_engine or (not (QApplication.keyboardModifiers() & Qt.ShiftModifier) and
                                  not (QApplication.keyboardModifiers() & Qt.AltModifier) and
                                  (QApplication.keyboardModifiers() & Qt.ControlModifier)):
        backengine_show(ui, config['market_type'])
        return None
    if ui.back_cancelling:
        QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
        return None

    randomopti = True if not (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
    onlybuy = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.ShiftModifier) else False
    onlysell = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False

    return {'randomopti': randomopti, 'onlybuy': onlybuy, 'onlysell': onlysell}


@error_decorator
def opti_start(ui, back_name, ui_type):
    """최적화 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ
    result = _opti_common_check(ui, ui_type)
    if result is None:
        return

    config = UI_EDITER_CONFIG[ui_type]
    randomopti, onlybuy, onlysell = result['randomopti'], result['onlybuy'], result['onlysell']

    starttime = _get_widget(ui, ui_type, 'line_start').text()
    endtime = _get_widget(ui, ui_type, 'line_end').text()
    betting = _get_widget(ui, ui_type, 'line_betting').text()
    buystg = _get_widget(ui, ui_type, 'combo_opti').currentText()
    sellstg = _get_widget(ui, ui_type, 'combo_sellstg').currentText()
    optivars = _get_widget(ui, ui_type, 'combo_vars').currentText()
    ccount = _get_widget(ui, ui_type, 'combo_ccount').currentText()
    optistd = _get_widget(ui, ui_type, 'combo_std').currentText()
    weeks_train = _get_widget(ui, ui_type, 'combo_week_train').currentText()
    weeks_valid = _get_widget(ui, ui_type, 'combo_week_valid').currentText()
    weeks_test = _get_widget(ui, ui_type, 'combo_week_test').currentText()
    benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
    bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
    optunasampl = ui.op_comboBoxxxx_01.currentText()
    optunafixv = ui.op_lineEditttt_01.text()
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

    clear_backtestQ(ui)
    for q in ui.back_eques:
        q.put(('백테유형', '최적화'))

    dict_cn = getattr(ui, config['dict_cn']) if config['dict_cn'] else None

    ui.backQ.put((
        betting, starttime, endtime, buystg, sellstg, optivars, dict_cn, ccount,
        ui.dict_set['최적화기준값제한'], optistd, ui.back_count, False, weeks_train, weeks_valid, weeks_test,
        benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos, randomopti, onlybuy, onlysell
    ))

    gubun = config['gubun_fn'](ui)

    opti_types = {
        '최적화O': 'o', '최적화OV': 'ov', '최적화OVC': 'ovc',
        '최적화B': 'b', '최적화BV': 'bv', '최적화BVC': 'bvc',
        '최적화OT': 'ot', '최적화OVT': 'ovt', '최적화OVCT': 'ovct',
        '최적화BT': 'bt', '최적화BVT': 'bvt'
    }
    suffix = opti_types.get(back_name, 'bvct')
    proc_name = f'proc_backtester_{suffix}'

    setattr(ui, proc_name, Process(
        target=Optimize,
        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
              ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
    ))
    getattr(ui, proc_name).start()
    backtest_log(ui, ui_type)
    _get_widget(ui, ui_type, 'progress').setValue(0)
    setattr(ui, config['icon_alert'], True)


@error_decorator
def opti_rwft_start(ui, back_name, ui_type):
    """전진분석 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ, backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            backengine_show(ui, config['market_type'])
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        randomopti = True if (QApplication.keyboardModifiers() & Qt.AltModifier) and 'B' not in back_name else False
        startday = _get_widget(ui, ui_type, 'date_start').date().toString('yyyyMMdd')
        endday = _get_widget(ui, ui_type, 'date_end').date().toString('yyyyMMdd')
        starttime = _get_widget(ui, ui_type, 'line_start').text()
        endtime = _get_widget(ui, ui_type, 'line_end').text()
        betting = _get_widget(ui, ui_type, 'line_betting').text()
        buystg = _get_widget(ui, ui_type, 'combo_opti').currentText()
        sellstg = _get_widget(ui, ui_type, 'combo_sellstg').currentText()
        optivars = _get_widget(ui, ui_type, 'combo_vars').currentText()
        ccount = _get_widget(ui, ui_type, 'combo_ccount').currentText()
        optistd = _get_widget(ui, ui_type, 'combo_std').currentText()
        weeks_train = _get_widget(ui, ui_type, 'combo_week_train').currentText()
        weeks_valid = _get_widget(ui, ui_type, 'combo_week_valid').currentText()
        weeks_test = _get_widget(ui, ui_type, 'combo_week_test').currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
        optunasampl = ui.op_comboBoxxxx_01.currentText()
        optunafixv = ui.op_lineEditttt_01.text()
        optunacount = ui.op_lineEditttt_02.text()
        optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '전진분석'))

        dict_cn = getattr(ui, config['dict_cn']) if config['dict_cn'] else None

        ui.backQ.put((
            betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, dict_cn, ccount,
            ui.dict_set['최적화기준값제한'], optistd, ui.back_count, False, weeks_train, weeks_valid, weeks_test,
            benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos, randomopti
        ))

        gubun = config['gubun_fn'](ui)

        rwft_types = {
            '전진분석OR': 'or', '전진분석ORV': 'orv', '전진분석ORVC': 'orvc',
            '전진분석BR': 'br', '전진분석BRV': 'brv'
        }
        suffix = rwft_types.get(back_name, 'brvc')
        proc_name = f'proc_backtester_{suffix}'

        setattr(ui, proc_name, Process(
            target=RollingWalkForwardTest,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                  ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
        ))
        getattr(ui, proc_name).start()
        backtest_log(ui, ui_type)
        _get_widget(ui, ui_type, 'progress').setValue(0)
        setattr(ui, config['icon_alert'], True)


@error_decorator
def opti_ga_start(ui, back_name, ui_type):
    """GA 최적화 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ, backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            backengine_show(ui, config['market_type'])
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime = _get_widget(ui, ui_type, 'line_start').text()
        endtime = _get_widget(ui, ui_type, 'line_end').text()
        betting = _get_widget(ui, ui_type, 'line_betting').text()
        buystg = _get_widget(ui, ui_type, 'combo_opti').currentText()
        sellstg = _get_widget(ui, ui_type, 'combo_sellstg').currentText()
        optivars = _get_widget(ui, ui_type, 'combo_ga').currentText()
        optistd = _get_widget(ui, ui_type, 'combo_std').currentText()
        weeks_train = _get_widget(ui, ui_type, 'combo_week_train').currentText()
        weeks_valid = _get_widget(ui, ui_type, 'combo_week_valid').currentText()
        weeks_test = _get_widget(ui, ui_type, 'combo_week_test').currentText()
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', 'GA최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, None, ui.dict_set['최적화기준값제한'], optistd,
            ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        gubun = config['gubun_fn'](ui)

        ga_types = {'최적화OG': 'og', '최적화OGV': 'ogv'}
        suffix = ga_types.get(back_name, 'ogvc')
        proc_name = f'proc_backtester_{suffix}'

        setattr(ui, proc_name, Process(
            target=OptimizeGeneticAlgorithm,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                  ui.back_sques, ui.multi, back_name, gubun, ui.dict_set)
        ))
        getattr(ui, proc_name).start()
        backtest_log(ui, ui_type)
        _get_widget(ui, ui_type, 'progress').setValue(0)
        setattr(ui, config['icon_alert'], True)


@error_decorator
def opti_cond_start(ui, back_name, ui_type):
    """조건 최적화 시작 (코인/주식 공통)"""
    from ui.ui_backtest_engine import clear_backtestQ, backengine_show
    config = UI_EDITER_CONFIG[ui_type]

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            backengine_show(ui, config['market_type'])
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime = _get_widget(ui, ui_type, 'line_start').text()
        endtime = _get_widget(ui, ui_type, 'line_end').text()
        betting = _get_widget(ui, ui_type, 'line_betting').text()
        avgtime = _get_widget(ui, ui_type, 'line_avg').text()
        buystg = _get_widget(ui, ui_type, 'combo_cond_buy').currentText()
        sellstg = _get_widget(ui, ui_type, 'combo_cond_sell').currentText()
        bcount = _get_widget(ui, ui_type, 'line_cond_03').text()
        scount = _get_widget(ui, ui_type, 'line_cond_04').text()
        rcount = _get_widget(ui, ui_type, 'line_cond_05').text()
        optistd = _get_widget(ui, ui_type, 'combo_std').currentText()
        weeks_train = _get_widget(ui, ui_type, 'combo_week_train').currentText()
        weeks_valid = _get_widget(ui, ui_type, 'combo_week_valid').currentText()
        weeks_test = _get_widget(ui, ui_type, 'combo_week_test').currentText()
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '조건최적화'))

        ui.backQ.put((
            betting, avgtime, starttime, endtime, buystg, sellstg, ui.dict_set['최적화기준값제한'], optistd, bcount,
            scount, rcount, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        gubun = config['gubun_fn'](ui)

        cond_types = {'최적화OC': 'oc', '최적화OCV': 'ocv'}
        suffix = cond_types.get(back_name, 'ocvc')
        proc_name = f'proc_backtester_{suffix}'

        setattr(ui, proc_name, Process(
            target=OptimizeConditions,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                  ui.multi, back_name, gubun, ui.dict_set)
        ))
        getattr(ui, proc_name).start()
        backtest_log(ui, ui_type)
        _get_widget(ui, ui_type, 'progress').setValue(0)
        setattr(ui, config['icon_alert'], True)


# =============================================================================
# 변수 변환 함수들 (설정 기반 공통)
# =============================================================================
@error_decorator
def optivars_to_gavars(ui, ui_type):
    """최적화 변수를 GA 변수로 변환 (코인/주식 공통)"""
    text_05 = _get_widget(ui, ui_type, 'text_05')
    opti_vars_text = text_05.toPlainText()
    if opti_vars_text:
        ga_vars_text = get_optivars_to_gavars(ui, opti_vars_text)
        text_06 = _get_widget(ui, ui_type, 'text_06')
        text_06.clear()
        text_06.append(ga_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 최적화 범위 코드가 공백 상태입니다.\n최적화 범위 코드를 작성하거나 로딩하십시오.\n')


@error_decorator
def gavars_to_optivars(ui, ui_type):
    """GA 변수를 최적화 변수로 변환 (코인/주식 공통)"""
    text_06 = _get_widget(ui, ui_type, 'text_06')
    ga_vars_text = text_06.toPlainText()
    if ga_vars_text:
        opti_vars_text = get_gavars_to_optivars(ui, ga_vars_text)
        text_05 = _get_widget(ui, ui_type, 'text_05')
        text_05.clear()
        text_05.append(opti_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 GA 범위 코드가 공백 상태입니다.\nGA 범위 코드를 작성하거나 로딩하십시오.\n')


@error_decorator
def stg_vars_change(ui, ui_type):
    """전략을 변수 형태로 변환 (코인/주식 공통)"""
    text_01 = _get_widget(ui, ui_type, 'text_01')
    text_02 = _get_widget(ui, ui_type, 'text_02')
    buystg = text_01.toPlainText()
    sellstg = text_02.toPlainText()
    buystg_str, sellstg_str = get_stgtxt_to_varstxt(ui, buystg, sellstg)
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    text_03.clear()
    text_04.clear()
    text_03.append(buystg_str)
    text_04.append(sellstg_str)


@error_decorator
def stgvars_key_sort(ui, ui_type):
    """변수 키 정렬 (코인/주식 공통)"""
    text_05 = _get_widget(ui, ui_type, 'text_05')
    text_06 = _get_widget(ui, ui_type, 'text_06')
    optivars = text_05.toPlainText()
    gavars = text_06.toPlainText()
    optivars_str, gavars_str = get_stgtxt_sort2(ui, optivars, gavars)
    text_05.clear()
    text_06.clear()
    text_05.append(optivars_str)
    text_06.append(gavars_str)


@error_decorator
def optivars_key_sort(ui, ui_type):
    """최적화 변수 키 정렬 (코인/주식 공통)"""
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    buystg = text_03.toPlainText()
    sellstg = text_04.toPlainText()
    buystg_str, sellstg_str = get_stgtxt_sort(ui, buystg, sellstg)
    text_03.clear()
    text_04.clear()
    text_03.append(buystg_str)
    text_04.append(sellstg_str)
