# SYS05 B4a 개별 분석·MC 품질 TASK_RECEIPT

부모 d6bef0b30c2789bbf198068ae022f18833c1ca97. branch codex/process-research-sys-05-individual-quality.
**B4a 원자 검증 완료. B4b/raw 피처, B5, 지표 정의 및 전체 통합 Gate는 별도다.**

## 구현과 재사용

```text
기존 job manager / readonly generation / REPO_ROOT 경로 제한
  → individual_source: 실행 정책 + 기존 typed CSV 품질 snapshot
  → individual_analysis: 준비된 거래만 기존 연산 함수에 전달
      ├─ 불가 → requested field=null + 품질/실행 근거
      └─ 가능 → 동일 snapshot 필터·계산 + 유한 JSON
  → MC hook: 소스/범위/호스트/hash/응답순서 확인
      ├─ 차단/오류/원본 불일치 → 보류 사유
      └─ 가능 → 기존 MC chart, 일반·전체화면 동일
```

대상: summary/equity/distribution/heatmap/underwater/insights/mae_mfe/exit_reasons/orderflow/gui_parity 10종과 MC. 기존 반환 field와 route signature를 유지하며 available/analysis_ready/data_quality/execution metadata를 추가했다. 호출자가 실패를 빈 list로 바꾸어 정상0 지표를 만들지 않도록 계산 전 차단한다. 기존 두 permissive private helper는 사용처를 모두 새 facade로 바꾼 뒤 제거했다. B4b/B5의 독립 경로는 유지했다.

Job은 기존 success+CSV 품질 정책, generation은 기존 generation_policy를 사용한다. writer ok와 gateFalse·손실은 partial/실행미검증 진단이며 가짜 rc=0은 없다. 정상0행은 NO_TRADES로 계산 불가, 정상 원본의 빈 조회 구간은 기존 연산의 실제0을 유지한다. 새 지표 정의는 도입하지 않았다.

새 입력·응답 모델/내부 값은 frozen이다. 새 Python2모듈은250LOC 이하이며 no-excuse 검사 위반0. 기존 대형API/화면 전체를 재작성하지 않고 관련 단위만 추출했다. LSP 도구 미노출로 rg/기존 소유 함수 조사/타입 검사/생산 API 회귀를 사용했다.

## 실제 시험

| 검사 | 결과 |
|---|---|
| 올바른 원인으로 재현한 API red | 66 failed22.70초 exit1; 계산 호출 또는 CSV 재읽기 확인 |
| 초기 harness 주의 | pytest.fail 예외가 TestClient portal 종료 오류에 가려져 호출 기록 spy로 교정; 해당 실행은 올바른 red 증거와 구분 |
| 초기 호환 회귀 | 116pass4fail; 축약/15자리 날짜 fixture와 missing-job 옛0 계약 |
| fixture·계약 교정 후 및 generation 추가 | 정상0행 ready=True라는 시험 가정1개를 기존 NO_TRADES 불가 정책에 맞게 정정 |
| 결합8파일 | 159 passed41.55초 exit0 |
| 최종 결합16파일 | 327 passed34.80초 exit0 |
| 새 Python2모듈 타입 | 0 errors/2 exhaustive unreachable 경고 유지 |
| 선택 ruff/no-excuse | PASS/위반0 |
| 실제 production React MC hook | 8/8 errors=[] exit0 |
| 실제 공유 renderer | 6/6 errors=[] exit0 |
| 최종 build | JSX143/graph596; app60120ec1; 번들+6HTML 재생성 exit0 |

327에는 이전 B1/B2/B3/CSV 시험이 포함된다. 다른 숫자와 더해 고유 통과 수로 보고하지 않는다. 참조 패키지 또는 생산 수용시험100개 완료 주장도 하지 않는다.

기존 MC/orderflow fixture의 Apr10이15자리로 생성되던 날짜를14자리로 고치고 공식 header를 사용했다. n상한·quantile·오더플로우 diff75 등의 assertion은 보존했다. missing-job GUI는 HTTP200/job_id를 유지하면서 null/MISSING_ARTIFACT로 의도된 계약 변경을 기록했다. 순수 계산기의 empty-input 테스트는 그대로다.

## UI/실사용

- hook은 MC 전체 envelope를 보존한다. 같은 소스의 실행 실패 전환, A→B, 범위·base URL·원본hash 변경, 늦은 응답을 차단한다.
- 화면 원본hash와 MC 원본hash가 다르면 서버 품질 값을 조작하지 않고 별도 display_ready=false를 붙여 차트를 숨긴다.
- 공유 보류 카드는 일반·전체화면 모두 같은 품질 컴포넌트를 사용하며 재확인 버튼을 제공한다.
- 실제 브라우저에서 결과는 정상으로 조회됐지만 MC 직전에 fake job이 error로 바뀐 경우: '몬테카를로 분석 보류 / 정상 CSV / 실행 실패 / 분석 준비 미충족'을 일반·전체화면에서 확인했다. 화면 스크린샷으로 카드와 hash 줄바꿈도 확인했다.
- 정상 손실 세대는 '실행 영수증 미확인'과2,000회/1일 진단 MC가 표시됐다.
- 실제 '이동 블록' 버튼이 legacy2종 mapping 때문에 shuffle을 보내던 결함 발견. requestURL red 실패→3종allowlist 최소수정→harness8/8→실제 '연속된 거래일 블록을 복원추출한 분포 · block=5' 표시와 method=moving_block HTTP200 로그 확인.
- production React의 act 미지원 및 Node setImmediate와 jsdom timer queue 차이는 시험 harness 문제였다. renderer의0-delay event-loop barrier로 동일 응답 완료를 검증했다. 제품 코드에 지연 sleep을 추가하지 않았다.

실사용은 tests/manual/sq01_browser_fixture.py의 임시 CSV/메모리 fake와 실제API/컴포넌트다. 운영 앱/DB/실제 시장 연구는 사용하지 않았다. fixture의 leaf_matrix/feature_map404는 B4b 미제공이며 완료로 주장하지 않는다. QA 탭/서버/Python 임시 CSV는 종료, debug journal은 이 문서에 요약 후 제거했다.

## 독립 검토

| 영역 | 최종 판정 | 실제 근거 |
|---|---|---|
| b4_goal_review | PASS | 범위·금지권한·method delta 읽기 검토 |
| b4_code_review | PASS | 새API74 pass, 최종hook8/8 독립실행 |
| b4_security_review | PASS | 경로/readonly/authority/유한응답/stale guard |
| b4_context_review | PASS | 과거계약46 pass, fixture·moving_block 호환 |
| b4_qa_review | PASS | 128 pass25.70초, hook8/8 및 renderer6/6, 별도HTTP parameter·0값·empty-range 검증 |

위 검토는 원자 기능 기준이며 전체Fast/Slow 통과를 대신하지 않는다. 다음 단계는 B4b 전체 raw snapshot 피처 adapter다. B4 전체 그룹은 아직 PARTIAL이며 기존5/8 완료 묶음 수를6/8로 올리지 않는다.

운영DB/봉인원본/dirty wt-dev/tmap 변경·stage 금지 유지. 새DB/table/의존성/경제 Gate/Holdout/자동채택/실주문/push 없음. rollback은 이 기능에 대한 새 역변경 commit으로만 수행한다.

보호 경로 확인: restart의 _database/strategy.db는0bytes, CreationTime2026-08-29 22:38:08인 기존 잔여 파일이다. _database는 junction이 아닌 일반 디렉터리이고 해당 DB는 tracked가 아니다. SYS04 구현 결과 문서193~206행의 사용자 정리 경계에 따라 삭제·변경하지 않았다. 이 파일을 실제 운영 DB 또는 연구 가능한 입력으로 취급하지 않는다. 전체 검증은 별도 integration worktree에서 수행한다.
