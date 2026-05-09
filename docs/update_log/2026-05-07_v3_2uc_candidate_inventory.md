# V3 -> 2U_C candidate inventory

작성일: 2026-05-07 KST  
문서 목적: V3 기능을 2U_C에 계속 적용하기 전에, V3 전체 변경을 먼저 후보 inventory로 정리하고 안전한 적용 순서를 고정한다.

## 0. 사용자 요청 원문 요약

사용자는 BP-008A 이후 다음 단계가 “V3 기능에서 반영할 후보를 모두 찾는 것”인지 질문했다. 예시는 다음과 같다.

> V3 신기능들을 모두 코드 비교와 검토로 찾고, 하나씩 찾아서 후보를 만드는 방식이 더 좋은가?

이번 문서의 답은 “예, 먼저 전체 후보 inventory를 만들고 이후 BP-ID별로 하나씩 적용한다”이다. 구현은 이 문서 단계에서 하지 않는다.

## 0.1 인코딩 보정 기록

초기 Page 1 commit `924b6805`는 PowerShell -> Python stdin 경로에서 한글이 `??`로 깨졌다. 금지된 history rewrite는 수행하지 않고, 이 후속 commit에서 같은 Page 1 내용을 정상 UTF-8 문서로 복구한다. 이후 commit message와 문서 생성은 PowerShell `[System.IO.File]::WriteAllText(..., UTF8Encoding(false))` 방식으로 작성한다.

## 1. Page 1 / 5 - 기준점과 원천 고정

```text
전체 inventory 진행률 [####----------------]  20.0%  1 / 5 pages
현재 page            [####################] 100.0%  Page 1 완료
남은 page            [################----]  80.0%  4 / 5 pages
기존 V3->2U_C baseline [####################] 100.0% 72 / 72 pages
```

### 1.1 현재 worktree 기준

| lane | path | branch | 역할 |
|---|---|---|---|
| V2/root | `C:/System_Trading/STOM/STOM_V` | `STOM_Version_2` | 공식 V2 유지 및 orchestration/docs |
| 2U_C | `C:/System_Trading/STOM/STOM_V.wt-dev` | `STOM_Version_2U_C` | Kiwoom 유지 custom/backport active lane |
| V3 | `C:/System_Trading/STOM/STOM_V.wt-3` | `STOM_Version_3` | V3 공식 ingress 완료 lane |
| V3U | `C:/System_Trading/STOM/STOM_V.wt-3u` | `STOM_Version_3U` | V3 pyd-free 완료 lane |

### 1.2 최신 기준 commit

| lane | HEAD |
|---|---|
| root `STOM_Version_2` | `59de5f62 BP-008A commit message index를 보정 기록으로 남긴다` |
| 2U_C `STOM_Version_2U_C` | `f3120448 BP-008A commit message index를 2U_C에 미러링한다` |
| V3 `STOM_Version_3` | `7faec937 STOM V3.18` |
| V3U `STOM_Version_3U` | `4aef1cce V3U 최종 parity 감사 증적을 고정한다` |

### 1.3 조사 원천

- V3 공식 update source: `STOM_Version_3:_update.txt`, `2026-04-18 V3.0`부터 `2026-05-05 V3.18`까지.
- 코드 diff 기준: `STOM_Version_2U_C` HEAD ↔ `STOM_Version_3` HEAD.
- 기존 적용/보류 근거:
  - `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
  - `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`
  - `docs/update_log/2026-05-07_v3_2uc_bp008a_commit_message_index.md`
  - `docs/CARRY_FORWARD_REGISTRY.md`

### 1.4 절대 gate

후보로 올리려면 아래 조건을 모두 통과해야 한다.

1. Kiwoom 유지가 가능해야 한다.
2. LS REST/REAL/WebSocket 전제를 포함하지 않아야 한다.
3. DB schema migration 또는 기존 `_database` 삭제/변경을 요구하지 않아야 한다.
4. pyd/UI 대규모 구조 변경 또는 V3U 전용 pyd-free 구현을 요구하지 않아야 한다.
5. 파일 단위 broad merge가 아니라 2U_C 기존 구조에 맞춘 최소 수동 이식이어야 한다.
6. 새 code 적용은 반드시 새 BP-ID와 Page 1 read-only inventory부터 시작한다.

### 1.5 Page 1 결론

현재 단계는 구현이 아니라 후보 지도를 만드는 단계다. BP-008A final guard 이후의 기본 상태는 “known-safe 후보 없음”이지만, 전체 V3 기능을 다시 구조화하여 future 후보/보류/제외 목록을 명시적으로 고정한다.

다음 Page 2에서는 V3.0~V3.18의 update 항목을 기능군으로 묶는다.
## 2. Page 2 / 5 - V3.0~V3.18 기능군 inventory

```text
전체 inventory 진행률 [########------------]  40.0%  2 / 5 pages
현재 page            [####################] 100.0%  Page 2 완료
남은 page            [############--------]  60.0%  3 / 5 pages
기존 V3->2U_C baseline [####################] 100.0% 72 / 72 pages
```

### 2.1 V3 version별 변경 묶음

| V3 version | 공식 update 핵심 | 2U_C 관점 기능군 |
|---|---|---|
| V3.0 | Kiwoom 삭제, LS RESTAPI 전면 개편, UI/DB/실행파일 간소화, base receiver/trader/strategy 도입, telegram screenshot 응답, web dashboard 추가 | LS/API/DB/UI 대전환은 제외. dashboard는 별도 제품 후보로만 보류. base class 구조는 Kiwoom 2U_C와 직접 merge 금지 |
| V3.01 | Python 3.13, mainwindow 일부 함수 파일 분리, chart hoga sound 재구동 삭제, AI agent rules, VI 등록/수신, 계정번호 추출, Binance precision, LS server error, 상장주식수 조회, requirements | pyd 분리는 V3U 전용/보류. AI rules는 문서 후보. Binance precision과 일부 runtime guard는 future conditional. LS/requirements broad cleanup은 제외 |
| V3.02 | Binance websocket queue/lib version, backtest unpack/load/resource cleanup, type conversion guard, BinanceWebSocket cleanup, realtime chart index mismatch, pyd rebuild | Binance/Upbit guard는 mock 가능하면 conditional. backtest는 BP-001 hold. pyd rebuild 제외 |
| V3.03 | realtime chart x축, crosshair duplicate, DB chart arg/arrow, image webcrawling exception, Python 3.13 color code, backtest log/cleanup, websocket close, receiver websocket close | 일부는 BP-002/BP-004에서 이미 처리/hold. 남은 chart/websocket guard는 새 mapping 필요 |
| V3.04 | backtest loading bug, shutdown 60초, receiver overhead, high-DPI font, market-cap unit, talib pattern learning | backtest/analysis/settings 영향이 커서 hold. UI high-DPI는 별도 재현 evidence 필요 |
| V3.05 | pattern learning multi count, UI circular import block, volume profile analyzer 추가 | UI import boundary는 2U/2U_C pyd wrapper 계약과 충돌 가능. analysis 추가는 HOLD-001 |
| V3.06 | realtime filter, receiver stop hang, chart hoga query sound exchange refresh, settings lock, DB manage log policy, market-cap registration exclude, login tab transition | receiver/trader/process/DB/UI 동시 영향. 단일 bugfix로 쪼개기 전까지 hold |
| V3.07 | chart moneytop, coin hoga after close, market-open predata, timeframe factor list, DB chart simplification, UI simplification, dialog close list, market-cap DB save, 체결/호가 time digit | chart/UI/close-list는 conditional. market-cap DB는 DB 영향으로 hold/excluded |
| V3.08 | settings lock dialog position, chart `is_min`, DB PK migration, exchange-specific settings, Upbit order websocket, error decorator, Alt+X, sound queue thread, pyttsx downgrade | DB/settings migration 제외. Upbit websocket/error decorator/sound queue는 개별 mock 가능성만 conditional |
| V3.09 | market info dict cleanup, REST simplification, strategy folder move, globals uppercase, pyd rename, window position, path refs, volatility/volume spike analysis, DB order alignment, analysis backengine/strategy 적용 | 대부분 구조 변경/analysis/DB/pyd 전제. 단일 path/window-position bugfix가 있으면 새 후보 필요 |
| V3.10 | analysis training future-reference fix, auto learning after DB manage, 1sec snapshot analysis, code-test analyzer variables | analysis runtime/DB 학습 흐름이라 HOLD-001/HOLD-002 |
| V3.11 | first candle amount fix, snapshot analysis 확장, risk data cleanup, risk 1m, pytz/dateutil/tzlocal 삭제, mock trading API skip, INSERT OR REPLACE helper, analysis messages | timezone은 BP-007A/BP-008A 완료. first candle/mock trading skip/INSERT helper는 Kiwoom/DB 영향 검토 필요 |
| V3.12 | crosshair zValue, prange, single strategy log process, get_optistd speed, radar chart, rank filter, training speed/chart funcs, coin receiver cleanup, analysis chart/factor settings, radar close guard, Binance non-stream guard | crosshair/radar close/Binance non-stream은 conditional. analysis chart/factor/radar 신규 기능은 hold |
| V3.13 | strategy module docs, filename shorten, snapshot date extraction, ranking order, volatility speed, volume settings 삭제, TP/SL analysis, date-change ignore | docs/filename은 low priority. snapshot/ranking/volatility는 analysis/DB 영향으로 hold |
| V3.14 | strategy variable rename, recent-30-day training, backengine 1m indicator, checkbox load simplification, numba optimization, AnalyzerRisk, volatility change levels, VI candle width | AnalyzerRisk dormant 보존은 BP-006A 완료. VI candle width와 checkbox load는 conditional, analysis/DB는 hold |
| V3.15 | volatility classification DB reset, profit/loss recent-month, numba, analysis optimization, BounceButton, analysis default settings, analysis progressbar | progressbar 일부는 BP-005A 완료. BounceButton 재적용은 no-op/보류. analysis DB reset은 제외 |
| V3.16 | min candle count, numba/prange, confidence calc, profit/loss confidence, futures order errors, analysis progressbar simplification, DB dialog progressbar, system log color tag filter | system log/progressbar 일부 완료. futures order/analysis progressbar는 broker/analysis 영향으로 conditional/hold |
| V3.17 | formula manager factors, Analyzer arg rename, PyCharm rules, LS order id, price analysis data load, LS TR/REAL notice, chart exception unify, listed-shares DB update, shutdown confirm, financial webcrawling, stock-info cleanup, strategy syntax test split from pyd, Upbit first tick quantity | financial webcrawling은 BP-004B 완료. chart exception/Upbit first tick/strategy syntax split은 conditional. LS/listed-shares DB/shutdown confirm은 hold/excluded |
| V3.18 | risk min data 30, prange removal, LS realtime websocket split, order-type guard, backtest profit-analysis load name, balance save-only-on-change, strategy-test dummy microstructure, strategy tab icons | order-type guard/backtest function-name/dummy object/icons는 conditional. LS/balance DB/analysis risk는 hold/excluded |

### 2.2 코드 diff 관찰 요약

`STOM_Version_2U_C` HEAD와 `STOM_Version_3` HEAD 사이에는 아래 영역 차이가 크다.

| 영역 | 관찰 | inventory 판정 |
|---|---|---|
| `trade/` | LS REST/REAL, receiver/trader 구조 차이와 coin exchange guard가 섞여 있음 | 파일 단위 merge 금지, mock 가능한 단일 guard만 future conditional |
| `backtest/` | engine 구조 재편, market별 폴더화, B/S/R custom과 충돌 가능 | BP-001 hold 유지 |
| `ui/` | V3 UI 폴더화, pyd 분리, chart/progress/dialog 변경 혼재 | pyd/UI 구조 제외, 단일 widget/chart bugfix만 conditional |
| `utility/` | static_method split, timesync/static dependency cleanup, sound/process split, settings/DB helper | BP-007A/BP-008A 완료. 나머지는 split/process/DB 영향으로 재분리 필요 |
| `strategy/` | AnalyzerRisk 등 analysis module 확대 | dormant 보존은 완료, runtime wiring은 hold |
| `dashboard/` | V3 신규 web dashboard | 2U_C backport가 아니라 별도 제품/feature spec 후보 |
| `docs/tests/research/cli` | V3/V3U/연구/문서/검증 산출물 차이 | 2U_C runtime backport 후보가 아님. 필요한 검증 도구만 별도 판단 |

### 2.3 Page 2 결론

V3 기능 전체는 “바로 적용 가능한 후보”보다 “구조 전환/DB/LS/pyd/analysis가 결합된 후보”가 많다. 따라서 Page 3에서는 위 기능군을 아래 4단계로 분류한다.

1. 이미 완료된 safe 후보
2. 새 BP-ID를 열 수 있는 conditional 후보
3. 설계서/테스트 없이는 보류할 hold 후보
4. 2U_C 목적과 충돌하여 제외할 excluded 후보
## 3. Page 3 / 5 - 후보 분류와 우선순위

```text
전체 inventory 진행률 [############--------]  60.0%  3 / 5 pages
현재 page            [####################] 100.0%  Page 3 완료
남은 page            [########------------]  40.0%  2 / 5 pages
기존 V3->2U_C baseline [####################] 100.0% 72 / 72 pages
```

### 3.1 이미 완료된 safe 후보

| 후보 | 상태 | 2U_C code commit | 의미 |
|---|---|---|---|
| `2UC-V3-BP-002A` | 완료 | `f2f447d1` | 차트 봉 폭 계산을 마지막 간격 기준으로 보정 |
| `2UC-V3-BP-002B` | 완료 | `76329b3b` | DB차트 진입 시 real chart 상태가 섞이지 않도록 초기화 |
| `2UC-V3-BP-004A` | 완료 | `e204e0f3` | 시스템로그 ANSI/color escape 표시 문제 제거 |
| `2UC-V3-BP-004B` | 완료 | `944bab37` | 재무정보 숫자 파싱 보정 |
| `2UC-V3-BP-005A` | 완료 | `f942ed2f` | progressbar 표시/순서/시간 문자열 보정 |
| `2UC-V3-BP-006A` | 완료 | `15467b43`, `0ea00ea4` | AnalyzerRisk를 runtime wiring 없는 dormant module로 보존 |
| `2UC-V3-BP-007A` | 완료 | `61e12951` | 기존 `utility/timesync.py` 경로에서 표준시간 로그/예외/timezone 보정 |
| `2UC-V3-BP-008A` | 완료 | `6e4c10a0` | 기존 `utility/static.py` 경로에서 `pytz` bootstrap을 stdlib timezone으로 보정 |

### 3.2 no-op 또는 현재 hold로 닫힌 후보

| 후보 | 현재 판정 | 재개 조건 |
|---|---|---|
| `2UC-V3-BP-004C` | no-op | 같은 파일/같은 증상에 대한 새 evidence가 있을 때만 재개 |
| `2UC-V3-BP-002C` | hold | realtime chart x축 append 조건이 rolling window인지 append-only인지 runtime evidence 필요 |
| `2UC-V3-BP-001` | hold | backtest B/S/R custom, legacy parity, V3 market별 engine 구조 충돌 분석과 test spec 필요 |
| `2UC-V3-BP-003` | hold | Binance/Upbit broad trade merge 금지. mock 가능한 단일 guard로 새 ID를 열 때만 재개 |
| `HOLD-001` | hold | analysis runtime wiring 설계, DB/settings 영향표, Kiwoom tick/min data shape 검증 필요 |
| `HOLD-002` | hold/excluded | DB schema migration은 별도 migration spec 전까지 금지 |

### 3.3 다음에 열 수 있는 conditional 후보 queue

아래 항목은 “바로 code 적용”이 아니라, 다음 작업에서 Page 1 read-only mapping으로 열 수 있는 후보이다.

| 우선순위 | 예정 후보 ID | 범위 | V3 근거 | 2U_C 적용 전 확인 | 초기 판정 |
|---|---|---|---|---|---|
| 1 | `2UC-V3-BP-009A` | chart/UI 소규모 표시·예외 보정 inventory | V3.07, V3.12, V3.14, V3.17 | `ui/` chart 함수와 2U_C pyd wrapper 계약 mapping, stock/coin 양쪽 영향 | read-only 우선 |
| 2 | `2UC-V3-BP-010A` | Binance/Upbit websocket guard 후보 inventory | V3.02, V3.03, V3.12, V3.17 | live API 금지, mock 입력으로 non-stream/close/first-tick case 재현 가능 여부 | read-only 우선 |
| 3 | `2UC-V3-BP-011A` | residual dependency cleanup 후보 inventory | V3.11 | `telegram_bot.py`, requirements, timezone import residue가 실제 2U_C runtime에 남았는지 확인 | read-only 우선 |
| 4 | `2UC-V3-BP-012A` | strategy syntax test pyd 분리 가능성 조사 | V3.17 | pyd inferred MainWindow 계약과 wrapper 경계 충돌 여부 | hold 우세 |
| 5 | `2UC-V3-BP-013A` | strategy-test dummy microstructure object 오류 조사 | V3.18 | AnalyzerRisk/runtime wiring 없이 단일 mock으로 고칠 수 있는지 확인 | conditional/hold |
| 6 | `2UC-V3-BP-014A` | 거래소별 주문유형 선택 방지 조사 | V3.18 | LS/해외주식 전제 제거 후 Kiwoom/Upbit/Binance에 필요한지 확인 | hold 우세 |

### 3.4 명시적 제외 목록

| 제외 영역 | 제외 이유 |
|---|---|
| LS REST/REAL/WebSocket 전환 | 2U_C는 Kiwoom 유지 lane이다. LS 전환은 V3 공식 lane의 목적이며 2U_C 목표와 다르다. |
| DB primary key, exchange-specific settings, balance save schema, analysis DB reset | 기존 2U_C DB와 비호환 가능성이 높고 `_database` 보호 원칙과 충돌한다. |
| V3U pyd-free 구현 또는 V3 pyd rename/split | 3U/V3U 전용 산출물이며 2U_C pyd-to-py 경계와 직접 merge하지 않는다. |
| dashboard 전체 도입 | 신규 web product에 가깝다. 2U_C backport가 아니라 별도 feature spec으로 다룬다. |
| backtest market별 engine 구조 broad merge | 2U_C의 B/S/R custom과 legacy parity 보정을 깨뜨릴 위험이 크다. |
| analysis runtime 전체 wiring | DB/settings/data shape/strategy runtime을 함께 바꾸므로 dormant module 보존 이상은 설계서가 필요하다. |

### 3.5 우선순위 결론

다음 실제 실행은 code 구현이 아니라 `2UC-V3-BP-009A` Page 1 read-only inventory가 가장 안전하다. 이유는 다음과 같다.

1. chart/UI 표시·예외 보정 후보는 LS API와 DB migration에 직접 묶이지 않을 가능성이 상대적으로 높다.
2. 이미 BP-002/BP-005에서 chart/progressbar 계열 최소 수동 이식 경험이 있다.
3. 단, pyd wrapper/UI 구조와 연결되므로 Page 1에서 mapping이 불명확하면 즉시 hold로 닫아야 한다.

다음 후보는 반드시 아래 명령형 원칙으로 시작한다.

```text
새 BP-ID 부여 -> Page 1 read-only inventory -> Page 2 scope decision -> Page 3 minimal patch or hold -> Page 4 docs sync -> Page 5 final guard
```
## 4. Page 4 / 5 - 공식 추적 문서 동기화

```text
전체 inventory 진행률 [################----]  80.0%  4 / 5 pages
현재 page            [####################] 100.0%  Page 4 완료
남은 page            [####----------------]  20.0%  1 / 5 pages
기존 V3->2U_C baseline [####################] 100.0% 72 / 72 pages
```

### 4.1 동기화 대상

| 문서 | 역할 | Page 4 처리 |
|---|---|---|
| `docs/update_log/2026-05-07_v3_2uc_candidate_inventory.md` | 신규 후보 inventory 본문 | Page 1~4 누적 |
| `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md` | 기존 2U_C V3 backport queue | candidate inventory checkpoint 추가 |
| `docs/CARRY_FORWARD_REGISTRY.md` | carry-forward 공식 registry | inventory checkpoint와 다음 후보 원칙 추가 |

### 4.2 해석 기준

이번 inventory는 BP-008A final guard의 “known-safe 후보 없음” 결론을 뒤집지 않는다. 대신 이후 작업자가 같은 탐색을 반복하지 않도록 다음 상태를 명확히 분리한다.

- 즉시 code 적용 후보: 없음
- 다음 read-only 후보: `2UC-V3-BP-009A`
- 보류/제외 후보: 문서의 hold/excluded 표를 기준으로 유지
- 새 code 변경: Page 4까지 없음

### 4.3 Page 4 결론

공식 추적 문서가 후보 inventory 기준을 참조하도록 동기화되었다. 다음 Page 5는 최종 검증과 다음 OMX 명령 고정만 수행한다.
## 5. Page 5 / 5 - final guard와 다음 명령

```text
전체 inventory 진행률 [####################] 100.0%  5 / 5 pages
현재 page            [####################] 100.0%  Page 5 완료
남은 page            [--------------------]   0.0%  0 / 5 pages
기존 V3->2U_C baseline [####################] 100.0% 72 / 72 pages
```

### 5.1 최종 검증 결과

| Guard | Result |
|---|---|
| root `verify_release_sync.py` | passed |
| 2U_C `verify_release_sync.py --root STOM_V.wt-dev` | passed |
| root status | clean before Page 5 append |
| 2U_C status | clean before Page 5 append |
| forbidden runtime artifacts | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| `STOM_Version_3U_C` | branch 없음 |
| runtime code change | 없음 |

### 5.2 최종 결론

V3 전체 후보를 먼저 찾고 분류하는 전략은 문서화 완료되었다. 이 단계는 code backport가 아니라 다음 code 후보를 안전하게 열기 위한 후보 지도이다.

현재 결론:

- 즉시 적용 가능한 새 safe code 후보는 아직 열지 않는다.
- 다음 후보는 `2UC-V3-BP-009A`로 시작하되, 반드시 read-only inventory만 수행한다.
- `2UC-V3-BP-009A`가 Page 1/2에서 safe하지 않으면 code 없이 hold로 닫는다.

### 5.3 다음 OMX 명령

```powershell
omx ralph --no-deslop "STOM V3에서 STOM_Version_2U_C로 선별 백포트할 다음 후보 2UC-V3-BP-009A를 read-only로 조사한다. 범위는 chart/UI 소규모 표시·예외 보정 후보 inventory이며 code 구현은 하지 않는다. V3.07, V3.12, V3.14, V3.17의 chart/UI 관련 update 항목과 STOM_Version_2U_C의 기존 ui/chart/pyd wrapper 계약을 비교해서 safe/hold/no-op을 결정하고 docs/update_log에 Page 1 문서와 commit만 남긴다. LS API, DB migration, pyd/UI broad merge, V3U 전용 변경은 제외한다."
```