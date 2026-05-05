
import re
from ui.event_activate import activated_stg
from ui.etcetera.etc import auto_back_schedule
from ui.event_click.button_clicked_database import *
from utility.static_method.static import now, qtest_qwait, now_cme
from ui.event_click.button_clicked_stg_editer import backtest_detail
from ui.event_click.button_clicked_backtest_engine import backtest_process_kill
from ui.create_widget.set_style import color_fg_rt, color_fg_dk, color_fg_bt, color_bt_yl


class UpdateTextedit:
    """텍스트 에디터 업데이트 클래스입니다.
    로그 텍스트 에디터를 업데이트하고 데이터베이스 관리를 수행합니다.
    """
    def __init__(self, ui):
        """텍스트 에디터 업데이트를 초기화합니다.
        Args:
            ui: UI 클래스 인스턴스
        """
        self.ui        = ui
        self.data_save = False

    def update_texedit(self, data):
        """텍스트 에디터를 업데이트합니다.
        수신된 데이터를 기반으로 로그 텍스트 에디터에 내용을 추가합니다.
        Args:
            data: 데이터 (데이터 타입, 내용)
        """
        if data[0] == ui_num['종목명데이터']:
            self.ui.dict_name.update(data[1])
            self.ui.dict_code.update(data[2])

        elif data[0] == ui_num['사용자수식']:
            self.ui.fm_list = data[1]
            self.ui.dict_fm = data[2]
            self.ui.fm_tcnt = data[3]
            self.ui.trading = True

        else:
            time_ = str(now())[:-3]
            if '오류' in data[1] or '주문실패' in data[1] or 'Traceback' in data[1] or 'Error' in data[1]:
                self.ui.lgicon_alert = True
                log_ = f'<font color=#ffffa0>{data[1]}</font>'
            else:
                log_ = data[1]
            text = f'[{time_}] {log_}' if '</font>' not in log_ else f'<font color=white>[{time_}]</font> {log_}'

            if data[0] in (ui_num['기본로그'], ui_num['타임로그'], ui_num['시스템로그']):
                self.ui.log.info(re.sub('(<([^>]+)>)', '', text))

            elif data[0] == ui_num['백테스트']:
                if not self.ui.dict_set['백테스트로그기록안함']:
                    self.ui.log.info(re.sub('(<([^>]+)>)', '', text))

            if data[0] == ui_num['기본로그']:
                self.ui.log_trade_basic_textedit.append(text)

            elif data[0] == ui_num['타임로그']:
                self.ui.log_trade_error_textedit.append(text)

            elif data[0] == ui_num['시스템로그']:
                self.ui.log_system_textedit.append(text)

            elif data[0] == ui_num['백테엔진']:
                self.ui.be_textEditxxxx_01.append(text)
                if data[1] == '백테엔진 준비 완료':
                    if not self.ui.qtimer3.isActive():
                        self.ui.qtimer3.start()
                    if self.ui.auto_mode:
                        if self.ui.dialog_backengine.isVisible():
                            self.ui.dialog_backengine.close()
                        qtest_qwait(2)
                        auto_back_schedule(self.ui, 2)

            elif data[0] == ui_num['백테스트']:
                if 'START' in data[1] or '그리드 최적화 시작' in data[1]:
                    self.ui.back_start_time = now()
                elif 'OPTUNA INFO' in data[1]:
                    self.ui.optuna_current_cnt = int(data[1].split('현재횟수[')[1].split(']')[0])
                    self.ui.optuna_remain_cnt  = int(data[1].split('남은횟수[')[1].split(']')[0])

                if ('self.vars' in data[1] and 'MERGE' not in data[1]) or '부트스트랩' in data[1]:
                    color = color_bt_yl
                elif '배팅금액' in data[1] or 'OUT' in data[1] or '결과' in data[1] or '백테스트 시작' in data[1] or \
                        ']단계' in data[1] or '최적값' in data[1]:
                    color = color_fg_rt
                elif ('AP' in data[1] and '-' in data[1].split('AP')[1]) or \
                        ('수익률' in data[1] and '-' in data[1].split('수익률')[1]):
                    color = color_fg_dk
                else:
                    color = color_fg_bt

                if '텍스트에디터 클리어' in data[1]:
                    self.ui.ss_textEditttt_09.clear()

                self.ui.ss_textEditttt_09.setTextColor(color)
                self.ui.ss_textEditttt_09.append(text)

                if '백테스트 엔진 전략연산 오류, 자동 중지 중 ...' in data[1]:
                    backtest_process_kill(self.ui, False, False)

                elif 'COMPLETE' in data[1] or 'STOP' in data[1]:
                    if data[1] in ('최적화O COMPLETE', '최적화OV COMPLETE', '최적화OVC COMPLETE', '최적화B COMPLETE',
                                   '최적화BV COMPLETE', '최적화BVC COMPLETE'):
                        activated_stg.activated_04(self.ui)

                    if data[1] in ('최적화OG COMPLETE', '최적화OGV COMPLETE', '최적화OGVC COMPLETE'):
                        activated_stg.activated_06(self.ui)

                    if not self.ui.dict_set['그래프띄우지않기'] and 'STOP' not in data[1] and data[1] not in \
                            ('백파인더 COMPLETE', '최적화OG COMPLETE', '최적화OGV COMPLETE', '최적화OGVC COMPLETE',
                             '최적화OC COMPLETE', '최적화OCV COMPLETE', '최적화OCVC COMPLETE'):
                        backtest_detail(self.ui)

                    self.ui.ssicon_alert = False
                    self.ui.main_btn_list[2].setIcon(self.ui.icon_stgs)

                    if self.ui.back_schedul:
                        qtest_qwait(3)
                        self.ui.sdButtonClicked_02()

                    self.ui.back_start_time = None
                    self.ui.optuna_current_cnt = 0
                    self.ui.optuna_remain_cnt = 0

            elif data[0] == ui_num['기업개요']:
                self.ui.gg_textEdittttt_01.clear()
                self.ui.gg_textEdittttt_01.append(data[1])

            if '전략연산 프로세스 데이터 저장 중 ...' in text:
                self.data_save = True

            elif data[0] == ui_num['기본로그'] and '전략연산 종료' in data[1]:
                if self.data_save and self.ui.dict_set['디비자동관리']:
                    self._auto_database_control(1)
                else:
                    self._shut_down_check()

            elif '휴무 종료' in data[1]:
                self._shut_down_check(force=True)

            elif data[0] == ui_num['DB관리']:
                if data[1] == 'DB업데이트완료':
                    self.ui.database_control = False
                else:
                    self.ui.db_textEdittttt_01.append(text)

                if self.ui.auto_mode:
                    if '당일DB 데이터, 일자DB로 분리 완료' in data[1]:
                        self._auto_database_control(2)
                    elif '당일DB 데이터, 백테DB로 추가 완료' in data[1]:
                        self._auto_database_control(3)

    def _auto_database_control(self, gubun):
        """데이터베이스 자동 관리를 수행합니다.
        Args:
            gubun: 구분 (1: DB관리 시작, 2: 일자DB 분리, 3: 백테DB 추가)
        """
        if gubun == 1:
            self.ui.auto_mode = True
            if self.ui.dict_set['알림소리']:
                self.ui.soundQ.put('데이터베이스 자동관리를 시작합니다.')
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            qtest_qwait(2)
            dbbutton_clicked_09(self.ui)
        elif gubun == 2:
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            qtest_qwait(2)
            dbbutton_clicked_08(self.ui)
        elif gubun == 3:
            if self.ui.dialog_db.isVisible():
                self.ui.dialog_db.close()
            self.ui.teleQ.put('데이터베이스 자동관리 완료')
            self.ui.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 데이터베이스 자동관리 완료'))
            self.ui.auto_mode = False
            self._shut_down_check()

    def _shut_down_check(self, force=False):
        """시스템 종료 여부를 확인합니다.
        설정에 따라 프로그램 또는 컴퓨터를 종료합니다.
        Args:
            force: 강제 종료 여부
        """
        from utility.static_method.static import str_hms
        if self.ui.dict_set['백테스케쥴실행'] and now().weekday() == self.ui.dict_set['백테스케쥴요일']:
            if self.ui.dict_set['알림소리']:
                self.ui.soundQ.put('오늘은 백테 스케쥴러의 실행이 예약되어 있어 프로그램을 종료하지 않습니다.')
        else:
            if self.ui.dict_set['프로그램종료']:
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(180 * 1000, self.ui.ProcessKill)
            if self.ui.dict_set['컴퓨터종료'] or (
                self.ui.dict_set['휴무컴퓨터종료'] and
                (
                    force or
                    (self.ui.market_gubun < 4 and 90000 < int(str_hms()) < 90500) or
                    (self.ui.market_gubun in (4, 8) and 93000 < int(str_hms(now_cme())) < 93500) or
                    (self.ui.market_gubun == 6 and 84500 < int(str_hms()) < 85000) or
                    (self.ui.market_gubun == 7 and 180000 < int(str_hms()) < 180500)
                )
            ):
                import os
                os.system('shutdown /s /t 300')
