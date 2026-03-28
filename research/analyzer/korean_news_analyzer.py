
import re
import sqlite3
import requests
from bs4 import BeautifulSoup
from collections import Counter
from fake_useragent import UserAgent
from typing import List, Dict, Tuple
from utility.lazy_imports import get_np, get_pd


class KoreanNewsAnalyzer:
    """
    한국 시장 뉴스 분석기
    속도 우선으로 간단한 감정 사전과 키워드 추출 사용
    """

    POSITIVE_WORDS = {'상승', '급등', '호재', '증가', '개선', '성장', '이익', '매수', '강세', '폭등', '반등', '돌파', '신고가',
                      '매수세', '급증', '호황', '흑자', '배당', '합병', '인수', '최고가', '호실적', '상향', '추천', '강력매수'}
    NEGATIVE_WORDS = {'하락', '급락', '악재', '감소', '악화', '침체', '손실', '매도', '약세', '폭락', '하락', '추락', '신저가',
                      '매도세', '급감', '불황', '적자', '부채', '폐업', '상폐', '최저가', '하향', '강력매도'}

    def __init__(self):
        self.base_url = 'https://finance.naver.com/'
        self.headers  = {
            'User-Agent': UserAgent().chrome,
            'Referer': self.base_url
        }
        self.session  = requests.Session()

    def fetch_news(self, code: str) -> List[Dict[str, str]]:
        """
        네이버 뉴스 검색으로 뉴스 수집 (속도 최적화)
        """
        try:
            news_list = []
            url  = f"{self.base_url}/item/news_news.naver?code={code}&page=1&clusterId="
            resp = self.session.get(url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            data_list = soup.select('table.type5 > tbody > tr')
            for news in data_list:
                title_tag = news.select_one('a.tit')
                title = title_tag.get_text(strip=True)
                news_list.append({'title': title})
            return news_list
        except Exception as e:
            print(f"뉴스 수집 오류: {e}")
            return []

    def analyze_sentiment(self, text: str) -> float:
        """
        간단한 감정 분석: 긍정/부정 단어 수로 점수 계산 (-1 부정, 1 긍정)
        속도 우선으로 정규식 토큰화 사용
        """
        words = re.findall(r'\b\w+\b', text.lower())
        positive_count = sum(1 for word in words if word in self.POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in self.NEGATIVE_WORDS)
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        return (positive_count - negative_count) / total

    def extract_keywords(self, text: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        키워드 추출: 빈도 기반 (속도 우선으로 카운터 사용)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        filtered_words = [word for word in words if len(word) > 1 and not word.isdigit()]
        return Counter(filtered_words).most_common(top_n)

    def analyze_market_news(self, code: str) -> Dict[str, any]:
        """
        종목별 뉴스 분석 통합
        """
        news = self.fetch_news(code)
        if not news:
            return {'stock': code, 'sentiment_score': 0.0, 'keywords': [], 'news_count': 0}

        all_titles = ' '.join([n['title'] for n in news])
        sentiment = self.analyze_sentiment(all_titles)
        keywords = self.extract_keywords(all_titles, top_n=5)

        return {
            'stock': code,
            'sentiment_score': sentiment,
            'keywords': keywords,
            'news_count': len(news),
            'news_titles': [n['title'] for n in news]
        }


def example():
    analyzer = KoreanNewsAnalyzer()
    conn = sqlite3.connect(f'../../_database/stock_tick_back.db')
    df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
    df_cn = get_pd().read_sql(f"SELECT * FROM stockinfo", conn).set_index('index')
    conn.close()
    df_cn = df_cn['종목명'].to_dict()
    codes = df['name'].to_list()
    codes.remove('moneytop')
    codes.remove('stockinfo')
    codes = get_np().random.choice(codes, size=10)
    for code in codes:
        result = analyzer.analyze_market_news(code)
        print(f"종목: [{result['stock']}] {df_cn.get(code)}")
        print(f"감정 점수: {result['sentiment_score']:.2f}")
        print(f"키워드: {result['keywords']}")
        print(f"뉴스 수: {result['news_count']}")


if __name__ == "__main__":
    example()
