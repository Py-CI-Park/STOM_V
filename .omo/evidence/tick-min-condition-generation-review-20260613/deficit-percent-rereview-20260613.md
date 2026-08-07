# Tick/Min 부족분 % 재검토

작성 시점: 2026-06-13
범위: 지금까지 개발한 설정/프롬프트/템플릿/테스트, 연구 로그, handoff 문서, tick/min roadmap, 기존 review artifacts 재검토.
주의: 이 문서는 소스 수정 없이 현재 증거를 재평가한 보조 보고서다.

## 최종 재판정

| 기준 | 완성도 | 부족분 | 판정 |
|---|---:|---:|---|
| 인프라/배선 기준 | 82% | 18% | 설정, 템플릿, 변수검증, warm-window는 대체로 준비됨 |
| 조건식 생성 기능 전체 기준 | 60% | 40% | 후보 생성 준비는 됐지만 수익 후보 검증은 부족 |
| 실전 후보 발굴 기준 | 52% | 48% | 실제 수익 후보 생성, OOS, min 전체시간 검증이 아직 큰 공백 |
| min 09:00~15:00 전체시간 기준 | 46% | 54% | 데이터 창은 열렸지만 시간대별 edge 지도와 LLM 가이드가 부족 |
| LLM 자동 생성 품질 기준 | 30% | 70% | 누적 LLM 세대가 다수 기각되었고, 새 tick/min 목표의 성공 후보가 없음 |

가장 현실적인 종합 판정은 `완성 52% / 부족 48%`다. 이전 `60%`는 인프라까지 포함한 넓은 점수이고, 사용자가 묻는 "실제로 tick/min 조건식을 만들고 검증 가능한 후보로 이어지는가" 기준으로는 더 엄격하게 봐야 한다.

## 영역별 부족분

| 영역 | 현재 증거 | 완성도 | 부족분 | 부족한 핵심 |
|---|---|---:|---:|---|
| 설정 배선 | `bt_timeframe`, `full_session_enabled`, tick/min preset 존재 | 88% | 12% | preset을 실제 smoke/run config로 이어붙이는 절차 증거 부족 |
| 프롬프트 | tick time-cap은 09:20~09:30 안내 가능 | 74% | 26% | min full-session 09:00~15:00 직접 가이드 부족 |
| 템플릿 | tick late/min full templates 렌더/검증 가능 | 84% | 16% | template 결과가 실제 sweep 성공으로 이어진 증거 부족 |
| 변수/스코프 안전 | targeted unit tests 통과 | 86% | 14% | LLM runtime 코드의 비용 폭탄/무효 변수 위험은 계속 관리 필요 |
| warm backtest 창 | min full-session 15:00 end time 연결 | 82% | 18% | 긴 min sweep에서 시간대별 데이터 충분성 미검증 |
| 테스트 | 68개 targeted tests 통과 | 90% | 10% | 테스트는 계약 검증이지 수익성 검증이 아님 |
| tick late 실제 증거 | T2C3 train/WF aggregate는 긍정 | 68% | 32% | 09:20~09:25 단독 edge와 LLM 생성 성공 미분리 |
| min 실제 증거 | min smoke 2개 실행됨 | 35% | 65% | 둘 다 음수/gate false, M1 primitive map 없음 |
| OOS/WF | THETA/T2C3 일부 증거 | 56% | 44% | 새 tick/min 후보의 promotion-grade OOS/WF 없음 |
| 전체 시간대 | min template/warm window는 15:00까지 가능 | 48% | 52% | 09:00~15:00 band별 신호 지도 없음 |

## 부족분을 구성하는 원인

| 부족 원인 | 전체 부족분 기여 | 근거 | 조치 |
|---|---:|---|---|
| LLM 생성 후보 성공 증거 없음 | 16%p | LLM 1~13세대 다수 기각, 새 tick/min 목표 성공 후보 없음 | 실패 교훈 context 주입 후 2-quarter smoke부터 재시작 |
| min full-session edge 미검증 | 14%p | min smoke는 실행됐지만 음수/gate false, M1 map 없음 | 6 primitive x time-band M1 map 작성 |
| OOS/WF promotion proof 부족 | 9%p | THETA/T2C3는 일부 증거, 새 후보는 freeze/OOS 전 | freeze rule -> OOS -> WF aggregate 순서화 |
| tick 09:20~09:25 단독성 부족 | 6%p | T2C3는 유망하지만 exact late window attribution 필요 | 09:20~09:25 vs 09:25~09:30 vs earlier spillover 분리 |
| runbook/증거 경로 불일치 | 3%p | `--out-prefix` 문서 불일치, aggregate sibling path | CLI 문서 수정, canonical aggregate path 적용 |

총 부족분: 약 48%p.

## Tick 재검토

| 항목 | 좋은 점 | 부족분 | 판단 |
|---|---|---:|---|
| THETA 기준선 | OOS 2022/2026 증거가 있고 현재 champion | 10% | baseline으로는 강함 |
| T2C3 구조 | train positive, WF aggregate positive | 32% | late 확장 후보로 유망하지만 단독 edge 분리 필요 |
| 09:20~09:25 템플릿 | 기본 window가 요청 구간과 일치 | 25% | 후보 생성은 가능 |
| LLM late generation | time-cap prompt는 있음 | 70% | 실제 LLM 수익 후보 생성은 미증명 |
| promotion readiness | V6/동결/OOS 절차 필요 | 45% | 연구 후보 단계 |

Tick은 "후보를 만들 수 있다"는 쪽은 강하다. 부족한 것은 "그 후보가 정확히 09:20~09:25에서 나온 edge이고, OOS/WF까지 견디는가"다.

## Min 재검토

| 항목 | 좋은 점 | 부족분 | 판단 |
|---|---|---:|---|
| 데이터 창 | 15:00까지 warm-window 연결 | 18% | 배선은 준비 |
| min template | 09:00~15:00 조건식 표현 가능 | 22% | 생성 형식은 준비 |
| min smoke | engine-chain 실행 확인 | 65% | 결과가 음수/gate false |
| 시간대별 지도 | M1 primitive map 계획만 있음 | 80% | 가장 큰 부족분 |
| min OOS | 2026-01~02만 가능 | 60% | 데이터 11개월 한계 때문에 엄격한 공시 필요 |

Min은 "기능 배선"보다 "연구 증거"가 부족하다. 전체 시간 조건식을 만들려면 먼저 09:00~15:00을 하나로 보지 말고 시간대별 primitive map으로 쪼개야 한다.

## 다음 개발 우선순위

| 순서 | 작업 | 메우는 부족분 | 완료 기준 |
|---:|---|---:|---|
| 1 | `tmap_sweep` runbook/CLI 명령 정리 | 3%p | `--out-prefix` 제거, `--run-id`/`--manifest-out` 예시 확정 |
| 2 | WF aggregate canonical path 정리 | 2%p | run directory 안에 `aggregate.json` 또는 manifest-linked aggregate 고정 |
| 3 | tick 09:20~09:25 2-quarter smoke | 6%p | 두 분기 모두 거래수/수익/MDD/gate reason 확보 |
| 4 | min M1 primitive map | 14%p | 6 primitives x time bands 결과표 생성 |
| 5 | min full-session prompt 개선 | 6%p | LLM prompt에 09:00~15:00 band별 지침 반영 |
| 6 | LLM context injection | 8%p | THETA/T2C3/기각 계열 교훈을 prompt context에 반영 |
| 7 | freeze/OOS/WF 자동화 | 9%p | frozen 후보만 OOS/WF 실행, aggregate 생성 |

## 즉시 판단

| 질문 | 답 |
|---|---|
| 지금 기능이 완전히 됐나? | 아니다. 인프라는 됐지만 수익 후보 생성/검증은 부족하다. |
| 현재 가장 부족한 쪽은? | min full-session 연구 증거와 LLM 생성 품질 증거. |
| 전체 부족분은? | 엄격 기준 약 48%. |
| 먼저 할 일은? | CLI/runbook 정리 후 tick 2-quarter smoke와 min M1 primitive map. |
| 개발을 계속할 가치가 있나? | 있다. tick 쪽은 T2C3 positive evidence가 있고, min 쪽은 아직 미탐색 공간이 크다. |

