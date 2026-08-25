# UX-01 — V4 Global Truth Bar 구현·직접 사용성 검증 결과

> 실행일: 2026-08-26
>
> 실행 브랜치: `codex/process-research-ux-01-global-truth-bar`
>
> 기준선: `codex/process-research-pipeline-restart` @ `52aff9ca`
>
> 연구 실행: **미수행**
>
> 보호 DB·운영 전략 DB write: **없음**

## 1. 결론

UX-01을 구현했다. V4 백테스트 워크벤치 최상단에서 선택한 job의 실행·경제·권위·다음 허용 행동을 한 번에 읽을 수 있다. 색만으로 상태를 표현하지 않고 한국어 라벨, typed code, 차단 사유, legacy identity, 원시 상태와 정정 원인을 함께 노출한다.

직접 사용 중 발견한 결함도 같은 단위에서 교정했다. 기존 결과 라이브러리는 산출물이 없는 취소·오류·시간초과 기록을 비활성화하여 Truth 조회조차 할 수 없었다. 결과 분석 선택과 Truth 선택 상태를 분리해, 열 수 있는 산출물이 없는 종료 기록도 행을 선택하면 결과를 가장하지 않고 Truth Bar만 갱신한다.

## 2. 구현 범위

| 구성 | 역할 | 상태 |
|---|---|---|
| `research-truth-model.mjs` | 4축 code를 한국어 라벨·상세·차단 사유로 변환 | 완료 |
| `research-truth-bar.jsx` | read-only API 조회·접근 가능한 상태 표시·수동 갱신 | 완료 |
| `bt-tab-root.jsx` | result 선택과 truth 선택을 분리하고 V4에 상단 배치 | 완료 |
| `bt-tab-run.jsx` | 산출물 없는 종료 기록도 Truth 확인 가능 | 완료 |
| `v4-backtest.jsx` | V4 정본 셸에만 `showTruthBar` 활성화 | 완료 |
| `v4.css` | 4축 데스크톱·2축 태블릿·1축 모바일 반응형 레이아웃 | 완료 |
| 5상태 JSON fixture | 실제 API·브라우저 반복 검증 가능한 명시적 QA 자료 | 완료 |
| production bundle/manifest/html | JSX 변경을 정식 번들로 재생성 | 완료 |

Legacy 셸에는 V4 전용 Truth Bar를 추가하지 않았다. 연구 엔진, 조건식 생성, 실행 정책, DB 쓰기 경계도 변경하지 않았다.

## 3. 사용자가 보는 정보 순서

| 순서 | 질문 | 화면 응답 |
|---:|---|---|
| 1 | 무엇을 보고 있는가 | candidate와 job identity |
| 2 | 실행은 끝났는가 | `SUCCESS/NO_TRADES/ERROR/TIMEOUT/CANCELLED/PARTIAL` |
| 3 | 경제 판단이 가능한가 | `INCONCLUSIVE/NOT_EVALUABLE` 등 별도 축 |
| 4 | 이 증거의 권위는 무엇인가 | 현재 legacy job은 `FEASIBILITY` |
| 5 | 지금 무엇을 할 수 있는가 | `DEBUG/REPRODUCE/STRUCTURAL_REVISE` 등 한 행동 |
| 6 | 무엇을 하면 안 되는가 | 상태별 차단 사유 |
| 7 | 원본과 정정은 무엇인가 | raw status, failure cause, correction reason, input hash |

`SUCCESS`도 곧바로 성공 후보로 표시하지 않는다. 표본·강건성 증거가 없으면 경제 상태는 `INCONCLUSIVE`, 권위는 `FEASIBILITY`, 다음 행동은 `REPRODUCE`다.

## 4. 5상태 직접 브라우저 검증

재현 가능한 fixture jobs-dir을 별도 테스트 서버에 연결하고 V4 `/ui/backtest` 화면에서 각 행을 실제로 선택했다.

| fixture | 화면 실행 상태 | 경제 | 권위 | 다음 행동 | 결과 |
|---|---|---|---|---|---|
| `UX_FIXTURE_SUCCESS` | 정상 완료 `SUCCESS` | 판정 유보 | 실행 가능성 | 동일 조건 재현 | PASS |
| `UX_FIXTURE_NO_TRADES` | 정상 무거래 `NO_TRADES` | 평가 불가 | 실행 가능성 | 구조 가설 작성 | PASS |
| `UX_FIXTURE_ERROR` | 실행 오류 `ERROR` | 평가 불가 | 실행 가능성 | 실행 진단 | PASS |
| `UX_FIXTURE_TIMEOUT` | 시간 초과 `TIMEOUT` | 평가 불가 | 실행 가능성 | 실행 진단 | PASS |
| `UX_FIXTURE_PARTIAL` | 부분 증거 `PARTIAL` | 평가 불가 | 실행 가능성 | 동일 조건 재현 | PASS |

모든 상태에서 `LEGACY_INCOMPLETE`, `persistence none`, 상태별 차단 사유가 함께 보였다. fixture 이름은 `UX_FIXTURE_*`로 명시하여 실제 연구 Evidence와 혼동되지 않게 했다.

## 5. 실제 job 직접 사용 결과

현재 worktree의 실제 `webbt_jobs` 6건은 모두 취소 기록이다. 첫 기록 `20260824_232753_기존매수_73311`을 결과 라이브러리에서 선택해 다음을 확인했다.

| 항목 | 관측값 |
|---|---|
| execution | `CANCELLED` |
| economic | `NOT_EVALUABLE` |
| authority | `FEASIBILITY` |
| next action | `REPRODUCE` |
| identity | `LEGACY_INCOMPLETE` |
| persistence | `none` |
| blocker | 완료 증거가 아니므로 KPI와 승격 판단 불가 |

이 검증은 기존 JSON을 읽기만 했으며 상태나 artifact를 수정하지 않았다. 현장 success/error/no-trades 표본은 없으므로 그 네 상태와 partial은 위의 고정 fixture가 UI 검증 권위를 담당한다.

## 6. 반응형·접근성·브라우저 결과

| 검증 | 결과 |
|---|---|
| 1280×800 | 4축 한 줄, sticky, 가로 넘침 없음 |
| 720×800 | 2열, 상단 콘텐츠를 가리지 않도록 relative, 가로 넘침 없음 |
| 560×760 | 1열, 가로 넘침 없음 |
| landmark | `section aria-label="연구 진실 바"` |
| 동적 상태 | `aria-live="polite"` |
| 키보드 | 새로고침 버튼 Enter 동작·focus outline 확인 |
| 색 비의존 | 라벨 + code + 상세 문구를 항상 병기 |
| browser console | warning/error 0건 |

## 7. 검증 영수증

| 검증 | 결과 |
|---|---|
| Truth·frontend·shell·module graph 관련 회귀 | `93 passed` |
| UX-01 집중 fixture | `5 passed` |
| runtime JSX graph | `136 JSX / 587 graph files PASS` |
| missing cross-module imports | `139 files / 396 inventory / 0 violations` |
| production build | PASS, `app.js v=9b83e8bd` |
| TypeScript typecheck | PASS |
| jsdom V1~V7 harness | `allPass=true` |
| Python no-excuse rules | `0 violations` |

전체 unit suite는 이 worktree에 root `node_modules`, `_database/strategy.db`, loop DB fixture가 없고 일부 DB 결합 테스트가 누락 DB를 0-byte 파일로 만들 수 있어 실행하지 않았다. 관련 범위·프로덕션 frontend build·실제 브라우저 검증으로 닫았으며, 누락 인프라를 성공으로 간주하지 않는다.

## 8. 성공·실패·가능성 판정

| 질문 | 판정 | 제한 |
|---|---|---|
| 30초 안에 실행·경제·권위·다음 행동을 구분할 수 있는가 | **성공** | 5상태 직접 선택·실제 취소 기록 확인 |
| 실패 기록을 숨기지 않고 볼 수 있는가 | **성공** | 비활성 행을 Truth-only 선택으로 교정 |
| 결과가 없는 실패를 분석 결과처럼 보이는가 | **아니오** | result state와 truth state 분리 |
| UI가 Evidence를 새로 쓰거나 정정 저장하는가 | **아니오—의도된 경계** | read-only, persistence none |
| 조건식 자율 개선·수익성·OOS가 성공했는가 | **아직 판정 불가** | 이번 단위는 판단 UX만 구현 |
| 모든 분석 페이지가 동일 bundle을 쓰는가 | **아직 아님** | ANA-01·UX-02 대상 |

## 9. 다음 원자 단위

다음은 `ANA-01 — AnalysisBundle v2 schema/builder 초안`이다. UI를 더 넓히기 전에 동일 입력에서 동일 hash를 만드는 read-only 분석 정본을 먼저 정의한다.

완료 조건은 다음과 같다.

1. source/engine/config/data identity와 실행 완전성을 bundle 최상위에 둔다.
2. summary, episode, diagnostics, robustness, decision을 명시적 섹션으로 구분한다.
3. 누락 필드는 `null/NOT_RUN/NOT_EVALUABLE`로 표현하고 0이나 성공으로 합성하지 않는다.
4. 같은 job artifact에서 반복 생성한 bundle canonical hash가 일치한다.
5. success/no-trades/error/timeout/partial fixture를 모두 fail-closed로 처리한다.
6. 새 bundle 생성은 read-only이고 기존 job JSON·CSV·DB를 수정하지 않는다.
