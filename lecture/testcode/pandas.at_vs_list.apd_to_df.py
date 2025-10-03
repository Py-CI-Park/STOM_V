import time
import pandas as pd

index_list = []
data_list  = [[], [], [], [], [], [], []]
total_list = []
columns1 = ['거래횟수', '보유기간합계', '익절', '손절', '승률', '수익률', '수익금']
columns2 = ['index', '거래횟수', '보유기간합계', '익절', '손절', '승률', '수익률', '수익금']
df = pd.DataFrame(columns=columns1)

start = time.time()
for i in range(1000):
    df.loc[i] = i, i+1, i+1, i+1, 50+i+1, i+1, 1000+i+1
print(time.time() - start)

start = time.time()
for i in range(1000):
    index_list.append(i)
    data_list[0].append(i)
    data_list[1].append(i+1)
    data_list[2].append(i+1)
    data_list[3].append(i+1)
    data_list[4].append(50+i+1)
    data_list[5].append(i+1)
    data_list[6].append(1000+i+1)
df = pd.DataFrame(dict(zip(columns1, data_list)), index=index_list)
print(time.time() - start)

start = time.time()
for i in range(1000):
    total_list.append([i, i, i+1, i+1, i+1, 50+i+1, i+1, 1000+i+1])
df = pd.DataFrame(total_list, columns=columns2)
df.set_index('index', inplace=True)
print(time.time() - start)
