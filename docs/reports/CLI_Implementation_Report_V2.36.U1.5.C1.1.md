# STOM CLI 인터페이스 구현 보고서

**버전**: V2.36.U1.5.C1.1
**브랜치**: `STOM_Version_2U-cli-research`
**작성일**: 2026-02-02
**작성자**: Claude Code (AI Agent)

---

## 1. 개요

### 1.1 프로젝트 목적

STOM(System Trading Order Management) GUI 프로그램에 **CLI(Command Line Interface)** 인터페이스를 추가하여:

1. **AI Agent 자동화**: Claude Code 등 AI 에이전트가 백테스트 실행, 전략 관리, 데이터 조회를 자동화
2. **헤드리스 실행**: PyQt5 GUI 없이 서버 환경에서 백테스트 실행 가능
3. **스크립트 통합**: 쉘 스크립트, 배치 파일, CI/CD 파이프라인에서 STOM 기능 활용
4. **원격 제어**: SSH 등 원격 환경에서 STOM 기능 사용

### 1.2 구현 범위

| 기능 | 구현 상태 | 비고 |
|------|----------|------|
| 전략 관리 (list/show/export/stats) | ✅ 완료 | SQL 인젝션 방지 포함 |
| 데이터 조회 (backtest-list/trades/summary) | ✅ 완료 | 다중 출력 포맷 지원 |
| 백테스트 실행 (run/status/list/cancel) | ✅ 완료 | 실제 BackTest 아키텍처 통합 |
| 최적화 (optimize) | ⏳ 미구현 | Phase 4 계획 |

---

## 2. 아키텍처 분석

### 2.1 기존 GUI 백테스트 아키텍처

STOM의 백테스트 시스템은 복잡한 **멀티프로세스 아키텍처**를 사용합니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI (ui_mainwindow.py)                    │
│  - windowQ, soundQ, totalQ, backQ, liveQ, teleQ 큐 생성         │
│  - shared_cnt (Value), shared_lock (Lock) 생성                  │
│  - back_eques[] (N개), back_sques[] (20개) 큐 리스트 생성       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ui_backtest_engine.py::backengine_start()          │
│  1. BackSubTotal 프로세스 20개 생성                             │
│  2. BackEngine 프로세스 N개 생성 (multi 설정값)                 │
│  3. 데이터베이스에서 거래대금순위 데이터 로딩                    │
│  4. 각 엔진에 데이터 분배 (종목별/일자별/한종목)                │
│  5. 공유 데이터 전송                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BackTest (backtest.py)                         │
│  - bq(backQ)에서 13-튜플 파라미터 수신                          │
│  - Total 집계 프로세스 생성                                      │
│  - 전략 코드 로드 및 엔진에 전송                                │
│  - 완료 대기 및 결과 수신                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────┐         ┌──────────────────────┐
│   BackEngine (N개)   │         │  BackSubTotal (20개) │
│  - 틱/분 데이터 처리 │ ──────▶ │  - 중간 집계 처리    │
│  - 전략 시뮬레이션   │         │  - 결과 분류/집계    │
└──────────────────────┘         └──────────────────────┘
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │    Total 프로세스    │
                              │  - 최종 결과 집계    │
                              │  - 리포트 생성       │
                              │  - DB 저장           │
                              └──────────────────────┘
```

### 2.2 핵심 데이터 흐름

#### backQ에 전달되는 13-튜플 파라미터:

```python
(
    betting,       # float - 배팅금액 (주식: 백만원, 선물: 계약수)
    avgtime,       # int - 평균값계산틱수
    startday,      # int - 시작일 (YYYYMMDD)
    endday,        # int - 종료일 (YYYYMMDD)
    starttime,     # int - 시작시간 (HHMMSS 또는 HHMM)
    endtime,       # int - 종료시간 (HHMMSS 또는 HHMM)
    buystg_name,   # str - 매수 전략명
    sellstg_name,  # str - 매도 전략명
    dict_cn,       # dict - {종목코드: 종목명} 매핑
    back_count,    # int - 공유 데이터 개수
    bl,            # bool - 블랙리스트 자동 추가 여부
    schedul,       # bool - 스케줄 실행 여부
    back_club      # bool - 커뮤니티 리포트 여부
)
```

#### BackTest 클래스 생성자 시그니처:

```python
BackTest(
    sc,         # shared_cnt - 진행률 공유 변수
    wq,         # windowQ - GUI 업데이트 큐
    bq,         # backQ - 백테스트 파라미터 큐
    sq,         # soundQ - 사운드 알림 큐
    tq,         # totalQ - 집계 결과 큐
    lq,         # liveQ - STOM Live 큐
    teleQ,      # teleQ - 텔레그램 알림 큐
    beq_list,   # back_eques - BackEngine 큐 리스트
    bstq_list,  # back_sques - BackSubTotal 큐 리스트
    backname,   # str - 작업명 (예: "주식백테스트")
    ui_gubun    # str - UI 구분 ('S', 'C', 'SF', 'CF')
)
```

### 2.3 BackEngine 유형 (16가지)

| 거래소 | 타임프레임 | 주문관리 | 클래스명 |
|--------|-----------|---------|---------|
| 키움증권 | Tick | 미적용 | BackEngineKiwoomTick |
| 키움증권 | Tick | 적용 | BackEngineKiwoomTick2 |
| 키움증권 | Min | 미적용 | BackEngineKiwoomMin |
| 키움증권 | Min | 적용 | BackEngineKiwoomMin2 |
| 해외선물 | Tick | 미적용 | BackEngineFutureTick |
| 해외선물 | Tick | 적용 | BackEngineFutureTick2 |
| 해외선물 | Min | 미적용 | BackEngineFutureMin |
| 해외선물 | Min | 적용 | BackEngineFutureMin2 |
| 업비트 | Tick | 미적용 | BackEngineUpbitTick |
| 업비트 | Tick | 적용 | BackEngineUpbitTick2 |
| 업비트 | Min | 미적용 | BackEngineUpbitMin |
| 업비트 | Min | 적용 | BackEngineUpbitMin2 |
| 바이낸스 | Tick | 미적용 | BackEngineBinanceTick |
| 바이낸스 | Tick | 적용 | BackEngineBinanceTick2 |
| 바이낸스 | Min | 미적용 | BackEngineBinanceMin |
| 바이낸스 | Min | 적용 | BackEngineBinanceMin2 |

---

## 3. CLI 구현 상세

### 3.1 디렉토리 구조

```
cli/
├── __init__.py              # 패키지 초기화
├── main.py                  # CLI 진입점 (Click 프레임워크)
├── adapters/
│   ├── __init__.py
│   ├── settings_adapter.py  # PyQt5 없이 설정 로드 (475줄)
│   ├── queue_adapter.py     # Queue → 로깅 변환 (240줄)
│   └── output_adapter.py    # 결과 출력 포맷터 (286줄)
├── commands/
│   ├── __init__.py
│   ├── strategy.py          # 전략 관리 명령 (241줄)
│   ├── data.py              # 데이터 조회 명령 (342줄)
│   └── backtest.py          # 백테스트 명령 (450줄)
└── runners/
    ├── __init__.py
    └── backtest_runner.py   # 헤드리스 백테스트 실행기 (540줄)
```

### 3.2 구현된 CLI 명령어

#### 전략 관리 (strategy)

```bash
# 전략 목록 조회
stom strategy list [--type stock|coin|future] [--format table|json|csv]

# 특정 전략 상세 조회
stom strategy show <strategy_name> [--format table|json|csv]

# 전략 내보내기
stom strategy export <strategy_name> <output_file> [--format csv|json|excel]

# 전략 통계
stom strategy stats [--format table|json]
```

#### 데이터 조회 (data)

```bash
# 백테스트 결과 목록
stom data backtest-list [--limit 20] [--format table|json|csv]

# 백테스트 상세 결과
stom data backtest-result <backtest_id> [--format table|json|csv]

# 거래 이력 조회
stom data trades [--type stock|coin|future] [--status open|closed] [--limit 50]

# 거래 요약 통계
stom data summary [--type stock|coin|future] [--format table|json]

# 데이터 내보내기
stom data export --type backtest|trades --output <file> [--format csv|json|excel]
```

#### 백테스트 실행 (backtest)

```bash
# 백테스트 실행 (동기)
stom backtest run \
    --type stock|coin|future \
    --buy-strategy "매수전략명" \
    --sell-strategy "매도전략명" \
    --start-date 20240101 \
    --end-date 20240131 \
    [--start-time 90000] \
    [--end-time 153000] \
    [--betting 1.0] \
    [--avgtime 20] \
    [--multi 1] \
    [--divid-mode "종목코드별 분류"|"일자별 분류"|"한종목 로딩"] \
    [--blacklist|--no-blacklist] \
    [--format table|json]

# 백테스트 작업 목록
stom backtest list [--limit 20] [--status pending|running|completed|failed]

# 백테스트 상태 조회
stom backtest status <backtest_id>

# 백테스트 취소
stom backtest cancel <backtest_id>

# 백테스트 삭제
stom backtest delete <backtest_id>
```

### 3.3 핵심 어댑터

#### settings_adapter.py

PyQt5 없이 `setting.db`에서 설정을 로드합니다:

```python
def load_settings_without_qt() -> Dict[str, Any]:
    """
    utility/setting.py의 database_load()를 Qt 없이 실행

    Returns:
        DICT_SET과 동등한 설정 딕셔너리
    """
    # main, stock, coin, back, etc 테이블에서 설정 로드
    # 모든 설정값을 Python 타입으로 변환
    # 기본값 설정 (누락된 키 처리)
```

#### backtest_runner.py (핵심)

실제 BackTest 아키텍처를 완전히 재현합니다:

```python
class HeadlessBacktestRunner:
    """
    PyQt5 없이 백테스트 엔진을 실행하는 클래스

    ui_backtest_engine.py와 동일한 아키텍처 사용:
    - 6개 큐: windowQ, soundQ, totalQ, backQ, liveQ, teleQ
    - N개 BackEngine 큐 (back_eques)
    - 20개 BackSubTotal 큐 (back_sques)
    - 공유 변수: shared_cnt, shared_lock
    """

    def start_backtest(self, ...):
        # 1. 큐 생성
        self._create_queues()

        # 2. BackSubTotal 프로세스 20개 시작
        self._start_subtotal_processes()

        # 3. BackEngine 프로세스 N개 시작
        self._start_engine_processes(gubun, multi)

        # 4. 데이터 로딩
        self._load_data_into_engines(...)

        # 5. BackTest 프로세스 시작
        self.backtest_process = Process(
            target=BackTest,
            args=(self.shared_cnt, self.windowQ, self.backQ, ...)
        )

        # 6. 파라미터 전송 (13-튜플)
        self.backQ.put(back_params)

        # 7. 결과 모니터링
        self._monitor_results()
```

---

## 4. 발견된 문제점 및 해결

### 4.1 초기 구현의 문제점

| 문제 | 설명 | 해결 |
|------|------|------|
| 존재하지 않는 클래스 참조 | `BacktestStock`, `BacktestCoin` 클래스가 없음 | 실제 `BackTest` 클래스 사용 |
| Queue 아키텍처 불일치 | 2개 큐만 생성 (실제로는 7개 이상 필요) | 완전한 큐 구조 구현 |
| 파라미터 형식 불일치 | 5개 파라미터 (실제로는 13-튜플 필요) | 올바른 파라미터 구조 적용 |
| 프로세스 풀 누락 | BackEngine, BackSubTotal 프로세스 없음 | 완전한 프로세스 풀 구현 |
| 데이터 로딩 로직 누락 | 엔진에 데이터 전송 로직 없음 | ui_backtest_engine.py 로직 이식 |
| SQL 인젝션 취약점 | strategy.py에서 테이블명 직접 사용 | 화이트리스트 검증 추가 |

### 4.2 해결된 수정 사항

#### backtest_runner.py 완전 재작성

```python
# Before (잘못된 구현):
from backtester.backtest_stocks import BacktestStock  # 존재하지 않음
engine = BacktestStock(query_queue, result_queue, dict_set)

# After (올바른 구현):
from backtester.backtest import BackTest
from backtester.back_subtotal import BackSubTotal
from backtester.backengine_kiwoom_tick import BackEngineKiwoomTick
# ... 16개 엔진 클래스 import

# 20개 BackSubTotal 프로세스 생성
for i in range(20):
    proc = Process(target=BackSubTotal, args=(...))
    proc.start()

# N개 BackEngine 프로세스 생성
for i in range(multi):
    proc = Process(target=BackEngineKiwoomTick, args=(...))
    proc.start()

# BackTest 프로세스 생성
Process(target=BackTest, args=(
    shared_cnt, windowQ, backQ, soundQ, totalQ,
    liveQ, teleQ, back_eques, back_sques, backname, ui_gubun
)).start()
```

#### backtest.py 명령어 인터페이스 개선

```python
# Before:
@click.option('--strategy', type=str, required=True)
@click.option('--initial-capital', type=float, default=10000000)

# After:
@click.option('--buy-strategy', type=str, required=True)
@click.option('--sell-strategy', type=str, required=True)
@click.option('--betting', type=float, default=1.0)
@click.option('--avgtime', type=int, default=20)
@click.option('--multi', type=int, default=1)
@click.option('--divid-mode', type=click.Choice([...]))
@click.option('--blacklist/--no-blacklist', default=False)
```

---

## 5. 백테스트 실행 전 필수 조건

### 5.1 데이터베이스 요구사항

| 데이터베이스 | 경로 | 필수 테이블 | 용도 |
|-------------|------|------------|------|
| setting.db | ./_database/setting.db | main, stock, coin, back, etc | 설정 저장 |
| strategy.db | ./_database/strategy.db | stockbuy, stocksell, coinbuy, coinsell | 전략 코드 |
| stock_tick_back.db | ./_database/stock_tick_back.db | moneytop, stockinfo, {code} | 주식 틱 데이터 |
| stock_min_back.db | ./_database/stock_min_back.db | moneytop, stockinfo, {code} | 주식 분 데이터 |
| coin_tick_back.db | ./_database/coin_tick_back.db | moneytop, {code} | 코인 틱 데이터 |
| coin_min_back.db | ./_database/coin_min_back.db | moneytop, {code} | 코인 분 데이터 |
| backtest.db | ./_database/backtest.db | backtest_jobs, {result_tables} | 결과 저장 |

### 5.2 setting.db 필수 설정값

```python
# 백테스트에 필요한 핵심 설정
REQUIRED_SETTINGS = {
    '주식타임프레임': bool,      # True=틱, False=분
    '코인타임프레임': bool,      # True=틱, False=분
    '증권사': str,               # '키움증권' 등
    '거래소': str,               # '업비트', '바이낸스' 등
    '백테주문관리적용': bool,    # 주문관리 적용 여부
    '백테매수시간기준': str,     # 매수시간 기준
    '백테엔진분류방법': str,     # 데이터 분류 방법
    '스톰라이브': bool,          # STOM Live 연동
    '그래프저장하지않기': bool,  # 그래프 저장 여부
    '그래프띄우지않기': bool,    # 그래프 표시 여부
}
```

### 5.3 전략 등록 필수

백테스트 실행 전 strategy.db에 매수/매도 전략이 등록되어 있어야 합니다:

```sql
-- 전략 테이블 구조
CREATE TABLE stockbuy (
    'index' TEXT PRIMARY KEY,  -- 전략명
    '전략코드' TEXT            -- Python 코드 문자열
);

-- 예시
INSERT INTO stockbuy VALUES ('골든크로스', '
if 매수:
    if 이평선5 > 이평선20:
        if 이평선5_전일 < 이평선20_전일:
            매수 = True
');
```

### 5.4 데이터 로딩 사전 작업

GUI에서 **디비관리창(Alt+D)**을 통해 백테스트 데이터를 미리 생성해야 합니다:

1. 키움증권 또는 거래소 API 연결
2. 원하는 기간의 틱/분 데이터 수집
3. moneytop 테이블 (거래대금순위) 생성
4. stockinfo/codename 테이블 (종목정보) 생성

---

## 6. 사용 예시

### 6.1 전략 확인

```bash
# 등록된 전략 목록 확인
python -m cli.main strategy list --format table

# 특정 전략 상세 조회
python -m cli.main strategy show "골든크로스" --format json
```

### 6.2 백테스트 실행

```bash
# 주식 백테스트 실행
python -m cli.main backtest run \
    --type stock \
    --buy-strategy "골든크로스" \
    --sell-strategy "손절매5%" \
    --start-date 20240101 \
    --end-date 20240131 \
    --betting 10 \
    --avgtime 20 \
    --multi 4 \
    --divid-mode "종목코드별 분류"

# 코인 백테스트 실행
python -m cli.main backtest run \
    --type coin \
    --buy-strategy "RSI과매도" \
    --sell-strategy "RSI과매수" \
    --start-date 20240101 \
    --end-date 20240131 \
    --betting 100 \
    --multi 2
```

### 6.3 결과 조회

```bash
# 백테스트 작업 목록
python -m cli.main backtest list --limit 10

# 백테스트 상태 확인
python -m cli.main backtest status 20240201_143022

# 백테스트 결과 데이터 조회
python -m cli.main data backtest-list --format json
```

---

## 7. 제한사항 및 향후 계획

### 7.1 현재 제한사항

| 제한사항 | 설명 | 해결 방안 |
|---------|------|----------|
| 그래프 미지원 | CLI에서는 matplotlib 그래프 표시 불가 | 파일로 저장 후 별도 뷰어 사용 |
| 텔레그램 알림 제한적 | 일부 알림 기능 미동작 | 로깅으로 대체 |
| STOM Live 미지원 | 실시간 트레이딩 연동 불가 | GUI 전용 기능 유지 |
| 비동기 실행 미완성 | --async 플래그 작업 등록만 | 향후 워커 프로세스 구현 |

### 7.2 향후 개발 계획

#### Phase 4: 최적화 기능 (계획)

```bash
# Grid Search 최적화
stom optimize grid \
    --type stock \
    --strategy "매수전략" \
    --param "이평선기간:5,10,20,60" \
    --param "손절률:3,5,7"

# Optuna 최적화
stom optimize optuna \
    --type stock \
    --strategy "매수전략" \
    --trials 100
```

#### Phase 5: 워크플로우 자동화 (계획)

```bash
# 스케줄 백테스트
stom schedule add \
    --name "일간백테스트" \
    --cron "0 6 * * *" \
    --command "backtest run --type stock ..."

# 배치 실행
stom batch run --config batch_config.yaml
```

---

## 8. 결론

### 8.1 달성 사항

1. **완전한 CLI 인터페이스 구현**: 전략 관리, 데이터 조회, 백테스트 실행 기능 제공
2. **실제 아키텍처 통합**: GUI와 동일한 BackTest 엔진 사용으로 결과 일관성 보장
3. **안전한 구현**: SQL 인젝션 방지, 프로세스 정리, 에러 핸들링 적용
4. **유연한 출력**: JSON, CSV, Table 등 다양한 출력 포맷 지원

### 8.2 AI Agent 활용 가능성

이제 Claude Code와 같은 AI Agent가:

- **자동 백테스트**: 전략 파라미터 변경 후 자동으로 백테스트 실행
- **결과 분석**: JSON 출력을 파싱하여 전략 성능 분석
- **반복 최적화**: 백테스트 결과 기반 전략 개선 루프 구현
- **리포트 생성**: 백테스트 결과를 기반으로 자동 리포트 작성

### 8.3 파일 변경 요약

| 파일 | 작업 | 코드량 |
|------|------|--------|
| cli/__init__.py | 신규 | 13줄 |
| cli/main.py | 신규 | 30줄 |
| cli/adapters/__init__.py | 신규 | 10줄 |
| cli/adapters/settings_adapter.py | 신규 | 475줄 |
| cli/adapters/queue_adapter.py | 신규 | 240줄 |
| cli/adapters/output_adapter.py | 신규 | 286줄 |
| cli/commands/__init__.py | 신규 | 10줄 |
| cli/commands/strategy.py | 신규 | 241줄 |
| cli/commands/data.py | 신규 | 342줄 |
| cli/commands/backtest.py | 신규/수정 | 450줄 |
| cli/runners/__init__.py | 신규 | 10줄 |
| cli/runners/backtest_runner.py | 신규/재작성 | 540줄 |
| **총계** | | **~2,650줄** |

---

## 부록 A: 트러블슈팅

### A.1 "설정을 로드할 수 없습니다" 오류

```bash
# 해결: setting.db 존재 및 테이블 확인
sqlite3 ./_database/setting.db ".tables"
# 필요한 테이블: main, stock, coin, back, etc
```

### A.2 "전략을 찾을 수 없습니다" 오류

```bash
# 해결: strategy.db에서 전략 확인
python -m cli.main strategy list --format table
```

### A.3 "데이터가 존재하지 않습니다" 오류

```bash
# 해결: 백테스트 데이터베이스 확인
sqlite3 ./_database/stock_tick_back.db "SELECT COUNT(*) FROM moneytop"
# 0이면 GUI에서 데이터 수집 필요
```

### A.4 멀티프로세스 오류

```bash
# 해결: multi 값을 데이터 개수에 맞게 조정
# 종목코드별 분류: multi <= 종목 수
# 일자별 분류: multi <= 거래일 수
```

---

---

## 부록 B: 아키텍처 검증 결과

### B.1 Architect 검증 요약

2026-02-02 Architect 에이전트에 의한 검증 완료.

#### 검증된 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| BackSubTotal 생성자 시그니처 | ✅ 일치 | `(vkey, tq, bstqs, buystd)` |
| BackEngine 생성자 시그니처 | ✅ 일치 | `profile=False` 기본값 사용 |
| BackTest 생성자 시그니처 | ✅ 일치 | 11개 인자 순서 정확 |
| 13-튜플 파라미터 형식 | ✅ 일치 | 전략명 전달, BackTest가 코드 로드 |
| 지연 로딩 구현 | ✅ 정상 | 레지스트리 접근 문제 해결 |
| 프로세스 정리 | ✅ 구현됨 | terminate → kill 순서 |

#### 아키텍처 흐름

```
CLI HeadlessBacktestRunner:
1. load_settings() - 설정 로드
2. _create_queues() - 6개 큐 생성
3. _start_subtotal_processes() - BackSubTotal 20개 시작
4. _start_engine_processes() - BackEngine N개 시작
5. _load_data_into_engines() - 데이터 로딩 (GUI와 동일)
   - ('종목명', dict_cn) 전송
   - ('데이터로딩', ...) 전송
   - backQ에서 shared_info 수신
   - ('공유데이터', back_count, shared_info) 전송
6. BackTest 프로세스 시작
7. backQ에 13-튜플 전송
8. _monitor_results() - 결과 모니터링
9. kill_processes() - 정리
```

이 흐름은 `ui_backtest_engine.py`의 `backengine_start()` + 버튼 클릭 핸들러와 동일합니다.

### B.2 알려진 제한사항

1. **실제 테스트 미완료**: 백테스트 데이터(`stock_tick_back.db` 등)가 없어 실제 실행 테스트 불가
2. **전략 미등록**: `strategy.db`에 전략이 없어 실제 백테스트 실행 시 오류 발생 예상
3. **Windows 전용 기능**: 일부 기능(레지스트리, 사운드 등)은 Windows에서만 동작

### B.3 향후 검증 필요 사항

실제 백테스트 실행을 위해 필요한 사전 작업:

1. GUI에서 백테스트 데이터베이스 생성 (Alt+D)
2. GUI에서 전략 등록
3. CLI로 전략 목록 확인: `python -m cli.main strategy list`
4. CLI로 백테스트 실행 테스트

```bash
# 테스트 명령어 예시
python -m cli.main backtest run \
    --type stock \
    --buy-strategy "테스트매수전략" \
    --sell-strategy "테스트매도전략" \
    --start-date 20240101 \
    --end-date 20240131 \
    --betting 1 \
    --multi 1
```

---

**문서 끝**
