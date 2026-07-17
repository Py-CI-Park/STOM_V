/* runs-shared.jsx — 페이지 전역 /runs 공용 캐시·디듀프 (검토 §3.1).
 *   /runs 는 대형 페이로드(527런 ≈ 3MB)라 여러 패널이 각자 요청하면 로드당 배수 낭비다.
 *   baseUrl 별 in-flight 프로미스 공유 + 짧은 TTL 캐시로 한 페이지의 동시/근접 중복 요청을
 *   1회로 접는다. 각 호출자는 독립 runs 배열 복사본을 받아(내부 sort 등 in-place 변형에 안전)
 *   서로의 상태를 오염시키지 않는다. 강제 새로고침은 fetchRunsShared(baseUrl, { force: true }).
 *   반환값은 파싱된 JSON 원문({ runs, ... })이므로 호출자는 .then(j => ...) 로 바로 소비한다.
 */
const _RUNS_TTL_MS = 20000;
const _runsCache = new Map(); // baseUrl -> { ts, promise, data }

function _cloneRuns(j) {
  if (!j || typeof j !== "object") return j;
  return { ...j, runs: Array.isArray(j.runs) ? j.runs.slice() : (j.runs || []) };
}

function fetchRunsShared(baseUrl, opts) {
  const o = opts || {};
  const key = baseUrl || "";
  const now = Date.now();
  const entry = _runsCache.get(key);
  if (!o.force && entry && (now - entry.ts) < _RUNS_TTL_MS) {
    if (entry.data) return Promise.resolve(_cloneRuns(entry.data));   // 최근 완료 데이터 재사용
    if (entry.promise) return entry.promise.then(_cloneRuns);          // 진행 중 프로미스 공유
  }
  const timeoutMs = o.timeoutMs || 15000;
  const promise = fetch(key + "/runs", { signal: AbortSignal.timeout(timeoutMs) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
    .then(j => { _runsCache.set(key, { ts: Date.now(), promise: null, data: j }); return j; })
    .catch(err => {
      const cur = _runsCache.get(key);
      if (cur && cur.promise === promise) _runsCache.delete(key);      // 실패 캐시 남기지 않음
      throw err;
    });
  _runsCache.set(key, { ts: now, promise, data: entry ? entry.data : null });
  return promise.then(_cloneRuns);
}

Object.assign(window, { fetchRunsShared });
// dual-safe ESM export. KEEP on ONE physical line.
export { fetchRunsShared };
