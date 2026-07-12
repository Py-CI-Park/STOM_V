(function () {
  const REMODEL_BASE = "/ui/remodel";
  const CANONICAL_REMAP = {
    "/ui": REMODEL_BASE + "/condition",
    "/ui/": REMODEL_BASE + "/condition",
    "/ui/evolution": REMODEL_BASE + "/condition",
    "/ui/evolution/overview": REMODEL_BASE + "/condition",
    "/ui/evolution/process": REMODEL_BASE + "/process",
    "/ui/evolution/records": REMODEL_BASE + "/history",
    "/ui/evolution/history": REMODEL_BASE + "/history",
    "/ui/evolution/lab": REMODEL_BASE + "/lab",
    "/ui/evolution/workbench": REMODEL_BASE + "/workbench",
    "/ui/evolution/verdict": REMODEL_BASE + "/audit",
    "/ui/backtest": REMODEL_BASE + "/backtest",
    "/ui/chart-replay": REMODEL_BASE + "/chart-replay",
    "/ui/simulation": REMODEL_BASE + "/chart-replay"
  };
  const ROUTE_TO_STATE = {
    "": ["evolution", "overview"],
    "condition": ["evolution", "overview"],
    "evolution": ["evolution", "overview"],
    "process": ["evolution", "process"],
    "history": ["evolution", "records"],
    "records": ["evolution", "records"],
    "lab": ["evolution", "lab"],
    "workbench": ["evolution", "workbench"],
    "audit": ["evolution", "verdict"],
    "verdict": ["evolution", "verdict"],
    "backtest": ["backtest", "overview"],
    "chart-replay": ["simulation", "overview"],
    "simulation": ["simulation", "overview"],
    "settings": ["evolution", "overview"]
  };

  function routeKeyFromLocation() {
    const path = String(window.location && window.location.pathname || "");
    if (!path.startsWith(REMODEL_BASE)) return "";
    return path.slice(REMODEL_BASE.length).replace(/^\/+/, "").split("/")[0] || "";
  }

  function seedRouteState() {
    const pair = ROUTE_TO_STATE[routeKeyFromLocation()] || ROUTE_TO_STATE[""];
    try {
      window.localStorage.setItem("stom_active_tab", pair[0]);
      window.localStorage.setItem("stom_active_evolution_tab", pair[1]);
    } catch (_) {}
  }

  function remapUrl(url) {
    if (url == null) return url;
    const raw = String(url);
    let parsed;
    try { parsed = new URL(raw, window.location.origin); } catch (_) { return url; }
    if (parsed.origin !== window.location.origin) return url;
    if (parsed.pathname.startsWith(REMODEL_BASE)) return url;
    const mapped = CANONICAL_REMAP[parsed.pathname];
    if (!mapped) return url;
    const next = mapped + parsed.search + parsed.hash;
    return raw.startsWith("http") ? window.location.origin + next : next;
  }

  function patchHistoryMethod(name) {
    const original = window.history && window.history[name];
    if (typeof original !== "function") return;
    window.history[name] = function (state, title, url) {
      return original.call(this, state, title, remapUrl(url));
    };
  }

  window.STOM_REMODEL_MODE = true;
  window.STOM_DASHBOARD_BASE_PATH = REMODEL_BASE;
  seedRouteState();
  patchHistoryMethod("pushState");
  patchHistoryMethod("replaceState");
  document.documentElement.setAttribute("data-remodel", "true");
  document.addEventListener("DOMContentLoaded", function () {
    document.body.classList.add("remodel-production-shell");
  });
})();
