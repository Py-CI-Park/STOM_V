/* QSP7 Korean guidance dictionary (P5): every machine reason maps to what the user should do. */
const _TP_REASON_KO = {
  // 데이터·잡 입력
  backtest_job_not_found: "선택한 공식 job 을 찾을 수 없습니다. 목록을 새로고침하고 다시 선택하세요.",
  backtest_result_not_ready: "완료(success)된 백테스트만 분석할 수 있습니다. 실패·진행 중 job 은 입력이 아닙니다.",
  backtest_result_csv_missing: "결과 CSV 파일이 없습니다. backtest/csv 경로와 job 기록을 확인하세요.",
  trade_csv_columns_missing: "CSV 에 필수 열(종목명·매수/매도시간·수익금)이 없습니다. 공식 결과 파일인지 확인하세요.",
  trade_csv_empty: "CSV 에 거래가 없습니다. 기간·전략을 확인해 다시 실행하세요.",
  invalid_forced_liquidation_time: "전체청산 시각이 HHMMSS 형식이 아닙니다. 예: 152800.",
  actual_exit_after_forced_liquidation: "입력한 전체청산보다 늦은 실제 매도가 있습니다. 경계를 실제 공식 값으로 맞추세요.",
  // 시세·종목 결합
  market_path_missing: "이 날짜의 시세 데이터가 없습니다. 일별 DB(stock_*_YYYYMMDD.db) 또는 통합 DB 의 해당 날짜를 확인하세요.",
  market_path_row_cap: "시세 행이 상한을 넘어 일부만 사용했습니다. 결과 해석 시 partial 표시를 확인하세요.",
  symbol_not_found: "종목명을 코드로 변환하지 못했습니다. code_info.db 등록 여부를 확인하세요.",
  ambiguous_symbol: "같은 종목명이 여러 코드에 연결돼 있어 제외했습니다. 코드 직접 표기 CSV 를 사용하세요.",
  invalid_trade_timestamp: "매수/매도시간 형식이 잘못됐습니다(12자리 분봉·14자리 틱).",
  split_entry_without_event_ledger: "분할매수 거래는 체결 원장이 없어 가상 재생 대상에서 제외됩니다.",
  // 분석 상태
  analysis_not_found: "분석 기록이 없습니다. 경로 분석을 먼저 시작하세요.",
  analysis_not_ready: "분석이 아직 완료되지 않았습니다. 완료 후 다시 시도하세요.",
  analysis_cancelled: "분석이 취소되었습니다. 다시 시작할 수 있습니다.",
  trade_not_found: "해당 거래를 찾을 수 없습니다. 요약에서 거래를 다시 선택하세요.",
  counterfactual_not_run: "가상 매도를 아직 실행하지 않았습니다.",
  counterfactual_ineligible: "이 거래는 가상 재생 자격이 없습니다(분할매수 또는 경로 없음).",
  // 매도식 재생
  sell_code_missing: "이 job 에 저장된 원본 매도식이 없습니다. 전략 코드가 함께 저장된 job 을 선택하세요.",
  insufficient_history: "창 계산에 필요한 과거 데이터가 부족해 일부 시점을 평가하지 않았습니다(0 대체 안 함).",
  // 게이트·레인
  unknown_lane: "레인은 tick 또는 min 만 가능합니다.",
  cohort_too_small: "표본이 부족해 통계를 만들지 않았습니다(그룹당 최소 30건). 기간을 늘리거나 다른 cohort 를 선택하세요.",
  incompatible_official_pair: "두 job 의 매수식·기간·timeframe·분류 방식이 달라 비교할 수 없습니다.",
  official_result_missing: "공식 결과 파일이 없어 pair 비교를 할 수 없습니다.",
  design_pair_unavailable: "설계 pair 를 만들 수 없습니다 — 두 설계 job 을 확인하세요.",
  oos_pair_unavailable: "OOS pair 를 만들 수 없습니다 — 두 OOS job 을 확인하세요.",
  period_metadata_missing: "job 기간 정보가 없어 겹침을 판정할 수 없습니다.",
  design_oos_period_overlap: "설계와 OOS 기간이 겹칩니다 — 비중첩 기간으로 다시 실행하세요.",
  design_not_improved: "설계 구간에서 개선되지 않았습니다 — 채택 불가가 정상입니다.",
  oos_not_improved: "OOS 구간에서 개선되지 않았습니다 — 채택 불가가 정상입니다.",
};

function _tpKo(reason) {
  if (!reason) return "";
  const text = String(reason);
  return _TP_REASON_KO[text] || _TP_REASON_KO[text.split(":")[0]] || text;
}

/* 단계 위저드(P5): 각 화면에서 "다음으로 가는 조건"을 말해준다. */
const _TP_NEXT_KO = {
  data: "다음 → 매수 해부: CSV 지문·전체청산 경계·비용이 모두 설명 가능해야 합니다. 경계가 legacy 추론이면 신규 공식 job 을 고려하세요.",
  entry: "다음 → 경로 분석 시작: 사후정보 없는 유효 변수를 확인했으면 상단의 [경로 분석 시작]을 누르세요.",
  summary: "다음 → 거래 경로: 연구할 매도사유 cohort 를 정하고 대표 거래를 클릭하세요.",
  path: "다음 → 매도식 추적: 회복·검열이 설명되면 원본 매도식의 최초 발동을 검증하세요.",
  "sell-trace": "다음 → 가상 매도: 재생 시각이 공식과 일치(또는 차이가 설명)되면 대체 가설을 비교하세요.",
  counterfactual: "다음 → 회복 판별: 가상 delta 는 자문입니다. 판별 변수로 가설 근거를 보강하세요.",
  insight: "다음 → 조건식 후보: FDR 통과 변수를 근거로 후보를 생성하세요. 통과 0개면 그것도 결과입니다.",
  proposals: "다음 → 후보 실행: 서로 다른 family 후보를 고르세요. 숫자만 다른 복제는 하나로 칩니다.",
  console: "다음 → 공식 pair: 설계 실행이 success 가 되면 기준선과 비교하세요.",
  official: "다음 → OOS 채택: 비용 후 손익·MDD·거래수가 함께 확인되면 OOS 로 넘어가세요.",
  oos: "다음 → 캘리브레이션·History: 설계·OOS 둘 다 개선 + 사람 승인 전에는 채택하지 않습니다.",
  calibration: "다음 → History: 오차 기록이 쌓일수록 가상 delta 의 신뢰 범위가 정확해집니다.",
  ledger: "원장은 항상 열람 가능합니다. 실패·0건 기록도 보존됩니다.",
};

function _tpNextHint(view) { return _TP_NEXT_KO[view] || ""; }

Object.assign(window, { _tpKo, _tpNextHint });
export { _tpKo, _tpNextHint, _TP_REASON_KO };
