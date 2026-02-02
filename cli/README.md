# STOM CLI Interface

PyQt5 없이 STOM을 CLI(Command Line Interface)로 제어하는 인터페이스입니다.

## 빠른 시작

```bash
# 버전 확인
python -m cli.main --version

# 도움말
python -m cli.main --help

# 주식 전략 목록
python -m cli.main strategy list --type stock

# 백테스트 실행
python -m cli.main backtest run --strategy "전략1" --type stock
```

## 주요 기능

### 1. 전략 관리 (strategy)

```bash
# 전략 목록 조회
python -m cli.main strategy list [--type stock|coin|future] [--format table|json|csv]

# 특정 전략 상세 조회
python -m cli.main strategy show <전략명> [--format table|json]

# 전략 내보내기
python -m cli.main strategy export <전략명> <출력파일>

# 전략 통계
python -m cli.main strategy stats [--type stock|coin|future]
```

### 2. 데이터 조회 (data)

```bash
# 거래 내역 조회
python -m cli.main data trades [--type stock|coin|future] [--date YYYY-MM-DD] [--format table|json|csv]

# 거래 요약
python -m cli.main data summary [--type stock|coin|future] [--format table|json]

# 데이터 내보내기
python -m cli.main data export <출력파일> [--type stock|coin|future] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

# 백테스트 목록
python -m cli.main data backtest-list [--format table|json]

# 백테스트 결과 조회
python -m cli.main data backtest-result <백테스트ID> [--format table|json]
```

### 3. 백테스트 (backtest)

```bash
# 백테스트 실행
python -m cli.main backtest run \
  --strategy "전략명" \
  --type stock|coin|future \
  [--start-date YYYY-MM-DD] \
  [--end-date YYYY-MM-DD] \
  [--initial-capital 10000000] \
  [--async]

# 백테스트 목록
python -m cli.main backtest list [--status all|running|completed|failed]

# 백테스트 상태 조회
python -m cli.main backtest status <백테스트ID>

# 백테스트 취소
python -m cli.main backtest cancel <백테스트ID>

# 백테스트 결과 삭제
python -m cli.main backtest delete <백테스트ID>
```

## 아키텍처

```
cli/
├── __init__.py              # CLI 패키지 초기화
├── main.py                  # Click 기반 메인 진입점
├── adapters/                # PyQt5 → CLI 어댑터들
│   ├── __init__.py
│   ├── settings_adapter.py  # 설정 로드 (PyQt5 없이 DICT_SET 로드)
│   ├── queue_adapter.py     # 프로세스 간 큐 통신
│   └── output_adapter.py    # CLI 출력 포매팅 (table/json/csv)
├── commands/                # CLI 커맨드 그룹
│   ├── __init__.py
│   ├── strategy.py          # 전략 관리 커맨드
│   ├── data.py              # 데이터 조회 커맨드
│   └── backtest.py          # 백테스트 커맨드
└── runners/                 # 헤드리스 실행기
    ├── __init__.py
    └── backtest_runner.py   # 백테스트 헤드리스 러너
```

## 주요 어댑터

### settings_adapter.py
PyQt5 없이 STOM 설정을 로드합니다.

```python
from cli.adapters.settings_adapter import load_settings_without_qt

# 설정 로드
dict_set = load_settings_without_qt()

# 설정 값 사용
print(dict_set['증권사'])
print(dict_set['거래소'])
print(dict_set['주식매수전략'])
```

**지원 기능**:
- setting.db에서 12개 테이블 로드 (main, stock, coin, sacc, cacc, telegram, buyorder, sellorder, etc, back)
- 암호화된 계정 정보 복호화 (증권사 계정 최대 8개, 코인 API 최대 2개)
- 블랙리스트 로드 (주식/선물/코인)
- 주문 관리 설정 완전 지원

### queue_adapter.py
프로세스 간 큐 통신을 위한 헬퍼입니다.

```python
from cli.adapters.queue_adapter import QueueAdapter
from multiprocessing import Queue

adapter = QueueAdapter()
queue = Queue()

# 메시지 전송
adapter.send_message(queue, {'command': 'start', 'args': []})

# 메시지 수신 (타임아웃 5초)
message = adapter.receive_message(queue, timeout=5)
```

### output_adapter.py
CLI 출력을 포매팅합니다.

```python
from cli.adapters.output_adapter import CLIOutputAdapter

adapter = CLIOutputAdapter()

# 테이블 형식 출력
data = [{'name': '전략1', 'profit': 1234567}]
adapter.display_table(data, headers=['name', 'profit'])

# JSON 형식 출력
adapter.display_json(data)

# CSV 형식 출력
adapter.display_csv(data)
```

## 헤드리스 러너

### backtest_runner.py
PyQt5 없이 백테스트 엔진을 실행합니다.

```python
from cli.runners.backtest_runner import HeadlessBacktestRunner

runner = HeadlessBacktestRunner()

# 백테스트 실행
success = runner.start_backtest(
    backtest_type='stock',
    strategy_name='전략1',
    start_date='20240101',
    end_date='20241231'
)

if success:
    print('백테스트 완료')
else:
    print('백테스트 실패')
```

**지원 엔진**:
- BacktestStock (주식)
- BacktestCoin (코인)
- BacktestFuture (선물, 준비 중)

## 의존성

```
click>=8.0.0         # CLI 프레임워크
tabulate>=0.9.0      # 테이블 출력
tqdm>=4.65.0         # 진행률 표시
pandas>=1.5.0        # 데이터 처리
```

## 활용 사례

### 1. 서버 환경에서 백테스트
```bash
# SSH로 서버 접속
ssh user@server

# 백테스트 실행
cd /path/to/STOM
python -m cli.main backtest run --strategy "전략1" --type stock --async
```

### 2. 배치 스크립트
```bash
#!/bin/bash
# daily_backtest.sh

STRATEGIES=("전략1" "전략2" "전략3")

for strategy in "${STRATEGIES[@]}"; do
    echo "Running backtest for $strategy"
    python -m cli.main backtest run \
        --strategy "$strategy" \
        --type stock \
        --start-date $(date -d "30 days ago" +%Y-%m-%d) \
        --end-date $(date +%Y-%m-%d)
done
```

### 3. CI/CD 파이프라인 (GitHub Actions)
```yaml
name: Strategy Validation

on: [push, pull_request]

jobs:
  backtest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run backtest
        run: |
          python -m cli.main backtest run \
            --strategy "전략1" \
            --type stock \
            --format json > result.json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: backtest-results
          path: result.json
```

### 4. Docker 컨테이너
```dockerfile
FROM python:3.9

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "cli.main"]
CMD ["--help"]
```

```bash
# 이미지 빌드
docker build -t stom-cli .

# 백테스트 실행
docker run --rm -v $(pwd)/_database:/app/_database stom-cli \
    backtest run --strategy "전략1" --type stock
```

## 알려진 제약사항

1. **RuntimeWarning**
   - 현상: `'cli.main' found in sys.modules`
   - 영향: 없음 (경고만 출력, 기능 정상)

2. **암호화 계정 정보**
   - CLI에서는 암호화된 정보를 직접 표시하지 않음 (보안상 의도된 동작)

3. **백테스트 엔진 의존성**
   - 실제 실행은 기존 STOM 엔진 의존

## 향후 계획

- **Phase 2**: 실거래 제어 (trade start/stop/status, positions, orders)
- **Phase 3**: 실시간 모니터링 (WebSocket 기반)
- **Phase 4**: 스케줄링 (Cron 기반 자동 실행)
- **Phase 5**: Docker 완전 지원

## 문서

- 전체 개발 보고서: `docs/update_log/20260202_cli_interface.md`
- 변경 로그: `docs/change_log/change_log.md`

## 버전

- **V2.36.U1.5.C1.0** (2026-02-02)
- CLI Component 1.0
