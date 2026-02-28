
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from strategy.microstructure_analyzer import MicrostructureAnalyzer


# noinspection PyUnresolvedReferences, PyTypeChecker
def example_realtime_simulation():
    try:
        conn = sqlite3.connect('../_database/stock_tick_back.db')
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        stock_codes = df['name'].to_list()
        while True:
            selected_stock = np.random.choice(stock_codes)
            df = pd.read_sql(f"SELECT * FROM '{selected_stock}'", conn)
            lastday = int(str(df['index'].iloc[-1])[:8]) * 1000000
            df = df[df['index'] >= lastday]
            if len(df[df['관심종목'] == 1]) > len(df) * 0.7:
                break

        print(f"선택된 종목: {selected_stock}")
        conn.close()

        df['idx'] = df['index']
        df.set_index('idx', inplace=True)
        data_array = np.array(df)

        print(f"데이터 로딩 완료: {len(data_array)}개 틱")

        trade_list = []
        max_capital = 100000000  # 1억
        microstructure_strategy = MicrostructureAnalyzer()

        print(f"\n=== 배팅 시뮬레이션 (최대 자본금: {max_capital:,}원) ===")
        
        total_profit_loss = 0
        win_trades = 0
        lose_trades = 0
        capital_used = 0
        current_position = None
        trade_count = 0
        two_way = False

        last = len(data_array) - 1
        for i, row in enumerate(data_array):
            current_price = row[1]
            orderbook_data = np.array([
                row[28], row[29], row[30], row[31], row[32],  # 매수호가1-5
                row[27], row[26], row[25], row[24], row[23],  # 매도호가1-5 (역순)
                row[38], row[39], row[40], row[41], row[42],  # 매수잔량1-5
                row[37], row[36], row[35], row[34], row[33]   # 매도잔량1-5 (역순)
            ])

            volume_data = np.array(([
                row[14],    # 매수수량
                row[15]     # 매도수량
            ]))

            signal, confidence = microstructure_strategy.analyze_microstructure_signal(selected_stock, orderbook_data, volume_data)

            final_signal = 'HOLD'
            final_confidence = 0.5
            if confidence >= 0.7:
                final_signal = signal
                final_confidence = confidence

            if current_position is None and final_signal != 'HOLD' and i != last:
                base_position_size = 0.20 * final_confidence
                bet_amount = max_capital * base_position_size
                should_entry = False

                if two_way or final_signal == 'BUY':
                    print("=" * 60)
                    print(f"[진입신호] {final_signal}, 신뢰도: {final_confidence:.3f}")
                    should_entry = True

                if should_entry:
                    print(f"[진입실행] 포지션 크기: {base_position_size:.3f}, 베팅액: {bet_amount:,.0f}원 @ {current_price:.0f}원")
                    current_position = {
                        'action': final_signal,
                        'price': current_price,
                        'amount': bet_amount,
                        'tick': i,
                        'confidence': final_confidence,
                        'entry_index': row[0]
                    }
                    capital_used += bet_amount

            elif current_position is not None:
                current_date = str(int(row[0]))[:8]
                next_date = str(int(data_array[i+1, 0]))[:8] if i < last else current_date

                should_close = False
                close_reason = ""

                if current_date != next_date:
                    should_close = True
                    close_reason = "일자청산"
                elif (current_position['action'] == 'BUY' and final_signal == 'SELL') or \
                        (current_position['action'] == 'SELL' and final_signal == 'BUY'):
                    print(f"[청산신호] {final_signal}, 신뢰도: {final_confidence:.3f}")
                    should_close = True
                    close_reason = "신호청산"

                if should_close:
                    trade_count += 1

                    if current_position['action'] == 'BUY':
                        actual_return = (current_price - current_position['price']) / current_position['price']
                        actual_return -= 0.003
                    else:
                        actual_return = (current_position['price'] - current_price) / current_position['price']
                        actual_return -= 0.003

                    profit_loss = current_position['amount'] * actual_return
                    total_profit_loss += profit_loss

                    if profit_loss > 0:
                        win_trades += 1
                    else:
                        lose_trades += 1

                    hold_ticks = i - current_position['tick']
                    buy_time = str(int(current_position['entry_index']))
                    buy_time = f'{buy_time[:4]}-{buy_time[4:6]}-{buy_time[6:8]} {buy_time[8:10]}:{buy_time[10:12]}:{buy_time[12:14]}'
                    sell_time = str(int(row[0]))
                    sell_time = f'{sell_time[:4]}-{sell_time[4:6]}-{sell_time[6:8]} {sell_time[8:10]}:{sell_time[10:12]}:{sell_time[12:14]}'

                    trade_list.append(
                        f"거래 #{trade_count}: {current_position['action']} "
                        f"{current_position['amount']:,.0f}원 "
                        f"@ {current_position['price']:.0f}원 → {current_price:.0f}원 "
                        f"({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원 "
                        f"(보유: {hold_ticks}틱, 진입:{buy_time}, 청산:{sell_time}, {close_reason})"
                    )

                    print(f"[{close_reason}] {current_position['amount']:,.0f}원 @{current_position['price']:.0f}원 → {current_price:.0f}원 ({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원")
                    print(f"진행률: {i + 1}/{len(data_array)} ({(i + 1) / len(data_array) * 100:.2f}%)")

                    current_position = None
                    continue

            if i == last and current_position is not None:
                trade_count += 1

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
                    f"거래 #{trade_count}: {current_position['action']} "
                    f"{current_position['amount']:,.0f}원 "
                    f"@ {current_position['price']:.0f}원 → {current_price:.0f}원 "
                    f"({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원 "
                    f"(보유: {hold_ticks}틱, 진입:{buy_time}, 청산:{sell_time}, 일자청산)"
                )

                print(f"[마감청산] {current_position['amount']:,.0f}원 @{current_position['price']:.0f}원 → {current_price:.0f}원 ({actual_return * 100:+.2f}%) = {profit_loss:+,.0f}원")

        print(f"\n=== 거래 결과 ===")
        for trade in trade_list:
            print(trade)

        final_capital = max_capital + total_profit_loss
        total_return_pct = (total_profit_loss / max_capital) * 100
        win_rate = win_trades / trade_count * 100 if trade_count > 0 else 0
        
        print(f"\n=== 최종 배팅 결과 ===")
        print(f"초기 자본금: {max_capital:,}원")
        print(f"최종 자본금: {final_capital:,.0f}원")
        print(f"총 수익/손실: {total_profit_loss:+,.0f}원 ({total_return_pct:+.2f}%)")
        print(f"승률: {win_rate:.1f}% ({win_trades}승 / {lose_trades}패)")
        print(f"평균 포지션 크기: {capital_used/trade_count:,.0f}원" if trade_count > 0 else "평균 포지션 크기: 0원")
        print(f"총 거래 횟수: {trade_count}회")
        
    except:
        print_exc()


if __name__ == "__main__":
    print("시장미시구조 분석 시뮬레이션")
    print("=" * 60)
    
    example_realtime_simulation()
