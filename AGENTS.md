# research/* - AI Agent Instructions

## 브랜치 역할

`research/*` 브랜치는 실험적 기능 프로토타입 전용입니다.
실패해도 다른 브랜치에 영향 없으며, 성공 시 wt-dev에서 머지합니다.

## 공식 업데이트 반영 기준

이 브랜치는 공식 업데이트를 장기간 미반영한 채 독립 진화시키는 브랜치가 아닙니다.
공식 버전 반영은 항상 아래 기준으로 진행합니다.

- **기준선(canonical base)**: `wt-dev / STOM_Version_2U_C_CLI_v267`
- **원칙 A**: 부모 브랜치의 공식 업데이트를 계속 흡수
- **원칙 B**: 리서치 브랜치 맥락에 맞게 추론·조정 적용
- **원칙 C**: branch-specific 문서와 최소 호환 보정은 유지

공식 업데이트 반영 전 반드시 아래 문서를 먼저 확인합니다.

- `docs/research/2026-03-28_research_init_v259_v267_sync_matrix_and_plan.md`
- `docs/research/2026-03-28_research_init_official_update_playbook.md`
- `docs/research/2026-03-28_research_init_v267_preparation_completion_report.md`
- 반영 후에는 `python scripts/verify_nonrelease_sync.py`를 실행해
  - `.pyd` 파일 부재
  - 텔레그램 qlist 계약 및 런타임 시작 경로 일치
  - 비정식 워크트리 시리얼키 UI/로드/저장 정책 유지
  를 반드시 확인합니다.

실무 반영 순서는 가능하면 아래 묶음을 따릅니다.

1. 용어/키 체계
2. UI / 설정 골격
3. 홈탭 crawler 구조
4. 런타임 구조(CHQS 등)
5. 백테스트 의미 체계
6. tick + 시장미시구조 분석
7. tail sync (docs/tests/CLI/assets)

## 시리얼키 정책 (필수)

> **이 브랜치에서는 시리얼키를 사용하지 않습니다.**

- 2U_C/CLI_v258에서 분기된 브랜치이므로 시리얼키 미사용 계승
- pyd→py 추론 시 **시리얼키 관련 코드를 절대 추가하지 않음**

## 실험 규칙

- 브랜치명: `research/{실험 주제}`
- 커밋 형식: 자유 (실험이므로 유연하게)
- 성공 시: wt-dev에서 `git merge research/xxx`
- 실패 시: 브랜치 유지 (히스토리 보존)
- `git add -A` 사용 금지

## 전략 조건식 실험

실험적 전략 조건식 생성 시 반드시 참조:

- **변수/조건식 레퍼런스**: `utility/ai_agent/strategy.txt`
- **AI 작업 규칙**: `utility/ai_agent/rules.txt`
- **생성된 전략 저장**: `utility/ai_agent/` 폴더 아래 `.txt` 파일로 기록
- **시장미시구조 분석 (V2.67+)**: `trade/microstructure_analyzer.py` 활용 가능
