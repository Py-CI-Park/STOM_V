import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Phase14.0 PoC 빌드 설정.
//   - root: 이 디렉토리(webui-build/). 엔트리는 index.html.
//   - outDir: ../frontend/poc → FastAPI StaticFiles(frontend, html=True)가 /ui/poc/ 로 자동 서빙.
//     (백엔드 라우트/마운트 변경 0. app.py:3251 의 재귀 서빙에 얹힌다.)
//   - base "./": /ui/poc/ 어느 경로에 놓여도 자산을 상대경로로 로드.
//   - emptyOutDir: PoC 전용 디렉토리이므로 매 빌드 정리(우리가 소유한 frontend/poc/만 대상).
export default defineConfig({
  root: __dirname,
  base: "./",
  build: {
    outDir: resolve(__dirname, "../frontend/poc"),
    emptyOutDir: true,
    sourcemap: false,
  },
});
