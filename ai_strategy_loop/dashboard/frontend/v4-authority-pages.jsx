/* v4-authority-pages.jsx — small page wrappers that preserve legacy owners. */
import { CurrentHistoryAuthority } from "./v4-current-history-authority.jsx";
import { V4History } from "./v4-history.jsx";
import { V4Workbench } from "./v4-workbench.jsx";

function V4HistoryWithAuthority({ baseUrl, wsStatus, onNavigate }) {
  return <><CurrentHistoryAuthority baseUrl={baseUrl} onNavigate={onNavigate} surface="history" /><V4History baseUrl={baseUrl} wsStatus={wsStatus} onNavigate={onNavigate} /></>;
}

function V4WorkbenchWithAuthority({ baseUrl, wsStatus, runId, onNavigate }) {
  return <><CurrentHistoryAuthority baseUrl={baseUrl} onNavigate={onNavigate} surface="workbench" /><V4Workbench baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} /></>;
}

Object.assign(window, { V4HistoryWithAuthority, V4WorkbenchWithAuthority });
export { V4HistoryWithAuthority, V4WorkbenchWithAuthority };
