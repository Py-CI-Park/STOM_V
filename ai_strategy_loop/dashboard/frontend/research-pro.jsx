/* research-pro.jsx — 리서치 프로(풀스크린 분석 워크스페이스). Phase6 트랙 L.
   window.ResearchProPanel 노출. 백테스트 탭처럼 화면 전체를 써서 '유의미한 수치·
   인사이트 도출과 그 시각화'를 한 화면에 모은다(E2). 구성:
     · 상단 셀렉터 바: run 선택 + 세대 선택 + 새로고침 + 프로세스 버튼(E10)
     · 시간대×시가총액 대형 히트맵(E7) — /edge_ratio segments.cross 재사용, 반응형 대형 셀
     · 명예의 전당 프로(E5/E8) — 조건식 펼침 뷰(monospace 매수+매도) + 변수 칩 + '바로 백테스트'
     · Run Compare 프로(E6) — 선택 run/gen 비교 + 행별 '바로 백테스트'
     · 히스토리(E9) — 과거 run 브라우저 + 조건식 + Bt* 차트 상세 시각화(window.BtResultArea)

   제약(in-browser Babel): import/export 금지 · window 전역 컴포넌트 · 파일별 훅 별칭 ·
   한국어 UI. 기존 파일(backtest.jsx/backtest-charts.jsx)은 수정하지 않고 window 전역만 재사용한다.
   BtVarChips는 window에 없으므로(backtest.jsx 내부 전용) 동일 데이터원(/bt/extract_vars)을
   호출하는 _RpVarChips를 자체 구현한다 — window.BtVarChips가 있으면 우선 사용한다. */

const {
  useState: useState_rp,
  useEffect: useEffect_rp,
  useCallback: useCallback_rp,
  useMemo: useMemo_rp,
  useRef: useRef_rp,
} = React;

/* ── 공용 fetch(무예외) — 실패는 거부로 흘려 호출측 catch가 빈 상태로 표준화한다. ── */
function _rpFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 8000) })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}
function _rpPostJson(url, body, timeoutMs) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
    signal: AbortSignal.timeout(timeoutMs || 8000),
  }).then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

/* 안전 포매터(전역 헬퍼 폴백 포함). */
const _rpMoney = (v) =>
  typeof window.fmtMoney === "function"
    ? window.fmtMoney(v)
    : typeof v === "number" && isFinite(v)
    ? Math.round(v).toLocaleString("ko-KR") + "원"
    : "—";
const _rpInt = (v) =>
  typeof v === "number" && isFinite(v) ? Math.round(v).toLocaleString("ko-KR") : "—";
const _rpNum = (v, d) =>
  typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 2 : d) : "—";
const _rpPct = (v, d) =>
  typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 1 : d) + "%" : "—";

/* 진화 워크벤치(백테스트 탭) 연동 — evolution-analysis.jsx와 동일 payload·전달 경로.
   CustomEvent + localStorage + onOpenWorkbench(탭 전환). 직접 결합 없음(느슨 결합). */
function _rpOpenWorkbench(runId, genNo, onOpenWorkbench) {
  const detail = { run_id: runId, gen_no: genNo };
  try {
    window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
    localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
  } catch (e) {
    /* 전달 실패해도 탭 전환은 시도한다. */
  }
  if (typeof onOpenWorkbench === "function") onOpenWorkbench(detail);
}

/* edge_ratio 색(1.0 발산 기준) — analysis.jsx _edgeColor와 동일 의미(자체 구현, 의존 제거). */
function _rpEdgeColor(er, alpha) {
  if (typeof er !== "number" || !isFinite(er)) return "rgba(40,50,60,0.4)";
  const a = alpha == null ? 0.85 : alpha;
  const d = Math.max(-1, Math.min(1, er - 1)); // 1.0 기준 발산
  if (d >= 0) {
    const t = Math.min(1, d / 0.6);
    return `rgba(${Math.round(60 - 25 * t)},${Math.round(170 + 20 * t)},${Math.round(120 + 10 * t)},${a})`;
  }
  const t = Math.min(1, -d / 0.6);
  return `rgba(${Math.round(200 + 40 * t)},${Math.round(110 - 40 * t)},${Math.round(90 - 30 * t)},${a})`;
}

/* ── 변수 칩(E8) — window.BtVarChips가 있으면 사용, 없으면 /bt/extract_vars 자체 호출. ── */
function _RpVarChips({ baseUrl, isDemo, code }) {
  if (typeof window.BtVarChips === "function") {
    return React.createElement(window.BtVarChips, { baseUrl, isDemo, code });
  }
  const [known, setKnown] = useState_rp([]);
  const [unknown, setUnknown] = useState_rp([]);

  useEffect_rp(() => {
    if (isDemo || !baseUrl) {
      setKnown([]);
      setUnknown([]);
      return undefined;
    }
    const trimmed = (code || "").trim();
    if (!trimmed) {
      setKnown([]);
      setUnknown([]);
      return undefined;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      _rpPostJson(baseUrl + "/bt/extract_vars", { code: trimmed }, 5000)
        .then((j) => {
          if (cancelled) return;
          setKnown(Array.isArray(j && j.known) ? j.known : []);
          setUnknown(Array.isArray(j && j.unknown) ? j.unknown : []);
        })
        .catch(() => {
          if (!cancelled) {
            setKnown([]);
            setUnknown([]);
          }
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [baseUrl, isDemo, code]);

  if (known.length === 0 && unknown.length === 0) {
    return (
      <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
        사용 변수 칩 — 조건식의 한글 변수가 SSOT 화이트리스트와 대조되어 표시됩니다.
      </div>
    );
  }
  const chip = (v, ok) => (
    <span
      key={(ok ? "k:" : "u:") + v.name}
      className="mono rp-chip"
      title={ok ? "SSOT 화이트리스트 변수" : "SSOT 어휘 밖 — 오타이거나 미정의 변수일 수 있습니다"}
      style={{
        border: "1px solid " + (ok ? "var(--teal-dim)" : "rgba(240,179,90,0.45)"),
        color: ok ? "var(--teal)" : "var(--amber)",
        background: ok ? "rgba(76,214,179,0.06)" : "rgba(240,179,90,0.06)",
      }}
    >
      {ok ? "" : "⚠ "}
      {v.name}
      {v.count > 1 && <span style={{ color: "var(--ink-3)" }}>×{v.count}</span>}
    </span>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {known.map((v) => chip(v, true))}
        {unknown.map((v) => chip(v, false))}
      </div>
      <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
        SSOT 변수 {known.length} · 미확인 {unknown.length}
      </div>
    </div>
  );
}

/* ── 조건식 뷰어(E5/E8/E9) — run+gen으로 /strategy_code 조회, 매수·매도 monospace + 변수칩. ── */
function _RpStrategyCode({ baseUrl, isDemo, runId, genNo }) {
  const [code, setCode] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);

  useEffect_rp(() => {
    if (isDemo || !baseUrl || !runId || genNo == null || genNo < 0) {
      setCode(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    /* /strategy_code 쿼리는 run/gen(런/세대) 키를 쓴다(코드 뷰어와 동일). */
    _rpFetchJson(
      baseUrl + "/strategy_code?run=" + encodeURIComponent(runId) + "&gen=" + encodeURIComponent(genNo),
      8000
    )
      .then((j) => {
        if (!cancelled) setCode(j || null);
      })
      .catch(() => {
        if (!cancelled) setCode(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, runId, genNo]);

  if (loading) {
    return <div className="mono rp-code-empty">조건식 불러오는 중…</div>;
  }
  if (!code) {
    return <div className="mono rp-code-empty">조건식 정보 없음</div>;
  }
  const buy = code.buy_code || "";
  const sell = code.sell_code || "";
  if (!buy && !sell) {
    return (
      <div className="mono rp-code-empty">
        이 세대의 조건식 코드가 없습니다{code.reason ? ` (${code.reason})` : ""}.
      </div>
    );
  }
  return (
    <div className="rp-code-grid">
      <div>
        <div className="rp-code-label" style={{ color: "var(--teal)" }}>
          매수 조건식 {code.buy_name ? `· ${code.buy_name}` : ""}
        </div>
        <pre className="rp-code-block">{buy || "(없음)"}</pre>
        <_RpVarChips baseUrl={baseUrl} isDemo={isDemo} code={buy} />
      </div>
      <div>
        <div className="rp-code-label" style={{ color: "var(--blue)" }}>
          매도 조건식 {code.sell_name ? `· ${code.sell_name}` : ""}
        </div>
        <pre className="rp-code-block">{sell || "(없음)"}</pre>
        <_RpVarChips baseUrl={baseUrl} isDemo={isDemo} code={sell} />
      </div>
    </div>
  );
}

/* ── E7: 시간대×시가총액 대형 히트맵 — /edge_ratio segments.cross 재사용, 반응형 큰 셀. ── */
function _RpBigHeatmap({ baseUrl, isDemo, runId }) {
  const [data, setData] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);
  const [err, setErr] = useState_rp(null);

  const refresh = useCallback_rp(() => {
    if (isDemo || !baseUrl || !runId) {
      setData(null);
      return;
    }
    setLoading(true);
    _rpFetchJson(
      baseUrl + "/edge_ratio?run_ids=" + encodeURIComponent(runId) + "&fine_time=true",
      8000
    )
      .then((j) => {
        setData(j);
        setErr(null);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId]);

  useEffect_rp(() => {
    refresh();
  }, [refresh]);

  const grid = useMemo_rp(() => {
    const cross = (data && data.segments && data.segments.cross) || [];
    if (!cross.length) return null;
    const timeLabels = [];
    const capLabels = [];
    const cellMap = {};
    for (const c of cross) {
      const parts = (c.label || "").split("×");
      const tl = parts[0] ? parts[0].trim() : c.label;
      const cl = parts[1] ? parts[1].trim() : "";
      if (!timeLabels.includes(tl)) timeLabels.push(tl);
      if (cl && !capLabels.includes(cl)) capLabels.push(cl);
      cellMap[tl + "×" + cl] = c;
    }
    if (capLabels.length === 0) return null;
    return { timeLabels, capLabels, cellMap };
  }, [data]);

  const globalEr = data && data.global && typeof data.global.edge_ratio === "number"
    ? data.global.edge_ratio : null;

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">시간대 × 시가총액 탐색 히트맵</span>
        <span
          className="rp-help"
          title="Edge Ratio = 유리한 가격 진행 / 불리한 가격 진행. 1.0 초과면 평균적으로 유리한 구간입니다. 시간대(행) × 시가총액(열) 교차에서 어느 환경이 우위인지 한눈에 봅니다."
        >
          ?
        </span>
        {globalEr != null && (
          <span className="rp-card-sub">전체 edge {_rpNum(globalEr, 3)}</span>
        )}
        <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={refresh} disabled={isDemo || loading}>
          {loading ? "조회중…" : "↻ 새로고침"}
        </button>
      </div>
      <div className="rp-card-bd">
        {isDemo ? (
          <div className="rp-empty">데모 모드 — 라이브 run 연결 시 히트맵이 표시됩니다.</div>
        ) : !runId ? (
          <div className="rp-empty">run을 선택하면 시간대×시총 히트맵이 표시됩니다.</div>
        ) : err ? (
          <div className="rp-empty">조회 실패 — {err}</div>
        ) : !grid ? (
          <div className="rp-empty">
            교차 세그먼트(시간대×시총)가 누적되면 히트맵이 표시됩니다.{loading ? " (로딩중…)" : ""}
          </div>
        ) : (
          <_RpHeatmapGrid grid={grid} />
        )}
      </div>
    </div>
  );
}

/* 반응형 대형 히트맵 그리드 — CSS grid로 컨테이너 폭을 채우는 큰 셀(트렌드 차트 급 크기). */
function _RpHeatmapGrid({ grid }) {
  const { timeLabels, capLabels, cellMap } = grid;
  const cols = `120px repeat(${capLabels.length}, minmax(64px, 1fr))`;
  return (
    <div className="rp-heatmap" style={{ gridTemplateColumns: cols }}>
      {/* 헤더 행 */}
      <div className="rp-heatmap-corner mono">시간대 \ 시총</div>
      {capLabels.map((cl) => (
        <div key={"h" + cl} className="rp-heatmap-colhd mono" title={cl}>
          {cl}
        </div>
      ))}
      {/* 본문 */}
      {timeLabels.map((tl) => (
        <React.Fragment key={"r" + tl}>
          <div className="rp-heatmap-rowhd mono" title={tl}>
            {tl}
          </div>
          {capLabels.map((cl) => {
            const cell = cellMap[tl + "×" + cl];
            const er = cell ? cell.edge_ratio : null;
            const bg = _rpEdgeColor(er, 0.85);
            const strong = er != null && Math.abs(er - 1) > 0.15;
            return (
              <div
                key={"c" + tl + cl}
                className="rp-heatmap-cell mono"
                style={{ background: bg, color: strong ? "#fff" : "var(--ink-1)" }}
                title={
                  cell
                    ? `${tl} × ${cl} · edge ${_rpNum(er, 3)} · ${cell.count || 0}건` +
                      (typeof cell.win_rate === "number" ? ` · 승률 ${_rpPct(cell.win_rate * 100)}` : "")
                    : `${tl} × ${cl} · 데이터 없음`
                }
              >
                <strong>{er != null ? _rpNum(er, 2) : "—"}</strong>
                {cell && typeof cell.count === "number" && (
                  <small>{cell.count}건</small>
                )}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}

/* ── E5: 명예의 전당 프로 — 행 펼침 시 조건식 + 변수칩 + '바로 백테스트'. ── */
function _RpHallOfFame({ baseUrl, isDemo, onOpenWorkbench }) {
  const [hof, setHof] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);
  const [expanded, setExpanded] = useState_rp(null); // "run/gen" 또는 null

  const refresh = useCallback_rp(() => {
    if (isDemo || !baseUrl) {
      setHof(null);
      return;
    }
    setLoading(true);
    _rpFetchJson(baseUrl + "/hall_of_fame", 8000)
      .then((j) => setHof(j))
      .catch(() => setHof(null))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_rp(() => {
    refresh();
  }, [refresh]);

  const ai = (hof && Array.isArray(hof.ai) ? hof.ai : []).filter((r) => r.run_id && r.gen_no != null);

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">🏆 명예의 전당 프로 — 조건식 · 바로 사용</span>
        <span
          className="rp-help"
          title="게이트를 통과한 흑자 전략을 점수 내림차순으로 보여줍니다. 행을 펼치면 매수·매도 조건식과 변수 칩을 확인하고, '바로 백테스트'로 백테스트 탭에 그대로 적재합니다."
        >
          ?
        </span>
        <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={refresh} disabled={isDemo || loading}>
          {loading ? "조회중…" : "↻ 새로고침"}
        </button>
      </div>
      <div className="rp-card-bd">
        {isDemo ? (
          <div className="rp-empty">데모 모드 — 백엔드 연결 시 명예의 전당이 표시됩니다.</div>
        ) : ai.length === 0 ? (
          <div className="rp-empty">게이트 통과 전략이 누적되면 표시됩니다.{loading ? " (로딩중…)" : ""}</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="rp-table mono">
              <thead>
                <tr>
                  <th>종류</th>
                  <th>전략(run/gen)</th>
                  <th>백테 기간</th>
                  <th>점수</th>
                  <th>총수익</th>
                  <th>수익률</th>
                  <th>연환산</th>
                  <th>MDD</th>
                  <th>거래</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ai.map((r) => {
                  const key = r.run_id + "/" + r.gen_no;
                  const isOpen = expanded === key;
                  return (
                    <React.Fragment key={key}>
                      <tr className={isOpen ? "rp-row-open" : ""}>
                        <td>
                          <span className={"rp-kind rp-kind-" + (r.kind || "ai")}>
                            {r.kind === "seed" ? "시드" : "AI"}
                          </span>
                        </td>
                        <td title={r.buy_name || ""}>{r.label || key}</td>
                        <td>{r.period || "기간 정보 없음"}</td>
                        <td style={{ color: "var(--teal)" }}>{_rpNum(r.score, 3)}</td>
                        <td className={r.total_return_krw > 0 ? "rp-pos" : "rp-neg"}>
                          {_rpMoney(r.total_return_krw)}
                        </td>
                        <td>{_rpPct(r.total_return_pct)}</td>
                        <td title={r.annual_unreliable ? "창 길이 0.25년 미만 — 연환산 과대 주의" : ""}>
                          {_rpPct(r.annual_return_pct)}
                          {r.annual_unreliable ? " ⚠" : ""}
                        </td>
                        <td style={{ color: "var(--red)" }}>{_rpPct(r.mdd_pct)}</td>
                        <td>{_rpInt(r.trades)}</td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button
                            className="btn ghost sm"
                            onClick={() => setExpanded(isOpen ? null : key)}
                            data-tip="조건식·변수 칩 펼치기"
                          >
                            {isOpen ? "▲ 닫기" : "▼ 조건식"}
                          </button>
                          <button
                            className="btn ghost sm"
                            style={{ marginLeft: 4 }}
                            onClick={() => _rpOpenWorkbench(r.run_id, r.gen_no, onOpenWorkbench)}
                            data-tip="백테스트 탭에 이 전략을 적재하고 전환"
                          >
                            바로 백테스트
                          </button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="rp-row-detail">
                          <td colSpan={10}>
                            <_RpStrategyCode baseUrl={baseUrl} isDemo={isDemo} runId={r.run_id} genNo={r.gen_no} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E6: Run Compare 프로 — run/gen 후보를 담아 나란히 비교 + 행별 바로 백테스트. ── */
function _RpRunCompare({ baseUrl, isDemo, runList, currentRunId, currentGenNo, onOpenWorkbench }) {
  const [items, setItems] = useState_rp([]); // [{run_id,gen_no,result}]
  const [addRun, setAddRun] = useState_rp("");
  const [addGen, setAddGen] = useState_rp(0);

  /* 현재 선택을 비교 후보로 추가 + 결과(/bt/result run+gen) 적재. */
  const add = useCallback_rp(
    (runId, genNo) => {
      if (isDemo || !baseUrl || !runId || genNo == null) return;
      const key = runId + "/" + genNo;
      setItems((prev) => {
        if (prev.some((p) => p.key === key)) return prev;
        return [...prev, { key, run_id: runId, gen_no: genNo, result: null, loading: true }];
      });
      _rpFetchJson(
        baseUrl + "/bt/result?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(genNo),
        9000
      )
        .then((j) => {
          setItems((prev) =>
            prev.map((p) => (p.key === key ? { ...p, result: j, loading: false } : p))
          );
        })
        .catch(() => {
          setItems((prev) => prev.map((p) => (p.key === key ? { ...p, loading: false } : p)));
        });
    },
    [baseUrl, isDemo]
  );

  const remove = useCallback_rp((key) => {
    setItems((prev) => prev.filter((p) => p.key !== key));
  }, []);

  const metricOf = (it) => {
    const m = (it.result && (it.result.metrics || (it.result.analysis && it.result.analysis.summary))) || {};
    return m || {};
  };

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">Run Compare 프로 — 좋은 결과를 바로 사용</span>
        <span
          className="rp-help"
          title="여러 run/세대 결과를 나란히 비교합니다. 각 행에서 '바로 백테스트'로 백테스트 탭에 적재해 정밀 분석합니다."
        >
          ?
        </span>
      </div>
      <div className="rp-card-bd">
        <div className="rp-compare-add">
          <button
            className="btn ghost sm"
            onClick={() => add(currentRunId, currentGenNo)}
            disabled={isDemo || !currentRunId}
            data-tip="상단에서 선택한 run·세대를 비교에 추가"
          >
            + 현재 선택 추가 ({currentRunId || "—"}/g{currentGenNo})
          </button>
          <span className="rp-compare-sep">또는</span>
          <select
            className="mono rp-select"
            value={addRun}
            onChange={(e) => setAddRun(e.target.value)}
            disabled={isDemo}
          >
            <option value="">run 선택</option>
            {(runList || []).map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}
                {r.label ? " · " + r.label : ""}
              </option>
            ))}
          </select>
          <label className="rp-compare-genlbl mono">
            gen
            <input
              type="number"
              min={0}
              value={addGen}
              onChange={(e) => setAddGen(Number(e.target.value) || 0)}
              className="rp-num-input mono"
            />
          </label>
          <button
            className="btn ghost sm"
            onClick={() => add(addRun, addGen)}
            disabled={isDemo || !addRun}
          >
            + 추가
          </button>
        </div>

        {items.length === 0 ? (
          <div className="rp-empty">비교할 run/세대를 추가하세요.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="rp-table mono">
              <thead>
                <tr>
                  <th>run / gen</th>
                  <th>총손익</th>
                  <th>MDD</th>
                  <th>승률</th>
                  <th>거래</th>
                  <th>Payoff</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const m = metricOf(it);
                  return (
                    <tr key={it.key}>
                      <td>{it.key}</td>
                      {it.loading ? (
                        <td colSpan={5} className="rp-muted">불러오는 중…</td>
                      ) : (
                        <>
                          <td className={m.total_profit > 0 ? "rp-pos" : "rp-neg"}>
                            {_rpMoney(m.total_profit != null ? m.total_profit : m.profit)}
                          </td>
                          <td style={{ color: "var(--red)" }}>{_rpPct(m.mdd)}</td>
                          <td>{_rpPct(m.win_rate != null ? m.win_rate * 100 : m.win_rate_pct)}</td>
                          <td>{_rpInt(m.trade_count != null ? m.trade_count : m.trades)}</td>
                          <td>{_rpNum(m.payoff_ratio != null ? m.payoff_ratio : m.payoff, 2)}</td>
                        </>
                      )}
                      <td style={{ whiteSpace: "nowrap" }}>
                        <button
                          className="btn ghost sm"
                          onClick={() => _rpOpenWorkbench(it.run_id, it.gen_no, onOpenWorkbench)}
                          data-tip="백테스트 탭에 적재"
                        >
                          바로 백테스트
                        </button>
                        <button className="btn ghost sm" style={{ marginLeft: 4 }} onClick={() => remove(it.key)}>
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E9: 히스토리 — 과거 run 브라우저. 선택 시 세대·조건식 + Bt* 차트 상세 시각화. ── */
function _RpHistory({ baseUrl, isDemo, runList, onOpenWorkbench }) {
  const [selRun, setSelRun] = useState_rp("");
  const [gens, setGens] = useState_rp([]);
  const [selGen, setSelGen] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);

  /* 선택 run의 세대 목록(/bt/evo_gens, 읽기 전용) — evolution-analysis.jsx와 동일 소스. */
  useEffect_rp(() => {
    if (isDemo || !baseUrl || !selRun) {
      setGens([]);
      setSelGen(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    _rpFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(selRun), 9000)
      .then((j) => {
        if (cancelled) return;
        const items = Array.isArray(j && j.items) ? j.items : [];
        setGens(items);
        /* 기본 선택: gate 통과 세대 우선, 없으면 score 최고. */
        const ranked = items
          .filter((g) => g.gen_no >= 0)
          .slice()
          .sort((a, b) => (b.score || 0) - (a.score || 0));
        const best = ranked.find((g) => g.gate_passed) || ranked[0];
        setSelGen(best ? best.gen_no : null);
      })
      .catch(() => {
        if (!cancelled) {
          setGens([]);
          setSelGen(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, selRun]);

  const topGens = useMemo_rp(
    () =>
      gens
        .filter((g) => g.gen_no >= 0)
        .slice()
        .sort((a, b) => (b.score || 0) - (a.score || 0))
        .slice(0, 12),
    [gens]
  );

  const hasBt = typeof window.BtResultArea === "function";

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">히스토리 — 과거 연구 재열람</span>
        <span
          className="rp-help"
          title="과거 run을 골라 세대별 조건식과 백테스트 탭과 동일한 상세 결과 시각화(자본곡선·분포·히트맵·언더워터 등)를 다시 봅니다."
        >
          ?
        </span>
      </div>
      <div className="rp-card-bd">
        <div className="rp-history-bar">
          <select
            className="mono rp-select"
            value={selRun}
            onChange={(e) => setSelRun(e.target.value)}
            disabled={isDemo}
          >
            <option value="">과거 run 선택…</option>
            {(runList || []).map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}
                {r.label ? " · " + r.label : ""}
                {r.gate_passed_count > 0 ? " ✓" : ""}
              </option>
            ))}
          </select>
          {loading && <span className="rp-muted mono">세대 불러오는 중…</span>}
        </div>

        {!selRun ? (
          <div className="rp-empty">과거 run을 선택하면 세대·조건식·상세 결과가 표시됩니다.</div>
        ) : (
          <div className="rp-history-grid">
            <div className="rp-history-genlist">
              <div className="rp-mini-label">세대 (score 내림차순)</div>
              {topGens.length === 0 ? (
                <div className="rp-empty">세대 없음</div>
              ) : (
                topGens.map((g) => (
                  <button
                    key={g.gen_no}
                    className={"rp-gen-btn mono" + (selGen === g.gen_no ? " active" : "")}
                    onClick={() => setSelGen(g.gen_no)}
                    title={`score ${_rpNum(g.score, 3)} · 손익 ${_rpMoney(g.profit)} · MDD ${_rpPct(g.mdd)}`}
                  >
                    <span>gen_{String(g.gen_no).padStart(2, "0")}</span>
                    <span className={g.profit > 0 ? "rp-pos" : "rp-neg"}>{_rpMoney(g.profit)}</span>
                    {g.gate_passed && <span style={{ color: "var(--teal)" }}>✓</span>}
                  </button>
                ))
              )}
            </div>
            <div className="rp-history-detail">
              {selGen == null ? (
                <div className="rp-empty">세대를 선택하세요.</div>
              ) : (
                <>
                  <div className="rp-history-actions">
                    <span className="rp-mini-label">
                      {selRun} / gen_{String(selGen).padStart(2, "0")} — 조건식 & 상세 결과
                    </span>
                    <button
                      className="btn ghost sm"
                      style={{ marginLeft: "auto" }}
                      onClick={() => _rpOpenWorkbench(selRun, selGen, onOpenWorkbench)}
                      data-tip="백테스트 탭에 적재"
                    >
                      바로 백테스트
                    </button>
                  </div>
                  <_RpStrategyCode baseUrl={baseUrl} isDemo={isDemo} runId={selRun} genNo={selGen} />
                  <div className="rp-history-charts">
                    {hasBt ? (
                      <window.BtResultArea
                        baseUrl={baseUrl}
                        isDemo={isDemo}
                        jobId={null}
                        evoSource={{ run_id: selRun, gen_no: selGen }}
                      />
                    ) : (
                      <div className="rp-empty">상세 차트 컴포넌트(BtResultArea)를 불러올 수 없습니다.</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E10: 프로세스 플로우 오버레이 — 전체 진화 파이프라인을 시각적 흐름으로. ── */
const RP_PIPELINE = [
  {
    key: "seed",
    title: "시드 선택",
    icon: "🌱",
    desc: "사람이 검증한 출발 전략(시드)을 고릅니다. 이후 모든 진화의 기준점이 됩니다.",
    terms: [["시드", "진화의 출발이 되는 기준 전략(예: Tick_902)."]],
  },
  {
    key: "gen",
    title: "후보 생성 (LLM)",
    icon: "🧬",
    desc: "LLM이 직전 세대의 부검(왜 졌는지)을 컨텍스트로 새 매수/매도 조건식을 생성합니다.",
    terms: [["세대", "한 번의 생성→평가 사이클. gen_00, gen_01 …로 번호가 매겨집니다."]],
  },
  {
    key: "grid",
    title: "격자 탐색",
    icon: "▦",
    desc: "파라미터(θ)를 격자(grid)로 훑어 어느 조합이 견고한지 지형을 만듭니다. 단일 피크가 아닌 '고원'을 찾습니다.",
    terms: [
      ["격자", "여러 파라미터 값을 바둑판처럼 조합해 전수 탐색하는 방식."],
      ["고원/mesa", "이웃 파라미터도 모두 흑자인 안정 영역 — 과최적화가 아닌 진짜 우위."],
    ],
  },
  {
    key: "bt",
    title: "백테스트 평가",
    icon: "📊",
    desc: "지정 기간·시간단위로 자본곡선·낙폭(MDD)·매매를 시뮬레이션해 성과를 측정합니다.",
    terms: [["MDD", "최대 낙폭 — 고점 대비 가장 크게 빠진 비율. 작을수록 안전."]],
  },
  {
    key: "gate",
    title: "적합도 / 품질 게이트",
    icon: "🚦",
    desc: "점수 ≥ 목표 & MDD ≤ 상한 & 거래수 ≥ 하한을 동시에 만족해야 통과합니다. 품질은 결과의 견고함을 봅니다.",
    terms: [
      ["적합도(fitness)", "손익·MDD·거래수·일관성의 가중합 점수."],
      ["니치", "특정 환경(시간대·시총)에 특화된 전략 군집."],
    ],
  },
  {
    key: "oos",
    title: "OOS 검증",
    icon: "🔬",
    desc: "학습에 쓰지 않은 기간(Out-Of-Sample)에서 성과가 유지되는지 확인합니다. 과최적화를 거르는 핵심 관문.",
    terms: [["OOS", "Out-Of-Sample — 최적화에 쓰지 않은 미래/별도 구간. 진짜 일반화 검증."]],
  },
  {
    key: "freeze",
    title: "명예의 전당 / 동결",
    icon: "🏆",
    desc: "검증을 통과한 전략을 명예의 전당에 올리고, 더 이상 바뀌지 않도록 동결(freeze)해 운영 후보로 보관합니다.",
    terms: [["동결", "전략을 고정·박제해 재현 가능한 기준선으로 보존하는 것."]],
  },
];

/* live 상태/ops에서 현재 활성 단계를 휴리스틱으로 추정(불가하면 -1=정적 흐름). */
function _rpActiveStage(liveState, ops) {
  const phase = (liveState && (liveState.phase || (liveState.latest && liveState.latest.phase))) || "";
  const status = (liveState && liveState.status) || "";
  const p = String(phase).toLowerCase();
  if (status === "running") {
    if (p.indexOf("generate") >= 0 || p.indexOf("loop_start") >= 0 || p.indexOf("warm") >= 0 || p.indexOf("ga_init") >= 0)
      return 1; // 후보 생성
    if (p.indexOf("backtest") >= 0 || p.indexOf("evaluate") >= 0) return 3; // 백테 평가
    if (p.indexOf("score") >= 0) return 4; // 게이트
    if (p.indexOf("autopsy") >= 0 || p.indexOf("generation_done") >= 0) return 1; // 다음 후보 생성
  }
  const active = (ops && Array.isArray(ops.active) ? ops.active : []).length;
  if (active > 0 && status !== "complete") return 3; // 돌고 있으면 평가 중으로 가정
  return -1;
}

function _RpProcessFlowOverlay({ onClose, liveState, ops }) {
  const activeStage = _rpActiveStage(liveState, ops);

  useEffect_rp(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="rp-overlay" onClick={onClose}>
      <div className="rp-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="rp-overlay-hd">
          <span className="rp-card-title">진화 프로세스 — 전체 흐름</span>
          {activeStage >= 0 && (
            <span className="rp-card-sub">현재 단계: {RP_PIPELINE[activeStage].title}</span>
          )}
          <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕ 닫기 (Esc)
          </button>
        </div>
        <div className="rp-flow">
          {RP_PIPELINE.map((s, i) => {
            const isActive = i === activeStage;
            return (
              <React.Fragment key={s.key}>
                <div className={"rp-flow-node" + (isActive ? " rp-flow-active" : "")}>
                  <div className="rp-flow-ico">{s.icon}</div>
                  <div className="rp-flow-name">
                    {i + 1}. {s.title}
                    {isActive && <span className="rp-flow-pulse"> ● 진행</span>}
                  </div>
                  <div className="rp-flow-desc">{s.desc}</div>
                  <div className="rp-flow-terms">
                    {s.terms.map(([t, d]) => (
                      <div key={t} className="rp-flow-term">
                        <b>{t}</b> {d}
                      </div>
                    ))}
                  </div>
                </div>
                {i < RP_PIPELINE.length - 1 && <div className="rp-flow-arrow">→</div>}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
/* 외부(research-lab.jsx 헤더 버튼 등)에서도 오버레이를 쓸 수 있게 전역 노출. */
Object.assign(window, { ResearchProcessFlowOverlay: _RpProcessFlowOverlay });

/* ── 메인: ResearchProPanel — 풀스크린 워크스페이스. ── */
function ResearchProPanel({ baseUrl, wsStatus, runId }) {
  const isDemo =
    typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";

  const [runList, setRunList] = useState_rp([]);
  const [selRun, setSelRun] = useState_rp(runId || "");
  const [selGen, setSelGen] = useState_rp(0);
  const [ops, setOps] = useState_rp(null);
  const [liveState, setLiveState] = useState_rp(null);
  const [showFlow, setShowFlow] = useState_rp(false);
  const [refreshKey, setRefreshKey] = useState_rp(0);

  /* 부모 runId가 처음 들어오면 기본 선택으로 따라간다(명시 선택 전까지). */
  useEffect_rp(() => {
    if (runId && !selRun) setSelRun(runId);
  }, [runId]);

  /* run 목록(/runs). */
  useEffect_rp(() => {
    if (isDemo || !baseUrl) {
      setRunList([]);
      return undefined;
    }
    let cancelled = false;
    _rpFetchJson(baseUrl + "/runs", 6000)
      .then((j) => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
        if (!selRun && runs.length) setSelRun(runs[0].run_id);
      })
      .catch(() => {
        if (!cancelled) setRunList([]);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, refreshKey]);

  /* ops_status(10초) + live state(현재 단계 추정용). */
  useEffect_rp(() => {
    if (isDemo || !baseUrl) return undefined;
    const pull = () => {
      _rpFetchJson(baseUrl + "/ops_status", 8000)
        .then((j) => setOps(j))
        .catch(() => {});
      _rpFetchJson(baseUrl + "/status", 8000)
        .then((j) => setLiveState(j))
        .catch(() => {});
    };
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [baseUrl, isDemo, refreshKey]);

  const onRefresh = useCallback_rp(() => setRefreshKey((k) => k + 1), []);
  const onOpenWorkbench = useCallback_rp(() => {
    /* 풀스크린(별도 페이지)에서는 부모 앱 탭을 직접 못 바꾸므로, 운영 앱이 새로고침 시
       마지막 탭으로 쓰는 localStorage(stom_active_tab)를 'backtest'로 설정한 뒤 운영
       페이지로 이동한다. 선택 세대는 _rpOpenWorkbench가 stom_bt_evo_pending에 적재해 둔다
       (백테 탭의 진화 셀렉터가 그 run을 펼쳐 둔 상태로 보여줌). 같은 페이지(운영 내부)
       에서 열린 경우엔 이 콜백이 주입되지 않으므로 이 경로는 풀스크린 전용이다. */
    try {
      localStorage.setItem("stom_active_tab", "backtest");
      window.location.href = "/ui/";
    } catch (e) {
      /* 무시 — 이동 실패해도 CustomEvent/localStorage 적재는 이미 끝났다. */
    }
  }, []);

  const activeRunLabel = useMemo_rp(() => {
    const r = (runList || []).find((x) => x.run_id === selRun);
    return r && r.label ? r.label : "";
  }, [runList, selRun]);

  return (
    <div className="research-pro">
      {/* 상단 셀렉터 바 */}
      <div className="rp-topbar">
        <div className="rp-topbar-title">
          <span className="rp-topbar-mark">🔬</span>
          <div>
            <div className="rp-topbar-h">리서치 프로 — 전체화면 분석 워크스페이스</div>
            <div className="rp-topbar-sub mono">
              {selRun ? selRun : "run 미선택"}
              {activeRunLabel ? " · " + activeRunLabel : ""}
            </div>
          </div>
        </div>
        <div className="rp-topbar-controls">
          <label className="rp-ctl mono">
            <span>run</span>
            <select
              className="mono rp-select"
              value={selRun}
              onChange={(e) => setSelRun(e.target.value)}
              disabled={isDemo}
            >
              <option value="">선택…</option>
              {(runList || []).map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id}
                  {r.label ? " · " + r.label : ""}
                  {r.gate_passed_count > 0 ? " ✓" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="rp-ctl mono">
            <span>gen</span>
            <input
              type="number"
              min={0}
              value={selGen}
              onChange={(e) => setSelGen(Number(e.target.value) || 0)}
              className="rp-num-input mono"
            />
          </label>
          <button className="btn ghost sm" onClick={onRefresh} disabled={isDemo}>
            ↻ 새로고침
          </button>
          <button className="btn ghost sm" onClick={() => setShowFlow(true)} data-tip="진화 전체 프로세스 보기">
            🧭 프로세스
          </button>
        </div>
      </div>

      {isDemo ? (
        <div className="rp-empty" style={{ margin: 24 }}>
          데모(미연결) 모드 — 실 run에 연결하면 리서치 프로 분석이 표시됩니다.
        </div>
      ) : (
        <div className="rp-grid">
          <_RpBigHeatmap baseUrl={baseUrl} isDemo={isDemo} runId={selRun} key={"hm" + refreshKey} />
          <_RpHallOfFame baseUrl={baseUrl} isDemo={isDemo} onOpenWorkbench={onOpenWorkbench} key={"hof" + refreshKey} />
          <_RpRunCompare
            baseUrl={baseUrl}
            isDemo={isDemo}
            runList={runList}
            currentRunId={selRun}
            currentGenNo={selGen}
            onOpenWorkbench={onOpenWorkbench}
          />
          <_RpHistory baseUrl={baseUrl} isDemo={isDemo} runList={runList} onOpenWorkbench={onOpenWorkbench} />
        </div>
      )}

      {showFlow && (
        <_RpProcessFlowOverlay onClose={() => setShowFlow(false)} liveState={liveState} ops={ops} />
      )}
    </div>
  );
}

Object.assign(window, { ResearchProPanel });
