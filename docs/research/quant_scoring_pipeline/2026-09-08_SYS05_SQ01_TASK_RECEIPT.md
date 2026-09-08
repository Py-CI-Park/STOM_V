# SYS-05 SQ01 데이터 계약 CSV 품질 연결 TASK_RECEIPT

2026-09-08. 부모 `23d3b16d3087af2b9b5d1e09a4d86408808e3cd3`.
branch `codex/process-research-sys-05-quality`. 이 문서 포함 commit은 로컬 개발 checkpoint이며 정본 병합/배포가 아니다.

## 판정과 실제 연결

**SQ01의 데이터 계약 소비 경로 완료. SYS05 전체·P03 전체·모든 분석 경로 완료는 아니다.**

```text
기존 job manager (실행 상태, metrics.trade_count, CSV 경로)
  -> bounded bytes snapshot (읽기 1회)
      +-> 공식 54/37 이름 검사 -> 기존 _normalize_row -> typed 정상행/문제
      +-> 기존 TradeArtifactContract (동일 bytes SHA·행수)
  -> 기존 /bt/trade-path/data-contract
  -> 기존 V4 BtTradePathTab + 새 CSV 품질 카드
```

기존 Card/Bundle/TradePath/Catalog를 대체하지 않았다. 새 DB/table·참조 parser 복제·병렬 운영 앱 없음. 기존 `load_trades_csv`와 full_analysis는 그대로이며 다른 소비자로의 전파는 SQ01B다.

## 변경 파일 책임

| 파일 | 단일 책임 |
|---|---|
| trade_csv_models.py | 불변 품질·문제·정상 거래·snapshot 결과 타입 |
| trade_csv_snapshot.py | bounded bytes read와 동일 버퍼 CSV parse/hash |
| trade_csv_schema.py | 실제 owner 이름 기반 modern54/legacy37 판별 |
| trade_csv_rows.py | 숫자/시각 검사 후 기존 행 정규화 재사용 |
| trade_csv_quality.py | 오류 종류·상세·수신/거부 수·준비 판정 |
| trade_contract.py / API | 같은 snapshot을 기존 계약·품질 envelope에 연결 |
| bt-csv-quality.jsx / 호출부 / CSS | 한국어 품질·행수·문제 표시, source 전환·지연 응답 보호 |

64MiB/250,000레코드/5,000,000 cells/128컬럼 상한을 두었다. 오류 상세는100개까지만 보이되 issue_count와 전체 issue_codes를 따로 보존한다. row 번호는 헤더를1로 센 논리 CSV 레코드 번호이며 물리 줄 번호와 다를 수 있다. 정상0은 보존하며 읽기/파싱 실패 count는 null이다.

공식 schema는 utility.setting_base columns_bt/btf와 back_static B/S/R 소유 상수를 사용한다. legacy는 737d3cde 확장 전 B14개다. 6열/custom54는 행 진단 가능하더라도 공식 schema 준비 통과하지 않는다. 빈 optional feature는 기존 profile 의미를 보존하며 전체 feature 완비를 인증하지 않는다.

## 발견한 문제와 수정

| 문제 | red 관측 | 수정 |
|---|---|---|
| typed loader 부재 | 11 failed, exit1 | 신규 타입 경계 |
| API 품질 필드 부재·두 번 파일 열기 | 5 failed, exit1; opens2 | 품질 envelope·snapshot builder |
| 공식 schema 검증 누락 | custom6 VALID | owner 이름 검증·가짜54 거부 |
| 100개 이후 오류 종류 유실 | late NaN 종류가 receipt에서 사라짐 | issue_codes 별도 요약 |
| 실제 거래 수 대조 누락 | metrics.trade_count 무시 | optional strict count 전달; 없는 값은 null |
| Unicode 숫자 시각으로 API500 | int('²...') ValueError | 기존 경계 profiler의 ASCII 숫자 제한 |
| 비투영 B factor NaN | B_현재가 NaN인데 VALID | B/S/R 숫자값도 검사 |
| UI 판정 혼동 | 품질 미충족 아래에 기존 '분석 가능' 표시 | '경로 자료 점검 통과'로 의미 분리 |

기존 contract의 schema_variant는 열수 기반 분류이므로 화면 라벨을 'CSV 열수 분류'로 명확히 했다. 공식 이름/구성 검사는 품질 카드의 official_schema로 따로 표시한다. 마지막 문구 변경 후 JSX8시나리오·빌드 및 실제 브라우저 정상 화면을 다시 확인했다.

첫4개 review 회귀 모두 red(exit1) 확인 후 수정했다. 숫자·시각·헤더·상태 판정을 소형 helper로 분리하고 기존 공개 signature/행 정규화 소유권은 유지했다.

## 시험 결과

| 실행 | 최종 실제 결과 | 범위 |
|---|---|---|
| 신규4파일 + 기존 backtest_analysis + V4 shell parity | **113 passed in18.52s, exit0** | 생산 모듈 import + 합성 파일/API |
| 독립 신규4파일 재검증 | 30 passed in12.22s, exit0 | 위113과 중복, 합산하지 않음 |
| 생산 JSX harness | 8/8, errors=[], exit0 | 정상/무거래/누락/부분/실패/미확인/HTML escape |
| npm run build | exit0 | runtime JSX142/graph595·Vite·실제 번들 및6HTML 갱신 |
| 신규5개 Python 모듈 ruff 선택 규칙 | PASS | E,F,I,C90,UP,B,SIM,TCH |
| 신규5개 Python 모듈 basedpyright | 0 errors / 1 warning | 기존 private _normalize_row 재사용 경고를 명시적으로 유지 |

원시 로그: `C:/Users/parkc/STOM_Verification/v1.5_20260907/sys05-sq01-*.log`.
최종 pytest 대상: test_trade_csv_quality.py, test_trade_quality_api.py, test_trade_quality_review_regressions.py, test_qsp7_data_contract.py, test_backtest_analysis.py, test_shell_wiring_parity.py (모두 tests/unit/dashboard).
기존 F02의10개 타입 오류, pytest_asyncio의 fixture scope 경고는 이 작업의 전체 정적/환경 PASS로 숨기지 않는다.

파일 크기 점검: 신규 Python 모듈27~151 nonblank/noncomment lines, 기존 contract197, API82. 기존 BtTradePathTab은220으로 경고 구간이며, 다음 기능 확장 시 inspection/source 선택 hook 분리를 우선 검토한다. 이번에는250 상한을 넘지 않는다. LSP/AST 도구는 현재 도구 목록에 없어서 실제 타입 진단·호출자 조회·회귀로 확인했다.

## 실제 인하우스 브라우저 QA

재현: `python -X utf8 tests/manual/sq01_browser_fixture.py` → localhost18765. 실제 생산 BtTradePathTab 번들과 data-contract API를 사용하고 job 목록/원천만 합성 fixture다. 전체 운영 app/실제 market DB를 실행하지 않는다. 연구용 POST route 자체가 없다.

| 시나리오 | 실제 화면 관측 |
|---|---|
| 정상 | 원본1/정상1/거부0/예상1, 동일 계약 해시, CSV 분석 준비 충족 |
| 정상 무거래 | 모두0, 오류와 구분, 시작 비활성 |
| 부분 파싱 | 원본2/정상1/거부1, 오류 상세 한국어, 시작 비활성 |
| 실행 실패+정상CSV | 품질 정상과 실행 실패를 동시에 표시, 시작 비활성 |
| 파일 없음 | count는 —, 해시 미확인, 시작 비활성 |
| 지연A→B | A 대기 중 B 무거래 선택 후 A 해제; B의0행/해시/차단 유지 |
| 키보드·좁은 폭 | 640px에서 Enter로 문제 상세 열림·표시 확인 |

초기 합성 preflight 응답에 기존 renderer 필수 source 필드가 빠져 화면 오류가 있었다. fixture를 실제 응답 형식에 맞춰 수정한 후 위 시나리오를 확인했다. 생산 코드 오류로 오인하지 않는다. 390px DOM 측정은 도구 timeout으로 완료 판정하지 않았다. 200% 전체 확대/전체 운영 V4 대시보드/모든 페이지 접근성은 미검증이다. viewport override는 복원했다. 스크린샷은 대화 도구 관측이며 별도 PNG 파일을 산출했다고 주장하지 않는다.

## 독립 최종 검토

| 영역 | task | 최종 판정 |
|---|---|---|
| 목적/권한 | res04_goal | PASS; 공식 schema blocker 해소, scoped 완료 |
| 코드 | res04_code | PASS; 오류 종류 보존·동일snapshot·helpers |
| 보안 | res04_security | PASS; Unicode500 수정·권한 유지 |
| 맥락 | res04_context | PASS; 실제 trade_count 연결·전역전환 경계 |
| QA | res04_qa | PASS; 30회귀+8component, 브라우저는 parent 수행 |

## 보호·롤백·다음 단계

운영 DB/봉인 evidence/tmap WIP/dirty wt-dev는 수정·stage하지 않았다. 실제 Stage F/G0/G2/Holdout/자동채택/실주문/merge/push 없음. feature/UI 준비는 실행 권한이 아니다.
롤백은 신규 adapter·API 필드·UI 배선 및 해당 build artifact만 새 역변경 commit으로 되돌린다. 사용자 파일이나 과거 보고서를 재작성하지 않는다.
다음은 SQ01B: 기존 결과 분석 API/full_analysis의 소비자 전환. 그 뒤 SQ02 지표 정의·비유한 효과값, ANA05 정본 Bundle, ANA06~08 연구 연결, UX06 전페이지 수용이다.
