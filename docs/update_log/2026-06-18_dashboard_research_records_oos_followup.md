# 2026-06-18 진화 대시보드 연구 기록 복구 및 OOS 후속 실행 보고

## 한 줄 요약

진화 대시보드에 과거 연구/백테스트 기록을 다시 볼 수 있는 패널과, 현재 선택한 generation의 백테스트 GUI parity 차트를 붙였다. 이어서 `exit2 balance`, `r2full MDD` 후보를 2022/2026 OOS로 검증했고, 기존 `r8_4`와의 조합 비교 JSON을 만들었다.

## 용어 정리

| 용어 | 뜻 | 이번 작업에서 한 일 |
|---|---|---|
| 연구 기록 | `.omo/evidence/tmap-walkforward`에 쌓인 후보 탐색, 로그, summary, pairs 파일 | 대시보드에서 캠페인별 후보와 산출물 상태를 볼 수 있게 했다. |
| GUI parity | STOM 백테스트 GUI 이미지에 있던 같은 형태의 분석 차트 | 진화 대시보드에서도 선택 generation의 시간별/요일별 손익 등 차트를 볼 수 있게 했다. |
| OOS | 학습/탐색에 쓰지 않은 기간으로 다시 돌리는 검증 | 2022 전체, 2026-01-01부터 2026-02-28까지 검증했다. |
| MDD | 최고점에서 최저점까지 가장 크게 빠진 비율 | 낮을수록 중간 손실 스트레스가 작다. |
| 연평균 수익률 | 테스트 기간 수익률을 1년 기준으로 환산한 값 | 2026은 59일뿐이라 연환산 숫자가 과장될 수 있다. |

## 기능 완료표

| 항목 | 상태 | 확인 위치 | 결과 |
|---|---|---|---|
| 연구 기록 API | 완료 | `GET /research_records`, `GET /research_records/detail` | 캠페인 14개와 후보/summary/pairs/log 상태를 반환한다. |
| 연구 기록 패널 | 완료 | Evolution 탭 main column | 최신 연구 캠페인, best 후보, top candidates, artifacts를 표로 표시한다. |
| 진화 generation GUI parity API | 완료 | `GET /evolution_gui_parity?run_id=<run>&gen_no=<n>` | 선택 generation의 `hourly`, `weekday` 등 GUI parity 구조를 반환한다. |
| 시간별/요일별 차트 | 완료 | Evolution 탭, 백테상세 아래 | 기존 `BtGuiParitySection`을 재사용해 백테스트 탭과 같은 차트를 표시한다. |
| 프론트엔드 번들 | 완료 | `ai_strategy_loop/dashboard/frontend/bundle/app.js` | `ResearchRecordsPanel`, `EvolutionGuiParityPanel` 포함. |
| OOS 실행 | 완료 | `loop_runs.db` | 신규 4개 run 모두 `complete`, gate 통과. |
| 포트폴리오 비교 | 완료 | `.omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-20260618.json` | `r8_4`, `exit2 balance`, `r2full MDD` 단독/조합 비교 산출. |

## OOS 결과

`총수익률`과 `연평균 수익률`은 DB의 `total_profit_pct` 기준이다. 2026 구간은 59일뿐이므로 연평균 수익률은 방향성 참고용이다.

| 후보 | 구간 | 수익금 | 총수익률 | MDD | 거래수 | 일평균 거래 | Gate | 연평균 수익률 |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `exit2 balance` | 2022 | 2,625,686 | 52.40% | 8.46% | 58 | 0.30 | 통과 | 52.40% |
| `exit2 balance` | 2026 | 41,002 | 0.82% | 18.45% | 10 | 0.30 | 통과 | 5.18% |
| `r2full MDD` | 2022 | 2,167,653 | 43.06% | 15.39% | 85 | 0.40 | 통과 | 43.06% |
| `r2full MDD` | 2026 | 288,526 | 5.75% | 14.39% | 10 | 0.30 | 통과 | 41.32% |

## 포트폴리오 비교

비교 기준은 전략 1개당 500만원 배정이다. 조합 수익률은 `조합 수익금 / (500만원 x 전략 수)`로 계산했다. 조합 MDD는 각 전략 CSV의 일별 손익을 합친 뒤 최고점 대비 최대 낙폭으로 계산했다.

| 조합 | 구간 | 수익금 | 조합 수익률 | 조합 MDD | 거래수 | 연평균 수익률 | 판단 |
|---|---:|---:|---:|---:|---:|---:|---|
| `r8_4` 단독 | 2022 | 2,201,399 | 44.03% | 11.46% | 75 | 44.03% | 기준선 |
| `r8_4 + exit2` | 2022 | 4,827,085 | 48.27% | 10.63% | 133 | 48.27% | 2022 기준 가장 균형 좋음 |
| `r8_4 + r2full` | 2022 | 4,369,052 | 43.69% | 14.69% | 160 | 43.69% | 거래수 증가, MDD 악화 |
| `r8_4 + exit2 + r2full` | 2022 | 6,994,738 | 46.63% | 12.58% | 218 | 46.63% | 수익 총액 최대, 위험도 중간 |
| `r8_4` 단독 | 2026 | 764,267 | 15.29% | 23.01% | 15 | 141.08% | 짧은 구간 수익은 좋지만 MDD 큼 |
| `r8_4 + exit2` | 2026 | 805,269 | 8.05% | 21.85% | 25 | 61.47% | exit2가 2026에는 보탬이 작음 |
| `r8_4 + r2full` | 2026 | 1,052,793 | 10.53% | 19.88% | 25 | 85.75% | 2026 기준 균형 우수 |
| `r8_4 + exit2 + r2full` | 2026 | 1,093,795 | 7.29% | 20.15% | 35 | 54.56% | 총수익금 최대, 자본 대비 효율은 낮음 |

## 해석

2022 전체 구간에서는 `exit2 balance`가 `r8_4`의 MDD를 낮추면서 수익률을 올렸다. 그래서 2022 기준 추천 조합은 `r8_4 + exit2`다.

2026 짧은 구간에서는 `exit2 balance`의 수익 기여가 거의 없고 MDD가 높다. `r2full MDD`는 수익과 MDD를 동시에 보완했으므로, 2026 기준으로는 `r8_4 + r2full`이 더 낫다.

3개 전체 조합은 수익금 총액은 가장 크지만, 전략 수가 늘어 자본도 같이 늘기 때문에 자본 대비 수익률은 2개 조합보다 낮아질 수 있다. 실전 후보로 바로 확정하기보다 2023-2025 train/OOS 연결 구간이나 월별 레짐 분해를 추가 확인하는 것이 안전하다.

## 산출물

| 파일 | 내용 |
|---|---|
| `ai_strategy_loop/dashboard/research_records.py` | 연구 기록 색인 로직 |
| `ai_strategy_loop/dashboard/evolution_gui_parity.py` | 진화 generation GUI parity payload |
| `ai_strategy_loop/dashboard/research_api.py` | 신규 API 라우트 |
| `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx` | 연구 기록 패널 |
| `ai_strategy_loop/dashboard/frontend/evolution-gui-parity-panel.jsx` | GUI parity 패널 |
| `ai_strategy_loop/dashboard/frontend/bundle/app.js` | 재빌드된 대시보드 번들 |
| `.omo/evidence/tmap-walkforward/pairs-ovn-exit2-balance-oos.json` | `exit2 balance` OOS 입력 |
| `.omo/evidence/tmap-walkforward/pairs-ovn-r2full-mdd-oos.json` | `r2full MDD` OOS 입력 |
| `.omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-20260618.json` | 포트폴리오 비교 결과 |

## 검증 명령

```powershell
pytest tests/unit/dashboard/test_research_records.py -q
pytest tests/unit/dashboard/test_evolution_gui_parity.py -q
pytest tests/unit/dashboard/test_research_records_frontend.py -q
pytest tests/unit/dashboard/test_no_duplicate_globals.py tests/unit/dashboard/test_no_missing_cross_module_imports.py -q
cd ai_strategy_loop/dashboard/webui-build
node build-app.mjs
python -m json.tool .omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-20260618.json
```

HTTP 수동 확인:

```powershell
python -m uvicorn ai_strategy_loop.dashboard.app:app --host 127.0.0.1 --port 8793
curl.exe -i http://127.0.0.1:8793/ui/
curl.exe -i http://127.0.0.1:8793/research_records
curl.exe -i "http://127.0.0.1:8793/evolution_gui_parity?run_id=&gen_no=-1"
```

실행 결과:

| 검증 | 결과 |
|---|---|
| 집중 대시보드/API/차트/정적 검사 | 89 passed |
| 백테스트 job 주변 검사 | 12 passed |
| 확장 대시보드 테스트 묶음 | 315 passed |
| `git diff --check` | 공백 오류 없음, LF/CRLF 경고만 있음 |
| 보호 경로 상태 점검 | 출력 없음 |
| 전체 `pytest tests/unit/ -q` | 3364 passed, 5 skipped, 7 failed |

전체 unit 실패 7개는 이번 변경 파일이 아니라 기존 `backtest/backtest.py`, `ui/ui_button_clicked_*`, `ui/ui_process_kill.py`, `cli/runner.py` 계약 검사에서 발생했다. 이번 작업 범위와 직접 겹치지 않으므로 잔여 위험으로 분리한다.

## 주의 및 다음 작업

| 항목 | 상태 | 이유 |
|---|---|---|
| 2026 연평균 수익률 | 주의 | 59일 구간을 1년으로 환산하므로 숫자가 커질 수 있다. |
| `exit2 balance` 2026 | 보류 | 수익 41,002원, MDD 18.45%라 단독 보완력이 약하다. |
| `r2full MDD` 2022 | 주의 | 수익은 좋지만 MDD 15.39%라 `r8_4 + r2full` 조합의 2022 MDD가 악화됐다. |
| 추천 후속 1 | 필요 | 월별/요일별 레짐에서 `exit2`와 `r2full`의 손실이 겹치는지 확인. |
| 추천 후속 2 | 필요 | 2023-2025 구간을 같은 방식으로 돌려 2022/2026 사이 단절 여부 확인. |
| 추천 후속 3 | 필요 | 2전략 조합을 우선 후보로 두고, 3전략 조합은 자본 대비 효율 재검토. |

## 2026-06-18 후속 결정 기록

사용자 확인 결과, 이번 연구 작업과 `backtest.py` 안정화 작업은 분리한다.

| 결정 | 상태 | 이유 |
|---|---|---|
| `backtest.py` 즉시 수정 | 보류 | 이번 요청은 대시보드 연구 기록 복구와 OOS 실험이며, `backtest.py` 수정 없이 완료됐다. |
| `backtest.py` 관련 대화 | 나중에 재개 | 전체 unit suite의 실패 7개는 기존 `backtest.py`/UI/runner 계약 불일치이므로 별도 안정화 과제로 다룬다. |
| 현재 우선순위 | 다음 실험 목적 설정 | 성과 판단에는 2023~2025 연결 구간과 손익 겹침 분석이 더 직접적으로 필요하다. |

`backtest.py`를 건드리는 목적은 수익 실험이 아니라 전체 테스트 green 복구와 백테스트 실행 계약 정리다. 공식 백테스트 엔진 영향 범위가 크므로 별도 계획 없이 수정하지 않는다.

## 다음 실험 목적

| 우선순위 | 실험 | 목적 | 성공 기준 | 보류/탈락 기준 |
|---:|---|---|---|---|
| 1 | 2023~2025 OOS 추가 | 2022와 2026 사이에서 성과가 끊기지 않는지 확인 | `r8_4 + exit2` 또는 `r8_4 + r2full`이 연속 양수, MDD 허용 범위 유지 | 중간 구간에서 손실 전환 또는 MDD 급증 |
| 2 | 월별 손익/MDD 분해 | 수익이 특정 달에만 몰리거나 특정 달 손실이 반복되는지 확인 | 월별 손익이 과도하게 한두 달에 집중되지 않음 | 수익 대부분이 소수 월에 몰리거나 특정 월 반복 손실 |
| 3 | 요일별/시간별 손익 겹침 분석 | `r8_4`, `exit2`, `r2full`이 같은 시간대에 같이 손실 나는지 확인 | 서로 손실 시간대가 덜 겹쳐 조합 분산 효과가 있음 | 같은 요일/시간대 손실이 겹쳐 조합 MDD가 커짐 |
| 4 | 2전략 조합 최종 후보 비교 | `r8_4 + exit2`와 `r8_4 + r2full` 중 운영 후보를 좁힘 | 2022/2023~2025/2026 전체에서 수익률 대비 MDD가 더 안정적인 조합 선정 | 구간마다 승자가 바뀌고 기준 미달 |
| 5 | 3전략 조합 재평가 | 총수익금은 크지만 자본 효율이 낮은지 최종 확인 | 2전략보다 MDD가 낮거나 수익률 개선이 명확 | 자본 대비 수익률이 2전략보다 낮고 MDD 개선도 없음 |
| 6 | `backtest.py` 계약 정비 계획 | 연구 실험과 별도로 전체 테스트 실패 7개 처리 | 변경 범위, 위험, 검증 명령을 별도 계획으로 확정 | 성과 실험 중 공식 엔진을 섞어서 수정해야 하는 상황 |

다음 실험의 핵심 목적은 “어떤 조건식이 최고였는가”가 아니라 “어떤 조합이 여러 기간에서 반복적으로 버티는가”를 확인하는 것이다. 따라서 단일 최고 수익보다 구간 연속성, MDD 안정성, 손실 시간대 비중을 우선 판단 기준으로 둔다.
