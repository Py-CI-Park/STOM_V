/* Strategy code viewer modal: shows full buy/sell code per generation */
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

function CodeBlock({ code }) {
  const highlighted = useMemo_cv(() => highlightPython(code), [code]);
  if (!code) return (
    <div className="code-block" style={{ color: "var(--ink-3)" }}>
      코드가 없습니다.
    </div>
  );
  return (
    <pre className="code-block">
      {highlighted.map((row, i) => (
        <div key={i}>
          <span className="ln">{row.ln}</span>
          {row.parts.map((p, j) => (
            <span key={j} className={p.cls}>{p.t}</span>
          ))}
        </div>
      ))}
    </pre>
  );
}

function CodeViewer({ generation, onClose, runId, baseUrl }) {
  const [tab, setTab] = useState_cv("buy");
  const [copied, setCopied] = useState_cv(false);
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
          { signal: AbortSignal.timeout(2500) })
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

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

  return (
    <div className="modal-bd" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" style={{ width: "min(960px, calc(100vw - 32px))" }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            전략 코드 보기
            <span className="sub">
              gen_{String(generation.gen_no).padStart(2, "0")} · score {fmtScore(generation.graded_score)}
              {generation.gate_passed && <span style={{ color: "var(--teal)", marginLeft: 8 }}>✓ 게이트 통과</span>}
              {isErr && <span style={{ color: "var(--red)", marginLeft: 8 }}>⚠ 오류</span>}
            </span>
          </h2>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button className="btn ghost sm" onClick={onCopy}>
              {copied ? "복사됨 ✓" : "복사"}
            </button>
            <button className="btn ghost sm" onClick={onClose}>닫기</button>
          </div>
        </div>

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

        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {loading ? (
            <div className="code-block" style={{ color: "var(--ink-3)" }}>
              코드 불러오는 중…
            </div>
          ) : fetchErr && !code ? (
            <div className="code-block" style={{ color: "var(--red)" }}>
              코드 조회 실패: {fetchErr}
            </div>
          ) : (
            <CodeBlock code={code} />
          )}
        </div>

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

Object.assign(window, { CodeViewer, CodeBlock, highlightPython });
