/* Strategy code viewer modal: shows full buy/sell code per generation */
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { StrategyInspectorTabs } from "./strategy-inspector.jsx";
const { useState: useState_cv, useMemo: useMemo_cv, useEffect: useEffect_cv } = React;

// Lightweight Python-ish syntax highlighter
function highlightPython(code) {
  if (!code) return [];
  const lines = code.split("\n");
  const KEYWORDS = new Set([
    "def", "return", "if", "elif", "else", "and", "or", "not", "for", "while",
    "in", "is", "None", "True", "False", "import", "from", "as", "pass",
    "break", "continue", "lambda", "try", "except", "finally", "with", "yield",
    "max", "min", "abs", "len",
  ]);
  const out = [];
  for (let ln = 0; ln < lines.length; ln++) {
    const line = lines[ln];
    const parts = [];
    let i = 0;
    while (i < line.length) {
      const ch = line[i];
      // Comment
      if (ch === "#") {
        parts.push({ cls: "tok-com", t: line.slice(i) });
        break;
      }
      // String
      if (ch === '"' || ch === "'") {
        const q = ch;
        let j = i + 1;
        while (j < line.length && line[j] !== q) j++;
        parts.push({ cls: "tok-str", t: line.slice(i, j + 1) });
        i = j + 1;
        continue;
      }
      // Number
      if (/[0-9]/.test(ch) && (i === 0 || /[^a-zA-Z_]/.test(line[i - 1]))) {
        let j = i;
        while (j < line.length && /[0-9_.e+-]/.test(line[j])) j++;
        parts.push({ cls: "tok-num", t: line.slice(i, j) });
        i = j;
        continue;
      }
      // Identifier / keyword
      if (/[a-zA-Z_]/.test(ch)) {
        let j = i;
        while (j < line.length && /[a-zA-Z0-9_]/.test(line[j])) j++;
        const word = line.slice(i, j);
        // Function call: next non-space is "("
        let k = j;
        while (k < line.length && line[k] === " ") k++;
        if (KEYWORDS.has(word)) parts.push({ cls: "tok-kw", t: word });
        else if (line[k] === "(") parts.push({ cls: "tok-fn", t: word });
        else parts.push({ cls: "", t: word });
        i = j;
        continue;
      }
      // Whitespace / symbol
      parts.push({ cls: "", t: ch });
      i++;
    }
    out.push({ ln: ln + 1, parts });
  }
  return out;
}

// 검색 하이라이트는 줄 전체 좌표에서 계산한다. 토큰 단위로 찾으면 한글 식별자처럼
//   highlightPython 이 한 글자씩 쪼개는 토큰에서는 절대 매치되지 않는다(2026-07-26 실측).
function _cvMatchRanges(lineText, needle) {
  if (!needle) return [];
  const lower = lineText.toLowerCase();
  const target = needle.toLowerCase();
  const ranges = [];
  let from = lower.indexOf(target);
  while (from !== -1) {
    ranges.push([from, from + target.length]);
    from = lower.indexOf(target, from + target.length);
  }
  return ranges;
}

// 한 토큰(offset ~ offset+text.length)을 매치 구간과 교차시켜 <mark> 로 쪼갠다.
function _cvSplitToken(text, offset, ranges, keyPrefix) {
  if (ranges.length === 0) return text;
  const end = offset + text.length;
  const hits = ranges.filter(([s, e]) => s < end && e > offset);
  if (hits.length === 0) return text;
  const out = [];
  let cursor = offset;
  for (const [s, e] of hits) {
    const from = Math.max(s, offset);
    const to = Math.min(e, end);
    if (from > cursor) out.push(text.slice(cursor - offset, from - offset));
    out.push(<mark key={`${keyPrefix}-${from}`} className="cv-hit">{text.slice(from - offset, to - offset)}</mark>);
    cursor = to;
  }
  if (cursor < end) out.push(text.slice(cursor - offset));
  return out;
}

function CvCodeBlock({ code, query = "", emptyLabel }) {
  const highlighted = useMemo_cv(() => highlightPython(code), [code]);
  if (!code) return (
    <div className="code-block" style={{ color: "var(--ink-3)" }}>
      {emptyLabel || "unavailable: strategy code not found for this generation."}
    </div>
  );
  const needle = String(query || "").trim();
  return (
    <pre className="code-block">
      {highlighted.map((row, i) => {
        const lineText = row.parts.map(p => p.t).join("");
        const ranges = _cvMatchRanges(lineText, needle);
        let offset = 0;
        return (
          <div key={i} className={ranges.length ? "cv-hit-line" : undefined}>
            <span className="ln">{row.ln}</span>
            {row.parts.map((p, j) => {
              const at = offset;
              offset += p.t.length;
              return <span key={j} className={p.cls}>{_cvSplitToken(p.t, at, ranges, `${i}-${j}`)}</span>;
            })}
          </div>
        );
      })}
    </pre>
  );
}

const _CV_FONT_STEPS = [11, 12.5, 14, 16, 18];

function CodeViewer({ generation, onClose, runId, baseUrl }) {
  const [tab, setTab] = useState_cv("buy");
  const [copied, setCopied] = useState_cv(false);
  const [expandedCodeView, setExpandedCodeView] = useState_cv(false);
  // v5.11.2 — 조건식은 "읽고 비교하는" 대상이다. 한쪽씩만 크게 보는 것으로는 부족해서
  //   매수·매도 나란히 보기, 글자 크기, 검색 하이라이트, 전체화면을 팝업에 넣는다.
  const [splitView, setSplitView] = useState_cv(false);
  // v5.13.0 — 기본 글자 14px(한 단계 확대).
  const [fontIdx, setFontIdx] = useState_cv(2);
  const [query, setQuery] = useState_cv("");
  // v5.13.0 — 검색 디바운스(A3): 키 입력마다 전체 코드 재하이라이트하면 큰 조건식에서
  //   타이핑이 밀린다. 150ms 지연 후에만 하이라이트를 다시 계산한다.
  const [debouncedQuery, setDebouncedQuery] = useState_cv("");
  useEffect_cv(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 150);
    return () => clearTimeout(t);
  }, [query]);
  // P10 — 세대 행(GenView)에는 코드가 없다. 인라인 코드(데모 소스)가 없으면
  //   /strategy_code?run=&gen= 로 fetch 해 채운다. {buy_code, sell_code} 또는 null.
  const [fetched, setFetched] = useState_cv(null);
  const [loading, setLoading] = useState_cv(false);
  const [fetchErr, setFetchErr] = useState_cv(null);

  // 인라인 코드(데모/직접 주입)가 이미 있으면 fetch 하지 않는다(LIVE/DEMO 규약).
  const hasInline = Boolean(generation && (generation.buy_code || generation.sell_code));

  useEffect_cv(() => {
    // 모달이 닫혀 있거나(generation 없음) 인라인 코드가 있으면 fetch 불필요.
    setFetched(null);
    setFetchErr(null);
    if (!generation || hasInline || !baseUrl || !runId) return;
    const gen = generation.gen_no;
    let cancelled = false;
    setLoading(true);
    fetch(`${baseUrl}/strategy_code?run=${encodeURIComponent(runId)}&gen=${gen}`,
          { signal: AbortSignal.timeout(window.CONDITION_FETCH_TIMEOUT_MS || 10000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { if (!cancelled) setFetched({ buy_code: j.buy_code || "", sell_code: j.sell_code || "" }); })
      .catch(e => { if (!cancelled) setFetchErr(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [generation, hasInline, baseUrl, runId]);

  if (!generation) return null;

  const isErr = generation.status === "error";
  // 인라인 코드 우선, 없으면 fetch 결과. 둘 다 없으면 빈 문자열(CodeBlock이 안내).
  const buyCode = generation.buy_code || (fetched && fetched.buy_code) || "";
  const sellCode = generation.sell_code || (fetched && fetched.sell_code) || "";
  const code = tab === "buy" ? buyCode : sellCode;
  const name = tab === "buy" ? generation.buy_name : generation.sell_name;
  const fontSize = _CV_FONT_STEPS[Math.max(0, Math.min(_CV_FONT_STEPS.length - 1, fontIdx))];
  const modalClass = "modal code-viewer-modal"
    + (expandedCodeView ? " code-viewer-expanded" : "")
    + (splitView ? " code-viewer-split" : "");
  // v5.13.0 — 기본 폭 확대(A1): 조건식은 줄이 길다. 960px 은 좁아 좌우 스크롤이 잦았다.
  const modalStyle = {
    width: expandedCodeView ? "calc(100vw - 20px)" : (splitView ? "min(1720px, calc(100vw - 32px))" : "min(1400px, calc(100vw - 32px))"),
    maxHeight: expandedCodeView ? "calc(100vh - 18px)" : undefined,
  };
  const countHits = (text) => {
    const needle = String(debouncedQuery || "").trim().toLowerCase();
    if (!needle) return 0;
    return String(text || "").toLowerCase().split(needle).length - 1;
  };
  const hits = splitView ? countHits(buyCode) + countHits(sellCode) : countHits(code);

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };
  const onCopy = () => copyText(splitView
    ? `# 매수 — ${generation.buy_name || "—"}\n${buyCode}\n\n# 매도 — ${generation.sell_name || "—"}\n${sellCode}`
    : code);

  return (
    <div className="modal-bd" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={modalClass} style={modalStyle} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            전략 코드 보기
            <span className="sub">
              gen_{String(generation.gen_no).padStart(2, "0")} · score {fmtScore(generation.graded_score)}
              {generation.gate_passed && <span style={{ color: "var(--teal)", marginLeft: 8 }}>✓ 게이트 통과</span>}
              {isErr && <span style={{ color: "var(--red)", marginLeft: 8 }}>⚠ 오류</span>}
            </span>
          </h2>
          <div className="cv-toolbar">
            <input className="input cv-search" type="search" spellCheck={false}
                   placeholder="조건식 안에서 찾기 (예: 등락율)"
                   value={query} onChange={(e) => setQuery(e.target.value)} />
            {query.trim() && <span className="cv-hitcount mono">{hits}건</span>}
            <span className="cv-fontctl" role="group" aria-label="글자 크기">
              <button className="btn ghost sm" onClick={() => setFontIdx(Math.max(0, fontIdx - 1))}
                      disabled={fontIdx <= 0} title="글자 작게">A−</button>
              <b className="mono">{fontSize}px</b>
              <button className="btn ghost sm" onClick={() => setFontIdx(Math.min(_CV_FONT_STEPS.length - 1, fontIdx + 1))}
                      disabled={fontIdx >= _CV_FONT_STEPS.length - 1} title="글자 크게">A+</button>
            </span>
            <button className="btn ghost sm" aria-pressed={splitView}
                    data-testid="code-viewer-split-toggle"
                    data-tip={splitView ? "한 쪽씩 크게 봅니다." : "매수와 매도를 나란히 놓고 비교합니다."}
                    onClick={() => setSplitView(!splitView)}>
              {splitView ? "한쪽만 보기" : "매수·매도 나란히"}
            </button>
            <button
              className="btn ghost sm"
              data-testid="code-viewer-height-toggle"
              data-tip={expandedCodeView ? "조건식 보기 창을 기본 크기로 줄입니다." : "조건식 보기 창을 화면 전체로 넓힙니다."}
              aria-pressed={expandedCodeView}
              onClick={() => setExpandedCodeView(!expandedCodeView)}
            >
              {expandedCodeView ? "기본 크기" : "전체화면"}
            </button>
            <button className="btn ghost sm" onClick={onCopy}>
              {copied ? "복사됨 ✓" : (splitView ? "매수+매도 복사" : "복사")}
            </button>
            <button className="btn ghost sm" onClick={onClose}>닫기</button>
          </div>
        </div>

        {!splitView && (
          <div className="code-tabs">
            <div className={`code-tab ${tab === "buy" ? "active" : ""}`}
                 onClick={() => setTab("buy")}>
              <span style={{ color: "var(--teal)" }}>●</span> 매수 — {generation.buy_name || "—"}
            </div>
            <div className={`code-tab ${tab === "sell" ? "active" : ""}`}
                 onClick={() => setTab("sell")}>
              <span style={{ color: "var(--amber)" }}>●</span> 매도 — {generation.sell_name || "—"}
            </div>
            <div style={{ marginLeft: "auto", padding: "8px 16px", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
              {(code || "").split("\n").length} lines
            </div>
          </div>
        )}

        <div className={"cv-body" + (splitView ? " split" : "")} style={{ fontSize }}>
          {loading ? (
            <div className="code-block" style={{ color: "var(--ink-3)" }}>코드 불러오는 중…</div>
          ) : fetchErr && !buyCode && !sellCode ? (
            <div className="code-block" style={{ color: "var(--red)" }}>코드 조회 실패: {fetchErr}</div>
          ) : splitView ? (
            <>
              <section className="cv-pane">
                <header>
                  <span style={{ color: "var(--teal)" }}>●</span> 매수 — {generation.buy_name || "—"}
                  <small className="mono">{(buyCode || "").split("\n").length} lines</small>
                  <button className="btn ghost sm" onClick={() => copyText(buyCode)}>복사</button>
                </header>
                <CvCodeBlock code={buyCode} query={debouncedQuery} emptyLabel="이 세대의 매수 조건식 코드를 찾지 못했습니다." />
              </section>
              <section className="cv-pane">
                <header>
                  <span style={{ color: "var(--amber)" }}>●</span> 매도 — {generation.sell_name || "—"}
                  <small className="mono">{(sellCode || "").split("\n").length} lines</small>
                  <button className="btn ghost sm" onClick={() => copyText(sellCode)}>복사</button>
                </header>
                <CvCodeBlock code={sellCode} query={debouncedQuery} emptyLabel="이 세대의 매도 조건식 코드를 찾지 못했습니다." />
              </section>
            </>
          ) : (
            <CvCodeBlock code={code} query={debouncedQuery}
                         emptyLabel={`이 세대의 ${tab === "buy" ? "매수" : "매도"} 조건식 코드를 찾지 못했습니다.`} />
          )}
        </div>

        <StrategyInspectorTabs
          generation={generation}
          runId={runId}
          baseUrl={baseUrl}
          buyCode={buyCode}
          sellCode={sellCode}
        />

        <div className="modal-ft" style={{ justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
              <span style={{ color: "var(--ink-3)" }}>요지:</span> {generation.strategy_gist || "—"}
            </span>
          </div>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
              거래 {generation.trade_count} · MDD <span style={{ color: "var(--red)" }}>{fmtPct(generation.mdd)}</span> ·
              손익 <span className={generation.profit > 0 ? "num-pos" : "num-neg"}>{fmtMoney(generation.profit)}</span>
            </span>
            <button className="btn ghost" onClick={onClose}>닫기</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { CodeViewer, CvCodeBlock, highlightPython });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { CodeViewer, CvCodeBlock };
