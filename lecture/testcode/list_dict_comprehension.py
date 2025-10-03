import time
import numpy as np


list_rand = list(np.random.rand(1000000))

print(' 리스트 캄프리헨션')

start = time.time()
result = []
for item in list_rand:
    if item > 0.000001:
        result.append(item)
print(' {:>10} {:<20}'.format('append', time.time() - start))

start = time.time()
result = [item for item in list_rand if item > 0.000001]
print(' {:>10} {:<20}'.format('comphs', time.time() - start))

print(' 딕셔너리 캄프리헨션')

start = time.time()
result_ = {}
for i, item in enumerate(list_rand):
    if item > 0.000001:
        result_[i] = item
print(' {:>10} {:<20}'.format('dic[x] = y', time.time() - start))

start = time.time()
result_ = {i: item for i, item in enumerate(list_rand) if item > 0.000001}
print(' {:>10} {:<20}'.format('comphs', time.time() - start))
