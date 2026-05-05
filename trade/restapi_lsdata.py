
from utility.static_method.static import str_ymd


class LsRestData:
    """LS증권 RESTAPI 데이터 클래스"""
    호스트주소 = 'https://openapi.ls-sec.co.kr:8080'
    웹소켓주소 = 'wss://openapi.ls-sec.co.kr:9443/websocket'
    마지막주소 = {
        '토큰발급': '/oauth2/token',
        '토큰폐기': '/oauth2/revoke',

        '국내주식종목정보': '/stock/etc',
        '국내주식상장주수': '/stock/market-data',
        '국내주식예수금': '/stock/accno',
        '국내주식일반주문': '/stock/order',
        '국내주식정정주문': '/stock/order',
        '국내주식취소주문': '/stock/order',

        '지수선물종목정보1': '/futureoption/market-data',
        '지수선물종목정보2': '/futureoption/market-data',
        '지수선물예수금': '/futureoption/accno',
        '지수선물일반주문': '/futureoption/order',
        '지수선물정정주문': '/futureoption/order',
        '지수선물취소주문': '/futureoption/order',

        '파생상품증거금조회': '/futureoption/etc',

        '야간선물종목정보': '/futureoption/market-data',
        '야간선물예수금': '/futureoption/accno',
        '야간선물일반주문': '/futureoption/order',
        '야간선물정정주문': '/futureoption/order',
        '야간선물취소주문': '/futureoption/order',

        '해외주식종목정보': '/overseas-stock/market-data',
        '해외주식예수금': '/overseas-stock/accno',
        '해외주식일반주문': '/overseas-stock/order',
        '해외주식정정주문': '/overseas-stock/order',

        '해외선물종목정보': '/overseas-futureoption/market-data',
        '해외선물예수금': '/overseas-futureoption/accno',
        '해외선물일반주문': '/overseas-futureoption/order',
        '해외선물정정주문': '/overseas-futureoption/order',
        '해외선물취소주문': '/overseas-futureoption/order'
    }

    당일일자 = str_ymd()
    장운영상태 = {
        '11': '장전 동시호가가 시작되었습니다.',
        '21': f'{당일일자[:4]}년 {당일일자[4:6]}월 {당일일자[6:8]}일 장이 시작되었습니다.',
        '22': '장 시작 10초 전입니다.',
        '23': '장 시작 1분 전입니다.',
        '24': '장 시작 5분 전입니다.',
        '25': '장 시작 10분 전입니다.',
        '31': '장후 동시호가가 시작되었습니다.',
        '41': f'{당일일자[:4]}년 {당일일자[4:6]}월 {당일일자[6:8]}일 장이 마감되었습니다.',
        '42': '장 마감 10초 전입니다.',
        '43': '장 마감 1분 전입니다.',
        '44': '장 마감 5분 전입니다.'
    }

    장구분 = {
        1: '1',
        2: '1',
        3: '1',
        4: '9',
        6: '5',
        7: '8',
        8: '9'
    }

    국내주식주문구분코드 = {
        '매도': '1',
        '매수': '2'
    }

    국내주식주문체결코드 = {
        '1': '매도',
        '2': '매수',
        '11': '체결',
        '12': '정정',
        '13': '취소'
    }

    해외주식주문구분코드 = {
        '매도': '01',
        '매수': '02',
        '취소': '08'
    }

    해외주식주문체결코드 = {
        '01': '매도',
        '02': '매수',
        '11': '체결',
        '12': '정정',
        '13': '취소'
    }

    국내주식호가유형코드 = {
        '지정가': '00',
        '시장가': '03',
        '최유리지정가': '06',
        '지정가IOC': '00',
        '지정가FOK': '00',
        '최유리IOC': '06',
        '최유리FOK': '06'
    }

    국내주식주문조건코드 = {
        '지정가': '0',
        '시장가': '0',
        '최유리지정가': '0',
        '지정가IOC': '1',
        '지정가FOK': '2',
        '최유리IOC': '1',
        '최유리FOK': '2'
    }

    지수선물호가유형코드 = {
        '지정가': '00',
        '시장가': '03',
        '최유리지정가': '06',
        '지정가IOC': '10',
        '지정가FOK': '20',
        '최유리IOC': '16',
        '최유리FOK': '26'
    }

    해외주식호가유형코드 = {
        '지정가': '00',
        '시장가': '03'
    }

    선물주문구분코드 = {
        'SELL_LONG': '1',
        'BUY_LONG': '2',
        'BUY_SHORT': '1',
        'SELL_SHORT': '2',
        'SELL_LONG_MODIFY': '1',
        'BUY_LONG_MODIFY': '2',
        'BUY_SHORT_MODIFY': '1',
        'SELL_SHORT_MODIFY': '2'
    }

    선물주문체결코드 = {
        '1': '체결',
        '2': '정정',
        '3': '취소'
    }

    해외선물호가유형코드 = {
        '지정가': '1',
        '시장가': '2'
    }

    실시간거래코드 = {
        '장운영정보': 'JIF',

        '국내주식체결': 'US3',
        '국내주식호가': 'UH1',
        '국내주식VI': 'UVI',

        '지수선물체결': 'FC0',
        '지수선물호가': 'FH0',

        '야간선물체결': 'DC0',
        '야간선물호가': 'DH0',

        '해외주식체결': 'GSC',
        '해외주식호가': 'GSH',

        '해외선물체결': 'OVC',
        '해외선물호가': 'OVH',
    }

    주문거래코드 = {
        '국내주식주문체결': 'SC1',

        '해외주식주문체결': 'AS1',

        '지수선물주문체결': 'C01',
        '지수선물정정취소': 'H01',

        '야간선물주문체결': 'C02',
        '야간선물정정취소': 'H02',

        '해외선물주문체결': 'TC3'
    }

    tr_data = {
        '국내주식종목정보': {
            'tr_cd': 't8436',
            'body_key': 't8436InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8436OutBlock'
        },
        '국내주식상장주수': {
            'tr_cd': 't1102',
            'body_key': 't1102InBlock',
            'element_keys': ['shcode', 'exchgubun'],
            'element_values': ['종목코드', '거래소구분코드'],
            'out_block': 't1102OutBlock'
        },
        '국내주식예수금': {
            'tr_cd': 'CSPAQ12200',
            'body_key': 'CSPAQ12200InBlock1',
            'element_keys': ['RecCnt', 'BalCreTp'],
            'element_values': ['레코드갯수', '잔고생성구분'],
            'out_block': 'CSPAQ12200OutBlock2'
        },
        '국내주식일반주문': {
            'tr_cd': 'CSPAT00601',
            'body_key': 'CSPAT00601InBlock1',
            'element_keys': ['IsuNo', 'OrdQty', 'OrdPrc', 'BnsTpCode', 'OrdprcPtnCode', 'MgntrnCode', 'LoanDt',
                             'OrdCndiTpCode', 'MbrNo'],
            'element_values': ['종목코드', '주문수량', '주문가격', '주문구분코드', '호가유형코드', '신용거래코드', '대출일', '주문조건코드',
                               '회원사번호'],
            'out_block': 'CSPAT00601OutBlock2'
        },
        '국내주식정정주문': {
            'tr_cd': 'CSPAT00701',
            'body_key': 'CSPAT00701InBlock1',
            'element_keys': ['OrgOrdNo', 'IsuNo', 'OrdQty', 'OrdprcPtnCode', 'OrdCndiTpCode', 'OrdPrc'],
            'element_values': ['원주문번호', '종목코드', '주문수량', '호가유형코드', '주문조건코드', '주문가격'],
            'out_block': 'CSPAT00701OutBlock2'
        },
        '국내주식취소주문': {
            'tr_cd': 'CSPAT00801',
            'body_key': 'CSPAT00801InBlock1',
            'element_keys': ['OrgOrdNo', 'IsuNo', 'OrdQty'],
            'element_values': ['원주문번호', '종목코드', '주문수량'],
            'out_block': 'CSPAT00801OutBlock2'
        },

        '지수선물종목정보1': {
            'tr_cd': 't8432',
            'body_key': 't8432InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8432OutBlock'
        },
        '지수선물종목정보2': {
            'tr_cd': 't8435',
            'body_key': 't8435InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8435OutBlock'
        },
        '지수선물예수금': {
            'tr_cd': 'CFOBQ10500',
            'body_key': 'CFOBQ10500InBlock1',
            'element_keys': ['RecCnt'],
            'element_values': ['레코드갯수'],
            'out_block': 'CFOBQ10500OutBlock2'
        },
        '지수선물일반주문': {
            'tr_cd': 'CFOAT00100',
            'body_key': 'CFOAT00100InBlock1',
            'element_keys': ['FnoIsuNo', 'BnsTpCode', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'OrdQty'],
            'element_values': ['종목코드', '주문구분코드', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CFOAT00100OutBlock2'
        },
        '지수선물정정주문': {
            'tr_cd': 'CFOAT00200',
            'body_key': 'CFOAT00200InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'MdfyQty'],
            'element_values': ['종목코드', '원주문번호', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CFOAT00200OutBlock2'
        },
        '지수선물취소주문': {
            'tr_cd': 'CFOAT00300',
            'body_key': 'CFOAT00300InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'CancQty'],
            'element_values': ['종목코드', '원주문번호', '주문수량'],
            'out_block': 'CFOAT00300OutBlock2'
        },

        '파생상품증거금조회': {
            'tr_cd': 'MMDAQ91200',
            'body_key': 'MMDAQ91200InBlock1',
            'element_keys': ['IsuLgclssCode', 'IsuMdclssCode'],
            'element_values': ['종목대분류코드', '종목중분류코드'],
            'out_block': 'MMDAQ91200OutBlock2'
        },

        '야간선물종목정보': {
            'tr_cd': 't8455',
            'body_key': 't8455InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8455OutBlock'
        },
        '야간선물예수금': {
            'tr_cd': 'CFOBQ10500',
            'body_key': 'CFOBQ10500InBlock1',
            'element_keys': ['RecCnt'],
            'element_values': ['레코드갯수'],
            'out_block': 'CFOBQ10500OutBlock2'
        },
        '야간선물일반주문': {
            'tr_cd': 'CCENT00100',
            'body_key': 'CCENT00100InBlock1',
            'element_keys': ['FnoIsuNo', 'BnsTpCode', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'OrdQty'],
            'element_values': ['종목코드', '주문구분코드', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CCENT00100OutBlock2'
        },
        '야간선물정정주문': {
            'tr_cd': 'CCENT00200',
            'body_key': 'CCENT00200InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'MdfyQty'],
            'element_values': ['종목코드', '원주문번호', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CCENT00200OutBlock2'
        },
        '야간선물취소주문': {
            'tr_cd': 'CCENT00300',
            'body_key': 'CCENT00300InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'CancQty'],
            'element_values': ['종목코드', '원주문번호', '주문수량'],
            'out_block': 'CCENT00300OutBlock2'
        },

        '해외주식종목정보': {
            'tr_cd': 'g3190',
            'body_key': 'g3190InBlock',
            'element_keys': ['delaygb', 'natcode', 'exgubun', 'readcnt', 'cts_value'],
            'element_values': ['지연구분', '국가구분', '거래소구분', '조회갯수', '연속구분'],
            'out_block': 'g3190OutBlock1'
        },
        '해외주식예수금': {
            'tr_cd': 'COSOQ02701',
            'body_key': 'COSOQ02701InBlock1',
            'element_keys': ['RecCnt', 'CrcyCode'],
            'element_values': ['레코드갯수', '통화코드'],
            'out_block': 'COSOQ02701OutBlock3'
        },
        '해외주식일반주문': {
            'tr_cd': 'COSAT00301',
            'body_key': 'COSAT00301InBlock1',
            'element_keys': ['RecCnt', 'OrdPtnCode', 'OrgOrdNo', 'OrdMktCode', 'IsuNo', 'OrdQty', 'OvrsOrdPrc',
                             'OrdprcPtnCode', 'BrkTpCode'],
            'element_values': ['레코드갯수', '주문구분코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격',
                               '호가유형코드', '중개인구분코드'],
            'out_block': 'COSAT00301OutBlock2'
        },
        '해외주식정정주문': {
            'tr_cd': 'COSAT00311',
            'body_key': 'COSAT00311InBlock1',
            'element_keys': ['RecCnt', 'OrdPtnCode', 'OrgOrdNo', 'OrdMktCode', 'IsuNo', 'OrdQty', 'OvrsOrdPrc',
                             'OrdprcPtnCode', 'BrkTpCode'],
            'element_values': ['레코드갯수', '주문구분코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격',
                               '호가유형코드', '중개인구분코드'],
            'out_block': 'COSAT00311OutBlock2'
        },

        '해외선물종목정보': {
            'tr_cd': 'o3101',
            'body_key': 'o3101InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 'o3101OutBlock'
        },
        '해외선물예수금': {
            'tr_cd': 'CIDBQ03000',
            'body_key': 'CIDBQ03000InBlock1',
            'element_keys': ['AcntTpCode', 'TrdDt'],
            'element_values': ['계좌구분코드', '거래일자'],
            'out_block': 'CIDBQ03000OutBlock2'
        },
        '해외선물일반주문': {
            'tr_cd': 'CIDBT00100',
            'body_key': 'CIDBT00100InBlock1',
            'element_keys': ['OrdDt', 'IsuCodeVal', 'FutsOrdTpCode', 'BnsTpCode', 'AbrdFutsOrdPtnCode',
                             'CrcyCode', 'OvrsDrvtOrdPrc', 'CndiOrdPrc', 'OrdQty', 'PrdtCode', 'DueYymm', 'ExchCode'],
            'element_values': ['주문일자', '종목코드', '주문구분', '주문구분코드', '호가유형코드', '통화코드', '주문가격',
                               '조건주문가격', '주문수량', '상품코드', '만기년월', '거래소코드'],
            'out_block': 'CIDBT00100OutBlock2'
        },
        '해외선물정정주문': {
            'tr_cd': 'CIDBT00900',
            'body_key': 'CIDBT00900InBlock1',
            'element_keys': ['OrdDt', 'OvrsFutsOrgOrdNo', 'IsuCodeVal', 'FutsOrdTpCode', 'BnsTpCode', 'FutsOrdPtnCode',
                             'CrcyCodeVal', 'OvrsDrvtOrdPrc', 'CndiOrdPrc', 'OrdQty', 'OvrsDrvtPrdtCode', 'DueYymm',
                             'ExchCode'],
            'element_values': ['주문일자', '원주문번호', '종목코드', '주문구분', '주문구분코드', '호가유형코드', '통화코드',
                               '주문가격', '조건주문가격', '주문수량', '상품코드', '만기년월', '거래소코드'],
            'out_block': 'CIDBT00900OutBlock2'
        },
        '해외선물취소주문': {
            'tr_cd': 'CIDBT01000',
            'body_key': 'CIDBT01000InBlock1',
            'element_keys': ['OrdDt', 'IsuCodeVal', 'OvrsFutsOrgOrdNo', 'FutsOrdTpCode', 'PrdtTpCode', 'ExchCode'],
            'element_values': ['주문일자', '종목코드', '원주문번호', '주문구분', '상품구분코드', '거래소코드'],
            'out_block': 'CIDBT01000OutBlock2'
        }
    }
