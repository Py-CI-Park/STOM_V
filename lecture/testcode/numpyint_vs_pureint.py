import time
import numpy as np

arry_hgjr = np.zeros(43, dtype=int)
realdata = ['3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000',
            '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000',
            '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000',
            '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000', '3000',
            '3000', '3000', '3000']

start = time.time()
out_data = {}
for i in range(0, 10000):
    arry_hgjr[:] = realdata
    out_data['offerho1'] = abs(arry_hgjr[1])
    out_data['bidho1'] = abs(arry_hgjr[2])
    out_data['offerrem1'] = arry_hgjr[3]
    out_data['bidrem1'] = arry_hgjr[4]
    out_data['offerho2'] = abs(arry_hgjr[5])
    out_data['bidho2'] = abs(arry_hgjr[6])
    out_data['offerrem2'] = arry_hgjr[7]
    out_data['bidrem2'] = arry_hgjr[8]
    out_data['offerho3'] = abs(arry_hgjr[9])
    out_data['bidho3'] = abs(arry_hgjr[10])
    out_data['offerrem3'] = arry_hgjr[11]
    out_data['bidrem3'] = arry_hgjr[12]
    out_data['offerho4'] = abs(arry_hgjr[13])
    out_data['bidho4'] = abs(arry_hgjr[14])
    out_data['offerrem4'] = arry_hgjr[15]
    out_data['bidrem4'] = arry_hgjr[16]
    out_data['offerho5'] = abs(arry_hgjr[17])
    out_data['bidho5'] = abs(arry_hgjr[18])
    out_data['offerrem5'] = arry_hgjr[19]
    out_data['bidrem5'] = arry_hgjr[20]
    out_data['totofferrem'] = arry_hgjr[41]
    out_data['totbidrem'] = arry_hgjr[42]
print(time.time() - start)

start = time.time()
out_data = {}
for i in range(0, 10000):
    out_data['offerho1'] = abs(int(realdata[1]))
    out_data['bidho1'] = abs(int(realdata[2]))
    out_data['offerrem1'] = int(realdata[3])
    out_data['bidrem1'] = int(realdata[4])
    out_data['offerho2'] = abs(int(realdata[5]))
    out_data['bidho2'] = abs(int(realdata[6]))
    out_data['offerrem2'] = int(realdata[7])
    out_data['bidrem2'] = int(realdata[8])
    out_data['offerho3'] = abs(int(realdata[9]))
    out_data['bidho3'] = abs(int(realdata[10]))
    out_data['offerrem3'] = int(realdata[11])
    out_data['bidrem3'] = int(realdata[12])
    out_data['offerho4'] = abs(int(realdata[13]))
    out_data['bidho4'] = abs(int(realdata[14]))
    out_data['offerrem4'] = int(realdata[15])
    out_data['bidrem4'] = int(realdata[16])
    out_data['offerho5'] = abs(int(realdata[17]))
    out_data['bidho5'] = abs(int(realdata[18]))
    out_data['offerrem5'] = int(realdata[19])
    out_data['bidrem5'] = int(realdata[20])
    out_data['totofferrem'] = int(realdata[41])
    out_data['totbidrem'] = int(realdata[42])
print(time.time() - start)
