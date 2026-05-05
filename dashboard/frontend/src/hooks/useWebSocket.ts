import { useState, useEffect, useRef, useCallback } from 'react'
import { DashboardData } from '../types'

// 환경변수에서 백엔드 포트 읽기 (기본값 8000)
const BACKEND_PORT = import.meta.env.VITE_STOM_BACKEND_PORT || '8000'
const WS_URL = `ws://${window.location.hostname}:${BACKEND_PORT}`
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(_market: string) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMountedRef = useRef(true)
  const isIntentionalCloseRef = useRef(false)
  const connectingRef = useRef(false)  // 연결 진행 중 플래그

  const connect = useCallback(() => {
    if (!isMountedRef.current || connectingRef.current) return

    connectingRef.current = true

    // 고정된 엔드포인트 /ws 사용
    const wsUrl = `${WS_URL}/ws`
    console.log(`[WebSocket] Connecting to: ${wsUrl}`)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!isMountedRef.current) return
      console.log('[WebSocket] Connected')
      setConnected(true)
      reconnectAttemptsRef.current = 0
      connectingRef.current = false
    }

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return
      try {
        const message = JSON.parse(event.data) as DashboardData
        setData(message)
        setIsLoading(false)
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }

    ws.onclose = (event) => {
      if (!isMountedRef.current) return
      console.log(`[WebSocket] Closed (code: ${event.code}, intentional: ${isIntentionalCloseRef.current})`)
      setConnected(false)
      wsRef.current = null
      connectingRef.current = false

      // 의도적인 종료시 재연결하지 않음
      if (isIntentionalCloseRef.current) {
        console.log('[WebSocket] Intentional close, skipping reconnect')
        return
      }

      // 자동 재연결
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++
        console.log(`[WebSocket] Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttemptsRef.current})`)
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, RECONNECT_DELAY)
      }
    }
  }, [])

  const disconnect = useCallback((intentional = false) => {
    if (intentional) {
      isIntentionalCloseRef.current = true
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // 초기 연결 설정
  useEffect(() => {
    isMountedRef.current = true
    isIntentionalCloseRef.current = false
    reconnectAttemptsRef.current = 0
    setIsLoading(true)

    // 연결 시도
    const timeout = setTimeout(() => {
      if (isMountedRef.current && !connectingRef.current) {
        connect()
      }
    }, 100)

    return () => {
      isMountedRef.current = false
      clearTimeout(timeout)
      disconnect(true)
    }
  }, [connect, disconnect])

  return { data, isLoading, connected }
}
