/* Connection: REST + WS w/ auto-reconnect; falls back to local simulator for demo.
   THIN BARREL (split for the <800-line cap). 실제 구현은 sibling 모듈에 있다:
     - conn-backend.jsx     : useBackend 훅 + DEFAULT_BASE + INITIAL_STATE + DEFAULT_CONFIG_SPEC
                              + 데모 시뮬레이터(REST/WS plumbing). window.useBackend/DEFAULT_BASE 노출.
     - conn-demo-codegen.jsx: genBuyCode/genSellCode (데모 조건식 생성기, conn-backend 가 소비).
   이 배럴은 sibling 들을 side-effect import 해서 그들의 window publish 를 실행시키고(엔트리가
   connection.jsx 만 side-effect import 해도 전이적으로 useBackend/DEFAULT_BASE 가 노출됨), LIVE↔DEMO
   필드 경계 판정 함수(isDemoSource/livePanelPending)는 여기에 그대로 유지한다(패널/테스트 공용).
   포매터 별칭(fmt 계열·STATUS_KR)도 여기 유지 — 빌드 번들이 정본이며 babel 스코프 별칭만 둔다.
*/
// Track Z — dual-safe ESM side-effect imports run each sibling's window publish. KEEP each on ONE physical line.
import "./conn-demo-codegen.jsx";
import { useBackend, DEFAULT_BASE } from "./conn-backend.jsx";

// =====================================================================
// LIVE ↔ DEMO 필드 경계 (contract v2, M1 격차 해소)
//
//  대시보드 상태는 두 출처 중 하나에서 온다:
//    - LIVE: 실제 루프(controller/loop.py:_publish_live) → current_state.json → WS.
//            contract.LoopState(pydantic)가 발행하는 필드만 담긴다.
//    - DEMO: 프론트 로컬 시뮬레이터(startDemo). backend가 없을 때만 동작하며
//            phase-detail 패널을 보여주려고 풍부한 필드를 "클라이언트에서 날조"한다.
//
//  LIVE가 실제로 발행하는 필드 (backend 계약):
//    contract_version, run_id, status, current_gen, max_generations, provider,
//    bt_timeframe, best, winner, generations[], latest{phase,last_checkpoint,message},
//    cumulative{tokens,cost_or_count}, page_data{...}(v2 패스스루), updated_at.
//
//  DEMO 전용(=backend가 발행하지 않는, 시뮬레이터가 날조하는) 필드:
//    engine{cpu_pct,mem_mb,workers_active,throughput,progress,chunks_* ...},
//    current_run{equity[],drawdown[],trades[],
//                generation{buy_code_partial,sell_code_partial,stream_tokens,...},
//                scoring{metrics[],composite}, autopsy{text_partial,...}}.
//
//  ⇒ 그래서 LIVE 모드에서는 시뮬레이터를 절대 돌리지 않는다(setState(data)만).
//    위 DEMO 전용 패널은 LIVE에서 "실시간 데이터 대기"로 비우고, DEMO 모드에서만
//    내용을 채우되 "DEMO" 배지로 출처를 명시한다(phase-detail.jsx 참조).
//    backend가 page_data로 실제 데이터를 발행하기 시작하면 해당 패널이 LIVE로 승격된다.
// =====================================================================

// 순수 판정 함수(테스트 가능): 현재 상태가 데모 시뮬레이터 출처인지.
//   wsStatus === "demo"일 때만 current_run/engine을 신뢰할 수 있다.
function isDemoSource(wsStatus) {
  return wsStatus === "demo";
}

// 순수 판정 함수(테스트 가능): 라이브 상태인데 DEMO 전용 패널 데이터가 비었는지.
//   true면 패널은 "실시간 데이터 대기"를 보여줘야 한다(날조 금지).
function livePanelPending(wsStatus, state) {
  if (isDemoSource(wsStatus)) return false;            // 데모는 자체 데이터로 채움
  const cr = state && state.current_run;
  const hasRich = !!(cr && ((cr.equity && cr.equity.length) ||
                            (cr.generation && (cr.generation.buy_code_partial ||
                                               cr.generation.sell_code_partial))));
  return !hasRich;                                     // 라이브인데 풍부 필드 없음 → 대기
}

// ---------- Formatting helpers ----------
//   Phase14.2 de-dup: 포매터 구현은 빌드 번들(bundle/stom-ui.js, 소스 webui-build/src/format.mjs)이
//   window 전역으로 제공한다(ESM 모듈이라 babel 실행보다 먼저 로드됨). 여기서는 babel 스코프
//   별칭만 둬서 기존 bare-식별자 소비처(backtest-charts.jsx 등)가 계속 해소되게 한다.
//   → 구현 중복 제거(window 단일 출처). 본래 정의는 format.mjs 가 정본.
const fmtScore = window.fmtScore;
const fmtPct = window.fmtPct;
const fmtMoney = window.fmtMoney;
const fmtInt = window.fmtInt;
const fmtTime = window.fmtTime;
const STATUS_KR = window.STATUS_KR;

Object.assign(window, {
  useBackend,
  DEFAULT_BASE,
  // 포매터·STATUS_KR 는 빌드 번들이 이미 window 에 세팅(중복 노출 제거).
  // LIVE↔DEMO 경계 판정은 아직 connection.jsx 정의 유지(번들도 동일 제공) — 14.x에서 통합.
  isDemoSource, livePanelPending,
});

// Track Z — dual-safe ESM re-export(배럴 표면 보존). KEEP on ONE physical line.
export { useBackend, DEFAULT_BASE, isDemoSource, livePanelPending };
