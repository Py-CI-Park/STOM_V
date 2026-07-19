/* v4-catalog.jsx — sealed rdc-1 P4 catalog prototype.
 *   Reports-owned rollback/prototype surface only. It consumes the sealed
 *   /research/assets|judgments|cells|clauses API contract and never reads raw
 *   research sources or legacy summary aggregation outside rdc-1.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_cat, useEffect: useEffect_cat, useRef: useRef_cat } = React;

const CAT_CONTRACT_VERSION = "rdc-1";
const CAT_CELL_SOURCES = Object.freeze(["o1g", "sv1_l0", "sv1_l1", "v2a_full", "v2a_pilot"]);
const CAT_ENDPOINTS = Object.freeze({
  assets: "/research/assets?limit=500",
  judgments: "/research/judgments?include_ledger=1&limit=200",
  clauses: "/research/clauses?limit=200",
});

function _catCellsRoute(source) {
  return "/research/cells?source=" + encodeURIComponent(source) + "&limit=2000";
}

function _catVerdictPrefix(v) {
  const s = String(v || "—");
  return s.split(" — ")[0] || s;
}

function _catVerdictCls(v) {
  const s = String(v || "");
  if (/^KILL|^KILL-2|^KILL\(0\/2\)|기각/.test(s)) return "bad";
  if (/^무가치/.test(s)) return "off";
  if (/^생존/.test(s)) return "win";
  if (/^PASS|^양성/.test(s)) return "ok";
  return "warn";
}

function _catText(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") return _catJsonPreview(value);
  return String(value);
}

function _catJsonPreview(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch (_err) {
    return String(value);
  }
}

function _catPct(value) {
  const n = Number(value);
  return Number.isFinite(n) ? (n * 100).toFixed(2) + "%" : "—";
}

function _catPp(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(3) + "%p" : "—";
}

function _catFlag(value) {
  if (value === true || value === 1 || value === "1") return "yes";
  if (value === false || value === 0 || value === "0") return "no";
  return "—";
}

function _catItems(envelope) {
  return envelope && envelope.available && Array.isArray(envelope.items) ? envelope.items : [];
}

function _catNormalizeEnvelope(name, value) {
  if (!value || typeof value !== "object") return { name, available: false, reason: "malformed_response" };
  if (value.available === false) return Object.assign({ name }, value);
  if (value.contract_version !== CAT_CONTRACT_VERSION) {
    return Object.assign({}, value, {
      name,
      available: false,
      reason: "contract_mismatch",
      actual_contract_version: value.contract_version || "missing",
    });
  }
  const items = Array.isArray(value.items) ? value.items : [];
  const count = Number.isFinite(Number(value.count)) ? Number(value.count) : items.length;
  return Object.assign({}, value, { name, available: true, items, count });
}

function _catUnavailableText(envelope) {
  if (!envelope) return "응답 대기";
  const parts = [envelope.name || "catalog", envelope.reason || "unavailable"];
  if (envelope.actual_contract_version) parts.push("actual=" + envelope.actual_contract_version);
  if (envelope.param) parts.push("param=" + envelope.param);
  if (Array.isArray(envelope.allowed)) parts.push("allowed=" + envelope.allowed.join(","));
  if (Array.isArray(envelope.missing)) parts.push("missing=" + envelope.missing.join(","));
  return parts.join(" · ");
}

function _catCatalogMtime(envelopes) {
  const hit = envelopes.find(env => env && env.catalog && env.catalog.db_mtime_utc);
  return hit ? hit.catalog.db_mtime_utc : "—";
}

function _catCellMasked(cell) {
  return Boolean(cell && (cell.insufficient === true || cell.insufficient === 1 || cell.insufficient === "1" || Number(cell.n) < 2000));
}

function _catCellTone(cell) {
  if (_catCellMasked(cell)) return "insufficient";
  const ciLow = Number(cell && cell.ci_low);
  if (Number.isFinite(ciLow) && ciLow > 0) return "positive";
  if (Number.isFinite(ciLow) && ciLow < 0) return "negative";
  return "neutral";
}

function _catUnique(rows, key) {
  const seen = new Set();
  const out = [];
  rows.forEach(row => {
    const value = row && row[key];
    if (value === null || value === undefined || value === "" || seen.has(String(value))) return;
    seen.add(String(value));
    out.push(value);
  });
  return out;
}


function _catSourceLabel(source) {
  return ({ o1g: "O-1G", sv1_l0: "S-v1 L0", sv1_l1: "S-v1 L1", v2a_full: "V2-A full", v2a_pilot: "V2-A pilot" })[source] || source;
}

function _V4CatalogNotice({ loading, error, envelopes }) {
  const bad = envelopes.find(env => env && env.available === false);
  if (loading) return <div className="research-empty mono">sealed rdc-1 카탈로그 불러오는 중…</div>;
  if (error) return <div className="research-empty danger mono">{error}</div>;
  if (bad) {
    return (
      <div className="research-empty warn mono" role="status">
        카탈로그 경로 설정 필요(P3-1 §2) · {_catUnavailableText(bad)}
      </div>
    );
  }
  return null;
}

function _V4CatalogProvenance({ assets }) {
  const rows = _catItems(assets).slice(0, 8);
  return (
    <section className="v4-catalog-provenance" aria-label="catalog provenance">
      <div className="v4-catalog-provenance-head">
        <b>provenance · /research/assets</b>
        <span className="mono">status_tag 원문 보존 · path/raw source 링크 없음</span>
      </div>
      {rows.length === 0 ? (
        <div className="v4-catalog-empty mono">자산 provenance 대기 — 집계나 기본 경로를 만들지 않습니다.</div>
      ) : (
        <div className="v4-catalog-asset-grid">
          {rows.map(asset => (
            <article className="v4-catalog-asset" key={asset.asset_id || asset.kind || asset.summary}>
              <div><b>{_catText(asset.asset_id)}</b><span className="mono">{_catText(asset.kind)}</span></div>
              <p>{_catText(asset.summary)}</p>
              <code title={_catText(asset.status_tag)}>{_catText(asset.status_tag)}</code>
              <span className="mono">commit {_catText(asset.produced_commit)} · seal {_catText(asset.seal_doc)}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function _V4CatalogV1({ judgments }) {
  const rows = _catItems(judgments);
  return (
    <section className="v4-catalog-panel v4-catalog-v1" aria-labelledby="v4-catalog-v1-heading">
      <div className="v4-catalog-panel-head">
        <div>
          <h3 id="v4-catalog-v1-heading">V1 연구 파이프라인/연혁실</h3>
          <p className="mono">/research/judgments?include_ledger=1 · 응답 순서 그대로 · 확정 판정 잠금</p>
        </div>
        <span className="v4-chip warn">재현성 게이트</span>
      </div>
      <div className="v4-catalog-empty mono">진행 중 연구는 카탈로그 확장 후 표시 — 현재는 핸드오프 문서 참조</div>
      {rows.length === 0 ? (
        <div className="v4-catalog-empty mono">judgments 데이터 없음</div>
      ) : (
        <div className="v4-catalog-timeline">
          {rows.map(j => (
            <article className="v4-catalog-judgment-card" key={j.series || j.report_path}>
              <div className="v4-catalog-card-head">
                <b>{_catText(j.series)}</b>
                <span className={"v4-chip " + _catVerdictCls(j.verdict)} title={_catText(j.verdict)}>{_catVerdictPrefix(j.verdict)}</span>
              </div>
              <p className="v4-catalog-verdict">{_catText(j.verdict)}</p>
              <dl className="v4-catalog-kv mono">
                <div><dt>lock</dt><dd>잠금 · 확정 판정 · 편집 없음</dd></div>
                <div><dt>ledger_rows</dt><dd>{Array.isArray(j.ledger_rows) ? j.ledger_rows.join(", ") : _catText(j.ledger_rows)} · n={_catText(j.n_ledger_rows)}</dd></div>
                <div><dt>report</dt><dd>{_catText(j.report_path)}</dd></div>
                <div><dt>commit</dt><dd>{_catText(j.produced_commit || j.note)}</dd></div>
                <div><dt>ga_path_flag</dt><dd>{_catFlag(j.ga_path_flag)}{j.ga_path_flag ? " · GA 경로 — 해석 주의" : ""}</dd></div>
              </dl>
              <pre className="v4-catalog-json mono">key_metrics { _catJsonPreview(j.key_metrics) }</pre>
              {Array.isArray(j.ledger) && j.ledger.length > 0 && (
                <div className="v4-catalog-ledger" data-region="scroll" tabIndex={0} aria-label={_catText(j.series) + " ledger rows"}>
                  {j.ledger.slice(0, 6).map(row => (
                    <div key={row.row_num || row.ts} className="mono">
                      #{_catText(row.row_num)} · {_catText(row.ts)} · {_catText(row.trial_type)} · {_catText(row.target)} · {_catText(row.result)}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function _V4CatalogV2({ cellsBySource }) {
  return (
    <section className="v4-catalog-panel v4-catalog-v2" aria-labelledby="v4-catalog-v2-heading">
      <div className="v4-catalog-panel-head">
        <div>
          <h3 id="v4-catalog-v2-heading">V2 함정 설명 지도</h3>
          <p className="mono">/research/cells · insufficient 회색 마스킹 · 색상은 ci_low 기준</p>
        </div>
        <span className="v4-chip warn">veto 아님</span>
      </div>
      <p className="v4-catalog-safe">FDR 생존 0 · 현재 축·온셋·비용 가정에서 평균 양EV 셀 0 — 갭+20% 추격 최악</p>
      <p className="v4-catalog-safe">현재 축·온셋 라벨은 챔피언 우위를 포착하지 못함(칸-조준 KILL — h300·L3 교차)</p>
      <div className="v4-catalog-map-list">
        {CAT_CELL_SOURCES.map(source => {
          const envelope = cellsBySource[source];
          const rows = _catItems(envelope);
          const labelTag = _catText(rows.find(row => row && row.label_tag) && rows.find(row => row && row.label_tag).label_tag);
          const rowCount = envelope && envelope.available ? _catText(envelope.count) : "—";
          return (
            <article className="v4-catalog-map" key={source}>
              <div className="v4-catalog-map-head"><b>{_catSourceLabel(source)}</b><span className="mono">count {rowCount}</span></div>
              <div className="v4-catalog-watermark" title={labelTag}>label_tag: {labelTag} · 설명 지도(veto 아님)</div>
              <div className="v4-catalog-map-grid" role="grid" aria-label={_catSourceLabel(source) + " 함정 설명 지도"}>
                {rows.slice(0, 12).map(cell => {
                  const masked = _catCellMasked(cell);
                  return (
                    <div key={cell.cell_id} className={"v4-catalog-map-cell " + _catCellTone(cell)} role="gridcell" title={masked ? "표본 부족(n<2,000) — 판정 금지" : _catText(cell.label_tag)}>
                      <b>{_catText(cell.gap_label || cell.time_label || cell.cell_id)}</b>
                      {masked ? (
                        <span>표본 부족(n&lt;2,000) — 판정 금지</span>
                      ) : (
                        <span>ci_low {_catPct(cell.ci_low)} · mean {_catPct(cell.mean_net)}</span>
                      )}
                    </div>
                  );
                })}
                {rows.length === 0 && <div className="v4-catalog-empty mono">cells 데이터 없음 · 기본 source 추정 없음</div>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function _V4CatalogV3({ clauses }) {
  const rows = _catItems(clauses);
  const counts = [
    ["load_bearing", 5], ["counter_productive", 6], ["weak_signal", 5], ["inconclusive", 4], ["none", 18],
  ];
  return (
    <section className="v4-catalog-panel v4-catalog-v3" aria-labelledby="v4-catalog-v3-heading">
      <div className="v4-catalog-panel-head">
        <div>
          <h3 id="v4-catalog-v3-heading">V3 절 실험실</h3>
          <p className="mono">39절 중 측정 38절(#39=#15 순수 중복 병합) · FDR 분모 34</p>
        </div>
        <span className="v4-chip warn">RR8_12 조건부</span>
      </div>
      <div className="v4-catalog-class-counts" aria-label="classification counts">
        {counts.map(([name, count]) => <span key={name} className="mono">{name} {count}</span>)}
      </div>
      <div className="v4-catalog-empty mono">W5 유형 분포: 데이터 없음(카탈로그 확장 대기)</div>
      {rows.length === 0 ? (
        <div className="v4-catalog-empty mono">clauses 데이터 없음</div>
      ) : (
        <div className="v4-catalog-clause-grid">
          {rows.map(clause => (
            <article className={"v4-catalog-clause " + _catText(clause.classification, "none")} key={clause.clause_num}>
              <div className="v4-catalog-card-head">
                <b>#{_catText(clause.clause_num)} { _catText(clause.text) }</b>
                <span className="mono">{_catText(clause.classification)}</span>
              </div>
              <div className="v4-catalog-watermark">RR8_12 계보 · L3 출구 조건부 · 원-임계 이식 금지</div>
              <dl className="v4-catalog-kv mono">
                <div><dt>family</dt><dd>{_catText(clause.family)} · { _catText(clause.w5_category) }</dd></div>
                <div><dt>Δ / CI / MDE</dt><dd>{_catPp(clause.delta_pp)} · {_catPp(clause.ci_low_pp)}~{_catPp(clause.ci_high_pp)} · {_catPp(clause.mde_pp)}</dd></div>
                <div><dt>n_sat/n_unsat</dt><dd>{_catText(clause.n_sat)} / {_catText(clause.n_unsat)}</dd></div>
                <div><dt>floor/fdr</dt><dd>{_catFlag(clause.floor_pass)} / {_catFlag(clause.fdr_survive)}</dd></div>
              </dl>
              <pre className="v4-catalog-json mono">year_delta { _catJsonPreview(clause.year_delta) }</pre>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function _V4CatalogV4({ cellsBySource, lookupSource, setLookupSource, lookupLabel, setLookupLabel }) {
  const fallbackSource = CAT_CELL_SOURCES.find(source => _catItems(cellsBySource[source]).length > 0) || CAT_CELL_SOURCES[0];
  const activeSource = _catItems(cellsBySource[lookupSource]).length > 0 ? lookupSource : fallbackSource;
  const sourceRows = _catItems(cellsBySource[activeSource]);
  const labelOptions = _catUnique(sourceRows, "label_kind");
  const activeLabel = labelOptions.some(v => String(v) === String(lookupLabel)) ? lookupLabel : (labelOptions[0] || "");
  const matches = activeLabel ? sourceRows.filter(row => String(row.label_kind) === String(activeLabel)) : sourceRows;
  const selected = matches[0] || null;
  const masked = _catCellMasked(selected);
  const hasL3 = selected && String(selected.label_kind) === "l3";
  return (
    <section className="v4-catalog-panel v4-catalog-v4" aria-labelledby="v4-catalog-v4-heading">
      <div className="v4-catalog-panel-head">
        <div>
          <h3 id="v4-catalog-v4-heading">V4 표본/출구 은행 조회</h3>
          <p className="mono">/research/cells 조회 전용 · 원시 parquet/json 접근 없음 · 분포 곡선 재구성 없음</p>
        </div>
      </div>
      <div className="v4-catalog-lookup">
        <label>source<select value={activeSource} onChange={event => setLookupSource(event.target.value)}>{CAT_CELL_SOURCES.map(source => <option key={source} value={source}>{_catSourceLabel(source)}</option>)}</select></label>
        <label>label_kind<select value={activeLabel} onChange={event => setLookupLabel(event.target.value)}>{labelOptions.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      </div>
      {!selected ? (
        <div className="v4-catalog-empty strong" role="status">이 조합의 사전 집계가 없습니다 — 원시 재계산은 금지되어 있습니다. 필요하면 연구 트랙에 집계 추가를 요청하십시오(사전등록 종속).</div>
      ) : (
        <article className={"v4-catalog-bank-card " + _catCellTone(selected)}>
          <div className="v4-catalog-card-head"><b>{_catText(selected.cell_id)} · {_catText(selected.source)} · {_catText(selected.label_kind)}</b><span className="mono">{masked ? "masked" : "catalog row"}</span></div>
          <div className="v4-catalog-watermark" title={_catText(selected.label_tag)}>{_catText(selected.label_tag)}{hasL3 ? " · RR8_12 출구 조건부 — 원-임계 이식 금지" : ""}</div>
          {masked ? (
            <div className="v4-catalog-empty mono">표본 부족(n&lt;2,000) — 판정 금지</div>
          ) : (
            <dl className="v4-catalog-bank-metrics mono">
              <div><dt>n</dt><dd>{_catText(selected.n)}</dd></div>
              <div><dt>mean_net</dt><dd>{_catPct(selected.mean_net)}</dd></div>
              <div><dt>median_net</dt><dd>{_catPct(selected.median_net)}</dd></div>
              <div><dt>q25/q75</dt><dd>{_catPct(selected.q25_net)} / {_catPct(selected.q75_net)}</dd></div>
              <div><dt>p_net_ge0/ge1</dt><dd>{_catPct(selected.p_net_ge0)} / {_catPct(selected.p_net_ge1)}</dd></div>
              <div><dt>CI</dt><dd>{_catPct(selected.ci_low)} ~ {_catPct(selected.ci_high)}</dd></div>
              <div><dt>MFE/MAE</dt><dd>{_catPct(selected.mfe_mean)} / {_catPct(selected.mae_mean)}</dd></div>
              <div><dt>2022/2023</dt><dd>{_catPct(selected.year2022_mean)}({_catText(selected.year2022_sign)}) / {_catPct(selected.year2023_mean)}({_catText(selected.year2023_sign)})</dd></div>
            </dl>
          )}
          <pre className="v4-catalog-json mono">extra { _catJsonPreview(selected.extra) }</pre>
        </article>
      )}
      <div className="v4-catalog-empty mono">빈 조합 계약: 이 조합의 사전 집계가 없습니다 — 원시 재계산은 금지되어 있습니다.</div>
    </section>
  );
}

function _V4CatalogV5() {
  const panels = ["30거래일 채점표", "킬스위치 소진율", "실체결 잔차", "절 발동 기록"];
  return (
    <section className="v4-catalog-panel v4-catalog-v5" aria-labelledby="v4-catalog-v5-heading">
      <div className="v4-catalog-panel-head">
        <div>
          <h3 id="v4-catalog-v5-heading">V5 B1 honest empty skeleton</h3>
          <p className="mono">B1은 오프라인 판정 불가(inconclusive·kill-2 하한 미달) 출신 — 30거래일 채점 전 어떤 성공 주장도 금지</p>
        </div>
        <span className="v4-chip off">U-4 미확정</span>
      </div>
      <div className="v4-catalog-b1-status" role="status">운용 개시 전 — 데이터 없음</div>
      <div className="v4-catalog-b1-grid">
        {panels.map(panel => (
          <article key={panel} className="v4-catalog-b1-panel">
            <b>{panel}</b>
            <span>운용 개시 전 — 데이터 없음</span>
            <em>자본 C · 합의 실현율 기준 · 기록 그릇: U-4 미확정</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function V4Catalog({ baseUrl }) {
  const [state, setState] = useState_cat({ loading: false, error: "", listedBase: "", assets: null, judgments: null, clauses: null, cellsBySource: {} });
  const [lookupSource, setLookupSource] = useState_cat("o1g");
  const [lookupLabel, setLookupLabel] = useState_cat("l3");
  const generationRef = useRef_cat(0);
  const baseRef = useRef_cat(baseUrl);
  baseRef.current = baseUrl;

  useEffect_cat(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    setState({ loading: Boolean(baseUrl), error: "", listedBase: "", assets: null, judgments: null, clauses: null, cellsBySource: {} });
    if (!baseUrl) {
      clearTimeout(timeout);
      return () => controller.abort();
    }

    const get = path => fetch(baseUrl + path, { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
    const cellRequests = CAT_CELL_SOURCES.map(source => get(_catCellsRoute(source)).then(payload => [source, payload]));

    Promise.all([get(CAT_ENDPOINTS.assets), get(CAT_ENDPOINTS.judgments), get(CAT_ENDPOINTS.clauses), Promise.all(cellRequests)])
      .then(([assetsPayload, judgmentsPayload, clausesPayload, cellPairs]) => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        const cellsBySource = {};
        cellPairs.forEach(([source, payload]) => { cellsBySource[source] = _catNormalizeEnvelope("cells:" + source, payload); });
        setState({
          loading: false,
          error: "",
          listedBase: baseUrl,
          assets: _catNormalizeEnvelope("assets", assetsPayload),
          judgments: _catNormalizeEnvelope("judgments", judgmentsPayload),
          clauses: _catNormalizeEnvelope("clauses", clausesPayload),
          cellsBySource,
        });
      })
      .catch(e => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        setState({ loading: false, error: String(e && e.message ? e.message : e), listedBase: baseUrl, assets: null, judgments: null, clauses: null, cellsBySource: {} });
      })
      .finally(() => clearTimeout(timeout));

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [baseUrl]);

  const ownsData = Boolean(baseUrl && state.listedBase === baseUrl && !state.loading);
  const cellsBySource = ownsData ? state.cellsBySource : {};
  const envelopes = [state.assets, state.judgments, state.clauses].concat(CAT_CELL_SOURCES.map(source => cellsBySource[source])).filter(Boolean);
  const catalogMtime = _catCatalogMtime(envelopes);

  return (
    <section className="v4-catalog" aria-labelledby="v4-catalog-heading">
      <h2 id="v4-catalog-heading" className="panel-hd-title">연구 카탈로그 (P4) · sealed rdc-1 Reports prototype</h2>
      <p className="v4-catalog-safe mono" role="note">Reports-owned prototype · STOM_RESEARCH_ASSETS_DB env-only · read-only SELECT(mode=ro) · 재계산/쓰기/원시조회 없음</p>
      <p className="v4-catalog-safe mono" role="note">sealed endpoints only: /research/assets · /research/judgments · /research/cells · /research/clauses · legacy summary aggregation 금지</p>
      <div className="v4-catalog-contract mono" aria-label="catalog contract metadata">
        <span>contract {CAT_CONTRACT_VERSION}</span>
        <span>catalog mtime {catalogMtime}</span>
        <span>base guarded {ownsData ? "fresh" : "pending"}</span>
        <span>cell sources {ownsData ? CAT_CELL_SOURCES.length : "—"}</span>
      </div>
      <_V4CatalogNotice loading={state.loading} error={state.error} envelopes={envelopes} />
      <_V4CatalogProvenance assets={ownsData ? state.assets : null} />
      <div className="v4-catalog-view-grid">
        <_V4CatalogV1 judgments={ownsData ? state.judgments : null} />
        <_V4CatalogV2 cellsBySource={cellsBySource} />
        <_V4CatalogV3 clauses={ownsData ? state.clauses : null} />
        <_V4CatalogV4 cellsBySource={cellsBySource} lookupSource={lookupSource} setLookupSource={setLookupSource} lookupLabel={lookupLabel} setLookupLabel={setLookupLabel} />
        <_V4CatalogV5 />
      </div>
    </section>
  );
}

Object.assign(window, { V4Catalog });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Catalog };
