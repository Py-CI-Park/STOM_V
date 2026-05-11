# 2026-05-11 V3K Page 011 활성화 경계 선택 기록

## 1. 작업 목적

Phase A shadow DB rehearsal과 Phase B read-only learning DB 검증이 완료되었으므로, 다음 자동 구현 루프가 live runtime이나 거래 판단으로 너무 빨리 들어가지 않도록 Page 011의 다음 활성화 경계를 먼저 선택했다.

V3K 목적은 계속 다음과 같다.

```text
2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성을 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. 검토한 후보

| 후보 | 판단 |
| --- | --- |
| GUI/settings 연결 | **선택**. 기존 settings surface가 있고 default-OFF/no-GUI 검증부터 시작할 수 있다. |
| formula/global runtime hook | 보류. `globals().update`와 전략식 평가 경계에 닿아 이름 충돌과 runtime side effect 위험이 크다. |
| live Kiwoom dry-run preload diagnostic | 보류. live event loop와 latency 경계에 닿으므로 flag surface 안정화 이후가 안전하다. |
| analyzer output 전략 반영 | 보류. 실제 매수·매도·청산 판단을 바꾸는 최고위험 단계다. |

## 3. 결정

다음 phase는 **Phase C1 — GUI/settings default-OFF bridge**로 정한다.

단, 이 결정은 즉시 전체 GUI runtime 연결을 의미하지 않는다. Phase C1은 먼저 다음 범위로 제한한다.

1. 설정 저장/로드 경계 inventory.
2. V3K settings surface와 기존 설정 dict의 default-OFF 병합/bridge 설계.
3. QApplication 없이 실행 가능한 no-GUI smoke 우선.
4. MainWindow/pyd-free wrapper 변경은 필요성이 확인된 뒤 최소 범위로만 허용.
5. Kiwoom 주문·청산·live runtime, formula globals runtime hook, analyzer output trading decision은 계속 scope 밖.

## 4. 생성 문서

- `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md`

위 문서에 후보 matrix, 선택 사유, Phase C1 scope, 검증 명령, rollback plan, 다음 OMX 명령을 기록했다.

## 5. 안전성 판단

Phase C1을 선택한 이유는 다음과 같다.

| 근거 | 설명 |
| --- | --- |
| 기존 surface 존재 | `strategy/v3k_settings_surface.py`와 `scripts/smoke_v3k_settings_surface.py`가 이미 default-OFF contract를 갖고 있다. |
| live 영향 최소 | 설정 경계는 live 주문·청산 판단보다 앞단이며 OFF 상태에서는 기존 동작을 유지할 수 있다. |
| 후속 phase의 전제 | formula hook, live dry-run, analyzer output 반영은 모두 안전한 flag/setting surface가 먼저 필요하다. |
| rollback 용이 | 설정 key/bridge/smoke 단위로 되돌릴 수 있다. |

## 6. 검증

이번 commit은 계획/문서 commit이며 runtime code를 변경하지 않는다. 따라서 검증은 문서 sanity, V3K audit, nonrelease sync 중심으로 수행한다.

예정 검증:

```powershell
python -c "from pathlib import Path; ..."
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
```

## 7. 다음 작업

다음 작업은 Phase C1 구현이다. 권장 명령은 plan 문서 §10에 기록했다.

핵심 제한:

- 운영 `_database/` 변경 금지
- 실제 `_database_v3k_shadow/` row 변경 금지
- Kiwoom live/order/exit runtime 변경 금지
- formula globals runtime hook 금지
- analyzer output trading decision 반영 금지
- LS Securities 직접 의존성 금지