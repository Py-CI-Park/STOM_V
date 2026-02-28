"""
딥러닝 주가예측을 위한 데이터 전처리 모듈
STOM 2.0 데이터베이스와 연동하여 PCA/요인분석용 데이터 준비
"""

import os
import sqlite3
import logging
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.preprocessing import StandardScaler, MinMaxScaler

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DataPreprocessor')

# 절대 경로로 데이터베이스 경로 설정
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_STOCK_BACK_TICK  = os.path.join(base_dir, '_database', 'stock_tick_back.db')
DB_STOCK_BACK_MIN   = os.path.join(base_dir, '_database', 'stock_min_back.db')
DB_COIN_BACK_TICK   = os.path.join(base_dir, '_database', 'coin_tick_back.db')
DB_COIN_BACK_MIN    = os.path.join(base_dir, '_database', 'coin_min_back.db')
DB_FUTURE_BACK_TICK = os.path.join(base_dir, '_database', 'future_tick_back.db')
DB_FUTURE_BACK_MIN  = os.path.join(base_dir, '_database', 'future_min_back.db')


class DataPreprocessor:
    def __init__(self, market='stock', data_type='min'):
        """
        데이터 전처리기 초기화
        
        Args:
            market: 'stock', 'coin', 'future'
            data_type: 'tick', 'min'
        """
        self.market = market
        self.data_type = data_type
        self.scaler = StandardScaler()
        self.min_max_scaler = MinMaxScaler()
        
        # 데이터베이스 경로 설정
        db_paths = {
            'stock': {'tick': DB_STOCK_BACK_TICK, 'min': DB_STOCK_BACK_MIN},
            'coin': {'tick': DB_COIN_BACK_TICK, 'min': DB_COIN_BACK_MIN},
            'future': {'tick': DB_FUTURE_BACK_TICK, 'min': DB_FUTURE_BACK_MIN}
        }
        
        self.db_path = db_paths.get(market, {}).get(data_type)
        if not self.db_path:
            raise ValueError(f"지원하지 않는 마켓 또는 데이터 타입: {market}/{data_type}")
    
    def load_data(self, code='950160', start_date=None, end_date=None, limit=10000):
        """
        데이터베이스에서 주가 데이터 로드
        
        Args:
            code: 종목코드
            start_date: 시작일자
            end_date: 종료일자
            limit: 최대 데이터 수
            
        Returns:
            DataFrame: 주가 데이터
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f"SELECT * FROM '{code}'"
            
            if start_date and end_date:
                query += f' WHERE "index" BETWEEN \'{start_date}\' AND \'{end_date}\''
            
            query += f' ORDER BY "index" LIMIT {limit}'
            
            df = pd.read_sql(query, conn)
            conn.close()
            
            if df.empty:
                logger.warning(f"데이터가 없습니다: {code}")
                return None

            # 전처리
            if '초당거래대금' in df.columns:
                df['index'] = pd.to_datetime(df['index'], format='%Y%m%d%H%M%S')
            else:
                df['index'] = pd.to_datetime(df['index'], format='%Y%m%d%H%M')
            df.set_index('index', inplace=True)

            # 필요없는 칼럼 제거
            del_columns = [
                '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1',
                '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
                '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1',
                '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
            ]
            if self.market == 'stock':
                del_columns += ['시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위']
            df.drop(columns=del_columns, inplace=True)

            # 결측치 처리
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.ffill().bfill()
            
            logger.info(f"데이터 로드 완료: {code}, shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            return None
    
    def add_technical_indicators(self, df):
        """
        기술적 지표 추가 (속도 최적화)
        
        Args:
            df: 주가 데이터
            
        Returns:
            DataFrame: 기술적 지표가 추가된 데이터
        """
        if df is None or df.empty:
            return df
            
        try:
            # 이동평균선 (속도 최적화)
            for period in [5, 10, 20, 60]:
                df[f'MA_{period}'] = df['현재가'].rolling(period).mean()
                df[f'MA_ratio_{period}'] = df['현재가'] / df[f'MA_{period}']
            
            # RSI (속도 최적화 버전)
            delta = df['현재가'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 볼린저밴드
            df['BB_middle'] = df['현재가'].rolling(20).mean()
            bb_std = df['현재가'].rolling(20).std()
            df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
            df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
            df['BB_position'] = (df['현재가'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
            
            # MACD
            exp1 = df['현재가'].ewm(span=12).mean()
            exp2 = df['현재가'].ewm(span=26).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_histogram'] = df['MACD'] - df['MACD_signal']
            
            # 모멘텀 지표
            df['momentum_5'] = df['현재가'].pct_change(5)
            df['momentum_10'] = df['현재가'].pct_change(10)
            
            # 변동성 지표
            df['volatility'] = df['현재가'].rolling(20).std()
            
            # 거래량 관련 지표
            if '초당거래대금' in df.columns:
                df['volume_ma'] = df['초당거래대금'].rolling(20).mean()
                df['volume_ratio'] = df['초당거래대금'] / df['volume_ma']
            else:
                df['volume_ma'] = df['분당거래대금'].rolling(20).mean()
                df['volume_ratio'] = df['분당거래대금'] / df['volume_ma']
            
            # 호가 관련 지표
            if '매수총잔량' in df.columns and '매도총잔량' in df.columns:
                df['bid_ask_ratio'] = df['매수총잔량'] / (df['매도총잔량'] + 1e-10)
            
            # 결측치 제거
            df = df.dropna()
            
            logger.info(f"기술적 지표 추가 완료, shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"기술적 지표 계산 실패: {e}")
            return df
    
    def prepare_pca_data(self, df, n_components=10):
        """
        PCA를 위한 데이터 준비
        
        Args:
            df: 전처리된 데이터
            n_components: 주성분 개수
            
        Returns:
            tuple: (PCA 데이터, 주성분 설명력, PCA 객체)
        """
        if df is None or df.empty:
            return None, None, None
            
        try:
            # 수치형 컬럼만 선택
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            # 표준화
            scaled_data = self.scaler.fit_transform(df[numeric_cols])
            
            # PCA
            pca = PCA(n_components=n_components)
            pca_data = pca.fit_transform(scaled_data)
            
            # 주성분 DataFrame 생성
            pca_cols = [f'PC_{i+1}' for i in range(n_components)]
            pca_df = pd.DataFrame(pca_data, columns=pca_cols, index=df.index)
            
            # 설명력 계산
            explained_variance = pca.explained_variance_ratio_
            cumulative_variance = np.cumsum(explained_variance)
            
            logger.info(f"PCA 완료 - 설명력: {cumulative_variance[-1]:.3f}")
            
            return pca_df, cumulative_variance, pca
            
        except Exception as e:
            logger.error(f"PCA 데이터 준비 실패: {e}")
            return None, None, None
    
    def prepare_factor_analysis_data(self, df, n_factors=20):
        """
        요인분석을 위한 데이터 준비
        
        Args:
            df: 전처리된 데이터
            n_factors: 요인 개수
            
        Returns:
            tuple: (요인점수 데이터, 요인부하량, 요인분석 객체)
        """
        if df is None or df.empty:
            return None, None, None
            
        try:
            # 수치형 컬럼만 선택
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            # 표준화
            scaled_data = self.scaler.fit_transform(df[numeric_cols])
            
            # 요인분석
            fa = FactorAnalysis(n_components=n_factors, random_state=42)
            fa.fit(scaled_data)
            
            # 요인점수 계산
            factor_scores = fa.transform(scaled_data)
            
            # 요인점수 DataFrame 생성
            factor_cols = [f'Factor_{i+1}' for i in range(n_factors)]
            factor_df = pd.DataFrame(factor_scores, columns=factor_cols, index=df.index)
            
            # 요인부하량
            loadings = pd.DataFrame(
                fa.components_.T,
                index=numeric_cols,
                columns=factor_cols
            )
            
            logger.info(f"요인분석 완료 - {n_factors}개 요인 추출")
            
            return factor_df, loadings, fa
            
        except Exception as e:
            logger.error(f"요인분석 데이터 준비 실패: {e}")
            return None, None, None
    
    def create_sequences(self, data, target_col='현재가', sequence_length=60, prediction_horizon=1, original_data=None):
        """
        시퀀스 데이터 생성 (딥러닝용)
        
        Args:
            data: 입력 데이터 (PCA 또는 요인분석 데이터)
            target_col: 예측할 타겟 컬럼
            sequence_length: 입력 시퀀스 길이
            prediction_horizon: 예측 기간
            original_data: 원본 데이터 (타겟 컬럼을 찾기 위해 필요)
            
        Returns:
            tuple: (X, y)
        """
        if data is None or data.empty:
            return None, None
            
        try:
            # 타겟 데이터 준비
            if target_col not in data.columns:
                # 원본 데이터에서 타겟 찾기
                if original_data is not None and target_col in original_data.columns:
                    # 인덱스 맞추기
                    target_data = original_data.loc[data.index, target_col]
                else:
                    raise ValueError(f"타겟 컬럼 {target_col}을 찾을 수 없습니다")
            else:
                target_data = data[target_col]
            
            X, y = [], []
            
            for i in range(sequence_length, len(data) - prediction_horizon + 1):
                # 입력 시퀀스
                X.append(data.iloc[i-sequence_length:i].values)
                
                # 타겟 (미래 수익률)
                current_price = target_data.iloc[i-1]
                future_price = target_data.iloc[i+prediction_horizon-1]
                return_rate = (future_price - current_price) / current_price
                y.append(return_rate)
            
            X = np.array(X)
            y = np.array(y)
            
            logger.info(f"시퀀스 데이터 생성 완료 - X: {X.shape}, y: {y.shape}")
            
            return X, y
            
        except Exception as e:
            logger.error(f"시퀀스 데이터 생성 실패: {e}")
            return None, None
    
    def split_data(self, X, y, test_size=0.2, validation_size=0.1):
        """
        데이터 분할 (학습/검증/테스트)
        
        Args:
            X: 입력 데이터
            y: 타겟 데이터
            test_size: 테스트 데이터 비율
            validation_size: 검증 데이터 비율
            
        Returns:
            tuple: (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        if X is None or y is None:
            return None, None, None, None, None, None
            
        try:
            # 먼저 테스트 데이터 분리
            X_temp, X_test, y_temp, y_test = train_test_split(
                X, y, test_size=test_size, shuffle=False
            )
            
            # 학습/검증 데이터 분리
            val_size_adjusted = validation_size / (1 - test_size)
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp, test_size=val_size_adjusted, shuffle=False
            )
            
            logger.info(f"데이터 분할 완료 - 학습: {X_train.shape}, 검증: {X_val.shape}, 테스트: {X_test.shape}")
            
            return X_train, X_val, X_test, y_train, y_val, y_test
            
        except Exception as e:
            logger.error(f"데이터 분할 실패: {e}")
            return None, None, None, None, None, None


if __name__ == "__main__":
    # 테스트 코드
    preprocessor = DataPreprocessor(market='stock', data_type='min')
    
    # 샘플 데이터 로드
    df_ = preprocessor.load_data('950160')
    
    if df_ is not None:
        # 기술적 지표 추가
        df_with_indicators = preprocessor.add_technical_indicators(df_)
        
        # PCA 데이터 준비
        pca_df_, variance_, pca_ = preprocessor.prepare_pca_data(df_with_indicators)
        
        # 요인분석 데이터 준비
        factor_df_, loadings_, fa_ = preprocessor.prepare_factor_analysis_data(df_with_indicators)
        
        print(f"원본 데이터 shape: {df_with_indicators.shape}")
        print(f"PCA 데이터 shape: {pca_df_.shape if pca_df_ is not None else None}")
        print(f"요인분석 데이터 shape: {factor_df_.shape if factor_df_ is not None else None}")
