# 2026-04-23 Wide v1 Row-Level 후보 차이 분석 설계

## 목적

이번 설계의 목적은 기존 best candidate `WideV1RetentionCand5_20260422__cand003`과 v2 best candidate `WideV1IterationV2_20260423__cand005`의 거래 단위 차이를 분석해, 왜 v2가 기존 cand003보다 낮은 adjusted_score를 기록했는지 설명하는 것이다.

v2 실행 결과는 `HOLD`다. 실행은 성공했지만 기존 cand003을 개선하지 못했다. 따라서 다음 단계는 후보를 더 많이 실행하는 것이 아니라, 거래 단위로 무엇이 유지/제거/추가됐는지 확인하는 것이다.

```text
[기존 best cand003]
        |
        v
[v2 best cand005]
        |
        v
[row-level trade set diff]
        |
        v
[score 하락 원인 해석]
        |
        v
[v3 후보 생성 규칙 또는 candidate_count=10 확장 판단]
```

## 배경

기준 후보:

```text
baseline_candidate=WideV1RetentionCand5_20260422__cand003
expression=66.999 <= 시가총액 < 2_580
trade_count=36918
trade_count_retention=0.9018247551115128
adjusted_score=10943.034141541459
promotion_passed=True
candidate_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
```

v2 best 후보:

```text
v2_best=WideV1IterationV2_20260423__cand005
expression=66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4
trade_count=36096
trade_count_retention=0.9777344384852917
adjusted_score=2554.7109523820864
promotion_passed=True
candidate_csv=backtest/csv\stock_bt_WideV1IterationV2_20260423__cand005_*
```

핵심 질문:

```text
v2 cand005는 cand003에서 어떤 거래를 추가로 제거했는가?
그 제거된 거래들이 실제로 손실 개선에 도움이 됐는가?
혹은 수익 거래를 더 많이 제거해서 score가 하락했는가?
```

## 전체 개발 흐름에서의 위치

```text
[0. Wide v1 baseline]
        |
        v
[1. candidate_count=5 실행]
        |
        v
[2. cand003 best 확인]
        |
        v
[3. v2 후보 생성/실행]
        |
        v
[4. v2 HOLD 판정]
        |
        v
[5. row-level 후보 차이 분석]      <- 이번 설계
        |
        v
[6. v3 후보 생성 규칙 또는 candidate_count=10 확장 판단]
```

## 분석 대상

### 필수 CSV

```text
cand003_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
v2_cand005_csv=runtime JSON의 best_candidate.candidate_csv 값에서 확인한 WideV1IterationV2_20260423__cand005 CSV
```

v2 cand005 CSV는 runtime artifact이므로 Git에 없다. 실행 worktree의 `backtest/csv` 또는 runtime JSON에서 정확한 경로를 찾아야 한다.

### 비교 key

거래 단위 비교는 아래 key를 우선 사용한다.

```text
종목명
매수시간
매도시간
매수가
매도가
```

가능하면 추가 key:

```text
보유시간
매도조건
```

목표는 cand003과 v2 cand005의 거래 집합을 아래 3개로 나누는 것이다.

```text
common_trades: 양쪽 모두 존재
cand003_only: cand003에는 있으나 v2 cand005에는 없음
v2_only: v2 cand005에는 있으나 cand003에는 없음
```

## 접근안

### A. trade set diff + 손익 요약 추천

각 trade set의 count, 평균수익률, 총수익금, 승률, 평균 MAE/MFE를 비교한다.

장점:

```text
score 하락 원인을 가장 빠르게 설명 가능
v3 후보 생성 규칙으로 바로 연결 가능
```

단점:

```text
개별 거래 수준의 상세 원인은 추가 drill-down이 필요할 수 있음
```

판단: 추천한다.

### B. feature bucket별 diff

`cand003_only`와 `common_trades`를 시가총액, 당일거래대금, 체결강도, 등락율, 시분초 bucket으로 나눠 비교한다.

장점:

```text
v2 보조 feature인 당일거래대금 조건이 어떤 구간을 과도하게 제거했는지 확인 가능
```

단점:

```text
CSV 컬럼명/인코딩 정규화가 필요
```

판단: A 다음에 수행한다.

### C. 거래별 Top loss/profit 목록

`cand003_only`에서 제거된 거래 중 손실 상위/수익 상위를 뽑는다.

장점:

```text
제거된 거래가 손실 중심인지 수익 중심인지 직관적으로 확인 가능
```

단점:

```text
단일 사례 위주 해석으로 과적합될 수 있음
```

판단: A/B의 보조 리포트로 포함한다.

## 권장 설계

이번 단계는 A+B+C를 모두 포함하되, 구현 우선순위는 A -> B -> C다.

```text
1. CSV 로드 및 컬럼 정규화
2. trade key 생성
3. common / cand003_only / v2_only 분리
4. 각 set의 손익 요약
5. feature bucket별 손익 비교
6. cand003_only의 top loss/profit 목록 작성
7. score 하락 원인 판정
```

## 분석 지표

각 trade set별 기본 지표:

```text
trade_count
win_rate
avg_return
median_return
total_return
total_profit
avg_hold_time
avg_mfe
avg_mae
profit_factor
```

핵심 판정 지표:

```text
cand003_only.total_profit
cand003_only.avg_return
cand003_only.win_rate
v2_only.total_profit
v2_only.avg_return
common.avg_return_delta
```

해석:

```text
cand003_only가 큰 손실이면 v2 제거 조건은 유효했으나 다른 곳에서 손실
cand003_only가 수익 또는 상대적으로 양호하면 v2가 좋은 거래를 제거해 score 하락
v2_only가 손실이면 v2 조합이 신규 손실 거래를 만든 것
common 성능이 나빠졌다면 조건식 변경이 같은 거래의 매도/체결 결과에도 영향을 준 것
```

## 출력 산출물

새 모듈을 만들 경우:

```text
cli/research_rowdiff.py
tests/unit/test_research_rowdiff.py
```

문서:

```text
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md
docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md
```

runtime output:

```text
backtest/temp/wide_v1_row_level_candidate_diff_20260423.json
```

runtime output은 Git에 커밋하지 않는다.

## CLI 설계

이번 단계에서는 먼저 library + script/one-shot Python 실행으로 충분하다.

필요 시 후속으로 CLI subcommand를 추가한다.

예상 future CLI:

```powershell
python stom_backtest.py report row-diff `
  --left cand003.csv `
  --right v2_cand005.csv `
  --output-json backtest\temp\wide_v1_row_level_candidate_diff_20260423.json
```

하지만 이번 설계의 기본 범위는 library helper와 문서화다. 새 CLI subcommand는 필요성이 확인되면 별도 설계로 분리한다.

## PASS / HOLD / FAIL 기준

### PASS

```text
CSV 2개 로드 성공
trade key 생성 성공
common / cand003_only / v2_only 분리 성공
각 set별 손익 요약 생성
score 하락 원인을 설명할 수 있음
```

PASS 이후:

```text
$brainstorming Wide v1 v3 후보 생성 규칙 설계
```

### HOLD

```text
CSV 로드와 set 분리는 성공
하지만 score 하락 원인이 명확하지 않음
또는 key mismatch가 커서 거래 단위 비교 신뢰도가 낮음
```

HOLD 이후:

```text
$brainstorming Wide v1 row-level key 정합성 보강 설계
```

### FAIL

```text
CSV 파일 누락
필수 컬럼 누락
trade key 생성 실패
분석 결과 저장 실패
```

FAIL 이후:

```text
$brainstorming Wide v1 row-level 분석 실패 원인 설계
```

## runtime DB 정책

이번 분석은 CSV 기반이므로 DB 접근은 필수는 아니다.

다만 v2 cand005 CSV 경로를 runtime JSON에서 찾거나 후보 전략 DB 상태를 확인하는 경우 기존 정책을 유지한다.

```text
STOM_CLI_DATABASE_DIR=<실제 운용 _database 폴더>
```

폴더명 `STOM_V.wt-dev` 자체가 아니라 실제 운용 `_database` 경로가 기준이다.

## 남은 리스크

1. CSV key가 완전히 고유하지 않을 수 있다.
   - 매수시간/종목명/매도시간/가격 조합으로 보강한다.

2. 후보 CSV의 한글 컬럼명이 mojibake일 수 있다.
   - UTF-8-SIG 로드와 alias map을 사용한다.

3. row-level 분석 결과가 v3 후보 규칙으로 바로 연결되지 않을 수 있다.
   - 이 경우 feature bucket 분석을 확장한다.

4. score 하락 원인이 복합적일 수 있다.
   - trade set diff와 feature bucket diff를 함께 본다.

## 다음 단계

이 spec이 승인되면 다음은 `writing-plans`다.

권장 명령:

```text
$writing-plans Wide v1 row-level 후보 차이 분석 계획 작성
```
