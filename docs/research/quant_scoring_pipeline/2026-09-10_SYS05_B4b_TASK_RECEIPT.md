# SYS05 B4b 원본 피처 품질 연결 결과

## 판정과 범위

B4b 원자 구현·집중 회귀·독립 검토 완료. 전체 통합 unit Gate는 별도 영수증으로 판정한다.
작업 branch: codex/process-research-sys-05-feature-quality. 부모: 5f1e7ca901845a0dc396fec56e6d7c057f5b6f20.
선행 B4a 전체 Gate는 같은 부모에서 Fast 8154 passed/27 skipped, Slow 24 passed, 각각 exit 0이다. 정본 JSON 영수증은 planning/2026-09-10_b4a_integrated_receipt.json이며 B4b 검증으로 사용하지 않는다.

## 실제 변경

| 대상 | 변경 | 보존한 계약 |
|---|---|---|
| leaf_matrix | 품질·실행 admission 이후 동일 snapshot 집계 | 기존 리프·표본·변별 계산기 |
| feature_map | 동일 snapshot과 기존 B_/D_ 카탈로그 축 제한 | 기존 grid/regions와 구간 clamp |
| revision_proposals | admission 이후 기존 전략 조회와 메모리 diff·의도 검사 | 저장·채택·경제 실행 없음 |
| Leaf/FeatureMap/EntryAutopsy | 품질 사유, 원본 hash, 늦은 응답·소스 변경 방어 | 기존 생산 컴포넌트 재사용 |
| MC 보완 | 기대 hash가 있는데 응답 hash가 없으면 차단 | 기존 방법·계산기 유지 |

CsvSnapshot의 headers/rows를 csv.writer/StringIO로 기존 load_csv/enrich에 전달한다. 원본 bytes 복원을 주장하지 않는다. 계보 hash는 원본 snapshot 것이다. 공식 54/37열, tick/min의 dtype·NA·인용 문자열·CRLF 및 파일 교체 후 계산을 검증했다. 기존 pandas owner 유지, 새 DB/table/의존성 없음. 수치 원문이 기존 수치 parser에서 결측으로 바뀌면 typed PROCESSING_ERROR로 보류한다. S_/R_ 원본은 보존하되 진입 분석 축으로는 허용하지 않는다.

이 세 API는 전체 CSV 범위이며 시간 구간 필터 적용 결과가 아니다. API analysis_scope=full_source_csv와 화면 안내를 일치시켰다.

## 검증 영수증

- 최종 집중 회귀: 421 passed in 56.81s, exit 0. 로그 C:/Users/parkc/STOM_Verification/v1.5_20260910/b4b-focused.log.
- 독립 QA: 지정 6개 Python 모듈 60 passed in 17.42s, exit 0. 별도 문맥·코드 검토의 신규 3모듈 21 passed, exit 0.
- React 생산 vendor 하네스: feature 소비자 9/9, MC 9/9, 기존 result 6/6. 각 exit 0. null HTTP200, hash 누락/불일치, 소스 제거·변경, 오래된 제안 응답 포함.
- 독립 목표·코드·보안·문맥·QA 검토 5개 PASS. 전체 suite를 대신하지 않는다.
- 새 backend 5모듈 타입 검사 0 errors/24 warnings. 기존 pandas/proposer 타입 경계 경고가 남으며 프로젝트 전체 타입 무결성을 주장하지 않는다.
- 실제 인하우스 브라우저: 합성 160행을 실제 생산 컴포넌트/API로 열고 80행씩 두 리프, 개선 제안 diff(하한 0→2), 의도 일치 PASS와 경제 승인 아님 안내, 손실 영역 2개를 직접 확인했다. 화면 스크린샷에서 표·카드 배치도 확인했다. 실제 시장 연구·운영 검증이 아니다.

## 발견·수정·잔여 위험

1. float('1_0')과 기존 pandas 숫자 해석의 차이를 red로 재현하고 값 유실 차단을 추가했다. 60개 관련 회귀 green.
2. 중간 결합 시험은 ASGI TestClient 진입 대기로 종료했다(exit 1, PASS 아님). 정확한 원인 미확정. phase5 분리 36 passed/exit 0 후 최종 결합 421 passed/exit 0. 이벤트 루프·인증 설정을 완화하지 않았다.
3. 기존 화면의 일부 통계 설명·경제 표현, 축 구간 문자열 표현은 후속 SQ02/UX06 감사 대상이다. 관측된 합성 수치를 경제적 발견으로 사용하지 않는다.
4. 200% 확대/전체 14페이지 수용·실운영 데이터 검증은 이번 범위 완료가 아니다.

## 재개 및 안전 경계

B4a+B4b로 SYS05 8개 묶음 중 6개 원자 범위 검증 완료(75%: 묶음 개수 기준). 전체 단계 1/7, 전체 페이지 수용 0/14 유지. 다음 B5 compare/overlay/portfolio → SQ02 지표 정의 → ANA05 Bundle 순서.
통합은 명시 stage·한국어 commit→loop no-ff merge→문서 index 정규화 branch→고정 HEAD Fast/Slow Gate 순서다. 전체 Gate가 실패하면 실패 분류 후 수정한다.
dirty wt-dev/tmap, 운영 DB와 봉인 evidence는 변경하지 않았다. 연구/Stage F/G0/G2/Holdout/자동채택/주문/push 없음. rollback은 본 기능 역변경 commit으로 하며 원본·사용자 WIP를 되돌리지 않는다.
