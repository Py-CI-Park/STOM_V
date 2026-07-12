const fs = require('fs');
const wsUrl = process.env.CDP_WS;
const baseUrl = process.env.BASE_URL;
const outDir = process.env.EVIDENCE_DIR;
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
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) {
      const detail = result.exceptionDetails.exception && result.exceptionDetails.exception.description;
      fail(detail || result.exceptionDetails.text || 'Runtime.evaluate exception');
    }
    return result.result && result.result.value;
  }
  async function navigate(path, width, height, mobile) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });
    await send('Page.navigate', { url: `${baseUrl}${path}` });
    await new Promise(resolve => setTimeout(resolve, 1600));
  }
  async function screenshot(name) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    fs.writeFileSync(`${outDir}/${name}`, Buffer.from(shot.data, 'base64'));
  }
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      window.__todo15FetchCalls = [];
      window.__todo15WebSocketCalls = [];
      const nativeFetch = window.fetch;
      window.fetch = function(input, init) {
        window.__todo15FetchCalls.push({ url: String((input && input.url) || input || ''), method: String((init && init.method) || 'GET') });
        return nativeFetch.apply(this, arguments);
      };
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        window.__todo15WebSocketCalls.push(String(url));
        return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
      };
      window.WebSocket.prototype = NativeWebSocket.prototype;
      Object.setPrototypeOf(window.WebSocket, NativeWebSocket);
    })();`
  });
  const deepLinks = ['condition', 'process', 'history', 'lab', 'workbench', 'audit', 'backtest', 'chart-replay'];
  const results = [];
  for (const viewport of [
    { name: 'desktop', width: 1440, height: 900, mobile: false },
    { name: 'mobile', width: 390, height: 844, mobile: true },
  ]) {
    for (const leaf of deepLinks) {
      await navigate(`/ui/remodel/${leaf}?demo=reference`, viewport.width, viewport.height, viewport.mobile);
      const value = await evaluate(`(() => ({
        leaf: '${leaf}',
        viewport: '${viewport.name}',
        scrollWidth: document.documentElement.scrollWidth,
        bodyTextLength: document.body.innerText.length,
        h2: document.querySelector('h2')?.textContent || '',
        workflowSteps: document.querySelectorAll('[data-workflow-step]').length,
        contextChips: document.querySelectorAll('.context-chip').length,
        panels: document.querySelectorAll('.panel').length,
        forbidden: ['data-action="live-order"','data-action="broker-login"','data-action="account-trade"','주문 실행','계좌 로그인','브로커 로그인 버튼'].filter(x => document.documentElement.outerHTML.includes(x)),
        fetchCalls: window.__todo15FetchCalls || [],
        wsCalls: window.__todo15WebSocketCalls || [],
      }))()`);
      if (value.scrollWidth > viewport.width) fail(`${viewport.name} ${leaf} overflow ${value.scrollWidth}`);
      if (value.bodyTextLength < 500 || !value.h2) fail(`${viewport.name} ${leaf} appears blank`);
      if (value.workflowSteps !== 6 || value.contextChips !== 4) fail(`${viewport.name} ${leaf} missing workflow/context`);
      if (value.forbidden.length) fail(`${viewport.name} ${leaf} forbidden controls ${value.forbidden.join(',')}`);
      if (value.fetchCalls.length || value.wsCalls.length) fail(`${viewport.name} ${leaf} reference mode made executable calls`);
      results.push(value);
      await screenshot(`todo15_${viewport.name}_${leaf}.png`);
    }
  }
  await navigate('/ui/remodel/backtest?backend=http%3A%2F%2F127.0.0.1%3A9', 1280, 720, false);
  await new Promise(resolve => setTimeout(resolve, 5200));
  const liveFailure = await evaluate(`(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    liveMode: window.__STOM_REMODEL_LIVE_BACKEND__ === true,
    liveErrorCount: (document.body.innerText.match(/LIVE ERROR/g) || []).length,
    pendingOrManualCount: (document.body.innerText.match(/MANUAL-GATED|PENDING/g) || []).length,
    fetchCalls: window.__todo15FetchCalls || [],
    wsCalls: window.__todo15WebSocketCalls || [],
  }))()`);
  if (!liveFailure.liveMode) fail('live failure page was not in live mode');
  if (liveFailure.scrollWidth > 1280) fail(`live failure overflow ${liveFailure.scrollWidth}`);
  if (liveFailure.liveErrorCount < 1) fail('live backend failure did not surface LIVE ERROR');
  if (liveFailure.wsCalls.length) fail('live failure page opened a WebSocket');
  await screenshot('todo15_live_failure_backtest_1280.png');
  fs.writeFileSync(cdpPath, JSON.stringify({ deepLinks: results, liveFailure }, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
