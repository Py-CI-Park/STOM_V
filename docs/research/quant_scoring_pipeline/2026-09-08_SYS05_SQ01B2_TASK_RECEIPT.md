# SYS05 SQ01B2 세대 결과 품질 TASK_RECEIPT

부모 loop/process-research-pipeline @2cea89143b736346df5e8c86adbc06f5c707cf5a.
작업 branch codex/process-research-sys-05-generation-quality. 원자 구현 검증 완료, 통합 전체 Gate는 별도 기록한다.

## 완료 범위

기존 /bt/result?run_id=&gen_no=에 공식 CSV 품질과 typed 세대 정책을 연결했다. 기존 readonly 조회, REPO_ROOT 경로 제한, identity/context 소유 함수를 GenerationOwners로 주입한다. 새로운 DB/table/병렬 분석 시스템은 없다.

| 입력 | 새 결과 | 권한 |
|---|---|---|
| writer ok + 정상 CSV + 거래 수 일치 | 같은 검증 snapshot으로 기존 full_analysis | PARTIAL, execution_verified=false, 진단만 |
| 위 조건 + gate_passed=false 또는 손실 | 손실·탈락도 진단에 남김 | 수익/채택 성공으로 승격하지 않음 |
| error/timeout/cancelled/rejected/unknown | analysis=null, metrics=null | 실행·품질 축 별도 |
| 일부 파싱/거래 수 불일치 | 분석 차단, 품질 사유 표시 | 정상 행만으로 성과를 꾸미지 않음 |
| CSV 없음 | 저장 수치는 stored_unverified로 보존, analysis=null | 새 분석·검증 성공 아님 |

generation writer는 실제 returncode를 저장하지 않는다. 임의 rc=0을 만들거나 generic ResearchTruth SUCCESS로 변환하지 않는다. basis=generation_writer_v1_without_terminal_receipt. NaN/Inf는 표시 projection에서 null이며 원본 row는 불변이다. 플랫폼 범위 밖 created_at도 null로 반환한다.

## 시험·실사용

| 검사 | 실제 결과 |
|---|---|
| 신규 생산 API red | 10 failed, exit1 |
| 날짜 보안 경계 red | ±1e300: 2 failed, OverflowError |
| 날짜 경계 green 포함 신규 | 12 passed, exit0 |
| 최종 결합 회귀 12파일 | 229 passed in75.19s, exit0 |
| 독립 QA | 기존49 + 별도6 경계 PASS; 위229와 합산 금지 |
| 실제 공유 JSX harness | 5/5, errors=[], 차단 상태 추가 요청0, exit0 |
| npm run build | exit0, JSX142/graph595, app abcf7d15, 6HTML 갱신 |
| 선택 ruff | PASS |
| basedpyright 3새모듈 | 0 errors; exhaustive assert_never의 불필요 비교 경고4 유지 |
| 독립 검토 5영역 | 목적/코드/QA/맥락 PASS; 보안 날짜 오류 수정 후 재검토 PASS |

229 실행 파일은 test_generation_result_quality, test_result_quality_gate, test_backtest_ws_job, test_backtest_evo_portfolio, test_backtest_result_identity, test_backtest_analysis, test_backtest_phase4, test_backtest_phase5, test_trade_csv_quality, test_trade_quality_api, test_trade_quality_review_regressions, test_qsp7_data_contract이다. python -m pytest ... -q -p no:cacheprovider. 이 수치는 참조 패키지 또는 전체 생산 수용시험 통과 수가 아니다.

실제 인하우스 브라우저의 합성 GET fixture에서 생산 BtResultArea/API를 사용했다. g1 손실 -100·gate미통과+실행 영수증 미확인+정상 분석 차트, g2 정상 CSV지만 실행 실패로 분석 보류, g3 CSV 없음·저장 미검증 요약·-5,000원/MDD12% 유지·차트/MC 미지원 확인. 실제 시장 연구는 하지 않았다. fixture에서 제공하지 않는 feature_map/leaf_matrix의404는 전체 화면 검증으로 확대하지 않는다. 200%/모든14화면 수용은 미검증이다.

## 통합 Gate와 보호

9개 과거 미공개 작업을 no-ff 병합한 정본2cea8914의 전체 unit은 전용 integration worktree에서 별도 실행 중이다. 18~19%의 authority 계약은 SYS04 문서에 기록된 slow 구간이다. CPU 증가와 read-only py-spy stack의 _physical_path→validate_gate_receipt→build_all→test_canonical_post_is_catalog_direct_input을 확인했다. 무한대기라고 단정하거나 assertion을 약화하지 않았다. 종료 출력/exit code 전 PASS로 기록하지 않는다.

운영 DB·봉인 evidence·dirty wt-dev·tmap 수정 없음. StageF/G0/G2/Holdout/자동채택/실주문/push 없음. 이번 사용자 요청으로 로컬 작업별 no-ff merge는 허용되며 이전 merge금지 기록보다 최신 정책이 우선한다. rollback은 이 기능의 새 역변경 commit으로 수행하며 원본 자료는 되돌리지 않는다.

다음 B3: 보고서/export가 기존 legacy loader로 품질 Gate를 우회하는 경로부터 red 회귀로 고정한다. B4 개별 분석/MC, B5 비교/portfolio, SQ02 지표 정의는 별도 원자 작업이다.
