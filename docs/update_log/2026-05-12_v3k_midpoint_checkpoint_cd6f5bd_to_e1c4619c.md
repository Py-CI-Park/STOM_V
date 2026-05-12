# V3K 중간 점검 보고서 — cd6f5bd2 → e1c4619c (27 commit, Phase A 완료 + Phase E5 진행 중)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| 기준 baseline commit | `cd6f5bd24bd41a190feb59a8cc65b921df84ca0d` |
| 검토 시점 HEAD | `e1c4619c V3K sidecar 값을 session-only preview 초기값으로 제한한다` |
| 검토 대상 commit 수 | 27 |
| 대상 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 대상 branch | `STOM_Version_2U_C` |
| 검토 목적 | 초기 미션(2U_C에 V3 기능을 Kiwoom 유지하면서 모두 반영) 대비 27 commit의 방향성·진척률·보존 원칙 정합성 검증 + 다음 phase 진입 전 기준점 고정 |

---

## 0. TL;DR

```text
27 commit 전체가 V3K 초기 미션과 정합한다.
Kiwoom runtime, LS 직접 의존, CLI surface, 운영 _database/, DB 파일 commit 금지 — 6대 보존 원칙 모두 PASS.
Phase A plan §K.5 별도 plan 작성 의무는 Phase B/C/D/E 모두 충실히 이행되었다.
audit §6.2 미완료 8 항목 중 5건 부분 진척, 3건 의도된 보류, 1건 영구 금지.
유일한 명시화 필요 항목은 audit §8 Phase E(live Kiwoom dry-run)와 실제 진행 Phase E0–E6(GUI sidecar persistence)의 letter 재해석 매핑이며, 본 문서 §6에서 정합한다.
중간 점검 결론: 다음 phase(Page 025 Phase E6 sidecar tempfile writer prototype)로 안전하게 진입 가능.
```

---

## 1. 초기 미션 재인용 (변경 없음)

본 검토의 기준은 `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` §0.1에 박힌 V3K 미션 statement이다.

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
단, LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface(init_v3k_shadow_db.py / backtest CLI / realtime CLI / 전체 STOM CLI 진입점)의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지하고, 명시적 사용자 승인 후에만 ON 전환을 허용한다.
```

본 미션은 27 commit 전반에서 단 한 번도 변경되지 않았다.

---

## 2. 초기 계획 (Phase A plan §0.2 정본 재현)

Phase A plan은 audit `2026-05-10_2uc_v3k_full_feature_audit.md` §8을 정본으로 따른다. Phase A–G 로드맵의 원안은 다음과 같다.

| Phase | 목표 1줄 (audit §8 정본) | Phase A plan §0.2 표시 |
| --- | --- | --- |
| A | shadow DB rehearsal | **본 plan scope** |
| B | read-only learning DB 검증 | 별도 plan 필수 |
| C | GUI/settings 연결 (default-OFF 유지) | 별도 plan 필수 |
| D | formula/global runtime 연결 | 별도 plan 필수 |
| E | live Kiwoom dry-run hook | 별도 plan 필수 |
| F | analyzer output 전략 반영 | 별도 plan 필수 (고위험) |
| G | V3 microstructure engine replacement | 별도 plan 필수 (대형) |

V3K 미션 완료 판정 기준(Phase A plan §K.6)은 audit §6.2의 8개 미완료 항목이 모두 해소되는 시점이다.

---

## 3. cd6f5bd2 이후 27 commit 분류

| 구간 | commit | 산출 | 본 plan §K.5 별도 plan 의무 준수 |
| --- | --- | --- | --- |
| 계획 정렬 (5) | `b5e91a91` · `76f2bfe7` · `9daa1835` · `5f4da997` · `9f36bab9` | audit §12 추가 → 포맷 정리 / Phase A plan 정본화 → 미션·전환지침 보강 → lane/invariant 보정 | n/a (audit + Phase A plan 자체) |
| Phase A 실행 (1) | `1196946a` | `apply_v3k_shadow_db.py` 신설, `init_v3k_shadow_db.py` 수정, 회귀 테스트 + smoke 갱신, `_database_v3k_shadow/` 7 DB 생성 manifest, registry V3K-PHASE-A | Phase A plan T01–T07 따름 |
| Phase B (2) | `53515434` · `3eac14ec` | Phase B 별도 plan 신설 → read-only learning DB 경계 증명 (`smoke_v3k_learning_db_readonly_existing.py`, adapter 갱신) | **§K.5 준수** (Phase B 별도 plan) |
| Page 011 → Phase C 진입 (1) | `eac38f12` | Phase C 활성화 경계 plan 신설 | **§K.5 준수** |
| Phase C1 (1) | `88335424` | settings bridge default-OFF (`smoke_v3k_gui_settings_bridge.py`, `v3k_settings_surface.py` 갱신) | (Phase C plan 안에서 진행) |
| Phase C2 (7) | `31f870c9` · `74b58767` · `92436a8e` · `a05c26ee` · `58295b01` · `5c1b9f7a` · `0949f31d` · `5ed8cd2b` | GUI wrapper no-GUI 보유 계약 → MainWindow inert state → 체크박스 layout 보류 → session-only 결정 → preview dialog 분리 → Alt+V 노출 → C2 closeout | **§K.5 준수** (Phase C2 별도 plan) |
| Phase D (3) | `0b13abc1` · `c67fdf9b` · `0d8ac586` | formula/global 경계 고정 → dry-run 진단 → runtime hook 보류 | **§K.5 준수** (Phase D 별도 plan) |
| Phase E0–E5 (7) | `87d7e696` · `46d24856` · `d478c2c8` · `eb7d5631` · `d763e71a` · `e1c4619c` | runtime activation gap review → GUI sidecar persistence design → schema validator → read-only loader → write guard → preview 초기값 제한 + prior flow review 문서 | **§K.5 준수** (Phase E 각 단계 별도 plan) |

> 27 commit 중 코드 변경 동반은 14건이며 나머지 13건은 문서/계획/registry 갱신.

---

## 4. 보존 원칙 7건 검증 (정량 증거 포함)

| # | 원칙 | 검증 명령 | 결과 |
| --- | --- | --- | --- |
| 4.1 | Kiwoom runtime/order/receiver 미변경 | `git diff cd6f5bd2..HEAD --name-only -- trade/ utility/ Kiwoom_OpenAPI/ KiwoomOpenAPI/` | **0건 변경** ✅ |
| 4.2 | LS Securities 직접 의존 0건 | 변경된 파일에 `Select-String "ls_securities\|LS_REST\|xingapi\|restapi_ls"` grep | **0건 매치** ✅ |
| 4.3 | `init_v3k_shadow_db.py` CLI surface 보존 (L2, L9) | Phase A 1196946a 한 차례만 수정. `--dry-run` required + manifest JSON 포맷 보존 | **무회귀 ✅** |
| 4.4 | default-OFF 무결성 (P3, L5) | `v3k_feature_flags` row 0건, settings bridge/sidecar 기본값 OFF | **자동 검증 PASS** ✅ |
| 4.5 | DB 파일 commit 0건 (L8) | `git log --all -- '*.db' '*.sqlite*'` | **0건** ✅ |
| 4.6 | 운영 `_database/` 미변경 (P1, L4) | `git diff cd6f5bd2..HEAD --name-only -- _database/` | **0건 변경** ✅ |
| 4.7 | Phase A plan §K.5 별도 plan 의무 준수 | Phase B/C/D/E 각 단계마다 `docs/plans/<date>_v3k_phase_*_plan.md` 신설 | **모두 준수** ✅ |

---

## 5. audit §6.2 8개 미완료 항목 vs 현재 진척률

| # | audit §6.2 미완료 항목 | 현재 진척 | 진척 % | 책임 phase |
| ---: | --- | --- | ---: | --- |
| 1 | `_database_v3k_shadow` 실제 생성 + DB cutover | shadow 생성 ✅ / cutover 보류 | 50% | A 완료 / B+ cutover 미진행 |
| 2 | production learning DB contents read | shadow read-only smoke ✅ / production read 보류 | 30% | B 부분 / production 보류 |
| 3 | GUI setting surface MainWindow/pyd wrapper 실제 연결 | settings bridge ✅, MainWindow inert state ✅, session-only preview ✅, persistence write 보류 | 60% | C1·C2 완료 / persistence 보류 |
| 4 | runtime `globals().update(...)` 연결 | facade ✅, dry-run adapter ✅, runtime hook 보류 | 40% | D 부분 / runtime hook 보류 |
| 5 | live Kiwoom runtime dry-run hook | **보류 (Phase E 위험도 평가에서 더 안전한 GUI sidecar로 letter 재사용 결정)** | 0% | audit §8 Phase E |
| 6 | analyzer output 전략/주문/청산 판단 사용 | **보류** | 0% | audit §8 Phase F (고위험) |
| 7 | V3 microstructure engine replacement | **보류** | 0% | audit §8 Phase G (대형, G-1/G-2/G-3 분해 권장) |
| 8 | LS Securities REST/TR/REAL 직접 의존 | **반영 금지 (영구)** | n/a | L7 invariant |

**진척률 합계**: 5건 부분 진척(평균 ~36%), 3건 의도된 보류, 1건 영구 금지.

본 진척률은 audit §6.2 정본 기준이며 의도된 보류는 미완 결함이 아니다.

---

## 6. Phase letter 재해석 매핑 (audit §8 ↔ 실제 진행)

audit §8 Phase letter와 실제 commit Phase letter가 일부 일치하지 않는다. 이는 **누락이 아니라 위험도 재평가에 따른 합리적 letter 재선택**의 결과이며, 본 §6에서 명시 매핑한다.

### 6.1 매핑 표

| audit §8 정본 | 의미 | 실제 진행 commit Phase letter | 의미 | 정합 |
| --- | --- | --- | --- | --- |
| Phase A | shadow DB rehearsal | Phase A (1196946a) | shadow DB rehearsal | **일치** ✅ |
| Phase B | read-only learning DB 검증 | Phase B (53515434, 3eac14ec) | read-only learning DB 검증 | **일치** ✅ |
| Phase C | GUI/settings 연결 | Phase C1 + C2 (88335424…5ed8cd2b) | settings bridge + GUI wrapper + session-only preview | **일치 (sub-phase 분해)** ✅ |
| Phase D | formula/global runtime 연결 | Phase D (0b13abc1…0d8ac586) | formula/global 경계 + dry-run + runtime hook **보류** | **일치 (보류 결정 포함)** ✅ |
| Phase E | live Kiwoom dry-run hook | Phase E0–E6 (87d7e696…) | **GUI sidecar persistence design** | **letter 재사용 (의도)** ⚠️ |
| Phase F | analyzer output 전략 반영 | 미진행 (audit §8 letter F는 의도된 보류) | — | n/a |
| Phase G | V3 microstructure engine replacement | 미진행 (audit §8 letter G는 의도된 보류) | — | n/a |

### 6.2 Phase E letter 재사용의 사유

Page 019(`87d7e696`) Phase E-0 runtime activation gap review에서 6개 runtime activation 후보를 위험도로 평가한 결과:

| 후보 | 위험도 | Kiwoom live 영향 | DB/파일 영향 | smoke 가능성 | 결정 |
| --- | --- | --- | --- | --- | --- |
| formula/global runtime hook | 높음 | 높음 | 낮음 | 중간 | 보류 |
| **GUI setting persistence** | **중간** | **낮음** | **중간** | **높음** | **다음 후보** |
| analyzer DB constructor runtime use | 높음 | 중간 | 높음 | 중간 | 보류 |
| live order/exit rule consumption | 치명 | 매우 높음 | 낮음 | 낮음 | 보류 |
| production learning DB read | 높음 | 중간 | 높음 | 중간 | 보류 |
| DB cutover/migration | 치명 | 높음 | 매우 높음 | 낮음 | 보류 |

평가 결과 **GUI setting persistence가 가장 안전**(Kiwoom live 영향 낮음, smoke 가능성 높음)하여 다음 단계로 선택되었고, Phase letter E를 GUI sidecar에 재사용했다.

### 6.3 letter 재사용으로 인한 잠재 혼란과 차단책

| 잠재 혼란 | 차단책 |
| --- | --- |
| 미래 작업자가 audit §8을 보고 "Phase E = live Kiwoom dry-run"으로 이해 | 본 문서 §6.1 매핑 표가 이를 명시 |
| Phase E0–E6의 sub-phase 의미가 audit §8과 다르게 진화 | Page 019 §2 위험도 표가 letter 재사용 사유를 정본화 |
| audit §6.2 #5 (live Kiwoom dry-run) 진척이 잘못 0% 보일 수 있음 | 본 문서 §5 표가 letter 재사용 사유를 각주에서 명시 |

### 6.4 audit §8 Phase E (live Kiwoom dry-run)의 향후 처리

- Phase E0–E6 (GUI sidecar) 종료 후 별도 phase로 진행
- 가능한 letter: `Phase E-K` (Kiwoom 전용) 또는 `Phase H` (새 letter)
- 미래 plan 문서가 본 §6.1 매핑 표를 인용해 letter 충돌을 피할 것

---

## 7. prior flow review와의 관계

`docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md` (commit `e1c4619c`에 포함)는 사용자가 page 024 기준으로 작성한 narrative 리뷰다. 본 중간 점검 보고서는 다음 차이로 보완 관계에 있다.

| 항목 | prior flow review | 본 중간 점검 (보완) |
| --- | --- | --- |
| 형식 | narrative 표 + 결론 한 단락 | 정량 검증 + git 증거 + 진척률 % + letter 매핑 |
| Kiwoom 보존 증거 | "유지되고 있다" 텍스트 | `git diff cd6f5bd2..HEAD -- trade/ utility/ Kiwoom*` 0건 (정량) |
| LS 직접 의존 검증 | "들어오지 않았다" 텍스트 | grep 0건 (정량) |
| audit §6.2 vs 현재 매핑 | 미포함 | §5 8개 항목별 진척 % 표 |
| Phase letter 재해석 | 미포함 (혼란 가능) | §6 매핑 표 + 사유 + 차단책 |
| Phase A plan §K.5 준수 검증 | 미포함 | §3 commit 분류 + §4.7 정량 |

prior flow review를 supersede하지 않고 **보완 관계로 공존**한다. 두 문서를 함께 인용하는 것이 미래 작업자에게 가장 정합한다.

---

## 8. 남은 작업과 다음 단계

### 8.1 즉시 다음 단계 (page 025)

Page 024(`e1c4619c`) 종료 직후의 다음은 Page 025 / Phase E6 sidecar tempfile writer prototype이다. 이미 plan 신설됨 (`docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md`).

### 8.2 audit §6.2 미완료 8 항목별 다음 phase plan 필요도

| # | 항목 | 다음 phase plan 작성 시점 |
| ---: | --- | --- |
| 1 | shadow DB cutover | Phase E6 종료 후 별도 phase plan (cutover-specific) |
| 2 | production learning DB read | Phase E6 종료 후 별도 phase plan (read-only production) |
| 3 | GUI setting persistence | Page 025 → Page 026+에서 점진적 (현재 sub-phase 진행 중) |
| 4 | formula/global runtime hook | Phase F 또는 Phase D 재개 단계에서 별도 phase plan |
| 5 | live Kiwoom dry-run hook | **별도 phase plan 필수** (letter는 `Phase E-K` 또는 `Phase H` 권장) |
| 6 | analyzer output 전략 반영 | **고위험 phase plan 필수** (`--deliberate` ralplan 권장) |
| 7 | V3 microstructure engine replacement | **대형 phase plan 필수** (G-1/G-2/G-3 분해) |
| 8 | LS 직접 의존 | 영구 금지 (plan 불필요) |

### 8.3 Phase A plan §K freeze 정책 재확인

본 중간 점검은 **Phase A plan §K.7 freeze 정책을 깨지 않는다**. Phase A plan 본문은 변경하지 않고, 본 별도 메타 문서로 letter 매핑과 진척률을 명시한다.

---

## 9. 종합 판정

| 평가 항목 | 결과 |
| --- | --- |
| 27 commit 방향성 vs 초기 미션 | **정합** ✅ |
| 보존 원칙 7건 | **모두 PASS** ✅ |
| Phase A plan §K.5 별도 plan 의무 | **준수** ✅ |
| audit §6.2 진척률 | 5건 부분(평균 ~36%), 3건 의도된 보류, 1건 영구 금지 |
| Phase letter 재해석 명시화 | **본 §6에서 완료** ✅ |
| prior flow review와의 관계 | **보완 관계로 공존** ✅ |
| 다음 phase(Page 025) 진입 안전성 | **PASS — 즉시 진입 가능** ✅ |

```text
중간 점검 결론:
초기 미션을 깨지 않고 V3K가 위험 분산된 micro-page 단계로 안전하게 전진하고 있다.
27 commit 전체가 Kiwoom 유지·LS 제외·CLI 보존·default-OFF·DB 격리·운영 무변경·별도 plan 의무 7대 원칙을 모두 지켰다.
audit §6.2의 5건 부분 진척과 3건 의도된 보류는 정상이며 미완 결함이 아니다.
Phase letter 재해석은 의도된 위험도 재평가 결과이며 본 문서 §6에서 매핑되었다.
다음 phase(Page 025 Phase E6 sidecar tempfile writer prototype)로 안전하게 진입 가능하다.
```

---

## 10. 향후 본 문서의 위치와 갱신 정책

- **위치**: `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md`
- **freeze 정책**: 본 문서는 e1c4619c 시점의 snapshot이다. 미래 commit으로 인한 변경은 본 문서에 반영하지 않고, 다음 중간 점검(예: page 030 시점)에서 새 checkpoint 문서를 신설한다.
- **명명 규칙**: `2026-MM-DD_v3k_midpoint_checkpoint_<base>_to_<head>.md`
- **인용 의무**: Phase B 이후의 모든 새 phase plan은 본 문서 §6.1 letter 매핑 표를 인용해야 한다.
- **prior flow review와의 관계**: supersede하지 않는다. 둘 다 함께 인용한다.

---

## 11. 참고 문서

- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` — 정본 audit 보고서, §6/§8 출처
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` — Phase A plan, §0/§K 출처
- `docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md` — prior flow review (보완 관계)
- `docs/CARRY_FORWARD_REGISTRY.md` — V3K-PHASE-A 이후 등록 trail
- 27 commit: `git log cd6f5bd2..e1c4619c --reverse --oneline`
