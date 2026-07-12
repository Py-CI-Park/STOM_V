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
  async function navigate(path, width, height) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: `${baseUrl}${path}` });
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  async function screenshot(name) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    fs.writeFileSync(`${outDir}/${name}`, Buffer.from(shot.data, 'base64'));
  }
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      window.__desktopProbeFetchCalls = [];
      window.__desktopProbeWebSocketCalls = [];
      const nativeFetch = window.fetch;
      window.fetch = function(input, init) {
        window.__desktopProbeFetchCalls.push({ url: String((input && input.url) || input || ''), method: String((init && init.method) || 'GET') });
        return nativeFetch.apply(this, arguments);
      };
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        window.__desktopProbeWebSocketCalls.push(String(url));
        return protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
      };
      window.WebSocket.prototype = NativeWebSocket.prototype;
      Object.setPrototypeOf(window.WebSocket, NativeWebSocket);
    })();`
  });
  const pages = ['condition', 'process', 'history', 'lab', 'workbench', 'audit', 'backtest', 'chart-replay'];
  const viewports = [
    { name: 'desktop-1280', width: 1280, height: 720 },
    { name: 'desktop-1440', width: 1440, height: 900 },
    { name: 'desktop-1920', width: 1920, height: 1080 },
  ];
  const checks = [];
  for (const viewport of viewports) {
    for (const page of pages) {
      await navigate(`/ui/remodel/${page}?demo=reference`, viewport.width, viewport.height);
      const value = await evaluate(`(() => {
        const vw = ${viewport.width};
        const heatmapIssues = Array.from(document.querySelectorAll('.heatmap')).map((hm, idx) => {
          const hr = hm.getBoundingClientRect();
          const childIssues = Array.from(hm.children).map((child) => {
            const r = child.getBoundingClientRect();
            return { tag: child.tagName, cls: child.className, text: (child.textContent || '').slice(0, 40), left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width), parentLeft: Math.round(hr.left), parentRight: Math.round(hr.right) };
          }).filter(x => x.right > Math.ceil(hr.right) + 1 || x.left < Math.floor(hr.left) - 1 || x.width <= 0);
          return { index: idx, left: Math.round(hr.left), right: Math.round(hr.right), width: Math.round(hr.width), childIssues: childIssues.slice(0, 8) };
        }).filter(x => x.childIssues.length);
        const graphicIssues = Array.from(document.querySelectorAll('[data-ux-chart], .chart-box, .chart-svg, .candle-chart, [data-ux-heatmap]')).map((el) => {
          const r = el.getBoundingClientRect();
          return { tag: el.tagName, cls: el.className, left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width), height: Math.round(r.height) };
        }).filter(x => x.width <= 0 || x.height <= 0 || x.left < -1 || x.right > vw + 1).slice(0, 8);
        return {
          href: location.href,
          page: '${page}',
          viewport: '${viewport.name}',
          viewportWidth: vw,
          docScrollWidth: document.documentElement.scrollWidth,
          bodyTextLength: document.body.innerText.length,
          h2: document.querySelector('h2')?.textContent || '',
          workflowSteps: document.querySelectorAll('[data-workflow-step]').length,
          contextChips: document.querySelectorAll('.context-chip').length,
          heatmapIssues,
          graphicIssues,
          fetchCalls: window.__desktopProbeFetchCalls || [],
          wsCalls: window.__desktopProbeWebSocketCalls || [],
        };
      })()`);
      if (value.docScrollWidth > viewport.width) fail(`${viewport.name} ${page} document overflow ${value.docScrollWidth}`);
      if (value.bodyTextLength < 500 || !value.h2) fail(`${viewport.name} ${page} appears blank`);
      if (value.workflowSteps !== 6 || value.contextChips !== 4) fail(`${viewport.name} ${page} missing workflow/context`);
      if (value.heatmapIssues.length) fail(`${viewport.name} ${page} heatmap child overflow ${JSON.stringify(value.heatmapIssues[0])}`);
      if (value.graphicIssues.length) fail(`${viewport.name} ${page} graphic overflow ${JSON.stringify(value.graphicIssues[0])}`);
      if (value.fetchCalls.length || value.wsCalls.length) fail(`${viewport.name} ${page} reference mode made executable calls`);
      checks.push(value);
      if (page === 'condition' || page === 'chart-replay' || page === 'backtest') {
        await screenshot(`todo02_${viewport.name}_${page}.png`);
      }
    }
  }
  fs.writeFileSync(cdpPath, JSON.stringify({ generatedAt: new Date().toISOString(), checks }, null, 2));
  ws.close();
}
main().catch(err => { console.error(err.stack || String(err)); process.exit(1); });
