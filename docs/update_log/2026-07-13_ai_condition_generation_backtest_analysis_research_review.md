# 2026-07-13 AI 조건식 생성·백테스트 분석 심층 검토 및 잔여 개발 계획

> 브랜치: `feature/loop-remaining-research-plan-20260713`
>
> 기준 시작점: `cbea53c2` (`feature/loop-visual-and-quant-deepening-20260712`의 G1~G5 결과 보고서 포함)
>
> 범위: 조건식 생성 → 공식 STOM 백테스트 → 채점 → per-trade 분석 → 다음 프롬프트 환류 → 검증 증거.
>
> 전제: 현존 데이터만 사용한다. 신규 데이터 추가·수집·기간 연장은 오너의 별도 결정 전까지 보류한다. CL-R08~R10은 정확한 승인 문구 없이 실행하지 않는다. 전역 기능 기본값 OFF와 보호 DB 읽기 전용 원칙을 유지한다.
>
> 이번 작업에서 실행하지 않은 것: provider 호출, 조건식 신규 생성, 공식 백테스트, runtime DB 쓰기, CL-R08~R10, export/live.

---

## 1. 결론

### 1.1 최종 판정

**Architecture Status: BLOCK — 다음 수익 검증을 실행하기 전에 코드·증거·통계 계약을 먼저 교정해야 한다.**

G1~G5와 기존 CL-R01~R07은 기능 개발과 제한 프로세스 증명 측면에서 유효하다. 그러나 현재 정본 루프는 다음 문제 때문에 “AI가 데이터를 분석해 조건식을 지속적으로 개선했고 그 효과를 재현 가능하게 증명한다”는 목표에 아직 도달하지 못한다.

1. `research_presets.py`의 `min_full_0900_1500` 이름과 실제 `run_loop` 실행 시간창이 불일치할 수 있다. 현재 설정 조합은 실효 경로에서 15:00이 아니라 09:28로 남는다.
2. G1의 전체 Context Pack·복합 예제·repair/discovery 후보팩과 실제 `run_loop → generate_strategy → build_messages` 정본 생성 경로가 분리돼 있다.
3. seed 설정 일부와 `temperature`, `max_tokens`, `feedback_window`가 UI·config에 존재하지만 실제 생성 동작을 제어하지 않는다.
4. 세대 간 semantic dedup이 유지되지 않고 기본 hill-climb가 한 시드 주변 1~2개 조건 변경에 고착된다.
5. 증거 원장은 실제 prompt ID가 아닌 합성 ID로 소비를 기록할 수 있고, 여러 미소비 envelope 중 렌더하지 않은 항목까지 소비됐다고 기록할 수 있다.
6. EvaluationManifest의 `cost`와 `fill`이 실제 거래비용·체결 모델이 아니라 각각 MDD cap과 engine count를 담는다. 동일 조건 비교를 증명할 수 없다.
7. 채점의 `compute_uptrend_r2`는 하락 직선도 R²=1로 계산한다. 양의 총손익만 남은 지속 하락 곡선이 “우상향” 고득점을 받을 수 있다.
8. `trade_quant`의 최대낙폭은 첫 거래 손실을 누락하고, 시간대·B_* top 결론은 다중검정·표본 기준 없이 가장 큰 값만 고른다.
9. PBO/DSR은 “미구현”이 아니다. 이미 두 구현이 존재하지만 정본 루프·후보 선택·증거 계약에 통합되지 않았고 정의도 서로 다르다.
10. CL-R09는 현재 데이터 정책과 양립하지 않는다. 기존 DB는 2026-02-27까지지만 CL-R09는 2026-07-11 이후 20거래일 prospective OOS를 요구한다.

따라서 현재 상태는 다음과 같이 분리 보고해야 한다.

| 주장 | 현재 상태 | 판정 |
|---|---|---|
| `system_built` | G1~G5와 CL-R01~R07 기능 존재 | **true** |
| `learning_proved` | 격리 CL-R07 run#6의 `GO_PROCESS_PROOF` 기록 | **기록상 true, 이번 검토에서는 재증명하지 않음** |
| `performance_proved` | CL-R08 미실행 | **false** |
| `human_comparison_proved` | CL-R09/R10 미실행·동일 cohort 미동결 | **false** |
| `live_authorized` | export/live 승인 없음 | **false** |

### 1.2 이전 보고서에서 정정할 내용

#### 정정 A — Deflated Sharpe/PBO

이전 완료 보고서는 Deflated Sharpe/PBO를 “미구현”으로 기록했다. 재검 결과:

- `ai_strategy_loop/fitness/overfit_stats.py`에 daily PBO(CSCV)와 확률형 DSR이 구현돼 있다.
- `ai_strategy_loop/fitness/promotion_diagnostics.py`에 월별 PBO와 별도 DSR형 점수가 또 구현돼 있다.
- 실제 정본 선택·승격 소비자는 없고 과거 `.omo/evidence/.../select_and_freeze.py`가 일회성 산출물로 소비했다.
- 스코어카드는 `fitness/score.py`만 검사하므로 구현을 놓쳤다.

정확한 문제는 **미구현이 아니라 중복 구현·정본 부재·실행 경로 미배선**이다.

#### 정정 B — 정본 프로파일 18/20

스코어카드는 `_COMMON_DISCOVERY`만 검사해 `few_shot_enabled`와 `require_filter_gates`를 누락으로 판정한다. 실제 두 프리셋은 각 함수에서 두 값을 모두 `True`로 덮어쓴다. 따라서 18/20은 실효 설정 판정이 아니라 소스 배치 위치 판정이다.

반대로 더 중요한 값인 `condition_discovery_process="process-research"`, `condition_discovery_preset="research"`, `equity_points_enabled=True`는 정본 프리셋에 없다. 현재 77/100은 구성요소 존재를 보는 advisory 재고 점수이며, end-to-end 목표 준비도를 나타내지 않는다.

#### 정정 C — A-4의 P0 분류

A-4 매도 ablation은 실 provider와 공식 STOM 평가를 사용하므로 단순 승인 불필요 P0 실행으로 보면 안 된다. 기존 동결 R08 후보 슬롯이나 CL-R08 승인 범위에 사후 포함하지 않는다. 필요성이 유지되면 정본 planner가 별도 canonical amendment·권한·예산을 정의해야 하며, 그 전에는 가설·fixture 설계만 가능하다.

완료된 CL-R07 승인을 재사용해 새로운 결과-보유 실험을 실행하면 안 된다.

#### 정정 D — 완료 단계 사후 교정의 권한

아래에서 발견한 결함 일부는 완료된 CL-R02~R06의 계약·배선과 겹친다. 이 보고서는 지원 연구 문서이므로 완료 단계를 재개하거나 정본 상태기계에 새 단계를 만들 권한이 없다. 후속 코드는 먼저 정본 master/state-machine의 **versioned post-completion defect-remediation amendment**에서 다음을 확정한 뒤에만 변경한다.

- 기존 CL-R01~R07 receipt 보존·무효화·재검증 범위
- schema migration과 하위호환
- 코드 변경 권한과 검증 경계
- 기존 승인 문구·receipt 재사용 금지
- 결과-보유 runtime 재실행 여부와 별도 권한

이 보고서의 `DR-*`는 canonical phase가 아닌 backlog 식별자다.

---

## 2. 검토 범위와 직접 근거

| 영역 | 직접 검토한 파일·상태 |
|---|---|
| 정본 설계 | `2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md`, `lattice_v3_design_spec_20260709.md`, `lattice_v3_evaluation_protocol_20260709.md` |
| 생성 | `brain/prompt.py`, `brain/generator.py`, `brain/pack_producer.py`, `controller/context_pack_builder.py`, `controller/loop.py`, `config.py` |
| 프리셋 | `scripts/research_presets.py`, `launch_config.py`, `condition_discovery.py`, 관련 테스트 |
| 분석 | `autopsy/trade_quant.py`, `autopsy/analysis_card.py`, `autopsy/ablation.py`, 기존 segment/feature/edge 경로 |
| 채점 | `fitness/score.py`, `fitness/overfit_stats.py`, `fitness/promotion_diagnostics.py` |
| 증거 | `controller/evidence_store.py`, `controller/state.py`, `controller/evidence_contract.py`, loop evidence wiring |
| 공식 실행 | `controller/loop.py::run_backtest_for`, `cli/runner.py::_extract_metrics` |
| 상태 DB | `loop_runs.db`: runs 506, generations 5,124, prompts 460, equity_points 11,267, 증거 5개 테이블 0행 |
| 실 CSV 스모크 | G3 4,365거래: PF 0.55, 승률 33.7%, 최대연패 21, 손실 MAE 2.42배 |
| 독립 검토 | generation architect, backtest/analytics architect, research roadmap architect 3개 읽기 전용 검토 모두 `BLOCK` |
| 최종 계획 비평 | 1차 `REVISE` 4건을 DR/amendment·R08 동결 감사·CL-R07 근거 분리·train-only 환류로 교정 후 재비평 `APPROVE`, blocker 0 |

CL-R07의 `learning_proved` 근거는 일반 `loop_runs.db`가 아니라 `docs/update_log/2026-07-12_cl_r07_bounded_mini_loop_GO.md`의 격리 run#6이다. 해당 기록은 `GO_PROCESS_PROOF`, 26개 append-only evidence ID, feedback consumption 2건, 2×2 attribution, 공식 평가 9회를 보고한다. 이번 검토는 그 격리 artifact hash를 재검증하지 않았으므로 **기록상 true**로만 유지한다.

| 이번 EV finding | 일반 `run_loop` 영향 | 격리 CL-R07 run#6 영향 |
|---|---|---|
| 합성 prompt ID | 확인됨 | 별도 하네스라 영향 여부 미검증 |
| 미렌더 envelope 과잉 소비 | 확인됨 | 영향 여부 미검증 |
| evidence I/O fail-open | 확인됨 | 격리 receipt 완비 기록은 있으나 fault-path 영향 미검증 |

후속 remediation은 CL-R07을 자동 재실행하지 않는다. 먼저 기존 격리 artifact만 읽기 전용으로 재감사해 receipt 무결성과 finding 적용 여부를 판정한다.

현재 상태 DB 재확인:

| 항목 | 값 |
|---|---:|
| runs | 506 |
| generations | 5,124 |
| status ok | 4,897 |
| gate passed | 1,583 |
| profit positive | 1,782 |
| ok 세대 평균 MDD | 80.55% |
| prompts | 460 |
| candidate_passports | 0 |
| evaluation_manifests | 0 |
| feedback_envelopes | 0 |
| feedback_consumptions | 0 |
| run_receipts | 0 |

이 수치는 기능 존재와 실제 사용을 구분한다. 증거 스키마·프롬프트 로깅·분석 모듈은 존재하지만 정본 상태 DB에는 닫힌 학습 사슬 증거가 아직 없다.

### 2.1 순수 코드 재현 스모크

제품 코드·DB를 변경하지 않는 순수 호출로 핵심 결함을 재현했다.

| 재현 | 관측값 | 기대값 |
|---|---:|---:|
| `min_full_0900_1500 → config_from_dict → effective config` | preset=`fast`, process=`fast-discovery`, end=`92800`, equity_points=`False` | research process, end=`150000`, 필수 증거 영속 ON |
| `compute_uptrend_r2([50,40,30,20,10])` | `1.0` | `0.0` |
| `_drawdown_contributors([-100])` | 낙폭 `0` | `100` |
| `_drawdown_contributors([-100,-50])` | 낙폭 `50` | `150` |

이는 문서 추론만이 아니라 현재 브랜치 코드의 직접 재현 결과다.

---

## 3. 현재 프로세스의 실제 동작

### 3.1 실제 `run_loop` 경로

```text
LoopConfig 로드
  → condition-discovery 실효 정책 일부 적용
  → seed_buy + seed_sell이 있으면 gen-0 기존 시드 평가
  → gen-1+ 또는 fresh run에서 _generate_pair
      → build_messages
      → provider.chat
      → compile/token/variable/filter/exec/principle gate
      → loop_strategies.db 저장
  → 공식 stom_backtest.py 또는 warm session
  → CLI backtest.db 최신 결과 + per-trade CSV
  → compute_fitness + compute_graded_fitness
  → best/winner 갱신
  → buy/exit/segment/feature/hypothesis 분석
  → 자유 텍스트 피드백을 다음 build_messages에 주입
  → 다음 세대
```

AI의 실제 개입은 조건식 생성·게이트 재시도·다음 세대 프롬프트 해석이다. 공식 백테스트·채점·통계 계산은 코드가 수행한다.

### 3.2 별도 research 후보팩 경로

```text
cli.research_loop
  → Context Pack 조립
  → Analysis Card + coverage gap
  → pack_producer
  → repair 2 + discovery 2 후보
  → strict metadata/code 검증
  → research_candidate_pack
```

이 경로는 `run_loop`의 최종 계보 소유권과 직접 연결되지 않는다. `cli.research_loop` 자체 주석도 Context Pack이 단순 관측용일 수 있고 LLM 후보팩은 별도 옵션 경로라고 명시한다. 후보팩 생산 실패 시 결정론 폴백으로 조용히 내려갈 수 있다.

### 3.3 구조적 문제

정본 설계는 `run_loop`가 유일한 최종 계보 소유자라고 규정한다. 그러나 창의적 repair/discovery·coverage quota·전체 Context Pack은 별도 research lane에 있고, 실제 최종 owner는 기본적으로 단일 best hill-climb를 실행한다.

결과적으로 현재 시스템은 다음 두 시스템이 병존한다.

1. **실행 가능한 hill-climb:** 최종 owner이지만 국소 탐색·자유 텍스트 환류 중심.
2. **구조화된 다중가설 research pack:** 창의성과 근거 계약이 강하지만 최종 owner에 미통합.

가장 중요한 프로세스 개선은 기능을 더 추가하는 것이 아니라 **이 둘을 하나의 후보 제안 계약으로 합치는 것**이다.

---

## 4. 조건식 생성 심층 검토

### CG-01. 복합 예제는 정본 세대 프롬프트에 직접 들어가지 않는다 — HIGH

**근거**

- `_FULL_STOM_SOURCE_ASSETS`는 composite examples와 전체 원리 자산을 포함한다.
- `_build_system_message()`는 `_SYSTEM_ASSETS` 3종만 읽는다.
- `run_loop → generate_strategy → build_messages`는 축약 system message를 사용한다.
- 전체 Context Pack은 repair/discovery research prompt에만 사용된다.

**영향**

G1 자산의 존재·테스트 통과는 정본 hill-climb 세대에서 창의성이 실제 증가했다는 증거가 아니다.

**개선**

- 전체 250K pack을 매번 넣지 않는다.
- `PromptBundleRegistry`를 만들고 현재 slot·family·coverage gap에 필요한 구조 카드만 bounded selection한다.
- prompt bundle ID, 선택된 asset hash, 예제 ID를 PromptReceipt에 남긴다.

### CG-02. seed 설정이 실제 실행을 통제하지 않는다 — HIGH

**근거**

- config/UI에는 `seed_mode=fresh|manual_seed|best_refine`, `seed_source`가 있다.
- 실제 `run_loop`는 `gen_no == 0 and seed_buy and seed_sell`만 보고 시드를 사용한다.
- `seed_mode`와 `seed_source`는 검증·UI 외 실행 경로에서 소비되지 않는다.

**영향**

사용자는 fresh를 선택했다고 생각해도 seed 이름이 전달되면 시드가 평가될 수 있다. 시드 연구의 재현성과 설명 가능성이 깨진다.

**개선**

`SeedPlan`을 run 시작 시 한 번 동결한다.

```text
SeedPlan
- mode: fresh | manual_seed | best_refine | mixed
- source: passing | seed_db | manual | band | meta
- buy/sell body hash
- source DB/file hash
- selection rule
- selected_at_before_results
```

### CG-03. 세대 간 중복 방지가 사실상 없다 — HIGH

**근거**

- `_generate_pair`가 호출될 때마다 새 `DedupTracker(k=5)`를 만든다.
- 따라서 dedup 상태는 한 세대의 buy/sell 생성 뒤 사라진다.
- 기본 `bt_refine_from_best=True`이고 프롬프트는 1~2개 조건만 바꾸도록 강제한다.

**영향**

긴 run이 하나의 seed 주변에서 구조적으로 같은 후보를 반복하고, provider·공식 평가 예산을 낭비한다.

**개선**

- run-wide AST fingerprint archive.
- rowset fingerprint archive.
- family·time band·cap tier·regime coverage quota.
- `repair 2 + discovery 2` slot 계약을 최종 owner에 통합.
- 정적·행동 중복은 provider/backtest quota를 소비하지 않게 한다.

### CG-04. AND 강제와 OR 국면 분기가 충돌한다 — HIGH

**근거**

- composite examples는 OR 기반 국면 분기를 창의적 구조로 제공한다.
- 일반 프롬프트는 “OR 결합은 과발화”라고 광범위하게 금지한다.
- 필터 게이트는 전체 범주 수를 세지만 각 OR branch가 독립적으로 충분히 게이트됐는지 판정하지 않는다.

**영향**

안전한 `국면A OR 국면B` 구조까지 억제하거나, 반대로 한 branch만 느슨한 OR 우회를 놓칠 수 있다.

**개선**

- OR 자체를 금지하지 않는다.
- DNF/branch 단위로 각 진입 branch가 최소 필터 범주·유동성·시간창을 충족하는지 검사한다.
- 공통 precondition과 branch-specific event를 분리한다.

예시 계약:

```text
common_liquidity AND common_time AND (
  regime_breakout_filters
  OR regime_pullback_filters
)
```

각 OR branch는 독립적으로 실행 가능성과 과발화 위험을 검증한다.

### CG-05. 과거 실측 숫자가 cohort 없는 보편 진리로 프롬프트에 박혀 있다 — HIGH

**근거**

일반 매도 프롬프트는 give-back 70~88%, 손실 MAE 2.6배, MFE 실현 20%, 우수전략 18/19 등의 숫자를 현재 run의 manifest와 무관하게 상시 또는 토글로 주입한다.

**영향**

- tick/min, 시초/풀세션, 시총·레짐이 달라도 동일 처방을 강제한다.
- 과거 분석의 가설이 다음 데이터에서 사실처럼 자기강화된다.

**개선**

- 정적 prompt에는 원리만 둔다.
- 숫자는 current train manifest에서 재계산하고 sample size·기간·cohort·CI·source hash와 함께 주입한다.
- 표본 부족이면 숫자 처방을 생성하지 않는다.

### CG-06. band hint의 lookahead 경고만으로는 부족하다 — HIGH

밴드 힌트는 lookahead/survivorship 위험을 문장으로 경고하지만, 모델은 여전히 그 숫자를 본다. R08 후보에 쓰려면 train 40일과 train-only universe에서만 다시 채굴하고 manifest hash에 묶어야 한다. 기존 full/subset 채굴 밴드는 아이디어 카드로만 사용한다.

### CG-07. 샘플링·토큰·피드백 창 설정이 no-op이다 — MEDIUM

- `LoopConfig.temperature`, `max_tokens`가 `provider.chat(messages)`에 전달되지 않는다.
- gpt_auth translator는 해당 값을 지원하지 않는다.
- `feedback_window`는 실제 렌더 개수를 제어하지 않는다.

**개선**

- provider capability contract를 둔다.
- requested/effective/unsupported를 prompt receipt에 기록한다.
- 지원하지 않는 설정은 UI에서 효과가 있는 것처럼 보이지 않게 한다.

### CG-08. resume은 동일 실험을 재현하지 못한다 — HIGH

resume 시 복원되는 것은 `best_score`, `best_gen`뿐이다. 다음이 복원되지 않는다.

- best buy/sell 이름과 본문
- winner와 compare key
- base buy/sell code
- history summary
- segment avoid/feature hints
- pending/judged hypotheses
- MDD-only freeze 상태
- 모든 side의 pending feedback

재시작 후 refine이 fresh로 바뀌거나 이전 수렴 방향을 잃을 수 있다. 동일 run_id가 무중단 run과 다른 의미를 갖는다.

**개선**

세대 경계마다 versioned `EvolutionCheckpoint`를 남기고 다음 provider 호출 직전 상태를 완전 복원한다. checkpoint와 DB·전략 본문 hash가 다르면 동일 run을 계속하지 않는다.

### CG-09. AI 실패가 결정론 폴백으로 숨을 수 있다 — MEDIUM

research candidate pack 생산 실패가 `None`으로 흡수되면 기존 결정론 후보 생성으로 내려간다. 탐색 연속성에는 유용하지만 “AI 조건식 연구”의 효과 측정에는 부적합하다.

**개선**

실행 모드를 명확히 나눈다.

- `ai_required`: provider/pack/receipt 실패 시 해당 slot 실패, 결정론 대체 금지.
- `hybrid_allowed`: 폴백 허용, 후보에 `generation_origin=deterministic_fallback` 기록, AI 성과 집계에서 제외.
- `deterministic_control`: 음성 대조군.

---

## 5. 공식 백테스트·채점 심층 검토

### BT-01. min full-session 프리셋의 실효 시간창 불일치 — BLOCKER

**직접 코드 흐름**

1. `MIN_FULL_0900_1500`는 `bt_universe_end_time=92800`, `bt_min_universe_end_time=150000`, `full_session_enabled=True`를 설정한다.
2. 해당 프리셋은 `condition_discovery_preset="research"` 또는 process selector를 설정하지 않는다.
3. `effective_condition_discovery_runtime_config`는 preset이 research/promotion일 때만 `bt_universe_end_time`을 min full-session end로 바꾼다.
4. `run_backtest_for`는 명령행 `--end-time`에 `bt_universe_end_time`을 사용한다.

**판정**

현재 소스 계약대로면 “min 09:00~15:00” 프리셋이 09:28 종료로 실행될 수 있다. 기존 프리셋 테스트는 JSON에 `bt_min_universe_end_time=150000`이 있는지만 검사하고 실제 subprocess argv를 검증하지 않는다.

**개선·검증**

- 단일 effective profile resolver에서 process/preset/time window를 함께 고정한다.
- `preset_payload → config_from_dict → effective config → run_backtest argv` E2E 계약 테스트를 만든다.
- `--start-time 90000 --end-time 150000`이 아니면 min-full 연구 시작을 거부한다.

### BT-02. EvaluationManifest가 실제 비용·체결 계약을 담지 않는다 — BLOCKER

현재 manifest:

```text
capital = {universe_cap}
cost = {mdd_cap}
fill = {engine_count}
```

이는 정본 spec이 요구한 capital/cost/fill 의미가 아니다. 또한 manifest `data=timeframe`, `universe=scope`만으로 실제 DB hash, 날짜, 종목 집합, runner/engine code hash를 식별하지 못한다.

**필수 manifest v2**

- source DB path alias, SHA-256, byte size, schema fingerprint, read-only 상태
- 정확한 train/validation role, 날짜 목록 hash
- universe code list hash와 선택 규칙
- engine/runner commit·code hash
- betting·seed capital·동시보유 한도
- 수수료·세금·스프레드·슬리피지
- latency·volume participation·partial/rejected fill 규칙
- session start/end, timeframe, avg_time
- prompt bundle·SeedPlan·candidate pool hash

manifest가 없거나 결과가 manifest를 참조하지 않으면 certification run에 포함하지 않는다.

### BT-03. 우상향 R²가 하락 직선을 우상향으로 평가한다 — BLOCKER

`compute_uptrend_r2`는 `corr²`만 계산한다. 기울기의 부호를 버리므로:

```text
[50, 40, 30, 20, 10] → R² ≈ 1
```

총손익이 양수로 남아 있고 MDD cap을 통과하면 Calmar×R² 점수가 높아질 수 있다.

**수정 계약**

- regression slope `<= 0`이면 uptrend score 0.
- flat도 0.
- 상승 직선만 ≈1.
- `overfit_stats.curve_shape_metrics`와 정의를 단일 함수로 통일.
- 초기 급등 후 지속 하락·장기 정체 패턴을 별도 패널티로 측정.

### BT-04. gate-passed 후보 선택이 청산·분산 품질을 충분히 반영하지 않는다 — HIGH

기본 `winner_objective="risk_adjusted"`에서 hard gate 통과 후보끼리는 Calmar×R²가 핵심이다. exit-quality와 dispersion은 주로 gate 실패 분기의 선택 그래디언트에 들어간다. 청산 효율·종목 집중·tail loss가 좋아도 최종 winner 비교에서 직접 반영되지 않을 수 있다.

**개선**

하드 게이트는 그대로 두고, 통과 후보 선택 key를 사전등록된 다목적 lexicographic contract로 분리한다.

예:

```text
1) validation gate pass
2) cost-stress pass
3) worst-fold profit
4) MDD
5) net expectancy CI
6) Calmar/uptrend
```

결과를 본 뒤 가중치를 바꾸지 않는다.

### BT-05. 공식 지표 추출이 cohort 증거로 부족하다 — MEDIUM

`cli.runner._extract_metrics`는 거래수, 일평균, 승률, 평균/총수익, CAGR, MDD, TPI, 필요자금, 최대보유종목수, 평균보유기간을 반환한다. 그러나:

- `day_count`는 반올림된 일평균에서 역산한다.
- MDD amount는 0으로 고정된다.
- actual fee/fill/slippage 식별자는 없다.
- 결과 row가 어떤 manifest에서 나왔는지 FK가 없다.

정확한 거래일 목록·공식 MDD 금액·cost/fill 시나리오 ID를 결과 계약에 추가해야 한다.

### BT-06. 같은 CSV를 선택·부검·다음 변이에 반복 사용한다 — HIGH

한 CSV가 다음 역할을 동시에 수행한다.

- fitness와 best 선택
- buy/sell autopsy
- segment avoid
- feature prefer
- hypothesis 판정
- 다음 세대 부모 선택

이는 우연한 train 패턴을 부모와 프롬프트 양쪽에서 강화한다. `graduation_holdout`도 기본 OFF이며 same-CSV holdout은 정본 spec상 최종 OOS가 아니다.

**개선 역할 분리**

- optimization train: 분석·환류 전용
- validation: 후보 선택·정지 판단 전용, 프롬프트 입력 금지
- sealed OOS: 후보·설정 동결 후 1회 평가 전용

모든 FeedbackEnvelope에 `data_role=train`을 강제하고 validation/OOS hash가 prompt에 들어가면 실패 처리한다.

---

## 6. per-trade 데이터 분석 심층 검토

### QA-01. 최대낙폭이 첫 손실을 누락한다 — BLOCKER

`trade_quant._drawdown_contributors`는 누적합 뒤 바로 `cummax`를 계산한다. 시작 equity 0을 넣지 않으므로:

| 거래 PnL | 현재 계산 문제 | 올바른 최대낙폭 |
|---|---|---:|
| `[-100]` | 낙폭 없음으로 볼 수 있음 | 100 |
| `[-100, -50]` | 첫 -100 누락 | 150 |
| `[+100, -150]` | 정상 비교 가능 | 150 |

시작점 0 또는 시작자본을 prepend하고 index를 원 거래행에 다시 매핑해야 한다.

### QA-02. trade 순서를 검증·정렬하지 않는다 — HIGH

streak와 drawdown은 CSV 행 순서를 그대로 신뢰한다. 매도시간 기준 정렬 여부와 중복 trade ID를 확인하지 않는다. CSV 순서가 바뀌면 최대연패·낙폭 구간·기여 거래가 바뀐다.

**개선**

- `매도시간`, fallback `매수시간`, stable original row index로 정렬.
- 입력이 이미 정렬됐는지 `order_status` 기록.
- 중복·역전·파싱 실패 행 수 기록.

### QA-03. top 시간대와 top B_*가 선택편향을 만든다 — BLOCKER BEFORE AUTO-FEEDBACK

- 시간 버킷 중 total PnL 최대를 무조건 “최고”로 쓴다.
- B_* 중 |Cohen-like diff| 최대를 무조건 프롬프트 라인으로 쓴다.
- 최소 거래일·종목·효과 CI·FDR이 없다.

G3 실 스모크는 모든 시간대가 손실인데도 `1430`을 “누적손익 최고(-457,067원)”라고 출력했다. 상대적으로 덜 나쁜 구간이지 양의 edge가 아니다.

**자동 환류 허용 조건**

- `n_trades >= 30`
- `n_days >= 10`
- 복수 종목
- missing/excluded 비율 공개
- effect block-bootstrap CI가 0을 배제
- feature/bucket 탐색 BH q-value 기준 충족
- optimization-train 내부의 사전등록 inner split 또는 block-bootstrap에서 방향 재현

미충족 결과는 `descriptive_only`이며 dashboard에는 보여도 prompt directive로 만들지 않는다.

### QA-04. entry feature 분석 구현이 서로 다르다 — HIGH

- `analysis_card.py`는 기존 `analyze_trades`의 FDR 보정 Cohen’s d를 재사용한다.
- `trade_quant.py`는 별도 단순 평균차를 계산하고 FDR이 없다.
- 두 모듈이 서로 다른 top feature를 낼 수 있다.

**개선**

Analysis Card v3를 단일 구조화 결과로 만든다.

```text
AnalysisCardV3
- provenance/data role/source hash/order status
- official metrics
- trade distribution/streak/time/hold/MFE/MAE/drawdown
- segment/regime/symbol/day concentration
- FDR-corrected feature effects
- official 2x2/ablation evidence
- actionable directives[]
- descriptive findings[]
- insufficiency/error[]
```

대시보드, 프롬프트, 문서는 이 JSON의 서로 다른 renderer만 사용한다.

### QA-05. 중립 거래와 MFE 별칭이 채점에서 왜곡된다 — HIGH

`load_exit_quality_from_csv`는:

- `ret <= 0`을 전부 손실로 처리한다.
- 손실이 없으면 payoff를 999로 둔다.
- `R_MFE`만 인식한다.

반면 실 STOM CSV의 정본 이름은 `R_매수후최고수익률`일 수 있고 `trade_quant`는 두 별칭을 모두 처리한다. 0% 거래가 많으면 평균손실이 0에 가까워져 payoff가 과대평가될 수 있으며, MFE 컬럼을 놓치면 give-back이 조용히 사라진다.

**개선**

- win `>0`, loss `<0`, neutral `==0` 분리.
- neutral count/rate 별도 기록.
- 손실 표본 부족은 `insufficient`, 999 점수 금지.
- 공통 `TradeColumnContract`를 모든 분석기가 사용.

### QA-06. PBO/DSR 정본이 두 개다 — HIGH

| 구현 | 입력 | 의미 | 임계 |
|---|---|---|---|
| `overfit_stats.py` | 일별 손익 | CSCV PBO + 확률형 DSR | DSR 관례 0.95 |
| `promotion_diagnostics.py` | 월별 수익 | 단순 PBO + Sharpe haircut 값 | DSR형 값 >0 |

세 번째 구현을 `score.py`에 추가하면 안 된다. 후보 수·기간·trial count가 적은 R08에서 어떤 계약을 쓸지 사전등록해야 한다.

권고 정본:

- daily series 기반 `overfit_stats.py`를 기반으로 한다.
- 전체 생성·정적 거부·평가 후보의 trial accounting을 별도 원장에 기록한다.
- 후보 상관이 높으면 effective independent count와 PBO reliability warning을 함께 낸다.
- R08 hard gate에 넣을지 advisory로 둘지는 결과 보기 전 protocol amendment로만 결정한다.

### QA-07. 빠진 분석 축

현재 기능은 풍부하지만 다음은 승격 판단에 부족하다.

- 종목별·거래일별 손익 집중도
- 상위 1/5/10 거래 제거 민감도
- downside deviation, Sortino, Omega, CVaR/expected shortfall, tail ratio
- 거래당·일당 net expectancy CI
- 손익의 autocorrelation과 block length 근거
- 진입·청산 시간의 joint cell
- 포지션 중첩·자본 사용률·동시 손실 군집
- 거래대금 대비 주문 참여율·체결 가능 수량
- 수수료·세금·spread·slippage stress
- 시장방향·변동성·유동성·연도 regime별 worst-fold
- exit reason별 성과
- 데이터 결측·제외·중복·정렬 품질

모든 지표를 점수에 넣지 않는다. 분석 → 사전등록된 소수 decision feature → validation으로 역할을 분리한다.

---

## 7. 증거·환류 계약 심층 검토

### EV-01. 실제 prompt가 아닌 합성 prompt ID에 소비를 기록한다 — BLOCKER

- `prompts.prompt_id`는 SQLite INTEGER AUTOINCREMENT다.
- `record_prompt`는 ID를 반환하지 않는다.
- loop는 `promptrec_<run>_g<gen>` 문자열을 만들어 FeedbackConsumption에 기록한다.
- feedback_consumptions.prompt_id에는 prompts FK가 없다.

따라서 “이 피드백이 실제 이 프롬프트에 들어갔다”는 증명이 아니다.

### EV-02. 렌더하지 않은 envelope도 소비됐다고 기록할 수 있다 — BLOCKER

resume 시 모든 미소비 feedback ID를 모으지만 side별 첫 text만 복원한다. 이후 모든 ID에 consumption을 남긴다. 동일 side 다중 피드백이 있으면 일부는 prompt에 없는데도 소비 완료 처리된다.

### EV-03. certification 경로가 fail-open이다 — BLOCKER

passport, receipt, feedback, consumption append 실패와 unconsumed query 실패를 로그 후 흡수한다. 일반 탐색의 생존성에는 유용하지만 성능 증명 run에서는 원장 결손을 숨긴다.

### 개선 계약

```text
source CSV bytes hash
  → canonical AnalysisCardV3 hash
  → typed FeedbackEnvelope IDs
  → renderer returns actually_rendered_ids
  → persisted PromptArtifact ID + exact system/user hashes
  → FeedbackConsumption(actual prompt FK)
  → target CandidatePassport
  → official result + manifest ID
```

모드 분리:

- exploratory: evidence failure 허용 가능, `non_certifying=true`.
- certification/research: evidence I/O·hash·orphan 실패 시 `EVIDENCE_INVALID_STOP`.

완료 기준:

- 적격 run evidence 완비율 100%.
- orphan·dangling FK·미렌더 소비·합성 prompt ID 0.
- 1바이트 변경 시 hash 불일치.
- crash/resume 후 동일 prompt·parent·pending envelope 재현.

---

## 8. 목적 달성 관점의 재평가

기존 스코어카드 77/100은 파일·라우트·행수 중심의 **구성요소 재고 점수**다. 아래 평가는 이번 심층 검토의 goal-readiness 판단이며 공식 스코어카드를 대체하지 않는다.

| 단계 | 구성요소 존재 | 목적 달성 준비도 | 핵심 이유 |
|---|---:|---:|---|
| 데이터·공식 엔진 | 높음 | 65% | 기존 DB·공식 runner 존재, manifest/cost/fill 결박 미흡 |
| 시드 계획 | 중간 | 35% | 좋은 seed 자산 존재, seed_mode/source 실행 no-op |
| 프롬프트 지식 | 높음 | 60% | 자산 풍부, 정본 loop와 full bundle 분리·하드코딩 숫자 |
| 후보 다양성 | 중간 | 30% | 별도 pack은 우수, 최종 owner는 run-wide dedup/coverage 없음 |
| 기계 게이트 | 높음 | 85% | G2 오탐 0, OR branch 계약·엔진 AST 자동화 남음 |
| 공식 백테스트 실행 | 높음 | 65% | 엔진 경로 존재, min-full 시간창·manifest·비용 계약 문제 |
| 채점 | 중간 | 40% | graded 풍부, 하락 R² 결함·통과 후보 selection 부족 |
| per-trade 분석 | 높음 | 55% | 지표 풍부, 첫 손실 MDD·FDR·순서·provenance 문제 |
| 증거·환류 인과 | 중간 | 25% | 스키마 존재, 실제 행 0·합성 prompt ID·fail-open |
| 역사 validation | 설계 존재 | 0% | CL-R08 미실행 |
| prospective OOS | 계약 존재 | 0% | 데이터 정책과 R09 요구 불일치 |
| 인간 비교·live | 계약 존재 | 0% | R10/export/live 미승인 |

핵심 해석:

- “코드가 많다”와 “목적을 달성할 준비가 됐다” 사이에 큰 차이가 있다.
- 가장 부족한 부분은 UI가 아니라 **실효 프로파일·후보 다양성·정확한 통계·증거 인과·봉인 검증**이다.
- 수익 증명은 계속 0%로 유지한다.

---

## 9. 상세 잔여 개발 계획

### 9.1 선행 거버넌스 amendment — DR-00

`DR-*`는 canonical CL phase나 legacy P0 alias가 아니다. 완료된 CL-R01~R07의 post-completion defect-remediation backlog다. 구현 전에 정본 master/state-machine의 versioned amendment가 다음을 정의해야 한다.

1. 완료 receipt를 보존할지, 특정 claim만 보류할지, 어떤 부분을 artifact-only로 재검증할지.
2. schema v11 이후 migration과 기존 DB/receipt 호환성.
3. 코드·fixture 변경 권한과 결과-보유 provider/공식평가 권한의 분리.
4. defect remediation 뒤 R08 readiness를 재평가하는 방법.
5. 기존 CL 승인 문구와 receipt를 새 실행 권한으로 재사용하지 않는 규칙.

amendment가 없으면 아래 항목은 계획 상태에 머물며 제품 코드를 변경하지 않는다.

### 전체 의존성

```text
DR-00 정본 post-completion remediation amendment
  → DR-01 수학·CSV 계약 오류 교정
  → DR-02 단일 effective profile + manifest v2
  → DR-03 실제 prompt 기반 증거·resume 완결
  → DR-04 정본 후보 생성 통합(SeedPlan/repair/discovery/diversity)
  → DR-05 AnalysisCardV3 + trade_quant 통계 안전화
  → DR-06 기존 동결 R08 manifest/readiness 감사
  → R08_READY 또는 READINESS_BLOCKED/R08_CONTRACT_AMENDMENT_REQUIRED
  → HARD STOP
  → [정확한 CL-R08 승인] 제한 역사 validation
  → [데이터 정책 해소 + 정확한 CL-R09 승인] prospective OOS
  → [정확한 CL-R10 승인] 동일 cohort 인간 비교
```

DR-01~05는 validation-coupled다. 개별 구현은 분리할 수 있지만 최종 QA는 하나의 frozen profile·manifest·prompt·result·feedback 사슬로 함께 검증해야 한다.

### DR-01 — 수학·CSV 계약 오류 교정

**대상**

- `fitness/score.py`
- `autopsy/trade_quant.py`
- 공통 column resolver
- 관련 단위 테스트

**작업**

1. uptrend R²에 양의 slope 조건 추가.
2. trade_quant MDD 시작점 0 반영.
3. 거래 순서 정렬·검증.
4. win/loss/neutral 분리.
5. MFE/MAE 컬럼 별칭 단일화.
6. 음수뿐인 “best” 시간대를 actionable로 표현하지 않음.

**완료 기준**

- 하락·평탄 R²=0, 상승 직선≈1.
- `[-100]`, `[-100,-50]`, `[100,-150]` MDD=100/150/150.
- CSV 행 순열에 streak·MDD 결과 불변.
- 1승/1패/98중립 payoff가 1승/1패와 동일하고 neutral=98.
- `R_MFE`와 `R_매수후최고수익률` 결과 동일.

### DR-02 — 단일 effective research profile과 Manifest v2

**대상**

- `scripts/research_presets.py`
- `launch_config.py`
- `condition_discovery.py`
- `loop.py::run_backtest_for`, manifest builder

**작업**

1. profile 이름 하나가 CLI/UI/preset JSON에서 동일한 effective hash를 생성하게 한다.
2. min-full은 실제 argv가 09:00~15:00인지 검증한다.
3. research profile 필수값:
   - process-research/research policy
   - prompt logging
   - equity points
   - evidence ledger
   - 분석·환류 선택 토글
4. intentional OFF는 named ablation로만 허용하고 사유를 receipt에 기록한다.
5. Manifest v2에 데이터·유니버스·엔진·비용·체결·자본·session·prompt·seed hash를 넣는다.

**완료 기준**

- CLI/UI/preset script effective config hash 동일.
- min-full subprocess argv의 end-time 150000.
- manifest 누락·비용/체결 누락 시 certification 차단.
- global LoopConfig 기본값은 그대로 OFF.

### DR-03 — 증거 인과와 resume 완결

**대상**

- `state.py`
- `evidence_contract.py`
- `evidence_store.py`
- `generator.py` prompt callback
- `loop.py` evidence/resume 경로

**작업**

1. `record_prompt`가 실제 immutable prompt artifact ID를 반환.
2. PromptArtifact를 content-addressed화.
3. renderer가 실제 포함한 envelope ID를 반환.
4. consumption에 실제 prompt FK 적용.
5. certification profile에서 증거 실패 fail-closed.
6. EvolutionCheckpoint에 best/winner/base/history/hypothesis/feedback/coverage state 저장.

**완료 기준**

- source CSV→analysis→feedback→실제 prompt→passport→결과 단일 SQL/리플레이 가능.
- crash/resume와 무중단의 다음 prompt hash 동일.
- 미렌더 소비·orphan·중복 불일치 0.
- fault injection 시 GO receipt 미생성.

### DR-04 — 조건식 생성 파이프라인 통합

**대상**

- `brain/pack_producer.py`
- `brain/prompt.py`
- `brain/generator.py`
- `controller/loop.py`
- seed/coverage/fingerprint 모듈

**작업**

1. `CandidateProposalProvider` 경계 도입.
2. final owner가 bounded repair/discovery pack을 소비.
3. SeedPlan 동결.
4. run-wide AST/rowset dedup.
5. family/coverage quota.
6. bounded prompt bundle selection.
7. OR branch별 gate.
8. AI-required/hybrid/control origin 분리.
9. provider sampling capability receipt.

**완료 기준**

- 후보팩 4개 = repair 2 + discovery 2.
- family당 사전 quota, semantic/rowset duplicate 0.
- fresh는 seed 본문 소비 0.
- fallback 후보는 AI 성과 집계에서 제외.
- 최근 세대 동일 fingerprint 0.
- composite bundle ON/OFF가 prompt receipt에서 기계 식별 가능.

### DR-05 — AnalysisCardV3와 통계 안전한 자동 환류

**대상**

- `analysis_card.py`
- `trade_quant.py`
- segment/feature/edge/ablation 모듈
- FeedbackEnvelope renderer

**작업**

1. trade_quant를 별도 자유 JSON이 아닌 AnalysisCardV3 섹션으로 통합.
2. source CSV hash·data role·manifest·정렬·결측 품질 포함.
3. effect CI, n_days, n_symbols, n_trades.
4. BH-FDR 또는 사전등록 축만 actionable.
5. regime·symbol/day concentration·tail/capacity/cost stress 추가.
6. descriptive와 directive 분리.
7. row-based ablation은 근사임을 유지하고 실제 2x2 공식 평가 전 인과 주장 금지.

**완료 기준**

- null simulation 경험적 FDR≤5%.
- actionable directive는 최소 표본·CI·q-value·train-only 조건 100% 충족.
- dashboard/prompt/docs가 동일 card hash를 렌더.
- validation/OOS 데이터로 생성된 directive 0.
- official R08 validation/OOS hash가 train-role directive 입력에 포함된 건수 0.

### DR-06 — 기존 동결 R08 manifest/readiness 감사

실제 provider·공식 평가는 실행하지 않고, CL-R07 첫 결과 전에 동결된 기존 R08 preregistration과 상위 실행계획 todo 13/15를 읽기 전용으로 대조한다. 이 보고서가 새 후보·순위·tie rule을 만들거나 변경하지 않는다.

**동결 계약 대조 항목**

- 마지막 60 min 거래일: train 40 + validation 20.
- train-only top-20 universe.
- 후보 8개: repair 4 + discovery 4.
- family당 최대 2, semantic duplicate 0.
- 후보 동결 후 provider 호출 0.
- train 8회 전수 평가 후 기존 결정론 규칙으로 validation 최대 3회.
- 총 공식 평가 최대 11, wall 4시간.
- validation gate: 비용후 profit>0, MDD≤35, daily≥0.5, chronological half 각각 profit>0.
- 최종 survivor tie-break: validation worst-half profit → total profit → lower MDD → candidate ID.

**감사할 것**

- R08 manifest·후보 배분·순위·tie rule hash가 CL-R07 첫 결과 전에 존재했는지.
- 현재 정본 spec/evaluation protocol/상위 실행계획과 hash가 일치하는지.
- cost/fill 필드가 frozen 의미와 실제 실행 의미를 충분히 식별하는지.
- DSR/PBO 중복 계약이 기존 frozen R08 hard gate를 바꾸지 않는지.
- defect remediation이 기존 candidate/config/profile hash를 변경하는지.

**금지**

- A-4 또는 새 A/B arm을 R08 후보 슬롯에 사후 추가.
- validation 순위·대체·재시도 규칙 신규 작성.
- 결과를 본 뒤 prereg hash 교체.
- 기존 CL-R08 승인 문구에 별도 실험을 끼워 넣기.

기존 frozen 계약을 그대로 실행할 수 있으면 `R08_READY`, 결함 교정으로 hash·계약 변경이 필요하면 `R08_CONTRACT_AMENDMENT_REQUIRED`, 증거가 없거나 불일치하면 `READINESS_BLOCKED`다. amendment가 필요한 경우 이 지원 보고서에서 고치지 않고 정본 planner로 반환한다.

### CL-R08 — 정확 승인 후 제한 역사 validation

필요 문구:

`I approve CL-R08 bounded min performance only`

성공은 최소 1개 survivor가 정본 train/validation gate를 통과하는 것이다. 이것은 제한 역사 validation 증거이며 최종 OOS·인간 우위·live 증명이 아니다.

실패 전이:

- 결과 전 환경 실패: `ENVIRONMENT_BLOCKED`.
- 결과 보유 후 예산 초과: `no_go_budget_exhausted`.
- survivor 0: `NO_GO_STOP`, R09 잠금.

### CL-R09 — 현재 `BLOCKED_DATA_POLICY`

필요 문구:

`I approve CL-R09 sealed OOS/WF only`

그러나 승인만으로 실행할 수 없다. 현재 데이터는 2026-02-27까지이고 신규 데이터 추가는 보류다. R09는 2026-07-11 이후 20거래일 prospective DB를 요구한다.

재개 조건:

- 오너가 데이터 보류 정책을 별도로 해제.
- post-2026-07-11 20거래일 DB 존재.
- source SHA/size/read-only ACL.
- custodian 미접근 receipt.
- R08 survivor/config/profile/prereg hash 동결.
- 정확 승인 문구.

현 정책을 유지하면 `performance_proved`의 최종 prospective 단계는 계속 false다. 기존 데이터를 재분할해 R09라고 부르면 안 된다.

### CL-R10 — 인간 benchmark

필요 문구:

`I approve CL-R10 benchmark promotion review only`

사전 preflight만 준비한다.

- executable human buy/sell body와 hash.
- timeframe/period/universe/engine/methodology/capital/cost/fill/session 100% 일치.
- ranking formula와 tie rule 동결.

실행 본문이 없거나 cohort가 다르면 `not_comparable_missing_executable_reference`, `human_comparison_proved=false`다.

### 검증 임계경로 밖으로 이동할 작업

다음은 유용하지만 앞의 BLOCKER보다 후순위다.

- `/trade_quant`, `/research_maturity` V4 카드.
- 조건식 통합 카탈로그.
- sell scope engine AST 자동 추출.
- band direct compiler.
- alpha-lab intake.
- dashboard 시각 효과 추가.

UI는 저장된 증거를 그대로 렌더해야 하며 판정을 재계산하거나 승격할 수 없다.

---

## 10. 미래 A/B amendment 제안 — 동결 R08 범위 밖

### 10.1 목적

“프롬프트를 더 길게 만들었더니 좋아 보였다”가 아니라 어떤 요소가 후보 다양성·유효률·validation 성과를 바꿨는지 귀속한다.

### 10.2 독립 변수

한 번에 하나만 바꾼다.

1. composite structure bundle OFF/ON.
2. few-shot OFF/ON.
3. train-only band hint OFF/ON.
4. structured trade_quant feedback OFF/ON.
5. refine-only vs mixed repair/discovery.

### 10.3 고정 조건

- 같은 parent/SeedPlan.
- 같은 train manifest·universe·engine·cost/fill.
- 같은 provider/model capability.
- 같은 후보·token·wall budget.
- 같은 family quota.
- 결과 전 allocation과 stop rule 고정.

### 10.4 1차 지표

성능보다 먼저 과정 지표를 본다.

- valid code rate.
- gate reject reason distribution.
- unique AST fingerprint rate.
- unique rowset rate.
- family/coverage entropy.
- zero-trade rate.
- timeout rate.
- provider tokens per valid candidate.

### 10.5 2차 지표

optimization-train 내부의 사전등록 inner validation 또는 별도 미래 프로토콜에서만:

- parent 대비 net expectancy.
- worst-half profit.
- MDD.
- daily trades.
- cost-stress profit.
- effect CI.

### 10.6 중단 기준

- optional stopping 금지.
- inner validation 열람 후 prompt·threshold·candidate 교체 금지.
- gate 완화 금지.
- semantic duplicate는 평가 예산을 소비하지 않고 교체도 사전 규칙만 허용.
- 유효 후보 부족은 `INCONCLUSIVE`, 유리한 후보만 남겨 계속하지 않는다.

실 provider·공식 평가를 포함하는 A/B는 현재 동결 R08이나 기존 승인 문구에 포함하지 않는다. 필요성이 인정되면 정본 planner가 별도 canonical amendment·권한·예산을 정의해야 하며, 그 전에는 설계·합성 fixture만 허용한다.

---

## 11. defect-remediation 우선순위 요약

| 순위 | backlog | 작업 | 이유 | 선행 권한 |
|---:|---|---|---|---|
| 0 | DR-00 | 정본 post-completion amendment | 완료 단계 역행·receipt 재사용 방지 | 정본 planner/상태기계 amendment |
| 1 | DR-01 | 하락 R²·첫 손실 MDD·중립/MFE 별칭 | 현재 점수·분석이 틀릴 수 있음 | DR-00이 정의한 코드 권한 |
| 2 | DR-02 | min-full 실효 프로파일·Manifest v2 | 평가 조건 자체가 잘못 기록될 수 있음 | DR-00이 정의한 code/fixture 범위 |
| 3 | DR-03 | 실제 prompt ID 증거·resume | 학습 인과·재현이 거짓일 수 있음 | DR-00 + 기존 receipt 영향 감사 |
| 4 | DR-04 | final owner와 repair/discovery 통합 | 창의성·다양성 병목의 핵심 | DR-00 + frozen prereg 영향 판정 |
| 5 | DR-05 | AnalysisCardV3·FDR·CI·regime | 자동 환류 전에 통계 안전 필요 | DR-00이 정의한 code/fixture 범위 |
| 6 | DR-06 | 기존 동결 R08 readiness 감사 | 계약 변경 없이 실행 가능성 판정 | 읽기 전용 감사 |
| 7 | CL-R08 | 최초 제한 성능 검증 | 정확 문구 필요 | `R08_READY` + 정확 승인 |
| 8 | CL-R09 | prospective OOS | 데이터 정책 해제+정확 문구 필요 | R08 survivor + 데이터 |
| 9 | CL-R10 | 인간 동일 cohort 비교 | 정확 문구 필요 | GO_R10 |
| 10 | 후순위 | V4 상세 카드 | 관찰성 보강 | 검증 임계경로 아님 |

---

## 12. 금지·보류

### 계속 금지

- broad-grid 축 확장 재실행.
- 같은 seed 주변 무제한 미세변형.
- full-period winner를 OOS winner로 해석.
- 결과를 본 뒤 threshold·순위식·fold 변경.
- gate 완화로 통과율 높이기.
- 결정론 폴백 후보를 AI 생성 성과에 포함.
- 승인 없는 provider/공식 성능 평가·CL-R08~R10.
- export/live/V3K gate 우회.
- 보호 DB·결과 파일 수정.

### 오너 결정 전 보류

- 신규 데이터 수집·기간 연장.
- 외부 데이터 소스.
- CL-R09 prospective OOS 데이터 준비.
- 운영 DB 이관.

---

## 13. 보고서 완료 기준과 후속 인계 상태

이번 보고서는 다음을 완료했다.

- 새 잔여 작업 브랜치 생성.
- 기존 완료 범위와 미완료 범위 재분리.
- 조건식 생성 경로와 research 후보팩 경로의 분리 확인.
- 시드·샘플링·dedup·resume·프롬프트 자산의 실효성 검토.
- 공식 백테스트 argv·manifest·채점 수학 검토.
- trade_quant의 통계·회계·자동 환류 안전성 검토.
- 증거 원장의 실제 prompt 귀속과 fail-open 문제 확인.
- PBO/DSR 및 maturity scorecard의 이전 판정 정정.
- 데이터 정책과 CL-R09 계약 충돌 확인.
- 구현·사전등록·승인 단계의 의존성 계획 수립.
- 최종 critic 재비평 `APPROVE`, blocker 0.

인계 상태:

```text
branch_created = true
research_report_complete = true
code_changes_for_blockers = false
governance_amendment_required = true
remediation_code_authorized = false
R08_ready = false
CL_R08_authorized = false
CL_R09_data_available_under_policy = false
performance_proved = false
human_comparison_proved = false
live_authorized = false
```

한 문장 결론:

**조건식 자산과 분석 기능은 충분히 많지만, 현재 목적 달성의 병목은 정본 생성 경로의 국소 최적화, min-full 실효 설정, 잘못된 우상향·낙폭 계산, 통계 보정 없는 top 발견, 실제 prompt와 연결되지 않은 증거 원장, 비용·체결이 빠진 manifest다. 이 BLOCKER를 먼저 교정하고 사전등록을 동결한 뒤에만 CL-R08을 실행해야 한다.**
