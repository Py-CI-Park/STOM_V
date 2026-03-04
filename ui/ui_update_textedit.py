
import os
import re
from PyQt5.QtCore import QTimer
from ui.set_style import color_fg_rt, color_fg_dk, color_fg_bt, color_bt_yl
from utility.setting import ui_num
from utility.static import now, qtest_qwait, str_hms


class UpdateTextedit:
    def __init__(self, ui):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1      2       3      4       5      6      7       8         9         10     11     12      13       14
        """
        self.ui        = ui
        self.logging   = True
        self.data_save = False

    def update_texedit(self, data):
        if len(data) == 2:
            if '시스템 명령 오류 알림' in data[1]:
                self.ui.lgicon_alert = True
    
            time_ = str(now())[:-7] if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트'], ui_num['C백테스트'], ui_num['CF백테스트']) else str(now())
            log_  = f'<font color=#f7455d>{data[1]}</font>' if '오류' in data[1] else data[1]
            text  = f'[{time_}] {log_}' if '</font>' not in log_ else f'<font color=white>[{time_}]</font> {log_}'

            if data[0] in (ui_num['S로그텍스트'], ui_num['S단순텍스트'], ui_num['C로그텍스트'], ui_num['C단순텍스트']):
                try:
                    self.ui.log.info(text)
                except:
                    pass

            if data[0] == ui_num['S로그텍스트']:
                self.ui.sst_textEditttt_01.append(text)
            elif data[0] == ui_num['S단순텍스트']:
                self.ui.src_textEditttt_01.append(text)
            elif data[0] == ui_num['C로그텍스트']:
                self.ui.cst_textEditttt_01.append(text)
            elif data[0] == ui_num['C단순텍스트']:
                self.ui.crc_textEditttt_01.append(text)
            elif data[0] == ui_num['백테엔진']:
                self.ui.be_textEditxxxx_01.append(text)
                if data[1] == '백테엔진 준비 완료':
                    if not self.ui.qtimer3.isActive():
                        self.ui.qtimer3.start()
                    if self.ui.auto_mode:
                        if self.ui.dialog_backengine.isVisible():
                            self.ui.dialog_backengine.close()
                        qtest_qwait(2)
                        self.ui.AutoBackSchedule(2)

            elif data[0] in (ui_num['S백테스트'], ui_num['SF백테스트'], ui_num['C백테스트'], ui_num['CF백테스트']):
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

                if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                    if '텍스트에디터 클리어' in data[1]:
                        self.ui.ss_textEditttt_09.clear()
                    self.ui.ss_textEditttt_09.setTextColor(color)
                    self.ui.ss_textEditttt_09.append(text)
                else:
                    if '텍스트에디터 클리어' in data[1]:
                        self.ui.cs_textEditttt_09.clear()
                    self.ui.cs_textEditttt_09.setTextColor(color)
                    self.ui.cs_textEditttt_09.append(text)

                if '오류, 자동 중지 중 ...' in data[1]:
                    if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                        self.ui.BacktestProcessKill(False, False)
                    else:
                        self.ui.BacktestProcessKill(True, False)

                if self.ui.dict_set['최적화로그기록안함']:
                    if '백테스트 시작' in data[1] or '인샘플 최적화 시작' in data[1]: self.logging = False
                    elif '최적화 완료' in data[1] or '인샘플 최적화 완료' in data[1]: self.logging = True

                if self.logging: self.ui.log.info(re.sub('(<([^>]+)>)', '', text))

                if 'COMPLETE' in data[1] or 'STOP' in data[1]:
                    if data[1] in ('최적화O COMPLETE', '최적화OV COMPLETE', '최적화OVC COMPLETE', '최적화B COMPLETE',
                                   '최적화BV COMPLETE', '최적화BVC COMPLETE'):
                        if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                            self.ui.sActivated_04()
                        else:
                            self.ui.cActivated_04()

                    if data[1] in ('최적화OG COMPLETE', '최적화OGV COMPLETE', '최적화OGVC COMPLETE'):
                        if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                            self.ui.sActivated_06()
                        else:
                            self.ui.cActivated_06()

                    if not self.ui.dict_set['그래프띄우지않기'] and 'STOP' not in data[1] and data[1] not in \
                            ('백파인더 COMPLETE', '최적화OG COMPLETE', '최적화OGV COMPLETE', '최적화OGVC COMPLETE',
                             '최적화OC COMPLETE', '최적화OCV COMPLETE', '최적화OCVC COMPLETE'):
                        if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                            self.ui.StockBacktestDetail()
                        else:
                            self.ui.CoinBacktestDetail()

                    if data[0] in (ui_num['S백테스트'], ui_num['SF백테스트']):
                        self.ui.ssicon_alert = False
                        self.ui.main_btn_list[2].setIcon(self.ui.icon_stocks)
                    else:
                        self.ui.csicon_alert = False
                        self.ui.main_btn_list[3].setIcon(self.ui.icon_coins)

                    if self.ui.back_schedul:
                        qtest_qwait(3)
                        self.ui.sdButtonClicked_02()

                    self.ui.back_start_time = None
                    self.ui.optuna_current_cnt = 0
                    self.ui.optuna_remain_cnt = 0

            elif data[0] == ui_num['기업개요']:
                self.ui.gg_textEdittttt_01.clear()
                self.ui.gg_textEdittttt_01.append(data[1])

            if '전략연산 프로세스 데이터 저장 중' in text:
                self.data_save = True
            elif data[0] == ui_num['S단순텍스트'] and '에이전트 종료' in data[1]:
                self.ui.wdzservQ.put(('manager', '에이전트 종료'))
            elif data[0] == ui_num['S로그텍스트'] and '트레이더 종료' in data[1]:
                self.ui.wdzservQ.put(('manager', '트레이더 종료'))
            elif data[0] == ui_num['S로그텍스트'] and '전략연산 종료' in data[1]:
                self.ui.wdzservQ.put(('manager', '전략연산 종료'))
                if self.data_save and self.ui.dict_set['디비자동관리']:
                    self.AutoDataBase(1)
                else:
                    self.StockShutDownCheck()
            elif data[0] == ui_num['C단순텍스트'] and '리시버 종료' in data[1]:
                if self.ui.CoinReceiverProcessAlive():
                    self.ui.proc_receiver_coin.kill()
            elif data[0] == ui_num['C로그텍스트'] and '트레이더 종료' in data[1]:
                if self.ui.CoinTraderProcessAlive():
                    self.ui.proc_trader_coin.kill()
            elif data[0] == ui_num['C로그텍스트'] and '전략연산 종료' in data[1]:
                if self.ui.CoinStrategyProcessAlive():
                    self.ui.proc_strategy_coin.kill()
                if self.data_save and self.ui.dict_set['디비자동관리']:
                    self.AutoDataBase(4)
                else:
                    self.CoinShutDownCheck()
            elif data[0] == ui_num['S단순텍스트'] and '해외선물 휴무 종료' in data[1]:
                self.StockShutDownCheck()
            elif data[0] == ui_num['DB관리']:
                if data[1] == 'DB업데이트완료':
                    self.ui.database_control = False
                else:
                    self.ui.db_textEdittttt_01.append(text)
                if self.ui.auto_mode:
                    if data[1] in ('주식 일자별 DB 생성 완료', '해선 일자별 DB 생성 완료'):
                        self.AutoDataBase(2)
                    elif data[1] in ('주식 당일 데이터 백테디비로 추가 완료', '해선 당일 데이터 백테디비로 추가 완료'):
                        self.AutoDataBase(3)
                    elif data[1] == '코인 일자별 DB 생성 완료':
                        self.AutoDataBase(5)
                    elif data[1] == '코인 당일 데이터 백테디비로 추가 완료':
                        self.AutoDataBase(6)
        elif len(data) == 3:
            self.ui.dict_name = data[1]
            self.ui.dict_code = data[2]

    def AutoDataBase(self, gubun):
        if gubun == 1:
            self.ui.auto_mode = True
            if self.ui.dict_set['주식알림소리']:
                self.ui.soundQ.put('데이터베이스 자동관리를 시작합니다.')
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            self.ui.sdb_tapWidgettt_01.setCurrentIndex(self.ui.sdb_index1)
            qtest_qwait(2)
            self.ui.dbButtonClicked_08()
        elif gubun == 2:
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            self.ui.sdb_tapWidgettt_01.setCurrentIndex(self.ui.sdb_index1)
            qtest_qwait(2)
            self.ui.dbButtonClicked_07()
        elif gubun == 4:
            self.ui.auto_mode = True
            if self.ui.dict_set['코인알림소리']:
                self.ui.soundQ.put('데이터베이스 자동관리를 시작합니다.')
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            self.ui.sdb_tapWidgettt_01.setCurrentIndex(self.ui.sdb_index2)
            qtest_qwait(2)
            self.ui.dbButtonClicked_16()
        elif gubun == 5:
            if not self.ui.dialog_db.isVisible():
                self.ui.dialog_db.show()
            self.ui.sdb_tapWidgettt_01.setCurrentIndex(self.ui.sdb_index2)
            qtest_qwait(2)
            self.ui.dbButtonClicked_15()
        elif gubun in (3, 6):
            if self.ui.dialog_db.isVisible():
                self.ui.dialog_db.close()
            self.ui.teleQ.put('데이터베이스 자동관리 완료')
            self.ui.logger.info('데이터베이스 자동관리 완료')
            qtest_qwait(2)
            self.ui.auto_mode = False
            if gubun == 3:
                self.StockShutDownCheck()
            else:
                self.CoinShutDownCheck()

    def StockShutDownCheck(self):
        if self.ui.dict_set['백테스케쥴실행'] and now().weekday() == self.ui.dict_set['백테스케쥴요일']:
            if self.ui.dict_set['주식알림소리']:
                self.ui.soundQ.put('오늘은 백테 스케쥴러의 실행이 예약되어 있어 프로그램을 종료하지 않습니다.')
        else:
            if self.ui.dict_set['프로그램종료']:
                QTimer.singleShot(180 * 1000, self.ui.ProcessKill)
            if self.ui.dict_set['주식컴퓨터종료'] or \
                    ('키움증권' in self.ui.dict_set['증권사'] and 90000 < int(str_hms()) < 90500 and self.ui.dict_set['휴무컴퓨터종료']) or \
                    ('해외선물' in self.ui.dict_set['증권사'] and 213000 < int(str_hms()) < 233000 and self.ui.dict_set['휴무컴퓨터종료']):
                os.system('shutdown /s /t 300')

    def CoinShutDownCheck(self):
        if self.ui.dict_set['백테스케쥴실행'] and now().weekday() == self.ui.dict_set['백테스케쥴요일']:
            if self.ui.dict_set['코인알림소리']:
                self.ui.soundQ.put('오늘은 백테 스케쥴러의 실행이 예약되어 있어 프로그램을 종료하지 않습니다.')
        else:
            if self.ui.dict_set['프로그램종료']:
                QTimer.singleShot(180 * 1000, self.ui.ProcessKill)
            if self.ui.dict_set['코인컴퓨터종료']:
                os.system('shutdown /s /t 300')
