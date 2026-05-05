import { useState, useMemo, useEffect } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import SummaryCards from '../components/SummaryCards'
import JangoTable from '../components/JangoTable'
import ChegeolTable from '../components/ChegeolTable'
import TradeTable from '../components/TradeTable'
import AlertPanel from '../components/AlertPanel'
import { Sun, Moon as MoonIcon } from 'lucide-react'

// 마켓코드 -> 마켓명 매핑
const MARKET_NAMES: Record<string, string> = {
  stock: '국내주식',
  stock_etf: 'ETF',
  stock_etn: 'ETN',
  stock_usa: '미국주식',
  future: '선물',
  future_nt: '선물야간',
  future_os: '해외선물',
  coin: '코인',
  coin_future: '코인선물'
}

// 환경변수에서 마켓코드 읽기 (빌드 시점에 주입)
const FIXED_MARKET_CODE = import.meta.env.VITE_STOM_MARKET_CODE || 'stock'
const FIXED_MARKET_NAME = MARKET_NAMES[FIXED_MARKET_CODE] || '국내주식'

export default function Dashboard() {
  const [isDarkMode, setIsDarkMode] = useState(true)
  // 고정된 마켓코드로 WebSocket 연결
  const { data, isLoading } = useWebSocket(FIXED_MARKET_CODE)

  // 다크 모드 토글 시 HTML 태그에 dark 클래스 추가/제거
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  // useMemo로 items 데이터 캐싱 - 실제 데이터 변경 시에만 새로운 참조 생성
  const jangoItems = useMemo(() => data?.jangolist ?? [], [data])
  const chegeolItems = useMemo(() => data?.chegeollist ?? [], [data])
  const tradeItems = useMemo(() => data?.tradelist ?? [], [data])

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-100 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4 md:p-6 relative overflow-hidden">
      <div className="max-w-7xl mx-auto space-y-4 md:space-y-6">
        <div className="flex flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
              STOM BOARD ＠ {FIXED_MARKET_NAME}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-2 h-10 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 dark:from-gray-700 dark:to-gray-800 hover:from-blue-600 hover:to-purple-600 dark:hover:from-gray-600 dark:hover:to-gray-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
              aria-label="다크 모드 토글"
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <MoonIcon className="w-5 h-5" />}
            </button>
          </div>
        </div>
        <div className="space-y-3">
          {data && (data.jangolist || data.chegeollist || data.tradelist || data.totaltradelist) ? (
            <>
              {isLoading && (
                <div className="flex items-center justify-center py-2">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">데이터 업데이트 중...</p>
                  </div>
                </div>
              )}
              <SummaryCards totalTrade={data.totaltradelist} market={FIXED_MARKET_CODE} timestamp={data.timestamp} />
              <AlertPanel alerts={data.alerts || []} />
              <JangoTable items={jangoItems} />
              <ChegeolTable items={chegeolItems} />
              <TradeTable items={tradeItems} />
            </>
          ) : (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">데이터 로딩 중...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
