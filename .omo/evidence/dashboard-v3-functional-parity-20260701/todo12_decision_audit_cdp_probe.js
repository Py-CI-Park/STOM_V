const fs = require('fs');
const wsUrl = process.env.CDP_WS;
const targetUrl = process.env.TARGET_URL;
const screenshotPath = process.env.SCREENSHOT_PATH;
const cdpPath = process.env.CDP_JSON_PATH;
let nextId = 1;
const pending = new Map();
function fail(message) { throw new Error(message); }
async function main() {
  const ws = new WebSocket(wsUrl);
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result || {});
    }
  };
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = () => reject(new Error('CDP websocket open failed')); });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      window.__decisionFetchCalls = [];
      window.__decisionWebSocketOpened = false;
      const nativeFetch = window.fetch;
      window.fetch = function(input, init) {
        const url = String((input && input.url) || input || '');
        if (url.includes('/decisions') || url.includes('/record_decision')) {
          window.__decisionFetchCalls.push({ url, method: String((init && init.method) || 'GET') });
        }
        return nativeFetch.apply(this, arguments);
      };
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        window.__decisionWebSocketOpened = true;
        return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
      };
      window.WebSocket.prototype = NativeWebSocket.prototype;
      Object.setPrototypeOf(window.WebSocket, NativeWebSocket);
    })();`
  });
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 1200, deviceScaleFactor: 1, mobile: true });
  await send('Page.navigate', { url: targetUrl });
  await new Promise(resolve => setTimeout(resolve, 1800));
  const expression = `(async () => {
    const api = window.DecisionAuditSurface;
    const draft = api.draftContext({ run_id: 'runP', gen_no: 0, strategy: 'StratA', verdict: 'hold', note: 'Manual audit note run_id=runP gen_no=0 strategy=StratA' });
    const payload = api.buildPayload(draft);
    const valid = api.validatePayload(payload);
    const invalid = api.validatePayload({ verdict: 'yolo', note: 'x' });
    const cancel = await api.recordAfterConfirm(payload, () => false);
    const inert = await api.recordAfterConfirm(payload, () => true);
    const validationStatus = await api.recordAfterConfirm({ verdict: '', note: 'x' }, () => true);
    return {
      viewport: 390,
      scrollWidth: document.documentElement.scrollWidth,
      hasSurface: Boolean(document.querySelector('[data-decision-audit-surface]')),
      contractCount: document.querySelectorAll('[data-decision-contract]').length,
      decisionsEndpoint: document.querySelector('[data-decisions-endpoint]')?.getAttribute('data-decisions-endpoint') || '',
      recordEndpoint: document.querySelector('[data-record-decision-endpoint]')?.getAttribute('data-record-decision-endpoint') || '',
      manualGate: document.querySelector('[data-record-decision-gate]')?.getAttribute('data-record-decision-gate') || '',
      approvalBoundary: document.querySelector('[data-approval-boundary]')?.getAttribute('data-approval-boundary') || '',
      disabledReason: document.querySelector('[data-record-decision-disabled-reason]')?.getAttribute('data-record-decision-disabled-reason') || '',
      payloadAttribute: document.querySelector('[data-record-decision-payload]')?.getAttribute('data-record-decision-payload') || '',
      emptyState: Boolean(document.querySelector('[data-decision-empty-state]')),
      draft,
      payload,
      valid,
      invalid,
      cancel,
      inert,
      validationStatus,
      decisionFetchCalls: window.__decisionFetchCalls || [],
      websocketOpened: window.__decisionWebSocketOpened === true,
    };
  })()`;
  const evaluated = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  const value = evaluated.result && evaluated.result.value;
  if (!value) fail('CDP evaluation returned no value');
  if (value.scrollWidth > 390) fail(`horizontal overflow ${value.scrollWidth}`);
  if (!value.hasSurface || value.contractCount !== 2) fail('decision audit surface or contracts missing');
  if (value.decisionsEndpoint !== '/decisions') fail('decisions endpoint missing');
  if (value.recordEndpoint !== '/record_decision') fail('record_decision endpoint missing');
  if (value.manualGate !== 'manual-confirm-required') fail('manual confirm gate missing');
  if (value.approvalBoundary !== 'separate-route') fail('approval boundary marker missing');
  if (!value.valid.ok || value.payload.verdict !== 'hold') fail('valid payload failed');
  if (value.invalid.ok !== false) fail('invalid verdict was not rejected');
  if (value.cancel.status !== 'cancelled') fail('cancel scenario did not stay cancelled');
  if (value.inert.status !== 'inert') fail('reference confirm did not stay inert');
  if (value.validationStatus.status !== 'validation-error') fail('validation failure state missing');
  if (value.decisionFetchCalls.length !== 0) fail(`reference mode used decision fetch: ${JSON.stringify(value.decisionFetchCalls)}`);
  if (value.websocketOpened) fail('decision audit opened WebSocket');
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(screenshotPath, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(cdpPath, JSON.stringify(value, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
