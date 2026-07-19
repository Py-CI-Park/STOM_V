/* v4-audit.jsx — V4 "Audit" 탭: append-only 결정 감사(VerdictPanel) + compact 안전 strip.
 *   안전/감사 정보는 quiet-by-default(작은 strip). VerdictPanel 은 /decisions·/freeze_verdict
 *   등을 자체 fetch 하는 self-contained 원장이다. app.jsx:529-551 인라인 안전 타일을 복제.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { VerdictPanel } from "./dashboard-pages.jsx";

const { useEffect: useEffect_va, useState: useState_va } = React;

// 연구 전용 경계 — 실거래/주문/브로커 없음(app.jsx 안전 타일과 동일 문구).
const V4_SAFETY_TILES = [
  ["실거래/주문 기능 없음", "No Live Order"],
  ["브로커 로그인 없음", "No Broker Login"],
  ["계좌/자산 연동 없음", "No Account Trading"],
  ["연구 전용", "Research Only"],
  ["Human Approval Gate", "승인 후 Export"],
  ["Append-Only Audit", "불변 감사 로그"],
];

function auditDecisionMatches(decision, query, verdict) {
  const selectedVerdict = String(verdict || "all").toLocaleLowerCase();
  const decisionVerdict = String(decision.verdict || "").toLocaleLowerCase();
  if (selectedVerdict !== "all" && decisionVerdict !== selectedVerdict) return false;
  const needle = String(query || "").trim().toLocaleLowerCase();
  if (!needle) return true;
  const candidate = decision.candidate || {};
  return [
    decision.ts,
    decision.verdict,
    decision.note,
    decision.status,
    decision.provenance,
    decision.blocker,
    candidate.buy_name,
    candidate.sell_name,
    candidate.run_id,
    candidate.gen_no,
    candidate.status,
    candidate.source,
    candidate.blocker,
  ].some(value => String(value ?? "").toLocaleLowerCase().includes(needle));
}

function AuditDecisionTrace({ baseUrl }) {
  const [decisions, setDecisions] = useState_va([]);
  const [loading, setLoading] = useState_va(true);
  const [error, setError] = useState_va("");
  const [query, setQuery] = useState_va("");
  const [verdict, setVerdict] = useState_va("all");

  useEffect_va(() => {
    const base = String(baseUrl || "").replace(/\/+$/, "");
    setLoading(true);
    setError("");
    fetch(base + "/decisions", { signal: AbortSignal.timeout(8000) })
      .then(response => response.ok
        ? response.json()
        : Promise.reject(new Error("HTTP " + response.status)))
      .then(payload => setDecisions(Array.isArray(payload?.decisions) ? payload.decisions : []))
      .catch(reason => setError(String(reason)))
      .finally(() => setLoading(false));
  }, [baseUrl]);

  const visible = decisions.filter(decision => auditDecisionMatches(decision, query, verdict));

  return (
    <section className="panel v4-audit-trace" aria-labelledby="v4-audit-trace-title">
      <div className="panel-hd">
        <h2 id="v4-audit-trace-title" className="panel-hd-title">결정 추적</h2>
        <span className="mono">append-only · {decisions.length} records</span>
      </div>
      <div className="panel-bd">
        <fieldset className="v4-audit-filters">
          <legend>결정 기록 필터</legend>
          <label>
            추적 검색
            <input value={query} onChange={event => setQuery(event.target.value)}
                   placeholder="run, generation, 전략, 근거" />
          </label>
          <label>
            결정 상태
            <select value={verdict} onChange={event => setVerdict(event.target.value)}>
              <option value="all">전체</option>
              <option value="promote">promote</option>
              <option value="complement">complement</option>
              <option value="hold">hold</option>
              <option value="reject">reject</option>
            </select>
          </label>
        </fieldset>

        {loading ? <p role="status">감사 기록을 불러오는 중입니다.</p> : null}
        {error ? <p role="alert">감사 기록 로드 실패: {error}</p> : null}
        {!loading && !error && decisions.length === 0
          ? <p role="status">아직 append-only 결정 기록이 없습니다.</p> : null}
        {!loading && !error && decisions.length > 0 && visible.length === 0
          ? <p role="status">현재 필터와 일치하는 결정 기록이 없습니다.</p> : null}
        {!loading && !error && visible.length > 0 ? (
          <div data-region="scroll" tabIndex="0" aria-label="필터된 결정 추적 표">
            <table className="mono">
              <caption>필터 결과 {visible.length}건. 행을 펼치면 provenance, status, blocker를 확인할 수 있습니다.</caption>
              <thead><tr>
                <th scope="col">시각</th><th scope="col">결정</th><th scope="col">대상</th><th scope="col">추적 근거</th>
              </tr></thead>
              <tbody>{visible.slice().reverse().map((decision, index) => {
                const candidate = decision.candidate || {};
                const provenance = decision.provenance || candidate.source || "서버 미제공";
                const status = decision.status || candidate.status || "서버 미제공";
                const blocker = decision.blocker || candidate.blocker || "기록 없음";
                return (
                  <tr key={`${decision.ts || "unknown"}-${index}`}>
                    <td>{decision.ts ? new Date(decision.ts * 1000).toLocaleString("ko-KR") : "시각 미제공"}</td>
                    <td>{decision.verdict || "결정 미제공"}</td>
                    <td>{candidate.buy_name || candidate.sell_name || "대상 미제공"}</td>
                    <td><details><summary>decision trace</summary>
                      <dl>
                        <dt>provenance</dt><dd>{provenance}</dd>
                        <dt>status</dt><dd>{status}</dd>
                        <dt>blocker</dt><dd>{blocker}</dd>
                        <dt>evidence</dt><dd>{decision.note || "근거 메모 없음"}</dd>
                      </dl>
                    </details></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function V4Audit({ baseUrl, onNavigate }) {
  return (
    <div className="v4-audit">
      <section className="v4-safety-strip" data-safety-boundary="v4-research-only">
        {V4_SAFETY_TILES.map(([title, detail]) => (
          <div key={title} className="v4-safety-tile">
            <b>{title}</b>
            <span className="mono">{detail}</span>
          </div>
        ))}
      </section>
      <AuditDecisionTrace baseUrl={baseUrl} />
      <VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />
    </div>
  );
}

Object.assign(window, { V4Audit, AuditDecisionTrace });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Audit, AuditDecisionTrace };
