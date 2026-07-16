# G003 정적 O3 OR O4 진입 거부 판정

## Observation

- 권위 실행 기록은 `run_ctl/v1/status.json`의 `exit_code: 0` 및 `run_ctl/v1/log.txt` 한 줄 결과이다. 상태 기록의 시작·종료 시각은 각각 `2026-07-16T05:10:36+00:00`, `2026-07-16T05:11:03+00:00`이며, 대상 스크립트의 단일 실행으로 기록되어 있다.
- 로그의 최종 판정은 `FAIL`, `integrity_reasons`는 빈 배열이다. 엔진 실행, 보호 DB 쓰기, 전략 등록은 각각 0이다.
- 2022년: baseline profit 4,130,117, shadow profit 600,898, `delta_profit=-3,529,219`; baseline MDD 836,647, shadow MDD 530,457, `delta_mdd=+306,190`이다.
- 2023년: baseline profit 5,649,359, shadow profit 724,698, `delta_profit=-4,924,661`; baseline MDD 949,568, shadow MDD 1,098,092, `delta_mdd=-148,524`이다.
- 결합 결과: `delta_profit=-8,453,880`, 298건 중 120건 유지, 양의 거래 173건 중 112건이 false drop, O4 equivalence mismatch는 0이다.
- 세 provenance parquet(`d1_onset_clause_bits.parquet`, `o3_breakout_onset_bank.parquet`, `o4_candidate_bits.parquet`)는 측정 전후 SHA-256과 크기가 동일하다. 따라서 이번 기록은 provenance-only 확인을 넘는 데이터 변경 근거를 포함하지 않는다.
- 입력은 고정 snapshot, champion ledger, P3 두 청크, O3/O4 summary 및 위 세 parquet을 참조한다. 영수증·claim·seal의 정확한 경로와 해시는 `g003_veto_evidence.json`에 보존한다.

## Judgment

사전등록 kill 조건은 두 연도 모두 profit에서 발화한다. 또한 2023년에는 MDD가 악화된다. 따라서 고정된 정적 `O3 OR O4` veto family의 판정은 **FAIL**이다. 이 판단은 한 줄 실행 로그의 연간·결합 측정값에만 근거하며, deep-anchor overlap은 진단 전용이다.

## Operational Decision

이 고정 veto를 drop driver로서 retire한다. rescue, reweight, reselect를 하지 않는다. 후보 집합은 `[]`이며 candidate 또는 promotion은 없다. live, OOS, dynamic-capital 성과 주장을 하지 않는다. 엔진 실행·보호 DB 쓰기·전략 등록은 모두 0으로 유지한다.

## Caveats

이 결과는 historical drop-only diagnostic이며 OOS 또는 live 증거가 아니다. 동적 자본 재배분, 리사이징, 재진입, 현금 재사용, 복리, 기회비용, 스케줄 변경을 포함하지 않는다.
