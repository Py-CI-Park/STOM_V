"""
16코어 멀티프로세싱 실행 스크립트
FactorAnalysis와 PCA 모델을 동시에 병렬 실행
"""
import os
import logging
import sqlite3
from utility.lazy_imports import get_pd
from multiprocessing_utils import parallel_train_factor_analysis, parallel_train_pca, process_results, print_top_predictions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ParallelRunner')


def load_stock_codes():
    """데이터베이스에서 종목 코드 로드"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # FactorAnalysis용 tick 데이터
        DB_STOCK_TICK = os.path.join(base_dir, '_database', 'stock_tick_back.db')
        con_tick = sqlite3.connect(DB_STOCK_TICK)
        df_tick = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con_tick)
        tick_codes = df_tick['name'].to_list()
        tick_codes = [code for code in tick_codes if code not in ['moneytop', 'stockinfo']]
        con_tick.close()
        
        # PCA용 min 데이터
        DB_STOCK_MIN = os.path.join(base_dir, '_database', 'stock_tick_back.db')
        con_min = sqlite3.connect(DB_STOCK_MIN)
        df_min = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con_min)
        min_codes = df_min['name'].to_list()
        min_codes = [code for code in min_codes if code not in ['moneytop', 'stockinfo']]
        con_min.close()
        
        return tick_codes, min_codes
        
    except Exception:
        return [], []


def run_factor_analysis(codes):
    """FactorAnalysis 모델 병렬 실행"""
    try:
        results = parallel_train_factor_analysis(
            codes=codes,
            market='stock',
            data_type='tick',
            model_type='Transformer',
            sequence_length=60,
            n_factors=5,
            epochs=50,
            batch_size=32,
            max_workers=16
        )
        
        predictions = process_results(results)
        print_top_predictions(predictions, top_n=10)
        
        return predictions
        
    except Exception:
        return {}


def run_pca_analysis(codes):
    """PCA 모델 병렬 실행"""
    try:
        results = parallel_train_pca(
            codes=codes,
            market='stock',
            data_type='tick',
            model_type='LSTM',
            sequence_length=60,
            n_components=10,
            epochs=50,
            batch_size=32,
            max_workers=16
        )
        
        predictions = process_results(results)
        print_top_predictions(predictions, top_n=10)
        
        return predictions
        
    except Exception:
        return {}


def run_parallel_models(run_factor=True, run_pca=True):
    """두 모델을 동시에 병렬 실행"""
    tick_codes, min_codes = load_stock_codes()
    
    if not tick_codes and not min_codes:
        return None
    
    results = {}
    
    if run_factor and tick_codes:
        factor_results = run_factor_analysis(tick_codes)
        results['factor'] = factor_results
    
    if run_pca and min_codes:
        pca_results = run_pca_analysis(min_codes)
        results['pca'] = pca_results
    
    return results


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='16코어 딥러닝 모델 병렬 실행')
    parser.add_argument('--factor', action='store_true', help='FactorAnalysis 모델 실행')
    parser.add_argument('--pca', action='store_true', help='PCA 모델 실행')
    parser.add_argument('--both', action='store_true', help='두 모델 모두 실행')
    
    args = parser.parse_args()
    
    # 기본값은 두 모델 모두 실행
    if not any([args.factor, args.pca]):
        args.both = True
    
    results = None
    if args.both:
        results = run_parallel_models(run_factor=True, run_pca=True)
    elif args.factor:
        tick_codes, _ = load_stock_codes()
        results = {'factor': run_factor_analysis(tick_codes)}
    elif args.pca:
        _, min_codes = load_stock_codes()
        results = {'pca': run_pca_analysis(min_codes)}
    
    # 결과 요약
    if results:
        print("\n=== 최종 결과 요약 ===")
        for model_name, predictions in results.items():
            if predictions:
                top_5 = list(predictions.items())[:5]
                print(f"\n{model_name.upper()} 상위 5개:")
                for i, (code, pct) in enumerate(top_5, 1):
                    print(f"  {i}. {code}: {pct:+.2f}%")


if __name__ == "__main__":
    main()
