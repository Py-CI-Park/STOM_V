import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import esbuild from "esbuild";

const HERE = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(HERE, "../../..");
const DEFAULT_ENTRY = resolve(HERE, "src/track-z-entry.pilot.js");
const NODE_MODULES = resolve(HERE, "node_modules");

function parseArgs(argv) {
  let entry = DEFAULT_ENTRY;
  let json = false;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--json") {
      json = true;
    } else if (arg === "--entry") {
      const value = argv[index + 1];
      if (!value) throw new Error("--entry requires a path");
      entry = isAbsolute(value) ? value : resolve(HERE, value);
      index += 1;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return { entry: resolve(entry), json };
}

function displayPath(path) {
  const local = relative(HERE, path).replaceAll("\\", "/");
  return local.startsWith("../") ? path.replaceAll("\\", "/") : local;
}

function diagnosticText(error) {
  if (error && Array.isArray(error.errors)) {
    return error.errors.map((item) => {
      const location = item.location;
      const where = location
        ? `${displayPath(resolve(PROJECT_ROOT, location.file))}:${location.line}:${location.column}`
        : "runtime-jsx";
      return `${where}: ${item.text}`;
    }).sort();
  }
  return [String(error instanceof Error ? error.message : error)];
}

function graphHash(paths) {
  const hash = createHash("sha256");
  for (const path of paths) {
    const normalized = path.replaceAll("\\", "/");
    const modulesAt = normalized.lastIndexOf("/node_modules/");
    const identity = modulesAt >= 0
      ? normalized.slice(modulesAt + 1)
      : relative(PROJECT_ROOT, path).replaceAll("\\", "/");
    hash.update(identity);
    hash.update("\0");
    hash.update(readFileSync(path));
    hash.update("\0");
  }
  return hash.digest("hex");
}

async function check(entry) {
  if (!existsSync(entry)) throw new Error(`entry does not exist: ${displayPath(entry)}`);
  const result = await esbuild.build({
    entryPoints: [entry],
    absWorkingDir: PROJECT_ROOT,
    bundle: true,
    format: "iife",
    platform: "browser",
    target: "es2018",
    jsx: "transform",
    jsxFactory: "React.createElement",
    jsxFragment: "React.Fragment",
    minify: false,
    sourcemap: false,
    write: false,
    metafile: true,
    logLevel: "silent",
    loader: { ".jsx": "jsx" },
    nodePaths: [NODE_MODULES],
    alias: {
      "react/jsx-runtime": resolve(HERE, "src/react-jsx-runtime-shim.js"),
      "react/jsx-dev-runtime": resolve(HERE, "src/react-jsx-runtime-shim.js"),
      react: resolve(HERE, "src/react-shim.js"),
      "react-dom": resolve(HERE, "src/react-dom-shim.js"),
      "react-dom/client": resolve(HERE, "src/react-dom-shim.js"),
      "@xyflow/react": resolve(HERE, "node_modules/@xyflow/react/dist/esm/index.js"),
      dagre: resolve(HERE, "node_modules/dagre/index.js"),
    },
  });
  const inputs = Object.keys(result.metafile.inputs)
    .map((path) => isAbsolute(path) ? path : resolve(PROJECT_ROOT, path))
    .filter((path) => existsSync(path))
    .sort((left, right) => displayPath(left).localeCompare(displayPath(right)));
  const jsxInputs = inputs.filter((path) => path.endsWith(".jsx"));
  for (const path of jsxInputs) {
    await esbuild.transform(readFileSync(path, "utf8"), {
      loader: "jsx",
      jsx: "transform",
      jsxFactory: "React.createElement",
      jsxFragment: "React.Fragment",
      target: "es2018",
      sourcefile: displayPath(path),
      sourcemap: false,
    });
  }
  return {
    status: "pass",
    entry: displayPath(entry),
    graph_files: inputs.length,
    jsx_files: jsxInputs.length,
    graph_hash: graphHash(inputs),
    emitted_bytes: result.outputFiles.reduce((total, file) => total + file.contents.byteLength, 0),
    engines: { esbuild: esbuild.version, jsx_runtime: "classic-react-create-element" },
    diagnostics: [],
  };
}

let json = process.argv.includes("--json");
try {
  const args = parseArgs(process.argv.slice(2));
  json = args.json;
  const report = await check(args.entry);
  process.stdout.write(json ? `${JSON.stringify(report, null, 2)}\n` :
    `[runtime-jsx] PASS ${report.jsx_files} JSX / ${report.graph_files} graph files ${report.graph_hash}\n`);
} catch (error) {
  const report = { status: "fail", diagnostics: diagnosticText(error) };
  process.stdout.write(json ? `${JSON.stringify(report, null, 2)}\n` :
    `[runtime-jsx] FAIL\n${report.diagnostics.map((item) => `  ${item}`).join("\n")}\n`);
  process.exitCode = 1;
}
