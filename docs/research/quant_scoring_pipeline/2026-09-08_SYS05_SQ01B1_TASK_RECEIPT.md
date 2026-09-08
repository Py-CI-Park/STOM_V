# SYS05 SQ01B1 일반 job 결과 분석 품질 적용 TASK_RECEIPT

2026-09-08. 부모 `1933e7fbd0898cff630ef7ae34a3c07073f362d5`.
branch `codex/process-research-sys-05-analysis-quality`. 이 문서를 포함하는 commit은 로컬 checkpoint이며 loop 병합/배포가 아니다.

## 완료 범위

**일반 backtest job의 `/bt/result?job_id=` 경로 완료. 전역 소비자 전환·SYS05 전체는 미완료.**

```text
job record + 기존 REPO_ROOT 경로 제한
  -> typed trade_count metadata
  -> SQ01 동일 CSV snapshot 품질
      ├─ 불량 / 실행 미완료 -> metrics=null / analysis=null
      └─ 정상 성공 -> prepared_trades -> 기존 full_analysis 순수 계산
  -> 기존 공유 ResultDetailBody / BtResultArea
      ├─ 미충족 -> 품질 설명만, 차트/자동 MC 없음
      └─ 정상 -> 품질 카드 + 기존 분석·차트 유지
```

`available`은 job 존재를 유지한다. 새 `analysis_ready`가 계산 가능 여부이며 `execution_status`와 `data_quality`는 별도 축이다. 응답에는 `analysis_contract=job_result_quality_v1`을 추가했다. CSV 없는 no_trades 실행도 CSV 품질이 정상이라고 꾸미지 않는다. 정상 헤더0행은 NO_TRADES로 따로 설명한다.

## 변경과 호환

- job_result_quality.py가 기대 거래 수를 typed parsing한다. 잘못된 문자열/bool/음수/소수/NaN/Inf를 기대값 없음으로 바꾸지 않는다.
- TradeCountExpectation을 기존 CSV 모델에 모아 contract API와 result API가 재사용한다. 이전 내부 CompletedMetricsPayload 이름은 alias로 유지한다.
- 기존 full_analysis에 keyword-only prepared_trades를 추가했다. `None`은 옛 loader, 빈 tuple은 준비된0건으로 구분한다. 제공된 경우 CSV를 재개방하지 않고 model_dump 사본을 기존 계산 함수에 공급한다. 계산식은 바꾸지 않았다.
- no_trades/오류/불량 job 응답은 과거 빈 지표 구조 대신 metrics/analysis=null이다. UI도 함께 변경해0 성과를 만들지 않는다.
- 공유 ResultDetailBody는 차단 결과에서 차트·피처 패널을 생성하지 않는다. BtResultArea의 자동/수동 MC 시작 경로도 analysis_ready=false를 확인한다.
- 데모, WFO/sweep, run/gen 결과, report, compare, overlay, portfolio, 개별 analysis/MC endpoint는 이번 원자 밖이다. 직접 호출의 전역 품질 차단 완료로 확대하지 않는다.

## 실패 재현·회귀

| 검사 | 결과 |
|---|---|
| 신규 route red | 6 failed, exit1; 불량 입력에도 full_analysis 호출, legacy loader 사용 |
| 첫 호환 회귀 | 182 passed / 2 failed; 기존 축약 fixture와 잘못된 count 발견 |
| 공식 fixture 교정 후 | 184 passed in29.50s, exit0 |
| 최종 SQ01+SQ01B1 결합 회귀 | **217 passed in31.21s, exit0** |
| 독립 기존7파일 검증 | 184 passed in33.05s, exit0 |
| 독립 경계3개 | 3 passed in7.30s, exit0 |
| 공유 UI red | 품질 영역 부재 assertion 실패, exit1 |
| 공유 UI green | 4/4, errors=[], 추가 fetch 요청0, exit0 |
| npm run build | exit0; JSX142/graph595 및 실제 번들/6HTML 재생성 |
| 신규 helper/공통 count 모델 타입 검사 | 0 errors / 0 warnings |
| 신규 helper/model/시험 선택 lint | PASS |

최종 pytest: tests/unit/dashboard의 test_result_quality_gate, test_backtest_ws_job, test_backtest_evo_portfolio, test_backtest_result_identity, test_backtest_analysis, test_backtest_phase4, test_backtest_phase5, test_trade_csv_quality, test_trade_quality_api, test_trade_quality_review_regressions, test_qsp7_data_contract — 11파일, `-q -p no:cacheprovider`.
로그: `C:/Users/parkc/STOM_Verification/v1.5_20260907/sys05-sq01b1-*.log`.
217은 SQ01 검사도 포함한다. 113/184/217을 합산해 고유 시험 수로 보고하지 않는다.

테스트 보정: 임시CSV를 기존 REPO_ROOT 제한 안으로 주입했다. ws_job의 sample3행은 공식 헤더로 확장하고 원래 손익/ranged1행 assertions는 유지했다. relative-path 시험은 실제12행에 대해 이전 seed60을12로 바로잡고 result/report 모두12행 assertions를 유지했다. 기존 orderflow fixture·generation/portfolio 시나리오는 불필요하게 수정하지 않았다.

검증된 빈 tuple과 준비 자료 없음의 차이, 정상 원본1행의 빈 조회 구간(분석0/원본VALID1), 잘못된 기대 count는 영구 회귀에 추가했다. 빈 범위의 지표 정의 보강은 SQ02다.

## 실제 인하우스 브라우저

`tests/manual/sq01_browser_fixture.py`의 `/result-view?job=...`는 실제 BtResultArea와 실제 get_result를 GET으로 호출한다. job manager·CSV만 합성이고, 메인 운영 app/DB/연구 POST route는 없다.

| 입력 | 관측 |
|---|---|
| partial | 원본2/정상1/거부1 품질 설명; 성과·차트 navigation0 |
| empty | 정상 무거래/0행; '거래 표본이 없는 결과' 및 계산 생략 설명 |
| failed + 정상CSV | 품질 정상·실행 실패·분석 보류 동시 표시 |
| missing | count —·파일 없음·차트 없음 |
| normal | modern54/1행 준비 충족, 기존 결과 요약과 차트 navigation 유지 |

양성 화면 최초 시도에서 fixture가 기존 stom-ui 포맷 모듈을 누락해 fmtMoney/_btAxisTicks 오류가 발생했다. 운영 V4와 같은 모듈→bundle→DOMContentLoaded 순서로 fixture를 교정한 뒤 정상 화면을 확인했다. 운영 코드의 오류로 오인하지 않는다. 정상 fixture의 leaf_matrix/feature_map은 이번 QA 서버에서 제공하지 않아404이며 이 두 기능 완료를 주장하지 않는다. 정상 MC는 실행하지 않는 stub이며, 차단 결과에서 해당 요청이 없다는 점을 확인했다. 검증 탭/서버/임시 CSV는 종료·정리했다.

## 독립 최종 검토

| 영역 | task | 판정 |
|---|---|---|
| 목적 | res04_goal | PASS: 일반 job 경로에 한정 |
| 코드 | res04_code | PASS: 검증 배열·입력 불변·우회 분기 유지 |
| 보안 | res04_security | PASS:12합성 검사·경로 제한·invalid metadata 차단 |
| 맥락 | res04_context | PASS: no-trades 계약 변화·fixture 목적 보존 |
| QA | res04_qa | PASS:184+3 및 공유 JSX4; 브라우저 parent 수행 |

기존 거대 legacy 모듈에는 좁은 seam/분기만 추가했다. 전체 타입 부채·모듈 구조 이관을 완료한 것이 아니다. F02 기존 타입 오류10개 및 SQ01 private normalizer 경고는 별도 부채로 유지한다.

## 전체 계획·보호·롤백

SYS05 작업 묶음을 SQ00/SQ01/B1/B2/B3/B4/B5/SQ02로 명시했다. 현재3/8 완료는 같은 단위의 개수 비율이며 전체 노력/기능완성률이 아니다. 다음 B2는 진화 세대 결과이며 gate 탈락과 backtest 실행 실패를 기존 truth owner로 구분해야 한다.

운영 DB, 봉인 evidence, tmap WIP, dirty wt-dev 수정 없음. StageF/G0/G2/Holdout/자동채택/실주문/merge/push 없음. rollback은 이 job 결과 분기·prepared keyword·UI 배선 및 대응 번들만 새 역변경 commit으로 되돌리며 원본 결과는 재작성하지 않는다.
