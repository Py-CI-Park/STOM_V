/* Evidence-first sell proposal cards. Drafts are never saved automatically. */
function BtConditionProposals({ proposals }) {
  const rows = (proposals && proposals.proposals) || [];
  if (!rows.length) return <div className="tp-empty">분석을 완료한 뒤 후보를 생성하세요. 근거가 부족하면 후보를 만들지 않습니다.</div>;
  const copy = code => { try { navigator.clipboard.writeText(code); } catch (error) {} };
  return (
    <div className="tp-proposal-grid">
      {rows.map(row => <article className="tp-proposal" key={row.proposal_id}>
        <header><div><b>{row.title}</b><small>{row.intent}</small></div><span className="tp-authority advisory">자문</span></header>
        <pre>{row.stom_code}</pre>
        <dl><dt>근거</dt><dd>{row.evidence}</dd><dt>반증</dt><dd>{row.counterevidence}</dd><dt>위험</dt><dd>{row.risk}</dd></dl>
        <button className="btn ghost sm" onClick={() => copy(row.stom_code)}>초안 복사 · 자동 저장 안 함</button>
      </article>)}
    </div>
  );
}

Object.assign(window, { BtConditionProposals });
export { BtConditionProposals };
