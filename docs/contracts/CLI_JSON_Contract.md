# STOM CLI JSON 응답 계약서

## 1. 목적
- `--format json` 출력의 파싱 안정성을 보장하기 위한 계약 문서.
- AI 에이전트/자동화 스크립트/CI 파이프라인이 동일한 규칙으로 응답을 해석하도록 표준화.

## 2. 공통 규칙
1. JSON 모드에서는 배너(`====`)를 출력하지 않는다.
2. 빈 결과 문자열도 JSON 객체로 래핑한다.
3. 에러는 표준 에러 페이로드 구조를 따른다.
4. 명령에 따라 루트 타입은 `object` 또는 `array`가 될 수 있다.

## 3. 표준 응답 형태

### 3.1 성공(객체)
```json
{
  "database": "./_database/strategy.db",
  "size_mb": 0.21,
  "tables": 25
}
```

### 3.2 성공(배열)
```json
[
  {
    "id": "grid_20260206_192811",
    "type": "grid",
    "status": "pending"
  }
]
```

### 3.3 빈 결과(메시지 객체)
```json
{
  "message": "포지션이 없습니다."
}
```

### 3.4 에러(표준)
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

## 4. 명령별 계약

| 명령 | 루트 타입 | 필수 키 |
|------|------|------|
| `stom db info --type <db> --format json` | object | `database`, `size_mb`, `modified`, `tables`, `total_rows`, `table_info` |
| `stom trade status --format json` | object | `trading_status`, `configuration` |
| `stom positions list --format json` | array 또는 object | 배열일 경우 row 객체 목록, 객체일 경우 `message` |
| `stom orders list --format json` | array 또는 object | 배열일 경우 row 객체 목록, 객체일 경우 `message` |
| `stom data backtest-list --format json` | array 또는 object | 배열일 경우 row 객체 목록, 객체일 경우 `message` |
| `stom optimize list --format json` | array 또는 object | 배열일 경우 row 객체 목록, 객체일 경우 `message` |
| JSON 에러 공통 | object | `ok`, `error.code`, `error.type`, `error.message`, `error.title` |

## 5. 파서 권장 알고리즘
1. 프로세스 종료코드(`returncode`)를 먼저 확인한다.
2. `stdout`를 JSON 파싱한다.
3. 파싱 결과가 객체이고 `ok == false`이면 실패로 처리한다.
4. 파싱 결과가 객체이고 `message`만 있으면 빈 결과로 처리한다.
5. 파싱 결과가 배열이면 데이터 목록으로 처리한다.

## 6. 검증 테스트
- `tests/test_output_formats.py`
- `tests/test_trade.py`
- `tests/test_data.py`
- `tests/test_monitor.py`
- `tests/test_json_contract_schema.py` (jsonschema 자동검증)
- `tests/test_backtest.py`
- `tests/test_optimize.py`

## 7. 명령별 샘플 및 테스트 링크

| 명령 | 샘플 응답 유형 | 테스트 위치 |
|------|------|------|
| `stom trade status --format json` | 객체(`trading_status`, `configuration`) | `tests/test_trade.py` (`test_trade_status_json`) |
| `stom positions list --format json` | 배열 또는 `{"message": ...}` | `tests/test_trade.py` (`test_positions_list_json_payload_contract`) |
| `stom orders list --format json` | 배열 또는 `{"message": ...}` | `tests/test_trade.py` (`test_orders_list_json_payload_contract`) |
| `stom positions close --format json` 실패 | 표준 에러(`ok=false`, `POSITIONS_CLOSE_INVALID_ARGS`) | `tests/test_trade.py` (`test_positions_close_missing_target_json_error_contract`) |
| `stom orders cancel --format json` 실패 | 표준 에러(`ok=false`, `ORDERS_CANCEL_INVALID_ARGS`) | `tests/test_trade.py` (`test_orders_cancel_missing_target_json_error_contract`) |
| `stom positions close --all --format json` 성공 | 객체(`ok=true`, `order_type`, `asset_type`, `status`) | `tests/test_trade.py` (`test_positions_close_all_json_success_contract`) |
| `stom orders cancel --all --format json` 성공 | 객체(`ok=true`, `cancel_type`, `asset_type`, `status`) | `tests/test_trade.py` (`test_orders_cancel_all_json_success_contract`) |
| `stom data backtest-list --format json` | 배열 또는 `{"message": ...}` | `tests/test_data.py` |
| `stom db info --format json` | 객체(`database`, `table_info` 등) | `tests/test_db.py` |
| `stom backtest list --format json` | 배열 또는 `{"message": ...}` | `tests/test_json_contract_schema.py` (`test_backtest_list_schema`) |
| `stom optimize list --format json` | 배열 또는 `{"message": ...}` | `tests/test_json_contract_schema.py` (`test_optimize_list_schema`) |
| `stom backtest status unknown_job_id --format json` | 객체(`message`) | `tests/test_json_contract_schema.py` (`test_backtest_status_unknown_schema`) |
| `stom optimize status unknown_job_id --format json` | 객체(`message`) | `tests/test_json_contract_schema.py` (`test_optimize_status_unknown_schema`) |
| `stom backtest status <id> --format json` | 객체(`id`, `status`, `created_at` 등) | `tests/test_json_contract_schema.py` (`test_backtest_status_success_schema`) |
| `stom optimize status <id> --format json` | 객체(`id`, `type`, `asset_type`, `status` 등) | `tests/test_json_contract_schema.py` (`test_optimize_status_success_schema`) |

## 8. 자동검증 파이프라인
1. 로컬: `python -m pytest tests/test_json_contract_schema.py -q`
2. CI(Unit): `pytest tests/ -m "not integration and not slow"`
3. CI(Coverage): `pytest tests/ --cov=cli --cov-fail-under=55`

## 9. 명령별 계약 변경 이력

| 명령 | 버전 | 변경 필드/구조 | 호환성 | 테스트 링크 |
|------|------|----------------|--------|-------------|
| `trade status` | C2.10 | `trading_status`, `configuration` 필드 계약 명시 | 하위호환 | `tests/test_trade.py::test_trade_status_json` |
| `positions close` 실패 | C2.11 | 표준 에러(`ok=false`, `error.code=POSITIONS_CLOSE_INVALID_ARGS`) 계약 추가 | 하위호환 | `tests/test_trade.py::test_positions_close_missing_target_json_error_contract` |
| `orders cancel` 실패 | C2.11 | 표준 에러(`ok=false`, `error.code=ORDERS_CANCEL_INVALID_ARGS`) 계약 추가 | 하위호환 | `tests/test_trade.py::test_orders_cancel_missing_target_json_error_contract` |
| `positions close --all` 성공 | C2.12 | `ok`, `order_type`, `asset_type`, `status`, `message` 계약 명시 | 하위호환 | `tests/test_trade.py::test_positions_close_all_json_success_contract` |
| `orders cancel --all` 성공 | C2.12 | `ok`, `cancel_type`, `asset_type`, `status`, `message` 계약 명시 | 하위호환 | `tests/test_trade.py::test_orders_cancel_all_json_success_contract` |
| `backtest status` | C2.13 | 미존재 ID는 `message`, 존재 ID는 상태 객체(`id`, `status`, `created_at` 등) 계약 명시 | 하위호환 | `tests/test_json_contract_schema.py::test_backtest_status_unknown_schema`, `tests/test_json_contract_schema.py::test_backtest_status_success_schema` |
| `optimize status` | C2.13 | 미존재 ID는 `message`, 존재 ID는 상태 객체(`id`, `type`, `asset_type`, `status` 등) 계약 명시 | 하위호환 | `tests/test_json_contract_schema.py::test_optimize_status_unknown_schema`, `tests/test_json_contract_schema.py::test_optimize_status_success_schema` |
| `optimize list` | C2.13 | 배열 또는 `{"message": ...}` 계약 명시 및 jsonschema 자동검증 연동 | 하위호환 | `tests/test_json_contract_schema.py::test_optimize_list_schema` |
| `backtest list` | C2.13 | 배열 또는 `{"message": ...}` 계약 명시 및 jsonschema 자동검증 연동 | 하위호환 | `tests/test_json_contract_schema.py::test_backtest_list_schema` |

## 10. 계약 변경 운영 규칙
1. 계약 변경은 명령 단위로 본 문서 9절 이력 표에 반드시 추가한다.
2. 변경 필드가 있으면 필드명과 타입/의미를 요약하고 호환성(하위호환/비호환)을 명시한다.
3. 계약 변경은 최소 1개 이상의 자동화 테스트 링크를 함께 등록한다.
4. CI 커버리지/계약 검증 기준 변경 시 8절 파이프라인 수치를 즉시 동기화한다.
