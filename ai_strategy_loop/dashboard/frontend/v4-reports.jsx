/* v4-reports.jsx — V4 "Reports" 탭: 리포트 HTML 안전 뷰어.
 *   보안(§10-5, UXR-P7): 백엔드 /reports/view 가 CSP default-src 'none' 로 스크립트를 차단하고,
 *   여기서 sandbox="" iframe(스크립트·동일출처·폼·팝업 전면 차단)로 이중 방어한다.
 *   → inline JS 를 포함한 리포트(alpha_lab reporting 산출물 등)도 실행되지 않는다.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_rp7, useEffect: useEffect_rp7, useRef: useRef_rp7 } = React;
// dual-safe ESM import (esbuild bundle path). KEEP each on ONE physical line.
import { ResearchWikiPanel } from "./research-wiki.jsx";

function _fmtReportBytes(n) {
  if (!Number.isFinite(n)) return "";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}
function isReport(row) {
  return Boolean(row && typeof row === "object" && typeof row.path === "string" && row.path &&
    typeof row.name === "string" && Number.isFinite(row.bytes));
}


function V4Reports({ baseUrl }) {
  const [list, setList] = useState_rp7(null); // null=loading, []=empty
  const [err, setErr] = useState_rp7("");
  const [sel, setSel] = useState_rp7("");
  const [listedBase, setListedBase] = useState_rp7("");
  const generationRef = useRef_rp7(0);
  const selectionRef = useRef_rp7("");
  const baseRef = useRef_rp7(baseUrl);
  baseRef.current = baseUrl;

  useEffect_rp7(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    const priorSelection = selectionRef.current;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    setList(baseUrl ? null : []);
    setListedBase("");
    setErr("");
    setSel("");
    selectionRef.current = "";

    if (!baseUrl) {
      clearTimeout(timeout);
      return () => controller.abort();
    }

    fetch(baseUrl + "/reports", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        const reports = Array.isArray(j && j.reports) ? j.reports.filter(isReport) : [];
        const retained = reports.some(rp => rp.path === priorSelection) ? priorSelection : "";
        const nextSelection = retained || (reports.length ? reports[0].path : "");
        setList(reports);
        setListedBase(baseUrl);
        setSel(nextSelection);
        selectionRef.current = nextSelection;
      })
      .catch(e => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        setList([]);
        setErr(String(e && e.message ? e.message : e));
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [baseUrl]);

  const selectReport = path => {
    setSel(path);
    selectionRef.current = path;
  };
  const ownsSelection = Boolean(baseUrl && listedBase === baseUrl && Array.isArray(list) && list.some(rp => rp.path === sel));
  const viewUrl = ownsSelection ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";

  return (
    <section className="v4-reports" aria-labelledby="v4-reports-heading">
      <h2 id="v4-reports-heading" className="panel-hd-title">Reports · 리포트 뷰어</h2>
      <p className="v4-reports-safe mono" role="note">
        읽기 전용 · 스크립트 차단(CSP default-src 'none' + sandbox iframe) · docs/ 하위 HTML 한정
      </p>
      <div className="v4-reports-body">
        <aside className="v4-reports-list" aria-label="리포트 목록">
          {list === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
          {list !== null && list.length === 0 && (
            <div className="v4-reports-empty mono">
              리포트 없음{err ? " · " + err : ""}
              <div className="v4-reports-hint">docs/ 하위 *.html 생성 시 자동 표시</div>
            </div>
          )}
          {list !== null && list.map(rp => (
            <button key={rp.path}
                    className={"v4-reports-item" + (sel === rp.path ? " active" : "")}
                    onClick={() => selectReport(rp.path)} title={rp.path}>
              <span className="v4-reports-name">{rp.name}</span>
              <span className="v4-reports-meta mono">{_fmtReportBytes(rp.bytes)}</span>
            </button>
          ))}
        </aside>
        <div className="v4-reports-view">
          {viewUrl ? (
            <iframe key={viewUrl} className="v4-reports-frame" src={viewUrl}
                    sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" />
          ) : (
            <div className="v4-reports-empty mono">리포트를 선택하세요</div>
          )}
        </div>
      </div>
      <section className="v4-reports-wiki v4-cjk-safe" aria-labelledby="v4-reports-wiki-heading">
        <h2 id="v4-reports-wiki-heading" className="panel-hd-title">Research Wiki · 읽기 전용 참고 문서</h2>
        <ResearchWikiPanel baseUrl={baseUrl} wsStatus="na" />
      </section>
    </section>
  );
}

Object.assign(window, { V4Reports });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Reports };
