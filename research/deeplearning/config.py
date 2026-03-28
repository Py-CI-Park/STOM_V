"""
딥러닝 모델 설정 관리 모듈
모델 파라미터, 하이퍼파라미터, 실험 설정 등 관리
"""

import os
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DeepLearningConfig')


@dataclass
class ModelConfig:
    """모델 기본 설정"""
    market: str = 'stock'
    data_type: str = 'min'
    model_type: str = 'LSTM'
    sequence_length: int = 60
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    dropout_rate: float = 0.2
    
    # 데이터 관련
    n_components: int = 10  # PCA 주성분 개수
    n_factors: int = 5      # 요인분석 요인 개수
    prediction_horizon: int = 1  # 예측 기간
    
    # 학습 관련
    early_stopping_patience: int = 20
    reduce_lr_patience: int = 10
    min_lr: float = 1e-7
    validation_split: float = 0.2
    
    # 백테스팅 관련
    commission_rate: float = 0.00015
    min_confidence: float = 0.3
    position_size: float = 0.95


@dataclass
class PCAConfig:
    """PCA 모델 설정"""
    n_components: int = 10
    variance_threshold: float = 0.95
    use_kernel_pca: bool = False
    kernel_type: str = 'rbf'
    gamma: Optional[float] = None


@dataclass
class FactorAnalysisConfig:
    """요인분석 모델 설정"""
    n_factors: int = 5
    rotation: str = 'varimax'
    method: str = 'principal'
    use_smc: bool = True


@dataclass
class LSTMConfig:
    """LSTM 모델 설정"""
    units: List[int] = None
    return_sequences: List[bool] = None
    activation: str = 'tanh'
    recurrent_activation: str = 'sigmoid'
    use_batch_norm: bool = True
    
    def __post_init__(self):
        if self.units is None:
            self.units = [128, 64, 32]
        if self.return_sequences is None:
            self.return_sequences = [True, True, False]


@dataclass
class TransformerConfig:
    """Transformer 모델 설정"""
    embed_dim: int = 64
    num_heads: int = 4
    ff_dim: int = 128
    num_layers: int = 2
    dropout_rate: float = 0.1


class DeepLearningConfigManager:
    """딥러닝 설정 관리자"""
    
    def __init__(self, config_dir: str = './configs'):
        """
        설정 관리자 초기화
        
        Args:
            config_dir: 설정 파일 저장 디렉토리
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        # 기본 설정들
        self.default_configs = {
            'model': ModelConfig(),
            'pca': PCAConfig(),
            'factor_analysis': FactorAnalysisConfig(),
            'lstm': LSTMConfig(),
            'transformer': TransformerConfig()
        }
    
    def save_config(self, config_name: str, config: Dict, format_: str = 'json'):
        """
        설정 저장
        
        Args:
            config_name: 설정 이름
            config: 설정 딕셔너리
            format_: 'json' 또는 'yaml'
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{config_name}_{timestamp}.{format_}"
            filepath = os.path.join(self.config_dir, filename)
            
            if format_ == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False, default=str)
            elif format_ == 'yaml':
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"설정 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return None
    
    def load_config(self, filepath: str) -> Optional[Dict]:
        """
        설정 로드
        
        Args:
            filepath: 설정 파일 경로
            
        Returns:
            설정 딕셔너리
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"설정 파일이 없습니다: {filepath}")
                return None
            
            format_ = filepath.split('.')[-1]
            
            if format_ == 'json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            elif format_ == 'yaml':
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                logger.error(f"지원하지 않는 형식: {format_}")
                return None
            
            logger.info(f"설정 로드 완료: {filepath}")
            return config
            
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return None
    
    def get_default_config(self, config_type: str) -> Dict:
        """
        기본 설정 가져오기
        
        Args:
            config_type: 설정 타입 ('model', 'pca', 'factor_analysis', 'lstm', 'transformer')
            
        Returns:
            설정 딕셔너리
        """
        try:
            if config_type not in self.default_configs:
                logger.error(f"지원하지 않는 설정 타입: {config_type}")
                return {}
            
            config = self.default_configs[config_type]
            return asdict(config)
            
        except Exception as e:
            logger.error(f"기본 설정 가져오기 실패: {e}")
            return {}
    
    def create_experiment_config(self, experiment_name: str, **kwargs) -> str:
        """
        실험 설정 생성
        
        Args:
            experiment_name: 실험 이름
            **kwargs: 추가 설정 파라미터
            
        Returns:
            설정 파일 경로
        """
        try:
            # 기본 모델 설정
            config = self.get_default_config('model')
            
            # 실험별 설정 업데이트
            config.update(kwargs)
            
            # 실험 메타데이터 추가
            config['experiment_name'] = experiment_name
            config['created_at'] = datetime.now().isoformat()
            config['config_version'] = '1.0'
            
            # 설정 저장
            filepath = self.save_config(experiment_name, config)
            return filepath
            
        except Exception as e:
            logger.error(f"실험 설정 생성 실패: {e}")
            return ''
    
    def list_configs(self) -> List[str]:
        """
        저장된 설정 파일 목록
        
        Returns:
            설정 파일 경로 리스트
        """
        try:
            config_files = []
            for file in os.listdir(self.config_dir):
                if file.endswith(('.json', '.yaml', '.yml')):
                    config_files.append(os.path.join(self.config_dir, file))
            
            config_files.sort()
            return config_files
            
        except Exception as e:
            logger.error(f"설정 파일 목록 조회 실패: {e}")
            return []
    
    def delete_config(self, filepath: str) -> bool:
        """
        설정 파일 삭제
        
        Args:
            filepath: 설정 파일 경로
            
        Returns:
            삭제 성공 여부
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"설정 파일 삭제 완료: {filepath}")
                return True
            else:
                logger.warning(f"설정 파일이 없습니다: {filepath}")
                return False
                
        except Exception as e:
            logger.error(f"설정 파일 삭제 실패: {e}")
            return False


class HyperparameterOptimizer:
    """하이퍼파라미터 최적화 설정"""
    
    def __init__(self):
        self.search_spaces = {
            'lstm': {
                'units': [[64, 32], [128, 64, 32], [256, 128, 64]],
                'dropout_rate': [0.1, 0.2, 0.3],
                'learning_rate': [0.001, 0.0005, 0.0001],
                'batch_size': [16, 32, 64],
                'sequence_length': [30, 60, 120]
            },
            'transformer': {
                'embed_dim': [32, 64, 128],
                'num_heads': [2, 4, 8],
                'ff_dim': [64, 128, 256],
                'num_layers': [1, 2, 3],
                'dropout_rate': [0.1, 0.2, 0.3]
            },
            'pca': {
                'n_components': [5, 10, 15, 20],
                'variance_threshold': [0.90, 0.95, 0.99]
            },
            'factor_analysis': {
                'n_factors': [3, 5, 7, 10],
                'rotation': ['varimax', 'promax', 'oblimin']
            }
        }
    
    def get_search_space(self, model_type: str) -> Dict:
        """
        모델별 하이퍼파라미터 탐색 공간
        
        Args:
            model_type: 모델 타입
            
        Returns:
            탐색 공간 딕셔너리
        """
        return self.search_spaces.get(model_type, {})
    
    def generate_random_config(self, model_type: str) -> Dict:
        """
        랜덤 하이퍼파라미터 설정 생성
        
        Args:
            model_type: 모델 타입
            
        Returns:
            랜덤 설정 딕셔너리
        """
        import random
        
        search_space = self.get_search_space(model_type)
        config = {}
        
        for param, values in search_space.items():
            config[param] = random.choice(values)
        
        return config


# 전역 설정 관리자 인스턴스
config_manager = DeepLearningConfigManager()
hyperparameter_optimizer = HyperparameterOptimizer()


# 미리 정의된 설정들
PREDEFINED_CONFIGS = {
    'conservative': {
        'model_type': 'LSTM',
        'sequence_length': 120,
        'batch_size': 16,
        'epochs': 200,
        'learning_rate': 0.0001,
        'dropout_rate': 0.3,
        'n_components': 5,
        'n_factors': 3,
        'min_confidence': 0.5
    },
    'aggressive': {
        'model_type': 'Transformer',
        'sequence_length': 30,
        'batch_size': 64,
        'epochs': 50,
        'learning_rate': 0.001,
        'dropout_rate': 0.1,
        'n_components': 15,
        'n_factors': 7,
        'min_confidence': 0.2
    },
    'balanced': {
        'model_type': 'LSTM_GRU',
        'sequence_length': 60,
        'batch_size': 32,
        'epochs': 100,
        'learning_rate': 0.001,
        'dropout_rate': 0.2,
        'n_components': 10,
        'n_factors': 5,
        'min_confidence': 0.3
    }
}


def get_predefined_config(config_name: str) -> Dict:
    """
    미리 정의된 설정 가져오기
    
    Args:
        config_name: 설정 이름 ('conservative', 'aggressive', 'balanced')
        
    Returns:
        설정 딕셔너리
    """
    return PREDEFINED_CONFIGS.get(config_name, {})


if __name__ == "__main__":
    # 테스트 코드
    
    # 기본 설정 가져오기
    model_config = config_manager.get_default_config('model')
    print("기본 모델 설정:", model_config)
    
    # 실험 설정 생성
    experiment_config_path = config_manager.create_experiment_config(
        'samsung_lstm_test',
        model_type='LSTM',
        sequence_length=60,
        n_components=10
    )
    print(f"실험 설정 생성: {experiment_config_path}")
    
    # 설정 로드
    if experiment_config_path:
        loaded_config = config_manager.load_config(experiment_config_path)
        print("로드된 설정:", loaded_config)
    
    # 하이퍼파라미터 탐색 공간
    search_space_ = hyperparameter_optimizer.get_search_space('lstm')
    print("LSTM 하이퍼파라미터 탐색 공간:", search_space_)
    
    # 랜덤 설정 생성
    random_config = hyperparameter_optimizer.generate_random_config('lstm')
    print("랜덤 LSTM 설정:", random_config)
    
    # 미리 정의된 설정
    conservative_config = get_predefined_config('conservative')
    print("보수적 설정:", conservative_config)
