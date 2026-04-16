# 2026-04-17 세그먼트 기반 조건식 연구 루프 추가

## 개요

기존 매수 조건식을 보존한 상태에서 백테스트 결과 CSV를 분석하고, 손실 구간 필터 후보를 결합한 후보 전략을 생성·검증할 수 있는 1차 연구 루프를 추가했다.

이번 변경은 핵심 백테스트 엔진을 직접 수정하지 않고 `cli/research_*` 격리 모듈과 `discovery research` 하위 명령으로 구성했다. 정규 업데이트를 계속 반영하기 쉽도록 기존 `backtest/`, `trade/`, GUI 경로는 건드리지 않았다.

## 추가된 기능

- 백테스트 결과 CSV 기본 지표 계산
- 시간대/시가총액 세그먼트 분석
- `B_*` 기반 필터 후보 생성
- `S_*`, `R_*` 매수 조건 누수 방어
- 기준/후보 거래의 공통·제외·신규 분해
- 후보 승격 게이트와 점수화
- 한국어 연구 리포트 JSON/Markdown 생성
- 기존 매수전략에 필터를 결합하는 연구 루프
- `stom_backtest.py discovery research` CLI

## 안전장치

- 후보 전략명이 기준 매수전략명과 같으면 저장하지 않는다.
- 후보 전략명이 이미 다른 매수전략으로 존재하면 저장하지 않는다.
- 후보 조건식에는 `S_*`, `R_*`를 사용하지 않는다.
- 후보 거래 수가 너무 줄거나 신규 거래가 과도하게 늘면 승격 평가에서 탈락시킨다.
- 날짜/종목 집중도가 비정상적으로 높으면 탈락시킨다.
- 비유한 숫자값, 결측, 잘못된 지표값이 승격을 통과하지 않도록 방어한다.

## 검증

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
915 passed, 1 skipped, 10 warnings
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

```powershell
python stom_backtest.py discovery research --help
```

결과:

```text
--input 선택 입력
--base-buy-strategy 표시
--run-candidate 표시
```

## 남은 리스크

1. `discovery research`는 아직 WFO를 직접 실행하지 않는다. 실전 채택 전에는 기존 `discovery promote` 또는 후속 WFO 연결이 필요하다.
2. 기회집합 로그는 아직 없다. 매수되지 않은 후보를 직접 분석하려면 후속 Phase에서 엔진 계측이 필요하다.
3. 결과 CSV에 `종목코드`가 없으면 `종목명 + 매수시간 + 매수가`로 거래를 매칭한다.
4. 실제 장기간 데이터로 `--run-candidate`를 실행한 운영 파일럿은 아직 수행하지 않았다.
5. 전체 단위 테스트의 SciPy precision warning과 websocket deprecation warning은 기존 경고로 남아 있다.

## 브랜치/PR 안내

작업 커밋은 `56aef2a`부터 현재 작업 브랜치 `feature/segment-strategy-research-loop`로 이동했다.

PR 대상:

```text
base: STOM_Version_2U_C
head: feature/segment-strategy-research-loop
```

PR 문서:

```text
docs/pr/2026-04-17_segment_strategy_research_loop_pr.md
```
