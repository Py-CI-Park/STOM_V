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
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = () => reject(new Error('CDP websocket open failed'));
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      const NativeWebSocket = window.WebSocket;
      window.__replayStreamAutoOpened = false;
      window.WebSocket = function(url, protocols) {
        if (String(url).includes('/sim/ws')) window.__replayStreamAutoOpened = true;
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
    const timeline = window.ReplayTimeline;
    const cursor = timeline.normalizeCursor({
      bars: [{ t: '090000', code: '005930', c: 71000 }, { t: '093000', code: '005930', c: 71400 }],
      signals: [{ time: '093000', signal: 'BUY', stock: '005930', price: 71400 }],
      trades: [],
      positions: [],
      logs: ['manual probe'],
      selectedIndex: 1,
    });
    const handoff = timeline.handoffContext({ date: '20250516', code: '005930', buy: 'B', sell: 'S', selectedIndex: 1 });
    const emptyHtml = timeline.render({ bars: [], signals: [], trades: [], positions: [], logs: [] }, { code: '005930', name: 'Samsung' });
    const surface = document.querySelector('[data-replay-timeline-surface]');
    const investigation = document.querySelector('.replay-investigation-grid');
    const surfaceRect = surface ? surface.getBoundingClientRect() : null;
    const investigationRect = investigation ? investigation.getBoundingClientRect() : null;
    return {
      viewport: 390,
      scrollWidth: document.documentElement.scrollWidth,
      hasSurface: Boolean(surface),
      sharedCursor: surface ? surface.getAttribute('data-replay-cursor-source') : null,
      timelineCount: document.querySelectorAll('[data-replay-timeline]').length,
      signalEventCount: document.querySelectorAll('[data-replay-event-kind="signal"]').length,
      tradeEventCount: document.querySelectorAll('[data-replay-event-kind="trade"]').length,
      positionEventCount: document.querySelectorAll('[data-replay-event-kind="position"]').length,
      selectedDetail: Boolean(document.querySelector('[data-replay-selected-detail]')),
      backtestHandoff: Boolean(document.querySelector('[data-replay-backtest-handoff]')),
      handoffSource: document.querySelector('[data-replay-backtest-handoff]')?.getAttribute('data-replay-handoff-source') || null,
      streamAutoOpened: window.__replayStreamAutoOpened === true,
      cursor,
      handoff,
      emptySignals: emptyHtml.includes('data-replay-empty-signals'),
      emptyTrades: emptyHtml.includes('data-replay-empty-trades'),
      orderedBeforeChart: surfaceRect && investigationRect ? surfaceRect.bottom <= investigationRect.top + 1 : false,
    };
  })()`;
  const evaluated = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  const value = evaluated.result && evaluated.result.value;
  if (!value) fail('CDP evaluation returned no value');
  if (value.scrollWidth > 390) fail(`horizontal overflow ${value.scrollWidth}`);
  if (!value.hasSurface || value.sharedCursor !== 'shared') fail('missing shared replay timeline surface');
  if (!value.selectedDetail || !value.backtestHandoff) fail('missing selected detail or handoff card');
  if (value.handoffSource !== 'bt-result-localStorage-event') fail('handoff source mismatch');
  if (!value.handoff.prefillReady) fail('handoff prefill not ready');
  if (value.cursor.selectedIndex !== 1 || value.cursor.selectedTime !== '093000') fail('cursor normalization mismatch');
  if (!value.emptySignals || !value.emptyTrades) fail('empty signal/trade states missing');
  if (value.signalEventCount < 1 || value.tradeEventCount < 1 || value.positionEventCount < 1) fail('event timeline categories missing');
  if (!value.orderedBeforeChart) fail('timeline surface overlaps or follows chart investigation grid');
  if (value.streamAutoOpened) fail('/sim/ws stream auto-opened');
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(screenshotPath, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(cdpPath, JSON.stringify(value, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
