
import random
import requests
import matplotlib
import pandas as pd
from urllib import request
from threading import Timer
from bs4 import BeautifulSoup
from traceback import format_exc
from fake_useragent import UserAgent
from utility.setting_base import ui_num
from utility.static import thread_decorator


class WebCrawling:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ    = qlist[0]
        self.webcQ      = qlist[6]
        self.cmap       = matplotlib.colormaps['rainbow']
        self.norm       = matplotlib.colors.Normalize(vmin=0, vmax=29)

        self.base_url   = 'https://finance.naver.com/'
        self.headers    = {
            'User-Agent': UserAgent().chrome,
            'Referer': self.base_url
        }
        self.session    = requests.Session()

        self.treemap    = False
        self.imagelist1 = None
        self.imagelist2 = None

        self.MainLoop()

    def MainLoop(self):
        while True:
            data = self.webcQ.get()
            try:
                self.Crawling(data)
            except:
                self.windowQ.put((ui_num['시스템로그'], format_exc()))

    def Crawling(self, data):
        cmd, data = data
        if cmd == '기업정보':
            self.GugyCrawling(data)
            self.GugsCrawling(data)
            self.JmnsCrawling(data)
            self.JmjpCrawling(data)
        elif cmd == '트리맵':
            self.treemap = True
            self.UjTmCrawling()
        elif cmd == '트리맵1':
            self.UjTmCrawlingDetail(data, 1)
        elif cmd == '트리맵2':
            self.UjTmCrawlingDetail(data, 2)
        elif cmd == '트리맵중단':
            self.treemap = False
        elif cmd == '풍경사진요청':
            self.GetImage()

    @thread_decorator
    def GetImage(self):
        try:
            if self.imagelist1 is None:
                url   = 'https://search.naver.com/search.naver?sm=tab_hty.top&where=image&ssc=tab.image.all&query=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&oquery=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&tqi=iAM7jwqVN8VsslwnmiossssstI4-416434'
                resp  = self.session.get(url, headers=self.headers)
                datas = resp.text.split('"viewerThumb":"')[1:]
                datas = [x.split('lensThumb')[0] for x in datas]
                datas = [x.split('.jpg')[0] + '.jpg' for x in datas]
                self.imagelist1 = [x for x in datas if '\\' not in x]
            if self.imagelist2 is None:
                url  = 'https://search.naver.com/search.naver?sm=tab_hty.top&where=image&ssc=tab.image.all&query=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EC%84%B8%EB%A1%9C%EC%82%AC%EC%A7%84&oquery=%EA%B3%A0%ED%99%94%EC%A7%88%ED%92%8D%EA%B2%BD%EA%B0%80%EB%A1%9C%EC%82%AC%EC%A7%84&tqi=iAM7OdqVOsVssAwVjfossssstwd-182384'
                resp  = self.session.get(url, headers=self.headers)
                datas = resp.text.split('"viewerThumb":"')[1:]
                datas = [x.split('lensThumb')[0] for x in datas]
                datas = [x.split('.jpg')[0] + '.jpg' for x in datas]
                self.imagelist2 = [x for x in datas if '\\' not in x]
            webimage1 = request.urlopen(random.choice(self.imagelist1)).read()
            webimage2 = request.urlopen(random.choice(self.imagelist2)).read()
            self.windowQ.put((ui_num['풍경사진'], webimage1, webimage2))
        except:
            pass

    @thread_decorator
    def GugyCrawling(self, code):
        url  = f'{self.base_url}/item/coinfo.naver?code={code}'
        resp = self.session.get(url, headers=self.headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        gugy_result = ''
        titles = soup.select('.summary_info > p')
        for title in titles:
            title = title.get_text(strip=True).replace('.', '. ')
            if title:
                gugy_result += title
        self.windowQ.put((ui_num['기업개요'], gugy_result))

    @thread_decorator
    def GugsCrawling(self, code):
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
        self.windowQ.put((ui_num['기업공시'], df))

    @thread_decorator
    def JmnsCrawling(self, code):
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
        self.windowQ.put((ui_num['기업뉴스'], df))

    @thread_decorator
    def JmjpCrawling(self, code):
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
        self.windowQ.put((ui_num['재무년도'], df1))
        self.windowQ.put((ui_num['재무분기'], df2))

    @thread_decorator
    def UjTmCrawling(self):
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
        cl1 = [self.cmap(self.norm(value)) for value in df1['등락율']]

        df2 = pd.DataFrame({
            '테마명': name_list2[:len(per_list2)],
            '등락율': per_list2,
            'url': url_list2[:len(per_list2)]
        })
        df2 = df2[df2['등락율'] > 0]
        if len(df2) > 30: df2 = df2[:30]
        df2['등락율%'] = df2['등락율'].apply(lambda x: str(x) + '%')
        cl2 = [self.cmap(self.norm(value)) for value in df2['등락율']]

        self.windowQ.put((ui_num['트리맵'], df1, df2, cl1, cl2))
        if self.treemap:
            Timer(10, self.UjTmCrawling).start()

    @thread_decorator
    def UjTmCrawlingDetail(self, url, gubun):
        resp      = self.session.get(url, headers=self.headers)
        soup      = BeautifulSoup(resp.text, 'html.parser')
        name_list = [item.get_text(strip=True) for item in soup.select('.name_area')]
        per_list  = [float(item.get_text(strip=True).replace('%', '')) for i, item in enumerate(soup.select('.number > span')[1:]) if i % 2 != 0]

        df = pd.DataFrame({'종목명': name_list[:len(per_list)], '등락율': per_list})
        df = df[df['등락율'] > 0][:20]
        df['등락율%'] = df['등락율'].apply(lambda x: f'{x}%')
        cl = [self.cmap(self.norm(value)) for value in df['등락율']]

        if gubun == 1:
            self.windowQ.put((ui_num['트리맵1'], df, '', cl, ''))
        else:
            self.windowQ.put((ui_num['트리맵2'], '', df, '', cl))
