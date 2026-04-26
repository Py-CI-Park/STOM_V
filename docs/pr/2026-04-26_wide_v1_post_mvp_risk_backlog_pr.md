# Wide v1 post-MVP risk backlog 및 향후 조건식 개선 로드맵 PR

## 목적

Wide v1 MVP freeze 이후 방향성을 잃지 않도록, `WideV1Final_B_20260425`의 의미와 한계를 정리하고 다음 조건식 자동 개선 개발 흐름을 고정한다.

이번 PR은 신규 조건식 구현 PR이 아니다. Wide v1을 닫고 Wide v2 자동 조건식 개선 루프로 넘어가기 위한 post-MVP 정리 PR이다.

## 전체 개발 흐름

```text
Wide v1
  백테스트 CSV 분석
  -> 후보 조건식 생성
  -> 후보 N개 백테스트
  -> ranking
  -> row-set 중복 제거
  -> cand017 선택
  -> WideV1Final_B_20260425 생성
  -> WFO 검증
  -> MVP freeze

현재 PR
  post-MVP roadmap
  -> risk backlog
  -> 운영 파일럿 체크리스트
  -> Wide v2 다음 명령 고정

다음 PR
  Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```

## 변경 사항

- Wide v1 post-MVP roadmap 문서 추가
- Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 추가
- Wide v2 조건식 자동 개선 루프의 다음 명령 고정

## Wide v1 freeze 근거

- final_buy_strategy=`WideV1Final_B_20260425`
- primary_candidate=`WideV1IterationV5ObservableFull_20260425__cand017`
- primary_expression=`66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
- WFO `round_count=8`
- WFO `success_rate=1.0`
- WFO `mean_oos_metric=0.5762499999999999`
- WFO `mean_trade_count=2131.75`
- WFO `zero_trade_rounds=0`
- balanced preset 통과
- conservative preset 통과

## 중요한 판단

### WFO는 최종 검증 단계다

`discovery research`는 빠른 후보 생성/백테스트/ranking 루프로 유지한다. WFO는 최종 후보가 선택된 뒤 `discovery promote`, `cli.wfo`, `auto_discovery` 계층에서 수행한다.

### v6가 아니라 Wide v2가 다음 조건식 개선 단계다

v6는 v5 actual row-set 검증이 부족할 때 필요한 보강 분기였다. 실제로 v5는 통과했고 promote/WFO까지 완료했다. 따라서 추가 조건식 개선은 Wide v2 자동 반복 개선 루프로 새로 시작한다.

### WFO 통과는 실거래 수익 보장이 아니다

이번 문서는 실거래 전 위험을 닫는 문서가 아니라, 남은 위험을 명확히 드러내는 문서다.

## 변경 파일

- `docs/superpowers/specs/2026-04-26-wide-v1-post-mvp-roadmap-and-risk-backlog-design.md`
- `docs/superpowers/plans/2026-04-26-wide-v1-post-mvp-risk-backlog-and-roadmap.md`
- `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md`
- `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md`
- `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md`

## 검증

- `Select-String`으로 roadmap 핵심 문구 확인
- `Select-String`으로 risk backlog 핵심 문구 확인
- `git diff --check --ignore-cr-at-eol`

## 남은 위험

- 운영 파일럿 체크리스트 항목은 아직 닫힌 것이 아니라 Open 상태로 기록했다.
- Wide v2 자동 반복 개선 루프는 이번 PR에서 구현하지 않는다.
- 신규 백테스트나 WFO 재실행은 이번 PR 범위가 아니다.

## 다음 단계

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
