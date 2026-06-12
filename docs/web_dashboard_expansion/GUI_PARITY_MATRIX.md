# GUI 백테스트 ↔ 웹 워크벤치 기능 패리티 매트릭스

> 2026-06-12 · Phase 4 트랙 B(백테스트 탭 재설계) 산출물.
> 목적: GUI(`ui/ui_backtest_engine.py` · `ui/ui_activated_back.py` · `ui/set_dialog_back.py`)의
> 백테스트/최적화 분석 기능을 전수 나열하고 웹 대시보드 현황과 대조해, 향후 패리티 작업의 SSOT 로 삼는다.
>
> 범위: GUI '백테엔진' 다이얼로그(Alt+B 계열)와 '백테 스케쥴러/최적화' 다이얼로그 기능.
> 웹 대응은 `ai_strategy_loop/dashboard/backtest_api.py`(`/bt/*`) + `frontend/backtest.jsx` 기준.

## 범례

- ✅ 구현됨 — 웹에서 동등 기능 제공
- 🟡 부분 — 일부만/우회 제공
- ⛔ 미구현 — 웹 미제공(향후 단계)

## 1. 백테스트 실행 (단일)

| GUI 기능 | GUI 위치 | 웹 대응 | 상태 |
|----------|----------|---------|------|
| 매수/매도 조건식 선택 | `be_comboBox`(전략 셀렉터) | `/bt/strategies` + 실행 바 셀렉터 | ✅ |
| 백테 기간(시작/종료일자) | `be_dateEdit_01/02` | `/bt/run` start/end + 실행 바 입력 | ✅ |
| 시작/종료 시간 | `be_lineEdit_01/02` | (CLI 기본값 사용) | 🟡 |
| 타임프레임(틱/분봉) | `주식타임프레임` dict_set | `/bt/run` timeframe + 토글 | ✅ |
| 엔진 수(멀티) | `be_lineEdit_04` | `/bt/run` engines + 입력 | ✅ |
| 분류 방법(종목코드별/일자별/한종목) | `be_comboBox_01` divid_mode | `/bt/run` divid_mode·one_code | ✅ |
| 평균선 리스트(avg_list) | `be_lineEdit_03` | (CLI 기본값) | 🟡 |
| 백테 중지 | `backtest_process_kill` | `/bt/job/cancel` + 중지 버튼 | ✅ |
| 진행률 표시 | `ss_progressBar_01` | 활성 잡 카드 progress + WS 라이브 | ✅ |
| 결과 CSV/메트릭 | 결과 테이블 | `/bt/result` + 메트릭 카드 | ✅ |

## 2. 조건식/수식 관리

| GUI 기능 | 웹 대응 | 상태 |
|----------|---------|------|
| 매수/매도 조건식 목록 | `/bt/strategies?kind=buy\|sell` | ✅ |
| 조건식 코드 편집 | 듀얼 에디터(매수+매도 동시) | ✅ |
| 조건식 문법 검증(`back_code_test3`) | `/bt/strategy/validate`(compile) | ✅ |
| 조건식 저장/덮어쓰기/다른이름 | `/bt/strategy`(INSERT OR REPLACE) | ✅ |
| 조건식 삭제 | `/bt/strategy/delete`(confirm) | ✅ |
| 수식(formula) 관리(`formula_code_test`) | `/bt/strategies?kind=formula` + CRUD | 🟡 (편집 UI 는 buy/sell 중심) |
| 사용 변수 가시화 | 변수 키워드 칩(`/bt/extract_vars` SSOT 대조) | ✅ (웹 신규 — GUI 에 없던 가치) |

## 3. 결과 분석/시각화

| GUI 기능 | 웹 대응 | 상태 |
|----------|---------|------|
| 요약 메트릭(승률·손익·MDD·PF 등) | `/bt/analysis/summary` + 카드 | ✅ |
| 누적수익곡선 | `/bt/analysis/equity` + SVG 차트 | ✅ |
| 손익 분포 히스토그램 | `/bt/analysis/distribution` | ✅ |
| 요일×시간 히트맵 | `/bt/analysis/heatmap` | ✅ |
| 언더워터(MDD) 곡선 | `/bt/analysis/underwater` | ✅ |
| MAE/MFE 산점도 | `/bt/analysis/mae_mfe` | ✅ (웹 신규) |
| 청산사유 분해 | `/bt/analysis/exit_reasons` | ✅ (웹 신규) |
| 몬테카를로 분포 | `/bt/analysis/montecarlo` | ✅ (웹 신규) |
| 오더플로우 비교 | `/bt/analysis/orderflow` | ✅ (웹 신규) |
| 자급자족 HTML 리포트 | `/bt/report` | ✅ (웹 신규) |
| 구간 브러시 분석 | t_start/t_end 재계산 | ✅ (웹 신규) |
| 전체화면 분석 모드(롤링·월별 캘린더) | 트랙 D(`backtest-charts.jsx`) | ✅ (웹 신규, 별도 트랙) |

## 4. 결과 체계 관리

| 기능 | 웹 대응 | 상태 |
|------|---------|------|
| 잡 이력 영속(서버 재시작 후 조회) | `state/webbt_jobs/*.json` | ✅ |
| 태그/메모/즐겨찾기 | `/bt/job/meta` + 결과 라이브러리 | ✅ (웹 신규) |
| 이력 검색/태그 필터/즐겨찾기 정렬 | 결과 라이브러리 UI | ✅ (웹 신규) |
| A/B 잡 비교 | `/bt/compare` | ✅ (웹 신규) |
| 다중 잡 오버레이(수익곡선 겹쳐보기) | `/bt/overlay?job_ids=`(2~4) + 정규화 토글·범례 | ✅ (웹 신규) |
| 포트폴리오 결합 분석 | `/bt/portfolio` | ✅ (웹 신규) |
| 데모 예시 기본 표시 | `/bt/result?demo=1`('예시 데이터' 배지) | ✅ (웹 신규) |

## 5. 최적화/파라미터 탐색 (GUI '백테 스케쥴러' 다이얼로그)

| GUI 기능 | GUI 근거 | 웹 대응 | 상태 |
|----------|----------|---------|------|
| 파라미터 최적화(Grid/Random) | `최적화횟수` · `opti_standard` | `/bt/run` mode=optimize → `stom_backtest optimize` 래핑 | ✅ (1차) |
| 최적화 목표 지표 | `최적화기준` | `opt_objective`(기본 tpi) | ✅ |
| 최적화 방법 선택 | — | `opt_method`(grid/random) | ✅ |
| 파라미터 탐색공간 정의 | GUI 범위 입력 | `param_space` JSON 경로(allowlist) | 🟡 (JSON 경로 입력; GUI 처럼 인라인 범위 편집 UI 미제공) |
| 전진분석(WFO) | `전진분석` · `train/valid/test_period` | `/bt/run` mode=wfo → `stom_backtest wfo` 래핑(train/test 윈도우·선택 param_space) + 라운드별 결과표 | ✅ (2차) |
| 파라미터 스윕/날짜 롤링 | `일괄변경` · 스케쥴 | `/bt/run` mode=sweep(param/rolling) → `stom_backtest sweep` 래핑 + 조합/윈도우별 결과표 | ✅ (2차) |
| 백파인더(자동 조건 탐색) | discovery 계열 | `stom_backtest discovery *`(CLI 존재) | ⛔ (다음 단계) |
| 스케쥴러(예약 실행/일괄 큐) | `스케쥴 저장/로딩` | 잡 큐(FIFO, 동시 1) 존재하나 예약/배치 UI 미제공 | 🟡 |
| 완료 후 컴퓨터 종료 | `완료 후 컴퓨터 종료` 체크 | 미제공(웹 부적합) | ⛔ (의도적 제외) |

## 6. 다음 단계 우선순위 (패리티 보강)

> 2026-06-12 Phase5 트랙 B(백테탭 강화 2차)에서 WFO·스윕 잡 래핑 + 다중 잡 오버레이를 구현했다.
> 아래는 잔여 우선순위(재정렬).

1. **백파인더 진입점** — `discovery auto/analyze/generate` 를 잡 타입 확장으로 노출.
2. **param_space 인라인 편집기** — JSON 경로 대신 웹에서 탐색공간(optimize/wfo)·스윕 조합(sweep)을 폼으로 정의 → state/ 하위에 직렬화 후 실행(현재는 allowlist JSON 경로 입력).
3. **수식(formula) 전용 에디터** — 듀얼 에디터에 formula 탭 추가(차트표시/색상 등 메타 포함).
4. **WFO/스윕 결과 시각화 강화** — 현재 라운드/조합별 정렬 표 제공. 윈도우별 OOS 곡선·조합 히트맵 등 차트 추가 여지.

## 부록 — CLI 서브커맨드 계약(웹 래핑 근거)

`stom_backtest.py` 인식 서브커맨드(`cli/subcommands.py`): `optimize`, `sweep`, `wfo`, `tune`, `db`,
`formula`, `strategy`, `discovery`, `setting`, `report`, `ai-controller` 등.
optimize 인자: `--buy --sell --start --end --param-space(JSON) --method[grid|random] --objective
--engines --timeframe --timeout --format json`. (단일 백테는 서브커맨드 없이 `--buy/--sell` 직접.)
