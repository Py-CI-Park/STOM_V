import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // 환경변수 로드 (상대 경로 사용)
  const env = loadEnv(mode, './', 'STOM_')

  // 프론트엔드 포트 (기본값 3000)
  const frontendPort = parseInt(env.STOM_FRONTEND_PORT || '3000')
  // 백엔드 포트 (기본값 8000)
  const backendPort = parseInt(env.STOM_BACKEND_PORT || '8000')

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      proxy: {
        '/ws': {
          target: `ws://localhost:${backendPort}`,
          ws: true
        },
        '/api': {
          target: `http://localhost:${backendPort}`
        }
      }
    },
    define: {
      // 빌드 시점에 환경변수 주입
      'import.meta.env.VITE_STOM_MARKET_CODE': JSON.stringify(env.STOM_MARKET_CODE || 'stock'),
      'import.meta.env.VITE_STOM_BACKEND_PORT': JSON.stringify(env.STOM_BACKEND_PORT || '8000'),
      'import.meta.env.VITE_STOM_FRONTEND_PORT': JSON.stringify(env.STOM_FRONTEND_PORT || '3000')
    }
  }
})
