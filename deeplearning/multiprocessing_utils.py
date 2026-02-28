"""
딥러닝 모델 멀티프로세싱 유틸리티
16코어 병렬 처리를 위한 공통 함수들
"""
import time
import logging
import threading
from datetime import datetime
import multiprocessing as mp
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MultiprocessingUtils')


class MultiprocessingConfig:
    """멀티프로세싱 설정 클래스"""
    MAX_WORKERS = 8  # CPU만 사용하므로 코어 수 증가
    TIMEOUT_SECONDS = 1800  # 30분 타임아웃으로 증가
    CHUNK_SIZE = 8  # 청크 크기 증가
    
    @classmethod
    def get_optimal_workers(cls, total_tasks: int) -> int:
        """최적 워커 수 계산"""
        return min(cls.MAX_WORKERS, total_tasks, mp.cpu_count())


def progress_monitor(completed_ref, total_codes, start_time, stop_event):
    """주기적으로 진행 상황을 출력하는 모니터 함수"""
    last_completed = 0
    last_time = start_time
    
    while not stop_event.is_set():
        completed = completed_ref[0]
        current_time = time.time()
        elapsed_time = current_time - start_time
        elapsed_str = f"{int(elapsed_time//3600):02d}:{int((elapsed_time%3600)//60):02d}:{int(elapsed_time%60):02d}"
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        progress = (completed / total_codes) * 100
        
        if completed > 0 and completed > last_completed:
            # 최근 속도 기반 예상시간 계산
            recent_time = current_time - last_time
            recent_completed = completed - last_completed
            if recent_completed > 0:
                avg_time_per_stock = recent_time / recent_completed
                remaining_stocks = total_codes - completed
                eta_seconds = avg_time_per_stock * remaining_stocks
                eta_str = f"{int(eta_seconds//3600):02d}:{int((eta_seconds%3600)//60):02d}:{int(eta_seconds%60):02d}"
                last_completed = completed
                last_time = current_time
            else:
                eta_str = "--:--:--"
        elif completed > 0:
            # 전체 평균으로 계산
            avg_time_per_stock = elapsed_time / completed
            remaining_stocks = total_codes - completed
            eta_seconds = avg_time_per_stock * remaining_stocks
            eta_str = f"{int(eta_seconds//3600):02d}:{int((eta_seconds%3600)//60):02d}:{int(eta_seconds%60):02d}"
        else:
            eta_str = "--:--:--"
        
        print(f"[{current_time_str}] 📊 진행 상황: {completed}/{total_codes} ({progress:.1f}%) | 경과: {elapsed_str} | 예상: {eta_str} | 진행 중인 작업: {total_codes - completed}")
        
        # 30초마다 체크
        stop_event.wait(30)


def train_single_stock_factor(args: Tuple) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """단일 종목 FactorAnalysis 학습 함수"""
    code, market, data_type, model_type, sequence_length, n_factors, epochs, batch_size, worker_id, stock_index = args
    
    try:
        # 프로세스 내에서 모델 초기화
        from factor_analysis_model import FactorAnalysisModel
        model = FactorAnalysisModel(market, data_type, model_type)
        
        # 학습
        result = model.train(code, sequence_length, n_factors, epochs, batch_size, worker_id, stock_index)
        
        if result:
            # 예측
            prediction = model.predict(code, last_n_data=500, n_factors=n_factors)
            return code, result, prediction
        else:
            return code, None, None
            
    except:
        return code, None, None


def train_single_stock_pca(args: Tuple) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """단일 종목 PCA 학습 함수"""
    code, market, data_type, model_type, sequence_length, n_components, epochs, batch_size, worker_id, stock_index = args
    
    try:
        # 프로세스 내에서 모델 초기화
        from pca_prediction_model import PCAPredictionModel
        model = PCAPredictionModel(market, data_type, model_type)
        
        # 학습
        result = model.train(code, sequence_length, n_components, epochs, batch_size, worker_id, stock_index)
        
        if result:
            # 예측
            prediction = model.predict(code, last_n_data=500, n_components=n_components)
            return code, result, prediction
        else:
            return code, None, None
            
    except Exception:
        return code, None, None


def parallel_train_factor_analysis(
    codes: List[str],
    market: str = 'stock',
    data_type: str = 'tick',
    model_type: str = 'Transformer',
    sequence_length: int = 60,
    n_factors: int = 10,
    epochs: int = 50,
    batch_size: int = 32,
    max_workers: Optional[int] = None
) -> List[Tuple[str, Optional[Dict], Optional[Dict]]]:
    """
    FactorAnalysis 모델 병렬 학습
    
    Args:
        codes: 종목 코드 리스트
        market: 시장 종류
        data_type: 데이터 타입
        model_type: 모델 타입
        sequence_length: 시퀀스 길이
        n_factors: 요인 개수
        epochs: 학습 에포크
        batch_size: 배치 크기
        max_workers: 최대 워커 수 (None이면 자동 설정)
    
    Returns:
        학습 결과 리스트 [(code, result, prediction), ...]
    """
    if max_workers is None:
        max_workers = MultiprocessingConfig.get_optimal_workers(len(codes))
    
    # 인자 준비 - 워커 번호 순차 할당
    args_list = [
        (code, market, data_type, model_type, sequence_length, n_factors, epochs, batch_size, (idx % max_workers) + 1, idx)
        for idx, code in enumerate(codes)
    ]
    
    results = []
    completed = [0]  # 리스트로 감싸서 참조로 전달
    start_time = time.time()
    
    # 진행 상황 모니터링 스레드 시작
    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=progress_monitor, 
        args=(completed, len(codes), start_time, stop_event)
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 병렬 처리 실행
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Future 객체 생성
        future_to_code = {
            executor.submit(train_single_stock_factor, args): args[0]  # code만 전달
            for args in args_list
        }
        
        # 결과 수집
        for future in as_completed(future_to_code, timeout=MultiprocessingConfig.TIMEOUT_SECONDS):
            code = future_to_code[future]
            try:
                result = future.result(timeout=MultiprocessingConfig.TIMEOUT_SECONDS)
                results.append(result)
                completed[0] += 1
            except TimeoutError:
                results.append((code, None, None))
                completed[0] += 1
            except Exception:
                results.append((code, None, None))
                completed[0] += 1
    
    # 모니터링 스레드 중지
    stop_event.set()
    monitor_thread.join(timeout=1)
    
    return results


def parallel_train_pca(
    codes: List[str],
    market: str = 'stock',
    data_type: str = 'tick',
    model_type: str = 'LSTM',
    sequence_length: int = 60,
    n_components: int = 10,
    epochs: int = 50,
    batch_size: int = 32,
    max_workers: Optional[int] = None
) -> List[Tuple[str, Optional[Dict], Optional[Dict]]]:
    """
    PCA 모델 병렬 학습
    
    Args:
        codes: 종목 코드 리스트
        market: 시장 종류
        data_type: 데이터 타입
        model_type: 모델 타입
        sequence_length: 시퀀스 길이
        n_components: 주성분 개수
        epochs: 학습 에포크
        batch_size: 배치 크기
        max_workers: 최대 워커 수 (None이면 자동 설정)
    
    Returns:
        학습 결과 리스트 [(code, result, prediction), ...]
    """
    if max_workers is None:
        max_workers = MultiprocessingConfig.get_optimal_workers(len(codes))
    
    # 인자 준비 - 워커 번호 순차 할당
    args_list = [
        (code, market, data_type, model_type, sequence_length, n_components, epochs, batch_size, (idx % max_workers) + 1, idx)
        for idx, code in enumerate(codes)
    ]
    
    results = []
    completed = [0]  # 리스트로 감싸서 참조로 전달
    start_time = time.time()
    
    # 진행 상황 모니터링 스레드 시작
    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=progress_monitor, 
        args=(completed, len(codes), start_time, stop_event)
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 병렬 처리 실행
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Future 객체 생성
        future_to_code = {
            executor.submit(train_single_stock_pca, args): args  # args 전체 전달
            for args in args_list
        }
        
        # 결과 수집
        for future in as_completed(future_to_code, timeout=MultiprocessingConfig.TIMEOUT_SECONDS):
            code = future_to_code[future]
            try:
                result = future.result(timeout=MultiprocessingConfig.TIMEOUT_SECONDS)
                results.append(result)
                completed[0] += 1
            except TimeoutError:
                results.append((code, None, None))
                completed[0] += 1
            except Exception:
                results.append((code, None, None))
                completed[0] += 1
    
    # 모니터링 스레드 중지
    stop_event.set()
    monitor_thread.join(timeout=1)
    
    return results


def process_results(results: List[Tuple[str, Optional[Dict], Optional[Dict]]]) -> Dict[str, float]:
    """
    학습 결과 처리 및 예측 정렬
    
    Args:
        results: 학습 결과 리스트
    
    Returns:
        예측 결과 딕셔너리 {code: predicted_pct}
    """
    predictions = {}
    
    for code, result, prediction in results:
        if prediction and 'current_price' in prediction and 'predicted_price' in prediction:
            curr_price = prediction['current_price']
            pred_price = prediction['predicted_price']
            predict_pct = round((pred_price / curr_price - 1) * 100, 2)
            predictions[code] = predict_pct
    
    # 예측률 기준 내림차순 정렬
    sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    
    return dict(sorted_predictions)


def print_top_predictions(predictions: Dict[str, float], top_n: int = 10):
    """
    상위 예측 결과 출력
    
    Args:
        predictions: 예측 결과 딕셔너리
        top_n: 출력할 상위 개수
    """
    for i, (code, pct) in enumerate(list(predictions.items())[:top_n], 1):
        print(f"{i:2d}. {code}: {pct:+.2f}%")


if __name__ == "__main__":
    # 테스트 코드
    test_codes = ['950160', '005930', '000660']  # 샘플 종목 코드
    
    # FactorAnalysis 테스트
    print("FactorAnalysis 병렬 학습 테스트")
    factor_results = parallel_train_factor_analysis(
        test_codes,
        market='stock',
        data_type='tick',
        model_type='Transformer',
        epochs=10,  # 테스트용으로 에포크 감소
        max_workers=3  # 테스트용으로 워커 감소
    )
    
    factor_predictions = process_results(factor_results)
    print_top_predictions(factor_predictions)
    
    # PCA 테스트
    print("\nPCA 병렬 학습 테스트")
    pca_results = parallel_train_pca(
        test_codes,
        market='stock',
        data_type='tick',
        model_type='LSTM',
        epochs=10,  # 테스트용으로 에포크 감소
        max_workers=3  # 테스트용으로 워커 감소
    )
    
    pca_predictions = process_results(pca_results)
    print_top_predictions(pca_predictions)
