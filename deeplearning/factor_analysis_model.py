"""
요인분석 기반 주가예측 딥러닝 모델
잠재요인 추출 후 Transformer/Attention 기반 모델로 주가 예측
"""
import os
import joblib
import logging
import warnings
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from datetime import datetime
import matplotlib.pyplot as plt
from tensorflow.keras.models import Model
from data_preprocessor import DataPreprocessor
from tensorflow.keras.layers import (
    Input, Dense, Dropout, BatchNormalization, MultiHeadAttention, 
    LayerNormalization, GlobalAveragePooling1D, LSTM, GRU
)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from multiprocessing_utils import parallel_train_factor_analysis, process_results, print_top_predictions

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.get_logger().setLevel('ERROR')
tf.autograph.set_verbosity(0)
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

matplotlib.use('Agg')  # 비대화형 백엔드 설정

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FactorAnalysisModel')


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


class TransformerBlock(tf.keras.layers.Layer):
    """Transformer 블록 구현"""
    def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1, **kwargs):
        super(TransformerBlock, self).__init__(**kwargs)
        self.att = MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = tf.keras.Sequential([
            Dense(ff_dim, activation="relu"),
            Dense(embed_dim),
        ])
        self.layernorm1 = LayerNormalization(epsilon=1e-6)
        self.layernorm2 = LayerNormalization(epsilon=1e-6)
        self.dropout1 = Dropout(rate)
        self.dropout2 = Dropout(rate)

    def call(self, inputs, training):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)


class FactorAnalysisModel:
    def __init__(self, market='stock', data_type='min', model_type='Transformer'):
        """
        ?�인분석 ?�측 모델 초기??        
        Args:
            market: 'stock', 'coin', 'future'
            data_type: 'tick', 'min'
            model_type: 'Transformer', 'LSTM', 'GRU', 'Hybrid'
        """
        self.market = market
        self.data_type = data_type
        self.model_type = model_type
        self.preprocessor = DataPreprocessor(market, data_type)
        
        self.model = None
        self.factor_analyzer = None
        self.loadings = None
        self.history = None
        
        # 모델 ?�??경로 (?��? 경로)
        base_dir_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_dir = os.path.join(base_dir_, 'deeplearning', 'models', f'{market}_{data_type}')
        os.makedirs(self.model_dir, exist_ok=True)
    
    def build_model(self, input_shape, n_factors=5):
        """
        ?�러??모델 구축
        
        Args:
            input_shape: ?�력 ?�이???�태 (sequence_length, n_factors)
            n_factors: ?�인 개수
            
        Returns:
            모델 객체
        """
        try:
            inputs = Input(shape=input_shape)
            
            if self.model_type == 'Transformer':
                # Transformer 기반 모델
                # ?�베??- n_factors???�라 ?�적 조정
                embed_dim = max(32, n_factors * 12)  # 최소 32, n_factors * 12
                x = Dense(embed_dim, activation='relu')(inputs)
                x = BatchNormalization()(x)
                
                # Transformer 블록 - n_factors???�라 ?�드 ??조정
                num_heads = min(8, max(2, n_factors // 2))  # 2-8 ?�드
                ff_dim = embed_dim * 2
                transformer_block = TransformerBlock(embed_dim, num_heads, ff_dim)
                x = transformer_block(x, training=False)
                
                # Global Pooling
                x = GlobalAveragePooling1D()(x)
                
            elif self.model_type == 'LSTM':
                # LSTM 기반 모델 - n_factors???�라 ?�닛 ??조정
                lstm_units = max(64, n_factors * 24)  # 최소 64, n_factors * 24
                x = LSTM(lstm_units, return_sequences=True)(inputs)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
                x = LSTM(lstm_units // 2, return_sequences=True)(x)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
                x = LSTM(lstm_units // 4, return_sequences=False)(x)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
            elif self.model_type == 'GRU':
                # GRU 기반 모델 - n_factors에 따라 유닛 수 조정
                gru_units = max(64, n_factors * 24)  # 최소 64, n_factors * 24
                x = GRU(gru_units, return_sequences=True)(inputs)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
                x = GRU(gru_units // 2, return_sequences=True)(x)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
                x = GRU(gru_units // 4, return_sequences=False)(x)
                x = BatchNormalization()(x)
                x = Dropout(0.2)(x)
                
            else:  # Hybrid
                # LSTM + Transformer 하이브리드 - n_factors에 따라 동적 조정
                hybrid_units = max(64, n_factors * 12)  # 최소 64, n_factors * 12
                lstm_out = LSTM(hybrid_units, return_sequences=True)(inputs)
                lstm_out = BatchNormalization()(lstm_out)
                
                # Transformer 블록 - n_factors에 따라 헤드 수 조정
                num_heads = min(6, max(2, n_factors // 2))  # 2-6 헤드
                transformer_block = TransformerBlock(hybrid_units, num_heads, hybrid_units * 2)
                x = transformer_block(lstm_out, training=False)
                x = GlobalAveragePooling1D()(x)
            
            # Dense 레이어 - n_factors에 따라 동적 조정
            dense_units = max(16, n_factors * 3)  # 최소 16, n_factors * 3
            x = Dense(dense_units, activation='relu')(x)
            x = Dropout(0.2)(x)
            x = Dense(dense_units // 2, activation='relu')(x)
            x = Dropout(0.1)(x)
            x = Dense(dense_units // 4, activation='relu')(x)
            
            outputs = Dense(1, activation='linear')(x)
            
            # 모델 생성
            model = Model(inputs=inputs, outputs=outputs)
            
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
    
    def prepare_data(self, code, sequence_length=60, n_factors=5):
        """
        학습 데이터 준비
        
        Args:
            code: 종목 코드
            sequence_length: 시퀀스 길이
            n_factors: 요인 개수
            
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
            
            factor_df, loadings, self.factor_analyzer = self.preprocessor.prepare_factor_analysis_data(df, n_factors)
            if factor_df is None:
                return None, None, None, None, None, None
            
            self.loadings = loadings
            
            # 시퀀스 데이터 생성
            X, y = self.preprocessor.create_sequences(
                factor_df, 
                target_col='현재가',
                sequence_length=sequence_length,
                original_data=df
            )
            
            if X is None:
                return None, None, None, None, None, None
            
            # 데이터 분할
            return self.preprocessor.split_data(X, y)
            
        except Exception as e:
            logger.error(f"데이터 준비 실패: {e}")
            return None, None, None, None, None, None
    
    def train(self, code, sequence_length=60, n_factors=5, epochs=100, batch_size=32, worker_id=0, stock_index=0):
        """
        모델 학습
        
        Args:
            code: 종목 코드
            sequence_length: 시퀀스 길이
            n_factors: 요인 개수
            epochs: 학습 에포크
            batch_size: 배치 크기
            worker_id: 워커 ID
            stock_index: 종목 인덱스
            
        Returns:
            학습 결과
        """
        try:
            # 데이터 준비
            X_train, X_val, X_test, y_train, y_val, y_test = self.prepare_data(
                code, sequence_length, n_factors
            )
            
            if X_train is None:
                return None
            
            # 모델 구축
            input_shape = (sequence_length, n_factors)
            self.model = self.build_model(input_shape, n_factors)
            
            if self.model is None:
                return None
            
            # 콜백 설정 (ProgressCallback 추가)
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
    
    def predict(self, code, last_n_data=100, n_factors=5):
        """
        주가 예측
        
        Args:
            code: 종목 코드
            last_n_data: 사용할 최근 데이터 수
            n_factors: 요인 개수
            
        Returns:
            예측 결과
        """
        try:
            if self.model is None:
                return None
            
            # 최신 데이터 로드
            df = self.preprocessor.load_data(code, limit=last_n_data)
            if df is None:
                return None
            
            # 기술적 지표 추가
            df = self.preprocessor.add_technical_indicators(df)
            
            factor_df, _, _ = self.preprocessor.prepare_factor_analysis_data(df, n_factors)
            if factor_df is None:
                return None
            
            # 마지막 시퀀스 추출
            sequence_length = self.model.input_shape[1]
            
            # 데이터가 충분한지 확인
            if len(factor_df) < sequence_length:
                logger.error(f"예측에 필요한 데이터 부족: 필요 {sequence_length}, 실제 {len(factor_df)}")
                return None
            
            last_sequence = factor_df.iloc[-sequence_length:].values.reshape(1, sequence_length, -1)
            
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
    
    def evaluate(self, code, n_factors=5):
        """
        모델 평가
        
        Args:
            code: 종목 코드
            n_factors: 요인 개수
            
        Returns:
            평가 지표
        """
        try:
            if self.model is None:
                return None
            
            X_train, X_val, X_test, y_train, y_val, y_test = self.prepare_data(code, n_factors=n_factors)
            
            if X_test is None:
                return None
            
            # 예측
            y_pred = self.model.predict(X_test, verbose=0)
            
            # 평가 지표 계산
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            direction_accuracy = np.mean((y_test > 0) == (y_pred.flatten() > 0))
            
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
    
    def analyze_factors(self, code, n_factors=5):
        """
        ?�인분석 결과 ?�각??        
        Args:
            code: 종목 코드
            n_factors: ?�인 개수
        """
        try:
            if self.loadings is None:
                logger.error("요인부하량이 없습니다")
                return
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(
                self.loadings, 
                annot=True, 
                cmap='coolwarm', 
                center=0,
                fmt='.2f'
            )
            plt.title(f'Factor Loadings - {code}')
            plt.xlabel('Factors')
            plt.ylabel('Variables')
            plt.tight_layout()
            
            plot_path = os.path.join(self.model_dir, f'{code}_factor_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()  # 창 닫기
            
            print(f"\n{code} 요인분석 결과:")
            for j in range(n_factors):
                factor_col = f'Factor_{j+1}'
                top_vars = self.loadings[factor_col].abs().sort_values(ascending=False).head(5)
                print(f"\nFactor {j+1} 상위 변수:")
                for var, loading in top_vars.items():
                    print(f"  {var}: {loading:.3f}")
            
        except Exception as e:
            logger.error(f"요인분석 시각화 실패: {e}")
    
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
            
            model_path = os.path.join(self.model_dir, f'{code}_{self.model_type}_factor_{timestamp}.h5')
            self.model.save(model_path)
            
            fa_path = os.path.join(self.model_dir, f'{code}_factor_analyzer_{timestamp}.pkl')
            joblib.dump(self.factor_analyzer, fa_path)
            
            if self.loadings is not None:
                loadings_path = os.path.join(self.model_dir, f'{code}_loadings_{timestamp}.csv')
                self.loadings.to_csv(path_or_buf=loadings_path)
            
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
                model_files = [f for f in os.listdir(self.model_dir) if f.startswith(code) and 'factor' in f and f.endswith('.h5')]
                if not model_files:
                    logger.error(f"모델 파일을 찾을 수 없습니다: {code}")
                    return False
                
                model_files.sort()
                latest_model = model_files[-1]
                # 파일명에서 타임스탬프 추출 (예: 950160_Transformer_factor_20260215_040925.h5 -> 20260215_040925)
                parts = latest_model.split('_')
                if len(parts) >= 5:  # code_model_type_factor_timestamp 형식
                    timestamp = '_'.join(parts[-2:]).replace('.h5', '')  # 마지막 두 부분을 타임스탬프로 사용
                else:
                    timestamp = parts[-1].replace('.h5', '')
            
            # 모델 로드 (커스텀 객체 등록)
            model_path = os.path.join(self.model_dir, f'{code}_{self.model_type}_factor_{timestamp}.h5')
            with tf.keras.utils.custom_object_scope({'TransformerBlock': TransformerBlock}):
                self.model = tf.keras.models.load_model(model_path, compile=False)  # 컴파일 없이 로드
            
            # 요인분석 로드
            fa_path = os.path.join(self.model_dir, f'{code}_factor_analyzer_{timestamp}.pkl')
            self.factor_analyzer = joblib.load(fa_path)
            
            # 요인부하량 로드
            loadings_path = os.path.join(self.model_dir, f'{code}_loadings_{timestamp}.csv')
            if os.path.exists(loadings_path):
                self.loadings = pd.read_csv(loadings_path, index_col=0)
            
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return False
    
    def plot_training_history(self):
        """
        학습 과정 시각화
        """
        try:
            if self.history is None:
                logger.error("학습 기록이 없습니다")
                return
            
            plt.figure(figsize=(15, 5))
            
            # Loss
            plt.subplot(1, 3, 1)
            plt.plot(self.history.history['loss'], label='Train Loss')
            plt.plot(self.history.history['val_loss'], label='Validation Loss')
            plt.title('Model Loss')
            plt.xlabel('Epoch')
            plt.ylabel('Loss')
            plt.legend()
            
            # MAE
            plt.subplot(1, 3, 2)
            plt.plot(self.history.history['mae'], label='Train MAE')
            plt.plot(self.history.history['val_mae'], label='Validation MAE')
            plt.title('Model MAE')
            plt.xlabel('Epoch')
            plt.ylabel('MAE')
            plt.legend()
            
            # MAPE
            plt.subplot(1, 3, 3)
            plt.plot(self.history.history['mape'], label='Train MAPE')
            plt.plot(self.history.history['val_mape'], label='Validation MAPE')
            plt.title('Model MAPE')
            plt.xlabel('Epoch')
            plt.ylabel('MAPE')
            plt.legend()
            
            plt.tight_layout()
            
            plot_path = os.path.join(self.model_dir, f'training_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()  # 창 닫기
            
        except Exception as e:
            logger.error(f"시각화 실패: {e}")


if __name__ == "__main__":
    import sqlite3
    
    # 데이터베이스에서 종목 코드 로드
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_STOCK_BACK_MIN = os.path.join(base_dir, '_database', 'stock_min_back.db')
    
    try:
        con = sqlite3.connect(DB_STOCK_BACK_MIN)
        df_ = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df_['name'].to_list()
        table_list.remove('moneytop')
        table_list.remove('stockinfo')
        con.close()
        
        if not table_list:
            print("사용 가능한 종목 테이블이 없습니다.")
            exit()

        print(f"FactorAnalysisModel 병렬 학습 시작: {len(table_list)} 종목")
        
        # 병렬 학습 실행
        results = parallel_train_factor_analysis(
            codes=table_list,
            market='stock',
            data_type='min',
            model_type='Transformer',
            sequence_length=60,
            n_factors=5,
            epochs=20,  # CPU만 사용하므로 에포크 감소
            batch_size=32,
            max_workers=8  # CPU만 사용하므로 코어 수 증가
        )
        
        # 결과 처리
        predictions = process_results(results)

        print_top_predictions(predictions, top_n=10)
        
    except Exception as ee:
        print(f"오류 발생: {ee}")
        import traceback
        traceback.print_exc()
