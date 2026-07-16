# G005-X1 Exit Competing-Risk 기술 사전등록 (2026-07-16)

> 지위: **SEALED**
>
> 이 문서는 `G005-X1-EXIT-COMPETING-RISK`의 최초 측정 전 고정 설계다. 목적은 2022--2023 고정 외부 CSV ledger에서 RR8 family와 GPTAUTH_G8의 실현 `수익률` 차이를 exit-cause 구성으로 **기술(descriptive)** 하는 것이다. 인과 효과, 대체 exit 채택, 전략 등록, promotion 또는 live/engine 실행 권한을 만들지 않는다.

## 1. 고정 질문과 한계

- **고정 기술 질문:** 2022--2023으로 엄격히 제한한 외부 CSV 거래 행에서 `mean(수익률_RR8) - mean(수익률_GPTAUTH_G8)` raw contrast가, 사전 고정 exit-cause map으로 표준화한 뒤 얼마나 남는가.
- **주 추정량:** `residual_ratio = abs(standardized_contrast / raw_contrast)`이다. `raw_contrast == 0`이면 주 추정량은 `UNDETERMINED`이며 PASS/KILL로 구제하지 않는다.
- **기술 한계:** cause label은 관측된 청산 조건 텍스트와 `매도시간`에서 만든 사후 분류일 뿐이다. 특정 exit가 손익을 유발했다는 주장, exit 교체 효과, counterfactual 재청산, 신규 진입/청산 채택은 모두 금지한다.
- **금지 범위:** 2024년 이후 행, engine 실행, DB write, strategy registration, promotion, retry/rescue run, 결과 기반 cohort/분류/통계량 변경은 금지한다.

## 2. 봉인된 외부 출처

측정 입력은 아래 네 개의 외부 UTF-8 CSV뿐이다. 위치는 모두 `C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/`이며, 측정 전후의 SHA-256·크기·원시 행수는 정확히 일치해야 한다. 불일치, decode 실패, 행수 불일치 또는 다른 파일 대체는 `UNDETERMINED`다.

| slot | group | file | sha256 | size_bytes | raw_rows |
|---|---|---|---|---:|---:|
| RR8_12 | RR8 | `C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_12_20260707074238.csv` | `f5e3807f26c32d8e2409a56ed1cdc89c80c13b37bcf36f0dbed811595e2ee9ed` | 153817 | 454 |
| RR8_0 | RR8 | `C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_0_20260707074352.csv` | `ae90e89663dd1a704535893556a05954b016ec6b6ece766b9eeb236153fdd06c` | 115829 | 338 |
| RR8_21 | RR8 | `C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_21_20260707074459.csv` | `a22af054c264087d2b87f52ac178b7fe19d49a3c71e660965f6803b83083131f` | 128654 | 380 |
| GPTAUTH_G8 | GPTAUTH_G8 | `C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_GPTAUTH_G8_20260707075127.csv` | `830a003a046e6e1f14372838c458badb198dedb069539d2b6e8ede7f807eb4cd` | 464671 | 1447 |

## 3. Denominator와 행 권위

- 분석 단위는 CSV의 원 행(row)이다. RR8 family는 `RR8_12`, `RR8_0`, `RR8_21` 세 strategy-slot ledger의 합집합이 아니라 **세 ledger 행을 그대로 쌓은 비교군**이다. 동일 종목·날짜·시간처럼 보이는 행도 strategy slot이 다르면 중복 제거하지 않는다.
- 비교군은 `RR8 family` 대 `GPTAUTH_G8`로만 고정한다. 다른 strategy, W6a 결과, 2024+ 자료, DB 또는 engine output은 참조하지 않는다.
- strict date filter는 CSV의 정확한 `매수시간` 컬럼에서만 만든다. `매수시간`은 숫자 문자열 14자 `YYYYMMDDHHMMSS`여야 하며, 첫 8자리 `YYYYMMDD` day와 그중 첫 4자리 year로만 2022/2023 필터를 어떤 row-level output보다 먼저 적용한다. 기대 denominator는 `2022=510`, `2023=1148`, `total=1658`이다. 이 세 값 중 하나라도 맞지 않으면 결과를 출력하지 않고 `UNDETERMINED`로 끝낸다.
- 필터 이후 group별·year별 denominator는 관측된 고정 행수로 보고하되, 결과 기반으로 행을 제외·보정·재가중하지 않는다.
- `수익률`은 실현 수익률 percentage point(pp) 그대로 사용한다. 단위 변환, winsorization, trimming, missing-value fill, sign flip, 수수료 재계산은 금지한다. 필수 필드가 없거나 숫자 파싱이 불가능하면 `UNDETERMINED`다.

## 4. Matching, offsets, 시간 처리

- 이 설계에는 cross-ledger matching이 없다. RR8와 GPTAUTH_G8 행은 서로 짝짓지 않으며, instrument/day/entry identity를 맞추거나 nearest-neighbor, fill, interpolation을 적용하지 않는다.
- t0/t+1 같은 offset 보정은 없다. CSV에 기록된 원래 `매수시간`, `매도시간`, `매도조건` 컬럼만 사용한다.
- `매수시간`은 숫자 문자열 14자 `YYYYMMDDHHMMSS`여야 하며, `datetime.strptime(value, '%Y%m%d%H%M%S')`로 Asia/Seoul wall-clock timestamp로 유효성을 검증한다. 이는 timezone conversion이 아니라 해당 문자열을 서울 현지 벽시계 시각으로 해석하는 parser 검증이다. 날짜와 year는 오직 첫 8자리 day와 첫 4자리 year에서만 읽고, timezone 보정·day rollover 보정·다른 날짜 컬럼 대체는 금지한다. 길이 불일치, non-digits, `strptime` 실패, 결측·중복·모호한 필드는 `UNDETERMINED`다.
- `매도시간`은 숫자 문자열 14자 `YYYYMMDDHHMMSS`여야 하며, `datetime.strptime(value, '%Y%m%d%H%M%S')`로 Asia/Seoul wall-clock timestamp로 유효성을 검증한다. forced-cap 시간 비교는 마지막 6자리 `HHMMSS`만 `093000`과 비교한다. `매도시간`의 첫 8자리 day가 `매수시간`의 첫 8자리 day와 다르거나, 길이 불일치, non-digits, `strptime` 실패, 결측·중복·모호한 필드이면 `UNDETERMINED`이며 timezone/day rollover correction은 없다.
- cause 판정에 쓰는 텍스트는 정확한 `매도조건` 컬럼의 raw Unicode 문자열 하나뿐이다. 텍스트 매칭은 Python의 case-sensitive codepoint substring 연산인 `needle in text`만 사용하며, `strip`, Unicode normalization, `casefold`, 대소문자 변경, 번역, alternate field, 결측 보정, 동의어 추가, 정규식 확장, 수동 재분류는 금지한다. `매도조건`이 결측·비문자열·중복·모호하면 `UNDETERMINED`다.

## 5. 고정 exit-cause map

각 행은 아래 순서를 적용해 정확히 하나의 mutually exclusive cause를 받는다. 앞선 규칙이 참이면 뒤 규칙은 평가하지 않는다.

1. `forced_cap`: `매도시간`의 마지막 6자리 `HHMMSS >= 093000` 또는 `매도조건`이 `강제` 또는 `마감`을 포함.
2. `stop_loss`: `매도조건`이 `손절` 또는 `최저가이탈`을 포함.
3. `trailing`: `매도조건`이 `트레일링` 또는 `최고수익률`을 포함.
4. `time_exit`: `매도조건`이 `보유시간`을 포함.
5. `profit_take`: `매도조건`이 `익절`을 포함.
6. `other`: 위 어느 규칙도 해당하지 않음.

원인군 병합, 순서 변경, 새 cause 추가, 결과를 본 뒤의 예외 처리는 금지한다.

## 6. 통계량과 표준화

- Raw group mean은 filtered rows 전체의 `수익률` 평균이다. Raw contrast는 `mean(RR8) - mean(GPTAUTH_G8)`로 고정한다.
- 각 group `g`와 cause `c`에 대해 `P_g(c) = n_g(c) / N_g`, `E_g[Y|c] = mean(수익률 | g,c)`, raw contribution `P_g(c) * E_g[Y|c]`를 보고한다.
- Pooled standardization weight는 두 group을 합친 filtered sample에서 `w(c) = (n_RR8(c) + n_GPTAUTH(c)) / (N_RR8 + N_GPTAUTH)`로 계산한다.
- Standardized group mean은 `sum_c w(c) * E_g[Y|c]`이다. Standardized contrast는 `standardized_mean_RR8 - standardized_mean_GPTAUTH_G8`이다.
- pooled weight가 양수인 cause에 대해 어느 group이든 observed support가 없으면 해당 cause mean이 정의되지 않으므로 전체 주 추정량은 `UNDETERMINED`다. smoothing, pseudo-count, imputation, fallback mean, cause 병합은 금지한다.
- 분해 보고에는 cause별 `P(c)`, `E[Y|cause]`, contribution product를 group별 raw 기준과 pooled-standardized 기준으로 모두 표시한다.

## 7. Bootstrap과 신뢰구간

- Bootstrap seed는 `2026071603`으로 고정한다.
- Draw 수는 정확히 `20000`이다.
- 재표본 단위는 trading day block이다. 각 replicate는 year별로 독립 stratification하여 해당 연도의 관측 day block 수만큼 복원추출하고, block 내부 행 전체를 함께 포함한다.
- 각 replicate에서도 RR8 strategy-slot 행은 dedup하지 않는다. replicate statistic은 위 raw contrast, standardized contrast, residual ratio 공식을 동일하게 적용한다.
- 95% confidence interval은 exact nearest-rank percentile 방식으로 보고한다. 정렬된 `n`개 bootstrap 값 `x`에 대해 `Q(p)=x[ceil(p*n)-1]`로 고정하고, CI는 `[Q(0.025), Q(0.975)]`다. bootstrap replicate는 하나도 버리지 않는다. 어떤 replicate라도 필수 cause support 결여, raw-zero, parser/schema 문제 또는 기타 이유로 statistic이 undefined이면 전체 판정은 `UNDETERMINED`이며 replicate drop, 대체, 보간은 금지한다.
- annual raw contrast는 2022와 2023을 따로 계산한다. 두 연도 모두 0이 아닌 같은 부호여야 PASS 후보가 된다. 어느 한 연도라도 0이면 부호 기준은 `UNDETERMINED`이며, 한 연도 양수·다른 연도 음수이면 annual sign conflict로 KILL이다.

## 8. 결정 규칙과 multiplicity

- **1순위 UNDETERMINED:** source/provenance 실패, schema 실패, parser 실패, denominator 불일치, missing cause support, `raw_contrast == 0`, annual raw contrast zero, 또는 undefined bootstrap replicate가 하나라도 있으면 다른 규칙을 평가하지 않고 `UNDETERMINED`다.
- **2순위 KILL:** 1순위가 모두 통과한 뒤 pooled `residual_ratio >= 0.8`이거나 2022/2023 raw contrast에 annual sign conflict가 있으면 `KILL`이다.
- **3순위 PASS:** 1순위와 2순위가 모두 통과한 뒤 pooled `residual_ratio < 0.8`이고 2022와 2023의 raw contrast sign이 같은 0이 아닌 부호이면 `PASS`다.
- Multiplicity family는 `G005-X1-EXIT-COMPETING-RISK` 단일 descriptive family다. cause별 table, annual table, CI, group별 denominator는 설명 통계이며 PASS/KILL rescue나 새 family 생성에 쓰지 않는다.

## 9. 실행 권한, hash binding, no-retry 경계

- 이 문서는 source authority와 설계 seal만 제공한다. 지금 상태에서 engine budget=0, DB writes=0, strategy registration=0, promotion=0, measurement=0이다.
- finalizer 전에는 네 source CSV 각각의 pre-hash와 post-hash를 위 SHA-256·size·raw_rows에 결박해 `g005/x1/evidence/` 아래 receipt로 남겨야 한다. pre/post 중 하나라도 없거나 다르면 finalizer와 target run은 금지되고 `UNDETERMINED`다.
- `x1_input.json` materialization은 정확히 한 번, target 실행은 seal과 future `x1_input.json`이 커밋된 뒤 receipt/claim-bound run으로 정확히 한 번만 허용한다. `retry=false`이며 실패·불리한 결과·부분 output·CI 실패를 이유로 rerun, rescue, parameter change, alternate cause map, alternate denominator를 만들 수 없다.
- target path `scripts/g005_x1_competing_risk.py`는 authority sentinel 및 향후 측정 entrypoint 이름일 뿐이며, 이 문서가 DB 생성, DB write, engine launch, registration 또는 promotion을 허가하지 않는다.

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G005-X1-EXIT-COMPETING-RISK",
  "status": "SEALED",
  "claim_type": "descriptive_not_causal",
  "discovery_window": {
    "start": "2022-01-01",
    "end": "2023-12-31"
  },
  "primary_estimand": "2022-2023 fixed external CSV rows에서 raw_contrast=mean(RR8)-mean(GPTAUTH_G8)와 pooled-cause-standardized contrast의 residual_ratio=abs(standardized_contrast/raw_contrast)",
  "sample_floors": {
    "census_2022": 510,
    "census_2023": 1148,
    "census_total": 1658
  },
  "expected_filtered_counts_or_undetermined": {
    "year_2022": 510,
    "year_2023": 1148,
    "total": 1658
  },
  "parsing_contract": {
    "date_year_source": "exact CSV column 매수시간 only",
    "buy_time_format": "digit string exactly 14 chars YYYYMMDDHHMMSS",
    "sell_time_format": "digit string exactly 14 chars YYYYMMDDHHMMSS",
    "timestamp_validation": "first require 14 digits, then validate 매수시간 and 매도시간 with datetime.strptime(value, '%Y%m%d%H%M%S') as Asia/Seoul wall-clock; no timezone conversion",
    "date_filter": "before any row output, use 매수시간[0:8] day and 매수시간[0:4] year only; keep 2022 and 2023 only",
    "condition_text_source": "exact CSV column 매도조건 raw Unicode string only",
    "forced_cap_time": "compare final 6 digits of 매도시간 HHMMSS to 093000",
    "day_mismatch": "매도시간[0:8] must equal 매수시간[0:8]; mismatch => UNDETERMINED",
    "invalid_or_ambiguous_field": "missing, duplicate, ambiguous, non-string text, timestamp length mismatch, timestamp non-digits, invalid date/time, timezone correction need, or day rollover need => UNDETERMINED",
    "offsets": "none; no timezone/day rollover correction and no alternate date/text columns"
  },
  "text_matching": {
    "source": "exact raw Unicode string from 매도조건",
    "operation": "Python case-sensitive codepoint substring: needle in text",
    "forbidden_transforms": [
      "strip",
      "Unicode normalization",
      "casefold",
      "case change",
      "translation",
      "alternate field",
      "missing-value fill",
      "synonym expansion",
      "regex expansion",
      "manual reclassification"
    ],
    "invalid_or_ambiguous_field": "UNDETERMINED"
  },
  "comparison_groups": {
    "left": "RR8 family: RR8_12 + RR8_0 + RR8_21 strategy-slot ledgers, rows not deduplicated across strategies",
    "right": "GPTAUTH_G8",
    "raw_contrast": "mean(left 수익률 pp) - mean(right 수익률 pp)"
  },
  "source_files": [
    {
      "slot": "RR8_12",
      "group": "RR8",
      "path": "C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_12_20260707074238.csv",
      "encoding": "utf-8",
      "sha256": "f5e3807f26c32d8e2409a56ed1cdc89c80c13b37bcf36f0dbed811595e2ee9ed",
      "size_bytes": 153817,
      "raw_rows": 454
    },
    {
      "slot": "RR8_0",
      "group": "RR8",
      "path": "C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_0_20260707074352.csv",
      "encoding": "utf-8",
      "sha256": "ae90e89663dd1a704535893556a05954b016ec6b6ece766b9eeb236153fdd06c",
      "size_bytes": 115829,
      "raw_rows": 338
    },
    {
      "slot": "RR8_21",
      "group": "RR8",
      "path": "C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_21_20260707074459.csv",
      "encoding": "utf-8",
      "sha256": "a22af054c264087d2b87f52ac178b7fe19d49a3c71e660965f6803b83083131f",
      "size_bytes": 128654,
      "raw_rows": 380
    },
    {
      "slot": "GPTAUTH_G8",
      "group": "GPTAUTH_G8",
      "path": "C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_GPTAUTH_G8_20260707075127.csv",
      "encoding": "utf-8",
      "sha256": "830a003a046e6e1f14372838c458badb198dedb069539d2b6e8ede7f807eb4cd",
      "size_bytes": 464671,
      "raw_rows": 1447
    }
  ],
  "source_hash_binding": {
    "required_before_finalizer": true,
    "pre_hash": "before any row output, each source file must match source_files sha256, size_bytes, and raw_rows",
    "post_hash": "after materialization/target read and before finalizer completion, each source file must still match source_files sha256, size_bytes, and raw_rows",
    "mismatch_disposition": "UNDETERMINED and no receipt/claim target run"
  },
  "cause_order": [
    {
      "cause": "forced_cap",
      "rule": "매도시간 final 6 HHMMSS >= 093000 OR 매도조건 contains 강제 OR 매도조건 contains 마감"
    },
    {
      "cause": "stop_loss",
      "rule": "매도조건 contains 손절 OR 매도조건 contains 최저가이탈"
    },
    {
      "cause": "trailing",
      "rule": "매도조건 contains 트레일링 OR 매도조건 contains 최고수익률"
    },
    {
      "cause": "time_exit",
      "rule": "매도조건 contains 보유시간"
    },
    {
      "cause": "profit_take",
      "rule": "매도조건 contains 익절"
    },
    {
      "cause": "other",
      "rule": "no prior cause matched"
    }
  ],
  "standardization": {
    "weights": "pooled cause incidences over RR8 and GPTAUTH_G8 combined filtered rows",
    "group_means": "each group's E[수익률 pp | cause]",
    "missing_support": "UNDETERMINED; no smoothing, imputation, fallback, or cause merge"
  },
  "bootstrap": {
    "seed": 2026071603,
    "draws": 20000,
    "unit": "trading_day_block",
    "stratification": "annual",
    "ci": "95% exact nearest-rank percentile [Q(0.025), Q(0.975)] where sorted n values Q(p)=x[ceil(p*n)-1]",
    "undefined_replicate": "any undefined bootstrap replicate => UNDETERMINED; no replicate dropping, replacement, interpolation, or rescue"
  },
  "multiplicity_family": "G005-X1-EXIT-COMPETING-RISK 단일 descriptive competing-risk family; cause/annual/CI tables are non-rescue diagnostics",
  "kill_rule": "Ordered decision ladder: first source/provenance/schema/parser/denominator/cause-support/raw-zero/annual-zero/any undefined bootstrap replicate => UNDETERMINED; then pooled residual_ratio >= 0.8 or annual sign conflict => KILL; otherwise pooled residual_ratio < 0.8 plus same nonzero annual signs => PASS",
  "decision_precedence": [
    {
      "order": 1,
      "verdict": "UNDETERMINED",
      "conditions": [
        "source/provenance failure",
        "schema failure",
        "parser failure",
        "denominator mismatch",
        "missing cause support",
        "raw_contrast == 0",
        "annual raw contrast zero",
        "any undefined bootstrap replicate"
      ]
    },
    {
      "order": 2,
      "verdict": "KILL",
      "conditions": [
        "pooled residual_ratio >= 0.8",
        "2022/2023 annual raw contrast sign conflict"
      ]
    },
    {
      "order": 3,
      "verdict": "PASS",
      "conditions": [
        "pooled residual_ratio < 0.8",
        "2022/2023 annual raw contrast signs agree and are nonzero"
      ]
    }
  ],
  "ledger_path": "docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl",
  "authority_paths": {
    "seal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/seals",
    "receipts_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/receipts",
    "claims_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/claims",
    "promotions_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/promotions",
    "catalog_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/catalog",
    "journal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/journal",
    "backup_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/backups",
    "hash_audit_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/hash_audit",
    "target_db": "scripts/g005_x1_competing_risk.py"
  },
  "dependency_roots": [
    "scripts/g005_x1_competing_risk.py"
  ],
  "dynamic_python_dependencies": [],
  "non_python_dependencies": [
    "docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json"
  ],
  "receipt_claim_target_runs": 1,
  "one_shot": {
    "materializations": 1,
    "target_runs": 1,
    "retry": false
  },
  "bans": [
    "2024_plus_rows",
    "engine_execution",
    "db_write",
    "strategy_registration",
    "promotion",
    "retry",
    "rescue",
    "causal_claim",
    "exit_adoption"
  ]
}
```

이 SEALED 계약은 결과를 보지 않은 deterministic design만 고정한다. 관측 결과, 해석, 승격, 후속 채택은 이 문서 밖의 별도 evidence chain 없이는 주장할 수 없다.
