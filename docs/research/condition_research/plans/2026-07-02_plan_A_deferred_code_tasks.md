# 계획서 A — 이월 코드 3건 실행 계획 (2026-07-02)

> 권위: advisory_only (연구 레인 계획 문서). 이 문서는 **다음 코드 사이클**에서
> 실행할 이월 항목 3건(A1/A2/A3)의 실행 계획이다. 근거:
> `docs/update_log/2026-07-02_ai_loop_phase_implementation_record.md` "이월 항목" 1·2·4번,
> `docs/research/condition_research/2026-07-02_llm_auth_fallback_gap_note.md`.
> 이 문서만 읽고 다른 에이전트가 실행 가능하도록 명령어·경로·완료 기준·중단 조건을 명시한다.

## 0. 실행 전제 (읽고 시작할 것)

1. 작업 디렉터리: `C:/System_Trading/STOM/STOM_V.wt-dev` (브랜치 `STOM_Version_2U_C`).
2. A1/A2는 **기존 커밋 파일의 최소 diff 수정**을 포함한다. 이는 연구 실행 레인의
   "기존 파일 수정 금지" 규칙이 아니라, 07-02 Phase 0~6과 동일한 **코드 업데이트
   사이클 프로토콜**(전체 unit 게이트 + `verify_nonrelease_sync` 통과 후 한글 커밋)로
   수행한다. A3는 **사용자 승인 전 코드 수정 자체 금지**(§3 참조).
3. 실행 순서: A1 → A2 → (승인 시에만) A3. A1과 A2는 독립 커밋으로 분리한다.
4. Python 실행은 항상 UTF-8 강제: `PYTHONUTF8=1` 환경변수 또는 `python -X utf8`.

## 0.1 공통 불변 조건 (위반 = 즉시 중단)

- 연구 레인 전용: `can_promote / can_export / live = False` 계약 불변. export/live/승격
  플로우 권한 확장 금지.
- 신규 토글·배선은 전부 **기본 OFF(또는 미구성 시 no-op)** — 미구성 경로는 기존 동작과
  byte-동일해야 한다.
- `backtest/graph/` 불가침 (읽기 포함 어떤 조작도 금지).
- 기존 테스트 계약(`tests/unit/test_research_prompt_contracts.py` 등) 파괴 금지.
- 파일당 800줄 이하. 신규 CLI 출력은 `print` 대신 `sys.stdout.write` (기존 파일의
  기존 print는 건드리지 않는다).
- 커밋 메시지는 한글, 커밋 전 게이트 2종 통과 필수:
  ```
  PYTHONUTF8=1 python -m pytest tests/unit/ -q
  python scripts/verify_nonrelease_sync.py
  ```

## 0.2 기존 실패 허용 목록 (전문)

전체 unit 게이트에서 아래 목록의 실패만 허용한다. 이 목록은 브랜치에 **변경 전부터
존재**하는 기존 이슈다(2026-06-11 게이트 증거 2종의 합집합, 최근 07-02 최종 게이트는
3,972 통과 / 실패 8건 전부 이 목록 내). 증거:
`.omo/evidence/claude-condition-research-20260610/p10-full-tests-after-r.txt`(9건),
`.omo/evidence/tmap-walkforward/full-tests-after-tmap.txt`(8건).

| # | 허용 실패 테스트 ID |
|---|---|
| 1 | `tests/unit/test_backtest_button_contract.py::test_backtest_constructor_contract_is_small_and_queue_driven` |
| 2 | `tests/unit/test_backtest_process_protocol_diagnostics.py::test_backtest_start_emits_key_protocol_checkpoints` |
| 3 | `tests/unit/test_backtest_process_protocol_diagnostics.py::test_total_emits_key_protocol_checkpoints` |
| 4 | `tests/unit/test_backtest_spawn_contract_audit.py::test_stock_backtest_spawn_does_not_pass_legacy_long_signature` |
| 5 | `tests/unit/test_backtest_spawn_contract_audit.py::test_coin_backtest_spawn_does_not_pass_legacy_long_signature` |
| 6 | `tests/unit/test_dashboard_validation_views.py::TestFrontendContract::test_research_lab_has_validation_tab_and_panel` |
| 7 | `tests/unit/test_dashboard_validation_views.py::TestFrontendContract::test_index_html_cache_bumped` |
| 8 | `tests/unit/test_runner_helpers.py::TestCliDictSetProcessArgs::test_backtest_process_passes_dict_set_to_constructor` |
| 9 | `tests/unit/test_ui_jisu_cleanup.py::test_v270_removed_jisu_chart_references_are_fully_cleaned` |
| 10 | `tests/unit/test_analysis_gen_filter.py::TestFrontendContract::test_index_cache_bumped` (tmap 증거에서만 관측 — 환경 의존) |

운용 규칙:

1. **작업 시작 전** 전체 게이트를 1회 돌려 현재 기준선 실패 목록을 캡처한다
   (`PYTHONUTF8=1 python -m pytest tests/unit/ -q > baseline_gate.txt 2>&1` — 캡처
   파일은 커밋하지 않는다).
2. 변경 후 게이트 실패가 위 목록(및 시작 전 기준선)과 **완전히 동일 집합**이면 통과로
   본다. 목록 외 실패 1건이라도 나오면 **신규 회귀 — 커밋 금지, 원인 수정 또는 롤백**.

---

## A1 — FailoverProvider (발굴 루프 LLM auth 결정론 폴백)

### A1.1 근거 (격차 노트 요약)

원천: `docs/research/condition_research/2026-07-02_llm_auth_fallback_gap_note.md`.

- 조건식 연구 루프(`cli/research_loop.py`)는 provider 미주입/생산 실패 시
  `mark_diagnostic_fallback`(prompt credit 0) 결정론 폴백이 **이미 존재** → 무수정 유지.
- AI 전략 발굴 루프(`ai_strategy_loop/controller/loop.py`)는 폴백이 **없다**:
  gpt_auth 토큰 갱신 실패(`provider/chatgpt_oauth/token_manager.py:121-130`이 만료
  토큰을 그대로 반환) → 프록시 upstream 401 →
  `provider/openrouter.py:135-140`이 `ProviderError(retryable=False, status=401)` →
  `provider/base.py`의 `with_retry`는 retryable=False면 즉시 전파 →
  `brain/generator.py:221-228`이 `{"status": "error"}` 반환(폴백 없음) →
  `controller/loop.py:1406-1417`이 세대를 error로 기록하고 다음 세대 진행. auth 장애는
  지속 장애라 **잔여 세대 전부 error로 소진**된다(2026-06-27 실사례).
- 노트의 권장 설계: 신규 래퍼 모듈 `FailoverProvider`로 `brain/generator.py` 무수정
  우회, 배선은 `_make_provider_with_proxy` 1곳 최소 diff.

### A1.2 신규 파일

`ai_strategy_loop/provider/failover.py` (신규 — 800줄 제한, 표준 라이브러리만 사용)

```python
class FailoverProvider:
    def __init__(self, primary, fallbacks, *, on_switch=None,
                 retryable_streak_limit=3): ...
    def chat(self, messages, model=None, **kw): ...
```

duck-typing 계약 (실측 근거 — `brain/generator.py:222`는 `provider.chat(messages)`만
호출한다):

- `chat(messages, model=None, **kw) -> ChatResult` — `ai_strategy_loop/provider/base.py`
  의 `Provider.chat` 시그니처와 동일. `ChatResult`/`ProviderError`는 base.py 것을 재사용.
- 전환 규칙:
  1. `ProviderError(retryable=False, status in {401, 403})` → **즉시** 다음 폴백으로 전환.
  2. `ProviderError(retryable=True)` 가 **연속 `retryable_streak_limit`회(기본 3)** →
     전환. (retry 자체는 각 provider 내부 `with_retry`가 이미 수행하므로 여기서 sleep
     재시도를 중복 구현하지 않는다 — 연속 실패 횟수만 센다.)
  3. 그 외 예외(비 ProviderError)는 감싸지 않고 그대로 전파(조용한 삼킴 금지).
- 전환 시 `on_switch({"switched_at": <ISO 시각>, "reason": <status/message>,
  "from": <이름>, "to": <이름>})` 콜백 호출 — 감사 목표 "자동 전환 로그". 이름은
  `getattr(p, "name", type(p).__name__)`.
- `fallbacks`가 비어 있고 primary가 실패하면 **원래 예외를 그대로 전파**(정직 에러 —
  세대 조용 소진보다 즉시 중단이 낫다는 노트 §4-2 판정).
- 전환 후에는 폴백 provider를 계속 사용한다(요청마다 죽은 primary 재시도 금지).
- 상태 변이 최소화: 전환 인덱스·연속 실패 카운터 외 공유 상태 금지.

### A1.3 배선 지점 (기존 파일 최소 diff 1곳)

`ai_strategy_loop/controller/loop.py:2660` `_make_provider_with_proxy` — 현재 마지막 줄
`return make_provider(config), proxy_active` 를 다음 규칙으로 감싼다 (diff 1~5줄):

- 폴백 구성 조건: `os.environ.get("OPENROUTER_API_KEY")` 존재하고
  `config.provider != "openrouter"` 일 때만
  `FailoverProvider(primary, [OpenRouterProvider(config)], on_switch=<state 로그 기록>)`
  로 감싼다. (`OpenRouterProvider`는 `ai_strategy_loop/provider/openrouter.py`,
  키 env는 `OPENROUTER_API_KEY` — openrouter.py:38 실측.)
- 폴백 구성 불가(키 없음, 또는 이미 openrouter)면 **감싸지 않고 기존 반환 그대로**
  (no-op — 기존 경로 byte-동일).
- `on_switch` 로그는 stdout 한 줄(`[LOOP] provider failover: ...` — loop.py의 기존
  로그 스타일과 동일하게 `flush=True`) + 가능하면 run state에 구조화 dict 기록.

주의: `token_manager.py` 등 provider/auth 코드 보강(갱신 실패 시 None 반환)은
**이번 범위 밖** — FailoverProvider만으로 감사 목표가 달성된다(노트 §3-b).

### A1.4 테스트 요구 (신규 `tests/unit/test_provider_failover.py`)

mock provider(성공/401/403/retryable 예외를 시나리오별로 던지는 스텁)로:

1. primary가 `ProviderError(retryable=False, status=401)` → 폴백 provider가 호출되고
   `ChatResult`가 반환되며 `on_switch` 페이로드에 from/to/reason이 기록된다. 403 동일.
2. retryable 오류 연속 3회 → 전환. 2회 후 성공 → 카운터 리셋, 전환 없음.
3. 폴백 리스트 비어 있음 → 원래 `ProviderError` 그대로 전파(타입·status 보존).
4. 비 ProviderError 예외 → 전파(전환 없음).
5. 전환 후 후속 `chat` 호출은 폴백으로 직행(primary 미호출 — mock 호출 카운트 검증).
6. 배선 계약: `_make_provider_with_proxy`가 `OPENROUTER_API_KEY` 미설정이면 반환
   provider가 래핑되지 않은 원 객체임(monkeypatch로 env 제거 후 타입 검증) —
   기존 provider 계약 보존.

자기 테스트 실행: `PYTHONUTF8=1 python -m pytest tests/unit/test_provider_failover.py -q`

### A1.5 완료 기준 / 중단 조건

- 완료: 신규 테스트 전부 통과 + §0.1 게이트 2종 통과(허용 목록 외 실패 0) + 한글 커밋.
- 중단: (a) `_make_provider_with_proxy` 외 기존 파일을 추가로 수정해야만 동작하는 설계가
  되는 경우(설계 재검토로 회귀), (b) 기존 테스트(특히
  `tests/unit/test_ga_loop.py`, `test_autopsy.py` 등 `_make_provider_with_proxy`를
  monkeypatch하는 테스트 22곳)가 깨지는 경우, (c) 허용 목록 외 게이트 실패.
- 예상 소요: 구현+테스트 2~4시간, 게이트 1회 ~15분.

---

## A2 — provider 상위 진입점 배선 (run_research_iteration(provider=))

### A2.1 현황 (실측)

- `cli/research_loop.py:2419` — `run_research_iteration(config, controller, *,
  provider=None)`. provider는 **`Callable[[list[dict]], str]`** (messages → 응답 텍스트,
  research_loop.py:211 주석 실측). `config.llm_candidate_pack_enabled=True` 이고
  provider 주입 시에만 팩 생산, 미주입/실패는 결정론 폴백(credit 0) 자연 낙하
  (`_apply_llm_candidate_pack`, research_loop.py:1421-1481).
- `cli/ai_controller.py:800-819` `research_strategy_once` — config_dict를
  `allowed_fields`(ResearchLoopConfig 필드명)로 필터한 뒤 `:816`에서
  `run_research_iteration(config, self)` 호출 — **provider 전달 없음**.
- `cli/research_optimizer.py:424` `run_wide_v2_optimizer(..., research_runner=
  run_research_iteration)` — 라운드마다 `:457` `research_runner(round_config,
  controller)` 호출 — **provider 전달 없음**.

### A2.2 provider 팩토리 해석 규칙 (신규 파일)

`cli/research_provider.py` (신규):

```python
def resolve_llm_pack_provider(spec) -> tuple[callable | None, callable]:
    """spec(None|str)을 (provider_callable, cleanup)으로 해석한다."""
```

- `spec is None` 또는 빈 문자열 → `(None, no-op cleanup)` — **기본 불변**.
- `spec in {"openrouter", "codex_proxy"}` →
  `ai_strategy_loop.provider.factory.make_provider`로 인스턴스 생성 후
  `lambda messages: p.chat(messages).text` 어댑터 반환(연구 루프 계약이 str이므로
  `ChatResult.text`로 변환 필수). cleanup은 no-op.
- `spec == "gpt_auth"` → `ai_strategy_loop.provider.chatgpt_oauth`의
  `inject_env()/start_proxy_sync()` 선기동, cleanup에서 `stop_proxy_sync()/clear_env()`
  (`controller/loop.py:2660-2692` `_make_provider_with_proxy`/`_stop_proxy` 패턴 준수).
  프록시 시작 실패 시 `(None, no-op)` 반환 + 사유 로그(정직 폴백 — 연구 루프의
  결정론 폴백이 자연 발동, 예외로 iteration을 죽이지 않는다).
- A1 완료 후에는 여기서도 `FailoverProvider`로 감싼 뒤 어댑터를 씌운다(선택 보강 —
  A1 미완료여도 A2는 독립 동작).
- 미지 spec → `ValueError` (fail-closed, 조용한 무시 금지).

### A2.3 배선 지점 2곳 (기존 파일 최소 diff)

1. `cli/ai_controller.py` `research_strategy_once` (`:800` 부근):
   - `allowed_fields` 필터 **전에** `provider_spec = config_dict.pop('llm_pack_provider',
     None)` 으로 예약 키를 분리한다(ResearchLoopConfig 필드가 아니므로 필터에서
     어차피 탈락하는 키를 명시 계약으로 승격 — dict는 불변 패턴 `{k: v for ...}` 유지).
   - `config.run_candidates` 참일 때만 `resolve_llm_pack_provider(provider_spec)` 호출,
     `run_research_iteration(config, self, provider=provider)` 전달, `finally`에서
     cleanup 호출.
   - `run_research_once` 경로(`:817`)는 provider 파라미터가 없으므로 **무변경**.
2. `cli/research_optimizer.py` `run_wide_v2_optimizer` (`:421-424`):
   - 키워드 전용 인자 `provider=None` 추가(기본 None — 기존 호출부 전원 무영향).
   - `provider is not None`이고 `research_runner`가 기본값
     `run_research_iteration`일 때만
     `research_runner = functools.partial(run_research_iteration, provider=provider)`
     로 치환. 사용자 지정 runner가 주입된 경우 provider를 조용히 붙이지 않는다
     (주입 runner의 시그니처를 모름 — 명시 우선).

### A2.4 테스트 요구 (신규 `tests/unit/test_research_provider_entrypoints.py`)

1. `resolve_llm_pack_provider(None)` → `(None, cleanup)` , cleanup 호출 무해.
2. `"openrouter"` → callable 반환, mock provider의 `chat`이 호출되고 반환값이
   `ChatResult.text`의 str임(monkeypatch로 factory 대체).
3. 미지 spec → `ValueError`.
4. `research_strategy_once({... 'llm_pack_provider': 'openrouter',
   'run_candidates': True ...})` — `run_research_iteration`을 monkeypatch해
   `provider` 키워드가 not None으로 전달됨을 검증. `llm_pack_provider` 미지정 시
   `provider=None` 전달(기본 불변) 검증.
5. `run_wide_v2_optimizer(..., provider=<sentinel>)` — runner 호출 시
   run_research_iteration에 sentinel이 도달함을 검증(monkeypatch). `provider=None`
   기본 경로는 기존과 동일 호출임을 검증.
6. gpt_auth 경로: `start_proxy_sync` monkeypatch False → `(None, no-op)` 정직 폴백.

자기 테스트: `PYTHONUTF8=1 python -m pytest tests/unit/test_research_provider_entrypoints.py -q`

### A2.5 완료 기준 / 중단 조건

- 완료: 신규 테스트 통과 + `tests/unit/test_research_loop*.py`·
  `tests/unit/test_research_optimizer*.py` 기존 계약 무손상 + §0.1 게이트 2종 통과 +
  한글 커밋. 배선 후에도 `llm_candidate_pack_enabled=False`(기본)면 provider가
  주입돼도 팩 생산이 시도되지 않음(연구 루프 기존 계약)을 확인.
- 중단: (a) allowed_fields 필터 계약을 바꿔야 하는 설계(금지 — pop 방식 유지),
  (b) run_research_once 쪽까지 시그니처 변경이 필요해지는 경우, (c) 허용 목록 외
  게이트 실패.
- 예상 소요: 2~4시간.

---

## A3 — 승격 슬리피지 게이트 실배선 (**사용자 승인 선행 필수**)

### A3.1 승인 게이트 (최우선 규칙)

이 항목은 **사용자의 명시적 승인 없이는 코드 1줄도 수정하지 않는다.**
근거: 07-02 구현 기록 이월 4번 — "promotion-review 파이프라인 연결은 별도 승인
사항(zero-generation 계약)". promotion-review 프리셋은 `can_promote / can_export /
generation_allowed = False`가 계약이며(`ai_strategy_loop/portfolio/
promotion_preconditions.py:367-384` `_zero_generation_contract`, can_promote 항상
False), 게이트 배선이 이 계약을 흔들 여지가 있어 사용자 판단이 선행돼야 한다.

**승인 전 금지 사항** (전부 위반 = 즉시 중단·보고):

- promotion/승격/export 관련 어떤 파일도 수정 금지.
- `evaluate_slippage_gate` 판정을 승격·선택·동결 결정에 사용하는 코드/스크립트 작성 금지
  (advisory 리포트 출력도 승인 전에는 금지 — 판정 함수 호출 자체가 흐름 배선으로
  오인될 수 있다).
- "임시" 토글·환경변수로 우회 배선 금지.

### A3.2 승인 후 연결 지점 (설계 메모 — 실행은 승인 후)

이미 존재하는 부품 (전부 순수 함수 / 무배선 상태, 실측):

- 판정 함수: `ai_strategy_loop/controller/condition_discovery.py:347`
  `evaluate_slippage_gate(preset, slippage_profiles)` — promotion 프리셋
  `slippage_gate_profile='tick2'`, `total_profit > 0` 필수, evidence 부재/프로파일
  누락/비유한수 = **fail-closed 실패**.
- 5체크 집계: `ai_strategy_loop/portfolio/promotion_preconditions.py:386`
  `evaluate_promotion_preconditions(candidate_evidence)` — 1번 체크
  `check_slippage_gate`(`:140`)가 이미 `evaluate_slippage_gate`를 소비. 전부 통과여도
  `can_promote=False` 고정.
- 증거 생산: `cli/research_loop.py`의 `slippage_profiles_enabled=True` opt-in이 후보
  결과에 `slippage_profiles`를 additive 기록(T0.2b).

승인 후 배선 내용: promotion-review 레인(process 3, `condition_discovery_process=
'promotion-review'`)의 검토 산출물에 `evaluate_promotion_preconditions` 결과
dict(슬리피지 verdict 포함)를 **읽기 전용 리포트 필드로만** 포함한다. 배선 후에도
`can_promote`는 False 고정(zero-generation 불변)이며, 게이트 실패는 "승격 불가 사유
기록"일 뿐 어떤 자동 액션도 트리거하지 않는다. 신규 테스트는
`tests/unit/test_promotion_preconditions.py`의 기존 계약(전부 통과여도 can_promote
False)을 재확인하는 배선 테스트를 추가한다.

### A3.3 완료 기준 / 중단 조건

- 완료(승인 후): 리포트 필드 배선 + can_promote False 불변 테스트 + §0.1 게이트 통과 +
  한글 커밋. 승인 전 상태에서는 "이 문서의 §A3.1 준수 확인"이 곧 완료다.
- 중단: 사용자 승인 부재(기본 상태), 또는 배선 중 can_promote/export 경로에 True를
  낼 수 있는 어떤 조건 분기라도 필요해지는 경우(설계 자체를 사용자에게 회귀 보고).

---

## 공통 마무리 절차 (A1/A2 각 커밋마다)

1. `PYTHONUTF8=1 python -m pytest tests/unit/<신규 테스트 파일> -q` (자기 테스트)
2. `PYTHONUTF8=1 python -m pytest tests/unit/ -q` (전체 게이트 — §0.2 허용 목록 대조)
3. `python scripts/verify_nonrelease_sync.py`
4. 한글 커밋 (예: `연구 레인 provider 폴백 래퍼 및 상위 진입점 배선`)
5. `docs/update_log/2026-MM-DD_deferred_code_tasks_execution_log.md` 신규 작성 —
   커밋 해시, 게이트 결과(통과 수/실패 목록), 허용 목록 대조 결과를 기록.
