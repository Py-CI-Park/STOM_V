# Claude Design 프론트엔드 프롬프트 — STOM AI 조건식 자율 진화 대시보드

> 사용법: 아래 "=== PROMPT START ===" 부터 "=== PROMPT END ===" 까지를 그대로 Claude Design(클로드 디자인)에 붙여넣어 단일 페이지 웹앱을 생성한 뒤 zip으로 저장하세요. 백엔드(`python -m ai_strategy_loop`, 기본 `http://127.0.0.1:8770`)와 WebSocket으로 연결됩니다.

=== PROMPT START ===

You are building a single-page real-time web dashboard for an AI trading-strategy evolution system ("STOM AI 조건식 자율 진화 대시보드"). It connects to a local Python backend over REST + WebSocket and visualizes an autonomous loop that generates Korean stock buy/sell strategy code, backtests it, scores it, and iterates. All user-facing text is **Korean**.

## Tech & style
- Single-page app, React + Tailwind (or clean vanilla if simpler). One self-contained build, no backend code.
- **Dark "quant terminal" aesthetic**: near-black background, high-contrast typography, subtle teal/green accents for gains, red for losses/risk, amber for "running". Data-dense but uncluttered. Smooth, non-distracting transitions on live updates. Monospace font for strategy code and numbers.
- Use a lightweight chart lib (Recharts/Chart.js) for the trend chart.
- Fully responsive; primary target is a wide desktop monitor.

## Backend connection (exact)
- Base URL configurable (default `http://127.0.0.1:8770`). WebSocket at `ws://127.0.0.1:8770/ws`.
- On load: `GET /health` → `{status:"ok", contract_version:1}` (show connection badge). `GET /config/spec` → array of field specs to render the Start-settings form. `GET /status` → current state (fallback before WS).
- Open `WS /ws`: on connect the server sends the current state object immediately, then pushes the full state object whenever it changes (~1s cadence). Auto-reconnect with backoff if the socket drops; show a "연결 끊김/재연결 중" badge.

## State object schema (pushed over WS and from GET /status) — `LoopState`, contract_version 1
```
{
  contract_version: 1,
  run_id: string|null,
  status: "idle"|"running"|"stopping"|"complete"|"error",
  current_gen: number,
  max_generations: number,
  provider: string,            // e.g. "gpt_auth"
  bt_timeframe: string,        // "min" | "tick"
  best:   { gen, graded_score, gate_passed, buy_name, sell_name } | null,
  winner: { gen, score, buy_name, sell_name } | null,   // null until a strategy passes the hard gate
  generations: [ { gen_no, status, graded_score, gate_passed, gate_reason, trade_count, mdd, profit, strategy_gist } ],
  latest: { phase, last_checkpoint, message },   // current backtest progress / phase
  cumulative: { tokens, cost_or_count },
  updated_at: string (ISO)
}
```

## Control messages (send as JSON over the same WS)
- Start the loop:  `{ "action": "start", "config": { ...from the settings form... } }`
- Stop after current generation:  `{ "action": "stop" }`
- Approve & deploy a winner:  `{ "action": "final_approval", "buy_name": "<best/winner buy_name>", "sell_name": "<sell_name>", "user_buy": "<user-chosen name>", "user_sell": "<user-chosen name>" }`

## Start-settings form (render from GET /config/spec)
`/config/spec` returns ~13 field specs, each `{ name, label, type, default, help }`. Render a form (modal or left panel) with each field pre-filled with its `default` and the `help` text shown inline (tooltip or sub-label). Group sensibly:
- **목표/제약**: mdd_cap, min_trades, target_score
- **평가 스코프**: bt_timeframe, bt_scope, bt_one_code, bt_window_days
- **과적합 가드**: graduation_holdout (toggle — when ON show its help text about the extra holdout check; default OFF)
- **AI**: provider, model, max_generations
A prominent **"진화 시작"** button sends `{action:"start", config:{<all field values>}}`. Disable while status is running.

## Layout & components
1. **Top bar**: title, backend-connection badge (health + WS), run-status badge (idle/running/stopping/complete/error with color), current generation `current_gen / max_generations` as a progress bar, and **시작/정지** buttons (Start opens the settings form; Stop sends `{action:"stop"}`, enabled only while running).
2. **현재 세대 패널 (live)**: the active generation — `latest.phase` (생성중 / 백테스트중 / 채점중), `latest.message` / `last_checkpoint`, an animated indicator while running. If available, show the strategy_gist of the in-progress generation.
3. **적합도 추이 차트 (핵심)**: line chart of `graded_score` per `gen_no` across `generations`, with a horizontal "best-so-far" reference and distinct markers for `gate_passed=true` points. This is the centerpiece — it answers "루프가 개선되고 있는가?". Y-axis 0–1 (graded), highlight any point ≥1.0 (gate passed) specially.
4. **세대 테이블**: rows from `generations` — 세대(gen_no), 상태(status; success/error badge), 등급점수(graded_score, 3-dp), 게이트(gate_passed ✓/✗), 사유(gate_reason), 거래수(trade_count), MDD(mdd, % red if > mdd_cap), 손익(profit, +green/−red), 전략 요지(strategy_gist, monospace, truncate+expand). Newest at top, current generation highlighted.
5. **Best / Winner 카드**:
   - **Best (graded)** card: from `best` — gen, graded_score, gate_passed, buy/sell names. Always shown while running.
   - **Winner 카드**: only when `winner` is non-null (a strategy passed the hard gate). Show gen, score, names, and a **"실전 전략으로 승인·내보내기"** button that opens a confirm dialog asking for user-chosen 매수/매도 전략 이름, then sends `{action:"final_approval", buy_name, sell_name, user_buy, user_sell}`. Make clear this promotes the strategy to the production strategy DB (live-deploy gate) — require explicit confirmation.
6. **비용/누적 패널**: `cumulative.tokens`, `cumulative.cost_or_count` vs the cap; small gauge.
7. **피드백/부검 패널** (if `latest.message` or a feedback field carries it): show the latest autopsy / error-cause feedback being fed to the next generation, so the user can see the loop's "reasoning" (e.g. "손실 거래는 매수총잔량이 높았다 → 기준을 낮춰라", or "거래 0건 → 진입 완화").

## Behavior
- Everything updates reactively from the pushed state object; never poll-render aggressively (debounce to the ~1s push).
- Empty/idle state (`status:"idle"`, no run): show a welcoming empty state with the 진화 시작 form prominent.
- Gracefully handle nulls (no best/winner yet, empty generations).
- Number formatting: profit with thousands separators + sign; mdd/win-rate as %; scores 3 decimals.
- Korean throughout; keep STOM/AI terms (매수/매도, 적합도, 게이트, MDD, 부검) as-is.

Deliver a polished, production-feeling dashboard a quant would enjoy watching live. Provide the complete code, ready to open against the backend.

=== PROMPT END ===

## 연동 메모 (개발자용, Claude Design 출력 후)
- 백엔드 기동: `python -m ai_strategy_loop --port 8770` (기본 8770). `/health`로 연결 확인.
- 프론트가 zip으로 나오면 브라우저에서 열고 base URL을 백엔드와 맞춥니다(기본 127.0.0.1:8770). CORS는 백엔드에서 열려 있습니다.
- 제어 흐름: 대시보드 "진화 시작" → 백엔드가 루프를 서브프로세스로 기동 → 루프가 `current_state.json`에 상태 발행 → `/ws`가 폴링하여 push → 대시보드 실시간 갱신. "정지"는 STOP 플래그를 써서 현재 세대 후 종료. "승인"은 우승 전략을 운영 strategy.db로 export.
- 계약 버전(`contract_version`)이 바뀌면 이 프롬프트의 스키마 절을 함께 갱신하세요. 정본 계약: `ai_strategy_loop/controller/STATE_CONTRACT.md`.
- (향후) 우승 전략 전체 코드 리뷰 뷰: 현재 계약은 `strategy_gist`(요약)만 포함. 승인 전 전체 코드 확인이 필요하면 백엔드에 전략코드 조회 엔드포인트를 추가하는 것이 후속 작업.
