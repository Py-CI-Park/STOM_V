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
      window.__conditionDetailFetches = [];
      const nativeFetch = window.fetch;
      window.fetch = function(input, init) {
        const url = String(input && input.url ? input.url : input);
        if (/\/(strategy_code|strategy_diff|prompts|ai_context_pack|backtest_detail)(\?|$)/.test(url)) {
          window.__conditionDetailFetches.push(url);
        }
        return nativeFetch.apply(this, arguments);
      };
    })();`
  });
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 1100, deviceScaleFactor: 1, mobile: true });
  await send('Page.navigate', { url: targetUrl });
  await new Promise(resolve => setTimeout(resolve, 1600));
  const expression = `(() => {
    const surfaceApi = window.ConditionDetailSurface;
    const ready = surfaceApi.context({ run_id: 'runP', gen_no: 0 });
    const missingRun = surfaceApi.context({ run_id: '', gen_no: 0 });
    const missingGen = surfaceApi.context({ run_id: 'runP', gen_no: -1 });
    const endpoints = surfaceApi.contracts.map(contract => surfaceApi.endpoint(contract, ready));
    const missingHtml = surfaceApi.render(missingRun);
    const surface = document.querySelector('[data-condition-detail-surface]');
    return {
      viewport: 390,
      scrollWidth: document.documentElement.scrollWidth,
      hasSurface: Boolean(surface),
      domContext: surface ? surface.getAttribute('data-condition-detail-context') : null,
      apiCardCount: document.querySelectorAll('[data-condition-detail-api]').length,
      emptyCount: document.querySelectorAll('[data-condition-detail-empty]').length,
      selector: Boolean(document.querySelector('[data-condition-run-gen-selector]')),
      endpoints,
      ready,
      missingRun,
      missingGen,
      missingHtmlHasEmpty: missingHtml.includes('data-condition-detail-empty'),
      fetches: window.__conditionDetailFetches || [],
    };
  })()`;
  const evaluated = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  const value = evaluated.result && evaluated.result.value;
  if (!value) fail('CDP evaluation returned no value');
  if (value.scrollWidth > 390) fail(`horizontal overflow ${value.scrollWidth}`);
  if (!value.hasSurface || !value.selector) fail('missing condition detail surface or selector');
  if (value.apiCardCount !== 5) fail(`expected 5 API cards, got ${value.apiCardCount}`);
  if (!value.endpoints.includes('/strategy_code?run=runP&gen=0')) fail('strategy_code endpoint mismatch');
  if (!value.endpoints.includes('/strategy_diff?run_id=runP&gen_no=0&base_gen=previous')) fail('strategy_diff endpoint mismatch');
  if (value.missingRun.status !== 'missing-run') fail('missing run context was not preserved');
  if (value.missingGen.status !== 'missing-gen') fail('missing gen context was not preserved');
  if (!value.missingHtmlHasEmpty || value.emptyCount < 5) fail('empty states missing from DOM or render API');
  if (value.fetches.length !== 0) fail(`reference mode fetched condition detail APIs: ${value.fetches.join(', ')}`);
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(screenshotPath, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(cdpPath, JSON.stringify(value, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
