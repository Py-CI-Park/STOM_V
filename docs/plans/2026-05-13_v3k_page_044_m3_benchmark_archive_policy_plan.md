# V3K Page 044 ? M3 benchmark archive policy ?? ??

| ?? | ? |
| --- | --- |
| ??? | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| ?? page | Page 043 / M2 audit runner policy |
| ?? page | Page 044 / M3 benchmark archive policy |
| ?? | `completed-archive-policy` |
| ?? | Phase G parity/benchmark evidence? ?? ??? ??? ???? `.omx/reports` raw artifact commit ?? ??? ????. |
| ??? | medium |
| ON ?? | ??. evidence archive ??? ????. |

---

## 1. ??

M3? Architect addendum?? ??? benchmark baseline archive gap??. Page039? Page043 runner?? Phase G parity/benchmark proof? ???? `.omx/reports/*latest.json`? local evidence? ????. ??? `.omx/reports`? ignored artifact?? ??? commit?? ?? ??? ????.

??? Page044? raw report? commit?? ??? ?? ?? ??? evidence archive ??? ????.

---

## 2. ?? ??

1. `scripts/summarize_v3k_phase_g_evidence.py`? ????.
2. summarizer? `.omx/reports/v3k-phase-g-parity-latest.json`, `.omx/reports/v3k-phase-g-benchmark-latest.json`? ?? commit-safe summary? ????.
3. raw report? commit?? ?? SHA-256, threshold, pass/fail, scenario ??, benchmark ??? ??? ??? ??? ???.
4. `scripts/run_v3k_audit_suite.py`? `phase_g_evidence_summary` ??? ????.
5. VERIFY-1B? `V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY`, `RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED`, summarizer ??? policy doc token? ????? ????.
6. runtime activation gap? ?? ??? `governance-closeout-and-approval-gate`? ????.

---

## 3. Archive policy

- Policy marker: `V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY`
- Raw artifact policy: `RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED`
- `.omx/reports raw artifact commit ??`: raw JSON? ignored/local evidence?? ????.
- Commit ??: docs/update_log summary, threshold, command, SHA-256 hash, pass/fail, scenario/benchmark ??.
- Non-commit ??: `.omx/reports/*.json`, benchmark raw sample, DB, sidecar runtime artifact.

---

## 4. Page044 ?? evidence snapshot

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

## 5. ?? ?? ??

| ?? ?? | Page044 ?? |
| --- | --- |
| `.omx/reports/*.json` raw ?? commit | ?? ?? |
| benchmark threshold ?? | ?? ?? |
| Phase F/G/H ON | ?? ?? |
| enable registry ?? | ?? ?? |
| USER_ACK ?? | ?? ?? |
| Kiwoom live runtime ?? | ?? ?? |
| ?? `_database/` write | ?? ?? |
| DB ?? commit | ?? ?? |
| live order/exit rule ?? | ?? ?? |
| LS Securities ?? ?? ?? | ?? ?? |

---

## 6. ?? ???

?? ???? Page045 / `governance-closeout-and-approval-gate`?.

Page045??? M1/M2/M3 governance hardening ??? ??, ?? ??? ??? ??? ?? gate?? ????? ??.

Directive: Page044? evidence retention policy ???? Phase G ON ?? `.omx/reports` commit ??? ???.
