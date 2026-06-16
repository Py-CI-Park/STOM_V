// check-missing-imports.mjs — STATIC GUARD for the decomposed frontend module graph.
//
//   WHY THIS EXISTS
//   The P5 file decomposition split large .jsx modules into many small sibling modules. A helper or
//   const defined+exported in module A but referenced BARE (no `import`) in module B is left by
//   esbuild's bundle as a runtime free-global. If module A does NOT republish that symbol on
//   `window` (via `Object.assign(window, {...})`), the bare read resolves to `undefined` and the
//   first call throws `ReferenceError: <sym> is not defined` — a crash the render harness can miss
//   because it does not exercise every data-fetch code path. (Production hit: `_btFetchJson is not
//   defined` in bt-result-area.jsx on the backtest results path.)
//
//   THE RULE (precise, principled)
//   A cross-module exported symbol is reachable at runtime in a consumer module in exactly two ways:
//     (1) the consumer `import { sym } from "./definer.jsx"`  — proper ESM edge, OR
//     (2) the definer publishes `sym` on window via `Object.assign(window, {...})` AND the bundle
//         leaves the consumer's bare read as a global lookup — the HARD-RULE window surface
//         (stom-ui fmt*, connection useBackend/DEFAULT_BASE, every `Object.assign(window,...)`
//         republished component). These are intentional and MUST NOT be import-converted.
//   So a BARE reference is a genuine MISSING IMPORT only when the symbol is:
//     (a) in the cross-module EXPORTED inventory (some sibling `export {}`s it), AND
//     (b) NOT in the consumer's locally-defined ∪ imported set, AND
//     (c) NOT published on window by ANY of its definers (else the global lookup saves it), AND
//     (d) actually referenced (not just appearing inside a comment/string).
//
//   OUTPUT: deterministic, ASCII-only. Exit 0 = zero violations. Exit 1 = violations (listed).
//   Repeatable: re-run after any frontend change; the pytest guard wraps this.

import { readdirSync, readFileSync } from "node:fs";
import { resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(__dirname, "../frontend");

// ---------------------------------------------------------------------------
// 1) Lexical scrub — remove comments + string/template/regex literals so later regex/token scans
//    never see identifiers that live inside text. Conservative single-pass char scanner.
// ---------------------------------------------------------------------------
function scrub(src) {
  let out = "";
  let i = 0;
  const n = src.length;
  // Track the last significant char to disambiguate `/` (divide vs regex). Simple heuristic that is
  // safe for this codebase (no exotic regex-after-value cases that would alter identifier scanning).
  let prevSig = "";
  while (i < n) {
    const c = src[i];
    const c2 = src[i + 1];
    // line comment
    if (c === "/" && c2 === "/") {
      i += 2;
      while (i < n && src[i] !== "\n") i++;
      continue;
    }
    // block comment
    if (c === "/" && c2 === "*") {
      i += 2;
      while (i < n && !(src[i] === "*" && src[i + 1] === "/")) i++;
      i += 2;
      out += " ";
      continue;
    }
    // string literals ' " `
    if (c === '"' || c === "'") {
      const q = c;
      i++;
      while (i < n) {
        if (src[i] === "\\") { i += 2; continue; }
        if (src[i] === q) { i++; break; }
        i++;
      }
      out += '""';
      prevSig = '"';
      continue;
    }
    if (c === "`") {
      // template literal — also blank out ${...} contents (they may hold identifiers, but for the
      // purpose of "is sym referenced" we conservatively keep ${...} code, since template exprs can
      // legitimately call helpers). Re-scan inside expressions instead of blanking.
      i++;
      out += "`";
      while (i < n) {
        if (src[i] === "\\") { i += 2; continue; }
        if (src[i] === "`") { i++; out += "`"; break; }
        if (src[i] === "$" && src[i + 1] === "{") {
          // copy the expression through (depth-tracked) so referenced identifiers are still seen.
          out += "${";
          i += 2;
          let depth = 1;
          while (i < n && depth > 0) {
            if (src[i] === "{") depth++;
            else if (src[i] === "}") depth--;
            if (depth === 0) { out += "}"; i++; break; }
            out += src[i];
            i++;
          }
          continue;
        }
        // plain template text -> drop (becomes nothing)
        i++;
      }
      prevSig = "`";
      continue;
    }
    // regex literal — only when `/` cannot be a divide (prevSig is empty or an operator/paren/comma).
    if (c === "/") {
      const canBeRegex = prevSig === "" || "(,=:[!&|?{};+-*%<>~^".includes(prevSig) || /[\s]/.test(prevSig);
      if (canBeRegex) {
        let j = i + 1;
        let ok = false;
        let inClass = false;
        while (j < n) {
          const cj = src[j];
          if (cj === "\\") { j += 2; continue; }
          if (cj === "\n") break;
          if (cj === "[") inClass = true;
          else if (cj === "]") inClass = false;
          else if (cj === "/" && !inClass) { ok = true; break; }
          j++;
        }
        if (ok) {
          i = j + 1;
          // skip regex flags
          while (i < n && /[a-z]/i.test(src[i])) i++;
          out += "0";
          prevSig = "0";
          continue;
        }
      }
    }
    out += c;
    if (!/\s/.test(c)) prevSig = c;
    i++;
  }
  return out;
}

// strip comments but KEEP string/template/regex literal contents intact. Used only for parsing
//   `import ... from "<specifier>"` (the specifier string must survive). Same comment-skipping +
//   literal-skipping logic as scrub(), but literals are copied through verbatim.
function stripCommentsKeepStrings(src) {
  let out = "";
  let i = 0;
  const n = src.length;
  let prevSig = "";
  while (i < n) {
    const c = src[i];
    const c2 = src[i + 1];
    if (c === "/" && c2 === "/") { i += 2; while (i < n && src[i] !== "\n") i++; continue; }
    if (c === "/" && c2 === "*") { i += 2; while (i < n && !(src[i] === "*" && src[i + 1] === "/")) i++; i += 2; out += " "; continue; }
    if (c === '"' || c === "'") {
      const q = c; out += c; i++;
      while (i < n) {
        out += src[i];
        if (src[i] === "\\") { out += src[i + 1] ?? ""; i += 2; continue; }
        if (src[i] === q) { i++; break; }
        i++;
      }
      prevSig = q; continue;
    }
    if (c === "`") {
      out += c; i++;
      while (i < n) {
        out += src[i];
        if (src[i] === "\\") { out += src[i + 1] ?? ""; i += 2; continue; }
        if (src[i] === "`") { i++; break; }
        i++;
      }
      prevSig = "`"; continue;
    }
    out += c;
    if (!/\s/.test(c)) prevSig = c;
    i++;
  }
  return out;
}

// ---------------------------------------------------------------------------
// 2) Per-file extraction from scrubbed source.
// ---------------------------------------------------------------------------
const IDENT = "[A-Za-z_$][A-Za-z0-9_$]*";

// names inside an `export { a, b as c }` -> the EXPORTED (outer) names.
function parseExportNames(code) {
  const names = new Set();
  const re = /export\s*\{([^}]*)\}/g;
  let m;
  while ((m = re.exec(code))) {
    for (const part of m[1].split(",")) {
      const t = part.trim();
      if (!t) continue;
      // `local as exported` -> exported is what consumers see
      const asMatch = t.match(new RegExp(`^(${IDENT})\\s+as\\s+(${IDENT})$`));
      names.add(asMatch ? asMatch[2] : t);
    }
  }
  return names;
}

// imports: `import { a, b as c } from "./x.jsx"` (local binding names) + default/namespace + bare.
function parseImports(code) {
  const localNames = new Set();
  const sources = new Set(); // module specifiers imported from (for completeness/debug)
  // named
  const reNamed = /import\s+(?:([A-Za-z_$][\w$]*)\s*,\s*)?\{([^}]*)\}\s*from\s*["']([^"']+)["']/g;
  let m;
  while ((m = reNamed.exec(code))) {
    if (m[1]) localNames.add(m[1]); // default in `import Def, { ... }`
    for (const part of m[2].split(",")) {
      const t = part.trim();
      if (!t) continue;
      const asMatch = t.match(new RegExp(`^(${IDENT})\\s+as\\s+(${IDENT})$`));
      localNames.add(asMatch ? asMatch[2] : t);
    }
    sources.add(m[3]);
  }
  // default-only: import Def from "..."
  const reDef = /import\s+([A-Za-z_$][\w$]*)\s+from\s*["']([^"']+)["']/g;
  while ((m = reDef.exec(code))) { localNames.add(m[1]); sources.add(m[2]); }
  // namespace: import * as NS from "..."
  const reNs = /import\s+\*\s+as\s+([A-Za-z_$][\w$]*)\s+from\s*["']([^"']+)["']/g;
  while ((m = reNs.exec(code))) { localNames.add(m[1]); sources.add(m[2]); }
  return { localNames, sources };
}

// locally-defined names: function/class decls, top-level & nested const/let/var bindings
// (incl. object/array destructure such as `const {useState: useState_x} = React` and
// `const X = window.X`). We collect ALL binding names defensively (over-collecting only makes the
// checker MORE conservative — it never produces a false violation, only risks missing one).
function parseDefined(code) {
  const names = new Set();
  let m;
  // function NAME( ... )   and   async function NAME
  const reFn = new RegExp(`function\\s+(${IDENT})\\s*\\(`, "g");
  while ((m = reFn.exec(code))) names.add(m[1]);
  // class NAME
  const reClass = new RegExp(`class\\s+(${IDENT})`, "g");
  while ((m = reClass.exec(code))) names.add(m[1]);
  // simple bindings: const/let/var NAME =   (single identifier target)
  const reSimple = new RegExp(`\\b(?:const|let|var)\\s+(${IDENT})\\s*=`, "g");
  while ((m = reSimple.exec(code))) names.add(m[1]);
  // destructure bindings: const { a, b: bb, c } = ...   and   const [ x, y ] = ...
  const reObjD = /\b(?:const|let|var)\s*\{([^}]*)\}\s*=/g;
  while ((m = reObjD.exec(code))) {
    for (const part of m[1].split(",")) {
      const t = part.trim();
      if (!t) continue;
      // `key: local` -> local is the binding; `name` -> name; ignore `...rest` rest captured below
      const kv = t.match(new RegExp(`^(?:${IDENT}\\s*:\\s*)?(${IDENT})`));
      if (kv) names.add(kv[1]);
      const rest = t.match(new RegExp(`^\\.\\.\\.(${IDENT})$`));
      if (rest) names.add(rest[1]);
    }
  }
  const reArrD = /\b(?:const|let|var)\s*\[([^\]]*)\]\s*=/g;
  while ((m = reArrD.exec(code))) {
    for (const part of m[1].split(",")) {
      const t = part.trim().replace(/^\.\.\./, "");
      const id = t.match(new RegExp(`^(${IDENT})`));
      if (id) names.add(id[1]);
    }
  }
  return names;
}

// names republished on window via `Object.assign(window, { ... })` (one or more blocks).
function parseWindowPublished(code) {
  const names = new Set();
  const re = /Object\.assign\s*\(\s*window\s*,\s*\{/g;
  let m;
  while ((m = re.exec(code))) {
    // capture balanced { ... } following the match
    let i = re.lastIndex - 1; // at the `{`
    let depth = 0;
    let body = "";
    for (; i < code.length; i++) {
      const ch = code[i];
      if (ch === "{") depth++;
      else if (ch === "}") { depth--; if (depth === 0) break; }
      if (depth >= 1) body += ch;
    }
    for (const part of body.replace(/^\{/, "").split(",")) {
      const t = part.trim();
      if (!t) continue;
      // `key: value` (shorthand `key` or `key: expr`) -> the published KEY is what window exposes.
      const key = t.match(new RegExp(`^(${IDENT})\\s*(?::|$)`));
      if (key) names.add(key[1]);
    }
  }
  return names;
}

// collect BARE identifier references in the scrubbed code — i.e. identifiers used as free
//   variables, NOT as a member access. We MUST exclude member positions:
//     - `obj.NAME`            (property read; resolves on the object, not the module scope)
//     - `obj ?. NAME`         (optional chaining)
//     - `window.NAME`         (the HARD-RULE window surface — `typeof window.BtVarChips === ...`)
//   A symbol referenced ONLY as `window.X`/`obj.X` is never a missing-import (it never tries to
//   resolve `X` as a free binding). This is what kept the BtVarChips false-positive out.
//   We also exclude object-literal shorthand-free `key:` positions only when they are clearly keys;
//   to stay conservative we keep `key:` as a reference (collisions on the underscore helper names
//   are vanishingly rare and only ever ADD a violation we would otherwise want).
function collectReferencedIdents(code) {
  const refs = new Set();
  // (?<![.\w$]) — not a member access (no preceding `.`) and not the tail of a longer identifier.
  // optional-chaining `?.` ends in `.`, so it is also excluded by the `.` in the lookbehind.
  const re = new RegExp(`(?<![.\\w$])(${IDENT})`, "g");
  let m;
  while ((m = re.exec(code))) refs.add(m[1]);
  return refs;
}

// ---------------------------------------------------------------------------
// 3) Build the project model.
// ---------------------------------------------------------------------------
const files = readdirSync(FRONTEND)
  .filter((f) => f.endsWith(".jsx"))
  .sort();

const model = new Map(); // file -> { exports, importNames, defined, windowPub, refs }
for (const f of files) {
  const raw = readFileSync(resolve(FRONTEND, f), "utf8");
  const code = scrub(raw);
  // IMPORTANT: imports are parsed from RAW source — scrub() blanks string literals to "", which
  //   would destroy the `from "./module.jsx"` specifier (the regex requires a non-empty specifier).
  //   The `import { ... }` binding list itself is plain identifiers, unaffected by raw vs scrubbed.
  //   To avoid picking up an `import` token that appears inside a comment/string, we parse imports
  //   from a comment-stripped-but-string-preserving variant.
  const codeNoComments = stripCommentsKeepStrings(raw);
  model.set(f, {
    exports: parseExportNames(code),
    importNames: parseImports(codeNoComments).localNames,
    defined: parseDefined(code),
    windowPub: parseWindowPublished(code),
    refs: collectReferencedIdents(code),
  });
}

// cross-module exported inventory: symbol -> [definer files]
const inventory = new Map();
for (const [f, info] of model) {
  for (const sym of info.exports) {
    if (!inventory.has(sym)) inventory.set(sym, []);
    inventory.get(sym).push(f);
  }
}

// global set of symbols published on window by ANY module (the runtime global-lookup safety net).
const windowPublishedAnywhere = new Set();
for (const [, info] of model) {
  for (const sym of info.windowPub) windowPublishedAnywhere.add(sym);
}

// ---------------------------------------------------------------------------
// 4) Detect violations.
// ---------------------------------------------------------------------------
const violations = []; // { module, symbol, definer }
for (const [f, info] of model) {
  for (const sym of info.refs) {
    if (!inventory.has(sym)) continue;            // (a) must be a cross-module exported symbol
    const definers = inventory.get(sym).filter((d) => d !== f);
    if (definers.length === 0) continue;          // exported only by THIS file -> local, fine
    if (info.exports.has(sym) || info.defined.has(sym)) continue; // defined locally here
    if (info.importNames.has(sym)) continue;      // (b) already imported
    if (windowPublishedAnywhere.has(sym)) continue; // (c) reachable via window global lookup
    // (d) genuine bare reference -> missing import. Pick the (single) sibling definer.
    const definer = definers.length === 1 ? definers[0] : definers.sort().join("|");
    violations.push({ module: f, symbol: sym, definer });
  }
}

violations.sort((a, b) =>
  a.module === b.module
    ? (a.symbol < b.symbol ? -1 : a.symbol > b.symbol ? 1 : 0)
    : (a.module < b.module ? -1 : 1),
);

// ---------------------------------------------------------------------------
// 5) Report (ASCII-only, deterministic).
// ---------------------------------------------------------------------------
const wantJson = process.argv.includes("--json");
if (wantJson) {
  process.stdout.write(JSON.stringify({
    files: files.length,
    inventorySize: inventory.size,
    windowPublished: windowPublishedAnywhere.size,
    violations,
  }, null, 2) + "\n");
} else {
  console.log(`[check-missing-imports] scanned ${files.length} .jsx modules`);
  console.log(`[check-missing-imports] cross-module exported symbols: ${inventory.size}`);
  console.log(`[check-missing-imports] window-published symbols (global-lookup safe): ${windowPublishedAnywhere.size}`);
  if (violations.length === 0) {
    console.log("[check-missing-imports] OK: ZERO missing cross-module imports.");
  } else {
    console.log(`[check-missing-imports] FAIL: ${violations.length} missing import(s):`);
    for (const v of violations) {
      console.log(`  ${v.module}  ->  ${v.symbol}  (definer: ${v.definer})  ==>  add: import { ${v.symbol} } from "./${v.definer.replace(/\.jsx$/, "")}.jsx";`);
    }
  }
}

process.exit(violations.length === 0 ? 0 : 1);
