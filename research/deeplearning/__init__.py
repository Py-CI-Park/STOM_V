"""
STOM 2.0 딥러닝 모듈
PCA와 요인분석 기반 주가예측 시스템
"""

from .data_preprocessor import DataPreprocessor
from .pca_prediction_model import PCAPredictionModel
from .factor_analysis_model import FactorAnalysisModel
from .backtest_integration import DeepLearningBacktestEngine
from .config import (
    DeepLearningConfigManager,
    HyperparameterOptimizer,
    config_manager,
    hyperparameter_optimizer,
    get_predefined_config
)

__version__ = "1.0.0"
__author__ = "STOM 2.0 Team"

# 모듈 정보
__all__ = [
    'DataPreprocessor',
    'PCAPredictionModel', 
    'FactorAnalysisModel',
    'DeepLearningBacktestEngine',
    'DeepLearningConfigManager',
    'HyperparameterOptimizer',
    'config_manager',
    'hyperparameter_optimizer',
    'get_predefined_config'
]
