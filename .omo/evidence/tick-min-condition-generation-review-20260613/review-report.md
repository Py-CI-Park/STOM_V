# Tick/Min Condition Generation Review

## 현재 판정

조건식 생성 기능은 "배선과 후보 생성 준비" 기준으로는 부분 작동한다. 그러나 "tick/min 데이터를 이용해 수익 후보를 안정적으로 생성한다"는 기준으로는 아직 완성이라고 볼 수 없다.

Four-status answer:

| status | verdict |
|---|---|
| config/prompt works | tick late는 대부분 작동. min full-session은 데이터 창 배선은 작동하지만 프롬프트 가이드는 부족. |
| template generation works | tick 09:20~09:25 and min 09:00~15:00 TMAP templates render/validate. |
| actual profitable generation not proven | tick TMAP has promising evidence; new LLM late-tick and min full-session profitable generation are not proven. |
| OOS robustness pending | THETA and T2C3 have useful evidence, but min full-session and new LLM candidates lack promotion-grade OOS/WF proof. |

## 달성률

| area | score | short reason |
|---|---:|---|
| config wiring | 88 | Required fields and presets exist. |
| prompt generation | 74 | Tick time-cap guidance exists; min full-session guidance is incomplete. |
| template generation | 84 | Both tick/min templates validate. |
| variable scope safety | 86 | Timeframe-specific tests pass. |
| warm backtest data window | 82 | Min full-session end time opens to 15:00. |
| targeted unit tests | 90 | 68 targeted tests pass. |
| real tick sweep evidence | 68 | T2C3 has positive evidence, but exact late-window attribution remains. |
| real min sweep evidence | 35 | Min smoke runs execute but are negative/gate false. |
| OOS/WF robustness | 56 | THETA/T2C3 useful; min and LLM targets pending. |
| full-day time coverage | 48 | Min can express 09:00~15:00 but lacks band evidence. |

Overall evidence-weighted completion: 60/100. Infrastructure readiness: 82/100. Profitable generation readiness: 49/100. Full-time condition generation readiness: 46/100.

## 작동하는 것

- Tick LLM path: `time_cap_bucket_generation_enabled` and `time_cap_bucket_end_time=93000` inject 09:20~09:30 bucket guidance, including 09:20~09:25.
- Tick TMAP path: `tick_late_0920_0925_continuation.json` can create valid 09:20~09:25 candidates.
- Min data-window path: `full_session_enabled=True` with `bt_timeframe=min` opens warm backtest end time to `bt_min_universe_end_time=150000`.
- Min TMAP path: `min_session_0900_1500_rotation.json` can create valid min candidates through 15:00.
- Tests: 68 targeted tests pass for config, prompt, template, scope, and warm-window contracts.

## 부족한 것

- LLM output quality proof: no current run proves late-tick or min-full LLM generation creates profitable candidates.
- Min full-session guidance: prompt wording still centers on opening-session ranges, not 09:00~15:00 time bands.
- Min primitive evidence: M1 6-primitives x time-band map is missing.
- Command contract: roadmap `tmap_sweep` examples use unsupported `--out-prefix`.
- Evidence-path contract: `wf_t2c3_aggregate.json` exists as a sibling aggregate, while `wf_t2c3_20260613/aggregate.json` is absent.
- Promotion proof: new targets need 2-quarter smoke, full train sweep, fixed OOS, and canonical WF aggregate.

## 전체 시간

For tick, the hard data boundary is 09:00~09:30. The late-tick request is narrower: 09:20~09:25 should be evaluated separately from THETA and earlier seed-family windows.

For min, the intended operating day is 09:00~15:00, but current evidence only proves that the system can express and load the range. A full-time condition requires band-level evidence:

| band | required next proof |
|---|---|
| 09:00~10:00 | opening continuation vs overfire |
| 10:00~11:30 | morning continuation profile |
| 11:30~13:00 | lunch liquidity and false-break profile |
| 13:00~14:50 | afternoon trend/rotation profile |
| 14:50~15:00 | close-risk and forced-exit profile |

## Evidence Map

- Strong contract evidence: config fields, presets, `_generate_pair` forwarding, template validation, variable scope tests, warm-window tests.
- Promising tick runtime evidence: T2 corner train log and sibling T2C3 WF aggregate.
- Weak min runtime evidence: min smoke logs execute but are negative.
- Current champion context: THETA remains the usable baseline; it is not proof that new 09:20~09:25 discovery is complete.

## Next Development Sequence

1. Fix command contract documentation/examples in a later implementation pass.
2. Create canonical evidence config files outside `ai_strategy_loop/state` for smoke runs.
3. Run exact tick late 2-quarter smoke.
4. Build min M1 primitive map before any broad min LLM generation.
5. Add min full-session prompt-band guidance.
6. Run bounded TMAP sweeps only after smoke gates.
7. Freeze candidates only with predeclared acceptance criteria.
8. Run OOS/WF only after freeze, with canonical aggregate paths.

No source, test, runtime DB, or roadmap document updates were performed by this review.

