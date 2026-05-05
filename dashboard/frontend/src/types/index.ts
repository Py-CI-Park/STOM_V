export interface JangoItem {
  index: string
  종목명: string
  매수가: number
  현재가: number
  수익률: number
  평가손익: number
  매입금액: number
  평가금액: number
  보유수량: number
  분할매수횟수: number
  분할매도횟수: number
  매수시간: string
}

export interface ChegeolItem {
  index: string
  종목명: string
  주문구분: string
  주문수량: number
  체결수량: number
  미체결수량: number
  체결가: number
  체결시간: string
  주문가격: number
  주문번호: string
}

export interface TradeItem {
  index: string
  종목명: string
  매수금액: number
  매도금액: number
  주문수량: number
  수익률: number
  수익금: number
  체결시간: string
}

export interface TotalTrade {
  거래횟수: number
  총매수금액: number
  총매도금액: number
  총수익금액: number
  총손실금액: number
  수익률: number
  수익금합계: number
}

export interface Alert {
  type: 'profit' | 'loss'
  message: string
  stock: string
}

export interface DashboardData {
  jangolist: JangoItem[]
  chegeollist: ChegeolItem[]
  tradelist: TradeItem[]
  totaltradelist: TotalTrade | null
  alerts?: Alert[]
  timestamp: string
}

export type MarketType = 'stock' | 'stock_etf' | 'stock_etn' | 'stock_usa' | 'future' | 'future_nt' | 'future_os' | 'coin' | 'coin_future'
