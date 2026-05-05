
import time
import random
import requests
import matplotlib
import pandas as pd
from threading import Lock
from urllib import request
from threading import Timer
from bs4 import BeautifulSoup
from traceback import format_exc
from fake_useragent import UserAgent
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import ui_num
from utility.static_method.static import str_ymdhm, str_ymd_ios, dt_ymdhms_ios, timedelta_day, dt_ymd, str_hms, now, \
    str_ymd, thread_decorator, timedelta_sec


class WebCrawling(QThread):
    """웹 크롤링 클래스입니다.
    웹에서 데이터를 수집합니다.
    """
    signal = pyqtSignal(tuple)

    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ, testQ
           0        1       2      3       4      5      6      7       8        9       10     11    12
        """
        super().__init__()
        self.webcQ       = qlist[6]
        self.cmap        = matplotlib.colormaps['rainbow']
        self.norm1       = matplotlib.colors.Normalize(vmin=0, vmax=10)
        self.norm2       = matplotlib.colors.Normalize(vmin=0, vmax=35)
        self.base_url    = 'https://finance.naver.com/'
        self.headers     = {
            'User-Agent': UserAgent().chrome,
            'Referer': self.base_url
        }
        self.session     = requests.Session()
        self.treemap     = False
        self.imagelist1  = None
        self.imagelist2  = None
        self.dt_today    = None
        self.dict_data   = {}
        self.thread_lock = Lock()
        self.thread_join = 0

    def run(self):
        """웹 크롤링을 실행합니다.
        """
        self._crawling_homtap_data()
        hometap_crawling_time = timedelta_sec(30)
        while True:
            if not self.webcQ.empty():
                data = self.webcQ.get()
                self._crawling(data)

            if now() > hometap_crawling_time:
                self._crawling_homtap_data()
                hometap_crawling_time = timedelta_sec(30)

            if self.thread_join == 16:
                self.thread_join = 0
                self.signal.emit((ui_num['홈차트'], self.dict_data))

            time.sleep(0.01)

    def _crawling(self, data):
        """크롤링을 수행합니다.
        Args:
            data: 크롤링 데이터
        """
        cmd, data = data
        if cmd == '기업정보':
            self._gugy_crawling(data)
            self._gugs_crawling(data)
            self._jmns_crawling(data)
            self._jmjp_crawling(data)
        elif cmd == '트리맵':
            self.treemap = True
            self._ujtm_crawling()
        elif cmd == '트리맵1':
            self._ujtm_crawling_detail(data, 1)
        elif cmd == '트리맵2':
            self._ujtm_crawling_detail(data, 2)
        elif cmd == '트리맵중단':
            self.treemap = False
        elif cmd == '풍경사진요청':
            self._get_image()

    @thread_decorator
    def _get_image(self):
        """이미지를 가져옵니다.
        """
        try:
            if self.imagelist1 is None:
                url   = 'https://search.naver.com/search.naver?sm=tab_hty.top&where=image&ssc=tab.image.all&query=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&oquery=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&tqi=iAM7jwqVN8VsslwnmiossssstI4-416434'
                resp  = self.session.get(url, headers=self.headers)
                datas = resp.text.split('"viewerThumb":"')[1:]
                datas = [x.split('lensThumb')[0] for x in datas]
                datas = [x.split('.jpg')[0] + '.jpg' for x in datas]
                self.imagelist1 = [x for x in datas if '\\' not in x]
            if self.imagelist2 is None:
                url   = 'https://search.naver.com/search.naver?sm=tab_hty.top&where=image&ssc=tab.image.all&query=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EC%84%B8%EB%A1%9C%EC%82%AC%EC%A7%84&oquery=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&tqi=iAM7OdqVOsVssAwVjfossssstwd-182384'
                resp  = self.session.get(url, headers=self.headers)
                datas = resp.text.split('"viewerThumb":"')[1:]
                datas = [x.split('lensThumb')[0] for x in datas]
                datas = [x.split('.jpg')[0] + '.jpg' for x in datas]
                self.imagelist2 = [x for x in datas if '\\' not in x]
            if self.imagelist1 and self.imagelist2:
                webimage1 = request.urlopen(random.choice(self.imagelist1)).read()
                webimage2 = request.urlopen(random.choice(self.imagelist2)).read()
                self.signal.emit((ui_num['풍경사진'], webimage1, webimage2))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def _gugy_crawling(self, code):
        """기업 개요를 크롤링합니다.
        Args:
            code: 종목 코드
        """
        try:
            url  = f'{self.base_url}/item/coinfo.naver?code={code}'
            resp = self.session.get(url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            gugy_result = ''
            titles = soup.select('.summary_info > p')
            for title in titles:
                title = title.get_text(strip=True).replace('.', '. ')
                if title:
                    gugy_result += title
            self.signal.emit((ui_num['기업개요'], gugy_result))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def _gugs_crawling(self, code):
        """기업 공시를 크롤링합니다.
        Args:
            code: 종목 코드
        """
        try:
            date_list, jbjg_list, gygs_list, link_list = [], [], [], []
            for i in (1, 2):
                url  = f'{self.base_url}/item//news_notice.naver?code={code}&page={i}'
                resp = self.session.get(url, headers=self.headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                tits = soup.select('a.tit')
                if not tits:
                    break
                for title in tits:
                    text = title.get_text(strip=True)
                    if not text:
                        continue
                    gygs_list.append(text)
                    link_list.append(self.base_url + title['href'])
                date_list += [date.get_text(strip=True) for date in soup.select('td.date')]
                jbjg_list += [info.get_text(strip=True) for info in soup.select('td.info')]
            df = pd.DataFrame({'일자': date_list, '정보제공': jbjg_list, '공시': gygs_list, '링크': link_list})
            self.signal.emit((ui_num['기업공시'], df))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    # noinspection PyUnresolvedReferences
    @thread_decorator
    def _jmns_crawling(self, code):
        """종목 뉴스를 크롤링합니다.
        Args:
            code: 종목 코드
        """
        try:
            data_list = []
            for i in (1, 2):
                url   = f'{self.base_url}/item/news_news.naver?code={code}&page={i}&clusterId='
                resp  = self.session.get(url, headers=self.headers)
                soup  = BeautifulSoup(resp.text, 'html.parser')
                news_list = soup.select('table.type5 > tbody > tr')
                if not news_list:
                    break
                for news in news_list:
                    title_tag = news.select_one('a.tit')
                    if not title_tag:
                        continue
                    date = news.select_one('td.date').get_text(strip=True)
                    press = news.select_one('td.info').get_text(strip=True)
                    title = title_tag.get_text(strip=True)
                    hlink = self.base_url + title_tag['href']
                    data_list.append({
                        '일자 및 시간': date,
                        '언론사': press,
                        '제목': title,
                        '링크': hlink
                    })
            df = pd.DataFrame(data_list)
            self.signal.emit((ui_num['기업뉴스'], df))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def _jmjp_crawling(self, code):
        """기업 재무정보를 크롤링합니다.
        Args:
            code: 종목 코드
        """
        try:
            url      = f'{self.base_url}/item/main.naver?code={code}'
            resp     = self.session.get(url, headers=self.headers)
            soup     = BeautifulSoup(resp.text, 'html.parser').select('div.section.cop_analysis > div.sub_section')[0]
            txt_list = [item.get_text(strip=True) for item in soup.select('th')]
            num_list = [item.get_text(strip=True) for item in soup.select('td')][:130]
            columns1 = ['구분'] + txt_list[3:7]
            columns2 = txt_list[7:13]
            data1 = [
                txt_list[-16:-3],
                num_list[::10],
                num_list[1::10],
                num_list[2::10],
                num_list[3::10]
            ]
            data2 = [
                num_list[4::10],
                num_list[5::10],
                num_list[6::10],
                num_list[7::10],
                num_list[8::10],
                num_list[9::10]
            ]
            df1 = pd.DataFrame(dict(zip(columns1, data1)))
            df2 = pd.DataFrame(dict(zip(columns2, data2)))
            self.signal.emit((ui_num['재무년도'], df1))
            self.signal.emit((ui_num['재무분기'], df2))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def _ujtm_crawling(self):
        """업종/테마 트리맵을 크롤링합니다.
        """
        try:
            url        = f'{self.base_url}/sise/sise_group.naver?type=upjong'
            resp       = self.session.get(url, headers=self.headers)
            soup       = BeautifulSoup(resp.text, 'html.parser')
            url_list1  = [self.base_url + item['href'] for item in soup.select('td > a')]
            name_list1 = [item.get_text(strip=True) for item in soup.select('td > a')]
            per_list1  = [float(item.get_text(strip=True).replace('%', '')) for item in soup.select('.number > span')]

            url        = f'{self.base_url}/sise/theme.naver?&page=1'
            resp       = self.session.get(url, headers=self.headers)
            soup       = BeautifulSoup(resp.text, 'html.parser')
            url_list2  = [self.base_url + item['href'] for item in soup.select('.col_type1 > a')[1:]]
            name_list2 = [item.get_text(strip=True) for item in soup.select('.col_type1 > a')[1:]]
            per_list2  = [float(item.get_text(strip=True).replace('%', '')) for item in soup.select('.col_type2 > span')]

            df1 = pd.DataFrame({
                '업종명': name_list1[:len(per_list1)],
                '등락율': per_list1,
                'url': url_list1[:len(per_list1)]
            })
            df1 = df1[df1['등락율'] > 0]
            if len(df1) > 30: df1 = df1[:30]
            df1['등락율%'] = df1['등락율'].apply(lambda x: str(x) + '%')
            cl1 = [self.cmap(self.norm1(value)) for value in df1['등락율']]

            df2 = pd.DataFrame({
                '테마명': name_list2[:len(per_list2)],
                '등락율': per_list2,
                'url': url_list2[:len(per_list2)]
            })
            df2 = df2[df2['등락율'] > 0]
            if len(df2) > 30: df2 = df2[:30]
            df2['등락율%'] = df2['등락율'].apply(lambda x: str(x) + '%')
            cl2 = [self.cmap(self.norm1(value)) for value in df2['등락율']]

            self.signal.emit((ui_num['트리맵'], df1, df2, cl1, cl2))
            if self.treemap:
                Timer(10, self._ujtm_crawling).start()
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def _ujtm_crawling_detail(self, url, gubun):
        """업종/테마 상세정보를 크롤링합니다.
        Args:
            url: URL
            gubun: 구분
        """
        try:
            resp      = self.session.get(url, headers=self.headers)
            soup      = BeautifulSoup(resp.text, 'html.parser')
            name_list = [item.get_text(strip=True) for item in soup.select('.name_area')]
            per_list  = [float(item.get_text(strip=True).replace('%', '')) for i, item in enumerate(soup.select('.number > span')[1:]) if i % 2 != 0]

            df = pd.DataFrame({'종목명': name_list[:len(per_list)], '등락율': per_list})
            df = df[df['등락율'] > 0][:20]
            df['등락율%'] = df['등락율'].apply(lambda x: f'{x}%')
            cl = [self.cmap(self.norm2(value)) for value in df['등락율']]

            if gubun == 1:
                self.signal.emit((ui_num['트리맵1'], df, '', cl, ''))
            else:
                self.signal.emit((ui_num['트리맵2'], '', df, '', cl))
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    def _crawling_homtap_data(self):
        """모든 데이터를 수집합니다 (한국주식+암호화폐).
        """
        search_time = now()
        weekday = search_time.weekday()
        before_open = int(str_hms(search_time)) < 90000
        market_open = True
        if weekday == 5:
            search_time = timedelta_day(-1, search_time)
            market_open = False
        elif weekday == 6:
            search_time = timedelta_day(-2, search_time)
            market_open = False
        elif weekday == 0 and before_open:
            search_time = timedelta_day(-3, search_time)
            market_open = False
        elif before_open:
            search_time = timedelta_day(-1, search_time)
            market_open = False

        search_today = str_ymd_ios(search_time)
        if market_open:
            search_time = str_ymdhm(search_time) + '00'
        else:
            search_time = str_ymd(search_time) + '185900'

        if self.dt_today != search_today:
            for name in ('코스피', '코스닥', '코스피100', '코스피200', '코스피200선물'):
                if name in self.dict_data:
                    del self.dict_data[name]
            self.dt_today = search_today

        self.get_korean_stocks(search_today, search_time, '코스피', 'KOSPI')
        self.get_korean_stocks(search_today, search_time, '코스닥', 'KOSDAQ')
        self.get_korean_stocks(search_today, search_time, '코스피100', 'KPI100')
        self.get_korean_stocks(search_today, search_time, '코스피200', 'KPI200')
        self.get_korean_stocks(search_today, search_time, '코스피200선물', 'FUT')
        self.get_market_indicator()
        self.get_crypto_data()

    # noinspection PyUnresolvedReferences
    @thread_decorator
    def get_korean_stocks(self, search_today, search_time, name, symbol):
        """한국주식 데이터를 수집합니다 (네이버).
        Args:
            search_today: 검색 일자
            search_time: 검색 시간
            name: 이름
            symbol: 심볼
        """
        try:
            existing_data = self.dict_data.get(name)
            if existing_data is not None:
                last_time = existing_data['time'].iloc[-1]
            else:
                last_time = None

            i = 1
            time_list  = []
            price_list = []
            gap_list   = []
            pct_list   = []
            last_times = None

            while True:
                url  = f'{self.base_url}/sise/sise_index_time.naver?code={symbol}&thistime={search_time}&page={i}'
                resp = self.session.get(url, headers=self.headers)
                soup = BeautifulSoup(resp.text, 'html.parser')

                page_times = [t.get_text(strip=True) for t in soup.select('td.date')]
                if last_times != page_times:
                    last_times = page_times
                else:
                    break

                page_prices = [p.get_text(strip=True) for p in soup.select('td.number_1')[::4]]
                page_gaps   = [p.get_text(strip=True) for p in soup.select('span.tah')]
                page_buhos  = [t['alt'] for t in soup.select('td > img')]
                page_buhos  = [-1 if b == '하락' else 1 for b in page_buhos]

                if '0' in page_gaps:
                    k = 0
                    new_buhos = []
                    for g in page_gaps:
                        if g != '0':
                            new_buhos.append(page_buhos[k])
                            k += 1
                        else:
                            new_buhos.append(1)
                    page_buhos = new_buhos

                page_times  = [dt_ymdhms_ios(f"{search_today} {t}:00").timestamp() for t in page_times if t != '']
                page_prices = [float(p.replace(',', '')) for p in page_prices if p != '']
                page_gaps   = [float(g.replace(',', '')) for g in page_gaps if g != '']
                page_gaps   = [g * b for g, b in zip(page_gaps, page_buhos)]
                page_pcts   = [round((p / (p - g) - 1) * 100, 2) for p, g in zip(page_prices, page_gaps)]

                if page_times and page_prices and page_gaps and page_pcts:
                    if existing_data is not None and last_time in page_times:
                        duplicate_index = page_times.index(last_time)
                        if duplicate_index > 0:
                            time_list.extend(page_times[:duplicate_index])
                            price_list.extend(page_prices[:duplicate_index])
                            gap_list.extend(page_gaps[:duplicate_index])
                            pct_list.extend(page_pcts[:duplicate_index])
                        break
                    else:
                        time_list.extend(page_times)
                        price_list.extend(page_prices)
                        gap_list.extend(page_gaps)
                        pct_list.extend(page_pcts)

                time.sleep(0.1)
                i += 1

            if time_list:
                df = pd.DataFrame({
                    'time': time_list[::-1],
                    'price': price_list[::-1],
                    'gap': gap_list[::-1],
                    'change': pct_list[::-1]
                })
            else:
                df = None

            with self.thread_lock:
                if existing_data is not None:
                    if df is not None:
                        self.dict_data[name] = pd.concat([existing_data, df])
                else:
                    self.dict_data[name] = df
                self.thread_join += 1
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def get_market_indicator(self):
        """시장 지표를 가져옵니다.
        """
        try:
            symbols = {
                '환율': f'{self.base_url}/marketindex/exchangeDailyQuote.naver?marketindexCd=FX_USDKRW&page=',
                '휘발유': f'{self.base_url}/marketindex/oilDailyQuote.naver?marketindexCd=OIL_GSL&page=',
                '국제금': f'{self.base_url}/marketindex/worldDailyQuote.naver?marketindexCd=CMDT_GC&fdtc=2&page='
            }

            for name, url_base in symbols.items():
                existing_data = self.dict_data.get(name)
                if existing_data is not None:
                    # noinspection PyUnresolvedReferences
                    last_time = existing_data['time'].iloc[-1]
                else:
                    last_time = None

                i = 1
                time_list  = []
                price_list = []
                pct_list   = []
                list_gap   = 3 if name in ('휘발유', '국제금') else 2

                while True:
                    url  = f'{url_base}{i}'
                    resp = self.session.get(url, headers=self.headers)
                    soup = BeautifulSoup(resp.text, 'html.parser')

                    page_times  = [t.get_text(strip=True) for t in soup.select('td.date')]
                    page_prices = [t.get_text(strip=True) for t in soup.select('td.num')][::list_gap]
                    page_gaps   = [t.get_text(strip=True) for t in soup.select('td.num')][1::list_gap]
                    page_buhos  = [t['alt'] for t in soup.select('td > img')]
                    page_buhos  = [-1 if b == '하락' else 1 for b in page_buhos]
                    page_times  = [dt_ymd(t.replace('.', '')).timestamp() for t in page_times if t != '']
                    page_prices = [float(p.replace(',', '')) for p in page_prices if p != '']
                    page_gaps   = [float(g.replace(',', '')) for g in page_gaps if g != '']
                    page_gaps   = [g * b for g, b in zip(page_gaps, page_buhos)]
                    page_pcts   = [round((p / (p - g) - 1) * 100, 2) for p, g in zip(page_prices, page_gaps)]

                    if existing_data is not None and last_time in page_times:
                        duplicate_index = page_times.index(last_time)
                        if duplicate_index > 0:
                            time_list.extend(page_times[:duplicate_index])
                            price_list.extend(page_prices[:duplicate_index])
                            pct_list.extend(page_pcts[:duplicate_index])
                        break
                    else:
                        time_list.extend(page_times)
                        price_list.extend(page_prices)
                        pct_list.extend(page_pcts)

                    if len(time_list) > 100:
                        break

                    time.sleep(0.1)
                    i += 1

                if time_list:
                    df = pd.DataFrame({
                        'time': time_list[::-1],
                        'price': price_list[::-1],
                        'change': pct_list[::-1]
                    })
                else:
                    df = None

                with self.thread_lock:
                    if existing_data is not None:
                        if df is not None:
                            self.dict_data[name] = pd.concat([existing_data, df])
                    else:
                        self.dict_data[name] = df
                    self.thread_join += 1
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))

    @thread_decorator
    def get_crypto_data(self):
        """암호화폐 데이터를 수집합니다 (1분봉 전체).
        """
        try:
            symbols = {
                'BTC/USDT': 'BTCUSDT',
                'ETH/USDT': 'ETHUSDT',
                'BNB/USDT': 'BNBUSDT',
                'XRP/USDT': 'XRPUSDT',
                'SOL/USDT': 'SOLUSDT',
                'DOGE/USDT': 'DOGEUSDT',
                'ADA/USDT': 'ADAUSDT',
                'LINK/USDT': 'LINKUSDT'
            }

            for name, symbol in symbols.items():
                url  = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=1000"
                try:
                    resp = requests.get(url, headers=self.headers, timeout=10)
                    data = resp.json()
                except Exception:
                    time_list = []
                    price_list = []
                    change_list = []
                else:
                    time_list = [int(kline[0] / 1000) for kline in data]
                    price_list = [float(kline[4]) for kline in data]
                    change_list = [round((price / float(data[0][4]) - 1)  * 100, 2) for price in price_list]

                if time_list:
                    df = pd.DataFrame({
                        'time': time_list,
                        'price': price_list,
                        'change': change_list
                    })
                else:
                    df = None

                with self.thread_lock:
                    self.dict_data[name] = df
                    self.thread_join += 1

                time.sleep(0.1)
        except Exception:
            self.signal.emit((ui_num['시스템로그'], format_exc()))
