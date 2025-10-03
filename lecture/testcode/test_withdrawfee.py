import re
import binance
import pyupbit
import pandas as pd
from utility.setting import DICT_SET

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

df = pd.DataFrame(columns=['송금수수료수량', '현재가', '네트워크', '송금수수료'])
codes = pyupbit.get_tickers(fiat="KRW")
codes = [x.replace('KRW-', '') for x in codes]

bn = binance.Client(DICT_SET['Access_key2'], DICT_SET['Secret_key2'])

dict_close = {}
data = bn.get_all_tickers()
for x in data:
    code = x['symbol']
    if re.search('USDT$', code) is not None:
        dict_close[code.replace('USDT', '')] = float(x['price'])

data = bn.get_all_coins_info()
for x in data:
    code = x['coin']
    if code in codes and code in dict_close.keys():
        count_ = 1000000
        for network in x['networkList']:
            name   = network['network']
            enable = network['withdrawEnable']
            count  = float(network['withdrawFee'])
            c      = dict_close[code]
            if name not in ('BNB', 'BSC') and count != 0 and enable and count < count_:
                count_ = count
                df.loc[code] = count, c, name, round(count * c, 8)

df.sort_values(by=['송금수수료'], ascending=True, inplace=True)
print(df)
