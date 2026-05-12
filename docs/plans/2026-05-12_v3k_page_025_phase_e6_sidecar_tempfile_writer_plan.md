# V3K Page 025 — Phase E-6 sidecar tempfile-only writer prototype 계획/완료 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_ralph_command_playbook.md`
- `docs/update_log/2026-05-12_v3k_phase_e5_readonly_sidecar_preview_init.md`
- `docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md`

---

## 0. 목적

Page 025의 목적은 repo sidecar actual write가 아니라, Page 023에서 정의한 guard 조건을 만족할 수 있는 writer contract를 **tempfile 안에서만** prototype으로 검증하는 것이다.

이 단계는 actual persistence가 아니다. 운영 `_database/setting.db`, repo `_v3k_sidecar/`, Kiwoom live runtime, analyzer trading decision, formula/global runtime hook은 변경하지 않는다.

---

## 1. 완료 범위

| Step | 작업 | 완료 조건 | 상태 |
| ---: | --- | --- | --- |
| 025-1 | writer contract 설계 | atomic write, backup-before-replace, rollback, corruption recovery 조건 명세 | 완료 |
| 025-2 | tempfile-only prototype | repo `_v3k_sidecar`가 아닌 tempfile directory에서만 writer 후보 검증 | 완료 |
| 025-3 | failure smoke | invalid payload, write failure, corrupt existing file 시 rollback 확인 | 완료 |
| 025-4 | no artifact guard | repo sidecar/DB/runtime artifact 미생성 확인 | 완료 |
| 025-5 | actual write go/no-go | repo sidecar write는 계속 보류하고 다음 단계는 A2/H-1로 결정 | 완료 |

진행률:

```text
Page 025: [████████████████████] 5 / 5 = 100%
```

---

## 2. 구현 결정

- prototype writer는 `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` 내부 smoke helper로만 존재한다.
- `strategy/v3k_gui_sidecar.py`는 계속 read-only validator/loader 모듈로 유지한다.
- writer prototype은 target path가 repo 내부면 실패하도록 강제한다.
- valid payload만 write 후보가 될 수 있고 invalid payload는 파일 생성 전에 reject한다.
- 기존 valid sidecar가 있으면 backup-before-replace를 수행한다.
- replace 실패는 target을 이전 상태로 보존하고 temp file을 제거한다.
- corrupt existing sidecar는 자동 overwrite하지 않고 reject한다.

---

## 3. 검증 기준

| 검증 | 기대 결과 |
| --- | --- |
| invalid payload | target file 미생성, rollback diagnostic |
| first valid write | tempfile 안에서 atomic write 후 read-only loader로 valid 확인 |
| second valid write | `.bak` 생성, backup은 이전 valid state 보존 |
| simulated replace failure | target 내용 불변, temp file leak 없음 |
| corrupt existing file | 기존 corrupt file 보존, overwrite reject |
| artifact guard | repo `_v3k_sidecar`, `_database`, `_log`, `*.db`, `backtest/graph` status clean |

---

## 4. Out-of-scope

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성

---

## 5. 다음 단계

다음 단계는 f51 playbook 추천 순서의 A2, 즉 `Phase H H-1 Kiwoom dry-run hook 모듈 설계`다.

H-1은 KHOPENAPI 호환 환경이 없어도 진행 가능한 낮은 위험 단계다. 다만 H-2/H-3부터는 KHOPENAPI 환경과 사용자 명시 승인이 필요하므로 자동 진행하지 않는다.
