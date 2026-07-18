# feature/dashboard-hodo-20260717 후속 업데이트 재검토 보고서

- 작성일: 2026-07-18
- 검토 브랜치: `feature/dashboard-hodo-20260717`
- 기준 커밋: `d4708d3e64abeede4d265b8e813efc32b88498f4`
- 최종 검토 커밋: `ae23c8474c979e7b21c4b6552a300301088efef6`
- 선행 보고서: `docs/update_log/2026-07-17_v4_alpha_css_v7_commit_range_review.md`
- 종합 판정: **BLOCK / REQUEST CHANGES 유지**

## 1. 결론

`d4708d3e` 이후 `ae23c847`까지 추가된 두 커밋은 모두 UX 재설계 마스터 플랜 문서의 생성·수정이다. `ai_strategy_loop/dashboard/**`와 `tests/unit/**`에는 변경이 없다. 따라서 직전 검토에서 확인한 Alpha 의미 오류, 파일 읽기 오류 계약, V4 `/runs` 공유 timeout·stale refresh, 파리티·안전 검증 및 정적 지문 판별 문제는 수정되지 않았다.

추가된 마스터 플랜은 향후 UX 방향을 제시하지만 현재 코드의 승인 차단 문제를 해소한 구현 증거가 아니다. 현재 브랜치는 테스트가 통과하더라도 화면 수치 의미와 일부 안전·회귀 계약이 잘못 고정돼 있어 최종 승인할 수 없다.

## 2. 변경 범위

| 커밋 | 변경 | 코드 반영 여부 |
|---|---|---:|
| `9f99b7c9` | V4 UX·UI·프로세스 재설계 마스터 플랜 신규 작성 | 없음 |
| `ae23c847` | D1~D4 결정, Backtest 유지·강화, P1~P8 순서 반영 | 없음 |

`git diff --quiet d4708d3e..HEAD -- ai_strategy_loop/dashboard tests/unit` 결과는 차이 없음(exit 0)이었다. 즉 이번 후속 범위는 문서 1개, 총 242행 추가뿐이다.

## 3. 기존 지적사항 재판정

| 선행 항목 | 현재 상태 | 판정 | 근거 |
|---|---|---:|---|
| Alpha 등록·판정 영수증 선택 | 실제 retrial/gate 파일 선택 유지 | 해결 유지 | `alpha_api.py:63-71`, `332-358` |
| Alpha 번역식 | `expr`/`buy_statement` 표시 유지 | 해결 유지 | `v4-alpha.jsx:193-198` |
| Alpha 봉인 판정 | 정상 JSON+sidecar+SHA 일치 요구 | 해결 유지 | `alpha_api.py:113-137` |
| Alpha polling race | request generation 적용 | 해결 유지 | `v4-alpha.jsx:41-64` |
| Alpha 비-P4 구분 | 상시 경고 배너 유지 | 해결 유지 | `v4-alpha.jsx:86-90` |
| Alpha 측정/게이트 의미 | `measured_ok`를 `gate_passed`로 매핑 | **미해결 High** | `alpha_api.py:375-390` |
| Alpha read-error 계약 | 직접 `read_bytes/read_text`, 오류 무시 잔존 | **미해결 Medium** | `alpha_api.py:119`, `147`, `323-329`, `370-371` |
| V4 `/runs` 동시 중복 | 공용 Promise/TTL 캐시 유지 | 부분 해결 | `runs-shared.jsx:16-35` |
| V4 공유 timeout | 최초 호출자 timeout이 공용 요청 지배 | **미해결 Medium** | `runs-shared.jsx:21-26` |
| V4 종료 refresh | `runsEpoch` 갱신에 `force:true` 없음 | **미해결 Medium** | `dashboard-v4-shell.jsx:168-196` |
| 셸 파리티 | import 도달성 강화, 주석 import 오인 가능 | 부분 해결 | `test_shell_wiring_parity.py:53-76` |
| V4 안전 검증 | 소스 문자열 중심, 실제 렌더·네트워크 검증 부족 | 부분 해결 | `test_v4_default_safety.py:24-57` |
| 정적 캐시 no-store | 미지문 자산 `no-store` | 해결 유지 | `app.py:107-114` |
| 지문 검증 | query에 `v=` 포함만 확인 | **미해결 Medium** | `app.py:103-110` |
| CSS_V7 위험 도구 | `a8ba6c83` revert로 제거 | 해결 유지 | 현재 HEAD에 도구·원장 없음 |

## 4. Alpha 핵심 오류 재확인

현재 authoritative 자료의 의미는 다음과 같다.

| 구분 | 실제 값 | 현재 API/UI 취급 |
|---|---:|---:|
| 봉인/엔진 대상 | 10 | `engine_checked=10` |
| 정상 측정 완료 | 8 | `gate_passed=8` |
| timeout/error | 2 | 검열 2 |
| 개별 성능 게이트 통과 | **0** | 별도 값 없음 |

`rho_retrial_verdict.json`의 `coverage.measured_ok=8`은 정상 측정 수다. 실제 `per_rule`과 `rho_retrial_engine_runs.json`의 10개 `gate_passed`는 모두 false/0이다. 그러므로 `alpha_api.py:378`의 `gate_passed = measured_ok`와 `v4-alpha.jsx:31`의 `측정성공(게이트)` 표기는 연구 의미를 혼합한다.

필수 교정 필드는 다음처럼 분리해야 한다.

- `engine_targeted`: 10
- `engine_attempted`: 10
- `engine_measured_ok`: 8
- `engine_censored`: 2
- `performance_gate_passed`: 0

테스트 `tests/unit/test_alpha_api.py:286-287`도 현재 잘못된 10/8 해석을 기대하므로 함께 수정해야 한다.

## 5. V4 잔여 위험

### 5.1 공용 timeout 소유권

Evolution/Run Compare는 3초, 셸은 15초 timeout을 전달한다. 먼저 캐시 miss를 만든 소비자의 timeout으로 공용 fetch가 생성되므로 3초 소비자가 먼저 시작하면 셸의 15초 요구도 무효화된다. transport timeout은 공용 고정 상한으로 두고 소비자 deadline은 공유 요청을 abort하지 않는 방식으로 분리해야 한다.

### 5.2 run 종료 직후 stale 목록

active→inactive 전이에서 `runsEpoch`는 증가하지만 공유 캐시를 강제로 무효화하지 않는다. TTL 20초 안의 데이터가 있으면 새로 종료된 run이 목록에 나타나지 않을 수 있다. 종료 전이는 `force:true` 또는 명시적 invalidate를 사용해야 한다.
또한 새 refresh가 시작될 때 `runs-shared.jsx:34`는 이전 `data`와 새 `promise`를 함께 저장한다. 이후 일반 호출은 `lines 21-23`에서 `data`를 먼저 반환하므로 진행 중인 최신 refresh에 합류하지 않고 이전 목록을 받을 수 있다. 데이터의 생성 시각과 refresh 시작 시각을 분리하고, 진행 중 promise를 stale data보다 우선해야 한다.

### 5.3 파리티·안전·캐시 검증

- import graph는 raw source에서 import를 찾은 뒤 tag 추출 때만 주석을 제거하므로 주석 처리된 import가 도달 파일로 계산될 수 있다.
- 안전 테스트는 원본 JSX와 번들에서 일부 문자열을 따로 찾으며 실제 V4 mount에 네 안전 문구가 렌더되는지, 승인 없는 POST/WS가 없는지 증명하지 않는다. 기존 `scripts/verify_dashboard_safety_audit.py`의 runtime surface도 legacy/V3 중심이라 정본 V4 탭을 직접 순회하지 않는다.
- `b"v=" in query`는 빈 값·다른 파라미터 값에 포함된 문자열도 1년 immutable로 만들 수 있다. 정확한 query parsing과 비어 있지 않은 허용 hash 형식 검증이 필요하다.

## 6. 검증 기록

실행:

```text
python -m pytest tests/unit/test_alpha_api.py tests/unit/test_v4_default_safety.py tests/unit/test_dashboard_static_cache_headers.py tests/unit/dashboard/test_shell_wiring_parity.py tests/unit/dashboard/test_evolution_analysis_panel.py tests/unit/test_dashboard_live_demo_split.py -q
```

| 검증 | 결과 |
|---|---:|
| 집중 테스트 | **71 passed** |
| 실패 | 0 |
| 경고 | pytest-asyncio loop scope deprecation 1건 |
| 후속 범위 dashboard/tests 코드 차이 | 없음 |
| 추적 파일 미커밋 변경 | 보고서 작성 전 기준 없음 |
| 미추적 자료 | `.gjc/`, `.omo/`, `artifacts/` 다수 — 전수검토 제외 |

테스트 통과는 현재 코드와 테스트의 일치를 뜻할 뿐 `gate_passed` 의미가 맞다는 증거가 아니다. 해당 테스트가 잘못된 의미를 기대하고 있어 의미 오류를 회귀 계약으로 고정한다.

## 7. 승인 조건

1. Alpha 퍼널을 대상/시도/측정완료/검열/성능게이트 통과로 분리하고 실제 자료 기준 `10/10/8/2/0`을 검증한다.
2. present-but-broken authoritative receipt를 이전 파일이나 0으로 축소하지 않고 오류로 노출하며 모든 직접 파일 읽기를 soft-error 계약으로 감싼다.
3. `/runs` 공용 transport timeout과 subscriber deadline을 분리하고 종료 전이 강제 갱신을 동작 테스트로 고정한다.
4. 파리티 import 탐색 전 주석을 제거하고 V4 안전 strip 실제 렌더 및 무승인 mutation 부재를 검증한다.
5. 정적 지문 query를 정확히 파싱·검증한다.
6. 선행 보고서 §4.7의 Alpha current-state·권한·문서 충돌을 최신 정본 문서로 정리한다.

위 조건 전에는 **BLOCK / REQUEST CHANGES**를 유지한다.
