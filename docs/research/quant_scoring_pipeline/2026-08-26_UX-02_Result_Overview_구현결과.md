# UX-02 — Result Overview 구현·직접 사용성 검증 결과

> 실행일: 2026-08-26
>
> 실행 브랜치: `codex/process-research-ux-02-result-overview`
>
> 기준선: `codex/process-research-pipeline-restart` @ `213c6825`
>
> 연구 실행: **미수행**
>
> 보호 DB·운영 전략 DB write: **없음**

## 1. 결론

UX-02를 구현했다. V4 결과 분석 화면이 선택 job의 `AnalysisBundle v2`를 직접 읽어, 결과 차트보다 먼저 정체성·실행 완전성·경제 판정·권위·다음 행동·분석 가능성을 보여준다.

결과가 없는 오류·취소·시간초과·부분 기록도 분석 화면에서 사라지지 않는다. 대신 미관측 값을 0으로 보이지 않고 `NOT_RUN` 또는 `NOT_EVALUABLE`로 표시한다. 이 변경은 read-only 조회와 표현 계층만 다루며, 조건식 생성·백테스트 실행·승격·DB 저장은 수행하지 않는다.

## 2. 구현 범위

| 구성 | 역할 | 상태 |
|---|---|---|
| `analysis-bundle-overview-model.mjs` | 4축 Truth와 7개 분석 기능 상태를 사용자 문구로 변환 | 완료 |
| `analysis-bundle-overview.jsx` | bundle identity·완전성·capability·evidence 개요 렌더링 | 완료 |
| `bt-tab-root.jsx` | V4 결과 분석에서 선택한 Truth job을 AnalysisBundle 조회에 연결 | 완료 |
| `v4.css` | 4/2/1축 및 7/2/1 기능 카드 반응형 레이아웃 | 완료 |
| production bundle/manifest/html | 새 JSX를 정식 제공 번들로 재생성 | 완료 |
| frontend 회귀 테스트 | mount 순서·API·상태 문구·접근성·V4 한정 배선 고정 | 완료 |

Legacy 셸과 진화 세대 화면은 이번 단위에서 bundle 개요를 억지로 공유하지 않았다. generation bundle은 전략 소스 hash·엔진/설정/데이터 provenance가 아직 완전하지 않아 계속 fail-closed다.

## 3. 결과 화면의 정보 순서

| 순서 | 사용자 질문 | 화면 응답 |
|---:|---|---|
| 1 | 어떤 분석 정본인가 | AnalysisBundle 버전·strategy identity·content hash·persistence |
| 2 | 실행 증거는 완전한가 | raw status·return code·event·row/trade·checkpoint·failure cause |
| 3 | 성과 판단이 가능한가 | 실행·경제·권위·다음 행동 4축 |
| 4 | 어떤 분석을 실제로 할 수 있는가 | 7개 기능별 `OBSERVED / NOT_RUN / NOT_EVALUABLE` |
| 5 | 무엇으로 재현하는가 | Evidence ID·CSV hash/size·spec hash·prereg·생성시각 출처·content hash |

## 4. 분석 기능 가용성 계약

| 기능 | 관측 가능 조건 | 미관측 표현 |
|---|---|---|
| 핵심 지표 | 완료된 결과의 metrics가 실제 존재 | 실행 미완료면 `NOT_EVALUABLE` |
| 시계열 | 검증된 trade CSV가 존재 | CSV 부재면 `NOT_RUN`, 실행 미완료면 `NOT_EVALUABLE` |
| 분포 | 검증된 trade CSV가 존재 | CSV 부재면 `NOT_RUN`, 실행 미완료면 `NOT_EVALUABLE` |
| 에피소드 | 별도 episode 분석 실행 | 미실행이면 `NOT_RUN` |
| 기여 분석 | 검증된 trade CSV가 존재 | CSV 부재면 `NOT_RUN`, 실행 미완료면 `NOT_EVALUABLE` |
| 반사실 | 별도 counterfactual 실행 | 미실행이면 `NOT_RUN` |
| 강건성 | fold/control/FDR/posterior 실행 | 미실행이면 `NOT_RUN` |

`NOT_RUN`은 실행하지 않았다는 뜻이고, `NOT_EVALUABLE`은 현재 증거로 평가할 수 없다는 뜻이다. 둘 다 0이나 실패 수익률을 의미하지 않는다.

## 5. 직접 브라우저 검증

### 5.1 실제 job

현재 worktree의 취소 기록 `20260824_232753_기존매수_73311`을 실제 결과 라이브러리에서 선택했다.

| 항목 | 관측값 |
|---|---|
| execution | `CANCELLED` |
| economic | `NOT_EVALUABLE` |
| authority | `FEASIBILITY` |
| next action | `REPRODUCE` |
| persistence | `legacy` 자료를 read-only 투영 |
| capability | 평가 불가 5개·미실행 3개 표시 |

원시 artifact를 변경하지 않았고, 결과가 없는 상태에 성과 지표를 합성하지 않았다.

### 5.2 고정 5상태 fixture

| fixture | 실행 상태 | 기능 행렬 | 결과 |
|---|---|---|---|
| `UX_FIXTURE_SUCCESS` | 정상 완료 | 핵심 지표 `OBSERVED` 1·나머지 `NOT_RUN` 6 | PASS |
| `UX_FIXTURE_NO_TRADES` | `NO_TRADES` | 실행 의존 5 `NOT_EVALUABLE`·별도 분석 3 `NOT_RUN` | PASS |
| `UX_FIXTURE_ERROR` | `ERROR` | 실행 의존 5 `NOT_EVALUABLE`·별도 분석 3 `NOT_RUN` | PASS |
| `UX_FIXTURE_TIMEOUT` | `TIMEOUT` | 실행 의존 5 `NOT_EVALUABLE`·별도 분석 3 `NOT_RUN` | PASS |
| `UX_FIXTURE_PARTIAL` | `PARTIAL` | 실행 의존 5 `NOT_EVALUABLE`·별도 분석 3 `NOT_RUN` | PASS |

성공 fixture도 CSV가 없으므로 시계열·분포·기여 분석을 관측됨으로 과장하지 않았다.

## 6. UX·접근성·반응형 결과

| 검증 | 결과 |
|---|---|
| 1280×800 | 4개 판단축·7개 기능 카드 한 줄, 가로 넘침 없음 |
| 720×800 | 판단축 2열·기능 카드 2열, 가로 넘침 없음 |
| 560×800 | 판단축·기능 카드 1열, 가로 넘침 없음 |
| landmark | `region aria-label="분석 번들 개요"` |
| 동적 상태 | `aria-live="polite"` |
| 키보드 | `Bundle 새로고침` Enter 동작 후 선택 상태 유지 |
| 색 비의존 | 한국어 상태·typed code·사유를 함께 표시 |
| browser console | 실제 서버와 fixture 서버 모두 warning/error 0건 |

## 7. 검증 영수증

| 검증 | 결과 |
|---|---|
| UX-02·Truth·AnalysisBundle·shell 관련 회귀 | `47 passed` |
| UX-02 집중 테스트 | `3 passed` |
| runtime JSX graph | `137 JSX / 589 graph files PASS` |
| production build | PASS, `app.js v=d35033a2` |
| TypeScript typecheck | PASS |
| jsdom V1~V7 harness | `allPass=true` |
| Python no-excuse rules | `0 violations` |
| 보호 경로 변경 | 없음 |

## 8. 성공·제한·다음 판단

| 질문 | 판정 | 제한 |
|---|---|---|
| 결과를 보기 전에 증거 완전성과 권위를 알 수 있는가 | **성공** | 실제 취소 job·5상태 fixture 직접 확인 |
| 미실행 분석과 평가 불가를 구분하는가 | **성공** | capability별 code와 사유 표시 |
| 실패 기록도 분석 진입점에서 확인 가능한가 | **성공** | 결과 artifact는 열지 않고 bundle 개요만 표시 |
| 백테스트 후 분석 고도화가 가능한가 | **가능** | CSV·episode·fold evidence가 추가될수록 동일 bundle에 관측 상태로 연결 가능 |
| 강건성·반사실 분석이 완료됐는가 | **아니오** | 현 단계는 `NOT_RUN`; ANA-02 이후 실제 분석 필요 |
| 조건식 자율 개선·수익성·OOS가 성공했는가 | **판정 불가** | 연구 실행을 하지 않았음 |

## 9. 다음 원자 단위

다음은 `RES-01 — <3000 다기간 연구 사전등록`이다. 실행 전에 기간, 후보, seed, source/engine/config/data identity, 비용, 실패 분류, 분석 순서, 중지 조건을 한 커밋으로 봉인한다.

사전등록 커밋이 없거나 필요한 read-only DB 자산을 식별할 수 없으면 `RES-02` 공식 실행은 시작하지 않는다.
