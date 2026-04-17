# 세그먼트 기반 조건식 연구 루프 PR 보고서

## 목적

이 PR은 기존 매수 조건식을 보존한 상태에서, 백테스트 결과 CSV를 분석해 손실 구간 필터 후보를 만들고 재백테스트 가능한 후보 전략으로 연결하는 1차 연구 루프를 추가한다.

핵심 목표는 AI가 임의로 조건식을 확정하는 것이 아니라, 백테스트 데이터 기반의 개선 가설을 만들고 검증 가능한 후보로 관리하는 것이다.

```text
기준 전략
-> 백테스트 결과 CSV 분석
-> 세그먼트/피처 후보 생성
-> 기존 매수전략에 필터 결합
-> 후보 백테스트
-> 기준/후보 거래 비교
-> 승격 평가 및 리포트
```

## 변경 요약

- 세그먼트 기반 조건식 연구 루프 설계와 구현 계획을 문서화했다.
- 백테스트 결과 CSV에서 기본 거래 지표를 계산하는 모듈을 추가했다.
- 시간대와 시가총액 세그먼트 분석 모듈을 추가했다.
- `B_*` 피처 기반 필터 후보 생성 모듈을 추가했다.
- 기준 전략과 후보 전략의 거래를 공통/제외/신규 거래로 분해하는 비교 모듈을 추가했다.
- 후보 전략 승격 게이트와 점수 계산 모듈을 추가했다.
- 한국어 Markdown/JSON 연구 리포트 생성 모듈을 추가했다.
- 기존 매수전략을 보존하고 자동 필터를 결합하는 단일 연구 루프를 추가했다.
- `stom_backtest.py discovery research` CLI 진입점을 추가했다.

## 주요 파일

### 문서

- `docs/superpowers/specs/2026-04-16-segment-strategy-research-loop-design.md`
- `docs/superpowers/plans/2026-04-16-segment-strategy-research-loop.md`
- `docs/pr/2026-04-17_segment_strategy_research_loop_pr.md`
- `docs/update_log/2026-04-17_segment_strategy_research_loop.md`

### 구현

- `cli/research_metrics.py`
- `cli/research_segments.py`
- `cli/research_candidates.py`
- `cli/research_compare.py`
- `cli/research_promotion.py`
- `cli/research_report.py`
- `cli/research_loop.py`
- `cli/ai_controller.py`
- `cli/subcommands.py`

### 테스트

- `tests/unit/test_research_metrics.py`
- `tests/unit/test_research_segments.py`
- `tests/unit/test_research_candidates.py`
- `tests/unit/test_research_compare.py`
- `tests/unit/test_research_promotion.py`
- `tests/unit/test_research_report.py`
- `tests/unit/test_research_loop.py`
- `tests/unit/test_subcommands.py`

## 기능 상세

### 1. 기준 전략 보존형 후보 생성

후보 전략은 새 매수전략을 독립적으로 만드는 방식이 아니다. 사용자가 선택한 기존 매수전략을 로드하고, 최종 `self.Buy()` 직전에 자동 필터를 결합한 복사본을 저장한다.

이 방식은 기존 조건식의 의도를 최대한 보존하면서 손실 구간 제거 가설만 추가한다.

안전장치:

- 후보 전략명이 기준 매수전략명과 같으면 저장하지 않는다.
- 후보 전략명이 이미 다른 매수전략으로 존재하면 저장하지 않는다.
- 저장 전 `generate_buy_filter_strategy()`로 구문 가능한 전략 코드를 생성한다.

### 2. 데이터 누수 방어

조건식 후보 생성에는 매수 시점에 알 수 있는 `B_*` 정보만 사용한다.

`S_*`와 `R_*`는 진단과 리포트에는 사용할 수 있지만, 새 매수 조건식 생성에는 사용하지 않는다.

### 3. 세그먼트 분석

현재 1차 구현은 다음 분석 기반을 제공한다.

- 시간대 세그먼트
- 시가총액 세그먼트
- 단일/2축 세그먼트 요약
- 손실 구간 후보 추출을 위한 기본 지표

시가총액은 현재 CSV 값 형태를 고려해 유효한 양수/유한값만 단위 추론에 사용한다. 결측, 문자열 오류, 무한값, 0 이하 값은 `미분류`로 처리한다.

### 4. 기준/후보 거래 비교

후보 전략을 평가할 때 단순 총수익률만 보지 않고 거래 집합을 분해한다.

```text
공통 거래: 기준과 후보가 모두 매수한 거래
제외 거래: 기준은 매수했지만 후보는 제외한 거래
신규 거래: 기준은 매수하지 않았지만 후보가 새로 매수한 거래
```

거래 identity는 매수 집합 비교 목적에 맞춰 다음 기준을 사용한다.

```text
종목코드가 있으면 종목코드, 없으면 종목명
+ 매수시간
+ 매수가
```

매도시간은 identity에서 제외한다. 같은 매수 거래의 청산 시점 차이는 공통 거래 진단으로 남겨야 하기 때문이다.

### 5. 승격 평가

후보 전략은 다음 게이트를 통과해야 한다.

- 최소 거래 수
- 후보 거래 수 / 기준 거래 수 비율 하한/상한
- 신규 거래 확장률 상한
- 날짜 집중도 상한
- 종목 집중도 상한
- 유효하지 않은 숫자값 방어
- 기준 전략 대비 점수 개선

승격 평가는 현재 1차 파일럿 기준의 휴리스틱 게이트이며, 최종 실전 채택에는 별도 WFO 검증이 필요하다.

### 6. 리포트

연구 결과는 한국어 Markdown/JSON 리포트로 출력할 수 있다.

리포트에는 다음이 포함된다.

- 후보 조건식
- 후보 생성 이유
- 기준/후보 CSV 경로
- 공통/제외/신규 거래 수
- 기준/후보 평균 수익률과 승률
- 제외 거래/신규 거래 요약
- 승격 평가 결과
- 게이트/델타/사유

JSON 저장 시 `Infinity`, `NaN` 같은 비표준 토큰이 나오지 않도록 비유한 숫자는 `null`로 정규화한다.

## CLI 사용 예시

### 기존 CSV를 기준으로 후보 미리보기

```powershell
python stom_backtest.py discovery research AutoResearch01 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min
```

### 기준 전략 백테스트부터 후보 백테스트까지 실행

```powershell
python stom_backtest.py discovery research AutoResearch01 `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate
```

## 검증

최신 커밋 기준으로 다음 검증을 통과했다.

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
--input은 선택 입력
--base-buy-strategy 표시
--run-candidate 표시
```

최종 코드 리뷰도 통과했다.

## 남은 리스크

### 1. WFO 직접 연결은 아직 없음

`discovery research` 명령은 1차 연구 파일럿이다. 현재 승격 판단은 CSV 비교와 휴리스틱 게이트 중심이다.

실전 채택 전에는 기존 `discovery promote` 경로 또는 후속 Phase에서 WFO를 직접 연결해야 한다.

### 2. 기회집합 로그 미구현

현재는 실제 매수된 거래 결과를 분석하고, 조건 변경 후 재백테스트로 새 기회를 검증한다.

기존 조건 때문에 매수되지 않은 후보 전체를 직접 분석하려면 후속 Phase에서 기회집합 로그가 필요하다.

### 3. 종목코드 부재 시 매칭 한계

현재 결과 CSV에 `종목코드`가 없으면 `종목명 + 매수시간 + 매수가`로 거래를 매칭한다.

후속으로 백테스트 상세 결과에 `종목코드`를 추가하면 비교 정확도가 좋아진다.

### 4. 실제 장기간 운용 검증 미수행

이번 PR은 단위 테스트와 동기화 가드레일 중심으로 검증했다.

실제 장기간 `--run-candidate` 연구 실행은 PR 이후 별도 파일럿으로 수행해야 한다.

### 5. 기존 경고

전체 단위 테스트에서 SciPy precision warning, websocket deprecation warning이 남아 있다.

이번 변경에서 새로 만든 경고는 아니며 기존 테스트 환경에서 발생한다.

## PR 판단

이 PR은 핵심 백테스트 엔진을 변경하지 않고, 기존 CLI/분석/전략 생성 기능을 조합하는 격리 모듈 중심의 1차 연구 루프다.

정규 업데이트 반영을 어렵게 만드는 대규모 엔진 수정은 피했고, 후속 Phase로 확장할 수 있는 기반을 만든다.
