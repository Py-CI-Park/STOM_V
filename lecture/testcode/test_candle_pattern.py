import talib
import sqlite3
import pandas as pd
from utility.setting import DB_STOCK_BACK_TICK

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

patterns = talib.get_function_groups()['Pattern Recognition']
pattern_number = {x: i + 1 for i, x in enumerate(patterns)}
print(pattern_number)

con = sqlite3.connect(DB_STOCK_BACK_TICK)
df = pd.read_sql(f"SELECT * FROM '089140' WHERE `index` LIKE '20221007%'", con)
con.close()

columns = ['index', '시가', '고가', '저가', '현재가']
df = df[columns]
df.set_index('index', inplace=True)

df2 = pd.DataFrame(data={x: getattr(talib, x)(df['시가'], df['고가'], df['저가'], df['현재가']) for x in patterns})
df['패턴'] = df2.idxmax(axis=1)

print(df)
