# UXR-P3 — IA migration (탭 구조 정리)

- 작성: 2026-07-18
- 브랜치: `uxr-p3-ia` (from `feature/dashboard-hodo-20260717`)

## 1. 변경 (안전·가역 우선 — §10-7 "목적지 없는 삭제 금지" 준수)

- **Bench → 성과(전당) 개명**: `workbench` key·라우팅(`/ui/evolution/workbench`)·콜백(`onOpenWorkbench`)·컴포넌트(`V4Workbench`) 전부 불변, 라벨만 "성과", full "성과 · 명예의 전당", badge HALL.
- **레일 구획**: primary/secondary 그룹 도입.
  - primary(연구 워크스페이스 6): Live · Backtest · Replay · History · 성과 · Alpha.
  - "보조" 구분선 후 secondary(보조 도구): Lab · Audit · Context (opacity 0.68, hover/active 시 1).
- key 불변 → 딥링크·`test_shell_wiring_parity` 파리티·키보드 nav 순서만 재정렬(그룹 순서 반영).

## 2. 스코핑 결정 (정직한 경계)

마스터플랜 최종 IA는 **Audit 거버넌스를 Reports/History로 이전**, Context 드로어 격하, Lab 해체다.
그러나 §10-7은 "새 owner dual-mount + parity 통과 후에만 기존 내비 retire, 삭제를 목적지보다 앞세우지 않는다"를 요구한다.

- Audit 거버넌스의 지정 이전처(**Reports 허브**)는 아직 존재하지 않음(UXR-P7 신설 예정).
- 따라서 P3에서는 **삭제·이전 대신 구획**만 수행 — Audit(freeze/verdict/`/decisions`/export 경계)·Lab·Context 기능·거버넌스 **완전 보존**, 레일에서 보조군으로 시각 강등.
- **완전 이전/해체는 P7에서** Reports 허브를 owner로 신설한 뒤 dual-mount + field-level parity 통과 후 수행한다.

이로써 "6 primary 탭" 명료성은 지금 확보하고, 거버넌스 안전성은 훼손하지 않는다.

## 3. 검증

- 번들 재빌드: app.js `v=1c232e63`.
- 회귀: shell_wiring_parity · v4_lab_workbench_contract · v4_audit_context_contract · v4_ui_foundation 15 통과.
- 실브라우저(2560×1440): 레일 primary 6 + "보조" 구분선 + secondary 3 렌더. 성과 탭 클릭 → "성과 · 명예의 전당" 정상(workbench key 보존). `artifacts/uxr_p3_rail.png`.

## 4. 다음(P4 울트라와이드·반응형)

- 브레이크포인트·그래프 폭·밀도·overflow·접근성 게이트.
- 이후 P5 Live 스테퍼 → P6 Backtest gap → P7 Reports 허브(+Audit 거버넌스 이전·Lab 해체 완료).
