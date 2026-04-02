# Network Noise Handling And Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공식 `STOM_V`에서 외부 네트워크 실패를 traceback 대신 짧은 경고로 낮추고, 같은 정책을 `2U -> 2U_C -> wt-dev -> research/init` 순으로 전파한다.

**Architecture:** 공식 `STOM_V`에 원본 fix 브랜치를 만들고 `utility/webcrawling.py`와 `utility/telegram_bot.py`에 “한 줄 경고 + 기존 상태 유지 + 중복 경고 억제” 정책을 먼저 구현한다. 공식에서 테스트와 수동 확인을 끝낸 뒤, 구조가 가까운 `2U`, `2U_C`에는 같은 코드 의미를 유지하며 최소 diff로 전파하고, 구조가 갈라진 `wt-dev`와 `research/init`은 동일 정책을 의미상 맞춘다.

**Tech Stack:** Python 3.11, PyQt5/QThread, requests, telegram/httpx, pytest, PowerShell, git worktree

---

## File Structure

- Create: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\telegram_bot.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\telegram_bot.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\telegram_bot.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\utility\telegram_bot.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\telegram_bot.py`
- Create downstream copies of the two new unit-test files under each target worktree’s `tests\unit\`

## Task 1: Create the Official Fix Worktree And Write Failing Tests

**Files:**
- Create: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py`
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py`
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Create the official fix worktree**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V worktree add C:\System_Trading\STOM\STOM_V.wt-netfix -b fix/network-noise-handling
```

Expected: a new `C:\System_Trading\STOM\STOM_V.wt-netfix` worktree checked out on `fix/network-noise-handling`.

- [ ] **Step 2: Write the failing webcrawling contract tests**

Create `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py` with this exact content:

```python
from threading import Lock

import requests
import utility.webcrawling as webcrawling_module


class _SignalStub:
    def __init__(self):
        self.messages = []

    def emit(self, payload):
        self.messages.append(payload)


def _build_crawler():
    crawler = webcrawling_module.WebCrawling.__new__(webcrawling_module.WebCrawling)
    crawler.signal = _SignalStub()
    crawler.thread_lock = Lock()
    crawler.warning_lock = Lock()
    crawler.warning_state = {}
    crawler.warning_cooldown = 60
    crawler.thread_join = 0
    crawler.dict_data = {'BTC/USDT': 'old-data'}
    return crawler


def test_emit_network_warning_throttles_duplicate_messages(monkeypatch):
    crawler = _build_crawler()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    crawler._emit_network_warning('바이낸스 데이터', 'BTC/USDT', requests.exceptions.ReadTimeout())
    crawler._emit_network_warning('바이낸스 데이터', 'BTC/USDT', requests.exceptions.ReadTimeout())

    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '바이낸스 데이터 갱신 실패(BTC/USDT): ReadTimeout')
    ]


def test_run_network_job_keeps_existing_data_and_marks_completion():
    crawler = _build_crawler()

    def boom():
        raise requests.exceptions.ReadTimeout()

    result = crawler._run_network_job('바이낸스 데이터', 'BTC/USDT', boom)

    assert result is None
    assert crawler.dict_data['BTC/USDT'] == 'old-data'
    assert crawler.thread_join == 1
```

- [ ] **Step 3: Run the webcrawling tests to verify they fail**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py -q
```

Expected: FAIL because `_emit_network_warning` and `_run_network_job` do not exist yet.

- [ ] **Step 4: Write the failing telegram contract tests**

Create `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py` with this exact content:

```python
from threading import Lock

from utility.setting_base import ui_num
from utility.telegram_bot import TelegramBot


class _QueueStub(list):
    def put(self, item):
        self.append(item)


def _build_bot():
    bot = TelegramBot.__new__(TelegramBot)
    bot.windowQ = _QueueStub()
    bot.warning_lock = Lock()
    bot.warning_state = {}
    bot.warning_cooldown = 60
    return bot


def test_is_transient_network_error_matches_dns_and_timeout():
    bot = _build_bot()

    assert bot._is_transient_network_error(RuntimeError('httpx.ConnectError: [Errno 11001] getaddrinfo failed'))
    assert bot._is_transient_network_error(TimeoutError('timed out'))
    assert bot._is_transient_network_error(OSError('[WinError 10065] 연결할 수 없는 호스트로 소켓 작업을 시도했습니다'))
    assert bot._is_transient_network_error(RuntimeError('ReadTimeoutError: HTTPSConnectionPool(...)'))
    assert bot._is_transient_network_error(RuntimeError('NetworkError: httpx.ConnectError'))
    assert not bot._is_transient_network_error(RuntimeError('ValueError: local bug'))


def test_emit_network_warning_throttles_duplicate_messages(monkeypatch):
    import utility.telegram_bot as telegram_bot_module

    bot = _build_bot()
    monkeypatch.setattr(telegram_bot_module.time, 'time', lambda: 100.0)

    bot._emit_network_warning('텔레그램 봇 시작', TimeoutError('timed out'))
    bot._emit_network_warning('텔레그램 봇 시작', TimeoutError('timed out'))

    assert bot.windowQ == [
        (ui_num['시스템로그'], '텔레그램 봇 시작 실패: TimeoutError')
    ]
```

- [ ] **Step 5: Run the telegram tests to verify they fail**

Run:

```powershell
python -m pytest tests\unit\test_telegram_network_noise.py -q
```

Expected: FAIL because `_is_transient_network_error` and `_emit_network_warning` do not exist yet.

- [ ] **Step 6: Commit the failing tests**

Run:

```powershell
git add tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py
git commit -m "test: lock network noise handling contract"
```

Expected: a tests-only commit on `fix/network-noise-handling`.

## Task 2: Implement Official `webcrawling.py` Noise Handling

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\webcrawling.py`
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py`

- [ ] **Step 1: Add warning state and helper methods**

Update `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\webcrawling.py` to add the new fields inside `WebCrawling.__init__`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Add these exact helper methods under `stop()`:

```python
    def _emit_network_warning(self, category, target, exc):
        key = (category, target, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.signal.emit((ui_num['시스템로그'], f'{category} 갱신 실패({target}): {type(exc).__name__}'))

    def _clear_network_warning(self, category, target):
        with self.warning_lock:
            for key in [k for k in self.warning_state if k[0] == category and k[1] == target]:
                del self.warning_state[key]

    def _complete_network_job(self):
        with self.thread_lock:
            self.thread_join += 1

    def _run_network_job(self, category, target, job):
        try:
            result = job()
            self._clear_network_warning(category, target)
            return result
        except (requests.exceptions.RequestException, OSError, TimeoutError, ValueError) as exc:
            self._emit_network_warning(category, target, exc)
            return None
        finally:
            self._complete_network_job()
```

- [ ] **Step 2: Refactor `get_korean_stocks` to use `_run_network_job`**

Replace the method body with this exact structure:

```python
    @thread_decorator
    def get_korean_stocks(self, search_today, search_time, name, symbol):
        existing_data = self.dict_data.get(name)

        def job():
            i = 1
            time_list = []
            price_list = []
            gap_list = []
            pct_list = []
            last_times = None

            while True:
                url = f'{self.base_url}/sise/sise_index_time.naver?code={symbol}&thistime={search_time}&page={i}'
                resp = self.session.get(url, headers=self.headers, timeout=self.request_timeout)
                soup = BeautifulSoup(resp.text, 'html.parser')

                page_times = [t.get_text(strip=True) for t in soup.select('td.date')]
                if last_times != page_times:
                    last_times = page_times
                else:
                    break

                page_prices = [p.get_text(strip=True) for p in soup.select('td.number_1')[::4]]
                page_gaps = [p.get_text(strip=True) for p in soup.select('span.tah')]
                page_buhos = [t['alt'] for t in soup.select('td > img')]
                page_buhos = [-1 if b == '하락' else 1 for b in page_buhos]

                if '0' in page_gaps:
                    k = 0
                    new_buhos = []
                    for gap in page_gaps:
                        if gap != '0':
                            new_buhos.append(page_buhos[k])
                            k += 1
                        else:
                            new_buhos.append(1)
                    page_buhos = new_buhos

                page_times = [dt_ymdhms_ios(f"{search_today} {t}:00").timestamp() for t in page_times if t != '']
                page_prices = [float(p.replace(',', '')) for p in page_prices if p != '']
                page_gaps = [float(g.replace(',', '')) for g in page_gaps if g != '']
                page_gaps = [g * b for g, b in zip(page_gaps, page_buhos)]
                page_pcts = [round((p / (p - g) - 1) * 100, 2) for p, g in zip(page_prices, page_gaps)]

                if page_times and page_prices and page_gaps and page_pcts:
                    if existing_data is not None and existing_data['time'].iloc[-1] in page_times:
                        duplicate_index = page_times.index(existing_data['time'].iloc[-1])
                        if duplicate_index > 0:
                            time_list.extend(page_times[:duplicate_index])
                            price_list.extend(page_prices[:duplicate_index])
                            gap_list.extend(page_gaps[:duplicate_index])
                            pct_list.extend(page_pcts[:duplicate_index])
                        break
                    time_list.extend(page_times)
                    price_list.extend(page_prices)
                    gap_list.extend(page_gaps)
                    pct_list.extend(page_pcts)

                time.sleep(0.1)
                i += 1

            if not time_list:
                return None

            return pd.DataFrame({
                'time': time_list[::-1],
                'price': price_list[::-1],
                'gap': gap_list[::-1],
                'change': pct_list[::-1],
            })

        df = self._run_network_job('네이버 지수', name, job)
        if df is None:
            return

        with self.thread_lock:
            if existing_data is not None:
                self.dict_data[name] = pd.concat([existing_data, df])
            else:
                self.dict_data[name] = df
```

- [ ] **Step 3: Apply this wrapped-call pattern to `get_market_indicator` and `get_crypto_data`**

For each market-indicator symbol, wrap the per-symbol fetch in `self._run_network_job('시장 지표', name, job)` and only update `dict_data[name]` when `df is not None`.

For `get_crypto_data`, replace the bottom half with this exact pattern:

```python
    @thread_decorator
    def get_crypto_data(self):
        symbols = {
            'BTC/USDT': 'BTCUSDT',
            'ETH/USDT': 'ETHUSDT',
            'BNB/USDT': 'BNBUSDT',
            'XRP/USDT': 'XRPUSDT',
            'SOL/USDT': 'SOLUSDT',
            'DOGE/USDT': 'DOGEUSDT',
            'ADA/USDT': 'ADAUSDT',
            'LINK/USDT': 'LINKUSDT',
        }

        for name, symbol in symbols.items():
            def job():
                url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=1000'
                resp = requests.get(url, headers=self.headers, timeout=self.request_timeout)
                resp.raise_for_status()
                data = resp.json()

                time_list = [int(kline[0] / 1000) for kline in data]
                price_list = [float(kline[4]) for kline in data]
                change_list = [round((price / float(data[0][4]) - 1) * 100, 2) for price in price_list]

                if not time_list:
                    return None

                return pd.DataFrame({
                    'time': time_list,
                    'price': price_list,
                    'change': change_list,
                })

            df = self._run_network_job('바이낸스 데이터', name, job)
            if df is None:
                continue

            with self.thread_lock:
                self.dict_data[name] = df

            time.sleep(0.1)
```

- [ ] **Step 4: Run focused tests and `py_compile`**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py -q
python -m py_compile utility\webcrawling.py
```

Expected: the new test passes and `py_compile` produces no output.

- [ ] **Step 5: Commit the official webcrawling fix**

Run:

```powershell
git add utility/webcrawling.py tests/unit/test_webcrawling_network_noise.py
git commit -m "fix: soften webcrawling network exception noise"
```

Expected: one focused commit containing only the webcrawling fix and its tests.

## Task 3: Implement Official `telegram_bot.py` Noise Handling

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\telegram_bot.py`
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Add warning state and helper methods**

Update the imports in `C:\System_Trading\STOM\STOM_V.wt-netfix\utility\telegram_bot.py` to include `time` and `Lock`:

```python
import time
from threading import Thread, Lock
```

Add these exact fields inside `TelegramBot.__init__`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Add these exact helper methods under `run()`:

```python
    def _is_transient_network_error(self, exc):
        text = f'{type(exc).__name__}: {exc}'.lower()
        markers = (
            'networkerror',
            'connecterror',
            'readtimeout',
            'timed out',
            'getaddrinfo failed',
            'maxretryerror',
            'remote end closed connection',
            'winerror 10065',
        )
        return any(marker in text for marker in markers)

    def _emit_network_warning(self, context, exc):
        key = (context, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.windowQ.put((ui_num['시스템로그'], f'{context} 실패: {type(exc).__name__}'))

    def _handle_bot_exception(self, context, exc):
        if self._is_transient_network_error(exc):
            self._emit_network_warning(context, exc)
        else:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - {context}'))
```

- [ ] **Step 2: Use the helper methods in `start_bot` and `restart_bot`**

Change the `except` blocks to this exact pattern:

```python
        except Exception as exc:
            self._handle_bot_exception('텔레그램 봇 시작', exc)
            self.running = False
```

and:

```python
        except Exception as exc:
            self._handle_bot_exception('텔레그램 봇 재시작', exc)
            self.running = False
```

- [ ] **Step 3: Run focused tests and `py_compile`**

Run:

```powershell
python -m pytest tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\telegram_bot.py
```

Expected: the new test passes and `py_compile` produces no output.

- [ ] **Step 4: Commit the official telegram fix**

Run:

```powershell
git add utility/telegram_bot.py tests/unit/test_telegram_network_noise.py
git commit -m "fix: soften telegram network exception noise"
```

Expected: one focused commit containing only the telegram fix and its tests.

## Task 4: Verify The Official Branch And Prepare It For PR

**Files:**
- Modify: none
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py`
- Test: `C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Run the focused official verification suite**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git status --short
```

Expected:
- pytest reports `4 passed`
- `py_compile` prints nothing
- `git status --short` is clean

- [ ] **Step 2: Do the manual runtime smoke check**

Run the app from the official fix worktree with external networking temporarily degraded or disconnected. Verify all of the following:

```text
- 백테스트 완료 로그가 정상적으로 출력된다.
- 홈 데이터 크롤링 실패가 발생해도 traceback 대신 한 줄 경고만 남는다.
- 텔레그램 polling 실패가 발생해도 traceback 대신 한 줄 경고만 남는다.
- 프로그램 전체가 실패한 것처럼 보이지 않는다.
```

- [ ] **Step 3: Capture the PR-ready summary**

Write this exact summary into your PR body or issue comment:

```markdown
## Summary
- Lower webcrawling network failures from traceback noise to one-line warnings
- Preserve existing home data when Naver/Binance requests fail
- Lower Telegram polling connection failures from traceback noise to one-line warnings
- Add focused unit tests for warning throttling and transient network error classification

## Verification
- `python -m pytest tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py -q`
- `python -m py_compile utility/webcrawling.py utility/telegram_bot.py`
- Manual smoke: backtest complete still visible, network failures only emit warnings
```

## Task 5: Propagate The Official Fix To `STOM_Version_2U`

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\telegram_bot.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Copy the two focused test files from the official fix branch**

Run:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_webcrawling_network_noise.py
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_telegram_network_noise.py
```

- [ ] **Step 2: Port the official `webcrawling.py` helper block and wrapped network calls**

Add these exact fields into `C:\System_Trading\STOM\STOM_V.wt-2u\utility\webcrawling.py`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Add these exact helper methods:

```python
    def _emit_network_warning(self, category, target, exc):
        key = (category, target, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.signal.emit((ui_num['시스템로그'], f'{category} 갱신 실패({target}): {type(exc).__name__}'))

    def _clear_network_warning(self, category, target):
        with self.warning_lock:
            for key in [k for k in self.warning_state if k[0] == category and k[1] == target]:
                del self.warning_state[key]

    def _complete_network_job(self):
        with self.thread_lock:
            self.thread_join += 1

    def _run_network_job(self, category, target, job):
        try:
            result = job()
            self._clear_network_warning(category, target)
            return result
        except (requests.exceptions.RequestException, OSError, TimeoutError, ValueError) as exc:
            self._emit_network_warning(category, target, exc)
            return None
        finally:
            self._complete_network_job()
```

Then port the `_run_network_job(...)` pattern into:

```python
get_korean_stocks(...)
get_market_indicator(...)
get_crypto_data(...)
```

Use the same warning text and the same “keep old data when `df is None`” policy from the official branch.

- [ ] **Step 3: Port the official `telegram_bot.py` helper block and exception handling**

Apply the exact helper fields and methods from Task 3 into `C:\System_Trading\STOM\STOM_V.wt-2u\utility\telegram_bot.py`, and replace the broad traceback-only exception handlers in `start_bot` and `restart_bot` with:

```python
except Exception as exc:
    self._handle_bot_exception('텔레그램 봇 시작', exc)
    self.running = False
```

and:

```python
except Exception as exc:
    self._handle_bot_exception('텔레그램 봇 재시작', exc)
    self.running = False
```

- [ ] **Step 4: Verify and commit `2U`**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git add utility/webcrawling.py utility/telegram_bot.py tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py
git commit -m "fix: propagate network noise handling from STOM_V"
```

Expected: tests pass, `py_compile` is silent, and a single propagation commit is created.

## Task 6: Propagate The Official Fix To `STOM_Version_2U_C`

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\telegram_bot.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Copy the two focused test files from the official fix branch**

Run:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_webcrawling_network_noise.py
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_telegram_network_noise.py
```

- [ ] **Step 2: Port the same webcrawling helper block and wrapped call policy**

Add these exact fields into `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\webcrawling.py`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Add these exact helper methods:

```python
    def _emit_network_warning(self, category, target, exc):
        key = (category, target, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.signal.emit((ui_num['시스템로그'], f'{category} 갱신 실패({target}): {type(exc).__name__}'))

    def _clear_network_warning(self, category, target):
        with self.warning_lock:
            for key in [k for k in self.warning_state if k[0] == category and k[1] == target]:
                del self.warning_state[key]

    def _complete_network_job(self):
        with self.thread_lock:
            self.thread_join += 1

    def _run_network_job(self, category, target, job):
        try:
            result = job()
            self._clear_network_warning(category, target)
            return result
        except (requests.exceptions.RequestException, OSError, TimeoutError, ValueError) as exc:
            self._emit_network_warning(category, target, exc)
            return None
        finally:
            self._complete_network_job()
```

Use the same wrapped method policy:

```python
df = self._run_network_job('네이버 지수', name, job)
if df is None:
    return
```

for `get_korean_stocks`, and the same `continue` pattern for `get_market_indicator` / `get_crypto_data`.

- [ ] **Step 3: Port the same telegram helper block and warning policy**

Apply the exact helper code from Task 3 into `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\telegram_bot.py`.

The two exception blocks must end up identical to:

```python
except Exception as exc:
    self._handle_bot_exception('텔레그램 봇 시작', exc)
    self.running = False
```

and:

```python
except Exception as exc:
    self._handle_bot_exception('텔레그램 봇 재시작', exc)
    self.running = False
```

- [ ] **Step 4: Verify and commit `2U_C`**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git add utility/webcrawling.py utility/telegram_bot.py tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py
git commit -m "fix: propagate network noise handling from STOM_V"
```

Expected: tests pass, `py_compile` is silent, and a single propagation commit is created.

## Task 7: Propagate The Policy To `wt-dev`

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\utility\telegram_bot.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Copy the same two focused test files into `wt-dev`**

Run:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_webcrawling_network_noise.py
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_telegram_network_noise.py
```

- [ ] **Step 2: Apply the same webcrawling helper policy in `wt-dev`**

Insert these exact fields into `C:\System_Trading\STOM\STOM_V.wt-dev\utility\webcrawling.py`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Add these exact helper methods:

```python
    def _emit_network_warning(self, category, target, exc):
        key = (category, target, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.signal.emit((ui_num['시스템로그'], f'{category} 갱신 실패({target}): {type(exc).__name__}'))

    def _clear_network_warning(self, category, target):
        with self.warning_lock:
            for key in [k for k in self.warning_state if k[0] == category and k[1] == target]:
                del self.warning_state[key]

    def _complete_network_job(self):
        with self.thread_lock:
            self.thread_join += 1

    def _run_network_job(self, category, target, job):
        try:
            result = job()
            self._clear_network_warning(category, target)
            return result
        except (requests.exceptions.RequestException, OSError, TimeoutError, ValueError) as exc:
            self._emit_network_warning(category, target, exc)
            return None
        finally:
            self._complete_network_job()
```

The `wt-dev` file already has `alive`, `request_timeout`, and `treemap_timer`. Keep those. Only add the network-warning helpers and replace the three data-fetch methods to use the same `_run_network_job(...)` pattern.

- [ ] **Step 3: Adapt the telegram warning policy to the `wt-dev` telegram structure**

`wt-dev` uses a different `TelegramBot` structure from official, so do not overwrite the file wholesale. Instead, add the same warning fields and helpers into `C:\System_Trading\STOM\STOM_V.wt-dev\utility\telegram_bot.py`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

and:

```python
    def _is_transient_network_error(self, exc):
        text = f'{type(exc).__name__}: {exc}'.lower()
        markers = (
            'networkerror',
            'connecterror',
            'readtimeout',
            'timed out',
            'getaddrinfo failed',
            'maxretryerror',
            'remote end closed connection',
            'winerror 10065',
        )
        return any(marker in text for marker in markers)

    def _emit_network_warning(self, context, exc):
        key = (context, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.windowQ.put((ui_num['시스템로그'], f'{context} 실패: {type(exc).__name__}'))

    def _handle_bot_exception(self, context, exc):
        if self._is_transient_network_error(exc):
            self._emit_network_warning(context, exc)
        else:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - {context}'))
```

Then change the broad `except:` blocks in `start_bot` and `restart_bot` to `except Exception as exc:` and route through `_handle_bot_exception(...)`.

- [ ] **Step 4: Verify and commit `wt-dev`**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git add utility/webcrawling.py utility/telegram_bot.py tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py
git commit -m "fix: propagate network noise handling from STOM_V"
```

Expected: tests pass, `py_compile` is silent, and a single propagation commit is created.

## Task 8: Propagate The Policy To `research/init`

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\webcrawling.py`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\telegram_bot.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_webcrawling_network_noise.py`
- Create: `C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_telegram_network_noise.py`

- [ ] **Step 1: Copy the same two focused test files into `research/init`**

Run:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_webcrawling_network_noise.py C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_webcrawling_network_noise.py
Copy-Item C:\System_Trading\STOM\STOM_V.wt-netfix\tests\unit\test_telegram_network_noise.py C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_telegram_network_noise.py
```

- [ ] **Step 2: Port the `wt-dev` helper fields and helper methods into `research/init`**

Apply these exact `webcrawling.py` helper fields into `C:\System_Trading\STOM\STOM_V.wt-lab\utility\webcrawling.py`:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

Apply these exact `webcrawling.py` helper methods:

```python
    def _emit_network_warning(self, category, target, exc):
        key = (category, target, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.signal.emit((ui_num['시스템로그'], f'{category} 갱신 실패({target}): {type(exc).__name__}'))

    def _clear_network_warning(self, category, target):
        with self.warning_lock:
            for key in [k for k in self.warning_state if k[0] == category and k[1] == target]:
                del self.warning_state[key]

    def _complete_network_job(self):
        with self.thread_lock:
            self.thread_join += 1

    def _run_network_job(self, category, target, job):
        try:
            result = job()
            self._clear_network_warning(category, target)
            return result
        except (requests.exceptions.RequestException, OSError, TimeoutError, ValueError) as exc:
            self._emit_network_warning(category, target, exc)
            return None
        finally:
            self._complete_network_job()
```

Apply these exact `telegram_bot.py` helper fields and methods:

```python
        self.warning_lock = Lock()
        self.warning_state = {}
        self.warning_cooldown = 60
```

```python
    def _is_transient_network_error(self, exc):
        text = f'{type(exc).__name__}: {exc}'.lower()
        markers = (
            'networkerror',
            'connecterror',
            'readtimeout',
            'timed out',
            'getaddrinfo failed',
            'maxretryerror',
            'remote end closed connection',
            'winerror 10065',
        )
        return any(marker in text for marker in markers)

    def _emit_network_warning(self, context, exc):
        key = (context, type(exc).__name__)
        now_ts = time.time()
        with self.warning_lock:
            last_ts = self.warning_state.get(key)
            if last_ts is not None and now_ts - last_ts < self.warning_cooldown:
                return
            self.warning_state[key] = now_ts
        self.windowQ.put((ui_num['시스템로그'], f'{context} 실패: {type(exc).__name__}'))

    def _handle_bot_exception(self, context, exc):
        if self._is_transient_network_error(exc):
            self._emit_network_warning(context, exc)
        else:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - {context}'))
```

Then port them into:

```text
C:\System_Trading\STOM\STOM_V.wt-lab\utility\webcrawling.py
C:\System_Trading\STOM\STOM_V.wt-lab\utility\telegram_bot.py
```

Keep the existing runtime queue layout and bot lifecycle that already differ from official. Only port the warning throttling and “keep old state on failure” policy.

- [ ] **Step 3: Verify and commit `research/init`**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git add utility/webcrawling.py utility/telegram_bot.py tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py
git commit -m "fix: propagate network noise handling from STOM_V"
```

Expected: tests pass, `py_compile` is silent, and a single propagation commit is created.

## Task 9: Final Cross-Worktree Verification

**Files:**
- Modify: none
- Test: all four propagation targets

- [ ] **Step 1: Run the final verification commands in every target**

Run:

```powershell
python -m pytest tests\unit\test_webcrawling_network_noise.py tests\unit\test_telegram_network_noise.py -q
python -m py_compile utility\webcrawling.py utility\telegram_bot.py
git status --short
```

Run those commands in:

```text
C:\System_Trading\STOM\STOM_V.wt-netfix
C:\System_Trading\STOM\STOM_V.wt-2u
C:\System_Trading\STOM\STOM_V.wt-2uc
C:\System_Trading\STOM\STOM_V.wt-dev
C:\System_Trading\STOM\STOM_V.wt-lab
```

Expected:
- each worktree shows passing focused tests
- each worktree compiles cleanly
- each worktree is clean after its commit

- [ ] **Step 2: Run the manual `wt-dev` smoke check that motivated the fix**

Run `python stom.py` in `C:\System_Trading\STOM\STOM_V.wt-dev`, then:

```text
- start a normal backtest
- wait for `백테스트 COMPLETE`
- observe that network failures, if any, are now one-line warnings rather than traceback floods
```

- [ ] **Step 3: Write the final propagation summary**

Record this exact matrix in your final handoff:

```markdown
| Workspace | Status |
| --- | --- |
| STOM_V official fix branch | implemented and verified |
| STOM_Version_2U | propagated and verified |
| STOM_Version_2U_C | propagated and verified |
| STOM_V.wt-dev | propagated and verified |
| research/init | propagated and verified |
```
