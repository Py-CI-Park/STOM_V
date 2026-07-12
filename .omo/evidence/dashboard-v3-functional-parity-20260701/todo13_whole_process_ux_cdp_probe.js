const fs = require('fs');
const wsUrl = process.env.CDP_WS;
const targetUrl = process.env.TARGET_URL;
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
    if (result.exceptionDetails) fail(result.exceptionDetails.text || 'Runtime.evaluate exception');
    return result.result && result.result.value;
  }
  async function screenshot(name) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    fs.writeFileSync(`${outDir}/${name}`, Buffer.from(shot.data, 'base64'));
  }
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      window.__todo13FetchCalls = [];
      window.__todo13WebSocketOpened = false;
      const nativeFetch = window.fetch;
      window.fetch = function(input, init) {
        window.__todo13FetchCalls.push(String((input && input.url) || input || ''));
        return nativeFetch.apply(this, arguments);
      };
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        window.__todo13WebSocketOpened = true;
        return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
      };
      window.WebSocket.prototype = NativeWebSocket.prototype;
      Object.setPrototypeOf(window.WebSocket, NativeWebSocket);
    })();`
  });
  const results = [];
  for (const viewport of [
    { name: '1440', width: 1440, height: 900, mobile: false },
    { name: '1280', width: 1280, height: 720, mobile: false },
    { name: '390', width: 390, height: 844, mobile: true },
  ]) {
    await send('Emulation.setDeviceMetricsOverride', { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.mobile });
    await send('Page.navigate', { url: targetUrl });
    await new Promise(resolve => setTimeout(resolve, 1400));
    const base = await evaluate(`(() => ({
      viewport: '${viewport.name}',
      scrollWidth: document.documentElement.scrollWidth,
      workflowSteps: document.querySelectorAll('[data-workflow-step]').length,
      activeStep: document.querySelector('.workflow-step.active')?.getAttribute('data-workflow-step') || '',
      contextChips: document.querySelectorAll('.context-chip').length,
      runGen: document.querySelector('[data-context-run-gen]')?.textContent || '',
      strategy: document.querySelector('[data-context-strategy]')?.textContent || '',
      symbolDate: document.querySelector('[data-context-symbol-date]')?.textContent || '',
      decision: document.querySelector('[data-context-decision]')?.textContent || '',
      fetchCalls: window.__todo13FetchCalls || [],
      websocketOpened: window.__todo13WebSocketOpened === true,
    }))()`);
    if (base.scrollWidth > viewport.width) fail(`viewport ${viewport.name} overflow ${base.scrollWidth}`);
    if (base.workflowSteps !== 6 || base.contextChips !== 4) fail(`viewport ${viewport.name} missing workflow/context`);
    results.push(base);
    await screenshot(`todo13_workflow_${viewport.name}.png`);
  }
  const nav = await evaluate(`(async () => {
    const clickStep = async (id) => {
      document.querySelector('[data-workflow-step="' + id + '"]').click();
      await new Promise(resolve => setTimeout(resolve, 250));
      return {
        id,
        path: location.pathname,
        active: document.querySelector('.workflow-step.active')?.getAttribute('data-workflow-step') || '',
        rail: document.querySelectorAll('[data-workflow-step]').length,
        chips: document.querySelectorAll('.context-chip').length,
        scrollWidth: document.documentElement.scrollWidth,
      };
    };
    const backtest = await clickStep('backtest');
    const replay = await clickStep('replay');
    const audit = await clickStep('audit');
    document.querySelector('[data-workflow-step="settings"]').click();
    await new Promise(resolve => setTimeout(resolve, 200));
    return {
      backtest,
      replay,
      audit,
      settingsModal: Boolean(document.querySelector('.modal-backdrop.open')),
      finalPath: location.pathname,
      scrollWidth: document.documentElement.scrollWidth,
    };
  })()`);
  if (nav.backtest.path !== '/ui/remodel/backtest' || nav.backtest.active !== 'backtest') fail('backtest workflow navigation failed');
  if (nav.replay.path !== '/ui/remodel/chart-replay' || nav.replay.active !== 'replay') fail('replay workflow navigation failed');
  if (nav.audit.path !== '/ui/remodel/audit' || nav.audit.active !== 'audit') fail('audit workflow navigation failed');
  if (!nav.settingsModal) fail('settings workflow did not open modal');
  if (nav.scrollWidth > 390) fail(`navigation overflow ${nav.scrollWidth}`);
  const stress = await evaluate(`(() => {
    const longStrategy = 'Strategy_' + 'LONG_CONTEXT_NAME_'.repeat(10);
    const strip = window.RemodelWorkflowUX.renderSharedContextStrip({
      run_id: 'RUN_' + 'X'.repeat(72),
      gen_no: 9999,
      strategy: longStrategy,
      code: '005930-' + 'LONGSYMBOL'.repeat(6),
      date: '20250516-20250517-20250518',
      decision: 'hold-with-additional-oos-validation-required',
    });
    document.querySelector('[data-shared-context-strip]').outerHTML = strip;
    const stressPanel = document.createElement('section');
    stressPanel.className = 'panel';
    const headers = Array.from({ length: 14 }, (_, i) => '<th>dense_col_' + i + '</th>').join('');
    const row = Array.from({ length: 14 }, (_, i) => '<td>' + ('dense_value_' + i + '_').repeat(4) + '</td>').join('');
    stressPanel.innerHTML = '<div class="notice danger">' + 'Long error message '.repeat(50) + '</div><div class="table-wrap"><table><thead><tr>' + headers + '</tr></thead><tbody><tr>' + row + '</tr></tbody></table></div><div class="table-wrap"><table><tbody></tbody></table></div>';
    document.querySelector('#page').prepend(stressPanel);
    return {
      scrollWidth: document.documentElement.scrollWidth,
      contextChips: document.querySelectorAll('.context-chip').length,
      longStrategyVisible: document.querySelector('[data-context-strategy]')?.textContent.includes('LONG_CONTEXT_NAME') || false,
      longErrorVisible: document.querySelector('.notice.danger')?.textContent.length > 300,
      denseTableColumns: document.querySelectorAll('th').length,
      emptyTablePresent: Boolean(document.querySelector('.table-wrap table tbody:empty')),
    };
  })()`);
  if (stress.scrollWidth > 390) fail(`stress overflow ${stress.scrollWidth}`);
  if (!stress.longStrategyVisible || !stress.longErrorVisible || stress.denseTableColumns < 14 || !stress.emptyTablePresent) fail('stress DOM checks failed');
  await screenshot('todo13_workflow_stress_390.png');
  const finalValue = { viewports: results, navigation: nav, stress };
  fs.writeFileSync(cdpPath, JSON.stringify(finalValue, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
