/* Settings modal: renders form from /config/spec */
const { useState: useState_s, useMemo: useMemo_s, useEffect: useEffect_s } = React;

function SettingsModal({ open, onClose, onStart, configSpec, disabled }) {
  const [values, setValues] = useState_s({});

  useEffect_s(() => {
    if (!open) return;
    const init = {};
    for (const f of configSpec) init[f.name] = f.default;
    setValues(init);
  }, [open, configSpec]);

  const groups = useMemo_s(() => {
    const g = {};
    const order = ["목표/제약", "평가 스코프", "과적합 가드", "AI"];
    for (const f of configSpec) {
      const grp = f.group || "기타";
      if (!g[grp]) g[grp] = [];
      g[grp].push(f);
    }
    const sorted = [];
    for (const k of order) if (g[k]) sorted.push([k, g[k]]);
    for (const [k, v] of Object.entries(g)) if (!order.includes(k)) sorted.push([k, v]);
    return sorted;
  }, [configSpec]);

  if (!open) return null;

  const set = (name, v) => setValues(prev => ({ ...prev, [name]: v }));

  const renderField = (f) => {
    const val = values[f.name];
    const id = `cfg-${f.name}`;
    if (f.type === "boolean") {
      return (
        <div key={f.name} className="field" style={{ gridColumn: "1 / -1" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button type="button" className={`toggle ${val ? "on" : ""}`}
                    onClick={() => set(f.name, !val)}
                    aria-label={f.label}></button>
            <label htmlFor={id} style={{ marginBottom: 0, cursor: "pointer" }}
                   onClick={() => set(f.name, !val)}>
              {f.label}
            </label>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: val ? "var(--teal)" : "var(--ink-3)" }}>
              {val ? "ON" : "OFF"}
            </span>
          </div>
          {f.help && (
            <span className="help" style={{ paddingLeft: 46 }}>
              {f.help}
            </span>
          )}
        </div>
      );
    }
    if (f.type === "select" && f.options) {
      return (
        <div key={f.name} className="field">
          <label htmlFor={id}>{f.label}</label>
          <select id={id} className="select" value={val ?? ""}
                  onChange={e => set(f.name, e.target.value)}>
            {f.options.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          {f.help && <span className="help">{f.help}</span>}
        </div>
      );
    }
    // text / number
    return (
      <div key={f.name} className="field">
        <label htmlFor={id}>{f.label}</label>
        <input id={id} className="input"
               type={f.type === "number" ? "number" : "text"}
               value={val ?? ""}
               step={f.type === "number" ? "any" : undefined}
               onChange={e => {
                 const v = f.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value;
                 set(f.name, v);
               }} />
        {f.help && <span className="help">{f.help}</span>}
      </div>
    );
  };

  const submit = () => {
    // strip empty strings -> default if there was one
    const clean = {};
    for (const f of configSpec) {
      let v = values[f.name];
      if (v === "" || v === null || v === undefined) v = f.default;
      clean[f.name] = v;
    }
    onStart(clean);
  };

  return (
    <div className="modal-bd" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" style={{ width: "min(820px, calc(100vw - 32px))" }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            진화 시작 설정
            <span className="sub">목표 · 스코프 · AI 파라미터</span>
          </h2>
          <button className="btn ghost sm" onClick={onClose}>닫기</button>
        </div>
        <div className="modal-bd-content">
          {groups.map(([grp, fields]) => (
            <div key={grp} className="group">
              <div className="group-title">{grp}</div>
              <div className="field-row" style={{
                gridTemplateColumns: fields.length === 1 ? "1fr" : "1fr 1fr",
              }}>
                {fields.map(renderField)}
              </div>
            </div>
          ))}
        </div>
        <div className="modal-ft">
          <button className="btn ghost" onClick={onClose}>취소</button>
          <button className="btn primary lg" onClick={submit} disabled={disabled}>
            ▸ 진화 시작
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SettingsModal });
