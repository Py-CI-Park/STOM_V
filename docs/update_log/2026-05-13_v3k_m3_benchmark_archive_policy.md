# V3K M3 benchmark archive policy ?? ??

| ?? | ? |
| --- | --- |
| ??? | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 044 |
| source | Page043 M2 audit runner policy, Architect addendum M3 |
| ?? | `completed-archive-policy` |
| next candidate | `governance-closeout-and-approval-gate` |

---

## 1. ??

Page041 governance gap triage?? M3? benchmark baseline archive gap?? ?????. Page039? Page043 runner? Phase G parity/benchmark proof? ?????, raw output? `.omx/reports/*latest.json` ??? ??? ?? ??? commit ??? ???.

Page044? ??? `.omx/reports raw artifact commit ??` ??? ??????, ?? ?? ??? evidence summary? ?? ? ?? ??? ??? ??? ???.

---

## 2. ?? ??

### 2.1 Commit-safe summarizer ??

`scripts/summarize_v3k_phase_g_evidence.py`? ????.

- marker: `V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY`
- raw policy: `RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED`
- ??: `.omx/reports/v3k-phase-g-parity-latest.json`, `.omx/reports/v3k-phase-g-benchmark-latest.json`
- ??: JSON ?? Markdown summary
- write side effect: ??
- raw report commit: ?? ??

### 2.2 Audit runner ??

`scripts/run_v3k_audit_suite.py`? `phase_g_evidence_summary` ??? ????. ?? runner? Phase G parity/benchmark report ?? ? ?? summary/hash ??? ????.

### 2.3 VERIFY-1B guard ??

`scripts/audit_v3k_verify_1b_closure.py`? `_assert_benchmark_archive_policy()`? ????.

?? ??? ??? ??.

- `V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY` marker ??
- `RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED` marker ??
- `sha256`, `parity_limit`, `performance_limit`, `raw_reports_committed` token ??
- ? ??? `.omx/reports raw artifact commit ??` ?? ??

### 2.4 Runtime activation gap ??

`scripts/audit_v3k_runtime_activation_gap.py`?? ?? ??? ????.

- `governance-m3-benchmark-archive-policy`: `completed-archive-policy`
- `NEXT_CANDIDATE`: `governance-closeout-and-approval-gate`

---

## 3. Evidence archive policy

| ?? | ?? |
| --- | --- |
| Raw report | `.omx/reports/*.json`? commit?? ???. |
| Commit-safe summary | docs/update_log? command, threshold, pass/fail, SHA-256, scenario/benchmark ??? ????. |
| Hash | raw report bytes? SHA-256? ??? local evidence ??? ???? ????. |
| Threshold | parity `?15%`, performance `+20%` ??? ???? ???. |
| Runtime | broker runtime call, live decision consumption, operating store write, runtime hook connection? ?? false?? ??. |
| DB/sidecar | ?? `_database/`, DB ??, sidecar artifact? commit?? ???. |

---

## 4. Page044 ?? evidence summary

### Parity

- Report: `.omx/reports/v3k-phase-g-parity-latest.json`
- SHA-256: `e3e4861a5b96cb8a20fc58834f686e8602edecac4632656b32fb0a215a4c9189`
- Schema: `v3k-phase-g-parity-v1`
- Generated UTC: `2026-05-13T02:45:40+00:00`
- Passed: `True`
- Parity limit: `0.15`
- Worst relative delta: `0.0`
- Scenarios:
  - `buy_flow`: passed=`True`, signal=`buy`, risk=`MEDIUM`, worst_delta=`0.0`
  - `sell_flow`: passed=`True`, signal=`sell`, risk=`MEDIUM`, worst_delta=`0.0`
  - `balanced_flow`: passed=`True`, signal=`buy`, risk=`MEDIUM`, worst_delta=`0.0`

### Benchmark

- Report: `.omx/reports/v3k-phase-g-benchmark-latest.json`
- SHA-256: `5a5314865b19f8d6988614d0f6920da1014005dba9e0b71a5ec3ab12baaef347`
- Schema: `v3k-phase-g-benchmark-v1`
- Generated UTC: `2026-05-13T02:45:44+00:00`
- Passed: `True`
- Operations: `6000`
- Iterations: `50`
- Elapsed seconds: `2.8136` / max `3.5999999999999996`
- Peak bytes: `231335` / max `9600000`

---

## 5. ????? ?? ?? ?

| ?? | ?? |
| --- | --- |
| `.omx/reports/*.json` raw commit | ?? artifact policy? ????? ????. |
| benchmark threshold ?? | G-2 proof ??? ???? ON ? ?? ??? ????. |
| Phase G ON | explicit user approval, USER_ACK, enable registry, rollback/monitoring gate? ??. |
| Kiwoom live runtime ?? | live decision path? ?? ?? cycle? ????. |
| ?? DB write | DB cutover? ?? approval gate ????. |
| LS Securities ?? ?? | 2U_C ??? ????. |

---

## 6. ?? ??

?? ??? Page045 / `governance-closeout-and-approval-gate`?.

Page045??? M1/M2/M3 governance hardening? ?? ?????? ??, ?? ?? ??? ?? gate?? ???? ??.

Directive: M3 archive policy ??? Phase G ON ???? ???? ???. Raw `.omx/reports` ??? ?? commit?? ???.
