> 본 보고서는 Python 3.13.13 기준으로 갱신되었다. Python 3.11 환경에서 수행된 초기 시도 결과(이전 §4.2/§4.5 일부)는 부록 A에 보관한다. 본문 §4·§5·§6·§8은 모두 Python 3.13.13 재검증 결과를 정본으로 한다.

# 2U_C V3K 전체 기능 반영 재감사 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-10 KST |
| 마지막 갱신 | 2026-05-10 (포맷 정리 + Phase A–G 정본화) |
| 대상 branch | `STOM_Version_2U_C` |
| 대상 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 관련 계획 | `.omx/plans/ralplan-five-worktree-2uc-v3k-audit-20260510T101121Z.md` |
| 검증 런타임 | Python 3.13.13 (NumPy 2.4.4 / PyQt5 / talib 0.6.8 / pandas import OK) |

## 0. TL;DR

```text
2U_C는 V3K safe-staged 기준으로 V3 신기능을 모두 반영했다.
Kiwoom 유지 / LS 직접 의존 제외 / default-OFF / non-invasive staging 원칙은 모두 지켜졌다.
완전 활성화는 의도적으로 미완료다. DB cutover, GUI flag, runtime hook, live Kiwoom, 전략 반영은 사용자 승인 후 별도 phase다.
다음 단계는 Phase A (shadow DB rehearsal)이며, Kiwoom·운영 _database·LS 의존성은 변경하지 않는다.
이 보고서는 2U_C에만 commit한다.
```

## 1. 사용자 질문과 즉답

### 1.1 사용자 요청 인용

> 활성 worktree 5개를 다시 검토한다.
> `STOM_Version_2`, `STOM_Version_3` 공식 업데이트 lane은 잘 반영되었다고 판단하지만 다시 확인한다.
> `STOM_Version_2U`, `STOM_Version_3U` pyd 제거/추론 lane도 다시 확인한다.
> 가장 중요한 대상은 `STOM_Version_2U_C`이며, LS증권 전환은 제외하고 Kiwoom증권 API를 유지한 상태로 V3의 새로운 기능이 모두 잘 반영되었는지 상세 검토한다.
> 검토 보고서를 2U_C에 작성하고, 다른 worktree branch에도 함께 commit해야 한다면 추천한다.

### 1.2 즉답 표

| 질문 | 답변 |
| --- | --- |
| V2 공식 lane은 정상인가 | `scripts/verify_release_sync.py` 통과. 정상이다. |
| V3 공식 lane은 정상인가 | `STOM V3.18` HEAD가 origin과 동기화되어 있다. 정상이다. |
| 2U pyd-free lane은 정상인가 | `.pyd` 0개. Python 3.13.13 기준 offline GUI smoke / pyd GUI contract / nonrelease sync 모두 통과. |
| 3U pyd-free lane은 정상인가 | `.pyd` 0개. V3U smoke/contract 통과. |
| 2U_C는 V3 기능을 모두 반영했는가 | **safe-staged 기준 완료. 완전 활성화 기준 미완료(의도적).** §6 참조. |
| LS증권 기능은 어떻게 처리되었나 | LS REST/TR/REAL 직접 의존은 2U_C 목표와 충돌하므로 “미반영”이 아니라 **명시적 제외/반영 금지**다. |
| Kiwoom 유지 조건은 지켜졌나 | 통과. Kiwoom receiver/order/strategy live 경로는 V3K 기능에 의해 직접 변경되지 않는다. |
| 다른 branch에도 commit해야 하는가 | **2U_C에만 commit 권장.** §9 참조. |

## 2. 활성 worktree 5개 기준선

```text
C:/System_Trading/STOM/STOM_V         adfe80c7 [STOM_Version_2]
C:/System_Trading/STOM/STOM_V.wt-2u   3b7a3aeb [STOM_Version_2U]
C:/System_Trading/STOM/STOM_V.wt-3    7faec937 [STOM_Version_3]
C:/System_Trading/STOM/STOM_V.wt-3u   4a4d989c [STOM_Version_3U]
C:/System_Trading/STOM/STOM_V.wt-dev  9042be5e [STOM_Version_2U_C] (보고서 본문 작성 시점)
```

| Lane | Worktree | HEAD | 상태 |
| --- | --- | --- | --- |
| V2 | `STOM_V` | `adfe80c7` | origin 동기화, clean |
| 2U | `STOM_V.wt-2u` | `3b7a3aeb` | origin 대비 1 local commit ahead, 미추적 `backtest/graph/` 존재(release 입력 아님) |
| 2U_C | `STOM_V.wt-dev` | `9042be5e` | 보고서 본문 기준. 갱신 commit은 별도. |
| V3 | `STOM_V.wt-3` | `7faec937` | origin 동기화, clean |
| 3U | `STOM_V.wt-3u` | `4a4d989c` | origin 동기화, clean |

`STOM_Version_2U`의 `backtest/graph/`는 운영 규칙상 release input이 아니며, 본 감사의 commit 대상에도 포함하지 않는다.

## 3. pyd / py 개수 기준

`.git`, `_database`, `_log`, `backtest/graph`를 제외한 집계.

| Lane | pyd | py | 판정 |
| --- | ---: | ---: | --- |
| V2 | 1 | 215 | 공식 lane이므로 upstream `.pyd` 보존이 정상 |
| 2U | 0 | 224 | pyd-free 구조 충족 |
| 2U_C | 0 | 404 | pyd-free custom/backport lane 구조 충족 |
| V3 | 1 | 188 | 공식 V3 lane이므로 upstream `.pyd` 보존이 정상 |
| 3U | 0 | 192 | V3 pyd-free 구조 충족 |

## 4. 검증 결과 (Python 3.13.13 기준 정본)

### 4.1 런타임 정렬

```text
python --version       -> Python 3.13.13
sys.executable         -> C:\Python\64\Python31313\python.exe
numpy                  -> 2.4.4   OK
PyQt5                  -> import OK
talib                  -> 0.6.8   OK
pandas                 -> import OK
```

`py -3.13t`(free-threaded) 인터프리터는 NumPy C-extension import 문제로 대상 런타임이 아니다. Python 3.11 경로 역시 TA-Lib / NumPy ABI mismatch가 잔존해 대상 런타임이 아니다(부록 A 참조).

### 4.2 V2 공식 lane

```powershell
python scripts/verify_release_sync.py
```

```text
release sync preflight passed
EXIT_CODE=0
```

판정: 정상.

### 4.3 2U pyd-free lane (Python 3.13.13)

```powershell
python scripts/smoke_offline_gui.py --branch STOM_Version_2U --version V2.79 --offline --log-dir .omx/logs/v279
python scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v279/python313_verify_pyd_gui_contract.json --log-dir .omx/logs/v279
python scripts/verify_nonrelease_sync.py
```

```text
[OK] offline GUI smoke passed
[OK] pyd GUI contract passed
all nonrelease guardrails passed
```

남은 caveat(실패 아님):

- offline GUI smoke의 Qt font/OpenGL 경고
- offline 경로에서 KHOPENAPI 호환 인터프리터 미발견 보고(오프라인 검증 환경에서는 정상)

판정: 통과. 실제 Kiwoom live runtime은 KHOPENAPI 호환 환경에서 별도 검증이 필요하다.

### 4.4 V3 공식 lane

```text
7faec9373fc8af5f5d00c8401bc959b6b7ecbba2 2026-05-05 22:02:36 +0900 STOM V3.18
```

판정: V3 공식 lane은 `STOM V3.18` 기준으로 보존되어 있다. 공식 lane이므로 `.pyd` 보존이 정상이다.

### 4.5 3U pyd-free lane

3U는 본 감사 시점에 Python 3.13.13 기준 추가 재검증을 수행하지 않았으며, Python 3.11 기준 결과를 정본으로 인용한다(과거 결과는 통과 상태).

```powershell
py -3.11 scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u
py -3.11 scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/ralph_verify_v3u_pyd_gui_contract.json --log-dir .omx/logs/v3u
```

```text
[OK] V3U offline structural smoke passed
[OK] V3U pyd GUI contract passed
```

판정: 통과. Python 3.13 재검증은 후속 항목으로 둔다.

### 4.6 2U_C V3K (Python 3.13.13)

```powershell
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_settings_surface.py
python scripts/v3k_db_health.py --read-only --stdout
python scripts/verify_nonrelease_sync.py
```

| 명령 | 결과 | 의미 |
| --- | --- | --- |
| `audit_v3k_verify_1a.py --base 57496d24` | passed (changed files: 52)[^files] | compact history 기준 V3K 변경 범위 audit 통과 |
| `audit_v3k_verify_1b_closure.py` | passed | safe-staged 완료/보류/승인 필요 분류 통과 |
| `smoke_v3k_analyzer_modules.py` | passed | V3 analyzer module staging / field contract 통과 |
| `smoke_v3k_analyzer_adapter.py` | passed | default OFF no-signal, ON path intentionally disabled 확인 |
| `smoke_v3k_learning_loader.py` | passed | learning loader query/identifier guard 통과 |
| `smoke_v3k_backtest_learning_hook.py` | passed | OFF no-op, ON missing-DB no-op 통과 |
| `smoke_v3k_realtime_learning_boundary.py` | passed | realtime learning boundary no-op/missing-DB 통과 |
| `smoke_v3k_formula_facade.py` | passed | `V3K_` prefix facade 통과, runtime globals update 없음 |
| `smoke_v3k_settings_surface.py` | passed | settings contract default-OFF 통과 |
| `v3k_db_health.py --read-only --stdout` | exit 0, `ok=false` | shadow DB 미생성을 read-only로 보고. 정책상 정상 |
| `verify_nonrelease_sync.py` | passed | 2U_C 비정식 worktree guardrail 통과 |

[^files]: 부록 A의 Python 3.11 시도에서 `audit_v3k_verify_1a.py` 결과는 41 files로 기록되어 있다. 본 보고서 기준은 52 files이며, 차이는 V3K 작업이 추가로 진행되어 변경 범위가 확대된 결과다.

`v3k_db_health.py` 결과의 `ok=false`는 `_database_v3k_shadow`와 V3K shadow DB 파일을 safe-staged 단계에서 의도적으로 생성하지 않기 때문이다. 이는 “DB cutover/생성/활성화는 사용자 승인 gate 통과 후”라는 정책과 일치한다.

### 4.7 audit script 보정 후보

`audit_v3k_verify_1a.py`는 인자 없이 실행하면 compact 전 commit subject를 찾으려 하므로 현재 compact history에서 기본 실행이 실패한다. 후속 보정 옵션:

- 문서/CI에서 항상 `--base 57496d24`를 명시한다.
- 또는 script가 compact history fallback base를 인식하도록 보정한다.

본 단계에서는 “구현 변경 금지” 원칙으로 script 자체를 수정하지 않는다.

## 5. 2U_C V3K 기능 영역별 판정

| 영역 | safe-staged | 완전 활성화 | 판정 근거 |
| --- | --- | --- | --- |
| DB/learning migration spec | 완료 | 미완료 | migration spec, dry-run/read-only script, `v3k_db_health` |
| V3 analyzer module staging | 완료 | 부분 활성 아님 | analyzer module import/field-contract smoke 통과 |
| AnalyzerRisk adapter | 완료 | live 주문 판단 미연결 | adapter smoke에서 default-OFF no-signal 확인 |
| Backtest learning loader/hook | 완료 | 실제 DB contents 사용 미완료 | OFF no-op, ON missing-DB no-op smoke 통과 |
| Realtime learning boundary | 완료 | live Kiwoom runtime hook 미완료 | realtime boundary smoke 통과 |
| Formula/global facade | 완료 | runtime `globals().update(...)` 미연결 | `V3K_` prefix facade smoke 통과 |
| Settings surface contract | 완료 | GUI 실제 연결 미완료 | default-OFF settings surface smoke 통과 |
| Kiwoom runtime/order/receiver 보존 | 완료 | 해당 없음 | VERIFY-1A/1B, nonrelease sync 통과 |
| LS Securities 직접 의존 제외 | 완료 | 반영 금지 | LS direct marker 없음. audit script 내 금지 패턴만 정의 |
| DB shadow contents | 준비만 완료 | 미완료 | `_database_v3k_shadow` 없음. read-only health에서 missing DB 보고 |

## 6. V3 기능 반영 결론 (이중 기준)

### 6.1 safe-staged 기준 — 완료

`STOM_Version_2U_C`는 V3의 LS 직접 의존을 제외한 학습/분석/DB 설계/backtest/realtime/formula/settings 기능을 Kiwoom 유지 조건에서 다음 형태로 반영했다.

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

“2U_C에 V3 기능을 안전하게 탑재할 준비가 되었는가?”에는 **그렇다**.

### 6.2 operational activation 기준 — 미완료(의도적)

다음 8개 항목은 의도적으로 미완료다(번호는 §7.1 / §8 phase letter와 일대일 매핑된다).

| # | 미완료 항목 | Phase | 비고 |
| ---: | --- | --- | --- |
| 1 | `_database_v3k_shadow` 실제 생성과 DB cutover | A | 운영 `_database`와 분리 필수 |
| 2 | production learning DB contents read | B | `mode=ro`, `last_update < backtest_date` 유지 |
| 3 | GUI setting surface를 MainWindow/pyd wrapper에 실제 연결 | C | default-OFF 유지 필수 |
| 4 | runtime `globals().update(...)` 연결 | D | `V3K_` prefix만 |
| 5 | live Kiwoom runtime dry-run hook | E | 주문/청산 경로 변경 금지 |
| 6 | analyzer output을 실제 전략식/주문/청산 판단에 사용 | F | 고위험. backtest 회귀 + rollback flag 필수 |
| 7 | V3 microstructure engine replacement | G | 별도 설계 단계, 대형 작업 |
| 8 | LS Securities REST/TR/REAL 직접 의존 | (제외) | 2U_C 목표상 반영 금지 |

8번은 “나중에 할 일”이 아니라 **반영하면 안 되는 일**이다. 1–7은 사용자 승인 후 §8의 phase 순서로 진행한다.

### 6.3 두 기준의 차이

safe-staged 완료 기준:

- Kiwoom runtime/order/receiver를 직접 변경하지 않는다.
- V3 학습/분석/DB/backtest/realtime/formula/settings 기능을 adapter, contract, read-only loader, no-op boundary로 준비한다.
- feature flag는 기본 OFF다.
- missing DB는 실패나 자동 생성이 아니라 diagnostic no-op으로 처리한다.
- LS 증권 직접 의존은 제외한다.

operational activation 기준은 위에 더해 다음을 요구한다.

- 실제 shadow DB 생성과 schema 검증
- 실제 read-only learning DB 조회
- GUI 또는 설정 저장소를 통한 flag 노출
- runtime hook 연결
- live Kiwoom dry-run
- analyzer output이 전략/주문/청산에 영향을 줄 때의 회귀 테스트

따라서 “완전 활성화 미완료”는 실패가 아니라 **안전한 단계 분리**다.

## 7. 의도적 미완료 항목별 분석

### 7.1 항목별 반영 가능성 표

| # | 의도적 미완료 항목 | 반영 가능 여부 | 현재 코드/문서 근거 | 반영 시 선행 조건 | Phase |
| ---: | --- | --- | --- | --- | --- |
| 1 | `_database_v3k_shadow` 실제 생성 | 가능 | `scripts/init_v3k_shadow_db.py`가 shadow DB manifest와 schema 후보를 정의. 현재는 `--dry-run`만 허용. | 운영 `_database`와 분리, DB 파일 미커밋, 생성 전/후 health report 저장 | A |
| 2 | production learning DB read-only 검증 | 조건부 가능 | `V3KLearningDataAdapter`가 DB 존재 시 `?mode=ro` SQLite URI로만 읽음. missing DB는 no-op diagnostic. | shadow DB 생성, 최소 샘플 row 또는 기존 학습 DB 복제본, `last_update < backtest_date` 유지 | B |
| 3 | GUI settings surface 실제 연결 | 가능 | `strategy/v3k_settings_surface.py`가 default-OFF settings contract 제공. smoke에서 모든 기본값 OFF 강제. | MainWindow/pyd-free wrapper 영향 검토, UI event/DB setting persistence 분리, OFF 회귀 테스트 | C |
| 4 | runtime `globals().update(...)` 연결 | 가능 | `strategy/v3k_formula_facade.py`가 `V3K_` prefix callable dict 생성. 현재 runtime globals update는 없음. | `V3K_` prefix 유지, 기존 전략식 이름 오염 금지, default-OFF, facade smoke + 전략식 compile smoke | D |
| 5 | live Kiwoom runtime dry-run hook | 조건부 가능 | `V3KRealtimeLearningAdapter`는 Kiwoom receiver/trader/strategy를 import하지 않는 boundary. 현재 live 경로 미연결. | KHOPENAPI 호환 runtime, 주문/청산 경로 변경 금지, preload diagnostic-only mode, live dry-run log | E |
| 6 | analyzer output을 전략식/주문/청산 판단에 사용 | 가능하지만 고위험 | `V3KAnalyzerAdapter`와 formula facade가 output 생성 가능. 현재 주문 판단 미사용. | 충분한 backtest 회귀, feature flag 이중 gate, 손실/거래횟수/성능 기준, rollback plan | F |
| 7 | V3 microstructure engine replacement | 가능하지만 대형 작업 | 현재 V3K safe-staged 범위에는 engine replacement가 아니라 adapter/contract/read-only boundary만 포함. | 별도 설계 문서, Kiwoom data-shape mapping, 성능/메모리 benchmark, backtest parity 기준 | G |
| 8 | LS Securities REST/TR/REAL 직접 의존 | **반영 금지** | 2U_C 목표는 “V3 기능 + Kiwoom 유지”. audit script도 LS direct marker를 금지. | 해당 없음. 필요 시 별도 LS lane 또는 broker-neutral adapter 설계가 먼저 필요. | (제외) |

### 7.2 LS 직접 의존이 단순 미완료가 아닌 이유

- 2U_C 정의가 “V3 기능 + Kiwoom API 유지”다. LS 직접 의존을 도입하면 정의가 무너진다.
- 운영 audit script(`scripts/audit_v3k_verify_1a.py` 등)가 LS direct marker를 금지 패턴으로 정의하고 있다.
- LS 자체를 사용해야 한다면 broker-neutral adapter 설계가 선행돼야 하며, 이는 별도 lane(예: 신규 `STOM_Version_2U_LS` 또는 `broker-adapter`)에서 다뤄야 한다.

## 8. Operational activation phase 정본 (Phase A–G)

§6.2 / §7.1과 일치하는 단일 정본 phase 순서다. 본 보고서의 모든 phase 참조는 이 절을 기준으로 한다.

### Phase A — shadow DB rehearsal (#1)

목표:

```text
_database_v3k_shadow를 운영 _database와 분리해 생성한다.
DB 파일은 commit하지 않는다.
생성 스크립트, health check, manifest report만 commit한다.
```

완료 조건:

- `init_v3k_shadow_db.py` 또는 별도 apply script가 dry-run과 apply/rehearsal mode를 명확히 분리한다.
- `_database_v3k_shadow` 생성 전/후 `v3k_db_health.py --read-only --stdout` 결과를 비교한다.
- `.gitignore` 또는 audit guard가 DB 파일 commit을 차단한다.

### Phase B — read-only learning DB 검증 (#2)

목표:

```text
V3KLearningDataAdapter가 실제 shadow DB를 쓰지 않고 읽기만 하는지 검증한다.
```

완료 조건:

- DB connection은 `mode=ro`를 유지한다.
- `last_update < backtest_date` 정책을 유지한다.
- missing DB no-op smoke와 existing DB read smoke가 모두 존재한다.

### Phase C — GUI/settings 연결 (#3)

목표:

```text
V3K setting contract를 실제 GUI 또는 설정 저장소에 노출하되 모든 기본값은 OFF로 유지한다.
```

완료 조건:

- MainWindow/pyd-free wrapper contract를 깨지 않는다.
- default-OFF smoke가 유지된다.
- 사용자가 명시적으로 켜기 전에는 기존 backtest/realtime 결과가 변하지 않는다.

### Phase D — formula/global runtime 연결 (#4)

목표:

```text
V3K_ prefix가 붙은 formula/global callable만 runtime에 제한적으로 노출한다.
```

완료 조건:

- 기존 전략식 이름과 충돌하지 않는다.
- `V3K_` prefix 없는 값은 주입하지 않는다.
- OFF일 때 globals가 생성되지 않는다.

### Phase E — live Kiwoom dry-run hook (#5)

목표:

```text
Kiwoom live runtime에서 주문/청산 경로를 바꾸지 않고 V3K preload diagnostic만 남긴다.
```

완료 조건:

- KHOPENAPI 호환 환경에서 실행한다.
- 주문, 청산, 계좌, 체결 처리 경로를 변경하지 않는다.
- dry-run log만 남긴다.

### Phase F — analyzer output 전략 반영 (#6)

목표:

```text
V3K analyzer output을 전략 판단에 쓰기 전, backtest 기준으로 안전성을 검증한다.
```

완료 조건:

- 수익률, 손실, MDD, 거래횟수, 체결/미체결 변화 기준을 문서화한다.
- 기존 전략 대비 parity 또는 의도한 차이를 검증한다.
- rollback flag가 존재한다.

### Phase G — V3 microstructure engine replacement (#7)

목표:

```text
2U_C에 V3 microstructure 분석 엔진을 직접 이식하거나 동등 기능을 Kiwoom data shape 기준으로 재구현한다.
```

완료 조건:

- 별도 설계 문서가 존재하고 Kiwoom data-shape mapping이 명시된다.
- 성능/메모리 benchmark가 V3 대비 합리적 범위 내에 있다.
- backtest parity 기준이 정량적으로 검증된다.
- Phase F와 마찬가지로 default-OFF + rollback flag를 유지한다.

> Phase G는 단일 phase로는 가장 큰 작업이며, 필요 시 G-1(이식), G-2(parity 검증), G-3(전략 통합)으로 다시 분해해 진행하는 것을 권장한다.

### 8.x 다음 작업 지시문 후보 (Phase A 시작용)

```text
V3K full activation Phase A를 시작한다.
대상은 STOM_Version_2U_C만이다.
목표는 _database_v3k_shadow 생성 rehearsal을 구현하고 검증하는 것이다.
운영 _database, Kiwoom 주문/청산/live runtime, LS Securities 의존성은 변경하지 않는다.
DB 파일은 commit하지 않는다.
생성 스크립트/검증 스크립트/문서/registry만 commit한다.
검증은 Python 3.13.13 기준으로 수행한다.
```

이 지시문은 safe-staged 완료 상태를 깨지 않고, 의도적 미완료 항목 중 가장 앞단인 DB shadow rehearsal부터 operational activation으로 전환하기 위한 출발점이다.

## 9. 다른 branch에 commit해야 하는가?

| Branch | 추가 commit 필요 여부 | 이유 |
| --- | --- | --- |
| `STOM_Version_2` | 지금은 불필요 | 공식 V2 lane. 2U_C 감사 보고서는 custom lane 문서가 적절. 운영 총괄 index가 필요하면 별도 요약 commit 가능. |
| `STOM_Version_2U` | 불필요 | 2U는 pyd-free V2 parity lane. V3K 감사 결과를 넣으면 scope가 섞인다. |
| `STOM_Version_3` | 불필요 | 공식 V3 lane. 2U_C Kiwoom 유지 감사 문서는 V3 공식 lane에 넣지 않는다. |
| `STOM_Version_3U` | 불필요 | 3U는 V3 pyd-free lane. 2U_C custom backport 감사 문서는 부적합. |
| `STOM_Version_2U_C` | 필요 | V3K 기능 반영 여부의 대상 branch이므로 보고서 보관 위치가 맞다. |

추천:

- 본 보고서는 `STOM_Version_2U_C`에만 commit한다.
- 추후 `STOM_Version_2`의 `AGENTS.md` 또는 운영 문서에 “2U_C 감사 보고서 위치”를 index로 추가하는 것은 선택 사항이다.

## 10. 이전 문서 결론과의 정합성

본 재감사는 다음 기존 문서의 결론을 뒤집지 않고 재확인한다.

- `docs/update_log/2026-05-09_v3k_verify_1b_final_closure_audit.md`
- `docs/update_log/2026-05-09_v3k_closeout_safe_staged_completion.md`
- `docs/update_log/2026-05-09_v3k_activation_gap_review.md`

기존 결론:

```text
2U_C V3K safe-staged 목표는 완료.
완전 활성화는 미완료.
GUI/runtime/DB cutover는 사용자 승인 gate 필요.
```

본 보고서 결론도 동일하다.

## 11. 최종 결론

`STOM_Version_2U_C`는 **V3K safe-staged 목표**(V3 기능 + Kiwoom 유지 + LS 직접 의존 제외 + default-OFF/non-invasive staging)를 충족한다. 하지만 이것이 “V3 기능이 live trading/GUI/DB에 완전히 활성화되었다”를 의미하지는 않는다. 완전 활성화는 §6.2 / §8의 phase 절차로 사용자 승인 후 진행한다.

```text
2U_C는 V3의 LS 제외 신기능을 safe-staged 형태로 모두 반영했다.
Kiwoom증권 API/runtime 유지 원칙도 지켰다.
완전 활성화는 아직 아니며, GUI/runtime/DB/실거래 연결은 사용자 승인 후 별도 phase다.
이번 보고서는 2U_C에만 commit한다.
```

## 부록 A. Python 3.11 시도 이력 (supersede됨)

본 부록은 Python 3.13.13 정렬 이전의 Python 3.11 환경 시도 기록이다. 본문 §4의 결과로 supersede되며, 이력 보존 목적으로만 둔다.

### A.1 2U pyd-free lane (Python 3.11)

```powershell
py -3.11 scripts/smoke_offline_gui.py --branch STOM_Version_2U --version V2.79 --offline --log-dir .omx/logs/v279
py -3.11 scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v279/ralph_verify_pyd_gui_contract.json --log-dir .omx/logs/v279
```

```text
[FAIL] offline GUI smoke failed
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject

[FAIL] smoke status is failed
```

해석: `.pyd` 0개 구조 자체는 유지되나, Python 3.11 환경의 `talib`/`numpy` ABI mismatch로 인한 검증 환경 결함. 본문 §4.3 Python 3.13.13 결과로 supersede됨.

### A.2 2U_C V3K (Python 3.11)

```powershell
py -3.11 scripts/audit_v3k_verify_1a.py --base 57496d24
... (이하 §4.6과 동일한 명령군)
```

당시 결과 표는 본문 §4.6과 동일한 PASS 패턴이었으며, `audit_v3k_verify_1a.py`의 변경 파일 수는 41이었다. 본문 §4.6은 Python 3.13.13 시점의 52 files를 정본으로 한다(차이 사유: V3K 작업 진행으로 변경 범위 확대).

### A.3 supersede 매핑

| 부록 A 위치 | supersede한 본문 위치 |
| --- | --- |
| A.1 (Python 3.11 2U FAIL) | §4.3 (Python 3.13.13 2U PASS) |
| A.2 (Python 3.11 2U_C 41 files) | §4.6 (Python 3.13.13 2U_C 52 files) |
| 이전 §9.1 후속 권장(“Python 3.11 ABI 보정”) | §4.1 / §4.3 (Python 3.13.13 정렬로 해소) |
| 이전 §9.2 6단계 phase | §6.2 / §7.1 / §8 Phase A–G 단일 정본 |
| 이전 §11 Python 3.13 retest 절 | §4.1 / §4.3 / §4.6 본문 흡수 |
| 이전 §12 의도적 미완료 항목 절 | §6.2 / §7 / §8 분리 통합 |

## 부록 B. 갱신 이력

| 갱신 시각(KST) | 변경 |
| --- | --- |
| 2026-05-10 (최초) | 보고서 작성. Python 3.11 기준 결과 포함. |
| 2026-05-10 (Python 3.13 retest) | §11 추가, 1·4.2·9.1 banner로 supersede 표시. |
| 2026-05-10 (의도적 미완료 분석) | §12 추가, Phase A–F 권장 순서 정의. |
| 2026-05-10 (포맷 정리) | 전체 재구성: §0 TL;DR 추가, §4를 Python 3.13.13 정본으로 흡수, Phase A–G 단일 정본화(§8), Python 3.11 시도를 부록 A로 분리, supersede 매핑 표 명시. |
