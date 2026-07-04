# LLM Auth 장애 결정론 폴백 격차 노트 (T6.3, 2026-07-02)

> 권위: advisory_only (연구 레인). 이 노트는 코드 무수정 문서화다 — 배선 대상
> 파일(`brain/generator.py`, `controller/loop.py`)이 이번 사이클 수정 금지라
> 격차와 배선 설계만 기록한다.

## 결론 먼저

| 레인 | auth 장애 시 결정론 폴백 | 판정 |
|------|--------------------------|------|
| 조건식 연구 루프 (`cli/research_loop.py`) | **있음** — provider 미주입/생산 실패 시 `mark_diagnostic_fallback`(prompt credit 0) 결정론 폴백이 자연 발동 | **현행 유지 (무수정)** |
| AI 전략 발굴 루프 (`ai_strategy_loop/controller/loop.py`) | **없음** — auth 장애가 지속되면 세대만 error 로 기록하며 `max_generations` 를 소진 | **격차 — 다음 사이클 배선 필요** |

## 1. 장애 경로 (실측 코드 근거)

2026-06-27 사례(GPT OAuth 갱신 실패 → 루프 세대 소진)의 코드 경로:

1. `ai_strategy_loop/provider/chatgpt_oauth/token_manager.py:121-130`
   — 토큰 만료 + `_refresh()` 실패 시 경고(`"토큰 갱신 실패 - 기존 토큰 반환 시도"`)만
   남기고 **만료된 access token 을 그대로 반환**한다.
2. 로컬 프록시(`proxy_server.py`)가 만료 토큰으로 upstream 호출 → HTTP 401.
3. `ai_strategy_loop/provider/openrouter.py:135-140`
   — 401/403 은 `ProviderError(retryable=False, status=401)`.
   `GptAuthProvider` 는 `OpenRouterProvider.chat` 을 상속하므로 동일 경로
   (`provider/gpt_auth.py:27`). `provider/base.py:96-98` 의 `with_retry` 는
   `retryable=False` 면 재시도 없이 즉시 전파한다.
4. `ai_strategy_loop/brain/generator.py:221-228`
   — `provider.chat` 예외는 재시도 없이 즉시 `{"status": "error", "reason":
   "provider 호출 실패: ..."}` 반환. **폴백 없음.**
5. `ai_strategy_loop/controller/loop.py:1406-1417`
   — `gen_res.get("status") != "ok"` 이면 그 세대를 error(score 0,
   gate_passed=False)로 기록하고 다음 세대로 진행. auth 장애는 지속 장애이므로
   결과적으로 **모든 잔여 세대가 error 로 소진**된다(토큰/시간 낭비, 산출물 0).

## 2. 이미 폴백이 있는 곳 — 현행 유지 판정

조건식 연구 루프는 결정론 폴백을 이미 보유한다(코드 무수정 판정):

- `cli/research_loop.py:205, 1218-1219, 2139, 2289` — 팩 생산 실패/None/provider
  미주입이면 `mark_diagnostic_fallback`(prompt credit 0) 결정론 폴백이 자연 발동.
- `ai_strategy_loop/controller/context_pack_builder.py:19, 248` — falsy 반환 계약이
  위 폴백을 트리거하도록 설계돼 있음.
- `ai_strategy_loop/controller/condition_discovery.py:1462` —
  `"fallback_source": "diagnostic_deterministic_candidate_fallback"`.

즉 연구 레인에서는 LLM auth 가 죽어도 루프가 결정론 후보로 계속 전진한다.

## 3. 격차 — 발굴 루프에 필요한 배선 (전부 현재 수정 금지 → 다음 사이클)

감사 계획(T6.3, `2026-07-02_ai_loop_full_audit_and_code_update_plan.md:137`)의 목표는
"장애 시 결정론 폴백 자동 전환 로그"다. 필요한 배선:

### 3-a. 권장 설계: 별도 래퍼 모듈 (brain/generator.py 우회)

신규 파일 `ai_strategy_loop/provider/failover.py` (신규라 금지 대상 아님):

- `FailoverProvider(primary, fallbacks, on_switch=None)` — `Provider` 프로토콜
  (`chat(messages, model=None, **kw)`)을 만족하는 래퍼.
- 전환 규칙: `ProviderError(retryable=False, status in {401, 403})` 즉시 전환,
  또는 retryable 오류 연속 N회(기본 3) 시 전환.
- 전환 시 `on_switch` 콜백으로 {시각, 사유(status/message), from→to provider}
  구조화 로그를 state 에 남긴다 — 감사 목표의 "자동 전환 로그".
- 폴백 후보: `openrouter` (API 키 존재 시). 키도 없으면 정직 에러 유지
  (조용한 성공 위장 금지).

### 3-b. 배선 지점 (1곳, 현재 수정 금지)

`ai_strategy_loop/controller/loop.py:2660` `_make_provider_with_proxy` —
`make_provider(config)` 반환값을 `FailoverProvider` 로 감싸는 최소 diff(1~3줄).
`brain/generator.py` 는 provider 를 duck-typing 으로 받으므로 **무수정**으로
폴백이 적용된다(이번 사이클 "래퍼 모듈로 우회" 규약과 일치).

선택 보강(동일 사이클): `token_manager.py:121-130` 이 갱신 실패 시 만료 토큰을
반환하는 대신 None 을 반환하면 프록시가 upstream 왕복 없이 즉시 401 을 낼 수
있으나, 이는 provider/auth 코드 수정이므로 필수는 아니다(FailoverProvider 만으로
목표 달성 가능).

### 3-c. 배선 전 운영 우회 (코드 무수정)

- `--provider openrouter` 로 재기동 (`controller/loop.py:2706-2708`; OPENROUTER
  API 키 필요).
- 2026-06-27 처럼 수동 artifacts 스크립트로 세대 산출물 보전.

## 4. 검증 계획 (배선 사이클에서)

1. mock provider 로 401 → FailoverProvider 가 폴백 provider 호출 + 전환 로그 기록.
2. 폴백 부재(키 없음) 시 정직 에러 전파(세대 조용 소진 금지 — 즉시 중단이 낫다).
3. 기존 `controller/loop.py` 경로 byte-동일성: 폴백 미구성 시 래핑이 no-op.
