# GPT OAuth 재로그인 후 A/B/C 연구 재실행 기록

## 목적

이 문서는 2026-06-27 야간 process-research 결과를 기준선으로 남기고, ChatGPT OAuth 재로그인 성공 후 GPT 기반 A/B/C 연구 루프를 다시 실행하기 위한 기록입니다.

## 이전 연구 기준선

| 항목 | 값 |
|---|---|
| 이전 실행 경로 | A/B/C LLM 루프 시도 후 LLM-free anchor mutation fallback |
| LLM 장애 | `gpt_auth` `refresh_token_invalidated` / `token_expired` |
| fallback 방식 | `seed_902905` 기반 LLM 0회 앵커 변이 + 백테스트 hill-climb |
| 평가 후보 | 180개 |
| 게이트 통과 | 105개 |
| 최상위 후보 | `rr8_21_trail_keep=0.7` |
| 최상위 profit | 3,089,180 |
| 최상위 MDD | 18.84 |
| 최상위 trades/daily | 165 / 0.70 |
| 안전 경계 | advisory 연구 전용, export/live/final promotion 없음 |

## 이전 연구 Top 후보

| 순위 | 후보 | profit | MDD | trades | daily | 비고 |
|---:|---|---:|---:|---:|---:|---|
| 1 | `rr8_21_trail_keep=0.7` | 3,089,180 | 18.84 | 165 | 0.70 | 최고 손익 |
| 2 | `rr8_12_turnover_min_902=1.5` | 3,062,696 | 12.87 | 190 | 0.80 | 안정성 우수 |
| 3 | `rr8_0_cap_max=2500` | 3,047,522 | 17.34 | 145 | 0.60 | 시총 상한 축소 효과 |
| 4 | `rr8_4_strength_max=250` | 3,040,172 | 19.01 | 164 | 0.70 | strength 상한 축소 효과 |
| 5 | `rr7_3_strength_min=70` | 2,873,814 | 20.83 | 165 | 0.70 | r8 개선 기반 |

## 재실행 조건

| 항목 | 상태 |
|---|---|
| ChatGPT OAuth 재로그인 | 완료 |
| 토큰 파일 | `C:\Users\parkc\.config\newsletter-ai\chatgpt_auth.json` |
| proxy smoke | `gpt-5.5`로 `STOM_OK` 응답 확인 |
| 엔진 기본값 | 32 warm engines 유지 |
| 연구 기간 | 2025-01-01 ~ 2025-12-31 전체기간 |
| 안전 정책 | 연구만 허용, export/live/final promotion 차단 |

## 이번 재실행 계획

| 단계 | 프로세스 | 목적 | 완료 기준 |
|---:|---|---|---|
| A | `fast-discovery` | GPT로 새 후보 발굴 | 생성/실패 로그와 run id 기록 |
| B | `process-research` | 전체기간 GPT 기반 조건식 개선 | 백테스트 결과, top 후보, reject 이유 기록 |
| C | `promotion-review` | read-only evidence health 정리 | 후보 비교/검토만 수행, 승격 없음 |
| 종료 | report/safety | 이전 fallback 기준선과 비교 | 보고서, safety receipt, quality gate |

## 주의

- 이 재실행은 운영 승격이 아닙니다.
- `PROMOTE` 또는 기존 대시보드 검증 항목은 historical/advisory 정보이며 이번 실행의 직접적인 운영 승인 근거가 아닙니다.
- `export`, `live`, `final promotion`은 별도 승인 전까지 실행하지 않습니다.
