# G003 음성 지형 정적 veto 사전등록 (2026-07-16)

> 지위: **SEALED**
>
> 이 문서와 커밋된 outcome-blind 마스크 스냅샷 및 대상 코드는 최초 실현손익 집계 전의 고정 설계다. 검토와 커밋 뒤에만 finalizer/receipt 실행을 허용하며, 그 전에는 결과를 읽거나 설계를 바꾸지 않는다.
> 최초 combined finalizer/receipt 발행 시도는 측정 전에 실패하여 seal·receipt·claim·target 실행이나 outcome 공개를 전혀 만들지 않았으며, 이번 정정은 runtime dependency 분류만 바꾼다.

## 1. 관측과 범위

- 역사 진단 범위는 정확히 **2022-03-23..2023-12-31**이며, 2022년 101건과 2023년 197건, 합계 incumbent census 298건이다.
- 이것은 fresh OOS 또는 live 성과의 증명이 아니다. 시간축 blind가 없는 고정 역사 거래 집합에서의 drop-only 반사실 진단이다.
- agenda V1의 V1 Negative Veto는 확정 음성 지형을 매수 신호가 아니라 손실 거래 제외기로 평가하며, kill은 어느 한 연도라도 개선이 0 이하이거나 MDD가 악화되는 경우다.
- outcome-blind 입력은 `g003-static-veto-input-v1`이며, 불변 SHA-256은 `69da0107b9c46ac01e1a3527aeef17063bf3a0ca992c7e25f16582dd562c79d2`이다. 이 스냅샷과 `scripts/g003_veto_measure.py`가 측정 전 설계의 유일한 마스크·집계 권위다.

## 2. 고정 설계

### 2.1 마스크와 조인

- `M_O3`는 O3의 다섯 변형 전체 union이다. `surge_nonoverlap`은 별도 family가 아니라 이 union에 흡수되어 있으며, family별 대체·구제 규칙은 없다.
- `M_O4 = O4_ONSET_CARRIER AND (F1 OR F2 OR F3 OR F4@0.22)`이다. 이는 carrier 863,446행 전체에서 명시적 158-candidate DNF와 행별 동치가 검증되었고 mismatch는 0이다.
- `M_DROP = M_O3 OR M_O4`만 driver다. `M_DEEP = M_O3 AND M_O4`는 diagnostic only이며 driver, rescue, 재가중 또는 family별 판정에 쓰지 않는다.
- 각 incumbent의 instrument/day identity mapping은 종목·진입일·실시각의 결정론적 키로 유일하게 해소되어야 하며, source `t0` 또는 정확히 real-clock `t0+1초`만 허용한다. nearest-neighbor, fill, 보간은 금지한다. sparse O3 event bank에 사건이 없으면 봉인된 O3 정의상 `M_O3=false`이고, O4 onset carrier에 없으면 봉인된 O4 정의상 `M_O4=false`다. 즉 통상적인 no-event 행은 unmatched나 무결성 실패가 아니다. identity 미해소, 다중·상충 매핑, 또는 matched carrier 내부의 필수 평가값 부재만 무결성 실패로 측정을 중단한다.
- outcome 관측 전 고정 마스크 수는 다음과 같다. 2022: O3=46, O4=35, union=64, deep=17, carrier=35. 2023: O3=80, O4=69, union=114, deep=35, carrier=69. 이 수들은 설계 변경 근거가 아니며 이후 변경할 수 없다.

### 2.2 고정 입력 출처

스냅샷에 봉인된 출처의 행수·SHA-256·크기는 다음과 같고, 측정 전후 모두 일치해야 한다.

| 출처 | 행수 | SHA-256 | 크기(bytes) |
|---|---:|---|---:|
| champion ledger | 671 | `72b6a082774a61c235f865a61b34d8162ced1972a8e2e7ccc1be7252aff01477` | 779,908 |
| P3 rejoin chunk 1 | 229 | `a21d0144ca012af3965c74628bc16df584cc11d2aa4fbb0895070de03b77fc54` | 240,191 |
| P3 rejoin chunk 2 | 222 | `58fd87bb74c6af2d24cacc3f033f9ea42458f33ae8040804e9867cd4b4817c9e` | 245,320 |
| O3 onset bank | 702,613 | `ca06411c7471f9550c8a8727adad4680c60a6bd9431dc23f56043edea519c859` | 13,061,453 |
| O3 summary | 1 | `13a03c57c9ecc74473f88537f6c053ae879e86085b3ac0f9014191d93490f4ba` | 9,857 |
| O4 candidate bits | 863,446 | `105850275408b061d2406da3ec888bfd27a037531183f5827bd178392315b724` | 4,878,692 |
| O4 summary | 1 | `65f20ea3f229f03420c8ef088b60c64b7810330575ddb163096ca95461e1ea37` | 141,365 |
| D1 onset clause bits | 863,446 | `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56` | 6,783,855 |
O3 onset bank, O4 candidate bits, D1 onset clause bits의 세 parquet은 upstream provenance-only lineage이며, 현재 bytes의 SHA-256·크기를 측정 직전과 직후에 독립적으로 확인하고 evidence에 기록하되 runtime dependency로 stage하지 않는다.

### 2.3 정적 shadow와 집계

- static shadow set은 `M_DROP` 거래의 권위 있는 원래 청산 실현 슬롯에서만 `수익금`을 0으로 마스킹한다. 재진입, 리사이징, 현금 재사용, 복리, 기회비용, scheduling 변경은 모두 금지한다.
- 연도별 정렬은 `(sell timestamp, buy timestamp, original trade_id)` 오름차순이다. 각 연도는 독립적으로 equity=0, peak=0에서 시작한다. MDD는 시점별 `max(peak - equity)`다.
- 연도별 `delta_profit = shadow - baseline`, `delta_mdd = baseline - shadow`로 정의한다. 양의 false-drop share, retained count/rate, retained notional rate, O3/O4/deep/carrier count는 설명 통계일 뿐 판정 변수가 아니다.

## 3. 결정 규칙

- **PASS**: 2022와 2023 모두 `delta_profit > 0` 그리고 `delta_mdd >= 0`.
- **FAIL**: 어느 한 연도라도 `delta_profit <= 0` 또는 MDD가 악화한다. zero-drop 또는 정확한 동률은 agenda kill rule에 따라 유효하게 측정되었더라도 FAIL이다.
- **INSUFFICIENT**: 유효한 측정 전에 provenance, schema, O4 동치, t0/t0+1 조인, source hash/row count, census 또는 identity 무결성이 실패한 경우에만 사용한다. 이 경우 estimand 자체가 존재하지 않으므로 integrity가 우선한다.
- 무결성이 통과한 뒤에는 어떤 연도의 kill도 최종 FAIL이며, 다른 연도의 개선, descriptive count, 양의 false-drop share 또는 retention으로 rescue하지 않는다. known-year 결과에 따른 재정렬·재선택·재마스킹은 금지한다.

## 4. 실행 경계와 산출물

- engine budget=0, DB writes=0, strategy registration=0이다. 대상 실행은 receipt/claim-bound runlab을 통해 정확히 한 번만 허용한다.
- 측정 산출물은 log JSON이다. 이후에만 evidence-bound report와 v2 ledger append를 작성한다. 사전등록 이후의 결과값은 이 문서에 기록하지 않는다.
- 본 문서는 finalizer가 아니며 receipt를 발행하지 않는다. seal 검토 및 커밋이 끝나기 전 실행, outcome read, ledger append, target DB 생성은 금지한다. generic authority schema의 `target_db`에는 기존 비보호 코드 경로 `scripts/g003_veto_measure.py`를 no-promotion sentinel로 둔다. 이 경로는 DB 쓰기를 위해 열지 않으며 어떤 promotion이나 DB 생성도 발생하지 않는다.

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G003-V1-NEGATIVE-VETO",
  "discovery_window": {
    "start": "2022-03-23",
    "end": "2023-12-31"
  },
  "primary_estimand": "고정 incumbent census에서 M_DROP 정적 shadow와 baseline의 연도별 delta_profit 및 delta_mdd",
  "sample_floors": {
    "census_2022": 101,
    "census_2023": 197
  },
  "multiplicity_family": "G003-V1 정적 음성 veto 단일 family; 2022·2023 공동 PASS/FAIL",
  "kill_rule": "어느 한 연도라도 delta_profit <= 0 또는 delta_mdd < 0이면 FAIL; 무결성 실패는 측정 전 INSUFFICIENT",
  "ledger_path": "docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl",
  "authority_paths": {
    "seal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/evidence/seals",
    "promotions_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/evidence/promotions",
    "catalog_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/evidence/catalog",
    "journal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/evidence/journal",
    "backup_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/evidence/backups",
    "target_db": "scripts/g003_veto_measure.py"
  },
  "dependency_roots": [
    "scripts/g003_veto_measure.py"
  ],
  "dynamic_python_dependencies": [],
  "non_python_dependencies": [
    "docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md",
    "docs/research/condition_research/plans/2026-07-12_o3_breakout_onset_preregistration.md",
    "docs/research/condition_research/plans/2026-07-13_o4_generation_grammar_preregistration.md",
    "docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl",
    "docs/research/condition_research/research_runs/alpha_lab_20260705/p3_rejoin_chunk_1of2.json",
    "docs/research/condition_research/research_runs/alpha_lab_20260705/p3_rejoin_chunk_2of2.json",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/g003_veto_input.json",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/o3/o3_breakout_summary.json",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/o4/o4_candidate_summary.json"
  ]
}
```

이 SEALED 계약은 결과를 보지 않은 설계만 고정한다. 결과 해석, 후속 승격 또는 실전 적용은 이 계약 밖의 별도 evidence chain을 요구한다.
