import numpy as np
from sys import getsizeof

a = [15.20, 2.68, 300, 100, 15200, 104.25, 100.05, 105.02, 98.01, 10000.00000001, 150000, 300000, 1000000,
     1000000, 1000000, 1000000, 20220129090001, 10000.00000001, 10000.00000001, 10000.00000001]

b = np.array([a], dtype='float32')
c = np.array([a], dtype='float64')

print('어레이 일자 기록 확인')
print(b[0, -4])
print(c[0, -4])

print('어레이 메모리 용량 확인')
print(f'float32 [{getsizeof(b)}]byte')
print(f'float64 [{getsizeof(c)}]byte')
