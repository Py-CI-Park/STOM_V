import os
import time
import _pickle
import numpy as np

data = np.random.rand(1000000)

load_time1 = 0
load_time2 = 0
for i in range(1000):
    start1 = time.time()
    with open(f'./temp/{i}.pkl', "wb") as f:
        start2 = time.time()
        _pickle.dump(data, f)
        load_time2 += time.time() - start2
    load_time1 += time.time() - start1
print(load_time1, load_time2)

load_time1 = 0
load_time2 = 0
for i in range(1000):
    start1 = time.time()
    with open(f'./temp/{i}.pkl', "rb") as f:
        start2 = time.time()
        ar = _pickle.load(f)
        load_time2 += time.time() - start2
    load_time1 += time.time() - start1
print(load_time1, load_time2)

load_time1 = 0
load_time2 = 0
for i in range(1000):
    start1 = time.time()
    with open(f'./temp/{i}.pkl2', "wb") as f:
        start2 = time.time()
        _pickle.dump(data, f, protocol=-1)
        load_time2 += time.time() - start2
    load_time1 += time.time() - start1
print(load_time1, load_time2)

load_time1 = 0
load_time2 = 0
for i in range(1000):
    start1 = time.time()
    with open(f'./temp/{i}.pkl2', "rb") as f:
        start2 = time.time()
        ar = _pickle.load(f)
        load_time2 += time.time() - start2
    load_time1 += time.time() - start1
print(load_time1, load_time2)

file_list = os.listdir('./temp')
for file in file_list:
    os.remove(f'./temp/{file}')
