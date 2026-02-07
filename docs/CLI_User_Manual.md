# STOM CLI 사용자 매뉴얼

**버전**: 2.36.U1.5.C2.20
**System Trading Open Machine - 명령줄 인터페이스**

---

## 목차

1. [빠른 시작](#빠른-시작)
2. [AI 에이전트 연동 가이드 (Claude Code 통합)](#ai-에이전트-연동-가이드-claude-code-통합)
3. [명령어 참조](#명령어-참조)
4. [출력 형식](#출력-형식)
5. [JSON 응답 계약 (AI 파싱 기준)](#json-응답-계약-ai-파싱-기준)
6. [Docker 사용법](#docker-사용법)
7. [문제 해결](#문제-해결)
8. [예제](#예제)

---

## 빠른 시작

### 설치

STOM CLI는 Python 3.8 이상과 다음 종속 라이브러리가 필요합니다:

```bash
pip install click pandas sqlite3 openpyxl
```

### CLI 실행

STOM 프로젝트 루트 디렉토리에 있는지 확인하세요:

```bash
python -m cli.main --help
```

또는 직접 실행:

```bash
python cli/main.py --help
```

### 버전 확인

```bash
stom --version
# 출력: STOM, version 2.36.U1.5.C2.20
```

### 처음 실행할 명령어

```bash
# 사용 가능한 모든 명령어 보기
stom --help

# 모든 전략 목록
stom strategy list

# 백테스트(Backtest) 작업 보기
stom backtest list

# 트레이딩 상태 확인
stom trade status

# 실시간 가격 모니터링 (주식)
stom monitor live --type stock --interval 5
```

---

## AI 에이전트 연동 가이드 (Claude Code 통합)

이 섹션은 Claude Code와 같은 AI 에이전트가 STOM CLI를 자동화와 통합을 위해 상호작용하는 방법을 설명합니다.

### 핵심 통합 원칙

1. **JSON 출력**: 자동 파싱을 위해 항상 `--format json` 사용
2. **에러 처리**: 출력의 종료 코드와 에러 메시지 확인
3. **데이터베이스 상태**: 작업 전 데이터베이스 연결 확인
4. **비동기 작업**: 논블로킹 작업을 위해 `--async` 플래그 사용

### AI 에이전트의 STOM CLI 사용 방법

#### 전략 관리 자동화

AI 에이전트는 프로그래매틱하게 전략을 관리할 수 있습니다:

```bash
# 전략을 JSON으로 내보내기 (버전 관리용)
stom strategy export "MyStrategy" output.json --format json

# 설정 파일에서 전략 가져오기
stom strategy import --file strategy_config.json --type stock

# 백테스트 전에 전략 문법 검증
stom strategy validate --name "MyStrategy" --type stock --buy

# 전략 통계를 JSON으로 조회 (분석용)
stom strategy stats --format json
```

**JSON 응답 예시**:
```json
{
  "Total Strategies": 3,
  "Strategies": {
    "stockbuy": 5,
    "stocksell": 3,
    "coinbuy": 2
  }
}
```

#### 백테스트 자동화

분석을 위해 JSON 출력으로 자동 백테스트 실행:

```bash
# 동기 백테스트 실행 및 결과 캡처
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --format json

# 비동기: 백테스트 등록 및 별도로 모니터링
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --async \
  --format json

# 백테스트 상태 확인
stom backtest status 20240115_143022 --format json

# 필터링을 포함한 모든 백테스트 작업 목록
stom backtest list --limit 100 --status completed --format json
```

**JSON 상태 응답**:
```json
{
  "id": "20240115_143022",
  "status": "completed",
  "buy_strategy": "GoldenCross",
  "sell_strategy": "StopLoss",
  "type": "stock",
  "start_date": "20240101",
  "end_date": "20240131",
  "betting": 10.0,
  "created_at": "2024-01-15T14:30:22",
  "completed_at": "2024-01-15T15:45:33"
}
```

#### 최적화 워크플로우

여러 전략으로 매개변수 최적화 자동화:

```bash
# 그리드 서치(Grid Search) 최적화
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"var1": [10, 20, 30], "var2": [0.5, 1.0, 1.5]}' \
  --format json

# 베이지안 최적화 (Optuna)
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 100 \
  --format json

# 최적화 진행 상황 확인
stom optimize status grid_20240115_143022 --format json

# 유전 알고리즘 최적화 (오래 걸리는 작업)
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 50 \
  --async \
  --format json
```

#### AI용 데이터 분석

ML 분석을 위한 거래 데이터 추출:

```bash
# 거래 기록을 JSON으로 조회
stom data trades --type stock --format json

# 모든 거래를 분석용 CSV로 내보내기
stom data export --type trades --output trades.csv --format csv

# 요약 통계 조회
stom data summary --type stock --format json
```

**거래 요약 JSON**:
```json
{
  "Total Trades": 156,
  "Win Rate": 62.5,
  "Profit": 450000.0,
  "Loss": -120000.0,
  "Net Profit": 330000.0,
  "By Type": {
    "stockbuy": {
      "Count": 78,
      "Wins": 50,
      "Losses": 28,
      "Profit": 250000.0,
      "Loss": -80000.0
    }
  }
}
```

#### CI/CD 파이프라인의 데이터베이스 관리

데이터베이스 작업 자동화:

```bash
# 대규모 변경 전 백업 생성
stom db backup --output ./backups --compress

# 데이터베이스 통계 조회
stom db info --type backtest --format json

# 최적화를 위해 모든 데이터베이스 정리
stom db vacuum --type all --yes

# 기존 테스트 데이터 삭제
stom db delete --type stock --date 20230101 --yes
```

### 에러 처리 패턴

AI 에이전트는 에러 처리를 구현해야 합니다:

```python
import subprocess
import json
import sys

def run_stom_command(args: list) -> tuple[int, dict]:
    """STOM CLI 명령어를 실행하고 종료 코드와 JSON 출력을 반환합니다."""
    try:
        result = subprocess.run(
            ['python', '-m', 'cli.main'] + args,
            capture_output=True,
            text=True,
            timeout=300
        )

        # 종료 코드 확인
        if result.returncode != 0:
            return result.returncode, {'error': result.stderr}

        # 요청된 경우 JSON 출력 파싱
        if '--format json' in args and result.stdout:
            try:
                return 0, json.loads(result.stdout)
            except json.JSONDecodeError:
                return 1, {'error': 'Invalid JSON output', 'raw': result.stdout}

        return 0, {'output': result.stdout}

    except subprocess.TimeoutExpired:
        return 124, {'error': 'Command timeout'}
    except Exception as e:
        return 1, {'error': str(e)}

# 자동화에서의 사용
exit_code, result = run_stom_command([
    'backtest', 'run',
    '--type', 'stock',
    '--buy-strategy', 'Golden Cross',
    '--sell-strategy', 'Stop Loss',
    '--start-date', '20240101',
    '--end-date', '20240131',
    '--format', 'json'
])

if exit_code == 0:
    backtest_id = result.get('id')
    print(f"Backtest started: {backtest_id}")
else:
    print(f"Error: {result.get('error')}")
```

### 권장 자동화 스크립트

#### 매일 백테스트 자동 실행

```bash
#!/bin/bash
# 일일 백테스트 실행기

YESTERDAY=$(date -d yesterday +%Y%m%d)
WEEK_AGO=$(date -d '7 days ago' +%Y%m%d)

# 지난 주에 대한 백테스트 실행
python -m cli.main backtest run \
  --type stock \
  --buy-strategy "DailyStrategy" \
  --sell-strategy "DailyStop" \
  --start-date $WEEK_AGO \
  --end-date $YESTERDAY \
  --format json \
  --async

# 최근 백테스트 목록
python -m cli.main backtest list --limit 10 --format json
```

#### 일괄 전략 검증

```bash
#!/bin/bash
# 최적화 전 모든 전략 검증

for strategy in GoldenCross MACD RSI; do
  echo "Validating $strategy..."
  python -m cli.main strategy validate \
    --name "$strategy" \
    --type stock \
    --buy
done
```

#### 거래 분석 파이프라인

```bash
#!/bin/bash
# 거래 추출, 분석 및 보고

# 모든 거래 내보내기
python -m cli.main data export \
  --type trades \
  --output trades_$(date +%Y%m%d).csv

# 통계 조회
python -m cli.main data summary \
  --type stock \
  --format json > trade_stats_$(date +%Y%m%d).json
```

---

## 명령어 참조

### strategy - 전략 관리

SQLite 데이터베이스에 저장된 거래 전략을 관리합니다.

#### strategy list

선택적 유형 필터링을 포함한 모든 등록된 전략을 나열합니다.

```bash
stom strategy list [옵션]

옵션:
  --type [stock|coin|future]  전략 유형별 필터링
  --format [table|json|csv]   출력 형식 (기본값: table)
  --help                      도움말 표시
```

**예제**:
```bash
# 모든 전략 나열 (테이블 형식)
stom strategy list

# 주식 전략만 나열 (파싱용 JSON 형식)
stom strategy list --type stock --format json

# CSV로 내보내기
stom strategy list --format csv > strategies.csv
```

**출력 (테이블)**:
```
전략타입    테이블          name          code                              created_at
stock       stockbuy        GoldenCross   import ta; def signal...          2024-01-01 10:00:00
stock       stocksell       StopLoss      def check_loss(price)...          2024-01-01 10:05:00
coin        coinbuy         MomentumBot   def calculate_momentum...          2024-01-02 14:30:00
```

**출력 (JSON)**:
```json
{
  "strategies": [
    {
      "전략타입": "stock",
      "테이블": "stockbuy",
      "name": "GoldenCross",
      "code": "import ta; def signal...",
      "created_at": "2024-01-01 10:00:00"
    }
  ]
}
```

---

#### strategy show

특정 전략에 대한 상세 정보를 표시합니다.

```bash
stom strategy show 전략명 [옵션]

인수:
  전략명                      표시할 전략의 이름

옵션:
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
# GoldenCross 전략 보기
stom strategy show GoldenCross

# JSON으로 보기
stom strategy show GoldenCross --format json
```

---

#### strategy export

전략을 파일(CSV, JSON 또는 Excel)로 내보냅니다.

```bash
stom strategy export 전략명 출력파일 [옵션]

인수:
  전략명                      전략의 이름
  출력파일                    출력 파일 경로

옵션:
  --format [csv|json|excel]   내보내기 형식 (기본값: csv)
```

**예제**:
```bash
# CSV로 내보내기
stom strategy export GoldenCross strategies/golden_cross.csv

# JSON으로 내보내기
stom strategy export GoldenCross strategies/golden_cross.json --format json

# Excel로 내보내기
stom strategy export GoldenCross strategies/golden_cross.xlsx --format excel
```

---

#### strategy stats

전략 통계와 개수를 표시합니다.

```bash
stom strategy stats [옵션]

옵션:
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
stom strategy stats
stom strategy stats --format json
```

**출력 (테이블)**:
```
============================================================
전략 통계
============================================================

총 전략 수: 5

전략별 항목 수:
  stockbuy: 3
  stocksell: 2
  coinbuy: 2
```

---

#### strategy save

인라인 코드 또는 파일에서 전략을 저장하거나 업데이트합니다.

```bash
stom strategy save [옵션]

옵션:
  --name TEXT                 전략 이름 (필수)
  --type [stock|coin|future]  전략 유형 (필수)
  --buy/--sell                매수 또는 매도 전략 (기본값: buy)
  --code TEXT                 인라인 Python 코드
  --file PATH                 전략 코드 파일 경로
```

**예제**:
```bash
# 인라인 코드에서 저장
stom strategy save \
  --name "MyStrategy" \
  --type stock \
  --code "def signal(): return True"

# 파일에서 저장
stom strategy save \
  --name "GoldenCross" \
  --type stock \
  --buy \
  --file strategies/golden_cross.py

# 매도 전략 저장
stom strategy save \
  --name "StopLoss" \
  --type stock \
  --sell \
  --code "def stop_loss(price): return price < entry * 0.95"
```

---

#### strategy delete

전략을 삭제합니다 (확인 필요).

```bash
stom strategy delete [옵션]

옵션:
  --name TEXT                 전략 이름 (필수)
  --type [stock|coin|future]  전략 유형 (필수)
  --buy/--sell                매수 또는 매도 전략 (기본값: buy)
```

**예제**:
```bash
stom strategy delete --name "OldStrategy" --type stock --buy
# 프롬프트: "정말로 삭제하시겠습니까? (y/N)"
```

---

#### strategy import

JSON 또는 CSV 파일에서 전략을 가져옵니다.

```bash
stom strategy import [옵션]

옵션:
  --file PATH                 가져오기 파일 경로 (필수)
  --type [stock|coin|future]  전략 유형 (필수)
```

**예제**:
```bash
# JSON에서 가져오기
stom strategy import --file strategies.json --type stock

# CSV에서 가져오기
stom strategy import --file strategies.csv --type coin
```

**예상 CSV/JSON 형식**:
```csv
name,code,table
GoldenCross,"def signal()...",stockbuy
StopLoss,"def stop()...",stocksell
```

---

#### strategy validate

전략 문법과 구조를 검증합니다.

```bash
stom strategy validate [옵션]

옵션:
  --name TEXT                 전략 이름 (필수)
  --type [stock|coin|future]  전략 유형 (필수)
  --buy/--sell                매수 또는 매도 전략 (기본값: buy)
```

**예제**:
```bash
stom strategy validate --name "GoldenCross" --type stock --buy
```

**출력**:
```
============================================================
전략 유효성 검사: GoldenCross
============================================================

전략 코드가 유효합니다.
```

---

### data - 데이터 조회 및 내보내기

거래 데이터와 백테스트 결과를 조회합니다.

#### data backtest-list

최근 백테스트 결과를 나열합니다.

```bash
stom data backtest-list [옵션]

옵션:
  --limit INTEGER             최대 결과 수 (기본값: 20)
  --format [table|json|csv]   출력 형식 (기본값: table)
```

---

#### data backtest-result

특정 ID에 대한 상세 백테스트 결과를 조회합니다.

```bash
stom data backtest-result 백테스트ID [옵션]

인수:
  백테스트ID                  백테스트 결과 ID

옵션:
  --format [table|json|csv]   출력 형식 (기본값: table)
```

---

#### data trades

필터링을 포함한 거래 기록을 조회합니다.

```bash
stom data trades [옵션]

옵션:
  --type [stock|coin|future]  자산 유형별 필터링
  --status [open|closed|cancelled]  거래 상태별 필터링
  --limit INTEGER             최대 결과 수 (기본값: 50)
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
# 최근 모든 거래 보기
stom data trades --limit 100

# 종료된 주식 거래 보기
stom data trades --type stock --status closed --format json

# 분석용 CSV로 내보내기
stom data trades --format csv > all_trades.csv
```

---

#### data summary

모든 거래에 대한 요약 통계를 표시합니다.

```bash
stom data summary [옵션]

옵션:
  --type [stock|coin|future]  자산 유형별 필터링
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
stom data summary --type stock
stom data summary --format json
```

**출력 (JSON)**:
```json
{
  "Total Trades": 156,
  "Win Rate": 62.5,
  "Profit": 450000.0,
  "Loss": -120000.0,
  "Net Profit": 330000.0,
  "By Type": {
    "stockbuy": {
      "Count": 78,
      "Wins": 50,
      "Losses": 28,
      "Profit": 250000.0,
      "Loss": -80000.0
    }
  }
}
```

---

#### data export

백테스트 결과 또는 거래 기록을 내보냅니다.

```bash
stom data export [옵션]

옵션:
  --type [backtest|trades]    내보낼 데이터 유형 (필수)
  --output PATH               출력 파일 경로 (필수)
  --format [csv|json|excel]   내보내기 형식 (기본값: csv)
```

**예제**:
```bash
# 모든 거래를 CSV로 내보내기
stom data export --type trades --output trades.csv

# 백테스트 결과를 JSON으로 내보내기
stom data export --type backtest --output results.json --format json

# Excel로 내보내기
stom data export --type trades --output trades.xlsx --format excel
```

---

### backtest - 백테스트 엔진

백테스트를 실행하고 관리합니다.

#### backtest run

지정된 전략과 매개변수로 백테스트를 실행합니다.

```bash
stom backtest run [옵션]

옵션:
  --buy-strategy TEXT         매수 전략 이름 (필수)
  --sell-strategy TEXT        매도 전략 이름 (필수)
  --type [stock|coin|future]  자산 유형 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD 또는 YYYY-MM-DD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD 또는 YYYY-MM-DD (필수)
  --start-time TEXT           시작 시간: HHMMSS 또는 HHMM (선택)
  --end-time TEXT             종료 시간: HHMMSS 또는 HHMM (선택)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
                              주식: 백만 원, 암호화폐: USDT, 선물: 계약
  --avgtime INTEGER           계산용 평균 틱 (기본값: 20)
  --multi INTEGER             멀티프로세스 개수 (기본값: 1)
  --divid-mode TEXT           데이터 분할 모드 (기본값: 종목코드별 분류)
  --blacklist/--no-blacklist  자동 블랙리스트 추가 (기본값: false)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행 (작업만 등록)
```

**예제**:
```bash
# 기본 백테스트
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10

# 비동기 백테스트 (논블로킹)
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --async \
  --format json

# 멀티프로세스 백테스트
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240228 \
  --multi 4 \
  --betting 10

# 특정 거래 시간 포함 (오전 9:30 - 오후 3:30)
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --start-time 093000 \
  --end-time 153000 \
  --betting 10
```

---

#### backtest status

백테스트 작업의 상태를 확인합니다.

```bash
stom backtest status 백테스트ID [옵션]

인수:
  백테스트ID                  백테스트 작업 ID (형식: YYYYMMDD_HHMMSS)

옵션:
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
# 백테스트 상태 확인
stom backtest status 20240115_143022

# 파싱용 JSON 출력 조회
stom backtest status 20240115_143022 --format json
```

**출력 (JSON)**:
```json
{
  "id": "20240115_143022",
  "buy_strategy": "GoldenCross",
  "sell_strategy": "StopLoss",
  "type": "stock",
  "start_date": "20240101",
  "end_date": "20240131",
  "betting": 10.0,
  "avgtime": 20,
  "multi": 1,
  "divid_mode": "종목코드별 분류",
  "blacklist": 0,
  "async": 0,
  "created_at": "2024-01-15T14:30:22",
  "started_at": "2024-01-15T14:30:23",
  "completed_at": "2024-01-15T15:45:33",
  "status": "completed"
}
```

---

#### backtest list

선택적 필터링을 포함한 모든 백테스트 작업을 나열합니다.

```bash
stom backtest list [옵션]

옵션:
  --limit INTEGER             최대 결과 수 (기본값: 20)
  --status [pending|running|completed|failed]  상태별 필터링
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
# 최근 백테스트 나열
stom backtest list --limit 50

# 완료된 백테스트 나열
stom backtest list --status completed --limit 100 --format json

# 실패한 백테스트 나열
stom backtest list --status failed
```

---

#### backtest cancel

대기 중이거나 실행 중인 백테스트를 취소합니다.

```bash
stom backtest cancel 백테스트ID
```

**예제**:
```bash
stom backtest cancel 20240115_143022
# 출력: 백테스트 '20240115_143022'이 취소되었습니다.
```

---

#### backtest delete

데이터베이스에서 백테스트 작업을 삭제합니다.

```bash
stom backtest delete 백테스트ID
```

**참고**: 확인 프롬프트가 필요합니다.

---

### trade - 트레이딩 제어

자동 거래 시작/중지 및 포지션/주문 관리.

#### trade start

지정된 자산 유형에 대한 자동 거래를 시작합니다.

```bash
stom trade start [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
stom trade start --type stock
stom trade start --type coin --format json
```

**참고**: CLI는 상태만 업데이트합니다. 실제 거래는 STOM 메인 애플리케이션이 필요합니다.

---

#### trade stop

자동 거래를 중지합니다.

```bash
stom trade stop [옵션]

옵션:
  --type [stock|coin|future|all]  중지할 자산 유형 (기본값: all)
  --format [table|json]           출력 형식 (기본값: table)
```

**예제**:
```bash
# 모든 거래 중지
stom trade stop

# 주식 거래만 중지
stom trade stop --type stock

# 여러 유형 중지 및 형식 지정
stom trade stop --type coin --format json
```

---

#### trade status

현재 거래 상태와 설정을 확인합니다.

```bash
stom trade status [옵션]

옵션:
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
stom trade status
stom trade status --format json
```

**출력 (테이블)**:
```
======================================================================
트레이딩 상태
======================================================================

[실행 상태]

STOCK:
  상태: running
  시작 시간: 2024-01-15T09:30:00
  마지막 업데이트: 2024-01-15T14:30:00

COIN:
  상태: stopped
  마지막 업데이트: 2024-01-14T18:00:00

[설정 정보]

MAIN:
  setting_version: 2.36
  ...
```

---

#### positions list

현재 포지션을 나열합니다.

```bash
stom positions list [옵션]

옵션:
  --type [stock|coin|future]  자산 유형별 필터링
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
# 모든 포지션 나열
stom positions list

# 주식 포지션만 나열
stom positions list --type stock

# JSON으로 내보내기
stom positions list --format json
```

---

#### positions close

지정된 포지션을 종료합니다.

```bash
stom positions close [옵션]

옵션:
  --all                       모든 포지션 종료
  --code TEXT                 특정 자산 코드 종료
  --type [stock|coin|future]  자산 유형 (--all 사용 시)
```

**예제**:
```bash
# 모든 주식 포지션 종료
stom positions close --all --type stock

# 특정 포지션 종료
stom positions close --code 005930
```

**참고**: 종료 주문을 생성합니다. 실제 실행은 STOM 메인 애플리케이션이 필요합니다.

---

#### orders list

대기 중이고 체결된 주문을 나열합니다.

```bash
stom orders list [옵션]

옵션:
  --type [stock|coin|future]  자산 유형별 필터링
  --status [pending|filled|cancelled]  상태별 필터링
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
# 모든 대기 중인 주문 나열
stom orders list --status pending

# 주식 주문 나열
stom orders list --type stock --format json
```

---

#### orders cancel

대기 중인 주문을 취소합니다.

```bash
stom orders cancel [옵션]

옵션:
  --all                       모든 대기 주문 취소
  --id TEXT                   특정 주문 ID 취소
  --type [stock|coin|future]  자산 유형 (--all 사용 시)
```

**예제**:
```bash
# 모든 주식 주문 취소
stom orders cancel --all --type stock

# 특정 주문 취소
stom orders cancel --id 12345
```

**참고**: 취소 요청을 생성합니다. 실제 실행은 STOM 메인 애플리케이션이 필요합니다.

---

### monitor - 실시간 모니터링

실시간 가격, 손익 및 포지션 변화를 모니터링합니다.

#### monitor live

실시간 가격 정보를 표시합니다.

```bash
stom monitor live [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --interval INTEGER          갱신 간격(초) (기본값: 5)
  --count INTEGER             갱신 횟수 (0: 무한, 기본값: 0)
  --limit INTEGER             표시할 자산 수 (기본값: 10)
  --format [table|json]       출력 형식 (기본값: table)
```

**예제**:
```bash
# 5초마다 주식 가격 모니터링
stom monitor live --type stock

# 3초마다 암호화폐 가격 모니터링, 10회 업데이트
stom monitor live --type coin --interval 3 --count 10

# 20개 자산 표시
stom monitor live --type stock --limit 20
```

**출력 (테이블 - 자동으로 새로고침)**:
```
================================================================================
실시간 가격 (STOCK) - 2024-01-15 14:30:45
업데이트: 5회 | 간격: 5초
================================================================================
종목코드  현재가    등락율    거래량      체결시간
005930   70500.0  +2.5%    1234567    2024-01-15 14:30:45
051910   62400.0  -1.2%    567890     2024-01-15 14:30:44
...
```

---

#### monitor pnl

실시간 손익을 표시합니다.

```bash
stom monitor pnl [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --interval INTEGER          갱신 간격(초) (기본값: 5)
  --count INTEGER             갱신 횟수 (0: 무한, 기본값: 0)
  --format [table|json]       출력 형식 (기본값: table)
  --details/--no-details      포지션 상세 표시 (기본값: false)
```

**예제**:
```bash
# 5초마다 주식 손익 모니터링
stom monitor pnl --type stock

# 상세 정보를 포함한 암호화폐 손익 모니터링
stom monitor pnl --type coin --details

# 손익을 JSON으로 조회
stom monitor pnl --type stock --count 1 --format json
```

**출력 (JSON)**:
```json
{
  "total_pnl": 450000.0,
  "realized_pnl": 0.0,
  "unrealized_pnl": 450000.0,
  "position_count": 5,
  "details": [
    {
      "종목코드": "005930",
      "종목명": "Samsung",
      "수량": 100,
      "평균단가": 70000.0,
      "현재가": 70500.0,
      "수익금": 50000.0,
      "수익률": 0.71
    }
  ]
}
```

---

#### monitor positions

실시간 포지션 변화를 추적합니다.

```bash
stom monitor positions [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --interval INTEGER          갱신 간격(초) (기본값: 5)
  --count INTEGER             갱신 횟수 (0: 무한, 기본값: 0)
  --format [table|json]       출력 형식 (기본값: table)
  --alert/--no-alert          변화 표시 (기본값: false)
```

**예제**:
```bash
# 포지션 변화 모니터링
stom monitor positions --type stock --alert

# 한 번만 확인
stom monitor positions --type coin --count 1
```

---

### optimize - 전략 최적화

다양한 알고리즘을 사용하여 최적의 매개변수를 찾습니다.

#### optimize grid

모든 매개변수 조합에 대해 그리드 서치를 수행합니다.

```bash
stom optimize grid [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --buy-strategy TEXT         매수 전략 이름 (필수)
  --sell-strategy TEXT        매도 전략 이름 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD (필수)
  --params TEXT               JSON 형식 그리드 매개변수 (필수)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행
```

**예제**:
```bash
# 단순 그리드 서치
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"ma_short": [10, 20], "ma_long": [50, 100]}'

# 비동기 그리드 서치
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"ma_short": [10, 20, 30], "ma_long": [50, 100, 150, 200]}' \
  --async \
  --format json
```

---

#### optimize bayesian

Optuna를 사용한 베이지안 최적화입니다.

```bash
stom optimize bayesian [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --buy-strategy TEXT         매수 전략 이름 (필수)
  --sell-strategy TEXT        매도 전략 이름 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD (필수)
  --trials INTEGER            시행 횟수 (필수)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행
```

**예제**:
```bash
# 100회 시행 실행
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 100

# 높은 시행 횟수의 비동기 실행
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 500 \
  --async \
  --format json
```

---

#### optimize ga

유전 알고리즘 최적화입니다.

```bash
stom optimize ga [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --buy-strategy TEXT         매수 전략 이름 (필수)
  --sell-strategy TEXT        매도 전략 이름 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD (필수)
  --generations INTEGER       세대 수 (필수)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행
```

**예제**:
```bash
# 50세대 실행
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 50

# 더 많은 세대의 비동기 실행
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 100 \
  --async
```

---

#### optimize walkforward

강력한 검증을 위한 워크포워드(Walk-Forward) 분석입니다.

```bash
stom optimize walkforward [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --strategy TEXT             전략 이름 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD (필수)
  --train-weeks INTEGER       훈련 기간(주) (기본값: 4)
  --valid-weeks INTEGER       검증 기간(주) (기본값: 1)
  --test-weeks INTEGER        테스트 기간(주) (기본값: 1)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행
```

**예제**:
```bash
# 표준 워크포워드
stom optimize walkforward \
  --type stock \
  --strategy "GoldenCross" \
  --start-date 20240101 \
  --end-date 20240331 \
  --train-weeks 4 \
  --valid-weeks 1 \
  --test-weeks 1

# 사용자 정의 기간
stom optimize walkforward \
  --type stock \
  --strategy "GoldenCross" \
  --start-date 20240101 \
  --end-date 20240630 \
  --train-weeks 8 \
  --valid-weeks 2 \
  --test-weeks 2 \
  --async
```

---

#### optimize backfinder

자동 변수 조합 발견입니다.

```bash
stom optimize backfinder [옵션]

옵션:
  --type [stock|coin|future]  자산 유형 (필수)
  --start-date TEXT           시작 날짜: YYYYMMDD (필수)
  --end-date TEXT             종료 날짜: YYYYMMDD (필수)
  --betting FLOAT             베팅 금액 (기본값: 1.0)
  --min-profit FLOAT          최소 수익 필터 % (기본값: 0.0)
  --format [table|json]       출력 형식 (기본값: table)
  --async                     비동기 실행
```

**예제**:
```bash
# 수익성 조합 찾기
stom optimize backfinder \
  --type stock \
  --start-date 20240101 \
  --end-date 20240131 \
  --min-profit 5.0

# 비동기 백파인더
stom optimize backfinder \
  --type stock \
  --start-date 20240101 \
  --end-date 20240331 \
  --min-profit 3.0 \
  --async
```

---

#### optimize status

최적화 작업 상태를 확인합니다.

```bash
stom optimize status 작업ID [옵션]

인수:
  작업ID                      최적화 작업 ID

옵션:
  --format [table|json]       출력 형식 (기본값: table)
```

---

#### optimize list

최적화 작업을 나열합니다.

```bash
stom optimize list [옵션]

옵션:
  --limit INTEGER             최대 결과 수 (기본값: 20)
  --type [grid|bayesian|ga|walkforward|backfinder]  유형별 필터링
  --status [pending|running|completed|failed]       상태별 필터링
  --format [table|json|csv]   출력 형식 (기본값: table)
```

---

#### optimize cancel

최적화 작업을 취소합니다.

```bash
stom optimize cancel 작업ID
```

---

#### optimize delete

최적화 작업을 삭제합니다.

```bash
stom optimize delete 작업ID
```

---

### db - 데이터베이스 관리

STOM 데이터베이스를 관리합니다.

#### db create

스키마가 포함된 새 데이터베이스를 생성합니다.

```bash
stom db create [옵션]

옵션:
  --type [backtest|tradelist]  데이터베이스 유형 (필수)
  --force                      존재하면 덮어쓰기
```

**예제**:
```bash
stom db create --type backtest
stom db create --type tradelist --force
```

---

#### db append

데이터베이스에 과거 데이터를 추가합니다.

```bash
stom db append [옵션]

옵션:
  --type [stock|coin|future]  데이터 유형 (필수)
  --date TEXT                 YYYYMMDD 형식의 날짜 (필수)
  --source PATH               소스 파일 또는 디렉토리
```

---

#### db delete

날짜별로 데이터를 삭제합니다.

```bash
stom db delete [옵션]

옵션:
  --type [stock|coin|future]  데이터 유형 (필수)
  --date TEXT                 YYYYMMDD 형식의 날짜 (필수)
  --yes                       확인 건너뛰기
```

**예제**:
```bash
stom db delete --type stock --date 20230101
stom db delete --type coin --date 20240101 --yes
```

---

#### db info

데이터베이스 정보와 통계를 표시합니다.

```bash
stom db info [옵션]

옵션:
  --type [backtest|tradelist|strategy|setting|stock_tick|stock_min|coin_tick|coin_min]  (필수)
  --format [table|json|csv]   출력 형식 (기본값: table)
```

**예제**:
```bash
stom db info --type backtest
stom db info --type tradelist --format json
```

**출력 (JSON)**:
```json
{
  "database": "./_database/backtest.db",
  "size_mb": 45.32,
  "modified": "2024-01-15 14:30:00",
  "tables": 3,
  "total_rows": 1250
}
```

---

#### db vacuum

데이터베이스 성능을 최적화합니다.

```bash
stom db vacuum [옵션]

옵션:
  --type [all|backtest|tradelist|...]  데이터베이스 유형 (필수)
  --yes                                확인 건너뛰기
```

**예제**:
```bash
stom db vacuum --type all --yes
stom db vacuum --type backtest
```

---

#### db backup

데이터베이스의 타임스탬프 백업을 생성합니다.

```bash
stom db backup [옵션]

옵션:
  --output PATH               출력 디렉토리 (필수)
  --compress                  백업을 ZIP으로 압축
```

**예제**:
```bash
# 백업 생성
stom db backup --output ./backups

# 압축 백업 생성
stom db backup --output ./backups --compress
```

---

## 출력 형식

### 테이블 형식 (기본값)

ASCII 형식을 사용한 사람이 읽을 수 있는 표 형식입니다.

```bash
stom strategy list --format table
```

**예시 출력**:
```
전략타입    테이블          name          code                code_sample
stock       stockbuy        GoldenCross   import ta; def...   (생략됨)
stock       stocksell       StopLoss      def check_loss...   (생략됨)
```

### JSON 형식

자동화와 통합을 위한 기계 해석 가능한 JSON 출력입니다.

```bash
stom strategy list --format json
```

**예시 출력**:
```json
{
  "strategies": [
    {
      "전략타입": "stock",
      "테이블": "stockbuy",
      "name": "GoldenCross",
      "code": "import ta\ndef signal():\n  ..."
    }
  ]
}
```

**Python에서의 JSON 파싱**:
```python
import json
import subprocess

result = subprocess.run(
    ['python', '-m', 'cli.main', 'strategy', 'list', '--format', 'json'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
for strategy in data.get('strategies', []):
    print(f"{strategy['name']} ({strategy['전략타입']})")
```

### CSV 형식

스프레드시트 가져오기용 쉼표로 구분된 값입니다.

```bash
stom data trades --format csv > trades.csv
```

**예시 출력**:
```csv
거래날짜,거래시간,자산,매수가,매도가,수익금
20240101,093000,005930,70000,70500,50000
20240102,140000,051910,62000,61900,-10000
```

---

## JSON 응답 계약 (AI 파싱 기준)

이 섹션은 `--format json` 사용 시 파싱 안정성을 위한 최소 계약입니다.

### 공통 규칙

1. JSON/CSV 모드에서는 title 배너(`====`)를 출력하지 않습니다.
2. 데이터가 없는 문자열 응답도 JSON 객체로 감쌉니다.
3. JSON 에러 응답은 표준 구조를 따릅니다.

### 빈 결과 응답 (정상)

```json
{
  "message": "백테스트 결과가 없습니다."
}
```

### 표준 에러 응답

```json
{
  "ok": false,
  "error": {
    "code": "DATA_BACKTEST_LIST_FAILED",
    "type": "OperationalError",
    "message": "no such table: backtest_results",
    "title": "백테스트 목록 조회 실패"
  }
}
```

### 명령별 JSON 필드 계약

| 명령 | 루트 타입 | 필수 필드 | 선택 필드 |
|------|------|------|------|
| `stom db info --format json` | object | `database`, `size_mb`, `modified`, `tables`, `total_rows`, `table_info` | - |
| `stom data backtest-list --format json` | array 또는 object | (배열일 때) 결과 row 객체들, (객체일 때) `message` | - |
| `stom positions list --format json` | array 또는 object | (배열일 때) 포지션 row 객체들, (객체일 때) `message` | - |
| `stom optimize list --format json` | array 또는 object | (배열일 때) 작업 row 객체들, (객체일 때) `message` | - |
| `stom trade status --format json` | object | `trading_status`, `configuration` | - |
| JSON 에러 공통 | object | `ok`, `error.code`, `error.type`, `error.message`, `error.title` | - |

### 파서 구현 권장사항

1. 먼저 `returncode` 확인 후, `stdout` JSON 파싱을 시도합니다.
2. 파싱 후 `ok == false`이면 에러로 처리합니다.
3. 루트가 배열인 명령과 객체인 명령을 모두 처리하도록 분기합니다.
4. `message` 단독 응답은 빈 결과로 간주합니다.

상세 계약 문서:
- `docs/contracts/CLI_JSON_Contract.md`

---

## Docker 사용법

### Docker 이미지 빌드

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /stom

# 프로젝트 파일 복사
COPY . .

# 종속 라이브러리 설치
RUN pip install -r requirements.txt

# CLI를 진입점으로 설정
ENTRYPOINT ["python", "-m", "cli.main"]
```

**빌드 명령어**:
```bash
docker build -t stom-cli:latest .
```

### Docker에서 STOM CLI 실행

```bash
# 컨테이너에서 백테스트 실행
docker run --rm \
  -v $(pwd)/data:/stom/data \
  -v $(pwd)/_database:/stom/_database \
  stom-cli:latest backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131

# 전략 목록 조회
docker run --rm \
  -v $(pwd)/_database:/stom/_database \
  stom-cli:latest strategy list --format json
```

### Docker Compose 예제

```yaml
version: '3.8'

services:
  stom-cli:
    build: .
    image: stom-cli:latest
    volumes:
      - ./_database:/stom/_database
      - ./strategies:/stom/strategies
      - ./data:/stom/data
    environment:
      - PYTHONUNBUFFERED=1
    command: backtest run --type stock --buy-strategy "GoldenCross" --sell-strategy "StopLoss" --start-date 20240101 --end-date 20240131
```

**docker-compose로 실행**:
```bash
docker-compose run --rm stom-cli strategy list
docker-compose run --rm stom-cli backtest run ...
```

---

## 문제 해결

### 일반적인 문제

#### "No module named 'cli'"

**문제**: Python이 CLI 모듈을 찾을 수 없습니다.

**해결 방법**:
```bash
# PYTHONPATH에 프로젝트 루트가 포함되어 있는지 확인
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 프로젝트 디렉토리에서 실행
cd /path/to/STOM_V
python -m cli.main --help
```

#### RuntimeWarning 메시지

STOM은 더 이상 사용되지 않는 pandas 또는 numpy 기능에 대해 RuntimeWarning을 발생시킬 수 있습니다:

```
RuntimeWarning: invalid value encountered in sqrt
```

**설명**: 이는 일반적으로 금융 계산이나 최적화 알고리즘이 엣지 케이스를 만날 때 발생합니다.

**해결 방법**: 경고는 치명적이지 않으며 억제할 수 있습니다:

```bash
python -W ignore::RuntimeWarning -m cli.main backtest run ...
```

#### 데이터베이스 잠금 에러

**문제**: 작업 중 "Database is locked" 에러 발생.

**해결 방법**:
```bash
# 데이터베이스 정리/최적화로 잠금 해제
stom db vacuum --type backtest --yes

# 데이터베이스를 사용 중인 다른 프로세스 확인
lsof _database/*.db  # macOS/Linux에서
```

#### 전략을 찾을 수 없음

**문제**: "Strategy 'X' not found in database" 에러.

**해결 방법**:
```bash
# 전략이 존재하는지 확인
stom strategy list --format json

# 데이터베이스 직접 확인
sqlite3 _database/strategy.db "SELECT name FROM stockbuy;"

# 누락된 경우 전략 저장
stom strategy save --name "MyStrategy" --type stock --code "def signal(): return True"
```

#### 백테스트 타임아웃

**문제**: 백테스트가 너무 오래 걸리거나 타임아웃.

**해결 방법**:
```bash
# 길어질 백테스트는 비동기 모드 사용
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20200101 \
  --end-date 20240131 \
  --async

# 멀티프로세스를 사용하여 속도 향상
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20200101 \
  --end-date 20240131 \
  --multi 4
```

#### 연결 거부됨

**문제**: 데이터 소스에 연결할 수 없습니다.

**해결 방법**:
```bash
# STOM 메인 애플리케이션이 실행 중인지 확인
# _database/ 디렉토리에 데이터베이스 파일이 존재하는지 확인

# 누락된 경우 데이터베이스 생성 시도
stom db create --type backtest --force
stom db create --type tradelist --force
```

---

## 예제

### 완전한 워크플로우: 전략 개발에서 백테스트까지

```bash
# 1. 전략 생성 및 저장
stom strategy save \
  --name "MyGoldenCross" \
  --type stock \
  --buy \
  --code "
import ta

def signal(data):
    ma_short = ta.trend.sma_indicator(data['close'], 20)
    ma_long = ta.trend.sma_indicator(data['close'], 50)
    return ma_short > ma_long
"

# 2. 매도 전략 생성
stom strategy save \
  --name "MyStopLoss" \
  --type stock \
  --sell \
  --code "
def signal(price, entry_price):
    return price < entry_price * 0.95
"

# 3. 전략 검증
stom strategy validate --name "MyGoldenCross" --type stock --buy
stom strategy validate --name "MyStopLoss" --type stock --sell

# 4. 백테스트 실행
stom backtest run \
  --type stock \
  --buy-strategy "MyGoldenCross" \
  --sell-strategy "MyStopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --multi 2

# 5. 백테스트 상태 확인
stom backtest list --limit 5 --format json

# 6. 결과 분석
stom data summary --type stock --format json
```

### AI 에이전트: 자동화된 매개변수 최적화 파이프라인

```python
#!/usr/bin/env python3
"""
STOM CLI용 자동화된 최적화 파이프라인.
여러 최적화 알고리즘을 병렬로 실행합니다.
"""

import subprocess
import json
import time
from datetime import datetime, timedelta

def run_stom(args):
    """STOM CLI 명령어를 실행하고 JSON 결과를 반환합니다."""
    result = subprocess.run(
        ['python', '-m', 'cli.main'] + args,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except:
            return {'output': result.stdout}
    else:
        raise Exception(result.stderr)

# 설정
asset_type = 'stock'
buy_strategy = 'GoldenCross'
sell_strategy = 'StopLoss'
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

# 1. 그리드 서치
print("Running Grid Search...")
grid_result = run_stom([
    'optimize', 'grid',
    '--type', asset_type,
    '--buy-strategy', buy_strategy,
    '--sell-strategy', sell_strategy,
    '--start-date', start_date,
    '--end-date', end_date,
    '--params', '{"ma_short": [10, 20], "ma_long": [50, 100]}',
    '--async',
    '--format', 'json'
])
grid_job_id = grid_result['id']
print(f"Grid job started: {grid_job_id}")

# 2. 베이지안 최적화
print("Running Bayesian Optimization...")
bayesian_result = run_stom([
    'optimize', 'bayesian',
    '--type', asset_type,
    '--buy-strategy', buy_strategy,
    '--sell-strategy', sell_strategy,
    '--start-date', start_date,
    '--end-date', end_date,
    '--trials', '100',
    '--async',
    '--format', 'json'
])
bayesian_job_id = bayesian_result['id']
print(f"Bayesian job started: {bayesian_job_id}")

# 3. 완료 대기
print("Waiting for optimization to complete...")
for job_id in [grid_job_id, bayesian_job_id]:
    while True:
        status = run_stom(['optimize', 'status', job_id, '--format', 'json'])
        if status['status'] in ['completed', 'failed']:
            print(f"Job {job_id}: {status['status']}")
            break
        time.sleep(10)

# 4. 결과 비교
grid_status = run_stom(['optimize', 'status', grid_job_id, '--format', 'json'])
bayesian_status = run_stom(['optimize', 'status', bayesian_job_id, '--format', 'json'])

print("\n=== RESULTS ===")
print(f"Grid Search Result: {grid_status.get('result', 'N/A')}")
print(f"Bayesian Result: {bayesian_status.get('result', 'N/A')}")
```

### 데이터 내보내기 및 분석

```bash
# 분석을 위해 모든 거래 내보내기
stom data export --type trades --output analysis/trades.csv --format csv

# 요약 통계 조회
stom data summary --type stock --format json > analysis/summary.json

# 백테스트 결과 내보내기
stom data export --type backtest --output analysis/backtest.xlsx --format excel

# Python으로 분석
python << 'EOF'
import pandas as pd
import json

# 거래 데이터 로드
trades = pd.read_csv('analysis/trades.csv')
print(f"Total trades: {len(trades)}")
print(f"Win rate: {(trades['수익금'] > 0).sum() / len(trades) * 100:.2f}%")
print(f"Total profit: {trades['수익금'].sum():,.0f}")

# 요약 로드
with open('analysis/summary.json') as f:
    summary = json.load(f)
print(f"\nNet Profit: {summary['Net Profit']:,.0f}")
print(f"By Type: {summary['By Type']}")
EOF
```

---

## 버전 히스토리

- **2.36.U1.5.C2.20**: runner 실패 시나리오(queue timeout, process join timeout) 계약 테스트를 추가해 예외/강제종료 경계 동작 검증 강화
- **2.36.U1.5.C2.19**: runner 계층(backtest/optimize) 경계·오류·정리 경로 테스트를 보강해 runner 커버리지와 전체 CLI 커버리지를 개선
- **2.36.U1.5.C2.18**: tests/README를 최신 테스트 구조(243개) 기준으로 동기화하고 파일별 테스트 수/실행 가이드를 최신화
- **2.36.U1.5.C2.17**: backtest/optimize run 실패(JSON 파라미터 오류, DB 오류) 계약을 jsonschema로 확장하고 JSON 에러 종료 경로를 정리해 실패 payload 파싱 안정성 강화
- **2.36.U1.5.C2.16**: backtest/optimize run 성공 payload 계약을 status/list 계약과 분리하고 run 전용 jsonschema 검증을 추가, 작업 ID를 마이크로초 단위로 생성해 충돌 리스크 완화
- **2.36.U1.5.C2.15**: CLI JSON 계약서에 명령별 변경 이력 표와 계약 변경 운영 규칙을 추가해 계약 변경 추적성을 강화
- **2.36.U1.5.C2.14**: optimize status/list/cancel 성공 경로 분기 테스트를 추가해 전체 커버리지를 55% 기준으로 끌어올리고 CI 하한선을 55로 상향
- **2.36.U1.5.C2.13**: jsonschema 계약 검증 범위를 backtest/optimize list/status까지 확장하고 상태 조회 성공 검증을 안정화(DB 최신 ID 기반)하여 테스트 충돌 리스크 제거
- **2.36.U1.5.C2.12**: positions/orders 성공 JSON payload 계약 테스트 + jsonschema 자동검증 + 전체 CLI 커버리지 하한선 적용
- **2.36.U1.5.C2.11**: positions/orders 취소/청산 실패 JSON 에러코드 계약 추가 + runner/schema 커버리지 하한선 적용
- **2.36.U1.5.C2.10**: trade JSON 계약 테스트 강화 + runner/schema 커버리지 스냅샷 + 독립 계약 문서 추가
- **2.36.U1.5.C2.9**: JSON 응답 계약 문서화 + trade 명령 인코딩 정리 + CI 러너/스키마 게이트 추가
- **2.36.U1.5.C2.8**: C2.5~C2.8 안정화(스키마 정합성/테스트 신뢰도/러너 강화/JSON 에러 표준화) 반영
- **2.36.U1.5.C2.0**: 전체 명령어 참조를 포함한 CLI 기준 버전
- **2.36.U1.5.C1.0**: 초기 CLI 개발 검토 릴리스
- **2.36.U1**: ui_mainwindow .pyd에서 .py로 마이그레이션

---

## 지원 및 문서

자세한 아키텍처 정보는 다음을 참조하세요:
- `docs/AGENTS.md` - AI 에이전트 통합 가이드
- `docs/change_log/` - 버전별 변경 로그
- `docs/update_log/` - 날짜별 상세 업데이트 기록

---

**문서 마지막 업데이트**: 2026-02-07
**관리자**: STOM 개발팀
