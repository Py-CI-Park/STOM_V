/* 페이지 25 — 분석 카드 뷰어 (마스터 웨이브 W1).
   부검이 산출한 근본원인·변이축을 화면에서 볼 수 있게 한다. 이전에는 카드가
   AI 프롬프트로만 흘러 아무도 볼 수 없었다(감사 결함 #5).

   권한 계약: 관측 전용. 승인·승격 버튼을 두지 않는다 — 자율 루프의 수정 결정은
   Claude 가 같은 카드를 읽고 내린다(사람 검토 단계가 아니다).
   전역 이름 충돌 방지를 위해 BtCard* 접두를 쓴다. */

const { useState: useState_ac, useEffect: useEffect_ac, useCallback: useCallback_ac } = React;

function btCardGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function btCardNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

/* 정직 라벨 — 모든 섹션은 status('ok'|'insufficient_data')를 가진다. */
function BtCardStatus({ status, note }) {
  if (status === "ok") return null;
  return <p className="tp-next-hint" role="note">데이터 부족 — {note || "이 섹션은 표본이 모자라 계산하지 않았습니다."}</p>;
}

function BtCardSection({ title, section, children, hint }) {
  const status = section && section.status;
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">{title}</div>
        {hint && <small className="v4s-en">{hint}</small>}</div>
      <div className="panel-bd">
        <BtCardStatus status={status} note={section && section.note}/>
        {status === "ok" ? children : null}
      </div>
    </section>
  );
}

/* 근본원인 — 카드의 결론. 자율 루프가 다음 수정 지점을 여기서 고른다. */
function BtCardRootCause({ card }) {
  const root = (card && card.root_cause) || {};
  const items = root.items || root.causes || [];
  const axis = (card && card.mutation_axis) || {};
  const axes = axis.items || axis.axes || [];
  return (
    <BtCardSection title="근본원인 · 변이축" section={root}
                   hint="다음 수정 1절이 여기서 나온다">
      {items.length === 0 && <p className="v4s-note">보고된 근본원인이 없습니다.</p>}
      <ol className="tp-cause-list">
        {items.map((item, index) => (
          <li key={index}>
            <b>{item.title || item.kind || `원인 ${index + 1}`}</b>
            {item.detail && <span> — {item.detail}</span>}
            {item.evidence && <small className="mono"> · 근거 {String(item.evidence)}</small>}
          </li>
        ))}
      </ol>
      {axes.length > 0 && <>
        <h4>변이축 (수정 후보)</h4>
        <ul className="tp-cause-list">
          {axes.map((item, index) => <li key={index}><span className="badge">{item.axis || item.kind || "축"}</span> {item.detail || item.hint || ""}</li>)}
        </ul>
      </>}
    </BtCardSection>
  );
}

/* 승/패 판별력 — Cohen's d + FDR. 어느 지표가 이기고 지는 거래를 가르는가. */
function BtCardFeatures({ card }) {
  const section = (card && card.feature_importance) || {};
  const rows = section.features || section.items || [];
  return (
    <BtCardSection title="승·패 판별 지표" section={section} hint="Cohen's d · FDR 보정">
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>지표</th><th className="num">승자 평균</th><th className="num">패자 평균</th><th className="num">효과크기 d</th><th className="num">q</th></tr></thead>
          <tbody>
            {rows.slice(0, 20).map((row, index) => (
              <tr key={index}>
                <td>{row.feature || row.name}</td>
                <td className="num mono">{btCardNum(row.winner_mean, 3)}</td>
                <td className="num mono">{btCardNum(row.loser_mean, 3)}</td>
                <td className="num mono">{btCardNum(row.cohens_d, 3)}</td>
                <td className="num mono">{btCardNum(row.q_value !== undefined ? row.q_value : row.qvalue, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </BtCardSection>
  );
}

/* 손실이 몰린 구역 / 이익이 몰린 구역 — 시간대 × 시총. */
function BtCardZones({ card }) {
  const avoid = (card && card.avoid_zones) || {};
  const prefer = (card && card.prefer_zones) || {};
  const render = (section, label) => {
    const rows = section.zones || section.items || [];
    return (
      <div>
        <h4>{label}</h4>
        <BtCardStatus status={section.status} note={section.note}/>
        {section.status === "ok" && (
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>구역</th><th className="num">표본</th><th className="num">평균 수익률</th></tr></thead>
              <tbody>
                {rows.slice(0, 12).map((row, index) => (
                  <tr key={index}>
                    <td className="mono">{row.segment || row.cell || row.label}</td>
                    <td className="num mono">{btCardNum(row.n || row.samples)}</td>
                    <td className={"num mono " + (Number(row.mean_return || row.mean) >= 0 ? "pos" : "neg")}>
                      {btCardNum(row.mean_return !== undefined ? row.mean_return : row.mean, 3)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  };
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">구역 대조 (피할 곳 · 선호할 곳)</div>
        <small className="v4s-en">시간대 × 시총</small></div>
      <div className="panel-bd v4s-probe-grid">{render(avoid, "손실 집중")}{render(prefer, "이익 집중")}</div>
    </section>
  );
}

/* MFE/MAE·엣지비 — 청산 축 개선 여지를 보는 곳. */
function BtCardEdge({ card }) {
  const mfeMae = (card && card.mfe_mae) || {};
  const edge = (card && card.edge_ratio) || {};
  return (
    <BtCardSection title="MFE · MAE · 엣지비" section={mfeMae}
                   hint="청산 축(매도 규칙) 개선 여지">
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>평균 MFE</b><span className="mono">{btCardNum(mfeMae.mean_mfe, 3)}%</span></div>
        <div className="v4s-probe-card"><b>평균 MAE</b><span className="mono">{btCardNum(mfeMae.mean_mae, 3)}%</span></div>
        <div className="v4s-probe-card"><b>엣지비 (MFE/|MAE|)</b><span className="mono">{btCardNum(edge.value !== undefined ? edge.value : edge.edge_ratio, 3)}</span></div>
      </div>
      <p className="v4s-note">엣지비가 1보다 크면 “먹을 수 있었던 폭”이 “맞은 폭”보다 크다는 뜻이다 —
        진입은 맞았고 <b>청산이 늦거나 이르다</b>는 신호일 수 있다.</p>
    </BtCardSection>
  );
}

/* 손실 거래 목록 — 숫자를 실제 거래로 확인한다. */
function BtCardLosers({ baseUrl, jobId }) {
  const [rows, setRows] = useState_ac([]);
  const [error, setError] = useState_ac("");
  useEffect_ac(() => {
    if (!jobId) return;
    btCardGet(baseUrl, `/bt/analysis-card/losers?job_id=${encodeURIComponent(jobId)}&limit=20`)
      .then((d) => { if (d && d.available) setRows(d.rows || []); else setError((d && d.reason) || "손실 거래를 불러오지 못했습니다."); })
      .catch(() => setError("손실 거래 요청 실패"));
  }, [baseUrl, jobId]);
  if (error) return <p className="tp-error" role="alert">{error}</p>;
  if (rows.length === 0) return null;
  const columns = Object.keys(rows[0]);
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">최악 손실 거래 20건</div>
        <small className="v4s-en">근본원인을 눈으로 확인</small></div>
      <div className="panel-bd">
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>{columns.map((c) => <td key={c} className="mono">{row[c] === null ? "—" : String(row[c])}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export function BtAnalysisCardTab({ baseUrl, jobId }) {
  const [payload, setPayload] = useState_ac(null);
  const [error, setError] = useState_ac("");
  const [loading, setLoading] = useState_ac(false);

  const load = useCallback_ac(() => {
    if (!jobId) { setError("완료된 백테스트 job 을 먼저 선택하세요."); return; }
    setLoading(true); setError("");
    btCardGet(baseUrl, `/bt/analysis-card?job_id=${encodeURIComponent(jobId)}`)
      .then((d) => {
        setLoading(false);
        if (d && d.available) setPayload(d);
        else setError(`카드를 만들 수 없습니다 — ${(d && d.reason) || "알 수 없는 이유"}`);
      })
      .catch(() => { setLoading(false); setError("분석 카드 요청 실패"); });
  }, [baseUrl, jobId]);

  useEffect_ac(() => { if (jobId) load(); }, [jobId, load]);

  const card = payload && payload.card;
  return (
    <div className="bt-analysis-card" aria-label="분석 카드 뷰어 (페이지 25)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">분석 카드 v2 <small className="v4s-en">페이지 25 · 관측 전용</small></div>
          <span className="badge warn" title="연구 분석 전용 카드입니다. 승격·실전 권한이 없습니다.">research_analysis_card_only</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">백테스트 결과의 <b>근본원인</b>과 <b>변이축</b>을 한 화면에서 봅니다.
            자율 루프는 같은 카드를 읽어 다음 수정 1절을 결정합니다 — 이 화면은 그 판단을 관측하기 위한 것입니다.</p>
          <div className="v4s-log-controls">
            <button className="btn primary sm" type="button" onClick={load} disabled={loading || !jobId}>
              {loading ? "카드 생성 중…" : "분석 카드 열기"}</button>
            {payload && <span className="mono" style={{ fontSize: 11.5 }}>
              거래 {btCardNum(payload.trade_count)}건 · {payload.cached ? "캐시" : "새로 계산"}</span>}
          </div>
          {error && <p className="tp-error" role="alert">{error}</p>}
        </div>
      </div>
      {card && <>
        <BtCardRootCause card={card}/>
        <BtCardEdge card={card}/>
        <BtCardFeatures card={card}/>
        <BtCardZones card={card}/>
        <BtCardLosers baseUrl={baseUrl} jobId={jobId}/>
      </>}
    </div>
  );
}
