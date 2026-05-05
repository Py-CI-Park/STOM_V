import React from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TradeItem } from '../types'

interface Props {
  items: TradeItem[]
}

function TradeTable({ items }: Props) {
  // 당일일자 필터링 (체결시간 형식: 20260416122457)
  const today = new Date()
  const todayStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`
  
  const filteredItems = items.filter(item => {
    if (!item.체결시간) return false
    const timeStr = String(item.체결시간)
    const dateStr = timeStr.substring(0, 8)
    return dateStr === todayStr
  })

  return (
    <Card className="rounded-xl border border-indigo-200/50 dark:border-gray-700/50 bg-gradient-to-br from-white via-indigo-100 to-purple-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 shadow-lg hover:shadow-xl transition-all duration-200">
      <CardHeader className="p-3 md:p-6">
        <CardTitle className="text-base md:text-xl">거래 내역</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-6 overflow-x-auto">
        <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs md:text-sm text-center">종목명</TableHead>
                <TableHead className="text-xs md:text-sm text-center">수익률</TableHead>
                <TableHead className="text-xs md:text-sm text-center">수익금</TableHead>
                <TableHead className="text-xs md:text-sm text-center">체결시간</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.map((item) => (
                <TableRow key={`${item.종목명}-${item.체결시간}`}>
                  <TableCell className="font-medium text-xs md:text-sm">{item.종목명}</TableCell>
                  <TableCell className={`text-xs md:text-sm ${item.수익률 >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                    {(item.수익률 >= 0 ? '+' : '')}{item.수익률.toFixed(2)}%
                  </TableCell>
                  <TableCell className={`text-xs md:text-sm ${item.수익금 >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                    {(item.수익금 >= 0 ? '+' : '')}{item.수익금.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-xs md:text-sm">
                    {(() => {
                      if (!item.체결시간) return '-'
                      try {
                        let date: Date
                        // YYYYMMDDHHMMSS 형식인 경우
                        if (item.체결시간.length === 14 && /^\d+$/.test(item.체결시간)) {
                          const year = item.체결시간.substring(0, 4)
                          const month = item.체결시간.substring(4, 6)
                          const day = item.체결시간.substring(6, 8)
                          const hour = item.체결시간.substring(8, 10)
                          const minute = item.체결시간.substring(10, 12)
                          const second = item.체결시간.substring(12, 14)
                          date = new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`)
                        } else {
                          date = new Date(item.체결시간)
                        }
                        if (isNaN(date.getTime())) return '-'
                        return date.toLocaleTimeString('ko-KR', {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                          hour12: false
                        })
                      } catch {
                        return '-'
                      }
                    })()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
      </CardContent>
    </Card>
  )
}

export default React.memo(TradeTable)
