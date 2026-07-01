# Condition Research

## 목적

이 디렉터리는 STOM 조건식 연구에 필요한 원본 보고서, 요약, 전략 설계 근거, 실험 로그를 보존하기 위한 공간이다.

이 디렉터리는 원본 보고서 보존, tick 연구 baseline, process-research v2 실행 기록, Condition Passport, 연구 계획/관리/결과 보고서를 함께 묶어 사람이 읽는 wiki와 AI가 재사용하는 context source 역할을 한다.

## 전체 흐름

```text
[원본 전략 분석 보고서]
        |
        v
[요약 / 해석]
        |
        v
[연구용 wide 조건식]
        |
        v
[연구용 후보 저장 / 운영 DB·프로모션 아님]
        |
        v
[직접 백테스트]
        |
        v
[Retention-Aware 후보 개선 루프]
```

## 하위 디렉터리

- `source_reports/`: 외부 원본 보고서를 수정 없이 보존한다.
- `summaries/`: 원본 보고서에서 조건식 연구에 필요한 시간대, tick 설정, 주요 변수, 해석 원칙을 요약한다.

## 최신 기준 문서

| 날짜 | 문서 | 역할 |
|---|---|---|
| 2026-06-18 | `2026-06-18_current_state_rereview_summary.md` | 조건식 생성/OOS/포트폴리오/대시보드 연구 현황의 최신 점수와 다음 공식 OOS 우선순위 |
| 2026-06-30 | `2026-06-30_condition_research_knowledge_system.md` | 조건식 이름/계보/Condition Passport/연구 문서 관리 시스템 설계 |
| 2026-06-30 | `2026-06-30_next_improved_process_research_plan.md` | 개선된 process-research v2의 다음 실제 연구 실행 계획서 |
| 2026-07-01 | `2026-07-01_process_research_v2_handoff_and_sell_axis.md` | process-research v2 전체 핸드오프: 실전 검증 결과, 커밋 정리 결과, 매도 조건식 연구축 |
| 2026-07-01 | `2026-07-01_uncommitted_inventory_and_commit_plan.md` | 커밋 전 인벤토리와 커밋 후 `.gjc`/`.omo` 보류 상태 정리 기록 |

## 원본 보고서 핵심

- 거래 시간대는 `09:00 ~ 09:30` 중심이다.
- 평균 간격 설정은 `30틱`이 공통 기준이다.
- 주요 매수 변수는 현재가, 등락율, 거래대금, 시가총액, 시분초, 체결강도 계열이다.
- 주요 매도 변수는 체결강도, 이동평균, 수익률, 최고수익률, 매수시간 계열이다.

## 주의

wide baseline은 최적 조건식이 아니다. 목적은 실전 채택이 아니라 연구 데이터 확보와 자동 개선 루프의 기준 CSV 생성이다.

## 운영 메모

`source_reports/`의 원문 보고서는 원본 파일과 hash 동일 보존을 위해 trailing whitespace를 포함한 공백을 수정하지 않는다. 공백 정리가 필요하면 원본 보존본이 아니라 별도 summary 또는 후속 연구 문서에서 처리한다.

## 연구 문서 관리 원칙

- 조건식 id는 추적용이고, AI 프롬프트에는 이전 매수/매도 조건식 전문과 sha256을 함께 전달한다.
- 조건식별 `Condition Passport`를 만들어 사람이 이해하는 이름, 기계 id, buy/sell 전문, 공식 결과, OOS 상태, 실패 원인, 다음 허용 작업을 함께 보존한다.
- 실제 연구는 `연구 계획서 -> 연구 관리 보고서 -> 연구 결과 보고서` 3종 문서로 남긴다.
- `promotion-review`는 생성 없이 frozen/fresh/OOS/WF/evidence health만 점검하며, export/live/final promotion은 계속 금지한다.
