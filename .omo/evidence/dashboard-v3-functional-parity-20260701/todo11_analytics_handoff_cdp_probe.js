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
      window.__handoffSetItemCalls = [];
      window.__handoffWebSocketOpened = false;
      const nativeSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function(key, value) {
        window.__handoffSetItemCalls.push(String(key));
        return nativeSetItem.apply(this, arguments);
      };
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        window.__handoffWebSocketOpened = true;
        return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
      };
      window.WebSocket.prototype = NativeWebSocket.prototype;
      Object.setPrototypeOf(window.WebSocket, NativeWebSocket);
    })();`
  });
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 1100, deviceScaleFactor: 1, mobile: true });
  await send('Page.navigate', { url: targetUrl });
  await new Promise(resolve => setTimeout(resolve, 1600));
  const expression = `(() => {
    const api = window.AnalyticsHandoffSurface;
    const ready = api.context({ run_id: 'runP', gen_no: 0, buy: 'B', sell: 'S', date: '20250516', code: '005930' });
    const condition = api.conditionToBacktest(ready);
    const replay = api.backtestToReplay({ job_id: 'J10235', date: '20250516', code: '005930', buy: 'B', sell: 'S' });
    const missing = api.validate(api.context({ run_id: '', gen_no: -1, buy: '', sell: '' }));
    return {
      viewport: 390,
      scrollWidth: document.documentElement.scrollWidth,
      hasSurface: Boolean(document.querySelector('[data-analytics-handoff-surface]')),
      endpointCount: document.querySelectorAll('[data-analytics-endpoint]').length,
      conditionHandoff: Boolean(document.querySelector('[data-condition-to-backtest-handoff]')),
      replayHandoff: Boolean(document.querySelector('[data-backtest-to-replay-handoff]')),
      disabledReason: document.querySelector('[data-handoff-disabled-reason]')?.getAttribute('data-handoff-disabled-reason') || '',
      backtestRoute: document.querySelector('[data-condition-to-backtest-handoff]')?.getAttribute('data-handoff-route') || '',
      replayRoute: document.querySelector('[data-backtest-to-replay-handoff]')?.getAttribute('data-handoff-route') || '',
      ready,
      condition,
      replay,
      missing,
      setItemCalls: window.__handoffSetItemCalls || [],
      websocketOpened: window.__handoffWebSocketOpened === true,
    };
  })()`;
  const evaluated = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  const value = evaluated.result && evaluated.result.value;
  if (!value) fail('CDP evaluation returned no value');
  if (value.scrollWidth > 390) fail(`horizontal overflow ${value.scrollWidth}`);
  if (!value.hasSurface || value.endpointCount !== 3) fail('analytics surface or endpoint cards missing');
  if (!value.conditionHandoff || !value.replayHandoff) fail('handoff cards missing');
  if (value.backtestRoute !== '/ui/remodel/backtest') fail('backtest route mismatch');
  if (value.replayRoute !== '/ui/remodel/chart-replay') fail('replay route mismatch');
  if (value.condition.payload.mode !== 'backtest' || value.condition.prefillOnly !== true) fail('condition handoff is not prefill-only backtest payload');
  if (value.replay.payload.action !== 'start' || value.replay.prefillOnly !== true) fail('replay handoff is not prefill-only start payload');
  if (value.missing.ok !== false || value.missing.disabledReason !== 'Incomplete context disables handoff actions.') fail('incomplete context did not disable');
  if (value.setItemCalls.length !== 0) fail(`handoff wrote localStorage: ${value.setItemCalls.join(', ')}`);
  if (value.websocketOpened) fail('handoff opened WebSocket');
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(screenshotPath, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(cdpPath, JSON.stringify(value, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
