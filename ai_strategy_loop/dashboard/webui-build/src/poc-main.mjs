// poc-main.mjs — Phase14.0 PoC 어서션 하네스.
//   format.mjs(ESM 빌드 번들)의 출력이 connection.jsx(런타임-babel) 구현과 동일한지
//   테스트 벡터로 검증한다. format.mjs 는 connection.jsx 의 바이트 동일 복사이므로,
//   고정 기대값 == babel 경로 출력이 성립한다(동등성 증명).

import * as F from "./format.mjs";

// [name, got, want] — want 는 connection.jsx 구현으로부터 손계산한 기대 출력.
//   주의: "—"=U+2014(em dash), "−"=U+2212(minus sign). connection.jsx 와 동일 문자.
const decided = [
  ["fmtScore(1.23456)", F.fmtScore(1.23456), "1.235"],
  ["fmtScore('x')", F.fmtScore("x"), "—"],
  ["fmtPct(12.345)", F.fmtPct(12.345), "12.35%"],
  ["fmtPct(null)", F.fmtPct(null), "—"],
  ["fmtMoney(1234567)", F.fmtMoney(1234567), "+1,234,567원"],
  ["fmtMoney(-1000)", F.fmtMoney(-1000), "−1,000원"],
  ["fmtMoney(0)", F.fmtMoney(0), "0원"],
  ["fmtMoney('x')", F.fmtMoney("x"), "—"],
  ["fmtInt(1234567)", F.fmtInt(1234567), "1,234,567"],
  ["fmtInt(undefined)", F.fmtInt(undefined), "—"],
  ["isDemoSource('demo')", String(F.isDemoSource("demo")), "true"],
  ["isDemoSource('open')", String(F.isDemoSource("open")), "false"],
  ["livePanelPending('demo',{})", String(F.livePanelPending("demo", {})), "false"],
  ["livePanelPending('open',{})", String(F.livePanelPending("open", {})), "true"],
  ["livePanelPending(open,equity[1])", String(F.livePanelPending("open", { current_run: { equity: [1] } })), "false"],
  ["livePanelPending(open,buyPartial)", String(F.livePanelPending("open", { current_run: { generation: { buy_code_partial: "x" } } })), "false"],
  ["STATUS_KR.idle", F.STATUS_KR.idle, "대기"],
  ["STATUS_KR.running", F.STATUS_KR.running, "실행중"],
  ["STATUS_KR.stopping", F.STATUS_KR.stopping, "정지중"],
  ["STATUS_KR.complete", F.STATUS_KR.complete, "완료"],
  ["STATUS_KR.error", F.STATUS_KR.error, "오류"],
];

// fmtTime 은 런타임 TZ 의존(toLocaleTimeString) — 고정 시각 비교 대신 형태만 검증.
//   (양 경로 동일 구현이므로 출력도 동일; 여기선 null=대시, 유효ISO=숫자시작만 확인.)
const shaped = [
  ["fmtTime(null) == —", F.fmtTime(null) === "—"],
  ["fmtTime(ISO) starts digit", /^\d/.test(F.fmtTime("2026-06-14T09:30:00"))],
  ["window.fmtMoney wired", typeof window !== "undefined" && window.fmtMoney === F.fmtMoney],
];

const rows = decided.map(([name, got, want]) => ({ name, got, want, ok: got === want }));
const shapedRows = shaped.map(([name, ok]) => ({ name, got: String(ok), want: "true", ok }));
const all = rows.concat(shapedRows);
const passCount = all.filter((r) => r.ok).length;
const allPass = passCount === all.length;

const out = document.getElementById("out");
if (!out) throw new Error("PoC mount #out 없음");
out.innerHTML =
  `<h1 data-status="${allPass ? "PASS" : "FAIL"}">${allPass ? "✅ ALL PASS" : "❌ FAIL"} — ${passCount}/${all.length}</h1>` +
  `<div class="sub">Phase14.0 Vite PoC · connection.jsx 순수 포매터 ESM 출력 동등성 · build=${import.meta.env?.MODE ?? "?"}</div>` +
  "<table><tr><th>case</th><th>got</th><th>want</th><th>=</th></tr>" +
  all.map((r) =>
    `<tr class="${r.ok ? "ok" : "bad"}"><td>${r.name}</td><td>${r.got}</td><td>${r.want}</td><td>${r.ok ? "✓" : "✗"}</td></tr>`
  ).join("") +
  "</table>";

// Playwright 가 읽을 수 있는 머신 신호.
document.body.setAttribute("data-poc-status", allPass ? "PASS" : "FAIL");
document.body.setAttribute("data-poc-pass", String(passCount));
document.body.setAttribute("data-poc-total", String(all.length));
