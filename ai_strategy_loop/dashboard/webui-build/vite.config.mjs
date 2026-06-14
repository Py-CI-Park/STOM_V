import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Phase14.1 — 정식 빌드 하네스(lib 모드).
//   - 입력 src/format.mjs → 단일 ES 번들 ../frontend/bundle/stom-ui.js.
//   - 고정 파일명: index.html이 정적 참조 가능(수동 ?v= 캐시 계약 유지). content-hash 자동화는 14.5.
//   - 출력 dir = frontend/bundle: .gitignore가 build/·dist/·frontend/{build,dist}/는 무시하지만
//     bundle/ 은 무시 대상이 아니다 → 산출물 커밋(런타임 npm-free).
//   - 로드 시 format.mjs의 Object.assign(window,…) 부작용으로 window.fmt* 세팅.
//     connection.jsx(babel)도 동일 전역을 세팅하므로 양립(babel = 폴백). de-dup은 14.2.
export default defineConfig({
  root: __dirname,
  build: {
    outDir: resolve(__dirname, "../frontend/bundle"),
    emptyOutDir: true,
    sourcemap: false,
    lib: {
      entry: resolve(__dirname, "src/format.ts"),
      formats: ["es"],
      fileName: () => "stom-ui.js",
    },
  },
});
