import os
import re
import sys
import time
import pytz
import _pickle
import datetime
import logging
from threading import Thread, Timer
from traceback import print_exc
from utility.safe_exec import safe_compile

try:
    import psutil
except ImportError:
    psutil = None

try:
    import winreg as reg
except ImportError:
    reg = None

try:
    from loguru import logger as _loguru_logger
except ImportError:
    _loguru_logger = None

try:
    import exchange_calendars as ec
except ImportError:
    ec = None

try:
    from PyQt5.QtTest import QTest
except ImportError:
    QTest = None

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None


now_utc_ = datetime.datetime.now(pytz.utc)
now_cme_ = now_utc_.astimezone(pytz.timezone('America/Chicago'))
summer_t = int(now_cme_.dst().total_seconds())
time_gap = int(summer_t - 50400)


def get_logger(name):
    if _loguru_logger is not None:
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <5}</level> | "
                   f"<cyan>{name}</cyan> : "
                   "<level>{message}</level>",
            level="DEBUG",
            colorize=True
        )
        return _loguru_logger

    fallback_logger = logging.getLogger(name)
    if not fallback_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-5s | " + f"{name} : " + "%(message)s"
        ))
        fallback_logger.addHandler(handler)
    fallback_logger.setLevel(logging.DEBUG)
    return fallback_logger


def now():
    return datetime.datetime.now()


def now_utc():
    return timedelta_sec(-32400)


def now_cme():
    return timedelta_sec(time_gap)


def str_ymdhmsf(std_time=None):
    if std_time is not None:
        return strf_time('%Y%m%d%H%M%S%f', std_time)
    else:
        return strf_time('%Y%m%d%H%M%S%f')


def str_ymdhms(std_time=None):
    if std_time is not None:
        return strf_time('%Y%m%d%H%M%S', std_time)
    else:
        return strf_time('%Y%m%d%H%M%S')


def str_ymdhms_ios(std_time=None):
    if std_time is not None:
        return strf_time('%Y-%m-%d %H:%M:%S', std_time)
    else:
        return strf_time('%Y-%m-%d %H:%M:%S')


def str_ymdhms_utc(time_):
    return str_ymdhms(from_timestamp(int(time_ / 1000 - 32400)))


def str_ymd(std_time=None):
    if std_time is not None:
        return strf_time('%Y%m%d', std_time)
    else:
        return strf_time('%Y%m%d')


def str_hmsf(std_time=None):
    if std_time is not None:
        return strf_time('%H%M%S%f', std_time)
    else:
        return strf_time('%H%M%S%f')


def float_hmsf(std_time=None):
    if std_time is not None:
        return float(strf_time('%H%M%S.%f', std_time))
    else:
        return float(strf_time('%H%M%S.%f'))


def str_hms(std_time=None):
    if std_time is not None:
        return strf_time('%H%M%S', std_time)
    else:
        return strf_time('%H%M%S')


def int_hms(std_time=None):
    if std_time is not None:
        return int(strf_time('%H%M%S', std_time))
    else:
        return int(strf_time('%H%M%S'))


def str_hms_cme_from_str(std_hms=None):
    if std_hms is not None:
        std_time = timedelta_sec(time_gap, dt_hms(std_hms))
    else:
        std_time = now_cme()
    return str_hms(std_time)


def str_hm(std_time):
    return strf_time('%H%M', std_time)


def dt_ymdhms_ios(str_time):
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhms(str_time):
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}:{str_time[12:14]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhm(str_time):
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymd(str_time):
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hms(str_time):
    if len(str_time) == 5: str_time = str_time.zfill(6)
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}:{str_time[4:6]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hm(str_time):
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}'
    return datetime.datetime.fromisoformat(str_time)


def strf_time(timetype, std_time=None):
    return now().strftime(timetype) if std_time is None else std_time.strftime(timetype)


def from_timestamp(time_):
    return datetime.datetime.fromtimestamp(time_)


def timedelta_sec(second, std_time=None):
    return now() + datetime.timedelta(seconds=float(second)) if std_time is None else std_time + datetime.timedelta(seconds=float(second))


def timedelta_day(day, std_time=None):
    return now() + datetime.timedelta(days=float(day)) if std_time is None else std_time + datetime.timedelta(days=float(day))


def thread_decorator(func):
    def wrapper(*args):
        Thread(target=func, args=args, daemon=True).start()
    return wrapper


def error_decorator(func):
    def wrapper(*args):
        try:
            func(*args)
        except:
            print_exc()
    return wrapper


def threading_timer(sec, func, args=None):
    if args is None:
        Timer(float(sec), func).start()
    else:
        Timer(float(sec), func, args=[args]).start()


def win_proc_alive(name):
    if psutil is None:
        return False
    alive = False
    for proc in psutil.process_iter():
        if name in proc.name():
            alive = True
    return alive


def opstarter_kill():
    import subprocess
    if win_proc_alive('opstarter'):
        subprocess.run(['C:/Windows/System32/taskkill', '/f', '/im', 'opstarter.exe'],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    if win_proc_alive('nfstarter'):
        subprocess.run(['C:/Windows/System32/taskkill', '/f', '/im', 'nfstarter.exe'],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def pickle_write(file, data):
    with open(f'{file}.pkl', "wb") as f:
        # noinspection PyTypeChecker
        _pickle.dump(data, f, protocol=-1)


def pickle_read(file, allowed_root=None):
    data = None
    try:
        file = os.fspath(file)
    except TypeError:
        return None

    if not file or '\x00' in file:
        return None

    pkl_path = file if file.endswith('.pkl') else f'{file}.pkl'
    real_pkl_path = os.path.realpath(pkl_path)

    if allowed_root is not None:
        try:
            root = os.path.realpath(os.fspath(allowed_root))
        except TypeError:
            return None
        try:
            if os.path.commonpath([real_pkl_path, root]) != root:
                return None
        except ValueError:
            return None

    try:
        if os.path.isfile(real_pkl_path) and not os.path.islink(real_pkl_path):
            with open(real_pkl_path, "rb") as f:
                data = _pickle.load(f)
    except Exception:
        return None
    return data


def qtest_qwait(sec):
    if QTest is not None:
        # noinspection PyArgumentList
        QTest.qWait(int(sec * 1000))
        return
    time.sleep(max(float(sec), 0))


def change_format(text, dotdowndel=False, dotdown4=False, dotdown8=False):
    text = str(text)
    try:
        format_data = f'{int(text):,}'
    except:
        if dotdowndel:
            format_data = f'{float(text):,.0f}'
        elif dotdown4:
            format_data = f'{float(text):,.4f}'
        elif dotdown8:
            format_data = f'{float(text):,.8f}'
        else:
            format_data = f'{float(text):,.2f}'
    return format_data


def floor_down(float_, decimal_point):
    float_ = int(float_ * (1 / decimal_point))
    float_ = float_ * decimal_point
    return float_


def comma2int(t):
    if '.' in t: t = t.split('.')[0]
    if ':' in t: t = t.replace(':', '')
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return int(t)


def comma2float(t):
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return float(t)


def write_key():
    if Fernet is None:
        raise RuntimeError('cryptography package is required for key encryption')
    key = str(Fernet.generate_key(), 'utf-8')
    if reg is None:
        return key
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM')
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY')
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    reg.SetValueEx(openkey, 'EN_KEY', 0, reg.REG_SZ, key)
    reg.CloseKey(openkey)
    return key


def read_key():
    if reg is None:
        return os.environ.get('STOM_EN_KEY', 'STOM_CLI_FALLBACK_KEY')
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    key, _ = reg.QueryValueEx(openkey, 'EN_KEY')
    reg.CloseKey(openkey)
    return key


def en_text(key, text):
    if Fernet is None:
        raise RuntimeError('cryptography package is required for encryption')
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.encrypt(bytes(text, 'utf-8')), 'utf-8')


def de_text(key, text):
    if Fernet is None:
        raise RuntimeError('cryptography package is required for decryption')
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.decrypt(bytes(text, 'utf-8')), 'utf-8')


def factorial(x):
    if x <= 1: return 1
    result  = 1
    current = 2
    while current <= x:
        result *= current
        current += 1
    return result


def text_not_in_special_characters(t):
    t = t.replace(' ', '')
    if t == re.findall(r'\w+', t)[0]:
        return True
    return False


def cme_normal_open():
    if ec is None:
        return False
    str_day  = str_ymd(now_cme())
    today    = dt_ymdhms_ios(f'{str_day} 17:00:00')
    ec_cme   = ec.get_calendar('CMES')
    day_list = ec_cme.sessions_in_range(start=str_day, end=str_day)
    if len(day_list) > 0:
        close_time = ec_cme.session_close(day_list[0]).tz_convert('America/Chicago').time()
        if today.time() != close_time:
            return False
    else:
        return False
    return True


def get_buy_indi_stg(buytxt):
    lines   = [line for line in buytxt.split('\n') if '#' not in line]
    buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
    indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
    if buystg:
        try:
            buystg = safe_compile(buystg, '<string>', 'exec', context='utility.static.get_buy_indi_stg.buystg')
        except:
            buystg = None
    else:
        buystg = None
    if indistg:
        try:
            indistg = safe_compile(indistg, '<string>', 'exec', context='utility.static.get_buy_indi_stg.indistg')
        except:
            indistg = None
    else:
        indistg = None
    return buystg, indistg


def roundfigure_upper5(price, index):
    if index < 20230125000000:
        if 1000 <= price <= 1025:
            return True
        if 5000 <= price <= 5050:
            return True
        if 10000 <= price <= 10250:
            return True
        if 50000 <= price <= 50500:
            return True
        if 100000 <= price <= 102500:
            return True
        if 500000 <= price <= 505000:
            return True
    else:
        if 2000 <= price <= 2025:
            return True
        if 5000 <= price <= 5050:
            return True
        if 20000 <= price <= 20250:
            return True
        if 50000 <= price <= 50500:
            return True
        if 200000 <= price <= 202500:
            return True
        if 500000 <= price <= 505000:
            return True
    return False


def roundfigure_upper(price, unit, index):
    if index < 20230125000000:
        if 1000 <= price <= 1000 + 5 * unit:
            return True
        if 5000 <= price <= 5000 + 10 * unit:
            return True
        if 10000 <= price <= 10000 + 50 * unit:
            return True
        if 50000 <= price <= 50000 + 100 * unit:
            return True
        if 100000 <= price <= 100000 + 500 * unit:
            return True
        if 500000 <= price <= 500000 + 1000 * unit:
            return True
    else:
        if 2000 <= price <= 2000 + 5 * unit:
            return True
        if 5000 <= price <= 5000 + 10 * unit:
            return True
        if 20000 <= price <= 20000 + 50 * unit:
            return True
        if 50000 <= price <= 50000 + 100 * unit:
            return True
        if 200000 <= price <= 200000 + 500 * unit:
            return True
        if 500000 <= price <= 500000 + 1000 * unit:
            return True
    return False


def roundfigure_lower(price, unit, index):
    if index < 20230125000000:
        if 1000 - 1 * unit <= price <= 1000:
            return True
        if 5000 - 5 * unit <= price <= 5000:
            return True
        if 10000 - 10 * unit <= price <= 10000:
            return True
        if 50000 - 50 * unit <= price <= 50000:
            return True
        if 100000 - 100 * unit <= price <= 100000:
            return True
        if 500000 - 500 * unit <= price <= 500000:
            return True
    else:
        if 2000 - 1 * unit <= price <= 2000:
            return True
        if 5000 - 5 * unit <= price <= 5000:
            return True
        if 20000 - 10 * unit <= price <= 20000:
            return True
        if 50000 - 50 * unit <= price <= 50000:
            return True
        if 200000 - 100 * unit <= price <= 200000:
            return True
        if 500000 - 500 * unit <= price <= 500000:
            return True
    return False


def GetUpbitHogaunit(price):
    hoga_map = [
        (0.01, 0.0001),
        (1, 0.001),
        (10, 0.01),
        (100, 0.1),
        (1000, 1),
        (10000, 5),
        (100000, 10),
        (500000, 50),
        (1000000, 100),
        (2000000, 500),
        (float('inf'), 1000)
    ]
    return next((hoga for limit, hoga in hoga_map if price < limit), 1000)


def GetHogaunit(kosd, price, index):
    if index < 20230125000000:
        if kosd:
            hoga_map = [
                (1000, 1),
                (5000, 5),
                (10000, 10),
                (50000, 50),
                (float('inf'), 100)
            ]
        else:
            hoga_map = [
                (1000, 1),
                (5000, 5),
                (10000, 10),
                (50000, 50),
                (100000, 100),
                (500000, 500),
                (float('inf'), 1000)
            ]
    else:
        hoga_map = [
            (2000, 1),
            (5000, 5),
            (20000, 10),
            (50000, 50),
            (200000, 100),
            (500000, 500),
            (float('inf'), 1000)
        ]
    return next((hoga for limit, hoga in hoga_map if price < limit), 1000)


def GetVIPrice(kosd, std_price, index):
    uvi = int(std_price * 1.1)
    x = GetHogaunit(kosd, uvi, index)
    if uvi % x != 0:
        uvi += x - uvi % x
    dvi = int(std_price * 0.9)
    y = GetHogaunit(kosd, dvi, index)
    if dvi % y != 0:
        dvi -= dvi % y
    return int(uvi), int(dvi), int(x)


def GetSangHahanga(kosd, predayclose, index):
    uplimitprice = int(predayclose * 1.30)
    x = GetHogaunit(kosd, uplimitprice, index)
    if uplimitprice % x != 0:
        uplimitprice -= uplimitprice % x
    downlimitprice = int(predayclose * 0.70)
    x = GetHogaunit(kosd, downlimitprice, index)
    if downlimitprice % x != 0:
        downlimitprice += x - downlimitprice % x
    return int(uplimitprice), int(downlimitprice)


def GetUvilower5(uvi, hogaunit, index):
    upper5 = uvi - hogaunit * 5
    if GetHogaunit(True, upper5, index) != hogaunit:
        k = 0
        hogaunit2 = 0
        for i in (1, 2, 3, 4, 5):
            hogaunit_ = GetHogaunit(True, uvi - hogaunit * i, index)
            if hogaunit_ != hogaunit:
                hogaunit2 = hogaunit_
                break
            k += 1
        upper5 = uvi - hogaunit * k - hogaunit2 * (5 - k)
    return upper5


try:
    from numba import jit


    @jit(nopython=True, cache=True)
    def GetKiwoomPgSgSp(bg, cg):
        texs = int(cg * 0.0018)
        bfee = int(bg * 0.00015 / 10) * 10
        sfee = int(cg * 0.00015 / 10) * 10
        pg = int(cg - texs - bfee - sfee)
        sg = int(round(pg - bg))
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    @jit(nopython=True, cache=True)
    def GetUpbitPgSgSp(bg, cg):
        bfee = bg * 0.0005
        sfee = cg * 0.0005
        pg = int(round(cg - bfee - sfee))
        sg = int(round(pg - bg))
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    @jit(nopython=True, cache=True)
    def GetBinanceLongPgSgSp(bg, cg, market1, market2):
        bfee = bg * (0.0004 if market1 else 0.0002)
        sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
        pg = round(cg - bfee - sfee, 4)
        sg = round(pg - bg, 4)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    @jit(nopython=True, cache=True)
    def GetBinanceShortPgSgSp(bg, cg, market1, market2):
        bfee = bg * (0.0004 if market1 else 0.0002)
        sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
        pg = round(bg + bg - cg - bfee - sfee, 4)
        sg = round(pg - bg, 4)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    @jit(nopython=True, cache=True)
    def GetFutureLongPgSgSp(bg, cg, code):
        fee = 2 if code.startswith('M') or code.startswith('SIL') else 7.5
        pg = round(cg - fee * 2, 1)
        sg = round(pg - bg, 1)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    @jit(nopython=True, cache=True)
    def GetFutureShortPgSgSp(bg, cg, code):
        fee = 2 if code.startswith('M') or code.startswith('SIL') else 7.5
        pg = round(bg + bg - cg - fee * 2, 1)
        sg = round(pg - bg, 1)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp
except:
    def GetKiwoomPgSgSp(bg, cg):
        texs = int(cg * 0.0018)
        bfee = int(bg * 0.00015 / 10) * 10
        sfee = int(cg * 0.00015 / 10) * 10
        pg = int(cg - texs - bfee - sfee)
        sg = int(round(pg - bg))
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    def GetUpbitPgSgSp(bg, cg):
        bfee = bg * 0.0005
        sfee = cg * 0.0005
        pg = int(round(cg - bfee - sfee))
        sg = int(round(pg - bg))
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    def GetBinanceLongPgSgSp(bg, cg, market1, market2):
        bfee = bg * (0.0004 if market1 else 0.0002)
        sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
        pg = round(cg - bfee - sfee, 4)
        sg = round(pg - bg, 4)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    def GetBinanceShortPgSgSp(bg, cg, market1, market2):
        bfee = bg * (0.0004 if market1 else 0.0002)
        sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
        pg = round(bg + bg - cg - bfee - sfee, 4)
        sg = round(pg - bg, 4)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp

    def GetFutureLongPgSgSp(bg, cg, code):
        fee = 2 if code.startswith('M') or code.startswith('SIL') else 7.5
        pg = round(cg - fee * 2, 1)
        sg = round(pg - bg, 1)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp


    def GetFutureShortPgSgSp(bg, cg, code):
        fee = 2 if code.startswith('M') or code.startswith('SIL') else 7.5
        pg = round(bg + bg - cg - fee * 2, 1)
        sg = round(pg - bg, 1)
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp
