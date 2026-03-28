"""
PCA 기반 주가예측 딥러닝 모델
주성분 분석으로 차원 축소 후 LSTM/GRU로 주가 예측
"""
import os
import joblib
import logging
import warnings
import tensorflow as tf
from datetime import datetime
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import Sequential
from data_preprocessor import DataPreprocessor
from utility.lazy_imports import get_np, get_pd
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, BatchNormalization

# TensorFlow 경고 메시지 제거
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.get_logger().setLevel('ERROR')
tf.autograph.set_verbosity(0)
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PCAPredictionModel')


class ProgressCallback(tf.keras.callbacks.Callback):
    """학습 진행률을 시각적으로 표시하는 커스텀 콜백"""
    
    def __init__(self, worker_id=0, stock_index=0, epochs=50, stock_code=""):
        super().__init__()
        self.worker_id = worker_id
        self.stock_index = stock_index
        self.epochs = epochs
        self.stock_code = stock_code
        
    def on_epoch_end(self, epoch, logs=None):
        """에포크 종료 시 진행률과 손실을 한 줄로 표시"""
        if logs:
            progress = (epoch + 1) / self.epochs * 100
            loss = logs.get('loss', 0)
            val_loss = logs.get('val_loss', 0)
            
            # 열맞춤 정렬
            worker_str = f"Worker-{self.worker_id}"
            epoch_str = f"Epoch {epoch+1}/{self.epochs}"
            progress_str = f"({progress:.1f}%)"
            loss_str = f"Loss: {loss:.4f}"
            val_loss_str = f"Val Loss: {val_loss:.4f}"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            print(f"[{current_time}] 🚀 [{self.stock_code}] {worker_str:<10} | {epoch_str:<12} {progress_str:<8} | 💡 {loss_str:<12} | {val_loss_str:<12}")
    
    def on_train_end(self, logs=None):
        """학습 완료 시 상태 업데이트"""
        if logs:
            final_loss = logs.get('loss', 0)
            worker_str = f"Worker-{self.worker_id}"
            loss_str = f"최종 Loss: {final_loss:.4f}"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{current_time}] ✅ [{self.stock_code}] {worker_str:<10} 학습 완료! 🎯 {loss_str}")


class PCAPredictionModel:
    def __init__(self, market='stock', data_type='min', model_type='LSTM'):
        """
        PCA 예측 모델 초기화
        
        Args:
            market: 'stock', 'coin', 'future'
            data_type: 'tick', 'min'
            model_type: 'LSTM', 'GRU', 'LSTM_GRU'
        """
        self.market = market
        self.data_type = data_type
        self.model_type = model_type
        self.preprocessor = DataPreprocessor(market, data_type)
        
        self.model = None
        self.pca = None
        self.scaler = None
        self.history = None
        
        # 모델 저장 경로 (절대 경로)
        base_dir_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_dir = os.path.join(base_dir_, 'deeplearning', 'models', f'{market}_{data_type}')
        os.makedirs(self.model_dir, exist_ok=True)
    
    def build_model(self, input_shape, n_components=10):
        """
        딥러닝 모델 구축
        
        Args:
            input_shape: 입력 데이터 형태 (sequence_length, n_components)
            n_components: 주성분 개수
            
        Returns:
            모델 객체
        """
        try:
            model = Sequential()
            
            # n_components에 따라 동적으로 레이어 크기 조정
            lstm_units = max(32, min(128, n_components * 8))
            dropout_rate = max(0.1, min(0.3, n_components * 0.02))
            
            if self.model_type == 'LSTM':
                # LSTM 기반 모델
                model.add(LSTM(lstm_units, return_sequences=True, input_shape=input_shape))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(LSTM(lstm_units // 2, return_sequences=True))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(LSTM(lstm_units // 4, return_sequences=False))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
            elif self.model_type == 'GRU':
                # GRU 기반 모델
                model.add(GRU(lstm_units, return_sequences=True, input_shape=input_shape))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(GRU(lstm_units // 2, return_sequences=True))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(GRU(lstm_units // 4, return_sequences=False))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
            else:  # LSTM_GRU 하이브리드
                model.add(LSTM(lstm_units // 2, return_sequences=True, input_shape=input_shape))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(GRU(lstm_units // 2, return_sequences=True))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
                
                model.add(LSTM(lstm_units // 4, return_sequences=False))
                model.add(BatchNormalization())
                model.add(Dropout(dropout_rate))
            
            # Dense 레이어 - n_components에 따라 동적 조정
            dense_units = max(8, min(32, n_components * 2))
            model.add(Dense(dense_units, activation='relu'))
            model.add(Dropout(dropout_rate / 2))
            model.add(Dense(dense_units // 2, activation='relu'))
            model.add(Dense(1, activation='linear'))  # 수익률 예측
            
            # 컴파일
            optimizer = Adam(learning_rate=0.001)
            model.compile(
                optimizer=optimizer,
                loss='mse',
                metrics=['mae', 'mape']
            )
            
            return model
            
        except Exception as e:
            logger.error(f"모델 구축 실패: {e}")
            return None
    
    def prepare_data(self, code, sequence_length=60, n_components=10):
        """
        학습 데이터 준비
        
        Args:
            code: 종목코드
            sequence_length: 시퀀스 길이
            n_components: 주성분 개수
            
        Returns:
            tuple: (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        try:
            # 데이터 로드
            df = self.preprocessor.load_data(code, limit=20000)
            if df is None:
                return None, None, None, None, None, None
            
            # 기술적 지표 추가
            df = self.preprocessor.add_technical_indicators(df)
            
            # PCA 데이터 준비
            pca_df, variance, self.pca = self.preprocessor.prepare_pca_data(df, n_components)
            if pca_df is None:
                return None, None, None, None, None, None
            
            # 시퀀스 데이터 생성
            X, y = self.preprocessor.create_sequences(
                pca_df, 
                target_col='현재가',
                sequence_length=sequence_length,
                original_data=df  # 원본 데이터 전달
            )
            
            if X is None:
                return None, None, None, None, None, None
            
            # 데이터 분할
            return self.preprocessor.split_data(X, y)
            
        except Exception as e:
            logger.error(f"데이터 준비 실패: {e}")
            return None, None, None, None, None, None
    
    def train(self, code, sequence_length=60, n_components=10, epochs=100, batch_size=32, worker_id=0, stock_index=0):
        """
        모델 학습
        
        Args:
            code: 종목 코드
            sequence_length: 시퀀스 길이
            n_components: 주성분 개수
            epochs: 학습 에포크
            batch_size: 배치 크기
            worker_id: 워커번호
            stock_index: 인덱스
            
        Returns:
            학습 결과
        """
        try:
            # 데이터 준비
            X_train, X_val, X_test, y_train, y_val, y_test = self.prepare_data(
                code, sequence_length, n_components
            )
            
            if X_train is None:
                return None
            
            # 모델 구축
            input_shape = (sequence_length, n_components)
            self.model = self.build_model(input_shape, n_components)
            
            if self.model is None:
                return None
            
            # 콜백 설정
            callbacks = [
                ProgressCallback(worker_id=worker_id, stock_index=stock_index, epochs=epochs, stock_code=code),
                EarlyStopping(patience=20, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=10, min_lr=1e-7)
            ]
            
            # 학습
            self.history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=0  # 딥러닝 메세지 제거, ProgressCallback만 표시
            )
            
            # 평가
            train_score = self.model.evaluate(X_train, y_train, verbose=0)
            val_score = self.model.evaluate(X_val, y_val, verbose=0)
            test_score = self.model.evaluate(X_test, y_test, verbose=0)
            
            # 모델 저장
            self.save_model(code)
            
            return {
                'train_score': train_score,
                'val_score': val_score,
                'test_score': test_score,
                'history': self.history.history
            }
            
        except Exception as e:
            logger.error(f"모델 학습 실패: {e}")
            return None
    
    def predict(self, code, last_n_data=500, n_components=10):
        """
        주가 예측
        
        Args:
            code: 종목 코드
            last_n_data: 사용할 최근 데이터 수
            n_components: 주성분 개수
            
        Returns:
            예측 결과
        """
        try:
            if self.model is None:
                logger.error("모델이 학습되지 않았습니다")
                return None
            
            # 시퀀스 길이 확인
            sequence_length = self.model.input_shape[1]
            
            # 충분한 데이터 로드 (기술적 지표 계산 고려)
            required_data = last_n_data + sequence_length + 100
            df = self.preprocessor.load_data(code, limit=required_data)
            if df is None:
                return None
            
            # 기술적 지표 추가
            df = self.preprocessor.add_technical_indicators(df)
            
            # 데이터가 충분한지 확인
            if len(df) < sequence_length:
                logger.error(f"데이터 부족: 필요 {sequence_length}, 실제 {len(df)}")
                return None
            
            # PCA 변환
            pca_df, _, _ = self.preprocessor.prepare_pca_data(df, n_components)
            if pca_df is None:
                return None
            
            # 마지막 시퀀스 추출
            if len(pca_df) < sequence_length:
                logger.error(f"PCA 데이터 부족: 필요 {sequence_length}, 실제 {len(pca_df)}")
                return None
                
            last_sequence = pca_df.iloc[-sequence_length:].values.reshape(1, sequence_length, -1)
            
            # 예측
            predicted_return = self.model.predict(last_sequence, verbose=0)[0][0]
            
            # 현재가
            current_price = df['현재가'].iloc[-1]
            
            # 예측가
            predicted_price = current_price * (1 + predicted_return)
            
            result = {
                'code': code,
                'current_price': current_price,
                'predicted_return': predicted_return,
                'predicted_price': predicted_price,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return None
    
    def evaluate(self, code, n_components=10):
        """
        모델 평가
        
        Args:
            code: 종목 코드
            n_components: 주성분 개수
            
        Returns:
            평가 지표
        """
        try:
            if self.model is None:
                logger.error("모델이 학습되지 않았습니다")
                return None
            
            # 테스트 데이터 준비
            X_train, X_val, X_test, y_train, y_val, y_test = self.prepare_data(code, n_components=n_components)
            
            if X_test is None:
                return None
            
            # 예측
            y_pred = self.model.predict(X_test, verbose=0)
            
            # 평가 지표 계산
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # 방향성 정확도
            direction_accuracy = get_np().mean((y_test > 0) == (y_pred.flatten() > 0))
            
            result = {
                'mse': mse,
                'mae': mae,
                'r2_score': r2,
                'direction_accuracy': direction_accuracy,
                'y_true': y_test,
                'y_pred': y_pred.flatten()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"평가 실패: {e}")
            return None
    
    def save_model(self, code):
        """
        모델 저장
        
        Args:
            code: 종목 코드
        """
        try:
            if self.model is None:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 모델 저장
            model_path = os.path.join(self.model_dir, f'{code}_{self.model_type}_{timestamp}.h5')
            self.model.save(model_path)
            
            # PCA 객체 저장
            pca_path = os.path.join(self.model_dir, f'{code}_pca_{timestamp}.pkl')
            joblib.dump(self.pca, pca_path)
            
        except Exception as e:
            logger.error(f"모델 저장 실패: {e}")
    
    def load_model(self, code, timestamp=None):
        """
        모델 로드
        
        Args:
            code: 종목 코드
            timestamp: 타임스탬프 (None이면 최신 모델)
        """
        try:
            if timestamp is None:
                # 최신 모델 찾기
                model_files = [f for f in os.listdir(self.model_dir) 
                               if f.startswith(code) and f'{self.model_type}_' in f and f.endswith('.h5')]
                if not model_files:
                    logger.error(f"모델 파일을 찾을 수 없습니다: {code}")
                    return False
                
                model_files.sort()
                latest_model = model_files[-1]
                # 파일명에서 타임스탬프 추출 (예: 950160_LSTM_20260215_041234.h5 -> 20260215_041234)
                parts = latest_model.split('_')
                if len(parts) >= 4:
                    timestamp = '_'.join(parts[-2:]).replace('.h5', '')  # 마지막 두 부분을 타임스탬프로 사용
                else:
                    timestamp = parts[-1].replace('.h5', '')
            
            # 모델 로드 (커스텀 메트릭 등록)
            model_path = os.path.join(self.model_dir, f'{code}_{self.model_type}_{timestamp}.h5')
            self.model = tf.keras.models.load_model(model_path, compile=False)  # 컴파일 없이 로드
            
            # PCA 로드
            pca_path = os.path.join(self.model_dir, f'{code}_pca_{timestamp}.pkl')
            self.pca = joblib.load(pca_path)
            
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return False


if __name__ == "__main__":
    import sqlite3
    from multiprocessing_utils import parallel_train_pca, process_results, print_top_predictions
    
    # 데이터베이스에서 종목 코드 로드
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_STOCK_BACK_MIN = os.path.join(base_dir, '_database', 'stock_tick_back.db')
    con = sqlite3.connect(DB_STOCK_BACK_MIN)
    df_ = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
    con.close()
    table_list = df_['name'].to_list()
    table_list.remove('moneytop')
    table_list.remove('stockinfo')
    table_list = table_list[:10]

    print(f"PCAPredictionModel 병렬 학습 시작: {len(table_list)} 종목")
    
    # 병렬 학습 실행
    results = parallel_train_pca(
        codes=table_list,
        market='stock',
        data_type='tick',
        model_type='LSTM',
        sequence_length=60,
        n_components=10,
        epochs=50,
        batch_size=32,
        max_workers=10  # 16코어 고정
    )
    
    # 결과 처리
    predictions = process_results(results)
    
    # 상위 10개 예측 결과 출력
    print_top_predictions(predictions, top_n=10)
