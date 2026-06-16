/* Backtest workbench tab — shared helpers/constants (split from backtest.jsx for the 800-line cap).
   무예외 fetch 헬퍼·WS URL·잡 배지/모드 라벨·기간 예시·경과시간·숫자포맷·드릴다운 행·
   오버레이 팔레트·스윕 카운트·금액포맷 등 백테탭 sub-file 들이 공유하는 순수 유틸 묶음.

   소비처: bt-tab-library / bt-tab-run / bt-tab-mode-results / bt-tab-analysis / backtest(배럴).
     각 sub-file 이 필요한 심볼만 골라 import 한다.

   stom-ui 전역(fmt* / _axisTicks 등)은 절대 import-변환하지 않는다(window 전역으로 공유).
   _btFetchJson 은 backtest-charts.jsx 의 BtResultArea 도 전역으로 공유해 쓴다(이 파일이 window 재게시).
*/
const {
  useState: useState_bt, useEffect: useEffect_bt,
  useCallback: useCallback_bt, useRef: useRef_bt, useMemo: useMemo_bt,
} = React;

// 무예외 fetch 헬퍼 — 실패 시 throw 대신 거부를 호출측 catch 로 흘린다.
//   backtest-charts.jsx 의 BtResultArea 도 _btFetchJson 을 전역으로 공유해 쓴다(호출은 렌더 시점).
function _btFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 5000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}
function _btPostJson(url, body, timeoutMs) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
    signal: AbortSignal.timeout(timeoutMs || 8000),
  }).then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

// http(s) baseUrl + 경로 → ws(s) URL. baseUrl 이 비면 현재 origin 기준.
function _btWsUrl(baseUrl, path) {
  let origin = baseUrl || (window.location ? window.location.origin : "");
  origin = origin.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
  if (!/^wss?:/i.test(origin)) {
    const loc = window.location || {};
    const proto = (loc.protocol === "https:") ? "wss:" : "ws:";
    origin = proto + "//" + (loc.host || "");
  }
  return origin.replace(/\/$/, "") + path;
}

const _BT_JOB_BADGE = {
  pending:   { txt: "대기", cls: "badge idle" },
  running:   { txt: "실행중", cls: "badge run" },
  success:   { txt: "성공", cls: "badge done" },
  no_trades: { txt: "거래 0건", cls: "badge warn" },
  error:     { txt: "오류", cls: "badge err" },
  timeout:   { txt: "시간초과", cls: "badge err" },
  cancelled: { txt: "취소됨", cls: "badge idle" },
};

// 모드별 대형 실행 버튼 라벨.
const _BT_MODE_RUN_LABEL = {
  backtest: "백테스트 실행",
  optimize: "최적화 실행",
  wfo: "전진분석 실행",
  sweep: "스윕 실행",
};

// 모드 토글 hover 설명 — 전문 용어(WFO·스윕)를 풀어 쓴다.
const _BT_MODE_TIP = {
  backtest: "백테스트 — 고른 기간에 매수/매도 조건식을 1회 시뮬레이션합니다.",
  optimize: "최적화 — 파라미터 탐색공간을 격자로 훑어 최적 조합을 찾습니다.",
  wfo: "WFO(전진분석, Walk-Forward) — 훈련 구간에서 파라미터를 고른 뒤, "
     + "바로 다음 미학습 구간에서 검증하기를 굴려가며 반복합니다(과최적화 점검).",
  sweep: "스윕(sweep) — 파라미터 조합 또는 날짜 윈도우를 일괄로 쓸어가며 "
       + "성과 지형(고원/절벽)을 펼쳐 봅니다.",
};

// 기간 입력 placeholder 예시 — 현재 연도 기준으로 동적 생성(연도 고정 시 매년 노후화).
//   예: 2026년이면 시작 "20260101" · 종료 "20261231".
const _BT_YEAR = (new Date()).getFullYear();
const _BT_START_EG = _BT_YEAR + "0101";
const _BT_END_EG = _BT_YEAR + "1231";

function _btElapsed(rec) {
  const s = rec.started_at;
  if (!s) return "—";
  const end = rec.finished_at || (Date.now() / 1000);
  const sec = Math.max(0, Math.round(end - s));
  if (sec < 60) return sec + "s";
  return Math.floor(sec / 60) + "m " + (sec % 60) + "s";
}

function _btNum(v, digits) {
  const n = Number(v);
  if (v == null || isNaN(n)) return "—";
  return n.toFixed(digits == null ? 2 : digits);
}

// 드릴다운 상세 한 줄(WFO·스윕 공용) — 라벨 + key=value 칩들. 빈 객체면 "—".
//   numeric 이면 값에 _btNum(소수 2자리) 적용, 아니면 원문(파라미터 값 등).
function _BtRowDetail({ label, data, numeric }) {
  const keys = Object.keys(data || {});
  return (
    <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", display: "flex", flexWrap: "wrap", gap: 14, marginTop: 4 }}>
      <span style={{ color: "var(--ink-3)", minWidth: 80 }}>{label}</span>
      {keys.length === 0
        ? <span>—</span>
        : keys.map(k => (
            <span key={k}>{k}=<b style={{ color: "var(--ink-1)" }}>{numeric ? _btNum(data[k]) : String(data[k])}</b></span>
          ))}
    </div>
  );
}

const _BT_OVERLAY_COLORS = ["var(--teal)", "var(--amber)", "var(--violet)", "var(--blue)"];

// _btSweepRowCount: 빈 변수명 행을 제외한 유효 행 수(제출 검증·미리보기 공용 순수 함수).
function _btSweepRowCount(rows) {
  if (!Array.isArray(rows)) return 0;
  return rows.filter(r => r && String(r.name || "").trim()).length;
}

// 행 한 줄 → 조합 개수 추정(min/max/step 펼침). 미리보기 배지가 데카르트 곱 추정에 쓴다.
//   백엔드 _expand_sweep_range 와 동일 규칙(포함 구간, step<=0/lo>hi → 1개).
function _btSweepValueCount(row) {
  if (!row) return 0;
  const lo = Number(row.min), hi = Number(row.max), step = Number(row.step);
  if (!isFinite(lo) || !isFinite(hi)) return 0;
  if (!isFinite(step) || step <= 0 || lo > hi) return 1;
  return Math.min(64, Math.floor((hi - lo) / step + 1e-9) + 1);
}

function _pfFmtMoney(v) {
  const n = Number(v) || 0;
  return (n >= 0 ? "+" : "") + Math.round(n).toLocaleString() + "원";
}

// Track Z — dual-safe ESM export (stripped by build-app.mjs in the concat path; kept by the bundle). KEEP on ONE physical line.
export { useState_bt, useEffect_bt, useCallback_bt, useRef_bt, useMemo_bt, _btFetchJson, _btPostJson, _btWsUrl, _BT_JOB_BADGE, _BT_MODE_RUN_LABEL, _BT_MODE_TIP, _BT_YEAR, _BT_START_EG, _BT_END_EG, _btElapsed, _btNum, _BtRowDetail, _BT_OVERLAY_COLORS, _btSweepRowCount, _btSweepValueCount, _pfFmtMoney };
