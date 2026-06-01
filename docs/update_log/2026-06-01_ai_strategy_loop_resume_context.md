# AI 조건식 루프 — 세션 재개 컨텍스트 (2026-06-01)

> **목적**: 새 세션에서 곧바로 이어가기 위한 집중 재개 가이드.
> **단일 자급자족 상세본**: `docs/update_log/2026-05-28_ai_strategy_loop_R6_FULLUNIVERSE_HANDOFF.md` (§3.23이 최신).
> **브랜치**: `STOM_Version_2U_C-ai-strategy-loop` · **워크트리**: `C:/System_Trading/STOM/STOM_V.wt-dev`

---

## 0. 한 줄 현황

② 다년 학습 파이프라인 + 평가기준 정합 + **(A) 생성 품질 개선(과발화 차단 필터게이트)**까지 구현·검증·커밋 완료. **다음 = (A)로 잘 게이트된 생성물이 실제 백테에서 과발화 없이 흑자/시드급인지 짧은 백테로 확인.** (리부팅으로 RAM 정리됨 — 고아 프로세스 0.)

---

## 1. 이 작업 체인 커밋 (최신순)

| 커밋 | 내용 |
|------|------|
| `e333be18` | docs §3.23 ((A) 생성품질 기록) |
| `e16ab39e` | **feat(A)**: 필터범주 구조게이트 + 시드급 게이팅 프롬프트(과발화 방지) |
| `53c5e07e` | docs §3.22 (resume 실패 + 고아 OOM 인프라 교훈) |
| `c9e8fca8` | docs §3.22 (평가기준 정정 + 긴 run OOM + Phase E) |
| `51b35ffc` | **fix(②E)**: multiyear = '연도 균등성' → '다년 전구간 우상향', winner=graded |
| `ab0175ab` | feat(②D): launch_config 스키마 + docs §3.21 |
| `609bde6c` | feat(②C): 연도별 cross-tab 부검 + 시초 5분 + 분산 넛지 |
| `49db2288` | feat(②): winner_objective='multiyear' |
| `bed0a1d0` | feat(GUI): 웹 대시보드 프로세스 플로우 + 실시간 로그 |

baseline: **1856 passed / 7 failed**(기존 pre-existing, 신규 0) · 엔진/하드게이트 무수정 · 모든 신규기능 default-OFF 토글.

---

## 2. 핵심 결론 (지금까지 학습)

1. **AI refine는 인간 시드 Tick_902를 못 이긴다** — 다년/단기 모든 정직평가에서 시드 1등. 원인 = refine 과발화(진입 게이트 부실). 이게 핵심 미해결 연구질문(§3.16-D).
2. **시드는 견고한 다년 우상향** — 2023~25 +8.27M·r²0.90·MDD17.76%. 단일년(2025 MDD36%) 비관은 최악연도만 본 착시.
3. **평가기준(사용자 정정)** = "등락·기울기변동 있어도 다년 전구간 누적곡선이 장기 우상향" 하나. **매년 균등/일정기울기/매년흑자 요구 안 함**. → multiyear stability_term = clamp01(전구간 단일 누적곡선 우상향 R²), winner=graded (Phase E §3.22).
4. **정적 코드게이트로 "좋은 전략" 판별 불가**(R7.4·§3.14·§3.15). 단 "충분히 게이트됐나"(구조) 검사는 가능 → (A).
5. **(A) 생성품질 = 작동 실증** — 토글 ON 시 LLM이 매수 3/3 전부 1회만에 8개 필터범주(시드 9 근접) 생성. 과발화(1~2범주) → 시드급으로 개선(§3.23).

---

## 3. 🔴 다음 단계 (권장: (A) 짧은 백테 검증)

**열린 질문**: (A)로 잘 게이트된(범주≥5) 생성물이 실제 백테에서
- (a) 거래수가 bounded인가(과발화·크래시 안 함)?
- (b) 흑자·시드급 위험조정인가?

이건 백테가 필요한데, **3년 풀유니버스는 OOM**이므로 **소규모/단기**로 한다.

### 실행 명령 (require_filter_gates=ON, 짧은 run)
```bash
# 기존 multiyear config를 복제해 require_filter_gates 추가 + 기간 단축(예: 1개월) + max_gen 작게
# (config는 gitignored; ai_strategy_loop/state/ 에 새로 만든다)
# 예: run_filtergate_smoke_config.json = run_multiyear_long2_config.json 기반 +
#     "require_filter_gates": true, "min_filter_categories": 5,
#     "bt_full_start": 20250101, "bt_full_end": 20250131,  (1개월)
#     "max_generations": 4, "bt_warm_engine_count": 16

STOM_ALLOW_MINIMAL_SETTING=1 PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop \
  --config-json ai_strategy_loop/state/run_filtergate_smoke_config.json --run-id fg1
```
검증 포인트: 생성 세대들의 trade_count가 bounded(과발화 안 함)·타임아웃/크래시 감소·게이트 통과(흑자) 여부.

### ⚠️ 인프라 주의 (반드시 지킬 것)
- **3년 풀유니버스 단일 warm 세션은 ~5세대에서 OOM**(과발화 전략의 per-run 메모리 폭증). 크래시 시 **16개 엔진 자식이 고아로 남아 누적** → 다음 run 즉시 OOM.
- **크래시 후 반드시 정리**: `MSYS_NO_PATHCONV=1 taskkill /F /IM python.exe` (단 `python3.exe`는 보존). 리부팅도 정리됨.
- 그래서 검증은 **단기/소형 우선**, 3년 장기 진화 run은 회피(엔진측 거래수 캡/고아 정리 = 별도 보호영역 과제).

### 결과 분석 (백테 없이도 가능한 부분)
- `_temp_filtergate_gen.py`(gitignored): gpt_auth로 매수 생성 → `filter_gate.count_filter_categories`로 범주 수 확인(이미 8 실측).
- 연도별 안정 특성: `ai_strategy_loop.autopsy.analyze_segments_by_year`(C-1) — 시드 소형avoid/초소형prefer 3년 일관.

---

## 4. 대안 경로 (참고)

- **(B) 시드 감독형 배포**: 시드는 운영DB `_database/strategy.db`에 byte-동일 존재(메모리⑮·`2026-05-30_seed_tick902_supervised_deployment_plan.md`). 사람 감독 실매매 준비 = STOM GUI 운영백테 1회 + 소액 검증(사용자 수동).
- 대시보드 실시간 관찰: `python -m ai_strategy_loop` → `http://127.0.0.1:8770/ui/`. **단 3년 16엔진 run과 동시 구동은 메모리 압박**(저사양시 주의; 짧은 run엔 OK).

---

## 5. 재개 명령어 (compact 후 새 세션 첫 메시지로 복사)

```
ai_strategy_loop (A) 검증 이어가자. docs/update_log/2026-06-01_ai_strategy_loop_resume_context.md
+ docs/update_log/2026-05-28_..._HANDOFF.md(§3.23) 먼저 읽고, (A) require_filter_gates=ON으로
잘 게이트된 생성물이 짧은 백테(1개월/소형, 3년 OOM 회피)에서 (a)거래수 bounded·과발화 안 함
(b)흑자/시드급인지 검증. 크래시 시 taskkill /F /IM python.exe(python3.exe 보존)로 고아 정리.
신규기능 default-OFF·엔진 무수정·code-reviewer APPROVE·baseline 신규0 유지.
```

재개 시 MEMORY.md ⑳ + 위 두 문서 자동 로드 → 무중단.
