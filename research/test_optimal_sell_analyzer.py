"""
최적 매도 타이밍 분석기 테스트

실제 과거 데이터를 사용하여 OptimalSellAnalyzer의 성능을 테스트합니다.
- 10개 종목의 마지막 거래일 데이터 로드
- 지정틱에서 무조건 매수 가정
- 각 종목별 최적 매도 타이밍 분석 및 결과 비교
"""

import sqlite3
from traceback import print_exc
from research.optimal_sell_analyzer import OptimalSellAnalyzer
from utility.lazy_imports import get_np, get_pd


def test_optimal_sell_analyzer(market_type: str = 'stock', num_stocks: int = 10, buy_tick_offset: int = 100, signal_only: bool = False):
    """
    최적 매도 타이밍 분석기 테스트
    
    Args:
        market_type: 시장 종류 ('stock', 'coin', 'future')
        num_stocks: 테스트할 종목 수
        buy_tick_offset: 매수 타이밍 (데이터 시작으로부터의 틱 수)
        signal_only: 신호만으로 매도할지 여부 (True=신호만, False=손절/익절 포함)
    """
    try:
        print(f"=== 최적 매도 타이밍 분석기 테스트 ({market_type}) ===")
        print(f"테스트 모드: {'신호 전용' if signal_only else '신호+손절/익절'}")
        print(f"테스트 종목 수: {num_stocks}개")
        print(f"매수 타이밍: {buy_tick_offset}번째 틱")
        
        # 데이터베이스 연결 및 종목 목록 조회
        conn = sqlite3.connect(f'../_database/{market_type}_tick_back.db')
        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        
        stock_codes = df['name'].to_list()
        # 시스템 테이블 제외
        system_tables = ['moneytop', 'stockinfo']
        stock_codes = [code for code in stock_codes if code not in system_tables]
        
        # 종목 정보 조회 (주식인 경우)
        stock_names = {}
        if market_type == 'stock':
            try:
                df_cn = get_pd().read_sql(f"SELECT * FROM stockinfo", conn).set_index('index')
                stock_names = df_cn['종목명'].to_dict()
            except:
                print("종목명 정보를 불러올 수 없습니다.")
        
        # 랜덤으로 종목 선택
        selected_stocks = get_np().random.choice(stock_codes, min(num_stocks, len(stock_codes)), replace=False)
        
        print(f"선택된 종목: {len(selected_stocks)}개")
        
        # 분석기 초기화
        analyzer = OptimalSellAnalyzer(market_type=market_type)
        
        # 결과 저장
        test_results = []
        
        for i, stock_code in enumerate(selected_stocks):
            try:
                print(f"\n{'='*60}")
                print(f"[{i+1}/{len(selected_stocks)}] {stock_code} {stock_names.get(stock_code, '')}")
                print(f"{'='*60}")
                
                # 종목별 데이터 로드
                df = get_pd().read_sql(f"SELECT * FROM '{stock_code}'", conn)
                lastday = int(str(df['index'].iloc[-1])[:8])
                df = df[df['index'] >= lastday * 1000000]
                data_array = get_np().array(df)
                
                if len(data_array) < buy_tick_offset + 50:
                    print(f"데이터 부족: {len(data_array)}개 틱 (필요: {buy_tick_offset + 50}개 이상)")
                    continue
                
                print(f"데이터 로드: {len(data_array)}개 틱")
                
                # 매수 시점 설정 (buy_tick_offset에서 매수)
                buy_tick = buy_tick_offset
                if buy_tick >= len(data_array):
                    buy_tick = len(data_array) // 2
                
                entry_price = data_array[buy_tick, 1]  # 현재가 칼럼
                entry_time = buy_tick
                
                print(f"매수 시점: {buy_tick}번째 틱")
                print(f"매수 가격: {entry_price:,.0f}원")
                
                # 분석기 데이터 초기화
                analyzer.data_buffers = {}  # 데이터 초기화
                
                # 매수 시점까지 데이터 업데이트
                for j in range(buy_tick + 1):
                    analyzer.update_data(stock_code, data_array[j])
                
                # 실시간 매도 시뮬레이션 (매수 후 틱별로 매도 신호 확인)
                position_open = True
                sell_results = []
                
                for j in range(buy_tick + 1, len(data_array)):
                    if not position_open:
                        break
                    
                    # 현재 틱 데이터 업데이트
                    analyzer.update_data(stock_code, data_array[j])
                    
                    # 매도 타이밍 분석
                    result = analyzer.analyze_sell_timing(stock_code, entry_price, entry_time)
                    
                    current_price = data_array[j, 1]
                    profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    # 매도 조건 확인
                    should_sell = False
                    sell_reason = ""
                    
                    if result['recommendation'] in ['STRONG_SELL', 'SELL']:
                        should_sell = True
                        sell_reason = f"매도신호({result['recommendation']})"
                    elif result['sell_score'] >= 0.7:  # 매도 점수 0.7 이상
                        should_sell = True
                        sell_reason = f"고점수({result['sell_score']:.3f})"
                    
                    # 신호만 사용하는 모드가 아니면 손절/익절 조건 추가
                    if not signal_only:
                        if profit_loss_pct >= 3.0:  # 수익률 3% 이상
                            should_sell = True
                            sell_reason = f"수익실현({profit_loss_pct:+.2f}%)"
                        elif profit_loss_pct <= -2.0:  # 손실률 2% 이상
                            should_sell = True
                            sell_reason = f"손절매({profit_loss_pct:+.2f}%)"
                    
                    # 매도 실행
                    if should_sell or j == len(data_array) - 1:  # 마지막 틱이면 강제 매도
                        if j == len(data_array) - 1 and not should_sell:
                            sell_reason = "마감청산"
                        
                        print(f"\n--- 매도 실행 ---")
                        print(f"매도 사유: {sell_reason}")
                        print(f"매도 가격: {current_price:,.0f}원")
                        print(f"수익률: {profit_loss_pct:+.2f}%")
                        print(f"보유 기간: {j - buy_tick}틱")
                        print(f"매도 점수: {result['sell_score']:.3f}")
                        print(f"추천: {result['recommendation']}")
                        print(f"신뢰도: {result['confidence']:.3f}")
                        
                        sell_results.append({
                            'sell_tick': j,
                            'sell_price': current_price,
                            'profit_loss_pct': profit_loss_pct,
                            'sell_score': result['sell_score'],
                            'recommendation': result['recommendation'],
                            'confidence': result['confidence'],
                            'sell_reason': sell_reason,
                            'holding_ticks': j - buy_tick
                        })

                        break
                
                # 결과 저장
                if sell_results:
                    sell_result = sell_results[0]  # 첫 번째 매도 결과
                    
                    test_results.append({
                        'stock_code': stock_code,
                        'stock_name': stock_names.get(stock_code, ''),
                        'entry_price': entry_price,
                        'sell_price': sell_result['sell_price'],
                        'profit_loss_pct': sell_result['profit_loss_pct'],
                        'sell_score': sell_result['sell_score'],
                        'recommendation': sell_result['recommendation'],
                        'confidence': sell_result['confidence'],
                        'sell_reason': sell_result['sell_reason'],
                        'data_ticks': len(data_array),
                        'buy_tick': buy_tick,
                        'sell_tick': sell_result['sell_tick'],
                        'holding_ticks': sell_result['holding_ticks']
                    })
                else:
                    # 매도가 없었던 경우 (마감청산)
                    final_price = data_array[-1, 1]
                    final_profit_pct = ((final_price - entry_price) / entry_price) * 100
                    
                    test_results.append({
                        'stock_code': stock_code,
                        'stock_name': stock_names.get(stock_code, ''),
                        'entry_price': entry_price,
                        'sell_price': final_price,
                        'profit_loss_pct': final_profit_pct,
                        'sell_score': 0.0,
                        'recommendation': 'NO_SELL_SIGNAL',
                        'confidence': 0.0,
                        'sell_reason': '마감청산',
                        'data_ticks': len(data_array),
                        'buy_tick': buy_tick,
                        'sell_tick': len(data_array) - 1,
                        'holding_ticks': len(data_array) - 1 - buy_tick
                    })
                
            except Exception as e:
                print(f"종목 {stock_code} 분석 중 오류: {e}")
                continue
        
        conn.close()
        
        # 전체 결과 요약
        if test_results:
            print(f"\n{'='*80}")
            print("전체 테스트 결과 요약")
            print(f"{'='*80}")
            
            # 기본 통계
            avg_profit_loss = get_np().mean([r['profit_loss_pct'] for r in test_results])
            avg_sell_score = get_np().mean([r['sell_score'] for r in test_results])
            avg_confidence = get_np().mean([r['confidence'] for r in test_results])
            
            # 추천별 분류
            recommendations = {}
            for result in test_results:
                rec = result['sell_reason']
                if rec not in recommendations:
                    recommendations[rec] = []
                recommendations[rec].append(result)
            
            print(f"테스트 종목 수: {len(test_results)}개")
            print(f"평균 수익률: {avg_profit_loss:+.2f}%")
            print(f"평균 매도 점수: {avg_sell_score:.3f}")
            print(f"평균 신뢰도: {avg_confidence:.3f}")
            
            print(f"\n매도 사유별 분류:")
            for reason, results in recommendations.items():
                print(f"  {reason}: {len(results)}개 ({len(results)/len(test_results)*100:.1f}%)")
                if results:
                    avg_pl = get_np().mean([r['profit_loss_pct'] for r in results])
                    avg_holding = get_np().mean([r['holding_ticks'] for r in results])
                    print(f"    평균 수익률: {avg_pl:+.2f}%, 평균 보유: {avg_holding:.0f}틱")
            
            # 상세 결과 테이블
            print(f"\n상세 결과:")
            print(f"{'종목코드':<10} {'수익률':>2} {'보유틱':>7}        {'매도사유':<11} {'점수':>9}")
            print("-" * 70)
            
            for result in test_results:
                print(f"{result['stock_code']:<10} {result['profit_loss_pct']:>+6.2f}% "
                      f"{result['holding_ticks']:>6}틱     {result['sell_reason']:<18} {result['sell_score']:>8.3f}")
            
            # 최고/최저 성과 종목
            best_performer = max(test_results, key=lambda x: x['profit_loss_pct'])
            worst_performer = min(test_results, key=lambda x: x['profit_loss_pct'])
            tital_profit = sum([result['profit_loss_pct'] for result in test_results])
            
            print(f"\n최고 성과 종목: {best_performer['stock_code']} ({best_performer['stock_name']}) "
                  f"{best_performer['profit_loss_pct']:+.2f}%")
            print(f"최저 성과 종목: {worst_performer['stock_code']} ({worst_performer['stock_name']}) "
                  f"{worst_performer['profit_loss_pct']:+.2f}%")
            print(f"수익률합계: {tital_profit:.2f}%")
        
        else:
            print("테스트 결과가 없습니다.")
            
    except Exception as e:
        print(f"테스트 실행 중 오류 발생: {e}")
        print_exc()


if __name__ == "__main__":
    test_optimal_sell_analyzer(
        market_type='stock',
        num_stocks=100,
        buy_tick_offset=60,
        signal_only=False
    )
