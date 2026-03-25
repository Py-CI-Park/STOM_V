
import time
import requests
from bs4 import BeautifulSoup
from threading import Lock
from fake_useragent import UserAgent
from utility.lazy_imports import get_pd
from utility.setting_base import ui_num
from utility.static import str_ymdhm, error_decorator, set_builtin_print, str_ymd_ios, dt_ymdhms_ios, timedelta_day, \
    dt_ymd, str_hms, now, str_ymd, thread_decorator


class WebCrawingHomTab:
    def __init__(self, windowQ):
        self.windowQ   = windowQ
        self.dict_data = {}
        self.base_url  = 'https://finance.naver.com/'
        self.headers   = {
            'User-Agent': UserAgent().chrome,
            'Referer': self.base_url
        }
        self.session = requests.Session()
        self.thread_lock = Lock()
        self.complted_thread = 0

        set_builtin_print(True, self.windowQ)
        self.MainLoop()

    def MainLoop(self):
        while True:
            self.get_all_data()
            self.windowQ.put((ui_num['홈차트'], self.dict_data))
            time.sleep(30)

    @error_decorator
    def get_all_data(self):
        """모든 데이터 수집 (한국주식+암호화폐)"""
        self.complted_thread = 0
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
        self.get_korean_stocks(search_today, search_time, '코스피', 'KOSPI')
        self.get_korean_stocks(search_today, search_time, '코스닥', 'KOSDAQ')
        self.get_korean_stocks(search_today, search_time, '코스피100', 'KPI100')
        self.get_korean_stocks(search_today, search_time, '코스피200', 'KPI200')
        self.get_korean_stocks(search_today, search_time, '코스피200선물', 'FUT')
        self.get_market_indicator()
        self.get_crypto_data()
        while self.complted_thread < 16:
            time.sleep(0.1)

    @thread_decorator
    def get_korean_stocks(self, search_today, search_time, name, symbol):
        """한국주식 데이터 수집 (네이버)"""
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

            if existing_data is not None and last_time in page_times:
                duplicate_index = page_times.index(last_time)
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
            df = get_pd().DataFrame({
                'time': time_list[::-1],
                'price': price_list[::-1],
                'gap': gap_list[::-1],
                'change': pct_list[::-1]
            })
        else:
            df = None

        with self.thread_lock:
            if existing_data is not None:
                self.dict_data[name] = get_pd().concat([existing_data, df])
            else:
                self.dict_data[name] = df
            self.complted_thread += 1

    @thread_decorator
    def get_market_indicator(self):
        symbols = {
            '환율': f'{self.base_url}/marketindex/exchangeDailyQuote.naver?marketindexCd=FX_USDKRW&page=',
            '휘발유': f'{self.base_url}/marketindex/oilDailyQuote.naver?marketindexCd=OIL_GSL&page=',
            '국제금': f'{self.base_url}/marketindex/worldDailyQuote.naver?marketindexCd=CMDT_GC&fdtc=2&page='
        }

        for name, url_base in symbols.items():
            existing_data = self.dict_data.get(name)
            if existing_data is not None:
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
                df = get_pd().DataFrame({
                    'time': time_list[::-1],
                    'price': price_list[::-1],
                    'change': pct_list[::-1]
                })
            else:
                df = None

            with self.thread_lock:
                if existing_data is not None:
                    self.dict_data[name] = get_pd().concat([existing_data, df])
                else:
                    self.dict_data[name] = df
                self.complted_thread += 1

    @thread_decorator
    def get_crypto_data(self):
        """암호화폐 데이터 수집 (1분봉 전체)"""
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
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            time_list = [int(kline[0] / 1000) for kline in data]
            price_list = [float(kline[4]) for kline in data]
            change_list = [round((price / float(data[0][4]) - 1)  * 100, 2) for price in price_list]

            if time_list:
                df = get_pd().DataFrame({
                    'time': time_list,
                    'price': price_list,
                    'change': change_list
                })
            else:
                df = None

            with self.thread_lock:
                self.dict_data[name] = df
                self.complted_thread += 1

            time.sleep(0.1)
