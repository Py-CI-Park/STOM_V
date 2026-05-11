# V3K Page 011 — Phase C-G 활성화 경계 선택 계획

작성일: 2026-05-11 KST  
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`  
대상 branch: `STOM_Version_2U_C`  
직전 기준 commit: `3eac14ec V3K Phase B에서 학습 DB read-only 경계를 증명한다`

---

## 0. 목적

이 문서는 Phase A/B 완료 이후 Page 011에서 **다음 활성화 경계 1개를 선택**하기 위한 계획서다.

V3K 전체 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

이번 문서는 구현 문서가 아니다. 다음 구현 phase를 잘못 선택하면 live runtime, GUI/pyd wrapper, formula globals, 주문·청산 판단이 동시에 흔들릴 수 있으므로, Phase C-G 후보 중 가장 안전한 다음 1개 phase를 고르고 후속 실행 조건을 고정한다.

---

## 1. 현재 완료 상태

| Page/Phase | 상태 | 증거 |
| --- | --- | --- |
| Page 009 / Phase A | 완료 | `_database_v3k_shadow/` DDL-only rehearsal, schema_hash, manifest, health 검증 |
| Page 010 / Phase B | 완료 | temp fixture DB 기반 read-only row-read/leakage/write-rejection smoke |
| Safe-staged V3K | 완료 | analyzer/backtest/realtime/formula/settings surface가 default-OFF, read-only, no-op 경계로 준비됨 |
| Activation | 미완료 | GUI wrapper 연결, formula runtime hook, live Kiwoom dry-run, analyzer output trading 반영은 아직 미진행 |

Phase B 이후 확정된 안전 경계:

1. 운영 `_database/`는 변경하지 않았다.
2. 실제 `_database_v3k_shadow/`는 read-only health/hash 확인만 수행했다.
3. `V3KLearningDataAdapter`는 `?mode=ro` 경로에서 row-read를 검증했다.
4. `last_update < backtest_date` leakage 차단이 검증되었다.
5. Kiwoom live/order runtime은 변경하지 않았다.
6. LS증권 직접 의존성은 추가하지 않았다.

---

## 2. 절대 금지 경계

Page 011에서도 아래는 계속 금지한다.

| 금지 항목 | 이유 |
| --- | --- |
| 운영 `_database/` cutover | DB/schema/data 손상 위험, 별도 backup/rollback/cutover plan 필요 |
| live order/exit decision 반영 | 실제 거래 판단에 영향, 별도 high-risk phase 필요 |
| LS Securities 직접 의존성 | V3K 정의 위반 |
| feature flag default-ON | 기존 2U_C 동작 보존 실패 |
| root `STOM_Version_2` 개발 코드 commit | 공식 V2 lane 오염 |
| V3/3U lane 변경 | 현재 목표는 2U_C V3K 활성화 경계 선택 |
| broad merge | Phase C-G는 한 경계씩 진행해야 rollback 가능 |

---

## 3. 후보 비교

### 3.1 후보 목록

| 후보 | 설명 | 대표 위험 |
| --- | --- | --- |
| A. GUI/settings 연결 | 기존 `strategy/v3k_settings_surface.py`를 실제 설정/GUI 경계로 노출 | MainWindow/pyd wrapper, 설정 저장/불러오기 side effect |
| B. formula/global runtime hook | `V3K_` prefixed facade를 실제 strategy globals에 연결 | `globals().update`, 이름 충돌, 전략식 평가 영향 |
| C. live Kiwoom dry-run preload diagnostic | 실시간 Kiwoom runtime에서 V3K preload diagnostic만 수행 | live event loop, latency, receiver/trader coupling |
| D. analyzer output 전략 반영 | analyzer output을 백테스트/전략 판단에 실제 반영 | 매수·매도·청산 결과 변화, 회귀 범위 폭증 |

### 3.2 위험/효용 matrix

| 후보 | 사용자 가치 | 위험도 | 검증 난이도 | rollback 용이성 | 선택 판단 |
| --- | ---: | ---: | ---: | ---: | --- |
| A. GUI/settings 연결 | 높음 | 중간 | 중간 | 높음 | **선택** |
| B. formula/global runtime hook | 높음 | 높음 | 높음 | 중간 | 보류 |
| C. live Kiwoom dry-run preload diagnostic | 중간~높음 | 높음 | 높음 | 낮음 | 보류 |
| D. analyzer output 전략 반영 | 매우 높음 | 매우 높음 | 매우 높음 | 낮음 | 보류 |

### 3.3 선택 결과

다음 활성화 경계는 **Phase C1 — GUI/settings default-OFF bridge**로 선택한다.

단, “GUI/settings 연결”을 즉시 전체 MainWindow runtime 연결로 해석하지 않는다. 가장 안전한 첫 실행 단위는 다음이다.

```text
Phase C1 = settings surface를 2U_C 설정 경계에 default-OFF로 연결하기 위한 contract/bridge 단계
```

Phase C1의 원칙:

1. `V3K_ANALYSIS_UI_ENABLED`를 포함한 모든 V3K flag는 default-OFF다.
2. UI/setting 경계에서 V3K flag를 인식할 수 있게 하되, ON 전환은 사용자 명시 입력 없이는 발생하지 않는다.
3. Kiwoom receiver/trader/order/exit path는 변경하지 않는다.
4. formula `globals().update`는 아직 연결하지 않는다.
5. live Kiwoom preload diagnostic은 아직 연결하지 않는다.
6. analyzer output을 매수·매도·청산 판단에 사용하지 않는다.
7. pyd-free 2U_C wrapper 경계에서만 검토하고, 공식 V2/V3/3U lane은 변경하지 않는다.

---

## 4. 왜 Phase C1이 가장 안전한가

| 근거 | 설명 |
| --- | --- |
| 이미 contract가 존재 | `strategy/v3k_settings_surface.py`와 `scripts/smoke_v3k_settings_surface.py`가 default-OFF contract를 검증 중이다. |
| live trading 영향이 없다 | 설정 surface 연결은 주문·청산 판단보다 앞단이며 feature flag OFF면 기존 동작이 보존된다. |
| rollback이 쉽다 | 설정 key/bridge/smoke 단위로 되돌릴 수 있다. |
| 후속 phase의 전제다 | formula hook, live dry-run, analyzer output 반영은 모두 flag/setting surface가 먼저 안정화되어야 한다. |
| 검증 가능하다 | QApplication 없이도 dict/setting contract smoke를 만들 수 있고, 필요 시 GUI wrapper smoke는 별도 단계로 분리할 수 있다. |

보류 후보의 이유:

| 후보 | 보류 이유 |
| --- | --- |
| formula/global runtime hook | 실제 `globals().update` 또는 strategy formula 평가 경계에 들어가면 이름 충돌과 runtime side effect가 발생할 수 있다. Phase C1 이후 flag surface가 안정화된 뒤 진행한다. |
| live Kiwoom dry-run preload diagnostic | Kiwoom live event loop와 latency에 닿는다. GUI/settings flag가 먼저 연결되어야 안전하게 ON/OFF 제어할 수 있다. |
| analyzer output 전략 반영 | 거래 판단과 성과가 바뀌는 최고위험 단계다. DB read, GUI flag, formula/runtime hook, dry-run evidence가 모두 쌓인 뒤 별도 high-risk plan으로 진행한다. |

---

## 5. Phase C1 실행 범위

### 5.1 In scope

| 항목 | 설명 |
| --- | --- |
| 설정 key inventory | 기존 2U_C 설정 저장/로드 경계에서 V3K flag가 들어갈 위치 확인 |
| default-OFF bridge | 누락된 V3K key가 있어도 기본값은 항상 False로 보정 |
| non-GUI smoke | QApplication 없이 dict/setting bridge 동작 검증 |
| wrapper 영향 audit | MainWindow/pyd-free wrapper에 필요한 경우에도 default-OFF/no-op만 허용 |
| 문서화 | update_log, carry-forward 필요 시 기록 |

### 5.2 Out of scope

| 항목 | 이유 |
| --- | --- |
| 실제 trading decision 반영 | Phase F/G 후보, 별도 high-risk plan 필요 |
| formula globals runtime 연결 | Phase D 후보, 이름 충돌 검증 필요 |
| live Kiwoom runtime hook | Phase E 후보, live loop/latency 검증 필요 |
| 운영 DB cutover | Phase G 이후 별도 승인 필요 |
| LS API import | V3K 정의 위반 |

---

## 6. Phase C1 상세 실행 계획

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| C1-0 | 설정 저장/로드 경계 inventory | 관련 파일 목록과 실제 변경 후보가 update_log에 기록됨 |
| C1-1 | V3K setting bridge 설계 | `normalize_v3k_settings()` 결과가 기존 `dict_set` 후보와 병합되어도 default-OFF 유지 |
| C1-2 | smoke 추가 | `scripts/smoke_v3k_gui_settings_bridge.py` 또는 동등 script가 no-GUI로 통과 |
| C1-3 | wrapper guard | MainWindow/pyd wrapper를 건드린다면 OFF 상태에서 기존 GUI smoke/audit가 통과 |
| C1-4 | 회귀 검증 | settings smoke, V3K smoke suite, VERIFY-1A/1B, nonrelease sync 통과 |
| C1-5 | 문서/registry/commit | update_log와 필요 시 `CARRY_FORWARD_REGISTRY.md`에 기록 후 commit |

권장 변경 whitelist:

```text
strategy/v3k_settings_surface.py
scripts/smoke_v3k_settings_surface.py
scripts/smoke_v3k_gui_settings_bridge.py
docs/update_log/<date>_v3k_phase_c1_gui_settings_bridge.md
docs/CARRY_FORWARD_REGISTRY.md
```

조건부 변경 후보:

```text
utility/setting.py
ui/set_*.py
ui/ui_button_clicked_*.py
```

조건부 변경은 반드시 inventory 이후에만 허용한다. 특히 `set_*.py`나 `ui_button_clicked_*.py`를 만질 경우 pyd-free wrapper contract를 깨지 않는지 별도 smoke가 필요하다.

---

## 7. Phase C1 검증 계획

최소 검증 명령:

```powershell
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev

python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_formula_facade.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git status --short -- _database/ _database_v3k_shadow/ *.db
```

GUI/wrapper 파일을 실제로 변경한 경우 추가 검증:

```powershell
python scripts/verify_pyd_gui_contract.py
python scripts/smoke_offline_gui.py
```

단, 위 두 script가 현재 worktree에서 사용 가능한지 먼저 확인한다. 없거나 환경 의존성이 있으면 update_log에 사유와 대체 smoke를 기록한다.

---

## 8. rollback plan

| 실패 지점 | rollback |
| --- | --- |
| 설정 key 병합 후 default-ON 발생 | bridge 변경 폐기, `DEFAULT_FLAGS`와 `v3k_settings_defaults()` 비교 smoke 강화 |
| GUI wrapper import 실패 | wrapper 변경만 되돌리고 no-GUI settings bridge로 축소 |
| Kiwoom/runtime audit 실패 | trade/receiver/runtime 변경 여부 확인 후 즉시 revert 또는 commit 중단 |
| DB artifact 발생 | `_database/`, `_database_v3k_shadow/*.db`, `*.db` staged 여부 확인 후 unstage/remove |
| formula/global side effect 발견 | Phase C1 scope 위반으로 중단, Phase D plan으로 분리 |

---

## 9. Page 011 진행률

Page 011은 “Phase C-G 활성화 경계 선택 및 첫 활성화 phase 준비” 페이지다. Phase C1 구현이 완료되었고, 마지막 단계인 “다음 경계 재선택”은 Phase C2 GUI wrapper inventory/plan으로 확정되었다.

| Step | 이름 | 상태 | 진행률 |
| ---: | --- | --- | ---: |
| 011-1 | Phase C-G 후보 비교와 다음 경계 선택 | 완료 | 100% |
| 011-2 | Phase C1 상세 inventory | 완료 | 100% |
| 011-3 | Phase C1 GUI/settings bridge 구현 | 완료 | 100% |
| 011-4 | Phase C1 회귀/audit/문서화 | 완료 | 100% |
| 011-5 | Phase D/E/F/G 중 다음 경계 재선택 | 완료 — Phase C2 선택 | 100% |

Page 011 내부 진행률:

```text
[██████████] 5 / 5 steps = 100%
```

초기 전체 11페이지 기준 진행률:

```text
[███████████] 11 / 11 pages = 100%
```

주의: 위 100%는 “초기 11페이지 계획”의 완료를 의미한다. V3K의 생산 활성화 전체가 완료되었다는 뜻은 아니다. 이후 작업은 Page 012 Phase C2부터 별도 페이지로 이어진다.

---

## 10. Page 012 전환 및 다음 실행 추천 명령

다음 구현 단계는 Phase C2-1이다. 실제 GUI checkbox 또는 persistent DB 저장이 아니라, no-GUI wrapper adapter smoke를 먼저 만든다.

연결 문서:

- `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
- `docs/update_log/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_selection.md`

```powershell
omx ralph "force: V3K Page 012 Phase C2-1 no-GUI GUI-wrapper adapter smoke를 구현한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md를 기준으로 실제 PyQt widget, 운영 _database/setting.db schema/write, _database_v3k_shadow row, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. Phase C1의 bridge_v3k_settings_into_dict_set을 재사용하여 Fake/MainWindow-like object가 V3K settings와 feature_flags를 default-OFF로 안전 보유하는 no-GUI helper와 smoke를 추가한다. 완료 시 py_compile, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, Phase B read-only smoke, 기존 V3K smoke suite, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```

현재 환경에서 `omx ralph`가 `stdin is not a terminal`로 실패하면, 동일 프롬프트를 현재 Codex 세션에서 직접 실행한다.
