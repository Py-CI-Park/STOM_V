
import os
import json
from datetime import datetime


class StrategyVersionManager:
    """
    전략 버전 관리 클래스
    - 매수/매도 전략 별도 관리
    - 저장 버튼 클릭 시 자동 버전 생성
    - 라인별 diff 색상 표시 지원
    """

    def __init__(self, market: str, gubun1: str, gubun2: str, strategy_name: str):
        """
        Args:
            market: 거래소 구분
            gubun1: 전략 구분 ('basic', 'opti', 'cond')
            gubun2: 매수, 매도, 최적화범위, GA범위 구분 ('buy', 'sell', 'vars', 'gavars')
            strategy_name: 전략 이름
        """

        self.market = market
        self.gubun1 = gubun1
        self.gubun2 = gubun2
        self.name   = strategy_name
        self.base_path = './_database/strategy_versions'
        os.makedirs(self.base_path, exist_ok=True)
        self.file_name = f'{market}_{gubun1}_{gubun2}_{strategy_name}'

    def _increment_version(self, current: str) -> str:
        """
        버전 증가: 1.00 -> 1.01, 1.09 -> 1.10, 1.99 -> 2.00
        """
        major, minor = map(int, current.split('.'))
        if minor >= 99:
            return f"{major + 1}.00"
        return f"{major}.{minor + 1:02d}"

    def _load_index(self) -> dict:
        """인덱스 파일 로드"""
        index_file = f'{self.base_path}/{self.file_name}_index.json'
        if os.path.isfile(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'versions': [], 'latest': '0.99'}

    def _save_index(self, index: dict):
        """인덱스 파일 저장"""
        index_file = f'{self.base_path}/{self.file_name}_index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def save_version(self, text: str):
        """버전 저장"""
        index = self._load_index()
        current = index.get('latest', '0.99')

        pre_text = self.load_version(current)
        if pre_text == text:
            return

        new_ver = self._increment_version(current)

        data = {
            'version': new_ver,
            'timestamp': datetime.now().isoformat(),
            'text': text
        }

        file_path = f'{self.base_path}/{self.file_name}_{new_ver}.json'

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        index['versions'].append(new_ver)
        index['latest'] = new_ver
        self._save_index(index)

    def load_version(self, version: str) -> str:
        """특정 버전 불러오기"""
        version = version.split(' ')
        version = version[0] if len(version) < 2 else version[1]
        file_path = f'{self.base_path}/{self.file_name}_{version}.json'
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('text', '')
        return ''

    def get_versions(self) -> list[str]:
        """버전 목록 조회"""
        index = self._load_index()
        versions = []

        for version in index.get('versions', []):
            file_path = f'{self.base_path}/{self.file_name}_{version}.json'
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                versions.append(f"{self.name} {data.get('version')} {data.get('timestamp')}")

        versions.sort(key=lambda x: x.split(' ')[1], reverse=True)
        return versions

    def delete_version(self, version: str) -> bool:
        """특정 버전 삭제"""
        deleted = False
        version = version.split(' ')[1]
        file_path = f'{self.base_path}/{self.file_name}_{version}.json'
        if os.path.isfile(file_path):
            os.remove(file_path)
            deleted = True

        if deleted:
            index = self._load_index()
            if version in index['versions']:
                index['versions'].remove(version)
                if index['latest'] == version and index['versions']:
                    index['latest'] = index['versions'][-1]
                self._save_index(index)

        return deleted


def stg_save_version(market, gubun1, gubun2, strategy_name, strategy):
    svm = StrategyVersionManager(market, gubun1, gubun2, strategy_name)
    svm.save_version(strategy)
