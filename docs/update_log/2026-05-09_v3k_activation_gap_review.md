# V3K activation gap review: safe-staged 완료와 완전 활성화 보류 재검토

- 작성일: 2026-05-09 KST
- 브랜치/워크트리: `STOM_Version_2U_C` / `C:\System_Trading\STOM\STOM_V.wt-dev`
- 성격: 작업 기록, 완료 상태 재정의, 보류 항목 타당성 재검토, 후속 계획 방향성 점검
- 코드 변경: 없음
- 결론: `2U_C V3K safe-staged 목표`는 완료. 단, `완전 활성화`는 완료가 아니며 사용자 승인 후 별도 phase가 필요하다.

## 1. 문서화 목적

본 문서는 다음 질문에 대한 기록이다.

> 그렇다면 V3 기능을 모두 2U_C에 반영 완료했는가?

짧은 답은 다음과 같다.

- **safe-staged 기준**: 완료했다.
- **완전 활성화 기준**: 완료하지 않았다.

여기서 safe-staged란 다음을 뜻한다.

1. V3의 LS증권 직접 의존 기능은 제외한다.
2. 2U_C의 Kiwoom runtime을 유지한다.
3. V3 학습/분석/formula/settings 기능을 adapter, contract, read-only, no-op, default-OFF 형태로 반영한다.
4. 실제 GUI wrapper, live runtime hook, DB cutover, 주문/청산 반영은 사용자 승인 전에는 하지 않는다.

따라서 이 문서의 목적은 **완료된 것과 일부러 완료하지 않은 것**을 구분하고, 일부러 보류한 판단이 타당했는지 재검토하는 것이다.

## 2. 현재 완료 상태 요약

최종 closeout commit:

```text
62d01f07 V3K closeout을 승인 gate로 고정한다
```

핵심 closure commit:

```text
97a4a607 V3K safe-staged 완료 기준을 닫는다
54d3a547 V3K 설정 surface를 기본 OFF 계약으로 고정한다
56aa770a V3K OFF 회귀 검증 기준을 고정한다
```

최종 검증 명령:

```powershell
python scripts\audit_v3k_verify_1b_closure.py
python scripts\audit_v3k_verify_1a.py
python scripts\smoke_v3k_settings_surface.py
python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py --root C:\System_Trading\STOM\STOM_V.wt-dev
python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

검증 결과:

- `V3K VERIFY-1B closure audit passed`
- `v3k verify-1a audit passed`
- `v3k settings surface smoke passed`
- `release sync preflight passed`
- forbidden artifact guard clean

## 3. safe-staged 기준 완료 항목

| 영역 | 완료 상태 | 근거 |
| --- | --- | --- |
| DB/learning 설계 | 완료 | migration spec, schema diff/dry-run/health scripts |
| analyzer module staging | 완료 | V3 analyzer modules staged, import/field-contract smoke |
| AnalyzerRisk adapter | 완료 | default OFF no-signal, ON synthetic smoke |
| backtest learning loader/hook | 완료 | read-only loader, missing-DB no-create diagnostics |
| realtime learning boundary | 완료 | preload boundary, feature flag OFF no-op, missing-DB no-create |
| formula/global facade | 완료 | `V3K_` prefix callable facade, no runtime `globals().update(...)` |
| settings surface contract | 완료 | contract-only setting keys, all default OFF |
| OFF regression audit | 완료 | Kiwoom/runtime untouched, default-OFF, artifact guard, LS marker audit |
| closeout gate | 완료 | STOP / approval gate 문서화 |

## 4. 완전 활성화가 아닌 항목 목록

다음 항목은 **V3 기능 활성화 관점에서는 남아 있는 항목**이다. 그러나 safe-staged 목표에서는 의도적으로 보류했다.

1. MainWindow/pyd wrapper 연결
2. GUI setting surface 실제 연결
3. live Kiwoom runtime dry-run hook
4. runtime `globals().update(...)` 연결
5. analyzer output의 실제 전략식/주문/청산 사용
6. `_database_v3k_shadow` 생성 및 DB cutover
7. production learning DB contents read
8. LS Securities REST/TR/REAL 직접 의존성
9. analyzer DB constructor runtime 사용
10. V3 microstructure engine replacement

## 5. 보류 항목별 상세 재검토

### 5.1 MainWindow/pyd wrapper 연결

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | 이 프로젝트는 V2/2U/2U_C의 pyd-wrapper 계약이 매우 민감하다. MainWindow wrapper, `set_*.py`, `ui_button_clicked_*.py`, activated/clicked 경계는 잘못 건드리면 GUI import/runtime이 깨질 수 있다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **반영하지 않는 것이 맞다**. settings surface contract를 만들었으므로 GUI 연결 전 단계의 준비는 완료되었다. |
| 언제 필요해지는가 | 사용자가 실제 UI에서 V3K flag를 켜고 끄는 화면을 원할 때 필요하다. |
| 선행 조건 | GUI/pyd contract 문서 재확인, offline GUI smoke, wrapper별 변경 범위 지정, rollback plan. |
| 결론 | 자동 진행 금지. 별도 `V3K-GUI-*` phase와 사용자 승인 필요. |

### 5.2 GUI setting surface 실제 연결

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | 현재 `strategy/v3k_settings_surface.py`는 dict/JSON-like 입력 normalize만 수행한다. 이것을 실제 GUI/DB setting에 연결하면 UI event, persistence, DB key migration 문제가 동시에 발생한다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. contract와 smoke로 key/default-OFF를 고정했기 때문에 GUI 연결 전 준비는 충분하다. |
| 언제 필요해지는가 | 사용자가 UI에서 V3K 기능을 조작하거나 저장해야 할 때. |
| 선행 조건 | 설정 저장 위치 결정, DB migration 여부 결정, MainWindow wrapper 영향 평가. |
| 결론 | contract-only 상태 유지가 안전하다. |

### 5.3 live Kiwoom runtime dry-run hook

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | Kiwoom runtime은 실시간 수신, 전략 판단, 주문 큐, 체결 이벤트와 연결된다. dry-run이라도 hook 위치가 잘못되면 latency, 상태 mutation, 주문 조건 변화가 생길 수 있다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **반영하지 않는 것이 맞다**. realtime learning boundary는 준비되어 있고, live runtime 연결은 별도 승인 대상이다. |
| 언제 필요해지는가 | 실제 실시간 데이터 흐름에서 V3K 분석/학습 결과를 관찰하려는 단계. |
| 선행 조건 | paper/live session 계획, non-blocking queue 설계, no-order-impact assertion, latency measurement. |
| 결론 | 자동 구현 금지. 별도 `V3K-RUNTIME-DRYRUN-*` phase 필요. |

### 5.4 runtime `globals().update(...)` 연결

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | `globals().update(...)`는 전략식에서 보이는 함수/이름 공간을 바꾸므로 기존 전략의 의미를 바꿀 수 있다. 이름 충돌과 예기치 않은 전략식 사용 위험이 크다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. `strategy/v3k_formula_facade.py`가 `V3K_` prefix callable 후보를 만들며, runtime update는 하지 않는다. |
| 언제 필요해지는가 | 사용자가 전략식에서 `V3K_리스크점수()` 같은 함수를 실제로 사용하려는 경우. |
| 선행 조건 | prefix 정책 확정, formula regression, 기존 전략식 collision audit, OFF/ON 비교 backtest. |
| 결론 | facade 준비는 완료. runtime update는 승인 전 금지. |

### 5.5 analyzer output의 실제 전략식/주문/청산 사용

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | analyzer output이 주문/청산에 영향을 주는 순간 실거래 리스크가 발생한다. V3 계산값이 Kiwoom 데이터 shape에서 충분히 검증되었는지, 손익/리스크 정책이 적절한지 확인되지 않았다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **반영하지 않는 것이 맞다**. smoke는 synthetic/path 검증이며 매매 성능 검증이 아니다. |
| 언제 필요해지는가 | V3K 분석값을 실제 전략 조건에 포함하려는 시점. |
| 선행 조건 | backtest A/B, paper trading, order/exit risk guard, loss-limit policy, rollback plan. |
| 결론 | 사용자 승인 및 검증 없는 자동 반영은 부적절하다. |

### 5.6 `_database_v3k_shadow` 생성 및 DB cutover

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | DB 생성/수정은 데이터 손상, schema mismatch, rollback 필요성, backtest leakage 가능성을 동반한다. 기존 지침도 `_database`, `_log`, `*.db` 커밋/생성을 금지한다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. migration spec과 dry-run scripts, read-only/missing-DB no-op path는 준비되어 있다. |
| 언제 필요해지는가 | 실제 V3 learning DB를 사용하거나 학습 데이터를 저장/읽는 단계. |
| 선행 조건 | backup, rollback rehearsal, DB health report, sample DB, 사용자 승인. |
| 결론 | DB cutover는 별도 `V3K-DB-CUTOVER-*` phase가 필요하다. |

### 5.7 production learning DB contents read

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | 실제 DB contents read는 data quality, schema, last_update leakage, performance 이슈를 검증해야 한다. 현재 smoke는 missing-DB no-op과 query contract 검증이다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. read-only adapter는 준비되어 있으나 실제 데이터 검증은 별도 환경이 필요하다. |
| 언제 필요해지는가 | production 또는 sample learning DB가 준비된 뒤. |
| 선행 조건 | sample/prod DB path 승인, read-only mount, health check, leakage policy 확정. |
| 결론 | 데이터 준비 없는 자동 활성화는 부적절하다. |

### 5.8 LS Securities REST/TR/REAL 직접 의존성

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 제외 |
| 왜 반영하지 않았는가 | 2U_C의 목표는 V3 branch가 아니라 V2/Kiwoom 유지 custom lane이다. LS broker 전환 자체는 목적에 반한다. |
| 반영하지 않아도 되는가 | **반영하면 안 된다**. 이 항목은 보류가 아니라 명시적 제외다. |
| 언제 필요해지는가 | 2U_C가 아니라 별도 LS 기반 branch 또는 V3 계열에서만 필요하다. |
| 선행 조건 | broker abstraction 또는 별도 branch 전략. |
| 결론 | 2U_C에는 계속 제외한다. |

### 5.9 analyzer DB constructor runtime 사용

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | V3 analyzer class constructor가 DB/table 초기화 side-effect를 가질 수 있다. runtime에서 constructor를 호출하면 DB 생성/수정 금지 원칙을 깰 수 있다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. module import/field contract와 adapter smoke만 수행하는 것이 안전하다. |
| 언제 필요해지는가 | 실제 analyzer DB lifecycle을 승인한 뒤. |
| 선행 조건 | constructor side-effect audit, read-only mode patch, DB cutover approval. |
| 결론 | 현 상태 유지가 타당하다. |

### 5.10 V3 microstructure engine replacement

| 항목 | 판단 |
| --- | --- |
| 반영 여부 | 보류 |
| 왜 반영하지 않았는가 | 2U_C에는 기존 Kiwoom/V2 기반 microstructure/risk 경로가 있다. V3 microstructure 교체는 데이터 shape와 runtime latency에 직접 영향을 줄 수 있다. |
| 반영하지 않아도 되는가 | safe-staged 목표에서는 **맞다**. 기존 경로 유지가 Kiwoom 유지 목표에 부합한다. |
| 언제 필요해지는가 | V3 microstructure의 구체적 이점과 Kiwoom 데이터 mapping이 검증된 뒤. |
| 선행 조건 | parity fixture, latency benchmark, feature flag OFF/ON A/B test. |
| 결론 | 현 단계 자동 반영은 부적절하다. |

## 6. “진짜 반영 안 해도 되는가?” 최종 판단

질문을 두 기준으로 나누면 답이 명확하다.

### 6.1 safe-staged 목표 기준

**반영하지 않아도 된다. 오히려 반영하지 않는 것이 맞다.**

이유:

- 사용자와 합의한 현재 목적은 `V3 기능 + Kiwoom 유지`를 안전하게 2U_C에 준비하는 것이었다.
- 안전 조건은 default-OFF, no-op, read-only, contract, adapter boundary였다.
- GUI/runtime/DB/주문·청산 연결은 이 안전 조건을 넘어선다.
- VERIFY-1A/1B audit가 이 경계를 검증한다.

### 6.2 완전 활성화 목표 기준

**반영이 필요하다. 다만 지금 자동으로 반영하면 안 된다.**

완전 활성화의 의미는 다음과 같다.

- UI에서 V3K flag를 조작한다.
- live Kiwoom runtime에서 V3K output을 생성한다.
- strategy formula/global에서 V3K 값을 실제로 읽는다.
- production learning DB를 read-only 또는 cutover 방식으로 사용한다.
- analyzer output이 전략 판단 또는 주문/청산에 영향을 준다.

이 목표는 더 높은 위험 단계이며, 별도 승인/검증/rollback 계획이 필요하다.

## 7. 방향성 점검

현재 방향성은 타당하다.

| 기준 | 판단 |
| --- | --- |
| Kiwoom 유지 | 충족 |
| V3 LS 제외 기능 준비 | 충족 |
| 안정성 | default-OFF/read-only/no-op로 충족 |
| 자동 검증 | VERIFY-1A/1B로 충족 |
| 완전 활성화 | 미완료, 승인 필요 |
| 추가 자동 구현 | 중단해야 함 |

따라서 closeout 이후 기본 상태는 **STOP / approval gate**가 맞다.

## 8. 후속 계획 선택지

후속 작업은 자동 진행하지 않는다. 사용자가 명시적으로 선택해야 한다.

### 선택지 A: 현 상태 유지

- 가장 안전하다.
- V3K safe-staged 기반은 준비되어 있다.
- 필요할 때 audit만 재실행한다.

### 선택지 B: GUI settings 연결 phase

- MainWindow/pyd wrapper 영향 검토가 필요하다.
- 권장 선행 명령:

```powershell
python scripts\audit_v3k_verify_1b_closure.py
python scripts\audit_v3k_verify_1a.py
```

### 선택지 C: live Kiwoom runtime dry-run phase

- 주문/청산 영향이 없어야 한다.
- latency/no-side-effect 검증이 필요하다.

### 선택지 D: DB shadow/read-only contents phase

- sample/prod DB path와 read-only policy가 필요하다.
- backup/rollback rehearsal 전 cutover 금지.

### 선택지 E: strategy/order activation phase

- 가장 위험하다.
- backtest, paper trading, risk guard, rollback plan 없이는 진행하지 않는다.

## 9. 최종 결론

`2U_C V3K safe-staged 목표`는 완료되었다.

하지만 다음은 완료되지 않았고, 완료되지 않은 것이 맞다.

- GUI wrapper 연결
- live runtime hook
- DB cutover
- production learning DB read
- analyzer output의 주문/청산 사용

이들은 “누락”이 아니라 “승인 gate로 분리한 고위험 활성화 단계”다.

따라서 현재 상태는 다음 문장으로 고정한다.

> 2U_C에는 V3의 LS 제외 학습/분석/formula/settings 기능을 Kiwoom 유지 조건에서 safe-staged 방식으로 모두 준비했다. 실제 GUI/runtime/DB/매매 활성화는 아직 하지 않았으며, 이는 의도적이고 타당한 보류다. 후속 활성화는 사용자 명시 승인과 새 phase 계획이 필요하다.
