# V3 / V3U / 2U_C 백포트 중간 점검 체크포인트 (v2)

작성일: 2026-05-06
v1 작성 시각: 2026-05-06 21:32:20 +0900 (root) / 21:32:22 +0900 (wt-dev)
v2 갱신: 2026-05-06 (동일일 이내 보강본)
기준 commit: `23924c8ffdede60c52f7dfe6eb4b15101ffa2679`
기준 제목: `V3 전환 전략 기준선을 문서화한다`
기준 시각: `2026-05-05 08:22:40 +0900`
체크포인트 commit (root): `38894912e05517ee443dba57a49dbbd7e74a1b1a`
체크포인트 commit (wt-dev): `8182764e1be54a2f39f5df3b97929d3fe57fe2d5`

## 0. v2 갱신 사유

v1 체크포인트는 현재 위치 고정에 집중했다. v2는 다음 작업자가 즉시 이어가도록 다음을 추가한다.

1. 과거 흐름을 단방향 타임라인으로 시각화한다.
2. 통합 진행률을 page 단위와 ASCII bar로 동시 표기한다.
3. 다음 단계용 OMC / PowerShell 명령을 단계별로 제공한다.
4. 종결까지 남은 모든 단계를 단일 테이블로 합친다.
5. 미래 개발을 더 잘하기 위한 운영 원칙을 영역별로 분리한다.
6. v1과 동일하게 root와 `wt-dev` 양쪽에 미러로 유지한다.

이 갱신은 기능 변경이 아니라 방향 유지 강화 목적이며, runtime 코드는 변경하지 않는다.

## 1. 문서 목적

이 문서는 V3 전환 전략 kick-off 이후 실제로 진행된 `STOM_Version_2`, `STOM_Version_3`, `STOM_Version_3U`, `STOM_Version_2U_C` 작업을 한 자리에서 추적하기 위한 checkpoint이다.

목적은 다음과 같다.

1. `23924c8f` 이후 진행된 V3 / V3U / 2U_C 흐름을 한 문서에서 다시 찾을 수 있게 한다.
2. V3 본편 11페이지가 어디까지 완료되었는지 명확히 한다.
3. 2U_C V3 backport 후속 cycle의 완료, no-op, hold 항목을 분리한다.
4. 다음 작업자가 즉시 이어갈 현재 page와 다음 page를 알 수 있게 한다.
5. `STOM_Version_3U_C`를 만들지 않는다는 원칙과 runtime artifact 미커밋 원칙을 다시 고정한다.
6. 다음 단계용 OMC / PowerShell 명령과 남은 전체 단계 테이블을 제공한다.

## 2. 통합 진행률 한눈 보기

```text
전체        [████████████████████]  100.0%   56 / 56 page  ← BP-001/BP-003 재평가 cycle 완료
────────────────────────────────────────────────────────────
V3 본편     [████████████████████]  100.0%   11 / 11 page
백포트      [████████████████████]  100.0%   30 / 30 page
재정렬      [████████████████████]  100.0%    5 /  5 page  ← 재정렬 cycle 완료
BP-005A     [████████████████████]  100.0%    5 /  5 page  ← BP-005A cycle 완료
BP-001/003 [████████████████████]  100.0%    5 /  5 page  ← final guard 완료
```

계산 기준:

```text
V3 본편 11 page 완료
+ 완료된 backport cycle 30 page (BP 사이클 6건 × 5 sub-page)
+ 재정렬 cycle 5 page 완료
+ BP-005A 적용 cycle 5 page 완료
+ BP-001/BP-003 read-only 재평가 cycle 5 page 완료
= 56 page 완료

전체 정의된 page = 11 + 30 + 5 + 5 + 5 = 56 page
남은 page = 0 page
```

이 v16 체크포인트 갱신은 `2UC-V3-BP-001` / `2UC-V3-BP-003` read-only 재평가 cycle Page 5 final guard 결과를 고정하기 위한 문서 변경이다. runtime code는 변경하지 않는다.

## 3. 워크트리 지도 (HEAD 일치 검증 포함)

| 경로 | branch | 역할 | HEAD | 상태 |
|---|---|---|---|---|
| `STOM_V/` | `STOM_Version_2` | root orchestration / 공식 V2 유지 / V3-2U_C 문서 추적 | `6700047d` 이후 이 BP-001/BP-003 Page 5 commit | clean |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | V2 pyd-free 유지 lane | `09c73048` | clean (현재 휴면) |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | Kiwoom 유지 custom / V3 선별 backport lane | `629689eb` 이후 이 BP-001/BP-003 Page 5 mirror commit | clean |
| `STOM_V.wt-3/` | `STOM_Version_3` | V3 공식 ingress 완료 lane (V3.18) | `7faec937` | clean |
| `STOM_V.wt-3u/` | `STOM_Version_3U` | V3 pyd-free + parity audit 완료 lane | `4aef1cce` | clean |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | archive / transition lane | `cf0e21c1` | active 아님 |

주의:

- `STOM_Version_3U_C`는 아직 만들지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/` runtime/output 파일은 커밋하지 않는다.
- 2U_C의 `backtest/graph/`는 보호 대상 output 폴더로 남겨 둔다.

## 4. 23924c8f 이후 단방향 타임라인

```text
23924c8f  V3 전환 전략 기준선 문서화
   │
   ├── Phase 0~5  V3 worktree / DB seed / upstream ref / slice 계획 고정
   │              82256855, 9e8b7685, f0974285, cecdd2a1, b1da9924
   │
   ├── Phase 6    STOM_Version_3 에 V3.0 → V3.18 공식 반영 (19 commits)
   │              06b70418 → cb4cf6aa → ... → f5975f4c → 7faec937
   │
   ├── Phase 7~10 STOM_Version_3U pyd-free 전환 + parity audit (4 commits)
   │              c04faec0 → d05c132c → 3d8f9c1e → 4aef1cce
   │
   ├── c9dec9a4   V3 / V3U handoff 종결
   │
   ├── Phase 11   2U_C V3 백포트 큐 시작 (allowlist 고정)
   │              9cd88726 → 96049642 → 542d5701
   │
   ├── 백포트 적용  BP-004A → 004B → 004C(no-op) → 002A → 002B → 002C(hold)
   │              e204e0f3, 944bab37, f2f447d1, 76329b3b
   │
   ├── 38894912   root v1 중간 점검 체크포인트 고정
   ├── 8182764e   wt-dev v1 동일 미러
   │
   ├── (이 v2 갱신)  과거 / 미래 / OMC 명령 / 남은 단계 테이블 보강
   │
   ├── 94889cc9  재정렬 cycle Page 4 완료 상태
   ├── 70ad7dd8  재정렬 cycle Page 5 final guard 완료 상태
   ├── 85b92c59  BP-005A 적용 cycle Page 1 read-only 결과 고정
   ├── 85be0e40  BP-005A 적용 cycle Page 2 최소 patch 결정 고정
   ├── f942ed2f  2U_C BP-005A code patch 적용 및 검증
   ├── 1ac3c401  BP-005A 적용 cycle Page 3 검증 결과 고정
   ├── e5f10e19  BP-005A 적용 cycle Page 4 공식 추적 문서 반영
   ├── 5402abd8  BP-005A 적용 cycle Page 5 final guard 완료
   ├── 43f3e6ce  BP-001/BP-003 재평가 cycle Page 1 read-only 결과 고정
   ├── 3e79626b  BP-001/BP-003 재평가 cycle Page 2 판단 결과 고정
   ├── 16697131  BP-001/BP-003 재평가 cycle Page 3 hold 기록 공식화
   ├── 6700047d  BP-001/BP-003 재평가 cycle Page 4 문서 동기화 검증
   └── (이 commit) BP-001/BP-003 재평가 cycle Page 5 final guard 완료
```

## 5. V3 본편 11페이지

```text
V3 kick-off / V3 / V3U 본편
[████████████████████] 100%
11 / 11 완료
```

| Page | 내용 | 상태 |
|---:|---|---|
| 1 | V3 전환 전략 기준선 문서화 | 완료 |
| 2 | AGENTS / docs 진입점 연결 | 완료 |
| 3 | DB seed / 2U pyd 추론 재사용 원칙 정리 | 완료 |
| 4 | V3 worktree 생성 준비 | 완료 |
| 5 | V3 upstream 기준 ref 고정 | 완료 |
| 6 | V3 공식 업데이트 계획 확정 | 완료 |
| 7 | V3.0 ~ V3.18 공식 반영 | 완료 |
| 8 | V3U pyd 제거 경계 고정 | 완료 |
| 9 | V3U pyd-free 구현 | 완료 |
| 10 | V3U parity 감사 | 완료 |
| 11 | V3 / V3U handoff 및 2U_C backport 진입 | 완료 |

## 6. 2U_C V3 백포트 후속 진행

```text
2U_C V3 backport 후속 (BP 사이클 6건)
[████████████████████] 100% (30 / 30 sub-page 완료)
```

| Cycle | 내용 | 상태 | 진행률 |
|---|---|---|---:|
| BP-004A | 시스템로그 ANSI escape 제거 | 완료 | 100% |
| BP-004B | 재무정보 / 웹크롤링 숫자 파싱 보정 | 완료 | 100% |
| BP-004C | chart payload 길이 처리 | no-op 완료 | 100% |
| BP-002A | 차트 봉 폭 계산 보정 | 완료 | 100% |
| BP-002B | DB차트 상태 초기화 | 완료 | 100% |
| BP-002C | 실시간차트 x축 append 조건 | hold 완료 | 100% |

각 cycle은 `(읽기 전용 분석 → mapping 확인 → 적용 또는 no-op/hold 판정 → 검증 → 문서화)` 5 sub-page 단위로 진행된다.

## 7. 현재 진행 페이지 (`BP-001/BP-003` read-only 재평가 cycle 5 page)

```text
현재 cycle: `2UC-V3-BP-001` / `2UC-V3-BP-003` read-only 재평가 cycle
현재 page: Page 5 / 5 완료
다음 page: 최종 handoff 또는 새 후보 ID 기반 별도 cycle
진행률: 100%
남은 page: 0

[████████████████████] 100%
```

| Page | 내용 | 상태 | 진행률 |
|---:|---|---|---:|
| 1 | BP-001/BP-003 기존 문서 근거, V3 diff 규모, 2U_C 파일 mapping read-only 확인 | 완료 | 100% |
| **2** | **BP-001 hold 유지 / BP-003 micro-candidate 분리 가능성 결정** | **완료** | **100%** |
| **3** | **BP-001 hold 확정과 BP-003 이번 cycle 미선정/hold 기록 공식화** | **완료** | **100%** |
| **4** | **root 공식 추적 문서와 2U_C mirror 동기화 검증** | **완료** | **100%** |
| **5** | **final guard / 다음 후보 또는 최종 handoff 안내** | **완료** | **100%** |

Page 5 결론: BP-001/BP-003 재평가 cycle은 hold 완료 상태로 종료한다. root/2U_C clean, release sync 통과, runtime artifact 미추적, `STOM_Version_3U_C` 미생성을 확인했다. 후속 재개는 새 후보 ID와 새 read-only cycle 없이는 시작하지 않는다.
## 8. 백포트 적용 결과 매트릭스

| Backport ID | V3 근거 | 2U_C commit | root 추적 commit | 결과 | 변경 파일 |
|---|---|---|---|---|---|
| `2UC-V3-BP-004A` | V3.03 `3e67661b` | `e204e0f3` | `cf0de0dd` | 완료 | `ui/ui_update_textedit.py` |
| `2UC-V3-BP-004B` | V3.17 `f5975f4c` / V3.18 `7faec937` | `944bab37` | `e7cb4035` | 완료 | `utility/webcrawling.py` |
| `2UC-V3-BP-004C` | V3.03 `3e67661b` | 없음 | `e7beae54` | no-op | — |
| `2UC-V3-BP-002A` | V3.14 `f76222f8` | `f2f447d1` | `58ecac0f` | 완료 | `ui/ui_draw_chart_items.py` |
| `2UC-V3-BP-002B` | V3.03 `3e67661b` | `76329b3b` | `4579096d` | 완료 | `ui/ui_draw_chart_db.py` |
| `2UC-V3-BP-002C` | V3.03 `3e67661b` | 없음 | `0200c855` | hold | — |

## 9. no-op / hold 판정 기록

### 9.1 no-op

| 항목 | 판정 | 이유 |
|---|---|---|
| `2UC-V3-BP-004C` | no-op | 2U_C는 `coin` 인자를 포함한 7/9 chart payload를 유지하지만, V3.03 변경은 6/8 payload를 전제한다. |
| BP-002 crosshair 중복 방지 | no-op | 2U_C에 이미 `not (same_code and same_time)` 조건이 존재한다. |
| BP-005 BounceButton | no-op | 2U_C `ui/set_widget.py`에 이미 동일 기능이 구현되어 있다. |

### 9.2 hold

| 항목 | 판정 | 이유 |
|---|---|---|
| `2UC-V3-BP-002C` | hold | V3는 `same_code and not same_time`에서 x축 append를 수행하지만, 2U_C draw/update 계열은 대부분 `same_code and same_time`에서만 incremental update를 수행한다. |
| `2UC-V3-BP-004D` | hold | DB관리/progressbar 개선은 V3 DB/분석 시스템 전제가 섞여 있어 별도 설계가 필요하다. |
| `2UC-V3-BP-004E` | hold | 프로그램 종료 흐름은 V3 LS receiver 종료 구조와 섞여 있어 Kiwoom 유지 종료 계약 재검토가 필요하다. |
| BP-002 arrow index 음수화 | hold | V3 LS `market_gubun` 구조 의존성이 강하고 2U_C factor map 구조와 충돌할 수 있다. |
| BP-002 LS routing | hold | Kiwoom 유지 lane에 LS routing 조건을 직접 가져오면 안 된다. |
| HOLD-001 분석 시스템 확장 | hold | strategy 신규 구조 / 분석 DB / 설정 UI / runtime 전략 연산이 묶여 있다. |
| HOLD-002 DB 구조 개선 | hold | 거래소별 분리 / PRIMARY KEY / INSERT OR REPLACE는 기존 2U_C DB와 비호환 가능성이 크다. |

## 10. 미진입 후보 재검토 표 (Page 2 작업 대상)

| 후보 | 우선 | 구분 | 다음 확인 방향 | 위험 |
|---|:---:|---|---|---|
| `2UC-V3-BP-001` 백테스트 엔진 안정화 | 1 | Page 2 검토 완료 / hold 우세 | V3 backtest 변경 범위가 V3.02~V3.18 전반에 걸쳐 넓고 2U_C B/S/R custom과 직접 충돌 가능성이 크므로, 즉시 적용하지 않고 특정 함수 단위 증거가 생길 때만 재개 | 2U_C custom 회귀 위험 큼 |
| `2UC-V3-BP-003` Binance/Upbit 안정화 | 2 | Page 2 검토 완료 / 조건부 | Kiwoom 영향은 낮지만 Binance/Upbit 실거래 runtime 영향이 있으므로 mock 가능한 websocket 종료/주문유형 guard 단위만 별도 후보화 | 실거래 runtime 영향 |
| `2UC-V3-BP-005` UI 버튼 / progress 표시 | 3 | Page 2 검토 완료 / 최우선 후보 | BounceButton은 2U_C에 이미 존재하므로 no-op, progressbar 표시 순서/시간 문자열 단축만 BP-005A로 분리 검토 가능 | 거의 no-op 예상 |
| `2UC-V3-BP-004D` | hold | hold | V3 DB/분석 시스템 분리 설계 후 재검토 | 적용 금지 |
| `2UC-V3-BP-004E` | hold | hold | Kiwoom 종료 계약 분리 설계 후 재검토 | 적용 금지 |
## 10.1 Page 2 검토 결과

Page 2는 코드 변경 없이 OMX read-only 명령으로 후보별 위험도를 확인했다.

| 후보 | Page 2 판정 | 근거 | 다음 처리 |
|---|---|---|---|
| `2UC-V3-BP-001` | hold 우세 | V3 backtest 변경은 `backtest/backengine_base.py`, OMS, optimiz, market별 engine까지 넓고 2U_C에는 B/S/R 확장과 legacy parity 보정이 존재한다. | 즉시 적용 금지. 특정 함수 단위 broker-neutral 증거가 있을 때만 새 micro-candidate로 재개 |
| `2UC-V3-BP-003` | 조건부 | Binance/Upbit 파일에 국한되면 Kiwoom 영향은 낮지만 websocket 종료, 주문유형, REST API 변경은 실거래 runtime에 영향이 있다. | mock 가능한 receiver/trader 단일 조건만 별도 후보화 |
| `2UC-V3-BP-005` | 최우선 소형 후보 | `BounceButton`은 2U_C에 이미 있어 no-op이며, V3.16 progressbar 변경은 표시 순서와 시간 문자열 단축 중심이다. | Page 3에서 `2UC-V3-BP-005A` progressbar 표시 보정 후보를 우선 검토 |
| `2UC-V3-BP-004D` | hold 유지 | V3 DB관리/progressbar 개선은 분석 시스템/DB관리 전제가 섞인다. | 별도 설계 전 적용 금지 |
| `2UC-V3-BP-004E` | hold 유지 | V3 LS receiver 종료 흐름과 Kiwoom 유지 종료 계약이 다르다. | 별도 설계 전 적용 금지 |

Page 3의 기본 추천은 `2UC-V3-BP-005A`를 다음 safe micro-candidate로 선택할지 최종 판단하는 것이다. 단, Page 3도 먼저 읽기 전용 diff 확인으로 시작하고, 코드 적용은 별도 Page/cycle로 분리한다.
## 10.2 Page 3 후보 선정 결과

Page 3은 코드 변경 없이 `2UC-V3-BP-005A`를 다음 safe micro-candidate로 선정하는 단계였다. `omx sparkshell`로 V3.16 diff와 2U_C 현재 파일을 재확인했고, `omx explore`도 시도했으나 Windows allowlist harness가 POSIX shell wrapper에 의존해 준비되지 않아 `sparkshell` 근거로 fallback했다.

| 항목 | 내용 |
|---|---|
| 선정 후보 | `2UC-V3-BP-005A` |
| 후보 성격 | progressbar 표시 보정 / 소형 UI 안정화 |
| V3 근거 | `66f90b1d STOM V3.16`, `ui/update_widget/update_progressbar.py` |
| 2U_C 대상 | `ui/ui_update_progressbar.py` |
| BounceButton 판단 | 2U_C `ui/set_widget.py`에 이미 존재하므로 no-op 유지 |
| 적용 후보 범위 | `setRange()` 후 `setValue()` 순서 보정, 경과/남은 시간 문자열을 `str(... )[:-3]` 형식으로 축약 |
| 2U_C 보정점 | V3에는 stock progressbar 중심 변경만 보이지만 2U_C에는 `ss_progressBar_01`과 `cs_progressBar_01` 분기가 모두 있으므로, 적용한다면 stock/coin 양쪽 형식을 일관되게 맞춘다 |
| 제외 범위 | DB관리 다이얼로그 progressbar 추가, 분석 시스템 progressbar, BounceButton 재적용, LS/API/DB/pyd 관련 변경 |
| Page 3 결론 | Page 4에서 root 공식 계획 문서에 `2UC-V3-BP-005A` 선정 결과를 반영한 뒤, 별도 적용 cycle에서 코드 변경 여부를 진행한다 |

Page 3은 후보 선정 단계이므로 runtime 코드를 변경하지 않는다. 다음 Page 4는 이 선정 결과를 `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`와 필요 시 `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`에 반영하는 문서 관리 단계다.
## 10.3 Page 4 공식 문서 반영 결과

Page 4는 Page 3에서 선정한 `2UC-V3-BP-005A`를 root 공식 계획 문서에 반영하는 단계였다. runtime 코드는 변경하지 않고, 다음 적용 cycle이 안전하게 시작될 수 있도록 선정 범위와 제외 범위를 문서화했다.

| 항목 | 내용 |
|---|---|
| 반영 문서 | `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`, `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md` |
| 선정 후보 | `2UC-V3-BP-005A` |
| 공식 반영 내용 | progressbar 표시 보정 후보를 BP-005 하위 micro-candidate로 등록 |
| 적용 전제 | 별도 BP-005A 적용 cycle에서 read-only diff 확인 후 `ui/ui_update_progressbar.py`만 최소 수정 |
| 제외 유지 | BounceButton 재적용, DB관리 다이얼로그 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| 다음 Page | Page 5에서 final guard와 다음 적용 cycle 명령을 안내 |

Page 4 완료 후 전체 진행률은 45/46 page였으며, Page 5에서 final guard와 다음 cycle 안내를 완료하면 재정렬 cycle은 5/5 page 완료 상태가 된다.

## 10.4 Page 5 final guard 및 다음 cycle 안내

Page 5는 재정렬 cycle의 종료 처리 단계다. runtime 코드는 변경하지 않고, root와 2U_C mirror 문서가 같은 방향을 가리키는지 확인한 뒤 다음 실제 적용 cycle을 `2UC-V3-BP-005A`로 고정한다.

| 항목 | Page 5 확인 결과 |
|---|---|
| 전체 page | 46 / 46 완료 |
| 재정렬 cycle | 5 / 5 완료 |
| root 직전 HEAD | `94889cc9` (`2U_C BP-005A 선정 결과를 공식 문서에 반영한다`) |
| 2U_C 직전 HEAD | `31bf760b` (`2U_C 백포트 재정렬 Page 4 결과를 미러에 남긴다`) |
| root status | clean 확인 후 이 문서만 stage |
| 2U_C status | `?? backtest/graph/`만 보호 출력으로 유지, 이 문서만 stage |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/` 미커밋 원칙 유지 |
| 3U_C guard | `STOM_Version_3U_C` 미생성 원칙 유지 |
| 다음 cycle | `2UC-V3-BP-005A` 적용 cycle Page 1 / 5 |

다음 cycle은 문서 갱신이 아니라 실제 코드 적용 가능성을 확인하는 cycle이다. 단, 첫 Page는 반드시 read-only diff 재확인으로 시작한다. `ui/ui_update_progressbar.py` 외 파일이 필요해지거나 LS/API/DB/pyd 결합이 발견되면 즉시 hold로 전환한다.

## 10.5 BP-005A 적용 cycle Page 1 read-only 결과

Page 1은 runtime 코드를 변경하지 않고 `STOM V3.16`의 progressbar 변경 근거와 2U_C 현재 구현을 대조했다. 이 단계의 결론은 BP-005A가 계속 broker-neutral / DB-neutral / pyd-neutral 단일 UI 표시 보정 후보라는 점이다.

| 항목 | Page 1 확인 결과 |
|---|---|
| V3 근거 | `66f90b1d STOM V3.16`, `ui/update_widget/update_progressbar.py` |
| 2U_C 대상 | `ui/ui_update_progressbar.py` |
| 후보 변경 1 | `setRange(0, total_back_count)` 호출을 `setValue(curr_back_count)`보다 먼저 수행 |
| 후보 변경 2 | 경과 시간 / 남은 시간 표시를 `str(... )[:-3]` 형식으로 줄여 초 단위 이하 표시를 단순화 |
| 2U_C 보정 포인트 | V3 diff는 stock progressbar 중심이지만 2U_C에는 `ss_progressBar_01`과 `cs_progressBar_01` 분기가 모두 있으므로 적용 시 stock/coin 양쪽 형식을 일관되게 맞춘다 |
| 제외 유지 | BounceButton, DB관리 다이얼로그 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| Page 1 결론 | Page 2에서 `ui/ui_update_progressbar.py` 단일 파일 최소 patch 여부를 결정한다 |

Page 1에서는 파일을 수정하지 않는다. 다음 Page 2에서 실제 patch를 만들더라도 변경 범위가 단일 UI 파일을 벗어나면 즉시 hold로 전환한다.

## 10.6 BP-005A 적용 cycle Page 2 최소 patch 결정

Page 2는 Page 1에서 확인한 후보를 실제 적용 가능한 최소 patch로 좁히는 단계다. runtime 코드는 아직 변경하지 않고, 다음 Page 3에서 적용할 단일 파일 수정안을 확정한다.

| 항목 | Page 2 결정 |
|---|---|
| 적용 여부 | 적용 진행 |
| 변경 파일 | `C:\System_Trading\STOM\STOM_V.wt-dev\ui\ui_update_progressbar.py` 단일 파일 |
| 적용 변경 1 | `ui.list_progressBarrr[ui.back_scount]`에서 `setRange(0, total_back_count)` 후 `setValue(curr_back_count)` 순서로 변경 |
| 적용 변경 2 | `ui.ss_progressBar_01`에서 시간 문자열을 `str(left_backtime)[:-3]`, `str(remain_backtime)[:-3]`로 단축하고 `setRange()` 후 `setValue()` 순서로 변경 |
| 적용 변경 3 | 2U_C 고유 coin 분기인 `ui.cs_progressBar_01`에도 stock과 동일한 표시 형식 및 `setRange()` / `setValue()` 순서를 적용 |
| 제외 유지 | BounceButton, DB관리 다이얼로그 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| Page 2 결론 | Page 3에서 위 단일 파일 patch를 적용한 뒤 `py_compile`, `diff --check`, `verify_release_sync.py`를 수행한다 |

이 결정은 V3 diff를 파일 단위로 cherry-pick하지 않고 2U_C 구조에 맞춘 최소 수동 이식이다. 특히 V3에는 coin 분기가 없지만 2U_C에는 stock/coin UI가 함께 있으므로, 한쪽만 바꾸는 대신 두 progressbar 표시 계약을 일관되게 맞춘다.

## 10.7 BP-005A 적용 cycle Page 3 patch 적용 및 검증 결과

Page 3은 Page 2에서 확정한 최소 patch를 2U_C에 실제 적용하고 검증한 단계다. code 변경은 2U_C lane의 별도 commit `f942ed2f`로 먼저 고정했고, 이 checkpoint는 그 결과를 root와 2U_C mirror에 기록한다.

| 항목 | Page 3 결과 |
|---|---|
| 2U_C code commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| 변경 파일 | `.gitignore`, `ui/ui_update_progressbar.py` |
| UI 변경 1 | `ui.list_progressBarrr[ui.back_scount]`의 `setRange()` / `setValue()` 순서 보정 |
| UI 변경 2 | `ui.ss_progressBar_01`의 경과/남은 시간 표시를 `str(... )[:-3]`로 단축 |
| UI 변경 3 | 2U_C 고유 `ui.cs_progressBar_01` 분기에도 stock과 같은 표시 형식 및 순서 적용 |
| `.gitignore` 변경 | `backtest/graph/` 보호 규칙 추가. `verify_release_sync.py`가 요구하는 runtime graph 산출물 미커밋 guard다. |
| 제외 유지 | BounceButton, DB관리 다이얼로그 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| 검증 | `py_compile`, `git diff --check`, `git diff --cached --check`, root/2U_C `verify_release_sync.py` 통과 |

검증 후 `STOM_Version_2U_C` status는 clean이며, 기존 `backtest/graph/` 산출물은 `.gitignore` 보호 대상이 되어 더 이상 stage 후보로 노출되지 않는다. 다음 Page 4는 이 code commit과 검증 결과를 공식 추적 문서에 반영하는 단계다.

## 10.8 BP-005A 적용 cycle Page 4 공식 추적 문서 반영 결과

Page 4는 Page 3 code commit `f942ed2f`와 검증 결과를 root 공식 추적 문서에 반영하는 단계다. runtime code는 변경하지 않고, 다음 Page 5 final guard가 같은 근거를 참조할 수 있도록 allowlist와 Phase 11 decision 문서를 갱신했다.

| 항목 | Page 4 결과 |
|---|---|
| 반영 문서 | `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`, `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md` |
| 반영 대상 commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| 공식 상태 | `2UC-V3-BP-005A` 적용 완료 및 검증 완료 |
| 기록한 변경 파일 | `.gitignore`, `ui/ui_update_progressbar.py` |
| 기록한 검증 | `py_compile`, `git diff --check`, `git diff --cached --check`, root/2U_C `verify_release_sync.py` 통과 |
| 제외 유지 | BounceButton, DB관리 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| 다음 Page | Page 5에서 final guard를 수행하고 BP-005A 종료 및 다음 후보 재평가 여부를 결정 |

Page 4 완료 후 BP-005A 적용 cycle은 4/5 page 완료 상태다. 다음 Page 5는 새 코드를 추가하지 않고 최종 guard와 후순위 후보 재평가만 수행한다.

## 10.9 BP-005A 적용 cycle Page 5 final guard 결과

Page 5는 BP-005A cycle을 닫는 final guard 단계다. 새 runtime code는 추가하지 않고, root와 2U_C worktree 상태, release sync, runtime artifact 보호, `STOM_Version_3U_C` 미생성 원칙을 최종 확인했다.

| 항목 | Page 5 final guard 결과 |
|---|---|
| 최종 상태 | `2UC-V3-BP-005A` 완료 |
| 2U_C code commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| root Page 4 commit | `e5f10e19 BP-005A Page 4 공식 추적을 완료한다` |
| 2U_C Page 4 mirror commit | `97221a2a BP-005A Page 4 상태를 2U_C 미러에 남긴다` |
| root status | clean |
| 2U_C status | clean |
| release sync | root/2U_C 모두 `release sync preflight passed` |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| 3U_C guard | `STOM_Version_3U_C` branch 없음 |
| 다음 후보 판단 | BP-001/BP-003은 즉시 적용하지 않고 별도 read-only 재평가 cycle에서만 재검토 |

이 final guard로 51/51 page가 완료됐다. 후속 작업을 계속한다면 새 denominator를 가진 별도 cycle로 시작해야 하며, 첫 단계는 BP-001/BP-003의 위험도와 broker/DB/pyd 결합 여부를 다시 읽기 전용으로 확인하는 것이다.

## 10.10 BP-001/BP-003 재평가 cycle Page 1 read-only 결과

Page 1은 BP-005A 완료 이후 남아 있는 큰 후보인 `2UC-V3-BP-001`과 `2UC-V3-BP-003`을 바로 적용하지 않고, 기존 문서의 hold/조건부 판정이 여전히 유효한지 read-only로 다시 확인하는 단계다. 이 단계에서는 파일을 수정하지 않았고, 다음 Page 2에서 후보를 더 쪼갤 수 있는지만 판단한다.

| 항목 | Page 1 확인 결과 |
|---|---|
| status guard | root clean, 2U_C clean 상태에서 시작 |
| OMX explore | Windows allowlist harness가 POSIX wrapper 의존으로 준비되지 않아 실패, `omx sparkshell`로 fallback |
| BP-001 V3 diff 규모 | `backtest/` 25 files, 1228 insertions, 1341 deletions |
| BP-001 commit 범위 | V3.02~V3.18 전반에 걸쳐 `backengine_base`, OMS, optimiz, market별 engine이 반복 변경됨 |
| BP-001 Page 1 판정 | hold 우세 유지. 2U_C B/S/R custom 및 legacy parity 보정과 충돌 가능성이 커서 broad merge 금지 |
| BP-003 V3 diff 규모 | `trade/binance`, `trade/upbit`, `trade/restapi_binance.py`, `trade/restapi_upbit.py` 8 files, 275 insertions, 374 deletions |
| BP-003 2U_C mapping | V3의 `binance_receiver.py`, `upbit_receiver.py`, root REST 파일과 2U_C의 `*_receiver_min/tick.py`, `upbit_restapi.py`, `binance_websocket.py` 구조가 다름 |
| BP-003 Page 1 판정 | 조건부 유지. Kiwoom 영향은 낮지만 실거래 runtime 영향이 있으므로 Page 2에서 mock 가능한 단일 조건만 분리 |
| 적용 여부 | 없음. Page 1은 read-only evidence commit으로 닫음 |

다음 Page 2는 BP-001을 계속 hold로 둘지 확정하고, BP-003에서 `trade/binance/binance_trader.py`, `trade/upbit/upbit_trader.py`, websocket 종료/주문유형 guard처럼 테스트 가능한 작은 후보가 있는지 좁혀야 한다. root REST 파일 전체 이식, V3 receiver/strategy 파일 단위 cherry-pick, 실거래 API 호출 방식 변경은 Page 2에서도 기본 제외한다.

## 10.11 BP-001/BP-003 재평가 cycle Page 2 판단 결과

Page 2는 Page 1의 diff 규모 확인 이후 실제로 다음 micro-candidate를 분리할 수 있는지 판단하는 단계다. 이 단계도 runtime code는 변경하지 않았고, `omx sparkshell`로 V3 commit/file map과 2U_C 현재 파일 구조를 추가 확인했다.

| 항목 | Page 2 판단 |
|---|---|
| status guard | root clean, 2U_C clean 상태에서 시작 |
| BP-001 최종 판단 | hold 확정. `backtest/` 25 files 변경이 V3.02~V3.18 전반에 걸쳐 있고 2U_C B/S/R custom 및 legacy parity 보정과 충돌할 수 있음 |
| BP-003 V3 변경 범위 | V3.01~V3.18에 걸쳐 receiver, strategy, trader, REST API가 반복 변경됨 |
| BP-003 2U_C 구조 차이 | V3는 `binance_receiver.py`, `upbit_receiver.py`, root `restapi_*.py` 중심이고, 2U_C는 `*_receiver_min/tick.py`, `binance_websocket.py`, `upbit_restapi.py`로 분리되어 있음 |
| trader 후보 검토 | V3 trader diff는 `UI_NUM` 상수화, BaseTrader/MonitorTraderQ 구조 변경, 주문 체결 처리 try/except 제거 등 V3 구조 전제가 섞여 있음 |
| websocket 후보 검토 | V3 REST/websocket diff는 Binance/Upbit websocket 연결 객체명, reconnect, close, 인증 헤더 변경이 함께 묶여 있어 단일 mock 후보로 바로 분리하기 어려움 |
| Page 2 결론 | 이번 cycle에서는 BP-003 적용 후보를 선정하지 않고 hold/no-op 문서화로 전환 |
| 다음 Page | Page 3에서 BP-001 hold 확정과 BP-003 미선정/hold 사유를 공식 기록으로 닫음 |

BP-003은 포기한 것이 아니라, 현재 V3 diff 단위가 2U_C 구조와 맞지 않아 즉시 이식하지 않는다는 의미다. 향후 재개하려면 V3 파일 단위가 아니라 2U_C 파일 기준으로 `websocket close guard`, `REST 응답 예외 처리`, `주문 실패 로그 보정`처럼 별도 mock test가 가능한 더 작은 후보 ID를 새로 만들어야 한다.

## 10.12 BP-001/BP-003 재평가 cycle Page 3 hold 기록 공식화

Page 3은 Page 2 판단을 공식 hold/no-apply 기록으로 고정하는 단계다. 이 단계에서도 runtime code는 변경하지 않았고, BP-001/BP-003을 broad merge하지 않는 결정을 문서화했다.

| 항목 | Page 3 기록 |
|---|---|
| BP-001 최종 상태 | hold 확정 |
| BP-001 hold 사유 | V3 backtest 변경 범위가 25 files로 넓고, `backengine_base`, OMS, optimiz, market별 engine 변경이 2U_C B/S/R custom 및 legacy parity 보정과 충돌할 수 있음 |
| BP-003 최종 상태 | 이번 cycle 적용 후보 미선정 / hold |
| BP-003 hold 사유 | V3 변경이 receiver, strategy, trader, REST API를 함께 바꾸며 2U_C의 `*_receiver_min/tick.py`, `binance_websocket.py`, `upbit_restapi.py` 구조와 1:1 대응하지 않음 |
| 적용 여부 | 없음 |
| 재개 조건 | 2U_C 파일 기준으로 `websocket close guard`, `REST 응답 예외 처리`, `주문 실패 로그 보정`처럼 mock 가능한 단일 조건 후보 ID를 새로 만들 때만 재개 |
| 다음 Page | Page 4에서 root 공식 문서와 2U_C mirror가 같은 결론을 가리키는지 동기화 검증 |

이 기록으로 BP-001/BP-003 재평가 cycle은 적용 후보 선정 단계에서 hold로 전환되었다. Page 4와 Page 5는 새 코드 적용이 아니라 문서 동기화와 final guard만 수행한다.

## 10.13 BP-001/BP-003 재평가 cycle Page 4 문서 동기화 검증

Page 4는 Page 3 hold 기록이 root 공식 문서와 2U_C mirror checkpoint에 일관되게 반영되었는지 검증하는 단계다. 이 단계에서도 runtime code는 변경하지 않았다.

| 항목 | Page 4 검증 결과 |
|---|---|
| root status | clean 상태에서 시작 |
| 2U_C status | clean 상태에서 시작 |
| root 공식 문서 | checkpoint, allowlist, Phase 11 decision 모두 Page 3 hold 기록 포함 |
| 2U_C mirror | Page 4 시작 시점 root checkpoint와 2U_C checkpoint SHA256 hash 일치 |
| BP-001 결론 | hold 확정 유지 |
| BP-003 결론 | 이번 cycle 적용 후보 미선정 / hold 유지 |
| 적용 여부 | 없음 |
| 다음 Page | Page 5 final guard에서 release sync, runtime artifact guard, 3U_C 미생성, 최종 handoff 조건 확인 |

Page 4 후속으로 이 checkpoint를 2U_C mirror에 다시 복사해 Page 4 기록까지 같은 hash가 되도록 만든다. Page 5는 새 판단을 추가하지 않고 최종 guard와 다음 작업 안내만 수행한다.

## 10.14 BP-001/BP-003 재평가 cycle Page 5 final guard 결과

Page 5는 BP-001/BP-003 재평가 cycle을 닫는 final guard 단계다. 이 단계에서도 runtime code는 변경하지 않았고, Page 3~4에서 확정한 hold 결론을 유지했다.

| 항목 | Page 5 final guard 결과 |
|---|---|
| 최종 상태 | BP-001/BP-003 재평가 cycle hold 완료 |
| root status | clean |
| 2U_C status | clean |
| release sync | root/2U_C 모두 `release sync preflight passed` |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| 3U_C guard | `STOM_Version_3U_C` branch 없음 |
| BP-001 결론 | hold 확정 |
| BP-003 결론 | 이번 cycle 적용 후보 미선정 / hold |
| 재개 조건 | 2U_C 파일 기준의 mock 가능한 단일 조건 후보 ID를 새로 만들고 새 read-only cycle Page 1부터 시작 |
| 다음 처리 | 최종 handoff 또는 별도 신규 후보 발굴 cycle |

이 final guard로 BP-001/BP-003 재평가 cycle은 5/5 page 완료로 닫는다. 현 시점의 안전한 기본값은 새 runtime 변경을 추가하지 않고, 전체 V3→3U→2U_C backport 상태를 handoff 문서로 정리하는 것이다.

## 11. 최신 commit 확인

### 11.1 `STOM_Version_2` 최신 10개 (BP-001/BP-003 Page 5 commit 직전)

```text
6700047d BP-001과 BP-003 문서 동기화를 검증한다
16697131 BP-001과 BP-003 hold 기록을 공식화한다
3e79626b BP-001과 BP-003 재평가 Page 2 판단을 고정한다
43f3e6ce BP-001과 BP-003 재평가 Page 1 근거를 고정한다
5402abd8 BP-005A final guard를 완료한다
e5f10e19 BP-005A Page 4 공식 추적을 완료한다
1ac3c401 BP-005A Page 3 검증 결과를 체크포인트에 고정한다
85be0e40 BP-005A Page 2 적용 범위를 확정한다
85b92c59 BP-005A Page 1 근거를 체크포인트에 고정한다
70ad7dd8 2U_C 백포트 재정렬 cycle을 완료 처리한다
```

### 11.2 V3 lane 최신 5개 (`STOM_Version_3`)

```text
7faec937 STOM V3.18
f5975f4c STOM V3.17
66f90b1d STOM V3.16
bbc3fd1d STOM V3.15
f76222f8 STOM V3.14
```

### 11.3 V3U lane 전체 V3U 전용 4개 (`STOM_Version_3U`)

```text
4aef1cce V3U 최종 parity 감사 증적을 고정한다
3d8f9c1e V3U pyd 제거를 실제 코드 경계로 전환한다
d05c132c V3U pyd 대체 검증 발판을 먼저 세운다
c04faec0 V3U pyd 제거 경계를 먼저 고정한다
```

### 11.4 2U_C lane 최신 5개 (`STOM_Version_2U_C`, BP-001/BP-003 Page 5 mirror commit 직전)

```text
629689eb BP-001과 BP-003 동기화 상태를 2U_C 미러에 남긴다
e30694ba BP-001과 BP-003 hold 상태를 2U_C 미러에 남긴다
63cff8ee BP-001과 BP-003 재평가 Page 2 상태를 2U_C 미러에 남긴다
1726a05d BP-001과 BP-003 재평가 Page 1 상태를 2U_C 미러에 남긴다
fc4e37fc BP-005A final guard 상태를 2U_C 미러에 남긴다
```

## 12. branch별 기준 이후 요약

| branch | 기준 이후 요약 | 현재 결론 |
|---|---|---|
| `STOM_Version_2` | V3 전략, V3/V3U handoff, 2U_C backport 추적 문서화 | root orchestration 정상 |
| `STOM_Version_3` | `STOM V3.0` ~ `STOM V3.18` 공식 반영 (19 commits) | 완료 |
| `STOM_Version_3U` | V3 기반 pyd-free 전환 + parity 감사 (4 commits) | 완료 |
| `STOM_Version_2U_C` | Kiwoom 유지 lane에 V3 기능 선별 backport (4 적용 + 1 no-op + 1 hold, BP-005A 완료, BP-001/BP-003 재평가 Page 5 완료) | BP-001/BP-003 hold 완료, 최종 handoff 또는 새 후보 ID 기반 별도 cycle 대기 |

## 13. 다음 단계 OMX / PowerShell 명령

BP-001/BP-003 read-only 재평가 cycle Page 5 final guard는 완료되었다. 다음 작업은 새 code 적용이 아니라 최종 handoff 점검 또는 새 후보 ID 기반 별도 read-only cycle로만 시작한다.

### 13.1 후속 최종 handoff 점검 명령

```powershell
omx sparkshell powershell -NoProfile -Command "Write-Output 'ROOT_STATUS'; git -C C:\System_Trading\STOM\STOM_V status --short; Write-Output 'WTDEV_STATUS'; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short; Write-Output 'ROOT_LOG'; git -C C:\System_Trading\STOM\STOM_V log -8 --oneline; Write-Output 'WTDEV_LOG'; git -C C:\System_Trading\STOM\STOM_V.wt-dev log -8 --oneline; Write-Output 'FINAL_GREP'; git -C C:\System_Trading\STOM\STOM_V grep -n -e '56 / 56 page' -e 'BP-001/BP-003 재평가 cycle hold 완료' -e 'Page 5 final guard 결과' -e '새 후보 ID' -- docs/update_log/2026-05-06_v3_2uc_backport_midpoint_checkpoint.md docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md; Write-Output 'WORKTREES'; git -C C:\System_Trading\STOM\STOM_V worktree list"
```

### 13.2 후속 판단 기준

| 기준 | 처리 |
|---|---|
| 최종 handoff | 전체 완료 상태와 hold 목록을 요약 문서로 닫음 |
| 새 후보 재개 | 반드시 새 후보 ID, 새 read-only Page 1, 별도 denominator로 시작 |
| BP-001/BP-003 | 이번 cycle 결론을 바꾸지 않음 |
| runtime code | 새 승인된 적용 cycle 전에는 변경하지 않음 |

### 13.3 코드 변경이 발생할 때의 필수 검증 게이트

| 검증 | 명령 |
|---|---|
| Python syntax | `python -m py_compile <changed-files>` |
| diff whitespace | `git diff --check` / `git diff --cached --check` |
| release preflight | `python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev` |
| runtime artifact guard | `git ls-files -- _database _log '*.db' 'backtest/graph/*'` |

## 14. 전체 page table (확장판)

| # | Cycle | Page | 목표 | 상태 | 진행률 | 실행 위치 |
|---:|---|---:|---|---|---:|---|
| 1 | 재정렬 | 1 | 완료 / no-op / hold / 미진입 inventory | 완료 | 100% | root |
| 2 | 재정렬 | 2 | BP-001 / BP-003 / BP-005 후보 위험도 확인 | 완료 | 100% | root + wt-3, wt-dev |
| 3 | 재정렬 | 3 | 다음 safe micro-candidate 또는 종료 후보 선정 | 완료 | 100% | root |
| 4 | 재정렬 | 4 | 선정 결과 root 문서 반영 | 완료 | 100% | root |
| 5 | 재정렬 | 5 | commit / final guard / 다음 cycle 안내 | 완료 | 100% | root + wt-dev |
| 6 | BP-005A | 1 | progressbar 적용 전 read-only diff 재확인 | 완료 | 100% | wt-3 ↔ wt-dev |
| 7 | BP-005A | 2 | `ui/ui_update_progressbar.py` 최소 patch 여부 결정 | 완료 | 100% | wt-dev |
| 8 | BP-005A | 3 | 최소 patch 적용 + py_compile + diff check + release sync 검증 | 완료 | 100% | wt-dev |
| 9 | BP-005A | 4 | 공식 추적 문서 반영 및 root/2U_C mirror commit | 완료 | 100% | wt-dev → root |
| 10 | BP-005A | 5 | final guard / 다음 후보 재평가 | 완료 | 100% | root + wt-dev |
| **11** | **BP-001/BP-003** | **1** | **기존 문서 근거, V3 diff 규모, 2U_C mapping read-only 재확인** | **완료** | **100%** | **root + wt-3 + wt-dev** |
| 12 | BP-001/BP-003 | 2 | BP-001 hold 유지 / BP-003 micro-candidate 분리 가능성 결정 | 완료 | 100% | root + wt-3 + wt-dev |
| **13** | **BP-001/BP-003** | **3** | **BP-001 hold 확정과 BP-003 이번 cycle 미선정/hold 기록** | **완료** | **100%** | **root** |
| **14** | **BP-001/BP-003** | **4** | **공식 문서 반영 및 2U_C mirror 동기화 검증** | **완료** | **100%** | **root + wt-dev** |
| **15** | **BP-001/BP-003** | **5** | **final guard / 다음 후보 또는 최종 handoff** | **완료** | **100%** | **root + wt-dev** |
| 16 | 종결 | - | 모든 BP 종료 / HOLD 항목 재확인 / 최종 handoff | 대기 | 0% | root |

조건부: BP-001/BP-003 재평가 cycle은 code 적용 cycle이 아니다. Page 2에서 안전한 micro-candidate가 없으면 Page 3~5는 hold 확정과 최종 handoff 문서화로 축소한다.
## 15. 미래 작업을 더 잘하기 위한 운영 원칙

| 영역 | 원칙 | 위반 시 행동 |
|---|---|---|
| 브랜치 분리 | V3 공식 lane은 upstream `.pyd` 보존 / pyd 제거는 V3U 전용 | 즉시 revert |
| 3U_C 정책 | `STOM_Version_3U_C` 미생성 유지 | 만들지 말 것 |
| 백포트 단위 | 파일 단위 cherry-pick 금지, micro-candidate 단위 수동 이식만 허용 | 후보 분리 후 재시작 |
| Stage 정책 | `git add -A` 금지, 변경 파일 명시 add만 허용 | hunk 단위 stage 재구성 |
| Runtime 보호 | `_database`, `_log`, `*.db`, `backtest/graph/` stage 금지 | 즉시 unstage |
| 검증 게이트 | py_compile + git diff --check + verify_release_sync.py | 실패 시 commit 차단 |
| 결합 변경 차단 | LS / DB / pyd 결합 변경이 한 commit에 있으면 즉시 hold | 후보 재분리 |
| 문서 동기 | root와 active worktree 양쪽에 동일 checkpoint 미러 | 미러 누락 시 commit 보강 |
| 커밋 메타 | 한국어 본문, Constraint / Rejected / Confidence / Directive / Tested 라인 유지 | 본문 보강 후 amend 금지, 신규 커밋으로 보강 |
| 위험도 분리 | 위험도가 다른 변경을 한 후보에 묶지 않는다 | 후보 ID 분리 |

## 16. 다음 작업자가 즉시 읽어야 할 문서 우선순위

1. 이 문서 (`docs/update_log/2026-05-06_v3_2uc_backport_midpoint_checkpoint.md`)
2. `docs/update_log/2026-05-06_v3_v3u_final_handoff.md`
3. `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
4. `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`
5. `docs/V3_KICKOFF_READINESS_PLAN.md`
6. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
7. `C:\System_Trading\STOM\STOM_V.wt-3u\docs\V3U_PYD_REMOVAL_PLAN.md`
8. `C:\System_Trading\STOM\STOM_V.wt-3u\docs\update_log\2026-05-06_v3u_final_parity_audit.md`
9. `CLAUDE.md`

## 17. 절대 유지할 원칙

- `STOM_Version_3U_C`는 아직 만들지 않는다.
- V3 공식 lane에는 upstream `.pyd`를 보존한다.
- V3 pyd 제거는 `STOM_Version_3U`에서만 수행한다.
- 2U_C는 V3 branch가 아니라 Kiwoom 유지 custom lane이다.
- 2U_C backport는 broker-neutral / DB-neutral / pyd-neutral micro-candidate만 우선한다.
- LS API 전제, DB migration 전제, chart payload 계약 변경은 별도 설계 전까지 hold한다.
- `git add -A`를 사용하지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/`를 커밋하지 않는다.

## 18. 변경 이력

| 버전 | 일자 | 변경 사항 | 추적 commit |
|---|---|---|---|
| v1 | 2026-05-06 21:32 KST | root와 wt-dev에 동일 미러로 최초 작성 | `38894912` (root), `8182764e` (wt-dev) |
| v2 | 2026-05-06 (당일 내 보강) | 과거 타임라인, 통합 진행률 그래프, OMC 명령, 남은 전체 단계 테이블, 운영 원칙 분리 추가 | `232263b2` (root), `f0bd404c` (wt-dev) |
| v3 | 2026-05-07 | Page 2 후보 위험도 검토 결과를 반영하고 전체 진행률을 43/46으로 갱신 | `ec4c54a3` (root), `94a882b8` (wt-dev) |
| v4 | 2026-05-07 | Page 3에서 BP-005A를 다음 safe micro-candidate로 선정하고 전체 진행률을 44/46으로 갱신 | `6f205232` (root), `f4d13222` (wt-dev) |
| v5 | 2026-05-07 | Page 4에서 BP-005A 선정 결과를 공식 계획 문서에 반영하고 전체 진행률을 45/46으로 갱신 | `94889cc9` (root), `31bf760b` (wt-dev) |
| v6 | 2026-05-07 | Page 5 final guard를 완료하고 재정렬 cycle을 46/46으로 종료 처리, 다음 BP-005A 적용 cycle 진입 명령을 고정 | `70ad7dd8` (root), `114d4000` (wt-dev) |
| v7 | 2026-05-07 | BP-005A 적용 cycle Page 1 read-only 결과를 반영하고 전체 확장 진행률을 47/51로 갱신 | `85b92c59` (root), `13fa5715` (wt-dev) |
| v8 | 2026-05-07 | BP-005A 적용 cycle Page 2 최소 patch 결정 결과를 반영하고 전체 확장 진행률을 48/51로 갱신 | `85be0e40` (root), `0067131e` (wt-dev) |
| v9 | 2026-05-07 | BP-005A 적용 cycle Page 3 patch 적용 및 검증 결과를 반영하고 전체 확장 진행률을 49/51로 갱신 | `f942ed2f` (2U_C code), `1ac3c401` (root), `9672ea9d` (wt-dev) |
| v10 | 2026-05-07 | BP-005A 적용 cycle Page 4 공식 추적 문서 반영 결과를 기록하고 전체 확장 진행률을 50/51로 갱신 | `e5f10e19` (root), `97221a2a` (wt-dev) |
| v11 | 2026-05-07 | BP-005A 적용 cycle Page 5 final guard를 완료하고 전체 확장 진행률을 51/51로 갱신 | `5402abd8` (root), `fc4e37fc` (wt-dev) |
| v12 | 2026-05-07 | BP-001/BP-003 재평가 cycle Page 1 read-only 결과를 고정하고 전체 진행률을 52/56으로 갱신 | `43f3e6ce` (root), `1726a05d` (wt-dev) |
| v13 | 2026-05-07 | BP-001/BP-003 재평가 cycle Page 2 판단 결과를 고정하고 전체 진행률을 53/56으로 갱신 | `3e79626b` (root), `63cff8ee` (wt-dev) |
| v14 | 2026-05-07 | BP-001/BP-003 재평가 cycle Page 3 hold 기록을 공식화하고 전체 진행률을 54/56으로 갱신 | `16697131` (root), `e30694ba` (wt-dev) |
| v15 | 2026-05-07 | BP-001/BP-003 재평가 cycle Page 4 문서 동기화 검증 결과를 고정하고 전체 진행률을 55/56으로 갱신 | `6700047d` (root), `629689eb` (wt-dev) |
| v16 | 2026-05-07 | BP-001/BP-003 재평가 cycle Page 5 final guard를 완료하고 전체 진행률을 56/56으로 갱신 | (이 commit) |
