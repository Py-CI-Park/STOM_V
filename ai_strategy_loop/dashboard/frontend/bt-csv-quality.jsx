/* Production CSV quality: evidence availability is not execution authority. */
const CSV_QUALITY_LABELS = {
  VALID: ["정상", "CSV 행 검사를 통과했습니다. 연구·수익성 승인을 뜻하지 않습니다."],
  NO_TRADES: ["정상 무거래", "유효한 헤더가 있지만 거래 행이 없습니다. 오류나 수익 0과 구분합니다."],
  MISSING_ARTIFACT: ["파일 없음", "결과 CSV 위치와 파일 존재 여부를 확인하세요."],
  INVALID_SCHEMA: ["CSV 구조 오류", "필수 컬럼·중복 헤더·CSV 구분 형식을 확인하세요."],
  ROW_PARSE_PARTIAL: ["일부 행 오류", "거부된 행을 확인하세요. 남은 행만으로 전체 성과를 판단하지 마세요."],
  ROW_COUNT_MISMATCH: ["거래 수 불일치", "예상 거래 수와 원본 행 수를 먼저 대조하세요."],
  NONFINITE_VALUE: ["잘못된 수치", "NaN·무한대가 포함된 행을 확인하세요. 0으로 대체하지 않습니다."],
  IDENTITY_MISMATCH: ["원본 식별 불일치", "예상 해시와 실제 CSV 해시가 다릅니다. 원본을 확인하세요."],
  IO_ERROR: ["파일 읽기 오류", "파일 형식·접근 권한을 확인하세요."],
  ENCODING_ERROR: ["문자 인코딩 오류", "UTF-8 CSV인지 확인하세요. 원본을 덮어쓰지 마세요."],
  RESOURCE_LIMIT: ["검사 한도 초과", "자료 크기·행 수 한도를 초과했습니다. 부분 성공으로 처리하지 않습니다."],
};
const CSV_EXECUTION_LABELS = {
  success: "실행 완료", error: "실행 실패", cancelled: "실행 취소",
  no_trades: "무거래 종료", timeout: "실행 시간 초과",
};
const csvCount = value => value == null ? "—" : Number(value).toLocaleString();
const CSV_DETAIL_LABELS = {
  "Column count differs from header": "헤더와 데이터의 컬럼 수가 다릅니다.",
  "Rejected rows are diagnostic only": "거부 행이 있어 전체 결과의 분석 준비를 충족하지 못했습니다.",
  "Numeric value must be finite": "NaN 또는 무한대 값은 사용할 수 없습니다.",
  "Numeric value cannot be parsed": "숫자로 읽을 수 없는 값입니다.",
  "Required value is empty": "필수 값이 비어 있습니다.",
  "Holding duration is negative": "보유시간이 음수입니다.",
  "Invalid or reversed trade timestamps": "거래 시각이 잘못되었거나 매도가 매수보다 빠릅니다.",
  "Expected raw row count differs": "실행 기록의 거래 수와 CSV 원본 행 수가 다릅니다.",
  "Expected source hash differs": "예상한 원본과 실제 파일의 해시가 다릅니다.",
  "Not a supported official 54/37-column schema": "지원하는 공식 54/37열 스키마가 아닙니다.",
  "Duplicate/empty/missing required header": "헤더가 중복되거나 필수 컬럼이 없습니다.",
  "CSV file is missing": "지정된 CSV 파일이 없습니다.",
  "Job has no CSV artifact path": "실행 기록에 CSV 경로가 없습니다.",
  "Job has no readable CSV artifact": "실행 기록에서 읽을 수 있는 CSV를 찾지 못했습니다.",
  "Invalid job trade_count metadata": "실행 기록의 예상 거래 수가 올바른 정수가 아닙니다.",
  "CSV cannot be read": "CSV 파일에 접근할 수 없습니다.",
  "CSV must be UTF-8": "UTF-8로 인코딩된 CSV가 필요합니다.",
  "Malformed CSV record": "CSV 따옴표나 레코드 형식이 잘못되었습니다.",
};

function BtCsvQuality({ envelope, pending = false }) {
  if (pending) return <div className="tp-csv-quality" role="status">선택한 결과의 CSV 품질을 확인하고 있습니다…</div>;
  if (!envelope) return null;
  const q = envelope.data_quality;
  const [label, help] = CSV_QUALITY_LABELS[q?.status] || ["품질 미확인", "현재 결과의 품질 영수증을 확인할 수 없습니다. 사전 점검을 다시 실행하세요."];
  const ready = envelope.analysis_ready === true;
  return <section className={`tp-csv-quality ${ready ? "ready" : "blocked"}`} aria-label="CSV 품질 진단" aria-live="polite">
    <header><div><small>자료 품질 · 실행 상태 별도 판정</small><h3>{label}</h3></div>
      <span>{CSV_EXECUTION_LABELS[envelope.execution_status] || "실행 상태 미확인"}</span>
      <strong>{ready ? "CSV 분석 준비 충족" : "분석 준비 미충족"}</strong></header>
    <p>{help}</p>
    <p>공식 스키마: <code>{q?.official_schema || "미확인"}</code> · 컬럼 이름과 구성을 함께 검사합니다.</p>
    {q?.issue_codes?.length > 0 && <p>문제 유형: {q.issue_codes.map(code => CSV_QUALITY_LABELS[code]?.[0] || code).join(" · ")}</p>}
    <dl className="tp-csv-counts">
      <div><dt>원본 행</dt><dd>{csvCount(q?.raw_count)}</dd></div>
      <div><dt>정상 행</dt><dd>{csvCount(q?.accepted_count)}</dd></div>
      <div><dt>거부 행</dt><dd>{csvCount(q?.rejected_count)}</dd></div>
      <div><dt>예상 행</dt><dd>{csvCount(q?.expected_row_count)}</dd></div>
    </dl>
    <p className="tp-csv-hash"><small>검사한 CSV SHA256</small><code>{q?.source_sha256 || "미확인"}</code></p>
    {q?.issues?.length > 0 && <details><summary>문제 상세 {csvCount(q.issue_count)}건{q.issues_truncated ? " · 일부 표시" : ""}</summary>
      <ul>{q.issues.map((issue, index) => <li key={index}>
        <b>{CSV_QUALITY_LABELS[issue.code]?.[0] || "검사 오류"}</b>
        {issue.row != null && <span> · 레코드 {issue.row}</span>}
        {issue.column && <code> · {issue.column}</code>}
        <span> · {CSV_DETAIL_LABELS[issue.detail] || issue.detail}</span>
      </li>)}</ul>
    </details>}
  </section>;
}

Object.assign(window, { BtCsvQuality });
export { BtCsvQuality };
