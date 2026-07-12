# 2026-07-08 V4 대시보드 핸드오프 — 개발 완료·push 완료, 남은 작업=PR only

## 1. 결론 (한 줄)

V4 대시보드 재구축 + 성숙도 로드맵 Phase 1 + 감사·테스트 정리까지 **개발 완료·origin push 완료**.
브랜치 `feature/dashboard-v4-20260704` @ **`47981e3c`**(origin 동기, 작업트리 clean). **남은 작업은 PR 하나뿐**이며,
PR은 사용자 지시로 **보류 중**(연구 종료 후 진행 예정). base·게이트·기존실패 처리 방법은 §5 참조.

## 2. 지금까지 한 것 (V4 델타 = base `loop/process-research-pipeline` 대비 32커밋)

| 구간 | 커밋 | 내용 |
|---|---|---|
| 스캐폴드·리디자인 | `2e7d7c80`~`dbe4684d`, `7fd1092e`(P1)·`4cd459bb`(P2~5)·`f797d9eb`(P6) | 프로토타입 IA로 V4 셸·8탭 재구축(opt-in `/ui/v4`) |
| wt-dev 백엔드 동기화 | `19ddf809`(merge)·`ab592614`·`360e6bef` | 연구 파이프라인 37커밋 격리검증(722 passed)→채택 ff-merge |
| UAT·접근성·CORS | `5cf11cd1`·`cd5ece18`·`3c93936d`·`f5ff7a63`·`3292f917` | 브라우저 UAT, CORS env 옵트인, 하네스 격리, 아카이브 스윕, 리다이렉트 쿼리 보존 |
| 전수 감사 + 수정 | `bafeec61`·`f0270437`·`15ab109f`·`62626df0` | 8뷰 UX 감사(~90) + 수정: RUN셀렉터·Lab위키·비-Live run제어·HoF경계스크롤·History 개발헤더숨김·Governed Index 로딩·재감사 |
| 로드맵 Phase 1 | `f5faf53a` | C4(HeroChart 초기상태)·C5(Index 로딩피드백)·C6(라이트 재검증) |
| 테스트 정합 | `47981e3c` | run_compare 소유권 계약을 V4 단일번들 현실에 맞게 갱신 |

성숙도: **~90% → ~95%**(Phase 1 완료). 8개 탭 전부 기능 완비. 상세 감사·증거는
`docs/update_log/2026-07-05_dashboard_v4_full_ux_audit.md`(§1~6), `..._redesign_completion.md`,
`..._v4_wtdev_backend_sync_verification.md`, `..._final_verification_and_guide.md` 참조.

## 3. 검증 상태 (현재 HEAD 기준)

| 게이트 | 결과 |
|---|---|
| `python scripts/verify_nonrelease_sync.py` | 통과(exit 0) |
| `node track-z-harness.mjs`(webui-build) | V1~V7 allPass |
| esbuild 빌드 | 0에러(app.js 최신 해시) |
| 전체 `pytest tests/unit/`(4091개) | **4077 passed / 12 failed** → `47981e3c` 후 **11 failed(전부 base 기존)** · **V4 신규 실패 0** |

## 4. 12개 실패 분석 (git 이력 대조로 정본 확정 — §5 PR 시 필수 참조)

- **11건 = base 기존 부채**: 테스트 파일·대상 소스(`ui/`·backtester·seed DB) 전부 **V4 델타에서 불변**
  → base `loop/process-research-pipeline`에서도 동일 실패. 내역:
  - 백엔드 backtester 계약 드리프트 7건(생성자 큐 `lq→tq`·`betting`·dict_set 인자·spawn 시그니처·process 진단·job cancel)
  - seed DB 환경 3건(`sqlite3.OperationalError: no such table: stockbuy` — 이 워크트리 seed 미완비)
  - 옛 V2 PyQt 1건(`test_ui_jisu_cleanup` — `ui/ui_process_kill.py` 창위치 인덱스)
- **1건 = V4가 바꾼 유일한 것**: `test_dashboard_run_compare_frontend::test_primary_bundle_keeps_compare_out_of_home_owner`.
  V4 Workbench(`v4-workbench.jsx`)가 `RunComparePanel`을 정당하게 import→공유 app.js 번들에 포함되며
  "번들 문자열 없음" 휴리스틱이 무효화됨. **`47981e3c`에서 소유권 계약을 소스검사(app.jsx는 미렌더·Workbench가 소유)로
  갱신해 해소**(삭제 아님·계약 강화). 4 passed 확인.

## 5. 다음 작업: PR (남은 유일 작업)

**전제**: 사용자 지시로 보류 중. 아래 순서·주의를 반드시 지킬 것.

| 순서 | 할 일 | 명령/주의 |
|---|---|---|
| 1 | **PR base 지정** | **`loop/process-research-pipeline`(wt-dev 레인)**. `main` 절대 금지 — main 대비 1454커밋(전체 베이스라인 포함). V4 델타는 base 대비 ~32커밋 |
| 2 | **타이밍** | wt-dev 연구 종료 후. draft로 열어두면 리뷰는 시작하되 머지는 종료 후(활성 레인 변경 방지) |
| 3 | **PR 직전 게이트** | base 최신 tip 재머지 → `verify_nonrelease_sync.py` + `track-z-harness.mjs` 재실행(그린 확인) |
| 4 | **PR 생성** | `git push` → `gh pr create --base loop/process-research-pipeline --head feature/dashboard-v4-20260704 --title "feat: V4 대시보드 리디자인 + 성숙도 로드맵 Phase1" --draft` |
| 5 | **PR 본문 주의** | "전체 pytest 11 failed는 base 기존 부채(§4 대조 증명), V4 신규 실패 0"을 명시해 리뷰어 오인 방지 |
| 6 | (선택) 최종 증거 | PR 전 전체 `pytest tests/unit/` 재실행으로 "11 failed(전부 기존)" 스냅샷 남기기(~15분) |

## 6. 로드맵 남은 항목 (PR과 별개 · 조건부)

| 항목 | 조건 |
|---|---|
| C7 라이브 승인 게이트 E2E | 실 LLM 비용 + `backtest/graph/` 기록 → 사용자 명시 승인 필요 |
| A1 거버넌스 라이브 · B3 analysis_card | same-origin 채택(=이 PR 머지) 시 자동 해소 |
| B2 measurement UI | slippage는 이미 Audit 노출 · measurement_frame은 백엔드 배선 선행 필요 |

## 7. 참조

- 브랜치: `feature/dashboard-v4-20260704` @ `47981e3c`(origin 동기)
- 프로젝트 메모리: `memory/v4-dashboard-pr-pending.md`(PR 절차 요약)
- 로드맵 Artifact: `https://claude.ai/code/artifact/ec3e9982-3219-4312-b875-3a5858c2aa25`
- 실행: 서버 80(이 워크트리)+8791(wt-dev 실데이터), `http://127.0.0.1/ui/v4?base=http://127.0.0.1:8791`
