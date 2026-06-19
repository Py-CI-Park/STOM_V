/* Settings modal: renders form from /config/spec */
const { useState: useState_s, useMemo: useMemo_s, useEffect: useEffect_s } = React;

function SettingsModal({
  open,
  onClose,
  onStart,
  configSpec,
  configSpecStatus,
  disabled,
  onGptAuthTest,
  gptAuthProbe,
}) {
  const [values, setValues] = useState_s({});

  useEffect_s(() => {
    if (!open) return;
    const init = {};
    for (const f of configSpec) init[f.name] = f.default;
    setValues(init);
  }, [open, configSpec]);

  const groups = useMemo_s(() => {
    const g = {};
    const order = ["목표/제약", "평가 스코프", "엔진 리소스", "과적합 가드", "AI"];
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
  const sourceLive = !!(configSpecStatus && configSpecStatus.live);
  const sourceLabel = sourceLive ? "LIVE /config/spec" : "DEMO/FALLBACK";
  const sourceMessage = (configSpecStatus && configSpecStatus.message) || "config spec status unavailable";

  const optionValue = (opt) => (opt && typeof opt === "object") ? opt.value : opt;
  const optionLabel = (opt) => (opt && typeof opt === "object") ? (opt.label ?? opt.value) : opt;

  const renderField = (f) => {
    const val = values[f.name];
    const id = `cfg-${f.name}`;
    const fieldType = f.type || "text";
    const boolType = fieldType === "boolean" || fieldType === "bool";
    const choices = f.options || f.choices || [];
    const help = f.help || f.description || "";
    const min = f.min ?? f.minimum;
    const max = f.max ?? f.maximum;
    const step = f.step ?? (fieldType === "number" ? "any" : undefined);

    if (boolType) {
      return (
        <div key={f.name} className="field" style={{ gridColumn: "1 / -1" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button type="button" className={`toggle ${val ? "on" : ""}`}
                    onClick={() => set(f.name, !val)}
                    aria-label={f.label}
                    title={help}></button>
            <label htmlFor={id} style={{ marginBottom: 0, cursor: "pointer" }}
                   onClick={() => set(f.name, !val)}
                   title={help}>
              {f.label}
            </label>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: val ? "var(--teal)" : "var(--ink-3)" }}>
              {val ? "ON" : "OFF"}
            </span>
          </div>
          {help && <span className="help" style={{ paddingLeft: 46 }}>{help}</span>}
        </div>
      );
    }

    if (fieldType === "select" && choices.length) {
      const numericChoices = choices.every(opt => typeof optionValue(opt) === "number");
      return (
        <div key={f.name} className="field">
          <label htmlFor={id} title={help}>{f.label}</label>
          <select id={id} className="select" value={val ?? ""}
                  title={help}
                  onChange={e => set(f.name, numericChoices ? Number(e.target.value) : e.target.value)}>
            {choices.map(opt => {
              const ov = optionValue(opt);
              return <option key={String(ov)} value={ov}>{optionLabel(opt)}</option>;
            })}
          </select>
          {help && <span className="help">{help}</span>}
        </div>
      );
    }

    return (
      <div key={f.name} className="field">
        <label htmlFor={id} title={help}>{f.label}</label>
        <input id={id} className="input"
               type={fieldType === "number" ? "number" : (fieldType === "date" ? "date" : "text")}
               value={val ?? ""}
               min={min}
               max={max}
               step={step}
               placeholder={f.placeholder || ""}
               title={help}
               onChange={e => {
                 const raw = e.target.value;
                 const v = fieldType === "number" ? (raw === "" ? "" : Number(raw)) : raw;
                 set(f.name, v);
               }} />
        {help && <span className="help">{help}</span>}
      </div>
    );
  };

  const submit = () => {
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
      <div className="modal" style={{ width: "min(920px, calc(100vw - 32px))" }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            진화 시작 설정
            <span className="sub">목표 · 백테스트 기간 · AI/GPT 인증 · 리소스 · 시드</span>
          </h2>
          <button className="btn ghost sm" onClick={onClose}>닫기</button>
        </div>

        <div className="modal-bd-content">
          <div className="group">
            <div className="group-title">설정 원본과 공식</div>
            <div className="field-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
              <div className="field" style={{ gridColumn: "1 / -1" }}>
                <label>설정 원본</label>
                <div className={`pill ${sourceLive ? "ok" : "warn"}`} style={{ width: "fit-content" }}>
                  {sourceLabel}
                </div>
                <span className="help">
                  {sourceMessage}. LIVE 진화 시작은 `/config/spec`가 정상 로드된 뒤에만 허용됩니다.
                </span>
              </div>
              <div className="field">
                <label>목표 적합도 공식</label>
                <span className="help">
                  winner_score가 목표 적합도 이상이면 졸업합니다. risk_adjusted=Calmar×우상향R²,
                  multi=Calmar·R²·일평균거래·payoff 평균입니다.
                </span>
              </div>
              <div className="field">
                <label>GPT auth 연결 테스트</label>
                <button type="button" className="btn ghost sm" onClick={onGptAuthTest} disabled={!onGptAuthTest}>
                  GPT 5.5 xhigh 테스트
                </button>
                <span className="help">
                  진화 시작, 내보내기, 주문 없이 로컬 GPT OAuth 프록시 응답만 점검합니다.
                  {gptAuthProbe ? ` 최근 결과: ${gptAuthProbe.status || "unknown"} ${gptAuthProbe.message || gptAuthProbe.reason || ""}` : ""}
                </span>
              </div>
            </div>
          </div>

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
          <span className="help" style={{ marginRight: "auto" }}>
            빈 시작일/종료일은 DB 최소/최대 거래일을 자동 사용합니다. MDD 상한은 최대 40%입니다.
          </span>
          <button className="btn ghost" onClick={onClose}>취소</button>
          <button className="btn primary lg" onClick={submit} disabled={disabled}>
            진화 시작
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SettingsModal });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { SettingsModal };
