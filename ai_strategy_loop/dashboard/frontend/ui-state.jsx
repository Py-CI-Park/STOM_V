/* Shared dashboard UI state primitives.
 *
 * Presentation-only helpers for empty/loading/error/demo/pending/info surfaces.  Domain fetch
 * logic stays inside owning panels; this file only standardizes the visible shell.
 */
const UI_STATE_KIND_META = {
  info: { icon: "ℹ", tone: "var(--blue)" },
  empty: { icon: "∅", tone: "var(--ink-2)" },
  loading: { icon: "◌", tone: "var(--amber)" },
  error: { icon: "!", tone: "var(--red)" },
  demo: { icon: "D", tone: "var(--violet)" },
  pending: { icon: "…", tone: "var(--amber)" },
  success: { icon: "✓", tone: "var(--teal)" },
};

function UiStateBlock({ kind = "info", title, children, detail, action, compact = false }) {
  const meta = UI_STATE_KIND_META[kind] || UI_STATE_KIND_META.info;
  return (
    <div className={"ui-state ui-state-" + kind + (compact ? " ui-state-compact" : "")}>
      <div className="ui-state-icon" style={{ color: meta.tone, borderColor: meta.tone }}>{meta.icon}</div>
      <div className="ui-state-body">
        {title && <div className="ui-state-title">{title}</div>}
        {children && <div className="ui-state-copy">{children}</div>}
        {detail && <div className="ui-state-detail mono">{detail}</div>}
      </div>
      {action && <div className="ui-state-action">{action}</div>}
    </div>
  );
}

function UiInlinePill({ tone = "info", children, title }) {
  return <span className={"ui-pill ui-pill-" + tone} title={title}>{children}</span>;
}

function WorkspaceCard({ eyebrow, title, children, badge, action, tone = "info" }) {
  return (
    <div className={"workspace-card workspace-card-" + tone}>
      <div className="workspace-card-top">
        {eyebrow && <span className="workspace-card-eyebrow mono">{eyebrow}</span>}
        {badge && <span className="workspace-card-badge mono">{badge}</span>}
      </div>
      <div className="workspace-card-title">{title}</div>
      <div className="workspace-card-copy">{children}</div>
      {action && <div className="workspace-card-action">{action}</div>}
    </div>
  );
}

function WorkspaceNav({ items = [], activeKey, onSelect }) {
  return (
    <div className="workspace-nav" role="navigation" aria-label="dashboard workspace links">
      {items.map(item => (
        <button
          type="button"
          key={item.key}
          className={"workspace-nav-item" + (item.key === activeKey ? " active" : "")}
          onClick={() => onSelect && onSelect(item.key)}
          title={item.contract || item.label}
        >
          <span className="workspace-nav-icon" aria-hidden="true">{item.icon || "•"}</span>
          <span>{item.label}</span>
          {item.badge && <span className="workspace-nav-badge mono">{item.badge}</span>}
        </button>
      ))}
    </div>
  );
}

function MetricList({ items = [] }) {
  return (
    <div className="metric-list">
      {items.map(item => (
        <div key={item.label} className="metric-list-item">
          <span className="metric-list-label">{item.label}</span>
          <b className="metric-list-value">{item.value}</b>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { UiStateBlock, UiInlinePill, WorkspaceCard, WorkspaceNav, MetricList });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { MetricList, UiInlinePill, UiStateBlock, WorkspaceCard, WorkspaceNav };
