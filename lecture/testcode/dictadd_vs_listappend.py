import time
import numpy as np

index = np.random.rand(500000)

dict_bct = {}
start = time.time()
for i in index:
    dict_bct[i] = 1
print('딕추가', time.time() - start)

list_bct = []
start = time.time()
for i in index:
    list_bct.append(i)
print('리추가', time.time() - start)
