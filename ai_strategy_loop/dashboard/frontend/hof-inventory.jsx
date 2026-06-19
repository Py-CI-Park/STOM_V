/* Hall-of-Fame inventory gate.
 *
 * This is deliberately an inventory, not a merge.  Any future HoF consolidation must keep every
 * listed field/action or add an explicit migration and test.
 */
const HOF_INVENTORY_FIELDS = [
  { key: "kind", label: "구분", source: "human.kind / ai.kind", obligation: "인간·시드·AI 구분 유지" },
  { key: "name", label: "이름", source: "label/name", obligation: "표시명 및 전략 식별 유지" },
  { key: "total_return_krw", label: "총수익금", source: "total_return_krw", obligation: "원 단위 성과 비교 유지" },
  { key: "total_return_pct", label: "총수익률", source: "total_return_pct", obligation: "운영금 대비 수익률 유지" },
  { key: "annual_return_pct", label: "연평균", source: "annual_return_pct + annual_unreliable", obligation: "단기 연환산 신뢰 경고 유지" },
  { key: "mdd_pct", label: "MDD", source: "mdd_pct", obligation: "손실위험 비교 유지" },
  { key: "payoff", label: "payoff", source: "payoff", obligation: "손익비 비교 유지" },
  { key: "daily_avg_trades", label: "일평균거래", source: "daily_avg_trades", obligation: "빈도/체결 현실성 판단 유지" },
  { key: "max_hold", label: "동시보유", source: "_maxHold <- human.max_holdings / ai.max_hold_count", obligation: "인간/AI 필드 정규화 유지" },
  { key: "operating_capital_krw", label: "운영금", source: "operating_capital_krw", obligation: "운영금 대비 비교 유지" },
  { key: "period", label: "백테 기간", source: "start/end/days", obligation: "기간과 표본 길이 유지" },
  { key: "screenshots", label: "스크린샷", source: "ReferenceGallery", obligation: "인간 결과 증거 갤러리 유지" },
  { key: "workbench_actions", label: "워크벤치 액션", source: "ResearchProPanel", obligation: "분석 프로의 편집/즉시 백테스트 책임 분리 유지" },
];

const HOF_FIELD_GROUPS = [
  { key: "identity", label: "정체성", fields: ["kind", "name", "period"] },
  { key: "return", label: "성과", fields: ["total_return_krw", "total_return_pct", "annual_return_pct"] },
  { key: "risk", label: "위험·체결", fields: ["mdd_pct", "payoff", "daily_avg_trades", "max_hold", "operating_capital_krw"] },
  { key: "evidence", label: "증거·액션", fields: ["screenshots", "workbench_actions"] },
];

const HOF_WORKBENCH_ACTIONS = [
  "조건 후보 열기",
  "즉시 백테스트 연결",
  "HoF 비교 기준 확인",
  "인간 reference screenshot 확인",
];

const HOF_MERGE_GATE_RULES = [
  "No HoF component merge before every inventory field has an assertion.",
  "Human, seed, and AI rows must remain visually distinguishable.",
  "Short-window annualization must keep the reliability warning.",
  "Reference screenshots and Research Pro workbench actions must not be hidden by benchmark-table cleanup.",
];

function HofInventoryGate({ compact = false }) {
  const covered = HOF_INVENTORY_FIELDS.length;
  return (
    <div className={"hof-inventory-gate" + (compact ? " compact" : "")}>
      <div className="hof-inventory-head">
        <div>
          <div className="hof-inventory-kicker mono">HOF FIELD CONTRACT</div>
          <b>명예의 전당 병합 전 인벤토리 게이트</b>
        </div>
        <span className="hof-inventory-count mono">{covered} fields locked</span>
      </div>
      <div className="hof-inventory-copy">
        이 표면은 벤치마크 성과판입니다. 시각 통합 전 아래 필드와 액션이 모두 보존되어야 하며,
        분석 프로 워크벤치 책임과 인간 reference 증거를 섞어 잃으면 안 됩니다.
      </div>
      <div className="hof-inventory-actions">
        {HOF_WORKBENCH_ACTIONS.map(action => <span key={action}>{action}</span>)}
      </div>
      {!compact && (
        <>
          <div className="hof-inventory-groups">
            {HOF_FIELD_GROUPS.map(group => (
              <div key={group.key}>
                <b>{group.label}</b>
                <small>{group.fields.join(" · ")}</small>
              </div>
            ))}
          </div>
          <div className="hof-inventory-grid">
            {HOF_INVENTORY_FIELDS.map(field => (
              <div key={field.key} className="hof-inventory-field">
                <span className="mono">{field.key}</span>
                <b>{field.label}</b>
                <small>{field.obligation}</small>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

Object.assign(window, { HOF_INVENTORY_FIELDS, HOF_FIELD_GROUPS, HOF_WORKBENCH_ACTIONS, HOF_MERGE_GATE_RULES, HofInventoryGate });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { HOF_INVENTORY_FIELDS, HOF_FIELD_GROUPS, HOF_WORKBENCH_ACTIONS, HOF_MERGE_GATE_RULES, HofInventoryGate };
