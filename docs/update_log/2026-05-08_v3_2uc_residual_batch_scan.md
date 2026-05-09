# 2UC V3 residual batch scan - BP-009C / BP-010A~BP-014A

작성일: 2026-05-08
작업 기준: `BP-009B` final guard 이후
운영 방식: 후보별 반복을 줄이기 위해 잔여 후보를 batch로 한 번에 read-only scan하고, safe patch만 최소 적용한다.

## 1. 이번 요청과 목적

사용자는 BP-009B 이후 다음 질문을 했다.

> 백포트 대략 몇개적도 더 검토해야하나요? 계속 이렇게 반복해야 하나요?

이에 대한 답으로 남은 후보를 개별 Page 1~5 반복으로 계속 진행하지 않고, 다음 후보들을 한 번에 batch 검토하기로 했다.

- `2UC-V3-BP-009C`: chart moneytop time/query normalization 재검토
- `2UC-V3-BP-010A`: Binance/Upbit websocket guard 후보
- `2UC-V3-BP-011A`: residual dependency cleanup 후보
- `2UC-V3-BP-012A`: strategy syntax test pyd 분리 가능성
- `2UC-V3-BP-013A`: strategy-test dummy microstructure object 오류 조사
- `2UC-V3-BP-014A`: 거래소별 주문유형 guard 조사

목적은 `STOM_Version_2U_C`가 V3 branch가 아니라 V2/Kiwoom 유지 custom lane이라는 원칙을 유지하면서, V3 기능 중 안전한 broker-neutral/DB-neutral/pyd-neutral 부분만 반영하는 것이다.

## 2. 진행률

BP-009B 기준 누적 `87 / 87` units 이후, 이번 residual batch는 6개 후보를 한 번에 닫는 것으로 계산한다.

```text
전체 문서화 진행률     [####################] 100.0%  93 / 93 units
이번 residual batch    [####################] 100.0%   6 /  6 candidates
실제 patch 후보        [#######-------------]  33.3%   2 /  6 candidates
hold/no-op 후보        [#############-------]  66.7%   4 /  6 candidates
남은 batch 검토        [--------------------]   0.0%   0 /  6 candidates
```

주의: 위 수치는 “현재 문서화된 후보/검토 단위”의 완료율이다. V3 전체 기능을 무조건 2U_C에 모두 이식했다는 뜻이 아니다. LS API, DB migration, pyd/UI broad merge, V3U-only pyd-free 변경은 여전히 제외/보류다.

## 3. 후보별 판정 요약

| 후보 | 판정 | 결과 | 근거 |
| --- | --- | --- | --- |
| `BP-009C` | hold | code 변경 없음 | V3.07 chart moneytop time/query normalization은 `starttime < 90030` 등 stock session 전제가 포함된다. 2U_C는 coin/stock/future, tick/min DB 경로가 함께 있어 BP-009B의 table clear 이상은 별도 runtime evidence 전까지 보류한다. |
| `BP-010A` | safe partial 적용 | `41a09d76` | Binance websocket이 `data` payload 없는 메시지를 넘길 때 tick/hoga handler가 예외 로그를 남기지 않고 무시하도록 최소 guard를 적용했다. V3 websocket resource manager 전체 구조는 미적용. |
| `BP-011A` | safe 적용 | `59ffaafc` | `utility/telegram_bot.py`의 `pytz` 사용을 stdlib `zoneinfo.ZoneInfo`로 대체하고, 직접 import가 사라진 `pytz`, `tzlocal`, `python-dateutil` pin을 requirements에서 제거했다. |
| `BP-012A` | no-op/hold | code 변경 없음 | 2U_C는 이미 `ui/ui_backtest_engine.py`와 MainWindow wrapper `BackCodeTest1/2/3`로 pyd 외부 호출 경계를 갖고 있다. V3.17의 파일/함수명을 그대로 가져오면 2U_C wrapper 계약과 충돌한다. |
| `BP-013A` | hold | code 변경 없음 | V3.18의 strategy-test dummy microstructure 오류는 V3 analysis runtime wiring과 연결되어 있다. 2U_C의 `MicrostructureAnalyzer`/backtest 구조와 AnalyzerRisk dormant 보존 상태에서는 별도 test spec 없이는 적용하지 않는다. |
| `BP-014A` | hold/excluded | code 변경 없음 | V3.18 주문유형 guard는 LS/해외주식/BaseTrader 전제와 묶여 있다. 2U_C는 Kiwoom/future/Upbit/Binance custom 주문 흐름이므로 broker별 지원 matrix 설계 전까지 적용하지 않는다. |

## 4. 적용 상세

### 4.1 `2UC-V3-BP-010A`

source:

- V3.12 `62e81349` - Binance websocket data 예외처리
- 참고 V3.02/V3.03 websocket resource cleanup은 구조 변경이 커서 제외

2U_C target:

- `trade/binance/binance_receiver_tick.py`

적용 내용:

```python
data = data.get('data') if isinstance(data, dict) else None
if data is None:
    return
```

위 guard를 `UpdateTickData`, `UpdateHogaData` 양쪽에 적용했다.

제외 내용:

- V3 `trade/restapi_binance.py` websocket 구조 전체 이식
- AsyncClient/BinanceSocketManager 재사용 구조 변경
- reconnect sleep/resource manager 변경
- live websocket 테스트

### 4.2 `2UC-V3-BP-011A`

source:

- V3.11 `dbab03b3` - `pytz`, `dateutil`, `tzlocal` 제거 방향

2U_C target:

- `utility/telegram_bot.py`
- `requirements32.txt`
- `requirements64.txt`

적용 내용:

- `pytz.timezone('Asia/Seoul')` -> `ZoneInfo('Asia/Seoul')`
- 직접 import가 남지 않은 dependency pin 제거

제외 내용:

- V3 telegram bot QThread 구조 전체 이식
- HTTPXRequest timeout/pool 구조 변경
- V3 token/chat_id setting key 구조 변경
- live Telegram polling 테스트

## 5. 제외/hold를 고정하는 이유

이번 residual batch의 목적은 “V3 기능을 모두 억지로 넣기”가 아니라 “2U_C 목적에 맞는 안전 후보를 끝까지 찾고, 위험한 후보는 재탐색 비용이 발생하지 않도록 기록하는 것”이다.

따라서 다음 변경은 별도 설계 문서 없이는 진행하지 않는다.

1. LS API / LS websocket / LS TR/REAL 대응
2. DB schema migration / 잔고 저장 정책 변경
3. pyd/UI broad merge / V3U pyd-free 전용 변경
4. analysis runtime wiring / AnalyzerRisk 실제 연결
5. backtest engine 대형 구조 변경
6. broker별 주문유형 matrix 변경

## 6. 검증 증거

적용 직후 실행한 검증:

```text
python -m py_compile trade/binance/binance_receiver_tick.py utility/telegram_bot.py
py_compile passed

git diff --check
exit 0
```

최종 guard에서 추가로 수행해야 하는 검증:

```text
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev
python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/trade/binance/binance_receiver_tick.py C:/System_Trading/STOM/STOM_V.wt-dev/utility/telegram_bot.py
```

## 7. 현재 stop condition

이번 residual batch를 기준으로 “즉시 적용 가능한 새 safe 후보”는 BP-010A/BP-011A를 제외하면 남지 않았다.

다음 중 하나가 새로 확인될 때만 새 BP-ID를 연다.

- GUI/live runtime 재현 evidence
- mock 가능한 단일 입력/출력 test spec
- broker별 주문유형 matrix 설계
- DB migration 설계
- analysis runtime wiring 설계

## 8. 다음 OMX 명령

현재 추천은 새 코드 구현이 아니라 final closure audit이다.

```powershell
omx ralph --prd "STOM V3에서 STOM_Version_2U_C로 선별 backport한 BP-009B 이후 residual batch 결과를 final closure audit한다. 현재 완료 기준은 BP-010A와 BP-011A code commit 및 residual batch 문서화이다. root와 2U_C 문서 동기화, CARRY_FORWARD_REGISTRY 반영, release sync, py_compile, forbidden artifact guard, 3U_C 미생성 guard를 확인하고, 즉시 적용 가능한 새 safe 후보가 없으면 no-more-safe-candidates 상태로 닫는다. LS API, DB migration, pyd/UI broad merge, V3U 전용 변경은 제외한다."
```