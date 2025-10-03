import time
import numpy as np

data_list1 = list(np.random.rand(1000))
data_list2 = list(np.random.rand(1000))

start = time.time()
count_in_data = 0
for i in data_list1:
    if i in data_list2:
        count_in_data += 1
print(f'count {count_in_data} in data')
print(time.time() - start)

data_list1 = np.random.rand(1000)
data_list2 = np.random.rand(1000)

start = time.time()
count_in_data = 0
for i in data_list1:
    if i in data_list2:
        count_in_data += 1
print(f'count {count_in_data} in data')
print(time.time() - start)
