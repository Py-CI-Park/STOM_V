import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TotalTrade, MarketType } from '../types'
import { Wallet, TrendingUp, DollarSign, BarChart3, Clock } from 'lucide-react'

interface Props {
  totalTrade: TotalTrade | null
  market: MarketType
  timestamp?: string
}

export default function SummaryCards({ totalTrade, market, timestamp }: Props) {
  if (!totalTrade) return null

  // 거래소별 금액 단위 결정
  const currencyUnits: Record<MarketType, string> = {
    stock: '원',
    stock_etf: '원',
    stock_etn: '원',
    stock_usa: 'USD',
    future: '원',
    future_nt: '원',
    future_os: 'USD',
    coin: '원',
    coin_future: 'USDT'
  }

  const currency = currencyUnits[market]

  // 연월일 시간 포맷팅
  const formattedDate = timestamp ? new Date(timestamp).toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour12: false
  }).replace(/\./g, '/').replace(/\/$/, '') : ''
  const formattedTime = timestamp ? new Date(timestamp).toLocaleString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\./g, '').replace(/\//g, '') : ''

  const cards = [
    { title: '일자 시간', value: { date: formattedDate, time: formattedTime }, color: 'text-gray-600 dark:text-white', icon: Clock, isDateTime: true },
    { title: '거래 횟수', value: totalTrade.거래횟수.toString(), color: 'text-gray-600 dark:text-white', icon: BarChart3 },
    { title: '총 매입금액', value: Math.floor(totalTrade.총매수금액).toLocaleString(), currency: currency, color: 'text-red-600 dark:text-red-400', icon: Wallet, isCurrency: true },
    { title: '총 매도금액', value: Math.floor(totalTrade.총매도금액).toLocaleString(), currency: currency, color: 'text-blue-600 dark:text-blue-400', icon: DollarSign, isCurrency: true },
    { title: '총 수익금', value: (totalTrade.수익금합계 >= 0 ? '+' : '') + Math.floor(totalTrade.수익금합계).toLocaleString() + currency, color: totalTrade.수익금합계 >= 0 ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400', icon: TrendingUp },
    { title: '총 수익률', value: (totalTrade.수익률 >= 0 ? '+' : '') + totalTrade.수익률.toFixed(2) + '%', color: totalTrade.수익률 >= 0 ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400', icon: TrendingUp }
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <Card key={card.title} className="rounded-xl border border-indigo-200/50 dark:border-gray-700/50 bg-gradient-to-br from-white via-indigo-100 to-purple-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 shadow-lg hover:shadow-xl transition-all duration-200">
            <CardHeader className="pb-2 p-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-xs font-medium text-gray-600 dark:text-white">{card.title}</CardTitle>
              <Icon className="w-4 h-4 text-gray-400 dark:text-gray-300" />
            </CardHeader>
            <CardContent className="p-3 pt-0">
              {card.isDateTime ? (
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold text-left text-gray-600 dark:text-white">{(card.value as { date: string; time: string }).date}</span>
                  <span className="text-lg font-bold text-right text-gray-600 dark:text-white">{(card.value as { date: string; time: string }).time}</span>
                </div>
              ) : card.isCurrency ? (
                <div className="text-lg font-bold text-right">
                  <span className={card.color}>{card.value as string}</span>
                  <span className="text-gray-600 dark:text-white">{card.currency}</span>
                </div>
              ) : (
                <div className={`text-lg font-bold text-right ${card.color}`}>
                  {card.value as string}
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
