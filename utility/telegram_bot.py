
import time
import asyncio
import pandas as pd
from zoneinfo import ZoneInfo
from threading import Thread, Lock
from traceback import format_exc
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from utility.setting_base import ui_num


def get_telegram_runtime_queues(qlist):
    return qlist[0], qlist[3], qlist[9], qlist[10], qlist[13]


class TelegramBot:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ, cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9        10     11    12      13       14
        """
        self.windowQ, self.teleQ, self.ctraderQ, self.cstgQ, self.wdzservQ = get_telegram_runtime_queues(qlist)
        self.dict_set    = dict_set

        self.token       = None
        self.chat_id     = None
        self.application = None
        self.running     = False
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60

        self.message_queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.run()

    def run(self):
        Thread(target=self.moniter_queue, daemon=True).start()
        self.loop.create_task(self.process_messages())

        gubun = self.dict_set['증권사'][4:]
        self.token = self.dict_set[f'텔레그램봇토큰{gubun}']
        self.chat_id = self.dict_set[f'텔레그램사용자아이디{gubun}']

        if self.token and self.chat_id:
            self.running = True
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .post_init(self.setup_application)
                .build()
            )
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.loop.create_task(self.start_bot())
        
        self.loop.run_forever()

    def _is_transient_network_error(self, exc):
        text = f'{type(exc).__name__}: {exc}'.lower()
        markers = (
            'networkerror',
            'connecterror',
            'connecttimeout',
            'readtimeout',
            'timed out',
            'timedout',
            'getaddrinfo failed',
            'maxretryerror',
            'remote end closed connection',
            'winerror 10065',
        )
        return any(marker in text for marker in markers)

    def _emit_network_warning(self, context, exc):
        key = (context, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.windowQ.put((ui_num['시스템로그'], f'{context} 실패: {type(exc).__name__}'))

    def _handle_bot_exception(self, context, exc):
        if self._is_transient_network_error(exc):
            self._emit_network_warning(context, exc)
        else:
            detail = format_exc()
            if detail.startswith('NoneType: None'):
                detail = f'{type(exc).__name__}: {exc}\n'
            self.windowQ.put((ui_num['시스템로그'], f'{detail}오류 알림 - {context}'))

    async def start_bot(self):
        try:
            await self.application.initialize()
            await self.application.start()
            update_queue = await self.application.updater.start_polling()

            keyboard = [
                ['주식      체결목록', '주식      거래목록', '주식      잔고평가', '주식      잔고청산', '주식      전략중지'],
                ['해선      체결목록', '해선      거래목록', '해선      잔고평가', '해선      잔고청산', '해선      전략중지'],
                ['코인      체결목록', '코인      거래목록', '코인      잔고평가', '코인      잔고청산', '코인      전략중지'],
                ['주식          라이브', '해선          라이브', '코인          라이브', '백테          라이브']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard)
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text='안녕하세요. STOM 텔레그램봇입니다.\n아래 버튼을 눌러 원하는 기능을 실행하세요.',
                reply_markup=reply_markup
            )

            while True:
                update = await update_queue.get()
                await self.application.process_update(update)
                update_queue.task_done()
        except Exception as exc:
            self._handle_bot_exception('텔레그램 봇 시작', exc)
            self.running = False

    async def setup_application(self, application):
        korea_timezone = ZoneInfo('Asia/Seoul')
        application.bot_data['timezone'] = korea_timezone

    # noinspection PyUnusedLocal
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cmd = update.message.text
        if '라이브' in cmd:
            cmd = cmd.replace('          ', '')
        else:
            cmd = cmd.replace('      ', '')

        if cmd in ('주식전략중지', '해선전략중지'):
            self.wdzservQ.put(('strategy', '매수전략중지'))
        elif cmd == '코인전략중지':
            self.cstgQ.put('매수전략중지')
        elif '라이브' in cmd:
            self.windowQ.put(cmd)
        elif '주식' in cmd:
            cmd = cmd.replace('주식', '')
            self.wdzservQ.put(('trade', cmd))
        elif '해선' in cmd:
            cmd = cmd.replace('해선', '')
            self.wdzservQ.put(('trade', cmd))
        elif '코인' in cmd:
            cmd = cmd.replace('코인', '')
            self.ctraderQ.put(cmd)

    def moniter_queue(self):
        while True:
            data = self.teleQ.get()
            if self.running:
                self.loop.call_soon_threadsafe(self.message_queue.put_nowait, data)
            elif data.__class__ in (str, pd.DataFrame):
                self.windowQ.put((ui_num['시스템로그'], '텔레그램봇 토큰 및 아이디가 설정되지 않아 메세지를 보낼 수 없습니다'))
            elif data.__class__ == tuple:
                self.loop.call_soon_threadsafe(self.message_queue.put_nowait, data)

    async def process_messages(self):
        while True:
            data = await self.message_queue.get()
            if data.__class__ == str:
                if '.png' in data:
                    await self.send_photo(data)
                else:
                    await self.send_message(data)
            elif data.__class__ == pd.DataFrame:
                text = self.GetTextFromDataframe(data)
                await self.send_message(text)
            elif data.__class__ == tuple:
                self.dict_set = data[1]
                await self.restart_bot()
            self.message_queue.task_done()

    async def restart_bot(self):
        change = False
        gubun = self.dict_set['증권사'][4:]
        if self.token != self.dict_set[f'텔레그램봇토큰{gubun}'] or \
                self.chat_id != self.dict_set[f'텔레그램사용자아이디{gubun}']:
            change = True
            self.token = self.dict_set[f'텔레그램봇토큰{gubun}']
            self.chat_id = self.dict_set[f'텔레그램사용자아이디{gubun}']

        if change:
            try:
                self.running = False
                if self.application and self.application.running:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                    self.application = None

                if self.token and self.chat_id:
                    self.running = True
                    self.application = (
                        ApplicationBuilder()
                        .token(self.token)
                        .post_init(self.setup_application)
                        .build()
                    )
                    self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                    await self.start_bot()
            except Exception as exc:
                self._handle_bot_exception('텔레그램 봇 재시작', exc)
                self.running = False

    @staticmethod
    def GetTextFromDataframe(df: pd.DataFrame):
        text = ''
        if '매수금액' in df.columns:
            for index in df.index:
                ct    = df['체결시간'][index][8:10] + ':' + df['체결시간'][index][10:12]
                per   = df['수익률'][index]
                sg    = df['수익금'][index]
                name  = df['종목명'][index]
                text += f'{ct} {per:.2f}% {sg:,.0f}원(USD) {name}\n'
        elif '매수가' in df.columns:
            m_unit = '원' if df.columns[1] == '매수가' else 'USD'
            for index in df.index:
                per   = df['수익률'][index]
                sg    = df['평가손익'][index]
                name  = df['종목명'][index]
                if df.columns[1] == '매수가':
                    text += f'{per:.2f}% {sg:,.0f}{m_unit} {name}\n'
                else:
                    pos   = df['포지션'][index]
                    text += f'{pos} {per:.2f}% {sg:,.0f}{m_unit} {name}\n'
            tbg   = df['매입금액'].sum()
            tpg   = df['평가금액'].sum()
            tsg   = df['평가손익'].sum()
            tpp   = round(tsg / tbg * 100, 2)
            text += f'{tbg:,.0f}{m_unit} {tpg:,.0f}{m_unit} {tpp:.2f}% {tsg:,.0f}{m_unit}\n'
        elif '주문구분' in df.columns:
            for index in df.index:
                ct   = df['체결시간'][index][8:10] + ':' + df['체결시간'][index][10:12]
                bs   = df['주문구분'][index]
                bp   = df['체결가'][index]
                name = df['종목명'][index]
                text += f'{ct} {bs} {bp:,.2f} {name}\n'
        return text

    async def send_message(self, text):
        if not self.running:
            return
        await self.application.bot.send_message(
            chat_id=self.chat_id,
            text=text
        )

    async def send_photo(self, photo_path):
        if not self.running:
            return
        with open(photo_path, 'rb') as photo:
            await self.application.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo
            )
