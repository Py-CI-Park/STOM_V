# 세션 핸드오프 — 앵커 변이 발굴 연구 (2026-06-17 09:41)

> compact/세션 교체돼도 이 한 장 + 디스크 상태로 이어간다. 이전 핸드오프(파이프라인 구현):
> `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md`(§7 P3·§8 P4/P5/A).

## 0. 마인드셋·규율(불변)
엔진/CLI/backtest_graph **무수정**. 출력=실매매용 per-stock 조건식. 정직지표=**OOS 통과 수**(baseline 0).
사후슬라이스≠엣지(재백테 게이트 필수). **커밋은 요청 시에만**(현재 전부 미커밋). 보고에 체크시각 포함.
★진단으로 **"데이터 천장 아님 — 알파 실재, 병목=콜드 LLM 생성"** 확정됨([[champion-passes-discovery-gate]]).

## 1. 어디까지 왔나
- **P0~P5 전부 구현·검증·code-reviewer APPROVE 완료**(이전 핸드오프 §7/§8). 미커밋.
- **양성대조 진단**(2026-06-16): 검증 챔피언 4종을 발굴 게이트(mdd20/daily0.05)로 재백테 → **4/4 통과**
  → 게이트 정상·알파 실재·병목=생성기. doc: `2026-06-16_champion_positive_control_diagnostic.md`.
- **앵커 변이 발굴(콜드생성→앵커변이 전환)**: 신규 `ai_strategy_loop/scripts/overnight_anchor_mutation.py`
  (LLM 0회). 검증 앵커에서 단일축 변이→materialize→`claude_candidate_batch_eval`(P0b 게이트)→
  gate=True 채택→최선을 새 앵커로(hill-climb)→마감까지. dry-run+실주행 검증됨.

## 2. ★밤샘 발굴 결과 (seed_902905, 완료)
- **19라운드·통과 399건·챔피언 `r8_4_strength_max=250` = +13,928,386 / MDD 9.62**. 통과율 99%·크래시 0.
- **r8에서 수렴**(증분 +1.1M→…→+0.13M→0, r9~19 평탄). = 구조해석/시뮬 반복수렴(잔차→0)과 동일 원리
  ([[anchor-mutation-convergence-fea-analogy]], doc `2026-06-17_anchor_mutation_convergence_structural_analogy.md`).
- 챔피언 θ(seed에서 7축 변경): cap_max3000·strength_min50→**70**·strength_max300→**250**·window_end90500→**90700**·
  burst3.0→**2.5**·take_hard5→**9**·stop_hard-5→**-7**·trail_start6→**4**. summary=`ovn_anchor_summary.json`.
- ★정직: 399는 **train 게이트** 통과. **OOS 검증 미실행**(사장님 지시로 보류) — 최종 결정 전 필수.

## 3. 멀티스타트(다른 봉우리, 사장님 질문) — 진행 중
- 가설: 수렴=국소최적 → 다른 시드/조건이면 더 높은 봉우리 가능(=최적화 multi-start / FEA 다중 초기조건). **맞음.**
- **t2late 멀티스타트**(`--template seed_902905_t2late`, run_prefix `ovn_t2late`, out `ovn_t2late.jsonl`,
  log `ovn_t2late_run.log`, --max-rounds 12 --deadline 12:00 --max-per-param 3): **3차 시도서 작동**(r4 진행,
  후보 ~10M·**payoff 1.6~1.7·MDD 8~13** = seed보다 payoff↑·MDD↓). 수렴 best를 +13.93M과 비교 예정. monitor `bk3019ztd`.
- ★1·2차 실패원인 = **워밍 prepare 타임아웃**(좀비 워커 53개가 시장DB 점유). **운영규칙**: 무거운 워밍 백테는
  **한 번에 하나만**(겹치면 prepare 경합 타임아웃). **고아 정리법**: `multiprocessing.spawn` 워커 중 ParentProcessId가
  죽은 것만 Stop-Process(활성 런·대시보드·타 워크트리 보존). 53개 정리 후 3차 성공.

## 4. 대시보드(8770) 변경 — 이번 세션
- **프로세스 흐름 페이지**(`scripts/build_process_flow_html.py` → /process_flow, 진화탭 외 process 탭 iframe):
  §1.5 진단·§1.5b 레짐의존성·§1.6 v2루프·§2 인라인 시각 단계카드·§7 라이브 hill-climb 트리·흐름 애니메이션(flowtok).
  ★캐시 끈질김 → Ctrl+Shift+R. 라우트가 매요청 재생성(import 캐시) → 생성기 수정 시 **서버 재시작 필요**.
- **`/time_profit`·`/run_log` 엔드포인트**(app.py) — 검증됨. **`fitness/backtest_timeseries.py`**(concurrent_holdings·
  time_of_day_profit, test 5).
- ★**`_csv_by_buy_name` 폴백**(app.py `_backtest_detail_payload`+`/time_profit`): warm-batch/밤샘 런은 csv_path가
  DB에 None → 전략명으로 backtest/csv/ 최신 CSV 폴백. **이게 진화탭 BacktestDetailChart(동시보유·일별손익·누적수익·
  낙폭)가 라이브 런을 실시간 표시하게 함**(30초 폴링+최고세대 추종). 동시보유 등 4차트는 *원래 있었고* csv_path가 빠져
  빈 것 → 폴백으로 해결(프론트 번들 재빌드 불필요).
- 서버 재시작: `python -m ai_strategy_loop --port 8770`(detached, powershell Start-Process). 프론트 jsx 변경 시만
  `cd dashboard/webui-build && node build-app.mjs`(이번 세션 번들 재빌드 없음).

## 5. 라이브 프로세스/모니터/크론 (세션 의존)
- t2late 발굴: detached python(overnight_anchor_mutation). 대시보드: detached 8770.
- monitor `bk3019ztd`(t2late 종료·크래시). cron `ac587037`(아침보고, 이미 발화·소진). seed monitor 종료됨.
- ★세션 닫으면: 발굴 detached는 생존, 모니터/크론 소멸. 결과는 jsonl/summary로 디스크 보존.

## 6. 다음 단계
1. **t2late 수렴 대기** → best를 seed +13.93M과 비교(payoff/MDD 차이 주목) → "다른 봉우리 더 나은가" 답.
2. 추가 멀티스타트: **exit2(7θ)·r2full(11θ)** (한 번에 하나씩, 엔진 경합 회피). 각 수렴 best 수집.
3. ★**OOS 검증**(최종·결정적): 최고 봉우리 챔피언을 OOS(다른 기간)로 재백테 → 진짜 알파/과적합 판별.
   넓게 탐색할수록 다중검정 위험↑ → OOS+FDR 게이트 필수. (사장님 지시로 *지금은 보류*, 최종 선택 전 필수.)
- 미완 태스크: #25 레짐 리포트 HTML, #27 v2 레짐인식 루프(현 드라이버=v1 단일축; 레짐별 분석+탐색/활용+robust 게이트는 미구현).

## 7. 재개 절차
1. 이 문서 → 멀티스타트 상태 확인: `ovn_t2late_run.log` tail + `ovn_t2late_summary.json`(있으면 완료).
2. 새 멀티스타트 기동 전: `python -m ai_strategy_loop.scripts.overnight_anchor_mutation --template <seed> --config-json
   ai_strategy_loop/state/run_p5_validation_tick_late.json --run-prefix <name> --out <...jsonl> --max-rounds 12 --deadline-hhmm <HH:MM>`.
   ★기동 전 다른 워밍 런 없는지 확인(겹치면 타임아웃). 좀비 있으면 고아 워커 정리(§3).
3. 진단 dry-run: `--dry-run --max-rounds 1`로 변이·재료화 확인 후 실주행.
