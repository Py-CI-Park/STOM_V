# V3U pyd→py 배선 최종 감사 (2026-07-12, V3.35 기준)

## 목적

`ui/main_window.pyd`(V3 공식)와 그 pyd-free 대체(`ui/main_window.py`, V3U/3U_C)의 관계,
UI 버튼-핸들러 기능 배선, 코드 전체의 상호 연관성을 기준으로 pyd→py 반영에 누락이
없는지 최종 확인한 기록이다. 기존 통합 게이트(8 stage)에 더해 게이트가 직접 다루지
않는 3개 축을 독립 AST 스캔으로 교차 검증했다.

## 검증 대상 상태

| 항목 | 값 |
|---|---|
| lane/commit | `STOM_Version_3U` V3.35 (`2fb212e2` overlay 이후) |
| V3 공식 pyd | `ui/main_window.pyd` 보존, upstream `refs/heads/V3.00` tip과 sha256 일치 |
| V3U/3U_C tracked `.pyd` | 0건 |

## 1축 — 기존 통합 게이트 (재실행 완료)

| 단계 | 결과 |
|---|---|
| 1_upstream_pyd_evidence ~ 8_attr_inventory_diff | **8/8 PASS** (manifest `.omx/logs/v3u/verify_2026-07-12_v335.json`) |
| pytest tests/v3u | 49 passed |
| attr inventory (strict) | critical=0 warn=0 (`.omx/logs/v3u/attr_inventory_final_audit_20260712.json`) |
| contract manifest 커버리지 | button 229, combobox 65, created_widget 601, dialog 24, event_function 93, referenced_attr 1607, runtime_state 10, tab_or_group 15, table 38 |

## 2축 — 호출 대상 전수 해석 (독립 AST 스캔, 신규)

ui/ 패키지 84개 모듈 전체에 대해, 모든 함수 호출(ast.Call/Name)의 이름을
모듈 로컬 정의 + import(와일드카드 포함, 대상 모듈 top-level defs로 확장) + builtins로
해석하는 NameError 후보 스캔.

| 검사 | 결과 |
|---|---|
| 미해결 호출 대상 (NameError 후보) | **0건** |
| 파싱 실패 모듈 | 0건 (전체 187개 runtime 모듈 파싱 성공) |

## 3축 — 버튼/시그널 핸들러 배선 (신규)

`ui/event_click/*` + `ui/event_activate/*`의 public 핸들러 전수 vs 전체 코드의
참조(Name load + **Attribute 참조** 포함) 대조.

| 검사 | 결과 |
|---|---|
| 미배선(orphan) 핸들러 | **0건** |
| 참고 | 1차 스캔에서 `activated_01~09`, `dactivated_01~02` 11건이 orphan으로 보였으나 전부 `activated_stg.activated_XX(ui)` / `activated_etc.dactivated_XX(ui)` 형태의 모듈 경유 배선으로 확인(set_stg_tap/set_setup_tap/set_dialog_* + update_textedit) — 오탐 |

## 4축 — MainWindow 메서드 계약 (신규)

pyd 대체 본체인 `ui/main_window.py`의 `MainWindow`가 외부 코드가 호출하는
`ui.<name>()` 표면을 모두 제공하는지 대조.

| 표면 | 값 |
|---|---|
| MainWindow 메서드 | 46 |
| MainWindow self attr | 148 |
| 외부 `ui.X =` 할당 (etc.py 등) | 98 |
| **미해결 `ui.<name>()` 직접 호출** | **0건** (Qt 상속 메서드 화이트리스트 적용) |

## 최종 판정

| 질문 | 판정 |
|---|---|
| pyd와의 관계(공식 pyd 보존/유래 추적) | 정상 — V3 공식 pyd upstream 일치, V3U는 `ui/main_window.py` 단일 대체 |
| UI 버튼 기능 배선 누락 | 없음 — click/activated/connect 대상 전부 해석, orphan 0 |
| 코드 전체 연관성(ui.X 계약) | 없음 — referenced_attr 1607 전수, strict critical=0, 미해결 호출 0 |
| **py 개선 업데이트 누락** | **없음 (V3.35 기준 완전)** |

잔여 참고: `ui/create_widget/set_style.py` +1줄(color_hv_bt)은 기지의 V3U 보정분으로
allowlist 정식 등재(A8)만 남음. 기능/배선 누락 아님.

## 재현 명령

```bash
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.35 \
  --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_2026-07-12_v335.json --log-dir .omx/logs/v3u
python scripts/v3u_attr_inventory_diff.py --strict --output .omx/logs/v3u/attr_inventory_final_audit_20260712.json
# 2~4축 AST 스캔은 본 문서 작성 세션의 일회성 스크립트 (결과 0/0/0)
```
