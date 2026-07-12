function _bindReplayKeydown(active, eventTarget, onKey) {
  if (!active || !eventTarget || typeof eventTarget.addEventListener !== "function") return () => {};
  eventTarget.addEventListener("keydown", onKey);
  return () => eventTarget.removeEventListener("keydown", onKey);
}

function _isReplayEditableTarget(target) {
  if (!target) return false;
  const tag = String(target.tagName || "").toUpperCase();
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable) return true;
  return typeof target.closest === "function" && !!target.closest('[contenteditable]:not([contenteditable="false"])');
}

function _resolveReplayDisplayState(selectedRun, fetchedRunState, archiveError, liveState) {
  if (!selectedRun) {
    return { mode: "live", displayState: liveState, error: "", loading: false };
  }
  if (archiveError) {
    return { mode: "archive", displayState: null, error: archiveError, loading: false };
  }
  if (!fetchedRunState) {
    return { mode: "archive", displayState: null, error: "", loading: true };
  }
  return { mode: "archive", displayState: fetchedRunState, error: "", loading: false };
}

function _exactReplayTimestamp(value) {
  const timestamp = Number(value);
  if (!Number.isInteger(timestamp) || timestamp < 0 || timestamp > 235959) return null;
  const hours = Math.floor(timestamp / 10000);
  const minutes = Math.floor(timestamp / 100) % 100;
  const seconds = timestamp % 100;
  return hours < 24 && minutes < 60 && seconds < 60 ? timestamp : null;
}

export { _bindReplayKeydown, _isReplayEditableTarget, _resolveReplayDisplayState, _exactReplayTimestamp };
