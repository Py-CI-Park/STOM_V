/* v4-workbench.jsx — V4 Workbench: Hall-of-Fame performance evidence. */
// dual-safe ESM import (esbuild bundle path). KEEP each on ONE physical line.
import { HallOfFamePanel } from "./chart.jsx";

function V4Workbench({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const connecting = wsStatus === "connecting" || wsStatus === "reconnecting";
  const surfaceState = connecting
    ? "loading"
    : isDemo
      ? "demo"
      : (wsStatus === "error" || wsStatus === "closed" || !baseUrl)
        ? "error"
        : "ready";
  const statusText = wsStatus === "reconnecting"
    ? "명예의 전당 연결이 끊겨 재연결 중입니다. 표시된 성과 근거를 최신으로 간주하지 마세요."
    : surfaceState === "loading"
      ? "전역 명예의 전당 데이터를 연결하고 있습니다."
      : surfaceState === "demo"
        ? "데모 데이터입니다. 운영 성과 근거와 분리된 전역 명예의 전당만 표시합니다."
        : surfaceState === "error"
          ? "전역 명예의 전당 데이터를 확인할 수 없습니다. 성과 판단을 보류하세요."
          : "전역 명예의 전당의 장기 성과 기준을 확인합니다.";

  return (
    <section
      className="v4-workbench v4-cjk-safe"
      aria-labelledby="v4-workbench-title"
      aria-busy={surfaceState === "loading"}
      data-state={surfaceState}
    >
      <header className="panel v4-tab-intro">
        <div className="panel-hd">
          <h2 id="v4-workbench-title" className="panel-hd-title">성과 · 장기 성과 기준과 명예의 전당</h2>
        </div>
        <div className="panel-bd">
          <p className="v4-surface-status" role="status" aria-live="polite">{statusText}</p>
          {surfaceState === "error" && (
            <p className="research-empty danger" role="alert">
              연결 오류 때문에 성과 근거가 불완전합니다. 성과 판단을 보류하세요.
            </p>
          )}
          <p id="v4-workbench-caveat" className="v4-data-caveat">
            수익률·점수는 장기 성과 기준일 뿐 미래 성과를 보장하지 않습니다. 기간, 표본 수, MDD,
            체결 비용과 표본 외 검증을 함께 확인하세요.
          </p>
          <aside className="v4-decision-blocker" aria-label="승격 결정 차단 조건">
            승격·최종 승인·운영 반영은 이 탭에서 실행되지 않습니다. 서버 검증, hard gate,
            코드·근거 해시와 사람의 최종 승인이 없으면 결정은 차단됩니다.
          </aside>
        </div>
      </header>

      <section className="v4-workbench-region v4-cjk-safe" aria-labelledby="v4-workbench-hof-title">
        <h3 id="v4-workbench-hof-title" className="stom-section-label">장기 비교 기준과 명예의 전당</h3>
        <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
      </section>
    </section>
  );
}

Object.assign(window, { V4Workbench });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Workbench };
