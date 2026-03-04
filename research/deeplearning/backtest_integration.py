"""
딥러닝 모델과 STOM 2.0 백테스팅 시스템 연동 모듈
PCA/요인분석 모델을 백테스팅 엔진에 통합
"""

import os
import sqlite3
import logging
import numpy as np
import pandas as pd
from typing import Dict
from pca_prediction_model import PCAPredictionModel
from factor_analysis_model import FactorAnalysisModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BacktestIntegration')


DB_STOCK_BACK_TICK  = '../_database/stock_tick_back.db'
DB_STOCK_BACK_MIN   = '../_database/stock_min_back.db'
DB_COIN_BACK_TICK   = '../_database/coin_tick_back.db'
DB_COIN_BACK_MIN    = '../_database/coin_min_back.db'
DB_FUTURE_BACK_TICK = '../_database/future_tick_back.db'
DB_FUTURE_BACK_MIN  = '../_database/future_min_back.db'
DB_STRATEGY         = '../_database/deeplearning.db'


class DeepLearningBacktestEngine:
    def __init__(self, market='stock', data_type='min'):
        """
        딥러닝 백테스팅 엔진 초기화
        
        Args:
            market: 'stock', 'coin', 'future'
            data_type: 'tick', 'min'
        """
        self.market = market
        self.data_type = data_type
        
        # 모델들 초기화
        self.pca_model = PCAPredictionModel(market, data_type)
        self.factor_model = FactorAnalysisModel(market, data_type)
        
        # 백테스팅 결과 저장
        self.backtest_results = {}
        
        # 데이터베이스 경로
        db_paths = {
            'stock': DB_STOCK_BACK_MIN,
            'coin': DB_COIN_BACK_MIN,
            'future': './_database/future_back_min.db'
        }
        self.backtest_db_path = db_paths.get(market)
    
    def load_trained_models(self, code: str) -> bool:
        """
        학습된 모델 로드
        
        Args:
            code: 종목 코드
            
        Returns:
            로드 성공 여부
        """
        try:
            pca_loaded = self.pca_model.load_model(code)
            factor_loaded = self.factor_model.load_model(code)
            
            if pca_loaded or factor_loaded:
                logger.info(f"모델 로드 완료: {code} (PCA: {pca_loaded}, Factor: {factor_loaded})")
                return True
            else:
                logger.warning(f"로드된 모델이 없습니다: {code}")
                return False
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return False
    
    def generate_signals(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        딥러닝 모델로 매매 신호 생성
        
        Args:
            code: 종목 코드
            start_date: 시작일자
            end_date: 종료일자
            
        Returns:
            매매 신호 DataFrame
        """
        try:
            # 데이터 로드
            df = self.pca_model.preprocessor.load_data(code, start_date, end_date)
            if df is None:
                return pd.DataFrame()
            
            # 기술적 지표 추가
            df = self.pca_model.preprocessor.add_technical_indicators(df)
            
            signals = pd.DataFrame(index=df.index)
            signals['price'] = df['현재가']
            signals['volume'] = df.get('당일거래대금', 0)
            
            # PCA 모델 신호
            if self.pca_model.model is not None:
                pca_signals = self._generate_model_signals(
                    self.pca_model, df, 'PCA'
                )
                signals = pd.concat([signals, pca_signals], axis=1)
            
            # 요인분석 모델 신호
            if self.factor_model.model is not None:
                factor_signals = self._generate_model_signals(
                    self.factor_model, df, 'Factor'
                )
                signals = pd.concat([signals, factor_signals], axis=1)
            
            # 앙상블 신호
            if 'PCA_signal' in signals.columns and 'Factor_signal' in signals.columns:
                signals['ensemble_signal'] = (
                    signals['PCA_signal'] * 0.5 + signals['Factor_signal'] * 0.5
                )
                signals['ensemble_confidence'] = (
                    signals['PCA_confidence'] * 0.5 + signals['Factor_confidence'] * 0.5
                )
            
            logger.info(f"매매 신호 생성 완료: {code}, shape: {signals.shape}")
            return signals
            
        except Exception as e:
            logger.error(f"매매 신호 생성 실패: {e}")
            return pd.DataFrame()
    
    def _generate_model_signals(self, model, df: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """
        개별 모델로 매매 신호 생성
        
        Args:
            model: PCA 또는 요인분석 모델
            df: 가격 데이터
            model_name: 모델 이름
            
        Returns:
            신호 DataFrame
        """
        try:
            signals = pd.DataFrame(index=df.index)
            
            # 시퀀스 길이
            sequence_length = model.model.input_shape[1]
            
            # 데이터 준비
            if model_name == 'PCA':
                n_components = model.model.input_shape[2]
                processed_df, _, _ = model.preprocessor.prepare_pca_data(df, n_components)
            else:  # Factor
                n_factors = model.model.input_shape[2]
                processed_df, _, _ = model.preprocessor.prepare_factor_analysis_data(df, n_factors)
            
            if processed_df is None:
                return signals
            
            # 슬라이딩 윈도우로 예측
            predictions = []
            confidences = []
            
            for i in range(sequence_length, len(processed_df)):
                # 시퀀스 추출
                sequence = processed_df.iloc[i-sequence_length:i].values.reshape(1, sequence_length, -1)
                
                # 예측
                pred = model.model.predict(sequence, verbose=0)[0][0]
                predictions.append(pred)
                
                # 신뢰도 계산 (예측값의 절대값을 신뢰도로 사용)
                confidence = min(abs(pred) * 10, 1.0)  # 스케일링
                confidences.append(confidence)
            
            # 신호 생성
            signals[f'{model_name}_prediction'] = np.nan
            signals[f'{model_name}_prediction'].iloc[sequence_length:] = predictions
            
            signals[f'{model_name}_signal'] = 0
            signals[f'{model_name}_signal'].iloc[sequence_length:] = np.where(
                np.array(predictions) > 0.01, 1,  # 1% 이상 상승 예상: 매수
                np.where(np.array(predictions) < -0.01, -1, 0)  # 1% 이상 하락 예상: 매도
            )
            
            signals[f'{model_name}_confidence'] = np.nan
            signals[f'{model_name}_confidence'].iloc[sequence_length:] = confidences
            
            return signals
            
        except Exception as e:
            logger.error(f"{model_name} 신호 생성 실패: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, code: str, start_date: str, end_date: str, 
                     initial_capital: float = 10000000, strategy: str = 'ensemble') -> Dict:
        """
        백테스팅 실행
        
        Args:
            code: 종목 코드
            start_date: 시작일자
            end_date: 종료일자
            initial_capital: 초기 자본
            strategy: 'PCA', 'Factor', 'ensemble'
            
        Returns:
            백테스팅 결과
        """
        try:
            # 모델 로드
            if not self.load_trained_models(code):
                logger.error(f"학습된 모델이 없습니다: {code}")
                return {}
            
            # 매매 신호 생성
            signals = self.generate_signals(code, start_date, end_date)
            if signals.empty:
                return {}
            
            # 전략 선택
            if strategy == 'PCA' and 'PCA_signal' in signals.columns:
                signal_col = 'PCA_signal'
                confidence_col = 'PCA_confidence'
            elif strategy == 'Factor' and 'Factor_signal' in signals.columns:
                signal_col = 'Factor_signal'
                confidence_col = 'Factor_confidence'
            elif strategy == 'ensemble' and 'ensemble_signal' in signals.columns:
                signal_col = 'ensemble_signal'
                confidence_col = 'ensemble_confidence'
            else:
                logger.error(f"지원하지 않는 전략: {strategy}")
                return {}
            
            # 백테스팅 실행
            backtest_result = self._execute_backtest(
                signals, signal_col, confidence_col, initial_capital
            )
            
            # 결과 저장
            self.backtest_results[code] = backtest_result
            
            # 데이터베이스에 저장
            self._save_backtest_result(code, backtest_result, strategy)
            
            logger.info(f"백테스팅 완료: {code}, 수익률: {backtest_result.get('total_return', 0):.2%}")
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"백테스팅 실행 실패: {e}")
            return {}
    
    def _execute_backtest(self, signals: pd.DataFrame, signal_col: str, 
                          confidence_col: str, initial_capital: float) -> Dict:
        """
        실제 백테스팅 로직 실행
        
        Args:
            signals: 신호 데이터
            signal_col: 신호 컬럼
            confidence_col: 신뢰도 컬럼
            initial_capital: 초기 자본
            
        Returns:
            백테스팅 결과
        """
        try:
            capital = initial_capital
            position = 0
            shares = 0
            entries = []
            
            # 수수료 설정
            commission_rate = 0.00015  # 0.015%
            
            for i, (timestamp, row) in enumerate(signals.iterrows()):
                if pd.isna(row[signal_col]) or pd.isna(row[confidence_col]):
                    continue
                
                price = row['price']
                signal = row[signal_col]
                confidence = row[confidence_col]
                
                # 신뢰도 필터
                if confidence < 0.3:  # 신뢰도 30% 미만은 거래 안함
                    continue
                
                # 매매 로직
                if signal == 1 and position == 0:  # 매수
                    shares = int(capital * 0.95 / price)  # 95% 투자
                    commission = shares * price * commission_rate
                    capital -= shares * price + commission
                    position = 1
                    
                    entries.append({
                        'timestamp': timestamp,
                        'action': 'BUY',
                        'price': price,
                        'shares': shares,
                        'commission': commission,
                        'capital': capital,
                        'confidence': confidence
                    })
                    
                elif signal == -1 and position == 1:  # 매도
                    commission = shares * price * commission_rate
                    capital += shares * price - commission
                    position = 0
                    
                    entries.append({
                        'timestamp': timestamp,
                        'action': 'SELL',
                        'price': price,
                        'shares': shares,
                        'commission': commission,
                        'capital': capital,
                        'confidence': confidence
                    })
                    
                    shares = 0
            
            # 최종 평가
            final_value = capital
            if position == 1:
                final_value += shares * signals['price'].iloc[-1]
            
            # 성과 지표 계산
            total_return = (final_value - initial_capital) / initial_capital
            
            # 거래 기록
            trades_df = pd.DataFrame(entries)
            
            # 최대 낙폭 계산
            if not trades_df.empty:
                trades_df['portfolio_value'] = np.where(
                    trades_df['action'] == 'BUY',
                    initial_capital - trades_df['capital'] - trades_df['commission'],
                    trades_df['capital']
                )
                
                peak = trades_df['portfolio_value'].expanding().max()
                drawdown = (trades_df['portfolio_value'] - peak) / peak
                max_drawdown = drawdown.min()
            else:
                max_drawdown = 0
            
            result = {
                'initial_capital': initial_capital,
                'final_value': final_value,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'total_trades': len(trades_df),
                'trades': trades_df,
                'signals': signals,
                'analyzer': signal_col
            }
            
            return result
            
        except Exception as e:
            logger.error(f"백테스팅 로직 실행 실패: {e}")
            return {}
    
    def _save_backtest_result(self, code: str, result: Dict, strategy: str):
        """
        백테스팅 결과 데이터베이스에 저장
        
        Args:
            code: 종목 코드
            result: 백테스팅 결과
            strategy: 전략 이름
        """
        try:
            conn = sqlite3.connect(DB_STRATEGY)
            cursor = conn.cursor()
            
            # 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deep_learning_backtest (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    analyzer TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    final_value REAL,
                    total_return REAL,
                    max_drawdown REAL,
                    total_trades INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 결과 저장
            cursor.execute('''
                INSERT INTO deep_learning_backtest 
                (code, analyzer, start_date, end_date, initial_capital, 
                 final_value, total_return, max_drawdown, total_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code, strategy,
                result['signals'].index[0].strftime('%Y-%m-%d'),
                result['signals'].index[-1].strftime('%Y-%m-%d'),
                result['initial_capital'],
                result['final_value'],
                result['total_return'],
                result['max_drawdown'],
                result['total_trades']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"백테스팅 결과 저장 완료: {code}")
            
        except Exception as e:
            logger.error(f"백테스팅 결과 저장 실패: {e}")
    
    def compare_strategies(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        전략별 성과 비교
        
        Args:
            code: 종목 코드
            start_date: 시작일자
            end_date: 종료일자
            
        Returns:
            비교 결과 DataFrame
        """
        try:
            strategies = ['PCA', 'Factor', 'ensemble']
            results = []
            
            for strategy in strategies:
                result = self.run_backtest(code, start_date, end_date, strategy=strategy)
                if result:
                    results.append({
                        'Strategy': strategy,
                        'Total Return': f"{result['total_return']:.2%}",
                        'Max Drawdown': f"{result['max_drawdown']:.2%}",
                        'Total Trades': result['total_trades'],
                        'Final Value': f"{result['final_value']:,.0f}"
                    })
            
            comparison_df = pd.DataFrame(results)
            logger.info(f"전략 비교 완료: {code}")
            
            return comparison_df
            
        except Exception as e:
            logger.error(f"전략 비교 실패: {e}")
            return pd.DataFrame()
    
    def get_backtest_report(self, code: str) -> Dict:
        """
        백테스팅 리포트 생성
        
        Args:
            code: 종목 코드
            
        Returns:
            리포트 딕셔너리
        """
        try:
            if code not in self.backtest_results:
                logger.error(f"백테스팅 결과가 없습니다: {code}")
                return {}
            
            result = self.backtest_results[code]
            
            # 기본 통계
            trades = result['trades']
            if not trades.empty:
                winning_trades = trades[trades['action'] == 'SELL']
                if len(winning_trades) > 0:
                    win_rate = len(winning_trades[winning_trades['capital'] > result['initial_capital']]) / len(winning_trades)
                else:
                    win_rate = 0
            else:
                win_rate = 0
            
            report = {
                'code': code,
                'analyzer': result['analyzer'],
                'period': f"{result['signals'].index[0].strftime('%Y-%m-%d')} ~ {result['signals'].index[-1].strftime('%Y-%m-%d')}",
                'initial_capital': f"{result['initial_capital']:,.0f}",
                'final_value': f"{result['final_value']:,.0f}",
                'total_return': f"{result['total_return']:.2%}",
                'max_drawdown': f"{result['max_drawdown']:.2%}",
                'total_trades': result['total_trades'],
                'win_rate': f"{win_rate:.2%}",
                'avg_confidence': f"{result['signals'][result['analyzer'].replace('_signal', '_confidence')].mean():.3f}"
            }
            
            return report
            
        except Exception as e:
            logger.error(f"리포트 생성 실패: {e}")
            return {}


if __name__ == "__main__":
    engine = DeepLearningBacktestEngine(market='stock', data_type='tick')

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_STOCK_BACK_MIN = os.path.join(base_dir, '_database', 'stock_tick_back.db')
    con = sqlite3.connect(DB_STOCK_BACK_MIN)
    df_ = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
    table_list = df_['name'].to_list()
    table_list.remove('moneytop')
    table_list.remove('stockinfo')
    
    last = len(table_list)
    for j, code_ in enumerate(table_list):
        print(f"DeepLearningBacktestEngine 시작 : {code_} [{j + 1}/{last}]")
        result_ = engine.run_backtest(
            code=code_,
            start_date='20250502090000',
            end_date='20260211153000',
            strategy='Factor'
        )
        if result_:
            print("백테스팅 결과:", result_)

            # # 리포트 생성
            # report_ = engine.get_backtest_report(code_)
            # print("리포트:", report_)
            #
            # # 전략 비교
            # comparison = engine.compare_strategies(code_, '20250410090000', '20260211153000')
            # print("전략 비교:")
            # print(comparison)
    print(f'DeepLearningBacktestEngine 완료')
