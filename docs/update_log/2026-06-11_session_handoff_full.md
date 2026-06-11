# 세션 핸드오프(전체) — 조건식 자율탐색 6/10~6/11 집중 개발 (2026-06-11)

> **이 문서 하나로 다음 세션(사람/에이전트)이 전체 맥락을 복원하고 즉시 재개할 수 있다.**
> 목표(불변): 시드 DB·연구 문서에서 출발해 **시간창과 매매 횟수를 최대로 늘려 최대
> 수익을 내는 조건식**을 만들고 → 백테스트로 검증하고 → 수익 모델을 확보한다.

---

## 1. 현재 도달점 한 줄

시스템(공장) ~92% 완성 — **TMAP(경향성 지도) 프로세스까지 가동**되어 첫 지도가
"시간 확대 축"(시드 905 창 09:05→09:07 = 수익 +61%·MDD −57%·거래 +58%)을 실증했다.
알파 트랙은 첫 OOS 흑자 후보(C7, 2022 +171만)와 다년 미검증 고원 후보(window_end·
cap_max)를 보유. **다음 행동 = W1 본 스윕**(아래 §4).

## 2. 이번 사이클 커밋 체인 (84acb6cb 이후 8커밋 — 전부 검증·클린)

| 커밋 | 내용 |
|---|---|
| `a9d5db1d` | 근본 원인 보고서(원인 6종) + zero-LLM 검증 사이클 증거 + v5.0 리포트 사본 |
| `488b71e8` | B군: seed_relative_v1 선택기·매도 계산예산 가드·v5 원리 프롬프트(+이월 정리) |
| `ef59c276` | C7 고정 OOS(2022 +1.71M/2026 −0.23M) + 결정 카드(REJECT — 최초 대형 OOS 흑자) |
| `1b8fc907` | C·D·E군: PBO/DSR + 대시보드 검증 뷰(연도분해·부검·선택기 미리보기) |
| `a5066254` | R1~R7: 분위수 임계·반사실 필터·블록 MC·gen 필터·플라시보·일별상관 |
| `e12f103a` | 전체 현황 문서(페이지 진행률·달성 가능성·로드맵) |
| `8c0a5520` | TMAP 프로세스 재설계 문서(템플릿×θ·고원·포트폴리오·전진분석) |
| `893cd77d` | **TMAP G1~G5 구현 + 첫 지도 실증** |

## 3. 시스템 자산 지도 (무엇이 어디에 있나)

### 3.1 TMAP (신규 핵심)
- `ai_strategy_loop/tmap/template.py` — θ 슬롯 템플릿 렌더러(identity 보증)
- `ai_strategy_loop/tmap/templates/seed_902905.json` — 시드 모수화 13θ
- `ai_strategy_loop/scripts/tmap_sweep.py` — 지형 스윕(prepare 1회+run N회)
- `ai_strategy_loop/tmap/tendency.py` + GET `/tmap_map` + Validation 탭 — 고원/절벽 지도
- `ai_strategy_loop/scripts/tmap_walkforward.py` — 전진분석 정책 드라이버(정책 v1)
- `ai_strategy_loop/tmap/portfolio.py` + GET `/portfolio_preview` — 저상관 결합

### 3.2 검증·분석 도구(기성)
- 선택기: `seed_relative_v1`(+sparse/yearly 병기) — `controller/candidate_selection.py`
- 과적합: `fitness/overfit_stats.py`(PBO/DSR/블록 MC/일별상관)
- 반사실: `fitness/counterfactual.py`(백테 0회 필터 검증) · 분위수 환류(autopsy R1)
- 플라시보: `scripts/gen_placebo_strategy.py`
- zero-LLM 평가: `scripts/claude_candidate_batch_eval.py`(pairs 배치)
- 동결/OOS 절차 스크립트: `.omo/evidence/claude-condition-research-20260610/`
  (select_and_freeze.py · gen_oos_configs.py · train/smoke/oos config JSON)
- 루프 신규 토글(기본 OFF): exec_budget_prompt/guard · report_principles ·
  quantile_feedback · counterfactual_feedback (launch_config/state 노출 완료)
- 대시보드: `python -m ai_strategy_loop --port 8770` — Validation 탭(연도분해·부검·
  반사실·MC 팬차트·선택기 미리보기·TMAP 지도), 분석 라우트 gen_no 필터

### 3.3 데이터 사실(실측)
- tick DB: 2022~2026 다년, 09:00~09:30 (다년 검증 축) — prepare 3년 279초/1년 107초
- min DB: **2025-04~2026-02(11개월)만** 풀세션 — 시간 확대 탐사용(다년 검증 불가 명시)
- 시드 라이브러리: loop_strategies.db 매수 452+·CLDGEN 19종·TMAP 변형들
- MDD% 정의: 낙폭금액/(피크누적수익+seed필요자금) — 분모가 동시보유 수에 비례(B2 감사)

## 4. "W1 본 스윕"이란 (다음 행동의 정확한 의미)

마이크로 스윕(2슬롯×2025Q1, 12포인트)으로 도구를 검증했으니, 이제 **본 스윕** =
**13개 슬롯 전체(56포인트)를 다년(2023~2025) train 데이터로** 돌려 정식 경향성 지도를
만드는 것이다. 단일 분기 지도는 인샘플 우연일 수 있으므로(2025Q1에서 cap 축소가
불리했지만 3년 반사실에선 유리했던 것처럼 구간별 경향이 다름), **다년 지도의 고원만**
동결·OOS 후보 자격을 갖는다.

```powershell
# W1-1. 본 스윕 (약 1.5~2시간 머신: prepare ~5분 + 56런×~90초)
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_sweep `
  --template seed_902905 `
  --config-json .omo/evidence/claude-condition-research-20260610/train-config.json `
  --run-id tmap_seed_full_train_20260611 `
  --manifest-out .omo/evidence/tmap-walkforward/full_train_manifest.json
# W1-2. 지도 열람: 대시보드 Validation 탭 'TMAP 지도' (run 셀렉터에서 위 run 선택)
#        또는 GET /tmap_map?run_id=tmap_seed_full_train_20260611
```

## 5. 목표 달성 트랙 (해야 하는 것 — 페이지 테이블)

| 페이지 | 단계 | 내용 | 도구 상태 | 예상 |
|---|---|---|---|---|
| A1 | **W1 본 스윕** | 13θ×56pt × 2023~2025 다년 지도(§4 명령) | ✅ 완비 | 1.5~2h 머신 |
| A2 | 고원 θ* 확정 | 다년 지도에서 슬롯별 고원 중심 + 상위 2~3 슬롯 **조합 점** 4~6개 추가 평가(배치도구 pairs) | ✅ 완비 | ~1h |
| A3 | 동결 재평가 run | BASE_SEED + θ* 후보들을 한 배치로 train 재평가 → `select_and_freeze.py <run_id>`로 seed_relative 동결 (스윕 run에는 BASE_ 라벨이 없으므로 **동결은 이 재평가 run에서** 한다 — 절차 주의) | ✅ 완비 | ~40m |
| A4 | 시간·횟수 확대 니치 | min 풀세션 템플릿 2종(오전 모멘텀·오후 되돌림) 신규 JSON 작성 → 지도 (코드 추가 불필요 — 템플릿 데이터만) | 템플릿 작성 필요 | W3 |
| A5 | 포트폴리오 조립 | 저상관 고원들 결합(/portfolio_preview → 채택 조합 실백테 확인) + 적응형 레짐타이밍 레이어 | ✅ 완비 | W3 |
| A6 | GPT 루프 합류 | 신규 토글 4종 ON 스모크 A/B → 루프가 템플릿 변이(구조 탐색) 담당 | ✅ 완비(GPT 충전 확인) | W4 |

## 6. 목표 달성 **검증** 트랙 (믿어도 되는지 — 페이지 테이블)

| 페이지 | 단계 | 내용 | 도구 상태 |
|---|---|---|---|
| V1 | 3중 분포검증 | 동결 시 자동: 블록 MC(P(흑자)·MDD 분포)/PBO(그리드=시도 집합)/DSR(n_trials=평가 수) — p5-overfit-advisory.json | ✅ select_and_freeze에 배선됨 |
| V2 | 플라시보 검정 | 동일 매도+무작위 진입 대비 초과 성과(`gen_placebo_strategy.py` → 배치 평가) | ✅ 완비(실전 1회 미실시) |
| V3 | **고정 OOS** | 2022/2026, 동일 창(93000), 시드 동시 재측정(`gen_oos_configs.py` → 배치) — 합격 규칙은 p0 정책 §5 | ✅ 완비(C7에서 1회 실증) |
| V4 | walk-forward 정책 | `tmap_walkforward.py --windows "20230101-20231231:20240101-20240630,..."` — 재적합 정책의 누적 OOS(시나리오 D) | ✅ 완비(다년 실가동 미실시) |
| V5 | 슬리피지 스트레스 | 승격 전 필수 advisory blocker — **도구 미구현(정직 공시)**, 수동 절차 또는 후속 빌드 | ⚠️ 미구현 |
| V6 | 결정 카드+운용 결정 | PROMOTE/REJECT/NEEDS_MORE + **사용자 결정점**(시드 대체 vs 보완 — 6/2 이래 미결) | 카드 양식 확립 |

정직성 불변식(전 단계): 엔진/하드게이트/backtest_graph 무수정 · OOS-blind 동결, 사후
재선택 금지 · 모든 지도/반사실/MC는 인샘플 advisory — 판정은 V3/V4 규율.

## 7. 다음 세션 재개 절차 (핸드오프)

1. **이 문서**를 읽는다 → 더 깊은 맥락이 필요하면 §8 문서 인덱스 순서로.
2. 상태 확인: `git log --oneline -8`(§2와 일치), `git status`(클린),
   `PYTHONUTF8=1 python -m pytest tests/unit/ -q`(기대: 실패 7건 고정 목록 외 전부 통과).
3. 대시보드: `PYTHONUTF8=1 python -m ai_strategy_loop --port 8770` → /health 200.
4. **W1 본 스윕 실행**(§4 명령) → A2~A3 → V1~V3 순서.
5. 주의: gpt_auth 사용 전 충전 상태 확인(6/11 10:00 충전 예정이었음). GPT 없이도
   A1~A5·V1~V4 전부 가능(zero-LLM 경로).

## 8. 문서 인덱스 (읽기 순서)
1. 본 문서 (재개 진입점)
2. `2026-06-11_tmap_process_redesign.md` — 현행 프로세스 설계+G1~G5 구현 기록(§7)
3. `2026-06-11_program_status_progress_and_roadmap.md` — 페이지 진행률·달성 가능성
4. `2026-06-10_condition_research_root_cause_and_plan.md` — 원인 6종·해결책·B~E군 기록
5. `2026-06-11_analysis_feedback_process_review.md` — 분석 환류 검토·R1~R7 기록
6. `docs/research/condition_research/2026-06-10_measurement_calibration_audit.md` — MDD 정의
7. 증거: `.omo/evidence/claude-condition-research-20260610/`(동결·OOS·결정 카드),
   `.omo/evidence/tmap-walkforward/`(첫 지도)
8. 영구 메모리: stom-tick-engine-compute-budget · stom-zero-llm-eval-path

## 9. W1 진행 추록 (2026-06-11 12시 — 중단·복구 기록)

핸드오프(`b6a3af45`) 이후 같은 날 진행된 작업과 중단 사건:

- 후속 커밋 2건: `dc36dbcb`(V5 슬리피지 스트레스 advisory 도구 — §6 V5 갭 해소,
  CSV 후처리 시나리오 재계산·엔진 무수정·테스트 215줄) ·
  `16bc3e4d`(A4 니치 템플릿 2종 — min 풀세션 오전 모멘텀/오후 되돌림 θ 모수화).
- gpt_auth 충전 확인(PONG, 429 미발생) — `gpt_auth_health_20260611.txt`.
- **W1 본 스윕 착수 → gen14에서 프로세스 중단**(56포인트 중 15만 기록,
  gen14는 child exit 1 — 중단 여파, 전략 문제 아님). 부분 지도에서도
  cap_max 2000~2500 우세 고원(평균 8.88M > 베이스라인 8.63M) 신호.
- θ* dry-run: `gen_theta_star_batch.py` + `theta_star_summary.json` —
  단, **3/13 슬롯 부분 지도 기준이므로 본 스윕 완주 후 재산출 필요**.
- 복구: `tmap_sweep.py`에 `--resume` 추가(ok 세대 스킵·error/누락 재평가·
  라벨 불일치 시 재평가, `tmap/resume.py` + TestResume). 같은 명령에
  `--resume`만 붙여 재개하면 된다(§4 명령 + `--resume`).
