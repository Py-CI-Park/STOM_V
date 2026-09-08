# SYS05 SQ01B3 보고서 품질 TASK_RECEIPT

branch codex/process-research-sys-05-report-quality. 부모 B2 b522a71a. 원자 기능 검증이며 전체 통합/전체14페이지 완료가 아니다.

## 구현

기존 /bt/report job·run/gen 경로의 legacy list 재읽기를 제거했다. 기존 경로 제한→typed CSV snapshot→같은 배열의 full_analysis와 Monte Carlo로 연결한다. generation은 B2 policy/context를 그대로 사용하고 prepared_source를 내부 전달한다. 원본 row/CSV를 재작성하지 않는다. MC는 기존 진단 계산(n=2000)을 유지하며 새 경제 실험/seed/승인을 발급하지 않는다.

품질 또는 실행 조건 미충족이면 analysis/metrics/montecarlo=null이다. HTML에는 자료/실행/원본·정상·거부·예상 행/hash를 표시하고 동일 정보의 stom-report-quality JSON을 삽입한다. 위험 문자열은 HTML 및 script문맥에서 escaping하며 비유한 값은 null이다. 차단 보고서는 성과 hero/차트 없이 이유만 표시한다. CSV없는 세대는 저장 손실을 미검증 요약으로 보존하되 빈 차트 navigation은 생성하지 않는다.

기존 render_report 입력 계약과 없는 job의 None→안내 HTML200을 보존했다. 정상 generation의 헤더 거래 수도 유지했다. 정의/Bundle namespace/6-table 규칙은 변경하지 않았다.

## 검증 영수증

| 항목 | 실제 결과 |
|---|---|
| 실제 API 신규 red | 8 failed in22.02s, exit1; 차단에서도 분석/MC 호출, 정상 입력 CSV 재읽기 |
| 기존 포함 첫 green 시도 | 49 passed/1 failed; 축약 CSV와 허용 경로 밖 양성 fixture 확인 |
| 공식 fixture/허용 경로/실제 writer상태 수정 | 50 passed in42.82s, exit0 |
| 결합14파일 | 251 passed in78.26s, exit0 |
| 마지막 미검증 요약/안전 JSON 추가 포함 신규 | 10 passed in20.10s, exit0 |
| 독립 QA | 43 passed45.58s + 별도3 passed14.34s, exit0; 합산 금지 |
| 독립 코드 | 22 tests PASS, exit0 |
| 독립 검토 | 목적/코드/보안/맥락/QA 모두 PASS |
| 신규 helper basedpyright | 0 errors/0 warnings, exit0 |
| 선택 lint·diff check | PASS |

251에는 B2/기존 품질 시험이 포함되며 전체 생산 수용시험100개 또는 전체 unit 통과로 바꾸어 말하지 않는다. 기존 보고서 테스트의 정상 fixture만 공식54열로 확장했고 REPO_ROOT를 tmp로 격리했다. evaluated 상태를 승인 상태로 추가하지 않고 실제 writer의 ok로 양성 fixture를 교정했다.

브라우저: 합성 GET fixture에서 실제 production report 렌더러를 사용했다. 정상손실g1은 -100원·정상1행·partial/hash·차트/진단MC, 실행실패g2는 VALID1행이지만 분석 보류/hero없음, noCSVg3는 -5,000원과 저장 미검증 안내를 확인했다. 보유시간 단위·자본없는 MDD/MC 해석 등 기존 지표 정의 문제는 SQ02에서 별도 definition으로 다룬다.

## 범위와 다음

이번 일치는 **한 보고서 요청 내부**의 동일 snapshot이다. 앞서 연 화면과 나중에 생성한 보고서의 hash가 항상 같음을 보장하지 않는다. 영속 Bundle와 시간차 export 고정은 ANA05다. 개별 MC·비교/overlay/portfolio API도 아직 전환하지 않았다.

SYS05 원자5/8 검증: SQ00/SQ01/B1/B2/B3. 다음 B4 직접 분석·MC admission→B5 복수 입력→SQ02 versioned metrics→ANA05 Bundle. 단계 Gate1/7, 전체 페이지0/14는 그대로다. 0/14는 새 수용범위의 완결 검증 수이며 기존 STOM 기능이0이라는 뜻이 아니다.

정본2cea8914 전체 unit은 별도 integration worktree에서 실행 중이며 중간에 실패1건 표시를 관찰했다. 최종 상세/exit code 전 통합 PASS를 주장하지 않는다. 보존해야 하는 user WIP/DB/evidence는 stage하지 않았다. 로컬 no-ff 병합 허용, push/경제 Gate/실전은 금지. 롤백은 기능 범위의 역변경 commit으로 수행한다.
