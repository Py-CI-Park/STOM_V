
import random
import sqlite3
from ui.create_widget.set_text import famous_saying
from utility.static_method.static import qtest_qwait
from utility.settings.setting_base import DB_STRATEGY
from PyQt5.QtWidgets import QMessageBox, QColorDialog
from ui.create_widget.set_text_stg_button import dict_stg_name


def formula_activated(ui):
    """수식을 활성화합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    dict_style = {
        1: '1:실선',
        2: '2:대시선',
        3: '3:점선',
        4: '4:대시점선',
        5: '5:대시점점선',
        6: '6:위쪽화살표(↑)',
        7: '7:아래쪽화살표(↓)',
        8: '8:우측쪽화살표(→)',
        9: '9:좌쪽화살표(←)'
    }
    fname = ui.fm_comboBoxxxxx_00.currentText()
    con = sqlite3.connect(DB_STRATEGY)
    cursor = con.cursor()
    cursor.execute(f"SELECT * FROM formula WHERE 수식명 = '{fname}'")
    row = cursor.fetchone()
    con.close()
    if row:
        name, check1, check2, fname, vtype, color, width, style, stg = row
        ui.fm_lineEdittttt_01.setText(name)
        ui.fm_checkBoxxxxx_01.setChecked(check1)
        ui.fm_checkBoxxxxx_02.setChecked(check2)
        ui.fm_comboBoxxxxx_01.setCurrentText(fname)
        ui.fm_comboBoxxxxx_02.setCurrentText(vtype)
        if '#' in color:
            ui.fm_frameeeeeeee_01.setStyleSheet('QWidget { background-color: %s }' % color)
            ui.fm_lineEdittttt_02.setText(color)
        ui.fm_comboBoxxxxx_03.setCurrentText(str(width))
        ui.fm_comboBoxxxxx_04.setCurrentText(dict_style[style])
        ui.fm_textEdittttt_01.clear()
        ui.fm_textEdittttt_01.append(stg)


def formula_button_clicked(ui):
    """수식 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    button_text = ui.dialog_formula.focusWidget().text()

    if button_text == '불러오기':
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()
        cursor.execute("SELECT * FROM formula")
        rows = cursor.fetchall()
        con.close()
        ui.fm_comboBoxxxxx_00.clear()
        name_list = [row[0] for row in rows]
        name_list.sort()
        for name in name_list:
            ui.fm_comboBoxxxxx_00.addItem(name)

    elif button_text == '저장하기':
        name   = ui.fm_lineEdittttt_01.text()
        check1 = 1 if ui.fm_checkBoxxxxx_01.isChecked() else 0
        check2 = 1 if ui.fm_checkBoxxxxx_02.isChecked() else 0
        fname  = ui.fm_comboBoxxxxx_01.currentText()
        vtype  = ui.fm_comboBoxxxxx_02.currentText()
        color  = ui.fm_lineEdittttt_02.text()
        width  = float(ui.fm_comboBoxxxxx_03.currentText())
        style  = int(ui.fm_comboBoxxxxx_04.currentText()[:1])
        stg    = ui.fm_textEdittttt_01.toPlainText()

        if name == '' or stg == '':
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '수식명 또는 수식코드가 공백상태입니다.\n')
            return
        elif name in dict_stg_name.values():
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '글로벌 함수명과 같은 이름을 사용할 수 없습니다.\n')
            return
        elif vtype in ('선:일반', '선:조건') and width > 5:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '실선의 최대크기는 5입니다.\n')
            return
        elif vtype in ('선:일반', '선:조건') and style > 5:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '선 종류 선택이 잘못되었습니다.\n')
            return
        elif vtype == '화살표:일반' and width < 10:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '화살표의 최소크기는 10입니다.\n')
            return
        elif vtype == '화살표:일반' and style < 6:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '화살표의 방향 선택이 잘못되었습니다.\n')
            return
        elif vtype == '화살표:매매' and check2:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '화살표:매매는 전략연산 및 백테에 적용할 수 없습니다.\n')
            return

        if ui.FormulaCodeTest(stg) and ui.proc_chqs.is_alive():
            delete_query  = f"DELETE FROM formula WHERE 수식명 = '{name}'"
            insert_query  = 'INSERT INTO formula VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
            insert_values = (name, check1, check2, fname, vtype, color, width, style, stg)
            ui.queryQ.put(('전략디비', delete_query))
            ui.queryQ.put(('전략디비', insert_query, insert_values))
            QMessageBox.information(ui.dialog_formula, '수식 저장 완료', random.choice(famous_saying))

    elif button_text == '삭제하기':
        name = ui.fm_lineEdittttt_01.text()
        if name == '':
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '삭제할 수식명을 선택하십시오.\n')
            return
        if ui.proc_chqs.is_alive():
            query = f"DELETE FROM formula WHERE 수식명 = '{name}'"
            ui.queryQ.put(('전략디비', query))
            QMessageBox.information(ui.dialog_formula, '수식 삭제 완료', random.choice(famous_saying))
            qtest_qwait(0.5)

            con = sqlite3.connect(DB_STRATEGY)
            cursor = con.cursor()
            cursor.execute("SELECT * FROM formula")
            rows = cursor.fetchall()
            con.close()
            ui.fm_comboBoxxxxx_00.clear()
            name_list = [row[0] for row in rows]
            for name in name_list:
                ui.fm_comboBoxxxxx_00.addItem(name)

    elif button_text == '색상선택':
        from PyQt5.QtCore import QTimer

        def center_dialog():
            parent_center_x = ui.dialog_formula.x() + ui.dialog_formula.width() // 2
            parent_center_y = ui.dialog_formula.y() + ui.dialog_formula.height() // 2
            dialog_x = parent_center_x - dialog.width() // 2
            dialog_y = parent_center_y - dialog.height() // 2
            dialog.move(dialog_x, dialog_y)

        dialog = QColorDialog(ui.dialog_formula)
        dialog.show()
        QTimer.singleShot(10, center_dialog)

        if dialog.exec_() == QColorDialog.Accepted:
            col = dialog.selectedColor()
            ui.fm_frameeeeeeee_01.setStyleSheet('QWidget { background-color: %s }' % col.name())
            ui.fm_lineEdittttt_02.setText(col.name())

    elif button_text == '예제확인':
        text = """# 수식관리자는 로딩된 차트 데이터를 기반으로
# 전략연산과 유사한 방식으로 작동되도록 설계되었으며
# 전략연산과 다르게 매도관련 팩터를 사용할 수 없습니다.
# (수익금, 수익률, 매수가, 보유수량, 매수시간, 보유시간 ...)
# 구간연산값은 항상 틱(봉)수를 만족하지 못할 경우 0이오니
# 구간연산값은 > 0 조건을 넣어 수식을 작성하시길 바랍니다.

# 수식을 작성할 때, 모든 수식의 이전틱(봉)값을 사용할 수 있습니다.
# 수식명(1) 형태로 입력하며 괄호안에 1이상을 입력하여 사용합니다.
# 모든 사용자 수식은 순차적으로 계산되므로 0을 입력할 경우
# 계산되지 않은 값이 리턴될 수 있으므로 사용하지 마십시오. 
# 또한 글로벌에 등록되어 있는 함수명과 같은 수식명을 입력할 수 없습니다.
# 저장 시 자동 필터링 되어 사용 시 경고 메시지가 표시됩니다.

# 차트표시는 DB에서 데이터를 불러와서 표시되는 차트에 표시를 의미하고
# 전략연산 및 백테 적용은 작성한 수식을 매도수 전략코드에
# 적용할 수 있는 설정입니다. 또한 실시간차트에 표시를 의미합니다.


# 선:일반, 고가 라인 표시
# self.line 에는 표시할 선의 값을 입력
self.line = 최고현재가(60)

# 선:조건, 최저현재가 대비 최고현재가 등락율 2%이상
# 발생한 시점에 선을 긋고 유지되며 다시 발생하면 갱신됨.
# self.check 에는 표시할 선의 발생 조건 입력
# self.line 에는 표시할 선의 값을 입력
high_price = 최고현재가(30)
low_price = 최저현재가(30)
if low_price > 0:
    self.check = (high_price / low_price - 1) * 100 >= 2
    self.line = (high_price + low_price) / 2

# 범위, 이동평균위
# self.up 에는 표시할 범위의 상한선
# self.down 에는 표시할 범위의 하한선
이평60 = 이동평균(60)
if 이평60 > 0:
    self.check = 현재가 > 이평60
    self.up = 현재가
    self.down = 이평60

# 화살표:일반, 호가상승압력
# self.check 에 표시할 화살표의 발생 조건 입력
총잔량 = 매수총잔량 + 매도총잔량
if 총잔량 > 0:
    self.check = 매수총잔량 / 총잔량 > 0.7

# 화살표:매매, 이평돌파 및 이탈 매매
# self.buy 에는 매수조건 입력
# self.sell 에는 매도조건 입력
현재이평 = 이동평균(60)
직전이평 = 이동평균(60, 1)
if 데이터길이 >= 61:
    self.buy = 현재가N(1) <= 직전이평 and 현재이평 < 현재가
    self.sell = 현재가N(1) >= 직전이평 and 현재이평 > 현재가
"""
        ui.fm_textEdittttt_01.clear()
        ui.fm_textEdittttt_01.append(text)
