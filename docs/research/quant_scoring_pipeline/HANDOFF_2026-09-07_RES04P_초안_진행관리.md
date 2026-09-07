# RES-04P 초안·진행관리 핸드오프 / TASK_RECEIPT

## 현재 위치

기준 정본 e30197c44507acf2f2360e78463e48b1ccfdc81c에서 codex/process-research-res-04p-manifest-plan 브랜치를 생성했다. 이 문서를 포함하는 commit은 `git log -1 --format=fuller -- <이 파일 경로>`로 확인한다. 자신을 포함한 commit hash를 파일 안에 사전 기입하지 않는다.

이번 산출물은 전체 실행/페이지/브랜치 원장, RES-04P 초안과 JSON이다. RES-04P는 DRAFT_NEEDS_DECISIONS이며 미완료다. 신규 생산 기능·실제 UI·경제 연구 완료를 주장하지 않는다.

## 읽는 순서

1. 2026-09-07_v15_실행계획_진행원장.md
2. 2026-09-07_RES-04P_사전등록_초안.md
3. planning/2026-09-07_res04p_draft.json
4. 이전 2026-08-30_RES-04_새구조가설_검토.md

## 권한과 보호

최신 사용자 요청의 계획/브랜치/커밋 관리에 따라 지정 문서의 로컬 commit을 수행한다. merge/push/원격 issue/PR은 별도 승인 없이 하지 않는다. 연구 임계·seed·승인자는 사용자 요청에서 제공되지 않았으므로 null이다. tmap feedback은 변경/stage하지 않는다. dirty wt-dev는 수정하지 않는다. 운영 DB/봉인 원본 evidence는 읽기 작업을 확장하거나 변경하지 않는다.

## 검증 기록

PowerShell ConvertFrom-Json 및 초안 불변식 검사: PASS, command exit 0. 출력: `DRAFT_CONTRACT_CHECK: PASS (authority false; 14 undecided fields null; 8 decisions; 0 research jobs)`. 상태/실행 false/prereg_hash null/미확정값/결정수/허용 필드수/연구 job수를 검사했다. JSON Schema 전체나 생산 validator 시험으로 부르지 않는다.

`git diff --check`: exit 0. LF→CRLF 안내는 있었고 오류는 없었다.

색인 검증 명령: `python -X utf8 scripts/build_research_docs_index.py`, `python -X utf8 scripts/build_research_docs_index.py --check`. 최종 출력/exit는 외부 `C:\Users\parkc\STOM_Verification\v1.5_20260907\res04p-index-build.log`, `res04p-index-check.log` 및 작업 최종 보고에 기록한다. 생성 색인은 새로운 봉인 연구 evidence가 아니라 파생 문서 메타데이터다.

생산 테스트/독립 reviewer/브라우저 QA는 이번 문서 변경에서 실행하지 않는다. 과거 참조 94 PASS는 이번 실행 실적이 아니다. 신규 source code/지표/DB 변경이 없으므로 production red→green을 수행했다고 주장하지 않는다.

## 다음 조건

사용자는 **“기존 순서 유지: RES-04P 확정 후 개발”**을 선택했다. 따라서 DEC01~08과 실제 검토 영수증이 먼저 필요하다. SYS-05의 합성 production-import red→green도 지금은 수행하지 않는다. 우선 실제 outcome-free source를 지정하고 가용성/역할/정책을 검토해야 하며, 이번 문서를 사전등록 완료나 실행 승인으로 소비하지 않는다.

어떤 경우에도 전체 계획을 완료로 표시하지 않는다. 실제 기능별 Gate/commit/시험 영수증이 쌓일 때 진행원장을 갱신한다.
