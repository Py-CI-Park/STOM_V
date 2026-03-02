"""
다종목 실시간 LightGBM + Online Learning 트레이딩 시스템
여러 종목 동시 실시간 예측 및 트레이딩
"""

import os
import logging
import sqlite3
import warnings
import numpy as np
import pandas as pd
from typing import Dict
from datetime import datetime
from traceback import print_exc
from lightgbm import LGBMRegressor

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['LIGHTGBM_NO_WARNINGS'] = '1'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger()


# 주식 틱 데이터 칼럼
list_stock_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]
# 버프에 기록된 이차원 어레이의 순서
buffer_arry_tick = [
    'index', '현재가', '등락율', '체결강도', '초당매수금액', '초당매도금액', '고저평균대비등락율', '저가대비고가등락율',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격', '매도총잔량', '매수총잔량'
]


def dt_ymdhms(str_time):
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}:{str_time[12:14]}'
    return datetime.fromisoformat(str_time)


class Model:
    """개별 종목 모델"""
    def __init__(self, code: str):
        self.code = code

        # LightGBM 모델 (러프한 설정으로 과적합 최소화)
        self.lgb_model = LGBMRegressor(
            n_estimators=20,                # 트리 개수: 20으로 극단적 감소
            learning_rate=0.3,              # 학습률: 0.3으로 극단적 증가
            min_child_samples=5,            # 최소 자식 샘플: 5개로 대폭 감소
            max_depth=2,                    # 최대 깊이: 2으로 극단적 감소
            reg_alpha=1.0,                  # L1 정규화: 1.0으로 강화
            reg_lambda=1.0,                 # L2 정규화: 1.0으로 강화
            random_state=1,                 # 랜덤 시드: 1로 고정하여 재현성 보장
            objective='regression_l2',      # MSE 기반으로 안정성 유지
            metric='rmse',                  # 평가 지표: RMSE로 오차 크기 측정
            n_jobs=-1,                      # 병렬 처리: -1로 모든 CPU 코어 사용하여 속도 최적화
            verbose=-1,                     # 로깅: -1으로 출력 억제하여 깨끗한 실행
        )

        # 데이터 버퍼
        self.tick_buffer    = []
        self.train_buffer   = []
        self.target_buffer  = []
        self.pred_buffer    = []

        # 상태
        self.model_learned  = False
        self.buffer_count   = 0

    def add_prediction_result(self, prediction, lookahead, test_mode):
        """예측 결과 추가"""
        # 실제등락율 및 모델점수는 self.predahead 개의 틱이 추가된 시점에서 처리
        self.pred_buffer.append([prediction, None, None])
        # 버퍼 관리 - 테스트 모드 일때는 결과 집계를 위해 삭제하지 않는다.
        if not test_mode:
            if len(self.pred_buffer) > lookahead:
                self.pred_buffer.pop(0)

    def update_prediction_result(self, actual_return, predahead):
        """모델 성능 평가"""
        prediction = self.pred_buffer[-predahead][0]
        performance_score = max(0, 1.0 - abs(prediction - actual_return))  # 오차가 작을수록 높은 점수
        self.pred_buffer[-predahead][1] = actual_return
        self.pred_buffer[-predahead][2] = performance_score

    def get_model_performance(self, lookahead, predahead) -> float:
        """특정 모델의 최근 성능 점수 반환"""
        # 최근 성능 점수 평균
        performance_scores = [p[2] for p in self.pred_buffer if p[2] is not None][-lookahead:]
        if len(performance_scores) >= predahead:
            weighted_performance = sum(performance_scores) / len(performance_scores)
            normalized_performance = max(0.1, min(weighted_performance, 1.0))
            return normalized_performance
        else:
            return 0.1


class RealtimeDeeplearning:
    """다종목 실시간 딥러닝"""
    def __init__(self, buyper, confidence: float = 0.6, betting: int = 20_000_000,
                 lookahead: int = 60, predahead: int = 10, test_mode: bool = False):

        self.buyper     = buyper        # 매수 예측 등락율
        self.confidence = confidence    # 진입 신뢰도 제한
        self.betting    = betting       # 종목당 배팅금액
        self.lookahead  = lookahead     # 학습에 사용할 데이터 수
        self.predahead  = predahead     # 예측할 미래의 데이터 수
        self.test_mode  = test_mode     # 테스트 모드, 모델평가버퍼 삭제 안함

        # 종목별 모델 관리
        self.models = {}
        self.signal = {}
        self.trade  = []

        # 가공된 팩터 번호
        self.factor_index = {name: i for i, name in enumerate(list_stock_tick)}

        # 기본 팩터 번호
        self.arry_index = {name: i for i, name in enumerate(buffer_arry_tick)}

    def _add_code_model(self, code: str):
        """종목 모델 및 시그널 생성"""
        self.models[code] = Model(code)
        self.signal[code] = [None, 0, 0, 0, 0]

    def _extract_features(self, model: Model, training: bool = True):
        """종목별 피처 추출
        Args:
            model: 종목별 모델
            training: 학습 및 예측 구분
        """
        try:
            if training:
                # 모텔 학습 시 마지막 self.predahead 개의 데이터 제외
                recent_ticks = np.array(model.tick_buffer[-(self.lookahead+self.predahead):-self.predahead])
            else:
                # 모텔 예측 시 마지막 self.lookahead 개의 데이터
                recent_ticks = np.array(model.tick_buffer[-self.lookahead:])

            # 가격 데이터 추출
            prices = recent_ticks[:, self.arry_index['현재가']]
            current_price = prices[-1]

            # 변동성 돌파
            index = int(self.lookahead / 2)
            curr_volatility = np.std(prices[-index:])
            prev_volatility = np.std(prices[:-index])
            # noinspection PyTypeChecker
            volatility_ratio = min(1.0, curr_volatility / (prev_volatility + 1e-8) / 10)

            # 현재가 대비 변동성
            volatility = np.std(prices)
            price_volatility_ratio = volatility / (current_price + 1e-8)

            # 모멘텀
            momentum = np.clip((current_price - prices[0]) / prices[0] * 10, -1.0, 1.0)

            # 초당매수금액 / (초당매수금액 + 초당매도금액)
            buy_amounts = recent_ticks[:, self.arry_index['초당매수금액']]
            sell_amounts = recent_ticks[:, self.arry_index['초당매도금액']]
            current_buy_amount = buy_amounts[-1]
            current_sell_amount = sell_amounts[-1]
            buy_sell_ratio = current_buy_amount / (current_buy_amount + current_sell_amount + 1e-8)

            # 초당매수금액평균 대비 초당매수금액
            avg_buy_amount = np.mean(buy_amounts)
            # noinspection PyTypeChecker
            buy_amount_ratio = min(1.0, current_buy_amount / (avg_buy_amount + 1e-8) / 10)

            # 초당매도금액평균 대비 초당매도금액
            avg_sell_amount = np.mean(sell_amounts)
            # noinspection PyTypeChecker
            sell_amount_ratio = min(1.0, current_sell_amount / (avg_sell_amount + 1e-8) / 10)

            # 거래대금평균 대비 거래대금
            volumes = buy_amounts + sell_amounts
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes)
            # noinspection PyTypeChecker
            volume_ratio = min(1.0, current_volume / (avg_volume + 1e-8) / 5)

            # 등락율
            current_change = min(1.0, recent_ticks[-1, self.arry_index['등락율']] / 30)

            # 고저평균대비등락율
            current_high_low_per = min(1.0, recent_ticks[-1, self.arry_index['고저평균대비등락율']] / 30)

            # 저가대비고가등락율
            current_low_high_per = min(1.0, recent_ticks[-1, self.arry_index['저가대비고가등락율']] / 30)

            # 당일매수금액 / (당일매수금액 + 당일매도금액)
            current_daily_buy = recent_ticks[-1, self.arry_index['당일매수금액']]
            current_daily_sell = recent_ticks[-1, self.arry_index['당일매도금액']]
            current_day_buy_sell_ratio = current_daily_buy / (current_daily_buy + current_daily_sell + 1e-8)

            # 최고매수금액 / (최고매수금액 + 최고매도금액)
            high_buy_amount = recent_ticks[-1, self.arry_index['최고매수금액']]
            high_sell_amount = recent_ticks[-1, self.arry_index['최고매도금액']]
            current_high_buy_sell_ratio = high_buy_amount / (high_buy_amount + high_sell_amount + 1e-8)

            # 최고매수가격 대비 현재가
            max_buy_price = recent_ticks[-1, self.arry_index['최고매수가격']]
            max_buy_per = np.clip((current_price - max_buy_price) / max_buy_price / 10, -1.0, 1.0)

            # 최고매도가격 대비 현재가
            max_sell_price = recent_ticks[-1, self.arry_index['최고매도가격']]
            max_sell_per = np.clip((current_price - max_sell_price) / (max_sell_price + 1e-8) / 10, -1.0, 1.0)

            # 최고매도가격 대비 최고매수가격
            max_sell_buy_per = np.clip((max_buy_price - max_sell_price) / (max_sell_price + 1e-8) / 10, -1.0, 1.0)

            # 매도수총잔량 비율
            total_bids_qty = recent_ticks[-1, self.arry_index['매수총잔량']]
            total_asks_qty = recent_ticks[-1, self.arry_index['매도총잔량']]
            total_bids_asks_ratio = total_bids_qty / (total_bids_qty + total_asks_qty + 1e-8)

            # RSI
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            # noinspection PyTypeChecker
            rs = avg_gain / (avg_loss + 1e-8)
            rsi = min(1.0, (100 - (100 / (1 + rs))) / 100)

            # 볼린저 밴드
            bb_middle = np.mean(prices)
            bb_std = np.std(prices)
            # noinspection PyTypeChecker
            bb_upper = bb_middle + 2 * bb_std
            # noinspection PyTypeChecker
            bb_lower = bb_middle - 2 * bb_std
            bb_position = min(1.0, (current_price - bb_lower) / (bb_upper - bb_lower + 1e-8) / 2)
            bb_area_ratio = min(1.0, (bb_upper - bb_lower) / bb_lower / 10)

            # MACD (12, 26, 9)
            ema12 = self._calculate_ema(prices, 12)
            ema26 = self._calculate_ema(prices, 26)
            macd_line = ema12[-1] - ema26[-1]
            signal_line = self._calculate_ema([macd_line], 9)[-1] if len([macd_line]) >= 9 else macd_line
            macd_histogram = np.clip((macd_line - signal_line) / (signal_line + 1e-8) * 10, -1.0, 1.0)

            # 거래량 모멘텀 (OBV 스타일)
            volume_momentum = np.sum(np.diff(volumes) * np.sign(np.diff(prices))) if len(volumes) > 1 else 0
            # noinspection PyTypeChecker
            volume_momentum_norm = volume_momentum / (np.sum(volumes) + 1e-8)

            # 단기 모멘텀 가속도
            price_momentum_10 = (prices[-1] - prices[-10]) / (prices[-10] + 1e-8) * 100
            price_momentum_20 = (prices[-10] - prices[-30]) / (prices[-30] + 1e-8) * 100
            momentum_acceleration = np.clip((price_momentum_10 - price_momentum_20) / (price_momentum_20 + 1e-8) * 10, -1.0, 1.0)

            # 거래량 가중 가격 (VWAP 스타일)
            # noinspection PyTypeChecker
            volume_weighted_price = np.sum(prices * volumes) / (np.sum(volumes) + 1e-8)
            vwap_deviation = np.clip((current_price - volume_weighted_price) / volume_weighted_price * 10, -1.0, 1.0)

            # 단기 변동성 스파이크
            short_volatility = np.std(prices[-10:])
            long_volatility = np.std(prices[-30:])
            # noinspection PyTypeChecker
            volatility_spike = short_volatility / (short_volatility + long_volatility + 1e-8)

            # 매수/매도 금액 추세
            buy_trend = np.polyfit(np.arange(len(buy_amounts)), buy_amounts, 1)[0]
            sell_trend = np.polyfit(np.arange(len(sell_amounts)), sell_amounts, 1)[0]
            money_flow_trend = (buy_trend - sell_trend) / (abs(buy_trend) + abs(sell_trend) + 1e-8)

            # 윌리엄스 %R
            williams_r = self._calculate_williams_r(prices)

            # 머니 플로우 인덱스
            mfi = self._calculate_money_flow_index(buy_amounts, sell_amounts)

            # 추세 강도
            trend_strength = self._calculate_trend_strength(prices)

            # CCI (Commodity Channel Index)
            cci = self._calculate_cci(prices)

            # ROC (Rate of Change)
            roc = self._calculate_roc(prices)

            # 가격 거래량 상관관계
            price_volume_correlation = self._calculate_price_volume_correlation(prices, volumes)

            # 시간 특성
            hour_ratio = int(str(int(recent_ticks[-1, self.arry_index['index']]))[-6:-4]) / 24

            features = np.array([
                volatility_ratio,
                price_volatility_ratio,
                momentum,
                buy_sell_ratio,
                buy_amount_ratio,
                sell_amount_ratio,
                volume_ratio,
                current_change,
                current_high_low_per,
                current_low_high_per,
                current_day_buy_sell_ratio,
                current_high_buy_sell_ratio,
                max_buy_per,
                max_sell_per,
                max_sell_buy_per,
                total_bids_asks_ratio,
                rsi,
                bb_position,
                bb_area_ratio,
                macd_histogram,
                volume_momentum_norm,
                momentum_acceleration,
                vwap_deviation,
                volatility_spike,
                money_flow_trend,
                williams_r,
                mfi,
                trend_strength,
                cci,
                roc,
                price_volume_correlation,
                hour_ratio,
            ])

            return features

        except:
            print_exc()
            logger.error(f"피처 추출 실패")
            return None

    def _calculate_ema(self, data, period):
        """EMA 계산"""
        try:
            if len(data) < period:
                return np.array([np.mean(data)])
            alpha = 2 / (period + 1)
            ema = [data[0]]
            for i in range(1, len(data)):
                ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
            return np.array(ema)
        except:
            return np.array([np.mean(data)])

    def _calculate_williams_r(self, prices):
        """윌리엄스 %R 계산"""
        try:
            highest = np.max(prices)
            lowest = np.min(prices)

            if highest == lowest:
                return 0.0

            williams_r = (highest - prices[-1]) / (highest - lowest)
            return np.clip(williams_r * 2 - 1, -1.0, 1.0)  # -1~1로 정규화
        except:
            return 0.0

    def _calculate_money_flow_index(self, buy_amounts, sell_amounts):
        """머니 플로우 인덱스 계산"""
        try:
            money_flow = buy_amounts - sell_amounts
            positive_flow = np.sum(np.where(money_flow > 0, money_flow, 0))
            negative_flow = np.sum(np.where(money_flow < 0, -money_flow, 0))

            if negative_flow == 0:
                return 1.0

            mfi = 1 - (1 / (1 + positive_flow / negative_flow))
            return np.clip(mfi * 2 - 1, -1.0, 1.0)  # -1~1로 정규화
        except:
            return 0.0

    def _calculate_trend_strength(self, prices):
        """추세 강도 계산"""
        try:
            # 선형 회귀 기반 추세 강도
            x = np.arange(len(prices))
            slope, intercept = np.polyfit(x, prices, 1)

            # R-squared 계산
            y_pred = slope * x + intercept
            ss_res = np.sum((prices - y_pred) ** 2)
            # noinspection PyTypeChecker
            ss_tot = np.sum((prices - np.mean(prices)) ** 2)

            if ss_tot == 0:
                return 0.0

            r_squared = 1 - (ss_res / ss_tot)

            # 추세 방향과 강도 결합
            trend_direction = np.sign(slope)
            trend_strength = trend_direction * r_squared

            return np.clip(trend_strength, -1.0, 1.0)
        except:
            return 0.0

    def _calculate_cci(self, prices):
        """CCI (Commodity Channel Index) 계산"""
        try:
            sma = np.mean(prices)
            # noinspection PyTypeChecker
            mean_deviation = np.mean(np.abs(prices - sma))

            if mean_deviation == 0:
                return 0.0

            # noinspection PyTypeChecker
            cci = (prices[-1] - sma) / (0.015 * mean_deviation)
            return np.clip(cci / 100, -1.0, 1.0)  # 정규화
        except:
            return 0.0

    def _calculate_roc(self, prices):
        """ROC (Rate of Change) 계산"""
        try:
            current_price = prices[-1]
            past_price = prices[0]

            if past_price == 0:
                return 0.0

            roc = (current_price - past_price) / past_price
            return np.clip(roc * 10, -1.0, 1.0)  # 정규화
        except:
            return 0.0

    def _calculate_price_volume_correlation(self, prices, volumes):
        """가격 거래량 상관관계"""
        try:
            price_changes = np.diff(prices)
            volume_changes = np.diff(volumes)

            if len(price_changes) == 0 or len(volume_changes) == 0:
                return 0.0

            correlation = np.corrcoef(price_changes, volume_changes)[0, 1]

            if np.isnan(correlation):
                return 0.0
            
            return np.clip(correlation, -1.0, 1.0)
        except:
            return 0.0

    def update_realtime_tick_data(self, code: str, tick_data: np.ndarray, index: int = 0, last: bool = False) -> Dict:
        """실시간 틱 처리
        Args:
            code: 종목 코드
            tick_data: 틱 데이터
            index: 인덱스번호
            last: 마지막 인덱스 유무
        """
        if code not in self.models:
            self._add_code_model(code)

        model = self.models[code]

        try:
            buffer_size_limit = self.lookahead + self.predahead

            # 데이터 버퍼에 데이터 추가
            self._add_tick_buffer(model, tick_data, buffer_size_limit)

            # 학습기간 + 예측기간 개의 데이터 쌓인 후부터 예측 시작 - 타겟 계산용인 예측기간 이후의 현재가 데이터가 있어야 하기 때문이다.
            if len(model.tick_buffer) < buffer_size_limit:
                return {
                    'status': 'collecting_data',
                    'code': code,
                    'buffer_size': len(model.tick_buffer)
                }

            # 모델 타겟 추출 - 예측기간 + 1 이전의 현재가 대비 현재가의 등락율이 타겟이다.(30틱 이후의 현재가)
            past_index = -(self.predahead + 1)
            future_price = model.tick_buffer[-1][self.arry_index['현재가']]
            current_price = model.tick_buffer[past_index][self.arry_index['현재가']]
            actual_return = (future_price - current_price) / current_price * 100

            # 과거 예측값의 성능 평가 - 모델 예측할 때 미리 생성해둔 성능평가용 리스트 업데이트 한다.
            # 예측한 이후 예측기간 만큼 데이터가 추가로 쌓였을 때 평가를 할 수 있다.
            if len(model.pred_buffer) >= self.predahead:
                model.update_prediction_result(actual_return, self.predahead)

            # 모델 학습
            self._training_model(model, actual_return)

            # 모델 예측 - 최초 학습이 실행된 이후부터 바로 예측
            if model.model_learned:
                prediction, confidence = self._predict_with_ensemble(model)
                if self.test_mode:
                    self._backtest(model, code, prediction, confidence, future_price, index, last)
            else:
                prediction, confidence = 0.0, 0.0

            # 결과
            result = {
                'code': code,
                'prediction': prediction,
                'confidence': confidence
            }
            return result

        except:
            print_exc()
            logger.error(f"종목 {code} 틱처리 실패")
            result = {
                'code': code,
                'prediction': 0.0,
                'confidence': 0.0
            }
            return result

    def _add_tick_buffer(self, model: Model, tick_data: np.ndarray, buffer_size_limit: int):
        new_data = [
            tick_data[self.factor_index['index']],
            tick_data[self.factor_index['현재가']],
            tick_data[self.factor_index['등락율']],
            tick_data[self.factor_index['체결강도']],
            tick_data[self.factor_index['초당매수금액']],
            tick_data[self.factor_index['초당매도금액']],
            tick_data[self.factor_index['고저평균대비등락율']],
            tick_data[self.factor_index['저가대비고가등락율']],
            tick_data[self.factor_index['당일매수금액']],
            tick_data[self.factor_index['최고매수금액']],
            tick_data[self.factor_index['최고매수가격']],
            tick_data[self.factor_index['당일매도금액']],
            tick_data[self.factor_index['최고매도금액']],
            tick_data[self.factor_index['최고매도가격']],
            tick_data[self.factor_index['매수총잔량']],
            tick_data[self.factor_index['매도총잔량']]
        ]

        # 데이터 버퍼에 추가
        model.tick_buffer.append(new_data)

        # 버퍼 크기 관리 - 원본 데이터는 학습기간 + 예측기간의 데이터만 보유
        if len(model.tick_buffer) > buffer_size_limit:
            model.tick_buffer.pop(0)

    def _training_model(self, model: Model, actual_return: float):
        """모델 학습"""
        try:
            # 피처 추출
            features = self._extract_features(model, True)

            # 버퍼 추가
            model.train_buffer.append(features)
            model.target_buffer.append(actual_return)
            model.buffer_count += 1

            # 버퍼 관리 - 학습용 데이터는 항상 학습기간 만큼의 데이터만 보유
            if len(model.train_buffer) > self.lookahead:
                model.train_buffer.pop(0)
                model.target_buffer.pop(0)

            # 버퍼 카운터가 학습구간 보다 같거나 높고 int(self.lookahead / 3) 으로 나누어 떨어질 때 학습한다.
            if model.buffer_count >= self.lookahead and model.buffer_count % int(self.lookahead / 3) == 0:
                features = np.array(model.train_buffer)
                targets = np.array(model.target_buffer)

                # 타겟 값의 유니크 개수 확인 - 모두 동일하면 학습 건너뛰기
                unique_targets = len(np.unique(targets))
                if unique_targets <= 5: return

                # 모든 모델 학습
                model.lgb_model.fit(features, targets)
                # model.sgd_model.fit(features, targets)

                if not model.model_learned: model.model_learned = True

        except:
            print_exc()
            logger.error(f"종목 학습 실패")

    def _predict_with_ensemble(self, model: Model) -> tuple:
        """예측 및 신뢰도 계산 (단순화)"""
        try:
            # 피처 추출
            features = self._extract_features(model, False)

            # 예측
            try:
                prediction = model.lgb_model.predict([features])[0]
            except:
                prediction = 0.0

            confidence = model.get_model_performance(self.lookahead, self.predahead)

            # 모델 성능 추적용
            model.add_prediction_result(prediction, self.lookahead, self.test_mode)

            return prediction, confidence
        except:
            print_exc()
            logger.error(f"모델 예측 실패")
            return 0.0, 0.0

    def _backtest(self, model: Model, code: str, prediction: float, confidence: float,
                  curr_price: float, index: int, last: bool):

        def currr_index():
            ci = str(int(model.tick_buffer[-1][self.arry_index['index']]))
            ci = f"{ci[:4]}-{ci[4:6]}-{ci[6:8]} {ci[8:10]}:{ci[10:12]}:{ci[12:14]}"
            return ci

        if len(model.pred_buffer) < 3:
            return

        pre1_prediction = model.pred_buffer[-2][0]
        pre2_prediction = model.pred_buffer[-3][0]
        if self.signal[code][0] is None:
            if confidence >= self.confidence and prediction >= self.buyper and \
                    pre1_prediction >= self.buyper and pre2_prediction >= self.buyper:

                lhp = model.tick_buffer[-1][self.arry_index['저가대비고가등락율']]
                betting = int(self.betting * max(0.2, (10 - lhp) / 10))
                self.signal[code] = [curr_price, betting, prediction, index]
                logger.info(f"종목코드[{code}] {currr_index()} | "
                            f"진입예측: {prediction:+.2f}% | 진입신뢰도: {confidence:.2f} | "
                            f"배팅금액: {betting:>10,}")

        else:
            buy_price, betting, buy_pred, buy_index = self.signal[code]
            sp = np.round((curr_price / buy_price - 1) * 100 - 0.3, 2)
            if last or sp >= 3 or sp <= -2:
                # noinspection PyTypeChecker
                sig = int(betting * sp / 100)
                hold_tick = index - buy_index
                self.trade.append([sp, sig, hold_tick, buy_pred])
                self.signal[code][0] = None
                if last: prediction, confidence = 0.0, 0.0
                logger.info(f"종목코드[{code}] {currr_index()} | "
                            f"청산예측: {prediction:+.2f}% | 청산신뢰도: {confidence:.2f} | "
                            f"수익금액: {sig:>+10,} | 수익률: {sp:>+6.2f}% | 보유기간: {hold_tick:>4,}")

    def get_portfolio_stats(self, buyper: float) -> Dict:
        """포트폴리오 전체 통계"""
        # 전체 성능 계산
        final_stats = {}

        # 모든 모델의 예측 결과 수집
        predictions = []
        for _, model in self.models.items():
            predictions.extend(model.pred_buffer)

        # 유효한 예측만 필터링 및 성능 계산
        valid_predictions = [p for p in predictions if p[2] is not None]
        final_stats['total_preds'] = len(valid_predictions)

        # 모델 성능 통계
        if len(valid_predictions) > 0:
            # 진입 타이밍 성능 (buyper 이상)
            buy_pred_values = [p[0] for p in valid_predictions if p[0] >= buyper]
            buy_actual_values = [p[1] for p in valid_predictions if p[0] >= buyper]
            final_stats['total_buy_preds'] = len(buy_pred_values)
            if len(buy_pred_values) > 0:
                final_stats['buy_direction_accuracy'] = sum(1 for p, a in zip(buy_pred_values, buy_actual_values) if (p >= 0) == (a >= 0)) / len(buy_pred_values) * 100
                final_stats['buy_mean_error'] = np.mean([abs(p - a) for p, a in zip(buy_pred_values, buy_actual_values)])
                final_stats['buy_rmse'] = np.sqrt(np.mean([(p - a) ** 2 for p, a in zip(buy_pred_values, buy_actual_values)]))

        return final_stats


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
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        codes = df['name'].to_list()
        codes.remove('moneytop')
        if 'stockinfo' in codes:
            codes.remove('stockinfo')
            dict_cn = pd.read_sql(f"SELECT * FROM stockinfo", conn).set_index('index')
            dict_cn = dict_cn['종목명'].to_dict()
        if 'futureinfo' in codes:
            codes.remove('futureinfo')

        while True:
            selected_code = np.random.choice(codes)
            codes.remove(selected_code)
            df = pd.read_sql(f"SELECT * FROM '{selected_code}' WHERE `index` >= 20250501000000", conn)
            if not df.empty:
                lastday = int(str(df['index'].iloc[-1])[:8])
                df = df[df['index'] >= lastday * 1000000]
                code_list.append(selected_code)
                data_list.append(np.array(df))
                print(f"선택종목 [{selected_code}] {dict_cn.get(selected_code)}")
                if len(code_list) == count:
                    break
    else:
        conn = sqlite3.connect(f'../_database/{db_file}.db')
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
        codes = df['name'].to_list()
        codes.remove('moneytop')
        count = len(codes)
        for i, code in enumerate(codes):
            df = pd.read_sql(f"SELECT * FROM '{code}'", conn)
            code_list.append(code)
            data_list.append(np.array(df))
            print(f"데이터로딩 [{code}], 길이[{len(df)}], [{i+1}/{count}]")

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
            last = i == len_list[j] - 1 or str(data_list[j][i, 0])[:8] != str(data_list[j][i+1, 0])[:8]
            trader.update_realtime_tick_data(code, tick_data, i, last=last)

        if i % 100 == 0:
            print(f"{datetime.now()} - 진행 상황 [{i+1}/{max_len}]")

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
        p_ratio = np.round(plus_cnt / (plus_cnt + minus_cnt) * 100, 2) if (plus_cnt + minus_cnt) > 0 else 0.0
        avg_hold = int(np.mean([x[2] for x in trader.trade]))
        t_per = sum([x[0] for x in trader.trade])
        t_sig = sum([x[1] for x in trader.trade])

        plus_cnt1 = len([x[0] for x in trader.trade if x[0] >= 0 and x[-1] >= 1.0])
        minus_cnt1 = len([x[0] for x in trader.trade if x[0] < 0 and x[-1] >= 1.0])
        t_cnt1 = plus_cnt1 + minus_cnt1
        p_ratio1 = np.round(plus_cnt1 / (plus_cnt1 + minus_cnt1) * 100, 2) if (plus_cnt1 + minus_cnt1) > 0 else 0.0
        # noinspection PyTypeChecker
        avg_hold1 = int(max(0, np.mean([x[2] for x in trader.trade if x[-1] >= 1.0])))
        t_per1 = sum([x[0] for x in trader.trade if x[-1] >= 1.0])
        t_sig1 = sum([x[1] for x in trader.trade if x[-1] >= 1.0])

        plus_cnt2 = len([x[0] for x in trader.trade if x[0] >= 0 and x[-1] >= 2])
        minus_cnt2 = len([x[0] for x in trader.trade if x[0] < 0 and x[-1] >= 2])
        t_cnt2 = plus_cnt2 + minus_cnt2
        p_ratio2 = np.round(plus_cnt2 / (plus_cnt2 + minus_cnt2) * 100, 2) if (plus_cnt2 + minus_cnt2) > 0 else 0.0
        # noinspection PyTypeChecker
        avg_hold2 = int(max(0, np.mean([x[2] for x in trader.trade if x[-1] >= 2])))
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
