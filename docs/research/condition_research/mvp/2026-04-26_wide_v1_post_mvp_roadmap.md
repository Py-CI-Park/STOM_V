# Wide v1 post-MVP roadmap

## Purpose

이 문서는 Wide v1 MVP freeze 이후 프로젝트 방향을 고정한다.

최종 목표는 단일 백테스트에서 좋아 보이는 조건식을 하나 찾는 것이 아니라, 백테스트 결과를 기반으로 조건식을 자동 개선하는 시스템을 구현하는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 기록
-> 데이터/퀀트 분석
-> 개선 후보 조건식 생성
-> 후보별 백테스트
-> 후보 ranking
-> best_candidate 선택
-> 반복 개선
-> 최종 후보 선택
-> 마지막 WFO 검증
-> freeze 또는 재연구
```

## Current baseline

- branch=feature/wide-v1-post-mvp-risk-backlog
- base_branch=STOM_Version_2U_C
- base_commit=9c4ad20d
- base_commit_title=Wide v1 MVP freeze 및 운영 재현 문서화

## Wide v1 frozen candidate

- final_buy_strategy=WideV1Final_B_20260425
- base_buy_strategy=WideV1IterationV2_20260423__cand005
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- source_candidate_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv

## Wide v1 completed scope

```text
1. 백테스트 CSV 분석
2. 후보 조건식 생성
3. 단일 후보 전략 생성/백테스트
4. 후보 백테스트 runtime 안정화
5. discovery research에서 WFO 제거 및 역할 분리
6. 후보 N개 1라운드 백테스트/ranking
7. 거래 유지율 기반 후보 선별
8. row-level 후보 차이 분석
9. score baseline 비교 가능성 보강
10. v3 후보 생성 규칙과 candidate_count=10 실행
11. v4 proxy row-set 다양성 보강
12. v5 actual row-set 대표 후보 선택
13. cand017 영구 전략 WideV1Final_B_20260425 재생성
14. runtime-preflight 통과
15. WFO 8개 window 검증 통과
16. MVP freeze 및 운영 재현 문서화
```

## Wide v1 WFO evidence

- round_count=8
- success_count=8
- success_rate=1.0
- metric=tpi
- mean_oos_metric=0.5762499999999999
- best_oos_metric=0.68
- mean_trade_count=2131.75
- zero_trade_rounds=0
- balanced_preset=pass
- conservative_preset=pass

## Wide v1 did not complete

Wide v1은 자동 조건식 개선 시스템의 MVP 후보를 만든 단계다. 다음 기능은 아직 최종 구현이 아니다.

```text
1. best_candidate를 다음 라운드 baseline으로 자동 승격
2. 여러 라운드 반복 실행
3. 라운드별 leaderboard 누적
4. 개선 정체 시 자동 종료
5. tighten/loosen/add/remove/replace 조건식 변형 정책
6. 최종 후보만 WFO에 넘기는 optimizer-level workflow
7. Wide v2 전용 리포트와 재현 명령어
```

## WFO role

WFO는 조건식 생성 도구가 아니라 최종 검증 도구다.

```text
discovery research:
  빠른 조건식 연구, 후보 생성, 후보 백테스트, ranking

discovery promote / cli.wfo / auto_discovery:
  최종 후보 검증, OOS 안정성 확인
```

따라서 다음 조건식 개선 개발에서도 WFO는 매 후보마다 실행하지 않는다. 백테스트 반복으로 최종 후보를 고른 뒤 마지막에만 WFO를 실행한다.

## Why this branch exists before Wide v2

이 브랜치는 운영 투입을 바로 시작하기 위한 브랜치가 아니다. Wide v1을 닫고, 다음 Wide v2 조건식 자동 개선 시스템 개발 전에 다음 기준을 고정하기 위한 브랜치다.

```text
1. Wide v1 freeze가 의미하는 것과 의미하지 않는 것을 기록한다.
2. WFO 통과를 실거래 수익 보장으로 오해하지 않게 한다.
3. 운영 위험과 조건식 연구 개발을 분리한다.
4. v6가 아니라 Wide v2로 새 연구 사이클을 여는 이유를 기록한다.
5. 다음 PR에서 자동 반복 개선 루프 설계를 시작할 수 있게 한다.
```

## Why Wide v2, not v6

v6는 v5가 실패했을 때 필요한 최소 보강 단계였다.

```text
v5 actual row-set 검증 성공:
  promote/WFO 진행

v5 actual row-set 대표 후보 부족:
  v6 후보 생성 확장

v5 runtime 실패:
  runtime recovery
```

실제 Wide v1은 v5 검증을 통과했고 WFO까지 완료했다. 따라서 다음 조건식 개선 개발은 v5 실패 보강인 v6가 아니라 Wide v2 자동 조건식 개선 루프로 시작한다.

## Remaining development flow

```text
[현재 PR]
Wide v1 post-MVP risk backlog
  - v1 완료 상태 정리
  - 위험 목록 정리
  - 운영 파일럿 체크리스트 정리
  - Wide v2 다음 명령 고정

[다음 PR]
Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
  - best_candidate -> next baseline
  - multi-round runner
  - leaderboard
  - stop condition
  - final candidate selection
  - WFO deferred validation

[후속 PR들]
Wide v2 구현
  - round state
  - candidate generation policy
  - automated backtest loop
  - result accumulation
  - ranking/reporting
  - final candidate freeze candidate

[마지막 검증]
Final WFO
  - 최종 후보만 WFO 실행
  - 통과 시 freeze
  - 실패 시 failure analysis 후 새 연구 cycle 판단
```

## Next command

현재 PR을 완료한 뒤 다음 조건식 개선 작업은 아래 명령으로 시작한다.

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
