# 2U_C V3K 전체 기능 반영 재감사 보고서

작성일: 2026-05-10 KST
대상 branch: `STOM_Version_2U_C`
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
관련 계획: `.omx/plans/ralplan-five-worktree-2uc-v3k-audit-20260510T101121Z.md`

## 1. 사용자 질문과 즉답

사용자 요청의 핵심은 다음이다.

> 활성 worktree 5개를 다시 검토한다.
> `STOM_Version_2`, `STOM_Version_3` 공식 업데이트 lane은 잘 반영되었다고 판단하지만 다시 확인한다.
> `STOM_Version_2U`, `STOM_Version_3U` pyd 제거/추론 lane도 다시 확인한다.
> 가장 중요한 대상은 `STOM_Version_2U_C`이며, LS증권 전환은 제외하고 Kiwoom증권 API를 유지한 상태로 V3의 새로운 기능이 모두 잘 반영되었는지 상세 검토한다.
> 검토 보고서를 2U_C에 작성하고, 다른 worktree branch에도 함께 commit해야 한다면 추천한다.

이번 재감사의 결론은 다음이다.

| 질문 | 답변 |
| --- | --- |
| V2 공식 lane은 정상인가 | `scripts/verify_release_sync.py` 통과. 현재 기준 정상으로 판단한다. |
| V3 공식 lane은 정상인가 | `STOM V3.18` HEAD가 origin과 동기화되어 있다. 공식 V3 lane으로 보존된다. |
| 2U pyd-free lane은 정상인가 | `.pyd`는 0개다. 다만 현 Python 3.11 환경에서 `talib`/`numpy` ABI mismatch 때문에 offline GUI smoke는 실패했다. 이는 코드 결함 확정보다 검증 환경 재정비 필요로 분류한다. |
| 3U pyd-free lane은 정상인가 | `.pyd`는 0개이며 V3U smoke/contract 검증이 통과했다. |
| 2U_C는 V3 기능을 모두 반영했는가 | **safe-staged 기준으로는 반영 완료**다. 단, **완전 활성화 기준으로는 완료가 아니다.** |
| LS증권 기능은 어떻게 처리되었나 | LS Securities REST/TR/REAL 직접 의존은 2U_C 목표와 충돌하므로 “미반영”이 아니라 **명시적 제외/반영 금지**다. |
| Kiwoom 유지 조건은 지켜졌나 | audit 기준 통과. Kiwoom receiver/order/strategy live 경로는 V3K 기능에 의해 직접 변경되지 않는다. |
| 다른 branch에도 commit해야 하는가 | 현재는 **2U_C에만 commit**하는 것을 권장한다. V2/2U/V3/3U에는 즉시 commit할 필요가 없다. |

## 2. 활성 worktree 5개 기준선

검증 시점의 worktree 목록은 다음과 같다.

```text
C:/System_Trading/STOM/STOM_V         adfe80c7 [STOM_Version_2]
C:/System_Trading/STOM/STOM_V.wt-2u   09c73048 [STOM_Version_2U]
C:/System_Trading/STOM/STOM_V.wt-3    7faec937 [STOM_Version_3]
C:/System_Trading/STOM/STOM_V.wt-3u   4a4d989c [STOM_Version_3U]
C:/System_Trading/STOM/STOM_V.wt-dev  9042be5e [STOM_Version_2U_C]
```

| Lane | Worktree | HEAD | 상태 |
| --- | --- | --- | --- |
| V2 | `STOM_V` | `adfe80c7` | origin 동기화, clean |
| 2U | `STOM_V.wt-2u` | `09c73048` | origin 동기화, `backtest/graph/` 미추적 존재 |
| 2U_C | `STOM_V.wt-dev` | `9042be5e` | origin 동기화, clean |
| V3 | `STOM_V.wt-3` | `7faec937` | origin 동기화, clean |
| 3U | `STOM_V.wt-3u` | `4a4d989c` | origin 동기화, clean |

`STOM_Version_2U`의 `backtest/graph/`는 기존 운영 규칙상 release input이 아니며, 이번 감사의 commit 대상에도 포함하지 않는다.

## 3. pyd / py 개수 기준

`.git`, `_database`, `_log`, `backtest/graph`를 제외하고 집계한 결과는 다음과 같다.

| Lane | pyd | py | 판정 |
| --- | ---: | ---: | --- |
| V2 | 1 | 215 | 공식 lane이므로 upstream `.pyd` 보존이 정상 |
| 2U | 0 | 224 | pyd-free 구조 충족 |
| 2U_C | 0 | 404 | pyd-free custom/backport lane 구조 충족 |
| V3 | 1 | 188 | 공식 V3 lane이므로 upstream `.pyd` 보존이 정상 |
| 3U | 0 | 192 | V3 pyd-free 구조 충족 |

## 4. 실행한 검증 명령과 결과

### 4.1 V2 공식 lane

```powershell
python scripts/verify_release_sync.py
```

결과:

```text
release sync preflight passed
EXIT_CODE=0
```

판정: V2 공식 업데이트 lane은 현재 기준 정상이다.

### 4.2 2U pyd-free lane

처음 `python` 기본 실행은 Python 3.13 환경에서 `PyQt5`가 없어 실패했다. 이후 Python 3.11 환경으로 재실행했다.

```powershell
py -3.11 scripts/smoke_offline_gui.py --branch STOM_Version_2U --version V2.79 --offline --log-dir .omx/logs/v279
py -3.11 scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v279/ralph_verify_pyd_gui_contract.json --log-dir .omx/logs/v279
```

결과:

```text
[FAIL] offline GUI smoke failed
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject

[FAIL] smoke status is failed
```

판정:

- `.pyd` 개수는 0개이므로 pyd-free 구조 자체는 유지된다.
- 실패 원인은 `talib`와 `numpy` ABI mismatch로 보인다.
- 따라서 이번 감사에서는 **2U 구현 결함 확정이 아니라 검증 환경 결함/재검증 필요**로 기록한다.
- 2U를 “완전히 검증 통과”라고 말하지는 않는다.

후속 권장:

```text
Python 3.11 환경의 numpy / TA-Lib binary compatibility를 맞춘 뒤 2U smoke 재실행
```

### 4.3 V3 공식 lane

`STOM_Version_3`는 다음 HEAD로 origin과 동기화되어 있다.

```text
7faec9373fc8af5f5d00c8401bc959b6b7ecbba2 2026-05-05 22:02:36 +0900 STOM V3.18
```

판정: V3 공식 lane은 `STOM V3.18` 기준으로 보존되어 있다. 공식 lane이므로 `.pyd` 보존이 정상이다.

### 4.4 3U pyd-free lane

```powershell
py -3.11 scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u
py -3.11 scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/ralph_verify_v3u_pyd_gui_contract.json --log-dir .omx/logs/v3u
```

결과:

```text
[OK] V3U offline structural smoke passed
[OK] V3U pyd GUI contract passed
```

판정: 3U pyd-free lane은 현재 기준 통과다.

### 4.5 2U_C V3K 검증

처음 Python 3.13 환경에서는 `numpy`가 없어 V3K script들이 실패했다. Python 3.11에서는 아래와 같이 재실행했다.

```powershell
py -3.11 scripts/audit_v3k_verify_1a.py --base 57496d24
py -3.11 scripts/audit_v3k_verify_1b_closure.py
py -3.11 scripts/smoke_v3k_analyzer_modules.py
py -3.11 scripts/smoke_v3k_analyzer_adapter.py
py -3.11 scripts/smoke_v3k_learning_loader.py
py -3.11 scripts/smoke_v3k_backtest_learning_hook.py
py -3.11 scripts/smoke_v3k_realtime_learning_boundary.py
py -3.11 scripts/smoke_v3k_formula_facade.py
py -3.11 scripts/smoke_v3k_settings_surface.py
py -3.11 scripts/v3k_db_health.py --read-only --stdout
py -3.11 scripts/verify_nonrelease_sync.py
```

결과 요약:

| 명령 | 결과 | 의미 |
| --- | --- | --- |
| `audit_v3k_verify_1a.py --base 57496d24` | 통과 | compact history 기준 V3K 변경 범위 41개 파일 audit 통과 |
| `audit_v3k_verify_1b_closure.py` | 통과 | safe-staged 완료/보류/승인 필요 분류 통과 |
| `smoke_v3k_analyzer_modules.py` | 통과 | V3 analyzer module staging / field contract 통과 |
| `smoke_v3k_analyzer_adapter.py` | 통과 | default OFF no-signal, ON path intentionally disabled 확인 |
| `smoke_v3k_learning_loader.py` | 통과 | learning loader query/identifier guard 통과 |
| `smoke_v3k_backtest_learning_hook.py` | 통과 | OFF no-op, ON missing-DB no-op 통과 |
| `smoke_v3k_realtime_learning_boundary.py` | 통과 | realtime learning boundary no-op/missing-DB 경계 통과 |
| `smoke_v3k_formula_facade.py` | 통과 | `V3K_` prefix facade 통과, runtime globals update 없음 |
| `smoke_v3k_settings_surface.py` | 통과 | settings contract default-OFF 통과 |
| `v3k_db_health.py --read-only --stdout` | exit 0, `ok=false` | shadow DB가 없음을 read-only로 보고. 생성하지 않음이 정책상 정상 |
| `verify_nonrelease_sync.py` | 통과 | 2U_C 비정식 worktree guardrail 통과 |

주의:

- `audit_v3k_verify_1a.py`를 인자 없이 실행하면 compact 전 commit subject를 찾으려 하므로 실패한다.
- compact 이후 기준에서는 `--base 57496d24`를 명시해야 현재 V3K safe-staged 변경 범위를 올바르게 감사한다.
- 이 동작은 코드 기능 결함이라기보다 history compaction 이후의 audit command 사용법 보정 사항이다.

## 5. 2U_C V3K 기능 영역별 판정

| 영역 | safe-staged 반영 | 완전 활성화 | 판정 근거 |
| --- | --- | --- | --- |
| DB/learning migration spec | 완료 | 미완료 | migration spec, dry-run/read-only script, `v3k_db_health` |
| V3 analyzer module staging | 완료 | 부분 활성 아님 | analyzer module import/field-contract smoke 통과 |
| AnalyzerRisk adapter | 완료 | live 주문 판단 미연결 | adapter smoke에서 default-OFF no-signal 확인 |
| Backtest learning loader/hook | 완료 | 실제 DB contents 사용 미완료 | OFF no-op, ON missing-DB no-op smoke 통과 |
| Realtime learning boundary | 완료 | live Kiwoom runtime hook 미완료 | realtime boundary smoke 통과, live hook은 승인 필요 |
| Formula/global facade | 완료 | runtime `globals().update(...)` 미연결 | `V3K_` prefix facade smoke 통과 |
| Settings surface contract | 완료 | GUI 실제 연결 미완료 | default-OFF settings surface smoke 통과 |
| Kiwoom runtime/order/receiver 보존 | 완료 | 해당 없음 | VERIFY-1A/1B, nonrelease sync 통과 |
| LS Securities 직접 의존 제외 | 완료 | 반영 금지 | runtime python LS direct marker 없음. audit script 내 금지 패턴 정의만 존재 |
| DB shadow contents | 준비만 완료 | 미완료 | `_database_v3k_shadow` 없음. read-only health에서 missing DB 보고 |

## 6. “V3의 모든 기능을 2U_C에 반영했는가?”에 대한 정확한 답변

정확한 답변은 다음과 같이 두 기준으로 나누어야 한다.

### 6.1 safe-staged 기준

**예. 완료로 판단한다.**

`STOM_Version_2U_C`는 V3의 LS증권 직접 의존을 제외한 학습/분석/DB 설계/backtest/realtime/formula/settings 관련 기능을 Kiwoom 유지 조건에서 다음 형태로 반영했다.

```text
adapter
contract
read-only loader
missing-DB no-create guard
feature flag default-OFF
no-op boundary
V3K_ prefixed facade
approval gate
```

따라서 “2U_C에 V3 기능을 안전하게 탑재할 준비가 되었는가?”라는 질문에는 **그렇다**고 답할 수 있다.

### 6.2 완전 활성화 기준

**아니다. 완료가 아니다.**

아래 항목은 의도적으로 아직 완료하지 않았다.

1. GUI setting surface를 MainWindow/pyd wrapper에 실제 연결
2. live Kiwoom runtime dry-run hook
3. analyzer output을 실제 전략식/주문/청산 판단에 사용
4. runtime `globals().update(...)` 연결
5. `_database_v3k_shadow` 실제 생성과 DB cutover
6. production learning DB contents read
7. V3 microstructure engine replacement
8. LS Securities REST/TR/REAL 직접 의존

이 중 8번 LS 직접 의존은 “나중에 해야 할 일”이 아니라 **2U_C 목표상 반영하면 안 되는 일**이다. 나머지는 사용자 승인 후 별도 phase로 진행해야 한다.

## 7. 이전 문서 결론과의 정합성

이번 재감사는 기존 문서의 결론을 뒤집지 않는다. 오히려 아래 기존 결론을 재확인한다.

- `docs/update_log/2026-05-09_v3k_verify_1b_final_closure_audit.md`
- `docs/update_log/2026-05-09_v3k_closeout_safe_staged_completion.md`
- `docs/update_log/2026-05-09_v3k_activation_gap_review.md`

기존 결론:

```text
2U_C V3K safe-staged 목표는 완료.
완전 활성화는 미완료.
GUI/runtime/DB cutover는 사용자 승인 gate 필요.
```

이번 재검토 결과도 동일하다.

## 8. 다른 branch에도 commit해야 하는가?

현재 즉시 commit이 필요한 branch는 `STOM_Version_2U_C`뿐이다.

| Branch | 추가 commit 필요 여부 | 이유 |
| --- | --- | --- |
| `STOM_Version_2` | 지금은 불필요 | 공식 V2 lane이며, 2U_C 감사 보고서는 custom lane 문서가 적절하다. 단, 운영 총괄 문서가 필요하면 별도 요약 commit 가능 |
| `STOM_Version_2U` | 불필요 | 2U는 pyd-free V2 parity lane이다. V3K 감사 결과를 넣으면 scope가 섞인다 |
| `STOM_Version_3` | 불필요 | 공식 V3 lane이다. 2U_C Kiwoom 유지 감사 문서는 V3 공식 lane에 넣지 않는다 |
| `STOM_Version_3U` | 불필요 | 3U는 V3 pyd-free lane이다. 2U_C custom backport 감사 문서를 넣지 않는다 |
| `STOM_Version_2U_C` | 필요 | V3K 기능 반영 여부의 대상 branch이므로 감사 보고서 보관 위치가 맞다 |

추천:

- 이번에는 `STOM_Version_2U_C`에만 commit한다.
- 추후 `STOM_Version_2`의 `AGENTS.md` 또는 운영 문서에 “2U_C 감사 보고서 위치”를 index로 추가하는 것은 선택 사항이다.

## 9. 남은 리스크와 후속 권장

### 9.1 2U 검증 환경 리스크

2U는 `.pyd` 제거 구조는 맞지만, Python 3.11에서 `talib`/`numpy` ABI mismatch로 GUI smoke가 실패했다.

후속 권장:

```text
Python 3.11 환경의 numpy / TA-Lib binary compatibility를 맞춘 뒤 2U smoke 재실행
```

이 작업은 V3K 감사와 별도로 처리한다.

### 9.2 2U_C full activation phase

사용자가 다음 단계에서 “완전 활성화”를 원한다면 권장 순서는 다음이다.

1. `_database_v3k_shadow` 생성 rehearsal
2. production learning DB read-only 검증
3. GUI settings surface 실제 연결
4. live Kiwoom runtime dry-run hook
5. analyzer output을 전략/주문/청산에 쓰기 전 성능/리스크 검증
6. 그 후에만 limited activation

### 9.3 audit script 보정 후보

`audit_v3k_verify_1a.py`는 compact 전 commit subject를 기본으로 찾는다. 현재 compact history에서는 기본 실행이 실패하므로, 다음 중 하나를 후속으로 검토할 수 있다.

- 문서에 항상 `--base 57496d24`를 명시한다.
- 또는 script가 compact history fallback base를 인식하도록 보정한다.

이번 단계에서는 구현 변경 금지 원칙 때문에 script를 수정하지 않았다.

## 10. 최종 결론

`STOM_Version_2U_C`는 현재 목표였던 **V3K safe-staged 목표**, 즉 “V3 기능 + Kiwoom 유지 + LS 직접 의존 제외 + default-OFF/non-invasive staging” 기준을 충족한다.

하지만 이것은 “V3 기능이 live trading/GUI/DB에 완전히 활성화되었다”는 의미가 아니다. 완전 활성화는 아직 수행하지 않았고, 수행해서도 안 되는 항목과 사용자 승인 후 별도 phase로 진행해야 하는 항목이 분리되어 있다.

따라서 현재 답변은 다음이다.

```text
2U_C는 V3의 LS 제외 신기능을 safe-staged 형태로 잘 반영했다.
Kiwoom증권 API/runtime 유지 원칙도 지켰다.
다만 완전 활성화는 아직 아니며, GUI/runtime/DB/실거래 연결은 사용자 승인 후 별도 단계다.
이번 보고서는 2U_C에만 commit하는 것이 맞다.
```
