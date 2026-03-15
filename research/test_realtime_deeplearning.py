
import sqlite3
from datetime import datetime
from utility.lazy_imports import get_np, get_pd
from research.realtime_deeplearning import RealtimeDeeplearning


def main(count: int = 10, buyper: float = 1.0, confidence: float = 0.6, betting: int = 20_000_000,
         lookahead: int = 60, predahead: int = 10, test_mode: bool = False, db_file: str = None):

    """메인 실행 - 다종목 실시간 시뮬레이션"""

    print("📈 실시간 딥러닝 예측 시스템 테스트 시작")
    print()

    code_list = []
    data_list = []

    if db_file is None:
        conn = sqlite3.connect('../_database/stock_tick_back.db')
        dict_cn = {}
        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        codes = df['name'].to_list()
        codes.remove('moneytop')
        if 'stockinfo' in codes:
            codes.remove('stockinfo')
            dict_cn = get_pd().read_sql(f"SELECT * FROM stockinfo", conn).set_index('index')
            dict_cn = dict_cn['종목명'].to_dict()
        if 'futureinfo' in codes:
            codes.remove('futureinfo')

        while True:
            selected_code = get_np().random.choice(codes)
            codes.remove(selected_code)
            df = get_pd().read_sql(f"SELECT * FROM '{selected_code}' WHERE `index` >= 20250501000000", conn)
            if not df.empty:
                lastday = int(str(df['index'].iloc[-1])[:8])
                df = df[df['index'] >= lastday * 1000000]
                code_list.append(selected_code)
                data_list.append(get_np().array(df))
                print(f"선택종목 [{selected_code}] {dict_cn.get(selected_code)}")
                if len(code_list) == count:
                    break
    else:
        conn = sqlite3.connect(f'../_database/{db_file}.db')
        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        codes = df['name'].to_list()
        codes.remove('moneytop')
        count = len(codes)
        for i, code in enumerate(codes):
            df = get_pd().read_sql(f"SELECT * FROM '{code}'", conn)
            code_list.append(code)
            data_list.append(get_np().array(df))
            print(f"데이터로딩 [{code}], 길이[{len(df)}], [{ i +1}/{count}]")

    conn.close()

    # 시스템 초기화
    trader = RealtimeDeeplearning(buyper, confidence, betting, lookahead, predahead, test_mode)

    k = 0
    start = datetime.now()
    len_list = [len(arry) for arry in data_list]
    max_len = max(len_list)
    for i in range(max_len):
        for j in range(count):
            code = code_list[j]
            if i >= len_list[j]:
                continue
            # 실시간 처리
            k += 1
            tick_data = data_list[j][i, :]
            last = i == len_list[j] - 1 or str(data_list[j][i, 0])[:8] != str(data_list[j][ i + 1, 0])[:8]
            trader.update_realtime_tick_data(code, tick_data, i, last=last)

        if i % 100 == 0:
            print(f"{datetime.now()} - 진행 상황 [{ i +1}/{max_len}]")

    end = datetime.now()
    laft = (end - start).total_seconds()

    final_stats = trader.get_portfolio_stats(buyper)

    # 모델별 성능 출력
    if final_stats['total_preds'] > 0:
        print(f"\n📊 모델 성능 평가")
        print(f" - 초당 처리 틱수: {k / laft:.0f} t/s")
        print(f" - 전체 예측 횟수: {final_stats['total_preds']:,}")
        if 'buy_direction_accuracy' in final_stats:
            acc = final_stats['buy_direction_accuracy']
            err = final_stats['buy_mean_error']
            rmse = final_stats['buy_rmse']
            print(f" - {buyper}% 이상 예측 횟수: {final_stats['total_buy_preds']:,}\n"
                  f" - 방향성 {acc:>5.2f}% | 평균오차 {err:>4.2f}% | RMSE {rmse:>4.2f}%")

    if len(trader.trade) > 0:
        print(f"\n📈 백테스트 결과:")
        plus_cnt = len([x[0] for x in trader.trade if x[0] >= 0])
        minus_cnt = len([x[0] for x in trader.trade if x[0] < 0])
        t_cnt = plus_cnt + minus_cnt
        p_ratio = round(plus_cnt / (plus_cnt + minus_cnt) * 100, 2) if (plus_cnt + minus_cnt) > 0 else 0.0
        avg_hold = int(get_np().mean([x[2] for x in trader.trade]))
        t_per = sum([x[0] for x in trader.trade])
        t_sig = sum([x[1] for x in trader.trade])

        plus_cnt1 = len([x[0] for x in trader.trade if x[0] >= 0 and x[-1] >= 1.0])
        minus_cnt1 = len([x[0] for x in trader.trade if x[0] < 0 and x[-1] >= 1.0])
        t_cnt1 = plus_cnt1 + minus_cnt1
        p_ratio1 = round(plus_cnt1 / (plus_cnt1 + minus_cnt1) * 100, 2) if (plus_cnt1 + minus_cnt1) > 0 else 0.0
        # noinspection PyTypeChecker
        avg_hold1 = int(max(0, get_np().mean([x[2] for x in trader.trade if x[-1] >= 1.0])))
        t_per1 = sum([x[0] for x in trader.trade if x[-1] >= 1.0])
        t_sig1 = sum([x[1] for x in trader.trade if x[-1] >= 1.0])

        plus_cnt2 = len([x[0] for x in trader.trade if x[0] >= 0 and x[-1] >= 2])
        minus_cnt2 = len([x[0] for x in trader.trade if x[0] < 0 and x[-1] >= 2])
        t_cnt2 = plus_cnt2 + minus_cnt2
        p_ratio2 = round(plus_cnt2 / (plus_cnt2 + minus_cnt2) * 100, 2) if (plus_cnt2 + minus_cnt2) > 0 else 0.0
        # noinspection PyTypeChecker
        avg_hold2 = int(max(0, get_np().mean([x[2] for x in trader.trade if x[-1] >= 2])))
        t_per2 = sum([x[0] for x in trader.trade if x[-1] >= 2])
        t_sig2 = sum([x[1] for x in trader.trade if x[-1] >= 2])

        gubun1, gubun2, gubun3 = f'{buyper}%이상', '1.0%이상', '2.0이상'
        print(f"거래구분: {gubun1:>12} | {gubun2:>12} | {gubun3:>12} |")
        print(f"거래횟수: {t_cnt:>13,} | {t_cnt1:>13,} | {t_cnt2:>13,} |")
        print(f"익절횟수: {plus_cnt:>13,} | {plus_cnt1:>13,} | {plus_cnt2:>13,} |")
        print(f"손절횟수: {minus_cnt:>13,} | {minus_cnt1:>13,} | {minus_cnt2:>13,} |")
        print(f"전체승률: {p_ratio:>13.2f} | {p_ratio1:>13.2f} | {p_ratio2:>13.2f} |")
        print(f"보유시간: {avg_hold:>13,.0f} | {avg_hold1:>13,.0f} | {avg_hold2:>13,.0f} |")
        print(f"총수익률: {t_per:>+13.2f} | {t_per1:>13.2f} | {t_per2:>13.2f} |")
        print(f"총수익금: {t_sig:>+13,} | {t_sig1:>13,} | {t_sig2:>13,} |")

    print(f"\n🎉 실시간 딥러닝 예측 시스템 테스트 완료!")


if __name__ == "__main__":
    main(
        count=50,               # 종목 로딩 개수
        buyper=0.5,             # 진입 예측 등락율
        confidence=0.6,         # 진입 신뢰도 제한
        betting=20_000_000,     # 종목당 배팅금액
        lookahead=60,           # 학습 구간
        predahead=10,           # 예측 구간
        test_mode=True,         # 테스트 모드 -> 백테스트
    )
