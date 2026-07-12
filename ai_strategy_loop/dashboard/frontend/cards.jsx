/* Best & Winner cards + Approval dialog */
const { useState: useState_card, useEffect: useEffect_card } = React;

function BestCard({ best, onViewCode }) {
  return (
    <div className="panel" style={{ borderColor: best ? "rgba(76,214,179,0.25)" : undefined }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          Best (graded)
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          현재 누적 최고 점수
        </span>
      </div>
      <div className="panel-bd">
        {!best ? (
          <div style={{ color: "var(--ink-3)", fontSize: 12, padding: "12px 0" }}>
            아직 평가된 세대가 없습니다
          </div>
        ) : (
          <>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 14 }}>
              <span className="stat-value lg mono" style={{ color: "var(--teal)" }}>
                {fmtScore(best.graded_score)}
              </span>
              <span className="mono" style={{ fontSize: 12, color: "var(--ink-2)" }}>
                gen_{String(best.gen).padStart(2, "0")}
              </span>
              {best.gate_passed && (
                <span className="pill gate-pass" style={{ marginLeft: "auto" }}>✓ 게이트</span>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
              <NameRow label="매수" value={best.buy_name} />
              <NameRow label="매도" value={best.sell_name} />
            </div>
            {onViewCode && (
              <button className="btn ghost sm" onClick={() => onViewCode(best.gen)}
                      style={{ width: "100%", justifyContent: "center" }}>
                &lt;/&gt; 코드 보기 — gen_{String(best.gen).padStart(2, "0")}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function WinnerCard({ winner, onApprove, onViewCode }) {
  if (!winner) {
    return (
      <div className="panel" style={{ borderStyle: "dashed", borderColor: "var(--line-2)" }}>
        <div className="panel-hd">
          <div className="panel-hd-title">
            <span className="dot"></span>Winner — 게이트 통과 대기
          </div>
        </div>
        <div className="panel-bd" style={{ color: "var(--ink-3)", fontSize: 12 }}>
          하드 게이트를 통과한 전략이 아직 없습니다.
          <div style={{ marginTop: 6, fontSize: 11, color: "var(--ink-3)" }}>
            target_score 이상 + MDD 상한 이내 + 일평균 거래 하한 이상
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="panel" style={{
      borderColor: "rgba(165,148,255,0.35)",
      background: "linear-gradient(180deg, rgba(165,148,255,0.06), var(--bg-1) 70%)",
    }}>
      <div className="panel-hd" style={{ background: "rgba(165,148,255,0.08)", borderBottom: "1px solid rgba(165,148,255,0.18)" }}>
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          🏆 Winner — 하드 게이트 통과
        </div>
        <span className="badge" style={{ color: "var(--violet)", borderColor: "rgba(165,148,255,0.32)", background: "rgba(165,148,255,0.08)" }}>
          gen_{String(winner.gen).padStart(2, "0")}
        </span>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 14 }}>
          <span className="stat-value lg mono" style={{ color: "var(--violet)" }}>
            {fmtScore(winner.score)}
          </span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
            graded_score
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 }}>
          <NameRow label="매수" value={winner.buy_name} />
          <NameRow label="매도" value={winner.sell_name} />
        </div>
        {onViewCode && (
          <button className="btn ghost sm" onClick={() => onViewCode(winner.gen)}
                  style={{ width: "100%", justifyContent: "center", marginBottom: 10 }}>
            &lt;/&gt; 전체 코드 검토
          </button>
        )}
        <button className="btn primary lg" style={{ width: "100%", justifyContent: "center" }}
                onClick={onApprove}>
          <span>연구 산출물 승인 · Export</span>
          <span style={{ fontSize: 12, opacity: 0.8 }}>→</span>
        </button>
        <p style={{ fontSize: 11, color: "var(--ink-2)", marginTop: 10, lineHeight: 1.55, textAlign: "center" }}>
          Human Approval Gate 통과 후 연구 결과로만 export됩니다.
          실거래/주문/계좌/브로커 연동은 없습니다.
        </p>
      </div>
    </div>
  );
}

// #65 P1 — Best/Winner 통합 카드. best.gen===winner.gen이면(게이트 통과한 best가
//   곧 winner) 두 카드가 같은 세대를 중복 표기하므로 한 카드로 병합한다. graded(best)와
//   score(winner)를 동시에 보여주고, 승인·코드보기 액션을 그대로 노출한다. App이 분기해
//   호출한다(다르면 기존 BestCard+WinnerCard 2카드 유지=하위호환).
function MergedBestWinnerCard({ best, winner, onApprove, onViewCode }) {
  const gen = winner.gen;
  return (
    <div className="panel" style={{
      borderColor: "rgba(165,148,255,0.35)",
      background: "linear-gradient(180deg, rgba(165,148,255,0.06), var(--bg-1) 70%)",
    }}>
      <div className="panel-hd" style={{ background: "rgba(165,148,255,0.08)", borderBottom: "1px solid rgba(165,148,255,0.18)" }}>
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          🏆 Best = Winner — 게이트 통과 최고 세대
        </div>
        <span className="badge" style={{ color: "var(--violet)", borderColor: "rgba(165,148,255,0.32)", background: "rgba(165,148,255,0.08)" }}>
          gen_{String(gen).padStart(2, "0")}
        </span>
      </div>
      <div className="panel-bd">
        {/* graded(best) + score(winner) 동시 표기 */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 4, flexWrap: "wrap" }}>
          <span className="stat-value lg mono" style={{ color: "var(--teal)" }}>
            {fmtScore(best.graded_score)}
          </span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>graded</span>
          <span className="stat-value mono" style={{ color: "var(--violet)", marginLeft: 6 }}>
            {fmtScore(winner.score)}
          </span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>winner_score</span>
          <span className="pill gate-pass" style={{ marginLeft: "auto" }}>✓ 게이트</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "12px 0 14px" }}>
          <NameRow label="매수" value={winner.buy_name} />
          <NameRow label="매도" value={winner.sell_name} />
        </div>
        {onViewCode && (
          <button className="btn ghost sm" onClick={() => onViewCode(gen)}
                  style={{ width: "100%", justifyContent: "center", marginBottom: 10 }}>
            &lt;/&gt; 전체 코드 검토 — gen_{String(gen).padStart(2, "0")}
          </button>
        )}
        <button className="btn primary lg" style={{ width: "100%", justifyContent: "center" }}
                onClick={onApprove}>
          <span>연구 산출물 승인 · Export</span>
          <span style={{ fontSize: 12, opacity: 0.8 }}>→</span>
        </button>
        <p style={{ fontSize: 11, color: "var(--ink-2)", marginTop: 10, lineHeight: 1.55, textAlign: "center" }}>
          Human Approval Gate 통과 후 연구 결과로만 export됩니다.
          실거래/주문/계좌/브로커 연동은 없습니다.
        </p>
      </div>
    </div>
  );
}

function NameRow({ label, value }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "7px 10px",
      background: "var(--bg-0)",
      border: "1px solid var(--line-1)",
      borderRadius: 5,
    }}>
      <span style={{ fontSize: 10.5, letterSpacing: ".14em", textTransform: "uppercase", color: "var(--ink-2)", width: 36 }}>
        {label}
      </span>
      <span className="mono" style={{ fontSize: 12, color: "var(--ink-0)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {value || "—"}
      </span>
    </div>
  );
}

// -------- Approval Dialog --------
function ApprovalDialog({ winner, onClose, onConfirm }) {
  const [userBuy, setUserBuy] = useState_card("");
  const [userSell, setUserSell] = useState_card("");
  const [confirmText, setConfirmText] = useState_card("");

  useEffect_card(() => {
    if (winner) {
      // suggest stripped versions
      const stripGen = (n) => (n || "").replace(/_g\d+$/, "");
      setUserBuy(stripGen(winner.buy_name) || "");
      setUserSell(stripGen(winner.sell_name) || "");
      setConfirmText("");
    }
  }, [winner]);

  if (!winner) return null;
  const canSubmit = userBuy.trim() && userSell.trim() && confirmText.trim() === "승인";

  return (
    <div className="modal-bd" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            연구 산출물 승인 · Export
            <span className="sub">gen_{String(winner.gen).padStart(2, "0")} · score {fmtScore(winner.score)}</span>
          </h2>
          <button className="btn ghost sm" onClick={onClose}>닫기</button>
        </div>
        <div className="modal-bd-content">
          <div className="alert-danger" style={{ marginBottom: 18 }}>
            <strong>⚠ Human Approval Gate</strong> — 이 우승 전략은 연구 산출물로만 export됩니다.
            실거래 주문, 브로커 로그인, 계좌/자산 연동, 자동매매 배포는 수행하지 않습니다.
          </div>

          {/* P2 결정 동선 크로스링크: 내보내기 승인(WS final_approval)과 운용 결정 기록
              (REST /record_decision)을 한 흐름으로 안내. 라우트 무변경(모달 — 기본 스냅샷 밖). */}
          <div className="mono" style={{ marginBottom: 14, fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5 }}>
            동선: 증거 → <b>내보내기 승인</b>(이 단계 · WS <span className="mono">final_approval</span>) →
            <b> 결정 이력 → 운용 결정</b> 탭에서 채택 사유 기록(REST <span className="mono">/record_decision</span>, append-only).
          </div>

          <div className="group">
            <div className="group-title">우승 전략 원본</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <NameRow label="매수" value={winner.buy_name} />
              <NameRow label="매도" value={winner.sell_name} />
            </div>
          </div>

          <div className="group">
            <div className="group-title">연구 Export 저장명 — 사용자 지정</div>
            <div className="field-row">
              <div className="field">
                <label>매수 전략 이름</label>
                <input className="input" value={userBuy} onChange={e => setUserBuy(e.target.value)}
                       placeholder="예: VWAP_MOMENTUM_v3" />
                <span className="help">연구 결과와 감사 기록에서 이 이름으로 참조됩니다</span>
              </div>
              <div className="field">
                <label>매도 전략 이름</label>
                <input className="input" value={userSell} onChange={e => setUserSell(e.target.value)}
                       placeholder="예: ATR_TRAILING_v3" />
                <span className="help">중복 시 연구 Export 후보명이 갱신됩니다</span>
              </div>
            </div>
          </div>

          <div className="group">
            <div className="group-title">최종 확인</div>
            <div className="field">
              <label>아래 입력란에 <span className="mono" style={{ color: "var(--amber)" }}>승인</span> 이라고 입력하세요</label>
              <input className="input" value={confirmText} onChange={e => setConfirmText(e.target.value)}
                     placeholder="승인" autoFocus />
            </div>
          </div>
        </div>
        <div className="modal-ft">
          <button className="btn ghost" onClick={onClose}>취소</button>
          <button className="btn primary" disabled={!canSubmit}
                  onClick={() => onConfirm({ userBuy: userBuy.trim(), userSell: userSell.trim() })}>
            승인 · 내보내기
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ApprovalDialog, BestCard, MergedBestWinnerCard, WinnerCard };
