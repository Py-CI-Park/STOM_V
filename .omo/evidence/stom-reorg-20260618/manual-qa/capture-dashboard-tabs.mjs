import { chromium } from "../../../../_temp_pw/node_modules/playwright/index.mjs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const baseUrl = process.argv[2];
if (!baseUrl) {
  throw new Error("Usage: node capture-dashboard-tabs.mjs http://127.0.0.1:<port>");
}

const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const tabs = [
  { key: "evolution", text: "진화 대시보드" },
  { key: "backtest", text: "백테스트" },
  { key: "simulation", text: "차트 시뮬레이션" },
  { key: "lab", text: "연구실" },
  { key: "pro", text: "분석 프로" },
  { key: "verdict", text: "결정 이력" },
  { key: "process", text: "프로세스 흐름" },
];

const summary = {
  started_at: new Date().toISOString(),
  baseUrl,
  chromePath,
  tabs: [],
  console: [],
  pageErrors: [],
};

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  page.on("console", msg => {
    if (["error", "warning"].includes(msg.type())) {
      summary.console.push({ type: msg.type(), text: msg.text() });
    }
  });
  page.on("pageerror", err => summary.pageErrors.push(String(err)));
  await page.addInitScript(() => {
    localStorage.setItem("stom_active_tab", "invalid-tab-from-qa");
  });
  await page.goto(`${baseUrl}/ui/`, { waitUntil: "networkidle", timeout: 20000 });
  for (const tab of tabs) {
    const tabStarted = Date.now();
    const tabButton = page.locator('button[role="tab"]').filter({ hasText: tab.text }).first();
    await tabButton.click({ timeout: 10000 });
    await page.waitForTimeout(800);
    const html = await page.content();
    const htmlPath = path.join(__dirname, `${tab.key}.html`);
    const pngPath = path.join(__dirname, `${tab.key}.png`);
    await fs.writeFile(htmlPath, html, "utf8");
    await page.screenshot({ path: pngPath, fullPage: true });
    const rootText = (await page.locator("#root").innerText({ timeout: 5000 })).slice(0, 500);
    summary.tabs.push({
      key: tab.key,
      label: tab.text,
      html: path.basename(htmlPath),
      png: path.basename(pngPath),
      htmlLength: html.length,
      rootTextLength: rootText.length,
      duration_ms: Date.now() - tabStarted,
    });
  }
  const processRouteStarted = Date.now();
  await page.goto(`${baseUrl}/process_flow`, { waitUntil: "networkidle", timeout: 20000 });
  const processRouteHtml = await page.content();
  await fs.writeFile(path.join(__dirname, "process-flow-route.html"), processRouteHtml, "utf8");
  await page.screenshot({ path: path.join(__dirname, "process-flow-route.png"), fullPage: true });
  summary.processRoute = {
    html: "process-flow-route.html",
    png: "process-flow-route.png",
    htmlLength: processRouteHtml.length,
    duration_ms: Date.now() - processRouteStarted,
  };
} finally {
  await browser.close();
}

summary.ended_at = new Date().toISOString();
await fs.writeFile(path.join(__dirname, "browser-capture-summary.json"), JSON.stringify(summary, null, 2), "utf8");
console.log(JSON.stringify(summary, null, 2));
