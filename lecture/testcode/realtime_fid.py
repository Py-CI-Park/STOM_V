with open('C:/OpenAPI/data/nkrealtime.dat') as f:
    realtimetxt = f.readlines()

주식체결, 주식호가 = '', ''
for txt in realtimetxt:
    if ';' not in txt:
        if '0B주식체결' in txt:
            주식체결 = '20' + txt.split('20')[1]
        if '0D주식호가잔량' in txt:
            주식호가 = '21' + txt.split('16321')[1]

주식체결 = 주식체결.replace('   ', ';').replace('  ', ';').split(';')
주식호가 = 주식호가.replace('   ', ';').replace('  ', ';').split(';')

주식체결피드번호 = [
    주식체결.index('20'), 주식체결.index('10'), 주식체결.index('12'), 주식체결.index('15'), 주식체결.index('14'),
    주식체결.index('16'), 주식체결.index('17'), 주식체결.index('18'), 주식체결.index('228'), 주식체결.index('29'),
    주식체결.index('30'), 주식체결.index('31'), 주식체결.index('851'), 주식체결.index('311'), 주식체결.index('27'),
    주식체결.index('28')
]

주식호가피드번호 = [
    주식호가.index('121'), 주식호가.index('125'), 주식호가.index('45'), 주식호가.index('44'), 주식호가.index('43'),
    주식호가.index('42'), 주식호가.index('41'), 주식호가.index('51'), 주식호가.index('52'), 주식호가.index('53'),
    주식호가.index('54'), 주식호가.index('55'), 주식호가.index('65'), 주식호가.index('64'), 주식호가.index('63'),
    주식호가.index('62'), 주식호가.index('61'), 주식호가.index('71'), 주식호가.index('72'), 주식호가.index('73'),
    주식호가.index('74'), 주식호가.index('75')
]

print('이전값', '[0, 1, 3, 6, 8, 9, 10, 11, 18, 14, 15, 16, 25, 19, 4, 5]')
print('현재값', 주식체결피드번호)

print('이전값', '[61, 63, 25, 19, 13, 7, 1, 4, 10, 16, 22, 28, 26, 20, 14, 8, 2, 5, 11, 17, 23, 29]')
print('현재값', 주식호가피드번호)
