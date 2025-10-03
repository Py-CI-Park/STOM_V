import time
import numpy as np
import pandas as pd

data  = np.zeros(500000)
index = np.random.rand(500000)
df = pd.DataFrame(data, columns=['보유종목수'], index=index)

dict_bct = {}
start = time.time()
for index in df.index:
    if index in dict_bct.keys():
        dict_bct[index] += 1
    else:
        dict_bct[index] = 1
for index in df.index:
    if index in dict_bct.keys():
        dict_bct[index] += 1
    else:
        dict_bct[index] = 1
print('딕키검색', time.time() - start)

dict_bct = {}
start = time.time()
for index in df.index:
    try:
        dict_bct[index] += 1
    except:
        dict_bct[index] = 1
for index in df.index:
    try:
        dict_bct[index] += 1
    except:
        dict_bct[index] = 1
print('예외처리', time.time() - start)

dict_bct = df['보유종목수'].to_dict()
start = time.time()
for index in df.index:
    dict_bct[index] += 1
for index in df.index:
    dict_bct[index] += 1
print('미리생성', time.time() - start)
