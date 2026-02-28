
"""
시장 미시구조 분석 시뮬레이션 테스트

이 모듈은 MicrostructureAnalyzer를 사용한 실시간 거래 시뮬레이션을 제공합니다:
- 실제 과거 데이터를 기반으로 한 백테스팅
- 동적 포지션 크기 조절
- 다양한 청산 조건 (일자청산, 신호청산)
- 수수료 반영한 수익률 계산
- 상세한 거래 기록 및 성과 분석

사용법:
python test_strategy_manager.py
"""

import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from strategy.strategy_manager import StrategyManager


def example_realtime_simulation(market_type: str = 'stock', data_type: str = 'tick',
                                buy_cfd_limit: float = 0.75, sell_cfd_limit: float = 0.65):
    """실시간 거래 시뮬레이션
    
    과거 데이터를 사용하여 MicrostructureAnalyzer의 성능을 테스트합니다.
    """
    try:
        # 데이터베이스 연결 및 종목 목록 조회
        conn = sqlite3.connect(f'../_database/{market_type}_{data_type}_back.db')
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)

        stock_codes = df['name'].to_list()
        stock_codes.remove('moneytop')
        stock_codes.remove('stockinfo')

        df_cn = pd.read_sql(f"SELECT * FROM stockinfo", conn).set_index('index')
        df_cn = df_cn['종목명'].to_dict()

        selected_stock = np.random.choice(stock_codes)
        df = pd.read_sql(f"SELECT * FROM '{selected_stock}'", conn)
        conn.close()

        # 데이터를 numpy 배열로 변환 (속도 최적화)
        data_array = np.array(df)

        print(f"데이터 로딩 완료: {len(data_array)}개 틱")

        # 시뮬레이션 설정
        trade_list = []             # 거래 기록 저장
        max_capital = 100000000     # 최대 자본금 (1억)

        strategy_manager = StrategyManager(market_type, data_type)

        print(f"\n=== 배팅 시뮬레이션 (최대 자본금: {max_capital:,}원) ===")
        
        # 성과 추적 변수
        total_profit_loss = 0
        win_trades = 0
        lose_trades = 0
        capital_used = 0
        current_position = {}
        trade_count = 0
        two_way = False  # 양방향 거래 여부 (False: 매수만)

        last = len(data_array) - 1
        # 메인 시뮬레이션 루프
        for i, row in enumerate(data_array):
            current_price = row[1]  # 현재가

            # 미시구조 분석 신호 생성
            signal, confidence = strategy_manager.get_signal_date(selected_stock, row)

            final_signal = 'HOLD'
            final_confidence = 0.5
            if (signal == 'BUY' and confidence >= buy_cfd_limit) or \
                    (signal == 'SELL' and confidence >= sell_cfd_limit):
                final_signal = signal
                final_confidence = confidence

            # 진입 로직 (포지션이 없고 신호가 있을 경우)
            if not current_position and final_signal != 'HOLD' and i != last:
                # 동적 포지션 크기 계산 (신뢰도에 비례)
                base_position_size = 0.20 * final_confidence / buy_cfd_limit
                bet_amount = max_capital * base_position_size
                should_entry = False

                # 양방향 거래 또는 매수 신호일 경우에만 진입
                if two_way or final_signal == 'BUY':
                    print("=" * 60)
                    print(f"[진입신호] {final_signal}, 신뢰도: {final_confidence:.3f}")
                    should_entry = True

                if should_entry:
                    print(f"[진입실행] 포지션 크기: {base_position_size:.3f}, 베팅액: {bet_amount:,.0f}원 @ {current_price:.0f}원")
                    # 포지션 정보 저장
                    current_position = {
                        'action': final_signal,
                        'price': current_price,
                        'amount': bet_amount,
                        'tick': i,
                        'confidence': final_confidence,
                        'entry_index': row[0]
                    }
                    capital_used += bet_amount

            elif current_position:
                # 청산 로직 (포지션이 있을 경우)
                current_date = str(int(row[0]))[:8]
                next_date = str(int(data_array[i+1, 0]))[:8] if i < last else current_date

                should_close = False
                close_reason = ""

                # 일자청산: 날짜가 바뀌면 무조건 청산
                if current_date != next_date:
                    should_close = True
                    close_reason = "일자청산"
                # 신호청산: 반대 신호가 발생하면 청산
                elif (current_position['action'] == 'BUY' and final_signal == 'SELL') or \
                        (current_position['action'] == 'SELL' and final_signal == 'BUY'):
                    print(f"[청산신호] {final_signal}, 신뢰도: {final_confidence:.3f}")
                    should_close = True
                    close_reason = "신호청산"

                if should_close:
                    trade_count += 1

                    # 수익률 계산 (수수료 0.3% 반영)
                    if current_position['action'] == 'BUY':
                        actual_return = (current_price - current_position['price']) / current_position['price']
                        actual_return -= 0.3  # 매수/매도 수수료
                    else:
                        actual_return = (current_position['price'] - current_price) / current_position['price']
                        actual_return -= 0.3  # 매수/매도 수수료

                    profit_loss = current_position['amount'] * actual_return
                    total_profit_loss += profit_loss

                    # 승/패 기록
                    if profit_loss > 0:
                        win_trades += 1
                    else:
                        lose_trades += 1

                    # 거래 정보 계산
                    hold_ticks = i - current_position['tick']
                    buy_time = str(int(current_position['entry_index']))
                    buy_time = f'{buy_time[:4]}-{buy_time[4:6]}-{buy_time[6:8]} {buy_time[8:10]}:{buy_time[10:12]}:{buy_time[12:14]}'
                    sell_time = str(int(row[0]))
                    sell_time = f'{sell_time[:4]}-{sell_time[4:6]}-{sell_time[6:8]} {sell_time[8:10]}:{sell_time[10:12]}:{sell_time[12:14]}'

                    # 거래 기록 저장
                    trade_list.append(
                        f"거래 #{trade_count:>2}: {current_position['action']} "
                        f"{current_position['amount']:,.0f}원 | "
                        f"{current_position['price']:>6.0f}원 → {current_price:>6.0f}원 "
                        f"({actual_return * 100:>+6.2f}%) = {profit_loss:>+10,.0f}원 | "
                        f"보유: {hold_ticks:>4}틱 | 진입:{buy_time} | 청산:{sell_time}, {close_reason})"
                    )

                    print(f"[{close_reason}] {current_position['amount']:,.0f}원 @{current_position['price']:.0f}원 → {current_price:.0f}원 ({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원")
                    print(f"진행률: {i + 1}/{len(data_array)} ({(i + 1) / len(data_array) * 100:.2f}%)")

                    if close_reason == "일자청산":
                        strategy_manager.clear_data()
                    current_position = None
                    continue

            # 마감청산: 마지막까지 포지션이 남아있으면 강제 청산
            if i == last and current_position:
                trade_count += 1

                # 수익률 계산 (수수료 0.3% 반영)
                if current_position['action'] == 'BUY':
                    actual_return = (data_array[-1][1] - current_position['price']) / current_position['price']
                    actual_return -= 0.003
                else:
                    actual_return = (current_position['price'] - data_array[-1][1]) / current_position['price']
                    actual_return -= 0.003

                profit_loss = current_position['amount'] * actual_return
                total_profit_loss += profit_loss

                if profit_loss > 0:
                    win_trades += 1
                else:
                    lose_trades += 1

                hold_ticks = len(data_array) - 1 - current_position['tick']
                buy_time = str(int(current_position['entry_index']))
                buy_time = f'{buy_time[:4]}-{buy_time[4:6]}-{buy_time[6:8]} {buy_time[8:10]}:{buy_time[10:12]}:{buy_time[12:14]}'
                sell_time = str(int(row[0]))
                sell_time = f'{sell_time[:4]}-{sell_time[4:6]}-{sell_time[6:8]} {sell_time[8:10]}:{sell_time[10:12]}:{sell_time[12:14]}'

                trade_list.append(
                    f"거래 #{trade_count:>2}: {current_position['action']} "
                    f"{current_position['amount']:,.0f}원 | "
                    f"{current_position['price']:>6.0f}원 → {current_price:>6.0f}원 "
                    f"({actual_return * 100:>+6.2f}%) = {profit_loss:>+10,.0f}원 | "
                    f"보유: {hold_ticks:>4}틱 | 진입:{buy_time} | 청산:{sell_time}, 일자청산)"
                )

                print(f"[마감청산] {current_position['amount']:,.0f}원 @{current_position['price']:.0f}원 → {current_price:.0f}원 ({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원")

        # 최종 결과 출력
        print(f"\n=== 거래 결과 ===")
        for trade in trade_list:
            print(trade)

        # 성과 지표 계산
        final_capital = max_capital + total_profit_loss
        total_return_pct = (total_profit_loss / max_capital) * 100
        win_rate = win_trades / trade_count * 100 if trade_count > 0 else 0
        
        print(f"\n=== 최종 배팅 결과 ===")
        print(f"선택된 종목: [{selected_stock}] {df_cn.get(selected_stock)}")
        print(f"초기 자본금: {max_capital:,}원")
        print(f"최종 자본금: {final_capital:,.0f}원")
        print(f"총 수익/손실: {total_profit_loss:+,.0f}원 ({total_return_pct:+.2f}%)")
        print(f"승률: {win_rate:.1f}% ({win_trades}승 / {lose_trades}패)")
        print(f"평균 포지션 크기: {capital_used/trade_count:,.0f}원" if trade_count > 0 else "평균 포지션 크기: 0원")
        print(f"총 거래 횟수: {trade_count}회")

    except:
        # 에러 발생 시 상세 정보 출력
        print_exc()


if __name__ == "__main__":
    print("시장미시구조 분석 시뮬레이션")
    print("=" * 60)
    
    example_realtime_simulation('stock', 'tick', 0.75, 0.65)
