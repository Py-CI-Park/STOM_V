"""자동 조건식 탐색 설정 객체 (library-only)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiscoveryAnalysisConfig:
    """통계 분석 설정."""
    top_n: int = 5
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    buy_var: str = '매수'
    strategy_type: str = 'buy'


@dataclass
class DiscoveryMlConfig:
    """ML 분석 설정."""
    feature_limit: int = 0
    model_type: str = 'random_forest'
    top_n: int = 10
    n_splits: int = 5
    random_state: int = 42
    weight: float = 0.0


@dataclass
class DiscoveryPromotionConfig:
    """채택 평가 설정."""
    preset: str = 'balanced'
    criteria: dict | None = None
    auto_relax: bool = False
    max_relax_steps: int = 3


@dataclass
class DiscoveryOutputConfig:
    """결과 출력 경로 설정."""
    code_path: str | None = None
    report_json_path: str | None = None
    report_md_path: str | None = None


@dataclass
class DiscoveryConfig:
    """자동 조건식 탐색 전체 설정."""
    analysis: DiscoveryAnalysisConfig = field(default_factory=DiscoveryAnalysisConfig)
    ml: DiscoveryMlConfig = field(default_factory=DiscoveryMlConfig)
    promotion: DiscoveryPromotionConfig = field(default_factory=DiscoveryPromotionConfig)
    output: DiscoveryOutputConfig = field(default_factory=DiscoveryOutputConfig)
