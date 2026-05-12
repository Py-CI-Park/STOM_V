# V3K F1 DB cutover 사전 ralplan 재합의 — Page 029

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| f51 단계 | B1 |
| 선행 완료 | Page 028 / `8ccbd5ed` mid-checkpoint v3 |
| 본 단계 성격 | deliberate-mode 사전 합의와 문서화 |
| 실제 cutover | **금지** |

---

## 0. 결론

```text
F1 DB cutover는 V3K의 첫 운영 DB 영구 변경 후보이므로 곧바로 실행하지 않는다.
Page 029의 합의 결과는 “B2 cutover script/dry-run 작성은 진행 가능, T05 actual cutover는 계속 사용자 승인 gate”다.
LC1 backup-first, LC2 단일 commit + 사용자 명시 승인, LC3 7일 모니터링은 충분하지만, script 단계와 actual cutover 단계는 반드시 분리한다.
다음 단계는 Page 030 / `f1-cutover-script-dryrun` / F1 cutover scripts dry-run이며 운영 _database write 없이 tempfile·dry-run 중심으로만 진행한다.
```

---

## 1. RALPLAN-DR 요약

### 1.1 Principles

1. **복구 가능성이 cutover보다 먼저다** — backup/checksum/rollback 없는 cutover는 금지한다.
2. **script 작성과 실제 실행을 분리한다** — B2는 script와 dry-run만, T05 actual cutover는 별도 사용자 승인 commit이다.
3. **운영 DB는 승인 전까지 immutable이다** — Page 029/030에서는 운영 `_database/` write가 없어야 한다.
4. **Kiwoom runtime은 거래 경계로 보호한다** — DB cutover 논의가 Kiwoom 주문/청산/live runtime으로 번지면 중단한다.
5. **LS 직접 의존은 영구 제외다** — V3K는 Kiwoom 유지 lane이므로 LS Securities REST/TR/REAL 직접 의존을 추가하지 않는다.

### 1.2 Decision drivers

| 우선 | Driver | 이유 |
| ---: | --- | --- |
| 1 | 운영 `_database/` 손상 방지 | cutover는 되돌리기 어려운 영구 변경이다. |
| 2 | cutover 실패 시 복구 시간 최소화 | backup/checksum/rollback script가 먼저 있어야 한다. |
| 3 | 사용자 승인 가시성 | 실제 cutover는 단일 commit과 명시 승인으로만 수행해야 한다. |

### 1.3 Viable options

| 옵션 | 내용 | 장점 | 단점 | 판정 |
| --- | --- | --- | --- | --- |
| A | Page 029에서 합의만 하고 Page 030에서 script/dry-run 작성 | 가장 안전, 운영 DB 무변경 | 실제 cutover까지 한 단계 더 필요 | **채택** |
| B | Page 029에서 script까지 함께 작성 | commit 수 감소 | 합의와 구현이 섞여 gate가 흐려짐 | 기각 |
| C | 곧바로 actual cutover 실행 | 빠름 | 사용자 승인·backup·rollback·모니터링 gate 미충족 | 기각 |
| D | F1을 무기한 보류하고 F3/F4로 이동 | DB 위험 회피 | V3K DB 적용 목표가 지연되고 F5 production read의 후속 경로가 막힘 | 기각 |

---

## 2. ADR

### Decision

F1은 다음처럼 3단계로 분리한다.

1. **B1 / Page 029**: 사전 합의, pre-mortem, expanded test plan 문서화 — 본 commit.
2. **B2 / Page 030**: backup/cutover/rollback script와 dry-run smoke 작성 — 운영 `_database/` write 없음.
3. **T05 actual cutover**: 사용자 명시 승인, backup-first, 단일 commit, 7일 모니터링 조건이 모두 충족될 때 별도 cycle로 실행.

### Consequences

- Page 030으로 script/dry-run 구현은 진행할 수 있다.
- actual cutover는 여전히 `db-cutover-migration` approval-gated 항목으로 남긴다.
- `scripts/verify_release_sync.py`는 2U_C에 사용하지 않고 `scripts/verify_nonrelease_sync.py`를 사용한다.

---

## 3. LC1~LC3 재검토

| invariant | 원문 의미 | Page 029 재검토 결과 | 보강 조건 |
| --- | --- | --- | --- |
| LC1 | cutover 전 운영 `_database/` 전체 backup 필수 | 충분함 | backup script는 dry-run 기본, `--apply`는 실제 승인 cycle에서만 허용 |
| LC2 | cutover commit은 단일 commit + 사용자 명시 승인 | 충분함 | `V3K_CUTOVER_USER_ACK=1` 같은 실행 marker와 commit 본문 승인 기록을 함께 요구 |
| LC3 | cutover 후 7일 모니터링 동안 새 cutover 금지 | 충분함 | monitoring audit가 cutover timestamp를 읽고 7일 미경과 시 실패해야 함 |

---

## 4. Deliberate pre-mortem 3개

### PM1. cutover 도중 power fail

| 항목 | 내용 |
| --- | --- |
| 실패 시나리오 | 운영 DB 일부만 복사된 상태에서 프로세스/PC가 중단된다. |
| 영향 | `_database/`가 mixed state가 되어 read smoke나 runtime 초기화가 실패할 수 있다. |
| 방어 | cutover 전 full backup + checksum manifest를 먼저 생성하고, target write 전 branch/ack/backup-first guard를 통과해야 한다. |
| Page 030 요구 | cutover script는 dry-run에서 tempfile target으로 partial-copy failure를 모사하고 rollback 경로를 증명한다. |
| actual cutover gate | 실패 시 즉시 `rollback_v3k_cutover.py --backup-dir <backup> --apply`를 수행할 수 있어야 한다. |

### PM2. backup 손상 또는 불완전 backup

| 항목 | 내용 |
| --- | --- |
| 실패 시나리오 | backup 디렉터리가 생성됐지만 일부 DB 누락 또는 checksum mismatch가 발생한다. |
| 영향 | cutover 실패 후 rollback source를 신뢰할 수 없다. |
| 방어 | backup manifest에 파일 목록, size, sha256, schema hash를 기록하고 mismatch면 cutover를 시작하지 않는다. |
| Page 030 요구 | checksum mismatch fixture를 만들고 cutover script가 target write 전에 실패하는지 smoke로 확인한다. |
| actual cutover gate | backup manifest와 실제 backup 디렉터리 검증이 모두 PASS여야 한다. |

### PM3. schema drift

| 항목 | 내용 |
| --- | --- |
| 실패 시나리오 | shadow DB schema가 운영 기대치 또는 V3K manifest와 달라 cutover 후 F5/분석 경로가 실패한다. |
| 영향 | production read 또는 analyzer contract가 깨질 수 있다. |
| 방어 | cutover 전/후 schema hash, required table/column, `last_update < backtest_date` invariant를 확인한다. |
| Page 030 요구 | dry-run smoke가 정상 schema와 drift schema를 모두 검사해야 한다. |
| actual cutover gate | post-cutover health smoke와 F5 production read smoke가 통과해야 한다. |

---

## 5. Expanded test plan

| 레벨 | 검증 | PASS 기준 |
| --- | --- | --- |
| Unit | backup manifest writer | 파일 목록, size, sha256, schema hash가 deterministic하게 생성 |
| Unit | checksum mismatch detector | mismatch 시 cutover 전 중단 |
| Unit | branch/ack/backup-first guard | 잘못된 branch, ack 없음, backup-first 없음은 SystemExit |
| Unit | rollback manifest parser | backup manifest를 읽고 누락/손상 항목을 거부 |
| Integration | tempfile backup dry-run | 운영 `_database/`가 아닌 tempfile source/target만 사용 |
| Integration | cutover dry-run | shadow fixture → tempfile target 복사, `mode=ro` sanity read 통과 |
| Integration | rollback dry-run | tempfile target을 backup fixture로 복원 |
| Integration | partial failure simulation | 일부 복사 실패 후 rollback 가능 상태 유지 |
| E2E | actual cutover rehearsal | 현재 금지. 사용자 승인 후 T05 cycle에서만 수행 |
| E2E | post-cutover health | actual cutover 후 schema/F5/VERIFY set 통과 |
| Observability | `.omx/reports` manifest | backup/cutover/rollback/monitor report가 audit trail로 남음 |
| Observability | 7일 monitor audit | 7일 미경과 시 새 cutover 거부, 경과 후 closure 후보로 이동 |

---

## 6. 다음 단계 판정

| 항목 | 판정 |
| --- | --- |
| B2 cutover scripts/dry-run 신설 (`f1-cutover-script-dryrun`) | 진행 가능 |
| T05 actual cutover | 진행 불가, 사용자 명시 승인 필요 |
| 운영 `_database/` write | 진행 불가 |
| DB 파일 commit | 진행 불가 |
| Kiwoom live runtime 변경 | 진행 불가 |
| LS Securities 직접 의존 | 영구 금지 |

---

## 7. Page 030 요구사항

Page 030은 다음 산출물을 만들 수 있다.

| 파일 | 허용 범위 |
| --- | --- |
| `scripts/backup_operational_database.py` | dry-run 기본, actual apply는 별도 승인 전까지 guard |
| `scripts/cutover_v3k_shadow_to_database.py` | dry-run/tempfile target 중심, `V3K_CUTOVER_USER_ACK` 미설정 시 apply 거부 |
| `scripts/smoke_v3k_cutover_dryrun.py` | tempfile fixture만 사용 |
| `scripts/rollback_v3k_cutover.py` | tempfile rollback 검증, 운영 target apply는 gate |
| `.gitignore` | `_database.backup.*` commit 금지 정책 |
| docs/registry | B2 script/dry-run 결과 문서화 |

---

## 8. 검증 기록

본 Page 029는 문서/합의 단계이므로 다음을 검증 대상으로 삼는다.

```powershell
python -m py_compile scripts/audit_v3k_runtime_activation_gap.py scripts/audit_v3k_verify_1b_closure.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph v3k_settings*.json
```

---

## 9. Freeze 정책

- 본 문서는 Page 029의 합의 snapshot이다.
- Page 030에서 script 구현이 시작되더라도 본 문서를 amend하지 않는다.
- actual cutover 승인 조건이 바뀌면 새 update_log로 남긴다.
