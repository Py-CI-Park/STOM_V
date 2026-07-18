/* runs-shared.jsx — 페이지 전역 /runs 공용 캐시·디듀프 (검토 §3.1 + 후속 §1c 교정).
 *   /runs 는 대형 페이로드(527런 ≈ 3MB)라 여러 패널이 각자 요청하면 로드당 배수 낭비다.
 *   baseUrl 별 in-flight 프로미스 공유 + 짧은 TTL 캐시로 한 페이지의 동시/근접 중복 요청을
 *   1회로 접는다. 각 호출자는 독립 runs 배열 복사본을 받아(내부 sort 등 in-place 변형에 안전)
 *   서로의 상태를 오염시키지 않는다. 반환값은 파싱된 JSON 원문({ runs, ... }).
 *
 *   §1c 교정(검토 반영):
 *   - transport timeout 은 **공용 고정 상한**(_RUNS_TRANSPORT_TIMEOUT_MS)으로, 최초 호출자의
 *     짧은 deadline(예: 3s)이 공유 fetch 를 지배(15s 소비자까지 조기 abort)하지 않게 한다.
 *   - 진행 중 promise 가 있으면 stale data 보다 **우선 합류**시켜, 종료 직후 갱신에 편승한다.
 *   - fetchRunsShared(baseUrl, { force: true }) 는 캐시를 삭제하고 새로 조회한다(런 종료 전이 등).
 */
const _RUNS_TTL_MS = 20000;
const _RUNS_TRANSPORT_TIMEOUT_MS = 15000;
const _runsCache = new Map(); // baseUrl -> { ts, promise, data }

function _cloneRuns(j) {
  if (!j || typeof j !== "object") return j;
  return { ...j, runs: Array.isArray(j.runs) ? j.runs.slice() : (j.runs || []) };
}

function fetchRunsShared(baseUrl, opts) {
  const o = opts || {};
  const key = baseUrl || "";
  if (o.force) _runsCache.delete(key);            // §1c: 강제 무효화(런 종료 등)
  const now = Date.now();
  const entry = _runsCache.get(key);
  if (entry) {
    if (entry.promise) return entry.promise.then(_cloneRuns);                      // 진행 중 우선 합류
    if (entry.data && (now - entry.ts) < _RUNS_TTL_MS) return Promise.resolve(_cloneRuns(entry.data));
  }
  const promise = fetch(key + "/runs", { signal: AbortSignal.timeout(_RUNS_TRANSPORT_TIMEOUT_MS) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
    .then(j => { _runsCache.set(key, { ts: Date.now(), promise: null, data: j }); return j; })
    .catch(err => {
      const cur = _runsCache.get(key);
      if (cur && cur.promise === promise) _runsCache.delete(key);                  // 실패 캐시 남기지 않음
      throw err;
    });
  _runsCache.set(key, { ts: now, promise, data: entry ? entry.data : null });
  return promise.then(_cloneRuns);
}

Object.assign(window, { fetchRunsShared });
// dual-safe ESM export. KEEP on ONE physical line.
export { fetchRunsShared };
