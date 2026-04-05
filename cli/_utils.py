"""CLI 모듈 간 공유 유틸리티."""
import pandas as pd


def ensure_dataframe(data) -> pd.DataFrame:
    """data가 DataFrame이면 복사본을, 파일 경로면 CSV로 읽어 반환한다."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.read_csv(data)
