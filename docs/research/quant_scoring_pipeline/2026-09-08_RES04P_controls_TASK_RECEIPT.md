# RES-04P control·STOP·overlap TASK_RECEIPT

일자: 2026-09-08. 부모 commit: `993001cddae6ea5c58aedb6c3fe20743542506bc`.
작업 branch: `codex/process-research-res-04p-controls`. 정본 loop는 `e30197c4` 유지.

## 판정

**RES-04P 계획·정의 Gate PASS. 실제 Stage F 미실행.**
검토한 정의 SHA-256: `05c14a641d3e4933c5c607f10f4285b655d4452496072d7315a6af7000a5a83c`.
정의: `planning/2026-09-08_res04p_definition.json`.
예상 receipt schema SHA-256: `4197de7a350b75c444c34657e6ad5efc799cee8810aaafaed50ad2204d5e29f1`.
최종 Markdown: `2026-09-08_RES04P_최종사전등록_정의.md`.

계획 선행 조건을 충족했으므로 SYS-05 개발 가능. 미래 원천 inventory·실행 감독·의미 검증·실행 승인은 Stage F 전에 필요하다. 미래 출력 hash나 승인자 서명을 만들지 않았다.

## 실제 개발

| 모듈 | 역할 |
|---|---|
| res04_control_models / validation | immutable typed scope·결과, chronology/gap/행수/identity 검사 |
| res04_controls | 기존 사건 스트림에서 재현 대조군·inventory-relative 표본 판정 |
| res04_overlap_models / overlap | 공통 시간 교집합·Family OR·동시 발화 진단 |
| exact receipt schema | 7후보/4fold, 금지 필드·불완전 상태·자원 초과의 성공 위장 거부 |

독립 code review가 발견한 **동일 후보 ID의 다른 정의 hash 혼합**을 거부하도록 수정했다. 실패 재현 `res04-definition-mix-red.log`의 DID NOT RAISE를 확인한 뒤 회귀가 통과했다. 최종 정적 검사에서 교집합 타입 추론 경고도 해소했다.

## 실행 증거

외부 로그 폴더: `C:/Users/parkc/STOM_Verification/v1.5_20260907/`.

| 검사 | 실제 결과 | 해석 |
|---|---|---|
| 최초 control red | 8 failed, exit 1 | 구현 전 API 부재 |
| 혼합 definition red | 1 failed, 5 deselected, exit 1 | 잘못된 입력 미거부 재현 |
| `pytest test_res04*.py` 11파일 | 90 passed in 107.69s, exit 0 | 실제 생산 모듈 + 합성 입력; 시장 연구 아님 |
| 최종 overlap/schema/SQLite delta | 14 passed in 19.71s, exit 0 | 마지막 타입 동등 수정 후 재검증 |
| 독립 QA 신규 5파일 | 28 passed in 43.18s, exit 0 | 위 시험과 중복; 합산하지 않음 |
| 독립 QA 추가 probes | 10 passed, exit 0 | 변조·순서·누락 등 |
| basedpyright 신규 생산 5파일 | 0 errors, 0 warnings, exit 0 | Python 3.13.13 지정 |
| ruff 신규 코드/시험 선택 규칙 | PASS, exit 0 | E,F,I,C90,UP,B,SIM,TCH; 전체 저장소 lint 통과 아님 |

실행 명령: `python -m pytest`에 `rg --files tests/unit -g 'test_res04*.py'` 파일 목록을 전달하고 `-q -p no:cacheprovider`, 외부 `--basetemp`를 사용했다. basedpyright는 Python311 Scripts의 설치된 executable에 `--pythonpath C:/Python/64/Python31313/python.exe`를 지정했다. `python -m basedpyright`는 해당 3.13 환경에 모듈이 없어 exit 1이었으며 성공으로 계산하지 않는다. pytest_asyncio의 기존 fixture loop scope 경고는 남아 있다.

## 독립 검토

| 영역 | 검토 task | 판정·근거 |
|---|---|---|
| 목적/권한 | res04_goal | PASS; 최종 definition hash·16 blob·schema 일치 재확인 |
| 코드 | res04_code | PASS; mixed definition 결함 수정 후 14검사 통과 |
| QA | res04_qa | PASS; 신규 28시험·별도10probes·pin 검증 |
| 보안 | res04_security | PASS; 12probes 및 최종 변조 schema 검사 |
| 맥락 | res04_context | PASS; E1/R1 정정·프로그램 우선순위·미래 실행 경계 |

5개 독립 검토를 수행했다. QA는 공개 라이브러리 import와 합성 SQLite 경로를 실제 실행했다. UI/API 변경이 없어 브라우저/화면 완료 판정은 하지 않는다. 패키지 참조시험 94개 또는 기존 생산 수용시험 100개 통과로 바꾸어 보고하지 않는다.

## 다음 원자 작업·전체 페이지 영향

SYS-05 SQ-00: F02의 발견창 통계가 평가창 결과에 남는 문제를 실제 `alpha_lab.mining.stats.evaluate_leaves` import 기반 red 회귀로 고친다. 기존 발견 통계는 별도 namespace로 보존하고 평가 통계 정의를 version으로 구분한다. 이후 SQ-01의 생산 CSV loader + TradeArtifactContract + typed DQ를 연결한다.

P05/P06/P09/P11의 데이터 기반은 강화됐다. P01~P14의 사용자 화면이 새로 완성된 것은 아니다. 전체 페이지·단계 지도는 `2026-09-07_v15_실행계획_진행원장.md`를 따른다.

## 보호·롤백·인계

dirty wt-dev, tmap feedback, 운영 DB 및 봉인 evidence는 수정·stage하지 않았다. merge/push/원격 Issue/PR 없음. 실제 Stage F·경제 G0/G2·Holdout·자동채택·주문 없음. rollback은 이 branch의 명시된 추가 모듈/시험/문서만 대상으로 새 역변경 commit으로 수행하며 원천·사용자 파일은 건드리지 않는다.

재개 시 현재 branch/HEAD/status와 이 정의 hash를 먼저 확인한다. RES-04P를 다시 초안 단계로 되돌리지 않는다. 실제 연구 입력 결과를 생성해 Gate를 채울 필요도 없다. 후속 branch는 이 commit 위에 쌓고 최종 정본 병합은 별도 승인으로 처리한다.
