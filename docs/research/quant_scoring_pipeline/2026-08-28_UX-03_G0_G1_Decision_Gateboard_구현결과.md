# UX-03 G0→G1 Decision Gateboard 구현 결과

> 완료일: 2026-08-28
>
> 구현 커밋: `0b1e6e09` — `기능(연구): 봉인된 G0-G1 중단 판정을 게이트보드에 연결`
>
> 권위: `DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION`
>
> 결론: **공식 실행 성공과 경제적 연구 중단을 한 화면에서 분리했다. G1은 플랫폼 28/28 PASS지만 개발 규칙 0/7이므로 G2·Holdout·자동채택은 차단된다.**

---

## 1. 왜 이 화면이 필요한가

이전 화면은 실행 완료, 과거 HOF, 차트, 실시간 상태가 한 흐름에 섞여 있었다. 사용자는 `28/28`을 전략 합격으로 오해하거나, 부모 대비 덜 나빠진 후보를 승격 후보로 읽을 수 있었다.

UX-03은 하나의 질문에 답한다.

> G0에서 G1으로 구조를 바꾼 결과, 무엇이 실제로 통과했고 지금 허용된 다음 행동은 무엇인가?

| 구분 | 화면 답변 |
|---|---|
| 실행 | G1 28/28 유효, SUCCESS 23, NO_TRADES 5 |
| 짝비교 | 7후보 중 3후보가 부모 대비 구조 신호 |
| 절대 경제 기준 | 7후보 중 0후보 통과 |
| 최종 행동 | `STOP_NO_G2_NO_HOLDOUT` |
| Holdout | `SEALED_NOT_TOUCHED` |
| 채택 | 불가 |

---

## 2. 구현 범위

| 영역 | 구현 | 파일 |
|---|---|---|
| 읽기 전용 API | 봉인된 G1 공식 실행과 G0/G1 짝비교를 strict Pydantic 모델로 읽어 하나의 결과로 투영 | `ai_strategy_loop/dashboard/research_result_api.py` |
| 증거 무결성 | 두 JSON의 SHA-256이 다르면 HTTP 503으로 실패 폐쇄 | 위 API |
| 라우팅 | `GET /research-result/current`만 등록, write endpoint 없음 | `ai_strategy_loop/dashboard/app.py` |
| 게이트 레일 | Platform / Economic / Paired를 같은 높이에서 분리 | `frontend/v4-research-result.jsx` |
| 다음 행동 잠금 | G2·Holdout·자동채택 금지를 상시 노출 | 같은 파일 |
| 후보 탐색 | 7후보 버튼, 선택 후보의 부모·추가 가드·자식 계보 | 같은 파일 |
| 같은 Fold 비교 | G0→G1 거래수·평균 Δ·총손익 Δ·G1 MDD | 같은 파일 |
| Exit attribution | STOP_LOSS / TAKE_PROFIT / TIME / SESSION / OTHER 변화 | 같은 파일 |
| 상태 표현 | NO_TRADES의 미관측 값을 0 또는 긍정 색으로 합성하지 않음 | JSX + CSS |
| 접근성 | `aria-pressed`, live region, keyboard-scroll table, focus-visible, reduced-motion | JSX + CSS |
| 프로덕션 산출물 | bundle/manifest/HTML cache hash 재생성 | `frontend/bundle/*`, HTML 6종 |

---

## 3. 봉인 증거

| 증거 | SHA-256 | 크기 |
|---|---|---:|
| `evidence/2026-08-26_res03_g1_official.json` | `86898e1e8cb4268528b11c846bba3131e4db12383ef75cc2b861d15f9b55b0a5` | 1,390,027 bytes |
| `evidence/2026-08-26_res03_g0_g1_paired_analysis.json` | `d4bf0a33e2e6813a7d424480b72256f48940f74248456acb63464db9c7aa9a4e` | 38,413 bytes |

API는 파일 존재와 JSON schema만 검사하지 않는다. 내용이 한 글자라도 바뀌어 SHA가 달라지면 `sealed research evidence fingerprint mismatch`로 503을 반환한다. 원본을 수정하거나 새로운 수치를 합성하지 않는다.

---

## 4. 실제 연구 결과

| Gate | 결과 | 성공 여부 |
|---|---|---|
| Platform | 28/28 valid, source 28/28, bundle 28/28 | **실행 성공** |
| Execution | SUCCESS 23, NO_TRADES 5 | **정상 분리** |
| Paired falsification | 3/7 | **구조 신호 일부** |
| Development Rule | 0/7 | **경제 실패** |
| 거래 | G0 1,415 → G1 819 | 감소 관측, 개선 주장 아님 |
| G1 양수 Fold | 전체 4/28 | 안정성 부족 |
| 최종 verdict | `STOP_AFTER_G1_NO_DEVELOPMENT_RULE_PASS` | **정상 중지** |
| 다음 Gate | `STOP_NO_G2_NO_HOLDOUT` | G2/OOS 미진입 |
| Holdout | `SEALED_NOT_TOUCHED` | 봉인 유지 |
| 자동채택 | `false` | 권한 없음 |

짝비교 3/7은 상대 변화다. 절대 개발 기준 0/7을 덮지 않는다. 화면의 핵심 문장은 다음과 같다.

> 실행은 성공했지만 절대 개발 기준을 통과한 전략은 없습니다.

---

## 5. 검증 결과

### 5.1 Python/API

| 검증 | 결과 |
|---|---|
| 게이트보드/API 집중 테스트 | **7 passed / 1.77s** |
| ANA-03 실제 중단 판정 회귀 | **4 passed / 3.56s** |
| Ruff | All checks passed |
| no-excuse rules | 2 files, violations 0 |
| basedpyright | 0 errors, 0 warnings, 0 notes |

7개 테스트는 실제 봉인 수치, GET-only route, 파일 누락 503, SHA 불일치 503, V4 배선, 세 Gate 분리, 계보/Fold/Exit/접근성 계약을 고정한다.

### 5.2 Frontend

| 검증 | 결과 |
|---|---|
| `npm run typecheck` | exit 0 |
| runtime JSX graph | 138 JSX / 590 graph files PASS |
| `npm run build` | exit 0 |
| bundle | `app.js v=cf4f893c`, `v4.css v=1f7803a7` |

### 5.3 실제 브라우저 사용

정상 진입 주소: `http://127.0.0.1:18833/?tab=research`

| 시나리오 | 결과 |
|---|---|
| 게이트보드 렌더 | 1개, 정상 |
| Platform 표시 | `28/28 VALID` |
| Economic 표시 | `0/7 · STOP` |
| Paired 표시 | `3/7` |
| Holdout 표시 | `SEALED_NOT_TOUCHED` |
| 후보 수 | 7개 |
| 후보 전환 | Absorption → Compression 상세 변경 확인 |
| 1280×720 | 가로 넘침 없음, console warn/error 0 |
| 620×900 | rail/body 1열, 가로 넘침 없음, console warn/error 0 |

`/v4.html` 직접 진입은 지원되는 앱 엔트리가 아니다. 정상 엔트리는 `/`이며 V4 bundle을 shell이 로드한다.

---

## 6. 페이지별 영향

| 페이지 | 이번 변화 | 남은 성숙화 |
|---|---|---|
| 라이브/연구 | 최신 G0/G1 판정이 기존 상세보다 먼저 보임 | Mission Control 아래 상세 접기 |
| 백테스트 | UX-01 Truth Bar·UX-02 Overview와 같은 권위 어휘 사용 | 설계/실행과 결과 분석 분리 |
| 기록 | 이번 변경 없음 | 현재 STOP을 역사 HOF보다 위에 표시 |
| 보고서 | 본 결과 문서가 새 정본 | 대시보드에서 2클릭 내 정본 접근 |
| 성과 | 이번 변경 없음 | 역사 성과 watermark |
| 리플레이 | 이번 변경 없음 | 후보→cohort→trade deep link |
| 연구 자산 | 이번 변경 없음 | authority/last verified |
| 설정 | 실행 정책과 분리 유지 | 현 상태 유지 |
| 용어 | 화면 자체에 해석 문구 제공 | paired Δ/Development Rule deep link |

---

## 7. 성공·실패 판정

| 질문 | 판정 |
|---|---|
| UX-03 구현은 성공했는가 | **예.** 봉인 evidence→API→화면→직접 사용이 연결됐다. |
| G1 연구 실행은 성공했는가 | **예.** 28/28 플랫폼 Gate를 통과했다. |
| G1 전략은 성공했는가 | **아니다.** 개발 규칙 0/7이다. |
| 자율 개선 루프는 의미가 있는가 | **연구 도구로는 가능성 있음.** 한 세대의 생성→실행→부검→자식→재실행→중지를 완주했다. |
| G2를 실행해야 하는가 | **아니다.** 사전등록 중지 조건이 발동했다. |
| Holdout을 열어야 하는가 | **아니다.** Robust 후보가 없다. |

---

## 8. 다음 권장 순서

| 순서 | ID | 작업 | 경계 |
|---:|---|---|---|
| 1 | DOC-04 | 이 결과·핸드오프·INDEX를 정본 브랜치에 통합 | 연구 재실행 없음 |
| 2 | UX-04 | 라이브를 Mission Control + 접힌 상세로 정리 | 실제 STOP 데이터만 사용 |
| 3 | ANA-04 | G0/G1 실패 공통점을 읽기 전용 부검 카드로 묶기 | threshold 변경 없음 |
| 4 | UX-05 | 기록/성과에서 현재 STOP과 역사 HOF 분리 | 과거 성과 재승격 없음 |
| 5 | RES-04 신규 프로그램 | 새로운 구조 가설을 결과 전에 사전등록할 때만 | 기존 G1 미세조정 금지 |

나머지 시총 Band, G2, D4/BO, Holdout, 자동채택은 현재 허용 행동이 아니다.
