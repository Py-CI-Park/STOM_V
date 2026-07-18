# F1 — Audit 거버넌스 History 이전 (§10-1 완결, P3 잔여)

- 작성: 2026-07-18 · 브랜치: `f1-audit-governance`

## 변경 (거버넌스 MOVE — 삭제 아님)

P3에서 Audit를 보조군으로 구획했고, P7에서 이전처(Reports/History)가 확보됐다. §10-1/§10-7대로 **거버넌스를 History로 이전 후 Audit 탭 retire**.

- `v4-audit.jsx`: `AuditDecisionTrace` export 추가(파일·`auditDecisionMatches`·VerdictPanel 계약 전부 보존 → `test_v4_audit_context_contract` 무영향).
- `v4-history.jsx`: 새 **"거버넌스 · 결정 원장 · 승급/Export 경계"** 섹션 — `AuditDecisionTrace`(append-only `/decisions`) + `VerdictPanel`(freeze/verdict/export) 마운트.
- `dashboard-v4-shell.jsx`: `V4_TABS`에서 audit 제거(rail retire), V4Audit import·렌더 케이스 제거, `V4_PATH_TAB_MAP` `verdict → history`(딥링크 승계).

## 검증

- 파리티: `test_shell_wiring_parity` 통과 — VerdictPanel·AuditDecisionTrace가 History 경유로 V4 도달(reachability 유지).
- audit 계약: `test_v4_audit_context_contract` 7 통과(파일 보존).
- 실브라우저: 레일에 **Audit 탭 없음**, History "거버넌스" 섹션에 결정 원장(실데이터 1 record·필터: promote/complement/hold/reject) + verdict 렌더. `/ui/evolution/verdict → history` 200. `artifacts/f1_history_governance.png`.
- 번들 v=589379f6.

## 안전성

- 거버넌스 기능(결정 원장·freeze/verdict·human-approval/export 경계) **완전 보존** — 위치만 Audit 탭 → History 섹션. 안전 문구는 상단바 유지.
- 완전 retire 완료(dual-mount 불필요 — 단일 정본 History로 이전, parity 테스트로 도달성 증명).
